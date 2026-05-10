---
phase: 08-competitive-parity-aura
checked: 2026-05-10
checker: gsd-plan-checker
verdict: NEEDS-PLANNER-REVISION
---

# Phase 8 Plan-Check Report

## Per-plan verdicts

| Plan | Req | Verdict | One-line reason |
|---|---|---|---|
| 08-01 doc-attachments | PARITY-01 | NEEDS-FIX | LOCKED-06 strict reading: adds `beautifulsoup4` as 6th lib + accepts transitive Pillow/lxml C extensions. Internally consistent with RESEARCH.md A8 but user's verification question reads LOCKED-06 strictly. |
| 08-02 cpp-authoring | PARITY-02 | NEEDS-FIX | Cross-plan friction on `NyraEditor.Build.cs` and `mcp_server/__init__.py` not flagged with sequencing note. Wave 0 ordering inversion (Wave 0 task numbered after Wave 1 in one place). |
| 08-03 behavior-tree | PARITY-03 | NEEDS-FIX | Same cross-plan Build.cs + mcp_server friction unaddressed. Otherwise sound. |
| 08-04 drag-content-browser | PARITY-04 | NEEDS-FIX | `FNyraAttachmentRef` enum extension overlap with 08-01 (Document vs Asset kind) needs explicit ordering note. |
| 08-05 niagara-vfx | PARITY-05 | NEEDS-FIX | Same shared-file friction unaddressed. T-08-04 GPU/CPU emitter coverage present. |
| 08-06 performance-profiling | PARITY-06 | PASS-WITH-NITS | LOCKED-05 citations_status field present, T-08-05 graceful degrade present, KbSearchTool import explicit. Nit: depends on Phase 3 corpus actually shipped. |
| 08-07 animation-blueprint | PARITY-07 | NEEDS-FIX | Same shared-file friction. AnimNode generation correctly out-of-scope. |
| 08-08 metasounds-audio | PARITY-08 | PASS-WITH-NITS | Smallest scope, gloss-tier acknowledgment honest. Nit: same mcp_server registration friction. |

**Tally:** 0 PASS / 6 NEEDS-FIX / 0 BLOCK / 2 PASS-WITH-NITS

## LOCKED decision compliance

| LOCKED | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 |
|--------|----|----|----|----|----|----|----|----|
| 01 (P8 displaces Fab Launch) | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| 02 (8 plans 1:1) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 03 (Phase 4 mutator) | N/A | ✅ | ✅ | N/A | ✅ | N/A | ✅ | ✅ |
| 04 (StagingManifest) | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| 05 (Phase 3 KB citations) | N/A | N/A | N/A | N/A | N/A | ✅ | N/A | N/A |
| 06 (pure-Python parsers) | ⚠️ | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| 07 (extend SNyraImageDropZone) | N/A | N/A | N/A | ✅ | N/A | N/A | N/A | N/A |
| 08 (independently shippable) | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| 09 (tier 1/2 + EXIT bar) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

LOCKED-08 ⚠️ across all 8 plans: shared-file friction means plans aren't *truly* independent — they're independently *designable* but execution order matters.

## Threat coverage

| Threat | Plans expected to address | Status |
|---|---|---|
| T-08-01 UE Python API drift 5.4-5.7 | 02, 03, 05, 07, 08 | ✅ Wave 0 symbol-survey in all five (one ordering inversion in 08-02) |
| T-08-02 wheel cache bloat | 01 | ✅ 75 MB fail-loud check present |
| T-08-03 Live Coding flakiness | 02 | ✅ Hot Reload fallback documented |
| T-08-04 Niagara GPU vs CPU emitter | 05 | ✅ `sim_target` enum branches |
| T-08-05 KB citation degradation | 06 | ✅ `citations_status: ok | no_index_loaded` |
| T-08-06 Content Browser drag format drift | 04 | ✅ per-version verification noted |

## Cross-plan friction (unaddressed by planner)

Two shared files with append-only edits across multiple plans:

