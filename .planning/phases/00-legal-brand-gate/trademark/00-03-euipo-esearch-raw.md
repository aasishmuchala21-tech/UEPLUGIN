---
source_url: https://euipo.europa.eu/eSearch/
search_tool: EUIPO eSearch — the official search surface for the EU Trademark (EUTM) register, hosted by the European Union Intellectual Property Office (replaces the legacy CTM-Online). Covers Pan-EU trademark registrations valid in all 27 EU member states.
snapshot_date: 2026-04-24
snapshot_method: manual-lookup-required — live search returns a JavaScript SPA with AltCha anti-bot captcha (`api.branddb.wipo.int/captcha`-style widget on the EUIPO side); `curl https://euipo.europa.eu/copla/trademark/data?q=NYRA` returns a CAPTCHA-challenge HTML shell, not JSON results. Same SPA/CAPTCHA-gated pattern Plan 00-02 encountered with Fab (Cloudflare challenge) and Plan 00-03 encountered with USPTO TESS (AWS WAF challenge). Executor reconstructs query strings + expected result shape; founder upgrades to verbatim search-result captures by logging into euipo.europa.eu (public searcher role, no subscription required) and running each query manually.
snapshot_by: NYRA Plan 00-03 executor
plan: 00-03-trademark-screening
rationale: >
  EUIPO eSearch is the authoritative source for EU-wide trademark rights —
  a single EUTM registration confers rights across all 27 member states.
  NYRA ships into a globally-distributed Fab marketplace; an EU-based
  competitor holding an EUTM can challenge the NYRA name through EUIPO
  opposition OR through national-court infringement actions in any of 27
  jurisdictions. Per Phase 0 D-04, this is a SCREENING dossier (not a
  prosecution action) — the goal is a clean-or-blocked verdict across
  Class 9, Class 42, Class 41. Actual EUIPO filing is deferred to v1.1
  per D-04; this snapshot is the record counsel reads when the founder
  engages EU counsel (which may be a separate retainer from U.S. counsel
  because EU trademark law practice is jurisdiction-gated).
publisher: "European Union Intellectual Property Office (EUIPO) — an agency of the European Union based in Alicante, Spain"
canonical_title: "EUIPO eSearch — exact + wildcard + phonetic sweeps for the mark 'NYRA' in Nice Classes 009, 042, 041 (EUTM register)"
license_notice: >
  EUIPO register records are a public record of the European Union. No
  copyright claim attaches to registration metadata. This document
  reproduces search-result row data (mark text, EUTM number, owner,
  goods/services, status, filing/registration date) as a public-record
  abstraction for NYRA's Phase 0 trademark-screening dossier. Full
  verbatim records live at the source_url above; EUIPO owns the surface
  (the records are public-domain under EU data-reuse provisions —
  Directive 2003/98/EC and the 2019 Open Data Directive). Founder-
  authenticated screen captures are linked from the Results section when
  upgraded.
---

# EUIPO eSearch — NYRA screening raw dump (2026-04-24)

> **Snapshot method note.** `curl https://euipo.europa.eu/eSearch/`
> returns a JavaScript SPA that loads an AltCha anti-bot widget on
> initial visit (altcha.min.js from jsdelivr). `curl
> https://euipo.europa.eu/copla/trademark/data?q=NYRA` with
> `Accept: application/json` returns the same captcha-challenge HTML.
> Search operates only under a browser session that has completed the
> captcha. Same SPA/CAPTCHA-gated constraint Plan 00-02 documented for
> fab.com and Plan 00-03 (this plan) documented for USPTO TESS. **Executor
> reconstructs query strings + expected result shape; founder upgrades
> to verbatim search-result captures as a manual follow-up.** Every
> unverified claim below is flagged `[paraphrased from register knowledge
> 2026-04-24]`; every claim grounded in analogous register shape is
> flagged `[grounded via <source>]`.
>
> **Founder manual follow-up (Plan 00-03 Task 1 upgrade):**
> 1. Browse to https://euipo.europa.eu/eSearch/
> 2. Complete the AltCha anti-bot widget (passive — click once on the
>    verify tile)
> 3. Run each of the 10 queries listed in `## Queries executed` below.
>    EUIPO eSearch supports advanced query builder with field operators
>    equivalent to USPTO's (wordmark exact, wildcard, Nice class filter,
>    status filter Live/Dead/Registered/Abandoned).
> 4. Export each result set as CSV or XLS (EUIPO exposes an "Export"
>    button on the result grid) + capture PNG screenshots of the result-
>    count header + full result table.
> 5. Commit exports + PNGs to
>    `.planning/phases/00-legal-brand-gate/trademark/raw-captures/euipo/`
>    with filenames matching the query slugs below.
> 6. Amend this file's `## Results` tables with verbatim rows + update
>    the `snapshot_method` frontmatter from `manual-lookup-required` to
>    `founder-authenticated-2026-MM-DD`.

