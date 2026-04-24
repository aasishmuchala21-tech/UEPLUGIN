---
plan: 00-01-anthropic-tos-email
status: DRAFT — ready to send (founder review + send required)
draft_date: 2026-04-24
intended_recipient_primary: support@anthropic.com
intended_recipient_fallback: partnerships@anthropic.com
subject: "ToS clarification: free third-party UE plugin subprocess-driving user's local `claude` CLI"
tone: direct founder-to-partner (per CONTEXT.md D-09)
length_target: "~550 words — short enough to read end-to-end, long enough to be precise"
quotes_verbatim:
  - "Unless previously approved, Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products, including agents built on the Claude Agent SDK. Please use the API key authentication methods described in this document instead."
cites_snapshots:
  - external-snapshots/claude-agent-sdk-overview-SNAPSHOT.md
  - external-snapshots/claude-code-cli-reference-SNAPSHOT.md
  - external-snapshots/anthropic-commercial-terms-SNAPSHOT.md
  - external-snapshots/anthropic-consumer-terms-SNAPSHOT.md
talking_points_checklist:
  - "(1) One-line intro — free Fab UE plugin, solo-dev, 6–9 month timeline"
  - "(2) Integration pattern described precisely (subprocess of user's claude CLI, stream-json, mcp-config, OAuth in user's own credentials file)"
  - "(3) Clarification question quoting agent-sdk Note paragraph verbatim"
  - "(4) Short-term asks — yes/no/conditional, conditions if conditional, partner-program redirect if better channel"
  - "(5) Context hooks — link to cli-reference with exact flags, 3-line architecture summary"
  - "(6) Signature — founder name + project site placeholder + GitHub org placeholder"
---

# DRAFT — Anthropic ToS clarification email

> **Status:** This is the committed pre-send draft. The founder reviews,
> sends from their personal email, and then pastes the as-sent body and
> headers into `00-01-anthropic-tos-email-sent.md`. If the draft is edited
> before sending (minor wording tweaks allowed, structural changes SHOULD
> be re-committed to this file first), the sent-record supersedes the
> draft as the canonical record.

---

**To:** support@anthropic.com
**Cc:** [leave empty — if support redirects, re-send to partnerships@anthropic.com per D-10 follow-up cadence]
**From:** \<founder\>@\<personal-domain\>
**Subject:** ToS clarification: free third-party UE plugin subprocess-driving user's local `claude` CLI

---

Hi Anthropic team,

I'm a solo founder building **NYRA**, a **free** Unreal Engine 5 plugin I'll be distributing on Fab in the next 6–9 months. NYRA gives UE developers an in-editor AI agent powered by **the user's own Claude subscription** — not a NYRA-owned API key. Before I write a line of subscription-driving code I want a written read from you that the pattern below is permitted under the Commercial and Consumer Terms. I'd rather get a clear "yes / no / here are the conditions" now than ship, get traction, and then discover I misread the Agent SDK docs.

## How NYRA actually talks to Claude

NYRA **subprocess-drives the user's own, already-installed `claude` CLI** on the user's own machine. The exact invocation is:

```
claude -p "<prompt>" \
  --output-format stream-json \
  --verbose \
  --include-partial-messages \
  --mcp-config <nyra-per-session-config.json>
```

