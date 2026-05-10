---
phase: 08-competitive-parity-aura
phase_number: 08
phase_name: Competitive Parity vs Aura
created: 2026-05-10
status: planning
goal: |
  Close the Aura feature-surface gap so NYRA's "no new AI bill + offline +
  computer-use + video-to-scene" wedge reads as ADDITIVE rather than substitute.
  Eight feature areas land as discrete plans; each is gated on the bar
  "Aura's documented capability is matched or exceeded on the same input."
trigger: |
  2026-05-10 Aura competitive analysis surfaced 8 feature gaps (document
  attachments, C++ authoring, BT agent, drag-drop UX, Niagara, performance
  profiling, AnimBP, Metasounds). Original Phase 8 (Fab Launch Prep)
  pushed to Phase 9.
---

# Phase 8: Competitive Parity vs Aura — CONTEXT

## Phase Boundary

This phase ships eight feature areas that close the gap surfaced by the
2026-05-10 comparison against Aura's public beta documentation
(tryaura.dev/documentation, fetched 2026-05-10). Each feature area is
its own plan; plans are independent and parallelizable in the executor.

The phase boundary is **feature-surface parity, not workflow superset**.
NYRA's existing wedges (free + user-subscription Claude + offline Gemma
+ computer-use for non-API apps + video-to-Sequencer DEMO-02) are NOT
touched here — those already differentiate. This phase exists because
Aura's broader feature surface would otherwise let reviewers / Fab
listing visitors dismiss NYRA as "narrower than Aura, but free."

## Locked Decisions

The following decisions are LOCKED and inputs to the planner. Do not
re-litigate during planning:

### LOCKED-01: Phase 8 displaces "Fab Launch Prep" to Phase 9.
**Why locked:** User decision via AskUserQuestion (2026-05-10):
"Replace Phase 8 entirely". Rationale: shipping NYRA against Aura's
public beta with a much narrower feature surface poisons launch
reception more than a 4–6-week delay does.
**How to apply:** Phase 9 is now Fab Launch Prep with content unchanged
from the prior Phase 8 — only the number is bumped. ROADMAP.md was
updated 2026-05-10.

### LOCKED-02: Eight feature areas, one plan each.
**Why locked:** User-selected via AskUserQuestion (2026-05-10) — all
four Tier-1 + all four Tier-2 options.
**How to apply:** Plans 08-01 through 08-08 map 1:1 to PARITY-01
through PARITY-08. Plan numbering matches feature numbering for grep
clarity.
| Plan | Slug | Requirement | Aura comparison |
|------|------|------------|-----------------|
| 08-01 | doc-attachments | PARITY-01 | Beats — accepts Aura's surface PLUS routes embedded images to vision |
| 08-02 | cpp-authoring-livecoding | PARITY-02 | Beats — decomposed transactional steps vs Aura's monolith |
| 08-03 | behavior-tree-agent | PARITY-03 | Beats — composable + idempotent + post-cond verified |
| 08-04 | drag-content-browser | PARITY-04 | Matches |
| 08-05 | niagara-vfx-agent | PARITY-05 | Matches |
| 08-06 | performance-profiling | PARITY-06 | Beats — cites Phase 3 RAG (Aura has no docs RAG) |
| 08-07 | animation-blueprint | PARITY-07 | Matches |
| 08-08 | metasounds-audio | PARITY-08 | Matches (acknowledged: feature-surface gloss) |

### LOCKED-03: Reuse Phase 4 Tool Catalog patterns.
**Why locked:** Phase 4 already established the canonical mutator
shape: `session_transaction` (BL-04), `idempotent_lookup/record` (BL-05),
`verify_post_condition` (BL-06), `NyraToolResult.to_dict()` for MCP
dispatch (BL-01). Plans 08-02, 08-03, 08-05, 08-07, 08-08 are mutator
tools and MUST follow this pattern — do not invent a new shape.
**How to apply:** Each mutator plan includes a "Pattern Compliance"
section in its PLAN.md showing which Phase 4 helper it reuses for each
of {transaction, idempotency, post-condition}.

