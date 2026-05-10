"""settings/get-instructions + settings/set-instructions handlers.

Phase 10-1. Wraps CustomInstructions for the WS dispatch surface.
Returns structured JSON-RPC envelopes so a malformed request never
crashes the chat handler.
"""
from __future__ import annotations

import os
from typing import Final, Optional

import structlog

from nyrahost.custom_instructions import CustomInstructions, MAX_BODY_BYTES

log = structlog.get_logger("nyrahost.handlers.instructions")

ERR_BAD_INPUT: Final[int] = -32602
ERR_TOO_LARGE: Final[int] = -32041
ERR_WRITE_FAILED: Final[int] = -32042


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


class InstructionsHandlers:
    """Reads + writes the per-project Custom Instructions file."""

    def __init__(self, instructions: CustomInstructions) -> None:
        self._instructions = instructions

    async def on_get(self, params: dict, session=None, ws=None) -> dict:
        # Always re-read disk before returning — the user may have
        # edited instructions.md externally between WS calls.
        body = self._instructions.reload()
        return {"body": body, "max_bytes": MAX_BODY_BYTES}

    async def on_set(self, params: dict, session=None, ws=None) -> dict:
        body = params.get("body")
        if not isinstance(body, str):
            return _err(ERR_BAD_INPUT, "missing_field", "body")
        try:
            path = self._instructions.save(body)
        except ValueError as exc:
            return _err(
                ERR_TOO_LARGE, "instructions_too_large", str(exc),
                remediation=f"Trim the body below {MAX_BODY_BYTES} bytes and retry.",
            )
        except (OSError, TypeError) as exc:
            return _err(ERR_WRITE_FAILED, "instructions_write_failed", str(exc))
        return {"saved": True, "path": str(path), "chars": len(body)}


__all__ = [
    "InstructionsHandlers",
    "ERR_BAD_INPUT",
    "ERR_TOO_LARGE",
    "ERR_WRITE_FAILED",
]
