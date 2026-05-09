"""Tests for GemmaBackend adapter wrapping Phase 1 InferRouter.

RED phase: these tests fail because GemmaBackend does not exist yet.
"""
from __future__ import annotations

import pytest

from nyrahost.backends.base import Delta, Done, Error, HealthState


class StubSseEvent:
    """Minimal stub matching the SSE delta shape from Phase 1 InferRouter."""

    def __init__(self, delta: str = "", done: bool = False, usage: dict | None = None):
        self.delta = delta
        self.done = done
        self.usage = usage or {}


class StubInferRouter:
    """Minimal InferRouter stub for testing GemmaBackend adapter."""

    def __init__(self, installed: bool = True, stream_events=None):
        self._installed = installed
        self._stream_events = stream_events or []
        self._cancel_called: list[str] = []

    async def gemma_not_installed(self) -> bool:
        return not self._installed

    async def stream_chat(self, content: str, cancel_event=None):
        for ev in self._stream_events:
            yield ev

    async def cancel(self, req_id: str) -> None:
        self._cancel_called.append(req_id)


class TestGemmaBackendHealthCheck:
    """Health check tests for GemmaBackend."""

    @pytest.mark.asyncio
    async def test_health_check_returns_ready_when_installed(self):
        """With gemma_not_installed() returning False, health_check() returns READY."""
        from nyrahost.backends import GemmaBackend

        router = StubInferRouter(installed=True)
        backend = GemmaBackend(infer_router=router)
        state = await backend.health_check()
        assert state == HealthState.READY

    @pytest.mark.asyncio
    async def test_health_check_returns_not_installed(self):
        """With gemma_not_installed() returning True, health_check() returns NOT_INSTALLED."""
        from nyrahost.backends import GemmaBackend

        router = StubInferRouter(installed=False)
        backend = GemmaBackend(infer_router=router)
        state = await backend.health_check()
        assert state == HealthState.NOT_INSTALLED


class TestGemmaBackendSend:
    """send() tests for GemmaBackend adapter."""

    @pytest.mark.asyncio
    async def test_send_emits_delta_then_done(self):
        """With SSE events ['hello', ' world', done frame], send emits Delta+Delta+Done."""
        from nyrahost.backends import GemmaBackend

        events = [
            StubSseEvent(delta="hello"),
            StubSseEvent(delta=" world"),
            StubSseEvent(done=True, usage={"input_tokens": 1, "output_tokens": 2}),
        ]
        router = StubInferRouter(stream_events=events)
        backend = GemmaBackend(infer_router=router)

        received: list = []

        async def collector(event):
            received.append(event)

        await backend.send(
            conversation_id="conv-1",
            req_id="req-1",
            content="hello world",
            attachments=[],
            mcp_config_path=None,
            on_event=collector,
        )

        assert len(received) == 3
        assert isinstance(received[0], Delta)
        assert received[0].text == "hello"
        assert isinstance(received[1], Delta)
        assert received[1].text == " world"
        assert isinstance(received[2], Done)
        assert received[2].usage["output_tokens"] == 2

    @pytest.mark.asyncio
    async def test_send_emits_error_on_exception(self):
        """If stream_chat raises, send emits Error via on_event."""
        from nyrahost.backends import GemmaBackend

        class FailingRouter:
            async def gemma_not_installed(self):
                return False

            async def stream_chat(self, content, cancel_event=None):
                yield  # must be an async generator so `async for` body runs
                raise RuntimeError("llama-server crashed")

        backend = GemmaBackend(infer_router=FailingRouter())
        received: list = []

        async def collector(event):
            received.append(event)

        await backend.send(
            conversation_id="conv-1",
            req_id="req-1",
            content="hello",
            attachments=[],
            mcp_config_path=None,
            on_event=collector,
        )

        assert len(received) == 1
        assert isinstance(received[0], Error)
        assert received[0].code == -32001


class TestGemmaBackendCancel:
    """cancel() tests for GemmaBackend."""

    @pytest.mark.asyncio
    async def test_cancel_routes_to_infer_router(self):
        """GemmaBackend.cancel(req_id) forwards to router.cancel(req_id)."""
        from nyrahost.backends import GemmaBackend

        router = StubInferRouter(installed=True)
        backend = GemmaBackend(infer_router=router)
        await backend.cancel("req-abc")
        assert "req-abc" in router._cancel_called


class TestGemmaBackendAttributes:
    """Name and capability attribute tests."""

    def test_backend_name_is_gemma_local(self):
        """GemmaBackend.name class attribute is 'gemma-local'."""
        from nyrahost.backends import GemmaBackend

        assert GemmaBackend.name == "gemma-local"
