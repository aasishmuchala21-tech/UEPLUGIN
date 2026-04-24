# Phase 2: Subscription Bridge + Four-Version CI Matrix — Context

**Gathered:** 2026-04-23
**Status:** Ready for planning (discuss-phase bypassed; decisions distilled directly from `02-RESEARCH.md` + inherited Phase 1 locks + user-provided suggested wave structure)
**Source:** `02-RESEARCH.md` + `PROJECT.md` + `ROADMAP.md` §Phase 2 + `01-CONTEXT.md` (inherited D-01..D-20)

---

<domain>
## Phase Boundary

Phase 2 delivers NYRA's **economic wedge** end-to-end: subprocess-driving the user's Claude Code CLI (`claude -p --output-format stream-json`) with structured NDJSON parsing, a multi-backend router (Claude + Gemma, Codex-ready for v1.1), graceful fallback on rate-limit / auth-drift, plan-first safe-mode preview gate (CHAT-04), per-session super-transaction undo (CHAT-03), console-command + log-tail introspection primitives (ACT-06/07), the four-version UE CI matrix (5.4/5.5/5.6/5.7) from day one, and EV code-signing acquisition + pipeline integration.

**Requirements this phase satisfies:** PLUG-04, SUBS-01, SUBS-02, SUBS-03, CHAT-02, CHAT-03, CHAT-04, ACT-06, ACT-07 (9 reqs).

**Out of scope (pushed to later phases):**
- MCP tool **catalog** (full tool-call surface) → Phase 3/4. Phase 2 ships *introspection primitives only* — console (ACT-06), log-tail (ACT-07), and the permission-gate MCP tool (CHAT-04) that every later phase's tools plug into.
- RAG / knowledge index → Phase 3
- Blueprint edits / actor CRUD / material ops → Phase 4
- Meshy / ComfyUI / Substance (API + computer-use) → Phase 5
- Scene assembly, lighting authoring, reference-image-to-scene → Phase 6
- Sequencer automation, reference-video-to-shot → Phase 7
- Fab listing submission + direct-download fallback host → Phase 8 (EV cert is **acquired** here, **used** at Fab launch)
- Codex CLI adapter → v1.1 (router is designed multi-backend; adapter deferred)
- Anthropic direct-API "bring-your-own-key" mode → v1.1
- Pre-flight cost / quota prediction UI → v1.1 polish
- Streaming partial JSON preview cards (>10-step plans rendering mid-build) → Phase 2 buffers to `content_block_stop`; incremental render is a Phase 2.1 nicety if users ask for it

</domain>

<decisions>
## Locked Decisions

### Router architecture & Claude driver

- **D-01:** **Backend-abstract router refactor before Claude adapter lands.** `nyrahost/backends/base.py` defines `AgentBackend` ABC with `send / cancel / health_check` (signatures per RESEARCH §2.5). Phase 1's Gemma path is extracted into `nyrahost/backends/gemma.py` as `GemmaBackend(AgentBackend)` — no behaviour change, only interface extraction. `nyrahost/backends/claude.py` is the new concrete. `nyrahost/router.py` owns the state machine. **The abstract class is Wave 0; every subsequent plan targets it, not a concrete.** Codex drop-in for v1.1 becomes "write `codex.py`, register in the backend registry" — no router/UE changes.

- **D-02:** **Subprocess-driving the `claude` CLI, never embedding the Agent SDK** (re-asserts PROJECT.md lock). Phase 2 implementation: NyraHost spawns `claude -p --output-format stream-json --verbose --include-partial-messages --mcp-config <file> --strict-mcp-config --session-id <uuid> --permission-mode dontAsk --permission-prompt-tool nyra_permission_gate [--resume <id>] [--model opus]` via `asyncio.create_subprocess_exec`. `--bare` is NOT used (it skips OAuth; subscription mode requires OAuth). `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN` are **scrubbed from the child env** before spawn in subscription mode (RESEARCH §1.2 critical trap).

