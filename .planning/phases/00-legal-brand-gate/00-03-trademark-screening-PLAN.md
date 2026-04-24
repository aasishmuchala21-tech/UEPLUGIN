---
phase: 00-legal-brand-gate
plan: 03
slug: trademark-screening
type: execute
tdd: false
wave: 1
depends_on: []
autonomous: true
requirements: [PLUG-05]
task_count: 3
files_modified:
  - .planning/phases/00-legal-brand-gate/trademark/00-03-nyra-screening-dossier.md
  - .planning/phases/00-legal-brand-gate/trademark/00-03-uspto-tess-raw.md
  - .planning/phases/00-legal-brand-gate/trademark/00-03-euipo-esearch-raw.md
  - .planning/phases/00-legal-brand-gate/trademark/00-03-wipo-brand-db-raw.md
  - .planning/phases/00-legal-brand-gate/trademark/00-03-backup-names-screening.md
  - .planning/phases/00-legal-brand-gate/trademark/00-03-verdict-and-reservations.md
objective: >
  Close ROADMAP Phase 0 SC#3 — screen NYRA across USPTO TESS + EUIPO eSearch
  + WIPO Global Brand Database in Class 9 (software plugins), Class 42 (SaaS
  / downloadable software), and Class 41 (educational/training) per D-04.
  Produce a clean-OR-blocked verdict. If clean, reserve `nyra.dev` +
  fallback domains + GitHub org + social handles. If blocked, pre-screen
  5 backup names, select one, re-screen it, and reserve. Actual USPTO
  filing is DEFERRED (D-04) — this plan only de-risks the name. Gate for
  the public devlog kickoff (PITFALLS §7.4 competitor-preempts mitigation).
must_haves:
  truths:
    - "USPTO TESS, EUIPO eSearch, and WIPO Global Brand DB raw search result dumps exist under trademark/ for the name 'NYRA' across Classes 9 + 42 + 41, each search date-stamped"
    - "A consolidated screening dossier exists summarising each search: hit count per class per registry, nearest-neighbor name/mark list, collision-risk rating (CLEAN | MEDIUM-RISK | BLOCKED) per class, and an aggregate verdict for NYRA"
    - "If aggregate verdict is BLOCKED or MEDIUM-RISK-IN-CLASS-9: a backup-names screening doc exists with 5 pre-screened candidates, each run through the same USPTO + EUIPO + WIPO screen, and a selected backup with rationale"
    - "A verdict-and-reservations doc exists naming the final chosen name (NYRA or backup), with confirmed-reserved evidence (receipts / screenshots / usernames) for: primary domain, fallback domain(s), GitHub org, X/Twitter handle, Discord server handle"
    - "The public devlog kickoff is UNBLOCKED by the verdict-and-reservations doc — PITFALLS §7.4 gate mentioned in CONTEXT.md canonical_refs"
    - "Filing decision is explicitly deferred per D-04: verdict-and-reservations doc contains a `filing_status: DEFERRED-TO-V1.1` line so future counsel review picks it up"
  artifacts:
    - path: .planning/phases/00-legal-brand-gate/trademark/00-03-nyra-screening-dossier.md
      provides: "Consolidated NYRA trademark-screening dossier — summary across 3 registries x 3 classes with collision-risk ratings + nearest-neighbor list + aggregate verdict"
      contains: "aggregate_verdict:"
    - path: .planning/phases/00-legal-brand-gate/trademark/00-03-uspto-tess-raw.md
      provides: "Raw USPTO TESS search dumps for NYRA + each backup candidate (if screened) — class-by-class hits, live/dead status, nearest-neighbor marks"
      contains: "USPTO TESS"
    - path: .planning/phases/00-legal-brand-gate/trademark/00-03-euipo-esearch-raw.md
      provides: "Raw EUIPO eSearch results for NYRA + any backup candidates"
      contains: "EUIPO"
    - path: .planning/phases/00-legal-brand-gate/trademark/00-03-wipo-brand-db-raw.md
      provides: "Raw WIPO Global Brand Database results for NYRA + any backup candidates"
      contains: "WIPO"
    - path: .planning/phases/00-legal-brand-gate/trademark/00-03-backup-names-screening.md
      provides: "5 backup-name candidates screened through USPTO + EUIPO + WIPO, each with a CLEAN/BLOCKED verdict and a selection rationale"
      contains: "candidates:"
    - path: .planning/phases/00-legal-brand-gate/trademark/00-03-verdict-and-reservations.md
      provides: "Final name + domain/org/handle reservation receipts + filing-status: DEFERRED-TO-V1.1 line"
      contains: "filing_status: DEFERRED-TO-V1.1"
  key_links:
    - from: trademark/00-03-nyra-screening-dossier.md
      to: trademark/00-03-uspto-tess-raw.md
      via: "Dossier summary references raw USPTO dump by hit-row and search-date"
      pattern: "uspto-tess-raw"
    - from: trademark/00-03-nyra-screening-dossier.md
      to: trademark/00-03-backup-names-screening.md
      via: "If aggregate_verdict != CLEAN, dossier links to backup-names screening doc as the next-action artifact"
      pattern: "backup-names-screening"
    - from: trademark/00-03-verdict-and-reservations.md
      to: trademark/00-03-nyra-screening-dossier.md
      via: "Reservations doc cites the dossier verdict as the justification for reserving the chosen name vs a backup"
      pattern: "aggregate_verdict"
    - from: trademark/00-03-verdict-and-reservations.md
      to: PITFALLS §7.4 public devlog
      via: "Reservations doc explicitly marks devlog kickoff UNBLOCKED — downstream consumer is the founder's week-1 devlog post"
      pattern: "devlog"
