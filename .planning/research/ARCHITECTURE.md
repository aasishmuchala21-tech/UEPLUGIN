# Architecture Patterns

**Domain:** Unreal Engine 5 editor-integrated AI assistant plugin (hybrid C++ + MCP bridge, multi-backend, computer-use-capable)
**Researched:** 2026-04-21
**Overall confidence:** MEDIUM

> **Research-environment note:** This session had no access to live web search, Context7, or the shell at write time. The recommendations below are grounded in (a) the locked decisions in `.planning/PROJECT.md`, (b) well-established UE plugin architecture patterns from 5.4+ (stable across the target range), and (c) documented behaviour of MCP, Claude Code CLI, Codex CLI, llama.cpp, and Anthropic computer-use as of the training cutoff. **Every "likely"/"believed" claim is flagged with LOW/MEDIUM confidence and marked as a validation task for Phase 1.** Nothing marked HIGH relies on unverified training data.

---

## 1. Recommended Architecture

### 1.1 High-Level Topology

NYRA is **three cooperating processes** plus a set of **child processes spawned on demand**. This split is driven by three hard constraints:

1. UE5 editor cannot tolerate long-blocking or crash-prone code in-process (a Python runtime, a 4B-parameter model, or a Chromium-based computer-use agent would all risk taking the editor down).
2. Claude Code CLI and Codex CLI are **user-owned authenticated subprocesses** — their tokens live in the user's home directory, managed by the CLIs themselves. The plugin must not re-implement that auth; it drives the CLIs.
3. Fab-distributable plugins are expected to stay small and install-once. Heavy runtimes (llama.cpp, Python, Node) ship as bundled binaries invoked out-of-process.

```
+------------------------------------------------------------------+
|  PROCESS 1 — UnrealEditor.exe (user's UE install)                |
|                                                                  |
|  +-----------------------------------------------------------+   |
|  |  NYRA UE Plugin (C++)                                     |   |
|  |                                                           |   |
|  |   [1] UE Plugin Shell                                     |   |
|  |       - UNyraEditorSubsystem, UNyraRuntimeSubsystem       |   |
|  |       - Slate chat panel, status HUD, attachment dropzone |   |
|  |       - Command dispatcher (async, non-blocking)          |   |
|  |                                                           |   |
|  |   [2] Tool Catalog (UE-native tools)                      |   |
|  |       - Blueprint read/edit, Actor spawn, Material,       |   |
|  |         Lighting, Sequencer, Asset import                 |   |
|  |       - Each tool = C++ function + JSON schema            |   |
|  |                                                           |   |
|  |   [3] Asset Import Bridge                                 |   |
|  |       - .fbx/.glb → UStaticMesh, .png/.exr → UTexture2D,  |   |
|  |         .sbsar → UMaterial                                |   |
|  |                                                           |   |
|  |   [8] UE Compat Shim (5.4 / 5.5 / 5.6 / 5.7)              |   |
|  |       - Wraps NNE, Slate, Material Editor, Sequencer,     |   |
|  |         Niagara, Asset Tools APIs behind NYRA::Compat::*  |   |
|  +-----------------------------------------------------------+   |
|                       ^                                          |
|                       | Local IPC (named pipe / loopback WS)     |
|                       v                                          |
+------------------------------------------------------------------+
                        |
+------------------------------------------------------------------+
|  PROCESS 2 — NyraHost.exe (bundled with plugin)                  |
|                                                                  |
|   [4] MCP Host + Agent Router                                    |
|       - Speaks MCP to tool servers (local + remote stdio)        |
|       - Routes each turn: Claude | Codex | Gemma                 |
|       - Owns conversation/session state (SQLite on disk)         |
|                                                                  |
|   [5] Backend Drivers (subprocess managers)                      |
|       - Claude Code CLI driver (spawn+JSON stdio)                |
|       - Codex CLI driver (spawn+JSON stdio)                      |
|       - Local Gemma driver (→ NyraInfer.exe)                     |
|                                                                  |
|   [6] RAG / Knowledge Layer                                      |
|       - Bundled vector index (sqlite-vec or LanceDB)             |
|       - Embedding pipeline (local ONNX model)                    |
|       - Incremental updater (GitHub releases feed)               |
|                                                                  |
|   [7] Conversation / Session State                               |
|       - SQLite: messages, attachments, tool-call log,            |
|         computer-use screenshots, phase progress                 |
+------------------------------------------------------------------+
        |              |                    |             |
        | spawn        | spawn              | spawn       | HTTP/MCP
        v              v                    v             v
+------------+ +-------------------+ +----------------+ +-------------+
| Claude     | | Codex CLI         | | NyraInfer.exe  | | External    |
| Code CLI   | | (npx @openai/     | | (llama.cpp +   | | tools:      |
| subprocess | |  codex or pkg)    | |  Gemma 4B gguf)| | Meshy, CU,  |
+------------+ +-------------------+ +----------------+ | ComfyUI,    |
                                                       | Blender,     |
                                                       | Substance    |
                                                       +-------------+
```

### 1.2 Component Boundaries (the 12)

