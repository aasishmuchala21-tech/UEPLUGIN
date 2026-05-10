---
phase: 06-scene-assembly-image-to-scene-fallback-demo
reviewed: 2026-05-10T00:00:00Z
depth: standard
files_reviewed: 25
files_reviewed_list:
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/scene_types.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/asset_pool.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/scene_orchestrator.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/scene_llm_parser.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/lighting_tools.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/asset_fallback_chain.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/scene_assembler.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/assembly_tools.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/canary/demo01_canary.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/base.py
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraLightingSelector.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraLightingSelector.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraLightingPanel.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraLightingPanel.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraImageDropZone.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraImageDropZone.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraRefImageTile.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraRefImageTile.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraAssetChip.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraAssetChip.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraProgressBar.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraProgressBar.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraLogDrawer.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraLogDrawer.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraToolCatalogCanary.cpp
findings:
  critical: 7
  warning: 11
  info: 5
  total: 23
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-05-10
**Depth:** standard
**Files Reviewed:** 25
**Status:** issues_found

## Summary

Phase 6 ships SCENE-01 lighting + DEMO-01 image-to-scene assembly across one Python package and seven new Slate widgets. The architecture is reasonable, but the implementation contains several BLOCKER-class defects that contradict the phase's own success criteria and threat-model documentation.

The single largest issue: the new `run_async_safely` helper added to `tools/base.py` (per the phase context, "the orchestrator just added... verify each tool that uses asyncio uses the helper, not raw asyncio.run") is **unused**. Every Phase 6 tool that needs asyncio (`AssembleSceneTool`, `LightingAuthoringTool`) calls bare `asyncio.run()` and will deadlock when dispatched from NyraHost's async WebSocket handler — exactly the scenario base.py warns about.

Several other defects directly invalidate the phase exit criteria:

- The `assemble()` orchestrator ignores the `lighting_plan` argument it asks for and hard-codes `preset_name="studio_fill"` instead, breaking SC#1 ("match this image's mood") and SC#2 (image-derived lighting).
- The `assemble()` method always sets `result.success = True` even when actors fail to spawn or lighting raises, masking failures from SNyraLogDrawer / WS notifier.
- The DEMO-01 canary's CLI rejects the exact invocation documented in 06-VERIFICATION.md (`--random --verbose`) and never wires backend_router / meshy_tool / comfyui_tool, so SC#1 (library-first) is never exercised in the canary.
- The image drop zone fires the delegate with an **empty FString** on drop (`Execute(FString())`), so the user dropping an image never delivers the path — a guaranteed P0 demo regression.
- The lighting Slate panel's "Apply Lighting" button is a no-op: the WS-send block contains only a comment.
- `NyraToolCatalogCanary.cpp` uses `DECLARE_STDOUT_CHANNEL`, which is not a UE macro — the file will not compile.

The C++ Slate code is documented as `pending_manual_verification`, so structural Slate-API mistakes are downgraded to WARNING per the phase reviewer guidance, but several issues (the `DECLARE_STDOUT_CHANNEL` typo, the empty-path delegate execution, the dead `Apply` button) are correctness defects that no UE compiler check would have hidden — they would survive even after the human verification step.

## Critical Issues

### CR-01: `run_async_safely` helper exists but is never used; tools will deadlock under NyraHost's async dispatcher

