"""Chat export — produce a self-contained Markdown / JSON dump for a conversation.

Aura ships a "chat export for troubleshooting with the Aura team" feature
(per tryaura.dev docs §Troubleshooting). NYRA needs the same surface so
users can attach a session to a bug report. The output deliberately
matches Aura's shape (one Markdown file per conversation, plus an
optional JSON sidecar with the full structured envelope) so users
copy-pasting between the two products see consistent affordance.

Privacy posture:
  - Attachments are NOT inlined; only their path / sha / kind is included.
    A user dragging a confidential PDF onto chat doesn't accidentally
    publish it by exporting.
  - Backend errors are included verbatim because they're the most useful
    diagnostic for the maintainer.
  - The export does not include the auth token, handshake state, or any
    NYRA-internal credentials — Storage doesn't store them, so this is
    structurally guaranteed.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import structlog

from nyrahost.storage import Conversation, Message, Storage

log = structlog.get_logger("nyrahost.chat_export")

__all__ = [
    "export_conversation_markdown",
    "export_conversation_json",
    "export_all_conversations",
    "ChatExportResult",
]


@dataclass(frozen=True)
class ChatExportResult:
    """Outcome of an export call."""

    conversation_id: str
    markdown_path: Path
    json_path: Optional[Path]
    message_count: int
    attachment_count: int


def _safe_filename(text: str, fallback: str) -> str:
    """Strip a string to a filesystem-safe slug."""
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "-", text or "").strip("-")
    return cleaned[:64] if cleaned else fallback


def _format_timestamp(ms: int) -> str:
    """Convert ms-since-epoch to a stable ISO-8601 UTC string."""
    if ms <= 0:
        return "unknown"
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ms / 1000))


def export_conversation_markdown(
    storage: Storage,
    conversation_id: str,
    out_dir: Path,
    *,
    include_attachments_summary: bool = True,
) -> ChatExportResult:
    """Write a Markdown dump of one conversation under ``out_dir``.

    Filename: ``<isodate>-<slugified-title>-<first8-of-id>.md``.
    Returns the export result with paths and counts.

    Raises:
        ValueError: if conversation_id is unknown.
    """
    convo = storage.get_conversation(conversation_id)
    if convo is None:
        raise ValueError(f"unknown conversation_id: {conversation_id!r}")

    out_dir.mkdir(parents=True, exist_ok=True)
    messages = storage.list_messages(conversation_id)
    title_slug = _safe_filename(convo.title or "untitled", "conversation")
    date = _format_timestamp(convo.created_at)[:10]
    md_name = f"{date}-{title_slug}-{conversation_id[:8]}.md"
    md_path = out_dir / md_name

    md_lines: list[str] = []
    md_lines.append(f"# NYRA Chat Export — {convo.title or '(untitled)'}")
    md_lines.append("")
    md_lines.append("> Self-contained Markdown export for troubleshooting / archive.")
    md_lines.append("")
    md_lines.append(f"**Conversation ID:** `{convo.id}`")
    md_lines.append(f"**Created:** {_format_timestamp(convo.created_at)}")
    md_lines.append(f"**Updated:** {_format_timestamp(convo.updated_at)}")
    md_lines.append(f"**Messages:** {len(messages)}")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")

    attachment_total = 0
    for i, msg in enumerate(messages, start=1):
        md_lines.append(f"## #{i} — {msg.role} ({_format_timestamp(msg.created_at)})")
        md_lines.append("")
        md_lines.append(msg.content or "_(empty)_")
        md_lines.append("")

        if msg.usage_json:
            md_lines.append("**usage:**")
            md_lines.append("```json")
            md_lines.append(_pretty_json(msg.usage_json))
            md_lines.append("```")
            md_lines.append("")

        if msg.error_json:
            md_lines.append("**error:**")
            md_lines.append("```json")
            md_lines.append(_pretty_json(msg.error_json))
            md_lines.append("```")
            md_lines.append("")

        if include_attachments_summary:
            attachments = _list_attachments(storage, msg.id)
            if attachments:
                attachment_total += len(attachments)
                md_lines.append(f"**attachments ({len(attachments)}):**")
                for att in attachments:
                    md_lines.append(
                        f"- `{att['kind']}` "
                        f"`{att.get('path', '?')}` "
                        f"({att.get('size_bytes', 0)} bytes, "
                        f"sha256:`{(att.get('sha256') or '')[:12]}…`)"
                    )
                md_lines.append("")

        md_lines.append("---")
        md_lines.append("")

    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    log.info(
        "chat_export_markdown_written",
        path=str(md_path),
        message_count=len(messages),
        attachment_count=attachment_total,
    )

    return ChatExportResult(
        conversation_id=conversation_id,
        markdown_path=md_path,
        json_path=None,
        message_count=len(messages),
        attachment_count=attachment_total,
    )


def export_conversation_json(
    storage: Storage,
    conversation_id: str,
    out_dir: Path,
) -> ChatExportResult:
    """Write a JSON sidecar of one conversation under ``out_dir``.

    Useful when the maintainer wants to programmatically replay a session
    or diff two exports. The JSON shape is intentionally schema-stable
    — fields here are not renamed without bumping ``schema_version``.

    Raises:
        ValueError: if conversation_id is unknown.
    """
    convo = storage.get_conversation(conversation_id)
    if convo is None:
        raise ValueError(f"unknown conversation_id: {conversation_id!r}")

    out_dir.mkdir(parents=True, exist_ok=True)
    messages = storage.list_messages(conversation_id)
    title_slug = _safe_filename(convo.title or "untitled", "conversation")
    date = _format_timestamp(convo.created_at)[:10]
    json_name = f"{date}-{title_slug}-{conversation_id[:8]}.json"
    json_path = out_dir / json_name

    payload = {
        "schema_version": 1,
        "exported_at_ms": int(time.time() * 1000),
        "conversation": {
            "id": convo.id,
            "title": convo.title,
            "created_at_ms": convo.created_at,
            "updated_at_ms": convo.updated_at,
        },
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at_ms": m.created_at,
                "usage": _maybe_json(m.usage_json),
                "error": _maybe_json(m.error_json),
                "attachments": _list_attachments(storage, m.id),
            }
            for m in messages
        ],
    }
    attachment_total = sum(len(m["attachments"]) for m in payload["messages"])
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    log.info(
        "chat_export_json_written",
        path=str(json_path),
        message_count=len(messages),
        attachment_count=attachment_total,
    )

    return ChatExportResult(
        conversation_id=conversation_id,
        markdown_path=Path(),  # not produced in this call
        json_path=json_path,
        message_count=len(messages),
        attachment_count=attachment_total,
    )


def export_all_conversations(
    storage: Storage,
    out_dir: Path,
    *,
    limit: int = 50,
) -> list[ChatExportResult]:
    """Export every conversation in storage; one Markdown + one JSON each.

    Bounded by ``limit`` so a runaway export doesn't blow up the
    filesystem. Default 50 matches Storage.list_conversations default.
    """
    convos = storage.list_conversations(limit=limit)
    results: list[ChatExportResult] = []
    for c in convos:
        md = export_conversation_markdown(storage, c.id, out_dir)
        js = export_conversation_json(storage, c.id, out_dir)
        results.append(
            ChatExportResult(
                conversation_id=c.id,
                markdown_path=md.markdown_path,
                json_path=js.json_path,
                message_count=md.message_count,
                attachment_count=md.attachment_count,
            )
        )
    return results


def _pretty_json(raw: Optional[str]) -> str:
    """Pretty-print a stored JSON string; fall back to verbatim on error."""
    if not raw:
        return ""
    try:
        return json.dumps(json.loads(raw), indent=2, sort_keys=True)
    except (json.JSONDecodeError, TypeError):
        return raw


def _maybe_json(raw: Optional[str]) -> Optional[dict]:
    """Decode a stored JSON string; None on failure."""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def _list_attachments(storage: Storage, message_id: str) -> list[dict]:
    """Read attachment rows linked to a message.

    Storage doesn't expose a public list_attachments helper yet; we go
    through the connection directly. If/when Storage grows the surface
    this falls back to it.
    """
    list_fn = getattr(storage, "list_attachments", None)
    if callable(list_fn):
        return list(list_fn(message_id))
    rows = storage.conn.execute(
        "SELECT id, kind, path, size_bytes, sha256 "
        "FROM attachments WHERE message_id=?",
        (message_id,),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "kind": r["kind"],
            "path": r["path"],
            "size_bytes": r["size_bytes"],
            "sha256": r["sha256"],
        }
        for r in rows
    ]
