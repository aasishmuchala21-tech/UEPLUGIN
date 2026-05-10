---
phase: 8
plan: 08-07
requirement: PARITY-07
type: execute
wave: 2
tier: 2
autonomous: false
depends_on: []
blocking_preconditions:
  - "Wave 0 UE Python symbol survey for unreal.AnimBlueprint* per UE 5.4/5.5/5.6/5.7 (Task 0 below)"
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/animbp_tools.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/__init__.py
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/ToolHelpers/NyraAnimBPHelper.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/ToolHelpers/NyraAnimBPHelper.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_animbp_authoring.py
  - .planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/symbol-survey-animbp-{ue}.md
---

# Plan 08-07: Animation Blueprint Authoring (PARITY-07)

## Goal

Ship the `nyra_animbp_create / nyra_animbp_add_state_machine / nyra_animbp_add_transition` triplet — Phase 4-shape mutators for AnimBP graph authoring (state machines + transitions only; no custom AnimNode generation per CONTEXT.md Out-of-Scope). C++ helper `UNyraAnimBPHelper` covers the AnimGraphNode spawn surface.

## Why this matches Aura

Per CONTEXT.md SC#7 (verbatim):

> **Matches Aura on Animation Blueprint authoring**: PARITY-07 ships `nyra_animbp_create / nyra_animbp_add_state_machine / nyra_animbp_add_transition`. Lower marketing visibility than BT but completes the "AI / character / animation" agent triplet.

This is a **matches**. Lower marketing visibility than PARITY-03 (BT) — but the same mutator-shape applies, so the cost is incremental.

## Wave 0: UE Python Symbol Survey

**Task 0** runs the symbol-survey script on each UE version BEFORE Tasks 1-5 land:

```python
import unreal
print("AnimBlueprint symbols:", [s for s in dir(unreal) if "AnimBlueprint" in s])
print("AnimGraph symbols:",     [s for s in dir(unreal) if "AnimGraph" in s])
print("hasattr AnimBlueprintFactory:", hasattr(unreal, "AnimBlueprintFactory"))
```

**Output:** `.planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/symbol-survey-animbp-{5.4,5.5,5.6,5.7}.md`

**Fail-fast rule:** if `AnimBlueprintFactory` not reflected on a shipped version, that version raises `not_supported_on_this_ue_version` at register-time. Plan does NOT abort.

## Pattern Compliance (Phase 4 mutator shape — LOCKED-03)

Per LOCKED-03 + PATTERNS.md §"PARITY-07 — Closest analog: PARITY-03 (BT)":

> Same Phase 4 mutator shape (`actor_tools.ActorSpawnTool` body), different UE asset class. Per-tool delta from BT: swap `unreal.BehaviorTree` → `unreal.AnimBlueprint`; swap composite/task/decorator nomenclature → state-machine/state/transition. All BL-04/05/06 wrapping identical.

| BL-helper | Where it's called | What it wraps |
|---|---|---|
| `idempotent_lookup(self.name, params)` | First line of `execute()` | Dedup repeats |
| `with session_transaction(...)`: | Wraps every AnimBP graph mutation | Ctrl+Z reverts |
| `verify_post_condition(...)` | After mutation | Re-load AnimBP, isinstance-check, confirm node count |
| `idempotent_record(...)` | Last line | Cache by hash |
| `NyraToolResult.ok({...})` / `.err(msg)` | Always | BL-01 envelope |

| Tool | post-condition (BL-06) check |
|---|---|
| `nyra_animbp_create` | `does_asset_exist(path)` AND `isinstance(load_asset(path), unreal.AnimBlueprint)` |
| `nyra_animbp_add_state_machine` | AnimGraph contains a state-machine node with the requested name |
| `nyra_animbp_add_transition` | Source state has outbound transition to target state |

## MCP Registration

**`nyrahost/mcp_server/__init__.py:_tools` dict** — slot under `# === Phase 8 PARITY-07 ===` banner:

```python
"nyra_animbp_create":             AnimBPCreateTool(),
"nyra_animbp_add_state_machine":  AnimBPAddStateMachineTool(),
"nyra_animbp_add_transition":     AnimBPAddTransitionTool(),
```

**Imports:**

```python
from nyrahost.tools.animbp_tools import (
    AnimBPCreateTool, AnimBPAddStateMachineTool, AnimBPAddTransitionTool,
)
```