**File:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/base.py:13` (helper); `tools/lighting_tools.py:192,197` and `tools/assembly_tools.py:64` (callers)

**Issue:** The phase context explicitly says: "asyncio.run() usage in Python tools is intentional. NyraHost dispatches tools through an async WS handler in production, so calling asyncio.run from a tool's execute() method will deadlock when called from the running loop. The orchestrator just added a `run_async_safely` helper to tools/base.py to handle this; verify each tool that uses asyncio uses the helper, not raw asyncio.run."

A grep across the new Python files shows zero call sites for `run_async_safely`. The Phase 6 tools call raw `asyncio.run()` from inside `execute()`:

- `lighting_tools.py:192`: `asyncio.run(parser.parse_from_image(...))`
- `lighting_tools.py:197`: `asyncio.run(parser.parse_from_text(...))`
- `assembly_tools.py:64`: `asyncio.run(self._assembler.analyze_image(image_path))`

When NyraHost's WS handler awaits `tool.execute(...)`, `asyncio.get_running_loop()` succeeds, so `asyncio.run` will raise `RuntimeError: asyncio.run() cannot be called from a running event loop` (Python 3.12 behavior). The intended runtime path produces a hard 500-class JSON-RPC error on every Phase 6 tool invocation.

**Fix:**
```python
# tools/lighting_tools.py
from nyrahost.tools.base import NyraTool, NyraToolResult, run_async_safely

# line 192
return run_async_safely(parser.parse_from_image(params["reference_image_path"]))
# line 197
return run_async_safely(parser.parse_from_text(params["nl_prompt"]))

# tools/assembly_tools.py:64
blueprint = run_async_safely(self._assembler.analyze_image(image_path))
```

### CR-02: `SceneAssembler.assemble` ignores its `lighting_plan` argument and hard-codes `studio_fill`

**File:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/scene_assembler.py:108-114`

**Issue:** `assemble(blueprint, lighting_plan=None, progress_callback=None)` accepts a `LightingParams` to honor, but step 3 builds the lighting tool payload with a literal preset name:

```python
if lighting_plan and self._lighting_tool is not None:
    try:
        lt_result = self._lighting_tool.execute({
            "preset_name": "studio_fill",      # <-- hard-coded
            "apply": True,
        })
```

The contents of `lighting_plan` are dropped on the floor. Phase 6 SC#2 explicitly requires "lighting from reference images (\"match this image's mood\")"; this code will produce the same neutral studio fill regardless of whether the LLM returned "moody_blue" / "golden_hour" / a custom param set. The `studio_fill` literal also bypasses the LLM's image-derived `LightingParams` even when the upstream `parse_from_image` succeeded.

`AssembleSceneTool` compounds the problem at `assembly_tools.py:80-84` by passing `lighting_plan=None` unconditionally, so the lighting step is silently skipped on every real run.

**Fix:**
```python
# scene_assembler.py
if lighting_plan and self._lighting_tool is not None:
    try:
        # Serialize the params to the JSON the tool's lighting_params_json contract
        # expects, OR add a direct LightingParams entry point to the tool.
        lt_result = self._lighting_tool.execute({
            "lighting_params_json": json.dumps(asdict(lighting_plan)),
            "apply": True,
        })

# assembly_tools.py — derive the plan from the blueprint / image:
lighting_plan = run_async_safely(
    LightingLLMParser(self._router).parse_from_image(image_path)
)
result = self._assembler.assemble(
    blueprint=blueprint,
    lighting_plan=lighting_plan,
    progress_callback=_emit_progress,
)
```

### CR-03: `assemble()` sets `result.success = True` unconditionally, masking spawn / lighting failures

**File:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/scene_assembler.py:127`

**Issue:** After all four steps the method does:
```python
# Step 4: Finalize
progress("Finalizing", 1, 1, "summary")
result.success = True
self.send_assembly_complete(result)
```

`success` defaults to `True` already, but the unconditional re-assign means even when `_place_actor` returned an error dict (line 169-176, `actor_name = "NYRA_{role}_error"`) or the lighting step's exception handler ran (line 121-123), `to_structured_summary()["success"]` reports `True`. SNyraLogDrawer and the WS `assembly_complete` consumer cannot tell a partial-failure assembly from a clean one.

This also breaks the canary's assumption: `grade_verdict` only inspects `result.errors`, but `run_canary` only appends to `errors` for assertion thresholds — it doesn't propagate the per-spec spawn errors. So a run where every actor spawn failed still yields a PASS verdict if `result.placed_actors` happens to have 4 error-stubs (each is still an entry in `placed_actors`).

**Fix:**
```python
# scene_assembler.py:125-128
result.success = (
    not any("error" in a for a in result.placed_actors)
    and not any("error:" in entry for entry in result.log_entries)
)
self.send_assembly_complete(result)
```
Also propagate `error_message` when `result.success` is false so SNyraLogDrawer can surface the cause.

### CR-04: DEMO-01 canary CLI rejects the exact invocation documented in VERIFICATION.md and never wires Meshy/ComfyUI

**File:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/canary/demo01_canary.py:148-181`

