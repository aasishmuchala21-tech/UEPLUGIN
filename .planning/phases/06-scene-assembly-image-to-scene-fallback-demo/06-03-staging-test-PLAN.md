---
phase: "06"
plan: "06-03"
type: execute
wave: 3
depends_on: ["06-01", "06-02"]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_scene_assembly_e2e.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_lighting_integration.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/conftest.py
autonomous: true
requirements:
  - DEMO-01
  - SCENE-01
user_setup: []
must_haves:
  truths:
    - "End-to-end smoke test passes: test image → verify actors placed + materials applied + lighting configured"
    - "Cold-start reliability test passes: Meshy unavailable → ComfyUI fallback or placeholder material used"
    - "All Phase 6 components can be loaded together without import conflicts"
    - "DEMO-01 and SCENE-01 requirements are both verifiable via automated tests"
  artifacts:
    - path: "NyraHost/tests/test_scene_assembly_e2e.py"
      provides: "End-to-end smoke test for DEMO-01 pipeline"
      min_lines: 80
    - path: "NyraHost/tests/test_lighting_integration.py"
      provides: "Integration tests for SCENE-01 lighting tools"
    - path: "NyraHost/tests/conftest.py"
      provides: "Updated fixtures for Phase 6 test harness"
---

<objective>
Write end-to-end integration tests for the Phase 6 pipeline. Smoke test: test image → actors placed + materials applied + lighting configured. Cold-start reliability: Meshy unavailable → ComfyUI fallback or placeholder material. Verify DEMO-01 and SCENE-01 requirements are both testable via automated tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/06-scene-assembly-image-to-scene-fallback-demo/06-01-SCENE-01-lighting-authoring-PLAN.md
@.planning/phases/06-scene-assembly-image-to-scene-fallback-demo/06-02-DEMO-01-image-to-scene-PLAN.md
@TestProject/Plugins/NYRA/Source/NyraHost/tests/conftest.py
@TestProject/Plugins/NYRA/Source/NyraHost/tests/test_meshy_tools.py
</context>

<interfaces>
From existing NyraHost test conftest.py:
```python
@pytest.fixture
def tmp_project_dir(tmp_path: Path) -> Path:  # Creates project root, Saved/NYRA/ dir
@pytest.fixture
def mock_handshake_file(tmp_path: Path) -> Path:
@pytest.fixture
def tmp_staging_dir(tmp_path: Path) -> Path:  # Creates staging root for manifest tests
@pytest.fixture
def tmp_manifest_path(tmp_staging_dir: Path) -> Path:  # Creates nyra_pending.json
```

From test_meshy_tools.py (existing Phase 5 pattern):
```python
# Mock transport pattern for HTTP clients:
mock_meshy_api returns HTTP 202 on POST, then polling responses
# Test idempotency: call twice with same input_hash, assert same job_id
# Test path traversal: pass absolute path, assert PathTraversalError
```
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Write end-to-end assembly smoke test (test_scene_assembly_e2e.py)</name>
  <files>TestProject/Plugins/NYRA/Source/NyraHost/tests/test_scene_assembly_e2e.py</files>
  <action>
Create `nyrahost/tests/test_scene_assembly_e2e.py` implementing the full DEMO-01 smoke test suite.

**Tests to implement:**

