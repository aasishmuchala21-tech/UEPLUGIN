"""settings/repro/* WS handlers — Phase 14-A."""
from __future__ import annotations

from typing import Final, Optional

from nyrahost.reproducibility import ReproPinStore

ERR_BAD_INPUT: Final[int] = -32602
ERR_OUT_OF_RANGE: Final[int] = -32056


def _err(code: int, message: str, detail: str = "", remediation: Optional[str] = None) -> dict:
    data: dict = {}
    if detail:
        data["detail"] = detail
    if remediation:
        data["remediation"] = remediation
    out: dict = {"error": {"code": code, "message": message}}
    if data:
        out["error"]["data"] = data
    return out


class ReproHandlers:
    def __init__(self, store: ReproPinStore | None = None) -> None:
        self._store = store or ReproPinStore()

    @property
    def store(self) -> ReproPinStore:
        return self._store

    async def on_get(self, params: dict, session=None, ws=None) -> dict:
        conv = params.get("conversation_id")
        if not isinstance(conv, str) or not conv:
            return _err(ERR_BAD_INPUT, "missing_field", "conversation_id")
        pin = self._store.get(conv)
        return {
            "conversation_id": conv,
            "seed": pin.seed,
            "temperature": pin.temperature,
            "has_seed": pin.has_seed,
            "has_temperature": pin.has_temperature,
        }

    async def on_set(self, params: dict, session=None, ws=None) -> dict:
        conv = params.get("conversation_id")
        if not isinstance(conv, str) or not conv:
            return _err(ERR_BAD_INPUT, "missing_field", "conversation_id")
        seed = params.get("seed")
        temp = params.get("temperature")
        ok = self._store.set(conv, seed=seed, temperature=temp)
        if not ok:
            return _err(
                ERR_OUT_OF_RANGE, "repro_out_of_range",
                f"seed={seed} temperature={temp}",
                remediation=(
                    "seed must be -1 (unpinned) or 0..2^63-1; "
                    "temperature must be -1.0 (unpinned) or 0.0..1.0"
                ),
            )
        return {"saved": True, "conversation_id": conv}

    async def on_clear(self, params: dict, session=None, ws=None) -> dict:
        conv = params.get("conversation_id")
        if not isinstance(conv, str) or not conv:
            return _err(ERR_BAD_INPUT, "missing_field", "conversation_id")
        cleared = self._store.clear(conv)
        return {"cleared": cleared, "conversation_id": conv}


__all__ = ["ReproHandlers", "ERR_BAD_INPUT", "ERR_OUT_OF_RANGE"]