**Issue:** 06-VERIFICATION.md prescribes the operator-run protocol:
```
MESHY_API_KEY=your_key COMFYUI_HOST=127.0.0.1:8188 \
  python -m nyrahost.canary.demo01_canary --random --verbose
```
But `main()` only declares `--test-image`, `--expect-actors`, `--expect-materials`, and `--json`. Argparse will exit with code 2 on `--random` or `--verbose` before any canary runs. The "cold-start reliability" command in VERIFICATION.md (also `--random`) hits the same wall.

Worse: even with the correct flags, `run_canary` is invoked with `meshy_tool=None, comfyui_tool=None, library_search=None`. Meshy and ComfyUI clients are never constructed from `MESHY_API_KEY` / `COMFYUI_HOST` env, and `library_search` is the no-op `lambda hint, role: None`. So the canary always falls straight to placeholder for every actor and material. SC#1 ("library first, then Meshy/ComfyUI") is never exercised in the actual canary; the verdict reflects only the placeholder path's reliability. SC#3 ("DEMO-01 passes the random-reference daily test") cannot be evaluated.

**Fix:**
```python
parser.add_argument("--random", action="store_true",
    help="Pick a random image from the test fixture pool.")
parser.add_argument("--verbose", action="store_true")

# pull keys from env, build clients with fallbacks
meshy_key = os.environ.get("MESHY_API_KEY")
comfy_host = os.environ.get("COMFYUI_HOST")
meshy_tool = MeshyImageTo3DTool(api_key=meshy_key) if meshy_key else None
comfyui_tool = ComfyUIRunWorkflowTool(host=comfy_host) if comfy_host else None
library_search = build_unreal_library_search()  # uses nyra_asset_search

# pass to run_canary; build_assembler already supports them
```

### CR-05: SNyraImageDropZone fires `OnDropped` with an empty path on every drop event

**File:** `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraImageDropZone.cpp:63-74`

**Issue:**
```cpp
FReply SNyraImageDropZone::OnDrop(const FGeometry& MyGeometry, const FDragDropEvent& DragDropEvent)
{
    bDragOverActive = false;
    // External-file drop wiring (FExternalDragOperation) is finished in operator
    // verification step; placeholder fires the delegate with empty path so wiring
    // is reachable for compile-time linking checks.
    if (OnImageDroppedDelegate.IsBound())
    {
        OnImageDroppedDelegate.Execute(FString());
    }
    return FReply::Handled();
}
```
The drop handler unconditionally executes the delegate with an empty `FString()`. Downstream consumers (e.g. SNyraLightingPanel storing `CurrentImagePath`, AssembleSceneTool which then calls `Path(image_path).exists()`) will receive an empty string. `Path("").exists()` returns `False`, so the assembler will raise `FileNotFoundError("Reference image not found: ")` — meaning the headline DEMO-01 user gesture (drop a reference image) is broken end-to-end.

The "compile-time linking checks" comment is misleading: an empty-string call is a runtime no-op that would likely look successful in casual testing because the delegate fires.