| # | Component | Lives In | Language | Responsibility | Talks To |
|---|-----------|----------|----------|----------------|----------|
| 1 | **UE Plugin Shell** | `UnrealEditor.exe` | C++ (UE module) | Editor UI (Slate), subsystems, command queue, user-facing chat panel | → (4) Agent Router over local IPC |
| 2 | **Tool Catalog** | `UnrealEditor.exe` | C++ (UE module) | UE-native tool implementations (BP/actor/material/lighting/Sequencer/Niagara) exposed as JSON-schema tools | ← called by (4) via IPC; uses (8) for version-safe APIs |
| 3 | **Asset Import Bridge** | `UnrealEditor.exe` | C++ (UE module) | Converts external tool outputs (.fbx/.glb/.sbsar/.png/.exr) into UE assets via `FAssetImportTask` | ← called by (2); ← invoked after (11) produces files |
| 4 | **MCP Host + Agent Router** | `NyraHost.exe` | Rust or C++ (decision below) | Hosts an MCP host; routes each turn to Claude / Codex / Gemma based on policy; aggregates tool responses | → (5), (6), (7); ↔ (1) |
| 5 | **Backend Drivers** | `NyraHost.exe` | same as (4) | Subprocess lifecycle for Claude Code CLI, Codex CLI, local Gemma; stdio JSON framing; heartbeat + restart | → CLIs + NyraInfer |
| 6 | **RAG / Knowledge Layer** | `NyraHost.exe` | same as (4) | Bundled vector store, embedder, retrieval + rerank; receives delta-updates signed by publisher | ← called by (4) at turn start |
| 7 | **Conversation / Session State** | `NyraHost.exe` | SQLite file | Persists chat, attachments, tool-call log, screenshots, phase progress. Survives editor restart | ↔ (1), (4) |
| 8 | **UE Compat Shim** | `UnrealEditor.exe` | C++ headers | `NYRA_IF_UE_VER(5,6, …)` branching for NNE, Slate, Material API, Sequencer deltas across 5.4–5.7 | linked into (1), (2), (3) |
| 9 | **Computer-Use Orchestrator** | `NyraHost.exe` + child OS actions | same as (4) | Screenshots (DXGI desktop duplication), mouse/keyboard (SendInput), window detection (EnumWindows + UIA), action log, user confirmation gate | ← called by (4) as an MCP tool; writes logs to (7) |
| 10 | **External Tool Adapters** | `NyraHost.exe` | same as (4) | Per-tool high-level recipes (Meshy web flow, ComfyUI API, Blender Python headless, Substance Sampler, Substance Player CLI). Some use (9), some use direct APIs | ← called by (4) as MCP tools; → (9) when GUI-only |
| 11 | **Asset Import Bridge staging** | disk | — | Watched folder + manifest file (`nyra_pending.json`) that (3) polls | written by (10), read by (3) |
| 12 | **Video Reference Analyzer** | `NyraHost.exe` + ffmpeg subprocess | same as (4) + ffmpeg | yt-dlp/ffmpeg keyframe extraction, scene detection, per-frame multimodal analysis (via Claude or Gemma-vision), plan generation | ← called by (4); → (6) for UE5 Sequencer docs; emits plan consumed by (2) |

**Why this split, not fewer pieces**: collapsing (4)+(5)+(6) into the UE plugin in-process means a Python or Rust runtime, a 4B model weight file, and multiple CLI subprocesses all share `UnrealEditor.exe`'s address space and process lifecycle. One crash or OOM in any of them takes the editor down mid-authoring. Competitors that *did* try in-process (some OSS MCP plugins) report exactly this instability. Splitting `NyraHost.exe` out is the single highest-leverage reliability decision.

**Why not more pieces** (e.g., one process per backend): process-per-backend triples install footprint, startup latency, and IPC debugging cost for a solo builder. Everything that can share `NyraHost.exe`'s lifecycle and logging should.

### 1.3 Protocol Choices

| Hop | Protocol | Rationale |
|-----|----------|-----------|
| UE Plugin Shell ↔ NyraHost | **Local WebSocket on 127.0.0.1** with length-prefixed JSON messages | UE's `FWebSocketsModule` is already built into the editor; works on 5.4–5.7 without extra deps. Named pipes are Windows-only-friendly but worse for debugging (can't point `wscat` at them). Pick loopback WS. [MEDIUM — alternative: UE has `IPC` classes, validate in Phase 1] |
| NyraHost ↔ Claude Code CLI | **stdio with line-delimited JSON** per Claude Code's `--output-format stream-json --verbose` | Official Claude Code CLI supports streamed JSON I/O for agent integration. [MEDIUM — verify exact flag names against current CLI in Phase 1] |
| NyraHost ↔ Codex CLI | **stdio with line-delimited JSON** per Codex CLI equivalent | Codex CLI exposes an equivalent non-interactive mode. [LOW — verify: confirm Codex CLI has stable scripting interface in Phase 1. If not, treat as research blocker.] |
| NyraHost ↔ NyraInfer (Gemma) | **stdio + OpenAI-compatible HTTP (localhost:N)** | llama.cpp's `llama-server` exposes an OpenAI-compatible endpoint, letting the Agent Router reuse one HTTP client for local + any future hosted model. [HIGH — this is well-established llama.cpp behaviour] |
| NyraHost ↔ MCP tool servers (built-in and future 3rd-party) | **MCP over stdio** (default) or **MCP over HTTP-SSE** for remote ones | Standard MCP transport. [HIGH] |
| NyraHost ↔ external APIs (Meshy, ComfyUI, Substance) | **HTTPS / local HTTP** per each | Meshy has an API; ComfyUI has a local HTTP + WS API. Substance 3D Sampler is GUI-only on Windows (use computer-use) unless we drive Substance Player CLI for non-Sampler assets. [MEDIUM — confirm in Phase 1 that we always prefer API over GUI when available] |

### 1.4 Language for `NyraHost.exe`

