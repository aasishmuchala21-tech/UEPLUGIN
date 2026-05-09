---
phase: "06"
plan: "06-02"
type: execute
wave: 2
depends_on: ["06-01"]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/assembly_tools.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/asset_fallback_chain.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/scene_assembler.py
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraImageDropZone.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraRefImageTile.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraAssetChip.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraProgressBar.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraLogDrawer.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraImageDropZone.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraRefImageTile.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraAssetChip.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraProgressBar.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraLogDrawer.h
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_assembly_tools.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_asset_fallback_chain.py
autonomous: false
requirements:
  - DEMO-01
  - SCENE-01
user_setup:
  - service: meshy
    why: "DEMO-01 requires Meshy for hero asset generation when user library is empty"
    env_vars:
      - name: MESHY_API_KEY
        source: "Meshy Dashboard -> API Settings (https://dashboard.meshy.ai/api)"
  - service: comfyui
    why: "DEMO-01 requires ComfyUI for texture generation as fallback chain step 3"
    env_vars:
      - name: COMFYUI_HOST
        source: "ComfyUI running locally — default 127.0.0.1:8188"
must_haves:
  truths:
    - "User drops a reference image in SNyraImageDropZone and sees drag-over state with animated #C6BFFF border"
    - "SNyraProgressBar animates through all 4 steps: Placing Actors (N/M) → Applying Materials (N/M) → Setting Up Lighting → Finalizing"
    - "DEMO-01 end-to-end: drop image → LLM analysis → 5-20 actors placed + materials applied + lighting configured"
    - "Asset fallback chain never blocks: library → Meshy → ComfyUI texture → placeholder material"
    - "SNyraLogDrawer shows assembly evidence (actor names, material paths, lighting config)"
    - "SCENE-01 lighting is triggered as part of assembly (no separate invocation needed)"
  artifacts:
    - path: "NyraHost/src/nyrahost/tools/scene_assembler.py"
      provides: "SceneAssembler.analyze_image (LLM) + assemble() orchestrator"
      min_lines: 120
    - path: "NyraHost/src/nyrahost/tools/assembly_tools.py"
      provides: "AssembleSceneTool (nyra_assemble_scene MCP tool)"
      exports:
        - "AssembleSceneTool"
    - path: "NyraHost/src/nyrahost/tools/asset_fallback_chain.py"
      provides: "AssetFallbackChain: library → Meshy → ComfyUI → placeholder"
    - path: "NyraEditor/Private/Panel/SNyraImageDropZone.cpp"
      provides: "DEMO-01 primary entry point, drag-drop + clipboard paste"
    - path: "NyraEditor/Private/Panel/SNyraProgressBar.cpp"
      provides: "Step-segment progress bar with lavender fill #C6BFFF"
    - path: "NyraEditor/Private/Panel/SNyraLogDrawer.cpp"
      provides: "Collapsible bottom drawer with log entry rows"
  key_links:
    - from: "SNyraImageDropZone.cpp"
      to: "scene_assembler.py"
      via: "WS notification on image drop triggers analyze_image()"
      pattern: "OnImageDropped.*analyze_image"
    - from: "assembly_tools.py AssembleSceneTool"
      to: "scene_assembler.py SceneAssembler.assemble()"
      via: "progress_callback fires at each step, sends WS message to panel"
      pattern: "progress_callback.*assembly_progress"
    - from: "asset_fallback_chain.py AssetFallbackChain"
      to: "meshy_tools.py MeshyImageTo3DTool"
      via: "meshy_tool.execute() called when library returns no match"
      pattern: "resolve_actor_asset.*MeshyImageTo3DTool"
    - from: "SNyraProgressBar.cpp"
      to: "assembly_tools.py"
      via: "WS message 'assembly_progress' animates FillColorAndOpacity"
      pattern: "assembly_progress.*step.*current.*total"
checkpoints:
  - type: checkpoint:human-verify
    gate: blocking
    what-built: "SNyraImageDropZone — the primary entry point for DEMO-01. User drops a reference image, panel shows drag-over state, thumbnail appears, progress bar animates through assembly steps."
    how-to-verify:
      - "Open UE editor, load NYRA chat panel"
      - "Locate the SNyraImageDropZone in the assembly UI panel (bottom or side dock)"
      - "Drag any JPG/PNG from file explorer over the drop zone — verify dashed #C6BFFF border pulses (lavender border animates, glass overlay brightens)"
      - "Drop the image — verify thumbnail appears in Reference Image strip"
      - "Verify chat auto-scrolls with agent message: 'I see a [scene type]. Assembling now...'"
      - "Watch progress bar animate through steps: 'Placing Actors (N/M)' → 'Applying Materials (N/M)' → 'Setting Up Lighting' → 'Finalizing'"
      - "On completion: verify success state (green checkmark in status pill), log drawer briefly auto-expands"
    resume-signal: "Type 'approved' or describe issues"
