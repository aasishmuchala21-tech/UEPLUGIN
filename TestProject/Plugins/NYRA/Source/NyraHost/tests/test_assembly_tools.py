from __future__ import annotations

from pathlib import Path

import pytest

from nyrahost.tools.assembly_tools import AssembleSceneTool
from nyrahost.tools.scene_assembler import SceneAssembler
from nyrahost.tools.scene_types import (
    ActorSpec,
    AssemblyResult,
    LightingParams,
    MaterialSpec,
    SceneBlueprint,
)


def _fake_image(tmp_path) -> str:
    img = tmp_path / "ref.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    return str(img)


def test_execute_requires_reference_image_path():
    tool = AssembleSceneTool()
    result = tool.execute({})
    assert result.error is not None
    assert "-32030" in result.error


def test_execute_missing_image_returns_error(tmp_path):
    tool = AssembleSceneTool()
    result = tool.execute({"reference_image_path": str(tmp_path / "ghost.png")})
    assert result.error is not None
    assert "-32030" in result.error


def test_execute_emits_progress_through_all_four_steps(tmp_path):
    received = []
    img = _fake_image(tmp_path)
    tool = AssembleSceneTool(ws_notifier=received.append)
    result = tool.execute({"reference_image_path": img})
    assert result.error is None
    assert result.data is not None
    # Every progress notification carries the canonical step + counters.
    progress_msgs = [m for m in received if m.get("type") == "assembly_progress"]
    steps = {m["step"] for m in progress_msgs}
    assert {"Placing Actors", "Applying Materials", "Setting Up Lighting", "Finalizing"}.issubset(steps)
    # Final assembly_complete is also emitted.
    assert any(m.get("type") == "assembly_complete" for m in received)


def test_execute_returns_summary_payload(tmp_path):
    img = _fake_image(tmp_path)
    tool = AssembleSceneTool()
    result = tool.execute({"reference_image_path": img})
    assert result.error is None
    data = result.data
    assert "scene_type" in data
    assert "actor_count" in data
    assert "material_count" in data
    assert "log_entries" in data
    assert "summary" in data
    # Stub blueprint places 4 actors total (1 floor + 1 hero + 2 background_prop).
    assert data["actor_count"] == 4
    assert data["material_count"] == 2


def test_assembler_stub_blueprint_has_required_fields(tmp_path):
    img = _fake_image(tmp_path)
    blueprint = SceneAssembler._stub_blueprint(img)
    assert isinstance(blueprint, SceneBlueprint)
    assert len(blueprint.actor_specs) >= 3
    assert len(blueprint.material_specs) >= 1
    assert blueprint.mood_tags
    # Every actor_spec has a hint that includes the image filename when role is hero.
    hero = [s for s in blueprint.actor_specs if s.role == "hero_furniture"][0]
    assert Path(img).name in hero.asset_hint


def test_assemble_increments_log_entries():
    blueprint = SceneBlueprint(
        scene_type="test_scene",
        actor_specs=[
            ActorSpec(role="floor", class_path="/Script/Engine.StaticMeshActor", asset_hint="floor"),
            ActorSpec(role="hero", class_path="/Script/Engine.StaticMeshActor", asset_hint="sofa"),
        ],
        material_specs=[
            MaterialSpec(target_actor="hero", material_type="hero", texture_hint="leather"),
        ],
        mood_tags=["test"],
        confidence=0.9,
    )
    assembler = SceneAssembler()
    progress_calls = []
    result: AssemblyResult = assembler.assemble(
        blueprint=blueprint,
        progress_callback=lambda step, c, t, m="": progress_calls.append((step, c, t, m)),
    )
    assert result.success is True
    assert result.actor_count == 2
    assert result.material_count == 1
    assert len(result.log_entries) >= 3  # 2 actors + 1 material
    # Progress was called for every actor + every material + lighting + finalize.
    steps_called = {p[0] for p in progress_calls}
    assert "Placing Actors" in steps_called
    assert "Applying Materials" in steps_called
    assert "Setting Up Lighting" in steps_called
    assert "Finalizing" in steps_called


def test_assemble_invokes_lighting_tool_when_supplied():
    invocations = []

    class _FakeLighting:
        def execute(self, params):
            invocations.append(params)
            from nyrahost.tools.base import NyraToolResult
            return NyraToolResult.ok({
                "actors_placed": [{"actor_name": "NYRA_Primary_directional"}],
                "primary_light_type": "directional",
                "mood_tags": ["warm"],
            })

    blueprint = SceneBlueprint(
        scene_type="x",
        actor_specs=[ActorSpec(role="floor", class_path="/Script/Engine.StaticMeshActor", asset_hint="floor")],
        material_specs=[],
        mood_tags=[],
        confidence=0.5,
    )
    assembler = SceneAssembler(lighting_tool=_FakeLighting())
    result = assembler.assemble(blueprint=blueprint, lighting_plan=LightingParams())
    assert result.lighting_count == 1
    assert invocations  # lighting tool was called
    assert any("lighting:directional" in entry for entry in result.log_entries)


def test_assemble_continues_when_lighting_tool_raises():
    class _BoomLighting:
        def execute(self, params):
            raise RuntimeError("lighting exploded")

    blueprint = SceneBlueprint(
        scene_type="x",
        actor_specs=[ActorSpec(role="floor", class_path="/Script/Engine.StaticMeshActor", asset_hint="floor")],
        material_specs=[],
        mood_tags=[],
        confidence=0.5,
    )
    assembler = SceneAssembler(lighting_tool=_BoomLighting())
    result = assembler.assemble(blueprint=blueprint, lighting_plan=LightingParams())
    # Doesn't crash, just logs the error.
    assert result.success is True
    assert any("lighting:error" in entry for entry in result.log_entries)
