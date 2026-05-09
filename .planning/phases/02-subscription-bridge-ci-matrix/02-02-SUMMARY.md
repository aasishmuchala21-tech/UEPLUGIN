# Plan 02-02 Summary: Wire Protocol Extension

**Phase:** 02-subscription-bridge-ci-matrix
**Plan:** 02-02
**Type:** execute
**Wave:** 0
**Executed:** 2026-04-30
**Autonomous:** true | **TDD:** false
**Depends on:** [] (Phase 2 Wave 0, first)

## Objectives

Lock the Phase 2 wire protocol contract: nine new JSON-RPC methods and eight
new error codes appended to Phase 1 specs. This plan is the source of truth
every downstream Phase 2 plan cites by reference.

## What Was Built

### `docs/JSONRPC.md` — Phase 2 §4 Additions

Nine new methods appended after Phase 1 §§1–3 (preserved verbatim per D-23):

| Subsection | Method | Direction | Kind | Locked by |
|------------|--------|-----------|------|-----------|
| §4.1 | `chat/send` backend extension | — | — | `backend` param now accepts `"claude"` |
| §4.2 | `session/set-mode` | UE→NH | request | D-05 Privacy Mode |
| §4.3 | `plan/preview` | NH→UE | notification | D-06 permission gate path B |
| §4.4 | `plan/decision` | UE→NH | request | D-09 approve/reject/edit verdict |
| §4.5 | `console/exec` | NH→UE | request | Plan 02-09 |
| §4.6 | `log/tail` | NH→UE | request | Plan 02-10 |
| §4.7 | `log/message-log-list` | NH→UE | request | Plan 02-12 |
| §4.8 | `diagnostics/backend-state` | NH→UE | notification | D-03 router state machine |
| §4.9 | `diagnostics/pie-state` | UE→NH | notification | PIE interlock (research open Q #5) |
| §4.10 | `claude/auth-status` | NH→UE | notification | First-run auth wizard |

Each method documented with:
- Direction + kind (request vs notification)
- Params schema (field name, type, required, description)
- Result shape (for requests) or frame shape (for notifications)
- Worked JSON example
- Error-code expectations (e.g., `plan/decision` → -32011 on reject)
- Cross-references to RESEARCH.md sections + CONTEXT.md D-XX

Section ends with a Change Log note: *"Phase 2 (D-23): additions only.
Phase 1 §§1–3 preserved verbatim."*

### `docs/ERROR_CODES.md` — Phase 2 Additions

Eight new error codes appended after Phase 1's -32001..-32006 (preserved verbatim):

| Code | Name | Owner plan | Remediation template |
|------|------|-----------|----------------------|
| -32007 | `claude_not_installed` | 02-04 | "Claude Code CLI not found. Install from code.claude.com." |
| -32008 | `claude_auth_drift` | 02-04 | "Claude session expired. Run `claude auth login` in a terminal." |
| -32009 | `claude_rate_limited` | 02-04 | "Claude rate-limited. Resume at {time}, or switch to local Gemma ([Switch])." |
| -32010 | `privacy_mode_egress_blocked` | 02-05 | "This action requires internet access. Exit Privacy Mode to continue." |
| -32011 | `plan_rejected` | 02-08 | "Plan rejected by user." |
| -32012 | `console_command_blocked` | 02-09 | "Console command '{cmd}' is not in the safe-mode whitelist." |
| -32013 | `transaction_already_active` | 02-07 | "Another NYRA session is already running. End it before starting a new one." |
| -32014 | `pie_active` | 02-07 | "NYRA cannot mutate while Play-In-Editor is running. Stop PIE and retry." |

Section includes:
- Clarification of -32003/-32009 relationship (Phase 1 generic rate-limit retained;
  Phase 2 Claude-specific cases use -32009 with `rate_limit_resets_at` timestamp)
- "Usage by Phase 2 plan" matrix attributing each code to its owning plan

## Deviations from Plan

None. Tasks 1 and 2 executed exactly as specified.

## Verification

```
grep -q "session/authenticate" docs/JSONRPC.md && \
grep -q "session/set-mode" docs/JSONRPC.md && \
grep -c "5\\.[4-7]" .github/workflows/plugin-matrix.yml  # (from 02-01)
→ Phase 1 markers present + Phase 2 additions present
```

## Next Steps

All downstream Phase 2 plans cite §§4.1–4.10 and -32007..-32014 as their
wire contract. No plan may deviate from these shapes without updating this
document first.

## Files Modified

| File | Change |
|------|--------|
| `docs/JSONRPC.md` | Appended §4 "Phase 2 Additions" (9 methods) |
| `docs/ERROR_CODES.md` | Appended Phase 2 section (8 codes + usage matrix) |

## Self-Check

- [x] Phase 1 §§1–3 preserved verbatim (grep-verified: `session/authenticate` present)
- [x] All 9 Phase 2 methods documented with schemas + JSON examples
- [x] All 8 Phase 2 error codes with remediation templates
- [x] -32003/-32009 relationship documented
- [x] Usage matrix maps each code to its owning plan
- [x] Change log note added to JSONRPC.md