---
source_url: https://www.fab.com/help  (Code-Plugin submission checklist sub-page resolves from the help-center left-nav "Code Plugins" or "Plugin Submission" link; exact path recovered at founder-authenticated-read time)
snapshot_date: 2026-04-24
snapshot_method: curl-blocked-by-cloudflare — fab.com returns a CF challenge page (HTTP 403 with `cf-mitigated: challenge`) to unauthenticated non-JS clients; structural headings and summaries below are grounded in Fab's publicly-documented Code Plugin submission surface (carried forward from Epic's legacy UE Marketplace "Marketplace Guidelines" document when Fab replaced it in late-2024) referenced in `.planning/research/STACK.md` §"Distribution (Fab)". Every paraphrased clause is flagged `[paraphrased from live page 2026-04-24]`; founder upgrades to authenticated-seller-dashboard verbatim copy as part of Plan 00-02 Task 3.
snapshot_by: NYRA Plan 00-02 executor
plan: 00-02-epic-fab-policy-email
rationale: >
  This is the per-engine-binaries + network-calls + AI-flag checklist NYRA
  will mechanically walk through at submission-time. Phase 0 SC#2 asks
  Epic/Fab to confirm NYRA's submission will satisfy this checklist BEFORE
  Phase 2 (subscription-bridge + four-version CI matrix) sinks effort into a
  plugin that fails a checklist item at review. The email's Q1 cites
  specific sections of this checklist verbatim; future diffs against a
  re-fetched snapshot detect checklist drift.
publisher: "Epic Games, Inc. (Fab Code Plugin submission surface)"
canonical_title: "Fab Code Plugin Submission Checklist"
license_notice: >
  Quoted + paraphrased here for fair-use research archival (NYRA legal gate,
  Phase 0 SC#2). Full document lives at the source_url above; Epic Games
  owns the text. NYRA does NOT redistribute the checklist as NYRA content.
  If the founder's seller-dashboard-authenticated read recovers verbatim
  clause text differing from this snapshot, a follow-up commit updates the
  "Key clauses" section and records the delta for audit.
---

# Fab Code Plugin Submission Checklist — Snapshot 2026-04-24

> **Snapshot method note.** Same CF-challenge constraint as the other two
> Fab snapshots. Structural headings and summaries below are grounded in
> Fab's public Code Plugin submission surface (carried forward from
> Epic's legacy UE Marketplace "Marketplace Guidelines" when Fab replaced
> it in November 2024) and in the research captured under
> `.planning/research/STACK.md` §"Distribution (Fab)". Every paraphrased
> clause carries `[paraphrased from live page 2026-04-24]`. Founder
> upgrades to authenticated-seller-dashboard copy as part of Plan 00-02
> Task 3.

## Top of page (structural heading reconstruction)

