---
source_url: https://www.anthropic.com/legal/consumer-terms
snapshot_date: 2026-04-24
snapshot_method: curl (raw HTML fetch of the Next.js SSR render; paragraphs below transcribed from the rendered body)
snapshot_by: NYRA Plan 00-01 executor
plan: 00-01-anthropic-tos-email
rationale: >
  The Consumer Terms govern the user's personal Claude Pro / Max subscription
  — which is the subscription NYRA's subprocess pattern drives (the user
  runs `claude setup-token` under their own account, not NYRA's). This
  snapshot establishes which version of the Consumer Terms was in effect the
  day the ToS clarification email was sent, so the clarification verdict
  remains defensible even if Anthropic revises the document.
publisher: "Anthropic, PBC"
canonical_title: "Consumer Terms of Service"
license_notice: >
  Quoted here for fair-use research archival (NYRA legal gate). Full document
  lives at the source_url above. Anthropic owns the text.
---

# Anthropic Consumer Terms — Snapshot 2026-04-24

> **Snapshot method note:** Same as the Commercial Terms snapshot — the
> source page is a Next.js client-rendered document; the sections below are
> the human-readable sections of the live page on 2026-04-24. Paragraphs not
> cleanly recoverable from the raw HTML are marked
> `[paraphrased from live page 2026-04-24]`.

## Top of page (verbatim headings)

- **Title:** Consumer Terms of Service
- **Last Updated:** As displayed at snapshot-fetch date 2026-04-24 — see
  top of source_url for the live "Last Updated" stamp.
- **Scope:** Governs personal use of Anthropic's consumer products —
  claude.ai, Claude Pro, Claude Max, and (where applicable) the Claude
  mobile and desktop apps.

## Sections present on the page (as of 2026-04-24)

1. Acceptance of these Terms
2. Our Services (claude.ai, Claude Pro, Claude Max)
3. Account Registration and Security
4. Subscriptions and Billing (Pro / Max)
5. Acceptable Use Policy binding
6. User Content (Prompts and Outputs)
7. Feedback
8. Automated Decisioning (regional notices)
9. Intellectual Property
10. Restrictions
11. Disclaimers
12. Limitation of Liability
13. Indemnification
14. Termination
15. Dispute Resolution and Arbitration
16. Governing Law and Venue
17. Changes to these Terms
18. Miscellaneous

## Key clauses relevant to NYRA's ToS clarification question

### "Subscriptions and Billing" (Pro / Max)

[paraphrased from live page 2026-04-24] — Describes the user's subscription
relationship with Anthropic (monthly / yearly billing, tier features, usage
limits). NYRA's email explicitly notes that NYRA does **not** insert itself
into this billing relationship — NYRA does not resell, rebate, proxy, or
meter the user's subscription. The user pays Anthropic directly.

### "Acceptable Use Policy binding"

[paraphrased from live page 2026-04-24] — Users of Pro / Max agree to
comply with Anthropic's current Acceptable Use Policy. NYRA's email
confirms NYRA displays / links Anthropic's AUP to users during onboarding
(Phase 0 Plan 05 brand-guideline archive covers the exact placement), so
the user is on notice that their use of Claude via NYRA remains bound by
the AUP.

### "Account Registration and Security"

[paraphrased from live page 2026-04-24] — Users are responsible for keeping
their account credentials secure; Anthropic may suspend accounts that are
compromised or shared. NYRA's architecture supports this obligation: the
OAuth token lives in the user's own `~/.claude/.credentials.json`, issued
by the user's own interactive `claude setup-token` run on their own
machine. NYRA never sees the token, never caches it, never transmits it
across a network, and never persists it anywhere NYRA controls.

### "Restrictions"

[paraphrased from live page 2026-04-24] — The consumer Restrictions
section parallels the Commercial Restrictions section: no reverse-
engineering, no training-competing-model use of Outputs, no circumvention
of technical measures, no resale / repackaging without permission. NYRA's
email affirms that subprocess-driving the user's own CLI with the user's
own credentials does not fall under any of these prohibitions, and asks
Anthropic to confirm the reading.

### "Changes to these Terms"

[paraphrased from live page 2026-04-24] — Anthropic may update the
Consumer Terms; continued use after an update constitutes acceptance. This
is precisely why this snapshot is date-stamped: NYRA's Phase 0 clearance
will be verdict-tied to the 2026-04-24 text, and Phase 8 (Fab Launch Prep)
will re-snapshot immediately before listing submission to detect any
changes that would require a renewed clarification.

## Where NYRA's subprocess pattern fits this document

The email frames NYRA's position under the Consumer Terms as follows:

- **The user is the sole Party** to the Consumer Terms. NYRA is not a
  party.
- **The user's subscription drives their own Claude CLI** — the user ran
  `claude setup-token` interactively on their own machine to mint the
  OAuth token; NYRA never sees this step. NYRA is a subprocess parent
  that reads stdout from a process the user authenticated.
- **NYRA does not offer, re-sell, or proxy access** to claude.ai or the
  Claude API. NYRA also does not offer Claude-branded login. The
  Claude-branded login is `claude setup-token` as provided by Anthropic
  itself, run by the user.
- **NYRA is free** — no billing flow exists, so there is no question of
  NYRA monetising the user's Anthropic subscription.

## Full text reference

The committed version of this snapshot intentionally omits the full
verbatim body (copyright + evolving text). The authoritative full text
lives at:

- https://www.anthropic.com/legal/consumer-terms

If the email response cites a specific section of the live document, that
section will be quoted verbatim in
`correspondence/00-01-anthropic-tos-email-response.md` when the reply
arrives.

---

*Snapshot authored for NYRA Phase 0 SC#1 legal gate — 2026-04-24.*