**Recommendation: Rust.** Reasoning:
- First-class MCP support (official Rust SDK plus `rmcp`, mature as of 2026). [MEDIUM — verify: Anthropic publishes TS/Python SDKs natively; Rust SDK existed in late-2025 community form. Check maturity in Phase 1.]
- llama.cpp has stable C FFI; Rust's `llama-cpp-2` crate is production-grade.
- Small static binary (<15MB before model), acceptable for Fab plugin bundle.
- Memory safety matters for a long-running host that manages subprocesses, websockets, and file IO.
- Avoids dragging a Python runtime into distribution (key Fab distribution win).

**Alternatives considered:**
- **C++ in NyraHost**: reuse Plugin Shell code. Rejected because: MCP SDK support for C++ is weak, and keeping host out of UE's build system accelerates iteration.
- **Node**: fast to ship, but `node.exe` adds ~60MB and startup latency. MCP TS SDK is the most mature, so this is a real second option if Rust MCP maturity lags in Phase 1 validation.
- **Go**: viable; rejected mainly on llama.cpp FFI ergonomics vs Rust.

**Phase 1 decision gate**: spike MCP host in both Rust and TS, pick based on SDK maturity + binary size measured, not guessed. Until that gate closes, the rest of this doc uses "NyraHost" as language-agnostic.

---

## 2. Data Flows (the 3 Core Workflows)

### 2.1 Workflow A — Chat Q&A ("how do I X in UE5?")

The happy-path baseline; exercises RAG + router + backend + UI round-trip, but no tools and no computer-use. **This is MVP Ring 0.**

```
[User] types question in Slate chat panel
   |
   v
[1] UE Plugin Shell
   - captures message, UE version, active asset context (optional)
   - sends JSON {type: "turn", text, context} over loopback WS
   |
   v
[4] Agent Router (NyraHost)
   - classifies intent: "knowledge query" → RAG-first route
   |
   v
[6] RAG Layer
   - embed query (local ONNX embedder, e.g., bge-small)
   - vector search over UE5 docs corpus (bundled index)
   - return top-K chunks with source URLs
   |
   v
[4] Agent Router
   - assembles prompt: system + retrieved chunks + user q
   - policy: default to Claude if connected, else Codex, else Gemma
   |
   v
[5] Claude Code CLI driver
   - spawn (or reuse) claude subprocess with --output-format stream-json
   - write prompt to stdin, read tokens from stdout
   |
   v
[4] Agent Router
   - streams tokens back over WS as {type: "token", delta} messages
   |
   v
[1] UE Plugin Shell
   - appends to Slate chat panel live
   - on final message, renders citations from RAG hits
   |
   v
[7] Session State
   - writes turn (user msg, assistant msg, citations, backend used) to SQLite
```

**Boundaries crossed:** UE process ↔ NyraHost (1 WS hop). No computer-use. No external tools. Everything else in-process within NyraHost.

**What stays local:** everything. No telemetry.

**Latency budget:** embed 30ms + retrieve 50ms + CLI spawn amortised (keep warm) + first-token from Claude ~500–1500ms.

### 2.2 Workflow B — Image → Scene ("here's a ref image, build a scene that matches")

Exercises: multimodal, Meshy computer-use, Substance, Asset Import Bridge, Tool Catalog. **This is MVP Ring 1.**

```
[User] drags image.png into chat, types "build a scene like this"
   |
   v
[1] UE Plugin Shell — sends {type: "turn", text, attachments: [file:...]}
   |
   v
[4] Agent Router
   - pins route to Claude (computer-use capable) even if Codex is also connected
   - loads "image→scene" recipe prompt + available tools manifest from (2),(10)
   |
   v
[5] Claude Code CLI driver
   - sends multimodal turn including image bytes
   - Claude plans: "extract subjects → Meshy per subject → Substance for ground
     material → spawn actors in UE → configure lighting → arrange camera"
   |
   v  (Claude emits MCP tool calls back to NyraHost)
   |
[10] External Tool Adapter: Meshy
   - has API? YES (Meshy has a documented image-to-3D API as of 2026)
   - POST image, poll job, download .glb to staging/<jobid>.glb
   - write (11) manifest entry
   [MEDIUM — verify Meshy API is still accessible at price-reasonable terms in Phase 1]
   |
   v
[3] Asset Import Bridge (inside UE process)
   - picks up manifest via file watcher, imports .glb → UStaticMesh
   - returns new asset path to Agent Router via WS
   |
   v
[10] External Tool Adapter: Substance (likely computer-use on Sampler)
   - invokes [9] Computer-Use Orchestrator with a Sampler recipe
   - OR falls back to ComfyUI PBR workflow if Sampler not installed
   |
   v
[9] Computer-Use Orchestrator
   - takes screenshot, asks Claude "click the Import button"
   - confirms bounding boxes with UI Automation (not pixel-matching alone)
   - emits clicks via SendInput, logs each action to (7) with screenshot
   - USER CONFIRMATION GATE on first action of a session (see §5)
   |
   v
[3] Asset Import Bridge — imports .sbsar or texture maps → UMaterial
   |
   v
[2] Tool Catalog
   - spawn_actor(static_mesh=<path>, location=<vec>)
   - set_material(actor, <mat>)
   - add_light(directional, color, intensity)
   - set_post_process(exposure, bloom)
   |
   v
[4] Agent Router — summarises what was done, cites assets
   |
   v
[1] UE Plugin Shell — shows "Scene ready" + list of actions with undo links
```

**Boundaries crossed:** UE ↔ NyraHost (ongoing WS), NyraHost → Claude CLI (one long-running session), NyraHost → Meshy API (HTTPS), NyraHost → OS (computer-use), NyraHost → disk (staging), UE ← disk (import watcher).

**What crosses MCP boundary:** tool schemas + tool calls + tool results. Never raw image bytes if avoidable (Claude gets the image via the multimodal turn; MCP tools pass file paths).