**Fix:** Implement actual drop-event extraction with `FExternalDragOperation` / `FAssetDragDropOp` before this can ship. The placeholder should at minimum fail closed (early-return without firing the delegate) so callers don't process garbage:
```cpp
FReply SNyraImageDropZone::OnDrop(...)
{
    bDragOverActive = false;
    TSharedPtr<FExternalDragOperation> Op = DragDropEvent.GetOperationAs<FExternalDragOperation>();
    if (!Op.IsValid() || !Op->HasFiles() || Op->GetFiles().Num() == 0)
    {
        return FReply::Unhandled();
    }
    const FString& First = Op->GetFiles()[0];
    if (OnImageDroppedDelegate.IsBound())
    {
        OnImageDroppedDelegate.Execute(First);
    }
    return FReply::Handled();
}
```

### CR-06: SNyraLightingPanel "Apply Lighting" button is a no-op — never sends a WS message

**File:** `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraLightingPanel.cpp:92-113`

**Issue:**
```cpp
if (TSharedPtr<FNyraWsClient> Pinned = WsClient.Pin())
{
    // FNyraWsClient::SendMessage(method, params) — pattern from Phase 1.
    // Method: nyra_lighting_authoring; params chosen by available state.
    // (Wire-up completed via the chat panel's existing WS plumbing.)
}
```
The pinned `Pinned` WS client is never used. `HandleDryRunHover` (line 121-128) has the identical defect. The panel transitions its visual state to `Applying`/`PreviewingDryRun` but no actual JSON-RPC call leaves the editor — the demo will hang in the "Applying lighting..." status forever, and no preset / image-path data ever reaches NyraHost.

This contradicts SC#2 (SCENE-01 from NL prompts AND from reference images) — the chat-panel-driven Apply / Preview path is dead code.

**Fix:** Build the JSON params from `CurrentPreset` / `CurrentImagePath` and dispatch via the actual `FNyraWsClient` interface (consult Phase 1 chat panel for the call shape):
```cpp
if (TSharedPtr<FNyraWsClient> Pinned = WsClient.Pin())
{
    TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
    if (!CurrentPreset.IsEmpty())
        Params->SetStringField(TEXT("preset_name"), CurrentPreset);
    if (!CurrentImagePath.IsEmpty())
        Params->SetStringField(TEXT("reference_image_path"), CurrentImagePath);
    Params->SetBoolField(TEXT("apply"), true);
    Pinned->SendToolCall(TEXT("nyra_lighting_authoring"), Params);
}
else
{
    SetState(ENyraLightingPanelState::Error, TEXT("WebSocket client unavailable."));
}
```

### CR-07: `DECLARE_STDOUT_CHANNEL` is not a UE macro — `NyraToolCatalogCanary.cpp` does not compile

**File:** `TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraToolCatalogCanary.cpp:14`

**Issue:**
```cpp
DECLARE_STDOUT_CHANNEL(LogNyraToolCanary);
```
No such macro exists in UE 5.4-5.7. The canonical macro is `DECLARE_LOG_CATEGORY_EXTERN(...)` in a header plus `DEFINE_LOG_CATEGORY(...)` in the .cpp, or `DEFINE_LOG_CATEGORY_STATIC(LogNyraToolCanary, Log, All)` for cpp-local categories. Grep confirms no other source file defines this macro and no header is included that would provide it. The 36 subsequent `UE_LOG(LogNyraToolCanary, ...)` calls reference an identifier that doesn't exist after preprocessing.

The `EditorScriptingUtilities/BlueprintEditorUtilityLibrary.h` include path on line 8 is also suspect — the public include is `BlueprintEditorLibrary.h` (under `Editor/EditorScriptingUtilities/Public/`). The plugin will fail UBT include resolution. None of `BlueprintEditorUtilityLibrary`, `IAssetRegistry`, `BlueprintEditorSubsystem`, `KismetSystemLibrary`, or `KismetMaterialLibrary` are actually used in this file — they're all dead includes.

**Fix:**
```cpp
// NyraToolCatalogCanary.cpp top
#include "NyraEditorModule.h"
#include "NyraEditorLogging.h"   // or define the category locally:
DEFINE_LOG_CATEGORY_STATIC(LogNyraToolCanary, Log, All);
// Drop the unused EditorScriptingUtilities/AssetRegistry/Kismet includes.
```