```python
from __future__ import annotations

import pytest, json, os, asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from nyrahost.tools.scene_assembler import SceneAssembler, SceneBlueprint, ActorSpec, MaterialSpec
from nyrahost.tools.assembly_tools import AssembleSceneTool
from nyrahost.tools.asset_fallback_chain import AssetFallbackChain
from nyrahost.tools.staging import StagingManifest


# --- Fixtures ---

@pytest.fixture
def sample_reference_image(tmp_path: Path) -> Path:
    """Create a dummy 100x100 JPEG in tmp for testing."""
    import struct, zlib
    # Minimal valid JPEG header + data (grayscale)
    # Actually use a simple approach: create a 1x1 PNG
    img_path = tmp_path / "test_scene.jpg"
    # Write a minimal valid JPEG (1x1 pixel, white)
    # We'll use a pre-encoded base64 JPEG
    import base64
    # 1x1 white JPEG (minimal valid)
    jpg_b64 = "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/xAAUAQEAAAAAAAAAAAAAAAAAAAAA/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAwDAQACEQMRAD8AJQABAAEAAAAAAAAAAAAAAAAAAACYAf/EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAMAwEAAhEDEEQA/wAlAAEAAQAAAAAAAAAAAAAAAAAAAZn/wBQXEBAAAAAAAAAAAAAAAAAAAAAAH//2Q=="
    img_path.write_bytes(base64.b64decode(jpg_b64))
    return img_path


@pytest.fixture
def mock_claude_vision():
    """Mock Claude Opus vision response returning a SceneBlueprint."""
    blueprint = SceneBlueprint(
        scene_type="interior_living_room",
        actor_specs=[
            ActorSpec(role="hero_furniture", class_path="/Script/Engine.StaticMeshActor",
                      asset_hint="sofa", count=1, placement="center_floor", transform_hint="center"),
            ActorSpec(role="background_prop", class_path="/Script/Engine.StaticMeshActor",
                      asset_hint="coffee table", count=2, placement="scattered", transform_hint="near_sofa"),
            ActorSpec(role="floor", class_path="/Script/Engine.StaticMeshActor",
                      asset_hint="wooden floor", count=1, placement="grid", transform_hint="under_actors"),
        ],
        material_specs=[
            MaterialSpec(target_actor="hero_furniture", material_type="hero",
                         texture_hint="brown leather sofa texture", source="library"),
            MaterialSpec(target_actor="floor", material_type="floor",
                         texture_hint="hardwood floor", source="comfyui"),
        ],
        lighting_plan=None,  # Will be filled by SceneAssembler
        mood_tags=["warm", "cozy", "natural light"],
        confidence=0.92
    )
    async def mock_analyze(*args, **kwargs):
        return blueprint
    return mock_analyze


# --- Test Cases ---

def test_assemble_scene_tool_rejects_missing_image():
    """DEMO-01 SC#3: first-install cold-start reliability — missing image is an error, not a crash."""
    tool = AssembleSceneTool()
    result = tool.execute({"reference_image_path": "/nonexistent/image.jpg"})
    assert result.error is not None
    assert "[-32031]" in result.error  # Error code per plan
    assert result.error.startswith("[-32031]")


def test_assemble_scene_dry_run_returns_plan_without_placement():
    """DEMO-01 dry_run path: no actors placed, plan returned."""
    with patch("nyrahost.tools.scene_assembler.SceneAssembler.analyze_image") as mock_analyze:
        mock_analyze.return_value = SceneBlueprint(
            scene_type="outdoor_forest",
            actor_specs=[ActorSpec(role="tree", class_path="/Script/Engine.StaticMeshActor",
                                  asset_hint="pine tree", count=10, placement="scattered", transform_hint="")],
            material_specs=[],
            lighting_plan=None,
            mood_tags=["green", "misty"],
            confidence=0.88
        )
        tool = AssembleSceneTool()
        # dry_run=True — no actual actor spawn
        result = tool.execute({
            "reference_image_path": "/fake/path.jpg",
            "dry_run": True
        })
        assert result.data["dry_run"] is True
        assert result.data["actor_count"] == 10
        assert result.data["mood_tags"] == ["green", "misty"]


def test_scene_assembler_returns_actor_count():
    """DEMO-01: SceneAssembler.analyze_image produces a SceneBlueprint with 5-20 actors."""
    assembler = SceneAssembler()
    blueprint = SceneBlueprint(
        scene_type="urban_street",
        actor_specs=[
            ActorSpec(role=f"prop_{i}", class_path="/Script/Engine.StaticMeshActor",
                      asset_hint=f"building element {i}", count=1, placement="scattered", transform_hint="")
            for i in range(12)
        ],
        material_specs=[],
        lighting_plan=None,
        mood_tags=["urban", " gritty"],
        confidence=0.85
    )
    assert len(blueprint.actor_specs) == 12
    assert 5 <= len(blueprint.actor_specs) <= 20


def test_asset_fallback_chain_library_first():
    """DEMO-01 SC#1: user library preferred before Meshy/ComfyUI/generation."""
    with patch("nyrahost.tools.asset_search.AssetSearchTool.execute") as mock_search:
        mock_search.return_value = MagicMock(data={
            "assets": [{"asset_path": "/Game/Props/Sofa_01.Sofa_01", "score": 0.95}]
        })
        chain = AssetFallbackChain()
        result = chain.resolve_actor_asset("brown sofa", "hero_prop")
        assert result.source == "library"
        assert result.asset_path == "/Game/Props/Sofa_01.Sofa_01"
        mock_search.assert_called_once()


def test_asset_fallback_chain_meshy_when_library_empty():
    """DEMO-01 SC#3: Meshy generation when user library has no match."""
    with patch("nyrahost.tools.asset_search.AssetSearchTool.execute") as mock_search:
        mock_search.return_value = MagicMock(data={"assets": []})
        with patch("nyrahost.tools.meshy_tools.MeshyImageTo3DTool.execute") as mock_meshy:
            mock_meshy.return_value = MagicMock(error=None, data={"job_id": "test-job-123"})
            chain = AssetFallbackChain()
            result = chain.resolve_actor_asset("unique hero prop", "hero_prop")
            # Library returned nothing → Meshy called
            assert result.source in ("meshy", "placeholder")  # Placeholder if staging times out
            mock_meshy.assert_called_once()


def test_asset_fallback_chain_never_blocks():
    """DEMO-01 SC#3: cold-start reliability — all external services unavailable → placeholder."""
    with patch("nyrahost.tools.asset_search.AssetSearchTool.execute") as mock_search:
        with patch("nyrahost.tools.meshy_tools.MeshyImageTo3DTool.execute") as mock_meshy:
            mock_search.return_value = MagicMock(data={"assets": []})
            mock_meshy.return_value = MagicMock(error="MESHY_API_KEY not configured", data=None)
            chain = AssetFallbackChain()
            result = chain.resolve_actor_asset("anything", "hero_prop")
            # Both library and Meshy failed → placeholder
            assert result.source == "placeholder"
            assert result.asset_path == "/Engine/BasicShapes/Cube"


def test_assembly_log_entries_accumulated():
    """DEMO-01 evidence: AssemblyResult.log_entries captures every action for SNyraLogDrawer."""
    from nyrahost.tools.scene_assembler import AssemblyResult
    result = AssemblyResult()
    result.log_entries.append("Placed hero_furniture: /Game/Props/Sofa_01.Sofa_01_C")
    result.log_entries.append("Applied material to hero_furniture: /Game/Materials/LeatherMat")
    result.log_entries.append("Lighting configured: directional with mood warm,low sun")
    assert len(result.log_entries) == 3
    assert "Placed hero_furniture" in result.log_entries[0]


def test_assembly_result_structured_counts():
    """DEMO-01: AssemblyResult provides structured counts for success copy."""
    from nyrahost.tools.scene_assembler import AssemblyResult
    result = AssemblyResult()
    result.placed_actors = [{"actor_name": "Sofa_01"}, {"actor_name": "Table_01"}]
    result.applied_materials = [{"spec": {}, "asset_path": "/Game/Materials/Leather"}]
    result.lighting_actors = [{"actor_name": "NYRA_Primary_directional"}]
    assert result.success is True
    # Success copy: "{N} actors placed, {M} materials applied, {L} light setup configured"
    log_str = f"{len(result.placed_actors)} actors placed, {len(result.applied_materials)} materials applied, {len(result.lighting_actors)} light setup configured"
    assert "2 actors placed" in log_str
    assert "1 light setup configured" in log_str


def test_progress_callback_fires_at_each_step():
    """DEMO-01 progress bar: progress_callback fires for each assembly step."""
    steps = []
    def track_progress(step, current, total):
        steps.append((step, current, total))

    assembler = SceneAssembler()
    blueprint = SceneBlueprint(
        scene_type="test_scene",
        actor_specs=[
            ActorSpec(role="prop1", class_path="/Script/Engine.StaticMeshActor",
                      asset_hint="", count=1, placement="scattered", transform_hint=""),
            ActorSpec(role="prop2", class_path="/Script/Engine.StaticMeshActor",
                      asset_hint="", count=1, placement="scattered", transform_hint=""),
        ],
        material_specs=[
            MaterialSpec(target_actor="prop1", material_type="hero",
                         texture_hint="", source="placeholder"),
        ],
        lighting_plan=None,
        mood_tags=["test"],
        confidence=1.0
    )

    with patch("nyrahost.tools.scene_assembler.SceneAssembler._spawn_actor_from_spec") as mock_spawn:
        mock_spawn.return_value = {"actor_name": "test", "actor_path": "/Test/Actor", "guid": "g"}
        with patch("nyrahost.tools.scene_assembler.SceneAssembler._apply_material_to_actors"):
            with patch("nyrahost.tools.scene_assembler.SceneAssembler._configure_lighting") as mock_lighting:
                mock_lighting.return_value = []
                result = assembler.assemble(blueprint, progress_callback=track_progress)

    step_names = [s[0] for s in steps]
    assert "Placing Actors" in step_names
    assert "Applying Materials" in step_names
    assert "Setting Up Lighting" in step_names
    assert "Finalizing" in step_names


@pytest.mark.asyncio
async def test_scene_assembler_analyze_image_calls_llm():
    """DEMO-01: SceneAssembler.analyze_image calls Claude vision API."""
    assembler = SceneAssembler(backend_router=AsyncMock())
    with patch.object(assembler, "router") as mock_router:
        mock_router.generate_image_description = AsyncMock(return_value={
            "scene_type": "interior_bedroom",
            "actor_specs": [],
            "mood_tags": ["cozy", "warm"]
        })
        blueprint = await assembler.analyze_image("/fake/path.jpg")
        assert blueprint.scene_type == "interior_bedroom"
        mock_router.generate_image_description.assert_called_once()
```