---

<objective>
Implement DEMO-01: end-to-end Image-to-Scene assembly. Reference image drop zone → LLM analysis → scene description → actor list + material list + lighting plan → assembly executor with full asset fallback chain (user library → Meshy → ComfyUI → placeholder material) → progress bar + log drawer. Also implements SNyraRefImageTile, SNyraAssetChip, SNyraProgressBar, SNyraLogDrawer, and SNyraImageDropZone per 06-UI-SPEC.md.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/06-scene-assembly-image-to-scene-fallback-demo/06-UI-SPEC.md
@.planning/phases/06-scene-assembly-image-to-scene-fallback-demo/06-01-SCENE-01-lighting-authoring-PLAN.md
@TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/actor_tools.py
@TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/material_tools.py
@TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/lighting_tools.py
@TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/meshy_tools.py
@TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/comfyui_tools.py
@TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/staging.py
</context>

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From nyrahost/tools/actor_tools.py (existing, ACT-04):
```python
class ActorSpawnTool(NyraTool):
    name = "nyra_actor_spawn"
    # execute(params) -> NyraToolResult with actor_name, actor_path, guid

class ActorTransformTool(NyraTool):
    name = "nyra_actor_transform"
    # execute(params) -> NyraToolResult with status: "ok"
```

From nyrahost/tools/material_tools.py (existing, ACT-05):
```python
# Material instance operations: read/write scalar/vector/texture params
# Pattern: use unreal.Unreal滨江.EditorMaterialEditingLibrary or similar
```

From nyrahost/tools/lighting_tools.py (from 06-01):
```python
class LightingAuthoringTool(NyraTool):
    name = "nyra_lighting_authoring"
    # execute(params) -> NyraToolResult with actors_placed, mood_tags
```

From nyrahost/tools/staging.py (Phase 5):
```python
class StagingManifest:
    def add_pending(self, job_id, tool, operation, input_ref, api_response=None): ...
    def update_job(self, job_id, ...): ...
    def get_job(self, job_id) -> JobEntry | None
    def find_by_hash(self, tool, operation, input_hash) -> str | None
```

From nyrahost/tools/meshy_tools.py (Phase 5):
```python
class MeshyImageTo3DTool(NyraTool):
    name = "nyra_meshy_image_to_3d"
    # execute(params) -> NyraToolResult with job_id, status: "pending"
```

From nyrahost/tools/comfyui_tools.py (Phase 5):
```python
class ComfyUIRunWorkflowTool(NyraTool):
    name = "nyra_comfyui_run_workflow"
    # execute(params) -> NyraToolResult with job_id, status: "pending"
```

From SNyraChatPanel.cpp (existing Slate pattern):
```cpp
// WS communication: FNyraWsClient::SendMessage(TEXT("assembly_progress"), Payload)
// Panel receives streaming updates, renders progress bar segments
// Log drawer: collapsible bottom drawer, auto-expands on completion
```
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: scene_assembler.py — scene analysis + assembly orchestrator</name>
  <files>TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/scene_assembler.py</files>
  <action>
Create `nyrahost/tools/scene_assembler.py` — the core assembly engine for DEMO-01.

**`SceneAssembler` class:**