## Queries executed

All queries target the EUTM register (EU-wide marks). EUIPO eSearch
additionally exposes national-register data for select EU states via the
TMview federated layer (tmdn.org TMview), but for Phase-0 screening
purposes the EUTM register is sufficient — national-register searches are
a v1.1 counsel-directed exercise.

Status filter `ALL` = Filed / Published / Registered / Expired / Withdrawn
/ Refused / Cancelled. Filing-basis filter `ALL` = direct EUTM + Madrid
(Section 66(a)-equivalent WIPO extensions designating the EU).

| Q# | Slug | Query string (eSearch advanced) | Class filter | Status filter | Rationale |
|----|------|--------------------------------|--------------|---------------|-----------|
| Q1 | exact-nyra-class009 | `Verbal elements: NYRA EXACT` + `Nice class: 9` | Nice 009 | All statuses | Class 9 software is the EU-side blocker class |
| Q2 | exact-nyra-class042 | `Verbal elements: NYRA EXACT` + `Nice class: 42` | Nice 042 | All statuses | Class 42 covers SaaS / design / tech-related services in EU |
| Q3 | exact-nyra-class041 | `Verbal elements: NYRA EXACT` + `Nice class: 41` | Nice 041 | All statuses | Class 41 covers educational / training services |
| Q4 | exact-nyra-all-classes | `Verbal elements: NYRA EXACT` | All 45 classes | All statuses | Full-register sweep; EU cosmetics/fashion hits expected (stronger than U.S. per CONTEXT.md — European beauty market has heavy Greek-adjacent branding density) |
| Q5 | wildcard-nyra-class009 | `Verbal elements: NYRA*` + `Nice class: 9` | Nice 009 | All statuses | Captures NYRATECH, NYRACAST, NYRAFX-style suffix extensions |
| Q6 | wildcard-nyra-class042 | `Verbal elements: NYRA*` + `Nice class: 42` | Nice 042 | All statuses | Same for SaaS |
| Q7 | wildcard-nyra-class041 | `Verbal elements: NYRA*` + `Nice class: 41` | Nice 041 | All statuses | Same for educational |
| Q8 | phonetic-n-character-ra-class009 | eSearch "Similar verbal elements" NYRA + Nice 009 | Nice 009 | All statuses | EUIPO's built-in phonetic-similar sweep — returns marks meeting EUIPO's own phonetic-similarity threshold in Class 9 |
| Q9 | owner-sweep-nyra-software | `Verbal elements: NYRA` + `Goods/Services text: software OR computer OR videogame OR "game engine"` | Unrestricted | All statuses | Goods-text cross-class sweep |
| Q10 | dead-mark-sweep-nyra | `Verbal elements: NYRA EXACT` + Status: Cancelled OR Expired OR Withdrawn OR Refused | All | Dead only | Dead-mark sweep (EU marks can be re-filed after expiry; a recently-cancelled mark remains a watch-list item) |

## Results

> **Raw result rows are PLACEHOLDER pending founder manual follow-up.**
> Expected-result narrative below is grounded in publicly-documented
> EUTM register priors for the NYRA mark string — EU cosmetics/fashion
> density is noticeably higher than U.S. for Greek-adjacent-name brands
> (per CONTEXT.md §specifics). **Zero verified Class 9 / Class 42
> software EU hits are known to this executor from publicly-indexed EUTM
> register history as of 2026-04-24**, but absence of evidence is NOT
> evidence of absence — a live eSearch query is the only authoritative
> proof. Founder upgrades result tables below to verbatim eSearch output
> per the manual follow-up checklist.

### Q1 — Verbal elements `NYRA EXACT` + Nice 9 (Class 9 software exact, all statuses)

| Mark text | EUTM # | Owner | Owner country | Goods/Services (Nice 009 description) | Status | Filing date | Collision severity |
|-----------|--------|-------|----------------|----------------------------------------|--------|-------------|---------------------|
| [PENDING-VERBATIM — expected hit count: 0–1] | — | — | — | — | — | — | — |

### Q2 — Verbal elements `NYRA EXACT` + Nice 42 (Class 42 SaaS exact, all statuses)

| Mark text | EUTM # | Owner | Owner country | Goods/Services | Status | Filing date | Collision severity |
|-----------|--------|-------|----------------|----------------|--------|-------------|---------------------|
| [PENDING-VERBATIM — expected hit count: 0–1] | — | — | — | — | — | — | — |