1. **`TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs`** — plans 02/03/05/07 each add `PrivateDependencyModuleNames` entries (LiveCoding, BehaviorTreeEditor, AIModule, Niagara, NiagaraEditor, AnimGraph, AnimGraphRuntime, BlueprintGraph). Same C# file. Parallel execution within Wave 2 → merge conflicts.
2. **`TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/__init__.py`** — plans 02/03/05/06/07/08 each append imports + `_tools` dict entries + `list_tools()` schemas. Append-only and trivially mergeable, but reviewer confusion if not committed in plan-number order.

Also: **`FNyraAttachmentRef` enum extension** in `NyraMessageModel.h` — 08-01 adds `Document`, 08-04 adds `Asset`. Either order works but neither plan flags the dependency on the other.

## Specific findings (severity-classified)

### BLOCKER (must fix before execution)

**B1.** `RESEARCH.md` `## Open Questions` section at line ~620 lacks per-question resolution. 4 questions present without `(RESOLVED)` / `(DEFERRED)` markers. Per Dimension 11 this is a phase-planning gate. Q1/Q2 are Wave-0-deferred; Q3/Q4 have implicit answers in the body that need to be lifted to inline resolutions.

**B2.** Cross-plan shared-file friction not flagged with sequencing notes in any of plans 02/03/05/06/07/08. Two acceptable mitigations:
- Add `serial_after: ["08-0N"]` frontmatter to each plan establishing plan-number-ordered commits
- Extract a "Wave 1.5" `08-00-shared-infra-PLAN.md` that owns Build.cs deps + mcp_server slot reservations

### NEEDS-FIX (should fix before execution)

**N1.** LOCKED-06 strict-vs-loose reading divergence in Plan 08-01:
- LOCKED-06 names exactly 5 libs: pypdf, python-docx, python-pptx, openpyxl, markdown
- Plan 08-01 adds `beautifulsoup4` as 6th lib for HTML parsing
- python-docx pulls `lxml` (C extension); python-pptx pulls `Pillow` (C extension)
- Plan 08-01 explicitly acknowledges this as an A8 "planner-clarification ask" but ships without resolution

Three resolution paths:
- (a) Drop `beautifulsoup4`; use stdlib `html.parser` (HTMLParser class) — weaker but zero deps
- (b) Drop HTML support entirely from PARITY-01; defer to a future PARITY-01.1
- (c) Amend LOCKED-06 in CONTEXT.md to allow `beautifulsoup4` and acknowledge transitive C extensions are unavoidable for python-docx/pptx

### NIT (polish; doesn't block execution)

**NIT-1.** Plan 08-02 task ordering inversion: Wave 0 task numbered after Wave 1 task in the body. Cosmetic but confusing.

**NIT-2.** Plan 08-08 frontmatter doesn't loudly mark "gloss-tier" the way the goal text does. Recommend `nature: gloss` or similar in frontmatter.

## Overall verdict

**NEEDS-PLANNER-REVISION**

Three blocker/needs-fix issues, all mechanically resolvable. The plans themselves show strong individual quality:
- Canonical Phase 4 mutator shape consistently applied (LOCKED-03)
- Wave 0 symbol-survey gates present (T-08-01)
- Out-of-scope discipline excellent across all 8 plans
- Threats addressed individually

If the user chooses to GREEN-LIGHT despite revision request:
- Serial execution within each wave downgrades B2 from BLOCKER to WARNING
- LOCKED-06 (a) or (c) resolves N1 in <30 minutes
- B1 is a docs-fix, ~5 minutes

The LOCKED-09 EXIT bar (tier-1 4/4 + tier-2 ≥2/4) remains structurally achievable: 01-04 are NEEDS-FIX-but-fixable; 06 + 08 are PASS-WITH-NITS already covering the ≥2 tier-2.

## Recommended next steps

1. Apply 3 fixes (B1, B2, N1) inline rather than re-spawning the planner — all are mechanical
2. Document serial-execution requirement in CONTEXT.md (downgrades B2 to satisfied)
3. Resolve Open Questions in RESEARCH.md (B1)
4. Pick one of LOCKED-06 paths (a)/(b)/(c) for N1 — recommended (c) amend, since (a) significantly weakens HTML support and (b) drops a documented Aura parity feature
5. Re-run plan-checker (lightweight) OR commit-and-execute if confident the fixes land cleanly

This report supersedes the inline summary the gsd-plan-checker agent delivered (its Bash heredoc was denied by harness; report content captured here verbatim).
