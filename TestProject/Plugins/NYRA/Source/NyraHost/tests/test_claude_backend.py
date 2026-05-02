"""Tests for claude.py — ClaudeBackend subprocess adapter (Plan 02-05).

Uses pytest-subprocess for mocking subprocess spawn without privilege escalation.
RED phase: tests fail because BACKEND_REGISTRY update + chat.py wiring not done.
GREEN phase: once claude.py + __init__.py + chat.py changes land, all pass.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Mark entire module as subprocess-spawning (skip in quick CI mode)
pytestmark = pytest.mark.integration


class TestClaudeBackendClass:
    """Smoke tests for ClaudeBackend public API surface."""

    @pytest.fixture
    def backend(self):
        from nyrahost.backends.claude import ClaudeBackend

        return ClaudeBackend(
            claude_path=Path("claude"),
            python_exe=Path(sys.executable),
        )

    def test_name_is_claude(self, backend):
        assert backend.name == "claude"

    @pytest.mark.asyncio
    async def test_send_scrubs_api_key_envs(self, backend, tmp_path: Path):
        """Spawned subprocess env does NOT contain ANTHROPIC_API_KEY/ANTHROPIC_AUTH_TOKEN."""
        from nyrahost.backends.base import Delta

        mcp_out = tmp_path / "mcp.json"
        mcp_out.write_text(json.dumps({"mcpServers": {"nyra": {"command": sys.executable, "args": [], "env": {}}}}))

        captured_env: dict = {}

        async def capture_env(*args, env=None, **kwargs):
            nonlocal captured_env
            captured_env = dict(env or {})
            # Return a fake completed process with NDJSON result
            class FakeProc:
                returncode = 0
                async def wait(self): return 0
                async def __aenter__(self): return self
                async def __aexit__(self, *a): pass
                @property
                def stdout(self):
                    # Yield one NDJSON line then close
                    class FakeStream:
                        async def __aiter__(self):
                            yield json.dumps({"type": "result", "stop_reason": "end_turn", "usage": {}}).encode()
                        async def __anext__(self): raise StopAsyncIteration
                    return FakeStream()
            return FakeProc()

        events: list = []

        async def on_event(ev):
            events.append(ev)

        with patch("asyncio.create_subprocess_exec", capture_env):
            await backend.send(
                conversation_id="conv-1",
                req_id="req-1",
                content="hello",
                attachments=[],
                mcp_config_path=None,
                on_event=on_event,
            )

        assert "ANTHROPIC_API_KEY" not in captured_env
        assert "ANTHROPIC_AUTH_TOKEN" not in captured_env

    @pytest.mark.asyncio
    async def test_send_builds_correct_argv_no_bare(self, backend, tmp_path: Path):
        """argv contains --mcp-config, --strict-mcp-config, --permission-mode dontAsk, --permission-prompt-tool; --bare is ABSENT."""
        captured_argv: list = []

        async def capture_argv(*args, env=None, **kwargs):
            nonlocal captured_argv
            captured_argv = list(args)
            class FakeProc:
                returncode = 0
                async def wait(self): return 0
                async def __aenter__(self): return self
                async def __aexit__(self, *a): pass
                @property
                def stdout(self):
                    class FakeStream:
                        async def __aiter__(self):
                            yield json.dumps({"type": "result", "stop_reason": "end_turn", "usage": {}}).encode()
                        async def __anext__(self): raise StopAsyncIteration
                    return FakeStream()
            return FakeProc()

        with patch("asyncio.create_subprocess_exec", capture_argv):
            await backend.send(
                conversation_id="conv-1",
                req_id="req-1",
                content="hello world",
                attachments=[],
                mcp_config_path=None,
                on_event=AsyncMock(),
            )

        assert "--mcp-config" in captured_argv
        assert "--strict-mcp-config" in captured_argv
        assert "--permission-mode" in captured_argv
        assert "dontAsk" in captured_argv
        assert "--permission-prompt-tool" in captured_argv
        assert "--bare" not in captured_argv

    @pytest.mark.asyncio
    async def test_cancel_sends_terminate(self, backend):
        """cancel(req_id) calls proc.terminate() on the tracked subprocess."""
        proc = AsyncMock()
        proc.returncode = None
        backend._inflight["req-99"] = proc

        await backend.cancel("req-99")
        proc.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_idempotent(self, backend):
        """cancel on unknown req_id does not raise."""
        await backend.cancel("req-unknown")
        # Should not raise

    @pytest.mark.asyncio
    async def test_health_check_not_installed(self, backend):
        """FileNotFoundError on spawn → NOT_INSTALLED."""
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
            state = await backend.health_check()
        from nyrahost.backends.base import HealthState
        assert state == HealthState.NOT_INSTALLED


class TestBackendRegistry:
    """Registry wiring — verifies claude + byok backends are registered."""

    def test_registry_has_claude(self):
        from nyrahost.backends import BACKEND_REGISTRY
        from nyrahost.backends.claude import ClaudeBackend

        assert "claude" in BACKEND_REGISTRY
        assert BACKEND_REGISTRY["claude"] is ClaudeBackend

    def test_registry_has_byok(self):
        from nyrahost.backends import BACKEND_REGISTRY
        from nyrahost.backends.byok import BYOKBackend

        assert "byok" in BACKEND_REGISTRY
        assert BACKEND_REGISTRY["byok"] is BYOKBackend

    def test_get_backend_claude(self):
        from nyrahost.backends import get_backend
        from nyrahost.backends.claude import ClaudeBackend

        assert get_backend("claude") is ClaudeBackend

    def test_get_backend_unknown_raises(self):
        from nyrahost.backends import get_backend

        with pytest.raises(ValueError, match="Unknown backend"):
            get_backend("unknown-backend")


class TestBYOKBackend:
    """BYOKBackend smoke tests — no subprocess needed."""

    @pytest.fixture
    def byok(self):
        from nyrahost.backends.byok import BYOKBackend

        return BYOKBackend(api_key=None)  # unconfigured state

    def test_name_is_byok(self, byok):
        assert byok.name == "byok"

    @pytest.mark.asyncio
    async def test_not_configured_emits_error(self, byok):
        from nyrahost.backends.base import Error

        events: list = []
        await byok.send("conv", "req", "hello", [], None, events.append)
        assert len(events) == 1
        assert isinstance(events[0], Error)
        assert "not_configured" in events[0].message

    @pytest.mark.asyncio
    async def test_health_check_not_configured(self, byok):
        from nyrahost.backends.base import HealthState

        state = await byok.health_check()
        assert state == HealthState.NOT_INSTALLED
