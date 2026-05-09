# Plan 02-14 Summary: Phase 2 Release Canary

**Phase:** 02-subscription-bridge-ci-matrix
**Plan:** 02-14
**Type:** execute / checkpoint
**Wave:** 3
**Autonomous:** false | **TDD:** false
**Depends on:** [01, 05, 06, 08, 09, 10, 11, 12]
**phase0_clearance_required:** true
**Blocking preconditions:** Phase 0 legal clearance on file, Phase 1 SC#3
bench pass verdict committed, all 02-01 through 02-13 SUMMARYs on disk

## Objectives

End-of-phase release canary: prove every Phase 2 thread lands correctly and
produce `02-VERIFICATION.md` as the phase-exit gate. All six ROADMAP Phase 2
Success Criteria evaluated PASS/FAIL with concrete evidence.

## Current Status: CHECKPOINT — awaiting Phase 0 clearance + Phase 1 bench verdict

### Hard Preconditions (all must be true before Task 1 executes)

1. **Phase 0 legal clearance:** `NYRA_PHASE0_CLEARANCE=confirmed` in the
   execution environment. Written Anthropic ToS clarification on file (Plan 00-01
   verdict ∈ {PERMITTED, CONDITIONAL}).
2. **Phase 1 SC#3 empirical bench:** `Nyra.Dev.RoundTripBench 100` pass verdict
   committed. `ring0-bench-results.md` frontmatter `pending_manual_verification: false`.
3. **Plan 02-04 EV cert:** `ev-cert-in-akv-and-secrets-populated` resume signal
   (or documented `ev-cert-stalled` deferral).
4. **All 02-01 through 02-13 SUMMARYs on disk.**

## What Will Be Built (Task 1 — auto, after preconditions clear)

### `FNyraDevTools::RunSubscriptionBridgeCanary(N, Prompt)`

Module-superset on Phase 1 Plan 14. Phase 1 `Nyra.Dev.RoundTripBench` preserved
verbatim. Phase 2 adds:

```cpp
// Nyra.Dev.SubscriptionBridgeCanary N [prompt]
// Default N=10, prompt="Reply with the single word OK only."
// Output:
//   [PER TURN] turn 1: first_token=1234ms total=3456ms tool_calls=0 errors=0 backend_state=ready
//   ...
//   [SUMMARY] turns=10 p50_total=3100ms p95_total=5200ms errors=0 plan_previews=0 state_transitions=11
//   [VERDICT] PASS / FAIL (reason if FAIL)
// Results file: Saved/NYRA/canary-subscription-bridge-<ISO-ts>.log
```

- Uses `backend=claude` (not gemma-local)
- Per-turn metrics: first_token_ms, total_ms, tool_calls_count, errors_count,
  backend_state_observed (from `diagnostics/backend-state` notifications)
- Pass verdict: all turns done=true with no error AND `diagnostics/backend-state`
  observed AND (if any turn induced `tool_use`) `plan/preview` + `plan/decision`
  round-trip observed
- Clamp N to [1, 50] (lower cap than Phase 1 bench; each Claude turn consumes
  real subscription quota)
- Consent modal on first run per session: "This will use ~N turns of your
  Claude subscription. Continue? [Y/N]"

### `Nyra.Dev.SubscriptionBridgeCanary` console command

Registered as `FAutoConsoleCommand` with default N=10. Clamps to [1, 50].

### `tests/test_claude_live_turn.py`

```python
pytestmark = pytest.mark.skipif(
    not os.getenv('CLAUDE_CODE_OAUTH_TOKEN'),
    reason='requires CLAUDE_CODE_OAUTH_TOKEN env'
)
pytestmark = pytest.mark.skipif(
    os.getenv('NYRA_PHASE0_CLEARANCE') != 'confirmed',
    reason='Phase 0 legal clearance precondition'
)
```

Two tests:
- `test_live_turn_emits_done` — spawns `ClaudeBackend` with real CLI; sends
  "Reply with OK only"; asserts `Done` event observed
- `test_live_turn_captures_ndjson_fixture` — captures raw stdout as NDJSON,
  writes to `tests/fixtures/stream-json-cli-v<VERSION>.ndjson` for schema-drift
  regression baseline

### `02-VERIFICATION.md` (empty template — Task 2 fills)

Phase-exit verification doc. Template authored now (Task 1); operator pastes
evidence after live canary run (Task 2).

## Task 2 (checkpoint:human-action): Founder runs live canary + authors VERIFICATION.md

### Procedure

1. **CI matrix:** Push Phase 2 branch. Wait for `plugin-matrix.yml` green on
   all four UE cells. Capture GitHub Actions run URL.
2. **Live canary:** Open UE editor, sign into Claude, open console, run:
   ```
   Nyra.Dev.SubscriptionBridgeCanary 10 "Reply with the single word OK only."
   ```
   Expect `VERDICT: PASS`. Capture `Saved/NYRA/canary-subscription-bridge-<ts>.log`.
3. **Manual sanity checks:**
   - Observe Claude pill turn Green during streaming
   - Prompt inducing `tool_use` (e.g. "Spawn a point light at origin");
     verify `SNyraPreviewCard` appears with correct plan summary
   - Click Reject on preview card; verify `-32011 plan_rejected`
   - After a tool-use turn, press Ctrl+Z; verify mutation undone (or UTransBuffer
     undo count incremented by 1)
   - Toggle Privacy Mode; verify Gemma backend answers; toggle off; verify Claude
     accepted again
4. **Live pytest:** `CLAUDE_CODE_OAUTH_TOKEN=<token> NYRA_PHASE0_CLEARANCE=confirmed
   python -m pytest tests/test_claude_live_turn.py -v -m live`
5. **Populate `02-VERIFICATION.md`:** Fill all PENDING cells with evidence;
   set `status: pass` if every SC is ✅; `partial` if at least one is ❌ with
   documented cut-line waiver; `fail` otherwise.

### Resume signal

- `phase-2-verified-pass` + populated `02-VERIFICATION.md` contents + GitHub
  Actions run URL + canary log path
- OR `phase-2-partial: SC#X failed; proposed waiver: ...`
- OR `phase-2-fail: SC#Y blocker; remediation plan needed`

## Phase 2 Exit Gate

Phase 2 is **COMPLETE** when:
- `02-VERIFICATION.md` frontmatter `status: pass`
- All six SC rows ✅
- All nine REQ-ID rows traceable to owning plan + verification test
- Schema-drift regression fixture committed

## Files Created (planned)

| File | Purpose |
|------|---------|
| `FNyraDevTools.cpp` | Adds `RunSubscriptionBridgeCanary` + console command |
| `FNyraDevTools.h` | Public declaration |
| `test_claude_live_turn.py` | Live-guarded pytest for Claude CLI driver |
| `stream-json-cli-v<VER>.ndjson` | Wave 0 NDJSON fixture for schema-drift regression |
| `02-VERIFICATION.md` | Phase-exit verification gate (operator fills) |

## Module-Superset Discipline

Phase 1 `Nyra.Dev.RoundTripBench` preserved verbatim in `FNyraDevTools.cpp`.
Phase 2 adds parallel method only. No changes to Phase 1 bench infrastructure.
