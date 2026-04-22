"""SQLite storage for conversations, messages, attachments.

Per-project: <ProjectDir>/Saved/NYRA/sessions.db (CD-07).

Single-writer (NyraHost only); PRAGMA journal_mode=WAL per RESEARCH §3.7.
UE does NOT link SQLiteCore in Phase 1 — it reads history via WS requests
(sessions/list, sessions/load) mounted on NyraServer in Plans 10/12.

Schema v1 tables (see <interfaces> in 01-07 PLAN):
  conversations(id, title, created_at, updated_at)
  messages(id, conversation_id, role, content, created_at, usage_json, error_json)
  attachments(id, message_id, kind, path, size_bytes, sha256)

Index: idx_messages_conv_created on messages(conversation_id, created_at).
Migration mechanism: PRAGMA user_version. v0 -> v1 on first open; v1 is a
no-op. Unknown versions raise RuntimeError so future schema bumps can't
silently downgrade an existing DB.
"""
from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

CURRENT_SCHEMA_VERSION = 1

Role = Literal["user", "assistant", "system", "tool"]
AttachmentKind = Literal["image", "video", "text"]

# NOTE: keep schema DDL in a single string constant so it's trivially
# grep-able for audit tools and so Plan 12's readers (UE C++ side, when
# Phase 2 links SQLiteCore) can mirror the exact shape. The comment
# "PRAGMA journal_mode=WAL" is also load-bearing for 01-07's grep-based
# acceptance criteria.
SCHEMA_V1 = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS conversations (
    id         TEXT PRIMARY KEY,
    title      TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK(role IN ('user','assistant','system','tool')),
    content         TEXT NOT NULL,
    created_at      INTEGER NOT NULL,
    usage_json      TEXT,
    error_json      TEXT
);
CREATE INDEX IF NOT EXISTS idx_messages_conv_created
    ON messages(conversation_id, created_at);

CREATE TABLE IF NOT EXISTS attachments (
    id          TEXT PRIMARY KEY,
    message_id  TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL,
    path        TEXT NOT NULL,
    size_bytes  INTEGER,
    sha256      TEXT
);
"""


@dataclass(frozen=True)
class Conversation:
    id: str
    title: str | None
    created_at: int
    updated_at: int


@dataclass(frozen=True)
class Message:
    id: str
    conversation_id: str
    role: Role
    content: str
    created_at: int
    usage_json: str | None = None
    error_json: str | None = None


def db_path_for_project(project_dir: Path) -> Path:
    """Canonical CD-07 DB location: <ProjectDir>/Saved/NYRA/sessions.db."""
    return project_dir / "Saved" / "NYRA" / "sessions.db"


class Storage:
    """Single-writer SQLite wrapper.

    NyraHost is the only writer per RESEARCH §3.7. WAL mode is set at
    bootstrap; subsequent connections only need to re-assert
    foreign_keys=ON and synchronous=NORMAL (WAL is persisted in the DB
    file itself).
    """

    def __init__(self, db_path: Path):
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(db_path),
            detect_types=sqlite3.PARSE_DECLTYPES,
            isolation_level="DEFERRED",
        )
        self._conn.row_factory = sqlite3.Row
        self._migrate()

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    def _migrate(self) -> None:
        cur = self._conn.execute("PRAGMA user_version")
        (version,) = cur.fetchone()
        if version == 0:
            # Fresh DB — install schema v1 and mark user_version.
            self._conn.executescript(SCHEMA_V1)
            self._conn.execute(f"PRAGMA user_version={CURRENT_SCHEMA_VERSION}")
            self._conn.commit()
        elif version != CURRENT_SCHEMA_VERSION:
            raise RuntimeError(
                f"Unsupported schema version {version}; "
                f"expected {CURRENT_SCHEMA_VERSION}"
            )
        # Enforce PRAGMAs on every new connection (WAL persists in the
        # file; foreign_keys + synchronous are per-connection so we
        # re-assert on every Storage() open).
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA synchronous=NORMAL")

    def bootstrap(self) -> None:
        """Idempotent — re-running migrate on an existing v1 DB is a no-op."""
        self._migrate()

    # ---- Conversations ----

    def create_conversation(self, *, title: str | None = None) -> Conversation:
        conv_id = str(uuid.uuid4())
        now = int(time.time() * 1000)
        self._conn.execute(
            "INSERT INTO conversations(id,title,created_at,updated_at) "
            "VALUES(?,?,?,?)",
            (conv_id, title, now, now),
        )
        self._conn.commit()
        return Conversation(
            id=conv_id, title=title, created_at=now, updated_at=now
        )

    def get_conversation(self, conv_id: str) -> Conversation | None:
        row = self._conn.execute(
            "SELECT id,title,created_at,updated_at FROM conversations "
            "WHERE id=?",
            (conv_id,),
        ).fetchone()
        if row is None:
            return None
        return Conversation(**dict(row))

    def list_conversations(self, *, limit: int = 50) -> list[Conversation]:
        rows = self._conn.execute(
            "SELECT id,title,created_at,updated_at FROM conversations "
            "ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [Conversation(**dict(r)) for r in rows]

    # ---- Messages ----

    def append_message(
        self,
        *,
        conversation_id: str,
        role: Role,
        content: str,
        usage_json: str | None = None,
        error_json: str | None = None,
    ) -> Message:
        msg_id = str(uuid.uuid4())
        now = int(time.time() * 1000)
        self._conn.execute(
            "INSERT INTO messages("
            "id,conversation_id,role,content,created_at,usage_json,error_json"
            ") VALUES(?,?,?,?,?,?,?)",
            (msg_id, conversation_id, role, content, now, usage_json, error_json),
        )
        self._conn.execute(
            "UPDATE conversations SET updated_at=? WHERE id=?",
            (now, conversation_id),
        )
        self._conn.commit()
        return Message(
            id=msg_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=now,
            usage_json=usage_json,
            error_json=error_json,
        )

    def list_messages(self, conversation_id: str) -> list[Message]:
        rows = self._conn.execute(
            "SELECT id,conversation_id,role,content,created_at,"
            "usage_json,error_json "
            "FROM messages WHERE conversation_id=? ORDER BY created_at ASC",
            (conversation_id,),
        ).fetchall()
        return [Message(**dict(r)) for r in rows]

    # ---- Attachments ----

    def link_attachment(
        self,
        *,
        message_id: str,
        kind: AttachmentKind,
        path: str,
        size_bytes: int,
        sha256: str,
    ) -> str:
        att_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO attachments("
            "id,message_id,kind,path,size_bytes,sha256"
            ") VALUES(?,?,?,?,?,?)",
            (att_id, message_id, kind, path, size_bytes, sha256),
        )
        self._conn.commit()
        return att_id

    def close(self) -> None:
        self._conn.close()
