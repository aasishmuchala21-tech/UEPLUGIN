---
phase: 3
slug: ue5-knowledge-rag
plan: 03-08
type: execute / checkpoint
wave: 3
autonomous: false
depends_on: [01, 02, 03, 04, 05, 06, 07]
blocking_preconditions: Phase 0 legal clearance must be confirmed (no new AI bill — this is RAG-only, but Phase 2 gates Phase 3; Phase 2 is precondition)
---

# Plan 03-08: Phase 3 Release Canary + KnowledgeBench

## Current Status

CHECKPOINT — Phase 3 ships a knowledge system, not a subscription driver. Precondition is Phase 2 completion (Phase 3 depends on Phase 2 per ROADMAP.md dependency graph), but Phase 3 itself has no new AI ToS surface.

## Objectives

End-of-phase release canary: prove every Phase 3 thread lands correctly, produce `03-VERIFICATION.md` as the phase-exit gate, and measure hallucination rate against the golden-set Q&A suite.

## What Will Be Built

### `Nyra.Dev.KnowledgeBench(N)` console command

```cpp
// Nyra.Dev.KnowledgeBench 50
// Runs N UE knowledge questions against the RAG pipeline.
// For each question:
//   - Retrieves chunks via nyra_retrieve_knowledge
//   - Validates symbols via nyra_validate_symbol
//   - Produces answer with citations
//   - Compares against golden-set expected answer (if available)
// Output:
//   [Q1] "How do I spawn an actor?" — retrieved 5 chunks, validated 2 symbols, answer: 312 chars
//   [Q1] hallucination_check: PASS (no unretrieved API cited)
//   ...
//   [SUMMARY] questions=50 hallucinated=1 hallucination_rate=2.0% p50_retrieval_ms=45 p95_retrieval_ms=112
//   [VERDICT] PASS (2.0% < 2% threshold — MARGINAL) / FAIL (>2%)
```

Pass criteria: `hallucination_rate < 2%` AND `p95_retrieval_ms < 500ms` AND `0` uncited-symbol errors.

### `tests/test_knowledge_e2e.py`

```python
import pytest

def test_retrieve_returns_version_tagged_chunks():
    """03-02: RAG retrieval returns chunks with version metadata."""
    from nyra_host.rag import retrieve_knowledge
    chunks = retrieve_knowledge("spawn actor with transform", ue_version_hint="5.6")
    assert all(c["ue_version"] in ["5.6", "5.5", "5.4"] for c in chunks)
    assert all("source_url" in c for c in chunks)

def test_symbol_validation_fails_unknown_api():
    """03-04: Symbol validation rejects fabricated API calls."""
    from nyra_host.symbols import validate_symbol
    result = validate_symbol("FMyFakeClass::DoMagic", "5.6")
    assert result["valid"] == False

def test_bootstrap_index_opens_on_empty_install():
    """03-01: Bootstrap index loads when no full index present."""
    # Simulate empty knowledge dir
    with patch("pathlib.Path.exists", return_value=False):
        from nyra_host.knowledge import load_index
        idx = load_index(ue_version="5.6")
        assert idx is not None  # Falls back to bootstrap

def test_gemma_offline_qa_uses_retrieved_chunks():
    """03-06: Gemma offline Q&A pipes retrieved chunks into prompt."""
    from nyra_host.offline import answer_with_gemma
    chunks = [{"content": "AActor::Spawn returns pointer to spawned actor"}]
    answer = answer_with_gemma(
        question="what does Spawn return?",
        retrieved_chunks=chunks,
        model_path="dummy.gguf"
    )
    assert "actor" in answer.lower()

def test_index_update_checks_github_releases():
    """03-05: Index update discovers and downloads newer index."""
    from nyra_host.knowledge import check_for_updates
    # Mock GitHub API response
    with requests_mock.mock() as m:
        m.get(GITHUB_RELEASES_URL, json=[{"tag_name": "v5.6.1", "assets": [...]}])
        update_info = check_for_updates(current_version="v5.6.0")
        assert update_info["available"] == True
        assert update_info["version"] == "v5.6.1"
```

### `03-VERIFICATION.md` (phase-exit gate)

