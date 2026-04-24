---
phase: 00-legal-brand-gate
plan: 01
slug: anthropic-tos-email
type: execute
tdd: false
wave: 1
depends_on: []
autonomous: false
requirements: [PLUG-05]
task_count: 3
files_modified:
  - .planning/phases/00-legal-brand-gate/correspondence/00-01-anthropic-tos-email-draft.md
  - .planning/phases/00-legal-brand-gate/correspondence/00-01-anthropic-tos-email-sent.md
  - .planning/phases/00-legal-brand-gate/correspondence/00-01-anthropic-tos-email-response.md
  - .planning/phases/00-legal-brand-gate/external-snapshots/anthropic-commercial-terms-SNAPSHOT.md
  - .planning/phases/00-legal-brand-gate/external-snapshots/anthropic-consumer-terms-SNAPSHOT.md
  - .planning/phases/00-legal-brand-gate/external-snapshots/claude-agent-sdk-overview-SNAPSHOT.md
  - .planning/phases/00-legal-brand-gate/external-snapshots/claude-code-cli-reference-SNAPSHOT.md
objective: >
  Close ROADMAP Phase 0 SC#1 — get a written clarification from Anthropic,
  on the record, that NYRA's subprocess-driving of the user's own local
  `claude` CLI (via `claude -p --output-format stream-json` + `--mcp-config`
  injecting NYRA's MCP server, with OAuth living in the user's
  `~/.claude/.credentials.json`, never touched by NYRA) is permitted under
  Anthropic Commercial + Consumer Terms. This is the single non-negotiable
  blocker on Phase 2 execution (subscription bridge code). Per D-03 the
  clearance MUST land as a written email response, not a phone call or DM.
must_haves:
  truths:
    - "A sent-record of the Anthropic ToS clarification email exists under correspondence/ with subject, recipient address, sent-timestamp, and message-id (raw .eml kept outside repo; committed version is markdown with redacted personal sender info per D-03)"
    - "A written response from Anthropic (support@anthropic.com or partnerships) is filed under correspondence/ with Anthropic's verbatim language quoted, received-timestamp, and founder's interpretation/followup notes"
    - "Date-stamped snapshots of Anthropic Commercial Terms, Consumer Terms, claude-agent-sdk overview (the 'third party developers may not offer claude.ai login' paragraph), and claude code cli-reference page exist under external-snapshots/ — proving which version of Anthropic's public policy the clarification was issued against"
    - "The email draft explicitly mentions: (a) NYRA is a free Fab plugin, (b) NYRA never sees the user's OAuth token, (c) NYRA invokes `claude -p --output-format stream-json --mcp-config <path>` as a subprocess on the user's machine using the user's own `claude setup-token` credential, (d) NYRA never offers claude.ai login and never embeds the Agent SDK with NYRA-owned keys, (e) NYRA's question is: does this fit within the Commercial Terms for third-party products that interoperate with a user's personal Claude subscription?"
    - "Founder sign-off note at the bottom of the response file: 'Approved: <date>, <name>, interpretation: <PERMITTED | CONDITIONAL | BLOCKED>' — the gate closes only on a PERMITTED or CONDITIONAL verdict; BLOCKED triggers a replan per D-10"
  artifacts:
    - path: .planning/phases/00-legal-brand-gate/correspondence/00-01-anthropic-tos-email-draft.md
      provides: "The email body, pre-send — subject line, recipient list, question text, signature block"
      contains: "claude -p --output-format stream-json"
    - path: .planning/phases/00-legal-brand-gate/correspondence/00-01-anthropic-tos-email-sent.md
      provides: "Sent-record: To:, Cc:, From: (redacted), Subject:, Date-sent, Message-Id (or Gmail thread id), email provider + thread URL so the founder can find the thread later"
      contains: "Date-sent:"
    - path: .planning/phases/00-legal-brand-gate/correspondence/00-01-anthropic-tos-email-response.md
      provides: "Anthropic's verbatim reply quoted, received timestamp, founder interpretation + sign-off"
      contains: "Verdict:"
    - path: .planning/phases/00-legal-brand-gate/external-snapshots/anthropic-commercial-terms-SNAPSHOT.md
      provides: "Snapshot of https://www.anthropic.com/legal/commercial-terms at email-send date"
      contains: "Snapshot-date:"
    - path: .planning/phases/00-legal-brand-gate/external-snapshots/anthropic-consumer-terms-SNAPSHOT.md
      provides: "Snapshot of https://www.anthropic.com/legal/consumer-terms at email-send date"
      contains: "Snapshot-date:"
    - path: .planning/phases/00-legal-brand-gate/external-snapshots/claude-agent-sdk-overview-SNAPSHOT.md
      provides: "Snapshot of code.claude.com/docs/en/agent-sdk/overview — specifically the 'Anthropic does not allow third party developers to offer claude.ai login' paragraph that motivates the clarification request"
      contains: "third party developers"
    - path: .planning/phases/00-legal-brand-gate/external-snapshots/claude-code-cli-reference-SNAPSHOT.md
      provides: "Snapshot of code.claude.com/docs/en/cli-reference covering `claude setup-token` + `-p --output-format stream-json` + `--mcp-config`"
      contains: "setup-token"
  key_links:
    - from: correspondence/00-01-anthropic-tos-email-draft.md
      to: external-snapshots/claude-agent-sdk-overview-SNAPSHOT.md
      via: "Draft quotes the agent-sdk 'third party developers' paragraph verbatim as the reason for asking"
      pattern: "third party developers"
    - from: correspondence/00-01-anthropic-tos-email-response.md
      to: correspondence/00-01-anthropic-tos-email-sent.md
      via: "Response file references sent-record thread-id so the audit trail is closed-loop"
      pattern: "Thread-Id:"
    - from: correspondence/00-01-anthropic-tos-email-response.md
      to: .planning/ROADMAP.md Phase 0 SC#1
      via: "Response verdict closes SC#1; ledger (00-06) reads this file to flip the SC#1 status bit"
      pattern: "Verdict:"
