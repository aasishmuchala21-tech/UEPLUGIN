---
phase: 06-scene-assembly-image-to-scene-fallback-demo
plan: "06-02"
subsystem: scene-assembly
tags: [demo-01, scene-assembler, asset-fallback, mcp-tool, slate-ui, drag-drop, progress-bar, log-drawer]

requires:
  - phase: "06-00"
    provides: SceneBlueprint / ActorSpec / MaterialSpec / AssemblyResult / AssetResolutionResult dataclasses + AssetPool LRU + SceneAssemblyOrchestrator base
  - phase: "06-01"
    provides: LightingAuthoringTool (injected as lighting_tool into SceneAssembler)
  - phase: 05-external-tool-integrations-api-first
    provides: MeshyImageTo3DTool / ComfyUIRunWorkflowTool (duck-typed via .execute(params) -> NyraToolResult)
provides:
  - AssetFallbackChain (library -> Meshy -> ComfyUI -> placeholder, with AssetPool caching)
  - SceneAssembler (analyze_image LLM call + 4-step assemble orchestrator)
  - AssembleSceneTool (nyra_assemble_scene MCP entry point with full progress streaming)
  - 5 Slate widgets: SNyraImageDropZone, SNyraRefImageTile, SNyraAssetChip, SNyraProgressBar, SNyraLogDrawer
affects: [06-03-staging-test, 06-04-canary, 07-00-foundation, 07-02-shot-block-ui]

tech-stack:
  added: []
  patterns:
    - "Synchronous orchestrator + injected progress_callback (not async): the assemble() method runs to completion in caller context, callback fires per step. Fits the MCP tool model (one execute call -> one NyraToolResult)."
    - "Duck-typed external tools: AssetFallbackChain doesn't import Meshy/ComfyUI tool classes — anything with .execute(params) -> NyraToolResult slots in. Lets unit tests use _FakeTool stubs without monkeypatching."
    - "Stub blueprint as the offline floor: when LLM analysis fails or is absent, _stub_blueprint deterministically returns a 4-actor 2-material living-room scene so the rest of the pipeline still exercises every step."
    - "Source-coloring on SNyraAssetChip: lookup table maps source -> FLinearColor (green=library, lavender=meshy, purple=comfyui, gray=placeholder); transparent at the boundary so the user can read the fallback path at a glance."

key-files:
  created:
    - "TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/asset_fallback_chain.py"
    - "TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/scene_assembler.py"
    - "TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/assembly_tools.py"
    - "TestProject/Plugins/NYRA/Source/NyraHost/tests/test_asset_fallback_chain.py"
    - "TestProject/Plugins/NYRA/Source/NyraHost/tests/test_assembly_tools.py"
    - "TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraImageDropZone.h"
    - "TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraRefImageTile.h"
    - "TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraAssetChip.h"
    - "TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraProgressBar.h"
    - "TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraLogDrawer.h"
    - "TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraImageDropZone.cpp"
    - "TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraRefImageTile.cpp"
    - "TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraAssetChip.cpp"
    - "TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraProgressBar.cpp"
    - "TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraLogDrawer.cpp"

key-decisions:
  - "_stub_blueprint generates a 4-actor 2-material living-room scene as the offline floor. This is deterministic so test_execute_returns_summary_payload can assert exact actor_count=4 / material_count=2."
  - "Material chain skips Meshy (Meshy is for 3D actors); actor chain skips ComfyUI (ComfyUI is for textures). The frontmatter docstring documents this; tests verify both directions."
  - "AssetPool keyed by (hint, role) - role is part of the key so the same hint ('brown sofa') can resolve differently for hero_furniture vs background_prop."
  - "SNyraImageDropZone fires OnImageDropped with an empty FString on raw drop because FExternalDragOperation file-list extraction needs operator-side wiring; the delegate firing path is reachable for compile-time link checks."

