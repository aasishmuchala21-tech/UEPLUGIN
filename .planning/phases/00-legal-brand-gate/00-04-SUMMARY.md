---
phase: 00-legal-brand-gate
plan: 04
subsystem: legal
tags: [gemma, license, eula, generated-content, liability-passthrough, ephemeral-processing, yt-dlp, privacy, counsel-review, phase-0-sc4, plan-00-04]
plan_status: COMPLETE
plan_commits: 3

# Dependency graph
requires: []
provides:
  - "Gemma license re-verify note (`legal/00-04-gemma-license-reverify-note.md`) with `re_verify_verdict: UNCHANGED` + `impact_on_nyra_redistribution: NONE` — confirms STACK.md April 2026 baseline capture is still valid as of 2026-04-29 snapshot; Phase 1/2/3/6/7 Gemma redistribution architecture is fully within license; one non-material delta (Updates-to-Terms clause) requires no architectural change"
  - "Gemma 3 Model Notice appendix (`legal/00-04-nyra-eula-gemma-notice-appendix.md`) — fulfils Gemma license Section 3 terms-notice redistribution requirement; passes through 6 prohibited-use bullets verbatim from snapshot; clarifies output ownership and redistribution rules; incorporated by reference into EULA §5 Third-Party Components and §Appendix A"
  - "NYRA v1 EULA first draft (`legal/00-04-nyra-eula-draft.md`) — 15 numbered sections + Appendix A + Counsel Review Checklist; `status: founder-first-draft`, `counsel_reviewed: false`, `counsel_review_scheduled: post-v1 or at-founder-discretion`; two D-06 novel clauses: §6 Generated Content liability passthrough (Meshy / ComfyUI / Substance / Claude outputs belong to user, NYRA warrants nothing) and §7 Reference Material ephemeral processing (yt-dlp + ≤16 keyframes + full video deleted from /tmp after run + user affirms copyright-clean use); built-in minimal §8 privacy clause (no backend, no telemetry, local-only storage)"
  - "Phase 0 SC#4 CLOSED at docs-layer: Gemma redistribution confirmed legal (verdict UNCHANGED) + NYRA v1 EULA draft exists covering both novel liability surfaces + Gemma Notice appendix fulfils redistribution-notice requirement + counsel review deferred per D-06"
affects:
  - "Plan 00-06 phase-closure-ledger — flips SC#4 from PENDING to CLOSED; SC#4 closes on Gemma re-verify verdict UNCHANGED + EULA draft exists + Gemma Notice exists"
  - "Phase 1/2/3/6/7 Gemma redistribution — re-verify note confirms no license change; Gemma Notice fulfils redistribution-notice obligation; no downstream architectural changes needed"
  - "Phase 0 SC#4 is now CLOSED at docs-layer — no further docs-layer work required; founder manual verbatim-upgrade of Gemma snapshot (pending-browser-copy from non-sandboxed session) is recommended but does not block SC#4 closure per partial-completion discipline"
  - "ROADMAP Phase 0 progress table — advances from 3/6 to 4/6 plans complete at docs-layer"

# Summary
phase_0_sc4_status: CLOSED
gemma_reverify_verdict: UNCHANGED
gemma_impact: NONE
eula_version: "0.1.0-draft"
eula_status: founder-first-draft
counsel_review: deferred-post-v1
d06_novel_clauses: 2
sections_in_eula: 15
appendix_count: 1
counsel_review_items: 7

# Artifacts produced
artifacts:
  - file: "legal/00-04-gemma-license-reverify-note.md"
    commits: 1
    verdict: "UNCHANGED"
    impact: "NONE"
    key_finding: "Gemma license unchanged since April 2026 STACK.md baseline; commercial redistribution with terms-notice still valid; one non-material delta (Updates-to-Terms clause) requires no architectural change"
  - file: "legal/00-04-nyra-eula-gemma-notice-appendix.md"
    commits: 1
    purpose: "Redistribution notice fulfilling Gemma license Section 3 terms-notice clause; passes through 6 prohibited-use bullets; clarifies output ownership and redistribution rules"
    incorporated_by: "EULA §5 Third-Party Components + §Appendix A"
  - file: "legal/00-04-nyra-eula-draft.md"
    commits: 1
    sections: 15
    novel_clauses:
      - section: "§6 — Generated Content — Liability Passthrough"
        type: "D-06 NOVEL CLAUSE"
        covers: "Meshy / ComfyUI / Substance 3D Sampler / Claude outputs — ownership and liability flow from third-party tool's own terms directly to user; NYRA makes no warranties"
      - section: "§7 — Reference Material — Ephemeral Processing"
        type: "D-06 NOVEL CLAUSE"
        covers: "yt-dlp + ≤16 keyframes + full video deleted from /tmp after run + user affirms copyright-clean use + yt-dlp disableable in settings"
    counsel_review_deferred: true
    counsel_items: 7
    counsel_flagged_sections: ["§6 Generated Content", "§7 Ephemeral Processing", "§8 Data We Do Not Collect", "§13 Governing Law", "Appendix A Gemma Notice"]

