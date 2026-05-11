"""health/snapshot WS handler — Phase 15-D."""
from __future__ import annotations

from typing import Final, Optional

from nyrahost.health import HealthDashboard

ERR_BAD_INPUT: Final[int] = -32602


def _err(code: int, message: str, detail: str = "") -> dict:
    out: dict = {"error": {"code": code, "message": message}}
    if detail:
        out["error"]["data"] = {"detail": detail}
    return out


class HealthHandlers:
    def __init__(self, dashboard: HealthDashboard) -> None:
        self._dash = dashboard

    async def on_snapshot(self, params: dict, session=None, ws=None) -> dict:
        try:
            recent_window = float(params.get("recent_window_s", 300.0))
        except (TypeError, ValueError):
            return _err(ERR_BAD_INPUT, "bad_recent_window")
        last_crash = params.get("last_crash_count")
        last_perf = params.get("last_perf_violations")
        last_hyg = params.get("last_hygiene_findings")
        snap = self._dash.snapshot(
            recent_window_s=recent_window,
            last_crash_count=int(last_crash) if last_crash is not None else None,
            last_perf_violations=int(last_perf) if last_perf is not None else None,
            last_hygiene_findings=int(last_hyg) if last_hyg is not None else None,
        )
        return snap.to_dict()


__all__ = ["HealthHandlers", "ERR_BAD_INPUT"]
