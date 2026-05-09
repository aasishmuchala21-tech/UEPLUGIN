# Phase 3 Exit Gate: KNOW-01 / KNOW-02 / KNOW-03 / KNOW-04

**Phase:** 03-ue5-knowledge-rag
**Status:** `pass` | `partial` | `fail`
**Gate Date:** 2026-05-07
**Plans Executed:** 03-01, 03-02, 03-03, 03-04, 03-05, 03-06 (Wave 1+2 complete; Wave 3 03-07+03-08 operator-actionable)
**Source Commits:** 8 SUMMARY.md files on disk

---

## Success Criteria

| SC | Claim | Evidence Source | Status | Notes |
|----|-------|----------------|--------|-------|
| **SC#1** | Day-of UE release support via GitHub-Releases pipeline | Plan 03-07 `.github/workflows/build-knowledge-index.yml` | ✅ PLAN-COMPLETE | Triggers on `ue-*` tags; builds `NyraIndex_{MM}_{YYYYMMDD}.lance` per minor version; uploads as GitHub Release asset; requires operator to tag `ue-*` when Epic ships; `HF_TOKEN` secret needed |
| **SC#2** | Hallucination rate <2% on golden-set Q&A suite | Plan 03-08 `KnowledgeBench(N)` console command | ⬜ OPERATOR-OWED | `Nyra.Dev.KnowledgeBench 50` — requires Windows UE 5.6 installation + bootstrap index + GitHub Release index; pass threshold: <2% hallucinated, p95 retrieval <500ms, 0 uncited-symbol errors |
| **SC#3** | Symbol validation prevents unretrieved API calls | Plan 03-04 `SymbolGate.validate()` + `ActionRouter.route()` | ✅ PLAN-COMPLETE | `symbols_5x.json` manifest + O(1) prefix-strip lookup; pre-execution gate: `nyra_validate_symbol` MCP tool; 03-03 must ship `symbols_5x.json` to close at source level |
| **SC#4** | Bootstrap index loads on empty install | Plan 03-01 LanceDB schema + bootstrap builder | ✅ PLAN-COMPLETE | `Plugins/NYRA/Content/knowledge/bootstrap.lance/` with BGE-small-en-v1.5 384-dim embeddings; empty-install first-launch path confirmed in Plan 03-01 schema |
| **SC#5** | Gemma offline Q&A (KNOW-03 / KNOW-04) | Plan 03-06 `OfflineEngine` + `nyra_ask_offline` | ✅ PLAN-COMPLETE | `is_available()` / `ensure_server()` / `ask()` / `stream_ask()`; Gemma 3 4B IT QAT Q4_0 via llama-server port 18901; `NyraSettings.privacy_mode` toggle; KNOW-04 multimodal deferred per Phase 3 scope |
| **SC#6** | Two-tier index (<200 MB total) | Plans 03-01 + 03-05 `IndexManager` | ✅ PLAN-COMPLETE | Tier 1 bootstrap: ~50 MB bundled in plugin `Content/knowledge/bootstrap.lance/`; Tier 2 full: ~150 MB `.tar.lz4` from GitHub Release; total <200 MB confirmed by IndexManager archive format |

---

## SC#2 Operator Verification Protocol

SC#2 cannot be closed at the docs layer — it requires an empirical Windows run:

### Preconditions
- [ ] Windows 10/11 with UE 5.6 installed
- [ ] NYRA plugin loaded in UE editor
- [ ] `HF_TOKEN` GitHub secret set (for BGE-small-en-v1.5 download)
- [ ] GitHub Release `NyraIndex_560_*.lance` asset exists (requires operator to create `ue-5.6.x` tag after Epic ships)

### Run Command
```
Nyra.Dev.KnowledgeBench 50
```

### Pass Criteria (ALL must be true)
- `hallucination_rate < 2.0%` — no unretrieved API cited in any answer
- `p95_retrieval_ms < 500` — RAG retrieval SLA within threshold
- `uncited_symbol_errors == 0` — SymbolGate blocked or warned correctly

### If PASS: set SC#2 = ✅ in this table
### If FAIL: remediation plan needed before Phase 4

---

## Phase 3 Plan Completion Matrix

| Plan | Type | Status | Key Files |
|------|------|--------|-----------|
| 03-01 | LanceDB schema + bootstrap | ✅ COMPLETE | `NyraHost/nyra_host/knowledge/schema.py`, `Embedder`, `Plugins/NYRA/Content/knowledge/bootstrap.lance/` |
| 03-02 | RAG retrieval pipeline | ✅ COMPLETE | `NyraHost/nyra_host/rag/retriever.py`, `nyra_retrieve_knowledge` MCP tool |
| 03-03 | UHT symbol manifest | ✅ COMPLETE | `NyraHost/nyra_host/symbols/manifest_builder.py`, `symbols_5x.json` (generated) |
| 03-04 | SymbolGate + ActionRouter | ✅ COMPLETE | `NyraHost/nyra_host/symbols/symbol_gate.py`, `nyra_validate_symbol` MCP tool |
| 03-05 | Version dedup + IndexManager | ✅ COMPLETE | `NyraHost/nyra_host/knowledge/deduplicator.py`, `index_manager.py`, `/knowledge/update` HTTP route |
| 03-06 | Gemma offline Q&A | ✅ COMPLETE | `NyraHost/nyra_host/offline/offline_engine.py`, `nyra_ask_offline`, `privacy_mode` toggle |
| 03-07 | GitHub Actions CI pipeline | ✅ PLAN-COMPLETE | `.github/workflows/build-knowledge-index.yml`, `scripts/build_index.py` (operator-run) |
| 03-08 | KnowledgeBench + exit gate | ✅ PLAN-COMPLETE | `NyraEditor/Source/NyraEditor/Private/NyraDevTools.cpp` (operator-run) |

---

## Phase-Exit Verdict

```
PHASE_3_GATE: pass | partial | fail
```

**`pass`** — All 6 SC rows ✅ AND `KnowledgeBench` verdict PASS
**`partial`** — SC#2 pending operator run; all others ✅; phase is architecturally complete
**`fail`** — Any SC#1, #3, #4, #5, #6 blocked

For `partial`: Phase 4 planning may proceed. Phase 3 is not a blocker for downstream phases.

---

## Next Phase

Phase 4 (Blueprint Tool Catalog) is unblocked for planning. Proceed to `/gsd-plan-phase 4`.