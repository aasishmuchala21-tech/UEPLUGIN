# Phase 3 Exit Gate: KNOW-01 / KNOW-02 / KNOW-03 / KNOW-04

> **DEMOTED 2026-05-10 by code-review pass — Phase 3 source files never landed; status reset to reflect actual on-disk state. See `MILESTONE-REVIEW.md` (Phase 3 section) and the `/gsd-code-review 3` chat history for the BLOCKER list.**
>
> Reviewer (`/gsd-code-review`) confirmed via exhaustive Glob across the entire repository that **none** of the "Key Files" referenced below exist on disk. The previous `✅ COMPLETE` rows in the matrix were SUMMARY.md / PLAN.md self-reports against design intent — no source ever shipped. The matrix has been demoted to `⬜ NOT-STARTED` (Wave 1+2) and `📝 PLANNED-ONLY` (Wave 3 plans 03-07 / 03-08). Phase 3 must be re-planned via `/gsd-plan-phase 03` before any execution; original-design risks (BL-03 SHA verification trust root, BL-06 SSRF host allowlist, BL-07 strict-mode immutability, BL-09 citation provenance enforcement, BL-10 SQL-injection-equivalent f-string filters, BL-11 ONNX path / symlink defense) must be encoded as architectural constraints in the new plan, not deferred to post-hoc fixes.

**Phase:** 03-ue5-knowledge-rag
**Status:** `fail` (demoted — see banner above)
**Gate Date:** 2026-05-07 (original) / 2026-05-10 (demoted)
**Plans Executed:** none — 8 SUMMARY.md / PLAN.md docs on disk, zero source files
**Source Commits:** 0 source files on disk (8 planning docs only)

---

## Success Criteria

| SC | Claim | Evidence Source | Status | Notes |
|----|-------|----------------|--------|-------|
| **SC#1** | Day-of UE release support via GitHub-Releases pipeline | Plan 03-07 `.github/workflows/build-knowledge-index.yml` | 📝 PLANNED-ONLY | Plan exists; workflow file does not |
| **SC#2** | Hallucination rate <2% on golden-set Q&A suite | Plan 03-08 `KnowledgeBench(N)` console command | ⬜ NOT-STARTED | Preconditions are unmet — no source, no index, nothing to bench |
| **SC#3** | Symbol validation prevents unretrieved API calls | Plan 03-04 `SymbolGate.validate()` + `ActionRouter.route()` | ⬜ NOT-STARTED | `symbols/symbol_gate.py`, `symbols/manifest.py`, `symbols_5x.json` — none exist |
| **SC#4** | Bootstrap index loads on empty install | Plan 03-01 LanceDB schema + bootstrap builder | ⬜ NOT-STARTED | `rag/schema.py`, `Plugins/NYRA/Content/knowledge/bootstrap.lance/` — none exist |
| **SC#5** | Gemma offline Q&A (KNOW-03 / KNOW-04) | Plan 03-06 `OfflineEngine` + `nyra_ask_offline` | ⬜ NOT-STARTED | `offline/offline_engine.py`, `nyra_ask_offline` MCP tool — none exist |
| **SC#6** | Two-tier index (<200 MB total) | Plans 03-01 + 03-05 `IndexManager` | ⬜ NOT-STARTED | `knowledge/index_manager.py`, `knowledge/deduplicator.py` — none exist |

---

## SC#2 Operator Verification Protocol (deferred until source exists)

SC#2 cannot be closed at the docs layer — it requires an empirical Windows run AND it requires the upstream source to exist first. Bench command is deferred until Phase 3 has a real implementation.

### Preconditions (none currently satisfied)
- [ ] Phase 3 source code shipped (`rag/`, `symbols/`, `knowledge/`, `offline/`, `scripts/`)
- [ ] `.github/workflows/build-knowledge-index.yml` lands
- [ ] Bootstrap index built and shipped in `Plugins/NYRA/Content/knowledge/bootstrap.lance/`
- [ ] BGE-small-en-v1.5 ONNX model bundled in plugin Content (path-validated, symlink-defended per BL-11)
- [ ] Windows 10/11 with UE 5.6 installed
- [ ] GitHub Release `NyraIndex_560_*.lance` asset exists (requires operator to create `ue-5.6.x` tag after Epic ships)

### Run Command (deferred)
```
Nyra.Dev.KnowledgeBench 50
```

### Pass Criteria (ALL must be true)
- `hallucination_rate < 2.0%` — no unretrieved API cited in any answer
- `p95_retrieval_ms < 500` — RAG retrieval SLA within threshold
- `uncited_symbol_errors == 0` — SymbolGate blocked or warned correctly