```markdown
# Phase 3 — Verification

## Success Criteria

| SC | Claim | Verifier | Evidence | Status |
|----|-------|---------|----------|--------|
| SC#1 | Day-of UE release support via GitHub-Releases pipeline | Plan 03-07 | GitHub Actions run URL + Release asset | ⬜ / ✅ / ❌ |
| SC#2 | Hallucination rate <2% on golden-set Q&A suite | Plan 03-08 KnowledgeBench | KnowledgeBench pass verdict + hallucination_rate value | ⬜ / ✅ / ❌ |
| SC#3 | Symbol validation prevents unretrieved API calls | Plan 03-04 | Nyra.Symbol.Validation It blocks PASS | ⬜ / ✅ / ❌ |
| SC#4 | Bootstrap index loads on empty install | Plan 03-01 | test_bootstrap_index_opens_on_empty_install PASS | ⬜ / ✅ / ❌ |
| SC#5 | Gemma offline Q&A (KNOW-04) | Plan 03-06 | test_gemma_offline_qa_uses_retrieved_chunks PASS + manual offline test | ⬜ / ✅ / ❌ |
| SC#6 | Two-tier index (<200 MB total) | Plan 03-01 + 03-05 | Bootstrap .lance size + full index download size measured | ⬜ / ✅ / ❌ |

## Requirement Coverage

| REQ | Plan(s) | Verified |
|-----|---------|----------|
| KNOW-01 | 03-07 | ⬜ / ✅ / ❌ |
| KNOW-02 | 03-02, 03-03, 03-04 | ⬜ / ✅ / ❌ |
| KNOW-03 | 03-06 | ⬜ / ✅ / ❌ |
| KNOW-04 | 03-06 | ⬜ / ✅ / ❌ |

## KnowledgeBench Run

- **Command:** `Nyra.Dev.KnowledgeBench 50`
- **Verdict:** ⬜ / ✅ PASS / ❌ FAIL
- **Hallucination rate:** `<value>%`
- **p50 retrieval ms:** `<value>ms`
- **p95 retrieval ms:** `<value>ms`
- **Symbol errors:** `<count>`
- **Log file:** `<path>`

## CI/CD

- **GitHub Actions run URL:** `<url>`
- **Bootstrap index artifact:** `<path or N/A>`
- **Release asset:** `<NyraIndex_*.lance URL>`
```

## Phase 3 Exit Gate

Phase 3 is **COMPLETE** when:
- `03-VERIFICATION.md` frontmatter `status: pass`
- All 4 REQ rows ✅
- KnowledgeBench run: `hallucination_rate < 2%` AND `p95_retrieval_ms < 500`
- GitHub Release asset exists for at least UE 5.6

## Files Created by This Plan

| File | Purpose |
|------|---------|
| `NyraEditor/Source/NyraEditor/Public/NyraDevTools.h` | Declares `KnowledgeBench` console command |
| `NyraEditor/Source/NyraEditor/Private/NyraDevTools.cpp` | Implements `KnowledgeBench` command |
| `tests/test_knowledge_e2e.py` | End-to-end knowledge system tests |
| `03-VERIFICATION.md` | Phase-exit gate (operator fills) |

## Module-Superset Discipline

Phase 1 `Nyra.Dev.RoundTripBench` and Phase 2 `Nyra.Dev.SubscriptionBridgeCanary` are preserved verbatim. This plan adds `KnowledgeBench` to `FNyraDevTools.cpp`. No modifications to prior-phase commands.

## Operator Actions (Task 2 — human checkpoint)

1. Run CI pipeline: push Phase 3 branch, wait for `build-knowledge-index.yml` green
2. Run `Nyra.Dev.KnowledgeBench 50` in UE editor with real UE 5.6 installation
3. Capture results: hallucination rate, retrieval latency, symbol error count
4. Populate `03-VERIFICATION.md` with evidence
5. Set `status: pass` if all SC rows are ✅

## Resume Signal

- `phase-3-verified-pass` + populated `03-VERIFICATION.md`
- OR `phase-3-partial: SC#X marginal; proposed waiver: ...`
- OR `phase-3-fail: SC#Y blocker; remediation plan needed`