## Warnings

### WR-01: `AssetPool.get()` writes the entire JSON manifest to disk on every cache hit

**File:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/asset_pool.py:60-69`

**Issue:** Every successful `get()` calls `move_to_end()` (LRU bookkeeping) and then `_save_to_disk()`. With a max of 200 entries this means a full rewrite of `asset_pool.json` (potentially several KB) on every read. Two concrete consequences:

1. Fault-injection during a save (interrupted `write_text`) corrupts the entire pool — the load handler clears the cache, so the user loses all 200 prior resolutions. Atomic-rename is the standard mitigation.
2. Hot-loop reads from `AssetFallbackChain.resolve_actor_asset` (called once per actor in `assemble`) cause N disk writes per assembly, in addition to the writes in `put()`. For a 5-20 actor scene this is ~40 syncs/run.

**Fix:** Save on `put()` and `clear()` only; the LRU re-ordering on read is in-memory and doesn't need persistence. Also write through a temp-file rename for atomicity:
```python
tmp = self._pool_path.with_suffix(".json.tmp")
tmp.write_text(json.dumps(data, indent=2))
tmp.replace(self._pool_path)
```

### WR-02: `AssetPool._save_to_disk` is not thread-safe / process-safe

**File:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/asset_pool.py:112-130`

**Issue:** Two NyraHost worker tasks calling `pool.put()` concurrently can both serialize a different snapshot of `_cache.items()` and clobber each other on `write_text`. The pool also lives at a per-user `%LOCALAPPDATA%/NYRA` path shared across UE editor instances; concurrent editors reading + writing produce torn JSON files. The existing `_load_from_disk` swallows the resulting `JSONDecodeError` by clearing the cache, which silently destroys persistent state.

**Fix:** Wrap the save with a `threading.Lock` shared across the pool object, or accept an explicit single-writer assumption and document it. For multi-process safety use a `portalocker`-style file lock or a sqlite-backed pool.

### WR-03: `LightingDryRunTool` reaches into a private helper across modules

**File:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/lighting_tools.py:326-327`

**Issue:**
```python
from nyrahost.tools.scene_llm_parser import _params_from_dict
lp = _params_from_dict(d)
```
`_params_from_dict` has a leading underscore (Python's "private" convention). Importing it across module boundaries couples the modules' refactor surface and silently breaks if `scene_llm_parser` renames or removes it. Move the helper to `scene_types.py` (where the dataclass lives) and rename it `LightingParams.from_dict(...)` so it's a public API.

**Fix:**
```python
# scene_types.py
@dataclass
class LightingParams:
    ...
    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LightingParams":
        ...
# lighting_tools.py uses LightingParams.from_dict(d)
```

### WR-04: `LightingAuthoringTool._preset_to_params` silently substitutes `studio_fill` for unknown preset names

**File:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/lighting_tools.py:200-202`

**Issue:**
```python
@staticmethod
def _preset_to_params(preset_name: str) -> LightingParams:
    return _PRESETS.get(preset_name, _PRESETS["studio_fill"])
```
A typo'd preset (`"goldenhour"`, `"moody-blue"`) silently returns the studio_fill default. The tool reports success ("Lighting applied: rect with mood neutral...") and the user's chat thread shows it lit the scene with a preset they did not request. The `nyra_lighting_dry_run_preview` path also passes through here, so the preview is also wrong.

**Fix:**
```python
@staticmethod
def _preset_to_params(preset_name: str) -> LightingParams:
    if preset_name not in _PRESETS:
        raise ValueError(
            f"Unknown lighting preset '{preset_name}'. "
            f"Valid: {sorted(_PRESETS)}"
        )
    return _PRESETS[preset_name]
```
And catch the `ValueError` in `execute()` to return a JSON-RPC error.

### WR-05: Two parallel preset definitions (`_PRESETS` in `lighting_tools.py` vs `_FALLBACK_PRESETS` in `scene_llm_parser.py`) drift independently

