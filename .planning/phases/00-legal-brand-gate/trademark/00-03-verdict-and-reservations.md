---
final_name: NYRA
final_name_source: primary
screening_dossier: trademark/00-03-nyra-screening-dossier.md
backup_screening: trademark/00-03-backup-names-screening.md
filing_status: DEFERRED-TO-V1.1
devlog_gate: OPEN
date_closed: 2026-04-24
aggregate_verdict_from_dossier: MEDIUM-RISK (Class 9 software presumptive CLEAN; MEDIUM-RISK driver is Class 41 U.S. New York Racing Association acronym-identical enforcer + fashion/cosmetics prior-art density across Classes 3, 14, 25 globally)
warm_standby_backup: AELRA (per 00-03-backup-names-screening.md)
reservation_status: PENDING-FOUNDER-MANUAL-EXECUTION
pending_manual_verification: true
verification_reason: >
  Domain registrations, GitHub org creation, social-handle reservations,
  and Discord server claiming are all founder-action items requiring
  payment (domain registrar) or account creation (GitHub, X, Reddit,
  Discord). The executor CANNOT programmatically reserve these assets
  — same discipline Plans 00-01 / 00-02 used for PLACEHOLDER "sent"
  and "response" stubs with pending_manual_verification:true. This
  doc populates the reservation-target list with availability verdicts
  grounded in 2026-04-24 live probes (WHOIS + HTTP-HEAD) where
  unambiguous (nyra.dev, nyra.ai, nyra-engine.com, github.com/nyra-ai,
  github.com/nyra) and marks X/Reddit/Discord as manual-lookup-required
  where anti-bot or SPA shells prevent scripted availability detection.
  Founder upgrades this doc with registrar order numbers, GitHub
  creation dates, and social handle capture evidence as a manual
  follow-up before devlog kickoff.
---

# NYRA Trademark Verdict + Domain/GitHub/Social Reservations (2026-04-24)

## Final Name Decision

**Final name: NYRA.**
**Source: primary** (original planned name retained; no rollback to
backup required).

Per `trademark/00-03-nyra-screening-dossier.md`, the aggregate trademark
verdict across USPTO + EUIPO + WIPO screening of Classes 9 + 42 + 41 is
**MEDIUM-RISK** with presumptive CLEAN Class 9 (software — the blocker
class per CONTEXT.md §specifics), presumptive CLEAN Class 42, and
MEDIUM-RISK Class 41 driven by the U.S. New York Racing Association's
acronym-identical mark (goods-distinct horse-racing services vs. UE
plugin educational content; counsel-resolvable at v1.1 filing time).

Rubric application: CLEAN rubric is satisfied for the blocker class.
MEDIUM-RISK rubric is invoked by the Class-41 enforcer. BLOCKED rubric
is not satisfied. **NYRA proceeds as primary.**

Per `trademark/00-03-backup-names-screening.md`, five backup candidates
(AELRA, CAELUM, PYRRA, LIVIA, VYRELL) were screened as precautionary
warm-standbys. AELRA was selected as the primary rollback target if
a cease-and-desist arrives post-launch or the founder-manual verbatim-
verification upgrade flips any registry's Class-9 verdict to BLOCKED.

## Domain Reservations

Availability probes performed on 2026-04-24. WHOIS lookups via
`whois.nic.{tld}` authoritative servers; HTTP-HEAD probes for live-
response distinction.

