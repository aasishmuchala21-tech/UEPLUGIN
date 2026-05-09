---
phase: 2
slug: subscription-bridge-ci-matrix
status: draft
ci_matrix_run: "<github-actions-run-url — operator fills after first green matrix run>"
canary_run: "Saved/NYRA/canary-subscription-bridge-<ts>.log — operator fills after live canary>"
phase0_clearance: pending
phase1_sc3_bench_commit: "<sha or n/a if not yet committed>"
pending_manual_verification: true
---

# Phase 2 — Verification

## Success Criteria

| SC | Claim | Verifier | Evidence | Status |
|----|-------|---------|----------|--------|
| SC#1 | Claude Code CLI subscription driving verified end-to-end | Plan 02-05 + live canary | canary log path; test_claude_live_turn.py PASS | ⬜ pending / ✅ pass / ❌ fail |
| SC#2 | Graceful fallback + Privacy Mode | Plan 02-06 + NyraStatusPillSpec | Nyra.Panel.StatusPill.PrivacyMode It block PASS + manual Privacy Mode toggle roundtrip | ⬜ / ✅ / ❌ |
| SC#3 | Plan-first-by-default (CHAT-04) | Plan 02-09 permission gate | Nyra.Preview.ApproveFlow + RejectFlow It blocks PASS + live canary plan/preview observed | ⬜ / ✅ / ❌ |
| SC#4 | FScopedTransaction + Ctrl+Z rollback | Plan 02-08 NyraTransactionsSpec | Nyra.Transactions.* It blocks PASS + manual Ctrl+Z after canary | ⬜ / ✅ / ❌ |
| SC#5 | Four-version CI matrix green + compat shim populated | Plans 02-01 + 02-07 + 02-13 | github-actions-run-url with all four cells green, EV-signed; compat-matrix-first-run.md committed | ⬜ / ✅ / ❌ |
| SC#6 | EV code-signing + router multi-backend + console/log tools | Plans 02-13 + 02-06 + 02-10 + 02-11 | signtool verify output committed; test_backend_interface passed; Nyra.Console.* + Nyra.Logging.* PASS | ⬜ / ✅ / ❌ |

## Requirement Coverage

| REQ | Plan(s) | Verified |
|-----|---------|---------|
| PLUG-04 | 02-01, 02-07, 02-13 | ⬜ pending / ✅ pass / ❌ fail |
| SUBS-01 | 02-05 | ⬜ pending / ✅ pass / ❌ fail |
| SUBS-02 | 02-06 | ⬜ pending / ✅ pass / ❌ fail |
| SUBS-03 | 02-03, 02-06 | ⬜ pending / ✅ pass / ❌ fail |
| CHAT-02 | 02-12 | ⬜ pending / ✅ pass / ❌ fail |
| CHAT-03 | 02-08 | ⬜ pending / ✅ pass / ❌ fail |
| CHAT-04 | 02-09 | ⬜ pending / ✅ pass / ❌ fail |
| ACT-06 | 02-10 | ⬜ pending / ✅ pass / ❌ fail |
| ACT-07 | 02-11 | ⬜ pending / ✅ pass / ❌ fail |

## CI Matrix Run

- **Run URL:** `<operator fills after first green matrix run>`
- **Triggered by:** `<branch or PR that caused the run>`
- **Matrix versions:** 5.4 / 5.5 / 5.6 / 5.7 (or documented deferral)
- **All four cells green:** ⬜ pending / ✅ yes / ❌ no
- **Artifacts uploaded:** ⬜ pending / ✅ yes / ❌ no
- **EV-signed:** ⬜ pending / ✅ yes / ❌ no

## Live Canary Run

- **Timestamp:** `<ISO timestamp of canary run>`
- **Command:** `Nyra.Dev.SubscriptionBridgeCanary 10 "Reply with the single word OK only."`
- **Verdict:** ⬜ pending / ✅ PASS / ❌ FAIL
- **p50 total ms:** `<value>`
- **p95 total ms:** `<value>`
- **Errors:** `<count>`
- **plan/preview observed:** ⬜ pending / ✅ yes / ❌ no
- **diagnostics/backend-state observed:** ⬜ pending / ✅ yes / ❌ no
- **Log file:** `<Saved/NYRA/canary-subscription-bridge-<ts>.log path>`

## Manual Verification Log

_Operator fills after live canary run:_

- `<ts>`: canary run N=10, all turns PASS, no Claude-side errors
- `<ts>`: Privacy Mode toggle — pill turned purple, subsequent chat/send refused Claude, GemmaBackend answered
- `<ts>`: Ctrl+Z after a canned-tool-call canary turn — full session rolled back, UTransBuffer visible entry disappeared

## Known Wave 0 Gaps

_Operator fills after live canary run:_

- `<gap 1 if any>`
- `<gap 2 if any>`

---

_Phase 2 is COMPLETE when all six SC rows are ✅ and all nine REQ rows are ✅._