```python
@dataclass
class SceneBlueprint:
    """Structured output from LLM image analysis."""
    scene_type: str                    # "interior_living_room", "outdoor_forest", "urban_street"
    actor_specs: list[ActorSpec]       # what actors to place
    material_specs: list[MaterialSpec] # what materials to apply
    lighting_plan: LightingParams      # from scene_llm_parser.py
    mood_tags: list[str]               # ["cozy", "warm", "cluttered"]
    confidence: float

@dataclass
class ActorSpec:
    role: str          # "hero_furniture", "background_prop", "floor", "wall"
    class_path: str    # UE class or asset path, e.g. "/Script/Engine.StaticMeshActor"
    asset_path: str    # specific asset, e.g. "/Game/Props/Sofa_01.Sofa_01"
    count: int = 1     # how many to place
    placement: str     # "scattered", "grid", "clustered"
    transform_hint: str  # "near_window", "center_floor", "against_wall"

@dataclass
class MaterialSpec:
    target_actor: str   # actor_path or role filter
    material_type: str # "hero", "background", "floor"
    source: str        # "library", "meshy", "comfyui", "placeholder"
    asset_path: str    # resolved UE asset path
    fallback_path: str # if primary fails


class SceneAssembler:
    """End-to-end assembly: reference image → scene blueprint → placed actors."""

    def __init__(self, backend_router=None, staging_manifest=None):
        self.router = backend_router
        self.staging = staging_manifest or StagingManifest()
        self.parser = LightingLLMParser(backend_router=backend_router)

    async def analyze_image(self, image_path: str) -> SceneBlueprint:
        """Call Claude Opus to analyze the reference image and produce SceneBlueprint.

        System prompt:
        "You are NYRA's scene analysis engine. Analyze this reference image and output a
        structured JSON scene blueprint for UE scene assembly.

        Return:
        {
          scene_type: string,           // e.g. "interior_living_room"
          actor_specs: [...],           // 5-20 actors to place
          material_specs: [...],        // materials for each role
          lighting_plan: { ... },       // lighting params (see LightingParams schema)
          mood_tags: [...],             // 3-5 mood descriptors
          confidence: float             // 0-1
        }

        ActorSpec schema:
        {
          role: string,        // hero_prop | background_prop | floor | wall | ceiling | lighting_actor
          class_path: string,  // /Script/Engine.StaticMeshActor (default)
          asset_hint: string,  // natural language hint for asset search
          count: int,          // 1-5
          placement: string,   // scattered | grid | clustered | linear
          transform_hint: string  // near_window | center_floor | against_wall | ...
        }

        MaterialSpec schema:
        {
          target_actor: string,   // role or asset_path
          material_type: string,  // hero | background | floor
          texture_hint: string,   // natural language for texture search
          source: string          // library | meshy | comfyui | placeholder
        }

        Prefer user asset library first. Only request generation (meshy/comfyui) for hero assets
        that have no close library match. Floor/wall/ceiling materials use library or ComfyUI.
        "
        """
        # 1. Read image bytes -> base64
        import base64

        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        # 2. Call Claude Opus via backend router
        resp = await self.router.generate_image_description(image_path)  # or similar method
        # ... parse resp JSON into SceneBlueprint ...
        return blueprint

    def assemble(self, blueprint: SceneBlueprint, progress_callback=None) -> AssemblyResult:
        """Execute the assembly: place actors → apply materials → configure lighting.

        Args:
            blueprint: SceneBlueprint from analyze_image
            progress_callback: callable(string step_name, int current, int total) for WS streaming

        Returns:
            AssemblyResult with placed_actors, applied_materials, lighting_actors, log_entries
        """
        results = AssemblyResult()

        # Step 1: Place actors (user library first, then generate)
        for i, spec in enumerate(blueprint.actor_specs):
            progress_callback("Placing Actors", i + 1, len(blueprint.actor_specs))

            # Try user library via asset_search (Phase 4)
            asset_path = self._resolve_asset(spec.asset_hint)

            if not asset_path and spec.source in ("meshy", "comfyui"):
                # Generate missing hero asset via Phase 5 tools
                asset_path = self._generate_asset(spec, progress_callback)

            if not asset_path:
                # Place a placeholder cube so scene still assembles
                asset_path = "/Engine/BasicShapes/Cube"

            actor_result = self._spawn_actor_from_spec(spec, asset_path)
            results.placed_actors.append(actor_result)
            results.log_entries.append(f"Placed {spec.role}: {actor_result['actor_path']}")

        # Step 2: Apply materials
        for i, spec in enumerate(blueprint.material_specs):
            progress_callback("Applying Materials", i + 1, len(blueprint.material_specs))

            mat_path = self._resolve_material(spec.texture_hint, spec.source)
            if not mat_path:
                mat_path = self._generate_material(spec, progress_callback)
            if not mat_path:
                mat_path = "/Engine/BasicShapes/BasicAssetMaterial"  # placeholder

            self._apply_material_to_actors(spec.target_actor, mat_path, results.placed_actors)
            results.applied_materials.append({"spec": spec, "asset_path": mat_path})
            results.log_entries.append(f"Applied material to {spec.target_actor}: {mat_path}")

        # Step 3: Configure lighting (delegate to LightingAuthoringTool)
        progress_callback("Setting Up Lighting", 1, 1)
        lighting_tool = LightingAuthoringTool(router=self.router)
        lit_result = lighting_tool.execute({
            "reference_image_path": blueprint.lighting_plan.reference_image_path
            if hasattr(blueprint.lighting_plan, 'reference_image_path') else "",
            "nl_prompt": f"{blueprint.mood_tags[0] if blueprint.mood_tags else 'default'} lighting",
            "apply": True
        })
        results.lighting_actors = lit_result.data.get("actors_placed", [])
        results.log_entries.append(f"Lighting configured: {lit_result.data.get('message', '')}")

        progress_callback("Finalizing", 1, 1)
        return results

    def _resolve_asset(self, asset_hint: str) -> Optional[str]:
        """Use Phase 4 asset_search to find a matching asset in the user's library."""
        from nyrahost.tools.asset_search import AssetSearchTool
        searcher = AssetSearchTool()
        result = searcher.execute({"query": asset_hint, "limit": 3})
        if result.data and result.data.get("assets"):
            return result.data["assets"][0]["asset_path"]
        return None

    def _generate_asset(self, spec: ActorSpec, progress_callback) -> Optional[str]:
        """Generate missing hero asset via Meshy or ComfyUI per fallback chain."""
        if spec.source == "meshy":
            tool = MeshyImageTo3DTool()
            res = tool.execute({"image_path": spec.asset_hint})
            # Poll until imported — placeholder stub
            ...
        elif spec.source == "comfyui":
            tool = ComfyUIRunWorkflowTool()
            ...
        return None

    def _spawn_actor_from_spec(self, spec: ActorSpec, asset_path: str) -> dict:
        """Spawn a UE actor from an ActorSpec."""
        import unreal
        class_name = spec.class_path or "/Script/Engine.StaticMeshActor"
        actor_class = unreal.UObject.load_system_class(class_name)

        transform = self._placement_to_transform(spec.placement, spec.transform_hint)
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(actor_class, transform)
        actor.set_actor_label(f"NYRA_{spec.role}_{actor.get_name()}")

        return {
            "actor_name": actor.get_name(),
            "actor_path": actor.get_path_name(),
            "guid": str(actor.get_actor_guid()),
            "role": spec.role
        }

    def _placement_to_transform(self, placement: str, hint: str) -> unreal.Transform:
        """Map placement strategy + transform_hint to UE Transform."""
        import random
        if placement == "scattered":
            offset = (random.uniform(-200, 200), random.uniform(-200, 200), 0)
        elif placement == "grid":
            offset = (0, 0, 0)
        elif placement == "clustered":
            offset = (random.uniform(-50, 50), random.uniform(-50, 50), 0)
        else:
            offset = (0, 0, 0)

        loc = unreal.Vector(offset[0], offset[1], offset[2])
        rot = unreal.Rotator(0, 0, 0)
        return unreal.Transform(loc, rot, unreal.Vector(1, 1, 1))
```

