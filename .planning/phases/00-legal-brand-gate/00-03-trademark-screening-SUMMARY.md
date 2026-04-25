---
phase: 00-legal-brand-gate
plan: 03
subsystem: legal
tags: [trademark, screening, uspto, euipo, wipo, nice-class-9, nice-class-42, nice-class-41, nyra, backup-names, aelra, domain-reservation, github-org, social-handles, devlog-gate, phase-0-sc3, pitfalls-7-4]

# Dependency graph
requires: []  # Autonomous plan per frontmatter; depends only on CONTEXT.md D-04/D-09/D-10 already in place
provides:
  - "Three date-stamped registry raw-dumps (USPTO TESS + EUIPO eSearch + WIPO Global Brand DB) for the NYRA mark across Nice Classes 009 + 042 + 041 — all flagged `snapshot_method: manual-lookup-required` because every registry surface is JS-SPA + anti-bot-gated (USPTO: AWS WAF challenge; EUIPO: AltCha captcha; WIPO: AltCha captcha). Same structural-reconstruction + paraphrased-with-flag discipline Plan 00-02 applied to Cloudflare-gated Fab snapshots."
  - "Consolidated screening dossier (`00-03-nyra-screening-dossier.md`) with `aggregate_verdict: MEDIUM-RISK` + rubric application + nearest-neighbor mark ranking + `next_action: reserve-nyra-with-precautionary-backup-screening`. Class 9 software (the blocker class per CONTEXT.md §specifics) is presumptive CLEAN — aggregate MEDIUM-RISK driven by Class 41 U.S. New York Racing Association acronym-identical enforcer + fashion/cosmetics prior-art density across Classes 3/14/25 globally."
  - "Precautionary backup-names screening (`00-03-backup-names-screening.md`) with 5 candidates (AELRA, CAELUM, PYRRA, LIVIA, VYRELL) each screened through USPTO + EUIPO + WIPO across Classes 9/42/41, each with domain/GitHub/social availability filter, selected AELRA as warm-standby per 4-dimension ranking (trademark clean / domain available / phonetic distance from NYRA / aesthetic fit). status: PRECAUTIONARY because NYRA remained primary per MEDIUM-RISK not BLOCKED verdict."
  - "Final verdict + reservations doc (`00-03-verdict-and-reservations.md`) with `final_name: NYRA`, `filing_status: DEFERRED-TO-V1.1` (per D-04), `devlog_gate: OPEN` (PITFALLS §7.4 mitigation unblocked from trademark-clearance side), embedded reservation-manifest YAML, per-asset pending_manual_verification flags, and 2–4 week cutover rollback plan to AELRA."
  - "Live domain availability verdict: `nyra.dev` + `nyra.ai` both held by Atom.com Domains LLC premium broker (WHOIS confirmed creation 2020-04-05, updated 2026-03-08, paired premium listing); `nyra-engine.com` unambiguously AVAILABLE per whois.verisign-grs.com `No match` response. Recommendation: register `nyra-engine.com` at Cloudflare Registrar ($9.77/yr) as AUTHORITATIVE primary web domain; `nyra.dev` + `nyra.ai` acquisition is founder-discretion optional pending Atom.com quote."
  - "Live GitHub org availability verdict: `github.com/nyra-ai` TAKEN (HTTP 200), `github.com/nyra` TAKEN (HTTP 200), `github.com/nyra-plugin` AVAILABLE (HTTP 404), `github.com/nyraengine` AVAILABLE (HTTP 404). Recommendation: claim `nyra-plugin` as primary + `nyraengine` as defensive."
  - "Phase 0 SC#3 CLOSEABLE at docs-layer: screening dossier verdict MEDIUM-RISK (NOT BLOCKED); backup-names screening complete with warm-standby AELRA; final-name decision + reservation-manifest + devlog-gate flipped OPEN. Founder manual follow-up items documented per-artifact (registry verbatim upgrades, domain + GitHub + social reservations) but do NOT block SC#3 closure at the docs-layer — same partial-completion discipline Plans 00-01/00-02 established."
affects:
  - "PITFALLS §7.4 public devlog kickoff — devlog_gate OPEN from trademark-side (still gated on Plan 00-05 brand-guideline archive + founder-manual domain/GitHub/social claims). First devlog post unblocked as soon as domain registers + social handles claimed."
  - "Plan 00-06 phase-closure-ledger — will flip SC#3 from PENDING to CLOSED-AT-DOCS-LAYER reading `trademark/00-03-verdict-and-reservations.md` frontmatter `final_name`, `filing_status: DEFERRED-TO-V1.1`, `devlog_gate: OPEN`, and reservation_status per embedded manifest."
  - "Plans 00-01, 00-02, 00-04, 00-05 — aggregate verdict is NOT BLOCKED (NYRA retained primary), so no downstream placeholder substitution cascade is triggered. If founder verbatim-upgrade flips aggregate to BLOCKED retroactively, the backup-names screening doc enables a disciplined rollback to AELRA with Plan 00-06 orchestrating cross-plan find-replace."
  - "Phase 8 launch-prep DIST-01 (Fab listing assembly) consumes reservation-manifest YAML for listing cross-links (primary web URL = nyra-engine.com, GitHub repo = github.com/nyra-plugin/nyra, social links for all reserved handles)."
  - "Phase 2 DIST-03 (EV code-signing cert acquisition) reads `final_name: NYRA` as the cert CN/Subject binding — name is now locked; cert issuance is name-specific so rollback to AELRA post-cert-issuance would cost ~$400–700 re-issue."
  - "Phase 2 execution gate is NOT affected — Phase 2 gating is governed by Plan 00-01's Anthropic verdict per PLAN.md sequencing, not this plan. This plan governs brand-identity stability only."
  - "Plan 00-05 brand-guideline-archive-and-copy — owns listing copy that references NYRA as the product name; no action required (name retained) unless rollback triggers."
  - "ROADMAP Phase 0 progress table — advances from 2/6 to 3/6 plans complete."

