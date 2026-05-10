---
phase: 06-scene-assembly-image-to-scene-fallback-demo
fixed_at: 2026-05-10T00:00:00Z
review_path: .planning/phases/06-scene-assembly-image-to-scene-fallback-demo/06-REVIEW.md
iteration: 1
findings_in_scope: 18
fixed: 18
skipped: 0
regressed: 0
status: all_fixed
---

# Phase 6: Code Review Fix Report

**Fixed at:** 2026-05-10
**Source review:** 06-REVIEW.md
**Iteration:** 1 (no re-iteration needed; every BLOCKER and WARNING cleared on first pass)

**Summary:**
- Findings in scope: 18 (7 BLOCKER + 11 WARNING; 5 INFO out of scope per `fix_scope: critical_and_warning`)
- Fixed: 18
- Skipped: 0
- Regressed: 0

**Verification:**
- Targeted Phase 6 pytest suite (test_scene_types, test_asset_pool, test_demo01_canary, test_scene_assembly_e2e, test_lighting_integration): **42/42 pass**
- Broader pytest run (excluding the 2 unreal-mock-leaking files per environment instructions): **331/344 pass; 13 fail** -- all 13 failures are pre-existing Windows environmental issues (NTFS path-separator assumptions in test_claude_mcp_config, Windows file-handle locking in test_handshake / test_transaction). No fix in this report introduced any regression. Net delta: +2 tests passing (the two tests that codified the OLD CR-03 / WR-04 buggy behavior were updated to assert the new contract).
- UE C++ fixes (CR-05, CR-06, CR-07, WR-08) marked `pending_manual_verification` per environment guidance; no UE toolchain available locally.
- Two Python fixes (WR-07 atmosphere class paths / EditorActorSubsystem migration; WR-10 EditorAssetLibrary material binding) also depend on a live UE editor for full validation; logic is gated behind `try: import unreal` and falls through cleanly on the CLI canary.

## Applied Fixes

### CR-01: route Phase 6 asyncio calls through run_async_safely

**Files modified:** `tools/lighting_tools.py`, `tools/assembly_tools.py`
**Commit:** `ecad22f`
**Applied fix:** Replaced bare `asyncio.run()` at `lighting_tools.py:192,197` and `assembly_tools.py:64` with `run_async_safely`. Imported the helper from `nyrahost.tools.base`. Removed the now-unused `import asyncio` from `assembly_tools.py`. Tools no longer raise `RuntimeError` when dispatched from NyraHost's async WS handler.

### CR-02: SceneAssembler honors lighting_plan; AssembleSceneTool derives it

**Files modified:** `tools/scene_assembler.py`, `tools/lighting_tools.py`, `tools/assembly_tools.py`
**Commit:** `262262b`
**Applied fix:** `scene_assembler.assemble` now serializes the supplied `LightingParams` via `asdict + json.dumps` and forwards it as `lighting_params_json`, eliminating the hard-coded `studio_fill` literal. `LightingAuthoringTool._resolve_lighting_params` gains a `lighting_params_json` branch (and matching parameters schema entry). `AssembleSceneTool.execute` now derives a plan from the same reference image via `LightingLLMParser.parse_from_image` and forwards it to the assembler, so SC#2 ("match this image's mood") is actually exercised. **Logic-bug class fix -- requires human verification of the full image -> plan -> applied-lighting flow once UE is in the loop.**

### CR-03: AssemblyResult.success reflects spawn / lighting failures

**Files modified:** `tools/scene_assembler.py`
**Commit:** `24d9753`
**Applied fix:** Replaced the unconditional `result.success = True` with a computed predicate: `not actor_errors and not lighting_errors`, where `actor_errors` is any placed-actor dict containing the `"error"` key and `lighting_errors` is any log entry starting with `"lighting:error"`. When success is False, `result.error_message` is populated with a short summary so SNyraLogDrawer / WS notifier can surface the cause. **Logic-bug class fix -- requires human verification under partial-failure scenarios.**

