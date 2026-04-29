# Phase 02 Plan 06: Router State Machine Summary

**Plan:** 02-06
**Phase:** 02-subscription-bridge-ci-matrix
**Subsystem:** nyrahost.router
**Wave:** 1
**Dependencies:** 02, 03, 05
**Phase 0 Clearance:** REQUIRED (Claude-path live after SC#1 clears)
**GSD Plan:** .planning/phases/02-subscription-bridge-ci-matrix/02-06-router-state-machine-PLAN.md

## One-Liner
Router state machine with Privacy Mode toggle and explicit fallback approval — Claude stubbed until Phase 0 SC#1 verdict permits.

## What Was Built

### Python: NyraRouter (nyrahost/router.py)

**BackendState enum** (7 states, lowercase wire-compatible):
```
IDLE → BACKEND_AIMING → CLAUDE_ACTIVE / GEMMA_ACTIVE
CLAUDE_ACTIVE → RATE_LIMITED → (user_approved_fallback) → GEMMA_ACTIVE
CLAUDE_ACTIVE → AUTH_DRIFT → (user_approved_fallback) → GEMMA_ACTIVE
CLAUDE_ACTIVE → (server_error attempt≥3) → stays + error surfaces
* → PRIVACY_MODE (orthogonal entry)
PRIVACY_MODE → prior_state (on exit)
```

**decide_backend() routing rules:**
1. Privacy mode → always gemma-local (cannot bypass)
2. SC#1 not cleared → stub to gemma-local
3. Rate-limited without user_approved_fallback → error(-32009)
4. Auth drift without user_approved_fallback → error(-32008)
5. Otherwise → claude (live when SC#1 clears)

**observe_event()** processes BackendEvent dicts: Retry, Error, Done.
Rate-limit: exhausted at attempt≥3 → RATE_LIMITED state.
Server-error: attempt≥3 → error surfaces but state stays (RESEARCH §10.6).
Auth-failed: immediate transition to AUTH_DRIFT.

**Privacy Mode**: enter_privacy_mode() / exit_privacy_mode() with prior_state pop-back.
set_mode('gemma'|'claude'|'auto') with ValueError on invalid mode.

**diagnostics/backend-state** emitted on every transition via injected emit_notification.

### Python: SessionModeHandler (nyrahost/handlers/session_mode.py)
Handles session/set-mode WS request. Calls router.enter_privacy_mode() / exit_privacy_mode().
Returns {mode_applied: True, mode: str}.

### Tests: test_router.py (18 test cases)
- Initial state (idle, privacy_mode=False, safe_mode=ON, claude_available=False)
- decide_backend routing (gemma stub, privacy mode, rate-limit error, fallback approval, auth drift error)
- State transitions (idle→aiming, ClaudeActive→Done→IDLE, invalid transition logged)
- Privacy Mode (enter stores prior, exit restores, set_mode invalid raises ValueError)
- Retry handling (rate_limit exhaustion at 3, auth_failed immediate, server_error attempt 1 stays, attempt 3 surfaces but stays)
- Diagnostics (diagnostics/backend-state emitted on transition, get_diagnostics() returns full state dict)
- BackendDecision dataclass correctness

## Key Decisions

1. **SC#1 gate**: `claude_available=False` stub in __init__ — Claude path activates when SC#1 verdict permits. No silent fallback mid-stream (D-04).

2. **State machine as explicit dict**: `_TRANSITIONS` table maps (current_state, event) → next_state. Unknown transitions logged and skipped (not exceptions).

3. **emit_notification injected at construction**: Allows async notification dispatch without circular deps.

4. **BackendDecision dataclass over tuple**: type-safe, self-documenting; error_code/error_message/error_remediation fields for all error paths.

## Deviation from Plan

- **No changes to handlers/chat.py** for Phase 2 Wave 1 — module-superset discipline preserved; chat.py routing upgrade (replacing direct BACKEND_REGISTRY with router.decide_backend) is a Phase 2 Wave 2 task deferred to Plans 02-08/09 activation.
- **No direct GEvent stream integration** in Wave 1 — BackendEvent dicts processed via observe_event(); GEvent binding deferred to Phase 2 Wave 2 backend integration.

## Artifacts Created

| File | Provides |
|------|----------|
| TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/router.py | NyraRouter + BackendState enum + BackendDecision dataclass |
| TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/session_mode.py | SessionModeHandler + session/set-mode WS handler |
| TestProject/Plugins/NYRA/Source/NyraHost/tests/test_router.py | 18 test cases across 6 test classes |
| TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/FNyraChatRouter.h/.cpp | C++ stub for UE-side router integration (transaction + PIE) |

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| T-02-06-01 | router.py | user_approved_fallback bypass — mitigated: ephemeral per call, UE CHAT-02 pill sets only on explicit click |
| T-02-06-02 | session_mode.py | session/set-mode spoofed in Privacy Mode — mitigated: first-frame auth blocks unauthenticated WS clients |
| T-02-06-03 | router.py | server_error retry storm — mitigated: attempt<3 silent cap; state stays, error surfaces (RESEARCH §10.6) |

## Known Stubs

- `_emit_for_phase2` in app.py is a no-op lambda — Phase 2 Wave 2 must wire real `server.send_notification()` dispatch
- ChatHandlers in app.py still uses direct BACKEND_REGISTRY path — Phase 2 Wave 2 completes the routing integration
- C++ FNyraChatRouter is a stub — Phase 2 Wave 2 must wire PIE delegate registration and diagnostics/pie-state emit

## Metrics

- Duration: Wave 1 batch
- Tasks: 2 (Task 1 router state machine + Task 2 session_mode handler)
- Files: 4 Python source, 1 Python test, 2 C++ files
- Tests: 18 passing across 6 test classes

## TDD Gate Compliance

RED (test) commit: `test(02-06): add failing router state-machine tests` — EXISTS
GREEN (impl) commit: `feat(02-06): router state machine + Privacy Mode toggle` — EXISTS

## Self-Check

- [x] test_router.py exists and covers 18 cases
- [x] NyraRouter class with BackendState enum + decision routing
- [x] SessionModeHandler wired in app.py register()
- [x] diagnostics/backend-state emitted on transitions
- [x] Phase 0 SC#1 gate: claude_available=False in production
- [x] privacy mode stores prior state, exit restores it
- [x] server_error attempt≥3 surfaces error but state stays (RESEARCH §10.6)

## Self-Check: PASSED