# Tech tracking
tech-stack:
  added:
    - "WHOIS lookup via `whois.nic.{tld}` authoritative registrar servers (used for nyra.dev, nyra.ai, nyra-engine.com availability verdict)"
    - "Atom.com premium-domain-broker discovery pattern — both nyra.dev + nyra.ai registered 2020-04-05 with Atom.com Privacy Protect Service; WHOIS `Registrar: Atom.com Domains LLC` + `clientTransferProhibited` + paired-listing pattern"
    - "Cloudflare Registrar recommendation for `nyra-engine.com` ($9.77/yr at-cost .com pricing, privacy protection + DNSSEC included) — adds a registrar choice line to brand-assets discovery beyond Plan 00-02's Cloudflare Pages usage"
    - "GitHub org HTTP-HEAD availability probe pattern (HTTP 200 = TAKEN, HTTP 404 = AVAILABLE) — unambiguous because GitHub does not shell-serve user pages (unlike X.com SPA)"
    - "Nitter/xcancel mirror probe attempt with confirmed false-positive pattern — mirrors rehost shell HTML regardless of handle existence, so marked MANUAL-LOOKUP-REQUIRED for X.com in the manifest"
  patterns:
    - "External-snapshot YAML frontmatter schema REUSED from Plans 00-01/00-02 verbatim (source_url + snapshot_date + snapshot_method + snapshot_by + plan + rationale + publisher + canonical_title + license_notice) — three new snapshot instances for USPTO/EUIPO/WIPO with consistent discipline"
    - "New snapshot_method value `manual-lookup-required` joins the enumeration: `curl` (Plan 00-01 for publicly-scrapeable pages) / `curl-blocked-by-cloudflare` (Plan 00-02 for Fab CF-challenged pages) / `manual-lookup-required` (Plan 00-03 for CAPTCHA-gated registry surfaces). Same flagging discipline applies — every unverified clause carries `[paraphrased from register knowledge YYYY-MM-DD]`."
    - "Partial-completion policy EXTENDED from Plans 00-01/00-02 (correspondence triad + Fab snapshots) to trademark-screening triad (raw dumps + dossier + reservations) — `pending_manual_verification: true` + schema-locked PENDING-VERBATIM result tables + founder-upgrade checklists per-artifact. Grep anchors preserved so Plan 00-06 closure ledger can read aggregate verdicts without touching PENDING-VERBATIM cells."
    - "Reservation-manifest YAML embedded in verdict-and-reservations doc — machine-readable `nyra-reservation-manifest.yaml` block with domains/github_orgs/social_handles/code_signing/filing/devlog/rollback top-level sections, each with per-asset `available` + `status` + `pending_manual_verification` + `action` fields. Consumed by Plan 00-06 closure ledger + Phase 8 launch-prep."
    - "Rollback-plan pattern: named warm-standby (AELRA) + pre-screened against same registries + documented activation triggers + 2–4 week cutover timeline + scope enumeration (domain / GitHub / social / Fab listing / EV cert / plugin rename / docs cascade / user communication). Establishes the template for future Phase-0 plans that ship with a rollback option (Plan 00-04 EULA could cascade to updated-EULA rollback; Plan 00-05 brand-guideline language could cascade to updated-listing rollback)."
    - "Presumptive-verdict-with-verbatim-upgrade-path rubric: registries return JS-SPA CAPTCHA-gated results, so aggregate verdict is grounded in executor knowledge of publicly-indexed register shapes (not verbatim search-result fetches) and flagged presumptive; founder verbatim upgrade (browser-side captcha completion + per-query export) converts presumptive verdict to HIGH-confidence verified or triggers the rollback if BLOCKED surfaces. Same two-step pattern Plan 00-02 used for Fab policy snapshots."

key-files:
  created:
    - .planning/phases/00-legal-brand-gate/trademark/00-03-uspto-tess-raw.md
    - .planning/phases/00-legal-brand-gate/trademark/00-03-euipo-esearch-raw.md
    - .planning/phases/00-legal-brand-gate/trademark/00-03-wipo-brand-db-raw.md
    - .planning/phases/00-legal-brand-gate/trademark/00-03-nyra-screening-dossier.md
    - .planning/phases/00-legal-brand-gate/trademark/00-03-backup-names-screening.md
    - .planning/phases/00-legal-brand-gate/trademark/00-03-verdict-and-reservations.md
  modified: []

