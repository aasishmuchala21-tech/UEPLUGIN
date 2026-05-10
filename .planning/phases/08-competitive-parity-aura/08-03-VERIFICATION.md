---
phase: 8
plan: 08-03
type: operator-verification
pending_manual_verification: true
title: PARITY-03 — Live UE editor verification of BT authoring
status: pending
ue_versions: [5.4, 5.5, 5.6, 5.7]
preconditions:
  - 08-03-WAVE-0-PLAN.md completed (per-version symbol survey passed)
  - NYRA plugin enabled in TestProject.uproject
  - NyraEditor + NyraHost modules loaded
  - Python sidecar reachable on loopback (default port from project settings)
related:
  - 08-03-behavior-tree-agent-PLAN.md
  - 08-03-WAVE-0-PLAN.md
---

# PARITY-03 — Live UE Editor Verification (Operator Runbook)

> Operator-run smoke test for the five BT mutator tools on a real
> UE editor. Repeat per-version for any UE version that PASSED Wave 0.

## What we're verifying

1. The five Python tools (`nyra_bt_create`, `nyra_bt_add_composite`,
   `nyra_bt_add_task`, `nyra_bt_add_decorator`,
   `nyra_bt_set_blackboard_key`) dispatch from MCP through the C++
   `UNyraBTHelper` and produce a real BT graph.
2. The graph round-trips through editor save → close → reopen.
3. Recompile is clean (no UHT/HotReload errors emitted).
4. Idempotency works: running the same sequence twice does not
   duplicate nodes.

## Test scenario: Guard Patrol BT

A small but exercised graph:

```
Root  (Selector)
 ├── Sequence_0
 │    ├── BTTask_MoveTo                  (decorated by BTDecorator_Blackboard "TargetActor")
 │    └── BTTask_Wait
 └── BTTask_RunBehavior  (or fallback wait)
```

Blackboard `BB_GuardPatrol` should contain:

| Key          | Type    |
|--------------|---------|
| TargetActor  | Object  |
| HomeLocation | Vector  |
| IsAlerted    | Bool    |

## Procedure

### Step 1 — Open TestProject in the UE version under test

1. Launch UE 5.X, open TestProject.
2. Confirm NYRA panel appears in the editor (`Window → NYRA`).
3. Open `NYRA → Show MCP Server Log` and confirm the sidecar is running.

### Step 2 — Create the Blackboard

The blackboard asset must exist before the BT references it. From the
NYRA chat panel:

```
Create a Blackboard at /Game/AI/BB_GuardPatrol with these keys:
  - TargetActor (Object)
  - HomeLocation (Vector)
  - IsAlerted (Bool)
```

Expected: NYRA invokes `nyra_bt_set_blackboard_key` three times after
auto-creating the BB asset (or operator pre-creates BB_GuardPatrol via
right-click → AI → Blackboard, then NYRA only adds keys). Verify in
the Content Browser that `BB_GuardPatrol` opens cleanly with three keys
of the expected types.

### Step 3 — Create the Behavior Tree

```
Create a BehaviorTree at /Game/AI/BT_GuardPatrol bound to /Game/AI/BB_GuardPatrol
```

Expected: `nyra_bt_create` returns `{ asset_path, blackboard }`.
Open `BT_GuardPatrol` in the editor — Blackboard panel shows
`BB_GuardPatrol`'s keys.

### Step 4 — Build the graph

```
Under the BT root, add a Selector. Under that Selector, add a Sequence.
Under the Sequence, add BTTask_MoveTo (decorated by BTDecorator_Blackboard
on key TargetActor) and BTTask_Wait. As a sibling of the Sequence, add
BTTask_RunBehavior.
```

Expected: four `nyra_bt_add_composite` / `nyra_bt_add_task` /
`nyra_bt_add_decorator` calls, each returning `node_name`.
Open the BT in the graph editor — visually confirm the layout.

### Step 5 — Save, close, reopen

1. Ctrl+S to save the BT asset.
2. Close `BT_GuardPatrol`.
3. Re-open it.
4. Confirm the graph is identical (no missing nodes, decorator still on
   MoveTo).

### Step 6 — Idempotency check

1. Re-run the exact same chat prompt from Step 4.
2. Expected: each tool returns `deduped: True`. Graph is unchanged.
3. Open `BT_GuardPatrol` — node count is the same as before.

### Step 7 — Recompile pass

1. `Tools → Recompile Game Code` (or trigger Live Coding).
2. Confirm no errors in the Output Log relating to NyraEditor.

### Step 8 — (Optional) Pawn-runs-the-BT

1. Spawn a pawn with `BrainComponent` configured to run
   `BT_GuardPatrol`.
2. PIE.
3. Verify the pawn enters Sequence_0 and runs MoveTo (target need not
   be set — what we're verifying is the BT *runs*, not its semantics).

## Per-version result table

Fill in PASS/FAIL/N-A per step per version after running:

| Step                          | UE 5.4 | UE 5.5 | UE 5.6 | UE 5.7 |
|-------------------------------|--------|--------|--------|--------|
| 1. Editor + NYRA panel open   |        |        |        |        |
| 2. Blackboard asset + 3 keys  |        |        |        |        |
| 3. BT created bound to BB     |        |        |        |        |
| 4. Graph authored end-to-end  |        |        |        |        |
| 5. Save / close / reopen      |        |        |        |        |
| 6. Idempotency (deduped:True) |        |        |        |        |
| 7. Recompile pass             |        |        |        |        |
| 8. Pawn runs BT (optional)    |        |        |        |        |

## Failure-mode notes

- **`unreal.NyraBTHelper not registered`** at any step → NyraEditor
  module did not load; check the editor's Output Log for module-load
  errors. This is a Wave 0 regression — recheck the symbol survey.
- **`AddCompositeNode helper returned empty name`** with `parent_node:
  "Root"` → `BT->RootNode` resolution edge case in `UNyraBTHelper.cpp`.
  Capture: Output Log lines tagged `LogNyraBT`, plus the BT's current
  RootNode FName.
- **Decorator missing after reopen** → 5.7 may have moved the
  per-task decorator storage (see `UNyraBTHelper::AddDecoratorNode`'s
  `TODO(version-drift)`). Capture the .uasset diff before vs. after
  reopen.
- **Blackboard key not visible in BT editor** → likely the BB asset
  package was not saved. Verify `UEditorAssetLibrary::SaveAsset`
  fires after `SetBlackboardKey`.

## Done criteria

- [ ] All applicable rows in the result table are PASS for at least
      UE 5.6 (the canonical target).
- [ ] At least two other UE versions are PASS (per LOCKED-09's
      6-of-8-plans EXIT bar — this plan needs broad version
      coverage, not exhaustive).
- [ ] Failure-mode artifacts (Output Log excerpts, .uasset diffs)
      committed for any FAIL row.

## Where to record results

Update this file in-place with the table filled in. Commit:

`docs(08-03): live UE verification — UE 5.X PASS/FAIL`
