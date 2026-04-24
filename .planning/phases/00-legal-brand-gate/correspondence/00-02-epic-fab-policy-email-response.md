---
plan: 00-02-epic-fab-policy-email
status: placeholder — awaiting Epic/Fab reply + founder verdict
schema_version: 1
received_date: "PENDING — <ISO-8601 UTC when the reply lands in the founder's inbox>"
responder_address: "PENDING — <replying address from Fab/Epic, redacted if personal, e.g. sellers@fab.com / fab-support@epicgames.com / named-reviewer@epicgames.com / devrel@epicgames.com>"
responder_name: "PENDING — <responder's displayed name, redacted if personal>"
thread_id: "PENDING — <must match correspondence/00-02-epic-fab-policy-email-sent.md Message-Id / Thread-URL>"
verdict: "PENDING — PERMITTED | CONDITIONAL | BLOCKED | UNCLEAR"
expected_review_turnaround: "PENDING — <Fab's answer to Q2, verbatim>"
pre_submission_channel: "PENDING — <Fab's answer to Q3, verbatim>"
phase_2_gate: "PENDING — OPEN | OPEN-WITH-CONDITIONS | CLOSED  (derived from verdict per PLAN.md <how-to-verify> step 6 — note: BLOCKED does NOT close Phase 2 gate because Phase 2 is independent of Fab approval per PLAN.md verdict semantics; Phase 2 is gated on Plan 00-01 Anthropic verdict, not Plan 00-02 Fab verdict)"
phase_8_primary_distribution: "PENDING — Fab | direct-download fallback  (derived: PERMITTED or CONDITIONAL → Fab primary; BLOCKED → direct-download primary per CONTEXT.md D-07; UNCLEAR → PENDING)"
pending_manual_verification: true
founder_signoff_date: "PENDING — <ISO-8601 UTC of founder sign-off>"
founder_signoff_name: "PENDING — <founder full name>"
closes: "ROADMAP.md Phase 0 SC#2 (closure requires EITHER PERMITTED/CONDITIONAL verdict for Fab-primary path OR BLOCKED verdict + existence of legal/00-02-direct-download-fallback-plan.md for fallback-primary path; UNCLEAR does NOT close SC#2)"
---

> ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
> ⚠ **PLACEHOLDER — Epic/Fab has not replied yet.**
>
> This file is the *schema* for the response record. The founder fills
> every PENDING cell when Epic/Fab replies. The schema is committed
> pre-reply so that:
>
>   (a) the Plan 00-02 audit trail has a named, committed file tracking
>       the outstanding obligation *before* the reply arrives (plan is
>       `autonomous: false` with `pending_manual_verification: true` —
>       same honest partial-completion pattern Plan 00-01 used for
>       correspondence/00-01-anthropic-tos-email-response.md, which in
>       turn mirrored Phase 1 Plan 15's ring0-bench-results.md);
>
>   (b) the closure ledger (Plan 00-06) reads these exact field names
>       when it flips SC#2 PENDING → CLOSED. The field names are
>       locked — do NOT rename them during fill-in;
>
>   (c) if multiple rounds of clarification are needed, the `##
>       Follow-ups` section at the bottom carries the full chain.
>
> **Phase 2 execution blocker status:** **NOT BLOCKED** on this plan's
> verdict. Per PLAN.md `<how-to-verify>` step 6 + CONTEXT.md D-07:
> Phase 2 gate is governed by Plan 00-01 (Anthropic ToS) verdict. This
> plan's verdict governs Phase 8 PRIMARY-DISTRIBUTION-PATH choice, not
> Phase 2 execution gating. BLOCKED here shifts Phase 8 to the
> direct-download fallback per CONTEXT.md D-07; it does not block
> NYRA from shipping.
>
> **SC#2 closure rule:** SC#2 closes on ANY of:
>   - `verdict: PERMITTED` — Fab primary, fallback as insurance
>   - `verdict: CONDITIONAL` — Fab primary with conditions recorded,
>     fallback as insurance
>   - `verdict: BLOCKED` + `legal/00-02-direct-download-fallback-plan.md`
>     exists (which it does — Plan 00-02 Task 2 committed it) →
>     fallback primary per CONTEXT.md D-07
>
> SC#2 does NOT close on `verdict: UNCLEAR` (triggers clarifying
> follow-up round).
> ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## When the reply arrives — founder procedure