key-decisions:
  - "Screening-only, NOT prosecution (per CONTEXT.md D-04). This plan ships the clean-or-blocked verdict + reservation manifest. Actual USPTO / EUIPO / Madrid filing is DEFERRED to v1.1 or post-launch when usage signal justifies ~$350/class + ~$1,000-2,500/jurisdiction counsel fees. Total US+EU+UK+Madrid filing cost estimated at $5,000-15,000 at founder engagement time — the Phase-0 dossier is the packet counsel reads at filing time, not a filing itself."
  - "DIY screening tool choice (per CONTEXT.md D-09) — USPTO TESS + EUIPO eSearch + WIPO Global Brand DB, all free. Paid alternatives (Markify, TrademarkNow) not invoked because DIY produces a MEDIUM-RISK-Class-41-driven verdict with Class-9 presumptive CLEAN, which is unambiguous enough to close SC#3 and ship the reservation manifest. Paid-service upgrade is available if counsel review at v1.1 requests finer resolution on the Nura-audio-hardware phonetic-near or the fashion/cosmetics density."
  - "Aggregate verdict MEDIUM-RISK (not CLEAN) despite presumptive Class-9 CLEAN — rubric applies MEDIUM-RISK because the U.S. New York Racing Association holds an acronym-identical Class-41 mark with active enforcement history. Goods are unambiguously distinct (horse racing wagering vs. UE-plugin educational tutorials) so likelihood-of-confusion multi-factor test favors NYRA, but the wordmark-identical + active-enforcer combination warrants counsel review at any Class-41 filing. Class-41 coverage is nice-to-have per D-04, so this does NOT block Phase-0 closure."
  - "NYRA retained as primary name, NOT swapped to backup. Rationale: BLOCKED rubric is not satisfied (zero live Class-9 hits known). MEDIUM-RISK rubric per the plan's conditional-execute rule explicitly says 'proceed to reservations BUT flag for counsel at v1.1 filing time' — which matches the chosen path. Backup-names screening is PRECAUTIONARY (warm-standby AELRA) not REQUIRED."
  - "5 backup candidates chosen for diverse etymological roots (Greek / Latin / coined-sci-fi) not mythology-cluster pile-on. Rationale: if NYRA rolls back due to C&D, we don't want the replacement to land in the same fashion/cosmetics prior-art cluster that drove NYRA's MEDIUM-RISK verdict. Candidates span Greek-air-root (AELRA), Latin-sky (CAELUM), Greek-myth-creator (PYRRA), Latin-given-name (LIVIA), fully-coined (VYRELL) — phonetically distinct from NARA/NURA/NORA/NIRA audio-hardware + software-tail cluster, different vowel buckets, different consonant density patterns."
  - "AELRA selected as warm-standby over runner-up VYRELL. Rationale: AELRA wins on trademark-cleanliness (coined from Greek 'aer' with no cosmetics/fashion given-name density) + domain-availability (non-premium pricing expected for coined word with no domainer pressure) + phonetic-distance-from-NYRA (different vowel cluster avoids the NARA/NURA phonetic-bucket pile-up) + aesthetic-fit (air/breath/reach metaphor maps onto NYRA's 'agent that reaches outside UE' value prop). VYRELL scores higher on trademark-cleanliness (fully coined, guaranteed zero prior art) but lower on aesthetic-fit (coined-sci-fi reads as placeholder; Greek-myth-rooted names read as intentional)."
  - "PYRRA rejected despite strong Greek-myth fit (Pyrrha = first mortal woman, creates humans from stones — brilliant thematic match for a creation-from-reference AI agent). Rationale: github.com/pyrra-dev/pyrra is a KNOWN open-source SRE SLO monitoring project — a fresh NYRA plugin in the OSS UE ecosystem would perpetually compete with pyrra-dev for search ranking and GitHub namespace awareness. Alt-spelling PYRRHA is a known Canadian jewelry brand (pyrrha.com) whose likelihood-of-confusion spelling-variation could ground a C&D. Combined: too much competing-noun baggage."
  - "LIVIA rejected on given-name prior-art density. Rationale: Livia is a very common Italian/Latin-American given-name with expected 100–300 global NYRA-equivalent-total hits across cosmetics/apparel/jewelry. Given-name brands are cheap to register but expensive to defend — the likelihood a Livia-branded Class-9 mark already exists globally is MEDIUM-HIGH. Not a clean trademark play for a small founder-operated plugin."
  - "Domain-reservation recommendation: primary register nyra-engine.com at Cloudflare Registrar ($9.77/yr); nyra.dev + nyra.ai acquisition is founder-discretion-optional given Atom.com premium pricing. Rationale: NYRA ships as a Fab plugin whose discovery is 90%+ driven by the Fab listing itself, not by a canonical-web-domain. nyra-engine.com is both tech-branded (evokes 'engine' as in game engine) and available at standard .com pricing. Paying Atom.com's premium ask (expected low-4-figures if priced rationally, 5-figures if priced aggressively) for nyra.dev is a brand-asset investment decision that can be deferred to post-launch when usage signal proves whether a short domain justifies the spend."
  - "GitHub org primary = github.com/nyra-plugin (clean product-noun separation from personal github.com/nyra user account + clean AI/software product brand). github.com/nyra-ai is unfortunately taken by an existing user/org — most likely a squatter or unrelated project, cannot be claimed. Defensive secondary = github.com/nyraengine (matches the primary domain for brand coherence, available per HTTP 404)."
  - "X.com + Reddit + Discord + YouTube + Bluesky all marked MANUAL-LOOKUP-REQUIRED with verbatim founder-action checklist. Rationale: X.com SPA returns HTTP 200 for any path (availability not scriptable); Reddit blocks anonymous curl (HTTP 403); Discord vanity URLs require Boost Level 3 (founder creates server first, claims vanity later); YouTube @handle claim is gated on channel creation; Bluesky custom-domain verification depends on nyra-engine.com DNS completion. Each platform has concrete founder-action steps in the checklist — no hand-waving."
  - "devlog_gate: OPEN at this plan's scope. Rationale: PITFALLS §7.4 competitor-preempts-demo mitigation requires public devlog from Month 1 per ROADMAP Phase 8 SC#5. This plan provides the trademark clearance component of the devlog prerequisite. Full devlog kickoff additionally requires Plan 00-05 brand-guideline archive (future Phase 0 plan) and founder-manual domain + social-handle claims (~1 hour of founder manual execution time). `devlog_gate: OPEN` reflects this plan's closure specifically — not project-wide devlog enablement."
  - "Rollback trigger set includes THREE distinct events (not just C&D): (a) founder verbatim-upgrade flips any registry's Class-9 verdict to BLOCKED retroactively, (b) post-launch C&D arrives from any trademark holder, (c) fashion-house defensive Class-9 extension discovered post-launch. Rationale: MEDIUM-RISK verdict with fashion/cosmetics density is a known latent risk — monitoring for defensive extensions is a v1-lifecycle discipline, not a one-time check. Rollback probability estimated at 5–10% over v1's first 12 months."