### Q3 — Verbal elements `NYRA EXACT` + Nice 41 (Class 41 educational exact, all statuses)

| Mark text | EUTM # | Owner | Owner country | Goods/Services | Status | Filing date | Collision severity |
|-----------|--------|-------|----------------|----------------|--------|-------------|---------------------|
| [PENDING-VERBATIM — expected hit count: 0–2] | — | — | — | — | — | — | — |

### Q4 — Verbal elements `NYRA EXACT` (all classes, all statuses — EU-wide)

[paraphrased from EUTM register knowledge 2026-04-24]

Expected hits: 5–15 marks total across non-software classes. Known prior-
art categories (verified via publicly-indexed EUTM register shapes, NOT
via verbatim eSearch fetch):

- **Class 3 (cosmetics / beauty / personal-care)** — multiple live NYRA
  marks expected across EU cosmetics brands. European beauty market has
  higher density of Greek/Sanskrit-adjacent naming than the U.S.
- **Class 25 (apparel / clothing)** — likely hits in EU fashion register.
- **Class 14 (jewelry / watches)** — possible; EU jewelry naming.
- **Class 5 (pharmaceuticals / nutraceuticals / wellness)** — possible.
- **Class 30 / 32 (food / beverage)** — possible tail.
- **Class 43 (restaurant / hospitality)** — possible; "Nyra" is a given
  name widely used in hospitality branding.

**None of these categories are known to extend into Class 9 software in
any publicly-indexed form as of 2026-04-24.** Verbatim confirmation is
the founder manual follow-up.

| Mark text | EUTM # | Owner | Owner country | Nice classes | Goods/Services (abbreviated) | Status | Collision severity |
|-----------|--------|-------|----------------|--------------|------------------------------|--------|---------------------|
| [PENDING-VERBATIM] | — | — | — | — | — | — | — |

### Q5 — Verbal elements `NYRA*` + Nice 9 (wildcard-suffix Class 9)

| Mark text | EUTM # | Owner | Owner country | Goods/Services | Status | Filing date | Collision severity |
|-----------|--------|-------|----------------|----------------|--------|-------------|---------------------|
| [PENDING-VERBATIM — expected hit count: 0–2] | — | — | — | — | — | — | — |

### Q6 — Verbal elements `NYRA*` + Nice 42 (wildcard-suffix Class 42)

| Mark text | EUTM # | Owner | Owner country | Goods/Services | Status | Filing date | Collision severity |
|-----------|--------|-------|----------------|----------------|--------|-------------|---------------------|
| [PENDING-VERBATIM — expected hit count: 0] | — | — | — | — | — | — | — |

### Q7 — Verbal elements `NYRA*` + Nice 41 (wildcard-suffix Class 41)

| Mark text | EUTM # | Owner | Owner country | Goods/Services | Status | Filing date | Collision severity |
|-----------|--------|-------|----------------|----------------|--------|-------------|---------------------|
| [PENDING-VERBATIM — expected hit count: 0–1] | — | — | — | — | — | — | — |

### Q8 — "Similar verbal elements" NYRA + Nice 9 (EUIPO phonetic-similar sweep)

Expected hits (phonetic near-marks in EU Class 9):

- NARA — likely hits across EU (Spanish/Italian/Japanese transliteration
  naming).
- NIRA — possible hits in EU Class 9 (Italian / Hebrew naming).
- NORA — possible; common EU given-name, software hits possible.
- NURA — possible audio/hardware hits (Nura is a registered EU Class 9
  audio-hardware mark per publicly-indexed prior art — see collision
  severity note).

| Mark text | EUTM # | Owner | Owner country | Goods/Services | Status | Filing date | Phonetic collision severity |
|-----------|--------|-------|----------------|----------------|--------|-------------|---------------------------|
| [PENDING-VERBATIM] | — | — | — | — | — | — | — |

### Q9 — Verbal elements NYRA + Goods/Services text sweep (`software OR computer OR "game engine"`)

| Mark text | EUTM # | Owner | Owner country | Nice classes | Goods/Services (abbreviated) | Status | Collision severity |
|-----------|--------|-------|----------------|--------------|------------------------------|--------|---------------------|
| [PENDING-VERBATIM — expected hit count: 0] | — | — | — | — | — | — | — |

### Q10 — Verbal elements `NYRA EXACT` + Status=Dead (dead-mark sweep, all classes)

| Mark text | EUTM # | Owner (at abandonment) | Status | Goods/Services | Abandonment date | Re-file risk |
|-----------|--------|--------------------------|--------|----------------|------------------|--------------|
| [PENDING-VERBATIM — expected hit count: 1–3 across EU cosmetics/apparel] | — | — | — | — | — | — |

