from __future__ import annotations

from nyrahost.tools.asset_fallback_chain import (
    AssetFallbackChain,
    PLACEHOLDER_ACTOR_PATH,
    PLACEHOLDER_MATERIAL_PATH,
)
from nyrahost.tools.asset_pool import AssetPool
from nyrahost.tools.base import NyraToolResult


class _FakeTool:
    def __init__(self, asset_path=None, error=None, raise_on_call=False):
        self.asset_path = asset_path
        self.error = error
        self.raise_on_call = raise_on_call
        self.call_count = 0

    def execute(self, params):
        self.call_count += 1
        if self.raise_on_call:
            raise RuntimeError("tool exploded")
        if self.error:
            return NyraToolResult.err(self.error)
        return NyraToolResult.ok({"asset_path": self.asset_path})


def _pool(tmp_path):
    return AssetPool(pool_root=tmp_path / "pool")


def test_actor_resolves_via_library_first(tmp_path):
    chain = AssetFallbackChain(
        asset_pool=_pool(tmp_path),
        library_search=lambda hint, role: "/Game/Library/Sofa.Sofa",
        meshy_tool=_FakeTool(asset_path="/Game/Meshy/should_not_be_called.uasset"),
    )
    res = chain.resolve_actor_asset("brown sofa", "hero_furniture")
    assert res.source == "library"
    assert res.asset_path == "/Game/Library/Sofa.Sofa"


def test_actor_falls_back_to_meshy_when_library_misses(tmp_path):
    meshy = _FakeTool(asset_path="/Game/Meshy/Generated_Sofa.Sofa")
    chain = AssetFallbackChain(
        asset_pool=_pool(tmp_path),
        library_search=lambda hint, role: None,
        meshy_tool=meshy,
    )
    res = chain.resolve_actor_asset("brown sofa", "hero_furniture")
    assert res.source == "meshy"
    assert res.asset_path == "/Game/Meshy/Generated_Sofa.Sofa"
    assert meshy.call_count == 1


def test_actor_falls_back_to_placeholder_when_meshy_unavailable(tmp_path):
    chain = AssetFallbackChain(
        asset_pool=_pool(tmp_path),
        library_search=lambda hint, role: None,
        meshy_tool=None,
    )
    res = chain.resolve_actor_asset("nonexistent thing", "hero_furniture")
    assert res.source == "placeholder"
    assert res.asset_path == PLACEHOLDER_ACTOR_PATH


def test_actor_falls_back_to_placeholder_when_meshy_errors(tmp_path):
    chain = AssetFallbackChain(
        asset_pool=_pool(tmp_path),
        library_search=lambda hint, role: None,
        meshy_tool=_FakeTool(error="[-32100] meshy down"),
    )
    res = chain.resolve_actor_asset("vase", "background_prop")
    assert res.source == "placeholder"
    assert res.asset_path == PLACEHOLDER_ACTOR_PATH


def test_actor_falls_back_to_placeholder_when_meshy_raises(tmp_path):
    chain = AssetFallbackChain(
        asset_pool=_pool(tmp_path),
        library_search=lambda hint, role: None,
        meshy_tool=_FakeTool(raise_on_call=True),
    )
    res = chain.resolve_actor_asset("chair", "background_prop")
    assert res.source == "placeholder"


def test_actor_caches_on_pool(tmp_path):
    pool = _pool(tmp_path)
    library_calls = {"n": 0}

    def lib(hint, role):
        library_calls["n"] += 1
        return "/Game/Library/Cache.Cache"

    chain = AssetFallbackChain(asset_pool=pool, library_search=lib)
    chain.resolve_actor_asset("table", "hero_furniture")
    chain.resolve_actor_asset("table", "hero_furniture")
    chain.resolve_actor_asset("table", "hero_furniture")
    # library should have been hit only once because subsequent calls hit pool.
    assert library_calls["n"] == 1


def test_material_resolves_via_library_first(tmp_path):
    chain = AssetFallbackChain(
        asset_pool=_pool(tmp_path),
        library_search=lambda hint, role: "/Game/Library/M_Leather.M_Leather",
        comfyui_tool=_FakeTool(asset_path="/Game/ComfyUI/should_not_be_called.uasset"),
    )
    res = chain.resolve_material_asset("leather", "hero")
    assert res.source == "library"


def test_material_falls_back_to_comfyui_when_library_misses(tmp_path):
    comfy = _FakeTool(asset_path="/Game/ComfyUI/Generated_Wood.M_Wood")
    chain = AssetFallbackChain(
        asset_pool=_pool(tmp_path),
        library_search=lambda hint, role: None,
        comfyui_tool=comfy,
    )
    res = chain.resolve_material_asset("warm wood", "floor")
    assert res.source == "comfyui"
    assert res.asset_path == "/Game/ComfyUI/Generated_Wood.M_Wood"


def test_material_placeholder_when_comfyui_unavailable(tmp_path):
    chain = AssetFallbackChain(
        asset_pool=_pool(tmp_path),
        library_search=lambda hint, role: None,
        comfyui_tool=None,
    )
    res = chain.resolve_material_asset("plastic", "background")
    assert res.source == "placeholder"
    assert res.asset_path == PLACEHOLDER_MATERIAL_PATH


def test_material_placeholder_when_comfyui_raises(tmp_path):
    chain = AssetFallbackChain(
        asset_pool=_pool(tmp_path),
        library_search=lambda hint, role: None,
        comfyui_tool=_FakeTool(raise_on_call=True),
    )
    res = chain.resolve_material_asset("plastic", "background")
    assert res.source == "placeholder"


def test_meshy_quality_score_lower_than_library(tmp_path):
    lib_chain = AssetFallbackChain(
        asset_pool=_pool(tmp_path / "lib"),
        library_search=lambda hint, role: "/Game/Library/A.A",
    )
    meshy_chain = AssetFallbackChain(
        asset_pool=_pool(tmp_path / "meshy"),
        library_search=lambda hint, role: None,
        meshy_tool=_FakeTool(asset_path="/Game/Meshy/A.A"),
    )
    lib_res = lib_chain.resolve_actor_asset("a", "r")
    meshy_res = meshy_chain.resolve_actor_asset("a", "r")
    assert lib_res.quality_score > meshy_res.quality_score
