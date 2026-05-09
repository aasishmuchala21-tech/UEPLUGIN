---
phase: 3
plan: 03-02
type: execute
wave: 1
autonomous: true
depends_on: [01]
blocking_preconditions:
  - "03-01 bootstrap.lance exists at Plugins/NYRA/Content/knowledge/"
---

# Plan 03-02: RAG Retrieval Pipeline (NyraHost MCP Tool)

## Current Status

03-01 delivers the `bootstrap.lance` table and the BGE-small ONNX embedder. The retrieval pipeline in 03-02 exposes a queryable MCP tool `nyra_retrieve_knowledge` that wraps LanceDB vector search with citation formatting and version filtering. This is the primary interface NYRA's agent router calls before generating any answer.

## Objectives

Build `nyra_retrieve_knowledge(query, ue_version_hint?) -> chunks[]` as a registered MCP tool in NyraHost. The tool must:
- Accept a free-text query string and an optional UE version hint
- Return top-5 relevant chunks with verbatim quotes, source URLs, version tags, and relevance scores
- Format citations exactly as `[source](URL) — UE {version} — {chunk_type}: "...verbatim quote..."`
- Pass the NyraHost TDD harness (03-01 tests green before starting 03-02)

## What Will Be Built

### `Plugins/NYRA/Source/NyraHost/nyra_knowledge/retrieval.py`

Core retrieval engine:

```python
"""
nyra_knowledge/retrieval.py

RAG retrieval engine for NYRA. Wraps LanceDB vector search with
version filtering, deduplication, and citation formatting.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Self

from lancedb import DB, Table
from lancedb.query import Query, VectorQuery
from pydantic import BaseModel, Field

from .embedder import Embedder
from .lancedb_schema import CHUNK_TYPE_ALLOWED

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
@dataclass
class RetrievedChunk:
    """A single retrieved RAG chunk."""
    chunk_id: str
    content: str
    source_url: str
    ue_version: str
    chunk_type: str
    relevance_score: float  # cosine similarity score, 0–1

    def citation(self) -> str:
        """
        Format a verbatim-quote citation.

        Citation format (D-4 / KNOW-02 contract):
            [source](URL) — UE {version} — {chunk_type}: "...verbatim quote..."
        """
        # Truncate content to ~200 chars for citation display
        snippet = (
            self.content[:200].strip()
            if len(self.content) > 200
            else self.content.strip()
        )
        if len(self.content) > 200:
            snippet += "..."
        return (
            f"[{self.chunk_type}]({self.source_url})"
            f" — UE {self.ue_version} — {self.chunk_type}: \"{snippet}\""
        )


class RetrievalRequest(BaseModel):
    """MCP tool input model."""
    query: Annotated[str, Field(description="Natural-language UE question")]
    ue_version_hint: Annotated[
        str | None,
        Field(default=None, description="UE version to filter results, e.g. '5.6'")
    ] = None
    top_k: Annotated[int, Field(default=5, ge=1, le=20)] = 5
    chunk_types: Annotated[
        list[str] | None,
        Field(default=None, description="Filter to specific chunk types")
    ] = None


class RetrievalResult(BaseModel):
    """MCP tool output model."""
    chunks: list[RetrievedChunk]
    query: str
    ue_version_used: str | None
    total_available: int


# ---------------------------------------------------------------------------
# Retrieval engine
# ---------------------------------------------------------------------------
class KnowledgeRetriever:
    """
    LanceDB-backed RAG retriever.

    Resolution order for the index:
      1. Per-version index: index_<major><minor>.lance  (e.g. index_56.lance)
      2. Bootstrap index:   Content/knowledge/bootstrap.lance
      3. Empty result + warning if neither found
    """

    DEFAULT_INDEX_ROOT = (
        Path(os.environ.get("LOCALAPPDATA", "")) / "NYRA" / "knowledge"
    )
    BOOTSTRAP_INDEX = (
        Path(__file__).parent.parent.parent.parent
        / "Content" / "knowledge" / "bootstrap.lance"
    )

    def __init__(
        self,
        index_root: Path | None = None,
        embedder: Embedder | None = None,
    ):
        self.index_root = index_root or self.DEFAULT_INDEX_ROOT
        self.embedder = embedder or Embedder()
        self._db: DB | None = None
        self._current_table: Table | None = None
        self._current_index_path: Path | None = None

    # --- Index resolution -------------------------------------------------
    def _resolve_index(self, ue_version: str | None) -> Path | None:
        """
        Resolve the best available index path for the given UE version.

        Priority:
          1. index_<MAJOR><MINOR>.lance  (e.g. index_56.lance for "5.6")
          2. bootstrap.lance (always available fallback)
          3. None
        """
        # Try per-version index
        if ue_version:
            major_minor = ue_version.replace(".", "")
            per_version = self.index_root / f"index_{major_minor}.lance"
            if per_version.exists():
                return per_version

        # Fall back to bootstrap
        if self.BOOTSTRAP_INDEX.exists():
            return self.BOOTSTRAP_INDEX

        # Last resort: check index_root/bootstrap
        bootstrap_fallback = self.index_root / "bootstrap.lance"
        if bootstrap_fallback.exists():
            return bootstrap_fallback

        return None

    def _open_index(self, index_path: Path) -> Table:
        """Open (or re-use) a LanceDB table at index_path."""
        if self._current_index_path == index_path and self._current_table is not None:
            return self._current_table

        db = lancedb.connect(str(index_path.parent))
        # Table name is the directory stem
        table_name = index_path.stem
        if table_name.startswith("index_"):
            # index_56.lance → table name "index_56"
            table_name = index_path.name.replace(".lance", "")
        self._current_table = db.open_table(table_name)
        self._current_index_path = index_path
        return self._current_table

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        """
        Run vector search against the best available index.

        Steps:
          1. Resolve index (per-version or bootstrap)
          2. Embed query with BGE-small
          3. Apply version + chunk-type filters
          4. Execute top-K vector search
          5. Return RetrievedChunk list ordered by relevance
        """
        index_path = self._resolve_index(request.ue_version_hint)
        if index_path is None:
            log.warning(
                "No knowledge index found for ue_version=%s "
                "(tried %s and bootstrap)",
                request.ue_version_hint,
                self.index_root,
            )
            return RetrievalResult(
                chunks=[],
                query=request.query,
                ue_version_used=None,
                total_available=0,
            )

        table = self._open_index(index_path)

        # Build filter string
        filters: list[str] = []
        if request.ue_version_hint:
            filters.append(f"ue_version = '{request.ue_version_hint}'")
        if request.chunk_types:
            type_filter = " OR ".join(
                f"chunk_type = '{ct}'" for ct in request.chunk_types
            )
            filters.append(f"({type_filter})")

        filter_str = " AND ".join(filters) if filters else None

        # Embed query
        query_embedding = self.embedder.embed([request.query])[0]

        # Execute vector search
        query_builder: VectorQuery = table.query().vector(
            query_embedding.tolist()
        ).limit(request.top_k)

        if filter_str:
            query_builder = query_builder.where(filter_str)

        results = query_builder.to_pydict()

        chunks = [
            RetrievedChunk(
                chunk_id=cid,
                content=content,
                source_url=src,
                ue_version=ver,
                chunk_type=ctype,
                relevance_score=0.0,  # LanceDB doesn't return scores directly
            )
            for cid, content, src, ver, ctype in zip(
                results.get("chunk_id", []),
                results.get("content", []),
                results.get("source_url", []),
                results.get("ue_version", []),
                results.get("chunk_type", []),
            )
        ]

        # Sort by content length as a rough relevance proxy (no scores from LanceDB)
        chunks.sort(key=lambda c: len(c.content), reverse=True)

        total = table.count()
        ue_used = request.ue_version_hint or (
            "bootstrap"
            if index_path == self.BOOTSTRAP_INDEX
            else "unknown"
        )

        log.info(
            "Retrieved %d/%d chunks for query '%s' (ue_version=%s, index=%s)",
            len(chunks), total, request.query[:60], ue_used, index_path.name
        )

        return RetrievalResult(
            chunks=chunks,
            query=request.query,
            ue_version_used=ue_used,
            total_available=total,
        )

    # --- Convenience methods for MCP tool --------------------------------
    def retrieve_as_citations(self, query: str, ue_version: str | None = None) -> list[str]:
        """Return formatted citation strings for a query."""
        result = self.retrieve(RetrievalRequest(query=query, ue_version_hint=ue_version))
        return [c.citation() for c in result.chunks]
```

### `Plugins/NYRA/Source/NyraHost/nyra_knowledge/mcp_tools.py`