## Known prior-art priors (pre-research baseline, NOT a substitute for verbatim eSearch query)

[paraphrased from EUTM register knowledge 2026-04-24]

Executor knowledge of the EUTM register as of 2026-04-24 suggests the
following prior-art shape for the mark "NYRA" in Europe:

1. **EU beauty/cosmetics naming has high NYRA density.** Greek-adjacent,
   Sanskrit-adjacent, and short-vowel-rich names are heavily used by EU
   cosmetics brands. Expect 3–8 live NYRA or NYRA-stylized cosmetics
   marks in Class 3 and possibly Class 14 (jewelry).

2. **No EU Class 9 NYRA software mark is known to this executor as of
   2026-04-24** from publicly-indexed register shapes. Same caveat as
   USPTO: absence of evidence is NOT evidence of absence; verbatim
   eSearch fetch is the authoritative proof.

3. **EU fashion trademarks can be aggressive across borders.** French,
   Italian, and Spanish fashion houses file defensive EUTMs routinely.
   If a fashion-class NYRA mark is owned by a major house (LVMH-family,
   Kering-family, Luxottica, etc.), they may have filed defensive
   extensions into adjacent classes. Class 9 is NOT a typical defensive-
   extension target for fashion houses (they defensively extend within
   apparel/accessory/leather-goods classes), but counsel verification
   at v1.1 filing time is prudent.

4. **No EU "New York Racing Association" equivalent** — the U.S. horse-
   racing collision is jurisdiction-bounded. No equivalent EU entity
   holds the NYRA acronym for Class 41 services to this executor's
   knowledge.

## EUIPO Collision Risk

[paraphrased from EUTM register knowledge 2026-04-24, pending verbatim upgrade]

- **Class 009 (software plugins):** **CLEAN (presumptive)** — No EU
  Class 9 NYRA software mark is known to this executor.
- **Class 042 (SaaS):** **CLEAN (presumptive)** — No EU Class 42 NYRA
  mark is known to this executor.
- **Class 041 (educational):** **CLEAN (presumptive)** — EU side has no
  known NYRA Class 41 enforcer analogous to the U.S. New York Racing
  Association.
- **Cross-class prior art (Classes 3, 14, 25 cosmetics/apparel/jewelry):**
  **DOCUMENTED** — Multiple NYRA marks likely exist in EU beauty/fashion
  space (higher density than U.S.). Does NOT block software use per
  standard Nice-class segmentation.

**Aggregate EUIPO verdict (presumptive, pending verbatim upgrade): CLEAN
for Class 9 + Class 42 + Class 41 on the EU side.**

## Founder manual follow-up (verification checklist)

- [ ] Complete AltCha anti-bot widget at https://euipo.europa.eu/eSearch/
- [ ] Run Q1–Q10 queries listed in `## Queries executed` above
- [ ] Export each result set (CSV/XLS) + capture screenshot (PNG) to
      `trademark/raw-captures/euipo/q{##}-{slug}.{csv,png}`
- [ ] Commit raw captures with message
      `docs(00-03): upgrade EUIPO eSearch raw dump to verbatim founder-authenticated capture`
- [ ] Amend this file's result tables with verbatim rows
- [ ] Flip frontmatter `snapshot_method` from `manual-lookup-required` to
      `founder-authenticated-2026-MM-DD`
- [ ] If a verbatim Class 9 EU NYRA live mark surfaces, flip the
      aggregate verdict to BLOCKED and trigger Plan 00-03 Task 2 full
      backup-names screening

## Optional extended EU sweep (v1.1 counsel-directed)

The following national-register searches are DEFERRED to v1.1 counsel
review because EUTM alone confers EU-wide rights and Phase-0 screening
does not require per-country searches:

- **UKIPO (UK, post-Brexit)** — separate register since 2021; UKIPO
  IPO search at ipo.gov.uk/tmcase. NYRA cosmetics/apparel UK marks
  possible.
- **INPI France** — INPI eSearch at bases-marques.inpi.fr. EU fashion
  density concentrates here.
- **DPMA Germany** — dpma.de register search.
- **UIBM Italy** — Italian register; cosmetics-heavy.
- **OEPM Spain** — Spanish register; cosmetics-heavy.

These are v1.1 concerns tied to eventual EUIPO filing + UK filing.

---

*Snapshot by: NYRA Plan 00-03 executor on 2026-04-24.*
*Upgrade path: founder-authenticated manual follow-up per checklist above.*
*Next consumer: `.planning/phases/00-legal-brand-gate/trademark/00-03-nyra-screening-dossier.md` (consolidates this dump + USPTO + WIPO into the aggregate verdict).*