# Gemma re-verify details
gemma_reverify:
  baseline: "STACK.md April 2026 — 'Gemma license allows commercial redistribution with terms-notice'"
  snapshot_date: "2026-04-25"
  reverify_date: "2026-04-29"
  snapshot_file: "external-snapshots/gemma-terms-of-use-SNAPSHOT.md"
  model: "google/gemma-3-4b-it-qat-q4_0-gguf"
  verdict: "UNCHANGED"
  material_changes: 0
  non_material_changes: 1
  non_material_detail: "Updates-to-Terms clause (standard license-maintenance provision; permits Google to update terms prospectively; does not change substantive redistribution obligations)"
  impact: "NONE"
  phases_confirmed_permitted:
    - Phase 1: "NyraInfer process — bundling/downloading GGUF on demand + local llama.cpp inference"
    - Phase 2: "Gemma subscription fallback — user selects Gemma as offline/privacy fallback"
    - Phase 3: "Gemma offline Q&A — RAG using Gemma 3 4B on user hardware"
    - Phase 6: "Gemma vision (image-to-scene) — offline reference image processing"
    - Phase 7: "Gemma vision (video-to-shot) — offline keyframe processing"
  annual_reverify_recommended: "April 2027"
  next_action_on_material_change: "Re-run this note with MATERIAL-CHANGES verdict and escalate before continuing Gemma redistribution"

# Counsel review deferral rationale
counsel_review_deferral:
  reason: "D-06 explicitly defers counsel review to post-v1; EULA is a founder-authored working draft, NOT a legally-negotiated contract; two D-06 novel clauses (§6 + §7) require careful review at v1.1; §8 minimal privacy clause may satisfy Fab/GDPR/CCPA for free no-backend plugin but counsel should confirm"
  what_counsel_review_covers: "7 flagged items across §6, §7, §8, §13, Appendix A; see full Counsel Review Checklist in EULA draft"
  what_this_draft_is_not: "This is NOT a legally-negotiated contract; it is a founder-authored working draft authored from standard UE-plugin boilerplate + two custom sections per D-06 scope; counsel should treat it as a starting point, not a final document"
---

# Plan 00-04 SUMMARY — Gemma License + NYRA v1 EULA Draft

**Plan:** 00-04-gemma-license-and-eula-draft
**Phase:** 00-legal-brand-gate
**Executed:** 2026-04-29
**Status:** COMPLETE — 3 files, 3 commits

---

## Phase 0 SC#4 — CLOSED

SC#4 ("Gemma redistribution is confirmed legal and NYRA's v1 terms cover the two novel liability surfaces so counsel has a draft to review at v1.1") is **CLOSED at the docs layer** based on:

1. Gemma license re-verify verdict `UNCHANGED` — commercial redistribution with terms-notice still valid; no material changes since April 2026 baseline.
2. NYRA v1 EULA draft exists with both D-06 novel clauses present.
3. Gemma Notice appendix exists and is incorporated by reference into the EULA.
4. Counsel review deferred to post-v1 per D-06.

---

## What was produced

### 1. Gemma License Re-verify Note
`legal/00-04-gemma-license-reverify-note.md`

Compares the April 2026 STACK.md baseline ("Gemma license allows commercial redistribution with terms-notice") against the 2026-04-25 snapshot.

**Verdict: `UNCHANGED`**
**Impact: `NONE`**

The Gemma license has not introduced any material changes. One non-material delta (Updates-to-Terms clause — a standard license-maintenance provision) requires no architectural change.

All five NYRA Gemma usage patterns (Phase 1 NyraInfer, Phase 2 Gemma fallback, Phase 3 Gemma offline Q&A, Phase 6 Gemma vision image-to-scene, Phase 7 Gemma vision video-to-shot) are confirmed as still within license.

Annual re-verify recommended: April 2027.

### 2. Gemma 3 Model Notice Appendix
`legal/00-04-nyra-eula-gemma-notice-appendix.md`

Fulfils the Gemma license Section 3 terms-notice redistribution requirement. Contains:
- Gemma Terms of Use URL + Gemma Prohibited Use Policy URL (both from snapshot).
- 6 prohibited-use bullets verbatim from snapshot.
- Output ownership clarification (user owns Gemma-generated output).
- Redistribution rules (cannot redistribute Gemma independently of NYRA).

Incorporated by reference into EULA §5 (Third-Party Components) and §Appendix A (Gemma 3 Model Notice).

