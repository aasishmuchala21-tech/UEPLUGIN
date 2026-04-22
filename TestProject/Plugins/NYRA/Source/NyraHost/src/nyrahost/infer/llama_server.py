"""llama-server subprocess spawn + port capture (D-18, RESEARCH §3.3, §3.5).

Canonical flags per RESEARCH §3.5 locked llama.cpp release (b8870):

    -m <gguf> --port 0 --host 127.0.0.1 --ctx-size 16384
    -ngl 99 --chat-template gemma --no-webui

``--port 0`` asks the kernel to assign an ephemeral port; llama-server
prints the chosen port on stdout as

    server listening at http://127.0.0.1:NNNNN

which we parse via :data:`PORT_RE`. A background ``_drain`` task consumes
remaining stdout after the port is captured so the pipe never fills and
blocks the subprocess.

Startup timeout defaults to 60s — model load for Gemma 4B Q4_0 is
typically 6-12s (cold) but can spike on first run because of Windows
Defender scanning the GGUF. The test suite passes a much shorter
timeout (2-5s) because the mock llama never loads a model.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path

import structlog

from .gpu_probe import GpuBackend

log = structlog.get_logger("nyrahost.llama_server")

# RESEARCH §3.3 Pattern B — port capture regex. llama.cpp's startup line
# can end with " for embeddings" or other suffixes on newer versions, so
# we anchor on the prefix and accept anything after the port number.
PORT_RE = re.compile(r"listening at http://[^:]+:(\d+)")

STARTUP_TIMEOUT_S = 60.0  # model load can take 6-12s; allow headroom


@dataclass
class InferHandle:
    """Owns a running llama-server subprocess.

    Call ``await handle.terminate()`` to SIGTERM+wait+kill cleanly. The
    drain task (captures stdout after the port line) is cancelled as
    part of termination so the event loop doesn't leak tasks.
    """

    proc: asyncio.subprocess.Process
    port: int
    backend: GpuBackend
    drain_task: asyncio.Task | None = None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    async def terminate(self) -> None:
        if self.proc.returncode is None:
            self.proc.terminate()
            try:
                await asyncio.wait_for(self.proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.proc.kill()
                await self.proc.wait()
        if self.drain_task is not None and not self.drain_task.done():
            self.drain_task.cancel()


def llama_server_executable_path(
    plugin_binaries_dir: Path, backend: GpuBackend
) -> Path:
    """Canonical layout: <Plugin>/Binaries/Win64/NyraInfer/<backend>/llama-server.exe."""
    return plugin_binaries_dir / "NyraInfer" / backend.value / "llama-server.exe"


async def spawn_llama_server(
    *,
    exe_path: Path,
    gguf_path: Path,
    backend: GpuBackend,
    ctx_size: int = 16384,
    startup_timeout_s: float = STARTUP_TIMEOUT_S,
) -> InferHandle:
    """Spawn llama-server bound to an ephemeral port; parse port from stdout.

    Returns an :class:`InferHandle` only after the port-announcement line
    is seen. On failure (process exit before port; startup timeout
    exceeded) raises :class:`RuntimeError` — the router is expected to
    catch and fall back to the next backend in the CUDA->Vulkan->CPU
    chain.

    Args:
        exe_path: path to llama-server.exe (per-backend folder)
        gguf_path: path to gemma-3-4b-it-qat-q4_0.gguf
        backend: which GPU backend's binary we're launching (for labelling)
        ctx_size: --ctx-size (Phase 1 default 16384)
        startup_timeout_s: max seconds to wait for port-announcement line
    """
    cmd = [
        str(exe_path),
        "-m", str(gguf_path),
        "--port", "0",
        "--host", "127.0.0.1",
        "--ctx-size", str(ctx_size),
        "-ngl", "99",
        "--chat-template", "gemma",
        "--no-webui",
    ]
    log.info("llama_server_spawn", cmd=cmd[0], backend=backend.value)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    port: int | None = None
    deadline = asyncio.get_event_loop().time() + startup_timeout_s
    while port is None:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            proc.terminate()
            await proc.wait()
            raise RuntimeError(
                f"llama-server ({backend.value}) did not announce port "
                f"within {startup_timeout_s}s"
            )
        if proc.returncode is not None:
            raise RuntimeError(
                f"llama-server ({backend.value}) exited with code "
                f"{proc.returncode} before port announcement"
            )
        try:
            line_bytes = await asyncio.wait_for(
                proc.stdout.readline(), timeout=remaining
            )
        except asyncio.TimeoutError:
            continue
        if not line_bytes:
            # EOF -> proc likely died; loop will see returncode next iter
            await asyncio.sleep(0.05)
            continue
        line = line_bytes.decode(errors="replace")
        log.debug("llama_server_stdout", line=line.rstrip())
        m = PORT_RE.search(line)
        if m:
            port = int(m.group(1))

    async def _drain() -> None:
        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                log.debug(
                    "llama_server_stdout",
                    line=line.decode(errors="replace").rstrip(),
                )
        except Exception:  # noqa: BLE001
            return

    drain_task = asyncio.create_task(_drain())
    log.info("llama_server_ready", port=port, backend=backend.value)
    return InferHandle(
        proc=proc, port=port, backend=backend, drain_task=drain_task
    )