**AssemblyResult dataclass:**
```python
@dataclass
class AssemblyResult:
    placed_actors: list[dict] = field(default_factory=list)
    applied_materials: list[dict] = field(default_factory=list)
    lighting_actors: list[dict] = field(default_factory=list)
    log_entries: list[str] = field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None
```

**Key behaviors:**
- `assemble()` is NOT async (calls synchronous Unreal Python API via `unreal` module)
- `analyze_image()` IS async (calls Claude Opus vision)
- `progress_callback(step, current, total)` is called at each step for WS streaming
- All actor labels prefixed `NYRA_` for undo tracking (inherited from SCENE-01)
- Asset fallback chain: library → Meshy → ComfyUI texture → placeholder (never block on unavailable service)
- Log entries accumulated and returned in `AssemblyResult.log_entries`
  </action>
  <verify>
    <automated>cd /Users/aasish/CLAUDE\ PROJECTS/UEPLUG/UEPLUGIN/TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest tests/test_assembly_tools.py -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>SceneAssembler.analyze_image calls LLM; assemble() orchestrates actor spawn → material apply → lighting config; progress_callback fires at every step; fallback chain never blocks on unavailable service</done>
</task>

<task type="auto">
  <name>Task 2: assembly_tools.py — nyra_assemble_scene MCP tool + asset_fallback_chain</name>
  <files>TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/assembly_tools.py, TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/asset_fallback_chain.py</files>
  <action>
Create `nyrahost/tools/assembly_tools.py` and `asset_fallback_chain.py`.

**asset_fallback_chain.py — AssetFallbackChain class:**

