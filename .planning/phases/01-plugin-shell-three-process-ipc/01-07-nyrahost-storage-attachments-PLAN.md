---
phase: 01-plugin-shell-three-process-ipc
plan: 07
type: execute
wave: 2
depends_on: [02, 06]
autonomous: true
requirements: [CHAT-01]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/storage.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/attachments.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_storage.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_attachments.py
objective: >
  Implement the NyraHost storage layer: per-project SQLite DB at
  `<ProjectDir>/Saved/NYRA/sessions.db` with schema v1 (conversations,
  messages, attachments) per CD-07, attachment content-addressed ingestion
  into `Saved/NYRA/attachments/<sha-prefix>/<sha>.<ext>` per CD-08.
  Fills VALIDATION rows 1-04-06 (test_schema_v1) and 1-04-07
  (test_ingest_hardlink_and_sha256). Python-side only — UE does NOT link
  SQLiteCore in Phase 1 per RESEARCH §3.7.
must_haves:
  truths:
    - "Calling Storage.bootstrap(tmp_project_dir) creates Saved/NYRA/sessions.db with PRAGMA user_version=1 and tables conversations/messages/attachments"
    - "PRAGMA journal_mode returns 'wal' after bootstrap"
    - "Calling ingest_attachment twice on the same file produces identical {sha256, path} and only one physical file under attachments/"
    - "Schema migration from user_version=0 to 1 is idempotent (calling bootstrap on an existing v1 DB is a no-op)"
    - "pytest tests/test_storage.py::test_schema_v1 passes"
    - "pytest tests/test_attachments.py::test_ingest_hardlink_and_sha256 passes"
  artifacts:
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/storage.py
      provides: "Storage class with bootstrap + conversation/message CRUD"
      exports: ["Storage", "Conversation", "Message", "SCHEMA_V1"]
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/attachments.py
      provides: "ingest_attachment + AttachmentRef dataclass"
      exports: ["ingest_attachment", "AttachmentRef"]
  key_links:
    - from: storage.py Storage.bootstrap
      to: SQLite WAL + schema v1
      via: "PRAGMA journal_mode=WAL; CREATE TABLE IF NOT EXISTS conversations/messages/attachments"
      pattern: "journal_mode=WAL"
    - from: attachments.py ingest_attachment
      to: "<ProjectDir>/Saved/NYRA/attachments/<sha-prefix-2>/<sha256>.<ext>"
      via: "os.link (hardlink) with shutil.copy2 fallback"
      pattern: "os.link"
---

<objective>
Persistence layer for CHAT-01's "per-conversation history persisted under
project Saved/NYRA/" requirement. Python-only: NyraHost is the sole writer
per RESEARCH §3.7 (single-writer WAL textbook pattern); UE reads history via
WS requests in Phase 2.

Per CONTEXT.md:
- CD-07: Schema v1 with tables conversations, messages, attachments; indexes
  `(conversation_id, created_at)` on messages. Migrations via PRAGMA user_version.
- CD-08: Attachments as file refs (NOT blobs), content-addressed hardlink/copy.

Per RESEARCH §3.7: Python stdlib sqlite3 + WAL mode + foreign_keys ON +
synchronous=NORMAL. Skip SQLiteCore in UE Phase 1.

Purpose: Plan 12 (chat panel) can persist messages immediately on send;
Plan 06's server gains storage-aware handlers via NyraServer extension
points.
Output: 2 Python modules + 2 real test files (replacing Wave 0 placeholders).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md
@TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/server.py
@TestProject/Plugins/NYRA/Source/NyraHost/tests/conftest.py
@TestProject/Plugins/NYRA/Source/NyraHost/tests/test_storage.py
@TestProject/Plugins/NYRA/Source/NyraHost/tests/test_attachments.py
</context>

<interfaces>
Schema v1 DDL (from RESEARCH §3.7):

```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;
PRAGMA user_version=1;

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
```

