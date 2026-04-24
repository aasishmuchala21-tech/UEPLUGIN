---
plan: 00-02-epic-fab-policy-email
status: placeholder — awaiting founder send + founder fills cells below
draft_source: correspondence/00-02-epic-fab-policy-email-draft.md
schema_version: 1
# The cells below are PLACEHOLDERS. The founder replaces them with the
# real values AFTER clicking send in their mail client. Schema is frozen
# so the closure ledger (Plan 00-06) can read these fields programmatically.
# Pattern mirrors correspondence/00-01-anthropic-tos-email-sent.md verbatim.
To: "PENDING — <recipient-address-as-sent>  (primary: Fab seller-support address surfaced from fab.com/help Content Guidelines footer at send-time — typically fab-support@epicgames.com or sellers@fab.com; fallback: devrel@epicgames.com or prior Epic dev-rel contact)"
Cc: "PENDING — empty on first send unless founder has prior Epic dev-rel contact to Cc; append here"
From: "PENDING — <founder>@<personal-domain>  (redact local part to `<founder>@` in the committed version)"
Subject: "Free UE plugin pre-clearance — AI-content disclosure + network-call pattern"
Date-sent: "PENDING — <ISO-8601 UTC timestamp, e.g. 2026-04-24T18:42:07Z>"
Message-Id: "PENDING — <Message-Id: header or Gmail thread-id from the sender's Sent Mail>"
Email-provider: "PENDING — e.g. Gmail / Fastmail / ProtonMail"
Thread-URL: "PENDING — <link to the sent message in the founder's mail client, so the thread can be reopened later>"
draft_was_edited_before_send: "PENDING — yes / no  (if yes, paste the final body verbatim under '## Final body as sent' below)"
attachments_sent:
  - "PENDING — fab-content-guidelines-snapshot-2026-04-24.pdf (export of external-snapshots/fab-content-guidelines-SNAPSHOT.md)"
  - "PENDING — fab-ai-disclosure-policy-snapshot-2026-04-24.pdf (export of external-snapshots/fab-ai-disclosure-policy-SNAPSHOT.md)"
  - "PENDING — fab-code-plugin-checklist-snapshot-2026-04-24.pdf (export of external-snapshots/fab-code-plugin-checklist-SNAPSHOT.md)"
---

> ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
> ⚠ **PLACEHOLDER — founder has not yet sent the email.**
>
> This file is the *schema* for the sent-record. Every `PENDING — …` cell
> in the frontmatter above is replaced with the real value after the
> founder clicks Send. The committed placeholder exists so that:
>
>   (a) the Plan 00-02 audit trail has a named, committed file *before*
>       the send happens (plan is `autonomous: false`; this is the
>       partial-completion artifact Plan 00-01 established as the Phase 0
>       correspondence-triad pattern);
>
>   (b) the Date-sent: line is present (Task 1 `<automated>` verify
>       command `grep -q "Date-sent:"` passes);
>
>   (c) when the founder sends, they edit this file in-place — they
>       do NOT rename it, do NOT create a new file, do NOT lose the
>       schema;
>
>   (d) the closure ledger (Plan 00-06) reads these exact field names
>       when it flips SC#2 PENDING → CLOSED.
> ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Founder send checklist

Before replacing the PENDING cells, run through this list:

- [ ] Open `correspondence/00-02-epic-fab-policy-email-draft.md` — read
      it end to end one more time.
- [ ] Resolve the `To:` address. Log into fab.com as a seller, open the
      Content Guidelines page via help-center left-nav, copy the
      seller-support email from the footer. If not obvious, try
      `sellers@fab.com` or `fab-support@epicgames.com`. If both bounce,
      fall back to `devrel@epicgames.com`. Record the final address in
      the frontmatter `To:` cell.
- [ ] Replace signature placeholders (`<founder-name>`, `<nyra.dev
      placeholder>`, `<nyra-ai placeholder>`) with real values. If Plan
      00-03 (trademark screening) has not yet resolved the project name,
      use the current working name + "(site coming soon)" and note in
      `pending_items` at the bottom of this file.