**`list_tools()` schemas** — under PARITY-07 banner. Mirror `actor_tools.py:84-111` for parameters shape.

## C++ Helper Surface

**File:** `NyraEditor/Public/ToolHelpers/NyraAnimBPHelper.h`

```cpp
// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "Animation/AnimBlueprint.h"
#include "NyraAnimBPHelper.generated.h"

UCLASS(MinimalAPI)
class UNyraAnimBPHelper : public UObject
{
    GENERATED_BODY()

public:
    /** Add a state machine node to the AnimBP's AnimGraph. Returns the node name; empty on failure. */
    UFUNCTION(BlueprintCallable, Category="Nyra|AnimBP", meta=(ScriptMethod))
    static FString AddStateMachine(
        UAnimBlueprint* AnimBP, FName MachineName, FVector2D NodePos);

    /** Add a state to a state machine. */
    UFUNCTION(BlueprintCallable, Category="Nyra|AnimBP", meta=(ScriptMethod))
    static FString AddState(
        UAnimBlueprint* AnimBP, FName MachineName, FName StateName, FVector2D NodePos);

    /** Add a transition between two states inside a state machine. */
    UFUNCTION(BlueprintCallable, Category="Nyra|AnimBP", meta=(ScriptMethod))
    static bool AddTransition(
        UAnimBlueprint* AnimBP, FName MachineName, FName FromState, FName ToState);
};
```

**`NyraEditor.Build.cs`** — add to `PrivateDependencyModuleNames`: `"AnimGraph"`, `"AnimGraphRuntime"`, `"BlueprintGraph"`.

## Tasks

### Task 0: Wave 0 — UE Python symbol survey for AnimBP (operator-run)

**Files:**
- `.planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/symbol-survey-animbp-{5.4,5.5,5.6,5.7}.md`

**Action:** Per Wave 0 section above. Operator runs in each UE version's Python REPL.

**Verify:** Four files committed.

**Done:** Symbol matrix known.

### Task 1: Build C++ helper UCLASS — `UNyraAnimBPHelper`

**Files:**
- `NyraEditor/Public/ToolHelpers/NyraAnimBPHelper.h`
- `NyraEditor/Private/ToolHelpers/NyraAnimBPHelper.cpp`
- `NyraEditor/NyraEditor.Build.cs`

**Action:** Per the C++ Helper Surface section above. Implementation uses `UAnimGraphNode_StateMachineBase`, `UAnimGraphNode_StateMachine`, state graph manipulation via `UEdGraph` utilities. Module deps include `AnimGraph` + `AnimGraphRuntime` + `BlueprintGraph`.

**Verify:** UE 5.6 editor builds clean.

**Done:** `unreal.NyraAnimBPHelper.add_state_machine(...)` callable from Python.

### Task 2: Build three `nyra_animbp_*` mutator tools

**Files:** `nyrahost/tools/animbp_tools.py`

**Action — copy-rename of PARITY-03's `BTCreateTool` + `BTAddCompositeTool` (the exact same shape, different asset class):**

