---
plan: 00-01-anthropic-tos-email
status: placeholder — awaiting Anthropic reply + founder verdict
schema_version: 1
received_date: "PENDING — <ISO-8601 UTC when the reply lands in the founder's inbox>"
responder_address: "PENDING — <replying address from Anthropic, redacted if personal, e.g. support-agent-name@anthropic.com or partnerships@anthropic.com>"
responder_name: "PENDING — <responder's displayed name, redacted if personal>"
thread_id: "PENDING — <must match correspondence/00-01-anthropic-tos-email-sent.md Message-Id / Thread-URL>"
verdict: "PENDING — PERMITTED | CONDITIONAL | BLOCKED | UNCLEAR"
phase_2_gate: "PENDING — OPEN | OPEN-WITH-CONDITIONS | CLOSED  (derived from verdict per PLAN.md <how-to-verify> step 6)"
pending_manual_verification: true
founder_signoff_date: "PENDING — <ISO-8601 UTC of founder sign-off>"
founder_signoff_name: "PENDING — <founder full name>"
closes: "ROADMAP.md Phase 0 SC#1 (once verdict is PERMITTED or CONDITIONAL)"
---

> ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
> ⚠ **PLACEHOLDER — Anthropic has not replied yet. Until they do, Phase 2
> execution remains GATED per ROADMAP.md.**
>
> This file is the *schema* for the response record. The founder fills
> every PENDING cell when Anthropic replies. The schema is committed
> pre-reply so that:
>
>   (a) the Plan 00-01 audit trail has a named, committed file tracking
>       the outstanding obligation *before* the reply arrives (plan is
>       `autonomous: false` with `pending_manual_verification: true` —
>       same honest partial-completion pattern Phase 1 Plan 15 used for
>       ring0-bench-results.md);
>
>   (b) the closure ledger (Plan 00-06) reads these exact field names
>       when it flips SC#1 PENDING → CLOSED. The field names are
>       locked — do NOT rename them during fill-in;
>
>   (c) if multiple rounds of clarification are needed, the `##
>       Follow-ups` section at the bottom carries the full chain.
>
> **Phase 2 execution blocker status:** BLOCKED. Do not start Phase 2
> code until `verdict` is set to `PERMITTED` or `CONDITIONAL` and the
> `Approved:` sign-off line at the bottom is filled in.
> ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## When the reply arrives — founder procedure

1. **Open the reply email** in your mail client. Note the received-timestamp (ISO-8601 UTC), the responding email address, the responder's name if given, and the thread URL. Verify the thread-id matches the one recorded in `00-01-anthropic-tos-email-sent.md`.

2. **Replace the PENDING cells in the frontmatter above.** Do NOT rename any field; only fill values.

3. **Paste the FULL reply body verbatim** under the `## Anthropic's Verbatim Reply` section below, as a quoted block. Do not paraphrase. Do not trim. If the reply has multiple paragraphs, keep them. If the reply includes signature/disclaimer boilerplate, keep it. The full text is the audit artifact.

4. **Write the founder interpretation** under `## Founder Interpretation` — 3 to 6 sentences explaining how you read the reply and why you chose the verdict bit.

5. **If the first reply was ambiguous** and a second round was needed, record the full chain under `## Follow-ups`. Every round goes in; nothing is paraphrased.

6. **Fill the Sign-off block** at the bottom with today's ISO-8601 date, your name, the chosen verdict, and the derived Phase 2 gate status.

7. **Commit** with `docs(00-01): file Anthropic response + founder verdict`. After this commit, Plan 00-06 (closure ledger) re-reads this file and flips SC#1.

## Verdict semantics (reference)

