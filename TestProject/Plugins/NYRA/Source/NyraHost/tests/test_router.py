"""Tests for NyraRouter — Phase 2 state machine (Plan 02-06).

RED phase: tests define the expected behaviour before implementation.
All tests should FAIL on the stub implementation and PASS once the full
router is wired.
"""
from __future__ import annotations

import pytest

from nyrahost.router import BackendState, BackendDecision, NyraRouter


class TestRouterInitialState:
    """Initial state and safe-mode defaults."""

    def test_initial_state_is_idle(self):
        """Router starts in IDLE state with no active backend."""
        router = _make_router()
        assert router.ctx.state == BackendState.IDLE
        assert router.ctx.active_backend is None

    def test_initial_privacy_mode_false(self):
        router = _make_router()
        assert router.ctx.privacy_mode is False

    def test_safe_mode_on_by_default(self):
        """Safe mode (Plan 02-09) is ON by default."""
        router = _make_router()
        assert router.is_safe_mode() is True

    def test_initial_claude_available_false(self):
        """Until SC#1 clears, Claude is not available."""
        router = _make_router(claude_available=False)
        assert router._claude_available is False


class TestRouterDecideBackend:
    """decide_backend routing logic."""

    async def test_decide_backend_gemma_when_claude_stubbed(self):
        """When SC#1 not cleared (claude_available=False), route to Gemma."""
        router = _make_router(claude_available=False)
        decision = await router.decide_backend("claude")
        assert decision.backend == "gemma-local"
        assert decision.state == BackendState.IDLE

    async def test_decide_backend_privacy_mode_always_gemma(self):
        """Privacy mode refuses Claude regardless of SC#1 status."""
        router = _make_router(claude_available=True)
        await router.enter_privacy_mode()
        decision = await router.decide_backend("claude")
        assert decision.backend == "gemma-local"
        assert decision.state == BackendState.PRIVACY_MODE

    async def test_decide_backend_rate_limited_refuses_without_fallback(self):
        """Claude rate-limited and no user-approved fallback → error."""
        router = _make_router(claude_available=True)
        await router.observe_event(
            {"type": "Retry", "attempt": 3, "error_category": "rate_limit"}
        )
        decision = await router.decide_backend("claude", user_approved_fallback=False)
        assert decision.backend is None
        assert decision.error_code == -32009

    async def test_decide_backend_rate_limited_with_approved_fallback_routes_gemma(self):
        """Rate-limited + user-approved fallback → Gemma."""
        router = _make_router(claude_available=True)
        await router.observe_event(
            {"type": "Retry", "attempt": 3, "error_category": "rate_limit"}
        )
        decision = await router.decide_backend(
            "claude", user_approved_fallback=True
        )
        assert decision.backend == "gemma-local"
        assert decision.state == BackendState.GEMMA_ACTIVE

    async def test_decide_backend_auth_drift_refuses_without_fallback(self):
        """Auth drift without fallback → error."""
        router = _make_router(claude_available=True)
        await router.observe_event(
            {"type": "Retry", "attempt": 1, "error_category": "authentication_failed"}
        )
        decision = await router.decide_backend("claude", user_approved_fallback=False)
        assert decision.backend is None
        assert decision.error_code == -32008

    async def test_decide_backend_gemma_explicit(self):
        """Explicit gemma request routes directly."""
        router = _make_router(claude_available=False)
        decision = await router.decide_backend("gemma")
        assert decision.backend == "gemma-local"


class TestRouterTransitions:
    """State machine transition table."""

    async def test_transition_idle_to_aiming_on_route(self):
        router = _make_router()
        await router.decide_backend("claude")
        assert router.ctx.state == BackendState.IDLE  # No actual route since claude unavailable

    async def test_transition_to_claude_active_when_available(self):
        router = _make_router(claude_available=True)
        decision = await router.decide_backend("claude")
        assert decision.state == BackendState.CLAUDE_ACTIVE

    async def test_transition_stream_done_returns_to_idle(self):
        router = _make_router(claude_available=True)
        await router.decide_backend("claude")
        await router.observe_event({"type": "Done"})
        assert router.ctx.state == BackendState.IDLE

    async def test_invalid_transition_logged_but_not_raised(self):
        """Unknown transition is a no-op, not an exception."""
        router = _make_router()
        # IDLE has no "unknown_event" transition — should be silently ignored
        await router._transition("unknown_event")
        assert router.ctx.state == BackendState.IDLE