---

<objective>
Phase 0 SC#3 protects two things at once: (a) the right to use the NYRA
name publicly without a cease-and-desist destroying the project mid-build,
and (b) the public-devlog kickoff that PITFALLS §7.4 identifies as the
competitor-preempts-demo mitigation. Both are blocked until this plan
closes.

Per CONTEXT.md D-04: this is SCREENING, not PROSECUTION. We're ruling out
collision risk, not filing a trademark application — filing is a v1.1
decision with lawyer engagement. Per D-09: the default screening tool
choice is DIY (USPTO TESS + EUIPO eSearch + WIPO Global Brand Database —
free). A paid service (Markify, TrademarkNow) is optional only if DIY
yields ambiguity the executor can't resolve.

Per CONTEXT.md §specifics: NYRA is a short Greek-mythology-adjacent name;
priors suggest low collision risk in software but medium risk in fashion/
cosmetics/adjacent. Screen Classes 9 + 42 + 41 together; Class 9 (software)
is the blocker; 42 + 41 are nice-to-have.

Purpose: Clean-or-blocked verdict for NYRA; if blocked, a screened backup.
Plus public-facing identity locked (domains, GitHub org, social handles).
Output: 6 markdown docs covering raw searches, dossier summary, backup
screening, and the final verdict + reservation receipts.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/00-legal-brand-gate/00-CONTEXT.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Run USPTO + EUIPO + WIPO screens on NYRA across Classes 9/42/41</name>
  <files>
    .planning/phases/00-legal-brand-gate/trademark/00-03-uspto-tess-raw.md,
    .planning/phases/00-legal-brand-gate/trademark/00-03-euipo-esearch-raw.md,
    .planning/phases/00-legal-brand-gate/trademark/00-03-wipo-brand-db-raw.md,
    .planning/phases/00-legal-brand-gate/trademark/00-03-nyra-screening-dossier.md
  </files>
  <action>
    Step A — USPTO TESS screen. Open https://www.uspto.gov/trademarks/search
    and run the following searches (record search URL + raw result table in
    `00-03-uspto-tess-raw.md`):
    - Exact match: `NYRA` in Class 009 (Live + Dead, so historic collisions
      are visible).
    - Exact match: `NYRA` in Class 042.
    - Exact match: `NYRA` in Class 041.
    - Phonetic/near-match sweep: `NYRA*` (wildcard), `N?RA`, `NYR*` — flag
      any mark within edit-distance 1 that overlaps software/tech goods.

    For each search: record hit count, list each hit as a row (mark text,
    serial/registration number, owner, goods/services Nice class + full
    description, status LIVE/DEAD, filing/registration date). Prefix dead
    marks with `(DEAD)`. At the bottom of the USPTO section write a
    `### USPTO Collision Risk` sub-section: per-class risk rating (CLEAN |
    MEDIUM | HIGH) with a one-sentence justification citing specific hits.

    Step B — EUIPO eSearch screen. Open https://euipo.europa.eu/eSearch and
    run the equivalent searches for the EUTM register. Record in
    `00-03-euipo-esearch-raw.md` using the same row format.

    Step C — WIPO Global Brand DB screen. Open https://branddb.wipo.int/
    and run the equivalent searches across all territories (limit to
    English name + Latin transliteration). Record in
    `00-03-wipo-brand-db-raw.md` using the same row format.

    Step D — Consolidate into `00-03-nyra-screening-dossier.md` with YAML
    frontmatter:
    ```
    name_screened: NYRA
    screening_date: <ISO-8601>
    registries: [USPTO, EUIPO, WIPO]
    classes: [9, 42, 41]
    aggregate_verdict: CLEAN | MEDIUM-RISK | BLOCKED
    next_action: reserve-nyra | screen-backup-names
    ```

    Body sections:
    1. `## Search Summary` — one table: registry × class × hit count +
       risk rating cell.
    2. `## Nearest-Neighbor Marks` — top 10 closest marks globally (any
       registry, any class), with one sentence per entry explaining
       collision severity. Includes a note on fashion/cosmetics adjacency
       flagged in CONTEXT.md §specifics ("NYRA" in fashion/cosmetics is
       expected; the question is whether any of those marks extend into
       Class 9 software).
    3. `## Aggregate Verdict` — one paragraph synthesising the three
       registries. Verdict rubric:
       - CLEAN: zero Class-9 hits on `NYRA` (live), zero edit-distance-1
         hits in Class 9, any non-9 hits are clearly non-software. Proceed
         to reservations.
       - MEDIUM-RISK: at most 1 Class-9 hit that looks non-overlapping
         (e.g. different product category under class 9 umbrella). Proceed
         to reservations BUT flag for counsel at v1.1 filing time.
       - BLOCKED: any live Class-9 hit on `NYRA` or exact phonetic match
         in software. Drop to backup-names screening (Task 2).
    4. `## Filing Decision` — one paragraph restating D-04: filing is
       DEFERRED to v1.1. This phase produces the dossier counsel needs.

    Commit with
    `docs(00-03): screen NYRA across USPTO+EUIPO+WIPO classes 9/42/41`.
  </action>
  <verify>
    <automated>test -f .planning/phases/00-legal-brand-gate/trademark/00-03-uspto-tess-raw.md && test -f .planning/phases/00-legal-brand-gate/trademark/00-03-euipo-esearch-raw.md && test -f .planning/phases/00-legal-brand-gate/trademark/00-03-wipo-brand-db-raw.md && test -f .planning/phases/00-legal-brand-gate/trademark/00-03-nyra-screening-dossier.md && grep -q "aggregate_verdict:" .planning/phases/00-legal-brand-gate/trademark/00-03-nyra-screening-dossier.md && grep -q "USPTO TESS" .planning/phases/00-legal-brand-gate/trademark/00-03-uspto-tess-raw.md && grep -q "EUIPO" .planning/phases/00-legal-brand-gate/trademark/00-03-euipo-esearch-raw.md && grep -q "WIPO" .planning/phases/00-legal-brand-gate/trademark/00-03-wipo-brand-db-raw.md</automated>
  </verify>
  <done>4 files exist: 3 raw-search dumps + consolidated dossier. Dossier has `aggregate_verdict` frontmatter set to CLEAN, MEDIUM-RISK, or BLOCKED.</done>