```python
class AssetFallbackChain:
    """Asset resolution with user-library-first fallback chain per SC#1."""

    def __init__(self, asset_searcher=None, meshy_tool=None, comfyui_tool=None):
        self.asset_searcher = asset_searcher or AssetSearchTool()
        self.meshy_tool = meshy_tool or MeshyImageTo3DTool()
        self.comfyui_tool = comfyui_tool or ComfyUIRunWorkflowTool()
        self.staging = StagingManifest()

    def resolve_actor_asset(self, hint: str, role: str) -> AssetResolutionResult:
        """Resolve an asset for an actor spec. Priority: user library → Meshy → ComfyUI → placeholder."""
        result = AssetResolutionResult(source="library")

        # Step 1: User library
        if role in ("hero_prop", "hero_furniture"):
            search_result = self.asset_searcher.execute({"query": hint, "limit": 5})
            if search_result.data and search_result.data.get("assets"):
                best = search_result.data["assets"][0]
                result.asset_path = best["asset_path"]
                result.source = "library"
                result.quality_score = 0.9
                return result

        # Step 2: Meshy (for hero meshes not in library)
        if role == "hero_prop":
            job_result = self.meshy_tool.execute({"image_path": hint})
            if job_result.error is None:
                job_id = job_result.data["job_id"]
                result.asset_path = self._wait_for_meshy_import(job_id)
                result.source = "meshy"
                result.quality_score = 0.85
                return result

        # Step 3: ComfyUI texture (for hero materials not in library)
        if role == "hero_material":
            workflow = self._build_tex_gen_workflow(hint)
            job_result = self.comfyui_tool.execute({"workflow_json": workflow})
            if job_result.error is None:
                result.asset_path = self._wait_for_comfyui_texture(job_result.data["job_id"])
                result.source = "comfyui"
                result.quality_score = 0.75
                return result

        # Step 4: Placeholder
        result.asset_path = "/Engine/BasicShapes/Cube"
        result.source = "placeholder"
        result.quality_score = 0.3
        return result

    def _wait_for_meshy_import(self, job_id: str, timeout: float = 600) -> Optional[str]:
        """Poll staging manifest for Meshy job completion and UE import."""
        import time
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            job = self.staging.get_job(job_id)
            if job and job.ue_asset_path:
                return job.ue_asset_path
            if job and job.ue_import_status in ("failed", "timeout"):
                return None
            time.sleep(5)
        return None

    def _build_tex_gen_workflow(self, hint: str) -> dict:
        """Build a minimal ComfyUI workflow JSON for texture generation from hint."""
        return {"nodes": [], "prompt": hint}

@dataclass
class AssetResolutionResult:
    asset_path: str
    source: str    # "library" | "meshy" | "comfyui" | "placeholder"
    quality_score: float  # 0-1
    generation_time: Optional[float] = None
```

**assembly_tools.py — AssembleSceneTool:**