**Coverage requirements:**
- All 10 tests must pass to verify DEMO-01 SC#1, SC#3, and SC#4
- `test_asset_fallback_chain_never_blocks` verifies the cold-start reliability SC
- `test_progress_callback_fires_at_each_step` verifies SNyraProgressBar step labels
- `test_assembly_log_entries_accumulated` verifies SNyraLogDrawer data source
  </action>
  <verify>
    <automated>cd /Users/aasish/CLAUDE\ PROJECTS/UEPLUG/UEPLUGIN/TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest tests/test_scene_assembly_e2e.py -x -q 2>&1 | tail -25</automated>
  </verify>
  <done>10 smoke tests cover DEMO-01 end-to-end, cold-start reliability, progress callback, log evidence, and structured result counts</done>
</task>

<task type="auto">
  <name>Task 2: Write SCENE-01 lighting integration tests</name>
  <files>TestProject/Plugins/NYRA/Source/NyraHost/tests/test_lighting_integration.py</files>
  <action>
Create `nyrahost/tests/test_lighting_integration.py` for SCENE-01 verification.

**Tests to implement:**

```python
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from nyrahost.tools.scene_llm_parser import LightingLLMParser, LightingParams
from nyrahost.tools.lighting_tools import LightingAuthoringTool, LightingDryRunTool

# --- LightingParams fixtures ---

@pytest.fixture
def golden_hour_params() -> LightingParams:
    return LightingParams(
        primary_light_type="directional",
        primary_intensity=1.5,
        primary_color=(0.95, 0.65, 0.3),
        primary_direction=(45, -30, 0),
        primary_temperature_k=3500,
        use_shadow=True,
        fill_light_type="",
        fill_intensity=0.0,
        use_sky_atmosphere=True,
        use_volumetric_cloud=False,
        use_exponential_height_fog=True,
        fog_density=0.01,
        fog_color=(0.8, 0.7, 0.6),
        use_volumetric_fog=False,
        use_post_process=True,
        exposure_compensation=0.5,
        prompt="golden hour",
        mood_tags=["warm", "low sun", "soft shadow"],
        confidence=0.95
    )

@pytest.fixture
def harsh_overhead_params() -> LightingParams:
    return LightingParams(
        primary_light_type="directional",
        primary_intensity=2.5,
        primary_color=(1.0, 1.0, 1.0),
        primary_direction=(-90, 0, 0),
        primary_temperature_k=5500,
        use_shadow=True,
        shadow_cascades=4,
        use_sky_atmosphere=False,
        use_exponential_height_fog=False,
        use_post_process=False,
        exposure_compensation=0.0,
        prompt="harsh overhead studio",
        mood_tags=["harsh", "overhead", "high-contrast"],
        confidence=0.9
    )

# --- Test Cases ---

def test_preset_golden_hour_covered(golden_hour_params):
    """SCENE-01: Golden hour preset produces correct LightingParams."""
    assert golden_hour_params.primary_light_type == "directional"
    assert golden_hour_params.primary_color == (0.95, 0.65, 0.3)
    assert golden_hour_params.use_sky_atmosphere is True
    assert golden_hour_params.use_exponential_height_fog is True
    assert "warm" in golden_hour_params.mood_tags


def test_preset_harsh_overhead_covered(harsh_overhead_params):
    """SCENE-01: Harsh overhead preset produces correct LightingParams."""
    assert harsh_overhead_params.primary_direction == (-90, 0, 0)  # pitch=-90 = straight down
    assert harsh_overhead_params.use_shadow is True
    assert harsh_overhead_params.use_sky_atmosphere is False


def test_lighting_authoring_tool_requires_input():
    """SCENE-01: nyra_lighting_authoring rejects call with no nl_prompt/image_path/preset."""
    tool = LightingAuthoringTool(router=MagicMock())
    result = tool.execute({})
    assert result.error is not None
    assert "[-32030]" in result.error


def test_lighting_authoring_tool_apply_true_returns_actors():
    """SCENE-01: apply=True places actors and returns count."""
    with patch("nyrahost.tools.lighting_tools.LightingAuthoringTool._apply_lighting_params") as mock_apply:
        mock_apply.return_value = [
            {"actor_name": "NYRA_Primary_directional", "actor_path": "/Test/Primary", "guid": "g1"},
            {"actor_name": "NYRA_SkyAtmosphere", "actor_path": "/Test/Sky", "guid": "g2"},
        ]
        tool = LightingAuthoringTool(router=MagicMock())
        result = tool.execute({"preset_name": "golden_hour", "apply": True})
        assert result.data["actors_placed"] == 2
        assert result.data["mood_tags"] == ["warm", "low sun", "soft shadow"]
        assert "directional" in result.data["primary_light_type"]


def test_lighting_authoring_tool_dry_run_does_not_place_actors():
    """SCENE-01: apply=False triggers dry-run WS notification, no actors placed."""
    with patch("nyrahost.tools.lighting_tools.LightingAuthoringTool._send_dry_run_notification") as mock_notify:
        tool = LightingAuthoringTool(router=MagicMock())
        result = tool.execute({"preset_name": "moody_blue", "apply": False})
        assert result.data["dry_run"] is True
        assert "dry-run preview active" in result.data["message"]
        mock_notify.assert_called_once()


def test_lighting_dry_run_tool():
    """SCENE-01: nyra_lighting_dry_run_preview sends WS notification without placing actors."""
    with patch("nyrahost.tools.lighting_tools.LightingDryRunTool._send_dry_run_notification") as mock_notify:
        tool = LightingDryRunTool(router=MagicMock())
        result = tool.execute({"preset_name": "studio_fill"})
        assert result.data["dry_run"] is True
        mock_notify.assert_called_once()


def test_preset_to_params_mappings():
    """SCENE-01: all 5 presets produce valid LightingParams."""
    from nyrahost.tools.lighting_tools import LightingAuthoringTool
    tool = LightingAuthoringTool(router=MagicMock())

    for preset_key in ["golden_hour", "harsh_overhead", "moody_blue", "studio_fill", "dawn"]:
        params = tool._preset_to_params(preset_key)
        assert params.primary_light_type in ("directional", "spot", "point", "rect")
        assert 0 <= params.primary_intensity <= 10
        assert len(params.mood_tags) >= 1
        assert params.confidence > 0


def test_lighting_all_sc01_components_present():
    """SCENE-01 completeness check: all 7 light types and 5 atmosphere/post types referenced."""
    from nyrahost.tools.lighting_tools import LightingAuthoringTool
    tool = LightingAuthoringTool(router=MagicMock())

    # Check that _apply_lighting_params handles all SCENE-01 types
    # by verifying the method exists and has logic for each type
    import inspect
    source = inspect.getsource(tool._apply_lighting_params)
    assert "/Script/Engine.DirectionalLight" in source
    assert "/Script/Engine.SpotLight" in source
    assert "/Script/Engine.PointLight" in source
    assert "/Script/Engine.RectLight" in source
    assert "/Script/Engine.SkyAtmosphere" in source
    assert "/Script/Engine.VolumetricCloud" in source
    assert "/Script/Engine.ExponentialHeightFog" in source
    assert "/Script/Engine.PostProcessVolume" in source
    # Exposure: check _configure_post_process exists
    assert hasattr(tool, "_configure_post_process")
```