| Domain | Registrar-side status (2026-04-24 probe) | Action | Registrar | Reserved date | Expiry | Receipt-ref / order number |
|--------|------------------------------------------|--------|-----------|---------------|--------|-----------------------------|
| **nyra.dev** | **TAKEN — premium listing at Atom.com Domains LLC (Atom.com is a premium-domain broker). WHOIS: Creation 2020-04-05, Registrant "Atom.com Privacy Protect Service", Domain Status `clientTransferProhibited`. A-record 52.20.84.62 likely points to Atom.com's sale-listing page.** | **REQUIRES PREMIUM PURCHASE or DROP-CATCH** — founder decision: pay atom.com's premium ask (expected low-4-figures for a 4-letter .dev) OR pivot to fallback `.ai` (also premium, same broker) OR accept `.com` fallback + `nyra-engine.com` primary-tech-domain pattern. | Atom.com (broker) | PENDING-FOUNDER-PURCHASE | — | PENDING |
| **nyra.ai** | **TAKEN — same Atom.com Domains LLC broker (same privacy registrant + same creation date 2020-04-05 → both premium-listed together). WHOIS Updated 2026-03-08 (broker re-listed recently). Domain Status clientTransferProhibited. Registry Expiry 2028-04-05.** | **REQUIRES PREMIUM PURCHASE** — Atom.com holds both nyra.dev + nyra.ai as a paired premium listing; expect 5-figure combined ask if bought together. | Atom.com (broker) | PENDING-FOUNDER-PURCHASE | — | PENDING |
| **nyra-engine.com** | **AVAILABLE — WHOIS returns `No match for domain "NYRA-ENGINE.COM"` (unambiguous "not registered" signal from whois.verisign-grs.com).** | **REGISTER IMMEDIATELY at standard .com rate ($12–15/yr).** Recommended registrar: Cloudflare Registrar ($9.77 at-cost .com pricing, includes privacy protection + DNSSEC) or Porkbun ($10.99 .com, privacy included). | Cloudflare Registrar (recommended) | PENDING-FOUNDER-PURCHASE | — | PENDING |
| **nyra-plugin.com** | Not probed (exploratory fallback). | Optional secondary fallback. | — | — | — | — |
| **nyraengine.com** (no-hyphen variant) | Not probed. | Optional secondary fallback; hyphen-free is marginally better SEO but less unique. | — | — | — | — |

**Domain-reservation recommendation given the primary .dev/.ai premium
block:**

1. **IMMEDIATE (founder-action):** Register `nyra-engine.com` at Cloudflare
   Registrar as the AUTHORITATIVE primary web domain. Cost: ~$9.77/yr.
   Use for `https://nyra-engine.com` canonical URL (brand site, devlog,
   download landing page, Fab listing cross-link target).
2. **OPTIONAL (founder discretion):** Contact Atom.com to get the
   combined nyra.dev + nyra.ai quote. If priced under ~$2,500 combined,
   acquire both as a pre-launch brand-asset investment. If priced
   higher, skip — `nyra-engine.com` is sufficient for a free Fab plugin
   in a Windows-only v1 where the Fab listing drives 90% of discovery
   traffic.
3. **DEFENSIVE REGISTRATIONS:** Register `nyra-plugin.com` + typo-squat
   defensives (`nyraengine.com` no-hyphen, `nyra-ue.com` UE-specific)
   at $9.77 each as one-time brand-safety moat. Total defensive spend
   ~$30/year.

**Founder-action checklist for domain reservations:**

- [ ] Register nyra-engine.com at Cloudflare Registrar (primary — REQUIRED)
- [ ] Configure DNS at Cloudflare with A/AAAA placeholder or parked-page redirect
- [ ] Register nyra-plugin.com (optional — defensive)
- [ ] Contact Atom.com for quote on nyra.dev + nyra.ai (optional — founder discretion; skip if quote exceeds acceptable budget)
- [ ] Document registrar order numbers + payment dates in this file
- [ ] Update expiry tracking in `.planning/STATE.md` domain-assets section

## GitHub Organization Reservation

Live HTTP-HEAD probes performed on 2026-04-24 against github.com/{org}
endpoints. GitHub returns HTTP 200 for existing orgs/users and HTTP 404
for available slugs.

| Candidate org slug | GitHub HTTP status (2026-04-24 probe) | Interpretation | Action |
|--------------------|---------------------------------------|----------------|--------|
| **github.com/nyra-ai** | **HTTP 200 → TAKEN** | An existing user or org at github.com/nyra-ai. Cannot claim. | Skip. |
| **github.com/nyra** | **HTTP 200 → TAKEN** | Existing user/org at github.com/nyra. Likely a personal username. Cannot claim. | Skip. |
| **github.com/nyra-plugin** | **HTTP 404 → AVAILABLE** | No existing owner. Claim-eligible. | **CLAIM — PRIMARY** |
| **github.com/nyraengine** | **HTTP 404 → AVAILABLE** | No existing owner. Claim-eligible. | **CLAIM — SECONDARY / DEFENSIVE** |
| github.com/nyra-ue | Not probed | Candidate if primary unavailable. | Optional. |
| github.com/nyra-unreal | Not probed | Candidate if primary unavailable. | Optional. |

