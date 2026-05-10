"""Phase 3 nyra_kb_search MCP tool tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from nyrahost.knowledge import KnowledgeChunk, KnowledgeIndex
from nyrahost.tools.kb_search import KbSearchTool


@pytest.fixture
def sample_index_file(tmp_path: Path) -> Path:
    chunks = [
        KnowledgeChunk(
            chunk_id="ue-actors.md#0",
            source_path="ue-actors.md",
            heading_path=["UE Actors", "Spawning"],
            body="To spawn an actor in the editor, call EditorActorSubsystem.spawn_actor_from_class.",
            n_tokens=12,
        ),
        KnowledgeChunk(
            chunk_id="ue-mats.md#0",
            source_path="ue-mats.md",
            heading_path=["Materials"],
            body="Material Instance Dynamic is created at runtime via CreateDynamicMaterialInstance.",
            n_tokens=10,
        ),
    ]
    idx = KnowledgeIndex.from_chunks(chunks)
    out = tmp_path / "ue5-index.json"
    idx.save(out)
    return out


class TestKbSearchTool:
    def test_no_index_returns_remediation(self, tmp_path: Path, monkeypatch):
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        monkeypatch.chdir(tmp_path)
        tool = KbSearchTool()
        result = tool.execute({"query": "spawn actor"})
        assert result.is_ok
        assert result.data["status"] == "no_index_loaded"
        assert "Download" in result.data["remediation"]

    def test_search_with_override_path(self, sample_index_file: Path):
        tool = KbSearchTool()
        result = tool.execute(
            {
                "query": "how do I spawn an actor",
                "index_path": str(sample_index_file),
                "min_score": 0.0,
            }
        )
        assert result.is_ok
        assert result.data["status"] == "ok"
        assert result.data["indexed_chunks"] == 2
        assert len(result.data["results"]) >= 1
        top = result.data["results"][0]
        assert top["source_path"] == "ue-actors.md"

    def test_empty_query_rejected(self, sample_index_file: Path):
        tool = KbSearchTool()
        result = tool.execute(
            {"query": "", "index_path": str(sample_index_file)}
        )
        assert not result.is_ok
        assert "query_required" in result.error

    def test_oversized_query_rejected(self, sample_index_file: Path):
        tool = KbSearchTool()
        result = tool.execute(
            {
                "query": "x" * 2000,
                "index_path": str(sample_index_file),
            }
        )
        assert not result.is_ok
        assert "query_too_long" in result.error

    def test_caching_avoids_reload(self, sample_index_file: Path):
        tool = KbSearchTool()
        tool.execute(
            {
                "query": "spawn actor",
                "index_path": str(sample_index_file),
                "min_score": 0.0,
            }
        )
        # After first call, the cached index should match the path
        assert tool._cached_path == sample_index_file
        first_idx = tool._cached_index
        # Second call should reuse the same instance
        tool.execute(
            {
                "query": "material instance",
                "index_path": str(sample_index_file),
                "min_score": 0.0,
            }
        )
        assert tool._cached_index is first_idx

    def test_invalidate_drops_cache(self, sample_index_file: Path):
        tool = KbSearchTool()
        tool.execute(
            {
                "query": "spawn",
                "index_path": str(sample_index_file),
                "min_score": 0.0,
            }
        )
        assert tool._cached_index is not None
        tool.invalidate()
        assert tool._cached_index is None
