"""Plan 06-03: end-to-end DEMO-01 smoke + cold-start tests.

Exercises the full Phase 6 pipeline (analyze_image -> assemble) without
requiring a live Meshy or ComfyUI service. Cold-start tests assert that
when external services degrade or are absent, the assembly still completes
through the placeholder fallback chain.
"""
from __future__ import annotations

import asyncio

import pytest

from nyrahost.tools.asset_fallback_chain import (
    AssetFallbackChain,
    PLACEHOLDER_ACTOR_PATH,
    PLACEHOLDER_MATERIAL_PATH,
)
from nyrahost.tools.asset_pool import AssetPool
from nyrahost.tools.assembly_tools import AssembleSceneTool
from nyrahost.tools.base import NyraToolResult
from nyrahost.tools.scene_assembler import SceneAssembler
from nyrahost.tools.scene_types import (
    ActorSpec,
    AssemblyResult,
    LightingParams,
    MaterialSpec,
    SceneBlueprint,
)


# ---------------------------------------------------------------------------
# Mock router for analyze_image
# ---------------------------------------------------------------------------

class _MockClaudeRouter:
    """Stand-in for the Phase 2 backend router; returns canned analyze_image dict."""

    def __init__(self, blueprint_dict=None, raise_on_call=False):
        self.blueprint_dict = blueprint_dict or {
            "scene_type": "interior_living_room",
            "actor_specs": [
                {
                    "role": "hero_furniture",
                    "class_path": "/Script/Engine.StaticMeshActor",
                    "asset_hint": "leather sofa",
                    "count": 1,
                    "placement": "center_floor",
                },
                {
                    "role": "background_prop",
                    "class_path": "/Script/Engine.StaticMeshActor",
                    "asset_hint": "coffee table",
                    "count": 2,
                    "placement": "scattered",
                },
                {
                    "role": "floor",
                    "class_path": "/Script/Engine.StaticMeshActor",
                    "asset_hint": "hardwood",
                    "count": 1,
                    "placement": "grid",
                },
            ],
            "material_specs": [
                {
                    "target_actor": "hero_furniture",
                    "material_type": "hero",
                    "texture_hint": "brown leather",
                },
                {
                    "target_actor": "floor",
                    "material_type": "floor",
                    "texture_hint": "warm hardwood",
                },
            ],
            "mood_tags": ["cozy", "warm", "evening"],
            "confidence": 0.88,
        }
        self.raise_on_call = raise_on_call
        self.calls = []

    async def generate_image_description(self, image_path):
        self.calls.append(image_path)
        if self.raise_on_call:
            raise RuntimeError("vision exploded")
        return self.blueprint_dict


# ---------------------------------------------------------------------------
# Smoke: full happy path with mocked router + library hits
# ---------------------------------------------------------------------------

def test_e2e_smoke_full_pipeline_with_library_hits(sample_reference_image, tmp_path):
    """LLM analysis -> 4 actors + 2 materials placed -> all 4 progress steps emitted."""
    pool = AssetPool(pool_root=tmp_path / "pool")
    chain = AssetFallbackChain(
        asset_pool=pool,
        library_search=lambda hint, role: f"/Game/Library/{role}.{role}",
    )
    router = _MockClaudeRouter()
    notifications = []
    assembler = SceneAssembler(
        backend_router=router,
        ws_notifier=notifications.append,
        fallback_chain=chain,
    )

    # Async: analyze
    blueprint = asyncio.run(assembler.analyze_image(str(sample_reference_image)))
    assert blueprint.scene_type == "interior_living_room"
    assert len(blueprint.actor_specs) == 3
    assert len(blueprint.material_specs) == 2

    # Sync: assemble
    progress_log = []
    result = assembler.assemble(
        blueprint=blueprint,
        progress_callback=lambda step, c, t, m="": progress_log.append((step, c, t)),
    )

    # 4 actors total (1 + 2 + 1) and 2 materials applied via library.
    assert result.success is True
    assert result.actor_count == 4
    assert result.material_count == 2
    # Every placed actor sourced from library because library_search always hits.
    assert all(a.get("source") == "library" for a in result.placed_actors)
    # All 4 canonical steps emitted at least once.
    steps = {p[0] for p in progress_log}
    assert {"Placing Actors", "Applying Materials", "Setting Up Lighting", "Finalizing"}.issubset(steps)
    # WS notifier received progress + completion frames.
    assert any(n.get("type") == "assembly_complete" for n in notifications)


def test_e2e_assemble_scene_tool_returns_summary(sample_reference_image, tmp_path):
    """End-to-end via the MCP tool surface: nyra_assemble_scene."""
    pool = AssetPool(pool_root=tmp_path / "pool")
    chain = AssetFallbackChain(
        asset_pool=pool,
        library_search=lambda hint, role: f"/Game/Library/{role}_{hint}.uasset",
    )
    router = _MockClaudeRouter()
    notifications = []
    assembler = SceneAssembler(
        backend_router=router,
        ws_notifier=notifications.append,
        fallback_chain=chain,
    )
    tool = AssembleSceneTool(ws_notifier=notifications.append, assembler=assembler)
    result = tool.execute({"reference_image_path": str(sample_reference_image)})

    assert result.error is None
    assert result.data is not None
    assert result.data["scene_type"] == "interior_living_room"
    assert result.data["actor_count"] == 4
    assert result.data["material_count"] == 2
    assert "cozy" in result.data["mood_tags"]