(Flags per your public docs at https://code.claude.com/docs/en/cli-reference.)

Authentication lives entirely in the user's own `~/.claude/.credentials.json`, issued by **the user's own interactive run of `claude setup-token`** — the `setup-token` subcommand your CLI ships, run by the user, on the user's machine, under their own Claude Pro / Max subscription.

Concretely:

- **NYRA never sees the user's OAuth token.** The `claude` process reads credentials itself; NYRA is just the parent process reading stdout.
- **NYRA never stores Anthropic credentials.** There is no NYRA-owned backend in v1 — the plugin is 100% localhost.
- **NYRA never offers a claude.ai-branded login UI.** Any authentication UI is `claude setup-token`'s own, i.e. yours.
- **NYRA never embeds the Claude Agent SDK with NYRA-owned API keys.** The plugin carries zero Anthropic SDK code.

The MCP config injected via `--mcp-config` points Claude Code at NYRA's own in-editor MCP server (exposing UE-specific tools: Blueprint reads/writes, asset imports, actor spawns, Sequencer edits). That's NYRA **extending** Claude Code with UE tools, not replacing its auth path.

## Why I'm asking

Your Agent SDK overview page (https://code.claude.com/docs/en/agent-sdk/overview) has a Note that reads, verbatim:

> **"Unless previously approved, Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products, including agents built on the Claude Agent SDK. Please use the API key authentication methods described in this document instead."**

I read NYRA's pattern as sitting **outside** that restriction, for two concrete reasons:

1. **We do not offer claude.ai login.** The user runs `claude setup-token` themselves, interactively, in their own terminal. The only login UI they see is the one you ship.
2. **We do not embed the Agent SDK.** We invoke **the user's own installed `claude` CLI** — your binary, on their machine, with their credentials.

My question: **Can you confirm this subprocess-driving pattern is permitted under the Anthropic Commercial and Consumer Terms for a free third-party product that interoperates with a user's personal Claude subscription?**

## What I'm asking for, specifically

1. A **yes / no / conditional** answer **in email**, so we have a written record I can show Fab reviewers and (worst case) a future legal counsel.
2. If the answer is **conditional**, the conditions — so I can comply pre-launch. (E.g. AUP passthrough in the plugin's EULA, explicit user consent dialog on first run, restrictions on commercial use, etc. I'd rather meet a spec than guess.)
3. If there is a **partner program or developer relations contact** better suited to this question, please redirect — happy to re-send to the right inbox.

## One-paragraph architecture summary, in case it helps the reviewer

NYRA = UE C++ plugin (editor panel) → Python MCP sidecar (`NyraHost`) → the user's own `claude` CLI as a subprocess. The plugin spawns `NyraHost` on startup; `NyraHost` spawns `claude -p --output-format stream-json` on each user prompt; Claude Code executes with the user's OAuth token (never touched by us). We also run a local Gemma 3 4B GGUF via llama.cpp as an offline / privacy-mode fallback — entirely orthogonal to the Claude path. Everything is localhost; no NYRA-owned cloud backend.

Happy to share the architecture doc (one page) or a short loom if useful. Thanks for the product — the `stream-json` + `setup-token` + `--mcp-config` combination is exactly what a plugin like this needs, and I'd love to ship it cleanly within your terms.

Warmly,

\<founder-name\>
NYRA — https://\<nyra.dev placeholder\>
GitHub: https://github.com/\<nyra-ai placeholder\>

---

## Internal notes (NOT sent — for the founder only)

- **Do NOT attach the raw snapshot files.** Anthropic can re-read their own docs; pasting the Note verbatim is enough.
- **Signature placeholders:** replace `<founder-name>`, `<nyra.dev placeholder>`, `<nyra-ai placeholder>` before send. If the trademark-screening plan (00-03) hasn't resolved the name at send-time, a "project landing page — coming soon" is acceptable as long as the domain is reserved.
- **Send from a personal address** (not a generic alias). D-03 written-record discipline wants a real human on both sides.
- **When the reply lands**, Task 3 (`00-01-anthropic-tos-email-response.md`) gets filled out. Until then, **Phase 2 execution is gated** per ROADMAP.md and PROJECT.md Key Decisions.
- **If the reply asks for the Agent SDK's "approved" flow** (the Note says "Unless previously approved"), consider replying with a request to be added to that approved list, citing the subprocess-driving architecture as evidence the pattern is materially different from embedding.
- **Keep the thread** — if a follow-up clarification is needed, reply in the same thread so Thread-Id lineage in the sent-record stays coherent.

---

*Plan: 00-01-anthropic-tos-email*
*Draft committed: 2026-04-24*
