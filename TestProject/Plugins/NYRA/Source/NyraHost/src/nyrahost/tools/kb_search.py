"""Phase 3 MCP tool — nyra_kb_search.

Surfaces the BM25 KnowledgeIndex (nyrahost.knowledge.index) to the agent.
The index file is loaded on first use and cached on the tool instance;
re-loads happen only via explicit ``invalidate()`` (Phase 3.1 will hook
this into a /diagnostics command).

Index location resolution order:
  1. ``params.index_path`` (debug override, dev-only)
  2. ``%LOCALAPPDATA%/NYRA/knowledge/ue5-index.json`` (downloaded asset)
  3. Repo-root ``.nyra-index.json`` (offline test fixture)

When no index is found, the tool returns ``status="no_index_loaded"``
with a clear remediation pointing at the downloader command. This is
honest about the v1 floor: shipping the package surface without forcing
a 50 MB download until the user opts in.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import structlog

from nyrahost.knowledge import KnowledgeIndex
from nyrahost.tools.base import NyraTool, NyraToolResult

log = structlog.get_logger("nyrahost.tools.kb_search")

__all__ = ["KbSearchTool"]


def _default_index_paths() -> list[Path]:
    """Return resolution order for the published index file."""
    paths: list[Path] = []
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        paths.append(
            Path(local_appdata) / "NYRA" / "knowledge" / "ue5-index.json"
        )
    paths.append(Path.cwd() / ".nyra-index.json")
    return paths


class KbSearchTool(NyraTool):
    name = "nyra_kb_search"
    description = (
        "Search the bundled UE5 knowledge index for documentation, "
        "tutorials, and forum guidance relevant to a natural-language "
        "query. Returns ranked passages with source paths so Claude can "
        "cite them. Use this BEFORE asking the user about UE behavior — "
        "the index is built from current UE5.x docs and is more reliable "
        "than the model's training cutoff."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural-language query (e.g. 'how do I bind an actor to a Sequencer track')",
            },
            "limit": {
                "type": "integer",
                "default": 6,
                "description": "Max number of passages to return (1..20).",
            },
            "min_score": {
                "type": "number",
                "default": 0.5,
                "description": "Minimum BM25 score to include in results.",
            },
            "index_path": {
                "type": "string",
                "description": "Optional override path to a knowledge index file (dev/test only).",
            },
        },
        "required": ["query"],
    }

    def __init__(self) -> None:
        super().__init__()
        self._cached_index: Optional[KnowledgeIndex] = None
        self._cached_path: Optional[Path] = None

    def invalidate(self) -> None:
        """Drop the cached index so the next call re-loads."""
        self._cached_index = None
        self._cached_path = None

    def _resolve_index_path(self, override: Optional[str]) -> Optional[Path]:
        if override:
            p = Path(override)
            return p if p.is_file() else None
        for candidate in _default_index_paths():
            if candidate.is_file():
                return candidate
        return None

    def _load_index(self, path: Path) -> KnowledgeIndex:
        if self._cached_index is not None and self._cached_path == path:
            return self._cached_index
        idx = KnowledgeIndex.load(path)
        self._cached_index = idx
        self._cached_path = path
        return idx

    def execute(self, params: dict) -> NyraToolResult:
        query = params.get("query", "")
        if not isinstance(query, str) or not query.strip():
            return NyraToolResult.err("query_required")
        if len(query) > 1024:
            return NyraToolResult.err("query_too_long_max_1024")

        limit = max(1, min(20, int(params.get("limit", 6))))
        min_score = float(params.get("min_score", 0.5))
        override = params.get("index_path")

        index_path = self._resolve_index_path(override)
        if index_path is None:
            return NyraToolResult.ok(
                {
                    "status": "no_index_loaded",
                    "results": [],
                    "remediation": (
                        "No UE5 knowledge index found. Open NYRA settings "
                        "and click 'Download UE5 Knowledge Index', or "
                        "place an index JSON at "
                        "%LOCALAPPDATA%/NYRA/knowledge/ue5-index.json."
                    ),
                }
            )

        try:
            idx = self._load_index(index_path)
        except (OSError, ValueError) as exc:
            log.warning(
                "kb_index_load_failed", path=str(index_path), err=str(exc)
            )
            return NyraToolResult.err(f"kb_index_load_failed: {exc}")

        hits = idx.search(query, k=limit, min_score=min_score)
        return NyraToolResult.ok(
            {
                "status": "ok",
                "index_path": str(index_path),
                "indexed_chunks": len(idx.chunks),
                "results": [
                    {
                        "chunk_id": h.chunk_id,
                        "source_path": h.source_path,
                        "heading_path": h.heading_path,
                        "body": h.body,
                        "score": round(score, 4),
                    }
                    for h, score in hits
                ],
            }
        )