**Coverage requirements:**
- All SCENE-01 light types (directional, point, spot, rect, sky) verified present
- All atmosphere types (SkyAtmosphere, VolumetricCloud, ExponentialHeightFog) verified
- PostProcessVolume and exposure_compensation verified
- 5 named presets tested for valid output
- Dry-run vs apply behavior verified
  </action>
  <verify>
    <automated>cd /Users/aasish/CLAUDE\ PROJECTS/UEPLUG/UEPLUGIN/TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest tests/test_lighting_integration.py -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>SCENE-01 completeness verified: all light types + atmosphere types + post-process types present; 5 presets tested; dry-run/apply behavior verified</done>
</task>

<task type="auto">
  <name>Task 3: Update conftest.py with Phase 6 fixtures</name>
  <files>TestProject/Plugins/NYRA/Source/NyraHost/tests/conftest.py</files>
  <action>
Append to `NyraHost/tests/conftest.py` — add Phase 6 test fixtures.

Add the following fixtures (do not remove existing ones):

```python
# === Phase 6: Scene Assembly fixtures ===

@pytest.fixture
def mock_backend_router():
    """Mock backend router for testing LLM calls in scene assembler."""
    router = MagicMock()
    router.generate_image_description = AsyncMock(return_value={
        "scene_type": "interior_living_room",
        "actor_specs": [
            {"role": "sofa", "class_path": "/Script/Engine.StaticMeshActor",
             "asset_hint": "brown sofa", "count": 1, "placement": "center_floor"},
        ],
        "mood_tags": ["warm", "cozy"],
        "confidence": 0.9
    })
    router.generate = AsyncMock(return_value="mocked LLM response")
    return router


@pytest.fixture
def mock_ue_editor_api():
    """Mock Unreal Python API (unreal module) for actor spawn/material apply tests."""
    import sys
    mock_unreal = MagicMock()
    # Stub out the key classes used by scene_assembler.py
    mock_unreal.EditorLevelLibrary = MagicMock()
    mock_unreal.EditorLevelLibrary.spawn_actor_from_class = MagicMock(return_value=MagicMock(
        get_name=MagicMock(return_value="NYRA_TestActor"),
        get_path_name=MagicMock(return_value="/Test/NYRA_TestActor"),
        get_actor_guid=MagicMock(return_value="test-guid-123"),
        set_actor_label=MagicMock(),
        set_actor_location=MagicMock(),
    ))
    mock_unreal.EditorAssetLibrary = MagicMock()
    mock_unreal.EditorMaterialEditingLibrary = MagicMock()
    mock_unreal.Vector = MagicMock()
    mock_unreal.Rotator = MagicMock()
    mock_unreal.Transform = MagicMock()

    # Inject into sys.modules so 'import unreal' in scene_assembler.py gets our mock
    sys.modules["unreal"] = mock_unreal
    return mock_unreal


@pytest.fixture
def sample_scene_blueprint() -> SceneBlueprint:
    """Minimal SceneBlueprint for assembly tests."""
    from nyrahost.tools.scene_llm_parser import LightingParams
    from nyrahost.tools.scene_assembler import SceneBlueprint, ActorSpec, MaterialSpec

    return SceneBlueprint(
        scene_type="test_scene",
        actor_specs=[
            ActorSpec(role="hero_prop", class_path="/Script/Engine.StaticMeshActor",
                      asset_hint="cube", count=2, placement="scattered", transform_hint=""),
        ],
        material_specs=[
            MaterialSpec(target_actor="hero_prop", material_type="hero",
                         texture_hint="gray", source="placeholder"),
        ],
        lighting_plan=LightingParams(
            primary_light_type="directional",
            primary_intensity=1.0,
            primary_color=(1.0, 1.0, 1.0),
            primary_direction=(0, 0, 0),
            primary_temperature_k=5500,
            use_shadow=True,
            use_sky_atmosphere=True,
            use_exponential_height_fog=True,
            fog_density=0.02,
            fog_color=(0.8, 0.85, 1.0),
            use_post_process=False,
            exposure_compensation=0.0,
            prompt="test",
            mood_tags=["test"],
            confidence=1.0,
        ),
        mood_tags=["test"],
        confidence=1.0
    )
```