**What stays in-process:** RAG retrieval, session state, UE asset imports, compat shim dispatch.

### 2.3 Workflow C — Video → Matched Shot (launch demo, "paste YouTube link")

The showcase. Exercises everything above plus (12) Video Reference Analyzer and Sequencer.

```
[User] pastes https://youtu.be/abc in chat, "match this shot"
   |
   v
[1] UE Plugin Shell — {type: "turn", text: "...", refs:[{url: youtube...}]}
   |
   v
[4] Agent Router — routes to "video→shot" recipe
   |
   v
[12] Video Reference Analyzer
   - yt-dlp subprocess: download 720p stream to /tmp (LOW — verify Fab-legal: we
     are not redistributing; user pastes their own link. Document in §5.)
   - ffmpeg: scene detect (select='gt(scene,0.3)') → N keyframes
   - for each keyframe: multimodal analysis call (Claude vision) →
     {subjects, composition, lighting, camera_angle, time_of_day}
   - aggregate into SHOT_PLAN.json:
        { shots: [
            {t: 0.0, duration: 3.2, subjects:[...], camera:{fov, pos, target}},
            {t: 3.2, duration: 2.1, ...}
          ],
          global: {lighting, post, ambience}
        }
   |
   v
[6] RAG Layer — pulls UE5 Sequencer docs + Cine Camera + Niagara atmosphere
   |
   v
[4] Agent Router — asks Claude to convert SHOT_PLAN → concrete UE tool calls
   |
   v  (same pattern as Workflow B for any per-shot assets needed)
   |
[10] + [9] + [3]  — assets flow in
   |
   v
[2] Tool Catalog — Sequencer-specific tools:
   - create_level_sequence
   - add_cine_camera_actor
   - add_camera_cut_track (start, duration, camera_ref)
   - add_transform_track_keyframes (camera, [t,pos,rot,fov])
   - configure_post_process_volume
   - set_directional_light(rot, color, intensity)
   |
   v
[1] UE Plugin Shell — "Play in Sequencer" button + side-by-side with ref video
```

**Boundaries crossed:** UE ↔ NyraHost, NyraHost → yt-dlp/ffmpeg subprocesses, NyraHost → Claude multimodal (per keyframe, batched where possible), plus full Workflow B pipeline for each shot's assets.

**What crosses MCP boundary:** final SHOT_PLAN is just JSON; intermediate keyframes are local files referenced by path.

**What stays local:** downloaded video. Gets deleted from `/tmp` after run unless user opts in to keep.

---

## 3. Process Model (Explicit)

| Question | Answer | Rationale |
|----------|--------|-----------|
| Is UE editor + plugin one process? | **Yes.** Plugin is a standard UE C++ module loaded into `UnrealEditor.exe`. | No choice — this is how UE plugins work. |
| Is MCP server a separate process or in-proc? | **Separate process (`NyraHost.exe`), auto-spawned by the plugin on editor start.** | Crash isolation, language freedom for host, model weight footprint. |
| Is Claude Code CLI spawned per-session or long-running? | **One long-running subprocess per editor session**, driven via stream-json stdio; NyraHost keeps it warm, resets on error or N turns idle. | Spawn cost is non-trivial; warm CLI keeps auth, tool registrations, and prompt caching alive. |
| Is Codex CLI spawned per-session or long-running? | **Same model as Claude.** Parallel warm subprocess; only one active at a time per turn. | Symmetry with Claude reduces driver complexity. |
| Is local Gemma loaded in-editor or in a helper process? | **Helper process: `NyraInfer.exe`** (llama.cpp server bundled). | 4B model is ~3GB RAM when loaded; unacceptable to pin inside the editor. Helper can be stopped when user doesn't need offline. |
| Is Computer-Use a process? | **Runs inside NyraHost** (screenshot + SendInput are userspace Win32 APIs), but **each action is a discrete call** with its own log entry. | No need for extra process; isolation is at the action-log and confirmation-gate level, not the process level. |
| Who owns the SQLite session DB? | **NyraHost only.** UE plugin asks NyraHost for session state via WS. | Single writer avoids SQLite locking pain. |
| Startup order | Editor launches → plugin loads → plugin spawns NyraHost → NyraHost opens loopback WS on a dynamic port → plugin connects → NyraHost lazily spawns backends on first use. | NyraHost start should not block editor open (async; show "AI offline" in panel until up). |
| Shutdown order | Editor quits → plugin sends `shutdown` → NyraHost drains, kills Claude/Codex/Infer children, flushes SQLite, exits. Plugin hard-kills NyraHost after timeout. | Standard subprocess hygiene. |

---

## 4. Patterns to Follow

### Pattern 1: Tool-as-Contract
**What:** Every UE-native capability is a function with a JSON schema, registered at plugin init. Agent never calls UE APIs directly; it calls tools.
**When:** Any time the agent needs to change UE state.
**Example:**
```cpp
NYRA_TOOL("spawn_actor", "Spawn an actor in the current level")
NYRA_PARAM(FString, static_mesh_path, "Content path of the static mesh")
NYRA_PARAM(FVector, location, "World location in cm")
NYRA_RETURNS(FString, actor_name)
static FString SpawnActor(const FString& MeshPath, FVector Loc) { ... }
```
Schema is generated at compile time; exposed to MCP. This lets us evolve tools without touching the host or the agent prompts.

### Pattern 2: Out-of-Process for Anything That Can Fail
**What:** Any binary or runtime we don't control (Claude CLI, Codex CLI, llama.cpp, ffmpeg, yt-dlp, Blender headless) runs as a child process with timeouts, heartbeats, and automatic restart.
**When:** Always, for 3rd-party binaries.
**Why:** A hung CLI must never hang the editor.