- [ ] Export each of the three Fab-policy snapshots
      (`external-snapshots/fab-content-guidelines-SNAPSHOT.md`,
      `fab-ai-disclosure-policy-SNAPSHOT.md`,
      `fab-code-plugin-checklist-SNAPSHOT.md`) to PDF. Attach all three.
- [ ] Copy the email body (everything between the `---` separator and
      `## Internal notes` section of the draft) into a new compose
      window.
- [ ] Verify the `To:`, `Subject:`, and attachments match the draft.
- [ ] Send from a **personal** address (not a generic alias) per D-03.
- [ ] Click Send.

## After sending

Replace the `PENDING — ...` cells in the frontmatter with the real
values. Then fill out the sections below.

## Final body as sent

> Paste the FINAL email body here verbatim, exactly as sent. If the body
> matches `correspondence/00-02-epic-fab-policy-email-draft.md` verbatim,
> it is sufficient to write:
>
> `See correspondence/00-02-epic-fab-policy-email-draft.md — sent verbatim.`
>
> If edits were made during compose, paste the full final text below.
> This matters for Task 3 — the verdict interpretation in the response
> file relies on knowing exactly what was asked.

**PENDING — paste final body here (or "sent verbatim" note).**

## Thread-lineage anchor

- Founder's outbox thread URL (so the thread can be reopened later): **PENDING**
- Gmail thread-id (if Gmail): **PENDING** — find it in the URL bar when the sent message is open.
- Message-Id (`Message-Id:` header): **PENDING** — "Show original" in Gmail / "View source" in Fastmail.

## Auto-responder received (if any)

If Fab's support system returns an immediate auto-response with a ticket
number, note it here — the real reply may reference it.

- Auto-response received: **PENDING — yes / no**
- Ticket / case number: **PENDING**
- Auto-response timestamp: **PENDING**

## Follow-up cadence tracker

Per CONTEXT.md D-10 (expected 2–4 week response window — Fab reviews are
typically busier than partner-support inboxes, so plan for the high end
of the range):

| Day / Event               | Date | Action taken | Next action |
| ------------------------- | ---- | ------------ | ----------- |
| Day 0 — sent              | PENDING | email sent to Fab seller-support address | wait 21 days before first nudge |
| Day 21 — no reply nudge   | PENDING | (if applicable) polite 2-line follow-up in same thread | wait another 21 days |
| Day 42 — no reply escalate | PENDING | (if applicable) re-send to devrel@epicgames.com (or prior Epic dev-rel contact) referencing original thread-id | plan an escalation conversation |
| Day 63 — no reply, plan-B   | PENDING | (if applicable) flag the direct-download fallback (`legal/00-02-direct-download-fallback-plan.md`) as primary distribution per CONTEXT.md D-07; file a "no response after 9 weeks" response file with verdict: BLOCKED-BY-SILENCE | — |

Append rows as events happen. Do not delete rows (audit trail).

## Pending items (open threads at send-time)

Use this section to record any draft content that was sent with a
placeholder value still embedded (e.g., signature name still to be
resolved, attachments omitted, Plan 00-03 trademark screening not
resolved).

- **PENDING — list any placeholder-still-present values in the sent email** (e.g., "sent with `<founder-name>` → founder full name; nyra.dev placeholder left generic; attachments included all 3 Fab-policy PDFs; Plan 00-03 trademark verdict not yet known").

## Parallel correspondence note

This email does NOT require Plan 00-01 (Anthropic ToS) to have replied
first. Both threads run in parallel per CONTEXT.md D-10. The draft
mentions once that the Anthropic thread is in flight and offers to
forward its reply when it lands — but the Fab reviewer's answer does
not depend on Anthropic's answer. Plan 00-01 verdict is independent of
Plan 00-02 verdict; the closure ledger (Plan 00-06) flips SC#1 and SC#2
separately.

---

*Plan: 00-02-epic-fab-policy-email*
*Placeholder sent-record committed: 2026-04-24*
*Next action: founder resolves To: address, sends email + attachments, then replaces PENDING cells.*