### Demoted-bench note (2026-05-10)
The reviewer's BL-09 finding (citation provenance is a prompt instruction, not an enforced invariant) means even if SC#2 were run today against a hypothetical implementation, a 2% measured rate could mask a 100% rate of unattributed-but-asserted-cited content. Re-plan must enforce citation provenance at retrieval-result construction (drop rows with null `source_url` before they reach the LLM) so SC#2 measures real behavior.

---

## Phase 3 Plan Completion Matrix

| Plan | Type | Status | Key Files (claimed; none exist on disk) |
|------|------|--------|-----------|
| 03-01 | LanceDB schema + bootstrap | ⬜ NOT-STARTED | `NyraHost/nyrahost/knowledge/schema.py`, `Embedder`, `Plugins/NYRA/Content/knowledge/bootstrap.lance/` |
| 03-02 | RAG retrieval pipeline | ⬜ NOT-STARTED | `NyraHost/nyrahost/rag/retriever.py`, `nyra_retrieve_knowledge` MCP tool |
| 03-03 | UHT symbol manifest | ⬜ NOT-STARTED | `NyraHost/nyrahost/symbols/manifest_builder.py`, `symbols_5x.json` (generated) |
| 03-04 | SymbolGate + ActionRouter | ⬜ NOT-STARTED | `NyraHost/nyrahost/symbols/symbol_gate.py`, `nyra_validate_symbol` MCP tool |
| 03-05 | Version dedup + IndexManager | ⬜ NOT-STARTED | `NyraHost/nyrahost/knowledge/deduplicator.py`, `index_manager.py`, `/knowledge/update` HTTP route |
| 03-06 | Gemma offline Q&A | ⬜ NOT-STARTED | `NyraHost/nyrahost/offline/offline_engine.py`, `nyra_ask_offline`, `privacy_mode` toggle |
| 03-07 | GitHub Actions CI pipeline | 📝 PLANNED-ONLY | `.github/workflows/build-knowledge-index.yml`, `scripts/build_index.py` (operator-run, not yet authored) |
| 03-08 | KnowledgeBench + exit gate | 📝 PLANNED-ONLY | `NyraEditor/Source/NyraEditor/Private/NyraDevTools.cpp` (operator-run; bench depends on Wave 1+2 source) |

The package path was also corrected during demotion: SUMMARY documents reference `nyra_host/...` (with underscore) but the canonical Phase 1 package layout is `nyrahost/...` (no underscore) at `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/`. Re-plan must use the correct package name.

---

## Phase-Exit Verdict

```
PHASE_3_GATE: fail (DEMOTED 2026-05-10)
```

Re-plan via `/gsd-plan-phase 03` before any further execution. Reviewer-flagged design risks must be encoded as architectural constraints in the new PLAN.md, not deferred to post-hoc fixes:

- **BL-03** SHA-256 archive verification — specify signing key (Ed25519 over the index archive, key shipped in plugin), verification before any directory swap, failure-mode (refuse swap, leave Tier-1 bootstrap active).
- **BL-04** Atomic swap on Windows — `MoveFileEx(MOVEFILE_REPLACE_EXISTING)` doesn't work on directories; use stage→rename→delete-stale with a recovery sentinel covering crash mid-swap.
- **BL-05** Cleanup of partial downloads — `*.partial` extension, sweep on next launch (>24h).
- **BL-06** Hard-coded host allowlist — `github.com`, `objects.githubusercontent.com`, `raw.githubusercontent.com` only. Reject before any HTTP request.
- **BL-07** Symbol-gate `mode` is server-side configuration, never accepted from MCP tool argument surface.
- **BL-08** Validated-symbol set derived from on-disk UHT manifest (allowlist), not a per-tool denylist.
- **BL-09** Citation provenance enforced at retrieval-result construction (drop null `source_url` rows). System prompt is reinforcement, not the gate.
- **BL-10** Use LanceDB parameterized predicate builder (or sanitize via closed enum of allowed predicate keys + escape values); ban `f"..."` filters at lint level.
- **BL-11** Embedding model from plugin `Content/` (read-only, signed) for Tier 1; if `%LOCALAPPDATA%` cache used for Tier 2, validate via `GetFinalPathNameByHandle` against canonical path (symlink/junction defense).

---

## Next Phase

Phase 4 (Blueprint Tool Catalog) is **BLOCKED** on a Phase-3 re-plan + execution. Phase 3 source code is non-existent; SC#3 (symbol validation) is a hard prerequisite for Phase 4 (the `nyra_validate_symbol` MCP tool that gates UE-touching agent actions). Run `/gsd-plan-phase 03` (re-plan), execute, then re-verify before unblocking Phase 4.

Note: Phase 4's own implementation has independently shipped (with its own pile of BLOCKERs — see `MILESTONE-REVIEW.md` Phase 4 section), so the practical impact is that Phase 4's BL-04 (no transaction wrapping) and BL-05/BL-06 (no idempotency / post-condition verification) cannot route through a real symbol gate today; the gate's contract is documentation-only.