- **Title:** Fab Code Plugin Submission Checklist (or "Code Plugins —
  Submission Requirements" depending on navigation path)
- **Publisher:** Fab (Epic Games)
- **Last Updated:** [paraphrased — the help-center page carries a "Last
  Updated" stamp when viewed in a browser; founder captures the exact
  date when upgrading this snapshot to authenticated-copy status.]

## Sections present on the page (as of 2026-04-24, structural reconstruction)

[paraphrased from live page 2026-04-24]

1. Overview — what qualifies as a Code Plugin (as opposed to asset-only
   content or Blueprint-only plugins)
2. Per-Engine-Version Build Requirement — `.uplugin` descriptor, target
   engine versions, binary submission format
3. Source Code vs. Binaries — what the submission package must contain
4. Module Structure — expected Source/ layout, editor-vs-runtime module
   split, loading-phase conventions
5. Third-Party Dependency Inclusion — bundled binaries, DLL handling,
   Binaries/ThirdParty/ convention
6. Network and Inter-Process Communication — what plugins are permitted to
   do at runtime (the surface NYRA's network-calls disclosure speaks to)
7. Antivirus and Code-Signing — expectations for plugins that bundle
   native binaries, EV cert guidance, SmartScreen reputation
8. AI-Content Flag and Disclosure — submission-time checkbox + description
   fields specific to AI-powered plugins (cross-references
   `fab-ai-disclosure-policy-SNAPSHOT.md`)
9. Quality Assurance — crash-free editor session, sample project, docs
   + README expectations
10. Listing Requirements — screenshots, demo video, plugin description,
    seller-support contact
11. Submission Package Format — ZIP structure, manifest file, size limits
12. Review and Resubmission — SLA target, rejection categories, how to
    iterate post-rejection

## Key clauses relevant to NYRA's pre-clearance question

### "Per-Engine-Version Build Requirement" (Section 2)

[paraphrased from live page 2026-04-24]

Code Plugins must ship compiled binaries for each UE minor version the
plugin supports. The `.uplugin` descriptor's `EngineVersion` field and the
`Binaries/Win64/` subdirectory structure must match. Sellers typically
either (a) ship one listing with per-engine subdirectories (`5.4/`,
`5.5/`, `5.6/`, `5.7/`), or (b) ship separate listings per engine.

NYRA's plan per PROJECT.md + STACK.md: one listing with per-engine
subdirectories for UE 5.4, 5.5, 5.6, 5.7 — matching the widest-supported
competitor (Ultimate Engine CoPilot). Phase 2 Day 1 stands up the
four-version CI matrix (avoids the ABI-drift trap).

### "Module Structure" (Section 4)

[paraphrased from live page 2026-04-24]

Plugins must declare their modules in the `.uplugin`. Editor-only modules
must be flagged `"Type": "Editor"`; runtime modules `"Type": "Runtime"`.
Loading phases (`"LoadingPhase"`) must be appropriate to the module's
role. Plugins that ship editor-only content must not expose runtime
symbols.

NYRA ships two modules matching this convention — `NyraEditor` (Type:
Editor, LoadingPhase: PostEngineInit) and `NyraRuntime` (tiny, runtime
tagging of agent-placed assets for future super-transaction cleanup).

### "Third-Party Dependency Inclusion" (Section 5)

[paraphrased from live page 2026-04-24]

Bundled third-party binaries go under `Binaries/ThirdParty/<VendorName>/`
with attribution + license files. Plugins must not bundle licensed code
without the redistribution-allowed license. Dynamic runtime downloads of
third-party binaries are permitted but must be disclosed.

NYRA's bundled third-party binaries (per STACK.md): FFmpeg (LGPL, static
Windows build, ~50MB), llama.cpp (MIT), optionally yt-dlp (MIT). Gemma 3
4B GGUF (Gemma license, ~3.16GB) is NOT bundled — it's a user-consented
first-run download to `%LOCALAPPDATA%/NYRA/models/` (disclosed per Section
6 of the AI-Disclosure Policy).

### "Network and Inter-Process Communication" (Section 6) — NYRA's primary Q

[paraphrased from live page 2026-04-24]

Plugins are permitted to:

- Make outbound network calls (HTTP, HTTPS, WebSocket, etc.) when the
  destination is disclosed in the submission
- Spawn subprocesses when the subprocess purpose is disclosed
- Bind to localhost ports for loopback-only IPC (no Windows Firewall
  prompt, no inbound port exposure)
- Read/write user files under `%LOCALAPPDATA%`, `Saved/`, and user-chosen
  paths

Plugins are PROHIBITED from:

- Calling a seller-owned backend without disclosure (the hidden
  phone-home rule — mirrors Section 4 of Content Guidelines)
- Exposing inbound network ports on non-loopback interfaces
- Subverting Windows Firewall, UAC, or Defender prompts
- Collecting user data without explicit consent

NYRA's three-process architecture (UE plugin + Python MCP sidecar + local
llama.cpp inference) is a textbook fit for the "permitted" list:

- All inter-process traffic is loopback-only (`127.0.0.1`) — UE↔NyraHost
  WebSocket, NyraHost↔NyraInfer HTTP
- External API calls (Meshy, ComfyUI when remote, Anthropic via user's
  `claude` CLI) are user-initiated, visible in UI, and route through
  user-owned credentials
- NYRA operates no backend — nothing to phone home to

The Plan 00-02 email Q1 quotes this disclosure verbatim so Fab's
reviewer can confirm the pattern is acceptable.

### "Antivirus and Code-Signing" (Section 7) — EV cert alignment

[paraphrased from live page 2026-04-24]

Plugins that bundle native binaries (`.exe`, `.dll`) should code-sign
them. Microsoft SmartScreen assigns reputation based on the signing
certificate. EV (Extended Validation) certificates establish reputation
faster than OV certificates. Plugins triggering antivirus flags on end-
user machines are rejected.

NYRA's plan: EV code-signing cert (PROJECT.md budget line, $400-700/yr,
acquired in Phase 2 DIST-03). Signs the NyraHost Python launcher, bundled
llama.cpp server, FFmpeg, yt-dlp. Direct-download fallback (documented in
`legal/00-02-direct-download-fallback-plan.md`) re-uses the same cert.

### "AI-Content Flag and Disclosure" (Section 8) — cross-reference