### LOCKED-04: Reuse Phase 5 staging manifest for any artefact-producing tools.
**Why locked:** None of Phase 8's plans currently produce Meshy/ComfyUI-
shaped artefacts, but Niagara system templates and behavior tree
templates COULD reasonably persist outside the UE project (`Saved/NYRA/
templates/`). If so, they go through `StagingManifest` from Phase 5.
**How to apply:** If any plan adds a "save template" surface, it MUST
use StagingManifest, not direct filesystem writes.

### LOCKED-05: Reuse Phase 3 RAG (`nyra_kb_search`) in Performance plan.
**Why locked:** SC#6 explicitly says "Beats Aura on Performance
Profiling: cross-reference against Phase 3 nyra_kb_search ... Aura
has no separate docs RAG." This claim only holds if 08-06 actually
emits docs citations.
**How to apply:** Plan 08-06's `nyra_perf_explain_hotspot` output
schema MUST include a `citations: list[str]` field populated from
`KbSearchTool.execute(...)` results.

### LOCKED-06: Document attachment text extraction is pure-Python.
**Why locked:** SC#1 explicitly bounds wheel cache impact under 50 MB.
Pure-Python parsers (`pypdf`, `python-docx`, `python-pptx`, `openpyxl`,
`markdown`) are all <5 MB combined and need no platform-specific
binaries. Native PDF tools (poppler, mupdf) are bigger and platform-
fragmented.
**How to apply:** Plan 08-01 MUST add only pure-Python deps to
`requirements.lock`. If any candidate parser pulls a C extension as a
hard requirement (not an optional accelerator), pick a different
parser.

### LOCKED-07: drag-drop into chat extends `SNyraImageDropZone`.
**Why locked:** That widget already implements Slate `OnDragOver` /
`OnDrop` for image paths. The Content Browser drag payload is
`FAssetData` — a different shape but the same Slate surface.
**How to apply:** Plan 08-04 EXTENDS the existing drop zone; it does
NOT add a new widget. Avoids two parallel drop-target codepaths.

### LOCKED-08: Each plan is INDEPENDENTLY shippable.
**Why locked:** Solo dev + 8 features = aggressive scope. If timeline
slips, the project lead must be able to ship the subset of plans that
are done at any given checkpoint without breaking what shipped.
**How to apply:** No plan's success criteria reference another Phase 8
plan. Each plan's tools are individually MCP-registered. The Phase 8
EXIT-GATE document checks "≥6 of 8 plans shipped" not "all 8 shipped"
— per LOCKED-09 below.

### LOCKED-09: Phase 8 EXIT bar is 6 of 8 plans, with PARITY-01..04 mandatory.
**Why locked:** PARITY-01 (docs) + 02 (C++) + 03 (BT) + 04 (drag-drop)
are the four highest-leverage gaps from the user's Tier-1 selection
+ are the most-cited Aura features. PARITY-05/06/07/08 are Tier-2 and
incremental. Shipping only Tier-1 still closes the most damaging gap.
**How to apply:** EXIT-GATE checks {PARITY-01, PARITY-02, PARITY-03,
PARITY-04} all shipped + at least two of {05, 06, 07, 08} shipped. If
that bar is met, Phase 8 is COMPLETE and Phase 9 (Fab Launch) can
proceed even if the remaining Tier-2 features slip.

## Out of Scope

These are deliberately deferred. Do not let plans expand into them.

- **Slate UI overlay generation** (Aura ships this; NYRA defers to v1.2).
  Code-generating UI from natural-language descriptions is a Slate-side
  large-surface feature; not in PARITY-* scope.
- **IDE / Claude Code integration** (Aura ships this in alpha). NYRA's
  users already use Claude Code separately — there's nothing to
  integrate. This is a strategic non-goal, not a scope cut.
- **Live Coding C++ for non-NYRA-authored code.** Plan 08-02 ships
  authoring + recompile loops for files NYRA created in the session.
  Reading + editing arbitrary user C++ is a v1.2 expansion.
- **Niagara module authoring (vs system/emitter authoring).** Plan
  08-05 ships system + emitter + module-parameter-set, NOT
  custom-module DSL authoring. The latter is a vastly larger surface.
- **Behavior Tree task implementation.** Plan 08-03 ships graph
  authoring (composites, decorators, blackboard keys, calling existing
  tasks) — NOT generating new C++ task class implementations. A task
  generator could land later via Plan 08-02's C++ authoring surface.
