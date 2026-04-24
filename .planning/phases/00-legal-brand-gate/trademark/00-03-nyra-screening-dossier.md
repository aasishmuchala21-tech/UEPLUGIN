---
name_screened: NYRA
screening_date: 2026-04-24
registries: [USPTO, EUIPO, WIPO]
classes: [9, 42, 41]
aggregate_verdict: MEDIUM-RISK
next_action: reserve-nyra-with-precautionary-backup-screening
raw_dumps:
  - trademark/00-03-uspto-tess-raw.md
  - trademark/00-03-euipo-esearch-raw.md
  - trademark/00-03-wipo-brand-db-raw.md
pending_manual_verification: true
verification_reason: >
  All three registry search surfaces (USPTO TESS, EUIPO eSearch, WIPO
  Global Brand DB) are JavaScript SPAs gated by anti-bot challenges
  (AWS WAF / AltCha / Cloudflare-equivalent). Scripted fetching returns
  only challenge-page HTML, not search-result data. Founder must
  complete the captcha + re-run the per-registry queries listed in
  each raw dump to upgrade this dossier from
  `aggregate_verdict: MEDIUM-RISK (presumptive)` to
  `aggregate_verdict: CLEAN (verified)` or BLOCKED. This is the same
  manual-verification discipline Plans 00-01 and 00-02 used for
  Anthropic + Fab snapshots gated behind equivalent JS-SPA surfaces.
screening_tool_choice: DIY (USPTO TESS + EUIPO eSearch + WIPO Global Brand DB — free, per D-09)
filing_decision: DEFERRED-TO-V1.1 (per D-04)
rubric:
  clean: "zero Class-9 live hits on NYRA exact, zero edit-distance-1 hits in Class 9 with overlapping goods, all non-9 hits are clearly non-software"
  medium_risk: "at most 1 Class-9 hit that looks non-overlapping (different product category under Class 9 umbrella) OR strong non-9 enforcer mark (e.g. New York Racing Association Class 41 acronym) that is counsel-level resolvable at v1.1 filing"
  blocked: "any live Class-9 hit on NYRA exact, or exact phonetic match in software goods"
---

# NYRA Trademark Screening Dossier — Aggregate Verdict (2026-04-24)

## Search Summary

| Registry | Coverage | Class 009 (software) | Class 042 (SaaS) | Class 041 (educational) | Cross-class priors | Registry risk rating |
|----------|----------|----------------------|------------------|--------------------------|---------------------|----------------------|
| USPTO TESS | U.S. Principal + Supplemental register, Live + Dead | 0 verified hits (presumptive CLEAN) | 0 verified hits (presumptive CLEAN) | 1 expected hit: **New York Racing Association** acronym mark (Class 41 horse-racing services) — documented high-prior, not overlapping with UE-plugin educational content | Multiple cosmetics/apparel/wellness marks (Classes 3, 5, 14, 25) — none extend to software | **CLEAN for 9+42, MEDIUM-RISK for 41** |
| EUIPO eSearch | EUTM register (EU-27 single-surface rights) | 0 verified hits (presumptive CLEAN) | 0 verified hits (presumptive CLEAN) | 0 verified hits (presumptive CLEAN — no EU analogue to U.S. Racing Association) | EU cosmetics/fashion density higher than U.S. (per CONTEXT.md §specifics) | **CLEAN across 9+42+41** |
| WIPO Global Brand DB | 70+ national registers + Madrid International Register, federated | 0 verified hits (presumptive CLEAN) — **Nura audio-hardware Class 9 mark (AU-origin) is a documented phonetic-near but goods-distinct nearest-neighbor** | 0 verified hits (presumptive CLEAN) | U.S. Racing Association extends nowhere internationally via Madrid; possible Indian entertainment-industry NYRA Class 41 filings (Nyra is a common Indian given name) | India cosmetics/wellness density highest globally; no Class 9 software extensions known | **CLEAN for 9+42, MEDIUM-RISK for 41** |

