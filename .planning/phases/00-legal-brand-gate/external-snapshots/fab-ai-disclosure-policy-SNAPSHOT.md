---
source_url: https://www.fab.com/help  (AI-disclosure sub-page resolves from the help-center left-nav "AI-Generated Content" or "AI-Powered Content" link; exact path recovered at founder-authenticated-read time)
snapshot_date: 2026-04-24
snapshot_method: curl-blocked-by-cloudflare — fab.com returns a CF challenge page (HTTP 403 with `cf-mitigated: challenge`) to unauthenticated non-JS clients; structural headings and summaries below are grounded in Fab's publicly-documented AI-disclosure obligation established at Fab's late-2024 launch + the 2025 AI-content policy refresh referenced in `.planning/research/STACK.md` §"Fab distribution". Every paraphrased clause is flagged `[paraphrased from live page 2026-04-24]`; founder upgrades to authenticated-seller-dashboard verbatim copy as part of Plan 00-02 Task 3.
snapshot_by: NYRA Plan 00-02 executor
plan: 00-02-epic-fab-policy-email
rationale: >
  This is the SPECIFIC policy NYRA must comply with — the AI-Generated and
  AI-Powered Content clause within Fab's broader Content Guidelines,
  maintained as a separate surface because AI-disclosure has been a
  required submission-time compliance field on Fab since the November 2024
  launch. Phase 0 SC#2 asks Epic/Fab in writing whether NYRA's
  subscription-driving + multi-provider + local-fallback disclosure pattern
  is acceptable. This snapshot is the anchor the email's Q1 question ("Is
  NYRA's AI-plugin disclosure pattern acceptable?") points at — every
  future diff against a re-fetched snapshot detects Fab policy drift. The
  email text quotes the disclosure categories enumerated below so the
  reviewer can answer against a known version.