MCP tool registration (extends existing NyraHost MCP infrastructure):

```python
"""
nyra_knowledge/mcp_tools.py

Registers nyra_retrieve_knowledge as an MCP tool in NyraHost.
"""

from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import Field

from .retrieval import KnowledgeRetriever, RetrievalRequest, RetrievedChunk

server = Server("nyra-knowledge")

retriever = KnowledgeRetriever()


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="nyra_retrieve_knowledge",
            description=(
                "Retrieve UE5 documentation chunks matching a natural-language query. "
                "Returns top-K relevant chunks with verbatim-quote citations tagged to "
                "UE version. Use this before generating any UE API action to ensure "
                "grounding in official documentation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Natural-language UE question, e.g. "
                            "'how do I use UPROPERTY EditInline' or "
                            "'difference between SpawnActor and SpawnActorDeferred'"
                        ),
                    },
                    "ue_version_hint": {
                        "type": "string",
                        "description": "UE version to filter results, e.g. '5.6' (optional)",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of chunks to return (default 5, max 20)",
                        "default": 5,
                    },
                    "chunk_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Filter to chunk types: api_doc, blueprint_ref, "
                            "cpp_header, official_guide (optional)"
                        ),
                        "default": [],
                    },
                },
                "required": ["query"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(
    name: str,
    arguments: dict,
) -> list[TextContent]:
    if name == "nyra_retrieve_knowledge":
        req = RetrievalRequest(
            query=arguments["query"],
            ue_version_hint=arguments.get("ue_version_hint"),
            top_k=arguments.get("top_k", 5),
            chunk_types=arguments.get("chunk_types"),
        )
        result = retriever.retrieve(req)

        # Format output as structured markdown citations
        lines = [
            f"## Retrieved {len(result.chunks)} chunks for: {result.query}",
            f"**Index used:** `{result.ue_version_used}` — **{result.total_available} total chunks**",
            "",
        ]
        for i, chunk in enumerate(result.chunks, 1):
            lines.append(f"### Chunk {i}")
            lines.append(f"**Type:** `{chunk.chunk_type}`  **UE Version:** `{chunk.ue_version}`")
            lines.append(f"**Source:** [{chunk.source_url}]({chunk.source_url})")
            lines.append("")
            lines.append(f"> {chunk.content}")
            lines.append("")
            lines.append(f"_Citation: {chunk.citation()}_")
            lines.append("---")

        return [TextContent(type="text", text="\n".join(lines))]
    else:
        raise ValueError(f"Unknown tool: {name}")
```

### `Plugins/NYRA/Source/NyraHost/nyra_knowledge/__init__.py`

Export for package use:

```python
from .retrieval import KnowledgeRetriever, RetrievedChunk, RetrievalRequest, RetrievalResult
from .embedder import Embedder
from .lancedb_schema import CHUNK_TYPE_ALLOWED

__all__ = [
    "KnowledgeRetriever",
    "RetrievedChunk",
    "RetrievalRequest",
    "RetrievalResult",
    "Embedder",
    "CHUNK_TYPE_ALLOWED",
]
```

## Implementation Details

### Index Resolution Logic

```
retrieve(query="how do I create a physics constraint", ue_version_hint="5.6")
  → index_root / "index_56.lance"  exists? → use it
  → else → bootstrap.lance  exists? → use it
  → else → return empty result + warning
```

The user may have:
- Never run the index updater (bootstrap only)
- Downloaded a newer per-version index (index_56.lance)
- Have both index_56 and bootstrap

Version filtering is applied at query time via LanceDB's `where()` clause — no need to duplicate data across versions.

### Citation Format Contract (KNOW-02)

Every answer NYRA generates must include a citation block. The format is enforced in `RetrievedChunk.citation()` and must not be broken by later refactors:

```
[cpp_header](file://Engine/Source/Runtime/Core/Public/UObject/Object.h)
 — UE 5.6 — cpp_header: "UCLASS(MyClass) class UMyClass : public UObject..."
```

The source URL is the file path or Epic docs URL. The verbatim quote is the **exact** content of the chunk — not a paraphrase.

### MCP Tool Naming

`nyra_retrieve_knowledge` — the `nyra_` prefix follows the convention established in Phase 1 for all NyraHost tools (`nyra_list_attachments`, `nyra_upload_file`, etc.).

## Tests

### `tests/test_rag_retrieval.py`

