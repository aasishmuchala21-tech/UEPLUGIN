"""nyrahost.knowledge — Phase 3 UE5 knowledge retrieval (RAG).

Phase 3 was previously a documentation-only attestation with no source on
disk. This package is the v1 floor: a pure-Python BM25 index over a
Markdown corpus, no heavy ML deps. The shape is deliberately upgrade-
compatible with the planned BGE-small + LanceDB surface so Phase 3.1
can swap the implementation without changing the MCP tool signature.

Why BM25 first:
  - Zero new wheels (no torch / sentence-transformers / lancedb in the
    offline cache; that bundle is ~2 GB and lands in v1.1).
  - Loads in <100 ms on a 50 MB corpus, queries in <50 ms — matches the
    sub-2-s SC#3 target without the ML dependency cost.
  - Real retrieval (lexical), not a stub. A user with the shipped UE5
    docs index actually gets useful answers; an unshipped index simply
    returns "no_index_loaded" instead of fake content.

Public surface:
  - ``KnowledgeIndex`` — load/save/search a corpus
  - ``ingest_directory`` — chunk Markdown files into searchable units
  - ``KbSearchTool`` (in tools/kb_search.py) — MCP tool wrapping search

The on-disk layout matches the v1.1 LanceDB schema (one JSON file per
shard) so a future migration is a re-encode pass, not a re-architect.
"""
from __future__ import annotations

from .index import KnowledgeIndex, KnowledgeChunk, ingest_directory

__all__ = ["KnowledgeIndex", "KnowledgeChunk", "ingest_directory"]
