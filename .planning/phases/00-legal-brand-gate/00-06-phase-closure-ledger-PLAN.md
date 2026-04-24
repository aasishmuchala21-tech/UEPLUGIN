---
phase: 00-legal-brand-gate
plan: 06
slug: phase-closure-ledger
type: execute
tdd: false
wave: 2
depends_on: [01, 02, 03, 04, 05]
autonomous: false
requirements: [PLUG-05]
task_count: 1
files_modified:
  - .planning/phases/00-legal-brand-gate/PHASE-0-CLOSURE-LEDGER.yaml
  - .planning/ROADMAP.md
  - .planning/REQUIREMENTS.md
  - .planning/STATE.md
objective: >
  Cross-plan invariant from the Phase 0 brief: consolidate the 5 success-
  criterion closures into ONE machine-readable ledger that external systems
  (ROADMAP progress bar, STATE.md phase status, Phase 2 pre-execution gate
  check) read to decide "is Phase 0 actually closed?". The ledger records
  per-SC status + evidence-file paths + responsible plan + closure date +
  overall Phase 0 verdict. Founder sign-off at the bottom is the
  non-negotiable seal — the ledger exists BUT is only CLOSED when the
  founder has reviewed every linked artifact and approves. Then propagates
  closure to ROADMAP, REQUIREMENTS, STATE.
must_haves:
  truths:
    - "A YAML ledger exists at phase root (.planning/phases/00-legal-brand-gate/PHASE-0-CLOSURE-LEDGER.yaml) with one entry per success criterion (SC#1–SC#5) containing: sc_id, description, responsible_plan, evidence_files (list), status (PENDING | CLOSED | BLOCKED), closure_date, founder_signoff (boolean), notes"
    - "Each of the 5 SC entries references AT LEAST the primary closure artifact from its responsible plan: SC#1 → correspondence/00-01-anthropic-tos-email-response.md, SC#2 → correspondence/00-02-epic-fab-policy-email-response.md + legal/00-02-direct-download-fallback-plan.md, SC#3 → trademark/00-03-verdict-and-reservations.md, SC#4 → legal/00-04-nyra-eula-draft.md + legal/00-04-gemma-license-reverify-note.md + legal/00-04-nyra-eula-gemma-notice-appendix.md, SC#5 → brand/00-05-brand-compliance-summary.md + brand/00-05-fab-listing-copy-fragments.md"
    - "The ledger has a top-level `phase_0_verdict:` field set to CLOSED | CLOSED-WITH-CONDITIONS | BLOCKED — derived deterministically from the 5 per-SC status values per a rubric included in the ledger itself"
    - "The ledger has a top-level `phase_2_execution_gate:` field set to OPEN | OPEN-WITH-CONDITIONS | CLOSED — this is what Phase 2 planning/execution checks before any subscription-driving code ships; gate is CLOSED if SC#1 verdict was BLOCKED (since SC#1 directly gates subscription driving)"
    - "ROADMAP.md is updated: Phase 0 row flipped to COMPLETE with the ledger path cited, progress bar recalculated (1/9 -> 1 complete when this closes)"
    - "REQUIREMENTS.md PLUG-05 row status flipped from Pending to Complete with Phase 0 closure date"
    - "STATE.md current_phase / progress reflect Phase 0 closure + carry any Phase 2 execution-gate conditions into Phase 2's gating notes"
    - "Founder sign-off block at the bottom of the ledger is populated with date + name; ABSENT founder sign-off means ledger is at most AUTHORED, not CLOSED — downstream automation MUST treat founder_signoff: false as equivalent to phase_0_verdict: PENDING"
  artifacts:
    - path: .planning/phases/00-legal-brand-gate/PHASE-0-CLOSURE-LEDGER.yaml
      provides: "Single-source-of-truth YAML ledger listing all 5 SCs + status + evidence + founder signoff + phase_0_verdict + phase_2_execution_gate"
      contains: "phase_0_verdict:"
    - path: .planning/ROADMAP.md
      provides: "ROADMAP Phase 0 row updated to COMPLETE with ledger path citation"
      contains: "PHASE-0-CLOSURE-LEDGER"
    - path: .planning/REQUIREMENTS.md
      provides: "PLUG-05 row status flipped to Complete"
      contains: "PLUG-05"
    - path: .planning/STATE.md
      provides: "Current phase + progress + any Phase 2 gate conditions propagated"
      contains: "phase_0"
  key_links:
    - from: PHASE-0-CLOSURE-LEDGER.yaml SC#1 entry
      to: correspondence/00-01-anthropic-tos-email-response.md verdict field
      via: "Ledger reads verdict from 00-01 response file as SC#1 status source-of-truth"
      pattern: "verdict:"
    - from: PHASE-0-CLOSURE-LEDGER.yaml SC#2 entry
      to: correspondence/00-02-epic-fab-policy-email-response.md + legal/00-02-direct-download-fallback-plan.md
      via: "SC#2 closes on verdict + fallback-plan existence; ledger records both"
      pattern: "verdict:"
    - from: PHASE-0-CLOSURE-LEDGER.yaml phase_2_execution_gate
      to: Phase 2 pre-execution check
      via: "Phase 2's first planning step reads this field; gate is OPEN/OPEN-WITH-CONDITIONS/CLOSED"
      pattern: "phase_2_execution_gate:"
    - from: .planning/ROADMAP.md Phase 0 row
      to: .planning/phases/00-legal-brand-gate/PHASE-0-CLOSURE-LEDGER.yaml
      via: "ROADMAP cites ledger path as proof-of-closure; roadmap tooling may lint this reference"
      pattern: "PHASE-0-CLOSURE-LEDGER"