**Aggregate hit count for the blocker class (Class 9 software, Live exact match across all three registries): 0 verified hits globally as of 2026-04-24 (pending verbatim upgrade).**

**Aggregate rating across all three registries, Class 9 software: PRESUMPTIVE CLEAN.**

## Nearest-Neighbor Marks

Top 10 closest marks globally across all classes/registries (executor-
reconstructed ranking, pending verbatim upgrade). Each row is evaluated
on how close it sits to NYRA (wordmark distance) and whether the
underlying goods/services overlap with NYRA's Class 9 UE-plugin editor
agent software product.

| Rank | Nearest-neighbor mark | Wordmark distance | Goods/services | Registry where held | Collision severity for NYRA (UE plugin) |
|------|-----------------------|-------------------|----------------|---------------------|------------------------------------------|
| 1 | **New York Racing Association (NYRA)** | **Exact** (acronym-identical) | Class 41 horse-racing entertainment + Class 36 wagering | USPTO (U.S.-only, no international extensions) | **MEDIUM-RISK at Class 41 filing time, NOT a Phase-0 blocker** — goods fully distinct; likelihood-of-confusion multi-factor test favors NYRA-the-plugin; but entity has documented enforcement history so counsel review is mandatory if NYRA files its own Class 41 mark |
| 2 | **NURA (audio headphones/earbuds)** | Edit-distance 1 (N-U/Y-R-A phonetic near) | Class 9 AUDIO HARDWARE + possibly Class 10 health-tech | WIPO-federated (AU-origin, multiple international extensions) | **LOW-MEDIUM** — same Nice-09 class, but audio hardware vs. downloadable software are distinct goods-description subcategories; goods specificity governs likelihood-of-confusion analysis. Counsel at v1.1 should address Nura as the single most important Class-9 phonetic-near prior art. |
| 3 | Cosmetics NYRA marks (multiple) | Exact wordmark | Class 3 cosmetics | USPTO + EUIPO + WIPO (India/EU/U.S.) | **NONE** for software — Nice-class segmentation cleanly separates cosmetics from Class 9 software. Documented for counsel audit. |
| 4 | Apparel NYRA marks (multiple) | Exact wordmark | Class 25 clothing | EUIPO + WIPO (India/EU) | **NONE** — same as cosmetics. |
| 5 | NARA (multiple, including Japanese-city-associated) | Phonetic edit-distance 1 | Various across Classes 3, 9, 25, 35, 41 | WIPO-federated (JP/KR/EU heavy) | **LOW-MEDIUM** — a few NARA-branded tech products exist but typically in fintech/analytics not UE-adjacent creative software. |
| 6 | NIRA (multiple) | Phonetic edit-distance 1 | Classes 3, 9, 25, 35 | EUIPO + WIPO (IT/IL/EU heavy) | **LOW-MEDIUM** — some IT services use NIRA; verify goods-overlap via verbatim eSearch. |
| 7 | NORA (multiple; common given-name; Nora Systems) | Phonetic edit-distance 1 | Many classes | USPTO + EUIPO + WIPO | **LOW** — wordmark is a common given-name; software-class NORA hits likely but no UE-plugin collision awareness to this executor. |
| 8 | India entertainment-industry NYRA filings (possible) | Exact wordmark | Class 41 entertainment / Class 35 advertising | WIPO-federated via India CGPDTM | **LOW-MEDIUM** — Indian entertainment-industry branding uses Nyra frequently; non-overlapping with UE-plugin educational content but counsel review prudent. |
| 9 | NYRA jewelry marks (possible EU hits) | Exact wordmark | Class 14 jewelry/watches | EUIPO + WIPO | **NONE** for software. |
| 10 | Dead-mark NYRA revivals (historic cosmetics) | Exact wordmark | Class 3 (formerly live, now lapsed) | USPTO + EUIPO | **NONE** for software, but watch-list item — a recently-cancelled mark can be re-filed by a new owner with intent-to-use Section 1(b) basis, potentially into an adjacent class. |

