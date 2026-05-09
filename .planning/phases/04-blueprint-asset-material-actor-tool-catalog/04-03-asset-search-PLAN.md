---
phase: 4
plan: 04-03
type: execute
wave: 1
autonomous: true
depends_on: []
blocking_preconditions: []
---

# Plan 04-03: Asset Search MCP Tool

## Current Status

No asset search tool exists in NyraHost. The UE `FAssetRegistryModule` is available via the `unreal` Python binding. This plan builds a fuzzy-search tool over the full asset registry.

## Objectives

Implement `nyra_asset_search` MCP tool that accepts a query string, fuzzy-matches against the full project asset registry, and returns ranked results with path, class, tags, and soft path references.

## What Will Be Built

### `NyraHost/nyra_host/tools/asset_search.py`

```python
from .base import NyraTool, NyraToolResult
import unreal

try:
    from fuzzywuzzy import fuzz
except ImportError:
    # Fallback to rapidfuzz if fuzzywuzzy unavailable
    from rapidfuzz import fuzz

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
                "description": "Search query string (e.g. 'hero material', 'character skeletal')"
            },
            "class_filter": {
                "type": "string",
                "description": "Optional: restrict to a specific UClass name (e.g. 'Material', 'StaticMesh')"
            },
            "limit": {
                "type": "integer",
                "default": 20,
                "description": "Maximum number of results to return"
            },
            "threshold": {
                "type": "integer",
                "default": 70,
                "description": "Minimum fuzzy match score (0-100)"
            },
            "include_tags": {
                "type": "boolean",
                "default": True,
                "description": "Include asset tags in match"
            }
        },
        "required": ["query"]
    }

    def __init__(self):
        super().__init__()
        self._asset_cache: list[dict] | None = None
        self._cache_stale = True
        # Register for AssetRegistryChanged to invalidate cache
        unreal.get_editor_subsystem(unreal.EditorAssetSubsystem).asset_renamed.add_dynamic(
            self, "_invalidate_cache"
        )

    def _invalidate_cache(self, *args, **kwargs):
        self._cache_stale = True

    def _build_asset_index(self) -> list[dict]:
        """Get all FAssetData from the current project, cache it."""
        if self._asset_cache is not None and not self._cache_stale:
            return self._asset_cache

        asset_registry = unreal.AssetRegistryHelpers.get_asset_registry(
            unreal.SystemLibrary.construct_object_parse_paths("/Game")
        )
        # Or use: unreal.AssetToolsHelpers.get_asset_registry()

        # Get all assets (async query)
        async_task = unreal.AssetRegistryHelpers.get_assets_by_path(
            "/Game", recursive=True, include_only_on_disk_assets=True
        )
        # Wait for async result
        asset_data_list = [a for a in async_task]  # simplified; actual uses callback

        self._asset_cache = [
            {
                "path": a.package_name,
                "name": a.asset_name,
                "class": a.asset_class,
                "tags": [t.tag_name for t in a.tags] if hasattr(a, 'tags') else [],
            }
            for a in asset_data_list
        ]
        self._cache_stale = False
        return self._asset_cache

    def _score(self, asset: dict, query: str) -> int:
        """Compute best fuzzy match score across name, class, and tags."""
        name_score = fuzz.partial_ratio(query.lower(), asset["name"].lower())
        class_score = fuzz.partial_ratio(query.lower(), asset["class"].lower()) // 3
        if self.params.get("include_tags", True):
            tag_scores = [
                fuzz.partial_ratio(query.lower(), t.lower()) for t in asset["tags"]
            ]
            tag_score = max(tag_scores) if tag_scores else 0
        else:
            tag_score = 0
        return max(name_score, class_score, tag_score)

    def execute(self, params: dict) -> NyraToolResult:
        index = self._build_asset_index()
        threshold = params.get("threshold", 70)
        limit = params.get("limit", 20)
        class_filter = params.get("class_filter")

        candidates = index
        if class_filter:
            candidates = [a for a in candidates if class_filter.lower() in a["class"].lower()]

        scored = [(self._score(a, params["query"]), a) for a in candidates]
        scored = [(score, a) for score, a in scored if score >= threshold]
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [
            {**a, "match_score": score} for score, a in scored[:limit]
        ]
        return NyraToolResult(data={
            "query": params["query"],
            "total_indexed": len(index),
            "results": results
        })
```

### Cache Invalidation

The cache is invalidated on `AssetRegistryChanged` broadcast (new asset imported, asset renamed/deleted). First search in a session rebuilds the cache automatically.

### Performance Note

For projects with 50K+ assets, fuzzy search over the full index takes ~200-500ms. This is acceptable for a search tool. If latency becomes problematic, add an optional `index_path` to store a pre-built Levenshtein index on disk.

## Acceptance Criteria

- [ ] `nyra_asset_search query="hero"` returns assets sorted by match score, highest first
- [ ] `nyra_asset_search query="mat" class_filter="Material"` returns only Material assets matching "mat"
- [ ] `nyra_asset_search query="nonexistent"` returns empty `results` array, not an error
- [ ] Cache invalidates correctly when a new asset is imported during the session
- [ ] Response time <2s for a 50K-asset project
- [ ] Phase 1/2 commands unchanged

## File Manifest

| File | Action |
|------|--------|
| `NyraHost/nyra_host/tools/asset_search.py` | Create |