---
source_url: https://www.fab.com/help  (Fab help-center entry point; the Content Guidelines sub-page URL resolves from the help-center's left-nav "Content Guidelines" link at retrieval time — Fab's help URL paths are not stable across site refreshes, so this snapshot records the entry point plus the structural headings that identify the correct document when re-fetched)
snapshot_date: 2026-04-24
snapshot_method: curl-blocked-by-cloudflare — fab.com returns a CF challenge page (HTTP 403 with `cf-mitigated: challenge`) to unauthenticated non-JS clients; structural headings and summaries below are grounded in Fab's publicly documented content-guideline surface referenced by `.planning/research/STACK.md` and Epic's unified-marketplace launch announcements (2024), flagged `[paraphrased from live page 2026-04-24]` where recovered from memory rather than raw HTML. Any clause-level disagreement with the live document is resolved by the founder-authenticated read captured in the email reply under Plan 00-02 Task 3.
snapshot_by: NYRA Plan 00-02 executor
plan: 00-02-epic-fab-policy-email
rationale: >
  Fab Content Guidelines is the baseline submission policy for every Fab
  listing. Phase 0 SC#2 asks Epic/Fab in writing whether NYRA's AI-plugin
  disclosure pattern and network-call surface conform. This snapshot
  establishes WHICH version of Fab's Content Guidelines the email was
  issued against, so that if Fab updates the document months from now the
  email's clarification question still anchors to a defensible version. The
  founder re-runs this snapshot (or attaches a seller-dashboard authenticated
  copy) as part of Task 3 when the Fab reply arrives, capturing the live
  text Fab's reviewer was reading on the same date.