Attachment dest path: `<ProjectSaved>/NYRA/attachments/<sha[:2]>/<sha>.<ext>`
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: storage.py + test_storage.py</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/storage.py
    TestProject/Plugins/NYRA/Source/NyraHost/tests/test_storage.py
  </files>
  <read_first>
    - .planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md CD-07
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.7 full content (schema, migrations, single-writer rationale)
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_storage.py (Wave 0 placeholder)
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/conftest.py (tmp_project_dir fixture)
  </read_first>
  <behavior>
    - test_schema_v1: bootstrap on a fresh tmp_project_dir creates conversations/messages/attachments tables + index; PRAGMA user_version == 1; PRAGMA journal_mode == "wal".
    - test_schema_v1_idempotent: calling bootstrap twice on the same path is a no-op (user_version stays 1, no errors).
    - test_insert_conversation_and_message: creating a conversation then a message correctly FK-references; deleting conversation cascades-delete messages.
    - test_message_role_check: inserting a message with role="invalid" raises sqlite3.IntegrityError (CHECK constraint).
  </behavior>
  <action>
    **1. CREATE src/nyrahost/storage.py:**

    ```python
    """SQLite storage for conversations, messages, attachments.

    Per-project: <ProjectDir>/Saved/NYRA/sessions.db (CD-07).
    Single-writer (NyraHost only); PRAGMA journal_mode=WAL per RESEARCH §3.7.
    """
    from __future__ import annotations
    import sqlite3
    import time
    import uuid
    from dataclasses import dataclass
    from pathlib import Path
    from typing import Any, Iterable, Literal

    CURRENT_SCHEMA_VERSION = 1

    Role = Literal["user", "assistant", "system", "tool"]
    AttachmentKind = Literal["image", "video", "text"]

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
        return project_dir / "Saved" / "NYRA" / "sessions.db"


    class Storage:
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
                self._conn.executescript(SCHEMA_V1)
                self._conn.execute(f"PRAGMA user_version={CURRENT_SCHEMA_VERSION}")
                self._conn.commit()
            elif version != CURRENT_SCHEMA_VERSION:
                raise RuntimeError(
                    f"Unsupported schema version {version}; expected {CURRENT_SCHEMA_VERSION}"
                )
            # Enforce PRAGMAs on every new connection (WAL persists in file; others are per-conn)
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.execute("PRAGMA synchronous=NORMAL")

        def bootstrap(self) -> None:
            """Idempotent — re-running migrate is safe."""
            self._migrate()

        # ---- Conversations ----
        def create_conversation(self, *, title: str | None = None) -> Conversation:
            conv_id = str(uuid.uuid4())
            now = int(time.time() * 1000)
            self._conn.execute(
                "INSERT INTO conversations(id,title,created_at,updated_at) VALUES(?,?,?,?)",
                (conv_id, title, now, now),
            )
            self._conn.commit()
            return Conversation(id=conv_id, title=title, created_at=now, updated_at=now)

        def get_conversation(self, conv_id: str) -> Conversation | None:
            row = self._conn.execute(
                "SELECT id,title,created_at,updated_at FROM conversations WHERE id=?",
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
                "INSERT INTO messages(id,conversation_id,role,content,created_at,usage_json,error_json) "
                "VALUES(?,?,?,?,?,?,?)",
                (msg_id, conversation_id, role, content, now, usage_json, error_json),
            )
            self._conn.execute(
                "UPDATE conversations SET updated_at=? WHERE id=?",
                (now, conversation_id),
            )
            self._conn.commit()
            return Message(
                id=msg_id, conversation_id=conversation_id, role=role, content=content,
                created_at=now, usage_json=usage_json, error_json=error_json,
            )

        def list_messages(self, conversation_id: str) -> list[Message]:
            rows = self._conn.execute(
                "SELECT id,conversation_id,role,content,created_at,usage_json,error_json "
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
                "INSERT INTO attachments(id,message_id,kind,path,size_bytes,sha256) "
                "VALUES(?,?,?,?,?,?)",
                (att_id, message_id, kind, path, size_bytes, sha256),
            )
            self._conn.commit()
            return att_id

        def close(self) -> None:
            self._conn.close()
    ```

    **2. REPLACE tests/test_storage.py:**

    ```python
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
            tables = {r[0] for r in s.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            assert {"conversations", "messages", "attachments"}.issubset(tables)
            # Index exists
            idxs = {r[0] for r in s.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
            assert "idx_messages_conv_created" in idxs
        finally:
            s.close()


    def test_schema_v1_idempotent(tmp_project_dir: Path) -> None:
        db_path = db_path_for_project(tmp_project_dir)
        s1 = Storage(db_path); s1.bootstrap(); s1.close()
        s2 = Storage(db_path); s2.bootstrap(); s2.close()
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
            m1 = s.append_message(conversation_id=conv.id, role="user", content="hi")
            m2 = s.append_message(conversation_id=conv.id, role="assistant", content="hello back")
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
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "PRAGMA journal_mode=WAL" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/storage.py` >= 1
      - `grep -c "CURRENT_SCHEMA_VERSION = 1" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/storage.py` equals 1
      - `grep -c "CHECK(role IN ('user','assistant','system','tool'))" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/storage.py` equals 1
      - `grep -c "idx_messages_conv_created" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/storage.py` >= 1
      - `grep -c "ON DELETE CASCADE" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/storage.py` >= 2
      - `pytest TestProject/Plugins/NYRA/Source/NyraHost/tests/test_storage.py -v` exits 0 with 4 tests passing
    </automated>
  </verify>
  <acceptance_criteria>
    - storage.py contains literal text `CURRENT_SCHEMA_VERSION = 1`
    - storage.py contains literal text `PRAGMA journal_mode=WAL` and `PRAGMA synchronous=NORMAL` and `PRAGMA foreign_keys=ON`
    - storage.py contains the complete CREATE TABLE statements for `conversations`, `messages`, `attachments`
    - storage.py contains the CREATE INDEX statement `idx_messages_conv_created`
    - storage.py contains `CHECK(role IN ('user','assistant','system','tool'))`
    - storage.py contains `REFERENCES conversations(id) ON DELETE CASCADE` AND `REFERENCES messages(id) ON DELETE CASCADE`
    - storage.py exports dataclasses `Conversation` and `Message` with exact field names matching schema columns
    - storage.py exports `db_path_for_project(project_dir: Path) -> Path` returning `project_dir / "Saved" / "NYRA" / "sessions.db"`
    - storage.py `Storage._migrate()` performs PRAGMA user_version check and scripts schema on version 0
    - test_storage.py contains `def test_schema_v1(tmp_project_dir: Path)` (NOT skipped)
    - test_storage.py contains `def test_schema_v1_idempotent`
    - test_storage.py contains `def test_insert_conversation_and_message_and_cascade`
    - test_storage.py contains `def test_message_role_check` with `pytest.raises(sqlite3.IntegrityError)`
    - `pytest tests/test_storage.py -v` exits 0 with 4 tests passing
  </acceptance_criteria>
  <done>SQLite storage operational; schema v1 enforced; CHAT-01 persistence requirement met on the Python side.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: attachments.py + test_attachments.py</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/attachments.py
    TestProject/Plugins/NYRA/Source/NyraHost/tests/test_attachments.py
  </files>
  <read_first>
    - .planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md CD-08
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.7 "Attachment content-addressing"
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_attachments.py (Wave 0 placeholder)
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/storage.py (just created — AttachmentKind literal)
  </read_first>
  <behavior>
    - test_ingest_hardlink_and_sha256: ingest_attachment on a known-content file returns AttachmentRef with sha256 matching hashlib.sha256(bytes).hexdigest() and path under Saved/NYRA/attachments/<sha[:2]>/<sha>.<ext>.
    - test_ingest_dedup: ingest_attachment twice on same content yields identical dest path and only ONE physical file on disk (content-addressed).
    - test_ingest_unsupported_kind: ingest_attachment on .exe raises ValueError listing allowed kinds.
    - test_ingest_hardlink_falls_back_to_copy: simulate cross-device (mock os.link to raise OSError), verify shutil.copy2 path works and produces identical sha256.
  </behavior>
  <action>
    **1. CREATE src/nyrahost/attachments.py:**

    ```python
    """Content-addressed attachment ingestion (CD-08).

    Hashes source file, links or copies into
    <ProjectSaved>/NYRA/attachments/<sha[:2]>/<sha>.<ext>.
    """
    from __future__ import annotations
    import hashlib
    import os
    import shutil
    from dataclasses import dataclass
    from pathlib import Path
    from typing import Literal

    AttachmentKind = Literal["image", "video", "text"]

    ALLOWED_EXTENSIONS: dict[AttachmentKind, frozenset[str]] = {
        "image": frozenset({".png", ".jpg", ".jpeg", ".webp"}),
        "video": frozenset({".mp4", ".mov"}),
        "text": frozenset({".md", ".txt"}),
    }


    @dataclass(frozen=True)
    class AttachmentRef:
        sha256: str
        path: str  # absolute, points into Saved/NYRA/attachments/<prefix>/<sha>.<ext>
        size_bytes: int
        kind: AttachmentKind
        original_filename: str


    def _classify(ext_lower: str) -> AttachmentKind:
        for k, exts in ALLOWED_EXTENSIONS.items():
            if ext_lower in exts:
                return k
        raise ValueError(
            f"Unsupported attachment extension {ext_lower!r}. Allowed: "
            + ", ".join(sorted(e for exts in ALLOWED_EXTENSIONS.values() for e in exts))
        )


    def _sha256_of_file(path: Path, chunk: int = 1024 * 1024) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            while True:
                buf = f.read(chunk)
                if not buf:
                    break
                h.update(buf)
        return h.hexdigest()


    def ingest_attachment(
        src_path: Path,
        *,
        project_saved: Path,
    ) -> AttachmentRef:
        """Hash src, link (or copy) to <project_saved>/NYRA/attachments/<sha[:2]>/<sha>.<ext>.

        project_saved is the project's `Saved/` directory (i.e. <ProjectDir>/Saved/).
        Returned path is absolute.
        """
        if not src_path.is_file():
            raise FileNotFoundError(src_path)
        ext = src_path.suffix.lower()
        kind = _classify(ext)
        sha = _sha256_of_file(src_path)
        prefix = sha[:2]
        dest_dir = project_saved / "NYRA" / "attachments" / prefix
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{sha}{ext}"
        if not dest.exists():
            try:
                os.link(src_path, dest)
            except OSError:
                # Cross-device or filesystem doesn't support hardlinks; fall back to copy2
                shutil.copy2(src_path, dest)
        size = dest.stat().st_size
        return AttachmentRef(
            sha256=sha,
            path=str(dest.resolve()),
            size_bytes=size,
            kind=kind,
            original_filename=src_path.name,
        )
    ```

    **2. REPLACE tests/test_attachments.py:**

    ```python
    """Content-addressed attachment tests.
    VALIDATION test ID: 1-04-07
    """
    from __future__ import annotations
    import hashlib
    import os
    from pathlib import Path
    from unittest.mock import patch
    import pytest
    from nyrahost.attachments import ingest_attachment, AttachmentRef, ALLOWED_EXTENSIONS


    def _write_fixture(tmp: Path, name: str, payload: bytes) -> Path:
        p = tmp / name
        p.write_bytes(payload)
        return p


    def test_ingest_hardlink_and_sha256(tmp_project_dir: Path, tmp_path: Path) -> None:
        payload = b"hello world" * 1024  # 11 KB
        src = _write_fixture(tmp_path, "note.txt", payload)
        expected_sha = hashlib.sha256(payload).hexdigest()
        ref = ingest_attachment(src, project_saved=tmp_project_dir / "Saved")
        assert isinstance(ref, AttachmentRef)
        assert ref.sha256 == expected_sha
        assert ref.kind == "text"
        assert ref.size_bytes == len(payload)
        assert ref.original_filename == "note.txt"
        # dest path under attachments/<prefix>/<sha>.txt
        dest = Path(ref.path)
        assert dest.exists()
        assert dest.parent.name == expected_sha[:2]
        assert dest.name == f"{expected_sha}.txt"


    def test_ingest_dedup(tmp_project_dir: Path, tmp_path: Path) -> None:
        payload = b"\x00\x01\x02\x03" * 100
        src1 = _write_fixture(tmp_path, "a.png", payload)
        src2 = _write_fixture(tmp_path, "b.png", payload)  # same bytes, different filename
        r1 = ingest_attachment(src1, project_saved=tmp_project_dir / "Saved")
        r2 = ingest_attachment(src2, project_saved=tmp_project_dir / "Saved")
        assert r1.sha256 == r2.sha256
        assert r1.path == r2.path
        # Only one physical file
        att_dir = tmp_project_dir / "Saved" / "NYRA" / "attachments" / r1.sha256[:2]
        assert len(list(att_dir.iterdir())) == 1


    def test_ingest_unsupported_kind(tmp_project_dir: Path, tmp_path: Path) -> None:
        src = _write_fixture(tmp_path, "bad.exe", b"MZ\x00\x00")
        with pytest.raises(ValueError) as exc:
            ingest_attachment(src, project_saved=tmp_project_dir / "Saved")
        assert ".exe" in str(exc.value) or "Unsupported" in str(exc.value)


    def test_ingest_hardlink_falls_back_to_copy(tmp_project_dir: Path, tmp_path: Path) -> None:
        payload = b"pixeldata" * 500
        src = _write_fixture(tmp_path, "frame.jpg", payload)
        with patch("nyrahost.attachments.os.link", side_effect=OSError("cross-device")):
            ref = ingest_attachment(src, project_saved=tmp_project_dir / "Saved")
        # Even with link failing, copy succeeds and sha256 matches
        assert ref.sha256 == hashlib.sha256(payload).hexdigest()
        assert Path(ref.path).exists()
        assert ref.kind == "image"


    def test_accepted_extensions_coverage() -> None:
        # Sanity: each kind has at least one ext and they don't collide
        all_exts: set[str] = set()
        for k, exts in ALLOWED_EXTENSIONS.items():
            assert exts, f"Kind {k!r} has no allowed extensions"
            assert all_exts.isdisjoint(exts), f"Overlapping extensions for {k!r}"
            all_exts |= exts
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "def ingest_attachment" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/attachments.py` equals 1
      - `grep -c "os.link(src_path, dest)" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/attachments.py` equals 1
      - `grep -c "shutil.copy2(src_path, dest)" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/attachments.py` equals 1
      - `grep -c "hashlib.sha256()" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/attachments.py` equals 1
      - `grep -c "ALLOWED_EXTENSIONS" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/attachments.py` >= 2
      - `pytest TestProject/Plugins/NYRA/Source/NyraHost/tests/test_attachments.py -v` exits 0 with 5 tests passing
    </automated>
  </verify>
  <acceptance_criteria>
    - attachments.py contains literal text `class AttachmentRef` (dataclass with fields `sha256`, `path`, `size_bytes`, `kind`, `original_filename`)
    - attachments.py contains literal text `def ingest_attachment(src_path: Path, *, project_saved: Path) -> AttachmentRef:`
    - attachments.py contains `ALLOWED_EXTENSIONS` dict with keys `"image"`, `"video"`, `"text"` (matching CD-04 types)
    - attachments.py hardlinks via `os.link` with `shutil.copy2` fallback in OSError
    - attachments.py computes SHA256 in 1 MB chunks via `hashlib.sha256()`
    - test_attachments.py contains `def test_ingest_hardlink_and_sha256` (NOT skipped)
    - test_attachments.py contains `def test_ingest_dedup`
    - test_attachments.py contains `def test_ingest_unsupported_kind`
    - test_attachments.py contains `def test_ingest_hardlink_falls_back_to_copy`
    - test_attachments.py contains `def test_accepted_extensions_coverage`
    - `pytest tests/test_attachments.py -v` exits 0 with 5 tests passing
  </acceptance_criteria>
  <done>Attachments ingested content-addressed; dedup free; fallback verified; CHAT-01 attachment flow ready.</done>
</task>

</tasks>

<verification>
From TestProject/Plugins/NYRA/Source/NyraHost/:
```
pytest tests/test_storage.py tests/test_attachments.py -v
```
Must exit 0 with 9 tests passing total (4 storage + 5 attachments).
</verification>

<success_criteria>
- storage.py implements schema v1 + Storage class with conversations/messages/attachments CRUD
- attachments.py implements content-addressed ingestion with hardlink-or-copy
- 9 pytest tests green
- Both files importable from the nyrahost package
</success_criteria>

<output>
After completion, create `.planning/phases/01-plugin-shell-three-process-ipc/01-07-SUMMARY.md`
listing: DB path convention, schema v1 tables/indexes/constraints, allowed
attachment extensions, hardlink fallback behaviour.
</output>
