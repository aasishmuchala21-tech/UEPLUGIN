"""Chat export tests — Markdown / JSON dump shapes + privacy guarantees."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nyrahost.chat_export import (
    ChatExportResult,
    export_all_conversations,
    export_conversation_json,
    export_conversation_markdown,
)
from nyrahost.storage import Storage, db_path_for_project


@pytest.fixture
def storage(tmp_path: Path) -> Storage:
    db = db_path_for_project(tmp_path)
    s = Storage(db)
    s.bootstrap()
    return s


def _seed_conversation(
    storage: Storage,
    *,
    title: str = "Test Convo",
    messages: list[tuple[str, str]] | None = None,
) -> str:
    convo = storage.upsert_conversation("conv-001", title=title)
    msgs = messages or [
        ("user", "Hello"),
        ("assistant", "Hi back"),
        ("user", "Spawn a cube"),
    ]
    for role, content in msgs:
        storage.append_message(
            conversation_id=convo.id,
            role=role,
            content=content,
        )
    return convo.id


class TestMarkdownExport:
    def test_writes_file_with_title_and_messages(
        self, storage: Storage, tmp_path: Path
    ):
        cid = _seed_conversation(storage, title="My Test")
        out = tmp_path / "exports"
        result = export_conversation_markdown(storage, cid, out)

        assert isinstance(result, ChatExportResult)
        assert result.markdown_path.exists()
        assert result.message_count == 3
        body = result.markdown_path.read_text(encoding="utf-8")
        assert "My Test" in body
        assert "## #1 — user" in body
        assert "Hello" in body
        assert "## #2 — assistant" in body
        assert "Spawn a cube" in body

    def test_unknown_conversation_raises(
        self, storage: Storage, tmp_path: Path
    ):
        with pytest.raises(ValueError, match="unknown conversation_id"):
            export_conversation_markdown(storage, "missing", tmp_path)

    def test_filename_is_filesystem_safe(
        self, storage: Storage, tmp_path: Path
    ):
        cid = _seed_conversation(
            storage, title='evil/path\\with:colons*and"quotes'
        )
        result = export_conversation_markdown(storage, cid, tmp_path)
        # The filename should not contain any of the bad chars
        for bad in ["/", "\\", ":", "*", '"']:
            assert bad not in result.markdown_path.name

    def test_empty_message_renders_placeholder(
        self, storage: Storage, tmp_path: Path
    ):
        cid = _seed_conversation(
            storage,
            messages=[("user", ""), ("assistant", "Got it")],
        )
        result = export_conversation_markdown(storage, cid, tmp_path)
        body = result.markdown_path.read_text(encoding="utf-8")
        assert "_(empty)_" in body

    def test_attachments_are_summarised_not_inlined(
        self, storage: Storage, tmp_path: Path
    ):
        # Privacy guarantee: PDF bytes don't leak into the export.
        convo = storage.upsert_conversation("c-att", title="With Attach")
        msg = storage.append_message(
            conversation_id=convo.id, role="user", content="See PDF"
        )
        storage.link_attachment(
            message_id=msg.id,
            kind="document",
            path="C:/secret/confidential.pdf",
            size_bytes=12345,
            sha256="deadbeef" * 8,
        )
        result = export_conversation_markdown(storage, convo.id, tmp_path)
        body = result.markdown_path.read_text(encoding="utf-8")
        # Path is included (already on user's disk), but no bytes are inlined
        assert "confidential.pdf" in body
        assert "12345 bytes" in body
        # Truncated sha (privacy: don't expose full sha which could be a key)
        assert "deadbeef…" not in body  # we use ellipsis after first 12 chars
        assert "deadbeefdead…" in body
        assert result.attachment_count == 1

    def test_usage_and_error_json_are_pretty_printed(
        self, storage: Storage, tmp_path: Path
    ):
        convo = storage.upsert_conversation("c-jsu", title="Usage")
        storage.append_message(
            conversation_id=convo.id,
            role="assistant",
            content="ok",
            usage_json=json.dumps({"input_tokens": 100, "output_tokens": 50}),
            error_json=json.dumps({"code": -32001, "message": "timeout"}),
        )
        result = export_conversation_markdown(storage, convo.id, tmp_path)
        body = result.markdown_path.read_text(encoding="utf-8")
        assert "**usage:**" in body
        assert "input_tokens" in body
        assert "**error:**" in body
        assert "timeout" in body


class TestJsonExport:
    def test_schema_v1_round_trips(
        self, storage: Storage, tmp_path: Path
    ):
        cid = _seed_conversation(storage)
        result = export_conversation_json(storage, cid, tmp_path)

        payload = json.loads(result.json_path.read_text(encoding="utf-8"))
        assert payload["schema_version"] == 1
        assert "exported_at_ms" in payload
        assert payload["conversation"]["id"] == cid
        assert len(payload["messages"]) == 3
        assert payload["messages"][0]["role"] == "user"
        assert payload["messages"][0]["content"] == "Hello"

    def test_unknown_conversation_raises(
        self, storage: Storage, tmp_path: Path
    ):
        with pytest.raises(ValueError, match="unknown conversation_id"):
            export_conversation_json(storage, "ghost", tmp_path)

    def test_attachment_metadata_in_payload(
        self, storage: Storage, tmp_path: Path
    ):
        convo = storage.upsert_conversation("ja", title="With Attach")
        msg = storage.append_message(
            conversation_id=convo.id, role="user", content="See"
        )
        storage.link_attachment(
            message_id=msg.id,
            kind="image",
            path="/tmp/a.png",
            size_bytes=1024,
            sha256="cafebabe",
        )
        result = export_conversation_json(storage, convo.id, tmp_path)
        payload = json.loads(result.json_path.read_text(encoding="utf-8"))
        atts = payload["messages"][0]["attachments"]
        assert len(atts) == 1
        assert atts[0]["kind"] == "image"
        assert atts[0]["path"] == "/tmp/a.png"


class TestExportAll:
    def test_walks_all_conversations(
        self, storage: Storage, tmp_path: Path
    ):
        # Seed three different conversations
        for i in range(3):
            convo = storage.upsert_conversation(f"c-{i}", title=f"T{i}")
            storage.append_message(
                conversation_id=convo.id, role="user", content=f"hello {i}"
            )
        results = export_all_conversations(storage, tmp_path)
        assert len(results) == 3
        # Each got both Markdown and JSON
        md_files = list(tmp_path.glob("*.md"))
        json_files = list(tmp_path.glob("*.json"))
        assert len(md_files) == 3
        assert len(json_files) == 3

    def test_limit_caps_count(self, storage: Storage, tmp_path: Path):
        for i in range(5):
            convo = storage.upsert_conversation(f"l-{i}", title=f"L{i}")
            storage.append_message(
                conversation_id=convo.id, role="user", content="x"
            )
        results = export_all_conversations(storage, tmp_path, limit=2)
        assert len(results) == 2
