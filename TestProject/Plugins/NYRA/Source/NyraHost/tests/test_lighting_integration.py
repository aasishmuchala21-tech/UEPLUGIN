"""Plan 06-03: SCENE-01 lighting integration tests.

Exercises LightingAuthoringTool with concrete preset / NL / image inputs,
asserts the scene_llm_parser <-> lighting_tools handshake, and verifies that
SceneAssembler's lighting step calls into LightingAuthoringTool correctly.
"""
from __future__ import annotations

import asyncio

import pytest

from nyrahost.tools.base import NyraToolResult
from nyrahost.tools.lighting_tools import LightingAuthoringTool, LightingDryRunTool, _PRESETS
from nyrahost.tools.scene_assembler import SceneAssembler
from nyrahost.tools.scene_llm_parser import LightingLLMParser
from nyrahost.tools.scene_types import (
    ActorSpec,
    LightingParams,
    MaterialSpec,
    SceneBlueprint,
)


# ---------------------------------------------------------------------------
# scene_llm_parser <-> lighting_tools handshake
# ---------------------------------------------------------------------------

def test_parser_output_feeds_lighting_tool_preset_path():
    """Parser-style dict can be coerced and applied via LightingAuthoringTool."""

    class _Router:
        async def generate_lighting_from_text(self, prompt, system=None):
            return {
                "primary_light_type": "directional",
                "primary_intensity": 1.5,
                "primary_color": [0.95, 0.65, 0.3],
                "primary_direction_deg": [45, -30, 0],
                "use_sky_atmosphere": True,
                "use_exponential_height_fog": True,
                "fog_density": 0.01,
                "fog_color": [0.8, 0.7, 0.6],
                "use_post_process": True,
                "exposure_compensation": 0.5,
                "mood_tags": ["warm", "low sun"],
                "confidence": 0.9,
            }

    parser = LightingLLMParser(backend_router=_Router())
    lp = asyncio.run(parser.parse_from_text("golden hour"))
    # Now feed those params into the dry-run tool to assert the WS payload shape.
    received = []
    LightingDryRunTool(ws_notifier=received.append).execute({
        "lighting_params_json": __import__("json").dumps({
            "primary_light_type": lp.primary_light_type,
            "primary_intensity": lp.primary_intensity,
            "mood_tags": lp.mood_tags,
        }),
    })
    assert received
    assert received[0]["primary_light_type"] == "directional"
    assert received[0]["mood_tags"] == ["warm", "low sun"]


def test_each_preset_applied_via_authoring_tool():
    """Every preset round-trips through LightingAuthoringTool.execute(apply=True)."""
    for preset_name in _PRESETS:
        tool = LightingAuthoringTool()
        result = tool.execute({"preset_name": preset_name, "apply": True})
        assert result.error is None, f"preset {preset_name} returned error"
        assert result.data["primary_light_type"] in {"directional", "spot", "point", "rect", "sky"}
        # Out-of-editor stub places at minimum the primary light placeholder.
        assert len(result.data["actors_placed"]) >= 1


def test_dry_run_does_not_emit_assembly_complete():
    """Dry-run only emits dry_run_preview, never assembly_complete."""
    received = []
    tool = LightingAuthoringTool(ws_notifier=received.append)
    result = tool.execute({"preset_name": "moody_blue", "apply": False})
    assert result.error is None
    assert result.data["dry_run"] is True
    types = {n["type"] for n in received}
    assert "dry_run_preview" in types
    assert "assembly_complete" not in types


# ---------------------------------------------------------------------------
# SceneAssembler -> LightingAuthoringTool integration
# ---------------------------------------------------------------------------

def test_scene_assembler_invokes_lighting_tool_during_assembly():
    """assemble() with a lighting_tool fires its execute() during step 3."""

    class _Tool:
        def __init__(self):
            self.calls = []

        def execute(self, params):
            self.calls.append(params)
            return NyraToolResult.ok({
                "actors_placed": [{"actor_name": "NYRA_Primary_directional"}],
                "primary_light_type": "directional",
                "mood_tags": ["warm"],
            })

    lighting = _Tool()
    blueprint = SceneBlueprint(
        scene_type="x",
        actor_specs=[ActorSpec(role="floor", class_path="/Script/Engine.StaticMeshActor", asset_hint="floor")],
        material_specs=[MaterialSpec(target_actor="floor", material_type="floor", texture_hint="wood")],
        mood_tags=[],
        confidence=0.5,
    )
    assembler = SceneAssembler(lighting_tool=lighting)
    result = assembler.assemble(blueprint=blueprint, lighting_plan=LightingParams())

    assert lighting.calls  # lighting_tool.execute was called
    assert result.lighting_count == 1
    assert any("lighting:directional" in entry for entry in result.log_entries)


def test_scene_assembler_omits_lighting_when_tool_not_supplied():
    """No lighting_tool -> assemble() runs lighting step but lighting_count stays 0."""
    blueprint = SceneBlueprint(
        scene_type="x",
        actor_specs=[ActorSpec(role="floor", class_path="/Script/Engine.StaticMeshActor", asset_hint="floor")],
        material_specs=[],
        mood_tags=[],
        confidence=0.5,
    )
    assembler = SceneAssembler(lighting_tool=None)
    result = assembler.assemble(blueprint=blueprint, lighting_plan=LightingParams())
    assert result.success is True
    assert result.lighting_count == 0


def test_lighting_actor_labels_use_nyra_prefix():
    """T-06-02 mitigation - all lighting placeholder actors carry NYRA_ prefix."""
    tool = LightingAuthoringTool()
    result = tool.execute({"preset_name": "studio_fill", "apply": True})
    assert result.error is None
    placed = result.data["actors_placed"]
    # In test env the placeholder uses 'actor_name' starting with 'NYRA_'.
    assert all(p.get("actor_name", "").startswith("NYRA_") for p in placed)
