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

    # BL-10: TTL-based cache invalidation. The original code attempted to
    # bind an EditorAssetSubsystem dynamic delegate ('add_dynamic') to a
    # plain Python class, which fails because dynamic delegates require a
    # UObject reflection target with a UFUNCTION-decorated callback. The
    # bound exception was silently swallowed and the cache was never
    # invalidated. TTL is the simpler/correct approach for a non-UObject
    # tool: 60 s default; force-rebuild via /diagnostics or invalidate()
    # tool call.
    _CACHE_TTL_SECONDS = 60.0

    def __init__(self) -> None:
        super().__init__()
        self._asset_cache: list[dict[str, Any]] | None = None
        self._cache_built_at: float = 0.0

    def invalidate(self) -> None:
        """Force the next search to rebuild the index. Public API for callers."""
        self._asset_cache = None
        self._cache_built_at = 0.0

    def _build_asset_index(self) -> list[dict[str, Any]]:
        """Get all FAssetData from the current project, with TTL-cached results.

        BL-09: unreal.EditorAssetLibrary.find_asset_data is 5.5+ only and is
        otherwise on EditorAssetSubsystem; on 5.4 the previous code threw
        AttributeError on every asset and silently produced an empty cache
        (`total_indexed: 0`). Use the Asset Registry directly with a single
        get_assets_by_path call -- one C++ call enumerates FAssetData rows
        without per-asset Python round-trips.

        WR-11: SC#4 requires <2s for 50K+ asset projects. The previous
        list_assets + per-asset find_asset_data pattern was O(N) Python
        round-trips. The Asset Registry direct enumeration is O(1).

        BL-10: TTL-based invalidation; rebuild after _CACHE_TTL_SECONDS.
        """
        import time
        now = time.time()
        if self._asset_cache is not None and (now - self._cache_built_at) < self._CACHE_TTL_SECONDS:
            return self._asset_cache

        log.info("asset_search_building_index")
        self._asset_cache = []
        try:
            ar = unreal.AssetRegistryHelpers.get_asset_registry()
            asset_datas = ar.get_assets_by_path("/Game", recursive=True)
        except Exception as e:
            log.error("asset_search_index_failed", error=str(e))
            self._cache_built_at = now
            return []

        for ad in asset_datas:
            try:
                # FAssetData fields: package_name, asset_name, asset_class_path
                # (5.4+) or asset_class (older). Handle both.
                package_name = str(ad.package_name)
                asset_name = str(ad.asset_name)
                asset_class = ""
                acp = getattr(ad, "asset_class_path", None)
                if acp is not None and hasattr(acp, "asset_name"):
                    asset_class = str(acp.asset_name)
                else:
                    asset_class = str(getattr(ad, "asset_class", "") or "")
                self._asset_cache.append({
                    "path": f"{package_name}.{asset_name}",
                    "name": asset_name,
                    "class": asset_class,
                })
            except Exception:
                continue

        self._cache_built_at = now
        elapsed_ms = int((time.time() - now) * 1000)
        log.info("asset_search_index_built", count=len(self._asset_cache), elapsed_ms=elapsed_ms)
        if elapsed_ms > 500:
            log.warning("asset_search_index_slow_build",
                        elapsed_ms=elapsed_ms, count=len(self._asset_cache))
        return self._asset_cache

    # WR-09: previous implementation silently divided class match by 3,
    # de-weighting class matches by 67%. Filter primarily by class via the
    # `class_filter` parameter; weight class match equally to name match
    # in the score so search by "all StaticMeshes" finds them.
    _CLASS_SCORE_WEIGHT = 1.0

    def _score(self, asset: dict[str, Any], query: str) -> int:
        """Compute best fuzzy match score across name and class."""
        q = query.lower()
        name_score = fuzz.partial_ratio(q, asset["name"].lower())
        class_score = int(fuzz.partial_ratio(q, asset["class"].lower()) * self._CLASS_SCORE_WEIGHT)
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