</task>

<task type="auto">
  <name>Task 2: If needed, pre-screen 5 backup names and select one</name>
  <files>
    .planning/phases/00-legal-brand-gate/trademark/00-03-backup-names-screening.md
  </files>
  <action>
    **Conditional-execute rule** — read the `aggregate_verdict` from
    Task 1's dossier:
    - If CLEAN: write a one-page stub file `00-03-backup-names-screening.md`
      with frontmatter `status: NOT-REQUIRED` and a note "NYRA screened
      CLEAN; backup screening skipped. If v1.1 counsel review revises this
      decision, re-run this plan task." Commit and move on to Task 3.
    - If MEDIUM-RISK: write the backup-screening doc as a PRECAUTIONARY
      exercise (5 candidates screened) but proceed with NYRA as primary.
      Backup names are warm-standby in case a cease-and-desist arrives
      post-launch.
    - If BLOCKED: execute the full backup screening + selection process
      below; NYRA is abandoned.

    For MEDIUM-RISK or BLOCKED paths:

    Step A — Generate 5 backup name candidates. Per CONTEXT.md §specifics
    selection criteria: short (4–6 letters), Greek/myth-adjacent OR
    thematically adjacent to "agent that reaches, that brings things
    back" (English or Latin roots, easy to say/spell, not-obviously-taken
    in software). Executor proposes 5; record generation rationale per
    candidate. Example shape (executor picks real candidates; these are
    illustrative only and MUST be re-confirmed at execution time):
      - A short Greek-myth-adjacent name
      - A short Latin-root name
      - A short Sanskrit/Vedic-adjacent name
      - A short Norse-adjacent name
      - A coined short name with clear pronunciation

    Step B — For EACH of the 5 candidates, run the same USPTO + EUIPO +
    WIPO screens as Task 1 (exact match + wildcard + edit-distance-1 in
    Classes 9/42/41). Record results inline in
    `00-03-backup-names-screening.md` under `## Candidate: <NAME>` with
    the same per-registry per-class table + aggregate verdict rubric as
    Task 1. DO NOT create separate raw-dump files per backup — keep them
    inline here; if the executor needs a separate dump file for evidence,
    append to the existing Task-1 raw files with a clear section divider.

    Step C — Apply an additional availability filter beyond trademark:
      - Primary domain availability: `<candidate>.dev`, `<candidate>.ai`,
        `<candidate>.com` — check via Cloudflare Registrar or Google
        Domains search. Mark each as AVAILABLE / TAKEN / PREMIUM.
      - GitHub org availability: `github.com/<candidate>-ai` or
        `github.com/<candidate>`. Mark AVAILABLE / TAKEN.
      - Social: X.com/twitter.com/@<candidate>, reddit.com/r/<candidate>.
        Mark AVAILABLE / TAKEN.

    Step D — Frontmatter + selection rationale. Frontmatter:
    ```
    status: REQUIRED | PRECAUTIONARY | NOT-REQUIRED
    candidates: [<name1>, <name2>, <name3>, <name4>, <name5>]
    selected: <chosen name>
    selection_reason: "<one sentence>"
    ```
    Body `## Selection Rationale` section: one paragraph explaining why
    the selected backup beats the other four across trademark-clean +
    domain-available + social-available + aesthetic-fit dimensions.

    Commit with `docs(00-03): pre-screen 5 backup names and select one`.
  </action>
  <verify>
    <automated>test -f .planning/phases/00-legal-brand-gate/trademark/00-03-backup-names-screening.md && grep -qE "status: (REQUIRED|PRECAUTIONARY|NOT-REQUIRED)" .planning/phases/00-legal-brand-gate/trademark/00-03-backup-names-screening.md</automated>
  </verify>
  <done>Backup-screening doc exists with frontmatter `status:` set correctly and, if status != NOT-REQUIRED, 5 candidate sections + a `selected:` frontmatter field.</done>