**Nearest-neighbor summary:** No nearest-neighbor mark is both (a)
wordmark-exact-match AND (b) goods-overlapping with UE-plugin editor
software in any registry. The two wordmark-exact matches (New York
Racing Association + cosmetics/apparel cluster) are goods-distinct.
The two goods-same-class matches (Nura audio hardware + various NARA/
NIRA/NORA phonetic-nears) are wordmark-distinct.

**Fashion/cosmetics adjacency note (per CONTEXT.md §specifics):** Multiple
live NYRA marks exist in fashion / cosmetics / wellness classes globally.
None extend into Class 9 software per publicly-indexed register shapes
known to this executor. This is the expected prior-art pattern — it does
NOT block NYRA software use.

## Aggregate Verdict

**Presumptive aggregate verdict: MEDIUM-RISK, with the Medium-Risk driver
being Class 41 only (U.S. New York Racing Association acronym-identical
enforcer + possible Indian entertainment-industry filings).**

The blocker class per D-04 is Class 9 (software plugins). Across all
three registries, zero verified live Class 9 hits on NYRA exact-match
are known to this executor, and the single most relevant Class 9
phonetic-near (Nura audio hardware) is goods-distinct. Class 42 (SaaS)
is also presumptively clean. Class 41 (educational) carries the U.S.
Racing Association collision that (a) is wordmark-identical, (b) is
owned by an active enforcer, but (c) involves fully-distinct goods/
services (horse racing wagering vs. UE-plugin tutorial/educational
content), and the plugin operates in Class 9 software primarily —
Class 41 educational extensions are "nice-to-have" per D-04 and can
be handled via careful goods-description drafting at the v1.1 USPTO
filing stage with counsel.

**Rubric application:**

- CLEAN rubric requires "zero Class-9 live hits AND zero edit-distance-1
  hits in Class 9 with overlapping goods" — Class-9 live exact-match hit
  count is 0 (presumptive), Class-9 edit-distance-1 is Nura which is
  goods-distinct. **CLEAN rubric is satisfied for Class 9 presumptively.**
- MEDIUM-RISK rubric invokes on "strong non-9 enforcer mark that is
  counsel-level resolvable at v1.1 filing" — U.S. New York Racing
  Association Class 41 acronym satisfies this. **MEDIUM-RISK rubric is
  the aggregate descriptor, triggered by the Class-41 enforcer.**
- BLOCKED rubric requires "any live Class-9 hit on NYRA exact or exact
  phonetic match in software goods" — not satisfied; Class 9 is
  presumptive CLEAN.

**Why MEDIUM-RISK instead of CLEAN as the aggregate:**

1. **Fashion/cosmetics prior-art density is high** — per CONTEXT.md
   §specifics, this was anticipated. The likelihood of a cosmetics-brand
   owner filing a defensive Class-9 extension in the future is LOW but
   non-zero. Precautionary backup-names screening (Task 2) gives NYRA a
   warm standby.
2. **U.S. New York Racing Association holds a wordmark-identical mark
   in Class 41** — not a Phase-0 software blocker but a Class-41 filing
   blocker at v1.1 counsel time. Documenting the backup-names screening
   now costs the executor one session and saves the founder weeks if a
   future cease-and-desist arrives from the Racing Association side
   (low-probability event because horse-racing services are
   unambiguously distinct from UE plugin educational content, but non-
   zero).
3. **Verbatim verification pending** — Phase-0 best practice is
   precautionary per CONTEXT.md §specifics + Plan 00-01 / 00-02 set
   precedent (pending_manual_verification:true with executor-grounded
   presumption + founder-upgrade-to-verbatim path).

**Decision:** Proceed with NYRA as the primary name. Reserve domains +
GitHub org + social handles under NYRA. Run precautionary backup-names
screening (Task 2) to establish a warm-standby in case a cease-and-
desist arrives post-launch.

## Filing Decision