| Verdict | Phase 2 gate | Action |
| --- | --- | --- |
| `PERMITTED` | `OPEN` | Proceed with Phase 2 planning + execution. No conditions to comply with. |
| `CONDITIONAL` | `OPEN-WITH-CONDITIONS` | Record the conditions under `## Conditions to Comply With Pre-Launch`. Phase 2 planning may start; any plan that touches the conditions MUST cite this file. |
| `BLOCKED` | `CLOSED` | Do NOT start Phase 2. Open a new planning conversation to rescope to the advanced-config "bring your own Anthropic API key" fallback path (documented in RESEARCH STACK as "Alternatives Considered"). |
| `UNCLEAR` | `PENDING` | Send a clarifying follow-up email in the same thread. Re-run this task when the clarified answer lands. Do NOT set a verdict on `UNCLEAR` — keep it PENDING. |

## Anthropic's Verbatim Reply

> **PENDING — paste the FULL reply body here verbatim as a quoted block.**
>
> Example shape of a real reply (for illustration only; delete when filling):
>
> > Hi \<founder-name\>,
> >
> > Thanks for the detailed question. We can confirm that a third-party
> > product which subprocess-invokes a user's own, locally-installed
> > `claude` CLI — with credentials managed by the user's own
> > `claude setup-token` flow and stored on their machine — is
> > permitted under our Commercial and Consumer Terms, provided you
> > continue to [condition 1], [condition 2], ...
> >
> > Best,
> > \<responder-name\>, Anthropic Support / Partnerships

## Founder Interpretation

**PENDING — 3 to 6 sentences covering:**

1. Which of the 4 verdict values you chose and why.
2. Which specific phrases in the reply (quote them) support your reading.
3. Any caveats the reply attached (e.g., "as long as you comply with the AUP" is a CONDITIONAL flag).
4. Whether the reply references a future "approved" third-party program that NYRA might want to apply to.

## Conditions to Comply With Pre-Launch

*(This section exists only if verdict = `CONDITIONAL`. Otherwise delete the section at fill-in time.)*

**PENDING — enumerate the conditions Anthropic placed on the permission.**

Each condition gets:

- A one-line statement of the condition.
- The Phase / Plan that will implement compliance (so the obligation is traceable).
- A verification bullet — how we'll confirm compliance at Fab submission.

Example (illustrative):

| # | Condition | Implementing plan | Verification |
|---|-----------|-------------------|--------------|
| 1 | AUP passthrough in NYRA EULA | 00-04 (EULA draft) | Grep EULA for "Acceptable Use Policy" link |
| 2 | Explicit user consent on first run | 02-XX (onboarding) | First-run UX test checks for consent dialog |
| 3 | No rate-limit advertising | 00-05 (brand copy) | Fab listing copy review — no claims about token limits |

## Follow-ups

*(Use this section if the first reply was ambiguous and a second round was needed. Append rows; do not edit old ones.)*

| Round | Date (UTC) | Direction | Summary | Verbatim text file |
|-------|------------|-----------|---------|--------------------|
| 1 | PENDING | NYRA → Anthropic | initial ToS clarification question | correspondence/00-01-anthropic-tos-email-draft.md + -sent.md |
| 2 | PENDING | Anthropic → NYRA | first reply (this file's `## Anthropic's Verbatim Reply`) | (this file) |
| 3 | PENDING | NYRA → Anthropic | (if needed) clarifying follow-up | (append as `-sent-round-3.md`) |
| 4 | PENDING | Anthropic → NYRA | (if needed) clarifying reply | (append as `-response-round-4.md`) |

## Sign-off

```
Approved: <today ISO-8601 UTC>, <founder full name>
Interpretation: <PERMITTED | CONDITIONAL | BLOCKED>
Phase 2 gate: <OPEN | OPEN-WITH-CONDITIONS | CLOSED>
```

**PENDING — fill in the three lines above. This triplet is the exact
string the Plan 00-06 closure ledger grep-lookups for to flip SC#1.**

---

*Plan: 00-01-anthropic-tos-email*
*Placeholder response-record committed: 2026-04-24*
*pending_manual_verification: true — Phase 2 execution remains GATED*
