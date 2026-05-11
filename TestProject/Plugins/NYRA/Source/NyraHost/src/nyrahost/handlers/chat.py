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

from ..attachments import AttachmentRef, ingest_attachment
from ..backends import BACKEND_REGISTRY, AgentBackend, get_backend
from ..infer.router import InferRouter
from ..jsonrpc import build_notification
from ..session import SessionState
from ..storage import Storage

log = structlog.get_logger("nyrahost.chat")


def _extract_and_link_document(
    *,
    ref: AttachmentRef,
    pth: str,
    project_saved: Path,
    storage: "Storage",
    user_msg_id: str,
) -> list[AttachmentRef]:
    """PARITY-01 — extract text + embedded images from a document AttachmentRef.

    Persists the extracted text as a sibling ``text`` AttachmentRef next
    to the original document in the content-addressed store, then links
    both the text and every embedded image into the user message via
    ``storage.link_attachment``. Returns the list of newly-emitted
    refs (text + images) so the claude-route path can append them to
    the backend's attachment payload.

    Failures are non-fatal: ``extract_*`` raises ``ValueError`` on
    malformed input, and the chat handler logs the warning and moves
    on rather than killing the whole submission. Aura crashes on
    malformed docs; we don't.
    """
    from nyrahost.extractors import dispatch as _doc_dispatch

    new_refs: list[AttachmentRef] = []
    try:
        text, image_refs = _doc_dispatch(
            Path(pth), project_saved=project_saved
        )
    except Exception as exc:
        log.warning("doc_extract_failed", path=pth, err=str(exc))
        return new_refs

    # Persist extracted text as a sibling .txt next to the doc in the
    # content-addressed shard. Path naming uses the document sha so the
    # text file dedups on identical document bytes.
    text_path = Path(ref.path).with_suffix(".txt")
    try:
        text_path.write_text(text, encoding="utf-8")
    except OSError as exc:
        log.warning(
            "doc_extract_text_write_failed", path=str(text_path), err=str(exc)
        )
        return new_refs

    text_ref = AttachmentRef(
        sha256=ref.sha256 + "_txt",  # derived — distinguishes from doc sha
        path=str(text_path),
        size_bytes=len(text.encode("utf-8")),
        kind="text",
        original_filename=Path(ref.original_filename).stem + ".txt",
    )
    storage.link_attachment(
        message_id=user_msg_id,
        kind=text_ref.kind,
        path=text_ref.path,
        size_bytes=text_ref.size_bytes,
        sha256=text_ref.sha256,
    )
    new_refs.append(text_ref)

    for img_ref in image_refs:
        storage.link_attachment(
            message_id=user_msg_id,
            kind=img_ref.kind,
            path=img_ref.path,
            size_bytes=img_ref.size_bytes,
            sha256=img_ref.sha256,
        )
        new_refs.append(img_ref)
    return new_refs


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
    # Phase 11-B — Custom Instructions injected into the system prompt
    # at chat/send time. None means "no project instructions". Constructed
    # by app.py::build_and_run from the per-project Saved/NYRA/instructions.md.
    custom_instructions: "object | None" = None
    _inflight: dict[str, asyncio.Event] = field(default_factory=dict)

    def _instructions_prefix(self) -> str:
        """Return the project Custom Instructions prefix (Aura parity).

        Empty string when no instructions are configured so callers can
        unconditionally concatenate. Reads cached body — does NOT touch
        disk on the chat hot path. Refresh the cache via the
        settings/set-instructions WS handler, which calls
        CustomInstructions.save → updates the cached body.
        """
        ci = self.custom_instructions
        if ci is None:
            return ""
        try:
            return ci.system_prompt_prefix()
        except Exception:  # noqa: BLE001
            # Custom Instructions are non-essential context — never let a
            # malformed instructions.md kill the chat path.
            return ""

    async def on_chat_send(
        self, params: dict, session: SessionState, ws: ServerConnection
    ) -> dict:
        conv_id = params["conversation_id"]
        req_id = params["req_id"]
        content = params["content"]
        backend = params.get("backend", "gemma-local")

        # Phase 2 (Plan 02-03): dispatch through BACKEND_REGISTRY.
        # gemma-local preserves Phase 1 behaviour (InferRouter path below).
        # claude / codex → AgentBackend.send() with BackendEvent → WS pump (CR-01).
        # Unknown backend → KeyError → ValueError caught and surfaced as -32601.
        if backend != "gemma-local":
            try:
                backend_cls = get_backend(backend)
            except ValueError:
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

            # CR-01: real Claude / Codex / future-backend wiring. Persist
            # the user message, ingest attachments, then run the
            # AgentBackend.send() coroutine in a background task that
            # translates BackendEvent objects into chat/stream WS
            # notifications. This used to raise NotImplementedError.
            # WR-03: route conversation insert through Storage.upsert_conversation
            # rather than reaching into self.storage.conn directly.
            self.storage.upsert_conversation(
                conv_id,
                title=content.split("\n", 1)[0][:48].strip() or "(empty)",
            )

            user_msg = self.storage.append_message(
                conversation_id=conv_id, role="user", content=content,
            )

            # Ingest attachments (CD-04). Same shape as the gemma path
            # below; keep them as a list[AttachmentRef] for the backend.
            backend_attachments: list = []
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
                        backend_attachments.append(ref)
                        # PARITY-01: documents (PDF/DOCX/PPTX/XLSX/HTML)
                        # get extracted into sibling text + embedded
                        # image refs that ride the existing image
                        # vision-routing path. Backend sees all derived
                        # refs alongside the original document.
                        if ref.kind == "document":
                            backend_attachments.extend(
                                _extract_and_link_document(
                                    ref=ref,
                                    pth=pth,
                                    project_saved=self.project_saved,
                                    storage=self.storage,
                                    user_msg_id=user_msg.id,
                                )
                            )
                    except Exception as _e:
                        log.warning(
                            "attachment_ingest_failed", path=pth, err=str(_e),
                        )

            # WR-06: defend against duplicate req_id collisions. If the
            # client retried a chat/send with the same req_id (client bug
            # or NyraHost reconnect), the prior stream's cancel Event was
            # silently overwritten and chat/cancel could no longer reach
            # it. Refuse the second send so the client surfaces the
            # collision instead of leaking a background task.
            if req_id in self._inflight:
                return {
                    "req_id": req_id,
                    "streaming": False,
                    "error": {
                        "code": -32602,
                        "message": "duplicate_req_id",
                        "data": {
                            "remediation": (
                                f"req_id {req_id!r} is already streaming. "
                                "Send chat/cancel first or generate a new "
                                "req_id."
                            ),
                        },
                    },
                }
            cancel = asyncio.Event()
            self._inflight[req_id] = cancel

            backend_inst = backend_cls()

            asyncio.create_task(
                self._run_backend_stream(
                    ws=ws,
                    backend=backend_inst,
                    conv_id=conv_id,
                    req_id=req_id,
                    content=content,
                    attachments=backend_attachments,
                    cancel=cancel,
                )
            )
            return {
                "req_id": req_id,
                "streaming": True,
                "backend": backend,
            }

        # Check Gemma installed (unless Ollama has it)
        if await self.router.gemma_not_installed():
            raise GemmaNotInstalledError()

        # WR-03: same conversation upsert pattern — go through Storage so
        # transaction semantics live in one place.
        self.storage.upsert_conversation(conv_id, title=content[:48])

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
                    # PARITY-01: same document branch as the claude
                    # path above. The gemma backend doesn't currently
                    # consume backend_attachments, so we don't need to
                    # collect the derived refs — link_attachment alone
                    # persists them for later UI display.
                    if ref.kind == "document":
                        _extract_and_link_document(
                            ref=ref,
                            pth=pth,
                            project_saved=self.project_saved,
                            storage=self.storage,
                            user_msg_id=user_msg.id,
                        )
                except Exception as _e:  # noqa: BLE001
                    log.warning(
                        "attachment_ingest_failed", path=pth, err=str(_e),
                    )

        # WR-06: same collision check on the gemma path.
        if req_id in self._inflight:
            return {
                "req_id": req_id,
                "streaming": False,
                "error": {
                    "code": -32602,
                    "message": "duplicate_req_id",
                    "data": {
                        "remediation": (
                            f"req_id {req_id!r} is already streaming. "
                            "Send chat/cancel first or generate a new "
                            "req_id."
                        ),
                    },
                },
            }
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

    async def _run_backend_stream(
        self,
        *,
        ws,
        backend,
        conv_id: str,
        req_id: str,
        content: str,
        attachments: list,
        cancel: asyncio.Event,
    ) -> None:
        """CR-01: pump AgentBackend.send() events into chat/stream notifications.

        Translates the BackendEvent tagged-union variants into the same
        chat/stream wire shape the gemma path produces:
          Delta(text)       -> {"delta": text, "done": False}
          ToolUse(...)      -> {"tool_use": {...}, "done": False}
          Retry(...)        -> {"retry": {...}, "done": False}
          Done(usage,reason)-> {"done": True, "usage": ..., "stop_reason": ...}
          Error(...)        -> {"done": True, "error": {...}}
        ToolResult is internal-only and not propagated to UE in v1.
        """
        from nyrahost.backends.base import (
            Delta as _Delta,
            ToolUse as _ToolUse,
            ToolResult as _ToolResult,
            Done as _Done,
            Error as _BErr,
            Retry as _Retry,
        )

        accumulated: list[str] = []
        final_usage: dict | None = None
        final_stop_reason: str | None = None
        error_payload: dict | None = None
        cancelled_flag = False

        async def _on_event(ev) -> None:
            nonlocal final_usage, final_stop_reason, error_payload, cancelled_flag
            if cancel.is_set():
                # Soft-cancel: stop forwarding deltas; the backend should
                # also be cancelled via backend.cancel(req_id) below.
                return
            if isinstance(ev, _Delta):
                if ev.text:
                    accumulated.append(ev.text)
                    try:
                        await ws.send(build_notification("chat/stream", {
                            "conversation_id": conv_id,
                            "req_id": req_id,
                            "delta": ev.text,
                            "done": False,
                        }))
                    except Exception:
                        pass
            elif isinstance(ev, _ToolUse):
                try:
                    await ws.send(build_notification("chat/stream", {
                        "conversation_id": conv_id,
                        "req_id": req_id,
                        "tool_use": {
                            "id": ev.id,
                            "name": ev.name,
                            "input_json": ev.input_json,
                        },
                        "done": False,
                    }))
                except Exception:
                    pass
            elif isinstance(ev, _ToolResult):
                # Internal — not surfaced to UE in v1.
                return
            elif isinstance(ev, _Retry):
                try:
                    await ws.send(build_notification("chat/stream", {
                        "conversation_id": conv_id,
                        "req_id": req_id,
                        "retry": {
                            "attempt": ev.attempt,
                            "delay_ms": ev.delay_ms,
                            "category": ev.error_category,
                        },
                        "done": False,
                    }))
                except Exception:
                    pass
            elif isinstance(ev, _Done):
                final_usage = dict(ev.usage) if ev.usage else None
                final_stop_reason = ev.stop_reason
            elif isinstance(ev, _BErr):
                error_payload = {
                    "code": ev.code,
                    "message": ev.message,
                    "data": {
                        "remediation": ev.remediation,
                        "retryable": ev.retryable,
                    },
                }

        try:
            await backend.send(
                conversation_id=conv_id,
                req_id=req_id,
                content=content,
                attachments=attachments,
                mcp_config_path=None,  # Phase 4+ wires this from MCP config writer
                on_event=_on_event,
            )
        except asyncio.CancelledError:
            cancelled_flag = True
            try:
                await backend.cancel(req_id)
            except Exception:
                pass
        except Exception as e:
            log.exception("backend_send_failed", req_id=req_id, backend=backend.name)
            error_payload = {
                "code": -32001,
                "message": "backend_failed",
                "data": {
                    "remediation": (
                        f"Backend {backend.name!r} raised {type(e).__name__}. "
                        "See Saved/NYRA/logs/ for the full traceback."
                    ),
                },
            }
        finally:
            self._inflight.pop(req_id, None)

        # Final frame
        final_params: dict[str, Any] = {
            "conversation_id": conv_id,
            "req_id": req_id,
            "delta": "",
            "done": True,
        }
        if cancel.is_set() or cancelled_flag:
            final_params["cancelled"] = True
        if final_usage is not None:
            final_params["usage"] = final_usage
        if final_stop_reason is not None:
            final_params["stop_reason"] = final_stop_reason
        if error_payload is not None:
            final_params["error"] = error_payload
        try:
            await ws.send(build_notification("chat/stream", final_params))
        except Exception:
            pass

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
