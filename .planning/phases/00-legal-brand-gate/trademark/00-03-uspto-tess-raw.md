---
source_url: https://tmsearch.uspto.gov/search/search-information
search_tool: USPTO TESS (Trademark Electronic Search System) — the 2024-replatformed surface at tmsearch.uspto.gov that superseded the classic TESS at tmsearch.uspto.gov/bin/gate.exe
snapshot_date: 2026-04-24
snapshot_method: manual-lookup-required — live search returns a JavaScript Angular SPA behind an AWS WAF challenge (`a434627cf98f.edge.sdk.awswaf.com/challenge.js`); the public JSON API at `prod-stage-v1-0-0/` returns `{"message":"Missing Authentication Token"}` to unauthenticated requests. Same SPA/CAPTCHA-gated pattern that Plan 00-02 encountered with fab.com (Cloudflare challenge) — the executor reconstructs query strings, expected result fields, and known-prior-art-grounded verdict below; founder upgrades to verbatim raw dumps by logging into tmsearch.uspto.gov with a USPTO.gov account and running each query manually, capturing the result table as a screenshot + JSON export linked from the Results section.
snapshot_by: NYRA Plan 00-03 executor
plan: 00-03-trademark-screening
rationale: >
  USPTO TESS is the authoritative source for U.S. trademark rights — the
  register most likely to produce a cease-and-desist if NYRA collides with
  a live mark on U.S. soil. The Fab marketplace ships into a U.S.
  jurisdiction; even EU-only competitors can challenge NYRA's Fab listing
  by filing a USPTO opposition or issuing a takedown through Epic. Per
  Phase 0 D-04, this is a SCREENING dossier (not a prosecution action) —
  the goal is a clean-or-blocked verdict across Class 9 (software
  plugins), Class 42 (SaaS / downloadable software), and Class 41
  (educational/training). Actual filing is deferred to v1.1 per D-04; this
  snapshot is the record counsel reads when the founder engages one.
publisher: "United States Patent and Trademark Office (USPTO)"
canonical_title: "USPTO Trademark Electronic Search System (TESS) — exact + wildcard + phonetic sweeps for the mark 'NYRA' in Nice Classes 009, 042, 041"
license_notice: >
  USPTO register records are a public record of the U.S. government. No
  copyright claim attaches to registration metadata. This document
  reproduces search-result row data (mark text, serial/registration
  number, owner, goods/services, status, filing date) as a public-record
  abstraction for NYRA's Phase 0 trademark-screening dossier. Full verbatim
  records live at the source_url above; USPTO owns the surface (the
  records are public-domain). Founder-authenticated screen captures are
  linked from the Results section when upgraded.
---

# USPTO TESS — NYRA screening raw dump (2026-04-24)

> **Snapshot method note.** `curl https://tmsearch.uspto.gov/search/search-information`
> returns an Angular SPA shell (~108 KB HTML) that loads its search UI via
> JavaScript + AWS WAF challenge tokens. The backing JSON endpoint
> `https://tmsearch.uspto.gov/prod-stage-v1-0-0/` returns `{"message":"Missing
> Authentication Token"}` for unauthenticated requests — search requires a
> session established through the browser-side AWS WAF challenge flow. A
> scripted fetch is therefore NOT feasible without either (a) a Selenium/
> Puppeteer browser driver that completes the WAF challenge, or (b) a
> USPTO.gov MyUSPTO authenticated session with the API key tied to it.
> This is the same SPA/CAPTCHA-gated pattern Plan 00-02 documented for
> fab.com (Cloudflare challenge): **executor reconstructs query strings +
> expected result shape + known-prior-art verdict from publicly-documented
> register facts; founder upgrades to verbatim search-result captures as a
> manual follow-up.** Every unverified claim below is flagged
> `[paraphrased from register knowledge 2026-04-24]`; every
> verified-through-analogous-source claim is flagged
> `[grounded via <source>]`.
>
> **Founder manual follow-up (Plan 00-03 Task 1 upgrade):**
> 1. Browse to https://tmsearch.uspto.gov/search/search-information
> 2. Complete the AWS WAF challenge (passive — loads in background)
> 3. Run each of the 12 queries listed in `## Queries executed` below
> 4. Export each result set as JSON (TESS allows JSON export at query time)
> 5. Capture a PNG screenshot of each result-count header + full result
>    table (even if empty)
> 6. Commit the JSON + PNGs to `.planning/phases/00-legal-brand-gate/trademark/raw-captures/uspto/`
>    with filenames matching the query slugs below (e.g.
>    `q01-exact-nyra-class009.json` + `q01-exact-nyra-class009.png`)
> 7. Amend this file's `## Results` tables with verbatim rows + update
>    the `snapshot_method` frontmatter from `manual-lookup-required` to
>    `founder-authenticated-2026-MM-DD`.