### Pattern 3: File-Manifest Handoff for Imports
**What:** External tools never directly modify UE's content. They drop files into a staging dir and append an entry to `nyra_pending.json`. Asset Import Bridge watches that manifest and imports in the editor tick.
**When:** Any asset flowing from external tool → UE.
**Why:** Decouples NyraHost's write side from UE's content lifecycle; makes imports undoable and auditable.

### Pattern 4: Confirmation Gate on Computer-Use
**What:** First computer-use action in a session requires explicit user click in Slate. Thereafter, an "autopilot" window (default 5 min) allows subsequent actions; window resets on inactivity. High-risk actions (typing passwords, clicking system dialogs) always re-prompt.
**When:** Any SendInput / screenshot action.
**Why:** Trust + safety (§5). Non-negotiable.

### Pattern 5: Versioned Compat Shim
**What:** All API differences between UE 5.4/5.5/5.6/5.7 are wrapped behind `NYRA::Compat::` free functions with `#if ENGINE_MAJOR_VERSION == 5 && ENGINE_MINOR_VERSION >= 6` branches. Plugin code calls the shim, never UE APIs directly in drift-prone areas.
**When:** NNE, MaterialX, Sequencer, Niagara, Slate style, Asset Tools. [MEDIUM — exact drift list needs Phase 1 empirical check]
**Why:** One fork point per API keeps the four-version matrix tractable for a solo builder.

### Pattern 6: RAG-First, Then Agent
**What:** For any user turn that looks like a knowledge question, do retrieval before calling a backend, inject chunks, set citations to be rendered in UI.
**When:** All chat Q&A.
**Why:** Cheaper, more accurate, and makes the "bundled UE5 knowledge" feature visible.

---

## 5. Anti-Patterns to Avoid

### Anti-Pattern 1: Agent as UE-API Caller
**What:** Giving the agent direct access to arbitrary UE APIs or raw BlueprintScript.
**Why bad:** Unbounded action surface; every UE version bump is a possible break; impossible to audit or undo.
**Instead:** Strict Tool Catalog (Pattern 1). New capabilities require new tool definitions, which go through review.

### Anti-Pattern 2: Python-in-Editor Dependency
**What:** Shipping an embedded Python or Node runtime inside the plugin for agent orchestration.
**Why bad:** Fab distribution friction, runtime version conflicts with users' existing Python in UE, slows editor start.
**Instead:** NyraHost is a single static binary (Rust or Node-compiled-to-single-exe). Python is only used headlessly inside `Blender --python`, outside our process.

### Anti-Pattern 3: Blocking the Game Thread
**What:** Awaiting network/subprocess results synchronously in UE's game thread.
**Why bad:** Freezes editor, makes Slate unresponsive, looks broken.
**Instead:** All NyraHost calls are async via UE `FTSTicker` + futures; Slate panel shows a busy indicator.

### Anti-Pattern 4: Hidden Computer-Use
**What:** Running a computer-use action without the user seeing it.
**Why bad:** Erodes trust; one accidental misclick (e.g., closing Photoshop with unsaved work) kills the product.
**Instead:** Always-visible action log with live screenshot thumbnail; Pattern 4 confirmation gate.

### Anti-Pattern 5: Storing User Tokens
**What:** Having NYRA read and cache the user's Claude/Codex auth tokens.
**Why bad:** Creates a credential-theft attack surface; Anthropic and OpenAI both consider CLI auth user-owned; we'd take on compliance risk.
**Instead:** NYRA never reads tokens. It spawns the CLI; the CLI reads its own auth from its own config. If the user is not logged in, NYRA shows "Please run `claude login` in a terminal" — that's it.

### Anti-Pattern 6: Redistributing Third-Party Content
**What:** Bundling YouTube transcripts, Epic docs text, or community forum posts verbatim in the Fab plugin.
**Why bad:** Fab review rejection and legal exposure.
**Instead:** Bundle only license-clean content (Epic docs are permissive but verify; BP node reference is auto-generated from the SDK). Everything else ships as a **downloadable delta index** the plugin fetches on first run from a publisher-controlled CDN, letting us update takedowns post-hoc.

---

## 6. Security & Trust Boundaries

| Asset | Where It Lives | Who Reads It | Leaves Machine? | Mitigations |
|-------|----------------|--------------|-----------------|-------------|
| Claude subscription auth token | Claude Code CLI's own config dir (e.g., `%APPDATA%\claude\`) | Only the `claude` CLI | No (unless user opts into Anthropic telemetry) | NYRA **never** reads this. Validated by an install-time test that NYRA's process has no token in memory. |
| Codex subscription auth token | Codex CLI's own config dir | Only the `codex` CLI | No | Same as above. |
| User's prompts and generated code | `NyraHost.exe` → Claude CLI → Anthropic | Anthropic sees them (standard Claude API ToS) | Yes, to Anthropic | Shown in UI: "This turn will be sent to Claude." Privacy mode (Gemma-only) available. |
| User's screenshots (computer-use) | `NyraHost.exe` → Claude CLI → Anthropic | Anthropic sees them | Yes, to Anthropic | Confirmation gate; visible "now screenshotting" indicator; full log in (7) user can review/purge. |
| User's UE project assets | User's disk | UE + NYRA tools | Only if the agent sends file bytes to a tool; file paths OK | Default policy: never upload project files unless user explicitly attaches them. Meshy etc. only see explicitly-attached references. |
| Computer-use action log | SQLite in (7), plus screenshots in a session dir | User | No (unless user explicitly submits bug report) | Easy-to-find "Delete session" button. |
| NYRA's own code / updates | On disk | NYRA | No | Updater verifies code signing before loading. |
| RAG index deltas | Downloaded from publisher CDN | NYRA updater | Incoming only | Signed manifests; fail closed if signature invalid. |
| Telemetry (opt-in only) | NYRA anonymous usage counters | Publisher | Yes, only if opted in | Default off; never includes prompt content, screenshots, or file paths. |

