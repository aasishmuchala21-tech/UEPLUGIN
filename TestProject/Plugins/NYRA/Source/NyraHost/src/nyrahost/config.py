"""Runtime config resolved from CLI args + env.

Immutable dataclass; passed through run_server so handlers read from
one source of truth. Default handshake_dir follows D-06 (primary
`%LOCALAPPDATA%/NYRA/`, POSIX fallback `~/.local/share/NYRA/`).
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NyraConfig:
    editor_pid: int
    log_dir: Path
    handshake_dir: Path
    bind_host: str = "127.0.0.1"
    bind_port: int = 0  # 0 == OS ephemeral
    ws_max_frame_bytes: int = 16 * 1024 * 1024
    ws_ping_interval_s: int = 30
    ws_ping_timeout_s: int = 10
    auth_token_bytes: int = 32

    @staticmethod
    def default_handshake_dir() -> Path:
        la = os.environ.get("LOCALAPPDATA")
        if la:
            return Path(la) / "NYRA"
        return Path.home() / ".local" / "share" / "NYRA"
