"""Session list/load JSON-RPC handlers (CD-05). See docs/JSONRPC.md 3.8, 3.9.

Pure read-only handlers backed by Plan 07's :class:`Storage` (SQLite).
Mounted on :class:`nyrahost.server.NyraServer` by :mod:`nyrahost.app` so the
UE-side history drawer (Plan 12b) can populate its conversation list and
load message snapshots on row click.

Wire shapes:

  sessions/list  request  -> {"limit": 50}                         (limit optional)
  sessions/list  response -> {"conversations": [
                               {"id","title","updated_at","message_count"}, ...
                             ]}
  sessions/load  request  -> {"conversation_id": "<uuid>", "limit": 200}
  sessions/load  response -> {"conversation_id": "<uuid>", "messages": [
                               {"id","role","content","created_at","attachments"},
                               ...
                             ]}

Ordering contract (CD-05):
  * sessions/list:  ORDER BY conversations.updated_at DESC
  * sessions/load:  messages returned in ASC created_at order so the
    panel renders them chronologically top-to-bottom. To bound memory
    when a conversation is huge, we fetch the latest ``limit`` messages
    by ``created_at DESC`` then reverse the result — equivalent to
    "last N" sorted ASC.

Attachment aggregation:
  Plan 07 stores attachments keyed by ``message_id``. We bulk-load all
  attachments for the returned message ids in a single query to keep
  the handler latency bounded at O(1) SQL round-trips regardless of
  how many messages are returned.
"""
from __future__ import annotations

from dataclasses import dataclass

import structlog

from ..session import SessionState
from ..storage import Storage

log = structlog.get_logger("nyrahost.sessions")

DEFAULT_LIST_LIMIT = 50
DEFAULT_LOAD_LIMIT = 200
MAX_LIST_LIMIT = 200
MAX_LOAD_LIMIT = 2000


def _clamp(val: int, lo: int, hi: int) -> int:
    return max(lo, min(val, hi))


@dataclass
class SessionHandlers:
    """Read-only sessions surface.

    One instance is constructed in :func:`app.build_and_run` and mounted
    on the singleton :class:`NyraServer` alongside the chat + download
    handlers. ``storage`` is shared with :class:`ChatHandlers` — both
    read/write the same sessions.db.
    """

    storage: Storage

    async def on_sessions_list(
        self, params: dict, session: SessionState
    ) -> dict:
        """Return recent conversations ordered by ``updated_at`` DESC.

        Each row carries a ``message_count`` (COUNT(*) subquery) so the
        drawer can surface message counts without a second round-trip.
        """
        raw_limit = params.get("limit") if isinstance(params, dict) else None
        try:
            limit = int(raw_limit) if raw_limit is not None else DEFAULT_LIST_LIMIT
        except (TypeError, ValueError):
            limit = DEFAULT_LIST_LIMIT
        limit = _clamp(limit, 1, MAX_LIST_LIMIT)

        rows = self.storage.conn.execute(
            "SELECT c.id, c.title, c.updated_at, "
            "  (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) "
            "  AS message_count "
            "FROM conversations c "
            "ORDER BY c.updated_at DESC "
            "LIMIT ?",
            (limit,),
        ).fetchall()
        return {
            "conversations": [
                {
                    "id": r[0],
                    "title": r[1] or "",
                    "updated_at": int(r[2] or 0),
                    "message_count": int(r[3] or 0),
                }
                for r in rows
            ],
        }

    async def on_sessions_load(
        self, params: dict, session: SessionState
    ) -> dict:
        """Return messages for ``conversation_id`` in ASC ``created_at`` order.

        Returns an empty ``messages`` list (no raise) when the id is
        unknown so the drawer can still surface an empty body without
        dedicated error handling.
        """
        if not isinstance(params, dict):
            params = {}
        conv_id = str(params.get("conversation_id") or "")
        raw_limit = params.get("limit")
        try:
            limit = int(raw_limit) if raw_limit is not None else DEFAULT_LOAD_LIMIT
        except (TypeError, ValueError):
            limit = DEFAULT_LOAD_LIMIT
        limit = _clamp(limit, 1, MAX_LOAD_LIMIT)

        if not conv_id:
            return {"conversation_id": "", "messages": []}

        # Latest N by DESC, reversed into ASC for panel chronology.
        latest = self.storage.conn.execute(
            "SELECT id, role, content, created_at FROM messages "
            "WHERE conversation_id = ? ORDER BY created_at DESC LIMIT ?",
            (conv_id, limit),
        ).fetchall()
        msg_rows = list(reversed(latest))
        if not msg_rows:
            return {"conversation_id": conv_id, "messages": []}

        # Bulk-load attachments for all returned message ids in one query.
        msg_ids = [m[0] for m in msg_rows]
        placeholders = ",".join(["?"] * len(msg_ids))
        att_rows = self.storage.conn.execute(
            f"SELECT id, message_id, kind, path, size_bytes, sha256 "
            f"FROM attachments WHERE message_id IN ({placeholders})",
            msg_ids,
        ).fetchall()
        att_by_msg: dict[str, list[dict]] = {}
        for a in att_rows:
            att_by_msg.setdefault(a[1], []).append(
                {
                    "id": a[0],
                    "kind": a[2],
                    "path": a[3],
                    "size_bytes": int(a[4] or 0),
                    "sha256": a[5],
                }
            )

        return {
            "conversation_id": conv_id,
            "messages": [
                {
                    "id": m[0],
                    "role": m[1],
                    "content": m[2],
                    "created_at": int(m[3] or 0),
                    "attachments": att_by_msg.get(m[0], []),
                }
                for m in msg_rows
            ],
        }
