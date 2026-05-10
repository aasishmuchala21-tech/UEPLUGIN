---
phase: 8
plan: 08-03
requirement: PARITY-03
type: execute
wave: 2
tier: 1
autonomous: false
depends_on: []
blocking_preconditions:
  - "Wave 0 UE Python symbol survey for unreal.BehaviorTree* + BlackboardData per UE 5.4/5.5/5.6/5.7 (Task 0 below)"
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/bt_tools.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/__init__.py
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/ToolHelpers/NyraBTHelper.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/ToolHelpers/NyraBTHelper.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_bt_authoring.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_unreal_symbols_bt.py
  - .planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/symbol-survey-bt-{ue}.md
---

# Plan 08-03: Behavior Tree Authoring Agent (PARITY-03)

## Goal

Ship the `nyra_bt_create / nyra_bt_add_composite / nyra_bt_add_task / nyra_bt_add_decorator / nyra_bt_set_blackboard_key` quintet as Phase 4-shape mutators. Each tool transactional (BL-04), idempotent (BL-05), post-condition-verified (BL-06). Where `unreal.*` doesn't reflect the EdGraph node spawn surface, a `UNyraBTHelper` UCLASS bridges the gap.

## Why this beats Aura

Per CONTEXT.md SC#3 (verbatim):

> **Beats Aura on Behavior Tree authoring**: PARITY-03 ships `nyra_bt_create / nyra_bt_add_composite / nyra_bt_add_task / nyra_bt_add_decorator / nyra_bt_set_blackboard_key` quintet via UE's `unreal.BehaviorTree` Python API. Aura's BT agent is monolithic; NYRA's surface is composable, idempotent (BL-05 pattern from Phase 4), and post-condition-verified (BL-06).

Aura's BT agent is documented "alpha" with AI Perception confusion (per RESEARCH.md Open Question 4). NYRA's mutator-shape gives "composable + transactional + verified" headroom Aura's monolith cannot reach.

## Wave 0: UE Python Symbol Survey

**Task 0** runs the symbol-survey script on each UE version BEFORE Tasks 1-5 land:

```python
import unreal
print("BehaviorTree symbols:", [s for s in dir(unreal) if "BehaviorTree" in s])
print("Blackboard symbols:",   [s for s in dir(unreal) if "Blackboard" in s])
print("BTComposite symbols:",  [s for s in dir(unreal) if "BTComposite" in s])
print("BTDecorator symbols:",  [s for s in dir(unreal) if "BTDecorator" in s])
print("BTTask symbols:",       [s for s in dir(unreal) if "BTTask" in s])
# Reachability probes
print("hasattr BehaviorTreeFactory:", hasattr(unreal, "BehaviorTreeFactory"))
print("hasattr BlackboardData:",      hasattr(unreal, "BlackboardData"))
```

**Output:** `.planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/symbol-survey-bt-{5.4,5.5,5.6,5.7}.md` — one per UE version.

**Fail-fast rule:** if `BehaviorTreeFactory` is not reflected on a version we ship for, that version raises `not_supported_on_this_ue_version` at register-time (per RESEARCH.md §Pitfall 1) — never silently no-op. The plan does NOT abort: defensive-coding pattern S5 from PATTERNS.md applies.

## Pattern Compliance (Phase 4 mutator shape — LOCKED-03)

Per LOCKED-03 + PATTERNS.md §"Per-Plan §PARITY-03", every BT tool is a copy-rename of `actor_tools.ActorSpawnTool.execute` (lines 78-170). Specifics:

| BL-helper | Where it's called | What it wraps |
|---|---|---|
| `idempotent_lookup(self.name, params)` | First line of `execute()` | Calling `nyra_bt_add_task` twice with the same `(bt_path, parent_node, task_class)` returns `deduped: True` |
| `with session_transaction(f"NYRA: {self.name}"):` | Wraps every BT graph mutation | Ctrl+Z reverts the entire mutation |
| `verify_post_condition(label, lambda: ...)` | After mutation | Re-load BT asset, isinstance-check `unreal.BehaviorTree`, confirm node count increased |
| `idempotent_record(self.name, params, data)` | Last line before `return ok(...)` | Cache by hash of (tool, params) |
| `NyraToolResult.ok({...})` / `.err(msg)` | Always | BL-01 envelope |

