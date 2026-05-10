"""Phase 3 BM25 index tests — round-trip persistence + retrieval ranking."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nyrahost.knowledge import KnowledgeChunk, KnowledgeIndex, ingest_directory
from nyrahost.knowledge.index import _split_markdown, _tokenize


class TestTokenizer:
    def test_lowercases_and_strips_punctuation(self):
        assert _tokenize("Hello, World!") == ["hello", "world"]

    def test_drops_stopwords(self):
        assert _tokenize("the quick brown fox") == ["quick", "brown", "fox"]

    def test_keeps_underscored_identifiers(self):
        # snake_case identifiers (UE Python API) should survive intact
        assert "spawn_actor" in _tokenize("call spawn_actor with params")


class TestMarkdownChunking:
    def test_splits_on_h1_h2_h3(self):
        md = """# Top
intro line

## Section A
body A

### Subsection
deeper

## Section B
body B
"""
        chunks = _split_markdown(md)
        # Expect: Top, A, Subsection, B (4 chunks)
        assert len(chunks) == 4
        # Heading paths reflect nesting
        paths = [tuple(p) for p, _ in chunks]
        assert ("Top",) in paths
        assert ("Top", "Section A") in paths
        assert ("Top", "Section A", "Subsection") in paths
        assert ("Top", "Section B") in paths

    def test_no_headings_returns_single_chunk(self):
        chunks = _split_markdown("just some flat text without headings")
        assert len(chunks) == 1
        assert chunks[0][0] == []


class TestIndexRetrieval:
    @pytest.fixture
    def sample_chunks(self) -> list[KnowledgeChunk]:
        return [
            KnowledgeChunk(
                chunk_id="actor.md#0",
                source_path="actor.md",
                heading_path=["Actors"],
                body="Spawn actor in the level using SpawnActor on the editor world.",
                n_tokens=12,
            ),
            KnowledgeChunk(
                chunk_id="material.md#0",
                source_path="material.md",
                heading_path=["Materials"],
                body="Create a Material Instance Constant via UMaterialInstanceConstant.",
                n_tokens=8,
            ),
            KnowledgeChunk(
                chunk_id="sequencer.md#0",
                source_path="sequencer.md",
                heading_path=["Sequencer", "Tracks"],
                body="Bind an actor to a track in Sequencer using AddPossessable on the LevelSequence.",
                n_tokens=14,
            ),
        ]

    def test_actor_query_finds_actor_chunk_first(self, sample_chunks):
        idx = KnowledgeIndex.from_chunks(sample_chunks)
        hits = idx.search("how do I spawn actor", k=3, min_score=0.0)
        assert hits, "expected at least one hit"
        top = hits[0][0]
        assert top.source_path == "actor.md"

    def test_material_query_finds_material_chunk_first(self, sample_chunks):
        idx = KnowledgeIndex.from_chunks(sample_chunks)
        hits = idx.search("material instance create", k=3, min_score=0.0)
        assert hits
        assert hits[0][0].source_path == "material.md"

    def test_empty_query_returns_empty(self, sample_chunks):
        idx = KnowledgeIndex.from_chunks(sample_chunks)
        assert idx.search("", k=3) == []

    def test_min_score_filters_weak_hits(self, sample_chunks):
        idx = KnowledgeIndex.from_chunks(sample_chunks)
        hits = idx.search("xyz unrelated query", k=3, min_score=10.0)
        assert hits == []


class TestPersistence:
    def test_round_trip_preserves_search_results(self, tmp_path: Path):
        chunks = [
            KnowledgeChunk(
                chunk_id="a#0",
                source_path="a.md",
                heading_path=["A"],
                body="lighting setup with ExponentialHeightFog and SkyAtmosphere",
                n_tokens=8,
            ),
            KnowledgeChunk(
                chunk_id="b#0",
                source_path="b.md",
                heading_path=["B"],
                body="blueprint compile errors and how to debug them",
                n_tokens=8,
            ),
        ]
        idx = KnowledgeIndex.from_chunks(chunks)
        out = tmp_path / "test.json"
        idx.save(out)

        loaded = KnowledgeIndex.load(out)
        hits_orig = idx.search("lighting fog", min_score=0.0)
        hits_loaded = loaded.search("lighting fog", min_score=0.0)
        assert [h[0].chunk_id for h in hits_orig] == [
            h[0].chunk_id for h in hits_loaded
        ]

    def test_unknown_schema_version_rejected(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text(
            json.dumps(
                {
                    "schema_version": 999,
                    "k1": 1.2,
                    "b": 0.75,
                    "avgdl": 0,
                    "idf": {},
                    "doc_freqs": [],
                    "chunks": [],
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="schema_version"):
            KnowledgeIndex.load(bad)


class TestIngestDirectory:
    def test_walks_md_files_and_chunks(self, tmp_path: Path):
        (tmp_path / "page1.md").write_text(
            "# Page 1\n\n## Section\n\nbody here\n", encoding="utf-8"
        )
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "page2.md").write_text(
            "# Page 2\n\nbody two\n", encoding="utf-8"
        )
        (tmp_path / "ignored.txt").write_text("ignored", encoding="utf-8")

        chunks = ingest_directory(tmp_path)
        sources = {c.source_path for c in chunks}
        assert "page1.md" in sources
        assert "subdir/page2.md" in sources
        assert "ignored.txt" not in sources

    def test_missing_dir_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            ingest_directory(tmp_path / "does-not-exist")
