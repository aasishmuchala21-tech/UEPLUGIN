# Phase 2: Subscription Bridge + Four-Version CI Matrix — Research

**Researched:** 2026-04-22
**Domain:** Claude Code CLI subprocess driver + Gemma fallback router, FScopedTransaction session discipline, safe-mode dry-run contract, UE 5.4/5.5/5.6/5.7 CI matrix, EV code-signing pipeline, console-command + log-tail MCP tools
**Confidence:** MEDIUM-HIGH. Claude Code CLI surface HIGH (verified against code.claude.com 2026-04-22). stream-json event schema MEDIUM-HIGH (confirmed event names + partial-message behaviour; example NDJSON lines drawn from Anthropic Messages API spec). FScopedTransaction nesting semantics HIGH (Engine source pattern well-established; UE 5.4-5.7 `UTransBuffer` unchanged). CI matrix MEDIUM (self-hosted Windows runner is the only viable path; no verified public UE-in-cloud runner). EV cert MEDIUM-HIGH (pricing verified 2026-04-22; Azure Key Vault flow verified). Console + Message Log patterns HIGH.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

> **Note:** Phase 2 CONTEXT.md has not yet been produced (discuss-phase not yet run for Phase 2 per STATE.md). The constraints below are inherited from PROJECT.md, ROADMAP.md Phase 2 success criteria, and Phase 1 CONTEXT.md locks that forward into Phase 2. They MUST be treated as locked unless superseded by a Phase 2 CONTEXT.md.

### Locked Decisions (inherited — treat as D-NN)

**From PROJECT.md Key Decisions (non-negotiable):**
- Subprocess-drive Claude Code CLI (not embed Agent SDK) — Anthropic ToS prohibits third-party claude.ai login embedding. Plugin never sees the token; user's CLI authenticates via user's own machine OAuth.
- Drop Codex from v1 — deferred to v1.1. Router MUST be designed multi-backend so Codex drops in cleanly post-v1 with no refactor (SUBS-03).
- Gemma 3 4B IT QAT Q4_0 GGUF as local fallback — 3.16 GB, 128K context, multimodal. Phase 1 Plan 09 liquidated the downloader stub.
- Four-version CI matrix (5.4/5.5/5.6/5.7) on day one of Phase 2 — non-negotiable per PITFALLS §3.3. No version-specific code merges without all four passing.
- EV code-signing cert acquired in Phase 2 ($400-700/yr budget line). Applied to plugin DLL + NyraHost.exe + NyraInfer.exe. SmartScreen clears on first install.
- Every agent mutation wrapped in `FScopedTransaction` under a per-session super-transaction. Ctrl+Z rolls back whole NYRA session as one unit.
- Plan-first-by-default (CHAT-04). Every agent mutation outputs tool-call sequence before execution; user approves/rejects.
- Privacy Mode first-class — Gemma-only toggle blocks all egress except to user's own CLI.
- Phase 0 legal clearance (Anthropic + Epic/Fab) is a HARD GATE on Phase 2 EXECUTION. Phase 2 PLANNING may proceed in parallel.

