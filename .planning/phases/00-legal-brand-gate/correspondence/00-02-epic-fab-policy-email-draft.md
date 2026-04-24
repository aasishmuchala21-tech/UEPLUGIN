---
plan: 00-02-epic-fab-policy-email
status: DRAFT — ready to send (founder review + send required)
draft_date: 2026-04-24
intended_recipient_primary: "Fab seller-support — address surfaced from fab.com/help Content Guidelines footer when the founder opens the help-center in a logged-in browser (typically fab-support@epicgames.com or sellers@fab.com; confirm at send-time)"
intended_recipient_fallback: "devrel@epicgames.com  (or any Epic dev-rel contact the founder has; the sent-record captures the final address)"
subject: "Free UE plugin pre-clearance — AI-content disclosure + network-call pattern"
tone: direct founder-to-partner (per CONTEXT.md D-09)
length_target: "~700 words — enumerates 5 AI deps + 3 network-call facts + 3 numbered questions without drifting"
cites_snapshots:
  - external-snapshots/fab-content-guidelines-SNAPSHOT.md
  - external-snapshots/fab-ai-disclosure-policy-SNAPSHOT.md
  - external-snapshots/fab-code-plugin-checklist-SNAPSHOT.md
enumerates:
  - "AI-plugin disclosure: Claude CLI subprocess + Meshy REST + ComfyUI HTTP + Anthropic computer-use (Substance + UE modals) + optional local Gemma 3 4B"
  - "Network-call surface: localhost-only inter-process + user-initiated external API + zero NYRA-owned backend"
  - "3 numbered questions: Q1 disclosure acceptability, Q2 review turnaround, Q3 pre-submission channel"
attachments_at_send:
  - "PDF export of fab-content-guidelines-SNAPSHOT.md (so reviewer sees the version we're asking against)"
  - "PDF export of fab-ai-disclosure-policy-SNAPSHOT.md"
  - "PDF export of fab-code-plugin-checklist-SNAPSHOT.md"
talking_points_checklist:
  - "(1) One-line intro — free UE plugin, solo-dev, 5.4–5.7, Fab submission in 6–9 months"
  - "(2) AI-plugin disclosure — enumerate all 4 external AI deps + Gemma"
  - "(3) Network-call surface — localhost + user-initiated + no NYRA backend"
  - "(4) 3 numbered questions — disclosure / turnaround / pre-submission channel"
  - "(5) Attachments note — PDFs of the 3 snapshotted Fab-policy pages"
  - "(6) Architecture one-paragraph summary + signature"
---

# DRAFT — Epic / Fab pre-clearance email

> **Status:** This is the committed pre-send draft. The founder reviews,
> sends from their personal email, and then pastes the as-sent body and
> headers into `00-02-epic-fab-policy-email-sent.md`. Minor wording
> tweaks allowed at send-time; structural changes SHOULD be re-committed
> to this file first so the snapshot → email → sent-record chain stays
> legible. Mirrors Plan 00-01's draft discipline.

---

**To:** \<fab-seller-support-address, resolved at send-time from fab.com/help Content Guidelines footer\>
**Cc:** \<optional — if the founder has a prior Epic dev-rel contact, Cc them for visibility\>
**From:** \<founder\>@\<personal-domain\>
**Subject:** Free UE plugin pre-clearance — AI-content disclosure + network-call pattern
**Attachments:** 3 PDFs — Fab Content Guidelines (2026-04-24 snapshot), Fab AI-Disclosure Policy (2026-04-24 snapshot), Fab Code Plugin Submission Checklist (2026-04-24 snapshot)

---

Hi Fab team,

I'm a solo founder building **NYRA**, a **free** Unreal Engine 5 plugin
targeting Fab submission in the next 6–9 months. Supported engines: **UE
5.4, 5.5, 5.6, and 5.7** (per-engine binaries via the standard
multi-version `.uplugin` pattern). Before I sink months of Phase 2–8
effort into a plugin that fails a checklist item at review, I want to
run the AI-content disclosure and network-call pattern past you in
writing. I'd rather meet your spec than guess at it — happy to
pre-comply with any conditions you can tell me about today.