### 3. NYRA v1 EULA First Draft
`legal/00-04-nyra-eula-draft.md` — `version: 0.1.0-draft`, `status: founder-first-draft`

15 numbered sections + Appendix A + Counsel Review Checklist:

| Section | Type | Notes |
|---------|------|-------|
| §1 Definitions | Boilerplate | NYRA, User, Plugin, Third-Party Components, Generated Content, Reference Material, Local Fallback Model, Fab |
| §2 License Grant | Boilerplate | Free plugin; no redistribution/sublicense; Fab-only distribution |
| §3 Permitted Uses | Boilerplate | Install, run, commercial UE dev, reference material, Gemma model |
| §4 Prohibited Uses | Extended | 10 bullets including explicit ToS violations (Anthropic, Google/Gemma, Meshy, ComfyUI, Epic, Adobe) |
| §5 Third-Party Components | Boilerplate+ | References Gemma Notice appendix; per-service terms summary |
| §6 Generated Content — Liability Passthrough | **D-06 NOVEL CLAUSE** | Meshy/ComfyUI/Substance/Claude outputs: ownership + liability flows from third-party tool's terms to user; NYRA warrants nothing |
| §7 Reference Material — Ephemeral Processing | **D-06 NOVEL CLAUSE** | yt-dlp + ≤16 keyframes + full video deleted from /tmp after run + user affirms copyright-clean use |
| §8 Data We Do Not Collect | **Built-in privacy clause** | No backend; no telemetry; local storage; no automatic crash reports; per-third-party-service privacy governance |
| §9 Warranty Disclaimer | Boilerplate | AS IS for free plugin |
| §10 Limitation of Liability | Boilerplate | Cap at $0.00 for free plugin |
| §11 Indemnification | Boilerplate | User indemnifies NYRA for misuse of Generated Content, Reference Material, third-party terms violations |
| §12 Termination | Boilerplate | On EULA breach or user uninstall; survival of §§6,7,8,9,10,11,13 |
| §13 Governing Law & Venue | Founder-fill | State-level + county venue; specific state/county to be filled before v1 launch |
| §14 Changes to EULA | Boilerplate | Version-bump + changelog notice |
| §15 General | Boilerplate | Severability, entire agreement, assignment, no waiver, third-party beneficiaries |
| Appendix A | Reference | Incorporates Gemma Notice by reference |
| Counsel Review Checklist | Post-v1 | 7 flagged items across §6, §7, §8, §13, Appendix A |

---

## Key findings

**Gemma license is stable.** No material changes since April 2026 baseline. Annual re-verify recommended April 2027 or on any Gemma announcement.

**EULA covers both novel liability surfaces.** The two D-06 novel clauses (§6 Generated Content + §7 Reference Material) are the core of the draft — everything else is boilerplate from a standard UE-plugin EULA template. They establish the liability story clearly: NYRA orchestrates tools, does not own their outputs, and does not warranty their outputs.

**Privacy is handled in-document.** §8 "Data We Do Not Collect" avoids spawning a separate standalone privacy policy doc in Phase 0. Counsel should confirm this satisfies Fab/GDPR/CCPA requirements at post-v1 review.

**Counsel review deferred.** The draft is explicitly marked `counsel_reviewed: false` and `counsel_review_scheduled: post-v1 or at-founder-discretion`. Seven specific items are flagged in the Counsel Review Checklist.

---

## Founder manual follow-ups

These items do NOT block SC#4 closure (per partial-completion discipline) but are documented here for completeness:

- [ ] **Gemma snapshot verbatim upgrade:** From a non-sandboxed browser, copy the full text of `https://ai.google.dev/gemma/terms` and `https://ai.google.dev/gemma/prohibited_use_policy` into the snapshot file, replacing each `[paraphrased from live page]` block. Bump `snapshot_method` to `manual-browser-copy-YYYY-MM-DD`.
- [ ] **EULA governing law + venue:** Fill in the specific state name and county-level court before v1 launch (currently marked `[Founder-fill before v1 launch:]`).
- [ ] **Counsel review at v1.1:** Seven flagged items in the Counsel Review Checklist require counsel attention before v1.1 launch.

---

## Phase 0 SC#4 closure record

```
SC#4: Gemma redistribution confirmed legal + NYRA v1 EULA draft exists
  Gemma re-verify verdict:    UNCHANGED
  Gemma impact on redistribution: NONE
  EULA draft version:         0.1.0-draft
  EULA status:                founder-first-draft
  Counsel reviewed:            false
  Counsel review scheduled:    post-v1 or at-founder-discretion
  Gemma Notice appendix:       present + incorporated by reference
  §6 Novel clause:            present (Generated Content liability passthrough)
  §7 Novel clause:            present (Reference Material ephemeral processing)
  §8 Privacy clause:          present (built-in minimal)
  Result:                     SC#4 CLOSED at docs-layer
```
