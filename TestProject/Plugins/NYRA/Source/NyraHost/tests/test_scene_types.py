from __future__ import annotations
import pytest
from nyrahost.tools.scene_types import (
    ActorSpec, MaterialSpec, SceneBlueprint, AssemblyResult,
    LightingParams, AssetResolutionResult, ProgressUpdate,
)


def test_actor_spec_defaults():
    spec = ActorSpec(role="hero", class_path="/Script/Engine.StaticMeshActor", asset_hint="sofa")
    assert spec.count == 1
    assert spec.placement == "scattered"
    assert spec.source == "library"


def test_scene_blueprint_fields():
    blueprint = SceneBlueprint(
        scene_type="interior_bedroom",
        actor_specs=[ActorSpec(role="bed", class_path="/Script/Engine.StaticMeshActor", asset_hint="bed")],
        material_specs=[],
        mood_tags=["cozy", "warm"],
        confidence=0.92
    )
    assert blueprint.scene_type == "interior_bedroom"
    assert len(blueprint.actor_specs) == 1
    assert blueprint.confidence == 0.92


def test_assembly_result_structured_summary():
    result = AssemblyResult()
    result.placed_actors = [{"actor_name": "Sofa_01"}, {"actor_name": "Table_01"}]
    result.applied_materials = [{"asset_path": "/Game/Materials/Leather"}]
    result.lighting_actors = [{"actor_name": "NYRA_Primary"}]
    summary = result.to_structured_summary()
    assert summary["actor_count"] == 2
    assert summary["material_count"] == 1
    assert summary["lighting_count"] == 1
    assert "2 actors placed" in summary["message"]


def test_assembly_result_failure():
    result = AssemblyResult(success=False, error_message="Actor spawn failed")
    summary = result.to_structured_summary()
    assert summary["success"] is False


def test_lighting_params_defaults():
    lp = LightingParams()
    assert lp.primary_light_type == "directional"
    assert lp.primary_intensity == 1.0
    assert lp.primary_color == (1.0, 1.0, 1.0)
    assert lp.use_shadow is True


def test_lighting_params_to_ue_params():
    lp = LightingParams(
        primary_light_type="point",
        primary_intensity=2.0,
        primary_color=(0.5, 0.6, 0.9),
        primary_direction=(30, -45, 0),
        exposure_compensation=0.5,
        mood_tags=["cool", "blue"],
    )
    ue = lp.to_ue_params()
    assert ue["primary_light_type"] == "point"
    assert ue["primary_intensity"] == 2.0
    assert ue["primary_color_r"] == 0.5
    assert ue["primary_color_g"] == 0.6
    assert ue["primary_color_b"] == 0.9
    assert ue["exposure_compensation"] == 0.5
    assert "cool" in ue["mood_tags"]


def test_progress_update_to_ws_payload():
    update = ProgressUpdate(step="Placing Actors", current=3, total=12, message="sofa placed")
    payload = update.to_ws_payload()
    assert payload["type"] == "assembly_progress"
    assert payload["step"] == "Placing Actors"
    assert payload["current"] == 3
    assert payload["total"] == 12


def test_asset_resolution_result_defaults():
    result = AssetResolutionResult(asset_path="/Game/Props/Cube", source="library", quality_score=0.9)
    assert result.generation_time is None


def test_assembly_result_property_counts():
    result = AssemblyResult()
    result.placed_actors = [{}] * 5
    result.applied_materials = [{}] * 3
    result.lighting_actors = [{}] * 2
    assert result.actor_count == 5
    assert result.material_count == 3
    assert result.lighting_count == 2