**Computer-use constraint model:**
- Allowlist of target windows (user-confirmed per first use): Meshy web, Substance Sampler, ComfyUI, Blender, UE editor.
- Blocklist always-on: system dialogs (UAC, password prompts), browser auth flows, anything in an "Administrator" elevation context.
- Audit: every click/keystroke timestamped, windowed to the target app, screenshotted before and after. Log viewable in plugin.

**Code execution from agents:**
- **Blueprint edits** go through the Tool Catalog — the agent never emits raw BP text; it calls typed tool functions that construct BP nodes programmatically. [HIGH — this is the right shape; exact UE BP authoring APIs vary 5.4→5.7, needs shim]
- **C++ generation**, if added later, writes to disk and requires explicit user "Compile" confirmation. Not in v1.
- **Python/Blender scripts** run inside `blender --python` — Blender's own sandbox, not ours, but kept out-of-process.

**User content vs. telemetry:**
- **Stays local always:** UE project files, chat history, session state, screenshots, RAG index, computer-use logs.
- **Goes to Anthropic/OpenAI:** only what the user sends to the respective CLI (prompts, attachments).
- **Goes to Meshy/ComfyUI/Substance/Blender backends:** only the specific files the recipe needs.
- **Goes to NYRA publisher:** nothing by default. Opt-in anonymous counters post-v1.

---

## 7. Extension Points (Post-v1)

| Extension | Accommodated By | Changes Needed |
|-----------|-----------------|----------------|
| **Anthropic direct API backend** | Agent Router already speaks to Claude CLI via JSON; adding a parallel HTTP driver is a new Backend Driver (5) | New driver module; router gains a new route; prompt format unchanged. |
| **Gemini / Qwen / local Qwen** | Same pattern | Driver per backend; router policy gains new eligibility rules. |
| **Houdini / ZBrush** | New External Tool Adapter (10) + new Tool Catalog entries; recipe prompts added to (4) | Follows Meshy/Substance pattern. |
| **Shared team RAG index** | RAG Layer (6) factored so index source is pluggable: bundled local → hosted remote | Add hosted provider behind `IRagSource`; config in plugin UI. |
| **Shared team run history** | Session State (7) already in SQLite; replace with Postgres-over-HTTP behind `ISessionStore` | Abstracted in Phase 1 to make this cheap later. |
| **Fine-tuned UE model** | If hosted, becomes another Backend Driver (5). If local, NyraInfer swaps the gguf. | Either fits. No architectural change. |
| **macOS / Linux** | Plugin Shell is UE-cross-platform already; NyraHost needs per-OS builds; Computer-Use (9) is the hard part (SendInput is Win32) | Plan for cross-platform CU abstraction from the start. |
| **v2 Slack/Discord companion** | Talk to NyraHost's WS directly from any client | No UE dependency. |

**Key architectural property enabling all of the above:** everything the agent can do is expressed as tools and drivers, not as hardcoded calls. The extension surface is additive.

---

## 8. UE Version Compatibility (5.4 → 5.7)

**Scope of concern:** NNE, Editor Subsystems, Slate, Material API, Sequencer, Niagara, Asset Tools, Blueprint editing APIs.

### Compat Strategy

All affected code lives behind `NYRA::Compat::`:

```cpp
// NyraCompat.h
#pragma once
#include "Runtime/Launch/Resources/Version.h"

#define NYRA_UE_AT_LEAST(MAJ, MIN) \
    ((ENGINE_MAJOR_VERSION > MAJ) || \
     (ENGINE_MAJOR_VERSION == MAJ && ENGINE_MINOR_VERSION >= MIN))

namespace NYRA::Compat {
    // NNE: runtime discovery API varied across 5.4→5.7
    class INNERuntime;
    TSharedPtr<INNERuntime> CreateNNERuntime(FName Backend);

    // Material Editor: asset-edit path changed in one of the minor versions
    UMaterial* CreateMaterial(const FString& PackagePath, const FString& Name);

    // Sequencer: track creation helpers moved modules at least once
    UMovieSceneCameraCutTrack* AddCameraCutTrack(ULevelSequence* Seq);

    // Slate: a few style keys were renamed
    const FSlateBrush* GetPanelBrush();
}
```

Per-version impls in `NyraCompat_5_4.cpp`, `NyraCompat_5_5.cpp`, etc., selected at build via `#if NYRA_UE_AT_LEAST(5,5)`.

### Known Drift Hotspots

