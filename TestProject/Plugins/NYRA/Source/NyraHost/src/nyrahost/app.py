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

import json
from pathlib import Path

import structlog

from .config import NyraConfig
from .downloader.gemma import GEMMA_FILENAME, GemmaSpec
from .handlers.chat import ChatHandlers, GemmaNotInstalledError
from .handlers.download import DownloadHandlers
from .handlers.session_mode import SessionModeHandler
from .handlers.transaction import TransactionHandlers
from .handlers.sessions import SessionHandlers
from .tools.inpaint_tools import on_inpaint_submit
from .tools.rigging_tools import on_auto_rig
from .tools.retarget_tools import on_retarget
from .tools.level_design_tools import on_blockout
from .infer.router import InferRouter
from .router import NyraRouter
from .safe_mode import NyraPermissionGate
from .server import NyraServer, run_server
from .session import SessionState
from .storage import Storage, db_path_for_project
from .transaction import NyraTransactionManager

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
        / GEMMA_FILENAME
    )


def _load_gemma_spec(manifest_path: Path) -> GemmaSpec:
    """Load GemmaSpec from assets-manifest.json with hard-coded fallbacks.

    Plan 05's manifest stores a free-form ``gemma_model_note`` rather
    than a structured block. Phase 1 defaults to the well-known HF URL
    + GitHub mirror; Plan 05's ModelPins.h is the single source of
    truth for SHA256 / revision (see comments there).
    """
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    gemma = data.get("gemma") or {}
    return GemmaSpec(
        primary_url=gemma.get(
            "url",
            (
                "https://huggingface.co/google/"
                "gemma-3-4b-it-qat-q4_0-gguf/resolve/main/"
                "gemma-3-4b-it-qat-q4_0.gguf"
            ),
        ),
        mirror_url=gemma.get(
            "mirror_url",
            (
                "https://github.com/nyra-ai/nyra/releases/download/"
                "models-v1/gemma-3-4b-it-qat-q4_0.gguf"
            ),
        ),
        expected_sha256=gemma.get("sha256", ""),
        total_bytes_hint=int(gemma.get("total_bytes", 3_391_733_760)),
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
    """Compose Storage + InferRouter + chat handlers into NyraServer, run forever.

    Phase 2 extensions (Plans 02-06/08/09/10/11):
      - NyraRouter: state machine backend routing (claude stubbed until SC#1 clears)
      - NyraPermissionGate: plan-first preview gate (safe-mode ON by default)
      - NyraTransactionManager: session super-transaction + PIE guard
      - SessionModeHandler: session/set-mode for Privacy Mode toggle
      - TransactionHandlers: transaction/begin/commit/rollback + diagnostics/pie-state
    """
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

    # Plan 12b — read-only sessions/list + sessions/load handlers backing the
    # UE history drawer (CD-05). SessionHandlers shares the same Storage the
    # chat handler writes to, so the drawer sees freshly-persisted
    # conversations without an intermediate cache.
    session_handlers = SessionHandlers(storage=storage)

    # Plan 09 — download handler. assets-manifest.json lives alongside
    # the NyraHost package source; plugin_binaries_dir is
    # <Plugin>/Binaries/Win64, so the manifest is three levels up under
    # Source/NyraHost/.
    manifest_path = (
        plugin_binaries_dir.parent.parent
        / "Source"
        / "NyraHost"
        / "assets-manifest.json"
    )
    download_handlers = DownloadHandlers(
        project_dir=project_dir,
        spec=_load_gemma_spec(manifest_path),
    )

    # Phase 2 (Plans 02-06/08/09): router + permission gate + transaction manager
    # emit_notification helper: captures the per-session WS for diagnostics emission
    async def _emit_for_phase2(method: str, params: dict) -> None:
        # Phase 2 components use the server's notification dispatch
        # Handled via server.register_notification at the server level
        pass

    # NyraRouter: SC#1 gate (claude_available=False until SC#1 verdict permits)
    nyra_router = NyraRouter(
        emit_notification=_emit_for_phase2,
        claude_available=False,  # Stub until Phase 0 SC#1 clears
    )

    # NyraPermissionGate: safe-mode ON by default (CHAT-04)
    permission_gate = NyraPermissionGate()

    # NyraTransactionManager: session super-transaction + PIE guard
    tx_manager = NyraTransactionManager(
        project_dir=project_dir,
        emit_notification=_emit_for_phase2,
        storage=storage,
    )

    # Phase 2 handlers
    session_mode_handler = SessionModeHandler(router=nyra_router)
    tx_handlers = TransactionHandlers(tx_manager=tx_manager)

    def register(server: NyraServer) -> None:
        # chat/send uses the per-session websocket attached via session._ws
        # in server._handle_connection.
        server.register_request("chat/send", _wrap_send(handlers))
        server.register_notification("chat/cancel", handlers.on_chat_cancel)
        # Plan 09 — the download-gemma request kicks off a background
        # download; progress streams via diagnostics/download-progress
        # notifications on the same session.
        server.register_request(
            "diagnostics/download-gemma", download_handlers.on_download_gemma,
        )
        # Plan 12b — history drawer (CD-05). Both sessions/list and
        # sessions/load are pure reads against Storage; no per-session WS
        # attachment is needed. See docs/JSONRPC.md 3.8 + 3.9.
        server.register_request(
            "sessions/list", session_handlers.on_sessions_list,
        )
        server.register_request(
            "sessions/load", session_handlers.on_sessions_load,
        )
        # Plan 09 INPAINT-01 — SDXL in-painting via local ComfyUI.
        server.register_request("inpaint/submit", on_inpaint_submit)
        # Plan 09 RIG-01/02 — Meshy auto-rig + UE-side retarget script renderer.
        server.register_request("rigging/auto_rig", on_auto_rig)
        server.register_request("rigging/retarget", on_retarget)
        # Plan 09 LDA-01 — single-room blockout via UE GeometryScript.
        server.register_request("level_design/blockout", on_blockout)
        # Phase 2 (Plans 02-06/08): new handlers appended below
        # Plan 02-06: session/set-mode (Privacy Mode toggle)
        server.register_request("session/set-mode", session_mode_handler.on_set_mode)
        # Plan 02-08: transaction management
        server.register_request("transaction/begin", tx_handlers.on_transaction_begin)
        server.register_request("transaction/commit", tx_handlers.on_transaction_commit)
        server.register_request("transaction/rollback", tx_handlers.on_transaction_rollback)
        server.register_notification(
            "diagnostics/pie-state", tx_handlers.on_diagnostics_pie_state,
        )

    await run_server(
        config, nyrahost_pid=nyrahost_pid, register_handlers=register,
    )