I've attached PDFs of the three Fab-policy pages I'm reading against
(Content Guidelines, AI-Disclosure Policy, Code Plugin Submission
Checklist — all snapshotted 2026-04-24) so your answer anchors to a
known version of each document.

## What NYRA does

NYRA gives UE developers an in-editor AI agent powered by **the user's
own Claude subscription** (no new AI bill). Reference image / video /
prompt → finished UE scene (imported meshes, authored materials,
configured lighting, Sequencer edits). Primary reasoning runs through
the user's own `claude` CLI; external tools are driven API-first with
computer-use reserved for apps without APIs.

## AI-plugin disclosure surface (5 dependencies, fully enumerated)

Per Fab's AI-Disclosure Policy §4 + §5 + §6, here is every external AI
dependency NYRA touches at runtime:

1. **Anthropic via the user's local `claude` CLI.** NYRA invokes the
   user's locally-installed Claude Code CLI as a subprocess —
   `claude -p --output-format stream-json --mcp-config <path>` — using
   the user's own subscription credentials (issued by the user's own
   `claude setup-token` interactive flow). **NYRA never sees the OAuth
   token and never embeds the Claude Agent SDK.** This pattern is
   separately being pre-cleared with Anthropic in a parallel thread
   (NYRA's Phase 0 SC#1); I can forward that reply when it lands.

2. **Meshy via REST API.** NYRA drives Meshy (image → 3D-model
   generation) via their REST API. **The user provides their own Meshy
   account + API key**; NYRA stores it in UE editor preferences on the
   user's machine only.

3. **ComfyUI via localhost HTTP API.** NYRA drives a **user-installed
   ComfyUI** via its localhost HTTP API for image-to-image workflows
   (texture variations, reference conditioning). If the user runs
   ComfyUI on a remote host, the user configures the URL; disclosed in
   the plugin UI when they do.

4. **Anthropic computer-use (`computer_20251124`, Opus 4.7).** For
   Substance 3D Sampler (no public API exists) and UE editor modal
   dialogs (operations the Unreal API does not expose). **Scoped to
   those applications only** per NYRA's documented computer-use policy
   — no general desktop automation. Uses Claude Desktop's computer-use
   path on Windows per Anthropic's current docs.

5. **Local Gemma 3 4B (GGUF, QAT Q4_0) via llama.cpp / Ollama.**
   Optional offline / rate-limited / privacy-mode fallback. Weights are
   a **first-run user-consented download** (not bundled) to
   `%LOCALAPPDATA%/NYRA/models/`. Gemma's license permits commercial
   redistribution with notice; re-verified pre-launch in Plan 00-04 of
   my Phase 0 work.

## Network-call surface (3 facts, all disclosed)

Per Fab's Code Plugin Submission Checklist §6 + Content Guidelines
"Network and External Service Integration":

1. **All inter-process NYRA traffic is localhost-only.** UE↔NyraHost
   (Python MCP sidecar) is a loopback WebSocket; NyraHost↔NyraInfer
   (llama.cpp) is localhost HTTP. Ephemeral ports bound to `127.0.0.1`
   — no Windows Firewall prompt, no inbound exposure.

2. **All external API traffic is user-initiated and visible in the
   plugin UI.** The user sees the outbound call in the chat panel
   before it happens; no hidden background traffic. Providers in scope:
   Meshy, ComfyUI (if remote), Anthropic (via the user's `claude` CLI
   subprocess).

3. **NYRA does NOT operate or call any NYRA-owned backend.** No
   telemetry. No hosted auth. No hosted RAG. No hosted billing. The
   plugin is 100% localhost + user-initiated external. Nothing to phone
   home to, by design.

## Three questions

I'd love a written answer to these three, in email, so I have a record I
can show a future legal counsel and file in the Fab submission package:

**Q1.** Is NYRA's AI-plugin disclosure pattern — as enumerated above —
acceptable for a free plugin submission under Fab's current AI-content
policy? If not, which specific element would need to change?

**Q2.** What is the current expected review turnaround for a free Code
Plugin with AI-content disclosure? I'd like to align our launch window
around a realistic target (and if the turnaround varies by complexity,
the factors that drive the variance).

**Q3.** Is there a pre-submission channel for policy clarifications
beyond this email thread — e.g. a dev-rel contact or a partner-program
rep for plugins that drive external tools? If so, I'd rather route
future disclosure questions (e.g., when NYRA v1.1 adds Codex) through
that channel.

## One-paragraph architecture summary, in case it helps

NYRA = UE C++ plugin shell (two modules: `NyraEditor` + `NyraRuntime`,
Fab Code Plugin checklist §4 compliant) → Python MCP sidecar
(`NyraHost`) spawned as a subprocess at plugin startup → orchestrates
the user's own `claude` CLI subprocess for reasoning + Meshy / ComfyUI
REST/HTTP for asset generation + Anthropic computer-use for
API-less apps + optional llama.cpp / Ollama (`NyraInfer`) for local
Gemma. Distribution: per-engine binaries for 5.4 / 5.5 / 5.6 / 5.7;
EV-signed; zero NYRA-owned backend.

Thanks for building Fab — the unified marketplace is exactly the
distribution surface a plugin like NYRA needs, and I'd love to ship it
cleanly within your AI-content policy.

Warmly,

\<founder-name\>
NYRA — https://\<nyra.dev placeholder; reserved in Plan 00-03\>
GitHub: https://github.com/\<nyra-ai placeholder; reserved in Plan 00-03\>

---

## Internal notes (NOT sent — for the founder only)

- **Resolve the To: address at send-time.** `fab.com/help` left-nav
  Content Guidelines footer lists the current seller-support email
  address; if not obvious, sellers@fab.com or fab-support@epicgames.com
  are reasonable first tries. Fallback: devrel@epicgames.com, or any
  existing Epic dev-rel contact the founder has. Thread-id tracking
  matters — keep the same thread even if support forwards.
- **Signature placeholders:** replace `<founder-name>`, `<nyra.dev
  placeholder>`, `<nyra-ai placeholder>` before send. If Plan 00-03
  (trademark screening) has not yet resolved the name at send-time,
  use the current working name + "(site coming soon)" and note the
  live name in the sent-record `pending_items` section.
- **Attachments.** Export each of the three Fab-policy snapshots to PDF
  (simplest: open each SNAPSHOT.md in a markdown viewer, print-to-PDF).
  Filenames: `fab-content-guidelines-snapshot-2026-04-24.pdf`, etc.
  Rationale: reviewer sees the version we're asking against so drift
  in fab.com/help a month from now doesn't invalidate their answer.
- **Send from a personal address** (not a generic alias). D-03
  written-record discipline wants a real human on both sides.
- **Parallel thread caveat.** Mention once — the Anthropic ToS thread
  (Plan 00-01) is in flight; the Fab reviewer does not need that
  thread's content, only the fact that NYRA is already pre-clearing on
  the Anthropic side too. Offer to forward if useful.
- **Keep the thread.** Any follow-up clarification goes in the same
  thread so Thread-Id lineage in the sent-record stays coherent.
- **If the reply is BLOCKED.** That does NOT fail Phase 0 SC#2 because
  the direct-download fallback plan
  (`legal/00-02-direct-download-fallback-plan.md`) is shelf-ready — see
  Plan 00-02 Task 2 deliverable and CONTEXT.md D-07.

---

*Plan: 00-02-epic-fab-policy-email*
*Draft committed: 2026-04-24*
