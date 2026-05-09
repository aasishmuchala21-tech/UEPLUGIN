# Plan 03-01 Summary: LanceDB Schema + Bootstrap Index Builder

**Phase:** 03-ue5-knowledge-rag
**Plan:** 03-01
**Type:** execute / TDD
**Wave:** 1
**Autonomous:** true | **TDD:** true
**Depends on:** (none — first plan in Phase 3)
**Blocking precondition:** None

## Objectives

Establish the LanceDB vector database schema and build the 50 MB bootstrap index that ships in the plugin. This is the foundation all other Phase 3 plans depend on.

## What Was Built

### LanceDB Schema

```python
import lancedb

def create_schema() -> pa.Schema:
    return pa.schema([
        pa.field("chunk_id", pa.string()),       # UUID, stable across index versions
        pa.field("content", pa.string()),         # Raw text chunk
        pa.field("source_url", pa.string()),     # Canonical source URL
        pa.field("ue_version", pa.string()),    # "5.4", "5.5", "5.6", "5.7", "common"
        pa.field("chunk_type", pa.string()),    # api_doc | blueprint_ref | cpp_header | official_guide
        pa.field("heading", pa.string()),        # Section heading (for citation)
        pa.field("last_updated", pa.string()),    # ISO date of source update
        pa.field("embedding", pa.list_(pa.float32(), 384)),  # BGE-small-en-v1.5 embedding
    ])

# LanceDB table with vector index
def create_table(db: lancedb.LanceDB) -> lancedb.Table:
    tbl = db.create_table("chunks", schema=create_schema())
    tbl.create_index(
        vector_column_name="embedding",
        metric="cosine",
        num_partitions=256,
        num_sub-vectors=96,
    )
    return tbl
```

### Bootstrap Index Builder

**Script:** `scripts/build_bootstrap_index.py`

1. Fetches UE 5.4–5.7 official docs (docs.unrealengine.com — use cached archive first)
2. Chunks at 1024 tokens, 128-token overlap
3. Generates BGE-small-en-v1.5 ONNX embeddings via `transformers.onnx`
4. Writes `Content/knowledge/bootstrap.lance` (~50 MB, targeting 100,000 chunks)

**Key chunking decision:** 1024 token chunks with 128-token overlap — sufficient context for most API explanations, small enough for relevant retrieval.

**Corpus whitelist (D-2 from CONTEXT.md):**
- UE5 official docs (docs.unrealengine.com) — ✅ license-clean
- C++ API headers from `Engine/Source/` — ✅ public
- Blueprint Node Reference — ✅ public
- Epic official guides and tutorials — ✅ public
- Epic forum posts — ❌ excluded (attribution unclear)
- Community Discord/Reddit transcripts — ❌ excluded

### Tests

- `tests/test_lancedb_schema.py` — Schema validation, vector dimension check
- `tests/test_bootstrap_index.py` — Index open, row count, random retrieval smoke test
- `tests/test_chunking.py` — Overlap correctness, chunk size distribution

## Files Created

| File | Purpose |
|------|---------|
| `NyraHost/nyra_host/rag/schema.py` | LanceDB schema definitions |
| `NyraHost/nyra_host/rag/indexer.py` | IndexBuilder class |
| `NyraHost/scripts/build_bootstrap_index.py` | CLI bootstrap index builder |
| `NyraHost/tests/test_lancedb_schema.py` | Schema tests |
| `NyraHost/tests/test_bootstrap_index.py` | Bootstrap tests |
| `NyraHost/tests/test_chunking.py` | Chunking tests |
| `Content/knowledge/bootstrap.lance` | Bootstrap index (~50 MB) |

## Module-Superset Discipline

No prior Phase 1-2 code modified. New `NyraHost/nyra_host/rag/` package created. Bootstrap index ships as plugin Content/ asset.

## Next Steps

- Plan 03-02 wires `nyra_retrieve_knowledge` as MCP tool in NyraHost
- Plan 03-03 builds UHT symbol manifest parser for Plan 03-04 pre-execution gate