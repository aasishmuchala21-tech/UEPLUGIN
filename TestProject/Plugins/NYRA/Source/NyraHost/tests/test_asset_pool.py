from __future__ import annotations
import pytest
import json
from pathlib import Path
from nyrahost.tools.asset_pool import AssetPool, PoolEntry
from nyrahost.tools.scene_types import AssetResolutionResult


@pytest.fixture
def tmp_pool_root(tmp_path):
    return tmp_path / "nyra_pool"


def test_pool_put_and_get(tmp_pool_root):
    pool = AssetPool(pool_root=tmp_pool_root)
    result = AssetResolutionResult(asset_path="/Game/Props/Sofa", source="library", quality_score=0.95)
    pool.put("brown sofa", "hero_prop", result)
    retrieved = pool.get("brown sofa", "hero_prop")
    assert retrieved is not None
    assert retrieved.asset_path == "/Game/Props/Sofa"
    assert retrieved.source == "library"
    assert retrieved.quality_score == 0.95


def test_pool_lru_eviction(tmp_pool_root):
    import nyrahost.tools.asset_pool as ap
    original = ap.AssetPool.MAX_ENTRIES
    ap.AssetPool.MAX_ENTRIES = 3
    try:
        pool = AssetPool(pool_root=tmp_pool_root)
        for i in range(5):
            result = AssetResolutionResult(
                asset_path=f"/Game/Props/Asset{i}", source="library", quality_score=0.9
            )
            pool.put(f"hint_{i}", "role", result)
        assert len(pool._cache) == 3
        assert pool.get("hint_0", "role") is None
        assert pool.get("hint_1", "role") is None
        assert pool.get("hint_2", "role") is not None
        assert pool.get("hint_3", "role") is not None
        assert pool.get("hint_4", "role") is not None
    finally:
        ap.AssetPool.MAX_ENTRIES = original


def test_pool_miss_returns_none(tmp_pool_root):
    pool = AssetPool(pool_root=tmp_pool_root)
    assert pool.get("nonexistent hint", "nonexistent_role") is None


def test_pool_case_insensitive_key(tmp_pool_root):
    pool = AssetPool(pool_root=tmp_pool_root)
    result = AssetResolutionResult(asset_path="/Game/Props/Cube", source="library", quality_score=0.9)
    pool.put("BROWN SOFA", "hero_prop", result)
    retrieved = pool.get("brown sofa", "hero_prop")
    assert retrieved is not None


def test_pool_persistence(tmp_pool_root):
    result = AssetResolutionResult(asset_path="/Game/Props/PersistTest", source="library", quality_score=0.99)
    pool1 = AssetPool(pool_root=tmp_pool_root)
    pool1.put("persist_hint", "role", result)
    pool2 = AssetPool(pool_root=tmp_pool_root)
    retrieved = pool2.get("persist_hint", "role")
    assert retrieved is not None
    assert retrieved.asset_path == "/Game/Props/PersistTest"


def test_pool_clear(tmp_pool_root):
    pool = AssetPool(pool_root=tmp_pool_root)
    result = AssetResolutionResult(asset_path="/Game/Props/Clear", source="library", quality_score=0.9)
    pool.put("clear_hint", "role", result)
    assert pool.get("clear_hint", "role") is not None
    pool.clear()
    assert pool.get("clear_hint", "role") is None
    assert len(pool._cache) == 0


def test_pool_stats(tmp_pool_root):
    pool = AssetPool(pool_root=tmp_pool_root)
    pool.put("h1", "r1", AssetResolutionResult(asset_path="/p1", source="library", quality_score=0.9))
    pool.put("h2", "r2", AssetResolutionResult(asset_path="/p2", source="meshy", quality_score=0.85))
    stats = pool.stats()
    assert stats["total_entries"] == 2
    assert stats["by_source"]["library"] == 1
    assert stats["by_source"]["meshy"] == 1
