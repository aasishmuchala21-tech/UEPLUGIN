# Plan 08-07 — Operator Verification Runbook (PARITY-07)

> **Status:** `pending_manual_verification: true`
>
> This document is filled in by the operator running the smoke test on a
> real UE editor. The autonomous executor cannot drive an interactive UE
> editor, so per CONTEXT.md / PLAN.md §"Task 5" the round-trip lives here.

## Pre-conditions

1. UE editor under test is one of: 5.4 / 5.5 / 5.6 / 5.7.
2. NYRA plugin recompiled with Plan 08-07 changes:
   - `Source/NyraEditor/Public/ToolHelpers/NyraAnimBPHelper.h`
   - `Source/NyraEditor/Private/ToolHelpers/NyraAnimBPHelper.cpp`
   - `Source/NyraHost/src/nyrahost/tools/animbp_tools.py`
   - `NyraEditor.Build.cs` (orchestrator-batched per LOCKED-10)
   - `nyrahost/mcp_server/__init__.py` (orchestrator-batched per LOCKED-10)
3. NyraHost MCP server is running and reachable from a Claude Code or
   Claude Desktop session.
4. A `USkeleton` asset exists in the project (e.g. the default Mannequin
   skeleton at `/Game/Mannequin/Mannequin_Skeleton`).
5. The AnimBP target path (`/Game/Anim/ABP_Test`) is empty — if a prior
   run left an asset there, delete it before re-running so this captures
   a clean create + populate cycle.

## Smoke test (per UE version)

Run all four steps in a single MCP session so the idempotency cache and
the editor's transaction stack stay aligned.

### Step 1 — Create the AnimBP

Tool call:

```json
{
  "tool": "nyra_animbp_create",
  "args": {
    "asset_path": "/Game/Anim/ABP_Test",
    "skeleton_path": "/Game/Mannequin/Mannequin_Skeleton"
  }
}
```

Expected:
- Result: `{"asset_path": "/Game/Anim/ABP_Test", "skeleton": "/Game/Mannequin/Mannequin_Skeleton"}`
- The Content Browser shows `ABP_Test` in `/Game/Anim/`.
- Opening it yields an empty AnimGraph + valid Skeleton binding.

### Step 2 — Add a state machine with three pre-declared states

Tool call:

```json
{
  "tool": "nyra_animbp_add_state_machine",
  "args": {
    "animbp_path": "/Game/Anim/ABP_Test",
    "machine_name": "Locomotion",
    "states": ["Idle", "Walk", "Run"]
  }
}
```

Expected:
- Result: `{"animbp_path": "...", "machine_name": "Locomotion", "states": ["Idle", "Walk", "Run"]}`
- Opening the AnimBP editor shows a `Locomotion` state-machine node in the
  AnimGraph; double-click reveals a state-machine graph with three nodes
  named `Idle`, `Walk`, `Run`.

### Step 3 — Add a transition between two states

Tool call:

```json
{
  "tool": "nyra_animbp_add_transition",
  "args": {
    "animbp_path": "/Game/Anim/ABP_Test",
    "machine_name": "Locomotion",
    "from_state": "Idle",
    "to_state": "Walk"
  }
}
```

Expected:
- Result: `{"status": "added", "from_state": "Idle", "to_state": "Walk", ...}`
- The state-machine graph shows a directed transition arrow from `Idle`
  → `Walk` with the small T-shaped transition node mid-arrow.

### Step 4 — Recompile + visual confirmation

1. In the AnimBP editor, click **Compile**.
2. Confirm zero compile errors.
3. Save the AnimBP.
4. Close the editor and re-open the AnimBP from the Content Browser.
5. Confirm the state machine + states + transition all persist after
   the close/reopen.

## Result template

For each UE version the operator fills in:

```markdown
## UE 5.{VERSION}

| Step | Status | Notes |
|------|--------|-------|
| 1. nyra_animbp_create                | PASS / FAIL | |
| 2. nyra_animbp_add_state_machine     | PASS / FAIL | |
| 3. nyra_animbp_add_transition        | PASS / FAIL | |
| 4. Recompile + persist round-trip    | PASS / FAIL | |

**Overall:** PASS / FAIL
**Operator:** {name/handle}
**Date:** YYYY-MM-DD
**Engine version (full):** 5.X.Y-build
```

## Acceptance criteria (per PLAN.md §"Acceptance criteria")

- [ ] PASS on UE 5.6 (current stable, mandatory)
- [ ] PASS on at least one of {5.4, 5.5, 5.7}
- [ ] Wave 0 symbol survey artifacts (`symbol-survey-animbp-{ue}.md`) are
      committed alongside this verification.
- [ ] All four steps of each PASS run reproduce after editor close/reopen.

## Failure remediation

- If `nyra_animbp_create` fails with `AnimBlueprintFactory not reflected`:
  expected on UE versions where the factory binding wasn't generated; flag
  as a per-version `not_supported_on_this_ue_version` in the survey and
  do not abort the plan.
- If `nyra_animbp_add_state_machine` returns `AddStateMachine helper
  returned empty name`: the AnimBP was created without an AnimGraph.
  Re-create it via Step 1 (which uses `AnimBlueprintFactory` and always
  produces an AnimGraph). If the second attempt also fails, the C++ helper
  needs a `FindAnimGraph` patch for that UE version — file under the
  Wave 0 survey for follow-up.
- If `nyra_animbp_add_transition` returns `AddTransition refused`: open
  the state-machine graph and confirm both states exist with the EXACT
  spelling/casing passed to the tool — state-name lookup is case-sensitive
  by FName.