---

<objective>
Plans 00-01 through 00-05 each close ONE success criterion and each
produce artifact files that say "this SC is closed". But across the 5
plans the artifacts are scattered across `correspondence/`, `trademark/`,
`legal/`, `brand/` subdirectories with file-level fingerprints that a
Phase 2 pre-execution check can't consume without rediscovery. The closure
ledger collapses the scatter into one machine-readable YAML that a single
grep or yq query answers the question "is Phase 0 done, and under what
conditions?"

This plan is `autonomous: false` because the final step — founder sign-off
— is a human approval that happens after the founder personally reviews
every linked artifact. Without sign-off, the ledger is AUTHORED but not
CLOSED; downstream automation MUST treat an unsigned ledger as PENDING.

Depends on: ALL of Plans 00-01 through 00-05 must have at minimum
AUTHORED their primary closure artifacts. If any of 00-01/00-02 are
still awaiting an external reply, the ledger entry for that SC records
status: PENDING with a due-date and the phase_0_verdict reflects that —
the ledger is REAL-TIME, not a one-shot.

Purpose: Single source of truth for Phase 0 status, consumable by
ROADMAP rendering, Phase 2 gate-check, and future audits.
Output: 1 YAML ledger + 3 project-level doc updates (ROADMAP, REQUIREMENTS,
STATE).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/00-legal-brand-gate/00-CONTEXT.md
</context>

