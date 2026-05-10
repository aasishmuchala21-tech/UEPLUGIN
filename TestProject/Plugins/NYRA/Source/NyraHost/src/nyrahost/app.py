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
import pathlib
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
# Phase 10 — Custom Instructions, three-mode toggle, model selector wiring.
from .custom_instructions import CustomInstructions
from .handlers.instructions import InstructionsHandlers
from .handlers.model_settings import ModelSettingsHandlers
from .handlers.composer import ComposerHandlers
from .handlers.mcp_install import McpInstallHandlers
from .tools.headless_ue import HeadlessUEManager
# Phase 13 — Multi-thread chats, Timeline, Asset Hygiene, Audit log, Perf Budget.
from .handlers.threads import ThreadHandlers, ThreadRegistry
from .tools.timeline_tools import on_add_timeline
from .tools.asset_hygiene import on_run_hygiene
from .tools.perf_budget import PerfBudgetHandlers
# Phase 14 — repro pin, cost forecast, agent trace, user tools, crash RCA,
# test gen, doc-from-code, replication scaffolder.
from .reproducibility import ReproPinStore
from .handlers.reproducibility import ReproHandlers
from .handlers.cost import CostHandlers
from .handlers.agent_trace import AgentTraceHandlers
from .user_tools import UserToolsLoader
from .handlers.user_tools import UserToolsHandlers
from .tools.crash_rca import CrashRCAHandlers
from .tools.test_gen import TestGenHandlers
from .tools.doc_from_code import DocFromCodeHandlers
from .tools.replication_scaffolder import ReplicationScaffolderHandlers
# Phase 15 — encrypted memory, localization, cinematic, health, privacy guard,
# blueprint static review.
from .encrypted_memory import EncryptedMemory
from .handlers.encrypted_memory import EncryptedMemoryHandlers
from .tools.localization import LocalizationHandlers
from .tools.cinematic import on_cinematic
from .health import HealthDashboard
from .handlers.health import HealthHandlers
from .privacy_guard import GUARD as PRIVACY_GUARD
from .tools.blueprint_review import on_review_graph
# Phase 16 — finish Tier 1.B (PCG scatter, validation, spiral stairs + arches,
# BP review LLM half, ControlNet inpaint, engine source RAG ingest).
from .tools.pcg_scatter import on_pcg_scatter
from .tools.blockout_validation import validate_blockout
from .tools.blueprint_review_llm import on_compose_review
from .audit import AuditLog
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

    # Phase 10-1 / 11-B — per-project Custom Instructions, constructed BEFORE
    # ChatHandlers so the chat path can prepend them to the system prompt.
    custom_instructions = CustomInstructions(project_dir=project_dir)
    instructions_handlers = InstructionsHandlers(custom_instructions)

    handlers = ChatHandlers(
        storage=storage,
        router=router,
        project_saved=project_dir / "Saved",
        custom_instructions=custom_instructions,
    )
    # Phase 11-C — @-search composer asset lookup.
    composer_handlers = ComposerHandlers()

    # Phase 12-A — one-click IDE MCP installer. python_exe + mcp_script
    # paths are best-effort; the panel UI will surface them so the user
    # can override before clicking Install.
    import sys as _sys
    _python_exe = pathlib.Path(_sys.executable) if False else __import__("pathlib").Path(_sys.executable)
    mcp_install_handlers = McpInstallHandlers(
        python_exe=_python_exe,
        mcp_script=plugin_binaries_dir.parent.parent / "Source" / "NyraHost" / "src" / "nyrahost" / "mcp_server" / "__init__.py",
    )

    # Phase 12-B — headless UE launch (one session per NyraHost process).
    headless_ue_mgr = HeadlessUEManager()

    # Phase 13-A — multi-thread chat thread registry (Aura parity, N=4).
    thread_handlers = ThreadHandlers(ThreadRegistry())

    # Phase 13-D — append-only audit log per project (Tier 2 privacy moat).
    audit_log = AuditLog(project_dir=project_dir)

    # Phase 13-E — perf budget handlers (per-project budgets file).
    perf_budget_handlers = PerfBudgetHandlers(project_dir=project_dir)

    # Phase 14-A — per-conversation seed + temperature pin (Tier 2).
    repro_handlers = ReproHandlers(ReproPinStore())

    # Phase 14-B — cost forecaster (read-only, no state).
    cost_handlers = CostHandlers()

    # Phase 14-C — agent trace view over audit_log.
    agent_trace_handlers = AgentTraceHandlers(audit_log=audit_log)

    # Phase 14-D — user-installable MCP tools loader. UserTools/ lives
    # next to the plugin's Source/ tree at install time.
    user_tools_dir = plugin_binaries_dir.parent.parent / "UserTools"
    user_tools_handlers = UserToolsHandlers(UserToolsLoader(tools_dir=user_tools_dir))

    # Phase 14-E — crash RCA over <ProjectDir>/Saved/Crashes/.
    crash_rca_handlers = CrashRCAHandlers(project_dir=project_dir)

    # Phase 14-F — test scaffolding over plugin source tree.
    plugin_source_dir = plugin_binaries_dir.parent.parent / "Source"
    test_gen_handlers = TestGenHandlers(plugin_source_dir=plugin_source_dir)

    # Phase 14-G — doc-from-code over plugin source tree.
    doc_handlers = DocFromCodeHandlers(plugin_source_dir=plugin_source_dir)

    # Phase 14-H — replication scaffolder (pure-function output).
    repl_handlers = ReplicationScaffolderHandlers()

    # Phase 15-A — encrypted per-project memory.
    encrypted_memory = EncryptedMemory(project_dir=project_dir)
    encrypted_memory_handlers = EncryptedMemoryHandlers(encrypted_memory)

    # Phase 15-B — LOCTEXT extractor.
    localization_handlers = LocalizationHandlers(plugin_source_dir=plugin_source_dir)

    # Phase 15-D — live project health dashboard backend.
    health_dashboard = HealthDashboard(
        project_dir=project_dir,
        audit_log=audit_log,
        thread_registry=thread_handlers.registry,
    )
    health_handlers = HealthHandlers(health_dashboard)

    # Phase 15-E — privacy-guard singleton (PRIVACY_GUARD is process-wide;
    # imported here so its existence is part of the build-up-and-go log
    # surface).
    _ = PRIVACY_GUARD

    # Phase 10-3 — model selector handlers (reuse the existing chat-handler ModelPreference).
    model_settings_handlers = ModelSettingsHandlers(
        model_preference=getattr(handlers, "model_preference", None) or __import__(
            "nyrahost.model_preference", fromlist=["ModelPreference"]
        ).ModelPreference()
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
    session_mode_handler = SessionModeHandler(router=nyra_router, permission_gate=permission_gate)
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
        # Phase 10-1 — Custom Instructions.
        server.register_request("settings/get-instructions", instructions_handlers.on_get)
        server.register_request("settings/set-instructions", instructions_handlers.on_set)
        # Phase 10-3 — Model selector.
        server.register_request("settings/get-model", model_settings_handlers.on_get)
        server.register_request("settings/set-model", model_settings_handlers.on_set)
        # Phase 11-C — @-search composer asset lookup.
        server.register_request("composer/asset_search", composer_handlers.on_asset_search)
        # Phase 12-A — IDE MCP installer.
        server.register_request("mcp_install/list_targets", mcp_install_handlers.on_list_targets)
        server.register_request("mcp_install/install", mcp_install_handlers.on_install)
        server.register_request("mcp_install/uninstall", mcp_install_handlers.on_uninstall)
        # Phase 12-B — headless UE launch (Aura-parity IDE/MCP surface).
        server.register_request("headless_ue/launch", headless_ue_mgr.launch)
        server.register_request("headless_ue/status", headless_ue_mgr.status)
        server.register_request("headless_ue/shutdown", headless_ue_mgr.shutdown)
        # Phase 13-A — multi-thread parallel chats.
        server.register_request("chat/threads/list", thread_handlers.on_list)
        server.register_request("chat/threads/create", thread_handlers.on_create)
        server.register_request("chat/threads/close", thread_handlers.on_close)
        server.register_request("chat/threads/touch", thread_handlers.on_touch)
        # Phase 13-B — Timeline node authoring.
        server.register_request("timeline/add", on_add_timeline)
        # Phase 13-C — whole-project Asset Hygiene Agent (Tier 2 moat).
        server.register_request("hygiene/run", on_run_hygiene)
        # Phase 13-E — Performance Budget Agent.
        server.register_request("perf_budget/render_script", perf_budget_handlers.on_render_script)
        server.register_request("perf_budget/get", perf_budget_handlers.on_get_budgets)
        server.register_request("perf_budget/set", perf_budget_handlers.on_set_budget)
        server.register_request("perf_budget/check", perf_budget_handlers.on_check)
        # Phase 14-A — reproducibility pin.
        server.register_request("settings/repro/get", repro_handlers.on_get)
        server.register_request("settings/repro/set", repro_handlers.on_set)
        server.register_request("settings/repro/clear", repro_handlers.on_clear)
        # Phase 14-B — cost forecaster.
        server.register_request("cost/forecast", cost_handlers.on_forecast)
        server.register_request("cost/price_table", cost_handlers.on_price_table)
        # Phase 14-C — agent trace.
        server.register_request("trace/get", agent_trace_handlers.on_get)
        # Phase 14-D — user MCP tools.
        server.register_request("user_tools/list", user_tools_handlers.on_list)
        server.register_request("user_tools/reload", user_tools_handlers.on_reload)
        server.register_request("user_tools/invoke", user_tools_handlers.on_invoke)
        # Phase 14-E — crash RCA.
        server.register_request("crash_rca/run", crash_rca_handlers.on_run)
        # Phase 14-F — test scaffolding.
        server.register_request("test_gen/scan", test_gen_handlers.on_scan)
        server.register_request("test_gen/render", test_gen_handlers.on_render_spec)
        # Phase 14-G — doc-from-code.
        server.register_request("docs/scan_module", doc_handlers.on_scan_module)
        # Phase 14-H — replication scaffolder.
        server.register_request("replication/scaffold", repl_handlers.on_scaffold)
        # Phase 15-A — encrypted memory.
        server.register_request("memory/get", encrypted_memory_handlers.on_get)
        server.register_request("memory/set", encrypted_memory_handlers.on_set)
        server.register_request("memory/delete", encrypted_memory_handlers.on_delete)
        server.register_request("memory/dump", encrypted_memory_handlers.on_dump)
        # Phase 15-B — localization.
        server.register_request("localization/scan", localization_handlers.on_scan)
        server.register_request("localization/emit", localization_handlers.on_emit)
        # Phase 15-C — Cinematic / DOP Agent.
        server.register_request("cinematic/create", on_cinematic)
        # Phase 15-D — live project health.
        server.register_request("health/snapshot", health_handlers.on_snapshot)
        # Phase 15-F — Blueprint static review.
        server.register_request("blueprint_review/run", on_review_graph)
        # Phase 16 — Tier 1.B finish line.
        server.register_request("level_design/pcg_scatter", on_pcg_scatter)
        server.register_request("blueprint_review/compose", on_compose_review)
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