# ---------------------------------------------------------------------------
# Cold-start reliability: services down, placeholders fill in
# ---------------------------------------------------------------------------

def test_cold_start_meshy_unavailable_lands_on_placeholder(sample_reference_image, tmp_path):
    """No Meshy + library miss -> every actor lands on /Engine placeholder."""
    pool = AssetPool(pool_root=tmp_path / "pool")
    chain = AssetFallbackChain(
        asset_pool=pool,
        library_search=lambda hint, role: None,  # library always misses
        meshy_tool=None,                          # service unavailable
    )
    router = _MockClaudeRouter()
    assembler = SceneAssembler(backend_router=router, fallback_chain=chain)
    blueprint = asyncio.run(assembler.analyze_image(str(sample_reference_image)))
    result = assembler.assemble(blueprint=blueprint)

    assert result.success is True
    # Every actor went to placeholder.
    assert all(a.get("source") == "placeholder" for a in result.placed_actors)
    assert all(a.get("asset_path") == PLACEHOLDER_ACTOR_PATH for a in result.placed_actors)


def test_cold_start_meshy_errors_falls_through_to_placeholder(sample_reference_image, tmp_path):
    """Meshy returns an error -> AssetFallbackChain still resolves to placeholder."""

    class _BrokenMeshy:
        def execute(self, params):
            return NyraToolResult.err("[-32100] meshy 503")

    pool = AssetPool(pool_root=tmp_path / "pool")
    chain = AssetFallbackChain(
        asset_pool=pool,
        library_search=lambda h, r: None,
        meshy_tool=_BrokenMeshy(),
    )
    router = _MockClaudeRouter()
    assembler = SceneAssembler(backend_router=router, fallback_chain=chain)
    blueprint = asyncio.run(assembler.analyze_image(str(sample_reference_image)))
    result = assembler.assemble(blueprint=blueprint)

    assert result.success is True
    assert all(a.get("source") == "placeholder" for a in result.placed_actors)


def test_cold_start_comfyui_unavailable_materials_use_placeholder(sample_reference_image, tmp_path):
    """No ComfyUI + library miss -> every material lands on placeholder material."""
    pool = AssetPool(pool_root=tmp_path / "pool")
    chain = AssetFallbackChain(
        asset_pool=pool,
        library_search=lambda h, r: None,
        comfyui_tool=None,
    )
    router = _MockClaudeRouter()
    assembler = SceneAssembler(backend_router=router, fallback_chain=chain)
    blueprint = asyncio.run(assembler.analyze_image(str(sample_reference_image)))
    result = assembler.assemble(blueprint=blueprint)

    assert all(m.get("source") == "placeholder" for m in result.applied_materials)
    assert all(m.get("asset_path") == PLACEHOLDER_MATERIAL_PATH for m in result.applied_materials)


def test_cold_start_router_exception_falls_back_to_stub_blueprint(sample_reference_image, tmp_path):
    """LLM router blows up -> SceneAssembler delivers the offline stub blueprint."""
    pool = AssetPool(pool_root=tmp_path / "pool")
    chain = AssetFallbackChain(asset_pool=pool, library_search=lambda h, r: None)
    router = _MockClaudeRouter(raise_on_call=True)
    assembler = SceneAssembler(backend_router=router, fallback_chain=chain)

    blueprint = asyncio.run(assembler.analyze_image(str(sample_reference_image)))
    # Stub blueprint contract: 4 actors, 2 materials, mood_tags non-empty.
    assert sum(s.count for s in blueprint.actor_specs) == 4
    assert len(blueprint.material_specs) == 2
    assert blueprint.mood_tags


def test_cold_start_no_router_at_all_still_assembles(sample_reference_image, tmp_path):
    """Router never even injected -> stub blueprint + placeholder chain still completes."""
    pool = AssetPool(pool_root=tmp_path / "pool")
    chain = AssetFallbackChain(asset_pool=pool, library_search=lambda h, r: None)
    assembler = SceneAssembler(backend_router=None, fallback_chain=chain)

    blueprint = asyncio.run(assembler.analyze_image(str(sample_reference_image)))
    result = assembler.assemble(blueprint=blueprint)

    assert result.success is True
    assert result.actor_count == 4
    assert result.material_count == 2


# ---------------------------------------------------------------------------
# Cross-component import sanity
# ---------------------------------------------------------------------------

def test_all_phase_6_modules_import_together():
    """All Phase 6 source modules + their dataclasses load without circular import."""
    # If any of these imports fail, it surfaces as a collection error before this test runs.
    from nyrahost.tools import (
        scene_types,
        scene_orchestrator,
        scene_llm_parser,
        lighting_tools,
        asset_pool,
        asset_fallback_chain,
        scene_assembler,
        assembly_tools,
    )
    # Spot-check that the canonical types are reachable by name.
    assert scene_types.LightingParams is not None
    assert scene_orchestrator.SceneAssemblyOrchestrator is not None
    assert lighting_tools.LightingAuthoringTool is not None
    assert asset_fallback_chain.AssetFallbackChain is not None
    assert scene_assembler.SceneAssembler is not None
    assert assembly_tools.AssembleSceneTool is not None