**From Phase 1 CONTEXT.md that forwards into Phase 2:**
- **Inherited D-09/D-10/D-11/D-12:** JSON-RPC 2.0 wire envelope locked. Phase 2 extends the method surface additively (no breaking changes to Phase 1 `session/*`, `chat/*`, `shutdown` methods). Error codes `-32001..-32006` already allocated; Phase 2 extends with new codes only.
- **Inherited D-15:** Runtime Python deps pinned in `requirements.lock` — Phase 2 adds deps in lockfile-additive pattern (no unpinned requires, Plan 06 decision).
- **Inherited D-17:** Gemma download flow operational. Phase 2 router CONSUMES that pipeline (doesn't re-implement).
- **Inherited D-18:** llama-server.exe / Ollama auto-detect operational. Phase 2 fallback CONSUMES (doesn't re-implement).
- **Inherited D-03 (reversal):** Phase 1 was UE 5.6-only; Phase 2 MUST build all four UE versions.
- **Inherited `NYRA::Compat::` placeholder:** Shim namespace exists but empty. Phase 2 populates it based on empirical drift discovered by CI.

### Claude's Discretion (planner decides)

- Exact router state-machine topology (state names, transition triggers) — RECOMMENDED topology in §2.
- Safe-mode preview frame JSON shape — RECOMMENDED schema in §4.
- Console command whitelist entries (first cut) — RECOMMENDED list in §7.
- Message Log listening category filter — RECOMMENDED pattern in §8.
- CI runner host — GitHub-hosted Windows runners CANNOT build UE (no engine install). Self-hosted Windows runner is the only viable path. RECOMMENDED layout in §5.
- EV vendor selection — RECOMMENDED DigiCert (Azure Key Vault compatibility). Cost comparison in §6.

### Deferred Ideas (OUT OF SCOPE for Phase 2)

- MCP server hosting + full tool catalog → Phase 3/4 (Phase 2 ships console + log tools only as introspection primitives, not the full catalog)
- RAG / knowledge index → Phase 3
- Blueprint graph edits, asset ops, material ops, actor CRUD → Phase 4
- Meshy / ComfyUI / Substance computer-use orchestration → Phase 5
- Scene assembly, lighting from reference → Phase 6
- Video reference analyzer → Phase 7
- Fab listing + direct-download fallback → Phase 8 (EV cert ACQUIRED in Phase 2; FAB USED in Phase 8)
- Codex CLI integration → v1.1 (router is multi-backend-ready but Codex adapter not written)
- Anthropic direct API "bring-your-own-key" mode → v1.1
- Token quota estimator / pre-flight cost preview → v1.1 polish (Phase 2 ships basic rate-limit detection, not prediction)

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **PLUG-04** | Four-version CI matrix (UE 5.4 / 5.5 / 5.6 / 5.7) running from day one; no version-specific code merges without all four passing | §5 — self-hosted Windows runner + `NYRA::Compat::` shim + matrix workflow |
| **SUBS-01** | Claude Code CLI subprocess driver using `claude -p --output-format stream-json`, injecting NYRA MCP server via `--mcp-config`, with OAuth via `claude setup-token` | §1 — verified 2026 CLI surface + NDJSON schema + auth model |
| **SUBS-02** | Rate-limit and auth-drift detection; graceful fallback to Gemma on 429 / expired token, with clear user-facing status | §1.3 (detection strings) + §2 (router state machine) |
| **SUBS-03** | Agent router designed multi-backend (Claude-only in v1) so Codex drop-in for v1.1 requires no refactor | §2.5 — backend-abstract interface |
| **CHAT-02** | Subscription connection status UI surfacing which backends are active (Claude Code, Gemma local, computer-use) and which features each unlocks | §9 — state detection + UI pill states |
| **CHAT-03** | Every agent mutation wrapped in `FScopedTransaction` so Ctrl+Z works; in-flight task cancellable and computer-use subprocesses cleanly unwound | §3 — super-transaction pattern |
| **CHAT-04** | Safe-mode / dry-run — agent outputs its planned tool-call sequence before execution; user can approve, edit, or reject | §4 — preview frame contract |
| **ACT-06** | Console command execution via `GEngine->Exec` — cvars, `stat`, `showflag`, custom exec commands | §7 — whitelist-based MCP tool |
| **ACT-07** | Output Log / Message Log streaming to agent context with category filtering | §8 — FOutputDevice sink + FMessageLog listener |

</phase_requirements>

---

## Phase Goal Restated

NYRA's economic wedge — subprocess-driving the user's Claude Code CLI — goes live end-to-end with graceful Gemma fallback on rate-limit or auth failure. Every agent mutation is transactional (Ctrl+Z safe) and preview-gated (plan-first-by-default). The four-version CI matrix enforces compat from day one. EV cert is acquired and signs every binary. Console + Message Log introspection primitives ship here so every Phase 4+ tool can call them.

This is the phase where the phrase **"bring your own $20/mo subscription"** becomes a provable user experience.

---

## Project Constraints (from CLAUDE.md)

- GSD workflow enforcement: file-changing tools MUST go through `/gsd-quick`, `/gsd-debug`, or `/gsd-execute-phase`. Direct repo edits outside a GSD workflow are forbidden unless explicitly requested.
- Phase 1 established: `Plugins/NYRA/Source/{NyraEditor,NyraRuntime,NyraHost}/` layout; `TestProject/` as UE 5.6 test host; pytest + UE Automation Spec as the test frameworks.
- Stack block mirrors `.planning/research/STACK.md`; plans cite STACK for locked versions.

---

## Summary

**Primary recommendation:** Build a **backend-agnostic router** on the Phase 1 NyraHost WebSocket+JSON-RPC foundation. Add a Claude adapter that spawns `claude -p --bare --output-format stream-json --verbose --include-partial-messages --mcp-config <json> --session-id <uuid> --permission-prompt-tool <nyra_perm>` and translates the NDJSON event stream (system/init, stream_event, content_block_delta, system/api_retry, result) into NYRA's existing `chat/stream` notifications. Detect rate-limit and auth-drift purely from `system/api_retry` events (which already carry `error` category: `rate_limit`, `authentication_failed`, etc.) and transition the router state machine to Gemma fallback on retryable failures exceeding threshold. Wrap every agent mutation in a **manual `GEditor->BeginTransaction` / `EndTransaction` pair** at the session boundary with inner `FScopedTransaction` RAII objects per tool call (nested scopes coalesce into the outer via `UTransBuffer`'s reference-counted LIFO stack). Safe-mode preview is a new JSON-RPC method `chat/preview` that emits a structured plan frame which the Slate panel renders as an approvable card. The four-version CI matrix MUST run on a self-hosted Windows runner (GitHub-hosted runners cannot install UE); seed `NYRA::Compat::` with the drift points empirically discovered on first matrix run. EV code-signing cert is DigiCert-in-Azure-Key-Vault via `AzureSignTool` in GitHub Actions (~$700/yr EV + ~$5/mo Key Vault Premium SKU).

**Critical non-negotiables for the planner:**

1. **Never parse `claude --version` flags from stdout — always use `--output-format stream-json` for programmatic consumption.** Human-readable output is not a contract.
2. **The Claude adapter is a child of NyraHost (Python), not of UE.** UE never sees the Claude CLI process; NyraHost owns the subprocess, stream parsing, and error surfacing. Maintains Phase 1's crash-isolation invariant.
3. **`--bare` is REQUIRED for scripted calls per Anthropic's explicit recommendation** (will become `-p` default). BUT `--bare` does NOT read `CLAUDE_CODE_OAUTH_TOKEN` — so NYRA must NOT use `--bare` in subscription mode. Use `--bare` ONLY if the user later opts into API-key mode (v1.1 fallback). For v1 subscription mode: use `-p` without `--bare` so OAuth/keychain works.
4. **Rate-limit detection reads `system/api_retry` events, not stderr or exit codes.** `error` field is an enumerated string: `authentication_failed | billing_error | rate_limit | invalid_request | server_error | max_output_tokens | unknown`.
5. **Self-hosted Windows runner is the only CI option for UE builds.** `runs-on: windows-latest` is a no-go — UE cannot be installed on a GitHub-hosted runner in 6-minute build timeouts, and source builds require Epic EULA via registered GitHub ID.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Claude CLI subprocess lifecycle + NDJSON parsing | NyraHost (Python) | — | UE plugin must never see Claude tokens; NyraHost already owns subprocess discipline (Plan 10) |
| Router state machine (Claude ↔ Gemma transitions) | NyraHost (Python) | — | Backend abstraction lives with the adapters; UE consumes via existing WS method surface |
| MCP config file generation (`--mcp-config <json>`) | NyraHost (Python) | — | NyraHost already hosts session state; MCP config is a per-invocation file |
| Backend status surface (CHAT-02 pill) | NyraHost (Python, state source) | UE Slate panel (rendering) | State transitions originate in router; UE renders the pill via existing `diagnostics/*` notification channel |
| FScopedTransaction session super-transaction | UE (NyraEditor C++) | — | Transaction system lives in editor; NyraHost requests `tool_begin/tool_end` via WS but C++ owns the transaction scope |
| Safe-mode plan preview UI | UE Slate panel | NyraHost (produces plan) | Previews rendered in UE; plan JSON produced by router |
| Console command tool (`GEngine->Exec` wrapper) | UE (NyraEditor C++) | NyraHost (MCP tool registration) | Must run on GameThread; NyraHost adapter routes `console/exec` over WS |
| Output/Message Log tailing | UE (NyraEditor C++) | NyraHost (MCP tool + category filter) | `FOutputDevice` subclass is editor-module; NyraHost decides what to surface to Claude |
| Four-version compile + automation run | CI (self-hosted Windows runner) | — | UE builds don't fit on ephemeral runners; Epic's own CI pattern |
| `NYRA::Compat::` shim | UE (NyraEditor C++) | — | C++ ABI drift requires C++-side `#if ENGINE_MINOR_VERSION` guards |
| EV code-signing | CI (post-build step) | — | Binaries signed after compile but before packaging; workflow-level secret access required |

---

## Runtime State Inventory

> Phase 2 is not a rename/refactor phase. Omitted.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Claude Code CLI | SUBS-01 | USER-PROVIDED | v2.1.118+ (latest as of 2026-04-22) | None for v1; v1.1 API-key mode is the fallback |
| `claude setup-token` | SUBS-01 | Bundled with CLI | — | User re-runs `claude auth login` interactively |
| Ollama | Inherited D-18 | USER-OPTIONAL | 0.5+ | Bundled llama-server.exe (Phase 1 Plan 08) |
| UE 5.4 install | PLUG-04 CI | Must install on runner | 5.4.4 (latest 5.4 LTS) | Drop 5.4 from matrix (PROJECT.md-blocking) |
| UE 5.5 install | PLUG-04 CI | Must install on runner | 5.5.4 | Drop 5.5 from matrix (PROJECT.md-blocking) |
| UE 5.6 install | PLUG-04 CI | Must install on runner | 5.6.1 | Already on Phase 1 dev host |
| UE 5.7 install | PLUG-04 CI | Must install on runner | 5.7.x | UE 5.7 presumed-stable 2026-04; defer one matrix slot if not-yet-GA |
| Windows 10/11 CI machine | PLUG-04 | Must provision | — | None — GitHub-hosted runners cannot install UE |
| Azure Key Vault Premium SKU | DIST-03 EV cert | Must acquire | — | USB HSM token (SafeNet 5110+FIPS) — less CI-friendly |
| DigiCert EV cert | DIST-03 | Must purchase | 1-year (new industry cap since Feb 2026) | Sectigo EV cheaper BUT not Azure Key Vault compatible |
| AzureSignTool | DIST-03 CI signing | Install in runner | Latest | Upgrade to Microsoft Trusted Signing (~$10/mo) post-launch |

**Missing dependencies with no fallback:**
- Self-hosted Windows runner with ≥4 UE versions installed. Planner MUST include the runner provisioning as a Wave 0 deliverable (either dev-host-as-runner or a dedicated Windows machine).
- DigiCert EV cert acquisition takes 1-3 business days of identity verification. Planner MUST include the purchase as a blocking pre-phase task for DIST-03 work (can run in parallel with compat-shim work).

**Missing dependencies with fallback:**
- UE 5.7 may not be GA at phase start — planner tolerates deferring 5.7 matrix cell if 5.7 is <4 weeks post-release. Document as compat-shim gap.

---

## 1. Claude Code CLI surface (live-verified 2026-04-22 flags + NDJSON schema + error detection)

### 1.1 Verified CLI surface

All items below are verified against `code.claude.com/docs/en/cli-reference` (fetched 2026-04-22). Quoted fragments are copy-preserved from official docs. `[VERIFIED: code.claude.com/docs/en/cli-reference]` unless otherwise noted.

**Flags NYRA uses:**

| Flag | Purpose | Notes |
|------|---------|-------|
| `-p` / `--print` | Run non-interactively and exit. Prints response without interactive mode. | Required for subprocess driving. [VERIFIED] |
| `--output-format <text\|json\|stream-json>` | Control output format. `stream-json` is newline-delimited JSON for real-time streaming. | NYRA MUST use `stream-json`. [VERIFIED] |
| `--verbose` | Shows full turn-by-turn output. | REQUIRED with `stream-json`. The jq example in the docs uses `--verbose`. [VERIFIED] |
| `--include-partial-messages` | Include partial streaming events. **Requires `--print` and `--output-format stream-json`.** | REQUIRED for token-by-token UI streaming. [VERIFIED] |
| `--input-format <text\|stream-json>` | Input format for print mode. | NYRA sends the prompt as a command-line argument; `--input-format` stays at default `text`. For multi-turn programmatic sessions, use `stream-json` input — but Phase 2 v1 ships single-prompt invocations + `--resume` for continuity. [VERIFIED] |
| `--mcp-config <json-file-or-string>` | Load MCP servers from JSON file or strings. | NYRA writes a per-session JSON file to a temp path; the file registers the NyraHost MCP server (stdio transport) so Claude can call NYRA's UE-native tools. [VERIFIED] |
| `--strict-mcp-config` | Only use MCP servers from `--mcp-config`, ignoring other MCP configurations. | RECOMMENDED to prevent the user's home `.mcp.json` from injecting unexpected tools into NYRA turns. [VERIFIED] |
| `--session-id <uuid>` | Use a specific session ID (must be valid UUID). | NYRA generates a UUID per conversation; enables `--resume` by ID. [VERIFIED] |
| `--resume <id-or-name>` / `-r` | Resume a specific session by ID or name. | NYRA uses this for conversation continuity across turns within the same user session. [VERIFIED] |
| `--fork-session` | When resuming, create a new session ID instead of reusing. | Useful for "re-run this prompt but don't mutate history" UX. [VERIFIED] |
| `--model <alias-or-full>` | Set model. `sonnet`, `opus`, or full name e.g. `claude-opus-4-7`. | Router defaults to `opus` (Opus 4.7) per STACK.md. [VERIFIED] |
| `--permission-mode <mode>` | `default`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`. | **NYRA uses `dontAsk`** because NYRA provides its own preview+approve UI (CHAT-04). `dontAsk` denies anything not in permissions.allow or the read-only command set — which for NYRA's MCP tools means NYRA approves the tools up-front via `--allowedTools` or settings, then dontAsk prevents accidental destructive calls. See §4. [VERIFIED] |
| `--permission-prompt-tool <mcp-tool>` | MCP tool to handle permission prompts in non-interactive mode. | NYRA exposes an MCP tool `nyra_permission_gate` that forwards prompts to the UE Slate panel (CHAT-04 preview-and-approve). This is the canonical integration point for safe-mode. [VERIFIED] |
| `--allowedTools <list>` | Tools that execute without prompting. | NYRA sets this to the NYRA MCP tool whitelist (read-only UE tools, no-preview-needed tools). [VERIFIED] |
| `--no-session-persistence` | Disable session persistence (print mode only). | Useful for one-shot diagnostics; NOT used for normal chat turns. [VERIFIED] |
| `--debug-file <path>` | Write debug logs to a specific file. Implicitly enables debug mode. | Planner SHOULD wire this to `Saved/NYRA/logs/claude-debug-<session-id>.log` for support triage. [VERIFIED] |
| `--max-budget-usd` | Max dollar amount to spend on API calls before stopping (print mode only). | OFF-PATH for subscription driving (no dollars charged). Useful only in v1.1 API-key mode. [VERIFIED] |

**Commands NYRA uses:**

| Command | Purpose | Notes |
|---------|---------|-------|
| `claude setup-token` | Generate long-lived 1-year OAuth token. **Prints token to terminal without saving.** Requires Pro/Max/Team/Enterprise plan. | Token must be copied by user into `CLAUDE_CODE_OAUTH_TOKEN` env var. Token is **scoped to inference only** and cannot establish Remote Control sessions. [VERIFIED] |
| `claude auth status` | Show auth status as JSON. Use `--text` for human-readable. **Exits 0 if logged in, 1 if not.** | **NYRA uses this as the health-check primitive** for subscription-connection state (CHAT-02). [VERIFIED] |
| `claude auth login` | Interactive browser OAuth flow. `--console` flag for API-key billing instead of subscription. | NYRA surfaces a "Sign into Claude" button that opens a terminal running `claude auth login`. NYRA does NOT capture the token; the CLI writes to `~/.claude/.credentials.json` (Windows) with user-profile ACLs. [VERIFIED] |
| `claude auth logout` | Log out. | Offered in NYRA settings. [VERIFIED] |
| `claude --version` / `-v` | Output version number. | Used at NyraHost startup to pin a tested-version range. [VERIFIED] |

**Bare mode caveat — CRITICAL [VERIFIED]:**
> "[Bare mode](/en/headless#start-faster-with-bare-mode) does not read `CLAUDE_CODE_OAUTH_TOKEN`. If your script passes `--bare`, authenticate with `ANTHROPIC_API_KEY` or an `apiKeyHelper` instead."

**Implication:** NYRA's subscription mode (v1) MUST NOT use `--bare`. Bare skips OAuth and keychain reads. v1.1's API-key mode CAN use `--bare` for faster startup.

### 1.2 Authentication precedence order [VERIFIED: code.claude.com/docs/en/authentication]

When multiple credentials are present, Claude Code chooses in this exact order:

1. Cloud provider credentials (Bedrock/Vertex/Foundry) when the corresponding `CLAUDE_CODE_USE_*` env var is set.
2. `ANTHROPIC_AUTH_TOKEN` env var (Bearer header).
3. `ANTHROPIC_API_KEY` env var (X-Api-Key header). **In interactive mode, user is prompted once; in `-p` mode, always used when present.**
4. `apiKeyHelper` script output.
5. `CLAUDE_CODE_OAUTH_TOKEN` env var (long-lived token from `claude setup-token`). **This is NYRA's primary path for CI/unattended.**
6. Subscription OAuth credentials from `/login` (default for Pro/Max/Team/Enterprise).

**CRITICAL trap [VERIFIED]:**
> "If you have an active Claude subscription but also have `ANTHROPIC_API_KEY` set in your environment, the API key takes precedence once approved. This can cause authentication failures if the key belongs to a disabled or expired organization."

**NYRA mitigation:** before spawning `claude -p`, NyraHost MUST scrub `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN` from the child-process environment if the user has declared subscription mode. Surface a warning banner if the user has both set.

### 1.3 stream-json NDJSON event schema

Source: `code.claude.com/docs/en/headless` (verified 2026-04-22) + Anthropic Messages API streaming spec (`platform.claude.com/docs/en/build-with-claude/streaming`).

**Stream structure** — one JSON object per line, consumed as NDJSON:

**Event #1: `system` with `subtype: "init"`** [VERIFIED]
> "The `system/init` event reports session metadata including the model, tools, MCP servers, and loaded plugins. It is the first event in the stream unless `CLAUDE_CODE_SYNC_PLUGIN_INSTALL` is set, in which case `plugin_install` events precede it."

```json
{"type":"system","subtype":"init","session_id":"550e8400-e29b-41d4-a716-446655440000","model":"claude-opus-4-7","tools":["Read","Edit","Bash","mcp__nyra__spawn_actor", ...],"mcp_servers":[{"name":"nyra","status":"connected"}],"plugins":[{"name":"foo","path":"..."}],"plugin_errors":[]}
```

**Event #2..N: `stream_event` (when `--include-partial-messages`)** [VERIFIED — NDJSON shape documented; inner `event` shape is the Messages API streaming spec]

The outer envelope is Claude Code's wrapper; the inner `event` is the Anthropic Messages API streaming event.

```jsonc
// message_start
{"type":"stream_event","session_id":"<uuid>","uuid":"<ev_uuid>","event":{"type":"message_start","message":{"id":"msg_014p7gG3wDgGV9EUtLvnow3U","type":"message","role":"assistant","model":"claude-opus-4-7","content":[],"stop_reason":null,"usage":{"input_tokens":472,"output_tokens":2}}}}

// content_block_start (text)
{"type":"stream_event","event":{"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}}

// content_block_delta (text_delta) — one per chunk
{"type":"stream_event","event":{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}}

// content_block_start (tool_use)
{"type":"stream_event","event":{"type":"content_block_start","index":1,"content_block":{"type":"tool_use","id":"toolu_01ABC...","name":"mcp__nyra__spawn_actor","input":{}}}}

// content_block_delta (input_json_delta) — partial JSON of tool input
{"type":"stream_event","event":{"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"{\"class\":\"Point"}}}

// content_block_stop
{"type":"stream_event","event":{"type":"content_block_stop","index":1}}

// message_delta (updates stop_reason + usage)
{"type":"stream_event","event":{"type":"message_delta","delta":{"stop_reason":"tool_use"},"usage":{"output_tokens":42}}}

// message_stop
{"type":"stream_event","event":{"type":"message_stop"}}
```

**Event: `assistant` (complete message, when partial-messages NOT enabled)** [VERIFIED]

Without `--include-partial-messages`, Claude Code emits complete assistant messages rather than the StreamEvent granularity. NYRA uses partial-messages, so this is seen only as a fallback.

**Event: `user` (tool_result events)** — Claude Code emits a `user` message carrying `tool_result` blocks when NYRA's MCP tool returns.

**Event: `system` with `subtype: "api_retry"` — CRITICAL FOR RATE-LIMIT / AUTH DETECTION** [VERIFIED]

> "When an API request fails with a retryable error, Claude Code emits a `system/api_retry` event before retrying. You can use this to surface retry progress or implement custom backoff logic."

Schema [VERIFIED, quoted fields exactly]:

| Field | Type | Description |
|-------|------|-------------|
| `type` | `"system"` | message type |
| `subtype` | `"api_retry"` | identifies this as a retry event |
| `attempt` | integer | current attempt number, starting at 1 |
| `max_retries` | integer | total retries permitted |
| `retry_delay_ms` | integer | milliseconds until the next attempt |
| `error_status` | integer or null | HTTP status code, or `null` for connection errors with no HTTP response |
| `error` | string | **error category**: `authentication_failed`, `billing_error`, `rate_limit`, `invalid_request`, `server_error`, `max_output_tokens`, or `unknown` |
| `uuid` | string | unique event identifier |
| `session_id` | string | session the event belongs to |

**NYRA uses this event as the SINGLE SOURCE OF TRUTH for backend health transitions.** The `error` field enum directly maps to router state transitions (see §2).

**Event: `result` (final event for the turn)** — Contains `result` (text or structured output), `session_id`, `usage`, and `stop_reason`. This is the turn-termination signal. NYRA's router emits a final `chat/stream` with `done:true` after seeing `result`.

### 1.4 Exit codes and signals

- `claude auth status` exits **0 if logged in, 1 if not** [VERIFIED]. NYRA uses this for CHAT-02 state detection.
- `claude -p` exits 0 on success. Non-zero on error (documented per-flag: `--max-turns` exits error on limit hit).
- **Cancellation:** NYRA sends SIGTERM (Windows: `GenerateConsoleCtrlEvent(CTRL_C_EVENT)`) to the child process. The CLI cleanly finalizes the session file. NYRA then emits a `chat/stream` `done:true, cancelled:true` notification (already wired in Phase 1 Plan 10).

### 1.5 Subscription tier + quota detection

Primary method: parse `claude auth status` JSON output. Fields documented to include auth method, account type, and login state [VERIFIED path; exact field names require Phase 2 Wave 0 empirical capture — schema is stable but subfield names not published].

Quota detection for display (CHAT-02 "light/medium/heavy usage" pill):
- **Primary:** read `~/.claude/projects/**/*.jsonl` session files. Each API response has a `usage` object: `cache_read_input_tokens`, `cache_creation_input_tokens`, `input_tokens`, `output_tokens` [VERIFIED: GitHub issue + community tools like `ccusage`].
- **In-CLI:** `/usage` slash command exists in interactive mode [VERIFIED]. Not available in `-p`.
- **Signal, not prediction:** NYRA uses `system/api_retry` with `error: "rate_limit"` as the authoritative signal that the user is rate-limited. Prediction ("your next job will cost X% of window") is deferred to v1.1 per the deferred list.

### 1.6 MCP config file shape

NYRA writes a per-session MCP config to `%LOCALAPPDATA%/NYRA/mcp-configs/<session-id>.json`:

```json
{
  "mcpServers": {
    "nyra": {
      "command": "C:\\path\\to\\Plugin\\Binaries\\Win64\\NyraHost\\cpython\\python.exe",
      "args": ["-m", "nyrahost.mcp_server", "--handshake-file", "C:\\Users\\...\\NYRA\\handshake-<pid>.json"],
      "env": {
        "NYRA_SESSION_ID": "<uuid>",
        "NYRA_CONVERSATION_ID": "<uuid>"
      }
    }
  }
}
```

`--strict-mcp-config` ensures no user-level `.mcp.json` leaks into the turn. The MCP server process is spawned BY Claude, not by NYRA — but it connects BACK to the NyraHost WebSocket (via handshake file) so UE-side tools remain routed through the existing JSON-RPC surface. This is the canonical stdio-MCP-talks-to-NyraHost pattern (Phase 3 deepens the MCP tool catalog; Phase 2 ships only `nyra_permission_gate`, `nyra_console_exec`, `nyra_output_log_tail`).

**Confidence:** HIGH on CLI surface (verified docs). MEDIUM-HIGH on NDJSON schema (outer wrapper verified, inner event shapes come from Messages API spec which is stable). MEDIUM on `claude auth status` exact JSON schema (Wave 0 must empirically capture).

---

## 2. Router state machine + Gemma fallback policy

### 2.1 States

```
                    ┌─────────────────────────────────────────┐
                    │                                          │
                    ▼                                          │
            [ Disconnected ]                                   │
                    │ claude auth status = ok                  │
                    │                                          │
                    ▼                                          │
            [ ClaudeReady ] ◄──────── api_retry(rate_limit)   │
                    │ │                 exhausted              │
           chat/send│ │                                        │
                    │ └─────────────► [ ClaudeRateLimited ]────┘
                    ▼                         │
            [ ClaudeStreaming ]               │
                    │                         │
          done:true │                         ▼
                    │                 [ GemmaFallback ]
                    ▼                         │
            [ ClaudeReady ]                   │  retry after retry_delay_ms
                                              │  AND user approves re-try
                                              ▼
                                      [ ClaudeReady ] (retried)

   ─────────────── independent state dimension ───────────────

          [ PrivacyMode: Gemma-only ]  (user toggle; forces Gemma,
                                         blocks egress except to
                                         user's own claude CLI which
                                         is NOT spawned in this mode)

          [ AuthDrift ]  (claude auth status exit code 1, OR
                          api_retry error=authentication_failed)
```

### 2.2 Concrete state definitions

| State | Enter conditions | Exit conditions | UI pill (CHAT-02) |
|-------|-----------------|----------------|-------------------|
| `Disconnected` | Initial; or `claude` binary not found on PATH | `claude auth status` exits 0 AND binary present | Grey: "Claude: not signed in" |
| `ClaudeReady` | Auth check passed | `chat/send` → `ClaudeStreaming`; auth drift → `AuthDrift`; privacy toggle → `PrivacyMode` | Green: "Claude Pro/Max connected" |
| `ClaudeStreaming` | `chat/send` with `backend=claude` | `result` event seen → `ClaudeReady`; `api_retry` exhausted → fallback decision | Blue spinner: "Claude thinking…" |
| `ClaudeRateLimited` | `api_retry` with `error=rate_limit` AND `attempt == max_retries` | `retry_delay_ms` elapsed AND user clicks retry → `ClaudeReady`; user approves fallback → `GemmaFallback` | Yellow: "Claude rate-limited — resume in 4h 12m, or use local Gemma" |
| `GemmaFallback` | User approved fallback from `ClaudeRateLimited` OR `AuthDrift` OR network offline | User explicitly exits; OR Claude readiness confirmed AND user switches back | Orange: "Using local Gemma (fallback)" |
| `AuthDrift` | `claude auth status` exits 1 mid-session; or `api_retry` with `error=authentication_failed` | User re-runs `claude auth login` | Red: "Claude signed out — sign in again" |
| `PrivacyMode` | User toggles "Privacy Mode: Gemma-only" | User toggles off | Purple: "Privacy Mode (Gemma, no egress)" |

### 2.3 Transition triggers (mapped to Phase 1 infrastructure)

- **Health probe on startup:** NyraHost runs `claude auth status` as a subprocess at plugin load and caches the result for 5 minutes (mirrors `apiKeyHelper`'s 5-minute TTL behaviour). Re-runs on every `chat/send` in `Disconnected` state.
- **api_retry event mid-stream:** Router reads the `error` field enum and branches:
  - `rate_limit` → count attempts; if exhausted, emit `chat/stream` error-frame (error code `-32003 rate_limit` already allocated in Phase 1 D-11) with remediation text: "Claude rate-limited. Retry in N minutes, or switch to local Gemma ([Switch])." State → `ClaudeRateLimited`.
  - `authentication_failed` → State → `AuthDrift`. Remediation: "Claude session expired. Run `claude auth login` in a terminal and retry."
  - `billing_error` → state stays but surface error banner with remediation pointing to billing portal.
  - `server_error` / `unknown` → attempt N < 3 is silent retry; attempt ≥ 3 surfaces error.
  - `max_output_tokens` → router transparently continues with a follow-up turn.
- **User cancel → SIGTERM:** existing `chat/cancel` notification path (Plan 10). Router guarantees a `chat/stream` `done:true, cancelled:true` final frame.
- **Privacy Mode toggle:** UE Slate panel sends new `session/set-mode` JSON-RPC request; NyraHost router flips mode and refuses any Claude adapter spawns.

### 2.4 Privacy Mode egress policy — EXACT SEMANTICS

"All egress blocked except user's own CLI" means:

- **In Privacy Mode, NYRA's router refuses to spawn the `claude` CLI.** There is no "your CLI only" egress because the CLI is what egresses. Privacy Mode is LOCAL-ONLY: only Gemma + NyraHost.
- NyraHost MUST NOT call Meshy/ComfyUI/Substance APIs in Privacy Mode (affects Phase 5).
- NyraHost MUST NOT fetch RAG index updates from GitHub releases in Privacy Mode (affects Phase 3).
- Attachment HASHES and NAMES are OK to log locally but MUST NOT leave the machine.
- MCP tool calls from Claude are impossible in Privacy Mode (because Claude is not spawned), so the MCP-over-stdio path is inert.
- The Gemma download (if not already downloaded) is BLOCKED in Privacy Mode — user must exit Privacy Mode to download, or pre-download via `claude` not yet being asked.

**UI implication:** Privacy Mode toggle must show a one-time disclaimer: "Privacy Mode disables Claude, all external APIs, and RAG updates. Gemma must already be downloaded."

### 2.5 Multi-backend abstraction for v1.1 Codex drop-in (SUBS-03)

Backend abstraction interface (Python, in NyraHost):

```python
# nyrahost/backends/base.py
class AgentBackend(abc.ABC):
    name: str  # "claude" | "gemma" | "codex" (v1.1)

    @abc.abstractmethod
    async def send(
        self,
        conversation_id: str,
        req_id: str,
        content: str,
        attachments: list[AttachmentRef],
        mcp_config_path: Path | None,
        on_event: Callable[[BackendEvent], Awaitable[None]],
    ) -> None:
        """Emit BackendEvent objects via on_event; must end with a Done event."""

    @abc.abstractmethod
    async def cancel(self, req_id: str) -> None: ...

    @abc.abstractmethod
    async def health_check(self) -> HealthState: ...
```

`BackendEvent` is a tagged union: `Delta(text)`, `ToolUse(id, name, input_json)`, `ToolResult(id, output)`, `Done(usage, stop_reason)`, `Error(code, message, remediation, retryable)`, `Retry(attempt, delay_ms, error_category)`.

The router reads `BackendEvent` and translates to Phase 1's existing `chat/stream` JSON-RPC notifications. **v1.1 Codex adapter writes a `CodexBackend(AgentBackend)` class and adds it to the backend registry.** No router or UE-side changes required.

**Confidence:** MEDIUM on state-machine completeness (novel design for this project; planner should empirically stress-test with intentional rate-limit + auth-drift fixtures in Wave 0). HIGH on api_retry event being the right signal source.

---

## 3. FScopedTransaction super-transaction pattern

### 3.1 `UTransBuffer` nesting semantics [VERIFIED via search: Epic Developer Community Forums + community tutorials]

Key facts:

- When `BeginTransaction` is called while another transaction is active, UE does **NOT** create a new independent transaction. It increments an internal reference count on the outermost (session-level) transaction.
- All `Modify()` calls from nested scopes get rolled into that single outermost transaction.
- `EndTransaction` decrements the count. Only when the count reaches zero is the transaction finalized and pushed onto the undo buffer.
- This makes the outermost `FScopedTransaction` (or outermost `BeginTransaction` call) the **super-transaction**. Ctrl+Z undoes everything inside it as one atomic unit.

### 3.2 Recommended pattern for NYRA

**Session boundary: manual `BeginTransaction` / `EndTransaction`** — NOT a long-lived `FScopedTransaction` member. Rationale: exception paths, early returns, and WS disconnects are easier to handle with explicit `CancelTransaction(Index)` on failure.

```cpp
// NyraEditor/Private/Transactions/FNyraSessionTransaction.cpp
class FNyraSessionTransaction
{
public:
    void Begin(const FString& SessionSummary)
    {
        if (!GEditor || !GEditor->Trans) { return; }
        const FText Desc = FText::Format(
            LOCTEXT("NyraSessionFmt", "NYRA: {0}"),
            FText::FromString(SessionSummary));
        TransactionIndex = GEditor->BeginTransaction(Desc);
    }

    void End()
    {
        if (!GEditor || !GEditor->Trans) { return; }
        GEditor->EndTransaction();
        TransactionIndex = INDEX_NONE;
    }

    void Cancel()
    {
        if (!GEditor || !GEditor->Trans) { return; }
        if (TransactionIndex != INDEX_NONE)
        {
            GEditor->CancelTransaction(TransactionIndex);
            TransactionIndex = INDEX_NONE;
        }
    }

private:
    int32 TransactionIndex = INDEX_NONE;
};
```

**Inner tool call: RAII `FScopedTransaction`** — coalesces into the outer via refcount.

```cpp
// Every tool invocation during a NYRA session:
{
    const FScopedTransaction Inner(LOCTEXT("SpawnActor", "Spawn Actor"));
    Target->Modify();  // Called BEFORE mutating state
    // ... mutate ...
}
// On scope exit, ref-count decrements; outer transaction still open.
```

### 3.3 Rules the planner MUST encode [VERIFIED]

1. **Objects must be flagged `RF_Transactional`** before any `Modify()` call. Pattern: `NewActor->SetFlags(RF_Transactional)` immediately after `SpawnActor`.
2. **`Modify()` must be called INSIDE the transaction scope, BEFORE mutating state.** Redundant per-scope `Modify()` calls are cheap (recorded only once per object per transaction).
3. **Guard with `GEditor && GEditor->Trans`** for `-game` / commandlet safety. NYRA is editor-only so this is a defensive check.
4. **Implement `PostEditUndo()` / `PostTransacted()`** on any NYRA custom UObjects to refresh derived state and broadcast change delegates.
5. **DO NOT open `FScopedTransaction` inside a delegate firing mid-event** (e.g., `OnCheckedStateChange`). The scope begins after the trigger, causing inconsistent undo. Open the transaction BEFORE the user-facing action that triggers the delegate.
6. **Interactive vs transactable changes:** for slider drags / spinner ticks where NYRA emits incremental updates, use `EPropertyValueSetFlags::InteractiveChange | EPropertyValueSetFlags::NotTransactable` per-tick, then a single final transactable commit. Prevents undo spam.
7. **PIE suspends the transaction system.** NYRA must NOT accept tool calls during Play-In-Editor. Router refuses `chat/send` with a remediation banner if PIE is active.
8. **Cancelling an inner `FScopedTransaction::Cancel()` effectively cancels the outer.** Do NOT use inner Cancel for retry logic. For tool-call failure: emit the error on the WS channel and let the router decide at session-boundary whether to roll back the entire session.

### 3.4 Cross-version stability (UE 5.4-5.7)

The `FScopedTransaction` constructor signature and `UTransBuffer` LIFO stack model are stable across UE 5.4 → 5.7 [INFERRED from forum discussion; no breaking changes surfaced in 5.4/5.5/5.6/5.7 release notes reviewed]. No `NYRA::Compat::` shim entry needed.

### 3.5 Interaction with Blueprint graph edits (Phase 4 dependency)

When Phase 4 ships Blueprint node add/remove/rewire, each `UEdGraphNode` modification must be inside a `FScopedTransaction` with `Modify()` called on the `UEdGraph` and the node. Use `FBlueprintEditorUtils::MarkBlueprintAsModified` after graph edits to trigger recompile hook. Phase 2 RESEARCH ONLY validates the session-scope super-transaction pattern; Phase 4 RESEARCH will go deeper on per-node BP edits.

### 3.6 Cancel-button unwind (CHAT-03 requirement)

When user clicks Cancel mid-session:

1. Panel sends `chat/cancel` notification (Phase 1 wired). NyraHost SIGTERMs the `claude` subprocess.
2. NyraHost router emits a `chat/stream` `done:true, cancelled:true` frame.
3. UE `FNyraSessionTransaction::Cancel()` — rolls back the entire super-transaction.
4. For computer-use subprocesses (Phase 5): router SIGTERMs any child process it spawned (Playwright, Claude Desktop computer-use session if ever wired). Phase 2 stubs this — Phase 5 fills in per-tool cleanup.

**Confidence:** HIGH on the pattern (well-established Epic source + community convergence). MEDIUM on per-version stability claim — no breaking changes found in docs but planner's CI matrix (§5) will empirically confirm.

---

## 4. Safe-mode / dry-run preview contract (JSON shape + UI flow)

### 4.1 Contract mechanics

Two integration paths exist; the planner RECOMMENDED choice is **path B**:

**Path A: Use Claude Code's `--permission-mode plan`.** Claude enters a planning loop and emits a plan assistant message before tool execution. NYRA parses the assistant text for the plan. Downside: plan is natural language, not structured JSON. The `--json-schema` flag does not stream partial JSON tokens ([known limitation, Anthropic issue #15511](https://github.com/anthropics/claude-code/issues/15511)).

**Path B (RECOMMENDED): Use `--permission-prompt-tool nyra_permission_gate`.** NYRA exposes an MCP tool called `nyra_permission_gate` that Claude is REQUIRED to call before any destructive MCP tool. The tool's input schema forces Claude to provide a structured plan that NYRA validates + surfaces to the user. User approves/rejects via the Slate panel, and the response determines whether Claude proceeds.

Path B is the canonical Anthropic-recommended pattern for third-party approval UIs and produces structured JSON from day one.

### 4.2 `nyra_permission_gate` MCP tool schema (CHAT-04 contract)

```json
{
  "name": "nyra_permission_gate",
  "description": "Request user approval for a planned sequence of UE mutations. MUST be called before any destructive tool (spawn_actor, edit_blueprint, modify_material, delete_*).",
  "inputSchema": {
    "type": "object",
    "required": ["summary", "steps"],
    "properties": {
      "summary": {"type": "string", "description": "One-sentence user-facing description of what this batch does."},
      "steps": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["tool", "args", "rationale"],
          "properties": {
            "tool": {"type": "string", "description": "MCP tool name, e.g., mcp__nyra__spawn_actor"},
            "args": {"type": "object", "description": "Args the tool will be called with."},
            "rationale": {"type": "string", "description": "Why this step is needed."},
            "risk": {"type": "string", "enum": ["read-only", "reversible", "destructive", "irreversible"]}
          }
        }
      },
      "estimated_duration_seconds": {"type": "number"},
      "affects_files": {"type": "array", "items": {"type": "string"}, "description": "Asset / file paths that will change."}
    }
  }
}
```

### 4.3 Preview frame over the WS (UE-side)

NyraHost router emits a new JSON-RPC notification:

```json
{
  "jsonrpc": "2.0",
  "method": "plan/preview",
  "params": {
    "conversation_id": "<uuid>",
    "req_id": "<uuid>",
    "preview_id": "<uuid>",
    "summary": "Spawn a point light + tint the floor material warm for a golden-hour look",
    "steps": [
      {
        "tool": "mcp__nyra__spawn_actor",
        "args": {"class": "PointLight", "location": [300, 0, 200], "intensity": 15000, "color": [1.0, 0.75, 0.5]},
        "rationale": "Key light warm tone matching golden hour",
        "risk": "reversible"
      },
      {
        "tool": "mcp__nyra__set_material_param",
        "args": {"mic_path": "/Game/Env/Floor_Inst", "param": "Tint", "value": [0.95, 0.85, 0.7]},
        "rationale": "Warm bounce simulation",
        "risk": "reversible"
      }
    ],
    "estimated_duration_seconds": 2.4,
    "affects_files": ["/Game/Env/Floor_Inst"]
  }
}
```

UE panel renders a `SNyraPreviewCard` Slate widget:

- Summary at top, large font.
- Expandable step list, each step showing tool name, rationale, risk pill (color-coded), args JSON collapsed-by-default.
- Three buttons: `[Approve]`, `[Reject]`, `[Edit]` (edit opens the plan JSON in a text editor for user modification in v1 — advanced).
- Auto-approval checkbox: "Auto-approve read-only steps for this session" (persisted per-session, not per-project).

UE replies with a new JSON-RPC request:

```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "method": "plan/decision",
  "params": {
    "preview_id": "<uuid>",
    "decision": "approve" | "reject" | "edit",
    "edited_plan": { /* only if decision=edit */ },
    "auto_approve_read_only_this_session": true
  }
}
```

NyraHost returns the decision to Claude as the `nyra_permission_gate` tool result. Claude proceeds (approve) or abandons (reject) the plan.

### 4.4 Streaming partial previews

For long plans (>10 steps): Claude emits the permission_gate tool_use block incrementally. NyraHost buffers the partial JSON from `input_json_delta` events and only emits `plan/preview` to UE when the block is COMPLETE (content_block_stop). This prevents the UE panel from re-rendering a plan card mid-build.

### 4.5 Read-only whitelist fast-path

Tools with `risk: read-only` (console stat queries, log tails, asset-registry fuzzy searches) bypass the preview gate IF user has opted into "Auto-approve read-only this session". This keeps the experience fluid for knowledge queries while preserving the hard gate for destructive ops.

### 4.6 `plan-first-by-default` enforcement

Router ALWAYS passes `--permission-prompt-tool nyra_permission_gate` to Claude. Claude's system prompt (NYRA's internal MCP tool description) instructs: "Before calling any tool with risk ≥ reversible, call `nyra_permission_gate` with the full plan." NYRA also sets `--permission-mode dontAsk` so Claude cannot fall back to its own prompt UI.

**Confidence:** HIGH on the `--permission-prompt-tool` mechanism (documented CLI flag). MEDIUM on partial JSON buffering being reliable — Anthropic issue #15511 flags stream partial JSON as a known limitation for `--json-schema`; `input_json_delta` itself is in the Messages API spec and works, but deep-nesting races are worth empirical testing in Wave 0.

---

## 5. Four-version UE CI matrix (drift hotspots + compat shim + runner choice)

### 5.1 Why self-hosted Windows runner is the ONLY option

[VERIFIED via WebSearch 2026-04-22]

- GitHub-hosted runners (`windows-latest`) do not have UE installed and can't install it inside a 6-hour job (full UE source build takes 4+ hours; binary install requires Epic Games Launcher with signed-in account).
- Engine source builds require EULA acceptance via Epic-registered GitHub ID.
- Typical UE CI pattern: provision a dedicated Windows VM (or dev machine) with UE 5.4/5.5/5.6/5.7 pre-installed under `C:\EpicGames\UE_5.X\`, register it as a self-hosted runner labeled `self-hosted, Windows, unreal`.
- Community caveat: repository checkout path must stay short (< 50 chars) because GitHub Actions Windows runners build to `C:\A\_work\<reponame>\<reponame>\` and UE's own path-length issues cascade from there.

### 5.2 Runner provisioning (Wave 0 deliverable)

1. Provision one Windows 11 machine (can be the solo dev's own workstation as primary runner; budget a backup cloud Windows VM for redundancy).
2. Install UE 5.4.4, 5.5.4, 5.6.1, and 5.7.x via Epic Games Launcher under `C:\EpicGames\UE_5.X\`.
3. Install Visual Studio 2022 Community with C++ game dev workload.
4. Install Python 3.12 (for pytest runs) + pip install requirements-dev.lock.
5. Register as self-hosted runner with label `self-hosted,Windows,unreal`.
6. Verify each UE install can `RunUAT.bat BuildCookRun -project=...` on the empty NYRA plugin in its shell state.

### 5.3 Matrix workflow shape

```yaml
# .github/workflows/plugin-matrix.yml
name: Plugin Multi-Version CI
on:
  push:
    branches: [main]
  pull_request:

jobs:
  compile-and-test:
    runs-on: [self-hosted, Windows, unreal]
    strategy:
      fail-fast: false  # all versions continue even if one fails
      matrix:
        ue-version: ['5.4', '5.5', '5.6', '5.7']
    steps:
      - uses: actions/checkout@v4
        with:
          lfs: true
      - name: Build plugin against UE ${{ matrix.ue-version }}
        shell: cmd
        run: |
          "C:\EpicGames\UE_${{ matrix.ue-version }}\Engine\Build\BatchFiles\RunUAT.bat" ^
            BuildPlugin ^
            -Plugin="%GITHUB_WORKSPACE%\TestProject\Plugins\NYRA\NYRA.uplugin" ^
            -Package="%GITHUB_WORKSPACE%\Artifacts\UE_${{ matrix.ue-version }}" ^
            -TargetPlatforms=Win64 ^
            -Unattended -NoP4
      - name: Run UE Automation Spec headless (UE ${{ matrix.ue-version }})
        shell: cmd
        run: |
          "C:\EpicGames\UE_${{ matrix.ue-version }}\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" ^
            "%GITHUB_WORKSPACE%\TestProject\TestProject.uproject" ^
            -ExecCmds="Automation RunTests Nyra;Quit" ^
            -unattended -nopause -nullrhi ^
            -testexit="Automation Test Queue Empty" ^
            -log=NyraAutomation-UE${{ matrix.ue-version }}.log
      - name: Upload artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: nyra-plugin-ue-${{ matrix.ue-version }}
          path: |
            Artifacts/UE_${{ matrix.ue-version }}/
            NyraAutomation-UE${{ matrix.ue-version }}.log
  pytest-single:
    runs-on: [self-hosted, Windows, unreal]
    steps:
      - uses: actions/checkout@v4
      - name: Python tests (version-agnostic)
        shell: cmd
        run: |
          cd TestProject\Plugins\NYRA\Source\NyraHost
          python -m pytest -v
