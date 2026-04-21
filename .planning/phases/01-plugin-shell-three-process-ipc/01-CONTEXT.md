# Phase 1: Plugin Shell + Three-Process IPC - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning
**Source:** /gsd:discuss-phase (4 areas discussed, 2 deferred to Claude's Discretion)

<domain>
## Phase Boundary

Deliver the three-process skeleton proven end-to-end on UE 5.6: a dockable Slate chat panel in the Unreal editor round-trips prompts to a Python NyraHost sidecar over loopback WebSocket; NyraHost can spawn a bundled llama.cpp NyraInfer process serving Gemma 3 4B IT QAT Q4_0 GGUF over localhost HTTP (OpenAI-compatible). Nothing in this phase depends on Phase 0 legal clearance — it is legal-safe scaffolding that validates the architectural gate before Phase 2 wires subscription-driving code onto it.

**Requirements this phase satisfies:** PLUG-01, PLUG-02, PLUG-03, CHAT-01.

**Out of scope for Phase 1** (pushed to later phases):
- Claude Code CLI subprocess driving → Phase 2 (SUBS-01)
- Four-version CI matrix (5.4/5.5/5.7) → Phase 2 (PLUG-04); Phase 1 targets 5.6 only
- MCP server hosting, tool catalog, RAG → Phase 3+
- EV code-signing → Phase 2 (DIST-03 work)
- Subscription connection status UI → Phase 2 (CHAT-02)
- FScopedTransaction, safe-mode preview → Phase 2 (CHAT-03, CHAT-04)
- Embedding model + /v1/embeddings surface → Phase 3 RAG

</domain>

<decisions>
## Implementation Decisions

### Process Model (locked upstream, restated for clarity)
- **D-01:** Three processes: `UnrealEditor.exe + Nyra{Editor,Runtime}` (C++ plugin), `NyraHost` (embedded CPython running Python MCP sidecar), `NyraInfer` (bundled `llama-server.exe`). NyraHost and NyraInfer both run out-of-process so a crash or Gemma OOM never takes the editor down.
- **D-02:** Plugin ships as two modules per `.uplugin` descriptor: `NyraEditor` (editor-only, contains all Phase 1 functionality — Slate panel, WebSocket client, subprocess supervisor) and `NyraRuntime` (minimal runtime stub with no Phase 1 behaviour; exists so the `.uplugin` layout is Fab-ready for later runtime-facing features). Phase 1 ships `NyraRuntime` as empty `FDefaultModuleImpl`.
- **D-03:** Phase 1 validates on UE 5.6 only. UE 5.4/5.5/5.7 compile-test is a Phase 2 day-one deliverable via the four-version CI matrix; `NYRA::Compat::` shim does not need entries in Phase 1.

### NyraHost Lifecycle & Discovery
- **D-04:** **Spawn on editor start, when plugin loads** (eager). `FNyraEditorModule::StartupModule` launches NyraHost via `FPlatformProcess::CreateProc` with the plugin's embedded Python interpreter. Predictable — first chat message has zero cold-start latency. Expected idle footprint ~30-80 MB RAM (no model loaded yet).
- **D-05:** **Clean shutdown on editor close** — `FNyraEditorModule::ShutdownModule` sends a `shutdown` WS notification, gives NyraHost 2s to exit, then `FPlatformProcess::TerminateProc` as fallback. NyraHost flushes logs and closes SQLite before exit.
- **D-06:** **Ephemeral-port handshake file** — NyraHost binds `127.0.0.1:0`, writes a JSON handshake file to `%LOCALAPPDATA%/NYRA/handshake-<editor-pid>.json` containing `{port, token, nyrahost_pid, ue_pid, started_at}`. File permissions: Windows owner-only (DACL restricts to current user SID). UE polls for file with exponential backoff (50ms × 1.5, capped at 2s for 30s total), then connects. On disconnect UE deletes the handshake file; NyraHost rewrites on restart.
- **D-07:** **Shared-secret auth on first WS frame** — NyraHost generates a 32-byte cryptographically-random token (from `secrets.token_bytes`), stores it in the handshake file. UE's first WebSocket frame after `Connection: Upgrade` is `{"jsonrpc":"2.0","method":"session/authenticate","params":{"token":"<token>"}}`. NyraHost rejects any other first method with WS close code 4401 + reason `unauthenticated`. Defends against other local processes scanning 127.0.0.1.
- **D-08:** **Supervisor policy: 3 restarts in 60 seconds, then surface banner** — UE watches `nyrahost_pid` (handle valid + WS alive). On crash: respawn, replay the single in-flight request (if any) with a new `req_id`, mark original cancelled in the UI with a small "retried" badge. After 3 crash-restarts inside a 60-second window, stop auto-restart; panel shows a persistent banner: "NyraHost is unstable — see `Saved/NYRA/logs/` for details" with a `[Restart]` button and a `[Open log]` button.

### WebSocket Wire Protocol
- **D-09:** **JSON-RPC 2.0 envelope** for all UE↔NyraHost messages. Requests use `{jsonrpc:"2.0", id, method, params}`; responses use `{jsonrpc:"2.0", id, result}` or `{jsonrpc:"2.0", id, error:{code,message,data}}`; streaming + fire-and-forget uses notifications (no `id`). Matches MCP vocabulary so later phases reuse the same parser.
- **D-10:** **Phase 1 method surface** (minimum viable):
  - `session/authenticate` (req) — auth token handshake
  - `session/hello` (req→resp) — server capabilities { backends: ["gemma-local"], phase: 1 }
  - `chat/send` (req→resp) — `{conversation_id, req_id, content, backend?:"gemma-local"}`; resp returns immediately with `{req_id, streaming:true}`; tokens arrive via `chat/stream` notifications
  - `chat/stream` (notification from NyraHost) — `{conversation_id, req_id, delta, done:bool, cancelled?:bool, usage?:{…}, error?:{…}}`. One frame per model chunk (NOT per byte). Panel coalesces deltas before markdown-rendering.
  - `chat/cancel` (notification from UE) — `{conversation_id, req_id}`; NyraHost SIGTERMs the llama-server request (or closes the HTTP stream) and emits a final `chat/stream` with `done:true, cancelled:true`. Idempotent — re-sending is a no-op.
  - `shutdown` (notification from UE) — graceful close signal
- **D-11:** **Error codes** in `error.code`: `-32001 subprocess_failed`, `-32002 auth`, `-32003 rate_limit` (placeholder for Phase 2), `-32004 model_not_loaded`, `-32005 gemma_not_installed`, `-32006 infer_oom`. `error.message` is short programmatic; `error.data.remediation` is a human-copy string the panel renders as-is (e.g., "Gemma model missing. Click Download in Settings or run `nyra install gemma`.").
- **D-12:** **No binary framing; text JSON only.** Loopback bandwidth is free; debuggability (pipe `nyrahost.log` through `jq`) is worth more than the few-percent size win from msgpack.

### Python Runtime Distribution
- **D-13:** **Embedded CPython via python-build-standalone** — Plugin bundles `indygreg/astral-sh python-build-standalone` CPython 3.12 Windows x64 under `<Plugin>/Binaries/Win64/NyraHost/cpython/`. NyraHost is invoked as `cpython/python.exe -m nyrahost` (module entry point). ~35 MB compressed, ~120 MB installed. Editable during development (unlike PyInstaller). No user setup. Does not interfere with UE's built-in Python or any user-installed Python.
- **D-14:** **Pre-resolved wheel cache + requirements.lock** — Plugin ships `<Plugin>/Binaries/Win64/NyraHost/wheels/*.whl` for every pinned dep plus `requirements.lock`. First run: NyraHost bootstrap script creates `%LOCALAPPDATA%/NYRA/venv/` linked to the embedded CPython, runs `pip install --no-index --find-links=<wheels-dir> -r requirements.lock`. Subsequent runs reuse the venv. Completely offline-installable (airgap/NDA studios supported). Venv location is outside the plugin install dir so Fab-updating the plugin doesn't nuke venv state; a plugin-version marker file triggers venv rebuild on version change.
- **D-15:** **Phase 1 Python deps (pinned)** — `mcp>=1.2.0`, `websockets>=12.0` (loopback WS server), `httpx>=0.27` (llama-server HTTP client), `pydantic>=2.7` (message schemas), `structlog>=24.1` (JSON logging). Explicitly NOT adding `anthropic` SDK — Phase 2 brings in Claude CLI subprocess, not SDK.
- **D-16:** **Logging** — `structlog` emits JSON lines to `Saved/NYRA/logs/nyrahost-YYYY-MM-DD.log` with 7-day rotation (`logging.handlers.TimedRotatingFileHandler`, `when='midnight', backupCount=7`). Log schema: `{ts, level, logger, msg, req_id?, conv_id?, error_type?, error_message?}`. Uncaught exceptions are captured via `sys.excepthook` and surfaced to UE via the next outgoing `chat/stream` with an error frame carrying `data.remediation`. Phase 1 panel shows a collapsed "Diagnostics" drawer that `tail`s the latest 100 lines on demand.

### Gemma + llama.cpp Provisioning
- **D-17:** **Download-on-first-run with progress UI + SHA256 verify** — Phase 1 plugin ZIP stays small (~50-80 MB). First time the user invokes a Gemma-routed request (or clicks "Download local model" in Settings), panel shows a progress modal. Primary URL: HuggingFace CDN (`huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf/resolve/main/...`). Fallback: GitHub Releases mirror on NYRA's org (manually synced). Verify SHA256 against pinned hash (stored in plugin code), write to `Saved/NYRA/models/gemma-3-4b-it-qat-q4_0.gguf` (3.16 GB). Retryable, resumable (HTTP Range).
- **D-18:** **Bundled `llama-server.exe` + Ollama auto-detect fast path** — Plugin ships a pinned llama.cpp release (~20 MB, CPU + CUDA + Vulkan backends) as `<Plugin>/Binaries/Win64/NyraInfer/llama-server.exe`. On NyraHost startup it probes `http://127.0.0.1:11434/api/tags` (Ollama default). If reachable AND returns a `gemma3:4b-it-qat` model, use Ollama (faster first-token — model already in user's VRAM). Else spawn bundled `llama-server.exe -m <gguf> --port 0 --host 127.0.0.1 --ctx-size 16384 -ngl 99`. Port is captured from `llama-server`'s startup log. Phase 1 can leave `-ngl 99` hardcoded; GPU-probe + offload policy is a Phase 2 refinement.
- **D-19:** **Lazy spawn + 10-minute idle shutdown for NyraInfer** — NyraInfer only starts when NyraHost receives the first `chat/send` routed to `backend:"gemma-local"`. First-token cost: ~6-12s model load (panel shows "Warming Gemma…" indeterminate spinner in the assistant bubble). NyraHost tracks `last_infer_request_ts`; a background task checks every 60s and `SIGTERM`s NyraInfer if idle >10 min, returning 2-4 GB RAM. Next request re-spawns transparently.
- **D-20:** **OpenAI-compatible surface: chat only in Phase 1** — NyraHost calls `POST http://<infer_host>:<port>/v1/chat/completions` with `stream:true`. Responses parsed as SSE, re-emitted as JSON-RPC `chat/stream` notifications on the UE WebSocket. `/v1/embeddings` surface is NOT exercised in Phase 1 (no RAG, no second embedder model load) — that arrives in Phase 3.

### Chat Panel UX (Claude's Discretion)
The user deferred UI gray areas. Planner + UI work should default to these choices and revisit in a dedicated `/gsd:ui-phase 1` if the founder wants contracts locked before layout work:
- **CD-01:** **Full-width message layout** (ChatGPT-style), not bubbles. More legible for code blocks and long markdown answers; matches Aura's quality bar on panel depth.
- **CD-02:** **Dockable as a standard editor tab** via `RegisterTabSpawner("NyraChatTab", …)` under the `Tools > NYRA > Chat` menu. Default dock: right side panel, width 420 px.
- **CD-03:** **Input:** growing multiline textarea (min 3 rows, max 12, then internal scroll). Cmd/Ctrl+Enter submits; Enter inserts newline.
- **CD-04:** **Attachments:** drop zone on the input + `[+]` picker button. Phase 1 accepts files but only forwards paths over the WS (not uploaded content — NyraHost reads from disk). Supported types enforced at UI: image (png/jpg/webp), video (mp4/mov), text (md/txt).
- **CD-05:** **History navigator:** collapsed left drawer with current conversation list (pulled from SQLite). "New Conversation" button creates a fresh `conversation_id`. No branching/edit-previous in Phase 1.
- **CD-06:** **Markdown rendering:** bundle a lightweight Slate markdown widget (research task for planner: choose between `SRichTextBlock` with a custom decorator vs shipping a minimal renderer; evaluate the community `UIAssetSlateWidgetLibrary` patterns used by Aura). Code blocks must have a copy button.

### Conversation Persistence (Claude's Discretion)
- **CD-07:** **Per-project SQLite DB** at `<ProjectDir>/Saved/NYRA/sessions.db` (one DB per UE project, not per conversation — simpler query surface, cheaper fsync). Migrations via `PRAGMA user_version`. Phase 1 schema:
  - `conversations(id TEXT PRIMARY KEY, title TEXT, created_at INTEGER, updated_at INTEGER)`
  - `messages(id TEXT PRIMARY KEY, conversation_id TEXT REFERENCES conversations(id), role TEXT CHECK(role IN('user','assistant','system','tool')), content TEXT, created_at INTEGER, usage_json TEXT, error_json TEXT)`
  - `attachments(id TEXT PRIMARY KEY, message_id TEXT REFERENCES messages(id), kind TEXT, path TEXT, size_bytes INTEGER, sha256 TEXT)`
  - Indexes: `(conversation_id, created_at)` on messages.
- **CD-08:** **Attachments as file refs, not blobs** — user-provided files are hashed and hard-linked (or copied) into `Saved/NYRA/attachments/<sha256_prefix_2>/<sha256>.<ext>`. DB stores the `path` and `sha256`. Content-addressed dedup is free; panel can garbage-collect orphaned blobs on conversation delete.

### Claude's Discretion (Phase 1 latitude)
- Choice of WebSocket library on the UE side (between shipping our own minimal WS client in `NyraEditor` vs wrapping `LibWebSockets` — planner should evaluate binary-size / UE-version-stability trade-offs).
- Internal threading model inside `NyraEditor` (WS I/O on a dedicated thread, Slate updates marshalled to GameThread via `AsyncTask(ENamedThreads::GameThread, ...)`).
- NyraHost async runtime (asyncio event loop is the obvious choice given `websockets` + `httpx` both native; planner confirms).
- Handshake-file path discovery in UE — primary `%LOCALAPPDATA%/NYRA/`, fallback `Saved/NYRA/` if LOCALAPPDATA is unwritable.
- Conversation title autogeneration (first user message truncated to 48 chars for Phase 1; LLM-summarised title is a Phase 3+ nicety).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-level (mandatory)
- `.planning/PROJECT.md` — Vision, constraints, key decisions, quality bar ("parity is failure"), Codex-deferred-to-v1.1 lock, three-process architecture lock, Python sidecar lock
- `.planning/REQUIREMENTS.md` — v1 requirements with IDs. Phase 1 must address PLUG-01, PLUG-02, PLUG-03, CHAT-01
- `.planning/ROADMAP.md` §"Phase 1: Plugin Shell + Three-Process IPC" — success criteria, depends-on, requirements map
- `.planning/STATE.md` — current project state (if any relevant flags)

### Research synthesis (mandatory — deep technical context)
- `.planning/research/SUMMARY.md` — cross-researcher synthesis; §"Stack (Verified — LOCKED)" lists locked versions; §"Architecture Spine" documents the three-process model; §"Phase 1: Plugin Shell + Subscription Bridge" gives the Ring 0 pass criteria though the roadmap splits subscription-driving to Phase 2
- `.planning/research/STACK.md` — verified versions for Claude Code CLI v2.1.111+, MCP Python SDK, Gemma 3 4B IT QAT Q4_0 GGUF (3.16 GB, 128K, multimodal), llama.cpp/Ollama, computer-use tool type, BGE-small embedding
- `.planning/research/ARCHITECTURE.md` — twelve-component breakdown across the three processes; tool-as-contract pattern; out-of-process supervision pattern; NyraHost language decision gate (superseded: Python is locked per PROJECT.md)
- `.planning/research/FEATURES.md` — table-stakes vs differentiator taxonomy; Phase 1 maps to TS1 (chat panel) and is prerequisite for TS10 (subscription status UI, Phase 2)
- `.planning/research/PITFALLS.md` — §1 (subscription/legal — Phase 2 relevance), §3.3-3.4 (ABI drift — Phase 2; SmartScreen/EV — Phase 2), §9 (trust-through-transparency — Phase 2 CHAT-04; informs Phase 1 error-remediation decision D-11)

### External specs / protocol references
- MCP spec 2025-11-25 — `https://modelcontextprotocol.io/specification/2025-11-25/` — referenced for JSON-RPC 2.0 vocabulary choice (D-09); not yet implemented in Phase 1 (MCP server hosting is Phase 3)
- JSON-RPC 2.0 — `https://www.jsonrpc.org/specification` — wire envelope for UE↔NyraHost messages
- python-build-standalone — `https://github.com/astral-sh/python-build-standalone` — embedded CPython build we bundle (D-13)
- llama.cpp server README — `https://github.com/ggerganov/llama.cpp/blob/master/examples/server/README.md` — OpenAI-compatible endpoint flags (D-18, D-20)
- Ollama API — `https://github.com/ollama/ollama/blob/main/docs/api.md` — `/api/tags` probe endpoint (D-18)
- Gemma 3 4B IT QAT Q4_0 GGUF — `https://huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf` — download URL for D-17, pinned SHA256 lives here

### UE API references (planner must consult during plan creation)
- `FPlatformProcess::CreateProc` + `FProcHandle` + `FPlatformProcess::IsProcRunning` — subprocess lifecycle for NyraHost/NyraInfer
- `IModuleInterface::StartupModule` / `ShutdownModule` — plugin lifecycle hooks for D-04, D-05
- `FTabManager::RegisterTabSpawner` + `SDockTab` + `FSlateStyleSet` — Slate dockable tab infrastructure
- `FTickerDelegate` (UE 5.6: `FTSTicker::GetCoreTicker()`) — WS-polling / supervisor timer
- `.uplugin` descriptor reference — `https://dev.epicgames.com/documentation/en-us/unreal-engine/plugins-in-unreal-engine` — two-module layout D-02

[None of the above are "paid-course" sourced — all are license-safe per PITFALLS §8.1 hard block.]

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **None.** This is a greenfield UE plugin. Repo contains only `.planning/`, `README.md` (empty stub), and `CLAUDE.md` (project guidelines). No existing C++ / Python / Slate code.

### Established Patterns
- Project documentation patterns (GSD planning) — every phase has `CONTEXT.md` → `RESEARCH.md` → `PLAN.md` → execution. Honour that in Phase 1 file placement under `.planning/phases/01-plugin-shell-three-process-ipc/`.
- Requirement ID convention (PLUG-NN, CHAT-NN, SUBS-NN, …) defined in REQUIREMENTS.md — plan frontmatter must use these exact IDs.

### Integration Points
- **New plugin scaffolding:** `Plugins/NYRA/` under a UE 5.6 test host project (planner decides whether Phase 1 creates the test host project inside this repo under `TestProject/` or expects the user to have one).
- **Python sidecar source:** `Plugins/NYRA/Source/NyraHost/` (Python package) — lays the groundwork for Phase 2 MCP server + Phase 3 RAG inside the same package.
- **Binary distribution:** `Plugins/NYRA/Binaries/Win64/{NyraHost/, NyraInfer/}` — embedded CPython + pre-resolved wheels + `llama-server.exe`. Phase 1 planner must decide whether to commit these artefacts to the repo (LFS) or treat them as build-time downloads pulled by a bootstrap script.

</code_context>

<specifics>
## Specific Ideas

- **Ring 0 stability gate (from ROADMAP success criterion #3):** 100 consecutive WS round-trips on UE 5.6 with the editor remaining responsive during streaming. Planner should formalise this as a test harness (e.g., a `NyraDevTools` editor command `Nyra.Dev.RoundTripBench 100` that issues 100 pings and asserts each `<200 ms` p95 with streaming token demo). This is an architectural gate for Phase 2 — failing it blocks subscription-driving work.
- **`Tools > NYRA > Chat`** editor menu — not cluttering the level editor toolbar.
- **Handshake file location preference** — `%LOCALAPPDATA%/NYRA/` is the primary; `Saved/NYRA/` is the per-project fallback. Rationale: multiple UE editors can open the same project (rare), so editor-pid-scoped files avoid clashes; LOCALAPPDATA is also where the venv lives (D-14).
- **Panel "Diagnostics" drawer** (D-16) — collapsed by default, shows the last 100 log lines pulled on demand via a new WS method `diagnostics/tail` (planner adds to the method surface if it fits Phase 1 scope; otherwise Phase 2).

</specifics>

<deferred>
## Deferred Ideas

Scope-creep temptations caught during discussion, noted for later phases:
- **Subscription connection status UI** — deferred to Phase 2 (CHAT-02). Phase 1 panel does NOT show "Claude: connected / Gemma: ready" badges; that's dependent on the subscription bridge.
- **Safe-mode / dry-run preview** — Phase 2 (CHAT-04). Phase 1 has no tool calls to preview.
- **FScopedTransaction wrapping** — Phase 2 (CHAT-03). Phase 1 makes no mutations to UE state (chat-only skeleton), so no transactions needed.
- **Four-version CI matrix** — Phase 2 (PLUG-04). Phase 1 builds only for UE 5.6.
- **MCP server hosting + tool catalog** — Phase 3/4.
- **Embedding model + `/v1/embeddings` endpoint** — Phase 3 RAG.
- **Plugin module split scope refinement** — `NyraRuntime` is empty in Phase 1 (D-02); runtime-facing behaviour (e.g., runtime-world chat for in-game dev-console use) is a v2 conversation, not a Phase 1 lock.
- **Ring 0 benchmark harness** as a first-class subcommand (`Nyra.Dev.*`) — planner decides whether to include in Phase 1 scope or defer to Phase 2 once multi-version CI exists.
- **EV code-signing for Phase 1 binaries** — Phase 2 (DIST-03). Phase 1 users can manually bypass SmartScreen; devlog explains.
- **User-selectable model runner preference** (force-Ollama / force-bundled) — add as a Phase 2 setting if needed; Phase 1 auto-detect is good enough.
- **LLM-summarised conversation titles** — Phase 3+ nicety (CD-08 notes).

</deferred>

---

*Phase: 01-plugin-shell-three-process-ipc*
*Context gathered: 2026-04-21 via /gsd:discuss-phase*
*Areas discussed: NyraHost lifecycle + port handshake, WebSocket wire protocol, Python runtime distribution, Gemma + llama.cpp provisioning*
*Areas deferred to Claude's Discretion: Slate chat panel layout, conversation persistence schema*
