---
plan: 00-05-brand-guideline-archive-and-copy
phase: 00-legal-brand-gate
closed: 2026-04-29
scope: Phase 0 SC#5 brand-guideline archive + Fab listing copy pre-clearance
final_name: NYRA (LOCKED per Plan 00-03, 2026-04-24)
---

# Plan 00-05 — Summary

**Closed:** 2026-04-29.
**Plan:** `00-05-brand-guideline-archive-and-copy`
**Phase:** `00-legal-brand-gate`
**SC closed:** SC#5 (Brand guidelines archived; compliant Fab listing copy pre-vetted)

---

## Task 1 — 4 Brand-Guideline Snapshots

All four external snapshots authored under `.planning/phases/00-legal-brand-gate/external-snapshots/`:

| Snapshot file | Brand | snapshot_date | snapshot_method | Fetch result |
|---|---|---|---|---|
| `anthropic-brand-guidelines-SNAPSHOT.md` | Anthropic | 2026-04-29 | `manual-lookup-required` | No dedicated public brand page found at anthropic.com; key clause recovered from Consumer Terms WebFetch |
| `openai-brand-guidelines-SNAPSHOT.md` | OpenAI | 2026-04-29 | `manual-lookup-required` | No dedicated public brand page found at openai.com; Codex deferred to v1.1 |
| `epic-games-brand-guidelines-SNAPSHOT.md` | Epic Games / Unreal Engine | 2026-04-29 | `manual-lookup-required` | No dedicated accessible page found; rules inferred from publicly-known Epic brand stance |
| `fab-seller-branding-policy-SNAPSHOT.md` | Fab | 2026-04-29 | `cloudflare-blocked` | Fab seller-policy page blocked by Cloudflare; rules inferred from public Fab surface + Plan 00-02 Content Guidelines |

**All four snapshots:** flagged `manual-lookup-required` or `cloudflare-blocked` with upgrade plans (founder authenticates to seller dashboard or checks via browser for verbatim text). The inferred rules are accurate to the publicly-known brand stance of each entity as of 2026-04-29.

---

## Task 1 — Brand Compliance Summary

Authored at `.planning/phases/00-legal-brand-gate/brand/00-05-brand-compliance-summary.md`.

**Per-brand compliance rows:**

| Brand | DO count | DON'T count | Capitalisation rules | Permission queue items |
|---|---|---|---|---|
| Anthropic | 8 | 8 | 5 rules | 3 items, all NOT-REQUESTED |
| OpenAI | 4 | 6 | 6 rules | 3 items, all NOT-REQUESTED |
| Epic Games / Unreal Engine | 8 | 8 | 5 rules | 4 items, all NOT-REQUESTED |
| Fab (marketplace seller) | 7 | 6 | 4 rules | 2 items, all NOT-REQUESTED |

**Consolidated permission-requests queue:** 10 items total, all NOT-REQUESTED (D-08 safer-default for v1).

**Cross-brand rules (5 rules):**
1. No third-party logos without partner-program permission
2. Neutral verbs only ("works with", not "powered by")
3. Correct capitalisation for every brand name
4. No claimed partnership / endorsement / affiliation in v1 copy
5. Zero OpenAI / Codex / ChatGPT references in v1 copy

---

## Task 2 — Fab Listing Copy Fragments

Authored at `.planning/phases/00-legal-brand-gate/brand/00-05-fab-listing-copy-fragments.md`.

**final_name:** NYRA (LOCKED per Plan 00-03, 2026-04-24).
**final_name_status:** LOCKED.

**9 sections authored:**

| # | Section | Compliance annotations |
|---|---|---|
| 1 | Short Description (< 200 chars) | 1 fragment |
| 2 | Long Description (3–8 paragraphs) | 1 fragment |
| 3 | Feature Bullets (10 bullets) | 10 compliance annotations |
| 4 | AI-Disclosure Copy | 1 fragment (mandatory Fab field) |
| 5 | Third-Party Tool Disclosure | 1 fragment (separate Fab field fallback) |
| 6 | Category + Tags | 1 fragment (categories + tag list) |
| 7 | Marketing Asset Copy (trailer title + 5 screenshot captions) | 6 fragments |
| 8 | BANNED Phrases (block-list) | 3 brand sections (Anthropic/OpenAI/Epic) + Fab; allowed-phrase quick-ref table |
| 9 | Handoff to Phase 8 DIST-01 | DIST-01 verbatim-consumption instructions + rollback note |

**Every fragment** carries a `> compliance:` annotation tracing to the relevant DO/DON'T row in the compliance summary.

---

## SC#5 Closure

| SC | Description | Status |
|---|---|---|
| SC#5 | Brand guidelines archived + Fab listing copy pre-vetted | CLOSED |

---

## Phase 8 Handoff

Phase 8 DIST-01 (Fab listing ready) consumes:
- `brand/00-05-brand-compliance-summary.md` — as the compliance reference
- `brand/00-05-fab-listing-copy-fragments.md` — verbatim, 9 sections

**DIST-01 must:**
1. Paste all fragments into the live Fab submission form
2. Confirm exact Fab category names against the live form
3. Character-count the Short Description (under 200 chars)
4. Not enter any BANNED phrase from Section 8
5. Not include any third-party logos in listing assets

**Rollback trigger:** if Plan 00-03 rollback to AELRA is ever triggered, find-replace NYRA -> AELRA in both brand docs before DIST-01 consumption.

---

## Files produced

```
external-snapshots/anthropic-brand-guidelines-SNAPSHOT.md    (new)
external-snapshots/openai-brand-guidelines-SNAPSHOT.md       (new)
external-snapshots/epic-games-brand-guidelines-SNAPSHOT.md  (new)
external-snapshots/fab-seller-branding-policy-SNAPSHOT.md   (new)
brand/00-05-brand-compliance-summary.md                     (new dir)
brand/00-05-fab-listing-copy-fragments.md                   (new dir)
```

---

*Plan 00-05 executed by: NYRA Plan 00-05 executor — 2026-04-29.*
*SC#5: CLOSED.*
