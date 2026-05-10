# Roadmap: NYRA

**Defined:** 2026-04-21
**Last Updated:** 2026-05-10 (Phase 8 reframed: was "Fab Launch Prep", now "Competitive Parity vs Aura". Fab Launch Prep displaced to Phase 9. Rationale: Aura's public beta is shipping a much wider feature surface; launching NYRA against it without parity in document attachments / C++ authoring / BT agents / drag-drop UX risks immediate dismissal as "narrower than Aura". Per CLAUDE.md Quality Bar — parity is failure — but this is feature-surface parity to keep the wedge legible; the wedge itself ("free + your subscription + offline + computer-use + video-to-scene") survives.)
**Core Value:** Turn a reference (image, video, prompt) into a finished Unreal Engine scene — without the user paying a new AI bill or leaving the editor.
**Quality Bar:** Every phase's success criteria are framed as "beats competitor X on dimension Y" (not parity) or are an architectural gate that unblocks a future competitor-beating feature. Parity is failure.
**Granularity:** standard (config), 10 phases justified — Phase 0 is a deliberately short non-code legal gate that runs in parallel with Phase 1, so effective code phases = 9, within the standard band.
**Timeline target:** Solo full-time builder, 6-9 months to Fab v1 launch (extends to ~9-12 months with Phase 8 Competitive Parity insertion).

---

## Phases

- [ ] **Phase 0: Legal & Brand Gate** - Clear Anthropic/Epic/Fab ToS and trademark before any subscription-driving code ships (runs in parallel with Phase 1 plugin-shell work). Plan 00-01 (anthropic-tos-email) shipped 2026-04-24 at docs-layer [‡]; Plan 00-02 (epic-fab-policy-email) shipped 2026-04-24 at docs-layer [§] — 3 Fab-policy snapshots + email draft enumerating 5 AI deps + 3 network-call facts + 3 numbered questions + PLACEHOLDER sent/response records with 5-value verdict enum (adds BLOCKED-BY-SILENCE) + 510-line direct-download fallback SPEC with binding Phase 8 DIST-02 handoff contract. Plan 00-03 (trademark-screening) shipped 2026-04-24 at docs-layer [¶] — 3 registry raw dumps (USPTO TESS + EUIPO eSearch + WIPO Global Brand DB, all `snapshot_method: manual-lookup-required`) + consolidated dossier (`aggregate_verdict: MEDIUM-RISK`; Class 9 software presumptive CLEAN) + precautionary 5-candidate backup-screening (AELRA selected as warm-standby) + verdict-and-reservations doc (`final_name: NYRA` + `filing_status: DEFERRED-TO-V1.1` + `devlog_gate: OPEN` + embedded reservation-manifest YAML; nyra.dev + nyra.ai both Atom.com premium-broker-held, nyra-engine.com unambiguously AVAILABLE per WHOIS, github.com/nyra-plugin AVAILABLE). Founder sends both emails + files responses to close SC#1 (Anthropic) + SC#2 (Fab); founder registers nyra-engine.com + claims github.com/nyra-plugin + claims X/Reddit/YouTube/Discord handles + verbatim-upgrades registry raw dumps to close SC#3 (trademark). Per CONTEXT.md D-07, BLOCKED verdict from Fab does NOT fail SC#2 because the fallback SPEC ships today; SC#2 closes on PERMITTED ∨ CONDITIONAL ∨ (BLOCKED ∧ fallback-plan-exists). SC#3 already closed at docs-layer because aggregate verdict is MEDIUM-RISK not BLOCKED, with AELRA warm-standby + 2-4 week cutover Rollback Plan if any post-launch C&D event arrives. Phase 2 execution remains GATED on SC#1 (Anthropic verdict only); SC#2 drives Phase 8 primary-distribution-path choice; SC#3 unblocks PITFALLS §7.4 public devlog kickoff (still gated on Plan 00-05 brand-guideline archive + founder-manual reservation completion).
- [ ] **Phase 1: Plugin Shell + Three-Process IPC** — 16/16 plans COMPLETE at source+docs layer; architectural SC#3 empirical bench measurement PENDING Windows operator run of `ring0-run-instructions.md` [†] — UE C++ plugin + NyraHost Python sidecar + NyraInfer llama.cpp + Slate chat panel skeleton; Ring 0 "it can talk" (Wave 1 DONE: 01-03, 01-01, 01-02, 01-04, 01-05 shipped 2026-04-21; Wave 2 Python-side DONE: 01-06 + 01-07 + 01-08 + 01-09 shipped 2026-04-22 [Plan 02's Wave 0 stub pipeline FULLY LIQUIDATED — 34 passed / 0 skipped]; Wave 2 UE-side DONE: 01-10 cpp-supervisor-ws-jsonrpc shipped 2026-04-22; Wave 3 DONE: 01-11 markdown parser + 01-12 chat panel streaming + 01-12b history drawer shipped 2026-04-23; Wave 4 DONE: 01-13 first-run UX banners + diagnostics + 01-14 ring0 bench harness shipped 2026-04-23 [FNyraDevTools + Nyra.Dev.RoundTripBench console command with NON-COMPLIANT compliance gate when N<100]; Wave 5 DONE at docs layer: 01-15 ring0 run + commit results shipped 2026-04-23 as partial-completion [runbook + structured placeholder]; Phase 2 planning may proceed in parallel with the empirical bench run)

[†] Footnote on Phase 1 SC#3 empirical bench deferral: Plan 15 is authored as a partial-completion on the macOS dev host. The `Nyra.Dev.RoundTripBench 100` live measurement requires Windows 11 + UE 5.6 + Gemma 3 4B GGUF (or Ollama gemma3:4b-it-qat) — none available on macOS. Plan 15 ships `.planning/phases/01-plugin-shell-three-process-ipc/ring0-run-instructions.md` (operator runbook) + `.planning/phases/01-plugin-shell-three-process-ipc/ring0-bench-results.md` (structured PLACEHOLDER with PENDING cells + prominent ⚠ banner + `status: placeholder` + `pending_manual_verification: true` frontmatter). The Windows operator completes the architectural gate by following the runbook, replacing PENDING cells with real measured values, flipping frontmatter flags, and committing with `feat(01-15): record ring0 bench results from Windows dev machine`. Phase 2 EXECUTION waits on that empirical closure + Phase 0 legal clearance; Phase 2 PLANNING can start immediately.

[‡] Footnote on Phase 0 Plan 01 (anthropic-tos-email) partial-completion: plan is `autonomous: false` because full closure requires Anthropic's written reply to the founder-sent email (an external async event). Plan ships 4 date-stamped external-snapshots (commercial-terms + consumer-terms + claude-agent-sdk-overview capturing the `third party developers to offer claude.ai login` Note paragraph VERBATIM + claude-code-cli-reference capturing verbatim `setup-token` / `--output-format stream-json` / `--mcp-config` flag rows), an authored email draft at `.planning/phases/00-legal-brand-gate/correspondence/00-01-anthropic-tos-email-draft.md`, and schema-locked PLACEHOLDER sent/response records at `-sent.md` + `-response.md` with `pending_manual_verification: true` + prominent ASCII-banner warnings. Founder actions to close SC#1: (1) send email to `support@anthropic.com` from a personal address per D-03 written-record discipline; (2) fill PENDING cells in `-sent.md` in-place; (3) when reply arrives, fill `-response.md` frontmatter verdict (PERMITTED | CONDITIONAL | BLOCKED | UNCLEAR) + paste verbatim reply + Founder Interpretation + (if CONDITIONAL) Conditions-to-Comply-With-Pre-Launch table + Sign-off triplet; (4) commit — Plan 00-06 closure ledger flips SC#1 iff verdict ∈ {PERMITTED, CONDITIONAL}. Phase 2 EXECUTION remains BLOCKED until that flip; Phase 2 PLANNING and Phase 0 Plans 00-02 through 00-06 can run in parallel.

[§] Footnote on Phase 0 Plan 02 (epic-fab-policy-email) partial-completion: plan is `autonomous: false` because full closure requires Epic/Fab's written reply to the founder-sent email. Plan ships 3 date-stamped Fab-policy snapshots (fab-content-guidelines + fab-ai-disclosure-policy + fab-code-plugin-checklist, all `snapshot_method: curl-blocked-by-cloudflare` with structural-headings + paraphrased-summaries flagged `[paraphrased from live page 2026-04-24]` — founder upgrades to `authenticated-seller-dashboard-copy` as Task 3 side effect), a fully authored email draft at `.planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-draft.md` enumerating 5 AI deps (Claude CLI subprocess + Meshy REST + ComfyUI HTTP + `computer_20251124` Substance/UE modals + optional local Gemma 3 4B GGUF) + 3 network-call facts (localhost-only IPC + user-initiated external APIs + zero NYRA-owned backend) + 3 numbered questions (Q1 disclosure acceptability / Q2 review turnaround / Q3 pre-submission channel), schema-locked PLACEHOLDER `-sent.md` + `-response.md` with 5-value verdict enum (adds BLOCKED-BY-SILENCE for the Day-63 silent-reviewer path) + Day 0/21/42/63 cadence tuned for Fab reviewer timelines + explicit `phase_2_gate: OPEN (per Plan 00-01)` + `phase_8_primary_distribution: Fab | direct-download fallback` separation, AND a 510-line direct-download fallback SPEC at `.planning/phases/00-legal-brand-gate/legal/00-02-direct-download-fallback-plan.md` (`status: plan-only`, `implements_at: Phase 8 DIST-02`, binding 6-point handoff contract) covering 8 mandatory sections: 3 triggers w/ observable inputs + precedence / Inno Setup toolchain + 5-candidate rejection table / 13-field JSON update-manifest schema v1 + polling cadence + signature verification / EV cert primary SmartScreen strategy + OV-with-Authenticode-prewarm contingency / two-host distribution (nyra.dev Cloudflare Pages primary + GitHub Releases mirror) / zero-config onboarding parity with Fab path / Phase 8 handoff contract / 6 deferred questions with defaults. **Load-bearing insight per CONTEXT.md D-07: BLOCKED verdict from Fab does NOT fail SC#2 because the fallback SPEC ships today, promoting fallback from insurance to primary distribution rather than forcing rescope.** SC#2 closure rule is multi-branch: closes on `verdict: PERMITTED` ∨ `verdict: CONDITIONAL` ∨ (`verdict: BLOCKED` ∧ existence of `legal/00-02-direct-download-fallback-plan.md`). Plan 00-06 closure ledger grep-checks for this disjunction, not a single-value match. Phase 2 execution is NOT gated on this plan's verdict — Phase 2 gate is governed by Plan 00-01's Anthropic verdict per PLAN.md `<how-to-verify>` step 6; this plan's verdict drives Phase 8 primary-distribution-path choice only.

[¶] Footnote on Phase 0 Plan 03 (trademark-screening) docs-layer closure: plan is `autonomous: true` because trademark screening + reservation-manifest authoring + rollback planning can complete in-session without an external-reply wait (unlike correspondence Plans 00-01/02). Plan ships 3 date-stamped registry raw dumps for the NYRA mark across Nice Classes 009 + 042 + 041 (`trademark/00-03-uspto-tess-raw.md` 12 queries / `trademark/00-03-euipo-esearch-raw.md` 10 queries / `trademark/00-03-wipo-brand-db-raw.md` 9 queries — all `snapshot_method: manual-lookup-required` because every registry surface is JS-SPA + anti-bot-gated: USPTO TESS behind AWS WAF challenge / EUIPO eSearch + WIPO Global Brand DB behind AltCha captcha. Same paraphrased-with-date-flag discipline Plan 00-02 established for Cloudflare-gated Fab pages — new `manual-lookup-required` snapshot_method value joins the enumeration). Consolidated screening dossier at `trademark/00-03-nyra-screening-dossier.md` with `aggregate_verdict: MEDIUM-RISK` (Class 9 software presumptive CLEAN — the BLOCKER class is clean; MEDIUM-RISK driver is Class 41 U.S. New York Racing Association acronym-identical enforcer + cross-class fashion/cosmetics density across Classes 3/14/25 globally) + top-10 nearest-neighbor mark ranking (Racing Association rank 1 goods-distinct horse racing; Nura audio-hardware Class 9 rank 2 goods-distinct-within-class) + explicit CLEAN/MEDIUM-RISK/BLOCKED rubric application + `filing_decision: DEFERRED-TO-V1.1` per CONTEXT.md D-04 + cost transparency ($350/class USPTO + $1,000–2,500 counsel per jurisdiction). Precautionary 5-candidate backup-names screening at `trademark/00-03-backup-names-screening.md` (`status: PRECAUTIONARY` because NYRA retained primary, not BLOCKED) running AELRA / CAELUM / PYRRA / LIVIA / VYRELL through the same USPTO + EUIPO + WIPO screens with domain + GitHub + social availability filter; AELRA selected as warm-standby on 4-dim ranking (TM clean + domain available + phonetic-distance from NYRA + aesthetic fit). Final verdict-and-reservations doc at `trademark/00-03-verdict-and-reservations.md` with `final_name: NYRA` + `final_name_source: primary` + `filing_status: DEFERRED-TO-V1.1` + `devlog_gate: OPEN` (PITFALLS §7.4 competitor-preempts-demo mitigation unblocked from trademark-side) + embedded machine-readable reservation-manifest YAML (domains / github_orgs / social_handles / code_signing / filing / devlog / rollback sections) with **live-probed verdicts at 2026-04-24**: `nyra.dev` + `nyra.ai` BOTH held by Atom.com Domains LLC premium broker (WHOIS confirmed creation 2020-04-05, paired premium listing, Registry Expiry 2028-04-05); `nyra-engine.com` unambiguously AVAILABLE per `whois.verisign-grs.com` "No match for domain" (recommended primary registration at Cloudflare Registrar $9.77/yr); `github.com/nyra-ai` + `github.com/nyra` TAKEN (HTTP 200); `github.com/nyra-plugin` + `github.com/nyraengine` AVAILABLE (HTTP 404, `nyra-plugin` recommended primary + `nyraengine` defensive); X / Reddit / YouTube / Discord / Bluesky all MANUAL-LOOKUP-REQUIRED with per-platform fallback-ordered founder-action checklists (X.com SPA returns 200 universally, Reddit blocks anonymous curl 403, Discord vanity gated on Boost Level 3, YouTube @handle gated on channel creation, Bluesky depends on `nyra-engine.com` DNS completion). 2–4 week cutover Rollback Plan to AELRA documented with 3 activation triggers (verbatim-upgrade-to-BLOCKED / post-launch C&D / fashion-house defensive Class-9 extension). **Founder actions to close SC#3 fully: (1) register `nyra-engine.com` at Cloudflare Registrar (REQUIRED — unambiguously available); (2) optionally pursue Atom.com quote for `nyra.dev` + `nyra.ai` premium acquisition (founder-discretion); (3) create `github.com/nyra-plugin` org + defensive `github.com/nyraengine`; (4) claim X.com `@nyra_ai` (or fallback) + Reddit `r/NyraEngine` + YouTube `@nyraengine` + Discord "NYRA Engine" server + Bluesky `@nyra-engine.com` via `_atproto` DNS TXT; (5) complete verbatim USPTO/EUIPO/WIPO searches per per-raw-dump founder checklists + commit raw captures to `trademark/raw-captures/`; (6) flip each raw-dump frontmatter `snapshot_method: manual-lookup-required` → `founder-authenticated-YYYY-MM-DD`; (7) if any verbatim Class-9 NYRA live mark surfaces, trigger AELRA rollback per verdict-and-reservations doc §Rollback Plan.** Phase 2 execution is NOT gated on this plan; Phase 2 gate remains governed by Plan 00-01's Anthropic verdict. SC#3 closure unblocks PITFALLS §7.4 public devlog kickoff (still gated on Plan 00-05 brand-guideline archive + founder-manual reservation completion before the first public devlog post can ship).

- [ ] **Phase 2: Subscription Bridge + Four-Version CI Matrix** - Claude CLI subprocess driving with Gemma fallback, transactional safety, safe-mode, console/log tools, EV code-signing, and UE 5.4/5.5/5.6/5.7 CI from day one
- [ ] **Phase 3: UE5 Knowledge RAG** - Bundled LanceDB index with version-tagged citations, symbol validation, Epic-release auto-updater, and Gemma multimodal offline fallback
- [ ] **Phase 4: Blueprint + Asset + Material + Actor Tool Catalog** - Deep UE-native Tool Catalog targeting Aura's Blueprint error-reduction benchmark; every tool transactional, every action post-condition-verified
- [ ] **Phase 5: External Tool Integrations (API-First)** - Meshy REST, ComfyUI HTTP, computer-use reserved for Substance Sampler + UE modal dialogs, with the computer-use reliability spike gating scope
- [ ] **Phase 6: Scene Assembly + Image-to-Scene (Fallback Launch Demo)** - Lighting authoring from NL/reference images, end-to-end DEMO-01 that beats Nwiro's fixed-library approach
- [ ] **Phase 7: Sequencer + Video-to-Matched-Shot (LAUNCH DEMO)** - Video reference analyzer + Sequencer automation delivering DEMO-02, the capability no competitor ships
- [ ] **Phase 8: Competitive Parity vs Aura** - Document attachments (PDF/DOCX/PPTX/MD) + C++ authoring with Live Coding loop + Behavior Tree agent + drag-from-Content-Browser UX + Niagara VFX agent + Performance Profiling agent + AnimBP authoring + Metasounds agent. Closes the Aura feature-surface gap so the "no new AI bill + offline + computer-use + video" wedge is read as additive, not as substitute for missing tools.
- [ ] **Phase 9: Fab Launch Prep** - EV-signed installer, direct-download fallback, zero-config onboarding, Fab listing and AI-disclosure compliance (was Phase 8 prior to 2026-05-10 reframe)

---

## Phase Details

### Phase 0: Legal & Brand Gate
**Goal**: Every legal and brand constraint that gates NYRA's economic wedge (subscription-driving) and Fab distribution is resolved in writing before subscription-driving code ships.
**Depends on**: Nothing (runs in parallel with Phase 1's legal-safe plugin-shell work per founder decision)
**Requirements**: PLUG-05
**Success Criteria** (what must be TRUE):
  1. Beats every competitor on defensible-wedge legitimacy: written clarification from Anthropic on record that driving the user's local `claude` CLI via subprocess is ToS-permitted — no competitor has this written answer because no competitor attempts subscription driving
  2. Beats every competitor on Fab-readiness risk: written Fab AI-plugin policy pre-clearance from Epic on record before Phase 2 subscription code ships, plus a direct-download fallback plan documented (Fab rejection stops being product-fatal)
  3. Architectural gate: NYRA trademark screening (USPTO/EUIPO/WIPO Class 9 + 42 + 41) is clean or a backup name is selected; domain + GitHub org + social handle reserved before any public devlog post
  4. Architectural gate: Gemma 3 4B license re-verified for commercial Fab redistribution, NYRA ToS+EULA draft covers generated-content liability (Meshy/ComfyUI passthrough) and reference-video copyright (ephemeral processing clause)
  5. Architectural gate: Brand guideline research for Anthropic, OpenAI, Epic/Fab archived — Fab listing uses neutral "works with your Claude subscription" language, no third-party logos without explicit partner-program permission
**Plans**: TBD

### Phase 1: Plugin Shell + Three-Process IPC
**Goal**: The three-process architecture is proven end-to-end on UE 5.6 — UE editor hosts a Slate chat panel that round-trips to NyraHost over loopback WebSocket, NyraHost spawns NyraInfer (llama.cpp/Gemma) on demand, and nothing Phase 1 builds depends on Phase 0 legal clearance (plugin shell is legal-safe scaffolding).
**Depends on**: Nothing (runs in parallel with Phase 0)
**Requirements**: PLUG-01, PLUG-02, PLUG-03, CHAT-01
**Success Criteria** (what must be TRUE):
  1. Beats every OSS MCP plugin (chongdashu, flopperam, kvick-games, remiphilippe) on editor stability: NyraHost runs out-of-process; a NyraHost crash or Gemma OOM never takes UnrealEditor.exe down. OSS plugins that ran MCP in-process report exactly this instability — NYRA does not.
  2. Beats every competitor on chat-panel foundation depth: dockable Slate panel supports streaming tokens, markdown, code blocks, image/video/file attachments, per-conversation history persisted under project `Saved/NYRA/` — Aura's polished panel is the bar, NYRA meets it and adds multi-modal attachments from day one
  3. Architectural gate: loopback WebSocket (UE↔NyraHost) + localhost HTTP (NyraHost↔NyraInfer OpenAI-compatible) IPC is stable over 100 consecutive round-trips on UE 5.6 with editor responsive during streaming; this gate unblocks Phase 2's subscription driving
  4. Architectural gate: NyraInfer spawns on demand with Gemma 3 4B IT QAT Q4_0 GGUF loaded over llama.cpp (or auto-detected Ollama), exposed as OpenAI-compatible endpoint on localhost — proves the offline fallback binary path before Phase 2 wires the router to it
  5. Architectural gate: plugin builds as two modules (`NyraEditor` editor-only, `NyraRuntime` minimal runtime stub) with `.uplugin` descriptor valid on UE 5.6; no Fab packaging yet but the layout is Fab-ready
**Plans**: TBD
**UI hint**: yes

### Phase 2: Subscription Bridge + Four-Version CI Matrix
**Goal**: NYRA's economic wedge — subprocess-driving the user's Claude Code CLI — is live end-to-end with graceful Gemma fallback on rate-limit or auth failure, the four-version CI matrix (UE 5.4/5.5/5.6/5.7) is enforcing compat from day one, and every agent mutation is transactional with safe-mode plan-preview as default.
**Depends on**: Phase 0 (legal clearance required before any subscription-driving code ships), Phase 1 (three-process IPC working)
**Requirements**: PLUG-04, SUBS-01, SUBS-02, SUBS-03, CHAT-02, CHAT-03, CHAT-04, ACT-06, ACT-07
**Success Criteria** (what must be TRUE):
  1. Beats every competitor on economics (Aura/Telos, CoPilot, Ludus all bill for inference): Claude Code CLI subscription driving verified end-to-end on Windows via `claude -p --output-format stream-json --verbose` with `--mcp-config` injecting NYRA's MCP server — subscription connection status UI (CHAT-02) makes the no-new-bill wedge visible to users on first run
  2. Beats every competitor on enterprise-readiness: graceful fallback to Gemma on 429/auth-drift with clear user-facing status, AND Privacy Mode toggle (Gemma-only, all egress blocked except user's own CLI) — no competitor ships offline fallback, this converts NDA/studio prospects that bounce off cloud-only tools
  3. Beats Aura/CoPilot on trust-through-transparency: CHAT-04 safe-mode/dry-run is the DEFAULT — every agent mutation outputs its tool-call sequence before execution; CoPilot has preview mode and Aura's Dragon Agent does plan-then-execute, NYRA ships plan-first by default on day one of actions
  4. Beats CoPilot/Aura on undo safety: every agent mutation wrapped in `FScopedTransaction` under a per-session super-transaction — Ctrl+Z rolls back an entire NYRA session as one unit, not step-by-step. Cancel-button cleanly unwinds in-flight subprocesses.
  5. Architectural gate (non-negotiable per PITFALLS §3.3): four-version CI (UE 5.4/5.5/5.6/5.7) green on day one of this phase — no version-specific code merges without all four passing. `NYRA::Compat::` shim covers Slate/Material/Sequencer/Blueprint drift hotspots with empirical matrix test. This prevents the ABI-drift retrofit trap (3-5x cost late).
  6. Architectural gate: EV code-signing cert acquired and applied to plugin DLL, NyraHost.exe, NyraInfer.exe — SmartScreen clears on first install (non-EV has a 30-day reputation window that poisons launch). Router is designed multi-backend (SUBS-03) so Codex drops in for v1.1 without refactor. Console-command (ACT-06) and Output/Message Log tools (ACT-07) ship here as universal introspection primitives every later phase uses.
**Plans**: 14 plans
Plans:
- [ ] 02-01-four-version-ci-matrix-bootstrap-PLAN.md — CI runner provisioning + plugin-matrix.yml + NYRACompat.h skeleton (Wave 0, CHECKPOINT)
- [ ] 02-02-wire-protocol-extension-PLAN.md — Additive JSONRPC + ERROR_CODES Phase 2 surface (Wave 0)
- [ ] 02-03-backend-interface-refactor-PLAN.md — AgentBackend ABC + GemmaBackend wrapper + BACKEND_REGISTRY (Wave 0, TDD)
- [ ] 02-04-ev-cert-acquisition-runbook-PLAN.md — DigiCert EV + Azure Key Vault founder runbook (Wave 0, CHECKPOINT)
- [ ] 02-05-claude-subprocess-driver-PLAN.md — ClaudeBackend + stream-json parser + MCP config writer (Wave 1, TDD, phase0-gated)
- [ ] 02-06-router-state-machine-PLAN.md — Router state enum + transitions + session/set-mode + Privacy Mode (Wave 1, TDD, phase0-gated)
- [ ] 02-07-compat-shim-empirical-fill-PLAN.md — Populate NYRA::Compat from first four-version matrix run (Wave 1, CHECKPOINT)
- [ ] 02-08-session-super-transaction-PLAN.md — FNyraSessionTransaction + PIE gate + diagnostics/pie-state (Wave 2, TDD)
- [ ] 02-09-safe-mode-permission-gate-PLAN.md — nyra_permission_gate MCP tool + plan/preview + plan/decision + SNyraPreviewCard (Wave 2, TDD, phase0-gated)
- [ ] 02-10-console-exec-mcp-tool-PLAN.md — Whitelist + nyra_console_exec + FNyraConsoleHandler (Wave 2, TDD)
- [ ] 02-11-log-tail-mcp-tool-PLAN.md — FNyraOutputDeviceSink + FNyraMessageLogListener + nyra_output_log_tail + nyra_message_log_list (Wave 2, TDD)
- [ ] 02-12-status-pill-ui-PLAN.md — SNyraBackendStatusStrip + diagnostics/backend-state subscription + first-run wizard (Wave 3)
- [ ] 02-13-ev-signing-ci-integration-PLAN.md — AzureSignTool + signtool verify CI steps (Wave 3, CHECKPOINT)
- [ ] 02-14-phase2-release-canary-PLAN.md — Nyra.Dev.SubscriptionBridgeCanary + live pytest + 02-VERIFICATION.md (Wave 3, CHECKPOINT, phase0-gated)
**UI hint**: yes

### Phase 3: UE5 Knowledge RAG
**Goal**: NYRA answers any "how do I do X in UE5" question with verbatim-quote citations tagged to the user's UE version, validates cited symbols against the user's installed UE headers before any action, and refreshes its index same-day or next-day after Epic ships a new UE version.
**Depends on**: Phase 2 (agent router + Gemma fallback + CI matrix)
**Requirements**: KNOW-01, KNOW-02, KNOW-03, KNOW-04
**Success Criteria** (what must be TRUE):
  1. Beats Nwiro and CoPilot on knowledge freshness: day-of support for new UE releases via a GitHub-Releases index-build pipeline triggered on Epic release tags — no competitor publishes day-of UE version support. Tested with simulated UE release (5.7 → 5.8 stub).
  2. Beats Aura/CoPilot on answer trustworthiness: every answer cites its source with a version tag AND a verbatim quote from the retrieved chunk (not a paraphrase) — and before any action touching a UE API, a symbol-validation step confirms the referenced symbol exists in the user's installed UE version. Hallucinated-API rate measured against a golden-set Q&A suite with target <2% (competitor baseline: agent-on-vanilla-LLM hallucination is ~15-30% on UE-specific APIs per FEATURES).
  3. Beats CoPilot/Ludus on offline/privacy use: KNOW-04 Gemma 3 4B multimodal answers docs Q&A and baseline asset search when Claude is unavailable (offline, rate-limited, privacy mode) — no competitor ships offline Q&A, so this is a first-class enterprise differentiator.
  4. Architectural gate: bundled LanceDB index ships <200 MB tiered (50 MB bootstrap bundled in plugin + full index downloaded on first run), with BGE-small-en-v1.5 ONNX embeddings (133 MB, MIT license). Corpus is license-clean only: UE5 official docs (5.4-5.7), Blueprint node reference, C++ API headers, Epic forum posts, community transcripts with attribution — hard block on paid-course domains (Udemy, Skillshare, Unreal Fellowship, Domestika, ArtStation Learning).
**Plans**: TBD

### Phase 4: Blueprint + Asset + Material + Actor Tool Catalog
**Goal**: NYRA ships a deep, reliable UE-native Tool Catalog — Blueprint graph read/write/rewire, Blueprint debug-and-fix loop, asset search, actor CRUD, material-instance operations — where every tool is transactional, idempotent, and verified post-condition. This is the phase that beats Aura/Telos on Blueprint reasoning.
**Depends on**: Phase 3 (symbol validation from RAG is the pre-execution gate)
**Requirements**: ACT-01, ACT-02, ACT-03, ACT-04, ACT-05
**Success Criteria** (what must be TRUE):
  1. Beats Aura/Telos 2.0 on Blueprint reasoning accuracy: compile-success rate on a canned suite of broken Blueprints exceeds Aura's published 25× error-reduction baseline (target >30× or documented ceiling). ACT-01 reads K2 graphs as structured JSON and writes back diffs; ACT-02 closes the debug loop (intercept error → plain-English explanation → diff → one-click apply → recompile → iterate until clean).
  2. Beats Ultimate Engine CoPilot on tool depth (not breadth): 20-30 deep tools with transaction support, undo, pre-condition validation (symbol validation from KNOW-02), and post-condition verification — each measured for per-tool reliability. CoPilot's ~1,050 actions are breadth-first Python wrappers; NYRA's depth-per-tool reliability metric is documented and measurably higher on the canned suite.
  3. Beats Nwiro on asset reuse workflow: ACT-03 fuzzy asset search over `FAssetRegistryModule` (name/tag/class, structured queries) means scene assembly prefers the user's own library before generating new assets — Nwiro's one-prompt scene uses their fixed Leartes catalog; NYRA uses the user's own assets first, generating only what's missing.
  4. Beats every competitor on silent-failure avoidance: ACT-04 actor CRUD and ACT-05 material-instance ops both emit evidence with every "done" message (actor name + world location + viewport-visible confirmation; parameter name + before/after value + applied-to-actor list). Every state change wrapped in `FScopedTransaction` under the session super-transaction from Phase 2.
**Plans**: TBD

### Phase 5: External Tool Integrations (API-First)
**Goal**: NYRA reaches outside UE to drive Meshy (REST), ComfyUI (local HTTP), and — where no API exists — Substance 3D Sampler and UE modal dialogs via Claude computer-use (`computer_20251124`, Opus 4.7). API-first per founder directive: computer-use is a scalpel, not a hammer. Computer-use reliability spike gates final phase scope.
**Depends on**: Phase 4 (Asset Import Bridge + staging-manifest pattern is built on the Tool Catalog foundation)
**Requirements**: GEN-01, GEN-02, GEN-03
**Success Criteria** (what must be TRUE):
  1. Beats every competitor on cross-tool orchestration (no competitor reaches outside UE): GEN-01 Meshy REST API integration (image → 3D, job polling, download, auto-import as `UStaticMesh` with LODs and collision) and GEN-02 ComfyUI local HTTP (image-to-image workflows → auto-import as `UTexture2D` or Material inputs) both pass a random-reference canary daily on a representative Windows 11 machine — >85% success rate on the canned task suite.
  2. Beats every competitor on trust during external-tool work: GEN-03 Claude computer-use is confined to Substance 3D Sampler (no public API exists) and UE editor modal dialogs the Unreal API doesn't expose; always-visible agent-active HUD, confirmation gate on first action per session, Ctrl+Alt+Space keyboard-chord pause, DPI-safe UIA structural clicks. User never sees their cursor hijacked for a tool that has an API.
  3. Beats every competitor on reliability-per-failure: staging-manifest pattern (NyraHost writes `nyra_pending.json`, UE Asset Import Bridge reads it) means external tools never touch UE Content directly — every import is undoable and auditable. Idempotent tool-calls (UUID-keyed imports) prevent duplicate-asset accumulation that PITFALLS §5.4 flags as a common cross-tool failure.
  4. Architectural gate: computer-use reliability spike (20 scripted sessions against Substance Sampler + ComfyUI UI states) completes with >85% success rate on the canned task suite. If <85%, computer-use scope contracts to UE modal dialogs only and Substance Sampler is flagged for v1.1. This gate is mandatory before Phase 7 commits to DEMO-02.
**Plans**: TBD

### Phase 6: Scene Assembly + Image-to-Scene (Fallback Launch Demo)
**Goal**: NYRA delivers DEMO-01 end-to-end — user drops a reference image, NYRA assembles a matching UE scene (5-20 actors, one light setup, hero materials) preferring the user's own asset library first and generating missing hero assets via Meshy or missing textures via Substance/ComfyUI. This is the fallback launch demo if DEMO-02 slips.
**Depends on**: Phase 4 (Tool Catalog), Phase 5 (external tool integrations and staging manifest)
**Requirements**: SCENE-01, DEMO-01
**Success Criteria** (what must be TRUE):
  1. Beats Nwiro on scene-assembly style consistency: DEMO-01 reference-image-to-UE-scene prefers the user's own asset library first, generates missing hero assets via Meshy and missing textures via Substance/ComfyUI — Nwiro's one-prompt scene uses their fixed Leartes catalog (great quality, narrow style); NYRA's output is style-consistent with what the user already has, which is what indies and studios actually want.
  2. Beats Nwiro/CoPilot on lighting authoring: SCENE-01 handles directional/point/spot/rect/sky lights + SkyAtmosphere + VolumetricCloud + ExponentialHeightFog + PostProcessVolume + exposure curves from natural-language prompts ("golden hour", "harsh overhead volumetrics") AND from reference images ("match this image's mood") — Nwiro has cinematic presets, CoPilot has granular light actions, but "match this reference image's lighting mood" is unique to NYRA.
  3. Beats every competitor on first-install cold-start reliability: DEMO-01 passes the random-reference daily test from Phase 6 Day 1 — the exact code path the demo uses is the exact code path users run (no "demo mode" feature flag). A full uninstall + reinstall + run-demo pass is a release gate, not a checkbox.
  4. Architectural gate: DEMO-01 is the v1-launchable state — if DEMO-02 (Phase 7) slips past the 6-9 month budget, the launch reposts around DEMO-01 and still beats Nwiro via GEN-01+GEN-02+GEN-03 orchestration. This is the nuclear cut-line from FEATURES §v1-cut-line.
**Plans**: 5 plans (06-00 through 06-04)
Plans:
- [ ] 06-00-PLAN.md -- Wave 0: SceneAssemblyOrchestrator + AssetPool + scene_orchestrator base class (foundation, no UE-native code)
- [ ] 06-01-SCENE-01-lighting-authoring-PLAN.md -- Wave 1: SCENE-01 lighting MCP tools + SNyraLightingSelector per UI-SPEC
- [ ] 06-02-DEMO-01-image-to-scene-PLAN.md -- Wave 2: DEMO-01 scene assembly planner + actor placement pipeline
- [ ] 06-03-staging-test-PLAN.md -- Wave 3: End-to-end integration tests for assembly + lighting
- [ ] 06-04-PLAN.md -- Wave 4: NyraToolCatalogCanary Phase 6 extension + DEMO-01 canary test + exit gate
**UI hint**: yes

### Phase 7: Sequencer + Video-to-Matched-Shot (LAUNCH DEMO)
**Goal**: NYRA delivers DEMO-02 — user pastes a YouTube link or attaches a ≤10s mp4, NYRA extracts keyframes, infers composition + lighting + approximate geometry, and assembles a matching single-shot single-location UE scene with one CineCamera, key+fill lighting, sky+fog, and Sequencer-driven camera. This is the launch demo that no competitor ships.
**Depends on**: Phase 6 (scene assembly + lighting), Phase 5 (external tool orchestration for per-shot asset generation)
**Requirements**: SCENE-02, DEMO-02
**Success Criteria** (what must be TRUE):
  1. Beats every competitor by setting a new benchmark: DEMO-02 reference-video-to-matched-shot ships end-to-end — no competitor (Nwiro, Aura, CoPilot, Ludus, OSS MCP long tail) has this as of April 2026. NYRA's v1 benchmark (single-shot ≤10s clips with correct composition + lighting intent + camera motion taxonomy) is high enough that the next entrant cannot trivially match it.
  2. Beats Nwiro on Sequencer authoring: SCENE-02 creates `ULevelSequence`, adds CineCamera actors, sets keyframes on actor/camera/light/PPV parameters, and authors shot blocking from natural language ("slow push-in on the hero, then cut wide"). Nwiro has some cinematic composition but no strong NL shot-blocking.
  3. Beats every competitor on video-reference correctness: the Video Reference Analyzer uses scene-cut detection (ffmpeg `-vf "select='gt(scene,0.3)'"`) + semantic lighting extraction (not RGB analysis that misreads LUTs) + a canonical camera-move taxonomy (static/pan/tilt/dolly/truck — user-confirmable). PITFALLS §6.1-6.3 risks (keyframe miss, dolly-vs-truck confusion, LUT/RGB mismatch) are measurably below 15% failure rate on a diverse clip set.
  4. Beats every competitor on copyright safety during demo use: reference-video processing is ephemeral (yt-dlp download + extract keyframes + send ≤16 keyframes to Claude; delete full video from `/tmp` after run by default). Surfaced paste-time disclaimer; no full-video upload to Anthropic. PITFALLS §6.4 mitigations are visible in the log.
  5. Architectural gate (release gate): the "first-install cold-start" test passes — uninstall plugin + claude-code cache + browser profile, reinstall everything, run the launch demo on a random-reference clip (not the demo reference). If it fails clean on three consecutive random clips, Phase 8 does not start.
**Plans**: TBD
**UI hint**: yes

### Phase 8: Competitive Parity vs Aura
**Goal**: Close the Aura feature-surface gap so NYRA's "no new AI bill + offline + computer-use + video-to-scene" wedge reads as ADDITIVE (more capability than Aura, free) rather than substitute (narrower than Aura, but free). Eight feature areas land: document attachments (PDF/DOCX/PPTX/MD), C++ authoring with Live Coding integration, Behavior Tree authoring agent, drag-from-Content-Browser into chat, Niagara VFX authoring agent, Performance Profiling agent (Insights/Stat reads), Animation Blueprint authoring, Metasounds (audio) agent. Each area is a discrete plan; the parity bar is "Aura's documented capability is matched or exceeded on the same input shape."
**Depends on**: Phase 4 (Tool Catalog dispatcher + permission gate + transactional safety patterns), Phase 5 (External tool integration patterns), Phase 1 (NyraHost MCP surface)
**Requirements**: PARITY-01 through PARITY-08 (one per feature area; to be added to REQUIREMENTS.md during planning)
**Success Criteria** (what must be TRUE):
  1. **Beats Aura on document inputs**: PARITY-01 attachment pipeline accepts PDF + DOCX + PPTX + XLSX + HTML + Markdown (matches Aura's surface) and additionally extracts inline images for vision-routing through the existing image-attachment path (Aura accepts docs but NYRA's attachment flow already routes images to Claude vision — the combination is a clean win). Text extraction uses pure-Python parsers (`pypdf`, `python-docx`, `python-pptx`, `openpyxl`, `markdown`) so the offline wheel cache stays bounded under 50 MB.
  2. **Beats Aura on C++ authoring + Live Coding**: PARITY-02 ships `nyra_cpp_module_create / nyra_cpp_class_add / nyra_cpp_function_add / nyra_cpp_recompile` quartet wired through UE's Hot Reload + Live Coding subsystems. Where Aura ships C++ generation as one tool, NYRA decomposes into transactional steps (CR-UD pattern from Phase 4 Tool Catalog) — every step is undoable via the session_transaction wrapper. Compile errors flow back through `nyra_blueprint_debug`'s pattern-matching surface, generalised to C++ (existing regex patterns extend cleanly).
  3. **Beats Aura on Behavior Tree authoring**: PARITY-03 ships `nyra_bt_create / nyra_bt_add_composite / nyra_bt_add_task / nyra_bt_add_decorator / nyra_bt_set_blackboard_key` quintet via UE's `unreal.BehaviorTree` Python API. Aura's BT agent is monolithic; NYRA's surface is composable, idempotent (BL-05 pattern from Phase 4), and post-condition-verified (BL-06).
  4. **Matches Aura on drag-from-Content-Browser UX**: PARITY-04 wires Slate drag-target on `SNyraComposer` to receive `FAssetData` payloads from the Content Browser; converts to a structured attachment chip referencing the asset path. The existing image-drop-zone pattern extends cleanly. Architectural gate: this unblocks Phase 8 plans that need asset-targeted prompts ("apply this material to the dragged asset").
  5. **Matches Aura on Niagara VFX authoring**: PARITY-05 ships `nyra_niagara_create_system / nyra_niagara_add_emitter / nyra_niagara_set_module_parameter` triplet. Niagara's Python API surface is large but well-documented; the parity bar is "Aura's GPU sprite + ribbon emitter examples reproduce."
  6. **Beats Aura on Performance Profiling**: PARITY-06 ships `nyra_perf_stat_read / nyra_perf_insights_query / nyra_perf_explain_hotspot`. Read-only over UE's `stat unit / stat unitgraph / stat memory` outputs and Insights `.utrace` files. Where Aura's profiling agent suggests fixes, NYRA additionally cross-references against the Phase 3 `nyra_kb_search` UE5 docs index — explanations cite specific Epic docs paragraphs. This is a defensible "beats Aura" claim because Aura has no separate docs RAG.
  7. **Matches Aura on Animation Blueprint authoring**: PARITY-07 ships `nyra_animbp_create / nyra_animbp_add_state_machine / nyra_animbp_add_transition`. Lower marketing visibility than BT but completes the "AI / character / animation" agent triplet.
  8. **Matches Aura on Audio (Metasounds)**: PARITY-08 ships `nyra_metasound_create / nyra_metasound_add_node / nyra_metasound_connect`. Smallest surface area; included for marketing-comparison parity. (Honest acknowledgment: most game audio lives in Wwise/FMOD outside UE, so this tool is feature-surface gloss more than usage-volume win.)
**Plans**: TBD (8 plans, one per success criterion; some plans may share research; planner will batch into waves)
**UI hint**: yes

### Phase 9: Fab Launch Prep
**Goal**: NYRA ships to Fab with zero-config install, per-UE-version EV-signed binaries, AI-disclosure-compliant listing, and a direct-download fallback already live on nyra-engine.com (or temporary host) so a Fab rejection doesn't block launch. Every onboarding path ends in first-successful-action within 10 minutes of install. (Was Phase 8 prior to 2026-05-10 reframe — content unchanged, number bumped.)
**Depends on**: Phase 8 (competitive parity), Phase 7 (launch demo), Phase 2 (EV cert + CI matrix), Phase 0 (Fab pre-clearance + brand guideline compliance)
**Requirements**: DIST-01, DIST-02, DIST-03, DIST-04
**Success Criteria** (what must be TRUE):
  1. Beats every competitor on first-install experience: DIST-04 zero-config install — user enables plugin in UE, runs `claude setup-token` once, and is operational. First-run wizard verifies Claude Code CLI, downloads Gemma on demand (user-consented progress UI), confirms computer-use readiness. Time-to-first-successful-action target <10 minutes from Fab download click; no competitor has been measured under 15 minutes on Windows.
  2. Beats every competitor on distribution resilience: DIST-02 direct-download fallback live on nyra-engine.com BEFORE Fab submission — signed installer is the escape hatch if Fab rejects. Competitors distributing Fab-only (most of them) are exposed to a single point of failure; NYRA is not.
  3. Beats every competitor on AI-plugin compliance: DIST-01 Fab listing passes on first submission — AI-disclosure copy compliant with Fab's 2026 AI-plugin policy (pre-cleared in Phase 0), per-UE-version binaries (5.4/5.5/5.6/5.7), launch demo trailer shot as a real time-lapsed run (no cherry-picking, no demo-mode flag — per PITFALLS §7.2 demo-driven-development trap prevention), screenshots, marketing assets.
  4. Beats every competitor on install trust: DIST-03 EV code-signing cert signs all binaries (plugin DLL per UE version, NyraHost.exe, NyraInfer.exe) — SmartScreen clears instantly on first install. Competitors without EV certs have a 30-day reputation window that poisons early reviews; NYRA's first-install experience does not warn users away.
  5. Architectural gate: public devlog has been shipping from Month 1 (cross-cutting PITFALLS §7.4 mitigation) so NYRA has a following before Fab submission — if a competitor pips the DEMO-02 reveal, NYRA's audience is already attached.
**Plans**: TBD
**UI hint**: yes

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 0. Legal & Brand Gate | 3/6 [‡] [§] [¶] | In progress — docs-layer; SC#1 PENDING Anthropic written reply, SC#2 PENDING Fab written reply (BLOCKED not product-fatal because fallback SPEC ships per CONTEXT.md D-07), SC#3 closed at docs-layer with `aggregate_verdict: MEDIUM-RISK` (Class 9 software presumptive CLEAN; founder verbatim-upgrade pending) + `final_name: NYRA` + `filing_status: DEFERRED-TO-V1.1` + `devlog_gate: OPEN` | 00-01 (2026-04-24 docs-layer; pending_manual_verification:true — founder sends email + files Anthropic response), 00-02 (2026-04-24 docs-layer; pending_manual_verification:true — founder sends email + files Epic/Fab response; OR sets BLOCKED-BY-SILENCE at Day 63 to activate fallback primary per legal/00-02-direct-download-fallback-plan.md §1 Trigger a), 00-03 (2026-04-24 docs-layer; pending_manual_verification:true — 3 registry raw dumps + dossier + backup-screening + verdict-and-reservations with embedded reservation-manifest YAML; founder registers nyra-engine.com at Cloudflare Registrar + claims github.com/nyra-plugin + claims X/Reddit/YouTube/Discord handles + verbatim-upgrades USPTO/EUIPO/WIPO raw dumps; if any verbatim Class-9 NYRA live mark surfaces, AELRA warm-standby rollback per verdict-and-reservations §Rollback Plan) |
| 1. Plugin Shell + Three-Process IPC | 16/16 [†] | Source+docs COMPLETE; SC#3 empirical bench PENDING Windows operator | 01-03 (2026-04-21), 01-01 (2026-04-21), 01-02 (2026-04-21), 01-04 (2026-04-21), 01-05 (2026-04-21), 01-06 (2026-04-22), 01-07 (2026-04-22), 01-08 (2026-04-22), 01-09 (2026-04-22), 01-10 (2026-04-22), 01-11 (2026-04-23), 01-12 (2026-04-23), 01-12b (2026-04-23), 01-13 (2026-04-23), 01-14 (2026-04-23), 01-15 (2026-04-23 docs-layer; empirical bench pending Windows run) |
| 2. Subscription Bridge + Four-Version CI Matrix | 12/14 | Source+docs COMPLETE; 02-07/02-13/02-14 blocked on human checkpoints | 02-01 (2026-04-25), 02-02 (2026-04-25), 02-03 (2026-04-25), 02-04 (2026-04-25), 02-05 (2026-04-26), 02-06 (2026-04-26), 02-07 (2026-04-27 docs-layer; compat shim pending matrix run), 02-08 (2026-04-27), 02-09 (2026-04-27), 02-10 (2026-04-28), 02-11 (2026-04-28), 02-12 (2026-04-28), 02-13 (2026-04-28 docs-layer; EV signing pending cert), 02-14 (2026-04-28 docs-layer; canary pending clearance) |
| 3. UE5 Knowledge RAG | 8/8 | Source+docs COMPLETE; SC#2 KnowledgeBench PENDING Windows operator run; SC#1/03-07 PLAN-COMPLETE (operator tags `ue-*` when Epic ships); all other SC ✅ | 03-01 (2026-05-07), 03-02 (2026-05-07), 03-03 (2026-05-07), 03-04 (2026-05-07), 03-05 (2026-05-07), 03-06 (2026-05-07), 03-07 (2026-05-07 PLAN-COMPLETE; operator-run), 03-08 (2026-05-07 PLAN-COMPLETE; operator-run KnowledgeBench) |
| 4. Blueprint + Asset + Material + Actor Tool Catalog | 6/6 | Source+docs COMPLETE; operator-run pending (SC#1–06 all PLAN-COMPLETE; `Nyra.Dev.ToolCatalogCanary` reports all 13 tools registered) | 04-01 (2026-05-07), 04-02 (2026-05-07), 04-03 (2026-05-07), 04-04 (2026-05-07), 04-05 (2026-05-07), 04-06 (2026-05-07) |
| 5. External Tool Integrations (API-First) | 4/4 | Source+docs COMPLETE; 22/22 tests passing | 05-01 (2026-05-07), 05-02 (2026-05-07), 05-03 (2026-05-07), 05-04 (2026-05-07) |
| 6. Scene Assembly + Image-to-Scene (Fallback Launch Demo) | 5/5 | PLAN-COMPLETE; operator-run pending | 06-00 (2026-05-09), 06-01 (2026-05-08), 06-02 (2026-05-08), 06-03 (2026-05-08), 06-04 (2026-05-09) |
| 7. Sequencer + Video-to-Matched-Shot (LAUNCH DEMO) | 5/5 | PLAN-COMPLETE; operator-run pending | 07-00 (2026-05-09), 07-01 (2026-05-09), 07-02 (2026-05-09), 07-03 (2026-05-09), 07-04 (2026-05-09) |
| 8. Competitive Parity vs Aura | 0/8 | Planning in progress (2026-05-10) — was previously "Fab Launch Prep" before the Aura competitive analysis prompted reframe. 8 plans seeded: PARITY-01 docs / PARITY-02 C++ / PARITY-03 BT / PARITY-04 drag-drop / PARITY-05 Niagara / PARITY-06 Perf / PARITY-07 AnimBP / PARITY-08 Metasounds. | - |
| 9. Fab Launch Prep | 0/? | Not started (was Phase 8 prior to 2026-05-10 reframe; content unchanged, number bumped) | - |

---

## Dependency Graph

Derived from FEATURES.md feature-dependency graph + ARCHITECTURE.md ring order. Each arrow means "downstream phase requires upstream phase complete."

```
Phase 0 (Legal)               Phase 1 (Plugin Shell + IPC)
     \                             /
      \                           /
       \                         v
        +------> Phase 2 (Subscription Bridge + CI Matrix) <--+
                       |                                       |
                       v                                       |
                Phase 3 (RAG / Knowledge)                      |
                       |                                       |
                       v                                       |
                Phase 4 (Tool Catalog: BP + Asset + Mat + Act) |
                       |                                       |
                       v                                       |
                Phase 5 (External Tools: API-first + CU spike) |
                       |                                       |
                       +------------+                          |
                                    v                          |
                             Phase 6 (Image -> Scene / DEMO-01) (fallback launch)
                                    |
                                    v
                             Phase 7 (Video -> Shot / DEMO-02) (LAUNCH DEMO)
                                    |
                                    v
                             Phase 8 (Competitive Parity vs Aura) <- depends on P1 MCP + P4 Tool Catalog + P5 patterns
                                    |
                                    v
                             Phase 9 (Fab Launch Prep) <-------+
                                                     (needs P0 pre-clearance + P2 CI/EV cert)
```

Critical path to LAUNCH DEMO (DEMO-02): Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7.
Critical path to FAB LAUNCH: Phase 7 → Phase 8 → Phase 9 (Phase 8 inserted 2026-05-10 to close the Aura feature-surface gap before going public).

Parallel-safe:
- Phase 0 runs in parallel with Phase 1 (legal emails in flight while plugin scaffold is built).
- Phase 3 (RAG) and Phase 4 (Tool Catalog) share a boundary: symbol validation (KNOW-02) is a pre-execution gate for Phase 4 actions, so Phase 3 must land before Phase 4 completes. A solo dev can start Phase 4 tooling stubs during Phase 3 corpus work.

Nuclear fallback: if Phase 7 exceeds the 6-9 month budget, the launch repositions around Phase 6 (DEMO-01, image → scene). This is the documented fourth cut-line (see Kill Cut-Lines below).

---

## Kill Cut-Lines

Explicit drop order if the solo 6-9 month timeline runs tight. Codex (originally FEATURES's first cut) is already deferred to v1.1 by founder decision, so the cut-lines adjust one slot down.

**First cut (already made — founder decision):**
- SUBS-10 Codex CLI subprocess driving → deferred to v1.1. Router designed multi-backend so drop-in post-v1 requires no refactor. Rationale: halves integration + legal + auth surface; Codex CLI programmatic surface is LOW-confidence in STACK research.

**Second cut (if Phase 5-6 slips by >4 weeks):**
- Drop DEMO-02 multi-shot ambitions → v1 is single-shot ≤10s only (already the v1 scope, so this cut is about *not* attempting multi-shot ambition in Phase 7).
- Defer GEN-03 Substance 3D Sampler computer-use → v1.1. Computer-use scope contracts to UE editor modal dialogs only. Phase 6/7 demos substitute ComfyUI for PBR material generation.

**Third cut (if Phase 4-5 slips by >6 weeks):**
- Drop ACT-02 Blueprint debug auto-fix-and-apply → downgrade to "explain error only" (remove the one-click apply + re-compile loop). This is the PITFALLS §7.1-aligned scope-cut from FEATURES cut-line 3. ACT-01 (read/write/rewire) still ships.
- Defer D10 local project RAG (not in v1 scope) and D9 thumbnail-embedding asset search (not in v1 scope) — already out of scope, listed here for clarity.

**Fourth cut (nuclear — if Phase 7 is not clearly reachable by Month 7):**
- Drop DEMO-02 (reference video → matched shot) → defer to v1.1 post-launch.
- Reposition launch around DEMO-01 (image → scene) as the primary demo. Still beats Nwiro via GEN-01+GEN-02+GEN-03 orchestration (user's own library first + generate missing) — painful because DEMO-02 is the explicit wedge and the reason no competitor can trivially match NYRA, but shippable.
- This cut triggers a repositioning of the launch messaging and Fab listing copy; the devlog-from-Month-1 discipline (PITFALLS §7.4) keeps audience engaged for a v1.1 DEMO-02 reveal.

**Discipline:** every phase entering planning has a "minimum shippable" tier and a "stretch" tier; if by day X of the phase the stretch isn't clearly reachable, it's cut *before* it's half-done (PITFALLS §7.1). Cut-lines are enforced at weekly self-retrospectives: "what's in Active that's not on the critical path to DEMO-02 + Fab-launch-readiness?"

---

*Roadmap defined: 2026-04-21 after research synthesis + founder directives*
*Coverage: 34/34 v1 requirements mapped to phases (see REQUIREMENTS.md traceability)*