class TestPrivacyMode:
    """Privacy Mode toggle (session/set-mode)."""

    async def test_enter_privacy_mode_stores_prior_state(self):
        router = _make_router(claude_available=True)
        await router.decide_backend("claude")
        prior = router.ctx.state
        await router.enter_privacy_mode()
        assert router.ctx.prior_state_before_privacy == prior
        assert router.ctx.privacy_mode is True
        assert router.ctx.state == BackendState.PRIVACY_MODE

    async def test_exit_privacy_mode_restores_prior(self):
        router = _make_router(claude_available=True)
        await router.decide_backend("claude")
        await router.enter_privacy_mode()
        await router.exit_privacy_mode()
        assert router.ctx.privacy_mode is False
        assert router.ctx.prior_state_before_privacy is None

    async def test_set_mode_gemma_enters_privacy(self):
        router = _make_router(claude_available=True)
        await router.set_mode("gemma")
        assert router.ctx.privacy_mode is True
        assert router.ctx.state == BackendState.PRIVACY_MODE

    async def test_set_mode_normal_exits_privacy(self):
        router = _make_router(claude_available=True)
        await router.set_mode("gemma")
        await router.set_mode("normal")
        assert router.ctx.privacy_mode is False

    async def test_set_mode_invalid_raises(self):
        router = _make_router()
        with pytest.raises(ValueError, match="invalid mode"):
            await router.set_mode("lol")


class TestRetryHandling:
    """RESEARCH §10.6: server_error retry cap at 3."""

    async def test_retry_rate_limit_exhausted_at_3_transitions(self):
        router = _make_router(claude_available=True)
        await router.decide_backend("claude")
        for attempt in range(1, 4):
            await router.observe_event(
                {"type": "Retry", "attempt": attempt, "error_category": "rate_limit"}
            )
        assert router.ctx.state == BackendState.RATE_LIMITED

    async def test_retry_rate_limit_not_exhausted_stays(self):
        router = _make_router(claude_available=True)
        await router.decide_backend("claude")
        await router.observe_event(
            {"type": "Retry", "attempt": 1, "error_category": "rate_limit"}
        )
        # attempt 1 < 3, state stays CLAUDE_ACTIVE
        assert router.ctx.state == BackendState.CLAUDE_ACTIVE

    async def test_retry_auth_failed_first_event_transitions(self):
        router = _make_router(claude_available=True)
        await router.decide_backend("claude")
        await router.observe_event(
            {"type": "Retry", "attempt": 1, "error_category": "authentication_failed"}
        )
        assert router.ctx.state == BackendState.AUTH_DRIFT

    async def test_retry_server_error_attempt_1_stays(self):
        router = _make_router(claude_available=True)
        await router.decide_backend("claude")
        await router.observe_event(
            {"type": "Retry", "attempt": 1, "error_category": "server_error"}
        )
        assert router.ctx.state == BackendState.CLAUDE_ACTIVE

    async def test_retry_server_error_attempt_3_stays_but_emits(self):
        """RESEARCH §10.6: attempt >= 3 surfaces error but state stays."""
        emit_log = []

        async def capture_emit(method: str, params: dict) -> None:
            emit_log.append((method, params))

        router = _make_router(claude_available=True, emit=capture_emit)
        await router.decide_backend("claude")

        for attempt in range(1, 4):
            await router.observe_event(
                {"type": "Retry", "attempt": attempt, "error_category": "server_error"}
            )
        # State stays CLAUDE_ACTIVE (no fallback silently)
        assert router.ctx.state == BackendState.CLAUDE_ACTIVE
        # But error was surfaced
        assert any("error_surface" in p for _m, p in emit_log)


class TestDiagnostics:
    """diagnostics/backend-state notification emission."""

    async def test_every_transition_emits_diagnostics_backend_state(self):
        emit_log = []
        router = _make_router(
            claude_available=True,
            emit=lambda m, p: emit_log.append((m, p)),
        )
        await router.enter_privacy_mode()
        assert any(m == "diagnostics/backend-state" for m, _ in emit_log)

    async def test_get_diagnostics_returns_state_dict(self):
        router = _make_router(claude_available=True)
        diag = router.get_diagnostics()
        assert "state" in diag
        assert "active_backend" in diag
        assert "privacy_mode" in diag
        assert "rate_limit_retries" in diag


class TestBackendDecision:
    """BackendDecision dataclass correctness."""

    def test_decision_has_all_fields(self):
        d = BackendDecision(backend="claude", state=BackendState.CLAUDE_ACTIVE)
        assert d.backend == "claude"
        assert d.state == BackendState.CLAUDE_ACTIVE
        assert d.error_code is None

    def test_decision_error_includes_all_fields(self):
        d = BackendDecision(
            backend=None,
            state=BackendState.RATE_LIMITED,
            error_code=-32009,
            error_message="claude_rate_limited",
            error_remediation="Use Gemma.",
        )
        assert d.backend is None
        assert d.error_code == -32009


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_router(
    claude_available: bool = False,
    emit: callable | None = None,
) -> NyraRouter:
    async def noop_emit(method: str, params: dict) -> None:
        pass

    async def async_emit_adapter(method: str, params: dict) -> None:
        # Wrap sync emit (e.g. test lambda) so router's `await self._emit(...)` works
        import asyncio
        if asyncio.iscoroutinefunction(emit):
            await emit(method, params)
        else:
            emit(method, params)

    return NyraRouter(
        emit_notification=async_emit_adapter if emit is not None else noop_emit,
        claude_available=claude_available,
    )