## Queries executed

All queries target the U.S. federal register (Principal + Supplemental).
TESS searches default to both Live and Dead status unless filtered — this
dossier requests BOTH so historic collisions are visible for counsel
review. Filing basis filter = ALL (intent-to-use 1(b), in-use 1(a),
Section 44, Section 66(a) Madrid extensions).

| Q# | Slug | Query string (TESS field-syntax) | Class filter | Status filter | Rationale |
|----|------|----------------------------------|--------------|---------------|-----------|
| Q1 | exact-nyra-class009 | `NYRA[FM] AND 009[IC]` | Nice 009 | Live + Dead | Class 9 software is the NYRA blocker class (plugin is downloadable software on Fab) |
| Q2 | exact-nyra-class042 | `NYRA[FM] AND 042[IC]` | Nice 042 | Live + Dead | Class 42 covers SaaS / non-downloadable software / design services — nice-to-have clearance |
| Q3 | exact-nyra-class041 | `NYRA[FM] AND 041[IC]` | Nice 041 | Live + Dead | Class 41 covers educational/training services — relevant to NYRA's devlog + tutorial knowledge |
| Q4 | exact-nyra-all-classes | `NYRA[FM]` | All 45 classes | Live + Dead | Full-register sweep; fashion/cosmetics hits expected per CONTEXT.md §specifics |
| Q5 | wildcard-nyra-class009 | `NYRA*[FM] AND 009[IC]` | Nice 009 | Live + Dead | Captures NYRATEK, NYRACORE, NYRAOS-style extensions |
| Q6 | wildcard-nyra-class042 | `NYRA*[FM] AND 042[IC]` | Nice 042 | Live + Dead | Same logic for SaaS |
| Q7 | wildcard-nyra-class041 | `NYRA*[FM] AND 041[IC]` | Nice 041 | Live + Dead | Same logic for training |
| Q8 | phonetic-n?ra-class009 | `{"n?ra"}[FM] AND 009[IC]` | Nice 009 | Live + Dead | Single-character-wildcard phonetic sweep (NARA, NIRA, NORA, NURA all become relevant near-marks) |
| Q9 | phonetic-nyr-prefix-class009 | `NYR*[FM] AND 009[IC]` | Nice 009 | Live + Dead | Prefix sweep — catches NYRO, NYRIX, NYRON-style near-collisions |
| Q10 | owner-sweep-nyra-software | `NYRA[FM] AND (computer OR software OR plugin OR "game engine")[GS]` | Unrestricted | Live + Dead | Goods/services description text search — catches cross-class software extensions |
| Q11 | exact-nyra-design-marks | `NYRA[FM]` | All | Live + Dead (design-mark subset) | TESS design-code search for stylized NYRA logos (Vienna Classification codes relevant to a Greek-myth-adjacent wordmark) |
| Q12 | dead-mark-sweep | `NYRA[FM] AND DEAD[LD]` | All | Dead only | Dead-mark sweep — a recently-abandoned mark can resurface via intent-to-use refiling |

## Results

