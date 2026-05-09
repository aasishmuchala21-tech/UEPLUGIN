# Plan 03-08 Summary: Phase 3 Release Canary + KnowledgeBench

**Phase:** 03-ue5-knowledge-rag
**Plan:** 03-08
**Type:** execute / checkpoint
**Wave:** 3
**Autonomous:** false
**Depends on:** [01, 02, 03, 04, 05, 06, 07]
**Blocking preconditions:** Phase 0 legal clearance must be confirmed

## Objectives

End-of-phase release canary: prove every Phase 3 thread lands correctly, produce `03-VERIFICATION.md` as the phase-exit gate, and measure hallucination rate against the golden-set Q&A suite.

## What Was Built

### `Nyra.Dev.KnowledgeBench(N)` Console Command

```cpp
// Nyra.Dev.KnowledgeBench 50
// Runs N UE knowledge questions against the RAG pipeline.
// Output format:
//   [Q1] "How do I spawn an actor?" — retrieved 5 chunks, validated 2 symbols, answer: 312 chars
//   [Q1] hallucination_check: PASS (no unretrieved API cited)
//   ...
//   [SUMMARY] questions=50 hallucinated=1 hallucination_rate=2.0% p50_retrieval_ms=45 p95_retrieval_ms=112
//   [VERDICT] PASS (2.0% < 2% threshold) / FAIL (>2%)
```

Pass criteria:
- `hallucination_rate < 2%` — no unretrieved API cited in any answer
- `p95_retrieval_ms < 500ms` — RAG retrieval latency within SLA
- `0` uncited-symbol errors — SymbolGate blocked or warned correctly

### End-to-End Tests: `tests/test_knowledge_e2e.py`

- `test_retrieve_returns_version_tagged_chunks` (03-02)
- `test_symbol_validation_fails_unknown_api` (03-04)
- `test_bootstrap_index_opens_on_empty_install` (03-01)
- `test_gemma_offline_qa_uses_retrieved_chunks` (03-06)
- `test_index_update_checks_github_releases` (03-05)

### Phase-Exit Gate: `03-VERIFICATION.md`

Status table tracking 6 success criteria:

| SC | Claim | Verifier | Status |
|----|-------|---------|--------|
| SC#1 | Day-of UE release support via GitHub-Releases pipeline | Plan 03-07 | ⬜ / ✅ / ❌ |
| SC#2 | Hallucination rate <2% on golden-set Q&A suite | KnowledgeBench | ⬜ / ✅ / ❌ |
| SC#3 | Symbol validation prevents unretrieved API calls | Plan 03-04 | ⬜ / ✅ / ❌ |
| SC#4 | Bootstrap index loads on empty install | Plan 03-01 | ⬜ / ✅ / ❌ |
| SC#5 | Gemma offline Q&A (KNOW-04) | Plan 03-06 | ⬜ / ✅ / ❌ |
| SC#6 | Two-tier index (<200 MB total) | Plans 03-01 + 03-05 | ⬜ / ✅ / ❌ |

Phase 3 is **COMPLETE** when: `status: pass`, all REQ rows ✅, KnowledgeBench verdict PASS, GitHub Release asset exists for at least UE 5.6.

## Files Created

| File | Purpose |
|------|---------|
| `NyraEditor/Source/NyraEditor/Public/NyraDevTools.h` | Declares `KnowledgeBench` console command |
| `NyraEditor/Source/NyraEditor/Private/NyraDevTools.cpp` | Implements `KnowledgeBench` command |
| `tests/test_knowledge_e2e.py` | End-to-end knowledge system tests |
| `03-VERIFICATION.md` | Phase-exit gate (operator fills) |

## Module-Superset Discipline

Phase 1 `Nyra.Dev.RoundTripBench` and Phase 2 `Nyra.Dev.SubscriptionBridgeCanary` preserved verbatim. `KnowledgeBench` added to `FNyraDevTools.cpp`. No modifications to prior-phase commands.

## Operator Actions (Human Checkpoint)

1. Run CI pipeline — push Phase 3 branch, wait for `build-knowledge-index.yml` green
2. Run `Nyra.Dev.KnowledgeBench 50` in UE editor with real UE 5.6 installation
3. Capture results: hallucination rate, retrieval latency, symbol error count
4. Populate `03-VERIFICATION.md` with evidence
5. Set `status: pass` if all SC rows are ✅

## Resume Signal

- `phase-3-verified-pass` + populated `03-VERIFICATION.md`
- OR `phase-3-partial: SC#X marginal; proposed waiver: ...`
- OR `phase-3-fail: SC#Y blocker; remediation plan needed`

## Next Steps

- Phase 3 complete → advance to Phase 4 (Blueprint Tool Catalog)
- Phase 4 CONTEXT.md discusses D-7 through D-12 grey areas