- **D-03:** **Router state machine states:** `Disconnected`, `ClaudeReady`, `ClaudeStreaming`, `ClaudeRateLimited`, `AuthDrift`, `GemmaFallback`, `PrivacyMode` (orthogonal mode dimension). Transitions driven primarily by NDJSON `system/api_retry` events whose `error` field is enumerated (`authentication_failed | billing_error | rate_limit | invalid_request | server_error | max_output_tokens | unknown`). Topology is locked per RESEARCH §2.1–2.3; transient `server_error` / `unknown` are **silent-retry up to 3** (RESEARCH §10.6) — they do NOT trip fallback.

- **D-04:** **Default backend policy at session start = Claude when `claude auth status` exits 0, else Gemma.** The router NEVER flips to Gemma without either (a) an exhausted rate-limit + user approval, (b) auth-drift detected, or (c) user-initiated Privacy Mode. There is no silent auto-fallback mid-stream. User gets an explicit one-click `[Switch to Gemma]` button when Claude errors.

- **D-05:** **Privacy Mode = LOCAL-ONLY.** No Claude spawn, no Meshy/ComfyUI calls (affects Phase 5), no RAG index updates from GitHub (affects Phase 3), no Gemma download fetch. Attachment hashes + names are OK to log locally but MUST NOT leave the machine. Toggle surfaces a one-time disclaimer modal on first activation. Privacy Mode is an orthogonal state dimension — can overlay any other state. Wire method is new `session/set-mode` JSON-RPC request (UE → NH).

### Safe-mode preview contract (CHAT-04)

- **D-06:** **Path B — `--permission-prompt-tool nyra_permission_gate`** is the canonical safe-mode path (RESEARCH §4.1). NOT `--permission-mode plan` (which emits natural language, not structured JSON). The `nyra_permission_gate` MCP tool is exposed by NyraHost's stdio MCP server (spawned by Claude via `--mcp-config`). Schema locked per RESEARCH §4.2: `{summary, steps[{tool, args, rationale, risk}], estimated_duration_seconds, affects_files}`. `risk` enum: `read-only | reversible | destructive | irreversible`.

- **D-07:** **`plan-first-by-default` is the default and cannot be disabled in v1.** Router ALWAYS passes `--permission-prompt-tool nyra_permission_gate` AND `--permission-mode dontAsk`. User-visible "Auto-approve read-only this session" checkbox only fast-paths `risk: read-only` steps — destructive / irreversible steps always show the card.