| Tool | post-condition (BL-06) check |
|---|---|
| `nyra_bt_create` | `unreal.EditorAssetLibrary.does_asset_exist(bt_path)` AND `isinstance(load_asset(bt_path), unreal.BehaviorTree)` |
| `nyra_bt_add_composite` | After mutation, BT root has child whose class matches `composite_class` |
| `nyra_bt_add_task` | Parent composite has the new task as child; node count +1 |
| `nyra_bt_add_decorator` | Target node has decorator in its decorator list |
| `nyra_bt_set_blackboard_key` | `BlackboardData.keys` contains key with matching name + type |

## MCP Registration

Per PATTERNS.md §"MCP Server Registration":

**`nyrahost/mcp_server/__init__.py:_tools` dict** — slot after PARITY-02 entries (after Plan 08-02 lines), banner `# === Phase 8 PARITY-03 ===`:

```python
"nyra_bt_create":              BTCreateTool(),
"nyra_bt_add_composite":       BTAddCompositeTool(),
"nyra_bt_add_task":            BTAddTaskTool(),
"nyra_bt_add_decorator":       BTAddDecoratorTool(),
"nyra_bt_set_blackboard_key":  BTSetBlackboardKeyTool(),
```

**Imports** — after the PARITY-02 import block:

```python
from nyrahost.tools.bt_tools import (
    BTCreateTool, BTAddCompositeTool, BTAddTaskTool,
    BTAddDecoratorTool, BTSetBlackboardKeyTool,
)
```

**`list_tools()` schemas** — slot in the PARITY-03 banner section after the PARITY-02 schemas. Mirror `actor_tools.py:84-111` (richest `parameters` exemplar).

## C++ Helper Surface

**File:** `NyraEditor/Public/ToolHelpers/NyraBTHelper.h`

```cpp
// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "BehaviorTree/BehaviorTree.h"
#include "BehaviorTree/BlackboardData.h"
#include "NyraBTHelper.generated.h"

UCLASS(MinimalAPI)
class UNyraBTHelper : public UObject
{
    GENERATED_BODY()

public:
    /** Add a composite node (Selector / Sequence / SimpleParallel) to the BT root or a parent.
     *  Returns the created node's name; empty string on failure.
     */
    UFUNCTION(BlueprintCallable, Category="Nyra|BT", meta=(ScriptMethod))
    static FString AddCompositeNode(
        UBehaviorTree* BT, FName CompositeClass, FName ParentName, FVector2D NodePos);

    /** Add a task node under a composite. */
    UFUNCTION(BlueprintCallable, Category="Nyra|BT", meta=(ScriptMethod))
    static FString AddTaskNode(
        UBehaviorTree* BT, FName TaskClass, FName ParentName, FVector2D NodePos);

    /** Add a decorator to an existing node. */
    UFUNCTION(BlueprintCallable, Category="Nyra|BT", meta=(ScriptMethod))
    static bool AddDecoratorNode(
        UBehaviorTree* BT, FName DecoratorClass, FName TargetNodeName);

    /** Set or create a Blackboard key. */
    UFUNCTION(BlueprintCallable, Category="Nyra|BT", meta=(ScriptMethod))
    static bool SetBlackboardKey(
        UBlackboardData* BB, FName KeyName, FName KeyType);
};
```

**`NyraEditor.Build.cs`** — add to `PrivateDependencyModuleNames`: `"AIModule"`, `"BehaviorTreeEditor"`.

**Python entrypoint:** `unreal.NyraBTHelper.add_composite_node(bt, "BTComposite_Sequence", "Root", unreal.Vector2D(0, 0))`.

## Tasks

### Task 0: Wave 0 — UE Python symbol survey for BT (operator-run on each UE version)

**Files:**
- `.planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/symbol-survey-bt-5.4.md`
- `... -5.5.md`, `... -5.6.md`, `... -5.7.md`
- `tests/test_unreal_symbols_bt.py` (skip when no `unreal` module)

