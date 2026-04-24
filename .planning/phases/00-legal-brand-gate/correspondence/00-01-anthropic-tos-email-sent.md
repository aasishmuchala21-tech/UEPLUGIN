---
plan: 00-01-anthropic-tos-email
status: placeholder — awaiting founder send + founder fills cells below
draft_source: correspondence/00-01-anthropic-tos-email-draft.md
schema_version: 1
# The cells below are PLACEHOLDERS. The founder replaces them with the
# real values AFTER clicking send in their mail client. Schema is frozen
# so the closure ledger (Plan 06) can read these fields programmatically.
To: "PENDING — <recipient-address-as-sent>  (primary: support@anthropic.com; fallback: partnerships@anthropic.com)"
Cc: "PENDING — empty on first send; founder adds Cc if a forward is requested later"
From: "PENDING — <founder>@<personal-domain>  (redact local part to `<founder>@` in the committed version)"
Subject: "ToS clarification: free third-party UE plugin subprocess-driving user's local `claude` CLI"
Date-sent: "PENDING — <ISO-8601 UTC timestamp, e.g. 2026-04-24T18:42:07Z>"
Message-Id: "PENDING — <Message-Id: header or Gmail thread-id from the sender's Sent Mail>"
Email-provider: "PENDING — e.g. Gmail / Fastmail / ProtonMail"
Thread-URL: "PENDING — <link to the sent message in the founder's mail client, so the thread can be reopened later>"
draft_was_edited_before_send: "PENDING — yes / no  (if yes, paste the final body verbatim under '## Final body as sent' below)"
---

> ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
> ⚠ **PLACEHOLDER — founder has not yet sent the email.**
>
> This file is the *schema* for the sent-record. Every `PENDING — …` cell
> in the frontmatter above is replaced with the real value after the
> founder clicks Send. The committed placeholder exists so that:
>
>   (a) the Plan 00-01 audit trail has a named, committed file *before*
>       the send happens (plan is `autonomous: false`; this is the
>       partial-completion artifact Phase 1 Plan 15 established);
>
>   (b) the Date-sent: line is present (Task 2 `<automated>` verify
>       command `grep -q "Date-sent:"` passes);
>
>   (c) when the founder sends, they edit this file in-place — they
>       do NOT rename it, do NOT create a new file, do NOT lose the
>       schema;
>
>   (d) the closure ledger (Plan 00-06) reads these exact field names
>       when it flips SC#1 PENDING → CLOSED.
> ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Founder send checklist

Before replacing the PENDING cells, run through this list:

- [ ] Open `correspondence/00-01-anthropic-tos-email-draft.md` — read it end to end one more time.
- [ ] Replace signature placeholders (`<founder-name>`, `<nyra.dev placeholder>`, `<nyra-ai placeholder>`) with real values. If Plan 00-03 (trademark screening) has not yet resolved the project name, use the current working name + "(site coming soon)" and note the live name in `pending_items` at the bottom of this file.
- [ ] Copy the email body (everything between the `---` separator and the `## Internal notes` section) into a new compose window.
- [ ] Verify the `To:` field reads `support@anthropic.com`. Keep `Cc:` empty.
- [ ] Send from a **personal** address (not a generic alias) per D-03.
- [ ] Click Send.

## After sending

Replace the `PENDING — ...` cells in the frontmatter with the real values. Then fill out the sections below.

## Final body as sent

> Paste the FINAL email body here verbatim, exactly as sent. If the body
> matches `correspondence/00-01-anthropic-tos-email-draft.md` verbatim, it
> is sufficient to write:
>
> `See correspondence/00-01-anthropic-tos-email-draft.md — sent verbatim.`
>
> If edits were made during compose, paste the full final text below. This
> is important — the response-interpretation in Task 3 relies on knowing
> exactly what was asked.

**PENDING — paste final body here (or "sent verbatim" note).**

## Thread-lineage anchor

- Founder's outbox thread URL (so the thread can be reopened later): **PENDING**
- Gmail thread-id (if Gmail): **PENDING** — find it in the URL bar when the sent message is open.
- Message-Id (`Message-Id:` header): **PENDING** — "Show original" in Gmail / "View source" in Fastmail.

## Auto-responder received (if any)

If Anthropic's support system returns an immediate auto-response with a ticket number, note it here — the real reply may reference it.

- Auto-response received: **PENDING — yes / no**
- Ticket / case number: **PENDING**
- Auto-response timestamp: **PENDING**

## Follow-up cadence tracker

Per CONTEXT.md D-10 (expected 2–4 week response window):

| Day / Event               | Date | Action taken | Next action |
| ------------------------- | ---- | ------------ | ----------- |
| Day 0 — sent              | PENDING | email sent to support@anthropic.com | wait 14 days before first nudge |
| Day 14 — no reply nudge   | PENDING | (if applicable) polite 2-line follow-up in same thread | wait another 14 days |
| Day 28 — no reply escalate | PENDING | (if applicable) re-send to partnerships@anthropic.com referencing original thread-id | plan an escalation conversation |
| Day 42 — no reply, plan-B   | PENDING | (if applicable) open a new planning conversation for fallback path (advanced-config bring-your-own-API-key mode) | — |

Append rows as events happen. Do not delete rows (audit trail).

## Pending items (open threads at send-time)

Use this section to record any draft content that was sent with a
placeholder value still embedded (e.g., signature name still to be
resolved) so the interpretation in Task 3 accounts for it.

- **PENDING — list any placeholder-still-present values in the sent email** (e.g., "sent with `<founder-name>` → founder full name; nyra.dev placeholder left generic; no specific GitHub org cited").

---

*Plan: 00-01-anthropic-tos-email*
*Placeholder sent-record committed: 2026-04-24*
*Next action: founder sends email, then replaces PENDING cells.*