patterns-established:
  - "Tool-fallback chain pattern: try sources in order, cache successful resolution in shared AssetPool, fall through to deterministic placeholder. Reused by Phase 7 video pipeline for keyframe-asset resolution."
  - "Progress callback as plain Callable[[step, current, total, message], None]: the same shape that the JSON-RPC progress payload uses, so the orchestrator can do `_emit_progress(step, current, total) -> ws.send({'type': 'assembly_progress', ...})` with minimal translation."
  - "Stub blueprint as router-down behavior: every assembler that talks to LLMs has a deterministic offline counterpart so the whole pipeline is testable end-to-end without any router."

requirements-completed: [DEMO-01]

ue_cpp_compile_verification: pending_manual_verification
ue_cpp_compile_verification_reason: "10 Slate files (5 widget pairs) authored against UE 5.4+ Slate API + 06-UI-SPEC.md tokens. Same authoring host limitation as Plans 01 and 06-01: no UnrealBuildTool / UE 5.4-5.7 source on PATH. Compile + integration test (drag JPG over drop zone, watch progress bar tick through 4 steps, log drawer auto-expand on completion) is required to close the loop."
ue_cpp_followup_actions:
  - "NyraEditor.Build.cs may need 'InputCore' in PublicDependencyModuleNames for the FDragDropEvent surface in SNyraImageDropZone (likely already present from earlier Slate work)."
  - "FExternalDragOperation file-list extraction in SNyraImageDropZone::OnDrop: operator implements the IDataObject -> file-paths conversion (UE has helpers in DesktopPlatform module)."
  - "Wire SNyraImageDropZone delegate to the MCP-side `nyra_assemble_scene` invocation through FNyraWsClient::SendMessage (pattern from Plan 06-01)."

external_service_setup_required:
  meshy:
    why: "DEMO-01 fallback step 2 (actor generation when library is empty)"
    env: MESHY_API_KEY
    fallback_when_unset: "AssetFallbackChain skips Meshy and lands on the /Engine placeholder cube. Source code path is exercised via _FakeTool in tests/test_asset_fallback_chain.py."
  comfyui:
    why: "DEMO-01 fallback step 3 (texture generation for materials)"
    env: COMFYUI_HOST (default 127.0.0.1:8188)
    fallback_when_unset: "AssetFallbackChain skips ComfyUI and lands on the BasicShapeMaterial placeholder. Same _FakeTool stubbing pattern."

duration: ~25min
completed: 2026-05-10
---

# Phase 06 Plan 02: DEMO-01 Image-to-Scene - Summary

**DEMO-01 source-layer complete: AssetFallbackChain (library->Meshy->ComfyUI->placeholder), SceneAssembler with 4-step orchestrator, nyra_assemble_scene MCP tool that streams assembly_progress for every actor / material / lighting step. 19/19 Python tests green. 5 UE Slate widget pairs authored per 06-UI-SPEC.md (compile pending operator).**

## Performance

- **Duration:** ~25 min inline
- **Completed:** 2026-05-10
- **Tasks:** 3 of 3 complete
- **Files created:** 15 (3 Python source + 2 Python tests + 10 UE5 C++)

## Accomplishments

- `AssetFallbackChain` resolves both actor and material assets through deterministic fallback chains. Library hits short-circuit; Meshy/ComfyUI failures or exceptions degrade silently to /Engine placeholders so assembly never blocks.
- `SceneAssembler` inherits `SceneAssemblyOrchestrator` (Plan 06-00) and adds `analyze_image` (LLM via injected backend router with offline stub fallback) plus the 4-step `assemble` orchestrator (Placing Actors / Applying Materials / Setting Up Lighting / Finalizing). Every step fires a progress callback; the final step emits `assembly_complete` via the inherited WS notifier.
- `AssembleSceneTool` (`nyra_assemble_scene`) is the MCP entry point: one `execute(params)` call drives analyze + assemble, stream progress, return the AssemblyResult summary. Validates `reference_image_path` exists; returns structured errors for missing or invalid input.
- 5 Slate widget pairs (10 files) cover the DEMO-01 UI surface: drop zone with drag/paste, reference tile, asset chip with source coloring, 4-segment progress bar, collapsible log drawer.
- 19/19 Python unit tests pass on Python 3.12 / Windows in 0.13s.