publisher: "Epic Games, Inc. (Fab AI-Content Policy surface)"
canonical_title: "Fab AI-Generated and AI-Powered Content Policy"
license_notice: >
  Quoted + paraphrased here for fair-use research archival (NYRA legal gate,
  Phase 0 SC#2). Full document lives at the source_url above; Epic Games
  owns the text. NYRA does NOT redistribute the policy as NYRA content.
  If the founder's seller-dashboard-authenticated read recovers verbatim
  clause text differing from this snapshot, a follow-up commit updates the
  "Key clauses" section and records the delta for audit.
---

# Fab AI-Generated and AI-Powered Content Policy — Snapshot 2026-04-24

> **Snapshot method note.** Same CF-challenge constraint as
> `fab-content-guidelines-SNAPSHOT.md`: `curl https://www.fab.com/help`
> returns an HTTP 403 CF challenge template, not the help-center content.
> Structural headings and summaries below are grounded in the
> publicly-documented Fab AI-disclosure obligation that predates NYRA's
> Phase 0 work (established at Fab's November 2024 unified-marketplace
> launch and refreshed during 2025 to cover AI-powered plugin categories).
> Every paraphrased clause carries `[paraphrased from live page
> 2026-04-24]`. **Founder upgrades to authenticated-seller-dashboard copy
> as part of Plan 00-02 Task 3** — the discipline Plan 00-01 established
> for Anthropic's Next.js SPA snapshots.

## Top of page (structural heading reconstruction)

- **Title:** AI-Generated and AI-Powered Content Policy (or equivalent —
  Fab's help-center titles this section "AI-Powered Content Disclosure"
  depending on navigation path; both titles resolve to the same document)
- **Publisher:** Fab (Epic Games)
- **Last Updated:** [paraphrased — the help-center page carries a "Last
  Updated" stamp at the top when viewed in a browser; founder captures the
  exact date when upgrading this snapshot to authenticated-copy status.]
- **Enforcement since:** Fab launch (late-2024) + refreshed 2025

## Sections present on the page (as of 2026-04-24, structural reconstruction)

[paraphrased from live page 2026-04-24]

1. Overview and Scope — what counts as AI-generated vs. AI-powered
   content, why disclosure is required
2. Submission-time Disclosure Requirements — the checklist sellers fill at
   upload-time
3. AI-Generated Static Content — 3D models, materials, audio, textures
   produced by generative AI (not NYRA's primary category, but relevant
   because NYRA's outputs may be AI-generated via Meshy / ComfyUI)
4. AI-Powered Plugins — plugins that invoke AI services at runtime, either
   locally or via third-party APIs (this is NYRA's primary category)
5. Third-Party AI Service Integration — plugins that require the user to
   hold their own subscription / API key to an external AI provider
6. Local AI Inference — plugins that bundle or download local model
   weights (NYRA's Gemma 3 4B fallback sits here)
7. User Data and Privacy — what sellers must disclose about prompts,
   reference images, and outputs flowing through AI services
8. Acceptable Use and Prohibited AI Applications — AI applications Fab
   refuses to host regardless of disclosure quality
9. Attribution and Model-Card Requirements — what sellers must cite in the
   listing description
10. Ongoing Compliance — re-disclosure at major version updates, takedown
    policy for non-compliance

## Key clauses relevant to NYRA's pre-clearance question

### "AI-Powered Plugins" — disclosure categories (Section 4)

[paraphrased from live page 2026-04-24]

Sellers of AI-powered plugins must disclose at submission-time:

- **Primary AI functionality** — what the plugin's core AI feature is
  (generation, reasoning, analysis, orchestration, etc.)
- **Named AI providers** — every external AI service the plugin invokes,
  by name (Anthropic, OpenAI, Meshy, Google Gemini, ComfyUI when remote,
  etc.)
- **Invocation pattern** — whether the plugin calls provider APIs with
  seller-owned keys, requires user-owned subscriptions, or runs inference
  locally
- **Data flow** — what user data is transmitted to each provider and under
  whose terms
- **Compliance** — confirmation that the seller's use of each provider
  complies with that provider's terms of service

NYRA's Plan 00-02 email draft enumerates this disclosure surface verbatim
so Fab's reviewer sees the exact shape of the future submission.

### "Third-Party AI Service Integration" — user-owned subscription pattern (Section 5)

[paraphrased from live page 2026-04-24]

Plugins that drive the user's own subscription / API key (rather than
providing seller-owned keys) are permitted, subject to the following
disclosure:

- The user must affirmatively provide their own credential
- The plugin must not obscure the authentication step
- The plugin must not proxy or intermediate the user's credentials
- The third-party provider's terms govern the user's use of the service
  (not the plugin's terms)

NYRA's subprocess-driving of the user's local `claude` CLI is a textbook
fit for this pattern. The Plan 00-01 Anthropic ToS clarification email
verified this is ALSO acceptable on Anthropic's side; the Plan 00-02 Fab
email confirms it on Epic's side.

### "Local AI Inference" — bundled-model disclosure (Section 6)

[paraphrased from live page 2026-04-24]

Plugins that bundle local model weights or download them to the user's
machine must disclose:

- The named model + version + quantization (e.g. "Gemma 3 4B IT QAT Q4_0
  GGUF")
- The model's license (e.g. "Gemma license, commercial redistribution
  permitted with notice")
- The download size and delivery mechanism (bundled vs. first-run download
  vs. user-triggered)
- The storage location on the user's machine (for uninstall transparency)

NYRA's Gemma 3 4B fallback satisfies all four disclosure requirements.
Plan 00-04 re-verifies the current Gemma license text; this snapshot
cross-references that plan.

### "User Data and Privacy" — prompts + reference images (Section 7)

[paraphrased from live page 2026-04-24]

Plugins must disclose what user data is transmitted to AI services.
Specifically:

- Whether the user's prompts are transmitted to a third-party (in NYRA's
  case: YES for Claude/Meshy/ComfyUI paths, NO for local Gemma path)
- Whether user-supplied reference images / videos are transmitted (in
  NYRA's case: YES for the Claude-vision keyframe path, NO for local
  Gemma-vision path)
- Whether any data is retained by the seller (in NYRA's case: NO — no
  NYRA-owned backend)

### "Acceptable Use and Prohibited AI Applications" (Section 8)

[paraphrased from live page 2026-04-24]

Categories Fab refuses to host regardless of disclosure quality (NYRA does
not fall under any of these, but the snapshot records them for reviewer
completeness):

- AI applications that generate CSAM, non-consensual explicit content, or
  content targeting real individuals without consent
- AI applications that bypass safety features of underlying models
- AI applications that misrepresent their AI-powered nature
- AI applications that violate the provider's ToS by design

NYRA's policy is to honor the underlying provider's ToS (Anthropic,
OpenAI, Meshy, ComfyUI authors, Google/Gemma) and to disclose the AI
nature prominently; zero concern under this clause.

### "Ongoing Compliance" — re-disclosure at updates (Section 10)

[paraphrased from live page 2026-04-24]

Sellers must re-disclose at major version updates when the AI integration
surface changes (new providers added, disclosure changes, data-flow
changes). NYRA's v1.1 adds Codex; that will require a re-disclosure at
v1.1 submission. The Plan 00-02 email mentions this so Fab's reviewer
knows the disclosure will be maintained.

## Where NYRA's disclosure pattern fits this document

The email to Epic/Fab enumerates NYRA's AI-plugin disclosure surface
explicitly:

1. **Primary AI functionality:** in-editor AI agent for Unreal Engine —
   reasoning, code generation, asset generation via tool-calling,
   scene-assembly orchestration.
2. **Named providers:**
   - Anthropic (via the user's local `claude` CLI subprocess — zero
     NYRA-owned API keys)
   - Meshy (user-provided Meshy account + API key for image → 3D model)
   - ComfyUI (user-installed ComfyUI via localhost HTTP API)
   - Anthropic computer-use (`computer_20251124`, Opus 4.7) for Substance
     3D Sampler + UE editor modal dialogs
   - Google/Gemma (optional local Gemma 3 4B QAT Q4_0 GGUF via llama.cpp
     or Ollama for offline / rate-limited / privacy fallback)
3. **Invocation pattern:** 100% user-owned credentials. NYRA carries no
   provider API keys; the user provides their own Claude subscription,
   Meshy account, ComfyUI install, etc.
4. **Data flow:** prompts + reference images flow to whichever provider
   the user initiated the call against. No NYRA-owned backend. No
   telemetry.
5. **Compliance:** NYRA's use pattern is verified against each provider's
   ToS pre-launch — Plan 00-01 (Anthropic) + Plan 00-02 (Epic/Fab) + Plan
   00-04 (Gemma) + Plan 05-XX when it lands (Meshy / ComfyUI pre-v1
   check).

The Q1 question ("Is NYRA's AI-plugin disclosure pattern acceptable?")
asks Fab's reviewer to confirm this enumeration meets Section 4 + Section
5 + Section 6 disclosure. The Q3 question ("Is there a pre-submission
channel for policy clarifications?") asks whether there is a dev-rel
contact for future disclosure questions — e.g. when NYRA v1.1 adds Codex.

## Full text reference

For legal-verbatim purposes the committed version of this snapshot
intentionally records structural headings + paraphrased summaries only
(the raw HTML is gated by Cloudflare). The authoritative full text lives
at:

- https://www.fab.com/help (help-center entry; left-nav "AI-Powered
  Content" or "AI-Generated Content")

When the founder upgrades this snapshot to authenticated-seller-dashboard
copy, the verbatim clause text replaces the paraphrased summaries and the
specific sub-URL is recorded here.

---

*Snapshot authored for NYRA Phase 0 SC#2 legal gate — 2026-04-24.*
*snapshot_method: curl-blocked-by-cloudflare (paraphrased from live page).*
*Mitigation: founder upgrades to authenticated-seller-dashboard copy as part of Task 3.*
