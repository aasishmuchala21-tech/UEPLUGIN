"""Rate-limited progress reporter for downloader + future bulk tasks.

Emits ``diagnostics/download-progress`` frames per docs/JSONRPC.md §3.7.
The emit hook is caller-supplied so the same reporter works in tests
(list appender) and in the real handler (WS notification send).

Rate-limit policy (D-17): no more than one ``downloading`` frame per
RATE_LIMIT_MS milliseconds OR every RATE_LIMIT_BYTES — whichever trips
first. Terminal frames (``verifying`` / ``done`` / ``error``) bypass
the rate limit so the UE panel always sees the final status.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Literal

RATE_LIMIT_MS = 500  # min time between consecutive "downloading" frames
RATE_LIMIT_BYTES = 10 * 1024 * 1024  # 10 MB

ProgressStatus = Literal["downloading", "verifying", "done", "error"]
Emit = Callable[[dict], Awaitable[None]]  # async callable; receives params dict


@dataclass
class ProgressReporter:
    emit: Emit  # async callable wrapping build_notification + ws.send
    asset: str
    total_bytes: int
    _last_emit_ms: float = 0.0
    _last_bytes: int = 0
    _sent_any: bool = False

    async def downloading(self, bytes_done: int) -> None:
        now_ms = time.monotonic() * 1000
        if self._sent_any:
            ms_since = now_ms - self._last_emit_ms
            bytes_since = bytes_done - self._last_bytes
            if ms_since < RATE_LIMIT_MS and bytes_since < RATE_LIMIT_BYTES:
                return
        await self.emit({
            "asset": self.asset,
            "bytes_done": int(bytes_done),
            "bytes_total": int(self.total_bytes),
            "status": "downloading",
        })
        self._last_emit_ms = now_ms
        self._last_bytes = bytes_done
        self._sent_any = True

    async def verifying(self) -> None:
        await self.emit({
            "asset": self.asset,
            "bytes_done": int(self.total_bytes),
            "bytes_total": int(self.total_bytes),
            "status": "verifying",
        })

    async def done(self) -> None:
        await self.emit({
            "asset": self.asset,
            "bytes_done": int(self.total_bytes),
            "bytes_total": int(self.total_bytes),
            "status": "done",
        })

    async def error(
        self, *, code: int, message: str, remediation: str
    ) -> None:
        await self.emit({
            "asset": self.asset,
            "bytes_done": int(self._last_bytes),
            "bytes_total": int(self.total_bytes),
            "status": "error",
            "error": {
                "code": code,
                "message": message,
                "data": {"remediation": remediation},
            },
        })
