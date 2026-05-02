"""chat/send request handler + chat/cancel notification handler.

Wires the Gemma chat surface through NyraServer's extension points
(Plan 06 :meth:`NyraServer.register_request` /
:meth:`register_notification`). Streams tokens back to UE via
``build_notification("chat/stream", ...)`` on the session's socket.

See docs/JSONRPC.md §3.3 (chat/send), §3.4 (chat/stream), §3.5 (chat/cancel)
and docs/ERROR_CODES.md for the -32001 / -32005 remediation strings.

Attachment ingestion (CD-04 + Plan 07): if ``params.attachments`` is a
non-empty list of absolute file-path strings, each path is fed through
:func:`nyrahost.attachments.ingest_attachment` BEFORE streaming
begins; the returned :class:`AttachmentRef` is bound to the persisted
user-message row via :meth:`Storage.link_attachment`.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog
from websockets.server import ServerConnection

from ..attachments import ingest_attachment
from ..backends import BACKEND_REGISTRY, AgentBackend, get_backend
from ..infer.router import InferRouter
from ..jsonrpc import build_notification
from ..session import SessionState
from ..storage import Storage

log = structlog.get_logger("nyrahost.chat")


class GemmaNotInstalledError(Exception):
    """Raised from on_chat_send when Gemma GGUF missing AND Ollama unavailable.

    Surfaced to UE by app.py's wrapper as error code -32005
    (gemma_not_installed) per docs/ERROR_CODES.md. Plan 09's downloader
    resolves this path.
    """


@dataclass
class ChatHandlers:
    """Per-NyraHost-process chat surface.

    One instance is constructed in :func:`app.build_and_run` and
    registered on the singleton :class:`NyraServer`. ``_inflight``
    maps req_id -> asyncio.Event so chat/cancel can signal the
    matching stream task.

    Phase 2 (Plan 02-03): dispatches ``params.backend`` through
    ``BACKEND_REGISTRY``. ``gemma-local`` preserves Phase 1 behaviour;
    other backends raise ``NotImplementedError`` until their adapter
    lands (e.g. ``"claude"`` → Plan 02-04).
    """

    storage: Storage
    router: InferRouter
    project_saved: Path  # <ProjectDir>/Saved — needed for ingest_attachment (CD-04)
    _inflight: dict[str, asyncio.Event] = field(default_factory=dict)

    async def on_chat_send(
        self, params: dict, session: SessionState, ws: ServerConnection
    ) -> dict:
        conv_id = params["conversation_id"]
        req_id = params["req_id"]
        content = params["content"]
        backend = params.get("backend", "gemma-local")

        # Phase 2 (Plan 02-03): dispatch through BACKEND_REGISTRY.
        # gemma-local preserves Phase 1 behaviour (InferRouter path below).
        # claude → ClaudeBackend (Plan 02-05); byok → BYOKBackend (Plan 02-05).
        # Unknown backend → KeyError → ValueError caught and surfaced as -32601.
        if backend != "gemma-local":
            try:
                backend_cls = get_backend(backend)
            except ValueError as exc:
                return {
                    "req_id": req_id,
                    "streaming": False,
                    "error": {
                        "code": -32601,
                        "message": "backend_not_supported",
                        "data": {
                            "remediation": (
                                f"Backend {backend!r} not yet implemented. "
                                "Use 'gemma-local' for now."
                            ),
                        },
                    },
                }
            # Instantiate and stream via the chosen backend (Plan 02-05).
            raise NotImplementedError(
                f"Backend {backend!r} — Plan 02-05 TODO: wire BackendEvent → WS"
            )

        # Check Gemma installed (unless Ollama has it)
        if await self.router.gemma_not_installed():
            raise GemmaNotInstalledError()

        # Persist user message (auto-create conversation if first time seen)
        now_ms = int(time.time() * 1000)
        if self.storage.get_conversation(conv_id) is None:
            # Caller passed a fresh conv_id — create with default title
            # (first 48 chars of the user message per the Plan 08 plan)
            self.storage.conn.execute(
                "INSERT INTO conversations(id,title,created_at,updated_at) "
                "VALUES(?,?,?,?)",
                (conv_id, content[:48], now_ms, now_ms),
            )
            self.storage.conn.commit()

        user_msg = self.storage.append_message(
            conversation_id=conv_id, role="user", content=content,
        )

        # Attachment ingestion (CD-04). params.attachments is an optional
        # list of absolute file path strings forwarded from UE. For each
        # path, ingest_attachment hashes + hardlinks into
        # <project_saved>/NYRA/attachments/<sha[:2]>/ and returns an
        # AttachmentRef; link_attachment binds that AttachmentRef to the
        # just-persisted user-message row. Ingestion happens BEFORE
        # streaming begins so the DB is consistent if the stream errors.
        raw_attachments = params.get("attachments") or []
        if isinstance(raw_attachments, list) and raw_attachments:
            for pth in raw_attachments:
                if not isinstance(pth, str) or not pth:
                    continue
                try:
                    ref = ingest_attachment(
                        Path(pth), project_saved=self.project_saved,
                    )
                    self.storage.link_attachment(
                        message_id=user_msg.id,
                        kind=ref.kind,
                        path=ref.path,
                        size_bytes=ref.size_bytes,
                        sha256=ref.sha256,
                    )
                except Exception as _e:  # noqa: BLE001
                    log.warning(
                        "attachment_ingest_failed", path=pth, err=str(_e),
                    )

        cancel = asyncio.Event()
        self._inflight[req_id] = cancel

        # Kick off the stream task — fire-and-forget; tokens stream via
        # WS notifications (chat/stream).
        asyncio.create_task(
            self._run_stream(
                ws=ws,
                conv_id=conv_id,
                req_id=req_id,
                content=content,
                cancel=cancel,
            )
        )
        return {"req_id": req_id, "streaming": True}

    async def _run_stream(
        self,
        *,
        ws: ServerConnection,
        conv_id: str,
        req_id: str,
        content: str,
        cancel: asyncio.Event,
    ) -> None:
        accumulated: list[str] = []
        final_usage: dict | None = None
        error_payload: dict | None = None
        try:
            async for ev in self.router.stream_chat(
                content=content, cancel_event=cancel,
            ):
                if cancel.is_set():
                    break
                if ev.delta:
                    accumulated.append(ev.delta)
                    await ws.send(
                        build_notification(
                            "chat/stream",
                            {
                                "conversation_id": conv_id,
                                "req_id": req_id,
                                "delta": ev.delta,
                                "done": False,
                            },
                        )
                    )
                if ev.done:
                    final_usage = ev.usage
                    break
        except Exception as e:  # noqa: BLE001
            log.exception("chat_stream_exception", req_id=req_id)
            error_payload = {
                "code": -32001,
                "message": "subprocess_failed",
                "data": {
                    "remediation": (
                        "A background NYRA process stopped unexpectedly. "
                        "Click [Restart] or see Saved/NYRA/logs/."
                    ),
                },
            }
        finally:
            self._inflight.pop(req_id, None)

        # Final frame — always emit done:true, even on cancel/error
        final_params: dict[str, Any] = {
            "conversation_id": conv_id,
            "req_id": req_id,
            "delta": "",
            "done": True,
        }
        if cancel.is_set():
            final_params["cancelled"] = True
        if final_usage is not None:
            final_params["usage"] = final_usage
        if error_payload is not None:
            final_params["error"] = error_payload

        try:
            await ws.send(build_notification("chat/stream", final_params))
        except Exception:  # noqa: BLE001 — socket closed mid-stream; ignore
            pass

        # Persist assistant reply (even if cancelled/error — record what we have)
        if accumulated:
            self.storage.append_message(
                conversation_id=conv_id,
                role="assistant",
                content="".join(accumulated),
                usage_json=json.dumps(final_usage) if final_usage else None,
                error_json=json.dumps(error_payload) if error_payload else None,
            )

    async def on_chat_cancel(
        self, params: dict, session: SessionState
    ) -> None:
        req_id = params.get("req_id")
        if not isinstance(req_id, str):
            return
        ev = self._inflight.get(req_id)
        if ev is not None:
            ev.set()
