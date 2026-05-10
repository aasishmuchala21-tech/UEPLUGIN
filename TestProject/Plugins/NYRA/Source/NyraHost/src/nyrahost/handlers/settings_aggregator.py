"""settings/all WS handler — Phase 18-D.

Tier 3 polish. The UE Settings tab needs ~7 different pieces of
state (model pin, Custom Instructions, operating mode, backend mode,
privacy guard, log level, user-tool inventory, marketplace targets).
Today each lives behind its own WS round-trip; opening the panel
hits 7 endpoints in serial. This aggregator returns all of it in
one call so the panel renders without flicker.

The handler holds NO new state — it composes the existing handlers
+ stores from earlier phases. Mirroring what each phase exposed:

  * settings/get-model         (Phase 10-3)
  * settings/get-instructions  (Phase 11-A)
  * session/set-mode + privacy (Phase 10-2 + 15-E)
  * settings/repro/get         (Phase 14-A)
  * user_tools/list            (Phase 14-D)
  * mcp_install/list_targets   (Phase 12-A)
"""
from __future__ import annotations

from typing import Final, Optional

import structlog

from nyrahost.handlers.composer import ComposerHandlers  # noqa: F401 (sibling)
from nyrahost.handlers.instructions import InstructionsHandlers
from nyrahost.handlers.mcp_install import McpInstallHandlers
from nyrahost.handlers.model_settings import ModelSettingsHandlers
from nyrahost.handlers.reproducibility import ReproHandlers
from nyrahost.handlers.session_mode import SessionModeHandler
from nyrahost.handlers.user_tools import UserToolsHandlers
from nyrahost.privacy_guard import GUARD as PRIVACY_GUARD

log = structlog.get_logger("nyrahost.handlers.settings_aggregator")

ERR_BAD_INPUT: Final[int] = -32602


def _err(code: int, message: str, detail: str = "") -> dict:
    out: dict = {"error": {"code": code, "message": message}}
    if detail:
        out["error"]["data"] = {"detail": detail}
    return out


class SettingsAggregatorHandlers:
    """``settings/all`` — single-round-trip Settings tab seed."""

    def __init__(
        self,
        *,
        instructions: InstructionsHandlers,
        model: ModelSettingsHandlers,
        repro: ReproHandlers,
        session_mode: SessionModeHandler,
        user_tools: UserToolsHandlers,
        mcp_install: McpInstallHandlers,
    ) -> None:
        self._instr = instructions
        self._model = model
        self._repro = repro
        self._mode = session_mode
        self._tools = user_tools
        self._mcp = mcp_install

    async def on_all(self, params: dict, session=None, ws=None) -> dict:
        conv = params.get("conversation_id")
        if not isinstance(conv, str) or not conv:
            return _err(ERR_BAD_INPUT, "missing_field", "conversation_id")

        instr = await self._instr.on_get({}, session, ws)
        model = await self._model.on_get({"conversation_id": conv}, session, ws)
        repro = await self._repro.on_get({"conversation_id": conv}, session, ws)
        targets = await self._mcp.on_list_targets({}, session, ws)
        tools = await self._tools.on_list({}, session, ws)

        privacy_stats = PRIVACY_GUARD.stats()

        return {
            "instructions": instr,
            "model": model,
            "repro": repro,
            "operating_mode": self._mode.operating_mode,
            "privacy": {
                "mode": "privacy" if privacy_stats["privacy_mode"] else "normal",
                "refusal_count": privacy_stats["refusal_count"],
            },
            "user_tools": tools,
            "mcp_install_targets": targets,
            "version": "phase-18",
        }


__all__ = ["SettingsAggregatorHandlers", "ERR_BAD_INPUT"]
