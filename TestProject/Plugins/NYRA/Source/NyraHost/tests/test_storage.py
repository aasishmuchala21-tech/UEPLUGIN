"""Storage + schema tests.
VALIDATION test ID: 1-04-06
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from nyrahost.storage import Storage, db_path_for_project, CURRENT_SCHEMA_VERSION


def test_schema_v1(tmp_project_dir: Path) -> None:
    db_path = db_path_for_project(tmp_project_dir)
    s = Storage(db_path)
    try:
        cur = s.conn.execute("PRAGMA user_version")
        assert cur.fetchone()[0] == CURRENT_SCHEMA_VERSION
        cur = s.conn.execute("PRAGMA journal_mode")
        assert cur.fetchone()[0].lower() == "wal"
        cur = s.conn.execute("PRAGMA foreign_keys")
        assert cur.fetchone()[0] == 1
        # Tables exist
        tables = {
            r[0]
            for r in s.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {"conversations", "messages", "attachments"}.issubset(tables)
        # Index exists
        idxs = {
            r[0]
            for r in s.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }
        assert "idx_messages_conv_created" in idxs
    finally:
        s.close()


def test_schema_v1_idempotent(tmp_project_dir: Path) -> None:
    db_path = db_path_for_project(tmp_project_dir)
    s1 = Storage(db_path)
    s1.bootstrap()
    s1.close()
    s2 = Storage(db_path)
    s2.bootstrap()
    s2.close()
    # Reopen and verify version is still 1
    s3 = Storage(db_path)
    try:
        (v,) = s3.conn.execute("PRAGMA user_version").fetchone()
        assert v == CURRENT_SCHEMA_VERSION
    finally:
        s3.close()


def test_insert_conversation_and_message_and_cascade(tmp_project_dir: Path) -> None:
    db = db_path_for_project(tmp_project_dir)
    s = Storage(db)
    try:
        conv = s.create_conversation(title="hello")
        s.append_message(conversation_id=conv.id, role="user", content="hi")
        s.append_message(
            conversation_id=conv.id, role="assistant", content="hello back"
        )
        msgs = s.list_messages(conv.id)
        assert [m.content for m in msgs] == ["hi", "hello back"]
        # Cascade delete
        s.conn.execute("DELETE FROM conversations WHERE id=?", (conv.id,))
        s.conn.commit()
        assert s.list_messages(conv.id) == []
    finally:
        s.close()


def test_message_role_check(tmp_project_dir: Path) -> None:
    db = db_path_for_project(tmp_project_dir)
    s = Storage(db)
    try:
        conv = s.create_conversation(title="t")
        with pytest.raises(sqlite3.IntegrityError):
            s.conn.execute(
                "INSERT INTO messages(id,conversation_id,role,content,created_at) "
                "VALUES('x',?,'invalid_role','c',0)",
                (conv.id,),
            )
            s.conn.commit()
    finally:
        s.close()