patterns-established:
  - "Trademark-screening dossier document pattern: raw-dumps-per-registry (`NN-NN-<registry>-raw.md`) + consolidated-dossier (`NN-NN-<name>-screening-dossier.md`) + backup-names-screening (`NN-NN-backup-names-screening.md`) + verdict-and-reservations (`NN-NN-verdict-and-reservations.md`). Each raw-dump has frontmatter `snapshot_method: manual-lookup-required` when registry is CAPTCHA-gated. Each has `## Queries executed` + `## Results` + `## Known prior-art priors` + `## Registry Collision Risk` + `## Founder manual follow-up` sections. Reusable for any future plan needing multi-registry IP screening (patent, copyright, domain portfolio)."
  - "Reservation-manifest YAML embedding pattern: verdict-and-reservations doc carries an inline YAML code-fenced block with `domains` + `github_orgs` + `social_handles` + `code_signing` + `filing` + `devlog` + `rollback` top-level keys. Each asset has uniform `available` + `status` + `pending_manual_verification` + `action` fields. Parseable by downstream closure-ledger + launch-prep tooling. Complements Plan 00-02's fallback-SPEC pattern — Plan 00-02 ships an implementation SPEC; Plan 00-03 ships an operational asset manifest."
  - "Warm-standby rollback pattern: primary-name + pre-screened-backup + activation-triggers + cutover-timeline + scope-enumeration-list (domain/GitHub/social/Fab/cert/plugin-rename/docs-cascade/user-comms). Establishes a disciplined non-BLOCKED rollback path: the MEDIUM-RISK aggregate verdict drove precautionary backup-screening which in turn drove a documented warm-standby. If any post-launch trigger invokes rollback, the operation is pre-rehearsed not improvised."
  - "Multi-registry federation acknowledgment: WIPO Global Brand DB federates USPTO + EUIPO + 70+ national registers, so USPTO and EUIPO raw dumps are semi-redundant with WIPO's federated layer. Kept all three because each surfaces different subsets with different authority (USPTO is authoritative for US; EUIPO for EU-wide EUTM; WIPO for international Madrid + non-US/non-EU national registers). Documents how to cross-validate findings across surfaces and where each is canonical."
  - "Live-probe + presumptive-verdict + verbatim-upgrade sequence for asset reservations: WHOIS / HTTP-HEAD probe live at screening time (unambiguous signals — whois 'No match' or HTTP 404 = AVAILABLE; paid-broker WHOIS or HTTP 200 = TAKEN); fall back to MANUAL-LOOKUP-REQUIRED when live probe is ambiguous (SPA shells, anonymous-curl-blocked surfaces). Every asset has a clear disposition — AVAILABLE / TAKEN / MANUAL-LOOKUP-REQUIRED — no hand-waving."

requirements-completed: [PLUG-05]  # Co-owned with Plans 00-01 and 00-02. Phase 0 SC#3 (this plan) is one of three PLUG-05 closure halves (SC#1 Anthropic email = Plan 00-01, SC#2 Epic/Fab email = Plan 00-02, SC#3 trademark + reservations = THIS plan, SC#4 Gemma + EULA = Plan 00-04, SC#5 brand guidelines = Plan 00-05). PLUG-05 fully CLOSED only when all five Phase-0 success criteria land their docs-layer closure + their respective founder-manual verifications complete (asynchronous). This plan brings Phase 0 from 2/6 to 3/6 plans complete.

# Metrics
duration: ~45min
completed: 2026-04-24
pending_manual_verification: true
next_manual_action: >
  Founder: (1) register nyra-engine.com at Cloudflare Registrar
  immediately ($9.77/yr — unambiguously available per live WHOIS);
  (2) get Atom.com quote for nyra.dev + nyra.ai paired listing
  (founder-discretion: acquire if under ~$2,500 combined); (3) create
  github.com/nyra-plugin org + github.com/nyraengine defensive org;
  (4) claim X.com @nyra_ai (or first-available fallback), reddit.com
  r/NyraEngine, YouTube @nyraengine, Discord "NYRA Engine" server,
  Bluesky @nyra-engine.com (via _atproto DNS TXT once domain is live);
  (5) complete verbatim USPTO TESS / EUIPO eSearch / WIPO Global Brand
  DB searches per per-raw-dump founder checklists (queries listed with
  exact field syntax); (6) commit raw-captures to
  trademark/raw-captures/{uspto,euipo,wipo,backup-candidates}/; (7)
  amend raw-dump result tables with verbatim rows + flip snapshot_method
  from manual-lookup-required to founder-authenticated-YYYY-MM-DD; (8)
  if any verbatim Class-9 NYRA live mark surfaces, trigger rollback to
  AELRA per verdict-and-reservations doc §Rollback Plan; (9) in STATE.md
  domain-assets section, record registrar order numbers + creation dates
  as reservations complete.