<tasks>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 1: Compose ledger, populate per-SC status from plan artifacts, founder sign-off, propagate closure</name>
  <files>
    .planning/phases/00-legal-brand-gate/PHASE-0-CLOSURE-LEDGER.yaml,
    .planning/ROADMAP.md,
    .planning/REQUIREMENTS.md,
    .planning/STATE.md
  </files>
  <what-built>
    Plans 00-01 through 00-05 have each produced their SC-closure
    artifacts (or at minimum their drafts if external replies are still
    pending). This task consolidates the 5 closures into a single YAML
    ledger, obtains founder sign-off, then propagates closure to the
    3 project-root docs.
  </what-built>
  <how-to-verify>
    Step A — Compose the ledger. Create
    `.planning/phases/00-legal-brand-gate/PHASE-0-CLOSURE-LEDGER.yaml`
    with this exact top-level structure (YAML, not markdown — it is
    machine-readable source of truth):

    ```yaml
    # Phase 0 Closure Ledger — Single source of truth for Phase 0 status.
    # Consumed by: ROADMAP progress rendering, Phase 2 pre-execution gate,
    # future audit / counsel review.
    #
    # Rubric for phase_0_verdict derivation (deterministic):
    #   - All 5 SCs status=CLOSED                    -> phase_0_verdict: CLOSED
    #   - SC#1 BLOCKED                                -> phase_0_verdict: BLOCKED
    #     (SC#1 is the only SC whose BLOCKED state directly prevents
    #      phase_2_execution_gate from opening; see D-01 + ROADMAP.md)
    #   - SC#2 verdict BLOCKED but fallback-plan doc exists
    #                                                -> phase_0_verdict: CLOSED-WITH-CONDITIONS
    #     (D-07: fallback covers Fab rejection; Phase 8 shifts to direct-download primary)
    #   - Any other SC at PENDING                    -> phase_0_verdict: PENDING
    #   - Any SC at BLOCKED with no fallback         -> phase_0_verdict: BLOCKED
    #
    # Rubric for phase_2_execution_gate:
    #   - SC#1 PERMITTED or CONDITIONAL              -> phase_2_execution_gate: OPEN (or OPEN-WITH-CONDITIONS)
    #   - SC#1 BLOCKED                               -> phase_2_execution_gate: CLOSED
    #     (Phase 2 must not ship subscription-driving code until SC#1 opens)
    #   - SC#1 PENDING                               -> phase_2_execution_gate: PENDING

    phase: 00-legal-brand-gate
    ledger_version: 1.0
    ledger_authored_date: <ISO-8601>
    founder: <founder name>
    founder_signoff: false    # flipped to true only after founder reviews every evidence file
    founder_signoff_date: null
    phase_0_verdict: PENDING | CLOSED | CLOSED-WITH-CONDITIONS | BLOCKED
    phase_2_execution_gate: PENDING | OPEN | OPEN-WITH-CONDITIONS | CLOSED

    success_criteria:
      - sc_id: SC-1
        description: "Written Anthropic ToS clarification on subprocess-driving user's local claude CLI"
        responsible_plan: 00-01-anthropic-tos-email
        evidence_files:
          - .planning/phases/00-legal-brand-gate/correspondence/00-01-anthropic-tos-email-draft.md
          - .planning/phases/00-legal-brand-gate/correspondence/00-01-anthropic-tos-email-sent.md
          - .planning/phases/00-legal-brand-gate/correspondence/00-01-anthropic-tos-email-response.md
          - .planning/phases/00-legal-brand-gate/external-snapshots/anthropic-commercial-terms-SNAPSHOT.md
          - .planning/phases/00-legal-brand-gate/external-snapshots/anthropic-consumer-terms-SNAPSHOT.md
          - .planning/phases/00-legal-brand-gate/external-snapshots/claude-agent-sdk-overview-SNAPSHOT.md
          - .planning/phases/00-legal-brand-gate/external-snapshots/claude-code-cli-reference-SNAPSHOT.md
        status: PENDING | CLOSED | BLOCKED
        verdict: PERMITTED | CONDITIONAL | BLOCKED | null   # mirrors 00-01 response file
        closure_date: null | <ISO-8601>
        conditions: []   # populated if CONDITIONAL
        notes: ""

      - sc_id: SC-2
        description: "Written Epic/Fab AI-plugin policy pre-clearance + direct-download fallback plan documented"
        responsible_plan: 00-02-epic-fab-policy-email
        evidence_files:
          - .planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-draft.md
          - .planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-sent.md
          - .planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-response.md
          - .planning/phases/00-legal-brand-gate/legal/00-02-direct-download-fallback-plan.md
          - .planning/phases/00-legal-brand-gate/external-snapshots/fab-content-guidelines-SNAPSHOT.md
          - .planning/phases/00-legal-brand-gate/external-snapshots/fab-ai-disclosure-policy-SNAPSHOT.md
          - .planning/phases/00-legal-brand-gate/external-snapshots/fab-code-plugin-checklist-SNAPSHOT.md
        status: PENDING | CLOSED | BLOCKED
        fab_verdict: PERMITTED | CONDITIONAL | BLOCKED | null   # mirrors 00-02 response file
        fallback_plan_authored: true | false
        phase_8_primary_distribution: Fab | direct-download | undecided
        closure_date: null | <ISO-8601>
        conditions: []
        notes: ""

      - sc_id: SC-3
        description: "NYRA trademark screening (USPTO+EUIPO+WIPO Class 9/42/41) clean OR backup name selected; domains + GitHub org + social handles reserved"
        responsible_plan: 00-03-trademark-screening
        evidence_files:
          - .planning/phases/00-legal-brand-gate/trademark/00-03-nyra-screening-dossier.md
          - .planning/phases/00-legal-brand-gate/trademark/00-03-uspto-tess-raw.md
          - .planning/phases/00-legal-brand-gate/trademark/00-03-euipo-esearch-raw.md
          - .planning/phases/00-legal-brand-gate/trademark/00-03-wipo-brand-db-raw.md
          - .planning/phases/00-legal-brand-gate/trademark/00-03-backup-names-screening.md
          - .planning/phases/00-legal-brand-gate/trademark/00-03-verdict-and-reservations.md
        status: PENDING | CLOSED | BLOCKED
        screening_verdict: CLEAN | MEDIUM-RISK | BLOCKED   # mirrors 00-03 dossier aggregate_verdict
        final_name: NYRA | <backup name>
        final_name_source: primary | backup
        filing_status: DEFERRED-TO-V1.1
        devlog_gate: OPEN | CLOSED
        reservations_complete: true | false   # all 4: domain + fallback domain + github org + social handle
        closure_date: null | <ISO-8601>
        notes: ""

      - sc_id: SC-4
        description: "Gemma license re-verified for commercial Fab redistribution; NYRA v1 EULA first draft covers generated-content liability + reference-video ephemeral processing"
        responsible_plan: 00-04-gemma-license-and-eula-draft
        evidence_files:
          - .planning/phases/00-legal-brand-gate/external-snapshots/gemma-terms-of-use-SNAPSHOT.md
          - .planning/phases/00-legal-brand-gate/legal/00-04-gemma-license-reverify-note.md
          - .planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-draft.md
          - .planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-gemma-notice-appendix.md
        status: PENDING | CLOSED
        gemma_reverify_verdict: UNCHANGED | NON-MATERIAL-CHANGES | MATERIAL-CHANGES
        eula_draft_status: founder-first-draft   # counsel review deferred per D-06
        closure_date: null | <ISO-8601>
        notes: ""

      - sc_id: SC-5
        description: "Anthropic + OpenAI + Epic + Fab brand-use guidelines archived; neutral-phrasing Fab listing copy fragments authored; no third-party logos on v1 listing"
        responsible_plan: 00-05-brand-guideline-archive-and-copy
        evidence_files:
          - .planning/phases/00-legal-brand-gate/external-snapshots/anthropic-brand-guidelines-SNAPSHOT.md
          - .planning/phases/00-legal-brand-gate/external-snapshots/openai-brand-guidelines-SNAPSHOT.md
          - .planning/phases/00-legal-brand-gate/external-snapshots/epic-games-brand-guidelines-SNAPSHOT.md
          - .planning/phases/00-legal-brand-gate/external-snapshots/fab-seller-branding-policy-SNAPSHOT.md
          - .planning/phases/00-legal-brand-gate/brand/00-05-brand-compliance-summary.md
          - .planning/phases/00-legal-brand-gate/brand/00-05-fab-listing-copy-fragments.md
        status: PENDING | CLOSED
        permission_requests_queue: ALL-NOT-REQUESTED | SOME-REQUESTED | NONE
        phase_8_dist_01_handoff_ready: true | false
        closure_date: null | <ISO-8601>
        notes: ""

    # Derived fields — update whenever per-SC status changes.
    summary:
      total_scs: 5
      closed_scs: 0
      pending_scs: 5
      blocked_scs: 0
      conditions_count: 0

    # Founder sign-off block — this is the non-negotiable seal.
    # Before flipping founder_signoff: true, the founder must:
    # 1. Read every evidence file listed above.
    # 2. Confirm each per-SC status matches the evidence.
    # 3. Confirm phase_0_verdict + phase_2_execution_gate derivation is correct.
    # 4. Sign below.
    founder_signoff_block:
      reviewed_all_evidence: false   # founder flips to true after reviewing
      signoff_statement: null        # e.g. "Phase 0 closed <date>, Phase 2 may execute within conditions X/Y"
      signoff_date: null
      signed_by: null
    ```

    Step B — Populate per-SC status fields.

    For each SC entry, open the responsible plan's primary closure file:
    - SC#1: read `verdict:` field from
      `correspondence/00-01-anthropic-tos-email-response.md` frontmatter.
      Copy into the ledger's `verdict:` field. If the response file does
      not exist yet (external reply still pending), set
      `status: PENDING`, `verdict: null`.
    - SC#2: read `verdict:` from
      `correspondence/00-02-epic-fab-policy-email-response.md`. Verify
      `legal/00-02-direct-download-fallback-plan.md` exists. Set
      `fab_verdict`, `fallback_plan_authored`,
      `phase_8_primary_distribution` accordingly.
    - SC#3: read `aggregate_verdict:` from
      `trademark/00-03-nyra-screening-dossier.md` and
      `final_name:`, `filing_status:`, `devlog_gate:` from
      `trademark/00-03-verdict-and-reservations.md`. Verify the 4
      reservations (domain + fallback domain + github org + social
      handle) are populated, set `reservations_complete`.
    - SC#4: read `re_verify_verdict:` from
      `legal/00-04-gemma-license-reverify-note.md`, verify EULA draft
      frontmatter `status: founder-first-draft`, verify Gemma Notice
      appendix exists.
    - SC#5: verify all 4 brand snapshots + compliance summary + copy
      fragments exist. Read `permission_requests_queue_status:` from
      compliance summary + confirm `phase_8_handoff:` in copy fragments.

    For each SC, set `status: CLOSED` ONLY IF the primary verdict field
    is populated AND all evidence files exist AND (per SC specifics) any
    conditional downstream fields are populated. Otherwise `status:
    PENDING` with a one-line `notes:` explaining what's still missing.

    Step C — Derive top-level verdicts per the rubric in the ledger
    header comments. `phase_0_verdict` and `phase_2_execution_gate` are
    deterministic functions of the per-SC status fields; the ledger
    header comments spec the exact rules. Record the derivation in a
    `notes:` near the top if there is any ambiguity.

    Step D — Update `summary:` counts.

    Step E — Founder sign-off. At this point the founder:
    1. Reviews every evidence file linked in the ledger (hand-reads
       response text, dossier, EULA draft, copy fragments — confirms
       the per-SC status matches the evidence).
    2. Reviews the top-level `phase_0_verdict` + `phase_2_execution_gate`
       derivation.
    3. Flips `founder_signoff: true`, fills `founder_signoff_date:
       <ISO-8601>`, writes `signoff_statement:` as a 1–3 sentence
       paragraph (e.g. "Phase 0 closed 2026-MM-DD. SC#1 and SC#2 both
       PERMITTED; SC#3 verdict CLEAN on primary name; SC#4 Gemma
       license UNCHANGED, EULA draft ready for post-v1 counsel review;
       SC#5 copy fragments ready for Phase 8 DIST-01. Phase 2 execution
       gate is OPEN."), fills `signed_by: <founder name>`, flips
       `founder_signoff_block.reviewed_all_evidence: true`.

    If founder declines to sign (e.g. wants another round of follow-up
    with Anthropic, or wants counsel review of the EULA before closure):
    leave `founder_signoff: false`. The ledger stays AUTHORED but not
    CLOSED; downstream automation treats this as equivalent to
    `phase_0_verdict: PENDING`. Open a new planning conversation for
    whatever follow-up is needed.

    Step F — Propagate closure to project-root docs.

    1. Update `.planning/ROADMAP.md`:
       - Phase 0 row in the top `## Phases` bullet list: flip to
         `[x] **Phase 0: Legal & Brand Gate**` with closure note citing
         the ledger path.
       - `## Phase Details` §"Phase 0" body: add a "Status: CLOSED
         <date> per PHASE-0-CLOSURE-LEDGER.yaml (verdict: <value>,
         phase_2_execution_gate: <value>)" line after the Goal/Depends/
         Requirements block.
       - `## Phase Details` §"Phase 2" body: if `phase_2_execution_gate`
         is OPEN-WITH-CONDITIONS, add the conditions list there so the
         Phase 2 planner sees them.
       - Progress table: Phase 0 row flipped to `Complete` with
         `Completed` date column populated.

    2. Update `.planning/REQUIREMENTS.md`:
       - PLUG-05 traceability row status: `Pending` -> `Complete`.

    3. Update `.planning/STATE.md`:
       - `## Progress by phase (REQ-ID coverage)` table: Phase 0 row
         status -> `Complete` with closure date.
       - Frontmatter `current_phase:` — do not change if a later phase
         is in-flight; if Phase 0 was the current focus, advance to
         next active phase or record "next: Phase 2 (pending Phase 1
         empirical gate per STATE.md header)".
       - `## Accumulated Context` section: append a new
         `### Decisions from Phase 0 (YYYY-MM-DD)` block summarising the
         5 SC verdicts + any conditions + the final product name (NYRA
         or backup).

    Commit with a single atomic commit
    `docs(00-06): close Phase 0 — consolidate 5 SC closures into ledger + propagate to ROADMAP/REQUIREMENTS/STATE`.
    (If founder sign-off is deferred, commit with
    `docs(00-06): author Phase 0 closure ledger (pending founder sign-off)`
    and DO NOT update ROADMAP/REQUIREMENTS/STATE until sign-off lands.)
  </how-to-verify>
  <resume-signal>Type "approved: ledger-closed" with founder sign-off, "approved: ledger-authored" if sign-off deferred, or paste the ledger path + phase_0_verdict value.</resume-signal>