```

**Critical settings:**
- `fail-fast: false` — one version failing does not cancel others. [VERIFIED]
- `-nullrhi` — headless UE automation without GPU. Cuts CI memory footprint.
- `BuildPlugin` target (not `BuildCookRun`) — we build the plugin binary, not a project cook.

### 5.4 `NYRA::Compat::` shim drift hotspots (empirical — populate after first matrix run)

Based on release notes review + community reports, these are the LIKELY drift points:

| Area | Potential drift | Shim strategy |
|------|----------------|---------------|
| **Slate `STextBlock` / `SRichTextBlock`** | "EPIC, please stop breaking Slate and UMG" community thread [VERIFIED: forums.unrealengine.com]. Between 5.5 and 5.6, UMG widgets no longer switch to volatile when animating. `FSlateFontInfo` APIs have drifted between 5.4 and 5.6. | `NYRA::Compat::MakeTextBlockStyle()` returns version-specific `FTextBlockStyle` init. |
| **`SDockTab` / `ETabRole::NomadTab`** | Stable across 5.4-5.7 per Phase 1 Plan 04 research. No shim expected. | No shim. |
| **Material Instance APIs (`UMaterialInstanceConstant`, `SetScalarParameterValueEditorOnly`)** | Function names drifted pre-5.4; current shape stable but deprecations accumulate. | `NYRA::Compat::SetMICParam()` wrapper. |
| **Sequencer / `UMovieScene`** | UE 5.6 deprecates `UUMGSequencePlayer` in favor of runner structs [VERIFIED: forums post on 5.6 release]. 5.7 continues the path. `IMovieScenePlayer` interface is deprecated. | Defer full shim to Phase 7 (when SCENE-02 needs Sequencer). Phase 2 only smoke-tests compilation. |
| **Blueprint graph APIs (`UEdGraph`, `UEdGraphNode`, `FBlueprintEditorUtils`)** | "Recent versions require animation-finished events to be in event graph, while prior versions allowed them as overridable functions" [VERIFIED: forums]. FLAGGED LOW CONFIDENCE in ARCHITECTURE.md. | Defer full shim to Phase 4. Phase 2 smoke-tests + pins the issue list discovered. |
| **NNE (Neural Network Engine)** | NNE introduced in 5.4 as a RHI-analogous inference layer. Backend availability (DirectML / CUDA / CPU) differs per version and per user hardware. Profile module deprecated 5.6. | `NYRA::Compat::NNE` deferred to Phase 3 (when RAG considers NNE for BGE-small inference). Phase 2 verifies NNE headers include cleanly across all four versions. |
| **`FWebSocketsModule`** | Expected stable (Phase 1 Plan 10 validated on 5.6). Not a known-drift area. | No shim expected; confirm empirically. |
| **`ToolMenus` module** | Introduced in 5.0; stable API but community reports subtle identifier-name changes between versions. Phase 1 Plan 04 uses `Tools > NYRA > Chat` — verify identifier still matches in 5.4 + 5.7. | Pin menu section name constants behind `NYRA::Compat::ToolMenuSections`. |
| **Profiler / Trace modules** | UE 5.6 deprecates Profiler* modules [VERIFIED], TraceDataFilters plugin deprecated. | Use Trace Control Widget path (Phase 3+ relevance, not Phase 2). |
| **SDL2 → SDL3 transition for Linux** | UE 5.7 Linux transitions SDL2→SDL3. | Windows-only plugin per PROJECT.md — not applicable to v1. |
| **UMG Sequence runner deprecation in 5.6** | `UUMGSequencePlayer` removed except for backwards compat. | Phase 4+ animation code may hit this. Phase 2 pins the deprecation list. |

**Wave 0 deliverable:** run `BuildPlugin` on all four UE versions with the Phase 1 codebase AS-IS. Capture every compile error / warning. This IS the empirical drift matrix. `NYRA::Compat::` entries emerge from that capture, not from speculation.

### 5.5 Version guarding pattern

```cpp
// NyraEditor/Public/NYRACompat.h
#include "Runtime/Launch/Resources/Version.h"

