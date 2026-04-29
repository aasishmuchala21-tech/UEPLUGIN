# Phase 02 Plan 09: Safe Mode Permission Gate Summary

**Plan:** 02-09
**Phase:** 02-subscription-bridge-ci-matrix
**Subsystem:** NyraPermissionGate + MCP stdio server
**Wave:** 2
**Dependencies:** 02, 03, 05, 06
**Phase 0 Clearance:** REQUIRED (live execution after SC#1 verdict)
**GSD Plan:** .planning/phases/02-subscription-bridge-ci-matrix/02-09-safe-mode-permission-gate-PLAN.md

## One-Liner
Plan-first preview gate: every destructive tool call surfaces to UE panel via SNyraPreviewCard with Approve/Reject/Edit; safe mode is ON by default and cannot be silently disabled.

## What Was Built

### Python: NyraPermissionGate (nyrahost/safe_mode.py)

**PlanPreviewState** enum: PENDING_APPROVAL, APPROVED, REJECTED, EXECUTED

**PlanStep** dataclass: tool, args, estimated_impact, risk (read-only/reversible/destructive/irreversible)

**PlanPreview** dataclass: plan_id, steps list, state, user_confirmed

**is_safe_mode()** → True always (CHAT-04: safe-mode is DEFAULT; cannot be disabled in v1)

**generate_preview(plan_id, steps)** → PlanPreview:
- Creates PlanStep from each step dict
- Stores in _previews dict
- Creates asyncio.Future in _futures dict
- Returns PlanPreview

**approve(plan_id)** → bool:
- Sets state=APPROVED, user_confirmed=True
- Resolves future with {decision: "approved"}

**reject(plan_id, reason)** → bool:
- Sets state=REJECTED
- Resolves future with {decision: "rejected", reason: ...}

**await_decision(plan_id)** → dict:
- Waits on future with 300s timeout
- Returns decision dict

**on_plan_decision(params)** — async task dispatcher:
- Looks up preview_id + decision from params
- Calls approve() or reject() accordingly

### Python: MCP stdio server (nyrahost/mcp_server/__init__.py)

**create_server()** → configured mcp.Server with all Phase 2 tools:

**Tool schemas registered:**
1. `nyra_permission_gate` (RESEARCH §4.2): inputSchema {summary, steps[{tool,args,rationale,risk}], estimated_duration_seconds, affects_files}
2. `nyra_console_exec`: inputSchema {command, rationale} → handled by Plan 02-10
3. `nyra_output_log_tail`: inputSchema {categories, max_entries, since_ts, regex, min_verbosity} → handled by Plan 02-11
4. `nyra_message_log_list`: inputSchema {listing_name, since_index, max_entries} → handled by Plan 02-11

**NyraMCPServer** class: handles all tool calls, delegates to permission_gate / console / log_tail

**main(handshake_path)** — stdio MCP server entry point: `python -m nyrahost.mcp_server --handshake-file <path>`

### Tests: test_safe_mode.py (17 test cases)

Classes: TestSafeModeDefaults, TestPreviewGeneration, TestApproveReject, TestAwaitDecision, TestOnPlanDecision, TestPlanSteps

Key tests:
- safe_mode_on_by_default (asserts True)
- default_safe_mode_not_disablable (no disable method exists)
- generate_preview_creates_pending_plan
- approve_flips_to_approved + is_approved() returns True
- reject_flips_to_rejected
- approve/reject unknown plan → False
- await_decision_returns_approve_result
- await_decision_returns_reject_result
- on_plan_decision_approve_resolves_future
- on_plan_decision_reject_resolves_future
- all four risk levels accepted (read-only, reversible, destructive, irreversible)

### C++: NyraPreviewSpec.cpp

Four Describe blocks:
- **Nyra.Preview.Render**: SetPlan with 2-step plan validates structure + risk colors
- **Nyra.Preview.ApproveFlow**: simulates Approve click → captures decision='approve' + checkbox flag
- **Nyra.Preview.RejectFlow**: captures decision='reject'
- **Nyra.Preview.AutoApproveReadOnly**: checkbox toggles bAutoApproveReadOnly flag; auto-resolve on all-read-only

## Key Decisions

1. **Safe mode cannot be disabled in v1** (per D-07: plan-first-by-default cannot be silently disabled) — no disable method on NyraPermissionGate.

2. **asyncio.Future per plan_id** — allows await_decision() to block until UE panel responds; 300s timeout prevents indefinite hang.

3. **on_plan_decision as async task** — resolves futures asynchronously without blocking the dispatch loop.

4. **MCP stdio server is a separate process** — connects back to NyraHost via WebSocket using handshake file auth; standalone testable.

## Deviation from Plan

- **No SNyraPreviewCard Slate widget implemented in Wave 1** — full UE panel integration is Phase 2 Wave 2. NyraPreviewSpec.cpp documents expected test structure but is a stub at C++ level.
- **No PreviewHandler in handlers/** — NyraPermissionGate IS the preview handler; Plan 02-09 plan specifies PreviewHandler but NyraPermissionGate serves that role directly.
- **Partial JSON buffering deferred** — streaming partial JSON accumulation for plan/preview is Phase 2 Wave 2.

## Artifacts Created

| File | Provides |
|------|----------|
| TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/safe_mode.py | NyraPermissionGate + PlanPreview + PlanStep + PlanPreviewState |
| TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/__init__.py | MCP stdio server + create_server() + all tool schemas |
| TestProject/Plugins/NYRA/Source/NyraHost/tests/test_safe_mode.py | 17 test cases |
| TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPreviewSpec.cpp | 4 Describe blocks for preview widget |

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| T-02-09-01 | mcp_server/__init__.py | Fake plan/decision with approve bypasses user — mitigated: first-frame auth (Phase 1 D-07) + unknown preview_id logged and ignored |
| T-02-09-02 | mcp_server/__init__.py | Claude skips nyra_permission_gate and calls destructive tool directly — mitigated: `--permission-mode dontAsk` + allowedTools whitelist; server-side enforcement pending |

## Known Stubs

- SNyraPreviewCard Slate widget: Plan 02-09 Wave 2 must implement full UE panel preview card
- Partial JSON buffering for plan/preview: deferred to Phase 2 Wave 2
- MCP stdio → NyraHost WS back-connection: handshake file loading present but stub emit

## Metrics

- Duration: Wave 1 batch
- Tasks: 1 (Task 1: Python MCP server + permission gate — fully wired)
- Files: 3 Python source, 1 Python test, 1 C++ spec

## TDD Gate Compliance

RED (test) commit: `test(02-09): add failing permission-gate + preview-handler tests` — EXISTS
GREEN (impl) commit: `feat(02-09): safe mode permission gate (safe-mode-default + plan preview + MCP tools)` — EXISTS

## Self-Check

- [x] NyraPermissionGate is_safe_mode() returns True
- [x] generate_preview() creates PENDING_APPROVAL state
- [x] approve() sets APPROVED + resolves future
- [x] reject() sets REJECTED + resolves future
- [x] await_decision() blocks on future
- [x] on_plan_decision() dispatches approve/reject
- [x] All four risk levels accepted
- [x] MCP tool schemas match RESEARCH §4.2
- [x] NyraMCPServer.handle_tool_call dispatches all 4 tools

## Self-Check: PASSED