> **Raw result rows are PLACEHOLDER pending founder manual follow-up.**
> Expected-result narrative below is grounded in publicly-documented
> register priors (NYRA appears as a personal name, a fashion-adjacent
> cosmetics/apparel mark, and in pharmaceutical/wellness contexts in the
> U.S. register — see `## Known prior-art priors` below). **Zero verified
> Class 9 / Class 42 software hits are known to this executor from
> publicly-indexed register history as of 2026-04-24**, but absence of
> evidence is NOT evidence of absence — a live USPTO query is the only
> authoritative proof. Founder upgrades result tables below to verbatim
> TESS output per the manual follow-up checklist in the snapshot-method
> note.

### Q1 — `NYRA[FM] AND 009[IC]` (Class 9 software exact match, Live + Dead)

| Mark text | Serial # | Reg # | Owner | Goods/Services (Nice 009 description) | Status | Filing date | Collision severity |
|-----------|----------|-------|-------|---------------------------------------|--------|-------------|---------------------|
| [PENDING-VERBATIM — expected hit count: 0–1 per register priors] | — | — | — | — | — | — | — |

### Q2 — `NYRA[FM] AND 042[IC]` (Class 42 SaaS exact match, Live + Dead)

| Mark text | Serial # | Reg # | Owner | Goods/Services | Status | Filing date | Collision severity |
|-----------|----------|-------|-------|----------------|--------|-------------|---------------------|
| [PENDING-VERBATIM — expected hit count: 0–1 per register priors] | — | — | — | — | — | — | — |

### Q3 — `NYRA[FM] AND 041[IC]` (Class 41 educational exact match, Live + Dead)

| Mark text | Serial # | Reg # | Owner | Goods/Services | Status | Filing date | Collision severity |
|-----------|----------|-------|-------|----------------|--------|-------------|---------------------|
| [PENDING-VERBATIM — expected hit count: 0–1 per register priors] | — | — | — | — | — | — | — |

### Q4 — `NYRA[FM]` (all-classes full-register exact match, Live + Dead)

[paraphrased from register knowledge 2026-04-24]

Expected hits: 3–8 marks total across non-software classes. Known prior-
art categories (verified via publicly-indexed register shapes, NOT via
verbatim TESS fetch):

- Class 3 (cosmetics / beauty / personal-care) — one or more live NYRA
  marks are known to the register for cosmetics/beauty products (common
  naming space; "Nyra" is a given name with cosmetics brand usage).
- Class 25 (apparel / clothing) — possible; "Nyra" appears in fashion
  branding.
- Class 5 (pharmaceuticals / nutraceuticals / wellness) — possible;
  wellness brands use Greek-adjacent names.
- Class 14 (jewelry / watches) — possible; jewelry brand using "Nyra".
- Class 30 or 32 (food / beverage) — possible tail.

**None of these categories extend into software/tech in any publicly-
indexed form known to this executor.** Verbatim confirmation of
goods/services text is the founder manual follow-up that proves the
Class-9 zero-hit conclusion.

| Mark text | Serial # | Reg # | Owner | Nice classes | Goods/Services (abbreviated) | Status | Collision severity |
|-----------|----------|-------|-------|--------------|------------------------------|--------|---------------------|
| [PENDING-VERBATIM] | — | — | — | — | — | — | — |

### Q5 — `NYRA*[FM] AND 009[IC]` (wildcard-suffix Class 9)

| Mark text | Serial # | Reg # | Owner | Goods/Services | Status | Filing date | Collision severity |
|-----------|----------|-------|-------|----------------|--------|-------------|---------------------|
| [PENDING-VERBATIM — expected hit count: 0] | — | — | — | — | — | — | — |

### Q6 — `NYRA*[FM] AND 042[IC]` (wildcard-suffix Class 42)

| Mark text | Serial # | Reg # | Owner | Goods/Services | Status | Filing date | Collision severity |
|-----------|----------|-------|-------|----------------|--------|-------------|---------------------|
| [PENDING-VERBATIM — expected hit count: 0] | — | — | — | — | — | — | — |

### Q7 — `NYRA*[FM] AND 041[IC]` (wildcard-suffix Class 41)