- **D-08:** **Partial-JSON buffering rule:** router buffers `input_json_delta` fragments for the `nyra_permission_gate` tool_use block and emits `plan/preview` to UE only on `content_block_stop` — never mid-build. Prevents UE panel from re-rendering a plan card as the JSON grows. (Open Q #4 + RESEARCH §4.4.)

- **D-09:** **`plan/preview` (NH → UE notification) + `plan/decision` (UE → NH request) wire shapes locked per RESEARCH §4.3.** `plan/decision` carries `decision: "approve" | "reject" | "edit"`, optional `edited_plan`, and `auto_approve_read_only_this_session: bool`. NyraHost returns the decision to Claude as the `nyra_permission_gate` tool result.

### Transaction discipline (CHAT-03)

- **D-10:** **Session super-transaction via MANUAL `GEditor->BeginTransaction` / `EndTransaction`** (not long-lived `FScopedTransaction` member). `FNyraSessionTransaction` owns `int32 TransactionIndex` and exposes `Begin(FString SessionSummary)`, `End()`, `Cancel()`. Inner tool calls use **RAII `FScopedTransaction`** which coalesces into the outer via `UTransBuffer`'s ref-counted LIFO stack (verified stable 5.4–5.7 per RESEARCH §3.4). Ctrl+Z rolls back an entire NYRA session as one atomic unit.

- **D-11:** **Session boundary rules** (all enforced as automation/unit tests):
  - Objects flagged `RF_Transactional` before any `Modify()` call
  - `Modify()` called INSIDE the transaction scope BEFORE mutating state
  - Hot-reload during active session = refused (banner surfaces); `ShutdownModule` unconditionally calls `Cancel()` (RESEARCH §10.4)
  - PIE active = `chat/send` refused with error `-32014 pie_active` (new Phase 2 code per RESEARCH §12)
  - `chat/cancel` (Phase 1 wired) triggers `FNyraSessionTransaction::Cancel()` — rolls back whole session

### Four-version CI matrix (PLUG-04)

- **D-12:** **Self-hosted Windows runner** labeled `self-hosted,Windows,unreal`. GitHub-hosted runners (`windows-latest`) are unacceptable (RESEARCH §5.1 — cannot install UE inside a 6-hour job). Founder's own Windows dev workstation is the primary runner for v1; backup cloud Windows VM budgeted as v1.1 item. UE installs pinned to specific point versions: **5.4.4, 5.5.4, 5.6.1, 5.7.X** (exact .X depends on GA availability at phase-execution time).

- **D-13:** **`NYRA::Compat::` shim discipline.** `NyraEditor/Public/NYRACompat.h` defines `NYRA_UE_AT_LEAST(Major, Minor)` macro. Every `#if` block is SMALL (<20 lines) and tagged with `// NYRA_COMPAT: <reason>` comment. Larger drift moves to separate source files. **Shim entries emerge from the empirical Wave 0 first-matrix run — NOT from speculation.** Phase 2 populates the namespace ONLY with entries that the CI matrix run actually surfaces. Anticipated hotspots (RESEARCH §5.4) are *candidates*, not pre-committed code.

- **D-14:** **Matrix `fail-fast: false`** so one bad version does not block the other three (RESEARCH §5.3). Every PR runs all four cells; CI blocks merge only when a cell regresses. Monthly "UE version refresh" MR batches point-version bumps into one review.

- **D-15:** **UE 5.7 deferral rule:** if UE 5.7 is not GA at phase-execution time (<4 weeks post-release), ship matrix with 5.4/5.5/5.6 initially and add 5.7 as a same-day follow-up MR when available. The **planner assumes 5.7 IS available** and wires all four cells in Wave 0; the operator downgrades to 3 cells at plan-execute time if empirically unavailable. Documented as gap in compat-shim notes.

### EV code-signing (supports DIST-03 prep)

- **D-16:** **DigiCert EV cert in Azure Key Vault (Premium SKU).** ~$700/yr EV + ~$5/mo AKV = ~$760/yr total. Only major CA fully AKV-compatible (RESEARCH §6.1). Sectigo cheaper but not AKV-compatible. AKV Premium required (Standard cannot create RSA-HSM keys). Hard rule: **no USB token variant** — CI-unfriendly, single-workstation lock-in.

- **D-17:** **AzureSignTool in CI signing step** (RESEARCH §6.4). RFC 3161 timestamp server `http://timestamp.digicert.com` on every signature so signatures remain valid after cert expiry. Signs ALL deliverable Windows binaries per RESEARCH §6.5: `UnrealEditor-NyraEditor.dll` (per UE version), `UnrealEditor-NyraRuntime.dll` (per UE version), bundled `python.exe` (only if not pre-signed by Astral — empirically verify in Wave 0), `llama-server.exe` (only if not pre-signed by ggml.ai — empirically verify in Wave 0). Secrets: `AZURE_VAULT_URI`, `AZURE_CERT_NAME`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`.

- **D-18:** **Cert acquisition is a FOUNDER task, parallelizable with planner work.** 1-3 business days DigiCert identity verification; may take 1-2 weeks if no business entity exists. Cert acquisition DOES NOT block Phase 2 planning; it DOES block the final "CI signs green artifacts" plan. A Wave 0 founder-task plan tracks this as a checkpoint — planner provides runbook (`docs/EV_CERT_ACQUISITION.md`), founder executes.

### Console + log introspection (ACT-06, ACT-07)

- **D-19:** **Three-tier console-command whitelist** (RESEARCH §7.3): Tier A auto-approved (stat/showflag/log/help/obj-classes/r.VSync), Tier B preview-gated (generic `r.*` cvar set, profilegpu), Tier C hard-blocked (quit/exit/exec <file>/obj gc/reloadshaders/travel/open <map>/unmapped). Whitelist is JSON data (`NyraEditor/Config/nyra-console-whitelist-v1.json`), not C++ constants — live-curatable without recompile. Wave 0 enumerates all registered commands via `IConsoleManager::ForEachConsoleObjectThatStartsWith()` and commits the initial classified whitelist.

- **D-20:** **Editor-world-only execution.** `GEngine->Exec(GEditor->GetEditorWorldContext().World(), ...)`. PIE-triggered commands rejected in v1. FOutputDevice capture via `FStringOutputDevice` returned as tool result.

- **D-21:** **Output Log sink uses bounded ring buffer** (`MaxEntries=2000`) + category whitelist + max-verbosity filter. `nyra_output_log_tail` MCP tool REQUIRES `since_ts` + `max_entries` (cap=200 per call); agent must poll — subscription is forbidden (prevents 1800 lines/sec stat-unit flood). High-verbosity categories (`LogRHI`, `LogRenderCore`) default-excluded; agent must opt in explicitly.

- **D-22:** **Message Log listener registers own `FName("NYRA")` listing** + subscribes to the existing listings (`LogBlueprint`, `LogPIE`, `LogAssetTools`) via `OnDataChanged`. Phase 2 ships the plumbing; per-category parsing of `FTokenizedMessage` navigation is the tool job. `FCoreDelegates::OnHandleSystemError` binding flushes ring buffer to `Saved/NYRA/logs/crash-<ts>.log` before UE crash (RESEARCH §8.7).

### Wire protocol extensions (additive to Phase 1)

- **D-23:** **`docs/JSONRPC.md` is extended ADDITIVELY.** Phase 1's method surface (`session/authenticate`, `session/hello`, `chat/send`, `chat/stream`, `chat/cancel`, `shutdown`, `diagnostics/*`) is preserved verbatim. Phase 2 appends: `chat/send.params.backend` gets new value `"claude"` (alongside existing `"gemma-local"`); new methods `session/set-mode`, `plan/preview`, `plan/decision`, `console/exec`, `log/tail`, `log/message-log-list`, `diagnostics/backend-state`, `diagnostics/pie-state`, `claude/auth-status`. Same pattern for `docs/ERROR_CODES.md`: new codes `-32007..-32014` (per RESEARCH §12). **Module-superset discipline:** NO existing Phase 1 method signatures may change; every Phase 2 plan that touches these docs is additive-only and MUST preserve Phase 1 content verbatim.

- **D-24:** **Module-superset discipline for source files** (inherited from Phase 1 Plans 04→10→12→13 precedent). Every Phase 2 plan that touches `NyraEditorModule.cpp`, `SNyraChatPanel.cpp/.h`, `app.py`, `__main__.py`, or `docs/JSONRPC.md`/`docs/ERROR_CODES.md` MUST preserve the Phase 1 content verbatim and add only. `IMPLEMENT_MODULE` + Plan 03 include order + Plan 04 `RegisterNomadTabSpawner` + Plan 10 `GNyraSupervisor` + Plan 13 banner/modal/diagnostics wiring are ALL preserved as-is.

### TDD discipline

- **D-25:** **TDD mode ON for eligible Python and C++ unit-testable logic.** Every plan with `tdd: true` in frontmatter follows Phase 1's RED→GREEN commit pattern: `test(XX-YY): add failing test for <feature>` then `feat(XX-YY): implement <feature>`. TDD applies to: NDJSON stream parser, router state machine transitions, console-command whitelist classifier, permission-gate schema validator, log-tail filter logic, JSON-RPC method handlers. **NOT TDD** (type=auto): CI workflow YAML, EV cert acquisition runbook, Slate widget layout, `NYRA::Compat::` empirical shim population, UBT compile gates, C++ header-only compatibility macros.

### Ordering & gates

- **D-26:** **Phase 0 legal clearance is an EXECUTION precondition, NOT a planning precondition.** Phase 2 planning proceeds in parallel with Anthropic/Epic email threads. **Before executing** Plan `02-04-claude-subprocess-driver` and any plan that actually spawns `claude -p`, Phase 0's written ToS clarification from Anthropic MUST be on file. Planner marks these plans with `phase0_clearance_required: true` frontmatter; orchestrator enforces at execute-plan time.

- **D-27:** **Phase 1 Plan 15 empirical bench gate (SC#3)** is an EXECUTION precondition for Plan 02-14 (the Phase 2 end-to-end CI canary that demonstrates economic-wedge live). Plan 02-14 does NOT need the bench green to PLAN — but its execute-time verification expects the Windows operator bench has been run and the Phase 1 pass verdict committed.

</decisions>

<granularity>
## Plan Granularity

**Target:** 14 plans (within the user-specified 12–16 range), 4 execution waves, ~4–6 weeks solo-dev work.

**Wave 0 (infrastructure, parallel):** 4 plans — CI runner provisioning + matrix workflow, wire-protocol doc extension, backend-interface refactor (Python), EV cert acquisition runbook.

**Wave 1 (Claude driver + router state machine, mostly parallel):** 3 plans — Claude subprocess driver + NDJSON parser, router state machine + fallback policy, `NYRA::Compat::` shim header + first-matrix empirical fill.

**Wave 2 (safety + transactions + permission gate + introspection, mostly parallel):** 4 plans — C++ super-transaction + hot-reload refuse + PIE refuse; permission-gate MCP tool + `plan/preview`+`plan/decision` UE/Python round-trip + safe-mode UI card; console-command whitelist + `console/exec` wire + `nyra_console_exec` MCP tool; Output Log sink + Message Log listener + `log/tail` + `nyra_output_log_tail` MCP tool.

**Wave 3 (status UI + EV signing + green-matrix release gate):** 3 plans — CHAT-02 status-pill Slate strip + `diagnostics/backend-state` wiring + first-run wizard integration; CI EV-signing step + AzureSignTool integration + `signtool verify` gate; end-to-end CI matrix green across all four UE versions with signed artifacts + fixture-NDJSON schema capture + release canary.

</granularity>

<canonical_refs>
## Canonical References

### Mandatory for every Phase 2 plan
- `.planning/PROJECT.md` — Quality Bar, Key Decisions (all Phase 2 respects these)
- `.planning/REQUIREMENTS.md` — Phase 2 REQ IDs: PLUG-04, SUBS-01/02/03, CHAT-02/03/04, ACT-06/07
- `.planning/ROADMAP.md` §Phase 2 — Success Criteria authoritative (six SCs)
- `.planning/phases/02-subscription-bridge-ci-matrix/02-RESEARCH.md` — THE authoritative technical spec (1500 lines)
- `.planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md` — inherited D-01..D-20
- `.planning/phases/02-subscription-bridge-ci-matrix/02-CONTEXT.md` — **this file**, D-01..D-27 locks
- `docs/JSONRPC.md` — extend additively; NEVER rewrite Phase 1 content
- `docs/ERROR_CODES.md` — extend additively; NEVER renumber Phase 1 codes

### Mandatory for Python plans
- `.planning/research/STACK.md` — Claude Code CLI v2.1.118+, model pins
- `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/` — current package layout (bootstrap, config, handshake, jsonrpc, server, session, storage, attachments, app, handlers, infer, downloader)
- `.planning/phases/01-plugin-shell-three-process-ipc/01-06-nyrahost-core-ws-auth-handshake-SUMMARY.md` — NyraServer extension-point pattern (`register_request`/`register_notification`); authoritative for how new methods plug in
- `.planning/phases/01-plugin-shell-three-process-ipc/01-08-nyrahost-infer-spawn-ollama-sse-SUMMARY.md` — current Gemma path being refactored behind `AgentBackend`

### Mandatory for C++ plans
- `TestProject/Plugins/NYRA/Source/NyraEditor/` — current module layout (WS/, Process/, Panel/, Markdown/, Dev/, Tests/)
- `.planning/phases/01-plugin-shell-three-process-ipc/01-10-cpp-supervisor-ws-jsonrpc-SUMMARY.md` — FNyraSupervisor, FNyraWsClient, FNyraJsonRpc — module-superset discipline on these files
- `.planning/phases/01-plugin-shell-three-process-ipc/01-12-chat-panel-streaming-integration-SUMMARY.md` — SNyraChatPanel composition contract being extended
- `.planning/phases/01-plugin-shell-three-process-ipc/01-13-first-run-ux-banners-diagnostics-SUMMARY.md` — SNyraBanner + diagnostics drawer; Phase 2 status-pill adjacent

### Mandatory for CI plan
- RESEARCH §5 — self-hosted-runner provisioning + matrix workflow YAML shape
- `.github/workflows/` (currently empty — Phase 2 creates `plugin-matrix.yml`)

### Mandatory for EV-cert plan
- RESEARCH §6 — DigiCert + AKV vendor choice + acquisition steps + AzureSignTool CI snippet

</canonical_refs>

<deferred>
## Deferred Ideas (explicitly OUT OF SCOPE for Phase 2)

Captured here so they do NOT appear in any Phase 2 plan:

- **Full MCP tool catalog** (Blueprint edits, asset spawn, material ops, actor CRUD) — Phase 3/4
- **RAG / LanceDB / BGE-small embeddings** — Phase 3
- **Symbol validation gate** (check cited UE API exists in user's UE version) — Phase 3
- **Meshy REST integration / ComfyUI HTTP / Substance computer-use** — Phase 5
- **Scene assembly / lighting authoring / image-to-scene (DEMO-01)** — Phase 6
- **Sequencer automation / video-to-shot (DEMO-02)** — Phase 7
- **Fab listing + AI-disclosure copy + marketing assets** — Phase 8 (cert is acquired here; USED at launch)
- **Direct-download fallback host + installer signing pipeline** — Phase 8
- **Codex CLI subprocess adapter** — v1.1 (router multi-backend-ready; adapter deferred per PROJECT.md)
- **Anthropic direct-API "bring-your-own-key" mode** — v1.1
- **Token quota prediction / pre-flight cost preview** — v1.1 polish (RESEARCH §1.5 "signal, not prediction" rule)
- **Streaming partial JSON preview cards** — Phase 2 buffers to `content_block_stop`; incremental render = Phase 2.1 nicety if users ask
- **Multi-region Azure Key Vault replication** — v2+
- **Microsoft Trusted Signing migration (~$10/mo alternative to DigiCert)** — v2+ evaluation after publisher reputation accrues
- **Editable plan / mid-plan human edit of tool args** — minimum plan/decision contract only; plan edit is UI-advanced for v1.1
- **Universal cancel of computer-use subprocesses** — Phase 2 stubs the router hook; Phase 5 fills in when computer-use lands
- **Per-category Message Log tokenized navigation** — Phase 2 ships plumbing only; deep parsing of `FTokenizedMessage` navigation tokens happens when a downstream phase needs "navigate to this BP compile error"

</deferred>

---

*Phase: 02-subscription-bridge-ci-matrix*
*Context distilled: 2026-04-23 from 02-RESEARCH.md + PROJECT.md + ROADMAP.md Phase 2 + inherited 01-CONTEXT.md locks + user-provided suggested wave structure (discuss-phase bypassed)*
*Decisions locked: D-01..D-27*