**Action:** Operator runs the symbol-survey script (see Wave 0 section above) inside each UE version's Python REPL. Commits output verbatim. Records reachable-vs-missing symbols.

**Fail-fast:** if `BehaviorTreeFactory` missing on a version, mark that version `unsupported_on_this_ue_version` in the tool init (per PATTERNS.md S5 defensive coding pattern).

**Verify:** Four `symbol-survey-bt-{ue}.md` files committed.

**Done:** Symbol matrix known; tool init code can branch correctly.

### Task 1: Build C++ helper UCLASS — `UNyraBTHelper`

**Files:**
- `NyraEditor/Public/ToolHelpers/NyraBTHelper.h`
- `NyraEditor/Private/ToolHelpers/NyraBTHelper.cpp`
- `NyraEditor/NyraEditor.Build.cs`

**Action:** Per the C++ Helper Surface section above. Implementation uses `UBehaviorTreeGraph` + `UEdGraphNode_BehaviorTreeComposite/Task/Decorator` from `BehaviorTreeEditor` module. Each function logs via `UE_LOG(LogNyra, ...)` and returns failure as empty FString / false.

**Verify:** UE editor builds clean on UE 5.6. Operator-run confirms reflection on 5.4/5.5/5.7 in Task 0.

**Done:** `unreal.NyraBTHelper.add_composite_node(...)` callable from Python in editor.

### Task 2: Build five `nyra_bt_*` mutator tools

**Files:** `nyrahost/tools/bt_tools.py`

**Action — copy-rename of `ActorSpawnTool` (PATTERNS.md canonical example):**

```python
"""
PARITY-03 — Behavior Tree authoring mutators.

Every tool is a copy-rename of actor_tools.ActorSpawnTool — same five-step
canonical Phase 4 mutator shape (BL-04/05/06).
"""
import structlog
from nyrahost.tools.base import (
    NyraTool, NyraToolResult,
    session_transaction, idempotent_lookup, idempotent_record,
    verify_post_condition,
)

log = structlog.get_logger("nyrahost.tools.bt_tools")

__all__ = [
    "BTCreateTool", "BTAddCompositeTool", "BTAddTaskTool",
    "BTAddDecoratorTool", "BTSetBlackboardKeyTool",
]


def _load_bt_asset(path: str):
    """Defensive UE 5.4-5.7 lookup; pattern from actor_tools.py:43-64."""
    import unreal
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if asset is None:
        return None
    if not isinstance(asset, unreal.BehaviorTree):
        return None
    return asset


class BTCreateTool(NyraTool):
    name = "nyra_bt_create"
    description = "Create a new UBehaviorTree asset at the given content path."
    parameters = {
        "type": "object",
        "properties": {
            "asset_path":  {"type": "string", "description": "/Game/AI/BT_MyTree"},
            "blackboard":  {"type": "string", "description": "/Game/AI/BB_MyBlackboard (optional)"},
        },
        "required": ["asset_path"],
    }

    def execute(self, params):
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        with session_transaction(f"NYRA: {self.name}"):
            try:
                import unreal
                if not hasattr(unreal, "BehaviorTreeFactory"):
                    return NyraToolResult.err(
                        "unreal.BehaviorTreeFactory not reflected on this UE version; "
                        "see Wave 0 symbol survey"
                    )
                factory = unreal.BehaviorTreeFactory()
                asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
                pkg_path, pkg_name = params["asset_path"].rsplit("/", 1)
                bt = asset_tools.create_asset(pkg_name, pkg_path, unreal.BehaviorTree, factory)
                if bt is None:
                    return NyraToolResult.err(f"create_asset returned None for {params['asset_path']}")
                if params.get("blackboard"):
                    bb = unreal.EditorAssetLibrary.load_asset(params["blackboard"])
                    if isinstance(bb, unreal.BlackboardData):
                        bt.blackboard_asset = bb
                unreal.EditorAssetLibrary.save_asset(params["asset_path"])
            except Exception as e:
                log.error("bt_create_failed", error=str(e))
                return NyraToolResult.err(f"failed: {e}")

            err = verify_post_condition(
                f"{self.name}({params['asset_path']})",
                lambda: _load_bt_asset(params["asset_path"]) is not None,
            )
            if err:
                return NyraToolResult.err(err)

        result = {"asset_path": params["asset_path"], "blackboard": params.get("blackboard")}
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)


class BTAddCompositeTool(NyraTool):
    name = "nyra_bt_add_composite"
    parameters = {
        "type": "object",
        "properties": {
            "bt_path":         {"type": "string"},
            "parent_node":     {"type": "string", "description": "'Root' or composite name"},
            "composite_class": {"type": "string", "enum": ["Selector", "Sequence", "SimpleParallel"]},
            "node_name":       {"type": "string"},
            "position":        {"type": "object", "properties": {"x": {"type": "number"}, "y": {"type": "number"}}},
        },
        "required": ["bt_path", "parent_node", "composite_class"],
    }

    def execute(self, params):
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        with session_transaction(f"NYRA: {self.name}"):
            try:
                import unreal
                bt = _load_bt_asset(params["bt_path"])
                if bt is None:
                    return NyraToolResult.err(f"BT not found: {params['bt_path']}")
                pos = params.get("position", {"x": 0, "y": 0})
                created = unreal.NyraBTHelper.add_composite_node(
                    bt,
                    f"BTComposite_{params['composite_class']}",
                    params["parent_node"],
                    unreal.Vector2D(pos["x"], pos["y"]),
                )
                if not created:
                    return NyraToolResult.err("AddCompositeNode helper returned empty name")
                unreal.EditorAssetLibrary.save_asset(params["bt_path"])
            except Exception as e:
                log.error("bt_add_composite_failed", error=str(e))
                return NyraToolResult.err(f"failed: {e}")

            err = verify_post_condition(
                f"{self.name}({params['bt_path']})",
                lambda: _load_bt_asset(params["bt_path"]) is not None,
            )
            if err:
                return NyraToolResult.err(err)

        result = {"bt_path": params["bt_path"], "node_name": created, "composite_class": params["composite_class"]}
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)


# BTAddTaskTool, BTAddDecoratorTool, BTSetBlackboardKeyTool follow the
# same shape — same five-step mutator skeleton, different helper call.
```

