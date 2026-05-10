"""SessionModeHandler — Phase 2 session/set-mode + Phase 10-2 ask/plan/agent.

Wires into NyraRouter for Privacy Mode AND into NyraPermissionGate for the
three operating modes (Aura parity):

  * **ask**   — read-only. Tools that mutate (asset edits, file writes,
                console exec) are gated to refuse with -32011 plan_rejected.
                The user can still run knowledge / search tools freely.
  * **plan**  — produces a Plan preview but does NOT auto-execute. User
                must click Approve before any mutation runs (current default;
                CHAT-04 hardcoded).
  * **agent** — auto-executes pre-approved plans. Per-step preview is
                still emitted for inspection but the gate's Future is
                pre-resolved-approved. Safe-mode itself stays ON (the
                un-disable-able invariant).

Privacy Mode is orthogonal — set independently via mode="privacy".
Registered in app.py alongside the router construction.
"""
from __future__ import annotations

from typing import Final

import structlog

from nyrahost.router import NyraRouter
from nyrahost.safe_mode import NyraPermissionGate

log = structlog.get_logger("nyrahost.handlers.session_mode")

# Aura-parity operating modes (ask/plan/agent).
AURA_MODES: Final[frozenset[str]] = frozenset({"ask", "plan", "agent"})
# Privacy / backend modes from Phase 2 — kept for backward compat.
BACKEND_MODES: Final[frozenset[str]] = frozenset({"normal", "privacy", "claude", "gemma"})


class SessionModeHandler:
    """
    Handles session/set-mode WS request from UE panel.

    Two orthogonal axes:
      * Operating mode (ask/plan/agent) — drives NyraPermissionGate behaviour
      * Backend mode (normal/privacy/claude/gemma) — drives NyraRouter

    Both can flow through the same WS method with the {"mode": ...} param;
    the handler dispatches based on which set the value falls into. Apps
    that want to set both in one round-trip can use {"operating_mode": X,
    "backend_mode": Y} explicitly.
    """

    def __init__(
        self, router: NyraRouter, permission_gate: NyraPermissionGate | None = None,
    ) -> None:
        self._router = router
        self._gate = permission_gate
        # Aura modes default to "plan" (matches CHAT-04 plan-first default).
        self._operating_mode: str = "plan"

    @property
    def operating_mode(self) -> str:
        return self._operating_mode

    async def on_set_mode(self, params: dict, session=None, ws=None) -> dict:
        """Handle session/set-mode request.

        Accepts either a single ``mode`` value (auto-dispatched) or
        explicit ``operating_mode`` / ``backend_mode`` keys.
        """
        applied: dict = {}

        # Explicit two-axis set
        if "operating_mode" in params or "backend_mode" in params:
            op = params.get("operating_mode")
            be = params.get("backend_mode")
            if op is not None:
                applied["operating_mode"] = await self._set_operating(op)
            if be is not None:
                applied["backend_mode"] = await self._set_backend(be)
            return {"mode_applied": True, **applied}

        # Single-arg backward-compatible path
        mode = params.get("mode", "")
        if mode in AURA_MODES:
            applied["operating_mode"] = await self._set_operating(mode)
        elif mode in BACKEND_MODES:
            applied["backend_mode"] = await self._set_backend(mode)
        else:
            raise ValueError(
                f"invalid mode {mode!r}; expected one of "
                f"{sorted(AURA_MODES)} or {sorted(BACKEND_MODES)}"
            )
        return {"mode_applied": True, **applied}

    async def _set_operating(self, mode: str) -> str:
        if mode not in AURA_MODES:
            raise ValueError(f"invalid operating_mode {mode!r}")
        self._operating_mode = mode
        if self._gate is not None and hasattr(self._gate, "set_operating_mode"):
            self._gate.set_operating_mode(mode)
        log.info("operating_mode_set", mode=mode)
        return mode

    async def _set_backend(self, mode: str) -> str:
        if mode in ("privacy", "gemma"):
            await self._router.enter_privacy_mode()
            log.info("session_mode_privacy_entered")
            return "privacy"
        if mode in ("normal", "claude"):
            await self._router.exit_privacy_mode()
            log.info("session_mode_normal")
            return "normal"
        raise ValueError(f"invalid backend_mode {mode!r}")


__all__ = ["SessionModeHandler", "AURA_MODES", "BACKEND_MODES"]