#define NYRA_UE_AT_LEAST(Major, Minor) \
    (ENGINE_MAJOR_VERSION > (Major) || \
     (ENGINE_MAJOR_VERSION == (Major) && ENGINE_MINOR_VERSION >= (Minor)))

namespace NYRA::Compat
{
#if NYRA_UE_AT_LEAST(5, 6)
    // 5.6+ path
    inline FTextBlockStyle MakeChatTextStyle() { /* 5.6+ shape */ }
#else
    // 5.4, 5.5 path
    inline FTextBlockStyle MakeChatTextStyle() { /* older shape */ }
#endif
}
```

**Rule:** every `#if` block must be small (<20 lines) and clearly tagged with a `// NYRA_COMPAT: <reason>` comment. Blocks larger than 20 lines indicate the drift is big enough to warrant separate source files (`NyraEditor_5_6+.cpp` vs `NyraEditor_5_5-.cpp` patterns).

**Confidence:** HIGH on the CI workflow shape (standard UE pattern). MEDIUM on specific drift hotspots (release notes review surfaced candidates but the empirical CI run is the authority). LOW on 5.7 readiness — presumed-GA 2026-04 but not directly verified.

---

## 6. EV code-signing (vendor + pipeline + cost + reputation timeline)

### 6.1 Vendor comparison (2026-04-22 verified)

| Vendor | EV Cert Cost | Azure Key Vault Compatible? | SmartScreen Reputation | Notes |
|--------|--------------|---------------------------|------------------------|-------|
| **DigiCert** | $559.99-$699 / 1 year | ✅ Yes | Near-instant (highest trust) | ONLY major CA fully AKV-compatible. [VERIFIED: ssl2buy.com, signmycode.com, fairssl.dk] |
| **GlobalSign** | ~$400-600 / 1 year | ✅ Yes | Near-instant | Also AKV-compatible. [VERIFIED] |
| **Sectigo (Comodo)** | $279.99 / 1 year | ❌ No | Near-instant | Cheapest, BUT "requires key attestation, which Azure Key Vault does not support" [VERIFIED]. Requires hardware USB token (SafeNet 5110). CI-unfriendly. |
| **SSL.com** | varies | ✅ Yes (some products) | Near-instant | Less well-documented AKV path. |

**Industry shift — 2026 regulation [VERIFIED]:** Starting **February 15, 2026**, code signing certificates are capped at **1-year maximum lifespan**. DigiCert now only sells 1-year plans. Multi-year pre-purchase options exist but require re-issue every ~400-460 days during the subscription.

### 6.2 RECOMMENDED vendor: DigiCert EV in Azure Key Vault

**Cost:** ~$700/year DigiCert EV cert + ~$5/month Azure Key Vault Premium SKU (Premium is required — Standard SKU cannot create RSA-HSM keys that are non-exportable) = **~$760/year total**.

**Why AKV + DigiCert:**
- Fully cloud-backed signing (no USB token shipping, no single-workstation lock-in).
- Microsoft Managed HSM (FIPS 140-2 Level 3) compliance [VERIFIED]. Key never leaves hardware.
- RBAC-gated — any CI runner with an Azure AD service principal can sign, full audit log.
- Works with AzureSignTool (free, open-source SignTool replacement) and with Microsoft's own SignTool.
- Since June 2023, HSM-backed key storage is mandatory for all code signing certs (OV and EV). Software .pfx files are no longer valid. AKV satisfies this.

### 6.3 Acquisition workflow (Wave 0 deliverable)

1. Create Azure Key Vault (Premium SKU) in an Azure subscription.
2. Generate certificate request (CSR) in AKV.
3. Order DigiCert EV cert, choose "Install on HSM" provisioning.
4. DigiCert identity verification (1-3 business days — REQUIRES D-U-N-S number for the publishing entity; solo founder sets up as a sole-proprietorship / LLC).
5. DigiCert delivers signed certificate; import into AKV by merging with the CSR.
6. Create Azure AD app registration + service principal with `Key Vault Crypto User` role over the vault.
7. Add `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET` as GitHub Actions secrets.

### 6.4 CI signing step

```yaml
# after BuildPlugin succeeds
- name: Install AzureSignTool
  run: dotnet tool install --global AzureSignTool
- name: Sign binaries
  shell: pwsh
  env:
    AZ_VAULT_URI: ${{ secrets.AZURE_VAULT_URI }}  # https://<vault>.vault.azure.net
    AZ_CERT_NAME: ${{ secrets.AZURE_CERT_NAME }}  # e.g. nyra-ev-cert
    AZ_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
    AZ_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}
    AZ_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
  run: |
    Get-ChildItem -Recurse -Include @("*.dll","*.exe") -Path Artifacts/UE_${{ matrix.ue-version }}/ | ForEach-Object {
      AzureSignTool sign `
        -kvu $env:AZ_VAULT_URI `
        -kvc $env:AZ_CERT_NAME `
        -kvi $env:AZ_CLIENT_ID `
        -kvs $env:AZ_CLIENT_SECRET `
        -kvt $env:AZ_TENANT_ID `
        -tr "http://timestamp.digicert.com" `
        -td sha256 `
        -fd sha256 `
        -v $_.FullName
    }
```

**Timestamp server URL** (`-tr http://timestamp.digicert.com`): ensures signature remains valid after cert expires via RFC 3161 timestamping [VERIFIED].

### 6.5 Which binaries to sign

Per DIST-03: all deliverable Windows binaries. That is:
- `UnrealEditor-NyraEditor.dll` (plugin module — one per UE version)
- `UnrealEditor-NyraRuntime.dll` (runtime module — one per UE version)
- `NyraHost` bootstrapped entry — the `cpython/python.exe` is bundled from python-build-standalone. **Question for planner:** python-build-standalone binaries are pre-signed by Astral? If not, NYRA re-signs them to satisfy enterprise AV. Phase 2 Wave 0 empirically verifies.
- `llama-server.exe` (bundled in `Binaries/Win64/NyraInfer/`) — pre-signed by ggml.ai? Empirically verify; if not, NYRA re-signs.

**Same EV cert can sign all of them** — one publisher identity. No need for per-binary certs.

### 6.6 SmartScreen reputation timeline

- Non-EV OV certs: 30-day reputation-building window — users see "Unknown Publisher" and SmartScreen warnings until the publisher has signed enough downloaded binaries. [VERIFIED]
- EV certs: near-instant SmartScreen trust (no/minimal warning) from the FIRST install. Caveat: "EV certificates establish stronger publisher identity, which helps build trust with SmartScreen faster. However, they no longer guarantee instant SmartScreen reputation removal" [VERIFIED: sslinsights.com 2026] — reputation still accumulates, but the starting floor is much higher than OV.

**Implication for Fab launch:** the 30-day OV warning window is the launch-poisoning risk. EV cert eliminates it. Budget the cert as a hard requirement before launch day, not as a post-launch polish item.

### 6.7 Microsoft Trusted Signing alternative

Microsoft now offers Azure Trusted Signing at ~$10/month [VERIFIED]. It handles certificate issuance + renewal + HSM for you. Valid option for v2+ once NYRA has publisher reputation; for v1 DigiCert EV is better understood + avoids dependency on Microsoft's own maturity curve.

**Confidence:** MEDIUM-HIGH on vendor recommendation (pricing verified; AKV path well-documented). MEDIUM on D-U-N-S identity verification timing for a solo founder (may need 1-2 weeks if no business entity exists yet).

---

## 7. Console-command tool design (whitelist model)

### 7.1 API surface [VERIFIED: unrealcommunity.wiki + Epic docs]

Console command execution in UE happens via:
- `GEngine->Exec(World, Command, Ar)` — runs any registered console command. `Ar` is an `FOutputDevice*` capturing output.
- `IConsoleManager::Get().ProcessUserConsoleInput(InStr, Ar, InWorld)` — alternative entry, parses cvar/command/setting syntax.

Registration:
- `IConsoleManager::Get().RegisterConsoleCommand(Name, Help, Delegate, Flags)`
- `FAutoConsoleCommand` / `FAutoConsoleCommandWithWorldArgsAndOutputDevice` — static init pattern.

### 7.2 Safety problem

No engine-provided whitelist exists. UE5 has ~6,607 entries. Some are safe (`stat fps`, `log verbose`), some destructive (`quit`, `exit`, `exec filename`, `reloadshaders` in shipping builds, `obj list` which can OOM).

### 7.3 RECOMMENDED whitelist strategy

Three tiers:

**Tier A — AUTO-APPROVED (read-only):**
- `stat <anything>` — all stat commands are read-only (stat fps, stat unit, stat scenerendering, etc.)
- `showflag.<anything> 0|1` — toggles viewport display flags; reversible and non-destructive
- `log <category> <verbosity>` — changes log verbosity
- `log list` — lists all log categories (read-only)
- `help` / `help <command>`
- `obj classes` / `obj hierarchy` — class list (read-only, but slow on large projects)
- `dumpticks` / `memreport -full` — diagnostic dumps
- `r.VSync`, `r.ScreenPercentage`, etc. — render tweaks (reversible)

**Tier B — PREVIEW-GATED (reversible but impactful):**
- `r.<anything>` that isn't in Tier A — generic CVar set (reversible, but may break rendering)
- `profilegpu` — captures a GPU trace
- Anything with a numeric argument that the user hasn't specified in natural language

**Tier C — HARD-BLOCKED (dangerous / irreversible in editor):**
- `quit`, `exit`, `exitnow`
- `exec <file>` — runs arbitrary command file
- `obj gc`, `gc.CollectGarbage` — GC forcing
- `reloadshaders` — can take minutes, can crash editor mid-run
- `travel <map>`, `open <map>` — switches level (loses unsaved work)
- `debugcreateplayer`, `camera` in certain modes
- Anything unmapped / unknown — default-deny

### 7.4 MCP tool schema (`nyra_console_exec`)

```json
{
  "name": "nyra_console_exec",
  "description": "Execute a whitelisted UE console command. Commands are tier-classified; Tier A runs immediately, Tier B requires user approval, Tier C is rejected.",
  "inputSchema": {
    "type": "object",
    "required": ["command"],
    "properties": {
      "command": {"type": "string", "description": "Console command including arguments, e.g. 'stat fps' or 'r.ScreenPercentage 50'"},
      "rationale": {"type": "string", "description": "Why the agent is running this."}
    }
  }
}
```

NyraHost adapter:
1. Classify `command` against the whitelist rules (pure string-match + prefix).
2. Tier A: forward to UE via new JSON-RPC method `console/exec` → UE runs `GEngine->Exec` on GameThread, captures `FOutputDevice` output, returns stdout to NyraHost → returns to Claude as tool_result.
3. Tier B: emit `plan/preview` with the single step; on approval, proceed as Tier A.
4. Tier C: return error `nyra_console_exec: command '<cmd>' is blocked. Reason: <reason>.` Claude sees the block and adapts.

### 7.5 Output-device capture pattern

```cpp
// NyraEditor/Private/Console/FNyraConsoleHandler.cpp
FString FNyraConsoleHandler::Exec(const FString& Command)
{
    FStringOutputDevice Ar;
    if (GEngine)
    {
        GEngine->Exec(GEditor ? GEditor->GetEditorWorldContext().World() : nullptr,
                      *Command, Ar);
    }
    return Ar;
}
```

`FStringOutputDevice` captures all `Serialize` calls during `Exec` into a single `FString`, which becomes the tool_result.

### 7.6 Editor vs Game world distinction

