"""ClaudeBackend — Claude Code CLI subprocess driver (Plan 02-05).

Drives the user's local ``claude`` CLI as a subprocess so NYRA never sees
the OAuth token (it lives in ``%USERPROFILE%\.claude\ACLs`` per RESEARCH §10.9).

Per D-02 critical caveats (RESEARCH §1.1):
  * NEVER use ``--bare`` — subscription mode requires OAuth which --bare skips.
  * ALWAYS scrub ``ANTHROPIC_API_KEY`` and ``ANTHROPIC_AUTH_TOKEN`` from the
    child env so a parent-process API key cannot redirect traffic.

Phase 0 gate (SC#1):
  This module is LIVE code — the ``claude_available`` flag gates whether the
  router uses ``ClaudeBackend`` or falls back to ``GemmaBackend``. The flag
  is ``False`` by default and flips to ``True`` only after the founder files
  the Anthropic ToS written clearance (SC#1 verdict). The backend class is
  fully implemented; the SC#1 gate controls routing, not presence.

Architecture:
  1. ``send()`` writes a per-session MCP config via ``claude_mcp_config.py``.
  2. ``send()`` builds the argv per RESEARCH §1.1 locked flag set.
  3. ``send()`` spawns ``claude -p ...`` with scrubbed env.
  4. ``send()`` reads NDJSON from stdout, parsing via ``StreamParser``.
  5. Each parsed ``BackendEvent`` is emitted to the caller-supplied ``on_event``.
  6. ``cancel()`` sends SIGTERM (Windows: ``proc.terminate()`` → CTRL_C_EVENT).
  7. ``health_check()`` runs ``claude auth status`` and maps exit code.

No rate-limit fallback logic here — that lands in Plan 02-06.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
from pathlib import Path
from typing import Final

import structlog

from nyrahost.attachments import AttachmentRef
from nyrahost.backends.base import (
    AgentBackend,
    BackendEvent,
    Done,
    Error,
    HealthState,
)
from nyrahost.backends.claude_mcp_config import (
    MCP_CONFIGS_DIR,
    cleanup_stale_configs,
    write_mcp_config,
)
from nyrahost.backends.claude_stream import StreamParser

__all__ = ["ClaudeBackend"]

log: Final = structlog.get_logger(__name__)

# Keys scrubbed from the child process env (D-02 trap; RESEARCH §1.2)
_SCRUB_KEYS: Final = frozenset(("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"))

# Error code for subprocess crash (JSON-RPC convention from ERROR_CODES.md)
_SUBPROCESS_ERROR_CODE: Final = -32_001


class ClaudeBackend(AgentBackend):
    """Claude Code CLI subprocess adapter.

    ``name = "claude"`` is the key used in ``BACKEND_REGISTRY['claude']``.
    """

    name: str = "claude"

    def __init__(
        self,
        *,
        claude_path: Path | str = "claude",
        python_exe: Path | str | None = None,
        handshake_file: Path | str | None = None,
    ) -> None:
        self._claude_path: Final[Path] = Path(claude_path)
        self._python_exe: Final[Path] = (
            Path(python_exe) if python_exe is not None
            else self._find_bundled_python()
        )
        self._handshake_file: Final[Path | None] = (
            Path(handshake_file) if handshake_file is not None else None
        )
        # req_id → asyncio.subprocess.Process (live children)
        self._inflight: dict[str, asyncio.subprocess.Process] = {}

    # ------------------------------------------------------------------
    # AgentBackend API
    # ------------------------------------------------------------------

    async def send(
        self,
        conversation_id: str,
        req_id: str,
        content: str,
        attachments: list[AttachmentRef],
        mcp_config_path: Path | None,
        on_event: callable,
    ) -> None:
        """Spawn ``claude -p`` and stream BackendEvent objects to ``on_event``."""
        import uuid as uuid_lib

        session_id = str(uuid_lib.uuid4())
        python_exe = self._python_exe

        # 1. Write per-session MCP config
        mcp_configs_dir = MCP_CONFIGS_DIR
        mcp_config_file = mcp_configs_dir / f"{session_id}.json"

        # Ensure parent dir exists
        mcp_configs_dir.mkdir(parents=True, exist_ok=True)

        # handshake_file defaults to None (no MCP server inject on very first
        # launch before NyraHost has written its handshake file)
        hf = self._handshake_file

        write_mcp_config(
            session_id=session_id,
            conversation_id=conversation_id,
            python_exe=python_exe,
            handshake_file=hf,
            out_path=mcp_config_file,
        )

        # CR-02: feed the prompt via stdin (--input-format=stream-json) rather
        # than positionally on argv. On Windows, CreateProcess + CommandLineToArgvW
        # reassemble argv from the joined command line; embedded `"`, NUL, or
        # leading `--` in user content can split the argument and inject flags
        # (e.g. an LLM-emitted system prompt containing
        # ` --dangerously-skip-permissions ` would land as a real flag).
        # Reject NUL bytes and feed the rest through stdin where the argv
        # parser cannot reach.
        if "\x00" in content:
            raise ValueError(
                "[-32030] prompt contains NUL byte; rejected to prevent "
                "Windows argv-reassembly truncation"
            )

        argv = [
            str(self._claude_path),
            "-p",
            "--input-format", "stream-json",
            "--output-format", "stream-json",
            "--verbose",
            "--include-partial-messages",
            "--mcp-config", str(mcp_config_file),
            "--strict-mcp-config",
            "--session-id", session_id,
            "--permission-mode", "dontAsk",
            "--permission-prompt-tool", "nyra_permission_gate",
        ]
        # CR-02: argv no longer carries the user-controlled `content`.
        # The prompt is written to stdin below as a JSON-RPC message frame
        # (Claude CLI's documented stream-json input format).

        # 3. Scrub API-key env vars from child env (D-02; RESEARCH §1.2)
        child_env: dict[str, str] = {}
        for k, v in os.environ.items():
            if k not in _SCRUB_KEYS:
                child_env[k] = v

        # 4. Spawn
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                env=child_env,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            log.error("claude_binary_not_found", path=str(self._claude_path))
            await on_event(
                Error(
                    code=_SUBPROCESS_ERROR_CODE,
                    message="claude_not_installed",
                    remediation=(
                        "Run 'claude auth login' in a terminal to install and "
                        "authenticate the Claude CLI."
                    ),
                    retryable=False,
                )
            )
            return

        self._inflight[req_id] = proc

        # CR-02: write the user prompt to stdin as a stream-json input frame.
        # Per Claude CLI docs (RESEARCH §1.1), --input-format=stream-json
        # reads a single JSON message from stdin: {"type":"user", "message":
        # {"role":"user","content":[{"type":"text","text":"..."}]}}.
        try:
            assert proc.stdin is not None
            input_frame = json.dumps({
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": content}],
                },
            })
            proc.stdin.write((input_frame + "\n").encode("utf-8"))
            await proc.stdin.drain()
            proc.stdin.close()
        except Exception as exc:
            log.warning("claude_stdin_write_failed", error=str(exc))

        # 5. Read NDJSON lines from stdout, parse, emit
        parser = StreamParser()
        try:
            assert proc.stdout is not None
            async for raw_line in proc.stdout:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    events = parser.parse_line(line)
                except ValueError:  # malformed JSON — skip, don't crash
                    log.warning("malformed_ndjson_line", line=line[:100])
                    continue
                for ev in events:
                    await on_event(ev)
        except asyncio.CancelledError:
            proc.terminate()
            raise
        finally:
            self._inflight.pop(req_id, None)
            # 6. Reap if still alive (cancelled or crash path)
            if proc.returncode is None:
                try:
                    await asyncio.wait_for(proc.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()

            # Cleanup stale configs (every ~10 requests)
            cleanup_stale_configs(mcp_configs_dir, max_age_seconds=86_400)

    async def cancel(self, req_id: str) -> None:
        """SIGTERM the in-flight subprocess matching ``req_id``."""
        proc = self._inflight.get(req_id)
        if proc is not None and proc.returncode is None:
            proc.terminate()

    async def health_check(self) -> HealthState:
        """Run ``claude auth status`` and map exit code to HealthState."""
        try:
            proc = await asyncio.create_subprocess_exec(
                str(self._claude_path),
                "auth",
                "status",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            if proc.returncode == 0:
                return HealthState.READY
            if proc.returncode == 1:
                return HealthState.AUTH_DRIFT
            return HealthState.UNKNOWN
        except FileNotFoundError:
            return HealthState.NOT_INSTALLED
        except Exception:  # noqa: BLE001
            return HealthState.UNKNOWN

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _find_bundled_python() -> Path:
        """Locate the bundled CPython 3.12 interpreter.

        Follows D-13: ``Binaries/Win64/NyraHost/python/python.exe`` is the
        canonical bundled path. Falls back to ``python`` on PATH so tests
        running against system Python still work.
        """
        bundled = (
            Path(__file__).resolve().parents[4]
            / "Binaries"
            / "Win64"
            / "NyraHost"
            / "python"
            / "python.exe"
        )
        if bundled.is_file():
            return bundled
        # Fallback: use whatever ``python`` is on PATH (dev/test path)
        fallback = shutil.which("python")
        if fallback is not None:
            return Path(fallback)
        raise RuntimeError(
            "Cannot find bundled python.exe. "
            "Set python_exe= when constructing ClaudeBackend."
        )