```python
"""
PARITY-07 — Animation Blueprint authoring mutators.

Tool shape mirrors bt_tools.py / actor_tools.py — five-step canonical
Phase 4 mutator. Different asset class (unreal.AnimBlueprint instead of
unreal.BehaviorTree), same helper composition.
"""
import structlog
from nyrahost.tools.base import (
    NyraTool, NyraToolResult,
    session_transaction, idempotent_lookup, idempotent_record,
    verify_post_condition,
)

log = structlog.get_logger("nyrahost.tools.animbp_tools")

__all__ = ["AnimBPCreateTool", "AnimBPAddStateMachineTool", "AnimBPAddTransitionTool"]


def _load_animbp(path: str):
    """Defensive lookup + isinstance check (BL-12)."""
    import unreal
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if asset is None:
        return None
    if not isinstance(asset, unreal.AnimBlueprint):
        return None
    return asset


class AnimBPCreateTool(NyraTool):
    name = "nyra_animbp_create"
    description = "Create a new UAnimBlueprint asset for the given Skeleton."
    parameters = {
        "type": "object",
        "properties": {
            "asset_path":     {"type": "string", "description": "/Game/Anim/ABP_Hero"},
            "skeleton_path":  {"type": "string", "description": "/Game/Anim/SK_Hero_Skeleton"},
        },
        "required": ["asset_path", "skeleton_path"],
    }

    def execute(self, params):
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        with session_transaction(f"NYRA: {self.name}"):
            try:
                import unreal
                if not hasattr(unreal, "AnimBlueprintFactory"):
                    return NyraToolResult.err(
                        "unreal.AnimBlueprintFactory not reflected on this UE version"
                    )
                skeleton = unreal.EditorAssetLibrary.load_asset(params["skeleton_path"])
                if not isinstance(skeleton, unreal.Skeleton):
                    return NyraToolResult.err(
                        f"skeleton_path must reference a USkeleton: {params['skeleton_path']}"
                    )
                factory = unreal.AnimBlueprintFactory()
                factory.set_editor_property("target_skeleton", skeleton)
                asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
                pkg_path, pkg_name = params["asset_path"].rsplit("/", 1)
                abp = asset_tools.create_asset(pkg_name, pkg_path, unreal.AnimBlueprint, factory)
                if abp is None:
                    return NyraToolResult.err(f"create_asset returned None for {params['asset_path']}")
                unreal.EditorAssetLibrary.save_asset(params["asset_path"])
            except Exception as e:
                log.error("animbp_create_failed", error=str(e))
                return NyraToolResult.err(f"failed: {e}")

            err = verify_post_condition(
                f"{self.name}({params['asset_path']})",
                lambda: _load_animbp(params["asset_path"]) is not None,
            )
            if err:
                return NyraToolResult.err(err)

        result = {"asset_path": params["asset_path"], "skeleton": params["skeleton_path"]}
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)


class AnimBPAddStateMachineTool(NyraTool):
    name = "nyra_animbp_add_state_machine"
    parameters = {
        "type": "object",
        "properties": {
            "animbp_path":   {"type": "string"},
            "machine_name":  {"type": "string"},
            "states":        {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional: state names to pre-create inside the machine",
            },
            "position":      {"type": "object", "properties": {"x": {"type": "number"}, "y": {"type": "number"}}},
        },
        "required": ["animbp_path", "machine_name"],
    }

    def execute(self, params):
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        with session_transaction(f"NYRA: {self.name}"):
            try:
                import unreal
                abp = _load_animbp(params["animbp_path"])
                if abp is None:
                    return NyraToolResult.err(f"AnimBP not found: {params['animbp_path']}")
                pos = params.get("position", {"x": 0, "y": 0})
                created = unreal.NyraAnimBPHelper.add_state_machine(
                    abp,
                    unreal.Name(params["machine_name"]),
                    unreal.Vector2D(pos["x"], pos["y"]),
                )
                if not created:
                    return NyraToolResult.err("AddStateMachine helper returned empty name")
                # Add pre-declared states if any
                for state_name in params.get("states", []):
                    unreal.NyraAnimBPHelper.add_state(
                        abp, unreal.Name(params["machine_name"]),
                        unreal.Name(state_name), unreal.Vector2D(0, 0),
                    )
                unreal.EditorAssetLibrary.save_asset(params["animbp_path"])
            except Exception as e:
                log.error("animbp_add_state_machine_failed", error=str(e))
                return NyraToolResult.err(f"failed: {e}")

            err = verify_post_condition(
                f"{self.name}({params['animbp_path']})",
                lambda: _load_animbp(params["animbp_path"]) is not None,
            )
            if err:
                return NyraToolResult.err(err)

        result = {"animbp_path": params["animbp_path"], "machine_name": created, "states": params.get("states", [])}
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)


class AnimBPAddTransitionTool(NyraTool):
    name = "nyra_animbp_add_transition"
    parameters = {
        "type": "object",
        "properties": {
            "animbp_path":   {"type": "string"},
            "machine_name":  {"type": "string"},
            "from_state":    {"type": "string"},
            "to_state":      {"type": "string"},
        },
        "required": ["animbp_path", "machine_name", "from_state", "to_state"],
    }
    # ... follows the same canonical shape ...
```

The third tool (`AnimBPAddTransitionTool`) is a copy-rename: calls `unreal.NyraAnimBPHelper.add_transition(abp, machine_name, from_state, to_state)` and verifies via re-load.

**Verify:** `pytest tests/test_animbp_authoring.py -x -q` (Task 4).

**Done:** Three tools subclass `NyraTool`, follow canonical shape.

### Task 3: MCP registration

**Files:** `nyrahost/mcp_server/__init__.py`