---

<objective>
Phase 0 SC#1 is the single most load-bearing clearance in the whole roadmap:
NYRA's economic wedge (no-new-AI-bill, because we drive the user's own Claude
subscription) only stands up if Anthropic has said in writing that the
subprocess-driving pattern is permitted. Phase 2 execution is explicitly gated
on this per ROADMAP.md.

Per CONTEXT.md D-03 (Written-record discipline), a phone call or a Slack DM
does not close this criterion. Per D-09 (Claude's Discretion), the email tone
is direct founder-to-partner, not lawyer-to-lawyer — the goal is a clear
human-readable yes/no/conditional from a human on Anthropic's side.

Per D-10 (Sequencing), this email is sent on Day 1 alongside the Epic/Fab
email (Plan 02). The response arrives asynchronously over 2–4 weeks. This
plan is `autonomous: false` because Task 3 (file the response) cannot
complete until Anthropic replies; the founder closes the plan by executing
Task 3 at that point.

Purpose: Close SC#1 with a verifiable paper trail that stands up to Fab
review, future legal counsel review, and (worst case) a dispute.
Output: 3 correspondence markdown files (draft, sent-record, response) +
4 external-snapshot markdown files capturing the Anthropic policy surface
the clarification was issued against.
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

<task type="auto">
  <name>Task 1: Snapshot Anthropic policy surface (date-stamped external-snapshots)</name>
  <files>
    .planning/phases/00-legal-brand-gate/external-snapshots/anthropic-commercial-terms-SNAPSHOT.md,
    .planning/phases/00-legal-brand-gate/external-snapshots/anthropic-consumer-terms-SNAPSHOT.md,
    .planning/phases/00-legal-brand-gate/external-snapshots/claude-agent-sdk-overview-SNAPSHOT.md,
    .planning/phases/00-legal-brand-gate/external-snapshots/claude-code-cli-reference-SNAPSHOT.md
  </files>
  <action>
    Fetch current (live, fetched on the day the email is drafted) versions of:
    - https://www.anthropic.com/legal/commercial-terms
    - https://www.anthropic.com/legal/consumer-terms
    - https://code.claude.com/docs/en/agent-sdk/overview
    - https://code.claude.com/docs/en/cli-reference

    For each, write a markdown snapshot file with YAML frontmatter
    `source_url:`, `snapshot_date:` (today in ISO-8601), `snapshot_method:`
    (e.g. "WebFetch" or "manual-browser-copy" — whichever the executor used),
    then the full text body below the frontmatter as normalised markdown.
    For the agent-sdk page specifically, HIGHLIGHT (quote-block) the paragraph
    starting "Unless previously approved, Anthropic does not allow third
    party developers to offer claude.ai login..." — this is the paragraph the
    email asks Anthropic to clarify NYRA's position against.

    Rationale (record in the frontmatter): these snapshots establish WHICH
    version of Anthropic's public policy the clarification was issued
    against, so if Anthropic updates the terms a year from now the Phase 0
    verdict is still defensible.
  </action>
  <verify>
    <automated>test -f .planning/phases/00-legal-brand-gate/external-snapshots/anthropic-commercial-terms-SNAPSHOT.md && test -f .planning/phases/00-legal-brand-gate/external-snapshots/anthropic-consumer-terms-SNAPSHOT.md && test -f .planning/phases/00-legal-brand-gate/external-snapshots/claude-agent-sdk-overview-SNAPSHOT.md && test -f .planning/phases/00-legal-brand-gate/external-snapshots/claude-code-cli-reference-SNAPSHOT.md && grep -l "third party developers" .planning/phases/00-legal-brand-gate/external-snapshots/claude-agent-sdk-overview-SNAPSHOT.md && grep -l "setup-token" .planning/phases/00-legal-brand-gate/external-snapshots/claude-code-cli-reference-SNAPSHOT.md</automated>
  </verify>
  <done>All 4 snapshot files exist with `snapshot_date` in frontmatter; agent-sdk snapshot contains the "third party developers" paragraph; cli-reference snapshot contains `setup-token`.</done>
</task>

<task type="auto">
  <name>Task 2: Draft + send Anthropic ToS clarification email</name>
  <files>
    .planning/phases/00-legal-brand-gate/correspondence/00-01-anthropic-tos-email-draft.md,
    .planning/phases/00-legal-brand-gate/correspondence/00-01-anthropic-tos-email-sent.md
  </files>
  <action>
    Compose the email draft as markdown (YAML frontmatter + body). Per D-09
    use a direct founder-to-partner tone, not lawyer-to-lawyer. The draft
    MUST include ALL of the following talking points in order:

    1. One-line intro: NYRA is a free Fab-distributed Unreal Engine plugin,
       solo-dev project, launching in 6–9 months.
    2. The integration pattern (be precise, so Anthropic's response is
       precise): "NYRA subprocess-drives the user's own installation of the
       Claude Code CLI using `claude -p --output-format stream-json --verbose
       --mcp-config <path>`. Authentication lives entirely in the user's own
       `~/.claude/.credentials.json` issued by their own invocation of
       `claude setup-token`. NYRA never sees the user's OAuth token; NYRA
       never stores Anthropic credentials; NYRA never offers a
       claude.ai-branded login UI; NYRA never embeds the Claude Agent SDK
       with NYRA-owned API keys."
    3. The clarification question (verbatim so there's no ambiguity in their
       reply): "We understand the agent-sdk documentation's note that
       'Anthropic does not allow third party developers to offer claude.ai
       login or rate limits for their products, including agents built on
       the Claude Agent SDK.' Our pattern is different in two concrete ways:
       (a) we do not offer claude.ai login — the user runs `claude
       setup-token` themselves, on their own machine, interactively; and
       (b) we do not embed the Agent SDK — we invoke the user's own
       installed `claude` CLI as a subprocess with the user's own
       credentials. Can you confirm this subprocess-driving pattern is
       permitted under the Anthropic Commercial and Consumer Terms for a
       free third-party product that interoperates with a user's personal
       Claude subscription?"
    4. Short-term asks: (a) a yes / no / conditional answer in email so we
       have a written record, (b) if conditional, the conditions so we can
       comply pre-launch, (c) if there is a partner-program or developer-
       relations contact better suited to this question, please redirect.
    5. Context hooks that help them answer quickly: link to
       https://code.claude.com/docs/en/cli-reference for the exact flags
       (quote the `-p --output-format stream-json` and `--mcp-config` rows
       inline from the snapshot), and a 3-line architecture summary (UE
       plugin -> Python MCP sidecar -> user's local `claude` CLI as a
       subprocess).
    6. Signature: founder name, NYRA project website placeholder
       (nyra.dev or backup from Plan 03), GitHub org placeholder.

    Recipient order to try (document in frontmatter): primary
    `support@anthropic.com`, fallback `partnerships@anthropic.com` if
    support redirects. Subject line: "ToS clarification: free third-party
    UE plugin subprocess-driving user's local `claude` CLI".

    Task hands off to the founder at this point. Founder action (record in
    `00-01-anthropic-tos-email-sent.md` after sending): paste the final
    subject, recipient, sent-timestamp (ISO-8601 UTC), message-id or Gmail
    thread-id, sender email (redacted in the committed file — replace local
    part with `<founder>@`), and the final body text EXACTLY as sent. If
    the draft was edited before sending, the sent-record supersedes the
    draft.

    Commit the draft + sent-record together with
    `docs(00-01): draft + send Anthropic ToS clarification email`.
  </action>
  <verify>
    <automated>test -f .planning/phases/00-legal-brand-gate/correspondence/00-01-anthropic-tos-email-draft.md && test -f .planning/phases/00-legal-brand-gate/correspondence/00-01-anthropic-tos-email-sent.md && grep -q "claude -p --output-format stream-json" .planning/phases/00-legal-brand-gate/correspondence/00-01-anthropic-tos-email-draft.md && grep -q "setup-token" .planning/phases/00-legal-brand-gate/correspondence/00-01-anthropic-tos-email-draft.md && grep -q "Date-sent:" .planning/phases/00-legal-brand-gate/correspondence/00-01-anthropic-tos-email-sent.md</automated>
  </verify>
  <done>Draft file exists with the 6 required talking points; sent-record exists with Date-sent, recipient, and redacted sender; founder confirms email left their outbox.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: File Anthropic's written response + founder verdict (gates Phase 2)</name>
  <files>
    .planning/phases/00-legal-brand-gate/correspondence/00-01-anthropic-tos-email-response.md
  </files>
  <what-built>
    Tasks 1+2 produced: 4 external-snapshot files capturing Anthropic's
    policy surface as of email-send date, an email draft, and a sent-record.
    Task 3 is the external-wait task: Anthropic's reply arrives
    asynchronously over 2–4 weeks. When it arrives, the founder files it
    here and writes a verdict.
  </what-built>
  <how-to-verify>
    Founder action when Anthropic replies:

    1. Open the reply email in your mail client. Note the received-timestamp
       (ISO-8601 UTC), the responding email address, and the thread URL.

    2. Create `.planning/phases/00-legal-brand-gate/correspondence/00-01-anthropic-tos-email-response.md`
       with YAML frontmatter:
       ```
       received_date: <ISO-8601>
       responder_address: <their email, redacted if personal>
       thread_id: <Gmail thread-id or Message-Id of your sent email>
       verdict: PERMITTED | CONDITIONAL | BLOCKED | UNCLEAR
       ```

    3. Below the frontmatter, under `## Anthropic's Verbatim Reply`, paste
       the FULL body of their reply as a quoted block. Do not paraphrase.

    4. Under `## Founder Interpretation`, write 3–6 sentences explaining
       how you read the reply and why you chose the verdict bit.

    5. Under `## Follow-ups` (optional), list any clarifying questions you
       sent back + their answers. If the first reply was ambiguous and a
       second round was needed, the full chain lives here.

    6. Under `## Sign-off`:
       ```
       Approved: <today ISO-8601>, <founder name>
       Interpretation: <PERMITTED | CONDITIONAL | BLOCKED>
       Phase 2 gate: <OPEN | OPEN-WITH-CONDITIONS | CLOSED>
       ```

    7. Commit with `docs(00-01): file Anthropic response + founder verdict`.

    Verdict semantics:
    - PERMITTED → Phase 2 gate OPEN. Proceed.
    - CONDITIONAL → Phase 2 gate OPEN-WITH-CONDITIONS. Record conditions as
      a new section `## Conditions to Comply With Pre-Launch`. Phase 2
      planning can start; any plan that touches the conditions MUST cite
      this file.
    - BLOCKED → Phase 2 gate CLOSED. Open a new planning conversation to
      rescope the subscription-driving approach (fallback: advanced-config
      "bring your own Anthropic API key" mode). Do NOT start Phase 2.
    - UNCLEAR → Send a clarifying follow-up email; re-run Task 3 when the
      clarified answer lands.

    If 4 weeks pass with no reply: send one polite follow-up in the same
    thread citing the original send-date. If another 2 weeks with no reply,
    open a planning conversation for an escalation path (e.g. going via
    partnerships or developer-relations explicitly).
  </how-to-verify>
  <resume-signal>Type "approved: permitted", "approved: conditional", "approved: blocked", or paste the response file path + verdict.</resume-signal>
</task>

</tasks>

<verification>
Phase 0 SC#1 closure verification:
- [ ] 4 external-snapshots exist with `snapshot_date` frontmatter
- [ ] Email draft contains all 6 required talking points
- [ ] Sent-record has Date-sent + thread-id + redacted sender
- [ ] Response file exists with Anthropic's verbatim reply + founder verdict
- [ ] Verdict is PERMITTED or CONDITIONAL (BLOCKED triggers a replan)
- [ ] Response file is committed to git
</verification>

<success_criteria>
Phase 0 SC#1 is CLOSED when:
1. `correspondence/00-01-anthropic-tos-email-response.md` exists with a
   PERMITTED or CONDITIONAL verdict + founder sign-off.
2. The response file's `thread_id` resolves to the sent-record's `message_id`.
3. The closure ledger (Plan 06) flips SC#1 from PENDING to CLOSED citing
   this response file.

If verdict is BLOCKED: Phase 0 is NOT closed on SC#1; Phase 2 cannot start.
A rescope-planning session is required before any subscription-driving code
ships. Fallback path (already documented in RESEARCH STACK as "Alternatives
Considered"): advanced-config bring-your-own-Anthropic-API-key mode, which
does not require subscription-driving clearance.
</success_criteria>

<output>
After completion, create `.planning/phases/00-legal-brand-gate/00-01-SUMMARY.md`
following the GSD summary template. Record: snapshot dates, email sent-date,
response received-date, verdict, and any follow-up threads.
</output>