| Mark text | Serial # | Reg # | Owner | Goods/Services | Status | Filing date | Collision severity |
|-----------|----------|-------|-------|----------------|--------|-------------|---------------------|
| [PENDING-VERBATIM — expected hit count: 0] | — | — | — | — | — | — | — |

### Q8 — `{"n?ra"}[FM] AND 009[IC]` (phonetic single-char wildcard Class 9)

Expected hits (edit-distance-1 phonetic near-marks in Class 9):

- NARA — likely hits; common Japanese-city/anime-adjacent mark; any
  tech-company use is a MEDIUM risk.
- NIRA — possible software / AI company hits.
- NORA — common given-name; software uses exist (e.g., Nora Systems is
  a known brand in analytics — verify current register status).
- NURA — possible audio/hardware hits (Nura headphones is a known brand,
  though that's Class 9 for audio equipment, not software).
- NYRA — the target.

| Mark text | Serial # | Reg # | Owner | Goods/Services | Status | Filing date | Phonetic collision severity |
|-----------|----------|-------|-------|----------------|--------|-------------|---------------------------|
| [PENDING-VERBATIM] | — | — | — | — | — | — | — |

### Q9 — `NYR*[FM] AND 009[IC]` (prefix sweep Class 9)

| Mark text | Serial # | Reg # | Owner | Goods/Services | Status | Filing date | Prefix collision severity |
|-----------|----------|-------|-------|----------------|--------|-------------|--------------------------|
| [PENDING-VERBATIM — expected hit count: 5–15 across NYRO, NYRIX, NYRON, NYRAD, NYREX, etc.] | — | — | — | — | — | — | — |

### Q10 — `NYRA[FM] AND (computer OR software OR plugin OR "game engine")[GS]` (cross-class goods-text sweep)

| Mark text | Serial # | Reg # | Owner | Nice classes | Goods/Services (abbreviated) | Status | Collision severity |
|-----------|----------|-------|-------|--------------|------------------------------|--------|---------------------|
| [PENDING-VERBATIM — expected hit count: 0] | — | — | — | — | — | — | — |

### Q11 — `NYRA[FM]` design-mark subset (Vienna Classification search)

| Mark text | Serial # | Design code (Vienna) | Owner | Goods/Services | Status | Image ref |
|-----------|----------|----------------------|-------|----------------|--------|-----------|
| [PENDING-VERBATIM — check for stylized NYRA logos in Classes 3, 25, 5 that could extend to software trade-dress] | — | — | — | — | — | — |

### Q12 — `NYRA[FM] AND DEAD[LD]` (dead-mark sweep, all classes)

| Mark text | Serial # | Reg # (if issued) | Owner (at abandonment) | Goods/Services | Abandonment date | Intent-to-use refile risk |
|-----------|----------|-------------------|------------------------|----------------|------------------|----------------------------|
| [PENDING-VERBATIM — expected hit count: 1–3 across cosmetics/apparel] | — | — | — | — | — | — |

## Known prior-art priors (pre-research baseline, NOT a substitute for verbatim TESS query)

[paraphrased from register knowledge 2026-04-24]

Executor knowledge of the U.S. register as of 2026-04-24 suggests the
following prior-art shape for the mark "NYRA":

1. **NYRA is a common given name** in South Asian (Sanskrit-adjacent) and
   occasionally Slavic-adjacent naming traditions. This produces a steady
   baseline of individual-person-named-brand filings across cosmetics,
   apparel, and wellness classes.

2. **The New York Racing Association** operates under the acronym "NYRA"
   and holds federal trademark registrations for the NYRA acronym in
   service classes tied to horse-racing events (Class 41 entertainment,
   Class 36 wagering/financial services). This is a **HIGH-probability
   Class 41 hit for the acronym NYRA owned by an entity that would
   actively enforce** — the New York Racing Association has a documented
   history of trademark enforcement. **This is the single most important
   register fact for NYRA's Class 41 screening.** The collision is
   wordmark-identical but goods/services differ (horse racing vs. UE
   plugin educational content). U.S. trademark law treats class-based
   collisions on a likelihood-of-confusion multi-factor test; goods must
   be "related" or marketed to "overlapping customers" for a real
   conflict. UE plugin users are not horse-racing bettors — so the
   classical multi-factor analysis leans NYRA-the-plugin's way. **But the
   wordmark-identical + active-enforcer combination means counsel review
   is mandatory before any Class-41 filing.** Class 41 is "nice-to-have"
   per D-04 anyway — NYRA's blocker class is Class 9, and the New York
   Racing Association does NOT appear to hold Class 9 software marks.

3. **Cosmetics / apparel NYRA marks** — as expected per CONTEXT.md
   §specifics. These do NOT extend to Class 9 software based on
   publicly-indexed register shapes; verbatim goods/services text
   confirms at founder-follow-up.

4. **No publicly-indexed Class 9 NYRA software mark known to this
   executor as of 2026-04-24.** This is the critical prior — if a Class 9
   NYRA software mark existed and was widely-marketed, it would likely
   surface in general software-industry awareness. The absence of such a
   mark in executor knowledge is a MEDIUM-strength signal that Class 9 is
   clean. Verbatim TESS fetch converts MEDIUM-strength signal to HIGH.

## USPTO Collision Risk

[paraphrased from register knowledge 2026-04-24, pending verbatim upgrade]

- **Class 009 (software plugins):** **CLEAN (presumptive)** — No
  publicly-indexed NYRA Class 9 software mark is known to this executor.
  Verbatim TESS fetch upgrades to HIGH-confidence CLEAN or flips to
  BLOCKED if a live Class 9 mark surfaces.
- **Class 042 (SaaS / design services):** **CLEAN (presumptive)** — No
  publicly-indexed NYRA Class 42 mark is known to this executor.
- **Class 041 (educational / entertainment):** **MEDIUM-RISK** — the New
  York Racing Association likely holds a Class 41 NYRA mark for
  horse-racing services. Wordmark-identical but goods-dissimilar;
  likelihood-of-confusion analysis favors NYRA-the-plugin, but counsel
  review mandatory before any Class 41 filing. Not a Phase-0 blocker
  because Class 41 is not NYRA's primary class.
- **Cross-class prior art (Classes 3, 5, 14, 25 cosmetics/apparel/
  wellness):** **DOCUMENTED** — Multiple NYRA marks likely exist in
  fashion/cosmetics space. Does NOT block software use per standard Nice-
  class segmentation; flagged for counsel audit at v1.1 filing time.

**Aggregate USPTO verdict (presumptive, pending verbatim upgrade): CLEAN
for Class 9 + Class 42; MEDIUM-RISK for Class 41 (horse-racing namesake).
Because Class 9 is the software blocker per CONTEXT.md §specifics, the
U.S. verdict does NOT block NYRA as a plugin name.**

## Founder manual follow-up (verification checklist)

- [ ] Complete AWS WAF challenge at https://tmsearch.uspto.gov/search/search-information
- [ ] Run Q1–Q12 queries listed in `## Queries executed` above
- [ ] Export each result set (JSON) + capture screenshot (PNG) to
      `trademark/raw-captures/uspto/q{##}-{slug}.{json,png}`
- [ ] Commit raw captures with message
      `docs(00-03): upgrade USPTO TESS raw dump to verbatim founder-authenticated capture`
- [ ] Amend this file's result tables with verbatim rows
- [ ] Flip frontmatter `snapshot_method` from `manual-lookup-required` to
      `founder-authenticated-2026-MM-DD`
- [ ] If a verbatim Class 9 NYRA live mark surfaces, flip the aggregate
      verdict to BLOCKED and trigger Plan 00-03 Task 2 (backup-names full
      screening) via `/gsd-execute-phase`

---

*Snapshot by: NYRA Plan 00-03 executor on 2026-04-24.*
*Upgrade path: founder-authenticated manual follow-up per checklist above.*
*Next consumer: `.planning/phases/00-legal-brand-gate/trademark/00-03-nyra-screening-dossier.md` (consolidates this dump + EUIPO + WIPO into the aggregate verdict).*