**File:** `tools/lighting_tools.py:29-95` and `tools/scene_llm_parser.py:50-136`

**Issue:** Both modules define five-entry preset dicts with overlapping but not identical content (the parser version has token lists; the tool version doesn't). Any change to e.g. `golden_hour`'s color or intensity has to be made in two places. The parser's `_FALLBACK_PRESETS["studio_fill"]["params"]` is consulted as the "safest neutral default"; the tool's `_PRESETS["studio_fill"]` is consulted as the unknown-preset fallback (WR-04). These will inevitably diverge.

**Fix:** Hoist a single `LIGHTING_PRESETS: dict[str, LightingParams]` module to `scene_types.py` (or a new `lighting_presets.py`), and have the parser keep only its `tokens` keyword index pointing to those presets:
```python
# scene_types.py
LIGHTING_PRESETS = {"golden_hour": LightingParams(...), ...}
PRESET_TOKENS = {"golden_hour": ["golden hour", "sunset", ...], ...}
```

### WR-06: `ProgressBar.ProgressFor` does not update for the "Placing Actors" step's cumulative count

**File:** `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraProgressBar.cpp:53-64`

**Issue:**
```cpp
float SNyraProgressBar::ProgressFor(const FString& Step) const
{
    float SegmentBase = 0.0f;
    if (Step == TEXT("Applying Materials"))    SegmentBase = 0.25f;
    else if (Step == TEXT("Setting Up Lighting")) SegmentBase = 0.50f;
    else if (Step == TEXT("Finalizing"))       SegmentBase = 0.75f;
    ...
}
```
The Python-side `assemble()` emits step strings `"Placing Actors"`, `"Applying Materials"`, `"Setting Up Lighting"`, `"Finalizing"`. When `Step` is empty (initial / `Reset()`) the function returns `0.0` but `Within * 0.25` may still produce a non-zero value because `CurrentN` and `CurrentTotal` carry over from the prior call — actually correct in this code path. However, the four labels are duplicated as English literals in two different files (Python and C++) with no shared constants — a Python-side label change ("Setting Up Lights" vs "Setting Up Lighting") silently breaks the progress bar without any compile or test signal.

**Fix:** Define an enum / wire constant set used by both sides. Send the step as an integer index (0..3) instead of a free-form string.

### WR-07: `LightingAuthoringTool._spawn_actor` calls `unreal.UObject.load_system_class` with a `/Script/Engine.SkyAtmosphere` path that may not be a Class

**File:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/lighting_tools.py:240-260`

**Issue:** `unreal.UObject.load_system_class` expects an Engine class path. `SkyAtmosphere`, `VolumetricCloud`, `ExponentialHeightFog`, and `PostProcessVolume` are concrete `AActor` subclasses (`ASkyAtmosphere`, `AExponentialHeightFogActor`, etc.) and the canonical paths use the actor name. `/Script/Engine.SkyAtmosphere` is the *component* class in many UE versions; the actor is `ASkyAtmosphere` which loads from `/Script/Engine.SkyAtmosphere`. `ExponentialHeightFog` similarly has both a component (`UExponentialHeightFogComponent`) and an actor (`AExponentialHeightFogActor`).

`spawn_actor_from_class` requires a class derived from `AActor`. Passing the component class will throw at runtime; passing the wrong actor name fails with a null `actor_class`. Worth verifying against the live UE 5.4-5.7 reflection database before relying on the strings in `_LIGHT_CLASS` and the inline strings here.

**Fix:** Use class references known to be actors and cover both UE 5.4 and 5.7. Concretely the actor names that exist in 5.4-5.7 are `/Script/Engine.SkyAtmosphere`, `/Script/Engine.VolumetricCloud`, `/Script/Engine.ExponentialHeightFogActor`, `/Script/Engine.PostProcessVolume` — note `ExponentialHeightFogActor`, not `ExponentialHeightFog`. Also, `unreal.EditorLevelLibrary` is deprecated in 5.5+; prefer `unreal.EditorActorSubsystem.spawn_actor_from_class()`.

### WR-08: `OnDragOver` / `OnDragLeave` mutate state but do not invalidate the widget; the visual highlight will not update

**File:** `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraImageDropZone.cpp:52-61`

**Issue:** The drop zone's border color is bound via `BorderBackgroundColor_Lambda([this]() { return bDragOverActive ? Accent : Dominant; })`. Slate generally re-evaluates lambda attributes during paint, but mutation of `bDragOverActive` from `OnDragOver` (which fires repeatedly during a hover) without an explicit `Invalidate(EInvalidateWidget::Paint)` may not visibly toggle the color until some other paint event hits — particularly with `SLATE_NEW_INVALIDATION` enabled. Returning `FReply::Unhandled()` from `OnDragOver` is the more conventional pattern when you want propagation for the cursor.

**Fix:**
```cpp
FReply SNyraImageDropZone::OnDragOver(...)
{
    bDragOverActive = true;
    Invalidate(EInvalidateWidget::Paint);
    return FReply::Handled();
}
```

### WR-09: Empty `FString()` accepted as a valid `CurrentImagePath` in `SNyraLightingPanel::HandleApplyClicked`

**File:** `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraLightingPanel.cpp:94`

**Issue:**
```cpp
if (CurrentPreset.IsEmpty() && CurrentImagePath.IsEmpty()) { ... }
```
Combined with CR-05 (drop zone fires the delegate with empty FString), this guard never triggers because `CurrentImagePath` is `IsEmpty()=true` only when *neither* preset nor image is set. After a drop event, `CurrentImagePath = ""` is treated as a valid configured image path, so the guard misclassifies the state. The error message ("Select a preset or attach a reference image first.") is therefore unreachable in practice.

**Fix:** Validate the path actually points to an existing file before accepting it:
```cpp
const bool bHasImage = !CurrentImagePath.IsEmpty()
    && FPaths::FileExists(CurrentImagePath);
const bool bHasPreset = !CurrentPreset.IsEmpty();
if (!bHasImage && !bHasPreset)
{
    SetState(...);
    return FReply::Handled();
}
```

### WR-10: `SceneAssembler._apply_material` returns metadata but never actually applies the material in editor

**File:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/scene_assembler.py:178-185`

**Issue:**
```python
def _apply_material(self, spec: MaterialSpec) -> dict:
    resolution = self._fallback.resolve_material_asset(spec.texture_hint, spec.material_type)
    return {
        "target_actor": spec.target_actor,
        "material_type": spec.material_type,
        "asset_path": resolution.asset_path,
        "source": resolution.source,
    }
```
The function name says "apply" but no `unreal.set_material(...)` / `MaterialEditingLibrary` call appears anywhere. The returned dict is appended to `result.applied_materials`, so `material_count` increases, but the spawned actor's mesh component is never bound to the resolved material. The DEMO-01 success criterion ("hero materials") is reported as satisfied via the count, but no material is actually visible in the scene.

**Fix:** Bind the material to the previously-spawned actor by `target_actor`:
```python
def _apply_material(self, spec, actor_lookup):
    resolution = self._fallback.resolve_material_asset(...)
    target_actor = actor_lookup.get(spec.target_actor)
    if target_actor and unreal:
        material = unreal.EditorAssetLibrary.load_asset(resolution.asset_path)
        smc = target_actor.get_component_by_class(unreal.StaticMeshComponent)
        if material and smc:
            smc.set_material(0, material)
    return {...}
```

### WR-11: `LightingAuthoringTool.execute` doesn't propagate WS notifier into the (re-created) `LightingLLMParser`

**File:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/lighting_tools.py:189-198`

**Issue:** `_resolve_lighting_params` constructs `LightingLLMParser(backend_router=self._router)` on every call, paying parser construction cost N times and producing a fresh logger context per call. More importantly, when `parse_from_image` falls back (e.g. router exception), the WS notifier on `LightingAuthoringTool` is never told that the LLM call failed and the user got the studio-fill default — they see "Lighting applied" without a hint that the request was downgraded.

**Fix:** Construct a single parser at `__init__` time and surface fallback events via the WS notifier so the chat panel can warn the user:
```python
def __init__(self, ...):
    ...
    self._parser = LightingLLMParser(backend_router=backend_router)

def _resolve_lighting_params(self, params):
    # ...
    lp = run_async_safely(self._parser.parse_from_image(path))
    if lp.confidence < 0.5:
        self._ws_notifier({"type": "lighting_fallback_used", "reason": "low_confidence"})
    return lp
```

## Info

### IN-01: `const_cast<SNyraLightingSelector*>(this)` is unnecessary inside a non-const lambda

**File:** `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraLightingSelector.cpp:97,101`

**Issue:** `this` is non-const inside `MakeCardWidget(const FNyraLightingPresetCard&)` because `MakeCardWidget` itself is a non-const member function. The lambda captures `this` by value (still non-const) so `HandleCardHovered`/`HandleCardUnhovered` (both non-const members) can be called directly. The `const_cast` is dead code that suggests confusion about Slate's mutability rules.

**Fix:** Drop both `const_cast`s.

### IN-02: `PoolEntry.resolved_at` stored as a string requires re-parsing for any temporal sorting / TTL logic

**File:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/asset_pool.py:74-80`

**Issue:** The pool persists `resolved_at` as an ISO-8601 string formatted with `.replace("+00:00", "Z")`. Any future TTL logic ("evict entries older than 7 days") must parse this back to `datetime`. Storing the float epoch (`time.time()`) keeps comparisons trivial and avoids the string-replace gymnastics.

**Fix:** Store `resolved_at: float` (epoch seconds) and only format on display.

### IN-03: Unused imports

**File:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/scene_assembler.py:15` (`from dataclasses import asdict`); `tools/scene_orchestrator.py:27` (`ProgressCallback` re-imported by scene_assembler.py:34); `canary/demo01_canary.py:17` (`from dataclasses import asdict`)

**Issue:** None of `asdict` is referenced in the importing modules. Linters like `ruff F401` would flag these.

**Fix:** Remove unused imports.

### IN-04: `SceneBlueprint` lacks an `error` field, so `SceneAssembler.analyze_image` swallows LLM errors silently

**File:** `tools/scene_types.py:39-46`; `tools/scene_assembler.py:67-70`

**Issue:** When `generate_image_description` raises, `analyze_image` logs the error and returns `_stub_blueprint(image_path)` with `confidence=0.4`. There is no way for AssembleSceneTool / the canary to distinguish "LLM analysis failed → stub" from "LLM analyzed → low confidence". Adding an optional `analysis_error: Optional[str] = None` to SceneBlueprint surfaces the cause to UI and makes the canary's PARTIAL verdict more accurate.

**Fix:** Add the field and populate it when stubbing. Have `assembler.assemble` propagate it into `result.error_message`.

### IN-05: Slate widgets duplicate the design-token color literals across three files

**File:** `Panel/SNyraLightingSelector.cpp:14-28`, `Panel/SNyraLightingPanel.cpp:14-27`, `Panel/SNyraImageDropZone.cpp:12-17`, `Panel/SNyraAssetChip.cpp:38-44`

**Issue:** Each Slate widget defines its own `Dominant` / `Accent` / `TextDim` color constants. The 06-UI-SPEC.md design tokens drift from each other in subtle ways already (e.g. `SNyraImageDropZone` lacks `Secondary`). Centralizing in a single `NyraDesignTokens` namespace prevents drift and lets a future theme change touch one file.

**Fix:**
```cpp
// NyraDesignTokens.h
namespace NyraDesignTokens
{
    extern const FLinearColor Dominant;
    extern const FLinearColor Secondary;
    extern const FLinearColor Accent;
    ...
}
```

---

_Reviewed: 2026-05-10_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