| Area | 5.4 vs 5.7 | Plan |
|------|-----------|------|
| **NNE (Neural Network Engine)** | Experimental in 5.4, more stable by 5.6; ORT backend APIs renamed; DML/CUDA availability differs | [MEDIUM confidence — needs Phase 1 empirical matrix test] If NNE is used at all (for local embedder or image→mesh), shim it *completely*, and feature-detect at runtime with a clear fallback to out-of-process llama.cpp / ONNX. |
| **Editor Subsystems** | Stable across 5.4–5.7 in general; `UEditorSubsystem` signatures unchanged. | Low risk; compile-test each version. |
| **Slate** | Generally stable; occasional style key renames. | Use `FAppStyle::Get()` — stable since 5.1. |
| **Material API (UMaterialEditingLibrary)** | Function signatures have shifted subtly; `CreateMaterialExpression` overloads differ | Shim every call site; hardest area to keep tidy. |
| **Sequencer** | `UMovieSceneSequencePlayer`, `UMovieSceneCameraCutTrack` APIs stable in 5.4+; Cine Camera settings expanded in 5.6 | Shim the expanded fields; default sensible on older versions. |
| **Niagara** | Scripting surface expanded; API mostly additive | Use only the intersection of APIs present in 5.4, plus feature-detect new ones. |
| **Asset Tools / Import** | `FAssetImportTask` stable, but `FbxImportUI` vs newer Interchange Framework differs | Prefer Interchange where available (5.5+), fall back to classic importers on 5.4. |
| **Blueprint editing (read/write graph)** | This is the highest-risk area for drift; internal `UEdGraph` APIs aren't guaranteed stable | [LOW — explicit Phase 1 research task: confirm we can author BP nodes cleanly on all four versions.] If not, degrade BP editing to "safe subset" (variable CRUD, simple node wiring) and raise risks for advanced graph edits. |

### Build & CI Implications

- **Four builds per release.** CI pipeline produces plugin binaries for 5.4, 5.5, 5.6, 5.7. Each runs a smoke-test UE project that exercises the Tool Catalog.
- Fab distribution packages one .zip containing all four target builds, selected at install per user's engine version.
- **Compat tests** are non-negotiable: every PR runs the full UE-side test suite on 5.4 and 5.7 (the corners), plus one midpoint alternating.

---

## 9. Build Order / Dependency Graph (Solo-Builder Topological Sort)

This is the opinionated sequence for a solo builder. Each ring is a demo-able slice; each unlocks the next by retiring specific risks.

```
Ring 0 — "It can talk"  (2–3 weeks)
  [1] UE Plugin Shell (minimal Slate panel, message list, text input)
  [4] Agent Router (NyraHost skeleton — WS server, message loop)
  [5] Claude Code CLI driver (only Claude; no Codex yet; no Gemma yet)
  [7] Session State (SQLite, one table)
  Demo: user asks a question in UE, Claude answers in the chat panel.
  Risks retired: process model, IPC, subprocess lifecycle, editor UI.

Ring 1 — "It knows UE"  (3–4 weeks)
  [6] RAG Layer (bundled index built from Epic docs only — legal-clean corpus)
  [8] UE Compat Shim (stub for 5.6 only initially)
  Demo: "How do I do soft shadows on a directional light in 5.6?" with citation.
  Risks retired: RAG quality, corpus-legality constraints, single-version build.

Ring 2 — "It changes UE"  (4–6 weeks)
  [2] Tool Catalog: first 6 tools — spawn_actor, place_static_mesh,
       set_material_parameter, add_light, set_post_process, create_level_sequence
  Agent Router learns to route between "Q&A" and "tool call" intents.
  Demo: "spawn 20 cubes in a spiral and make the middle one red."
  Risks retired: tool-as-contract shape, async editor-thread execution, undo.

Ring 3 — "It brings stuff in"  (3–4 weeks)
  [3] Asset Import Bridge
  [11] Staging / manifest
  [10] One External Tool Adapter with an API (Meshy — API-only, no CU yet)
  Demo: "generate a cartoon mushroom and put it on the ground."
  Risks retired: external-API-to-UE-asset round trip, watch/import pattern.

Ring 4 — "It drives other apps"  (4–6 weeks, highest-risk ring)
  [9] Computer-Use Orchestrator
  Confirmation gate, screenshot log, SendInput, window targeting via UIA
  [10] ComfyUI Adapter via local HTTP (no CU — prove API path first)
  [10] Substance Sampler via Computer-Use (CU's first real test)
  Demo: "make me a tileable mossy stone material" (ComfyUI OR Substance)
  Risks retired: computer-use reliability on Windows, user trust UX.

Ring 5 — "Image → scene"  (3–5 weeks)
  Scene-assembly recipe prompt in Agent Router
  More Tool Catalog: lighting presets, material author, camera framing
  Demo: ref image in → matching scene out. This is v1-launchable.
  Risks retired: end-to-end Workflow B; first public demo.

Ring 6 — "Video → matched shot"  (4–6 weeks, launch demo)
  [12] Video Reference Analyzer (yt-dlp + ffmpeg + multimodal keyframe loop)
  Sequencer tools in [2]
  Demo: YouTube link → matched Sequencer shot. THIS is the Fab launch demo.
  Risks retired: the distinguishing feature vs. competitors.

Ring 7 — "Works on all four UE versions"  (2–3 weeks, do before launch)
  Fill out [8] Compat Shim for 5.4, 5.5, 5.7 (we built on 5.6)
  CI matrix, smoke tests per version
  Risks retired: distribution to user base stuck on older versions.

Ring 8 — "Second backend + offline"  (3–4 weeks)
  [5] Codex CLI driver
  [5] + NyraInfer.exe + Gemma 4B gguf bundled
  Router policy for backend selection + user preference UI
  Risks retired: economic wedge breadth (Codex subs), offline/privacy mode.

Ring 9 — "Polish & Fab submission"  (3–4 weeks)
  Onboarding, error messages, telemetry-opt-in, Fab listing materials,
  documentation site, launch video.
```

**Critical path:** Ring 0 → 1 → 2 → 3 → 4 → 5 (launchable v0.9) → 6 (launch demo) → 7 (pre-launch compat) → 8 → 9.

