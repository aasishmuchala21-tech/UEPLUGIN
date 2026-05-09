"""nyrahost.tools.asset_pool - LRU asset resolution cache for Phase 6 assembly.

Prevents duplicate Meshy/ComfyUI imports by tracking resolved assets.
NOT a full asset database - wraps nyra_asset_search with caching.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import structlog

from nyrahost.tools.scene_types import AssetResolutionResult

log = structlog.get_logger("nyrahost.tools.asset_pool")


@dataclass
class PoolEntry:
    """A cached asset resolution result."""
    result: AssetResolutionResult
    resolved_at: str


class AssetPool:
    """LRU cache for asset resolution results.

    Tracks resolved assets by (hint, role) key to prevent duplicate
    searches and generation calls. Max 200 entries, LRU eviction.

    The pool is backed by an on-disk manifest at:
    %LOCALAPPDATA%/NYRA/asset_pool.json

    This allows the pool to survive NyraHost restarts.
    """

    MAX_ENTRIES = 200
    POOL_FILE = "asset_pool.json"

    def __init__(self, pool_root: Optional[Path] = None):
        if pool_root:
            self._root = pool_root
        else:
            import os
            la = os.environ.get("LOCALAPPDATA")
            self._root = Path(la) / "NYRA" if la else Path.home() / ".local" / "share" / "NYRA"
        self._root.mkdir(parents=True, exist_ok=True)
        self._pool_path = self._root / self.POOL_FILE
        self._cache: OrderedDict[str, PoolEntry] = OrderedDict()
        self._load_from_disk()

    def _make_key(self, hint: str, role: str) -> str:
        """Create a deterministic cache key from hint + role."""
        import hashlib
        normalized = f"{hint.lower().strip()}|{role}"
        short = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return short

    def get(self, hint: str, role: str) -> Optional[AssetResolutionResult]:
        """Return cached resolution result if exists, evicting if stale."""
        key = self._make_key(hint, role)
        if key in self._cache:
            self._cache.move_to_end(key)
            self._save_to_disk()
            entry = self._cache[key]
            log.info("asset_pool_hit", key=key, source=entry.result.source, hint=hint, role=role)
            return entry.result
        return None

    def put(self, hint: str, role: str, result: AssetResolutionResult) -> None:
        """Cache a resolution result, evicting LRU entry if at capacity."""
        key = self._make_key(hint, role)
        import datetime
        entry = PoolEntry(
            result=result,
            resolved_at=datetime.datetime.utcnow().isoformat() + "Z"
        )
        self._cache[key] = entry
        self._cache.move_to_end(key)

        while len(self._cache) > self.MAX_ENTRIES:
            evicted_key, evicted_entry = self._cache.popitem(last=False)
            log.info("asset_pool_evicted", key=evicted_key, source=evicted_entry.result.source)

        self._save_to_disk()
        log.info("asset_pool_put", key=key, source=result.source, hint=hint, role=role)

    def clear(self) -> None:
        """Clear the entire cache. Use when user wants a fresh start."""
        self._cache.clear()
        self._save_to_disk()
        log.info("asset_pool_cleared")

    def _load_from_disk(self) -> None:
        """Load cache from asset_pool.json on disk."""
        if not self._pool_path.exists():
            return
        import json
        try:
            data = json.loads(self._pool_path.read_text())
            for key, val in data.get("entries", {}).items():
                self._cache[key] = PoolEntry(
                    result=AssetResolutionResult(**val["result"]),
                    resolved_at=val["resolved_at"],
                )
            log.info("asset_pool_loaded", entries=len(self._cache))
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            log.warning("asset_pool_load_failed", error=str(e))
            self._cache.clear()

    def _save_to_disk(self) -> None:
        """Persist cache to asset_pool.json."""
        import json
        data = {
            "version": 1,
            "entries": {
                key: {
                    "result": {
                        "asset_path": entry.result.asset_path,
                        "source": entry.result.source,
                        "quality_score": entry.result.quality_score,
                        "generation_time": entry.result.generation_time,
                    },
                    "resolved_at": entry.resolved_at,
                }
                for key, entry in self._cache.items()
            }
        }
        self._pool_path.write_text(json.dumps(data, indent=2))

    def stats(self) -> dict:
        """Return pool statistics for diagnostics."""
        source_counts: dict[str, int] = {}
        for entry in self._cache.values():
            source_counts[entry.result.source] = source_counts.get(entry.result.source, 0) + 1
        return {
            "total_entries": len(self._cache),
            "max_entries": self.MAX_ENTRIES,
            "by_source": source_counts,
        }