Some commands target the game world (`travel`), some the editor viewport (`stat fps`), some either. NYRA ONLY executes in the EDITOR world context (`GEditor->GetEditorWorldContext().World()`); PIE-triggered commands are rejected in v1 to avoid accidentally affecting a play session.

**Confidence:** HIGH on the API + output capture pattern. MEDIUM on the whitelist completeness — the 6,607 command set requires ongoing curation. RECOMMENDED Wave 0 step: enumerate all registered commands via `IConsoleManager::ForEachConsoleObjectThatStartsWith()`, tag each, archive as `nyra-console-whitelist-v1.json`.

---

## 8. Output/Message-log tool design (filtering + volume)

### 8.1 Two log systems to tail

UE has two independent logging systems:
1. **Output Log** — `UE_LOG(LogCategory, Verbosity, ...)` emits through `GLog` to registered `FOutputDevice` instances.
2. **Message Log** — `FMessageLog("CategoryName").Info(TokenizedMsg)` — editor-side user-facing log (e.g., compile errors, asset import warnings) written to named listings displayed in the Message Log tab.

NYRA needs both. MCP tool `nyra_output_log_tail` and `nyra_message_log_list` are separate.

### 8.2 Output Log sink (tailing pattern) [VERIFIED]

```cpp
// NyraEditor/Private/Logging/FNyraOutputDeviceSink.h
class FNyraOutputDeviceSink : public FOutputDevice
{
public:
    virtual void Serialize(const TCHAR* Msg, ELogVerbosity::Type Verbosity,
                           const FName& Category) override
    {
        // Filter by category + verbosity
        if (!ShouldCapture(Category, Verbosity)) { return; }

        FScopeLock Lock(&BufferLock);
        Buffer.Add(FNyraLogEntry{
            FDateTime::UtcNow(), Category, Verbosity, FString(Msg)
        });
        if (Buffer.Num() > MaxEntries)
        {
            Buffer.RemoveAt(0, Buffer.Num() - MaxEntries);  // ring buffer
        }
    }

    bool ShouldCapture(const FName& Category, ELogVerbosity::Type Verbosity) const
    {
        // User- or agent-configured filters
        if (CategoryWhitelist.Num() > 0 && !CategoryWhitelist.Contains(Category))
        {
            return false;
        }
        return Verbosity <= MaxVerbosity;  // lower = more severe; Fatal=1
    }

    // ... GetTail(N), SetFilter(...) public surface ...

private:
    mutable FCriticalSection BufferLock;
    TArray<FNyraLogEntry> Buffer;
    TSet<FName> CategoryWhitelist;
    ELogVerbosity::Type MaxVerbosity = ELogVerbosity::Log;
    int32 MaxEntries = 2000;
};
```

Registration in `FNyraEditorModule::StartupModule()`:
```cpp
LogSink = MakeUnique<FNyraOutputDeviceSink>();
if (GLog) { GLog->AddOutputDevice(LogSink.Get()); }
```

Unregister in `ShutdownModule()`.

### 8.3 Message Log listener [VERIFIED]

```cpp
// In StartupModule:
FMessageLogModule& MLM = FModuleManager::LoadModuleChecked<FMessageLogModule>("MessageLog");
FMessageLogInitializationOptions Opts;
Opts.bShowFilters = true;
Opts.bShowPages = false;
Opts.bAllowClear = true;
MLM.RegisterLogListing(FName("NYRA"), LOCTEXT("NyraLog", "NYRA Agent"), Opts);
```

For tailing existing listings (LogBlueprint, LogPIE, LogAssetTools):

```cpp
TSharedRef<IMessageLogListing> Listing = MLM.GetLogListing(FName("LogBlueprint"));
Listing->OnDataChanged().AddRaw(this, &FNyraLogReader::OnMessageLogChanged);
```

`OnDataChanged` fires when a message is flushed (remember: `FMessageLog` destructor flushes).

### 8.4 Volume control (pitfall mitigation)

**Problem:** large log spam can flood the agent context. `stat unit` alone emits ~30 lines/frame at 60fps = 1,800 lines/sec.

**Mitigations:**
- `nyra_output_log_tail` REQUIRES `since` (timestamp or last-seen entry ID) and `max_entries` (capped at 200 per call). Agent must poll; never subscribe blind.
- Per-call filters: `categories` whitelist, `min_verbosity` (Error/Warning/Log/Verbose/VeryVerbose), optional `regex` post-filter.
- Ring buffer in the sink caps memory at `MaxEntries=2000`.
- High-verbosity categories (LogRHI, LogRenderCore) default-excluded; agent must explicitly opt them in.

### 8.5 `nyra_output_log_tail` MCP tool schema

```json
{
  "name": "nyra_output_log_tail",
  "description": "Retrieve recent lines from the UE Output Log with filtering.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "categories": {"type": "array", "items": {"type": "string"}, "description": "e.g., ['LogBlueprint','LogSlate']. Omit for all."},
      "min_verbosity": {"type": "string", "enum": ["Fatal","Error","Warning","Display","Log","Verbose","VeryVerbose"], "default": "Log"},
      "since_ts": {"type": "string", "format": "date-time", "description": "ISO-8601 UTC. Omit to read from start of session."},
      "max_entries": {"type": "integer", "default": 100, "maximum": 200},
      "regex": {"type": "string", "description": "Optional regex applied post-filter."}
    }
  }
}
```

Output: `{entries: [{ts, category, verbosity, message}...], truncated: bool, last_ts: string}`.

### 8.6 Structured-vs-unstructured concerns

Output Log messages are unstructured plaintext. Agent sees them as strings. For structured events (Blueprint compile errors with file:line), Message Log is better — `FTokenizedMessage` carries actor refs + navigation tokens. `nyra_message_log_list` returns the tokenized form so Claude can ask follow-up "navigate to this BP compile error" tool calls.

### 8.7 `FCoreDelegates::OnHandleSystemError` — crash interception

Bind in `StartupModule` to flush the in-memory ring buffer to disk before UE crashes. Writes to `Saved/NYRA/logs/crash-<timestamp>.log` for post-mortem. Low-cost defensive pattern.

**Confidence:** HIGH on the FOutputDevice + FMessageLog API (well-documented Epic patterns). MEDIUM on the exact verbosity levels accepted by Output Log UI (requires empirical confirm in Wave 0).

---

## 9. Subscription status UI (state detection + transitions)

### 9.1 State detection primitives

- **`claude` binary presence:** NyraHost shells out `where claude` (Windows) / `which claude` (Unix). Result cached for 60s.
- **`claude auth status`:** exits 0 if logged in, 1 if not [VERIFIED]. JSON output parsed for account info. Run at NyraHost startup and on every transition into `Disconnected`.
- **Gemma presence:** NyraHost checks `gemma_gguf_path(project_dir)` exists and SHA256 matches pin (Phase 1 Plan 09 operational).
- **Ollama presence:** probe `http://127.0.0.1:11434/api/tags` for `gemma3:4b-it-qat` (Phase 1 D-18).
- **Computer-use readiness:** Phase 2 defers full detection to Phase 5 (ACT-06/07 ship here, not computer-use). CHAT-02 shows "Computer-use: not yet configured" as a separate pill.

### 9.2 Wire protocol — `diagnostics/backend-state` notification

New JSON-RPC notification from NyraHost → UE, emitted on every router state transition:

```json
{
  "jsonrpc": "2.0",
  "method": "diagnostics/backend-state",
  "params": {
    "claude": {
      "installed": true,
      "version": "2.1.118",
      "auth": "pro" | "max" | "teams" | "enterprise" | "console" | "unknown" | "signed-out",
      "state": "ready" | "rate-limited" | "auth-drift" | "offline",
      "rate_limit_resets_at": "2026-04-22T15:00:00Z" | null
    },
    "gemma": {
      "model_present": true,
      "runtime": "ollama" | "bundled-llama-server" | "none",
      "state": "ready" | "downloading" | "loading" | "not-installed"
    },
    "computer_use": {
      "state": "not-configured"  // Phase 5 fills in
    },
    "mode": "normal" | "privacy-mode",
    "updated_at": "2026-04-22T14:00:00Z"
  }
}
```

### 9.3 UI rendering — where the status pill lives

Phase 1 Plan 13 ships `SNyraBanner` (for banner messages) and `SNyraDiagnosticsDrawer`. Phase 2 adds a **status pill row** between the banner and the message list:

```
┌───────────────────────────────────────────┐
│  SNyraBanner (existing)                   │
├───────────────────────────────────────────┤
│  [● Claude Pro]  [◐ Gemma ready]  [⚠ Priv]│   ← NEW: SNyraBackendStatusStrip
├───────────────────────────────────────────┤
│  SNyraMessageList + SNyraDownloadModal     │
│  (existing)                                │
├───────────────────────────────────────────┤
│  SNyraComposer (existing)                  │
├───────────────────────────────────────────┤
│  SNyraDiagnosticsDrawer (existing)        │
└───────────────────────────────────────────┘
```

- Pill colours: Green (ready), Yellow (rate-limited), Red (auth-drift), Purple (privacy mode), Grey (not installed).
- Hover tooltip shows verbose state (e.g., "Claude Max connected. Rate limit resets at 3:00 PM PT. 42% of window used.").
- Click → opens a small popover with `[Sign in]` / `[Sign out]` / `[Test connection]` buttons.

### 9.4 First-run wizard integration

PROJECT.md's zero-config install promise: "user enables plugin, runs `claude setup-token` once, and is operational." The status pill is where this feedback loops:
1. Plugin loads → pill shows "Claude: not signed in" (grey).
2. User runs `claude auth login` in external terminal.
3. NyraHost's 5-minute TTL elapses OR user clicks `[Test connection]` → `diagnostics/backend-state` emits with `auth: "pro"`.
4. Pill turns green → first-run wizard dismisses.

### 9.5 Gemma state transitions

- `not-installed` → user clicks `[Download local fallback]` → `diagnostics/download-progress` notifications (Phase 1 §3.7 wired) → `downloading` with percent → `loading` (model file verified, llama-server spawning) → `ready`.
- `ready` → `loading` when model reloads after 10-min idle shutdown (Phase 1 D-19).

**Confidence:** HIGH on the mechanism (reuses Phase 1 infrastructure). MEDIUM on exact `claude auth status` JSON field names (Wave 0 must empirically capture).

---

## 10. Pitfalls + mitigations

### 10.1 Anthropic CLI stream-JSON schema drifts between minor versions — HIGH

**What goes wrong:** NYRA parses `event.type == "content_block_delta"` with `delta.type == "text_delta"`. A future CLI version renames the event type. Stream-parsing breaks silently.

**Mitigations:**
- At NyraHost startup, shell out `claude --version` and compare against a tested-version range. Warn on mismatch.
- Snapshot the `stream-json` shape in pytest fixtures — `tests/fixtures/stream-json-cli-2.1.118.ndjson`. Detect schema drift by running a one-off `claude -p --output-format stream-json --verbose --include-partial-messages "Reply with OK"` during Wave 0 and committing the captured frames.
- Weekly-CI canary: nightly runner uses `claude install stable` and runs the NYRA round-trip bench. If parse errors spike, open an incident.
- Per PITFALLS §1.5: bias toward MCP (versioned at protocol level) over raw CLI parsing. NYRA relies on the CLI for stream events but MCP tool calls are the structured path.

**Warning signs:** unknown `type` fields in `stream_event.event`; NDJSON lines that fail to parse.

### 10.2 UE CI matrix becomes flaky on first-party changes — HIGH

**What goes wrong:** 5.7 ships a hotfix; 5.7.2 breaks a Slate API we were relying on; matrix cell goes red; blocks all PRs.

**Mitigations:**
- Pin runner UE installs to specific point versions (5.4.4, 5.5.4, 5.6.1, 5.7.X). Upgrade is an explicit MR ("bump UE 5.7 to 5.7.1").
- `fail-fast: false` so one bad version doesn't block others.
- Monthly "UE version refresh" MR that bumps point versions and captures all compat drift in one batch.
- Keep `NYRA::Compat::` shim blocks SMALL and comment-tagged so reading the drift delta is quick.
- PITFALLS §3.3 aligned.

### 10.3 EV cert renewal gotcha — MEDIUM

**What goes wrong:** Feb-2026 regulation caps cert lifespan at 1 year [VERIFIED]. NYRA forgets to renew; builds ship unsigned; SmartScreen warns; Fab reviews bomb.

**Mitigations:**
- Calendar reminder at day 300 of cert life (not day 365 — DigiCert renewal is 1-3 business days).
- RFC 3161 timestamping on every signature [VERIFIED] — binaries signed before cert expiry remain valid indefinitely.
- AKV auto-renewal can be configured via DigiCert API integration (evaluate in v1.1).
- Document renewal playbook in `docs/EV_CERT_RENEWAL.md`.

### 10.4 `FScopedTransaction` silently breaks if plugin unloads mid-session — HIGH

**What goes wrong:** NYRA plugin hot-reloads mid-session; outer `BeginTransaction` never gets matching `EndTransaction`; UTransBuffer refcount leaks; undo stack corrupts.

**Mitigations:**
- `FNyraSessionTransaction::Cancel()` called unconditionally in `FNyraEditorModule::ShutdownModule`. Safe to call on already-cancelled (INDEX_NONE).
- Refuse hot-reload during an active NYRA session — surface a banner "NYRA session active. End session before reloading plugin."
- Wave 0 test: manually hot-reload plugin mid-session in UE editor, verify undo stack stays sane.