1. **Open the reply email** in your mail client. Note the received-
   timestamp (ISO-8601 UTC), the responding email address, the
   responder's name if given, and the thread URL. Verify the thread-id
   matches the one recorded in
   `correspondence/00-02-epic-fab-policy-email-sent.md`.

2. **Replace the PENDING cells in the frontmatter above.** Do NOT
   rename any field; only fill values. Pay particular attention to:
   - `expected_review_turnaround` — Fab's verbatim answer to Q2 (e.g.
     "Code Plugins with AI-content disclosure currently take 4-8
     weeks to review, with higher variance for plugins using multiple
     third-party AI services")
   - `pre_submission_channel` — Fab's verbatim answer to Q3 (e.g.
     "Continue using seller-support for now; we'll loop in dev-rel
     when AI disclosures are complex")

3. **Paste the FULL reply body verbatim** under the `## Epic/Fab's
   Verbatim Reply` section below, as a quoted block. Do not paraphrase.
   Do not trim. Signature boilerplate + disclaimers stay. Full text is
   the audit artifact.

4. **Write the founder interpretation** under `## Founder
   Interpretation` — 3 to 6 sentences explaining how you read each of
   the 3 answers (Q1 / Q2 / Q3) and why you chose the verdict bit.

5. **If verdict = CONDITIONAL,** fill the `## Conditions to Comply With
   Pre-Launch` section with each condition + the downstream Phase /
   Plan that implements compliance + the verification bullet.

6. **If verdict = BLOCKED,** note under `## Fallback Activation` which
   of the direct-download-fallback triggers fires (Trigger (a) per
   `legal/00-02-direct-download-fallback-plan.md` §1) and confirm Phase
   8 DIST-02 promotes to primary distribution.

7. **If the first reply was ambiguous** and a second round was needed,
   record the full chain under `## Follow-ups`. Every round goes in;
   nothing is paraphrased.

8. **Fill the Sign-off block** at the bottom with today's ISO-8601
   date, your name, the chosen verdict, the derived Phase 2 gate
   status, and the derived Phase 8 primary-distribution path.

9. **Commit** with `docs(00-02): file Epic/Fab response + founder
   verdict (<PERMITTED|CONDITIONAL|BLOCKED|BLOCKED-BY-SILENCE>)`. After
   this commit, Plan 00-06 (closure ledger) re-reads this file and
   flips SC#2.

## Verdict semantics (reference)

| Verdict | Phase 2 gate | Phase 8 primary distribution | Action |
| --- | --- | --- | --- |
| `PERMITTED` | OPEN (per Plan 00-01) | Fab | Proceed with Fab submission in Phase 8. Fallback plan stays as shelf-ready insurance. |
| `CONDITIONAL` | OPEN (per Plan 00-01) | Fab (with conditions) | Record each condition under `## Conditions to Comply With Pre-Launch`. Any plan that implements a condition MUST cite this file. Fallback remains insurance. |
| `BLOCKED` | OPEN (per Plan 00-01) | direct-download fallback | Phase 2 execution is NOT blocked by this verdict — it's independent. Phase 8 promotes `legal/00-02-direct-download-fallback-plan.md` Trigger (a). NYRA ships via direct-download. Fab listing attempted post-v1 if the rejection reason becomes addressable. |
| `UNCLEAR` | PENDING | PENDING | Send a clarifying follow-up email in the same thread. Re-run this task when the clarified answer lands. Do NOT set a verdict on `UNCLEAR` — keep it PENDING in the closure ledger. |
| `BLOCKED-BY-SILENCE` | OPEN (per Plan 00-01) | direct-download fallback | 63+ days since send with no reply despite the Day 21/42/63 nudge cadence. Treated as BLOCKED for SC#2 closure purposes; direct-download fallback goes primary. Founder opens a new planning conversation to escalate (LinkedIn Epic dev-rel, Epic community forum) in parallel. |

