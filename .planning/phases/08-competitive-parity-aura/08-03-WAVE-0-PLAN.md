---
phase: 8
plan: 08-03
wave: 0
type: operator-runbook
pending_manual_verification: true
title: Wave 0 — UE Python symbol survey for BehaviorTree authoring (PARITY-03)
status: pending
ue_versions: [5.4, 5.5, 5.6, 5.7]
output_dir: wave-0-symbol-survey/
output_template: 08-03-bt-symbols-{ue}.md
related:
  - 08-03-behavior-tree-agent-PLAN.md
  - 08-03-VERIFICATION.md
---

# Wave 0 — UE Python Symbol Survey for PARITY-03 (Behavior Trees)

> **Operator-run on every shipped UE version (5.4 / 5.5 / 5.6 / 5.7)**
> before Plan 08-03 unblocks. This runbook is intentionally manual:
> the dev box has only a single UE install, the orchestrator cannot
> shell into the other three.

## Purpose

Confirm that the Python entrypoints Plan 08-03 depends on are
**reflected** on each UE version we ship for. Per CONTEXT.md
T-08-01 + PATTERNS.md §S5, missing symbols must surface as
`not_supported_on_this_ue_version` errors at register-time — never
silent no-ops.

## Symbols under audit

The Python tools (`nyrahost/tools/bt_tools.py`) call:

- `unreal.BehaviorTreeFactory()`
- `unreal.AssetToolsHelpers.get_asset_tools()`
- `unreal.EditorAssetLibrary.{load_asset, save_asset, does_asset_exist}`
- `unreal.BehaviorTree`
- `unreal.BlackboardData`
- `unreal.NyraBTHelper.{create_behavior_tree, add_composite_node, add_task_node, add_decorator_node, set_blackboard_key}`
  (registered by the C++ `UNyraBTHelper` UCLASS — only present once
  the NYRA plugin is loaded into the editor)
- `unreal.Vector2D(x, y)` (for node-graph positions)

## Procedure (per UE version)

1. Open the UE editor for the version under audit.
2. Make sure the NYRA plugin is enabled and the `NyraEditor` module
   loaded (so `unreal.NyraBTHelper` becomes reflected).
3. Open **Window → Developer Tools → Python Console** (or "Output
   Log" with the language switched to Python).
4. Paste and run the following script verbatim:

```python
import unreal
import json

probe = {
    "ue_version": unreal.SystemLibrary.get_engine_version(),
    "BehaviorTree_symbols": [s for s in dir(unreal) if "BehaviorTree" in s],
    "Blackboard_symbols":   [s for s in dir(unreal) if "Blackboard" in s],
    "BTComposite_symbols":  [s for s in dir(unreal) if "BTComposite" in s],
    "BTDecorator_symbols":  [s for s in dir(unreal) if "BTDecorator" in s],
    "BTTask_symbols":       [s for s in dir(unreal) if "BTTask" in s],
    "AssetTools_methods":   [m for m in dir(unreal.AssetToolsHelpers.get_asset_tools()) if not m.startswith("_")],
    "EditorAssetLibrary_methods": [m for m in dir(unreal.EditorAssetLibrary) if not m.startswith("_")],
    "reachability": {
        "BehaviorTreeFactory":    hasattr(unreal, "BehaviorTreeFactory"),
        "BlackboardData":         hasattr(unreal, "BlackboardData"),
        "BehaviorTree":           hasattr(unreal, "BehaviorTree"),
        "Vector2D":               hasattr(unreal, "Vector2D"),
        "NyraBTHelper":           hasattr(unreal, "NyraBTHelper"),
        "NyraBTHelper_methods":   sorted(
            [m for m in dir(getattr(unreal, "NyraBTHelper", object)) if not m.startswith("_")]
        ) if hasattr(unreal, "NyraBTHelper") else [],
    },
}
print(json.dumps(probe, indent=2, default=str))
```

5. Copy the JSON output verbatim into a new file:

   `.planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/08-03-bt-symbols-{ue}.md`

   (Replace `{ue}` with `5.4`, `5.5`, `5.6`, or `5.7`.)

6. Add a one-line PASS/FAIL header at the top of each file:

```md
# Wave 0 BT Symbol Survey — UE 5.X — PASS / FAIL

(Automated check: every entry under `reachability` must be `true`.)

## Raw probe output

```json
{ ...JSON pasted here... }
```
```

## Fail-fast rule

If `reachability.BehaviorTreeFactory` is **false** on a shipped UE
version, mark that version `unsupported_on_this_ue_version` in the
tool init code and document in the file header. Plan 08-03 still
ships — the missing version simply returns a structured error per
S5 defensive coding.

If `reachability.NyraBTHelper` is **false** on every version, escalate
as a blocker — the C++ helper is not loading at all.

## Where to commit

| File | Path |
|------|------|
| 5.4 survey | `.planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/08-03-bt-symbols-5.4.md` |
| 5.5 survey | `.planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/08-03-bt-symbols-5.5.md` |
| 5.6 survey | `.planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/08-03-bt-symbols-5.6.md` |
| 5.7 survey | `.planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/08-03-bt-symbols-5.7.md` |

Commit message convention:
`docs(08-03): wave-0 BT symbol survey for UE 5.X — pass/fail`

## Done criteria

- [ ] Four `08-03-bt-symbols-{5.4,5.5,5.6,5.7}.md` files committed.
- [ ] Each file's header is a one-line PASS or FAIL.
- [ ] If any file is FAIL, the version branch in `bt_tools.py`
      explicitly returns `not_supported_on_this_ue_version` with the
      missing-symbol name in the message.
- [ ] `08-03-VERIFICATION.md` (live BT graph round-trip) only attempts
      versions that PASS this survey.
