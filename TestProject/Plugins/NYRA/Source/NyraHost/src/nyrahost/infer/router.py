"""Backend router: Ollama fast path vs bundled llama-server.

Implements D-19 lazy spawn + 10-min idle shutdown and D-20 OpenAI-compatible
chat/completions streaming.

Order of operations on first chat/send:
  1. Probe Ollama at http://127.0.0.1:11434/api/tags — if gemma3:4b-it-qat
     tag is present, use Ollama (no subprocess spawn).
  2. Else probe GPU backend (CUDA > Vulkan > CPU) and spawn bundled
     llama-server.exe from the matching per-backend folder. If the
     preferred backend's binary is missing or fails to launch, fall
     through to the next backend in the order.
  3. Record last_request_ts; a background _idle_watchdog task runs every
     60s and SIGTERMs the llama-server subprocess if idle for ≥10 min.
     Next request lazily re-spawns via the same selection logic.

The router never raises on graceful cases (Ollama missing, a GPU
backend binary missing). It only raises :class:`RuntimeError` when
all candidate backends fail — this is surfaced to UE as
``-32001 subprocess_failed`` via chat/send.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import AsyncIterator, Callable

import httpx
import structlog

from .gpu_probe import GpuBackend, probe_gpu_backend
from .llama_server import (
    InferHandle,
    llama_server_executable_path,
    spawn_llama_server,
)
from .ollama_probe import detect_ollama
from .sse import SseEvent, aiter_sse_deltas

log = structlog.get_logger("nyrahost.router")

IDLE_SHUTDOWN_SECONDS = 10 * 60
IDLE_CHECK_INTERVAL_SECONDS = 60

# Backend fallback order when a GPU backend binary fails to launch.
_BACKEND_FALLBACK: list[GpuBackend] = [
    GpuBackend.CUDA,
    GpuBackend.VULKAN,
    GpuBackend.CPU,
]


class BackendChoice(str, Enum):
    OLLAMA = "ollama"
    BUNDLED = "bundled"


@dataclass
class RouterState:
    choice: BackendChoice
    base_url: str
    model_name: str
    handle: InferHandle | None = None
    last_request_ts: float = 0.0


class InferRouter:
    def __init__(
        self,
        *,
        plugin_binaries_dir: Path,
        gguf_path_getter: Callable[[], Path],
    ):
        self._plugin_binaries_dir = plugin_binaries_dir
        self._gguf_path_getter = gguf_path_getter
        self._state: RouterState | None = None
        self._lock = asyncio.Lock()
        self._idle_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start idle-shutdown background task."""
        self._idle_task = asyncio.create_task(self._idle_watchdog())

    async def stop(self) -> None:
        if self._idle_task is not None:
            self._idle_task.cancel()
        if self._state and self._state.handle is not None:
            await self._state.handle.terminate()

    async def gemma_not_installed(self) -> bool:
        """True iff Gemma GGUF is absent AND Ollama fast path is unavailable.

        Used by chat/send to emit ``-32005 gemma_not_installed`` instead
        of trying (and failing) to spawn llama-server. Plan 09's Gemma
        downloader surfaces a user-facing remediation when this returns
        True.
        """
        gguf = self._gguf_path_getter()
        if gguf.exists() and gguf.stat().st_size > 0:
            return False
        # If Ollama with gemma3:4b-it-qat is present, we're OK too
        return (await detect_ollama()) is None

    async def _ensure_backend(self) -> RouterState:
        """Lazy-resolve the backend. Ollama if available, else bundled."""
        if self._state is not None:
            return self._state
        async with self._lock:
            if self._state is not None:
                return self._state
            ollama = await detect_ollama()
            if ollama is not None:
                self._state = RouterState(
                    choice=BackendChoice.OLLAMA,
                    base_url=ollama,
                    model_name="gemma3:4b-it-qat",
                    last_request_ts=time.time(),
                )
                log.info("backend_chosen", choice="ollama")
                return self._state

            gpu = await probe_gpu_backend()
            handle = await self._spawn_bundled_with_fallback(gpu)
            self._state = RouterState(
                choice=BackendChoice.BUNDLED,
                base_url=handle.base_url,
                model_name="gemma-3-4b-it",
                handle=handle,
                last_request_ts=time.time(),
            )
            log.info(
                "backend_chosen",
                choice="bundled",
                port=handle.port,
                backend=handle.backend.value,
            )
            return self._state

    async def _spawn_bundled_with_fallback(
        self, preferred: GpuBackend
    ) -> InferHandle:
        # Order: preferred then the remaining in the canonical fallback order.
        order = [preferred] + [
            b for b in _BACKEND_FALLBACK if b != preferred
        ]
        last_err: Exception | None = None
        gguf = self._gguf_path_getter()
        if not gguf.exists():
            raise FileNotFoundError(f"Gemma GGUF not found at {gguf}")
        for backend in order:
            exe = llama_server_executable_path(
                self._plugin_binaries_dir, backend
            )
            if not exe.exists():
                log.info(
                    "llama_server_exe_missing",
                    backend=backend.value,
                    path=str(exe),
                )
                continue
            try:
                return await spawn_llama_server(
                    exe_path=exe, gguf_path=gguf, backend=backend,
                )
            except Exception as e:  # noqa: BLE001
                last_err = e
                log.warning(
                    "llama_server_spawn_failed",
                    backend=backend.value,
                    err=str(e),
                )
                continue
        raise RuntimeError(
            f"All llama-server backends failed; last_err={last_err}"
        )

    async def _idle_watchdog(self) -> None:
        while True:
            await asyncio.sleep(IDLE_CHECK_INTERVAL_SECONDS)
            if self._state is None or self._state.handle is None:
                continue
            idle_for = time.time() - self._state.last_request_ts
            if idle_for >= IDLE_SHUTDOWN_SECONDS:
                log.info("llama_server_idle_shutdown", idle_s=idle_for)
                async with self._lock:
                    await self._state.handle.terminate()
                    self._state = None

    # ---- Streaming ----
    async def stream_chat(
        self,
        *,
        content: str,
        cancel_event: asyncio.Event,
    ) -> AsyncIterator[SseEvent]:
        state = await self._ensure_backend()
        state.last_request_ts = time.time()
        url = f"{state.base_url}/v1/chat/completions"
        body = {
            "model": state.model_name,
            "messages": [{"role": "user", "content": content}],
            "stream": True,
        }
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5, read=None, write=None, pool=None)
        ) as client:
            async with client.stream("POST", url, json=body) as resp:
                resp.raise_for_status()

                async def line_iter():
                    async for line in resp.aiter_lines():
                        if cancel_event.is_set():
                            return
                        yield line

                async for ev in aiter_sse_deltas(line_iter()):
                    yield ev
                    if cancel_event.is_set():
                        return
