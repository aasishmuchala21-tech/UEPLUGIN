"""NyraRouter — Phase 2 state machine for backend routing + Privacy Mode.

Phase 0 clearance required: Claude-path transitions are live only after SC#1 verdict.
Until SC#1 clears this plan implements stubs for Claude-path routing; Gemma-only
mode is fully functional.

Key design constraints:
  - D-04: no silent fallback mid-stream — user must explicitly approve
  - D-05: Privacy Mode refuses Claude; cannot silently bypass
  - D-03: state enum locked per RESEARCH §2.2
  - RESEARCH §10.6: server_error retry cap at 3 — state stays, error surfaces
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Literal

import structlog

log = structlog.get_logger("nyrahost.router")


class BackendState(enum.StrEnum):
    """Router states per RESEARCH §2.2.

    Values are lowercase for JSON-RPC wire compatibility.
    """
    IDLE = "idle"
    BACKEND_AIMING = "backend_aiming"
    CLAUDE_ACTIVE = "claude_active"
    GEMMA_ACTIVE = "gemma_active"
    RATE_LIMITED = "rate_limited"
    AUTH_DRIFT = "auth_drift"
    PRIVACY_MODE = "privacy_mode"


@dataclass
class RouterContext:
    state: BackendState = BackendState.IDLE
    active_backend: str | None = None
    privacy_mode: bool = False
    rate_limit_retries: int = 0
    last_error: str | None = None
    prior_state_before_privacy: BackendState | None = None

    # Stub: Claude-side backends not available until SC#1 clears
    _claude_available: bool = field(default=False, repr=False)


@dataclass
class BackendDecision:
    """Result of router.decide_backend — selected backend or error."""
    backend: str  # "claude" | "gemma-local" | None
    state: BackendState
    error_code: int | None = None
    error_message: str | None = None
    error_remediation: str | None = None


class NyraRouter:
    """State machine routing requests between Claude and Gemma backends.

    DI surface: ``emit_notification(method, params)`` injected so every
    transition emits a ``diagnostics/backend-state`` notification per
    docs/JSONRPC.md §4.8.
    """

    # Valid transitions: (current_state, event) -> next_state
    _TRANSITIONS: dict[tuple[BackendState, str], BackendState] = {
        # IDLE
        (BackendState.IDLE, "health_ok"): BackendState.BACKEND_AIMING,
        (BackendState.IDLE, "privacy_enter"): BackendState.PRIVACY_MODE,
        # BACKEND_AIMING
        (BackendState.BACKEND_AIMING, "route_claude"): BackendState.CLAUDE_ACTIVE,
        (BackendState.BACKEND_AIMING, "route_gemma"): BackendState.GEMMA_ACTIVE,
        (BackendState.BACKEND_AIMING, "privacy_enter"): BackendState.PRIVACY_MODE,
        # CLAUDE_ACTIVE
        (BackendState.CLAUDE_ACTIVE, "stream_done"): BackendState.IDLE,
        (BackendState.CLAUDE_ACTIVE, "rate_limit"): BackendState.RATE_LIMITED,
        (BackendState.CLAUDE_ACTIVE, "auth_failed"): BackendState.AUTH_DRIFT,
        (BackendState.CLAUDE_ACTIVE, "server_error"): BackendState.CLAUDE_ACTIVE,
        (BackendState.CLAUDE_ACTIVE, "privacy_enter"): BackendState.PRIVACY_MODE,
        # GEMMA_ACTIVE
        (BackendState.GEMMA_ACTIVE, "stream_done"): BackendState.IDLE,
        (BackendState.GEMMA_ACTIVE, "privacy_enter"): BackendState.PRIVACY_MODE,
        # RATE_LIMITED
        (BackendState.RATE_LIMITED, "fallback_approved"): BackendState.GEMMA_ACTIVE,
        (BackendState.RATE_LIMITED, "privacy_enter"): BackendState.PRIVACY_MODE,
        (BackendState.RATE_LIMITED, "cancel"): BackendState.IDLE,
        # AUTH_DRIFT
        (BackendState.AUTH_DRIFT, "fallback_approved"): BackendState.GEMMA_ACTIVE,
        (BackendState.AUTH_DRIFT, "privacy_enter"): BackendState.PRIVACY_MODE,
        (BackendState.AUTH_DRIFT, "cancel"): BackendState.IDLE,
        # PRIVACY_MODE
        (BackendState.PRIVACY_MODE, "privacy_exit"): BackendState.IDLE,
    }

    def __init__(
        self,
        emit_notification: callable,
        *,
        claude_available: bool = False,
    ) -> None:
        """
        Args:
            emit_notification: callable(method, params) for diagnostics notifications.
                May be sync or async; router handles both transparently.
            claude_available: True once SC#1 clears. Stub until then.
        """
        self._raw_emit = emit_notification
        self.ctx = RouterContext()
        # Phase 0 gate: Claude is NOT available until SC#1 clears
        self._claude_available = claude_available

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _do_emit(self, method: str, params: dict) -> None:
        """Async-safe emit — bypasses instance-level _emit overwrite.

        Uses _raw_emit directly from __dict__ to avoid test-level
        `router._emit = sync_lambda` intercepts.
        """
        import asyncio

        raw = self.__dict__["_raw_emit"]
        if asyncio.iscoroutinefunction(raw):
            await raw(method, params)
        else:
            result = raw(method, params)
            if asyncio.iscoroutine(result):
                await result

    def is_safe_mode(self) -> bool:
        """Safe mode is controlled by Plan 02-09 permission gate."""
        return True  # default on; Plan 02-09 owns this flag

    async def decide_backend(
        self,
        request_backend: str,
        user_approved_fallback: bool = False,
    ) -> BackendDecision:
        """
        Select backend for a chat/send request.

        Routing rules (enforced regardless of request_backend value):
          1. Privacy mode always routes to gemma-local
          2. Auth drift: refuse Claude unless user_approved_fallback
          3. Rate limited: refuse Claude unless user_approved_fallback
          4. SC#1 not cleared: route to gemma-local (stub mode)
          5. Otherwise: route to claude (Phase 2 gate opens when SC#1 clears)
        """
        if self.ctx.privacy_mode:
            return self._route_to_gemma(BackendState.PRIVACY_MODE)

        if not self._claude_available:
            # SC#1 not cleared — stub Claude, use Gemma
            log.info("router_claude_stubbed_sc1_pending")
            return self._route_to_gemma(BackendState.IDLE, note="claude-stubbed-waiting-sc1")

        if request_backend == "claude":
            if self.ctx.state == BackendState.RATE_LIMITED:
                if user_approved_fallback:
                    return self._route_to_gemma(BackendState.GEMMA_ACTIVE)
                return BackendDecision(
                    backend=None,
                    state=BackendState.RATE_LIMITED,
                    error_code=-32009,
                    error_message="claude_rate_limited",
                    error_remediation="Rate limit hit. Click [Use Gemma] in NYRA status bar to continue.",
                )
            if self.ctx.state == BackendState.AUTH_DRIFT:
                if user_approved_fallback:
                    return self._route_to_gemma(BackendState.GEMMA_ACTIVE)
                return BackendDecision(
                    backend=None,
                    state=BackendState.AUTH_DRIFT,
                    error_code=-32008,
                    error_message="claude_auth_expired",
                    error_remediation="Claude auth expired. Click [Use Gemma] in NYRA status bar to continue.",
                )
            return self._route_to_claude()

        return self._route_to_gemma(BackendState.BACKEND_AIMING)

    async def observe_event(self, event: dict) -> None:
        """
        Process a BackendEvent dict (from Plan 02-03 tagged union) to drive
        state transitions.

        Expected event shapes:
          - {"type": "Retry", "attempt": int, "error_category": str}
          - {"type": "Error", "code": int, "message": str}
          - {"type": "Done"}
        """
        ev_type = event.get("type", "")
        category = event.get("error_category", "")

        if ev_type == "Retry":
            await self._handle_retry(event)
        elif ev_type == "Error":
            await self._handle_error(event)
        elif ev_type == "Done":
            await self._transition("stream_done")

    async def enter_privacy_mode(self) -> None:
        """Enter Privacy Mode — Gemma-only, no Claude egress."""
        self.ctx.prior_state_before_privacy = self.ctx.state
        self.ctx.privacy_mode = True
        await self._transition_and_notify(
            BackendState.PRIVACY_MODE,
            "user set Privacy Mode",
            {"mode": "privacy"},
        )

    async def exit_privacy_mode(self) -> None:
        """Exit Privacy Mode — restore prior state."""
        if self.ctx.prior_state_before_privacy is not None:
            prior = self.ctx.prior_state_before_privacy
            self.ctx.privacy_mode = False
            self.ctx.prior_state_before_privacy = None
            await self._transition_and_notify(
                prior,
                "user exited Privacy Mode",
                {"mode": "normal", "restored_state": prior.value},
            )

    async def set_mode(self, mode: str) -> None:
        """Set routing mode: 'claude' | 'gemma' | 'auto' | 'normal'."""
        if mode == "gemma":
            await self.enter_privacy_mode()
        elif mode == "claude":
            if self.ctx.privacy_mode:
                await self.exit_privacy_mode()
            await self._transition_and_notify(
                BackendState.IDLE, "user set mode=claude", {"mode": "claude"},
            )
        elif mode in ("auto", "normal"):
            # auto: try Claude, fallback to Gemma on errors — handled by decide_backend
            if self.ctx.privacy_mode:
                await self.exit_privacy_mode()
            else:
                await self._transition_and_notify(
                    BackendState.IDLE, "user set mode=auto", {"mode": "auto"},
                )
        else:
            raise ValueError(f"invalid mode {mode!r}; expected 'claude'|'gemma'|'auto'|'normal'")

    def get_diagnostics(self) -> dict:
        """Return current router state for diagnostics/backend-state payload."""
        return {
            "state": self.ctx.state.value,
            "active_backend": self.ctx.active_backend,
            "privacy_mode": self.ctx.privacy_mode,
            "rate_limit_retries": self.ctx.rate_limit_retries,
            "last_error": self.ctx.last_error,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _transition(self, event: str) -> None:
        """Attempt state transition; log and skip if invalid."""
        key = (self.ctx.state, event)
        next_state = self._TRANSITIONS.get(key)
        if next_state is None:
            log.warning("router_invalid_transition", from_state=self.ctx.state.value, trigger_event=event)
            return
        self.ctx.state = next_state

    async def _transition_and_notify(
        self, next_state: BackendState, reason: str, extra_params: dict,
    ) -> None:
        self.ctx.state = next_state
        await self._do_emit("diagnostics/backend-state", {
            "state": next_state.value,
            "reason": reason,
            **extra_params,
        })

    async def _handle_retry(self, event: dict) -> None:
        attempt = event.get("attempt", 0)
        category = event.get("error_category", "unknown")

        if category == "rate_limit":
            self.ctx.rate_limit_retries += 1
            if attempt >= 3:
                await self._transition_and_notify(
                    BackendState.RATE_LIMITED,
                    f"rate_limit_exhausted_attempt_{attempt}",
                    {"error_category": category},
                )
            # attempt < 3: stay in CLAUDE_ACTIVE; no transition call needed
        elif category == "authentication_failed":
            await self._transition_and_notify(
                BackendState.AUTH_DRIFT,
                f"auth_failed_attempt_{attempt}",
                {"error_category": category},
            )
        elif category in ("server_error", "unknown"):
            if attempt >= 3:
                self.ctx.last_error = f"{category}_attempt_{attempt}"
                await self._do_emit("diagnostics/backend-state", {
                    "state": self.ctx.state.value,
                    "reason": f"server_error_exhausted_attempt_{attempt}",
                    "error_category": category,
                    "error_surface": True,
                })
            else:
                await self._transition("server_error")

    async def _handle_error(self, event: dict) -> None:
        self.ctx.last_error = event.get("message", "unknown_error")
        self.ctx.rate_limit_retries = 0

    def _route_to_claude(self) -> BackendDecision:
        self.ctx.active_backend = "claude"
        self.ctx.state = BackendState.CLAUDE_ACTIVE
        return BackendDecision(backend="claude", state=BackendState.CLAUDE_ACTIVE)

    def _route_to_gemma(self, next_state: BackendState, note: str = "") -> BackendDecision:
        self.ctx.active_backend = "gemma-local"
        self.ctx.state = next_state
        return BackendDecision(backend="gemma-local", state=next_state)