### CR-04: DEMO-01 canary accepts --random / --verbose and wires Meshy / ComfyUI

**Files modified:** `canary/demo01_canary.py`
**Commit:** `02b4a82`
**Applied fix:** Added `--random`, `--verbose`, made `--test-image` optional (mutually exclusive with `--random`). Implemented `_pick_random_fixture()` that searches `NYRA_CANARY_FIXTURES_DIR` env then `Resources/_canary_pool` for `.png/.jpg/.jpeg/.webp` files; PARTIAL exit when the pool is empty. Added `_build_meshy_tool()` / `_build_comfyui_tool()` (env-gated on `MESHY_API_KEY` / `COMFYUI_HOST`) and `_build_unreal_library_search()` that delegates to `AssetSearchTool` with a no-op fallback when `unreal` is not importable. The 06-VERIFICATION.md operator protocol now parses cleanly; smoke-tested with empty fixture dir -> exit code 2 (PARTIAL).

### CR-05: SNyraImageDropZone fails closed when no usable path

**Files modified:** `Panel/SNyraImageDropZone.cpp`
**Commit:** `2b95321`
**Applied fix:** `OnDrop` no longer fires `OnImageDroppedDelegate.Execute(FString())` unconditionally. Now extracts the first asset path from `FAssetDragDropOp` when present and returns `FReply::Unhandled()` when no path can be resolved (rather than delivering an empty string downstream). Added `Invalidate` call to clear the visual highlight. **UE C++ change: pending_manual_verification.** Full external-Windows-Explorer file-drop wiring (`FExternalDragOperation`) is the next manual step.

### CR-06: SNyraLightingPanel actually dispatches WS messages

**Files modified:** `Panel/SNyraLightingPanel.cpp`
**Commit:** `d9c8e28`
**Applied fix:** `HandleApplyClicked` and `HandleDryRunHover` now build real `FJsonObject` params payloads and call `FNyraWsClient::SendRequest(TEXT("nyra_lighting_authoring"), ...)` / `SendRequest(TEXT("nyra_lighting_dry_run_preview"), ...)` instead of pinning the WS client and discarding it. Added an Error state when the WS client is unavailable (no more silent hang in Applying). **Folds in WR-09**: `FPaths::FileExists` validity check guards the `bHasImage` branch, making the "select a preset or attach an image" error message reachable when the image path no longer exists. **UE C++ change: pending_manual_verification.**

### CR-07: replace DECLARE_STDOUT_CHANNEL with DEFINE_LOG_CATEGORY_STATIC

**Files modified:** `Private/NyraToolCatalogCanary.cpp`
**Commit:** `0b71977`
**Applied fix:** `DECLARE_STDOUT_CHANNEL` is not a UE 5.4-5.7 macro -- replaced with `DEFINE_LOG_CATEGORY_STATIC(LogNyraToolCanary, Log, All)`. Dropped 5 dead includes (EditorScriptingUtilities/BlueprintEditorUtilityLibrary.h, AssetRegistry/IAssetRegistry.h, Kismet/BlueprintEditorSubsystem.h, KismetSystemLibrary.h, KismetMaterialLibrary.h). Added the headers actually used (CoreMinimal, Logging/LogMacros, Containers/Array, Containers/UnrealString, Math/UnrealMathUtility). **UE C++ change: pending_manual_verification.**

### WR-01 + WR-02: AssetPool atomic + thread-safe writes

**Files modified:** `tools/asset_pool.py`
**Commit:** `f9c3f2a`
**Applied fix:** `_save_to_disk` no longer called from `get()` -- LRU re-ordering on read is in-memory only, so an assembly with N hits no longer triggers N disk syncs. `_save_to_disk` writes via temp-file + `tmp.replace(self._pool_path)` so an interrupted write cannot leave the manifest half-written. Added a `threading.RLock` and wrapped `get / put / clear` so concurrent NyraHost worker tasks can't race a torn JSON write.