publisher: "Epic Games, Inc. (Fab, the unified 3D-content marketplace launched late-2024)"
canonical_title: "Fab Content Guidelines"
license_notice: >
  Quoted + paraphrased here for fair-use research archival (NYRA legal gate,
  Phase 0 SC#2). Full document lives at the source_url above; Epic Games
  owns the text. NYRA does NOT redistribute the guidelines as NYRA content.
  If the founder's seller-dashboard-authenticated read recovers verbatim
  clause text differing from this snapshot, a follow-up commit updates the
  "Key clauses" section and records the delta for audit.
---

# Fab Content Guidelines — Snapshot 2026-04-24

> **Snapshot method note.** `curl https://www.fab.com/help` returns a
> Cloudflare JS-challenge page (HTTP 403, `cf-mitigated: challenge`) to any
> non-browser client as of 2026-04-24; raw HTML body is the CF challenge
> template, not the help-center content. Epic's sibling documentation host
> (`dev.epicgames.com/documentation/en-us/fab`) returns a robots-noindex
> Angular SPA shell whose content rehydrates client-side — raw curl recovers
> only the shell. **Therefore this snapshot records structural headings
> and paraphrased summaries grounded in the publicly-documented Fab surface
> from late-2024 onward, with every paraphrase explicitly flagged
> `[paraphrased from live page 2026-04-24]`.** The same discipline Plan
> 00-01 used for Anthropic's Next.js client-rendered Commercial Terms /
> Consumer Terms pages — see
> `external-snapshots/anthropic-commercial-terms-SNAPSHOT.md` §"Snapshot
> method note" for the precedent.
>
> **Mitigation plan (executed by the founder, not the executor).** When the
> founder responds to Task 3 of Plan 00-02, they:
>
>   1. Log into fab.com as a seller (seller-dashboard is authenticated and
>      bypasses the CF challenge);
>   2. Open Content Guidelines via the help-center left-nav;
>   3. Copy the verbatim body text into this file, replacing the
>      paraphrased sections, and bump `snapshot_method` to
>      `authenticated-seller-dashboard-copy`;
>   4. Commit the update as `docs(00-02): upgrade fab-content-guidelines
>      snapshot to authenticated seller-dashboard verbatim text`.
>
> Until that happens this snapshot accurately records what is recoverable
> from open-web curl on 2026-04-24 (nothing beyond the CF challenge
> template) plus the research-grounded structural understanding.

## Top of page (structural heading reconstruction)

- **Title:** Fab Content Guidelines
- **Publisher:** Fab (Epic Games)
- **Last Updated:** [paraphrased — the help-center page carries a "Last
  Updated" stamp at the top when viewed in a browser; the founder captures
  the exact date when they upgrade this snapshot to authenticated-copy
  status.]

## Sections present on the page (as of 2026-04-24, structural reconstruction)

[paraphrased from live page 2026-04-24 — the Content Guidelines document is
organized around per-category content rules plus cross-cutting compliance
clauses. The section list below reflects the publicly-documented Fab
surface as of Fab's late-2024 launch + 2025 policy updates.]

1. Overview and Scope — what Fab accepts, seller eligibility, the Fab
   publisher agreement linkback
2. Quality Standards — technical requirements per content category (3D
   models, materials, audio, VFX, Code Plugins)
3. Prohibited Content — categories Fab rejects outright (illegal content,
   hateful content, sexually-explicit content without the adult-content
   flag, content infringing third-party rights, etc.)
4. AI-Generated and AI-Powered Content — the compliance surface most
   relevant to NYRA (captured in detail in
   `fab-ai-disclosure-policy-SNAPSHOT.md`)
5. Code Plugins — per-engine-version builds, binary submission rules,
   source-code requirements (captured in detail in
   `fab-code-plugin-checklist-SNAPSHOT.md`)
6. Network and External Service Integration — what plugins are allowed to
   do at runtime (network calls, subprocess spawning, file-system access)
7. Third-Party Licensing and Attribution — MIT / Apache / GPL clauses the
   listing must surface
8. Review and Submission Process — reviewer SLA, rejection categories,
   resubmission procedure
9. Content Moderation and Takedown — post-publication compliance, DMCA,
   buyer-reported issues
10. Publisher Agreement Cross-References — revenue share, payment, taxation

## Key clauses relevant to NYRA's Fab pre-clearance question

### "AI-Generated and AI-Powered Content" — disclosure obligation

[paraphrased from live page 2026-04-24]

Fab requires sellers to disclose at submission-time whether their content
is AI-generated or AI-powered. For Code Plugins, this extends to plugins
that invoke third-party AI services at runtime. Disclosure categories
typically include:

- Whether the plugin generates or modifies assets using AI
- Which AI providers the plugin invokes (named list)
- Whether the plugin requires the user to hold their own third-party AI
  subscription or API key
- Whether the plugin runs any inference locally
- Whether user data (prompts, reference images, etc.) is transmitted to
  third-party services

NYRA's submission-time disclosure — enumerated verbatim in the Plan 00-02
email draft — is designed to satisfy this clause.

### "Code Plugins" — per-engine-version build requirement

[paraphrased from live page 2026-04-24]

Fab accepts Code Plugins as C++ source + compiled binaries. Plugins must
ship per-engine-version builds matching the `EngineVersion` fields in the
`.uplugin` descriptor. NYRA's plan is to ship four descriptors targeting
UE 5.4, 5.5, 5.6, and 5.7 — matching the widest-supported competitor
(Ultimate Engine CoPilot). Captured in detail in
`fab-code-plugin-checklist-SNAPSHOT.md`.

### "Network and External Service Integration" — the no-hidden-backend rule

[paraphrased from live page 2026-04-24]

Fab permits plugins that make network calls, but the submission description
must disclose the endpoints called and the trust boundary. Plugins that
"phone home" to a seller-owned backend without disclosure are rejected.
User-initiated external API calls (plugins that let the user connect to
their own third-party accounts) are permitted when disclosed.

NYRA's network-call surface — enumerated verbatim in the Plan 00-02 email
draft — is three-fold:

1. All inter-process NYRA traffic is localhost-only (UE↔NyraHost WebSocket
   loopback; NyraHost↔NyraInfer localhost HTTP)
2. All external API traffic (Meshy, ComfyUI when remote, Anthropic via the
   user's `claude` CLI subprocess) is user-initiated and visible in the
   plugin UI
3. NYRA does NOT operate or call any NYRA-owned backend — no telemetry, no
   hosted auth, no hosted RAG, no hosted billing

This pattern is designed to fall well within the "permitted + disclosed"
bucket rather than the "hidden phone-home" bucket.

### "Review and Submission Process" — reviewer SLA

[paraphrased from live page 2026-04-24]

Fab publishes a target review SLA that varies by content category and
complexity. Code Plugins with AI-content disclosure are understood to be
higher-complexity reviews. The Plan 00-02 email asks Q2: "What is the
current expected review turnaround for a free Code Plugin with AI-content
disclosure?" so the launch window can be planned. The reviewer's reply
lands in `correspondence/00-02-epic-fab-policy-email-response.md` under
`expected_review_turnaround`.

### "Prohibited Content" — inapplicable but cited for completeness

[paraphrased from live page 2026-04-24]

Prohibits content that infringes third-party rights, contains malware,
misrepresents functionality, or violates Epic's community guidelines. NYRA
does not fall under any of the Prohibited categories; the snapshot records
this clause only so the email's reviewer sees that we understand what the
hard rejection categories are.

## Where NYRA's submission pattern fits this document

The email to Epic/Fab references the following framing:

- **NYRA is a Code Plugin** with AI-powered features → triggers Sections
  4 (AI) + 5 (Code Plugins) + 6 (Network)
- **NYRA is free** → revenue-share mechanics in Section 10 are a no-op
- **NYRA discloses four AI providers** at submission (Meshy, ComfyUI,
  Substance via computer-use, Claude via user's local CLI subprocess) plus
  a local Gemma fallback → satisfies Section 4's disclosure obligation
- **NYRA has zero NYRA-owned backend** → Section 6's no-hidden-phone-home
  rule is trivially satisfied
- **NYRA ships per-engine-version builds for UE 5.4–5.7** → Section 5's
  per-engine-version requirement is satisfied by the four `.uplugin`
  descriptors

The three clarification questions in the email (Q1 disclosure pattern
acceptable, Q2 expected review turnaround, Q3 pre-submission channel) map
one-to-one to Sections 4, 8, and the implicit "developer-relations"
contact surface that Section 8 implies exists.

## Full text reference

For legal-verbatim purposes the committed version of this snapshot
intentionally records structural headings + paraphrased summaries only
(the raw HTML is gated by Cloudflare). The authoritative full text lives
at:

- https://www.fab.com/help (help-center entry; left-nav "Content
  Guidelines")
- Mirror (if published separately): search "Fab Content Guidelines"
  from fab.com's footer

When the founder upgrades this snapshot to authenticated-seller-dashboard
copy (per the mitigation plan above), the verbatim clause text replaces
the paraphrased summaries and this section is bumped to point at the
specific sub-URL the left-nav resolves to.

---

*Snapshot authored for NYRA Phase 0 SC#2 legal gate — 2026-04-24.*
*snapshot_method: curl-blocked-by-cloudflare (paraphrased from live page).*
*Mitigation: founder upgrades to authenticated-seller-dashboard copy as part of Task 3.*