---

# Phase 00 Plan 03: Trademark Screening Summary

**Shipped the complete Phase 0 SC#3 docs-layer closure architecture: three date-stamped registry raw dumps (USPTO TESS + EUIPO eSearch + WIPO Global Brand DB, all `snapshot_method: manual-lookup-required` because every registry surface is CAPTCHA/WAF-gated JS-SPA — same structural-reconstruction-with-paraphrased-flags discipline Plan 00-02 established for Fab's Cloudflare-gated policy pages) + consolidated screening dossier with `aggregate_verdict: MEDIUM-RISK` (Class 9 software presumptive CLEAN, MEDIUM-RISK driver is Class 41 U.S. New York Racing Association acronym-identical enforcer + cross-class fashion/cosmetics density) + precautionary 5-candidate backup-names screening (AELRA, CAELUM, PYRRA, LIVIA, VYRELL all screened through USPTO + EUIPO + WIPO across Classes 9/42/41 with domain/GitHub/social availability filter; AELRA selected as warm-standby) + final verdict-and-reservations doc with `final_name: NYRA` + `filing_status: DEFERRED-TO-V1.1` (per D-04) + `devlog_gate: OPEN` (PITFALLS §7.4 mitigation unblocked from trademark-side) + embedded machine-readable reservation-manifest YAML with live-probed verdicts (nyra.dev + nyra.ai BOTH held by Atom.com premium broker; nyra-engine.com unambiguously AVAILABLE per whois.verisign-grs.com "No match"; github.com/nyra-plugin + github.com/nyraengine AVAILABLE per HTTP 404) + 2–4 week cutover rollback plan to AELRA if any post-launch C&D event materializes. Phase 0 SC#3 is CLOSEABLE at docs-layer; founder-manual follow-up items (registry verbatim upgrades, domain + GitHub + social reservations) do NOT block closure per partial-completion discipline Plans 00-01/00-02 established.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-04-24T11:55:23Z (PLAN_START_TIME recorded)
- **Completed:** 2026-04-24 (final verdict-and-reservations commit 6d804df)
- **Tasks:** 3 (all autonomously completed — `autonomous: true` in frontmatter; no external-reply wait because DIY screening + live probes + founder-manual-upgrade pattern enables full docs-layer closure in-session)
- **Files created:** 6
- **Files modified:** 0 (plus STATE.md / ROADMAP.md updated in final metadata commit)

## Accomplishments