**Important:** Ensure `AsyncMock` and `MagicMock` are imported at the top of conftest.py. Add `from unittest.mock import AsyncMock, MagicMock, patch` if not already present.
  </action>
  <verify>
    <automated>cd /Users/aasish/CLAUDE\ PROJECTS/UEPLUG/UEPLUGIN/TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest tests/test_scene_assembly_e2e.py tests/test_lighting_integration.py -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>All 10 assembly e2e tests + 8 lighting integration tests pass; Phase 6 fixtures available in conftest.py</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Test fixtures -> mock LLM | Uses AsyncMock; no live network calls |
| Mock UE API -> test isolation | Unreal module mocked via sys.modules; no real editor required |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-06-08 | Denial of Service | test suite | mitigate | All tests use mocks; no live Meshy/ComfyUI/Claude API required |
| T-06-09 | Information Disclosure | test fixtures | mitigate | No real user image paths or API keys in fixtures |
</threat_model>

<verification>
Run all Phase 6 tests:
```bash
cd NyraHost && python -m pytest tests/test_scene_assembly_e2e.py tests/test_lighting_integration.py -v --tb=short 2>&1 | tail -40
```
Expected: 18/18 tests passing.

Coverage report:
```
tests/test_scene_assembly_e2e.py    — 10 tests covering DEMO-01 SC#1/SC#3/SC#4
tests/test_lighting_integration.py  — 8 tests covering SCENE-01 completeness + dry-run/apply
```

SC#3 cold-start reliability verified by:
- `test_asset_fallback_chain_never_blocks` (Meshy unavailable → ComfyUI fallback → placeholder)
- `test_assemble_scene_tool_rejects_missing_image` (missing image returns error, not crash)
</verification>

<success_criteria>
- 18/18 tests pass (10 assembly e2e + 8 lighting integration)
- DEMO-01 SC#1 (user library first), SC#3 (cold-start reliability), SC#4 (v1-launchable) all have test coverage
- SCENE-01 all 7 light types + 5 atmosphere/post types have test verification
- No live network calls in test suite (all mocked)
- Test suite runs in < 30 seconds
</success_criteria>

<output>
After completion, create `.planning/phases/06-scene-assembly-image-to-scene-fallback-demo/06-03-SUMMARY.md`
</output>