```python
class AssembleSceneTool(NyraTool):
    """DEMO-01: Assemble a full UE scene from a reference image.

    End-to-end cold path: user drops reference image → NYRA analyzes it → assembles
    5-20 actors, hero materials (user library first → generate via Meshy/ComfyUI),
    light setup, ready in Level Editor.
    """
    name = "nyra_assemble_scene"
    description = (
        "Assemble a complete UE scene from a reference image. "
        "Places 5-20 actors, applies hero materials, configures lighting. "
        "Prefers your asset library first; generates missing assets via Meshy or ComfyUI. "
        "Works when Meshy is unavailable (ComfyUI fallback or placeholder material). "
        "Progress streamed to the NYRA panel via WS."
    )
    parameters = {
        "type": "object",
        "properties": {
            "reference_image_path": {
                "type": "string",
                "description": "Absolute path to the reference image on disk."
            },
            "scene_type_hint": {
                "type": "string",
                "description": "Optional scene type hint: 'interior', 'exterior', 'landscape', 'urban'."
            },
            "dry_run": {
                "type": "boolean",
                "default": False,
                "description": "If True, preview only — returns actor/material/lighting plan without placing anything."
            }
        },
        "required": ["reference_image_path"]
    }

    def execute(self, params: dict) -> NyraToolResult:
        from pathlib import Path

        image_path = params["reference_image_path"]

        # Validate image exists
        if not Path(image_path).exists():
            return NyraToolResult.err(f"[-32031] Reference image not found: {image_path}")

        log.info("assembly_started", image_path=image_path)

        # Step 1: Analyze image (LLM)
        self._send_progress("Analyzing Image", 0, 1)
        assembler = SceneAssembler(backend_router=self._router)
        blueprint = asyncio.run(assembler.analyze_image(image_path))

        if params.get("dry_run"):
            return NyraToolResult.ok({
                "dry_run": True,
                "scene_type": blueprint.scene_type,
                "actor_count": len(blueprint.actor_specs),
                "material_count": len(blueprint.material_specs),
                "mood_tags": blueprint.mood_tags,
                "lighting_type": blueprint.lighting_plan.primary_light_type,
                "message": f"Dry-run: would place {len(blueprint.actor_specs)} actors, apply {len(blueprint.material_specs)} materials, configure {blueprint.lighting_plan.primary_light_type} lighting"
            })

        # Step 2: Assemble (actor spawn → material apply → lighting)
        self._send_progress("Assembling Scene", 0, 1)
        result = assembler.assemble(blueprint, progress_callback=self._send_progress)

        # Step 3: Report
        if result.success:
            log.info("assembly_complete", actors=len(result.placed_actors),
                     materials=len(result.applied_materials), lighting=len(result.lighting_actors))
            return NyraToolResult.ok({
                "success": True,
                "actors_placed": len(result.placed_actors),
                "materials_applied": len(result.applied_materials),
                "lighting_configured": len(result.lighting_actors),
                "scene_type": blueprint.scene_type,
                "mood_tags": blueprint.mood_tags,
                "log_entries": result.log_entries,
                "message": (
                    f"Scene Assembled. {len(result.placed_actors)} actors placed, "
                    f"{len(result.applied_materials)} materials applied, "
                    f"{len(result.lighting_actors)} light setup configured. "
                    f"Your scene is ready in the Level Editor."
                )
            })
        else:
            log.warning("assembly_partial", error=result.error_message,
                       log_entries=result.log_entries)
            return NyraToolResult.ok({
                "success": False,
                "partial_actors": len(result.placed_actors),
                "partial_materials": len(result.applied_materials),
                "log_entries": result.log_entries,
                "error_message": f"Scene assembly failed: {result.error_message}. "
                                 f"NYRA made {len(result.placed_actors)} changes before stopping. "
                                 f"Check the log for details."
            })

    def _send_progress(self, step: str, current: int, total: int) -> None:
        """Send progress notification over WS to Slate panel."""
        msg = json.dumps({
            "type": "assembly_progress",
            "step": step,
            "current": current,
            "total": total
        })
        log.debug("progress", step=step, current=current, total=total)
```

Also update `nyrahost/mcp_server/__init__.py` to register `AssembleSceneTool`.

**Threat mitigations:**
- T-06-04: `reference_image_path` validated `Path.exists()` before analysis
- T-06-05: All assembly operations logged with `result.log_entries` for audit trail
- T-06-06: Meshy/ComfyUI unavailable → fallback to placeholder, never blocks assembly
  </action>
  <verify>
    <automated>cd /Users/aasish/CLAUDE\ PROJECTS/UEPLUG/UEPLUGIN/TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest tests/test_assembly_tools.py tests/test_asset_fallback_chain.py -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>nyra_assemble_scene accepts reference_image_path and returns structured result with actor/material/lighting counts; fallback chain never blocks; progress_callback fires at every step</done>
</task>

<task type="auto">
  <name>Task 3: Slate UI components — SNyraImageDropZone, SNyraRefImageTile, SNyraAssetChip, SNyraProgressBar, SNyraLogDrawer</name>
  <files>TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraImageDropZone.cpp, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraRefImageTile.cpp, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraAssetChip.cpp, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraProgressBar.cpp, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraLogDrawer.cpp, TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraImageDropZone.h, TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraRefImageTile.h, TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraAssetChip.h, TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraProgressBar.h, TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraLogDrawer.h</files>
  <action>
Implement all five Slate UI components per 06-UI-SPEC.md. All components use NYRADNA design tokens: glassmorphism, lavender #C6BFFF, Manrope+Inter font (Roboto fallback), 8-unit grid spacing.

**SNyraImageDropZone (primary DEMO-01 entry point):**