### 10.5 Whitelist-based console-command tool being too restrictive — MEDIUM

**What goes wrong:** User asks Claude "show me the shader complexity viewmode"; the command is `viewmode shadercomplexity` which isn't in the Tier A whitelist; Claude fails; user frustrated.

**Mitigations:**
- Whitelist is LIVE-CURATED — nightly review of denied-command logs. High-frequency denials graduate to Tier A after manual review.
- "Run once (not saved)" button in the preview UI lets user approve a single Tier B / Tier C command for the current turn only, without adding to whitelist. Keeps escape hatch alive.
- `nyra_console_exec` error response includes the reason AND suggestion: "Command 'viewmode shadercomplexity' is Tier C. If this is routine, add to whitelist via Settings > NYRA > Console Whitelist."

### 10.6 Rate-limit detection false positives from transient 5xx — MEDIUM

**What goes wrong:** Anthropic has a 30-second hiccup; NYRA sees 3 `api_retry` events with `error="server_error"`; router flips to GemmaFallback; user is bumped off Claude for no good reason.

**Mitigations:**
- Router treats `server_error` and `unknown` as RETRY-WITHOUT-USER-ACTION (background retries up to 3 attempts using `retry_delay_ms`), NOT as fallback triggers.
- Only `rate_limit`, `authentication_failed`, `billing_error` transition state.
- After a `server_error` retry that succeeds, emit a silent `diagnostics/backend-state` update but don't alarm the user.

### 10.7 `--mcp-config` file path race on concurrent sessions — LOW

**What goes wrong:** Two UE editors open the same project simultaneously; both write to `%LOCALAPPDATA%/NYRA/mcp-configs/<session-id>.json`; session IDs collide.

**Mitigations:**
- Session ID is a UUID (per Phase 1 D-10) — collision probability is effectively zero.
- File name includes UUID; no overwrites.
- Cleanup: NyraHost sweeps mcp-configs older than 24h on startup.

### 10.8 Azure Key Vault region outage blocks CI signing — LOW

**What goes wrong:** AKV region goes down; CI builds can't sign; release blocked.

**Mitigations:**
- Wait for region recovery; AKV SLA is 99.9%, recovery typically < 2 hours.
- Keep un-signed binaries as artifacts; sign manually from local machine using AzureSignTool if desperate.
- v2+ evaluate multi-region AKV replication.

### 10.9 `CLAUDE_CODE_OAUTH_TOKEN` env leak into subprocess-spawned children — MEDIUM

**What goes wrong:** Claude CLI spawns a bash subshell; OAuth token env var is inherited; hostile tool capture exposes token.

**Mitigations:**
- Per Anthropic docs, token is Claude-scoped (inference only, no remote-control).
- NyraHost NEVER reads `CLAUDE_CODE_OAUTH_TOKEN` — it passes through the parent env to the child `claude` process and no further.
- NYRA does NOT pass the token via `--settings` or any CLI flag. Token flows via env, which Claude Code reads natively.
- Document the threat model in `docs/THREAT_MODEL.md`: token remains on user's machine, never touches NyraHost code paths, never touches UE.

### 10.10 Session resumption via `--session-id` clashes with user's own Claude Code sessions — LOW

**What goes wrong:** User runs `claude` interactively in a terminal; NYRA uses `--session-id <uuid>`; the session shows up in the user's `/resume` picker, confusing them.

**Mitigations:**
- NYRA uses a UUID namespace prefix `nyra-` prepended to the session name via `--name "nyra-<short-id>"`. User sees `nyra-abc123` in their `/resume` picker, clearly attributed.
- `--no-session-persistence` is an option for one-shot diagnostics turns; NOT used for normal turns because conversation continuity needs persistence.

---

