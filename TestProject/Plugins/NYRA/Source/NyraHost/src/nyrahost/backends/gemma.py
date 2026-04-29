"""GemmaBackend — Phase 1 InferRouter adapter for the AgentBackend ABC (Plan 02-03).

Wraps the Phase 1 InferRouter (Plan 08) behind the AgentBackend interface.
Zero behaviour change — every Phase 1 pytest still passes after this refactor.

The adapter:
- Maps InferRouter.stream_chat SSE deltas → BackendEvent.Delta / Done
- Maps InferRouter exceptions → BackendEvent.Error
- health_check() delegates to InferRouter.gemma_not_installed()
- cancel() delegates to InferRouter.cancel(req_id)
"""
from __future__ import annotations

from pathlib import Path

import structlog

from nyrahost.attachments import AttachmentRef
from nyrahost.backends.base import (
    AgentBackend,
    BackendEvent,
    Delta,
    Done,
    Error,
    HealthState,
)
from nyrahost.infer.router import InferRouter

log = structlog.get_logger("nyrahost.backends.gemma")


class GemmaBackend(AgentBackend):
    """Phase 1 Gemma/InferRouter adapter — drop-in for AgentBackend ABC.

    ``infer_router`` is injected at construction (not resolved internally)
    so tests can inject StubInferRouter without mocking subprocesses.
    """

    name = "gemma-local"

    def __init__(self, infer_router: InferRouter) -> None:
        self._infer_router = infer_router

    # ------------------------------------------------------------------
    # AgentBackend contract
    # ------------------------------------------------------------------

    async def send(
        self,
        conversation_id: str,
        req_id: str,
        content: str,
        attachments: list[AttachmentRef],
        mcp_config_path: Path | None,
        on_event: callable,
    ) -> None:
        """Stream Gemma text through the adapter as BackendEvent deltas.

        ``on_event`` is a coroutine accepting a single BackendEvent.
        The stream ALWAYS ends with a Done or Error event.
        """
        try:
            async for sse_ev in self._infer_router.stream_chat(
                content=content,
            ):
                if sse_ev.delta:
                    await on_event(Delta(text=sse_ev.delta))
                if sse_ev.done:
                    await on_event(
                        Done(
                            usage=sse_ev.usage or {},
                            stop_reason="end_turn",
                        )
                    )
        except Exception as e:  # noqa: BLE001
            log.exception("gemma_send_exception", req_id=req_id)
            await on_event(
                Error(
                    code=-32001,
                    message="subprocess_failed",
                    remediation="A background NYRA process stopped unexpectedly. Click [Restart] or see Saved/NYRA/logs/.",
                    retryable=False,
                )
            )

    async def cancel(self, req_id: str) -> None:
        """Forward cancel to the injected InferRouter."""
        if hasattr(self._infer_router, "cancel"):
            await self._infer_router.cancel(req_id)

    async def health_check(self) -> HealthState:
        """Return NOT_INSTALLED if GGUF absent and Ollama unavailable, else READY."""
        installed = not await self._infer_router.gemma_not_installed()
        return HealthState.READY if installed else HealthState.NOT_INSTALLED