**Parallel-safe:** Ring 7 (compat) can partially overlap with Rings 5–6 if the builder switches context each week. Ring 8 can slip to post-launch if 6–9 months runs tight (Codex + Gemma are economic/privacy moat, not launch-blocker).

**Cut lines (in order of what to drop if time runs out):**
1. Ring 8 (Codex + Gemma) — deliver v1 as Claude-only if needed; add in v1.1.
2. Niagara/fog support in Tool Catalog — lighting + materials + meshes is the viable minimum.
3. Blender adapter — if retopology quality is fine from Meshy default.
4. ComfyUI — if Substance Sampler + Meshy cover the asset-gen need.
5. Ring 6 polish — ship with "image → scene" as launch demo, video as post-launch feature. **This is a painful cut; avoid if at all possible — the video-to-shot demo is the explicit wedge.**

---

## 10. MVP Ring 0 Definition (Smallest Slice That Proves the Core Loop)

**Claim being validated:** *A UE5 plugin can embed a chat panel that relays to the user's Claude subscription with acceptable latency and stability across a full editor session.*

**Scope of Ring 0:**
1. Slate chat panel docked as an editor tab.
2. Text input → NyraHost → Claude Code CLI → streaming reply in panel.
3. Session persists across editor restart (SQLite).
4. No RAG, no tools, no attachments, no Codex, no Gemma.
5. Runs on UE 5.6 only (other versions deferred to Ring 7).
6. Windows only.
7. Requires user has run `claude login` in a terminal.

**Pass criteria:**
- [ ] Plugin loads in UE 5.6 without errors, panel opens.
- [ ] NyraHost spawns reliably on editor start, reconnects on crash.
- [ ] Round-trip to Claude is <2s to first token on a reasonable network.
- [ ] 100 consecutive turns in one editor session without plugin-side error.
- [ ] Editor remains responsive during Claude streaming (no main-thread stalls).
- [ ] Claude CLI auth failure produces a clear in-panel message, not silent death.

**Fail criteria (kill-the-scope triggers):**
- Claude Code CLI doesn't support stream-json for our use case → fall back to non-streaming (acceptable) or rethink (if non-streaming UX is bad enough).
- Editor-side WS stability is unreliable under load → switch IPC to named pipes.
- NyraHost cold start >3s → rework to async post-editor-load spawn.

**What Ring 0 explicitly does NOT validate:**
- Computer-use reliability (Ring 4)
- RAG retrieval quality (Ring 1)
- UE 5.4/5.5/5.7 compat (Ring 7)
- Tool Catalog safety (Ring 2)

Ring 0 is the foundation for every later ring. Until Ring 0 passes, no further rings ship.

---

## 11. Scalability Considerations

| Concern | At 1 user (solo dev, MVP) | At 1k users (post-launch) | At 100k users (future-state) |
|---------|---------------------------|---------------------------|------------------------------|
| RAG index size | ~200MB bundled | ~200MB + delta updates (auto) | Hosted index offered as opt-in |
| Session DB growth | Unbounded, no issue | Retention policy + VACUUM | User-configurable retention |
| Computer-use log storage | Keep everything | Rotate screenshots after 30d | Same + S3 offload for teams |
| Backend cost | User's own subs (not NYRA's problem) | Same | Same |
| Fab plugin size | Target <150MB without Gemma, <4GB with Gemma bundled or "download on first use" | Same | Same — Gemma download on first enable |
| Telemetry infra | None | Lightweight anonymous counters | Proper OTEL backend behind opt-in |
| Support load | Self | Community Discord + issue tracker | Dedicated support eng (future) |
| Publisher CDN | Static host (Cloudflare R2 / GitHub Releases) | Same | Same |

Because NYRA is client-side and BYO-subscription, there is essentially no NYRA-hosted infrastructure cost to worry about until Pro/teams tier.

---

## 12. Sources

**Authoritative (from PROJECT.md — HIGH confidence, locked decisions):**
- `.planning/PROJECT.md` — constraints, key decisions, out-of-scope list.

**Established general knowledge (MEDIUM confidence — relies on training data, not verified this session):**
- Unreal Engine plugin module architecture (stable pattern since UE 4.x).
- UE Editor Subsystem (`UEditorSubsystem`) lifecycle.
- UE `FWebSocketsModule`, `FAssetImportTask`, `FMovieSceneCameraCutTrack`.
- Model Context Protocol (MCP) specification, transports (stdio, HTTP-SSE).
- Claude Code CLI existence and stream-json output mode.
- Codex CLI existence and scripting interface.
- llama.cpp `llama-server` OpenAI-compatible HTTP API.
- Anthropic Computer Use tool specification for Windows.
- Meshy image-to-3D HTTP API.
- ComfyUI local HTTP + WS API.
- Blender headless `--python` scripting.
- yt-dlp + ffmpeg scene-change detection.

**Flagged for Phase 1 verification (LOW confidence without session access to verify):**
- Claude Code CLI exact `--output-format stream-json` flag name and stability contract.
- Codex CLI scripting interface maturity (biggest open question; could be blocker).
- MCP Rust SDK maturity vs. TypeScript SDK as of April 2026.
- UE NNE API drift across 5.4→5.7 (empirical matrix test required).
- UE Blueprint graph authoring API stability across 5.4→5.7.
- Meshy API availability and pricing in April 2026.
- Claude computer-use reliability percentiles on Windows 11 with Meshy web UI, Substance Sampler, ComfyUI.
- Fab distribution constraints on bundle size and child-process spawning.
- Legality of shipping extracted Epic docs text inside the plugin vs. downloading on first run.

Every item in that third block is an explicit **Phase 1 research task** for the roadmapper to fold in.
