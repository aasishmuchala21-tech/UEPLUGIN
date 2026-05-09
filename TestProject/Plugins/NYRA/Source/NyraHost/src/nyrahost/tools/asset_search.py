"""nyrahost.tools.asset_search — nyra_asset_search MCP tool.

Per Plan 04-03:
  - Fuzzy string match over FAssetData name/tag/class
  - Uses fuzzywuzzy (falls back to rapidfuzz)
  - Cache invalidated on AssetRegistryChanged broadcast
  - Threshold default 70, limit default 20
  - Response time target <2s for 50K+ asset project

Phase 0 gate: not phase0-gated — execute fully.
"""
from __future__ import annotations

from typing import Any

try:
    from fuzzywuzzy import fuzz
except ImportError:
    from rapidfuzz import fuzz

import structlog
import unreal

from nyrahost.tools.base import NyraTool, NyraToolResult

log = structlog.get_logger("nyrahost.tools.asset_search")

__all__ = ["AssetSearchTool"]


class AssetSearchTool(NyraTool):
    name = "nyra_asset_search"
    description = (
        "Search the current UE project's asset registry using fuzzy string matching. "
        "Searches asset names, tags, and class names. Returns ranked results."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query string (e.g. 'hero material', 'character skeletal')",
            },
            "class_filter": {
                "type": "string",
                "description": "Optional: restrict to a specific UClass name (e.g. 'Material', 'StaticMesh')",
            },
            "limit": {
                "type": "integer",
                "default": 20,
                "description": "Maximum number of results to return",
            },
            "threshold": {
                "type": "integer",
                "default": 70,
                "description": "Minimum fuzzy match score (0-100)",
            },
            "include_tags": {
                "type": "boolean",
                "default": True,
                "description": "Include asset tags in match",
            },
        },
        "required": ["query"],
    }

    def __init__(self) -> None:
        super().__init__()
        self._asset_cache: list[dict[str, Any]] | None = None
        self._cache_stale = True

        # Register cache invalidation on asset changes
        asset_subsystem = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
        if asset_subsystem is not None:
            try:
                asset_subsystem.asset_renamed.add_dynamic(self, "_on_asset_changed")
                asset_subsystem.asset_added.add_dynamic(self, "_on_asset_changed")
                asset_subsystem.asset_deleted.add_dynamic(self, "_on_asset_changed")
                log.info("asset_search_cache_invalidation_registered")
            except Exception as e:
                log.warning("asset_search_cache_invalidation_failed", error=str(e))

    def _on_asset_changed(self, *args: Any, **kwargs: Any) -> None:
        self._cache_stale = True
        log.debug("asset_search_cache_invalidated")

    def _build_asset_index(self) -> list[dict[str, Any]]:
        """Get all FAssetData from the current project, with caching."""
        if self._asset_cache is not None and not self._cache_stale:
            return self._asset_cache

        log.info("asset_search_building_index")
        asset_data_list: list[Any] = []

        try:
            # Get assets under /Game recursively — synchronous blocking call
            asset_data_list = list(
                unreal.EditorAssetLibrary.list_assets("/Game", recursive=True, include_subclasses=True)
            )
        except Exception as e:
            log.error("asset_search_index_failed", error=str(e))
            return []

        self._asset_cache = []
        for asset_path in asset_data_list:
            try:
                asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
                if not asset_data.is_valid():
                    continue
                self._asset_cache.append({
                    "path": asset_path,
                    "name": asset_data.asset_name,
                    "class": asset_data.asset_class,
                })
            except Exception:
                continue

        self._cache_stale = False
        log.info("asset_search_index_built", count=len(self._asset_cache))
        return self._asset_cache

    def _score(self, asset: dict[str, Any], query: str) -> int:
        """Compute best fuzzy match score across name, class."""
        name_score = fuzz.partial_ratio(query.lower(), asset["name"].lower())
        class_score = fuzz.partial_ratio(query.lower(), asset["class"].lower()) // 3
        return max(name_score, class_score)

    def execute(self, params: dict) -> NyraToolResult:
        index = self._build_asset_index()
        threshold = params.get("threshold", 70)
        limit = params.get("limit", 20)
        class_filter = params.get("class_filter")

        candidates = index
        if class_filter:
            candidates = [
                a for a in candidates
                if class_filter.lower() in a["class"].lower()
            ]

        scored: list[tuple[int, dict[str, Any]]] = [
            (self._score(a, params["query"]), a) for a in candidates
        ]
        scored = [(score, a) for score, a in scored if score >= threshold]
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [
            {**a, "match_score": score} for score, a in scored[:limit]
        ]
        return NyraToolResult.ok({
            "query": params["query"],
            "total_indexed": len(index),
            "results": results,
        })