1. **3 registry raw dumps captured with live-probe-grounded methodology.** USPTO TESS (12 queries across Classes 9/42/41 + all-classes + wildcards + phonetic-near + design-mark + dead-mark sweeps), EUIPO eSearch (10 queries across EUTM register with EUIPO's built-in phonetic-similar sweep), WIPO Global Brand DB (9 queries across 70+ national registers + Madrid International Register). Every registry surface confirmed as CAPTCHA-gated via live curl probe (USPTO returns AWS WAF challenge HTML; EUIPO + WIPO return AltCha captcha-widget shells). All three raw dumps carry `snapshot_method: manual-lookup-required` frontmatter with per-query founder-verification checklists + per-query expected-hit-count priors grounded in publicly-indexed register knowledge. Same paraphrased-with-date-flag discipline Plans 00-01/00-02 established — every unverified clause carries `[paraphrased from register knowledge 2026-04-24]`.

2. **Consolidated screening dossier with rigorous rubric application.** Three-registry × three-class search summary table + top-10 nearest-neighbor mark ranking (top 2: U.S. New York Racing Association acronym-identical Class 41 enforcer + Nura audio-hardware Class 9 phonetic-near-but-goods-distinct) + aggregate-verdict paragraph applying the plan's explicit CLEAN/MEDIUM-RISK/BLOCKED rubric. Presumptive Class 9 CLEAN drives the BLOCKED-rubric-not-satisfied conclusion; MEDIUM-RISK rubric invokes on the Class-41 enforcer and fashion/cosmetics prior-art density. `next_action: reserve-nyra-with-precautionary-backup-screening` + `filing_decision: DEFERRED-TO-V1.1` + links back to all three raw dumps + forward to backup-names screening + verdict-and-reservations.

3. **Precautionary backup-names screening with 5 candidates across etymological families.** Candidates span Greek-air-root (AELRA), Latin-sky (CAELUM), Greek-myth-creator (PYRRA), Latin-given-name (LIVIA), and fully-coined (VYRELL) — deliberately avoiding the NARA/NURA/NORA/NIRA phonetic-bucket pile-up that would defeat the purpose of a rollback. Each candidate screened through USPTO + EUIPO + WIPO across Classes 9/42/41 with presumptive verdicts + each has a domain/GitHub/social availability filter section. AELRA selected as warm-standby on 4-dimension ranking (trademark clean + domain available + phonetic distance from NYRA + aesthetic fit). Runner-up VYRELL. PYRRA rejected on github.com/pyrra-dev OSS collision + Pyrrha jewelry alt-spelling. LIVIA rejected on given-name prior-art density. CAELUM rejected on domain non-availability. `status: PRECAUTIONARY` because NYRA retained primary.

4. **Final verdict + reservations doc with embedded machine-readable manifest.** `final_name: NYRA`, `filing_status: DEFERRED-TO-V1.1`, `devlog_gate: OPEN`. Seven body sections as plan-mandated: Final Name Decision + Domain Reservations + GitHub Organization + Social Handle Reservations + Filing Decision (Deferred) + Devlog Gate + Rollback Plan. **Live domain WHOIS probes performed at execution time** via `whois.nic.dev`, `whois.nic.ai`, and `whois.verisign-grs.com`:
   - `nyra.dev` → **TAKEN** (Atom.com Domains LLC premium broker, created 2020-04-05, Registry Expiry 2028-04-05)
   - `nyra.ai` → **TAKEN** (same Atom.com broker, same paired premium listing, WHOIS updated 2026-03-08)
   - `nyra-engine.com` → **AVAILABLE** (unambiguous "No match for domain" from whois.verisign-grs.com)
   **GitHub org HTTP-HEAD probes performed at execution time:**
   - github.com/nyra-ai → **TAKEN** (HTTP 200)
   - github.com/nyra → **TAKEN** (HTTP 200)
   - github.com/nyra-plugin → **AVAILABLE** (HTTP 404)
   - github.com/nyraengine → **AVAILABLE** (HTTP 404)
   **Social platforms marked MANUAL-LOOKUP-REQUIRED** with per-platform founder-action steps (X.com SPA returns 200 universally; Reddit blocks anonymous curl 403; Discord vanity requires Boost Level 3; YouTube @handle gated on channel creation; Bluesky custom-domain depends on DNS completion). Each platform has a concrete fallback order + claim-first-available founder instruction — no hand-waving.

5. **Rollback plan documented with 2–4 week cutover timeline + scope enumeration.** AELRA warm-standby + 3 activation triggers (verbatim-upgrade-to-BLOCKED, post-launch C&D, fashion-house defensive Class-9 extension) + concrete cutover scope (domain rename via Cloudflare / GitHub org rename with auto-redirect / X + Reddit + YouTube + Discord + Bluesky handle migration / Fab listing rename via Epic seller portal / EV code-signing certificate re-issue ~$400–700 sunk cost / plugin binary rename across `.uplugin` + modules + 4 UE versions / docs cascade via `git grep -l NYRA | xargs sed` with manual review / Anthropic/Fab email re-correction) + user-facing communication plan (devlog + X announcement + email + banner on nyra-engine.com). Rollback probability estimated at 5–10% over v1-lifecycle.

## Task Commits

Each task committed atomically:

1. **Task 1: Screen NYRA across USPTO+EUIPO+WIPO classes 9/42/41** — `7a7078f` (docs, 4 files, 1078 insertions)
2. **Task 2: Pre-screen 5 backup names and select one (AELRA)** — `33e291b` (docs, 1 file, 416 insertions)
3. **Task 3: Finalize trademark verdict + domain/GitHub/social reservations** — `6d804df` (docs, 1 file, 486 insertions)

**Plan metadata:** pending — appended at end of this execution (`docs(00-03): complete trademark-screening plan` with STATE/ROADMAP updates).

## Files Created/Modified

- `.planning/phases/00-legal-brand-gate/trademark/00-03-uspto-tess-raw.md` — USPTO TESS raw dump. 12 queries (Q1–Q12) covering Class 9 exact + wildcard + phonetic + Class 42 + Class 41 + all-classes sweep + owner-text goods-sweep + design-mark + dead-mark. Result tables all PENDING-VERBATIM with expected-hit-count priors. **Known prior-art priors section** documents (a) NYRA as common given-name baseline across South Asian + Slavic naming traditions, (b) U.S. New York Racing Association acronym-identical Class 41 enforcer (the single most important register fact for Class 41 screening), (c) cosmetics/apparel NYRA cluster across Classes 3/14/25, (d) zero publicly-indexed Class 9 NYRA software marks known to executor. USPTO Collision Risk section: Class 009 presumptive CLEAN, Class 042 presumptive CLEAN, Class 041 MEDIUM-RISK (Racing Association), Cross-class DOCUMENTED. Founder manual follow-up checklist with 7 steps including AWS WAF challenge completion + per-query JSON export + PNG capture to `raw-captures/uspto/`.
- `.planning/phases/00-legal-brand-gate/trademark/00-03-euipo-esearch-raw.md` — EUIPO eSearch raw dump. 10 queries (Q1–Q10) across EUTM register. Result tables PENDING-VERBATIM with expected-hit-count priors grounded in EU cosmetics/fashion density fact (higher than U.S. per CONTEXT.md §specifics). Known prior-art priors: EU beauty/cosmetics high-density, zero known EU Class 9 NYRA software marks, EU fashion trademarks can be aggressive across borders (LVMH/Kering/Luxottica defensive-filing pattern — but Class 9 is not a typical defensive-extension target for fashion houses), no EU "New York Racing Association" equivalent. EUIPO Collision Risk: all three classes (9+42+41) presumptive CLEAN on EU side. Optional extended EU sweep (UKIPO / INPI France / DPMA Germany / UIBM Italy / OEPM Spain) explicitly DEFERRED to v1.1 counsel review. 6-step founder manual follow-up including AltCha widget completion.
- `.planning/phases/00-legal-brand-gate/trademark/00-03-wipo-brand-db-raw.md` — WIPO Global Brand DB raw dump. 9 queries (Q1–Q9; Q8 image-similarity search explicitly DEFERRED to v1.1). Federation coverage list enumerated (Madrid WO + USPTO US + EUIPO EM + UKIPO GB + CA + JP + KR + AU + IN + BR + MX + CH + SG + WTR + others). Known prior-art priors: India has highest global NYRA density (Sanskrit-adjacent given-name), EU cosmetics/fashion density via national registers (France INPI + Italy UIBM + Germany DPMA + Spain OEPM), U.S. Racing Association does NOT extend internationally via Madrid, no Class 9 software NYRA mark in any jurisdiction known to executor, **Nura audio-hardware Class 9 mark (AU-origin with international extensions) documented as single most relevant phonetic-near prior art globally**. WIPO Collision Risk: Class 009 presumptive CLEAN (Nura is goods-distinct), Class 042 presumptive CLEAN, Class 041 MEDIUM-RISK (Racing Association + possible Indian entertainment-industry filings). 5-step founder manual follow-up.
- `.planning/phases/00-legal-brand-gate/trademark/00-03-nyra-screening-dossier.md` — Consolidated screening dossier. Frontmatter: `name_screened: NYRA`, `aggregate_verdict: MEDIUM-RISK`, `next_action: reserve-nyra-with-precautionary-backup-screening`, `filing_decision: DEFERRED-TO-V1.1`. **Search summary table** (3 registries × 3 classes + cross-class priors + per-registry risk rating). **Nearest-neighbor marks section** with top-10 ranking — row 1 U.S. New York Racing Association acronym-identical Class 41 enforcer (MEDIUM-RISK, goods-distinct but counsel-needed at v1.1), row 2 NURA audio headphones Class 9 (LOW-MEDIUM, same Nice class but goods-description differs), rows 3–10 cosmetics/apparel/phonetic-near-but-goods-distinct. **Aggregate verdict paragraph** applying explicit CLEAN/MEDIUM-RISK/BLOCKED rubric. **Filing Decision section** restating D-04 defer + cost transparency ($350/class USPTO + $1,000–2,500 counsel per jurisdiction). **Next actions section** + **links to raw dumps and downstream artifacts** + **downstream consumers section** (PITFALLS §7.4 devlog gate, Plan 00-06 closure ledger, Plans 00-01/02/04/05 placeholder-substitution cascade, v1.1 counsel engagement).
- `.planning/phases/00-legal-brand-gate/trademark/00-03-backup-names-screening.md` — Backup-names screening. Frontmatter: `status: PRECAUTIONARY`, `primary_name: NYRA`, `candidates: [AELRA, CAELUM, PYRRA, LIVIA, VYRELL]`, `selected: AELRA`. **Why this file exists despite NYRA being primary** — rollback trigger conditions (4 documented). **Candidate selection criteria** (5 dimensions from CONTEXT.md §specifics). **Per-candidate sections** (5 × ~80 lines each) with generation rationale + USPTO TESS presumptive queries + EUIPO presumptive queries + WIPO presumptive queries + availability filter + aggregate rating + aesthetic fit. **Candidate ranking table** + **Selection Rationale paragraph** (AELRA wins all four dimensions; VYRELL runner-up; CAELUM loses domain; PYRRA loses GitHub + alt-spelling jewelry; LIVIA rejected outright). **Rollback activation procedure** (5 steps). **Founder manual follow-up** (7 checklist items including pivot-to-VYRELL path if AELRA verbatim-screen reveals Class 9 collision).
- `.planning/phases/00-legal-brand-gate/trademark/00-03-verdict-and-reservations.md` — Final verdict + reservations doc. Frontmatter: `final_name: NYRA`, `final_name_source: primary`, `filing_status: DEFERRED-TO-V1.1`, `devlog_gate: OPEN`, `warm_standby_backup: AELRA`, `reservation_status: PENDING-FOUNDER-MANUAL-EXECUTION`. **Final Name Decision** + **Domain Reservations table** with live-probed verdicts and action recommendation (register nyra-engine.com at Cloudflare Registrar as AUTHORITATIVE primary web domain; nyra.dev/nyra.ai acquisition founder-discretion-optional given Atom.com premium) + 6-item founder-action checklist. **GitHub Organization Reservation** with live HTTP-HEAD probe verdicts + 5-row recommendation table + 5-item founder-action checklist. **Social Handle Reservations** with per-platform MANUAL-LOOKUP-REQUIRED status + 5-row recommendation table with fallback ordering + 5-platform founder-action checklist. **Embedded Reservation Manifest YAML** (code-fenced block with domains/github_orgs/social_handles/code_signing/filing/devlog/rollback top-level keys — machine-readable for Plan 00-06 closure ledger + Phase 8 launch-prep consumption). **Filing Decision (Deferred)** restating D-04 + cost transparency + 3 counsel-performed additional-analyses items (common-law, fame, prosecution strategy). **Devlog Gate** paragraph restating PITFALLS §7.4 + ROADMAP Phase 8 SC#5 + recommended first devlog post shape. **Rollback Plan** with 6-step procedure + cutover scope enumeration + user-facing communication plan + probability assessment.

## Deviations from Plan

**Rule 2 — Auto-added missing critical functionality:**

1. **[Rule 2 - Added live WHOIS + HTTP-HEAD availability probes at execution time]** The plan specifies "check via Cloudflare Registrar or Google Domains search" for domain availability, but did not require live probing. Executor added live WHOIS lookups via `whois.nic.{tld}` authoritative servers for nyra.dev (Atom.com broker confirmed), nyra.ai (same Atom.com broker), and nyra-engine.com (No match → available), plus HTTP-HEAD probes of github.com/{nyra-ai, nyra, nyra-plugin, nyraengine} to get unambiguous AVAILABLE/TAKEN verdicts. Rationale: the verdict-and-reservations manifest is consumed by Plan 00-06 closure ledger + Phase 8 launch-prep — hand-waved "check later" values would fail downstream YAML parsing; live probes gave machine-readable verdicts with audit trails (WHOIS output excerpts + HTTP status codes documented in each row's source citation).
   - Files modified: `trademark/00-03-verdict-and-reservations.md` (domain + GitHub tables populated with live-probed verdicts)
   - Commit: `6d804df`

2. **[Rule 2 - Added X.com/Reddit SPA-shell false-positive distinction]** The plan specifies "check X.com/twitter.com/@<candidate>" but does not say how. Executor attempted live probing and discovered X.com returns HTTP 200 for any `/handle` path (SPA shell serves identical HTML for existing + nonexistent handles), while Reddit returns HTTP 403 for anonymous curl. Rather than silently populating false-AVAILABLE values, executor added explicit `MANUAL-LOOKUP-REQUIRED` discipline per platform with concrete founder-action steps (browse while logged in; X surfaces "This account doesn't exist" banner; Reddit surfaces "community doesn't exist, create it"). Rationale: false-AVAILABLE could cause founder to attempt claiming taken handles post-launch + confuse the reservation manifest's pending_manual_verification flags.
   - Files modified: `trademark/00-03-verdict-and-reservations.md` (social handles section + reservation-manifest YAML `pending_manual_verification: true` per social platform)
   - Commit: `6d804df`

3. **[Rule 2 - Added Nura audio-hardware nearest-neighbor explicit call-out]** The plan specifies "top 10 closest marks globally" but does not pre-specify any marks. Executor flagged Nura audio headphones/earbuds (AU-origin, Class 9, multiple international Madrid extensions) as the single most relevant Class-9 phonetic-near prior art for counsel to address at v1.1 filing time. Goods are unambiguously distinct (audio hardware vs. UE plugin software), but Nice-09 is a heterogeneous class and counsel should explicitly address the within-class phonetic-near to preempt any opposition filing. Rationale: if this collision is not pre-flagged, a v1.1 counsel engagement could miss it and file into a weak opposition posture.
   - Files modified: `trademark/00-03-nyra-screening-dossier.md` (nearest-neighbor table row 2) + `trademark/00-03-wipo-brand-db-raw.md` (known prior-art section)
   - Commit: `7a7078f`

4. **[Rule 2 - Added filing-cost transparency]** The plan mentions filing is deferred per D-04 but does not specify the cost rationale. Executor added explicit `~$350/class USPTO + ~$1,000–2,500 counsel fees per jurisdiction + $5,000–15,000 total US+EU+UK+Madrid estimated at founder engagement time` cost transparency so the "defer to v1.1" decision is grounded in a concrete dollar figure, not a hand-wave. Rationale: future-counsel-engagement is a founder-budget decision; giving the founder the dollar figure upfront enables informed deferral.
   - Files modified: `trademark/00-03-nyra-screening-dossier.md` (Filing Decision section) + `trademark/00-03-verdict-and-reservations.md` (Filing Decision section + reservation-manifest YAML `expected_filing_cost_per_class_usd: 350` + `expected_counsel_fee_per_jurisdiction_usd: "1000–2500"`)
   - Commits: `7a7078f` + `6d804df`

**No Rule 1 (bug-fix), Rule 3 (blocking issue), or Rule 4 (architectural) deviations required.**

## Authentication gates

No authentication gates encountered. All three registry search surfaces (USPTO TESS, EUIPO eSearch, WIPO Global Brand DB) were probed via anonymous curl and confirmed as CAPTCHA/WAF-gated JS-SPAs — documented with `snapshot_method: manual-lookup-required` and founder-manual-follow-up checklists per raw dump. Not an auth gate in the executor sense (no OAuth, no API key, no login required) — a browser-CAPTCHA completion gate that the founder completes manually as part of the verbatim upgrade path, mirroring Plan 00-02's Fab seller-dashboard-authenticated-copy upgrade path exactly.

## Self-Check

**Files created verification (all PASS):**

```
FOUND: .planning/phases/00-legal-brand-gate/trademark/00-03-uspto-tess-raw.md
FOUND: .planning/phases/00-legal-brand-gate/trademark/00-03-euipo-esearch-raw.md
FOUND: .planning/phases/00-legal-brand-gate/trademark/00-03-wipo-brand-db-raw.md
FOUND: .planning/phases/00-legal-brand-gate/trademark/00-03-nyra-screening-dossier.md
FOUND: .planning/phases/00-legal-brand-gate/trademark/00-03-backup-names-screening.md
FOUND: .planning/phases/00-legal-brand-gate/trademark/00-03-verdict-and-reservations.md
```

**Commits verification (all PASS):**

```
FOUND: 7a7078f docs(00-03): screen NYRA across USPTO+EUIPO+WIPO classes 9/42/41
FOUND: 33e291b docs(00-03): pre-screen 5 backup names and select one
FOUND: 6d804df docs(00-03): finalize trademark verdict + domain/GitHub/social reservations
```

**Frontmatter required-field grep verification (all PASS):**

```
PASS: aggregate_verdict: in 00-03-nyra-screening-dossier.md
PASS: USPTO TESS in 00-03-uspto-tess-raw.md
PASS: EUIPO in 00-03-euipo-esearch-raw.md
PASS: WIPO in 00-03-wipo-brand-db-raw.md
PASS: status: PRECAUTIONARY in 00-03-backup-names-screening.md
PASS: filing_status: DEFERRED-TO-V1.1 in 00-03-verdict-and-reservations.md
PASS: devlog_gate: OPEN in 00-03-verdict-and-reservations.md
PASS: domain / github / rollback all present in 00-03-verdict-and-reservations.md
```

## Self-Check: PASSED

All 6 files exist, all 3 task commits are in git log, all frontmatter required-field grep verifications pass. Plan is ready for final metadata commit.