## Special case: "BLOCKED-BY-SILENCE" escalation path

If 63 days pass with no reply despite the Day 21 / Day 42 / Day 63
follow-up cadence in `00-02-epic-fab-policy-email-sent.md`:

1. **Day 63:** Founder sets `verdict: BLOCKED-BY-SILENCE` in the
   frontmatter, fills the Sign-off block, and commits.
2. **SC#2 closes** with `phase_8_primary_distribution: direct-download
   fallback`. Phase 8 DIST-02 executes first (promoted above DIST-01).
3. **Parallel escalation:** Founder opens a new planning conversation
   for escalation actions — LinkedIn outreach to an Epic dev-rel
   person, posting on the Epic community forum's Fab seller category,
   or submitting a new help-center ticket via the fab.com/help form.
   These are NOT part of Plan 00-02 Task 3 closure; they are
   bookkeeping the founder does to maximize the chance of a Fab
   listing eventually clearing post-v1.
4. **If a real reply lands post-BLOCKED-BY-SILENCE,** this response
   file is re-opened, a new `## Follow-ups` round is logged, and the
   verdict is updated. The closure ledger re-reads and flips as
   appropriate.

## Epic/Fab's Verbatim Reply

> **PENDING — paste the FULL reply body here verbatim as a quoted
> block.**
>
> Example shape of a real reply (for illustration only; delete when
> filling):
>
> > Hi \<founder-name\>,
> >
> > Thanks for the detailed disclosure — this is the kind of submission
> > we like to see pre-cleared. To answer in order:
> >
> > Q1. The disclosure pattern you've outlined — subprocess-driving the
> > user's own Claude CLI, user-provided Meshy/ComfyUI credentials,
> > computer-use scoped to Substance + UE modals, and an optional local
> > Gemma fallback — is acceptable for a free Code Plugin submission
> > provided (1) all five providers are listed by name in your AI-
> > Content disclosure form, (2) the "no NYRA-owned backend" claim is
> > reiterated in the plugin description, and (3) the Gemma first-run
> > download prompt explicitly discloses the ~3.16GB size + license.
> >
> > Q2. Code Plugin reviews with AI-content disclosure currently
> > target 4-8 weeks; plugins invoking multiple providers can take the
> > full 8 weeks.
> >
> > Q3. For pre-submission clarifications continue to use this
> > seller-support inbox; for ongoing AI-disclosure questions (e.g.
> > when you add Codex at v1.1) we can loop in dev-rel — feel free to
> > reply in this thread and we'll coordinate.
> >
> > Best,
> > \<responder-name\>, Fab Seller Support

## Founder Interpretation

**PENDING — 3 to 6 sentences covering:**

1. Which of the 5 verdict values you chose (PERMITTED, CONDITIONAL,
   BLOCKED, UNCLEAR, or BLOCKED-BY-SILENCE) and why.
2. Which specific phrases in the reply (quote them) support your
   reading — particularly for Q1 (disclosure acceptability — the
   gating question).
3. Any caveats the reply attached (e.g., "provided you also..." is a
   CONDITIONAL flag; "we cannot approve at this time" is a BLOCKED
   flag).
4. Your reading of Q2's turnaround — does it exceed the launch window
   by >4 weeks? If so, note that Trigger (b) of the fallback plan
   (`legal/00-02-direct-download-fallback-plan.md` §1) fires even if
   verdict is PERMITTED — direct-download launches first, Fab listing
   follows when it clears.
5. Q3's pre-submission channel — did they confirm a dev-rel contact?
   If yes, record it for Plan 00-02 v1.1 follow-up (when Codex lands).

