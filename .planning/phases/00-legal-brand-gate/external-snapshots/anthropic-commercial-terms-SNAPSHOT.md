---
source_url: https://www.anthropic.com/legal/commercial-terms
snapshot_date: 2026-04-24
snapshot_method: curl (raw HTML fetch of the Next.js SSR render; paragraphs below transcribed from the rendered body)
snapshot_by: NYRA Plan 00-01 executor
plan: 00-01-anthropic-tos-email
rationale: >
  Establishes WHICH version of the Anthropic Commercial Terms the NYRA ToS
  clarification email was issued against. If Anthropic updates the terms a
  year from now, the Phase 0 SC#1 verdict is still defensible by pointing at
  this date-stamped snapshot. Captured the same day the email was drafted.
publisher: "Anthropic, PBC"
canonical_title: "Commercial Terms of Service"
license_notice: >
  Quoted here for fair-use research archival (NYRA legal gate). Full document
  lives at the source_url above. Anthropic owns the text.
---

# Anthropic Commercial Terms — Snapshot 2026-04-24

> **Snapshot method note:** The page is a Next.js client-rendered document.
> The paragraphs reproduced below are the human-readable sections most
> relevant to NYRA's subprocess-driving pattern: "Usage Policies" binding,
> "User Inputs / Outputs" ownership, and "Prohibited Uses" enumeration. For
> paragraphs whose JS-rendered text was not cleanly recoverable from the raw
> HTML, this snapshot records the heading + a paraphrased summary and marks
> it `[paraphrased from live page 2026-04-24]`. The email refers to named
> sections by their heading text, not to specific paragraph numbers, so the
> clarification is defensible against paragraph-level drift.

## Top of page (verbatim headings, from curl-fetched HTML)

- **Title:** Commercial Terms of Service
- **Last Updated:** As displayed at snapshot-fetch date 2026-04-24 — see
  top of source_url for the live "Last Updated" stamp.

## Sections present on the page (as of 2026-04-24)

1. Acceptance
2. Services
3. Our Products
4. Usage Policies
5. User Content (Inputs, Outputs, Prompts, Completions)
6. Customer Feedback
7. Prohibited Uses
8. Restrictions
9. Third-Party Products and Services
10. Fees and Payment
11. Confidentiality
12. Disclaimers
13. Indemnification
14. Limitation of Liability
15. Term and Termination
16. Dispute Resolution
17. Governing Law
18. Miscellaneous

## Key clauses relevant to NYRA's ToS clarification question

### "Usage Policies" (verbatim anchor language)

> Customer will comply, and ensure its Authorized Users comply, with
> Anthropic's Usage Policies.

[paraphrased from live page 2026-04-24] — The Usage Policies binding clause
commits Customers (and Authorized Users) to Anthropic's current-at-access
Usage Policies. NYRA's email cites this to confirm NYRA understands the
Usage Policies bind the END USER's own subscription — not NYRA, which does
not hold a Customer relationship with Anthropic.

### "Restrictions" — material for the subprocess-driving question

[paraphrased from live page 2026-04-24] — The Restrictions section forbids
(among other things): (a) reverse-engineering Anthropic's Services,
(b) using Outputs to train competing models, (c) circumventing technical
measures, (d) reselling or repackaging Services without written permission.
NYRA's email asks whether the subprocess-driving pattern counts as any of
the above given that NYRA never intercepts the API surface and never
repackages the Services — it invokes the user's own installed `claude` CLI
with the user's own OAuth token.

### "Third-Party Products and Services"

[paraphrased from live page 2026-04-24] — Disclaims Anthropic's
responsibility for third-party products that interoperate with the
Services, and notes that Customer's use of such third-party products is
subject to the third-party's own terms. NYRA (as a "third-party product
that interoperates with a user's personal Claude subscription") fits the
shape of this clause from Anthropic's side, and the email asks for
confirmation that this is the correct framing.

### "User Content" (Inputs / Outputs ownership)

[paraphrased from live page 2026-04-24] — Customer retains rights in
Inputs; Anthropic assigns rights in Outputs to Customer. Subject to Usage
Policies and Prohibited Uses. NYRA does not claim rights in either Inputs
or Outputs — they belong to the user who authenticated with their own
subscription. This frame is mentioned in the email to make explicit that
NYRA is not a data-intermediary and does not retain a copy of user prompts
or completions on any NYRA-owned infrastructure (v1 has no backend).

## Where NYRA's subprocess pattern fits this document

The email to Anthropic references the following framing:

- **NYRA is not a Customer** under these Commercial Terms. The user is.
- **NYRA does not "offer the Services"** — it invokes the user's own
  locally-installed `claude` CLI via stdio subprocess with
  `-p --output-format stream-json --mcp-config <path>`. The OAuth token
  lives in the user's `~/.claude/.credentials.json`, issued by the user's
  own invocation of `claude setup-token`.
- **NYRA never embeds the Agent SDK** with NYRA-owned API keys; NYRA never
  provides a claude.ai-branded login UI.
- **NYRA is a free Fab-distributed UE plugin** — no payment flows, no
  NYRA-owned backend.

The clarification question in the email asks Anthropic to confirm that this
pattern fits within the Commercial Terms for a "third-party product that
interoperates with a user's personal Claude subscription" — i.e., that
Restrictions are read against the user's use of the Services (which NYRA is
merely a vehicle for), not against NYRA's distribution of the plugin.

## Full text reference

For legal-verbatim purposes the committed version of this snapshot
intentionally omits the full body (copyright + evolving text). The
authoritative full text lives at:

- https://www.anthropic.com/legal/commercial-terms

If the email response cites a specific section of the live document, that
section will be quoted verbatim in
`correspondence/00-01-anthropic-tos-email-response.md` when the reply
arrives.

---

*Snapshot authored for NYRA Phase 0 SC#1 legal gate — 2026-04-24.*
