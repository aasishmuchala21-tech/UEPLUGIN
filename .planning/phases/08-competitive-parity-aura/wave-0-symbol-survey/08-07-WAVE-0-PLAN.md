# Plan 08-07 — Wave 0 Operator Runbook (AnimBlueprint Symbol Survey)

> **Status:** `pending_manual_verification: true`
>
> This runbook is a placeholder. The four `symbol-survey-animbp-{ue}.md`
> outputs are produced by an operator, not by the autonomous executor. The
> survey can ONLY run after Task 1 (the C++ helper `UNyraAnimBPHelper`) has
> compiled into a real UE editor build. The autonomous executor cannot spawn
> UE 5.4/5.5/5.6/5.7 from this environment; the operator runs each version
> manually and commits the output.

## Pre-conditions (operator side)

1. UE editor is the version under test (5.4 / 5.5 / 5.6 / 5.7).
2. NyraEditor module has been recompiled with the Plan 08-07 changes:
   - `Source/NyraEditor/Public/ToolHelpers/NyraAnimBPHelper.h`
   - `Source/NyraEditor/Private/ToolHelpers/NyraAnimBPHelper.cpp`
   - `NyraEditor.Build.cs` PrivateDependencyModuleNames extended with
     `AnimGraph` + `AnimGraphRuntime` + `BlueprintGraph` (orchestrator
     batches that file edit per LOCKED-10).
3. The plugin builds clean and the editor launches without redlines.
4. A `USkeleton` asset exists somewhere in `/Game/...` (the default
   Mannequin skeleton at `/Game/Mannequin/Mannequin_Skeleton` works
   for the smoke test).

## Probe script (Python — paste into the UE Output Log Python REPL)

```python
import unreal
import time

print("=" * 60)
print(f"NyraAnimBPHelper symbol survey — UE {unreal.SystemLibrary.get_engine_version()}")
print("=" * 60)

# Reflection probe — does Python see the AnimBP authoring surface?
print("hasattr unreal.AnimBlueprint:",        hasattr(unreal, "AnimBlueprint"))
print("hasattr unreal.AnimBlueprintFactory:", hasattr(unreal, "AnimBlueprintFactory"))
print("hasattr unreal.AnimStateMachine:",     hasattr(unreal, "AnimStateMachine"))

print("AnimBlueprint symbols:", sorted(s for s in dir(unreal) if "AnimBlueprint" in s))
print("AnimGraph symbols:",     sorted(s for s in dir(unreal) if "AnimGraph"     in s))
print("AnimState symbols:",     sorted(s for s in dir(unreal) if "AnimState"     in s))

# Helper UCLASS reflection probe
present = hasattr(unreal, "NyraAnimBPHelper")
print("NyraAnimBPHelper present:", present)

if present:
    methods = [m for m in dir(unreal.NyraAnimBPHelper) if not m.startswith("_")]
    print("methods:", methods)

# Editor responsiveness check — wait 30s and confirm the editor is still alive.
print("Sleeping 30s; if the editor freezes, mark this version BAD.")
time.sleep(30)
print("Editor responsive after 30s.")
```

## Expected output template

For each UE version the operator runs the script and saves the console
output to:

- `.planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/symbol-survey-animbp-5.4.md`
- `... -5.5.md`
- `... -5.6.md`
- `... -5.7.md`

Each file uses this skeleton:

```markdown
# AnimBlueprint Symbol Survey — UE {VERSION}

**Operator:** {name/handle}
**Date:** YYYY-MM-DD
**Engine version (full):** 5.X.Y-build

## Reflection
- [ ] `unreal.AnimBlueprint` reflected:        PASS / FAIL
- [ ] `unreal.AnimBlueprintFactory` reflected: PASS / FAIL
- [ ] `unreal.AnimStateMachine` reflected:     PASS / FAIL
- [ ] `unreal.NyraAnimBPHelper` reflected:     PASS / FAIL
- Reflected helper methods: ...

## Editor responsiveness
- [ ] Editor responsive 30s after probe: YES / NO

## Verdict
- AnimBP authoring usable on this version: YES / NO
- If NO: register-time guard in `animbp_tools.py` already returns
  `not_supported_on_this_ue_version` — the plan does NOT abort.
```

## Fail-fast rule

Per PLAN.md §"Fail-fast rule": if `AnimBlueprintFactory` is **not reflected**
on a given version, the Python tool's register-time check returns
`NyraToolResult.err("unreal.AnimBlueprintFactory not reflected on this UE version")`
and the plan does NOT abort — fallback is the design (T-08-01).

## Build.cs deps that the orchestrator must add

Per LOCKED-10 the executor does NOT modify `NyraEditor.Build.cs`; the
orchestrator batches all Phase 8 plan deps in plan-number order in a single
commit at the end of the wave. Plan 08-07 needs **three** entries appended
to `PrivateDependencyModuleNames`:

```csharp
"AnimGraph",        // UAnimGraphNode_StateMachineBase, UAnimGraphNode_StateResult, UAnimStateTransitionNode
"AnimGraphRuntime", // UAnimStateMachineTypes / state-graph schema helpers
"BlueprintGraph",   // FBlueprintEditorUtils, UEdGraphSchema_K2, MarkBlueprintAsModified
```

Rationale:
- `AnimGraph`: editor-only AnimGraph node UClasses (state machine, state,
  transition) live here. Header `AnimGraphNode_StateMachine.h` is in this
  module.
- `AnimGraphRuntime`: state machine runtime types (`FAnimNode_StateMachine`)
  used by the editor graph nodes.
- `BlueprintGraph`: `FBlueprintEditorUtils` for `MarkBlueprintAsStructurallyModified`
  + `FindUserConstructionScript` and the K2 schema needed by the AnimGraph
  graph mutation helpers.

## mcp_server entries that the orchestrator must add

Per LOCKED-10 the executor does NOT modify
`nyrahost/mcp_server/__init__.py`. Plan 08-07 needs the orchestrator to
batch the following edits:

### Imports (after the existing PARITY-* import block):

```python
from nyrahost.tools.animbp_tools import (
    AnimBPCreateTool, AnimBPAddStateMachineTool, AnimBPAddTransitionTool,
)
```

### `_tools` dict entries (under a `# === Phase 8 PARITY-07 ===` banner):

```python
# PARITY-07: Animation Blueprint authoring
"nyra_animbp_create":             AnimBPCreateTool(),
"nyra_animbp_add_state_machine":  AnimBPAddStateMachineTool(),
"nyra_animbp_add_transition":     AnimBPAddTransitionTool(),
```

### `list_tools()` schemas (mirror the `nyra_actor_spawn` exemplar)

The three schemas must mirror the `tool.parameters` JSON Schemas declared
on each NyraTool subclass. The schema bodies are sourced verbatim from
the tool classes themselves; the orchestrator can copy `tool.parameters`
into the `inputSchema` field of each `Tool(...)` entry.

Tool names (for the schema list):
- `nyra_animbp_create`
- `nyra_animbp_add_state_machine`
- `nyra_animbp_add_transition`

## Why this lives outside the autonomous flow

The dev box (`C:\Users\aasis\UEPLUGIN`) does not have the four UE versions
side-by-side; the survey is genuinely operator-bound. The autonomous
executor produced this runbook (a) as proof Task 0 was considered, and
(b) so the operator has a paste-ready Python probe.