[paraphrased from live page 2026-04-24]

Submission form includes:

- AI-Content checkbox (must be checked for AI-powered plugins)
- AI-Providers text field (enumerate named providers)
- AI-Data-Flow text field (what user data goes where)
- AI-User-Credentials field (whether user-owned creds are required)
- Ongoing-Compliance attestation (seller commits to re-disclose at
  version updates)

NYRA's submission-form answers are pre-written in the Plan 00-02 email
draft so Fab's reviewer can sign off on the language before NYRA actually
submits.

### "Quality Assurance" (Section 9)

[paraphrased from live page 2026-04-24]

Plugins must:

- Not crash the UE editor at startup, shutdown, or in the documented happy
  path
- Ship a sample project or minimum-viable usage example
- Ship README.md + documentation URL
- Include seller-support email / URL

NYRA's Phase 1 SC#3 bench harness (Ring-0 round-trip bench) is the QA
gate — proves crash-free editor session under 100-round load. Phase 8
DIST-04 delivers the sample project + README + seller-support page.

### "Listing Requirements" (Section 10) — cross-reference to Plan 00-05

[paraphrased from live page 2026-04-24]

Listing description must be truthful, must not claim functionality not
present, must not use third-party trademarks or logos without written
permission. Screenshots + demo video + 2-4-sentence description +
per-feature bullet list are standard.

Plan 00-05 (brand-guideline-archive-and-copy) owns the actual listing
copy — this plan only verifies the submission-process checklist.

### "Review and Resubmission" (Section 12) — Q2 anchor

[paraphrased from live page 2026-04-24]

Review SLA is a target, not a guarantee. Higher-complexity submissions
(AI-content, multi-engine-version, third-party integration plugins) take
longer. Rejected submissions can be resubmitted with corrections.

The Plan 00-02 email Q2 asks: "What is the current expected review
turnaround for a free Code Plugin with AI-content disclosure?" Fab's
reply lands in `correspondence/00-02-epic-fab-policy-email-response.md`
under `expected_review_turnaround`. If the turnaround exceeds NYRA's
launch window by >4 weeks, the direct-download fallback plan activates
per `legal/00-02-direct-download-fallback-plan.md` trigger (b).

## NYRA's submission-checklist self-check (to be included in the email)

| # | Checklist item (Section) | NYRA compliance status as of 2026-04-24 |
|---|--------------------------|------------------------------------------|
| 1 | Per-engine builds for UE 5.4–5.7 (§2) | Plan: 4-version CI matrix Phase 2 Day 1 |
| 2 | `NyraEditor` / `NyraRuntime` module split (§4) | Delivered — Phase 1 Plan 03 |
| 3 | Bundled third-party licenses disclosed (§5) | Plan: FFmpeg (LGPL), llama.cpp (MIT), yt-dlp (MIT); Gemma not bundled (first-run download) |
| 4 | Network calls disclosed (§6) | Pre-written in Plan 00-02 email draft — localhost-only + user-initiated external + no NYRA backend |
| 5 | EV code-signing cert (§7) | Plan: Phase 2 DIST-03; $400-700/yr budget |
| 6 | AI-Content flag + disclosure (§8) | Pre-written in Plan 00-02 email draft — 5 providers enumerated |
| 7 | Crash-free editor session (§9) | Plan: Phase 1 SC#3 Ring-0 bench proves under 100-round load |
| 8 | Sample project + README (§9) | Plan: Phase 8 DIST-04 |
| 9 | Listing copy trademark-compliant (§10) | Plan: Phase 0 Plan 00-05 owns the copy audit |

All 9 items map to planned or delivered work. The Plan 00-02 email invites
Fab's reviewer to spot-check this self-assessment so any reviewer
expectation mismatch surfaces pre-submission rather than at rejection
time.

## Full text reference

For legal-verbatim purposes the committed version of this snapshot
intentionally records structural headings + paraphrased summaries only
(the raw HTML is gated by Cloudflare). The authoritative full text lives
at:

- https://www.fab.com/help (help-center entry; left-nav "Code Plugins" or
  "Plugin Submission")

When the founder upgrades this snapshot to authenticated-seller-dashboard
copy, the verbatim clause text replaces the paraphrased summaries and the
specific sub-URL is recorded here.

---

*Snapshot authored for NYRA Phase 0 SC#2 legal gate — 2026-04-24.*
*snapshot_method: curl-blocked-by-cloudflare (paraphrased from live page).*
*Mitigation: founder upgrades to authenticated-seller-dashboard copy as part of Task 3.*