</task>

<task type="auto">
  <name>Task 3: Final verdict + domain/GitHub/social reservations (devlog gate)</name>
  <files>
    .planning/phases/00-legal-brand-gate/trademark/00-03-verdict-and-reservations.md
  </files>
  <action>
    Author the final verdict + reservations doc. Frontmatter:
    ```
    final_name: <NYRA or backup>
    final_name_source: primary | backup
    screening_dossier: trademark/00-03-nyra-screening-dossier.md
    backup_screening: trademark/00-03-backup-names-screening.md
    filing_status: DEFERRED-TO-V1.1
    devlog_gate: OPEN
    date_closed: <ISO-8601>
    ```

    Body sections:

    1. `## Final Name Decision` — one paragraph. Cite the dossier verdict
       and (if applicable) the backup-selection rationale.

    2. `## Domain Reservations` — table of reserved domains:
       | Domain | Registrar | Reserved date | Expiry | Receipt-ref |
       Per CONTEXT.md §specifics: primary `<name>.dev`, fallback `<name>.ai`,
       tertiary `<name>-engine.com` (pattern translates to backup name if
       used). Receipts: redact payment details, keep order number +
       registrar + dates. The founder performs the actual purchase; the
       executor populates this doc from founder-provided receipts.

    3. `## GitHub Organization Reservation` — one row with org URL,
       date created, admin account (founder's GitHub username). Default
       suggestion: `github.com/<name>-ai`; if taken, fallback `github.com/
       <name>-plugin` or similar — document the chosen slug + why.

    4. `## Social Handle Reservations` — table:
       | Platform | Handle | Reserved date | Notes |
       Minimum coverage: X.com, Discord server/vanity, Reddit
       /r/<name>. Optional: YouTube @handle (if the devlog will be
       video-first), Bluesky, Mastodon.

    5. `## Filing Decision (Deferred)` — one paragraph restating D-04:
       USPTO filing deferred to v1.1 or post-launch when usage signal
       justifies the ~$350/class prosecution cost + counsel fees. The
       dossier + backup-screening + this reservations doc together form
       the packet counsel reviews at filing time.

    6. `## Devlog Gate` — one paragraph: this doc is the PITFALLS §7.4
       gate for the public devlog kickoff. With the name cleared and
       identity reserved, the first public devlog post is UNBLOCKED. Cite
       PITFALLS §7.4 and ROADMAP.md Phase 8 SC#5 ("public devlog has
       been shipping from Month 1").

    7. `## Rollback Plan` — one paragraph: if a cease-and-desist arrives
       post-launch, the backup-screening doc from Task 2 is the warm-
       standby. Process: file a rename RFC, run Task 2's selected backup
       through a fresh live USPTO re-screen (brand registers drift), and
       execute a coordinated cutover (domain, GitHub org rename, social
       handles, Fab listing, EV cert re-issue). Estimated cutover: 2–4
       weeks per registrar propagation.

    Commit with
    `docs(00-03): finalize trademark verdict + domain/GitHub/social reservations`.
  </action>
  <verify>
    <automated>test -f .planning/phases/00-legal-brand-gate/trademark/00-03-verdict-and-reservations.md && grep -q "filing_status: DEFERRED-TO-V1.1" .planning/phases/00-legal-brand-gate/trademark/00-03-verdict-and-reservations.md && grep -q "devlog_gate: OPEN" .planning/phases/00-legal-brand-gate/trademark/00-03-verdict-and-reservations.md && grep -qi "domain" .planning/phases/00-legal-brand-gate/trademark/00-03-verdict-and-reservations.md && grep -qi "github" .planning/phases/00-legal-brand-gate/trademark/00-03-verdict-and-reservations.md && grep -qi "rollback" .planning/phases/00-legal-brand-gate/trademark/00-03-verdict-and-reservations.md</automated>
  </verify>
  <done>Verdict-and-reservations doc exists with all required frontmatter fields + 7 body sections; domain/GitHub/social reservations table rows are populated (or explicitly marked PENDING with a due-date if the founder hasn't completed the purchase yet).</done>
</task>

</tasks>

<verification>
Phase 0 SC#3 closure verification:
- [ ] NYRA screened across USPTO + EUIPO + WIPO, Classes 9/42/41
- [ ] Consolidated dossier with aggregate_verdict exists
- [ ] Backup-names screening exists (even if status=NOT-REQUIRED)
- [ ] Final verdict-and-reservations doc exists with filing_status: DEFERRED-TO-V1.1
- [ ] Domain reservations, GitHub org, social handles reserved (or marked PENDING with due-date)
- [ ] devlog_gate: OPEN
- [ ] All files committed to git
</verification>

<success_criteria>
Phase 0 SC#3 is CLOSED when:
1. `trademark/00-03-verdict-and-reservations.md` exists with a final name
   selected and all four reservation tables populated (domains, GitHub,
   social; filing deferred).
2. The screening dossier + backup-screening doc are the paper trail behind
   the selection.
3. The closure ledger (Plan 06) flips SC#3 from PENDING to CLOSED and
   propagates the final name into any other docs that use NYRA
   placeholder (Plans 00-01, 00-02, 00-04, 00-05 may need the final name
   substituted if the backup was selected).
</success_criteria>

<output>
After completion, create `.planning/phases/00-legal-brand-gate/00-03-SUMMARY.md`
following the GSD summary template. Record: screening dates, per-registry
verdicts, aggregate verdict, backup-screening status, final name chosen,
reservation receipts, devlog gate status.
</output>