The remaining three tools (`BTAddTaskTool`, `BTAddDecoratorTool`, `BTSetBlackboardKeyTool`) are copy-renames with these specifics:

- `BTAddTaskTool.parameters`: `bt_path`, `parent_composite`, `task_class` (FName like `BTTask_MoveTo`), `position`. Calls `unreal.NyraBTHelper.add_task_node(...)`.
- `BTAddDecoratorTool.parameters`: `bt_path`, `target_node`, `decorator_class` (FName like `BTDecorator_Blackboard`). Calls `unreal.NyraBTHelper.add_decorator_node(...)`.
- `BTSetBlackboardKeyTool.parameters`: `blackboard_path`, `key_name`, `key_type` (`enum: ["Bool", "Int", "Float", "String", "Vector", "Object"]`). Calls `unreal.NyraBTHelper.set_blackboard_key(...)`.

**Verify:** `pytest tests/test_bt_authoring.py -x -q` (Task 4).

**Done:** All five tools subclass `NyraTool`, follow the canonical shape, return `NyraToolResult`.

### Task 3: MCP registration — imports + `_tools` dict + `list_tools()` schemas

**Files:** `nyrahost/mcp_server/__init__.py`

**Action:** Per the MCP Registration section above. Five entries under PARITY-03 banner; matching schemas after PARITY-02 schemas.

**Verify:** `pytest tests/test_mcp_server.py::test_list_tools_includes_phase_8_parity_03 -x -q`.

**Done:** `mcp_server.list_tools()` returns the five PARITY-03 tools.

### Task 4: Build BT unit tests with mocked `unreal`

**Files:** `tests/test_bt_authoring.py`

