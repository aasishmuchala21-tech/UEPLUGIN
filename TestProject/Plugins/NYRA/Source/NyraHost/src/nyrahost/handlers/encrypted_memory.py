"""memory/* WS handlers — Phase 15-A."""
from __future__ import annotations

from typing import Final, Optional

from nyrahost.encrypted_memory import EncryptedMemory, MAX_MEMORY_BYTES

ERR_BAD_INPUT: Final[int] = -32602
ERR_TOO_LARGE: Final[int] = -32063
ERR_FAILED: Final[int] = -32064


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


class EncryptedMemoryHandlers:
    def __init__(self, mem: EncryptedMemory) -> None:
        self._mem = mem

    async def on_get(self, params: dict, session=None, ws=None) -> dict:
        key = params.get("key")
        if not isinstance(key, str) or not key:
            return _err(ERR_BAD_INPUT, "missing_field", "key")
        return {"key": key, "value": self._mem.get_key(key)}

    async def on_set(self, params: dict, session=None, ws=None) -> dict:
        key = params.get("key")
        if not isinstance(key, str) or not key:
            return _err(ERR_BAD_INPUT, "missing_field", "key")
        if "value" not in params:
            return _err(ERR_BAD_INPUT, "missing_field", "value")
        try:
            self._mem.set_key(key, params["value"])
        except ValueError as exc:
            return _err(
                ERR_TOO_LARGE, "memory_too_large", str(exc),
                remediation=f"Memory body cap is {MAX_MEMORY_BYTES} bytes.",
            )
        except (OSError, TypeError) as exc:
            return _err(ERR_FAILED, "memory_set_failed", str(exc))
        return {"saved": True, "key": key}

    async def on_delete(self, params: dict, session=None, ws=None) -> dict:
        key = params.get("key")
        if not isinstance(key, str) or not key:
            return _err(ERR_BAD_INPUT, "missing_field", "key")
        return {"deleted": self._mem.delete_key(key), "key": key}

    async def on_dump(self, params: dict, session=None, ws=None) -> dict:
        return {"data": self._mem.load()}


__all__ = ["EncryptedMemoryHandlers", "ERR_BAD_INPUT", "ERR_TOO_LARGE", "ERR_FAILED"]