- **AnimBP node implementation.** Plan 08-07 ships state machine +
  transition authoring, NOT custom AnimNode generation.

## Cross-References

- **CLAUDE.md**: Quality Bar ("parity is failure") — but THIS phase is
  feature-surface parity to defend the wedge. Read carefully: NYRA's
  wedge (free + sub + offline + CU + video) is the differentiator;
  Phase 8 makes that wedge LEGIBLE by removing the "narrower than
  Aura" objection. The phase still has per-SC "beats Aura on X"
  framings (see SC#1, SC#2, SC#3, SC#6).
- **CONTEXT.md (Phase 4)**: Tool Catalog patterns. Plans 08-02, 08-03,
  08-05, 08-07, 08-08 inherit the BL-04/05/06 mutator shape.
- **CONTEXT.md (Phase 5)**: StagingManifest pattern.
- **`nyrahost.knowledge.KnowledgeIndex`**: Plan 08-06 dependency.
- **REQUIREMENTS.md**: Will gain PARITY-01..08 entries during planning.

## Inputs to Research

- UE 5.4–5.7 Python API surfaces for: `unreal.BehaviorTree`,
  `unreal.NiagaraSystem`/`unreal.NiagaraEmitter`, `unreal.AnimBlueprint`,
  `unreal.MetasoundDocument`. Verify each tool's intended Python
  entrypoint exists, has stable signature across the 4-version matrix,
  and is callable from outside an editor blueprint context.
- UE Hot Reload / Live Coding APIs accessible from Python (Plan 08-02's
  recompile triplet). May need a UE C++ helper that exposes a Python-
  callable wrapper if the native API isn't reflected.
- Insights `.utrace` file format for read-only parsing (Plan 08-06).
- pypdf vs pdfplumber vs pdfminer.six tradeoffs for embedded-image
  extraction (Plan 08-01 LOCKED-06 constraint).
- Slate `FAssetData` drop payload shape vs the existing image-drop-zone
  payload (Plan 08-04 LOCKED-07).

## Threats to Watch For

- **T-08-01: UE Python API drift across 5.4 → 5.7.** Some 5.7 APIs
  don't exist in 5.4. Plan 08-02..05/07/08 must each spell out which
  versions they support and what fallback (or hard-error) applies on
  older versions.
- **T-08-02: `requirements.lock` bloat from PDF parsers.** Pure-Python
  doesn't mean small — pypdf is 2 MB, python-pptx 1 MB, openpyxl
  10 MB. Plan 08-01 must measure the post-add wheel cache size and
  fail-loud if it crosses 75 MB total.
- **T-08-03: Live Coding has different reliability across UE versions.**
  Plan 08-02 must document which versions it actually verifies on, and
  fall back to standard Hot Reload (slower but more reliable) on
  versions where Live Coding is broken.
- **T-08-04: Niagara emitter API is GPU-vs-CPU-conditioned.** GPU
  emitters require shader compile pass; the API surface differs. Plan
  08-05's "GPU sprite + ribbon emitter examples reproduce" SC must
  cover both paths.
- **T-08-05: Plan 08-06's docs citation claim is brittle.** If
  `KbSearchTool` returns `no_index_loaded` (no UE5 corpus shipped yet),
  Plan 08-06 must degrade gracefully with a remediation pointing at
  the Phase 3 corpus build pipeline — NOT silently emit empty
  citations.
- **T-08-06: Drag-from-Content-Browser may not propagate `FAssetData`
  in all UE 5.x versions.** Slate Content Browser drag payload format
  changed between 5.4 and 5.6. Plan 08-04 must verify per-version.

## What This Phase Is NOT

- NOT a redesign of NYRA's wedge. The wedge stays.
- NOT a feature parity claim across the entire Aura surface — that's
  a moving target. The bar is "Aura's documented capabilities as of
  2026-05-10 fetch."
- NOT a v1.0 launch blocker for the no-AI-bill wedge. If everything in
  Phase 8 slipped, NYRA's wedge would still be defensible — it just
  wouldn't be marketed as cleanly. Phase 8 is the "defensible at the
  Fab listing review" phase.