**Action — minimum coverage (using existing `tests/conftest.py` mocked-unreal pattern from `test_attachments.py`):**
- Each tool's parameters validate (JSON-schema-driven).
- `nyra_bt_create("/Game/AI/BT_X")` succeeds with mocked `unreal.BehaviorTreeFactory + AssetTools`.
- Calling `nyra_bt_create` twice with same path returns `deduped: True` on the second call.
- `nyra_bt_add_composite` on a non-existent BT path returns `err`.
- Mocked `unreal` missing `BehaviorTreeFactory` → `BTCreateTool.execute` returns `err` with the "not reflected" message.
- All return `NyraToolResult` (never raw dict).

**Verify:** `pytest tests/test_bt_authoring.py -x -q` is green.

**Done:** Unit tests pass on dev box without UE editor.

### Task 5: Operator-run verification (live UE editor) — `pending_manual_verification: true`

**Files:** `08-03-VERIFICATION.md`

**Operator runbook:**
1. UE 5.6 editor with NYRA enabled
2. Build a BT: `nyra_bt_create("/Game/AI/BT_GuardPatrol", blackboard="/Game/AI/BB_GuardPatrol")`
3. Add a Sequence composite under root, then `BTTask_MoveTo` under it, then `BTDecorator_Blackboard` on the task
4. Open the BT in the editor and assert the graph matches
5. Run a test pawn that uses this BT — verify behavior runs (move-to)
6. Repeat on UE 5.4/5.5/5.7

**Done:** VERIFICATION.md filled with PASS/FAIL per UE version.

## Tests

| Test file | What it verifies | Pending manual? |
|---|---|---|
| `tests/test_bt_authoring.py` | Five tools' execute paths with mocked `unreal` | No |
| `tests/test_unreal_symbols_bt.py` | Operator-run; symbols present per UE version | **Yes** (operator) |
| `tests/test_mcp_server.py::test_list_tools_includes_phase_8_parity_03` | MCP registration | No |
| `08-03-VERIFICATION.md` | Live BT graph round-trip on UE 5.4/5.5/5.6/5.7 | **Yes** |

## Threats addressed

- **T-08-01** (UE Python API drift 5.4 → 5.7): Wave 0 symbol survey + `hasattr(unreal, "BehaviorTreeFactory")` register-time check.
- **PATTERNS.md S5 defensive coding**: every `unreal.*` symbol access is guarded. Missing symbol → `not_supported_on_this_ue_version` error, never silent no-op.
- **Out-of-Scope reminder**: Plan ships graph authoring only — composite/decorator/task instances drawn from existing classes. New BT task IMPLEMENTATIONS go through PARITY-02's C++ surface, not here.

## Acceptance criteria

- [ ] All five `nyra_bt_*` tools registered in `mcp_server.list_tools()` with valid JSON schemas (`pytest tests/test_mcp_server.py::test_list_tools_includes_phase_8_parity_03 -x` passes).
- [ ] `pytest tests/test_bt_authoring.py -x -q` is green — every tool returns `NyraToolResult`, dedup works, missing `unreal` symbol returns `err` cleanly.
- [ ] `unreal.NyraBTHelper.add_composite_node(...)` callable from Python in UE 5.6 editor (operator-confirmed in Task 5).
- [ ] Wave 0 symbol survey artifacts (`symbol-survey-bt-{ue}.md`) committed for each shipped UE version.
- [ ] `08-03-VERIFICATION.md` operator-run: build a 4-node BT (composite + task + decorator + bb-key) round-trips through editor → save → reopen and matches expected graph.

## Honest acknowledgments

- **`pending_manual_verification: true`** — Wave 0 symbol survey requires live UE editors. The dev box has only one UE version. Operator runs on each.
- **C++ helper surface is mandatory** per RESEARCH.md A1 — `unreal.BehaviorTree` is reflected for asset creation but EdGraph node spawn classes are not. The 50-line UCLASS is the cheapest path; building this without it would require ad-hoc `set_editor_property` calls that break dirty tracking + undo capture.
- **No new BT task IMPLEMENTATIONS** in this plan — that's PARITY-02 territory per CONTEXT.md Out-of-Scope.