```cpp
// SNyraImageDropZone.h
class SNyraImageDropZone : public SCompoundWidget {
public:
    SLATE_BEGIN_ARGS(SNyraImageDropZone) {}
    SLATE_EVENT(FSimpleDelegate, OnImageDropped)
    SLATE_EVENT<FSimpleDelegate, const FString&>, OnDragEnter)
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);
    // States: idle (subtle dashed border #C6BFFF at 40%), drag-over (lavender border pulses, glass brightens), loading (spinner + "Analyzing..."), error (red border + error copy)
    // Drag-drop handling via OnDragEnter/OnDragLeave/OnDrop
    // Clipboard paste: Ctrl+V handler registers at panel level

private:
    TSharedPtr<SOverlay> OverlayContainer;
    FReply OnDrop(FDragDropOperation const& Op);
    void SetState(EDropZoneState State);
    enum class EDropZoneState { Idle, DragOver, Loading, Error };
    EDropZoneState CurrentState = EDropZoneState::Idle;
};
```

```cpp
// SNyraImageDropZone.cpp — Construct():
// SVerticalBox:
//   [Idle: SImage (dashed border via FSlateBrush) + STextBlock: "Drop a Reference Image" (Display 24px Semibold)
//          + STextBlock: "Drag and drop any image..." (Body 14px/400) + SImage: upload icon]
//   [Drag-over: border animates to #C6BFFF full, glass overlay FLinearColor(0.776,0.749,1,0.1)]
//   [Loading: SSpinBox with "Analyzing..." text, pulsing accent dot]
//   [Error: border red #FF4D6A, error copy below image area]
//
// Design tokens:
// Background: FLinearColor(0.05f, 0.05f, 0.08f, 1.f) // #0D0D14 (Secondary, 30%)
// Border idle: FLinearColor(0.776f, 0.749f, 1.f, 0.4f) // accent at 40%
// Border drag-over: FLinearColor(0.776f, 0.749f, 1.f, 1.f) // accent full
// Spacing: lg=24px padding, 16px gap between icon and text
// Font: Display 24px/600 (Roboto fallback), Body 14px/400 Regular
```

**SNyraRefImageTile (reference image thumbnail):**

```cpp
// 120x90px rounded (corner_radius 0.75rem = 12px in UE units)
// FSlateRoundedBoxBrush or SImage with Brush.set_image_size(120, 90)
// Hover: scale 1.02 (FWidgetTransform) with 150ms ease
// Selected: 2px accent border
// Loading: shimmer animation (gradient sweep)
// Overlay with delete button (X) in top-right corner on hover
```

```cpp
void SNyraRefImageTile::Construct(const FArguments& InArgs) {
    // FSlateBrush from image path via FSlateImageWrapper or FSlateDynamicBrush
    // Selected state: FLinearColor(0.776f, 0.749f, 1.f, 1.f) 2px border
    // States: idle, selected, loading (shimmer), error
}
```

**SNyraAssetChip (asset pill):**

```cpp
// Pill shape, 28px height, slate brush with alpha
// Unselected: alpha 0.6; Selected: alpha 1.0; Generating: animated dots suffix
// Font: Body 14px/400; label: 11px uppercase with 0.15em letter-spacing
// Width: auto-sized to text + 16px padding
```

```cpp
void SNyraAssetChip::Construct(const FArguments& InArgs) {
    // SButton with FButtonStyle, height 28px
    // FSlateColor text: unselected FLinearColor(0.6,0.6,0.7,1) → selected accent #C6BFFF
    // On click: InArgs._OnChipClicked.ExecuteIfBound()
}
```

**SNyraProgressBar (assembly progress):**

```cpp
// Lavender fill #C6BFFF on dark track #0D0D14
// Two modes: indeterminate (sliding shimmer animation) and determinate (segment steps)
// Segments labeled: "Placing Actors (N/M)" | "Applying Materials (N/M)" | "Setting Up Lighting" | "Finalizing"
```

```cpp
void SNyraProgressBar::Construct(const FArguments& InArgs) {
    // Track: FSlateBrush with TintedImage(FLinearColor(0.05f,0.05f,0.08f,1.f)) // #0D0D14
    // Fill: FSlateBrush with TintedImage(FLinearColor(0.776f,0.749f,1.f,1.f)) // #C6BFFF
    // Segments: SOverlay with multiple SFillProgressBar widgets OR one SProgressBar with animated FillColorAndOpacity
    // Step label: STextBlock below bar, Body 14px/400, current/total
    // Indeterminate: FSlateBrush with AnimatedSequenceBrush (shimmer sweep)
}
```

**SNyraLogDrawer (assembly evidence):**

```cpp
// Collapsible bottom drawer, FLinearColor(0.04,0.04,0.08,1) background (#050507 at 40% opacity tint)
// Header: "Assembly Log" (Label 11px uppercase letter-spacing 0.15em) + collapse button
// Content: SVirtualizingListView of FLogEntry rows
// Each row: timestamp (Label role, 11px) + message (Body 14px)
// Auto-expands briefly on completion (3 seconds), then collapses
```