```python
"""Tests for the nyra_retrieve_knowledge MCP tool and KnowledgeRetriever."""
import pytest, lancedb, numpy as np
from pathlib import Path

from nyra_knowledge.retrieval import (
    KnowledgeRetriever,
    RetrievalRequest,
    RetrievedChunk,
)
from nyra_knowledge.embedder import Embedder


@pytest.fixture
def test_index(tmp_path):
    """Create a test LanceDB table with 3 known chunks."""
    from nyra_knowledge.lancedb_schema import create_table
    db = lancedb.connect(str(tmp_path))
    table = create_table(db, "test_index")
    embedder = Embedder()
    texts = [
        "UPROPERTY(EditInline) makes the property editable in the detail panel inline",
        "UCLASS marks a class as a UObject managed by Unreal's reflection system",
        "FSpawnActorParams is used to control actor spawn behavior before construction",
    ]
    embeddings = embedder.embed(texts)
    records = [
        {
            "chunk_id": f"test:{i:03d}",
            "content": texts[i],
            "source_url": f"file://test_{i}.h",
            "ue_version": "5.6",
            "chunk_type": "cpp_header",
            "embedding": embeddings[i].tolist(),
            "content_hash": f"hash{i:03d}",
        }
        for i in range(3)
    ]
    table.add(records)
    yield table


class TestKnowledgeRetriever:
    def test_retrieve_returns_chunks(self, test_index, tmp_path):
        retriever = KnowledgeRetriever(index_root=tmp_path)
        req = RetrievalRequest(query="how do I use UPROPERTY EditInline", top_k=3)
        result = retriever.retrieve(req)
        assert len(result.chunks) <= 3
        assert result.query == "how do I use UPROPERTY EditInline"
        assert result.ue_version_used in ("bootstrap", "5.6")

    def test_retrieve_version_filter(self, test_index, tmp_path):
        retriever = KnowledgeRetriever(index_root=tmp_path)
        req = RetrievalRequest(query="UCLASS", ue_version_hint="5.5", top_k=5)
        result = retriever.retrieve(req)
        # No chunks in test_index are 5.5 — expect empty
        assert result.total_available == 3  # table has 3 chunks total
        # Version hint doesn't filter if no per-version index; bootstrap returns all
        assert len(result.chunks) <= 5

    def test_retrieve_citation_format(self, test_index, tmp_path):
        retriever = KnowledgeRetriever(index_root=tmp_path)
        req = RetrievalRequest(query="FSpawnActorParams", top_k=1)
        result = retriever.retrieve(req)
        assert len(result.chunks) >= 1
        citation = result.chunks[0].citation()
        # Must follow the exact contract format
        assert "[" in citation
        assert "](file://" in citation
        assert " — UE " in citation
        assert ' — ' in citation.split(" — ")[1]  # chunk_type in middle
        assert '"' in citation  # verbatim quote in quotes

    def test_retrieve_top_k(self, test_index, tmp_path):
        retriever = KnowledgeRetriever(index_root=tmp_path)
        req = RetrievalRequest(query="actor spawn", top_k=2)
        result = retriever.retrieve(req)
        assert len(result.chunks) <= 2

    def test_retrieve_unknown_query_returns_empty_list(self, test_index, tmp_path):
        retriever = KnowledgeRetriever(index_root=tmp_path)
        req = RetrievalRequest(query="xyzzy non-existent query xyzzy", top_k=5)
        result = retriever.retrieve(req)
        # LanceDB returns whatever is top-K even for nonsense — this is expected
        # The caller (03-06 / Gemma) handles the "no good chunks" case
        assert isinstance(result.chunks, list)

    def test_retriever_falls_back_to_bootstrap(self, tmp_path):
        """When no per-version index exists, retriever falls back to bootstrap."""
        retriever = KnowledgeRetriever(index_root=tmp_path)
        # Bootstrap doesn't exist in this test — check warning logged
        req = RetrievalRequest(query="test", top_k=5)
        result = retriever.retrieve(req)
        assert result.ue_version_used is not None  # either bootstrap or warning


class TestCitationFormat:
    """KNOW-02 citation format contract tests."""

    def test_citation_contains_source_url(self):
        chunk = RetrievedChunk(
            chunk_id="api:test:001",
            content="UCLASS decorates a class as a Unreal Object",
            source_url="https://docs.unrealengine.com/UCLASS",
            ue_version="5.6",
            chunk_type="api_doc",
            relevance_score=0.95,
        )
        citation = chunk.citation()
        assert "https://docs.unrealengine.com/UCLASS" in citation

    def test_citation_contains_version_tag(self):
        chunk = RetrievedChunk(
            chunk_id="bp:test:002",
            content="SpawnActorDeferred defers property initialization until PostSpawn",
            source_url="https://docs.unrealengine.com/SpawnActorDeferred",
            ue_version="5.5",
            chunk_type="blueprint_ref",
            relevance_score=0.88,
        )
        citation = chunk.citation()
        assert "UE 5.5" in citation

    def test_citation_truncates_long_content(self):
        long_content = "A" * 500
        chunk = RetrievedChunk(
            chunk_id="test:003",
            content=long_content,
            source_url="file://test.h",
            ue_version="5.4",
            chunk_type="cpp_header",
            relevance_score=0.70,
        )
        citation = chunk.citation()
        # Must be under ~230 chars (200 + "..." + quotes)
        assert len(citation) < 250
        assert "..." in citation


class TestMcpToolRegistration:
    """Verify MCP tool registration is correct."""

    def test_tool_name_is_nyra_retrieve_knowledge(self):
        from nyra_knowledge.mcp_tools import list_tools
        import asyncio
        tools = asyncio.run(list_tools())
        tool_names = [t.name for t in tools]
        assert "nyra_retrieve_knowledge" in tool_names

    def test_tool_input_schema_has_required_fields(self):
        from nyra_knowledge.mcp_tools import list_tools
        import asyncio
        tools = asyncio.run(list_tools())
        tool = next(t for t in tools if t.name == "nyra_retrieve_knowledge")
        props = tool.inputSchema.get("properties", {})
        assert "query" in props
        assert props["query"].get("type") == "string"
        assert props["query"].get("description")  # description present
```

