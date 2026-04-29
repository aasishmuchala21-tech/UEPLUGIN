"""Tests for the AgentBackend ABC + BACKEND_REGISTRY contract.

RED phase: these tests fail because nyrahost.backends does not exist yet.
"""
from __future__ import annotations

import pytest


class TestAgentBackendContract:
    """Contract tests for the AgentBackend abstract base class."""

    def test_abc_rejects_direct_instantiation(self):
        """AgentBackend cannot be instantiated directly — it is abstract."""
        from nyrahost.backends import AgentBackend
        with pytest.raises(TypeError, match="abstract"):
            AgentBackend()

    def test_dummy_subclass_satisfies_isinstance(self):
        """A minimal subclass implementing all three abstracts satisfies isinstance."""
        from nyrahost.backends import AgentBackend, BackendEvent

        class DummyBackend(AgentBackend):
            name = "dummy"

            async def send(
                self, conversation_id, req_id, content, attachments, mcp_config_path, on_event,
            ):
                yield  # pragma: no cover

            async def cancel(self, req_id):
                pass  # pragma: no cover

            async def health_check(self):
                from nyrahost.backends.base import HealthState
                return HealthState.READY

        from nyrahost.backends.base import Delta, Done, Error, HealthState

        # ABC enforcement
        assert isinstance(DummyBackend(), AgentBackend)
        # HealthState is a str Enum
        assert HealthState.READY == "ready"

    def test_backend_event_tagged_union_isinstance(self):
        """Given Delta/Done/Error/Retry instances, isinstance checks route correctly."""
        from nyrahost.backends.base import Delta, Done, Error, Retry, BackendEvent

        delta = Delta(text="hello")
        done = Done(usage={"input_tokens": 1, "output_tokens": 2}, stop_reason="end_turn")
        error = Error(code=-32001, message="subprocess_failed", remediation="Restart.", retryable=False)
        retry = Retry(attempt=1, delay_ms=500, error_category="rate_limit")

        assert isinstance(delta, Delta)
        assert isinstance(delta, BackendEvent)
        assert isinstance(done, Done)
        assert isinstance(done, BackendEvent)
        assert isinstance(error, Error)
        assert isinstance(error, BackendEvent)
        assert isinstance(retry, Retry)
        assert isinstance(retry, BackendEvent)


class TestBackendRegistry:
    """Tests for BACKEND_REGISTRY and get_backend factory."""

    def test_registry_has_gemma_local(self):
        """BACKEND_REGISTRY['gemma-local'] is GemmaBackend."""
        from nyrahost.backends import BACKEND_REGISTRY, GemmaBackend

        assert "gemma-local" in BACKEND_REGISTRY
        assert BACKEND_REGISTRY["gemma-local"] is GemmaBackend

    def test_get_backend_unknown_raises(self):
        """get_backend('totally-made-up') raises ValueError listing registered names."""
        from nyrahost.backends import get_backend

        with pytest.raises(ValueError, match="totally-made-up") as exc_info:
            get_backend("totally-made-up")
        # Should list the registered backend names
        assert "gemma-local" in str(exc_info.value)

    def test_get_backend_gemma_local_returns_gemma_backend(self):
        """get_backend('gemma-local') returns GemmaBackend class (not instance)."""
        from nyrahost.backends import get_backend, GemmaBackend

        cls = get_backend("gemma-local")
        assert cls is GemmaBackend
