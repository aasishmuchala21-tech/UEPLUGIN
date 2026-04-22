"""Application composition root for NyraHost.

Plan 08 owns this module; downstream plans (09 Gemma downloader, 10
sessions handlers, 12 chat panel integration) extend ``build_and_run``
additively — register new handlers on the :class:`NyraServer` without
touching the auth gate or the chat/send wiring.

``build_and_run`` instantiates the full dependency graph:

    Storage  ──┐
    InferRouter ┼─> ChatHandlers ─> NyraServer (chat/send + chat/cancel)
    project_dir ┘

and invokes :func:`nyrahost.server.run_server` which binds the WS
listener, writes the handshake file (D-06), and serves forever.
"""
from __future__ import annotations

from pathlib import Path

import structlog

from .config import NyraConfig
from .handlers.chat import ChatHandlers, GemmaNotInstalledError
from .infer.router import InferRouter
from .server import NyraServer, run_server
from .session import SessionState
from .storage import Storage, db_path_for_project

log = structlog.get_logger("nyrahost.app")


def gemma_gguf_path(project_dir: Path) -> Path:
    """Canonical Gemma GGUF path per D-17.

    Plan 09's downloader writes here; the router reads from here. A
    single function keeps both in lockstep.
    """
    return (
        project_dir
        / "Saved"
        / "NYRA"
        / "models"
        / "gemma-3-4b-it-qat-q4_0.gguf"
    )


class _GemmaNotInstalledRpcError(Exception):
    """Sentinel caught by NyraServer._dispatch -> -32005 gemma_not_installed."""


def _wrap_send(handlers: ChatHandlers):
    """Adapt ChatHandlers.on_chat_send to NyraServer's request handler shape.

    NyraServer (Plan 06) expects ``(params, session) -> dict`` handlers;
    chat/send additionally needs the WebSocket connection so it can emit
    chat/stream notifications. server.py attaches the active ``ws`` to
    ``session._ws`` inside ``_handle_connection``; this wrapper pulls it
    back out before delegating to :meth:`ChatHandlers.on_chat_send`.
    """
    async def handle(params: dict, session: SessionState) -> dict:
        ws = getattr(session, "_ws", None)
        if ws is None:
            return {
                "req_id": params.get("req_id", ""),
                "streaming": False,
                "error": {
                    "code": -32001,
                    "message": "internal",
                    "data": {
                        "remediation": "Internal: no WS bound to session.",
                    },
                },
            }
        try:
            return await handlers.on_chat_send(params, session, ws)
        except GemmaNotInstalledError:
            # Surface to NyraServer's dispatch catch-all which will emit
            # -32001 subprocess_failed. Plan 09's downloader intercepts
            # at a higher layer; for Plan 08 we keep the error code in
            # the chat.py ERROR_CODES.md envelope and let server.py's
            # generic catch map to -32001 with remediation.
            # When Plan 09 lands, _wrap_send upgrades to emit -32005
            # directly via build_error.
            raise _GemmaNotInstalledRpcError(
                "Gemma model missing. Click Download in Settings."
            )

    return handle


async def build_and_run(
    *,
    config: NyraConfig,
    nyrahost_pid: int,
    project_dir: Path,
    plugin_binaries_dir: Path,
) -> None:
    """Compose Storage + InferRouter + chat handlers into NyraServer, run forever."""
    storage = Storage(db_path_for_project(project_dir))
    router = InferRouter(
        plugin_binaries_dir=plugin_binaries_dir,
        gguf_path_getter=lambda: gemma_gguf_path(project_dir),
    )
    await router.start()

    handlers = ChatHandlers(
        storage=storage,
        router=router,
        project_saved=project_dir / "Saved",
    )

    def register(server: NyraServer) -> None:
        # chat/send uses the per-session websocket attached via session._ws
        # in server._handle_connection.
        server.register_request("chat/send", _wrap_send(handlers))
        server.register_notification("chat/cancel", handlers.on_chat_cancel)

    await run_server(
        config, nyrahost_pid=nyrahost_pid, register_handlers=register,
    )