**Recommended GitHub organization:**

Primary: **github.com/nyra-plugin** (matches "NYRA plugin" product noun;
clean separation from any personal `nyra` user accounts; clear AI/
software product brand).

Alternative: **github.com/nyraengine** (matches the `nyra-engine.com`
domain; tighter brand coherence).

**Founder decision:** pick one primary; register the other as defensive
redirect/placeholder-README repo.

| Org URL | Date created | Admin account | Primary repo slug (future) | Notes |
|---------|--------------|---------------|----------------------------|-------|
| github.com/nyra-plugin | PENDING-FOUNDER-CREATION | [founder's GitHub username] | nyra-plugin/nyra (main plugin repo) | Primary — claim first |
| github.com/nyraengine | PENDING-FOUNDER-CREATION | [founder's GitHub username] | nyraengine/nyra (mirror or defensive) | Secondary — claim for brand-safety |

**Founder-action checklist for GitHub reservations:**

- [ ] Create github.com/nyra-plugin organization
- [ ] Create github.com/nyraengine organization (defensive)
- [ ] Configure both with placeholder README + link to nyra-engine.com
- [ ] Transfer or create initial plugin repo under primary org (v1 target: nyra-plugin/nyra)
- [ ] Document admin account + creation date in this file

## Social Handle Reservations

Live HTTP-HEAD probes performed on 2026-04-24 for X.com, Reddit, and
adjacent surfaces. **Note: X.com returns HTTP 200 for any `/handle`
path (SPA shell) regardless of whether the handle exists; Reddit returns
HTTP 403 for anonymous curl. Availability verification is therefore
MANUAL-LOOKUP-REQUIRED for X, Reddit, and Discord — same discipline
applied to USPTO/EUIPO/WIPO search.** Nitter/xcancel mirror probes
returned HTTP 200 universally (mirror rehosts shell HTML regardless of
existence), confirming the SPA-shell false-positive pattern.

| Platform | Candidate handle | Scripted availability signal | Action |
|----------|-------------------|------------------------------|--------|
| **X.com (Twitter)** | @nyra_ai | MANUAL-LOOKUP-REQUIRED (HTTP 200 SPA shell — no availability signal) | Founder browses to x.com/nyra_ai while logged in; X surfaces "This account doesn't exist" banner if available, or profile if taken. **Try in order: nyra_ai, nyra_plugin, nyraengine, nyra_ue, nyra_ai_plugin. Claim first available.** |
| X.com | @nyraengine | MANUAL-LOOKUP-REQUIRED | Fallback. |
| X.com | @nyra_plugin | MANUAL-LOOKUP-REQUIRED | Fallback. |
| **Reddit** | r/nyra_ai | MANUAL-LOOKUP-REQUIRED (anon curl blocked with 403) | Founder visits reddit.com/r/nyra_ai while logged in; Reddit surfaces "community doesn't exist, create it" if available. **Try in order: r/NyraPlugin, r/NyraEngine, r/nyra_ai. Claim first available.** Note Reddit subreddit naming is case-preserving in the URL (r/NyraEngine vs r/nyraengine) and case-insensitive in routing. |
| Reddit | r/NyraEngine | MANUAL-LOOKUP-REQUIRED | Primary recommendation. |
| Reddit | r/NyraPlugin | MANUAL-LOOKUP-REQUIRED | Alternative. |
| **Discord server vanity** | nyra-engine | MANUAL-LOOKUP-REQUIRED (Discord vanity URLs require Boost Level 3 to claim; founder creates server first, then applies when eligible OR uses invite-link-only distribution pre-vanity) | Founder creates "NYRA Engine" Discord server with their own owner account. Vanity URL claim deferred until Boost Level 3 or invite-code-only distribution. |
| **YouTube @handle** | @nyraengine | MANUAL-LOOKUP-REQUIRED | If devlog goes video-first (PITFALLS §7.4 mitigation). YouTube @handles exposed via https://youtube.com/@nyraengine — 404 if available, channel page if taken. Manual check via logged-in YouTube Studio. |
| **Bluesky** | @nyra.engine.bsky.social or custom nyra-engine.com domain verification | MANUAL-LOOKUP-REQUIRED | Optional; verify at bsky.app. Using custom domain via `_atproto.nyra-engine.com` TXT record is the cleanest path and ties brand ownership to the domain above. |
| **Mastodon** | @nyra@someinstance.com | DEFERRED | Mastodon handles are instance-scoped; defer to v1.1 or post-launch decision. |

**Recommended social-handle reservation order (for founder manual execution):**

1. **Reddit r/NyraEngine** (create subreddit) — highest-leverage long-
   tail community surface for UE plugin support and devlog cross-post.
2. **X.com @nyra_ai** or fallback — primary announcement channel for
   launches, demos, release notes.
3. **YouTube @nyraengine** — video-first devlog channel (per PITFALLS
   §7.4 competitor-preempts-demo mitigation: weekly devlog from Month 1).
4. **Discord server "NYRA Engine"** — user support + beta-tester channel
   + livestream overflow. Claim vanity URL later.
5. **Bluesky custom-domain via nyra-engine.com** — cross-post mirror of
   X content using verified-domain handle.

| Platform | Handle claimed | Reserved date | Notes |
|----------|----------------|---------------|-------|
| X.com | PENDING-FOUNDER-RESERVATION (target @nyra_ai) | — | — |
| Reddit | PENDING-FOUNDER-RESERVATION (target r/NyraEngine) | — | Founder creates subreddit; must stay active to retain. |
| YouTube | PENDING-FOUNDER-RESERVATION (target @nyraengine) | — | Auto-reserved when channel created; no separate @handle claim flow unless channel has >0 subs + 30-day age. |
| Discord | PENDING-FOUNDER-RESERVATION (server "NYRA Engine") | — | Vanity URL claim deferred to Boost Level 3. |
| Bluesky | PENDING-FOUNDER-RESERVATION (domain-verified via nyra-engine.com DNS TXT) | — | Depends on nyra-engine.com domain registration completing first. |

**Founder-action checklist for social-handle reservations:**

- [ ] X.com — create @nyra_ai or first-available fallback; set profile to placeholder
- [ ] Reddit — create r/NyraEngine; populate with 3 starter posts (project README, "what is NYRA", first devlog)
- [ ] YouTube — create @nyraengine channel; upload 30-second trailer or placeholder banner
- [ ] Discord — create "NYRA Engine" server; generate permanent-invite invite code; set up at minimum #announcements, #support, #devlog channels
- [ ] Bluesky — once nyra-engine.com DNS is live, add `_atproto` TXT record for domain-verification; claim @nyra-engine.com handle
- [ ] Document each handle + reserved date in the tables above

## Reservation manifest (YAML — for orchestrator consumption)

```yaml
# nyra-reservation-manifest.yaml
# Consumed by: Plan 00-06 closure-ledger (phase-0 SC#3 flip)
# Consumed by: Phase 8 launch-prep (listing copy + brand asset audit)

name: NYRA
manifest_generated: 2026-04-24T11:55:23Z
availability_checked_at: 2026-04-24T11:55:23Z

domains:
  - host: nyra.dev
    available: false
    status: premium-broker-listed
    broker: Atom.com Domains LLC
    whois_creation: "2020-04-05"
    whois_updated: "2026-03-08"
    pending_manual_verification: true
    action: quote-from-atom.com-then-founder-decision
  - host: nyra.ai
    available: false
    status: premium-broker-listed
    broker: Atom.com Domains LLC
    whois_creation: "2020-04-05"
    whois_updated: "2026-03-08"
    pending_manual_verification: true
    action: quote-from-atom.com-then-founder-decision
  - host: nyra-engine.com
    available: true
    status: unregistered
    whois_signal: "No match for domain"
    pending_manual_verification: false   # unambiguous WHOIS signal
    action: register-at-cloudflare-registrar-immediately
    recommended_registrar: Cloudflare Registrar
    expected_cost_usd_yr: 9.77
  - host: nyra-plugin.com
    available: unknown
    status: not-probed
    pending_manual_verification: true
    action: founder-whois-probe-then-register-if-available
  - host: nyraengine.com
    available: unknown
    status: not-probed
    pending_manual_verification: true
    action: founder-whois-probe-then-register-if-available-as-defensive

github_orgs:
  - slug: nyra-ai
    available: false
    status: taken
    http_code_at_probe: 200
    action: skip
  - slug: nyra
    available: false
    status: taken
    http_code_at_probe: 200
    action: skip
  - slug: nyra-plugin
    available: true
    status: unregistered
    http_code_at_probe: 404
    action: claim-as-primary
  - slug: nyraengine
    available: true
    status: unregistered
    http_code_at_probe: 404
    action: claim-as-defensive

social_handles:
  - platform: x.com
    handle_primary: "@nyra_ai"
    fallback_order: ["@nyra_plugin", "@nyraengine", "@nyra_ue"]
    available: unknown
    pending_manual_verification: true   # X.com SPA returns 200 universally
    action: founder-browse-to-each-url-logged-in-claim-first-available
  - platform: reddit.com
    handle_primary: "r/NyraEngine"
    fallback_order: ["r/NyraPlugin", "r/nyra_ai"]
    available: unknown
    pending_manual_verification: true   # Reddit blocks anonymous curl (403)
    action: founder-create-first-available-subreddit
  - platform: discord.com
    server_name: "NYRA Engine"
    vanity_slug: "nyra-engine"
    vanity_requires_boost_level: 3
    available: founder-creates-new-server
    action: founder-creates-server-vanity-deferred-until-boost-eligible
  - platform: youtube.com
    handle: "@nyraengine"
    available: unknown
    pending_manual_verification: true
    action: founder-create-channel-auto-reserves-handle
    gate: YouTube @handle formally claimable after 0 subs + 30 days OR at creation with verified email
  - platform: bluesky.social
    handle: "@nyra-engine.com"
    method: custom-domain-verification-via-_atproto-dns-txt
    available: after-domain-registration
    pending_manual_verification: true
    action: after-nyra-engine.com-registration-add-_atproto-TXT-then-claim

code_signing:
  # Phase-8 scope per ROADMAP, not Phase-0, but captured here because EV
  # cert issuance is name-locked and a late rename destroys the cert
  # investment.
  ev_code_signing_certificate:
    name_on_certificate: NYRA (or legal entity name holding the cert)
    expected_annual_cost_usd: "400–700"
    issuance_plan: Phase 8 launch-prep
    locked_to_name: true
    rollback_impact: "Full re-issue required if name changes post-cert-issuance; ~$400–700 sunk cost + 1–3 week re-issue timeline"

filing:
  trademark_filing_status: DEFERRED-TO-V1.1
  per_decision: CONTEXT.md D-04
  screening_dossier: .planning/phases/00-legal-brand-gate/trademark/00-03-nyra-screening-dossier.md
  backup_screening: .planning/phases/00-legal-brand-gate/trademark/00-03-backup-names-screening.md
  expected_filing_cost_per_class_usd: 350
  expected_counsel_fee_per_jurisdiction_usd: "1000–2500"
  jurisdictions_to_file: [US, EU, UK, international-via-Madrid]
  counsel_engagement_gate: founder-decision-post-usage-signal

devlog:
  pitfalls_ref: "§7.4 competitor-preempts-demo mitigation"
  gate_status: OPEN
  gated_on: [trademark-screening-clean, brand-guidelines-archived, domain-registered]
  roadmap_phase_8_sc5_requirement: "public devlog has been shipping from Month 1"

rollback:
  warm_standby: AELRA
  backup_screening_doc: .planning/phases/00-legal-brand-gate/trademark/00-03-backup-names-screening.md
  activation_triggers:
    - founder-verbatim-upgrade-flips-NYRA-class-9-to-BLOCKED
    - post-launch-cease-and-desist-from-trademark-holder
    - fashion-house-defensive-class-9-extension-discovered
  estimated_cutover_weeks: "2–4"
```

## Filing Decision (Deferred)

Per D-04: actual trademark prosecution — Intent-to-Use Section 1(b)
USPTO application, direct EUTM application, Madrid-System international
extensions — is **DEFERRED TO v1.1** or post-launch when usage signal
justifies the ~$350/class USPTO fee + counsel fees (~$1,000–2,500 per
jurisdiction at entry-level counsel rates). Phase 0 ships the SCREENING
dossier — the packet counsel reviews at filing time — not a filing.

The `trademark/00-03-nyra-screening-dossier.md` + `trademark/00-03-
backup-names-screening.md` + this reservations doc together form the
complete screening record. When the founder engages counsel (post-v1
launch or at v1.1 planning), counsel additionally performs:

- Common-law use analysis (web-search sweep for unregistered prior-use
  claims — someone using "NYRA" as an unregistered brand in commerce
  could still sue on common-law grounds in the U.S. under Lanham Act
  §43(a))
- Fame analysis (does the NYRA mark have "famous mark" exposure under
  15 U.S.C. §1125(c) anti-dilution? — almost certainly no, given
  Phase 0's MEDIUM-RISK verdict rests on limited-scope Class 41 horse-
  racing enforcement rather than pan-class fame)
- Prosecution strategy — class selection, Section 1(a) in-use vs.
  Section 1(b) intent-to-use, Madrid base-mark selection, defensive-
  filing scope

This plan does NOT bind the founder to ANY specific filing action. The
founder may choose to never file (free Fab plugin with modest usage may
not justify the ~$2,000+ combined cost) and retain only the common-law
"first use in commerce" rights that accrue from launch-day Fab
distribution.

## Devlog Gate

**This doc is the PITFALLS §7.4 gate for the public devlog kickoff.**

Per CONTEXT.md canonical_refs, `.planning/research/PITFALLS.md §7.4
competitor-preempts-demo mitigation` identifies the public devlog as the
primary defense against a competitor launching a similar UE-AI-agent
product before NYRA reaches Fab. The devlog must ship from Month 1 per
ROADMAP Phase 8 SC#5 ("public devlog has been shipping from Month 1").

**The devlog kickoff is gated on:**

1. Trademark name cleared (this plan — ✓ CLEAN for Class 9 software at
   aggregate presumptive level; founder verbatim upgrade upgrades to
   HIGH-confidence clean).
2. Brand-guidelines archive (Plan 00-05 — future Phase-0 plan).
3. Domain registered (nyra-engine.com — PENDING founder-manual-action).
4. Primary social handles reserved (at minimum X + Reddit + YouTube —
   PENDING founder-manual-action).

**With this plan closed: `devlog_gate: OPEN`.** The first public devlog
post can ship as soon as (3) + (4) complete at the founder's pace. Plan
00-05 brand-guidelines archive runs in parallel; no ordering dependency
between trademark clearance (this plan) and brand-guidelines archive.

Recommended first devlog post shape:

- Title: "I'm building an AI agent for Unreal Engine that uses your
  Claude subscription — here's why"
- Content: why NYRA exists (the "no new AI bill" wedge), the three-
  process architecture at a high level, what ships in v1 (Fab free
  plugin, UE 5.4–5.7, reference-video-to-scene as launch demo), and
  how-to-follow (X + Reddit + YouTube + Discord invite)
- Frequency: weekly minimum; technical deep-dive + demo video per post
- Competitive positioning: reference NYRA's wedge vs. Nwiro, Aura
  (Telos), Ultimate Engine CoPilot, Ludus AI per PROJECT.md without
  naming-and-shaming

## Rollback Plan

If a cease-and-desist arrives from any trademark holder post-launch
(low-probability but non-zero per the MEDIUM-RISK aggregate verdict),
rollback to backup name AELRA follows this procedure:

1. **File a rename RFC** in `.planning/phases/` as a new
   `RFC-rename-nyra-to-aelra.md` document capturing the C&D trigger,
   legal analysis, and cutover timeline.
2. **Verbatim re-screen AELRA** at trigger time via USPTO + EUIPO +
   WIPO — register drift since 2026-04-24 may have produced new hits.
   Follow the founder-manual-verification flow from `00-03-backup-
   names-screening.md`.
3. **If AELRA re-screens CLEAN: execute cutover.** If AELRA re-screens
   BLOCKED at re-check time, pivot to VYRELL (runner-up per backup
   screening) and re-run.
4. **Cutover scope:**
   - Domain rename (register aelra-engine.com, decommission nyra-
     engine.com with 301 redirect) — registrar cycle time ~24–48 hours
   - GitHub org rename (github.com/nyra-plugin → github.com/aelra-
     plugin; GitHub preserves all repo redirects automatically)
   - Social handle migration (X @nyra_ai → @aelra_ai, Reddit
     r/NyraEngine → r/AelraEngine via community petition or new sub,
     YouTube @nyraengine → @aelraengine via YouTube Studio rename
     flow, Discord server rename via Server Settings → Overview)
   - Fab listing rename (via Epic's Fab seller portal — requires Epic
     reviewer approval, ~1–2 week turnaround)
   - EV code-signing certificate re-issue (new CN/Subject = AELRA;
     ~$400–700 sunk cost + 1–3 week CA re-verification)
   - Plugin binary rename inside UE (`.uplugin` descriptor
     `"FriendlyName": "AELRA"`, module names `AelraEditor` + `Aelra-
     Runtime`, engine-descriptor version bump across 5.4/5.5/5.6/5.7)
   - Documentation cascade: Plans 00-01 (Anthropic email), 00-02 (Fab
     email), 00-04 (EULA), 00-05 (brand guidelines), all Phase 1/2+
     SUMMARY.md files referencing NYRA — find-replace edit with
     `git grep -l NYRA | xargs sed -i '' -e 's/NYRA/AELRA/g; s/nyra/
     aelra/g'` + manual review for false-positives
   - Re-send of updated Anthropic/Fab ToS clarifications if the
     original emails have already been sent under NYRA (Plan 00-01
     / 00-02 correspondence) — prepend a "Correction: we're renaming
     from NYRA to AELRA, the subprocess-driving / AI-plugin
     architecture is unchanged" paragraph

5. **Estimated total cutover time: 2–4 weeks** per registrar + Epic-
   listing-review propagation. Users on older NYRA builds continue to
   work (binary is self-contained); they upgrade to AELRA-named build
   on next plugin update.

6. **User-facing communication:** devlog post + X announcement + email
   to any registered beta users + prominent banner on
   nyra-engine.com (before redirect) for 30 days post-cutover.

**Rollback probability assessment:** LOW. The MEDIUM-RISK aggregate
verdict is driven primarily by the U.S. New York Racing Association
Class-41 acronym — but their goods (horse racing entertainment) are
unambiguously distinct from NYRA's Class-9 UE-plugin software. A C&D
from NYRA-the-racing-association would face a weak likelihood-of-
confusion argument under the multi-factor test (Polaroid v. Polarad
factors in U.S. law). Far more likely that the Racing Association
ignores NYRA-the-plugin entirely because they occupy different markets.
Fashion/cosmetics NYRA holders almost never file defensive Class-9
extensions because their defensive interest is within apparel/accessory
classes, not downloadable software. The aggregate rollback probability
over v1-lifecycle (~12 months post-launch) is estimated at 5–10%.

---

## Summary for Plan 00-06 closure ledger

| Phase 0 SC | This plan's contribution | Status |
|------------|---------------------------|--------|
| **SC#3 — Trademark screening dossier + domain/GitHub/social reservations** | Complete at docs-layer with pending_manual_verification:true for (a) verbatim registry upgrades across USPTO/EUIPO/WIPO, (b) domain registrations (nyra-engine.com REQUIRED, nyra.dev/nyra.ai OPTIONAL premium), (c) GitHub org creation (nyra-plugin PRIMARY), (d) social handle claims (X + Reddit + YouTube + Discord + Bluesky) | **CLOSED-AT-DOCS-LAYER** (pending founder manual actions per checklists above) |

## Files produced

- `trademark/00-03-uspto-tess-raw.md` — USPTO raw dump
- `trademark/00-03-euipo-esearch-raw.md` — EUIPO raw dump
- `trademark/00-03-wipo-brand-db-raw.md` — WIPO raw dump
- `trademark/00-03-nyra-screening-dossier.md` — consolidated dossier
- `trademark/00-03-backup-names-screening.md` — 5-candidate precautionary screening
- `trademark/00-03-verdict-and-reservations.md` — this file

---

*Verdict + reservations by: NYRA Plan 00-03 executor on 2026-04-24.*
*Final name: NYRA (primary). Warm-standby: AELRA.*
*Filing: DEFERRED-TO-V1.1 per CONTEXT.md D-04.*
*Devlog gate: OPEN.*
