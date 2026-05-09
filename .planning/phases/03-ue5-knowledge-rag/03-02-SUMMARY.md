# Plan 03-02 Summary: RAG Retrieval Pipeline (NyraHost MCP Tool)

**Phase:** 03-ue5-knowledge-rag
**Plan:** 03-02
**Type:** execute / TDD
**Wave:** 1
**Autonomous:** true | **TDD:** true
**Depends on:** [01]
**Blocking precondition:** Plan 03-01 bootstrap index must exist

## Objectives

Expose `nyra_retrieve_knowledge` as a first-class MCP tool in NyraHost — the retrieval engine for every knowledge question NYRA answers. This is the pipe between the LanceDB index and the AI model.

## What Was Built

### MCP Tool: `nyra_retrieve_knowledge`

```python
from mcp.server import MCPServer
from nyra_host.rag.retriever import KnowledgeRetriever

retriever = KnowledgeRetriever(lancedb_path="...")

@MCPServer.tool(name="nyra_retrieve_knowledge")
def nyra_retrieve_knowledge(
    query: str,                    # Natural language question
    ue_version_hint: str = None,   # Optional: "5.6" — filters results
    chunk_types: list[str] = None, # Optional: ["api_doc", "cpp_header"]
    top_k: int = 5,               # Default 5 chunks
) -> list[dict]:
    """
    Retrieve UE5 knowledge chunks relevant to the query.
    Returns version-tagged verbatim-quote citations.
    """
    chunks = retriever.retrieve(
        query=query,
        version_filter=ue_version_hint,
        type_filter=chunk_types,
        k=top_k,
    )
    return [
        {
            "chunk_id": c["chunk_id"],
            "content": c["content"],
            "source_url": c["source_url"],
            "ue_version": c["ue_version"],
            "chunk_type": c["chunk_type"],
            "heading": c["heading"],
            "relevance_score": c["score"],
            "citation": format_citation(c),
        }
        for c in chunks
    ]

def format_citation(chunk: dict) -> str:
    """Produces: [source](URL) — UE {version} — {type}: "...verbatim..." """
    return (
        f"[{chunk['heading'] or 'UE docs'}]({chunk['source_url']})"
        f" — UE {chunk['ue_version']} — {chunk['chunk_type']}:"
        f'\n> "{chunk["content"][:300]}{"..." if len(chunk["content"]) > 300 else ""}"'
    )
```

### Citation Format (KNOW-02 verbatim requirement)

Every answer from the RAG pipeline includes a `citation` field with:
1. Source title + URL (hyperlinked)
2. UE version tag (e.g., "UE 5.6")
3. Chunk type (api_doc | cpp_header | etc.)
4. Verbatim excerpt from the chunk (minimum 100 chars or full chunk if shorter)

### Retriever Implementation

```python
class KnowledgeRetriever:
    def __init__(self, lancedb_path: str):
        self.db = lancedb.connect(lancedb_path)
        self.tbl = self.db.open_table("chunks")

    def retrieve(
        self, query: str, version_filter: str = None,
        type_filter: list[str] = None, k: int = 5,
    ) -> list[dict]:
        # Generate query embedding
        from nyra_host.embeddings import get_embedding
        query_vec = get_embedding(query)  # BGE-small-en-v1.5 ONNX

        # Build filter
        where = []
        if version_filter:
            where.append(f'ue_version IN ["{version_filter}", "common"]')
        if type_filter:
            types = '", "'.join(type_filter)
            where.append(f'chunk_type IN ("{types}")')

        # Vector search + optional filters
        results = (
            self.tbl
            .search(query_vec, vector_column_name="embedding")
            .where(" AND ".join(where) if where else None)
            .limit(k)
            .to_list()
        )
        return results
```

### Two-Tier Index Loading

```python
def load_index(ue_version: str) -> lancedb.LanceDB:
    """Try full index first, fall back to bootstrap."""
    local_path = Path(os.environ["LOCALAPPDATA"]) / "NYRA" / "knowledge"
    full_index = local_path / f"NyraIndex_{ue_version.replace('.','')}.lance"
    if full_index.exists():
        return lancedb.connect(str(full_index))
    # Fall back to bootstrap (ships in plugin Content/)
    bootstrap = Path(__file__).parent / "bootstrap.lance"
    return lancedb.connect(str(bootstrap))
```

## Tests

- `tests/test_rag_retrieval.py` — Top-5 retrieval, version filter, citation format
- `tests/test_retriever_version_filter.py` — Filter by UE version
- `tests/test_citation_format.py` — Verbatim excerpt correctness
- `Nyra.RAG.It blocks` — Integration test for MCP tool roundtrip

## Files Created

| File | Purpose |
|------|---------|
| `NyraHost/nyra_host/rag/retriever.py` | KnowledgeRetriever class |
| `NyraHost/nyra_host/rag/__init__.py` | Package init + MCP tool registration |
| `NyraHost/nyra_host/embeddings.py` | BGE-small-en-v1.5 ONNX embedding wrapper |
| `NyraHost/tests/test_rag_retrieval.py` | Retrieval tests |
| `NyraHost/tests/test_citation_format.py` | Citation format tests |

## Module-Superset Discipline

Existing NyraHost MCP server infrastructure (from Phase 1-2) not modified. `nyra_host/rag/` is a new sub-package.

## Next Steps

- Plan 03-03 builds UHT symbol manifest parser for Plan 03-04 pre-execution gate
- Plan 03-06 uses this retriever as input to Gemma offline Q&A