</task>

</tasks>

<verification>
Phase 0 overall closure verification:
- [ ] PHASE-0-CLOSURE-LEDGER.yaml exists with all 5 SC entries populated
- [ ] Each SC status is CLOSED | PENDING | BLOCKED based on evidence files
- [ ] phase_0_verdict and phase_2_execution_gate are derived per the rubric
- [ ] founder_signoff is true (ledger CLOSED) or false (ledger AUTHORED only)
- [ ] If CLOSED: ROADMAP + REQUIREMENTS + STATE updated in same commit
- [ ] If AUTHORED-ONLY: ROADMAP/REQUIREMENTS/STATE left alone, follow-up planning conversation opened
</verification>

<success_criteria>
Phase 0 is CLOSED when:
1. PHASE-0-CLOSURE-LEDGER.yaml exists with founder_signoff: true and
   phase_0_verdict: CLOSED or CLOSED-WITH-CONDITIONS.
2. ROADMAP.md Phase 0 row + REQUIREMENTS.md PLUG-05 row + STATE.md
   progress table all reflect Phase 0 closure.
3. Phase 2 planning can read `phase_2_execution_gate:` from the ledger
   to determine whether subscription-driving code may start shipping.

Phase 0 is BLOCKED when:
1. phase_0_verdict: BLOCKED (typically triggered by SC#1 verdict BLOCKED
   with no fallback — meaning Anthropic explicitly said no).
2. Founder opens a rescope-planning session; fallback path is the "bring
   your own Anthropic API key" advanced-config mode per STACK.md
   Alternatives Considered.

Phase 0 is AUTHORED-BUT-PENDING when:
1. Founder has not yet signed off (founder_signoff: false).
2. Or any of SC#1/SC#2 are still waiting on external replies.
3. Ledger is committed and readable; downstream automation treats it as
   PENDING until founder_signoff flips.
</success_criteria>

<output>
After completion, create `.planning/phases/00-legal-brand-gate/00-06-SUMMARY.md`
following the GSD summary template. Record: ledger authoring date,
founder sign-off date (if signed), final phase_0_verdict,
phase_2_execution_gate, and any conditions carried forward to Phase 2.
</output>
