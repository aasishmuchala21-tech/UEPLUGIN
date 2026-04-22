"""diagnostics/download-gemma request handler.

The UE panel calls this once; NyraHost replies immediately with
``{started: true}`` (or ``{already_present: true, size_bytes: N}`` if
the file is already on disk, or ``{already_running: true}`` if a
download is already in flight) and streams progress via
``diagnostics/download-progress`` notifications on the same WS session.

See docs/JSONRPC.md §3.7 for the notification shape and
docs/ERROR_CODES.md for the -32005 remediation string surfaced when
both primary + mirror URLs fail.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import structlog
from websockets.server import ServerConnection

from ..downloader.gemma import (
    GEMMA_FILENAME,
    GemmaSpec,
    download_gemma,
)
from ..jsonrpc import build_notification
from ..session import SessionState

log = structlog.get_logger("nyrahost.download")


@dataclass
class DownloadHandlers:
    """Per-NyraHost-process download surface.

    One instance is constructed in :func:`app.build_and_run` and
    registered on the singleton :class:`NyraServer`. ``_inflight``
    tracks the active download task (at most one at a time).
    """

    project_dir: Path
    spec: GemmaSpec
    _inflight: Optional[asyncio.Task] = field(default=None)

    def dest_path(self) -> Path:
        return (
            self.project_dir
            / "Saved"
            / "NYRA"
            / "models"
            / GEMMA_FILENAME
        )

    async def on_download_gemma(
        self, params: dict, session: SessionState
    ) -> dict:
        ws: ServerConnection | None = getattr(session, "_ws", None)
        if ws is None:
            return {
                "started": False,
                "error": {
                    "code": -32001,
                    "message": "internal",
                    "data": {
                        "remediation": "No active WS bound to session.",
                    },
                },
            }
        if self._inflight is not None and not self._inflight.done():
            return {"started": False, "already_running": True}

        dest = self.dest_path()
        if dest.exists():
            # Size check only — full verify is the downloader's job if requested
            return {
                "started": False,
                "already_present": True,
                "size_bytes": dest.stat().st_size,
            }

        async def emit(progress_params: dict) -> None:
            try:
                frame = build_notification("diagnostics/download-progress", progress_params)
                await ws.send(frame)
            except Exception:  # noqa: BLE001
                pass

        async def run() -> None:
            try:
                await download_gemma(
                    spec=self.spec,
                    dest_path=dest,
                    emit_progress=emit,
                )
            except Exception:  # noqa: BLE001
                log.exception("gemma_download_task_failed")

        self._inflight = asyncio.create_task(run())
        return {"started": True}