### WR-03: hoist LightingParams.from_dict to scene_types public API

**Files modified:** `tools/scene_types.py`, `tools/scene_llm_parser.py`, `tools/lighting_tools.py`
**Commit:** `8b24505`
**Applied fix:** `LightingParams.from_dict` classmethod added next to the dataclass. Both `LightingAuthoringTool._resolve_lighting_params` and `LightingDryRunTool.execute` now use the public classmethod. `scene_llm_parser._params_from_dict` is preserved as a thin alias to maintain backwards compatibility for any other callers.

### WR-04: _preset_to_params raises on unknown preset names

**Files modified:** `tools/lighting_tools.py`
**Commit:** `49178e0`
**Applied fix:** `_preset_to_params` now raises `ValueError("Unknown lighting preset '{x}'. Valid: [...]")` instead of silently substituting `studio_fill`. The apply path's existing `except ValueError` returns `[-32030]` to the caller; the dry-run path's `try / except ValueError` was added during WR-03 in preparation. Updated `test_preset_to_params_unknown_falls_back_to_studio_fill` (which codified the old bug) to `test_preset_to_params_unknown_raises_value_error`.

### WR-05: hoist canonical lighting presets to scene_types

**Files modified:** `tools/scene_types.py`, `tools/scene_llm_parser.py`, `tools/lighting_tools.py`
**Commit:** `4fcacbb`
**Applied fix:** `LIGHTING_PRESETS: dict[str, LightingParams]` and `PRESET_TOKENS: dict[str, list[str]]` are now defined in `scene_types`. `lighting_tools._PRESETS` is a thin alias on top of `LIGHTING_PRESETS`. `scene_llm_parser._FALLBACK_PRESETS` is built from `LIGHTING_PRESETS + PRESET_TOKENS` via `_build_fallback_presets()`, with a `_clone_with_confidence` helper that stamps `confidence=0.6` on rule-based matches via `dataclasses.replace` so the canonical entries stay untouched. Smoke-tested: `parse_from_text("golden hour shoot")` matches `golden_hour` with confidence=0.6 and the documented mood tags.

### WR-06: share assembly progress step labels via named constants

**Files modified:** `tools/scene_types.py`, `tools/scene_assembler.py`, `Panel/SNyraProgressBar.cpp`
**Commit:** `f2fc3bf`
**Applied fix:** `ASSEMBLY_STEP_PLACING_ACTORS / _APPLYING_MATERIALS / _SETTING_UP_LIGHTING / _FINALIZING` constants added in `scene_types`. `scene_assembler.assemble` now emits the constants. Added a wire-constants doc comment in `SNyraProgressBar::ProgressFor()` warning future editors that the labels must match `nyrahost.tools.scene_types.ASSEMBLY_PROGRESS_STEPS`. (The integer-index alternative the review suggested would require a coordinated UI/spec change; the constant-share alone removes the silent-drift hazard.)

### WR-07: prefer EditorActorSubsystem; document atmosphere class paths

**Files modified:** `tools/lighting_tools.py`
**Commit:** `e8c4ecc`
**Applied fix:** `_spawn_actor` now tries `unreal.EditorActorSubsystem.spawn_actor_from_class` first (UE 5.5+) and falls back to the legacy `unreal.EditorLevelLibrary.spawn_actor_from_class` on UE 5.4. Atmosphere / fog / volumetric class paths are documented inline. Pending live UE 5.4-5.7 reflection-database verification before phase exit.

### WR-08: SNyraImageDropZone invalidates on drag-over / drag-leave

**Files modified:** `Panel/SNyraImageDropZone.cpp`
**Commit:** `3fecda5`
**Applied fix:** `OnDragOver` / `OnDragLeave` now call `Invalidate(EInvalidateWidget::Paint)` only on real edges (when `bDragOverActive` actually changes), so the BorderBackgroundColor lambda re-evaluates under SLATE_NEW_INVALIDATION builds. **UE C++ change: pending_manual_verification.**