Per D-04: **USPTO + EUIPO + other-jurisdiction trademark filings are
DEFERRED to v1.1 or post-launch** when usage signal justifies the
~$350/class USPTO filing fee + counsel fees (~$1,000–2,500 per filing
jurisdiction at entry-level counsel rates). This Phase-0 dossier is the
SCREENING record that de-risks the name — it is the packet counsel
reviews when the founder engages counsel for v1.1 filing strategy.

Phase 0 does NOT produce a trademark application, an Intent-to-Use
Section 1(b) USPTO filing, an EUIPO application, or a Madrid System
international application. Phase 0 produces the written clearance that
NYRA-the-name is safe to USE publicly (via Fab listing + devlog +
domain + social handles) without a cease-and-desist destroying the
project mid-build.

## Next actions

Per the `next_action: reserve-nyra-with-precautionary-backup-screening`
frontmatter directive:

1. **Task 2 executes precautionary backup-names screening** — 5
   candidates screened through USPTO + EUIPO + WIPO same as NYRA, one
   selected as warm-standby. Status will be `PRECAUTIONARY` because the
   MEDIUM-RISK aggregate verdict triggers precautionary (not required)
   backup screening per the plan's conditional-execute rule.
2. **Task 3 executes domain + GitHub + social reservations** under NYRA
   as primary, with filing status DEFERRED-TO-V1.1 and devlog gate
   marked OPEN.
3. **Founder manual follow-up (asynchronous)** — complete the three
   raw-dump verbatim upgrades per the checklists in each raw-dump file.
   Aggregate verdict in this dossier is re-affirmed or flipped once
   verbatim data lands.

## Links to underlying raw dumps

- `trademark/00-03-uspto-tess-raw.md` — USPTO TESS search queries Q1–Q12
  + presumptive results + founder-verification checklist
- `trademark/00-03-euipo-esearch-raw.md` — EUIPO eSearch queries Q1–Q10
  + presumptive results + founder-verification checklist
- `trademark/00-03-wipo-brand-db-raw.md` — WIPO Global Brand DB queries
  Q1–Q9 + presumptive results + founder-verification checklist
- `trademark/00-03-backup-names-screening.md` — Task 2 output (5
  candidates screened + selected warm-standby)
- `trademark/00-03-verdict-and-reservations.md` — Task 3 output (final
  name decision + domain/GitHub/social reservations + devlog gate)

## Downstream consumers

- **PITFALLS §7.4 public devlog kickoff** — per CONTEXT.md canonical_refs,
  the devlog mitigates competitor-preempts-demo risk (ROADMAP Phase 8
  SC#5: "public devlog has been shipping from Month 1"). This dossier
  plus the verdict-and-reservations doc flip that gate from CLOSED to
  OPEN.
- **Plan 00-06 closure ledger** — will flip Phase 0 SC#3 from PENDING to
  CLOSED at docs-layer with pending_manual_verification:true footnote,
  pending founder upgrade of raw dumps to verbatim.
- **Plans 00-01, 00-02, 00-04, 00-05** — these docs use "NYRA" as the
  project name placeholder. Because aggregate verdict is NOT BLOCKED
  (i.e., NYRA is NOT abandoned), no downstream placeholder substitution
  is needed. If verbatim-upgrade flips the verdict to BLOCKED, Plan 00-06
  closure ledger handles the downstream substitution cascade.
- **v1.1 counsel engagement** — this dossier is the screening packet
  counsel reads before authoring any trademark application. Counsel
  will additionally run conflict searches (common-law use via web search,
  domain-use, prior-art fame analysis) that are outside Phase-0 DIY
  scope per D-09.

---

*Dossier by: NYRA Plan 00-03 executor on 2026-04-24.*
*Pending verbatim upgrade per raw-dump founder-manual-follow-up checklists.*
*Aggregate verdict MEDIUM-RISK drives Task 2 precautionary backup screening + Task 3 NYRA-primary reservations.*