## Task Commits

1. **AssetFallbackChain + tests** - `31fea46` (feat)
2. **SceneAssembler + AssembleSceneTool + tests** - `2246aad` (feat)
3. **5 Slate widget pairs** - `8e54243` (feat) - **build pending_manual_verification**
4. **SUMMARY.md** - this commit (docs)

## Verification

```text
cd TestProject/Plugins/NYRA/Source/NyraHost
python -m pytest tests/test_asset_fallback_chain.py tests/test_assembly_tools.py -v
================================= 19 passed in 0.13s =================================
```

**UE5 C++ compile:** PENDING. The 10 Slate files follow the SNyraChatPanel / SNyraLightingPanel patterns established in Phase 1 and Plan 06-01 - same NYRAEDITOR_API export macro, same design-token namespace, same delegate types. NyraEditor.Build.cs may need an `InputCore` addition for the `FDragDropEvent` surface.

**External services (Meshy + ComfyUI):** the autonomous flag was `false` in the plan because DEMO-01's full canary requires both services. The source-layer implementation is testable without them — every external call is duck-typed and unit tests use _FakeTool stubs. The placeholder fallbacks deliver a complete (though low-fidelity) scene whether or not the services are available, which is exactly what the asset_fallback_chain contract promises.

## Truths Established (DEMO-01 contract)

- User drops a reference image -> `analyze_image` produces a SceneBlueprint via LLM or stub fallback. ✅
- SceneAssembler runs 4 fixed steps with progress callback firing for every actor / material. ✅ (test_execute_emits_progress_through_all_four_steps)
- Asset fallback chain never blocks: library / Meshy / ComfyUI / placeholder all return AssetResolutionResult. ✅ (test_actor_falls_back_to_placeholder_when_meshy_raises etc.)
- All 5 Slate widgets surface the UI-SPEC interaction model. ✅ (source-complete; compile pending)

## Threats Mitigated

- **T-06-01 IID via reference image path:** image_path validated via `Path.exists()` in SceneAssembler.analyze_image before any router call (same pattern as Plan 06-01 LightingLLMParser).
- **T-06-02 Tampering via NYRA actor proliferation:** every spawned actor labeled with `NYRA_` prefix in `_place_actor` (matches Plan 06-01 convention; supports user mass-undo).

## Downstream Unblocked

- **Plan 06-03 (staging tests):** can now exercise the full `nyra_assemble_scene` flow end-to-end with the stub blueprint + _FakeTool fallback chain — no Meshy/ComfyUI required for the green path.
- **Plan 06-04 (canary):** AssembleSceneTool + AssetFallbackChain + SceneAssembler are all importable; canary's "18 tools registered" assertion now has its DEMO-01 contributions.
- **Phase 7:** SceneAssembler is the substrate; video-to-shot adds keyframe extraction + per-shot assembly atop the same chain.

## Open Items

- UE5 C++ compile verification pending operator (see `ue_cpp_followup_actions` above).
- FExternalDragOperation file-list extraction in SNyraImageDropZone::OnDrop is stubbed (fires delegate with empty FString); operator implements the IDataObject -> path conversion.
- Meshy + ComfyUI live-service tests deferred to Plan 06-04 canary, which is also `autonomous: false`.

## Status

✅ **Plan 06-02 SOURCE LAYER COMPLETE.** Python: 19/19 tests green; UE5 Slate: source-complete, compile pending operator. Wave 3 (06-03 staging tests) and Wave 4 (06-04 canary) unblocked at the source level.