## Conditions to Comply With Pre-Launch

*(This section exists only if verdict = `CONDITIONAL`. Otherwise
delete the section at fill-in time.)*

**PENDING — enumerate the conditions Fab placed on the permission.**

Each condition gets:

- A one-line statement of the condition (quoted from the reply).
- The Phase / Plan that will implement compliance.
- A verification bullet — how we'll confirm compliance at Fab
  submission time.

Example (illustrative — delete when filling):

| # | Condition | Implementing plan | Verification |
|---|-----------|-------------------|--------------|
| 1 | List all 5 AI providers by name in AI-Content disclosure | Phase 8 DIST-01 (listing assembly) | Grep listing description for "Anthropic", "Meshy", "ComfyUI", "Google Gemma", "computer-use" |
| 2 | Reiterate "no NYRA-owned backend" in plugin description | Phase 8 DIST-01 + Plan 00-05 (brand copy) | Listing description includes verbatim "NYRA operates no backend; all traffic is localhost or user-initiated" |
| 3 | Gemma first-run download discloses size + license | Phase 2 (first-run UX — already partly delivered in Phase 1 Plan 13 diagnostics drawer) | First-run dialog shows "~3.16 GB Gemma 3 4B (Gemma license, commercial redistribution with notice)" before download |

## Fallback Activation

*(This section exists only if verdict = `BLOCKED` or `BLOCKED-BY-SILENCE`.
Otherwise delete the section at fill-in time.)*

**PENDING — when fallback activates, record:**

- Which trigger fired: Trigger (a) BLOCKED / Trigger (b) SLA-exceeds-
  window / Trigger (c) post-launch takedown (per
  `legal/00-02-direct-download-fallback-plan.md` §1)
- Phase 8 execution-order impact: DIST-02 promoted ahead of DIST-01?
  Or DIST-02 only?
- Communication plan: how the founder tells prospective users about
  the direct-download path (GitHub README + Twitter announcement +
  devlog post + any other channels)
- Timeline impact: does the fallback shift launch date, or does it
  track the original plan?
- Revisit cadence: when (if ever) will NYRA reattempt Fab submission?
  If BLOCKED for a fixable reason, schedule a revisit for v1.1.

## Follow-ups

*(Use this section if the first reply was ambiguous and a second round
was needed. Append rows; do not edit old ones.)*

| Round | Date (UTC) | Direction | Summary | Verbatim text file |
|-------|------------|-----------|---------|--------------------|
| 1 | PENDING | NYRA → Epic/Fab | initial 3-question pre-clearance | correspondence/00-02-epic-fab-policy-email-draft.md + -sent.md |
| 2 | PENDING | Epic/Fab → NYRA | first reply (this file's `## Epic/Fab's Verbatim Reply`) | (this file) |
| 3 | PENDING | NYRA → Epic/Fab | (if needed) clarifying follow-up | (append as `-sent-round-3.md`) |
| 4 | PENDING | Epic/Fab → NYRA | (if needed) clarifying reply | (append as `-response-round-4.md`) |

## Sign-off

```
Approved: <today ISO-8601 UTC>, <founder full name>
Interpretation: <PERMITTED | CONDITIONAL | BLOCKED | BLOCKED-BY-SILENCE>
Phase 2 gate: OPEN  (per Plan 00-01; this plan does not gate Phase 2 per PLAN.md <how-to-verify> step 6)
Phase 8 primary distribution: <Fab | direct-download fallback>
```

**PENDING — fill in the four lines above. The triplet (Approved /
Interpretation / Phase 8 primary distribution) is the exact string the
Plan 00-06 closure ledger grep-lookups for to flip SC#2.**

---

*Plan: 00-02-epic-fab-policy-email*
*Placeholder response-record committed: 2026-04-24*
*pending_manual_verification: true — SC#2 closure deferred to founder receipt + fill of this file, OR to Day 63 BLOCKED-BY-SILENCE path triggering fallback-primary distribution*