```cpp
void SNyraLogDrawer::Construct(const FArguments& InArgs) {
    // SExpandableArea for collapse/expand
    // Content: SScrollBox containing log entries
    // Auto-expand: FWidgetAnimation, 3s delay, then collapse
    // Max height: 200px when expanded
}
```

**Registration in NyraEditorModule.cpp:**
```cpp
// Register all five Slate components as dock panel extensions
// Add SNyraImageDropZone + SNyraProgressBar + SNyraLogDrawer to the chat panel's assembly section
// Follow the existing SNyraChatPanel registration pattern in NyraEditorModule.cpp
```
  </action>
  <verify>
    <automated>find "/Users/aasish/CLAUDE\ PROJECTS/UEPLUG/UEPLUGIN/TestProject/Plugins/NYRA/Source/NyraEditor" -name "SNyraImageDropZone.cpp" -o -name "SNyraRefImageTile.cpp" -o -name "SNyraAssetChip.cpp" -o -name "SNyraProgressBar.cpp" -o -name "SNyraLogDrawer.cpp" | xargs grep -l "SLATE_BEGIN_ARGS\|Construct" 2>/dev/null | wc -l</automated>
  </verify>
  <verify_meta>All 5 components present with SLATE_BEGIN_ARGS/Construct</verify>
  <done>All 5 Slate components implemented per 06-UI-SPEC.md; NYRADNA tokens applied; design tokens (#050507 dominant, #0D0D14 secondary, #C6BFFF accent) consistent across all components</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User reference image -> SceneAssembler.analyze_image | Untrusted file path crosses; validated with Path.exists() |
| LLM output -> actor spawn | LLM output validated before Unreal API calls (asset paths must exist in UE registry) |
| External tool result -> UE import | Staging manifest path traversal check before any asset is imported |
| Assembly log -> user display | Log entries are evidence; malicious injection in actor labels blocked by NYRA_ prefix check |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-06-04 | Information Disclosure | assembly_tools.py AssembleSceneTool | mitigate | reference_image_path validated `Path.exists()` before LLM call |
| T-06-05 | Tampering | scene_assembler.py _spawn_actor_from_spec | mitigate | All actor labels prefixed `NYRA_`; Ctrl+Z per Phase 2 session transaction |
| T-06-06 | Denial of Service | asset_fallback_chain.py resolve_actor_asset | mitigate | Service timeout (Meshy 600s, ComfyUI 300s); fallback to placeholder rather than block |
| T-06-07 | Information Disclosure | assembly log entries | mitigate | Actor labels sanitized before logging; no raw user input in log display |
</threat_model>

<verification>
Unit tests:
```
pytest tests/test_assembly_tools.py tests/test_asset_fallback_chain.py -x -q
```

Manual verification (checkpoint:human-verify — see frontmatter checkpoint):
1. Open UE editor with NYRA plugin loaded
2. Open NYRA panel, locate SNyraImageDropZone (bottom or side dock)
3. Drag any JPG from file explorer over drop zone — verify drag-over state
4. Drop image — verify "Analyzing..." state → thumbnail appears → progress bar
5. Watch assembly: actors placed, materials applied, lighting configured
6. On completion: verify "Scene Assembled" heading + structured result in chat
7. Verify log drawer auto-expands briefly showing assembly evidence

Cold-start reliability test:
8. Disable Meshy API key (set to dummy), run same test — verify ComfyUI fallback or placeholder material, never blocks
</verification>

<success_criteria>
- DEMO-01 end-to-end: drop image → LLM analysis → 5-20 actors placed + materials applied + lighting configured
- SCENE-01 lighting triggered as part of assembly (no separate invocation needed)
- Asset fallback chain: user library → Meshy → ComfyUI texture → placeholder material (never blocks on unavailable service)
- SNyraImageDropZone (primary entry point), SNyraProgressBar (animated steps), SNyraLogDrawer (evidence) all rendered per 06-UI-SPEC.md
- SNyraRefImageTile (120x90px thumbnail), SNyraAssetChip (pill) implemented per spec
- All SCENE-01 requirements addressed within assembly (lighting setup is a step in the assembly pipeline)
</success_criteria>

<output>
After completion, create `.planning/phases/06-scene-assembly-image-to-scene-fallback-demo/06-02-SUMMARY.md`
</output>