## 11. Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (C++) | UE **Automation Spec** (inherited from Phase 1 Plan 01). `Nyra.*` namespace. |
| Framework (Python) | **pytest 8.x** + `pytest-asyncio` + `pytest-httpx` (inherited from Phase 1 Plan 02). |
| Framework (CI) | **GitHub Actions** with self-hosted Windows runner labeled `self-hosted,Windows,unreal`. |
| C++ config file | None — specs discovered via macros in `NyraEditor/Private/Tests/`. |
| Python config file | `NyraHost/pyproject.toml` (extended additively; Phase 2 adds `pytest-subprocess` for mocking `claude` CLI spawn). |
| Quick run command (C++) | `UnrealEditor-Cmd.exe TestProject.uproject -ExecCmds="Automation RunTests Nyra;Quit" -unattended -nopause -nullrhi` |
| Quick run command (Python) | `pytest NyraHost/tests/ -x` |
| Full suite (C++) | As above, no filter |
| Full suite (Python) | `pytest NyraHost/tests/ -v` |
| Four-version matrix | `.github/workflows/plugin-matrix.yml` — triggered per PR; targets 5.4/5.5/5.6/5.7. |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PLUG-04 | Plugin compiles on UE 5.4 | CI compile | `RunUAT BuildPlugin` on UE_5.4 | ❌ Wave 0 (new workflow) |
| PLUG-04 | Plugin compiles on UE 5.5 | CI compile | `RunUAT BuildPlugin` on UE_5.5 | ❌ Wave 0 |
| PLUG-04 | Plugin compiles on UE 5.6 | CI compile | `RunUAT BuildPlugin` on UE_5.6 (inherits Phase 1 dev host) | ✅ Phase 1 |
| PLUG-04 | Plugin compiles on UE 5.7 | CI compile | `RunUAT BuildPlugin` on UE_5.7 | ❌ Wave 0 |
| PLUG-04 | `NYRA::Compat::` shim unit tests | unit (C++) | `Nyra.Compat.TextBlockStyle`, `Nyra.Compat.MICParam` etc. | ❌ Wave 0 |
| SUBS-01 | Claude CLI subprocess spawn + NDJSON parse | pytest | `pytest NyraHost/tests/test_claude_adapter.py::test_stream_json_parse` | ❌ Wave 0 |
| SUBS-01 | `--mcp-config` file generation | pytest | `pytest NyraHost/tests/test_mcp_config.py::test_writes_valid_json` | ❌ Wave 0 |
| SUBS-01 | End-to-end Claude turn (guarded integration) | pytest (guarded) | `pytest NyraHost/tests/test_claude_integration.py::test_live_turn -m live` — opt-in, requires `CLAUDE_CODE_OAUTH_TOKEN` env | ❌ Wave 0 |
| SUBS-02 | Rate-limit detection from `api_retry` event | pytest | `pytest NyraHost/tests/test_router.py::test_rate_limit_transition` (fixture NDJSON) | ❌ Wave 0 |
| SUBS-02 | Auth-drift detection from `api_retry` authentication_failed | pytest | `pytest NyraHost/tests/test_router.py::test_auth_drift_transition` | ❌ Wave 0 |
| SUBS-02 | Gemma fallback after user-approved fallback | pytest | `pytest NyraHost/tests/test_router.py::test_fallback_to_gemma` | ❌ Wave 0 |
| SUBS-03 | Router multi-backend abstraction | pytest | `pytest NyraHost/tests/test_backend_interface.py::test_abstract_contract` | ❌ Wave 0 |
| CHAT-02 | `diagnostics/backend-state` notification emission | pytest | `pytest NyraHost/tests/test_diagnostics.py::test_backend_state_on_transition` | ❌ Wave 0 |
| CHAT-02 | Status pill rendering per state | automation (C++) | `Nyra.Panel.StatusPill.Ready`, `Nyra.Panel.StatusPill.RateLimited` etc. | ❌ Wave 0 |
| CHAT-03 | `FNyraSessionTransaction::Begin/End/Cancel` roundtrip | unit (C++) | `Nyra.Transactions.SessionScope` | ❌ Wave 0 |
| CHAT-03 | Nested `FScopedTransaction` coalesces into outer | unit (C++) | `Nyra.Transactions.NestedCoalesce` | ❌ Wave 0 |
| CHAT-03 | Cancel during streaming rolls back super-transaction | integration (C++) | `Nyra.Transactions.CancelRollback` | ❌ Wave 0 |
| CHAT-04 | `nyra_permission_gate` MCP tool schema validation | pytest | `pytest NyraHost/tests/test_permission_gate.py::test_schema_valid` | ❌ Wave 0 |
| CHAT-04 | `plan/preview` → `plan/decision` roundtrip | integration (C++) | `Nyra.Preview.ApproveFlow` | ❌ Wave 0 |
| ACT-06 | Console whitelist classifier | pytest | `pytest NyraHost/tests/test_console_whitelist.py::{tier_a,tier_b,tier_c}` | ❌ Wave 0 |
| ACT-06 | `console/exec` GameThread execution + capture | unit (C++) | `Nyra.Console.ExecCaptureOutput` | ❌ Wave 0 |
| ACT-07 | `FNyraOutputDeviceSink` category filter | unit (C++) | `Nyra.Logging.CategoryFilter` | ❌ Wave 0 |
| ACT-07 | `nyra_output_log_tail` tool paging | pytest | `pytest NyraHost/tests/test_log_tail.py::test_since_and_limit` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest NyraHost/tests/ -x` (<10s) + `Nyra.*` automation quick filter on affected module (<60s).
- **Per wave merge:** full pytest + full `Nyra.*` automation on UE 5.6 (dev host). Four-version matrix runs on PR.
- **Phase gate (before `/gsd-verify-work`):**
  1. Four-version matrix green.
  2. EV-signed artifacts verified with `signtool verify /pa <dll>` (manual Wave 5 step).
  3. Live Claude turn (guarded, `CLAUDE_CODE_OAUTH_TOKEN` env set) passes `test_live_turn`.
  4. Privacy Mode toggle round-trip tested (one manual run).

### Wave 0 Gaps

- [ ] `.github/workflows/plugin-matrix.yml` — CI matrix workflow (net-new)
- [ ] Self-hosted Windows runner provisioned with UE 5.4/5.5/5.6/5.7 installed
- [ ] Azure Key Vault Premium SKU created + DigiCert EV cert in-vault (parallel track)
- [ ] `NyraEditor/Public/NYRACompat.h` — version-guard macros (net-new)
- [ ] `NyraEditor/Private/Transactions/FNyraSessionTransaction.{h,cpp}` (net-new)
- [ ] `NyraHost/src/nyrahost/backends/{base,claude,gemma}.py` — backend abstraction (net-new; `gemma` is extracted from Phase 1 Plan 08 router)
- [ ] `NyraHost/src/nyrahost/router.py` — refactored to use `AgentBackend` (upgrade existing)
- [ ] `NyraHost/src/nyrahost/claude_adapter/{subprocess_driver,stream_parser,mcp_config_writer}.py` (net-new)
- [ ] `NyraHost/tests/fixtures/stream-json-cli-2.1.X.ndjson` — captured sample events (Wave 0 empirical capture)
- [ ] `NyraHost/tests/test_claude_adapter.py`, `test_router.py`, `test_mcp_config.py`, `test_permission_gate.py`, `test_console_whitelist.py`, `test_log_tail.py` (net-new)
- [ ] `NyraEditor/Private/Tests/NyraCompatSpec.cpp`, `NyraTransactionsSpec.cpp`, `NyraConsoleSpec.cpp`, `NyraLoggingSpec.cpp`, `NyraPreviewSpec.cpp`, `NyraStatusPillSpec.cpp` (net-new)
- [ ] Extend `docs/JSONRPC.md` with Phase 2 method surface (`console/exec`, `plan/preview`, `plan/decision`, `diagnostics/backend-state`, `session/set-mode`)
- [ ] Extend `docs/ERROR_CODES.md` with new Phase 2 codes (see §12)

---

## 12. Wire protocol extensions (for planner)

Phase 2 adds the following to `docs/JSONRPC.md` (additive to Phase 1):

### New JSON-RPC methods (UE ↔ NyraHost)

| Method | Direction | Kind | Purpose |
|--------|-----------|------|---------|
| `chat/send` params extension | UE → NH | req | `backend` field gains `"claude"` value (in addition to `"gemma-local"` from Phase 1 D-10) |
| `session/set-mode` | UE → NH | req | Toggle Privacy Mode: `{mode: "normal" \| "privacy"}` |
| `plan/preview` | NH → UE | notification | Emit safe-mode plan for approval (§4.3) |
| `plan/decision` | UE → NH | req | User's approve/reject/edit verdict (§4.3) |
| `console/exec` | NH → UE | req | Execute whitelisted console command on GameThread, return captured output (§7.4) |
| `log/tail` | NH → UE | req | Return filtered Output Log tail (§8.5) |
| `log/message-log-list` | NH → UE | req | Return Message Log entries for a named listing (§8.3) |
| `diagnostics/backend-state` | NH → UE | notification | Router state transitions for CHAT-02 (§9.2) |
| `claude/auth-status` | NH → UE | notification | Fine-grained Claude auth state for first-run wizard |

### New error codes (extending Phase 1 D-11 `-32001..-32006`)

| Code | Name | Remediation template |
|------|------|----------------------|
| `-32007` | `claude_not_installed` | "Claude Code CLI not found. Install from code.claude.com." |
| `-32008` | `claude_auth_drift` | "Claude session expired. Run `claude auth login` in a terminal." |
| `-32009` | `claude_rate_limited` | "Claude rate-limited. Resume at {time}, or switch to local Gemma ([Switch])." |
| `-32010` | `privacy_mode_egress_blocked` | "This action requires internet access. Exit Privacy Mode to continue." |
| `-32011` | `plan_rejected` | "Plan rejected by user." |
| `-32012` | `console_command_blocked` | "Console command '{cmd}' is not in the safe-mode whitelist." |
| `-32013` | `transaction_already_active` | "Another NYRA session is already running. End it before starting a new one." |
| `-32014` | `pie_active` | "NYRA cannot mutate while Play-In-Editor is running. Stop PIE and retry." |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | UE 5.7 is GA-available at Phase 2 start (2026-04+) | §5.4, §5.5 | Medium — defer 5.7 cell one month; matrix ships with 5.4/5.5/5.6 initially |
| A2 | `claude auth status` JSON fields are stable and include subscription tier | §1.5, §9.1 | Low — Wave 0 empirical capture validates; fallback is to parse `--text` output |
| A3 | `--permission-prompt-tool` passes the tool call exactly as documented for destructive-only tools | §4.1 | Medium — pending live test; if Claude doesn't reliably call the gate, fallback to `--permission-mode plan` + assistant-text parsing |
| A4 | `system/api_retry` event fires for BOTH inference rate-limits AND MCP-tool-call throttling | §1.3, §10.6 | Medium — Wave 0 empirical fixture capture; if not, router needs secondary detection |
| A5 | `UTransBuffer` refcount-based nesting holds across UE 5.4-5.7 | §3.1, §3.4 | Low — engine-core behavior, stable for many versions |
| A6 | DigiCert EV cert identity verification completes in 1-3 business days | §6.3 | Medium — may take 1-2 weeks if founder has no business entity |
| A7 | python-build-standalone + llama-server.exe binaries bundled in Phase 1 arrive pre-signed | §6.5 | Low — re-signing with NYRA cert is a mitigation; empirical check in Wave 0 |
| A8 | `bMirrorToOutputLog=true` on `FMessageLog` forwards to `FOutputDevice` sinks | §8.2-8.3 | Low — standard UE pattern; Wave 0 confirms |
| A9 | Self-hosted dev-workstation-as-runner is acceptable for v1 (founder's own machine) | §5.2 | Medium — availability/reliability trade-off; budget a cloud Windows VM ($50-150/mo) as backup in v1.1 |
| A10 | Router's decision to stay in `ClaudeReady` after a 5xx recovers cleanly (no session-state loss) | §10.6 | Medium — retry semantics in Claude Code may differ; Wave 0 fixture-test and confirm |

---

## Open Questions

1. **Exact `claude auth status` JSON field names for subscription tier**
   - What we know: `claude auth status` exits 0/1 [VERIFIED]; default output is JSON.
   - What's unclear: precise field names for Pro vs Max vs Team vs Enterprise distinction.
   - Recommendation: Wave 0 — run `claude auth status` locally, capture the JSON, commit to `NyraHost/tests/fixtures/claude-auth-status-*.json`, use those field names in the adapter.

2. **Does `--permission-prompt-tool` reliably fire for all destructive MCP tools in Opus 4.7?**
   - What we know: Flag is documented and supported [VERIFIED]; Anthropic recommends it for third-party approval UIs.
   - What's unclear: Edge cases where Claude skips the gate (e.g., small "innocuous" tool calls).
   - Recommendation: Wave 0 empirical test with a 10-scenario suite (read, write, delete, BP edit, material edit, bulk spawn, etc.). If skip rate >0%, add NyraHost server-side enforcement that rejects any destructive MCP call not preceded by a `permission_gate` approval.

3. **Does UE 5.7 ship by Phase 2 start?**
   - What we know: April 2026 date; 5.7 presumed-GA based on Epic cadence.
   - What's unclear: actual release date for 5.7.0 + hotfix 5.7.1 timing.
   - Recommendation: CI matrix deferral — if 5.7 not available, ship 5.4/5.5/5.6 matrix and add 5.7 as a same-day follow-up MR when available. Document the deferral in `ROADMAP.md`.

4. **What is the exact NDJSON frame for a session with `--mcp-config` where MCP tool use occurs?**
   - What we know: MCP tools appear as `content_block_start` with `content_block.type == "tool_use"` and `name: "mcp__nyra__<toolname>"`.
   - What's unclear: whether the tool_result is delivered via a `user` event (per Anthropic convention) or a Claude Code-specific wrapper.
   - Recommendation: Wave 0 capture with a dummy MCP server that returns a trivial tool.

5. **Is there a way to detect PIE-active from NyraHost (Python), or must it be UE-side only?**
   - What we know: PIE suspends transaction system; NYRA must refuse mutations during PIE.
   - What's unclear: whether NyraHost has a way to know; `diagnostics/pie-state` notification from UE would be cleaner.
   - Recommendation: Phase 2 adds `diagnostics/pie-state` notification from UE → NyraHost (new method). Router refuses tool calls while PIE active.

6. **Does Ollama's `gemma3:4b-it-qat` model name match Phase 1 D-18's probe?**
   - What we know: Phase 1 Plan 08 validates Ollama detect with this model name.
   - What's unclear: whether Ollama model-naming conventions have drifted since model release (2025-03).
   - Recommendation: reuse Phase 1 probe; no change.

---

## Sources

### Primary (HIGH confidence — live-verified 2026-04-22)

- [Claude Code CLI Reference](https://code.claude.com/docs/en/cli-reference) — all CLI flags + commands [VERIFIED]
- [Claude Code Headless / Programmatic Use](https://code.claude.com/docs/en/headless) — `-p`, `--bare`, `stream-json`, `--include-partial-messages`, `api_retry` schema [VERIFIED]
- [Claude Code Authentication](https://code.claude.com/docs/en/authentication) — OAuth + `setup-token` + precedence order [VERIFIED]
- [Claude Agent SDK Overview](https://code.claude.com/docs/en/agent-sdk) — ToS on third-party claude.ai login + Opus 4.7 requirement [VERIFIED]
- [Anthropic Messages API Streaming](https://platform.claude.com/docs/en/build-with-claude/streaming) — inner `event` shape (`content_block_start`, `content_block_delta`, `input_json_delta`) [VERIFIED]
- [Anthropic Agent SDK Streaming Output](https://code.claude.com/docs/en/agent-sdk/streaming-output) — StreamEvent granularity, partial message semantics [VERIFIED]
- [Azure Key Vault Code Signing Instructions (TheSSLStore)](https://www.thesslstore.com/knowledgebase/code-signing-sign-code/azure-key-vault-code-signing-instructions/) — AKV + signing workflow [VERIFIED]
- [Azure Key Vault EV Code Signing (SSL2Buy)](https://www.ssl2buy.com/azure-key-vault-ev-code-signing-certificate.php) — pricing + compatibility [VERIFIED]
- [DigiCert EV + AKV (Joseph Guadagno blog)](https://www.josephguadagno.net/2024/07/17/ev-code-signing-certificates-with-azure-key-vault-and-digicert) — AKV ordering workflow [VERIFIED]
- [Sectigo EV vs DigiCert Pricing (signmycode.com)](https://signmycode.com/sectigo-ev-code-signing) — vendor comparison [VERIFIED]
- [EV Code Signing Guide 2026 (SSL Insights)](https://sslinsights.com/best-code-signing-certificate-providers/) — SmartScreen timeline [VERIFIED]

### Secondary (MEDIUM confidence — community/forums + Epic docs)

- [Epic Developer Community — Deep Dive into UE5 Transaction/Undo System Issues in Plugin Development](https://forums.unrealengine.com/t/deep-dive-into-ue5-transaction-undo-system-issues-in-plugin-development-need-community-guidance/2349470) — FScopedTransaction integration pitfalls
- [UE 5.7 FScopedTransaction API (Epic Developer Community)](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Editor/UnrealEd/FScopedTransaction)
- [UE5 Begin Transaction Blueprint API](https://dev.epicgames.com/documentation/en-us/unreal-engine/BlueprintAPI/Transactions/BeginTransaction) — `BeginTransaction` / `EndTransaction` semantics
- [Slate UI Programming Framework (UE 5.7)](https://dev.epicgames.com/documentation/en-us/unreal-engine/slate-user-interface-programming-framework-for-unreal-engine)
- [UMG-Slate-Compendium (YawLighthouse)](https://github.com/YawLighthouse/UMG-Slate-Compendium) — community reference for Slate API stability
- [Forum: "EPIC, please stop breaking Slate and UMG in new releases"](https://forums.unrealengine.com/t/epic-please-stop-breaking-slate-and-umg-in-new-releases/1179127) — empirical drift evidence
- [Unreal Engine 5.6 Released — Forum Announcement](https://forums.unrealengine.com/t/unreal-engine-5-6-released/2538952) — 5.6 release context
- [UE5.6.1 Hotfix Release Notes (Forum)](https://forums.unrealengine.com/t/5-6-1-hotfix-released/2639316) — hotfix context
- [Tom Looman — UE 5.6 Performance Highlights](https://tomlooman.com/unreal-engine-5-6-performance-highlights/) — 5.6 feature context
- [Message Log (Unreal Community Wiki)](https://unrealcommunity.wiki/message-log-4wzqj97j) — FMessageLog patterns
- [IConsoleManager (Unreal Community Wiki)](https://unrealcommunity.wiki/iconsolemanager-feb8r72t) — console command registration
- [UE Plugin CI — PureWeb blog](https://developer.pureweb.io/github-actions-unreal-builds/) — self-hosted runner pattern
- [UE CI via GitHub Actions — filfreire.com](https://filfreire.com/posts/unreal-gh-actions) — `RunUAT.bat` invocation patterns
- [UE4-GHA-Engine (falldamagestudio)](https://github.com/falldamagestudio/UE4-GHA-Engine) — GH Actions UE build example
- [Inworld AI — UE GitHub Build Automation](https://inworld.ai/blog/github-build-automation-for-unreal-engine)
- [Claude Code Rate Limits (SessionWatcher)](https://www.sessionwatcher.com/guides/claude-code-rate-limits-explained) — 5-hour window model [VERIFIED]
- [Claude Pro/Max Usage Guide (Anthropic Help Center)](https://support.claude.com/en/articles/11145838-using-claude-code-with-your-pro-or-max-plan) [VERIFIED]
- [Claude Code 5-hour Window + Weekly Caps](https://allthings.how/claude-code-usage-limits-explained-pro-max-and-weekly-caps/) — quota behavior

### Tertiary (LOW confidence — single source, unverified)

- `claude_code` stream-json NDJSON exact shape for tool_result delivery in MCP-injected mode — inferred from Messages API spec, not directly verified [Open Q #4].
- `claude auth status` JSON exact field names for subscription-tier detection — documented as JSON output but field names not quoted in docs [Open Q #1, A2].
- UE 5.7 API stability assumption — based on Epic's minor-version cadence; release date not directly verified [A1].

### Cross-references (already in `.planning/`)

- `.planning/PROJECT.md` — Constraints + Key Decisions forward-inherited.
- `.planning/REQUIREMENTS.md` — Phase 2 REQ IDs (PLUG-04, SUBS-01..03, CHAT-02..04, ACT-06, ACT-07).
- `.planning/ROADMAP.md` §Phase 2 — Success Criteria authoritative.
- `.planning/research/STACK.md` — Claude Code CLI, Gemma, llama.cpp, Windows Platform Specifics (locked versions).
- `.planning/research/PITFALLS.md` §1.x, §3.3, §3.4, §5.x, §9.x — upstream pitfalls that this research compounds with live-verified 2026 data.
- `.planning/research/ARCHITECTURE.md` — three-process model + `NYRA::Compat::` placeholder.
- `.planning/research/FEATURES.md` §TS10, TS11, TS12 — subscription status UI, undo, safe-mode competitor parity requirements.
- `.planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md` — D-01..D-20 forward-inherited.
- `.planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md` — Phase 1 research (WS, subprocess, SSE, markdown) reused.
- `docs/JSONRPC.md` — Phase 1 wire protocol; Phase 2 extends additively.
- `docs/ERROR_CODES.md` — Phase 2 extends with `-32007..-32014`.
- `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/` — Python package Phase 2 extends.

---

## Metadata

**Confidence breakdown:**
- Claude CLI surface: HIGH — verified 2026-04-22 against code.claude.com.
- NDJSON schema: MEDIUM-HIGH — outer wrapper + api_retry verified; inner event schema from Messages API spec (stable).
- FScopedTransaction nesting: HIGH — well-established Epic engine pattern.
- Four-version CI matrix: MEDIUM — self-hosted-runner pattern verified; specific UE drift points require Wave 0 empirical capture.
- EV code-signing: MEDIUM-HIGH — vendor + AKV path verified; D-U-N-S / identity timeline for solo founder is the main unknown.
- Console whitelist: HIGH — FOutputDevice and IConsoleManager patterns verified.
- Message Log tailing: HIGH — FMessageLog + FOutputDevice patterns verified.
- Subscription status UI: MEDIUM-HIGH — state model verified; exact `claude auth status` fields pending Wave 0 capture.
- Safe-mode preview contract: MEDIUM — `--permission-prompt-tool` is the documented path but production usage patterns need empirical validation.

**Research date:** 2026-04-22
**Valid until:** 2026-05-22 for Claude Code CLI surface (CLI ships weekly; re-verify before Phase 2 implementation). 2026-07-22 for UE CI + FScopedTransaction (stable). 2026-05-22 for EV cert pricing (subject to 1-year regulation cycles).