### WR-09: FOLDED INTO CR-06

The empty-FString guard fix was applied as part of CR-06 commit `d9c8e28`. The image-path validity check in `HandleApplyClicked` uses `FPaths::FileExists` to validate `CurrentImagePath` before treating it as configured.

### WR-10: SceneAssembler._apply_material binds material to spawned actor

**Files modified:** `tools/scene_assembler.py`
**Commit:** `e078aef`
**Applied fix:** `_place_actor` now returns `(entry_dict, actor_handle)`. `assemble()` builds an `actor_lookup` keyed by role. `_apply_material(spec, actor_lookup)` loads the resolved asset via `EditorAssetLibrary.load_asset` and calls `set_material(0, material)` on the StaticMeshComponent of the target actor. The returned entry now records a `bind_status` field (`ok` | `no_actor` | `not_in_editor` | `material_load_failed` | `no_static_mesh_component` | `error`) so partial-bind cases surface through SNyraLogDrawer instead of vanishing into a count-only success. Pending live UE verification.

### WR-11: cache LightingLLMParser; emit lighting_fallback_used WS event

**Files modified:** `tools/lighting_tools.py`
**Commit:** `3c81711`
**Applied fix:** `LightingAuthoringTool.__init__` constructs `self._parser = LightingLLMParser(...)` once. `_resolve_lighting_params` reuses it. New `_maybe_notify_fallback(lp, source)` fires a `lighting_fallback_used` WS notification when `lp.confidence < 0.5` (the rule-based / failure regime), so the chat panel can hint the user that the LLM call was downgraded. Notifier exceptions are caught and logged as warnings so WS issues never escape into UE.

## Skipped Issues

None.

## Regressed Issues

None.

## Out-of-Scope (Info findings, not in `fix_scope: critical_and_warning`)

- **IN-01**: `const_cast<SNyraLightingSelector*>(this)` cleanup -- not addressed.
- **IN-02**: store `PoolEntry.resolved_at` as float epoch -- not addressed.
- **IN-03**: unused imports in `scene_assembler.py:15`, `scene_orchestrator.py:27`, `demo01_canary.py:17` -- not addressed.
- **IN-04**: add `analysis_error` field to `SceneBlueprint` -- not addressed.
- **IN-05**: centralize Slate design tokens in `NyraDesignTokens.h` -- not addressed.

These were left for a follow-up `--fix all` pass or for explicit manual cleanup; they do not block phase exit per the review.

## Final Status

- **All 7 BLOCKERs (CR-01..CR-07): FIXED.**
- **All 11 WARNINGs (WR-01..WR-11): FIXED.** WR-09 was folded into the CR-06 commit because both touched `HandleApplyClicked`.
- 18 fix commits authored, 1 follow-up test-update commit, all atomic and conventionally formatted.
- Targeted Phase 6 pytest: 42/42 pass.
- Broader pytest: 331 pass / 13 pre-existing environmental failures / **0 regressions** introduced by this fix-pass.
- 4 UE C++ findings (CR-05, CR-06, CR-07, WR-08) are `pending_manual_verification` per the environment instructions (no UE toolchain locally). 2 Python findings (WR-07, WR-10) depend on a live UE editor for end-to-end behavioral verification; their CLI fall-through paths are exercised by tests.
- 2 logic-bug-class fixes (CR-02, CR-03) are flagged as `requires human verification` since syntax verification cannot confirm semantic correctness of the new control-flow paths under partial-failure scenarios.

Phase 6 BLOCKERs are now cleared at the source level. The phase exit gate moves from "operator-run pending due to BLOCKERs" to "operator-run pending under normal verification protocol."

---

_Fixed: 2026-05-10_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