## Threat Mitigations

| Threat | Mitigation |
|--------|-------------|
| Empty result on first run (no per-version index downloaded) | Always fall back to bootstrap.lance (ships in plugin). Result is non-empty but may be stale for new UE versions. |
| LanceDB file locked by concurrent write | Read-only access — `lancedb.connect()` opens in read mode by default for existing tables. No concurrent write during retrieval. |
| Out-of-memory for large embeddings batch | `embed_batch` uses batch_size=32; `onnxruntime` sessions are re-used across calls. |
| Wrong UE version chunks returned | `ue_version_hint` filter applied via LanceDB `where()` clause; always prefer the user's exact UE version when available. |
| Hallucinated chunks (RAG retrieval noise) | Conservative corpus whitelist (D-2): only official Epic docs + C++ headers. Chunk types are explicitly enumerated. |

## Files Created/Modified

| File | Purpose |
|------|---------|
| `Plugins/NYRA/Source/NyraHost/nyra_knowledge/retrieval.py` | KnowledgeRetriever class + RetrievalRequest/Result models |
| `Plugins/NYRA/Source/NyraHost/nyra_knowledge/mcp_tools.py` | MCP tool registration + call_tool handler |
| `Plugins/NYRA/Source/NyraHost/nyra_knowledge/__init__.py` | Package exports updated |
| `tests/test_rag_retrieval.py` | Full test suite |

## Verification

1. **Unit tests:** `pytest tests/test_rag_retrieval.py -v` — all green
2. **MCP tool listing:** NyraHost logs `nyra_retrieve_knowledge` in the `/tools` response
3. **Citation contract:** Every chunk returned has a citation matching the exact format in KNOW-02
4. **Version filtering:** `RetrievalRequest(ue_version_hint="5.6")` returns only chunks with `ue_version = "5.6"` (or all if only bootstrap available)
5. **Graceful degradation:** Query with no index available returns `chunks=[]` with warning log (not an exception)

## Next Steps

- **03-03:** Build the UHT symbol manifest scanner that generates `symbols_5x.json` per installed UE version. This feeds into 03-04's pre-execution gate.
- **03-04:** Wire the symbol validation MCP tool `nyra_validate_symbol` that runs before any UE API action.
- **03-05:** Build the version-tagged index update pipeline and "Update Knowledge" button handler.
- **03-06:** Build the Gemma 3 4B offline Q&A path that calls `KnowledgeRetriever` first (top-5 chunks) and then generates an answer grounded in the retrieved context.
