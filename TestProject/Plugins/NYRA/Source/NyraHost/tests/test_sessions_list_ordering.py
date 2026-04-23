"""sessions/list + sessions/load handler tests.

VALIDATION test ID: 1-12b-01 (per PLAN 01-12b). Covers the four
read-only cases the history drawer depends on:

  - test_sessions_list_ordering            -> ORDER BY updated_at DESC + message_count
  - test_sessions_list_respects_limit      -> params.limit is honoured + clamped
  - test_sessions_load_returns_messages_asc -> messages returned in ASC created_at
  - test_sessions_load_unknown_id_returns_empty -> bogus id returns empty list (no raise)

These handlers are pure readers against Plan 07's Storage. With
asyncio_mode = "auto" in pyproject.toml, the async test functions are
run by pytest-asyncio without per-test decorators.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from nyrahost.storage import Storage, db_path_for_project
from nyrahost.handlers.sessions import SessionHandlers
from nyrahost.session import SessionState


def _insert_conv(s: Storage, *, cid: str, title: str, updated_at: int) -> None:
    s.conn.execute(
        "INSERT INTO conversations(id,title,created_at,updated_at) VALUES(?,?,?,?)",
        (cid, title, updated_at, updated_at),
    )
    s.conn.commit()


def _insert_msg(
    s: Storage, *, cid: str, role: str, content: str, created_at: int
) -> str:
    mid = str(uuid.uuid4())
    s.conn.execute(
        "INSERT INTO messages(id,conversation_id,role,content,created_at) "
        "VALUES(?,?,?,?,?)",
        (mid, cid, role, content, created_at),
    )
    s.conn.commit()
    return mid


async def test_sessions_list_ordering(tmp_project_dir: Path) -> None:
    s = Storage(db_path_for_project(tmp_project_dir))
    try:
        _insert_conv(s, cid="conv-a", title="A", updated_at=1000)
        _insert_conv(s, cid="conv-b", title="B", updated_at=3000)
        _insert_conv(s, cid="conv-c", title="C", updated_at=2000)
        _insert_msg(s, cid="conv-b", role="user", content="1", created_at=3000)
        _insert_msg(s, cid="conv-b", role="assistant", content="1r", created_at=3001)
        _insert_msg(s, cid="conv-c", role="user", content="x", created_at=2000)

        h = SessionHandlers(storage=s)
        result = await h.on_sessions_list(
            {"limit": 50},
            SessionState(authenticated=True, session_id="sid"),
        )
        convs = result["conversations"]
        # DESC by updated_at -> conv-b (3000), conv-c (2000), conv-a (1000)
        assert [c["id"] for c in convs] == ["conv-b", "conv-c", "conv-a"]
        counts = {c["id"]: c["message_count"] for c in convs}
        assert counts == {"conv-a": 0, "conv-b": 2, "conv-c": 1}
        # Required row shape
        for c in convs:
            assert isinstance(c["title"], str)
            assert isinstance(c["updated_at"], int)
            assert isinstance(c["message_count"], int)
    finally:
        s.close()


async def test_sessions_list_respects_limit(tmp_project_dir: Path) -> None:
    s = Storage(db_path_for_project(tmp_project_dir))
    try:
        for i in range(5):
            _insert_conv(s, cid=f"c{i}", title=f"T{i}", updated_at=1000 + i)
        h = SessionHandlers(storage=s)
        result = await h.on_sessions_list(
            {"limit": 2},
            SessionState(authenticated=True, session_id="sid"),
        )
        assert len(result["conversations"]) == 2
        # Top 2 most recent: c4 (1004), c3 (1003)
        assert [c["id"] for c in result["conversations"]] == ["c4", "c3"]
    finally:
        s.close()


async def test_sessions_load_returns_messages_asc(tmp_project_dir: Path) -> None:
    s = Storage(db_path_for_project(tmp_project_dir))
    try:
        _insert_conv(s, cid="conv-x", title="X", updated_at=500)
        _insert_msg(s, cid="conv-x", role="user", content="m1", created_at=100)
        _insert_msg(s, cid="conv-x", role="assistant", content="m3", created_at=300)
        _insert_msg(s, cid="conv-x", role="user", content="m2", created_at=200)
        _insert_msg(s, cid="conv-x", role="assistant", content="m4", created_at=400)

        h = SessionHandlers(storage=s)
        result = await h.on_sessions_load(
            {"conversation_id": "conv-x", "limit": 200},
            SessionState(authenticated=True, session_id="sid"),
        )
        assert result["conversation_id"] == "conv-x"
        # ASC by created_at -> m1 (100), m2 (200), m3 (300), m4 (400)
        assert [m["content"] for m in result["messages"]] == [
            "m1",
            "m2",
            "m3",
            "m4",
        ]
        # Every message carries an attachments array (possibly empty)
        assert all(isinstance(m.get("attachments"), list) for m in result["messages"])
        # Required row shape
        for m in result["messages"]:
            assert isinstance(m["id"], str)
            assert m["role"] in {"user", "assistant", "system", "tool"}
            assert isinstance(m["created_at"], int)
    finally:
        s.close()


async def test_sessions_load_unknown_id_returns_empty(tmp_project_dir: Path) -> None:
    s = Storage(db_path_for_project(tmp_project_dir))
    try:
        h = SessionHandlers(storage=s)
        result = await h.on_sessions_load(
            {"conversation_id": "does-not-exist", "limit": 200},
            SessionState(authenticated=True, session_id="sid"),
        )
        assert result == {"conversation_id": "does-not-exist", "messages": []}
    finally:
        s.close()