**Action:** Per the MCP Registration section above. Three entries under PARITY-07 banner.

**Verify:** `pytest tests/test_mcp_server.py::test_list_tools_includes_phase_8_parity_07 -x -q`.

**Done:** Three tools in `mcp_server.list_tools()`.

### Task 4: Build AnimBP unit tests with mocked `unreal`

**Files:** `tests/test_animbp_authoring.py`

**Action — minimum coverage:**
- `nyra_animbp_create("/Game/Anim/ABP_Hero", skeleton_path="/Game/Anim/SK_Hero")` succeeds with mocked `unreal.AnimBlueprintFactory + AssetTools`.
- Idempotent: second call returns `deduped: True`.
- Passing a non-Skeleton asset path → `err`.
- `nyra_animbp_add_state_machine` on missing AnimBP → `err`.
- `nyra_animbp_add_transition` from non-existent state → `err` (helper returns false; readback catches).
- Missing `AnimBlueprintFactory` symbol → register-time `err`.

**Verify:** `pytest tests/test_animbp_authoring.py -x -q` is green.

**Done:** Unit tests pass on dev box.

### Task 5: Operator-run verification — `pending_manual_verification: true`

**Files:** `08-07-VERIFICATION.md`

**Operator runbook (per UE version 5.4/5.5/5.6/5.7):**
1. UE editor with NYRA enabled
2. Identify a USkeleton (e.g. `/Game/Mannequin/Mannequin_Skeleton`)
3. `nyra_animbp_create("/Game/Anim/ABP_Test", skeleton_path="/Game/Mannequin/Mannequin_Skeleton")` — assert AnimBP created
4. `nyra_animbp_add_state_machine(animbp_path, machine_name="Locomotion", states=["Idle", "Walk", "Run"])` — assert state machine + 3 states
5. `nyra_animbp_add_transition(animbp_path, machine_name="Locomotion", from_state="Idle", to_state="Walk")` — assert transition appears in editor
6. Open AnimBP in editor and visually confirm graph matches

**Done:** VERIFICATION.md filled with PASS/FAIL per UE version.

## Tests

| Test file | What it verifies | Pending manual? |
|---|---|---|
| `tests/test_animbp_authoring.py` | Three tools' execute paths with mocked `unreal` | No |
| `tests/test_mcp_server.py::test_list_tools_includes_phase_8_parity_07` | MCP registration | No |
| `08-07-VERIFICATION.md` | Live state-machine + transition round-trip on UE 5.4/5.5/5.6/5.7 | **Yes** |

## Threats addressed

- **T-08-01** (UE Python API drift): Wave 0 symbol survey + `hasattr(unreal, "AnimBlueprintFactory")` register-time check.
- **PATTERNS.md S5 defensive coding**: every `unreal.*` symbol access is guarded; missing symbol → `not_supported_on_this_ue_version` error.
- **Out-of-Scope reminder** (no AnimNode generation): Plan ships state machines + transitions only. Custom AnimNode C++ class generation goes through PARITY-02, not here.

## Acceptance criteria

- [ ] Three `nyra_animbp_*` tools registered in `mcp_server.list_tools()` (`pytest tests/test_mcp_server.py::test_list_tools_includes_phase_8_parity_07 -x` passes).
- [ ] `pytest tests/test_animbp_authoring.py -x -q` is green — every tool returns `NyraToolResult`, dedup works, missing-symbol/wrong-asset-class returns `err` cleanly.
- [ ] `unreal.NyraAnimBPHelper.add_state_machine(...)` callable from Python in UE 5.6 editor.
- [ ] Wave 0 symbol survey artifacts (`symbol-survey-animbp-{ue}.md`) committed for each shipped UE version.
- [ ] `08-07-VERIFICATION.md` operator-run: state-machine with 3 states + 1 transition round-trips through editor → save → reopen and matches expected graph on UE 5.6 + at least one of {5.4, 5.5, 5.7}.

## Honest acknowledgments

- **`pending_manual_verification: true`** — Wave 0 + operator runbook required.
- **C++ helper mandatory** per RESEARCH.md A3 — AnimGraphNode classes are not Python-reflected.
- **Lower marketing visibility than BT** per CONTEXT.md SC#7 — but the cost is incremental once PARITY-03's pattern is paid.
- **No AnimNode generation** — CONTEXT.md Out-of-Scope.
