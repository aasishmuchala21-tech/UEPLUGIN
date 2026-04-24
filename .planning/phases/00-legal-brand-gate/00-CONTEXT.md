# Phase 0: Legal & Brand Gate — Context

**Gathered:** 2026-04-24
**Status:** Ready for planning
**Source:** Orchestrator-direct (PROJECT.md + ROADMAP.md Phase 0 §Success Criteria are already explicit; discuss-phase bypassed for a non-code compliance gate where the work product is email drafts + legal research + brand archive, not design decisions)

<domain>
## Phase Boundary

Phase 0 delivers **five written clearances** that gate the economic wedge (subprocess-driving the user's Claude subscription) and Fab distribution. It runs IN PARALLEL with Phase 1 — Phase 1 ships legal-safe plugin-shell scaffolding without touching subscription-driving code, while Phase 0 emails are in flight. Phase 2 (Subscription Bridge) MUST NOT begin execution until Phase 0 is closed.

**Requirements this phase satisfies:** PLUG-05.

**What ships from Phase 0:**
1. Email draft + sent record + written response filed — Anthropic ToS clarification on subprocess-driving the user's local `claude` CLI.
2. Email draft + sent record + written response filed — Epic / Fab AI-plugin policy pre-clearance, PLUS direct-download fallback plan documented.
3. Trademark screening dossier — USPTO + EUIPO + WIPO Class 9 + 42 + 41 searches for "NYRA" with clean verdict OR backup name selected. Domain + GitHub org + social handle reservations committed.
4. Gemma license re-verification note + NYRA ToS+EULA first draft covering generated-content liability (Meshy / ComfyUI passthrough) and reference-video copyright (ephemeral processing clause).
5. Brand-guideline research dossier for Anthropic + OpenAI + Epic/Fab, plus copy-approved neutral-language Fab listing fragments ("works with your Claude subscription", no third-party logos without written partner-program permission).

**Out of scope for Phase 0:**
- Any plugin code changes — Phase 1 owns plugin-shell scaffolding.
- Legal counsel retainer contracts — founder decision; Phase 0 only produces the research dossier lawyers need.
- Epic partner-program applications beyond Fab listing prep — deferred to Phase 8.
- OpenAI / Codex clearance — Codex integration deferred to v1.1 per PROJECT.md Key Decisions, so no Phase 0 clearance needed now.

</domain>

<decisions>
## Implementation Decisions

### D-01: Parallel-track with Phase 1 (locked upstream — PROJECT.md, STATE.md)
Phase 0 runs concurrently with Phase 1. Legal clearances are prerequisites for Phase 2 execution, not Phase 1 execution. Phase 1 may ship legal-safe scaffolding (plugin shell, IPC, panels) while Phase 0 emails are in flight.

### D-02: Phase 0 is an artifact-gate phase, not a code-gate phase
Success criteria are "written response on file" / "dossier archived" / "EULA draft complete", not unit-test coverage. Plans in this phase DO NOT follow the TDD RED→GREEN pattern used in Phase 1. Validation = "the named artifact exists in .planning/phases/00-legal-brand-gate/ and is signed off by the founder".

### D-03: Written-record discipline
Every clearance requires a **written** response — a phone call, Slack DM, or verbal "it's fine" does not close a Phase 0 success criterion. Email threads are exported to `.pdf` or raw `.eml` and committed under `.planning/phases/00-legal-brand-gate/correspondence/` (with any personal contact info redacted in the committed copy — raw threads stored outside the repo, committed version has tracking numbers + redacted sender).

### D-04: Trademark — screening only, not prosecution
Phase 0 ships a **clean-or-blocked verdict** from USPTO TESS + EUIPO eSearch + WIPO Global Brand Database searches across Class 9 (software plugins), Class 42 (SaaS), Class 41 (educational). If clean → reserve nyra.dev / github.com/nyra-ai (or similar — researcher picks) + X handle + Discord. If blocked → select backup name from 5 pre-screened candidates and re-screen. **Actual USPTO filing is deferred to v1.1**; Phase 0 only de-risks the name.

### D-05: Gemma license — re-verify, not re-negotiate
Gemma 3 4B IT QAT Q4_0 GGUF has a Gemma-license (not Apache/MIT) that allows commercial redistribution with terms-notice. Phase 0 re-reads the current text at ai.google.dev/gemma/terms (snapshotted to `gemma-license-YYYY-MM-DD.pdf`), confirms the "Use Restrictions" list hasn't changed, and drafts the NYRA-ToS "Gemma Notice" passthrough clause. **Not a legal negotiation.**

### D-06: EULA scope — liability passthrough + ephemeral-processing, nothing else
NYRA's v1 EULA covers exactly two novel areas beyond the standard UE-plugin EULA template:
- **Generated-content liability passthrough** — Meshy / ComfyUI / Substance output belongs to the user; NYRA warranties nothing about third-party output.
- **Reference-video ephemeral processing** — yt-dlp download + keyframe extract + Claude vision; full video deleted from `/tmp` after run by default, no redistribution, user affirms copyright-clean use.
Everything else (user rights, warranty disclaimer, venue, indemnification) uses a standard UE-plugin template adapted for a free Fab plugin. First draft is founder-authored; legal-counsel review is a **post-v1** activity.

### D-07: Direct-download fallback is a plan, not an implementation
Phase 0 ships the **plan** for direct-download distribution (signed Windows installer + update manifest + SmartScreen mitigation). **Implementing** the fallback lives in Phase 8 (Fab Launch Prep). Phase 0 only de-risks a Fab rejection by documenting the workaround.

### D-08: Brand-guideline compliance — archive first, ask permission second
Phase 0 archives current Anthropic / OpenAI / Epic / Fab trademark-use guidelines (full-text snapshots, date-stamped) so Fab listing copy can be audited against them. **No third-party logos on the Fab listing unless an explicit partner-program permission is on file.** Copy uses neutral phrasing approved by the founder before submission.

### D-09: Claude's Discretion — tone, template, counsel choice
- **Email tone:** Direct, founder-to-partner, not lawyer-to-lawyer. The planner picks template style.
- **Trademark-screening tool choice:** Researcher picks between DIY (USPTO TESS + EUIPO eSearch + WIPO Global Brand DB — free) vs. a paid service (Markify, TrademarkNow) — default DIY.
- **Counsel-review timing:** Founder decision in Phase 0; Phase 0 artifacts are ready for counsel whenever the founder engages one (v1 ship or later).

### D-10: Sequencing WITHIN Phase 0
Legal emails are time-bound by the recipient's response cadence, not by the founder's ability to author. Therefore:
- **Day 1:** Author and send Anthropic + Epic emails (parallel).
- **Day 1–3:** Trademark screening + Gemma license re-verify + brand-guideline archive (founder-driven, no external dependency).
- **Day 3–N (depends on reply cadence, expect 2–4 weeks):** Receive + file written responses.
- **EULA first draft:** Can be authored in Day 2–5, independent of email responses.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-level (mandatory)
- `.planning/PROJECT.md` — Constraints §"Legal", Key Decisions (Codex deferred, free Fab plugin), Out of Scope §"Codex / ChatGPT subscription driving (v1)"
- `.planning/REQUIREMENTS.md` — PLUG-05 row (trace one plan per criterion)
- `.planning/ROADMAP.md` §"Phase 0: Legal & Brand Gate" — five success criteria verbatim; §"Phase 2" depends_on declaration (Phase 0 gates Phase 2 execution)
- `.planning/STATE.md` §"Current Focus" — parallel-track with Phase 1
- `.planning/research/PITFALLS.md` §7.4 competitor-preempts-demo mitigation — Phase 0 is where the public devlog kickoff gets unblocked (trademark clean + brand-guideline-archived before first post)

### External anchor docs (archive date-stamped snapshots under `.planning/phases/00-legal-brand-gate/external-snapshots/`)
- `https://www.anthropic.com/legal/commercial-terms` — Anthropic Commercial Terms
- `https://www.anthropic.com/legal/consumer-terms` — Anthropic Consumer Terms (covers Pro/Max subscription)
- `https://code.claude.com/docs/en/agent-sdk/overview` — "Anthropic does not allow third party developers to offer claude.ai login" paragraph is the blocker the subprocess-driving email asks to clarify
- `https://code.claude.com/docs/en/cli-reference` — canonical reference for `claude setup-token` + `-p --output-format stream-json` flags NYRA subprocesses
- `https://www.fab.com/help` — current Fab content / AI-disclosure / code-plugin submission policies (URLs resolve from Fab help center)
- `https://ai.google.dev/gemma/terms` — current Gemma terms-of-use for the NYRA redistribution-notice clause
- `https://www.uspto.gov/trademarks/search` — USPTO TESS entry point
- `https://euipo.europa.eu/eSearch` — EUIPO eSearch entry point
- `https://branddb.wipo.int/` — WIPO Global Brand Database entry point

### Phase 1 cross-reference (non-blocking — Phase 0 does NOT depend on Phase 1)
- `.planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md` — Phase 1 deliverable layout shows where legal-adjacent code lands in Phase 2+ (NyraHost subscription driver), so Phase 0 email wording can cite the concrete subprocess architecture.

</canonical_refs>

<specifics>
## Specific Ideas

- **Anthropic email** — lead with "NYRA is a free UE plugin that subprocess-drives the user's own `claude` CLI on their own machine via `claude -p --output-format stream-json` + `--mcp-config`; the plugin never sees the user's OAuth token and never offers claude.ai login. Does this fit within the Anthropic Commercial Terms for third-party products that interoperate with a user's personal subscription?" — get a clear yes/no in writing.
- **Epic / Fab email** — lead with the AI-plugin disclosure NYRA will make (Meshy, ComfyUI, Substance, Claude) and the network-calls disclosure (localhost-only + user-initiated external API calls + no NYRA-owned backend). Ask: (a) is this disclosure pattern acceptable for a free plugin submission, (b) what is the expected review turnaround, (c) is there a pre-submission channel for policy clarifications.
- **Trademark screening** — NYRA is a short Greek-mythology-adjacent name; priors suggest low collision risk in software but medium risk in fashion / cosmetics / adjacent. Screen all three classes together; if Class 9 (software) is clean, the other two classes are nice-to-have not blockers.
- **Backup names to pre-screen (5 candidates, researcher picks one if NYRA blocks):** suggestions from the planner — short, Greek/myth-adjacent, domain-available, not trademarked in software.
- **Domain reservation**: primary `nyra.dev` (Google Domains / Cloudflare Registrar), fallback `nyra.ai`, tertiary `nyra-engine.com`. GitHub org `nyra-ai` or similar.
- **Devlog kickoff is gated on trademark + brand-guideline archive** — PITFALLS §7.4 says "public devlog from Month 1" mitigates competitor-preempts-demo risk; Phase 0 unblocks it.

</specifics>

<deferred>
## Deferred Ideas

- **Actual USPTO trademark filing** — Phase 0 does screening only; filing (prosecution cost ~$350+/class + counsel) deferred to v1.1 or post-launch when usage signal justifies.
- **Legal counsel retainer** — Phase 0 produces the dossier; engaging counsel is a founder decision not bundled into Phase 0 scope.
- **Codex / OpenAI ToS clearance** — Deferred to v1.1 per PROJECT.md.
- **Full Fab Pro partner-program application** — Deferred to Phase 8 or v1.1.
- **Third-party-logo usage rights on Fab listing** — Default is "no logos". If the founder decides to request logo rights post-Phase-0, a separate correspondence thread is opened; it is not part of Phase 0 closure.
- **Privacy-policy drafting** — NYRA v1 has minimal data collection (localhost-only, no backend), so privacy policy is bundled into the EULA draft as a short §"Data We Do Not Collect". A separate standalone privacy policy is deferred until usage signal / Phase 0 counsel review identifies a need.

</deferred>

---

*Phase: 00-legal-brand-gate*
*Context gathered: 2026-04-24 orchestrator-direct (non-code phase, discuss-phase bypassed)*
