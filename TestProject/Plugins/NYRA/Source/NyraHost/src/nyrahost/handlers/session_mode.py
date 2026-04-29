"""SessionModeHandler — Phase 2 session/set-mode request handler (Plan 02-06).

Wires into NyraRouter to enter/exit Privacy Mode.
Registered in app.py alongside the router construction.
"""
from __future__ import annotations

import structlog

from nyrahost.router import NyraRouter

log = structlog.get_logger("nyrahost.handlers.session_mode")


class SessionModeHandler:
    """
    Handles session/set-mode WS request from UE panel.

    Calls router.enter_privacy_mode() / router.exit_privacy_mode()
    and emits diagnostics/backend-state notification.
    """

    def __init__(self, router: NyraRouter) -> None:
        self._router = router

    async def on_set_mode(self, params: dict) -> dict:
        """
        Handle session/set-mode request.

        Args:
            params: {"mode": "normal" | "privacy" | "claude" | "gemma"}

        Returns:
            {"mode_applied": True}

        Raises:
            ValueError: if mode is not a recognised string.
        """
        mode = params.get("mode", "")
        if mode in ("privacy", "gemma"):
            await self._router.enter_privacy_mode()
            log.info("session_mode_privacy_entered")
        elif mode in ("normal", "claude"):
            await self._router.exit_privacy_mode()
            log.info("session_mode_normal")
        else:
            raise ValueError(f"invalid mode {mode!r}; expected 'normal'|'privacy'|'claude'|'gemma'")

        return {"mode_applied": True, "mode": mode}


__all__ = ["SessionModeHandler"]