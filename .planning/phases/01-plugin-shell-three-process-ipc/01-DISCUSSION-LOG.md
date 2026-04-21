# Phase 1: Plugin Shell + Three-Process IPC - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `01-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 01-plugin-shell-three-process-ipc
**Areas discussed:** NyraHost lifecycle + port handshake, WebSocket wire protocol, Python runtime distribution, Gemma + llama.cpp provisioning
**Areas deferred to Claude's Discretion:** Slate chat panel visual layout (skeleton), Conversation + attachment persistence schema

---

## Area Selection

User was presented with 6 candidate gray areas in two batches (AskUserQuestion max 4 options per question).

**Batch 1 — Plumbing (multiSelect):**

| Option | Description | Selected |
|--------|-------------|----------|
| NyraHost lifecycle + port handshake | When does NyraHost spawn? How does UE discover the WebSocket port? Crash-restart policy. Shared-secret auth on loopback (or trust 127.0.0.1)? | ✓ |
| WebSocket wire protocol | JSON-RPC 2.0 vs custom envelope. Streaming token delivery (per-token vs chunked). Request correlation, cancel semantics, error shape. | ✓ |
| Python runtime distribution | How NyraHost ships. PyInstaller/Nuitka one-exe vs embedded CPython vs user-managed Python. Gates zero-config install (DIST-04). | ✓ |
| Gemma + llama.cpp provisioning | Bundled 3.16 GB vs download-on-first-run (progress UI + SHA256) vs user-installed. Ollama auto-detect. NyraInfer eager vs lazy spawn. | ✓ |

**Batch 2 — UI + data (multiSelect):**

| Option | Description | Selected |
|--------|-------------|----------|
| Slate chat panel visual layout (skeleton) | Full-width vs bubbles. Input style. Attachment UX (drop zone, picker, both). History navigator placement. | (deferred) |
| Conversation + attachment persistence schema | SQLite schema. Per-project DB vs per-conversation files. Attachment storage. Editor-restart survival. | (deferred) |

**User's choice on Batch 2:** "you decide best" — deferred to Claude's Discretion. Captured as `CD-01` through `CD-08` in CONTEXT.md.

---

## Area 1: NyraHost lifecycle + port handshake

### Q1: When should NyraHost spawn?

| Option | Description | Selected |
|--------|-------------|----------|
| On editor start, when plugin loads | Predictable — first chat message has no cold-start latency. Costs ~30-80 MB idle RAM. Matches Aura/CoPilot feel. Editor close → NyraHost exits cleanly via PostEditorTick shutdown hook. | ✓ (Recommended) |
| Lazy on first chat message | Zero idle footprint; but first message pays 1-3s cold start (Python import + WebSocket bind). User sees "Starting NyraHost…" spinner. | |
| Lazy but warmed by idle timer | Spawn on first chat; keep alive indefinitely. Adds policy complexity; not worth it for a desktop plugin. | |

**User's choice:** On editor start, when plugin loads (Recommended)

### Q2: How does UE discover NyraHost's WebSocket port?

| Option | Description | Selected |
|--------|-------------|----------|
| NyraHost binds ephemeral port, writes handshake file | NyraHost binds 127.0.0.1:0, writes {port, token, pid} to handshake file, UE polls for file ready. Survives port conflicts. | ✓ (Recommended) |
| Stdout handshake line | UE spawns NyraHost with piped stdout, waits for `NYRA-READY port=NNNNN token=...` line. Tighter coupling; stdout-draining adds UE-side complexity. | |
| Fixed port with fallback range | Try 37317 first, fall back 37318…. Simple to debug; breaks if user has multiple UE editors open on same machine. | |

**User's choice:** NyraHost binds ephemeral port, writes handshake file (Recommended)

### Q3: Loopback-only WebSocket — use a shared secret?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — random token in handshake, required on first WS message | NyraHost generates 32-byte random token, writes it in the handshake file (owner-only), UE sends it in first WS frame. Defense against other local processes scanning 127.0.0.1. | ✓ (Recommended) |
| No — trust 127.0.0.1 binding | Simpler. Any local process can connect. Acceptable for prosumer dev tool; rejected by enterprise/NDA studios. | |

**User's choice:** Yes — random token in handshake (Recommended)

### Q4: NyraHost crash/restart policy?

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-restart up to 3 times in 60s, then surface error banner | UE's supervisor detects WS disconnect + dead PID → respawns → replays unacked in-flight messages. After 3 fails, panel shows persistent banner with log path + Restart button. | ✓ (Recommended) |
| Manual restart only — always show error banner on crash | Simpler. Worse UX — transient crashes during development need one-click restart. | |
| Unlimited auto-restart | Masks bugs. Rejected per PITFALLS §1.5 (silent failure anti-pattern). | |

**User's choice:** Auto-restart up to 3 times in 60s (Recommended)

---

## Area 2: WebSocket wire protocol

### Q1: Envelope format for UE↔NyraHost messages?

| Option | Description | Selected |
|--------|-------------|----------|
| JSON-RPC 2.0 | Standard {jsonrpc,id,method,params}/{jsonrpc,id,result\|error}. Request correlation built in. Notifications for streaming. Matches MCP vocabulary downstream. | ✓ (Recommended) |
| Custom JSON envelope | {type,req_id,payload} — simpler logs but reinvents correlation + error shape. | |
| MsgPack / binary | Smaller frames but loses debuggability; text JSON is fine on loopback. | |

**User's choice:** JSON-RPC 2.0 (Recommended)

### Q2: How should streaming tokens be delivered?

| Option | Description | Selected |
|--------|-------------|----------|
| JSON-RPC notification per chunk | {method:'chat/stream', params:{req_id, delta:'word ', done:false}}. One msg per model chunk. Final frame has done:true + usage stats. Panel coalesces deltas. | ✓ (Recommended) |
| Per-token messages | One WS frame per token. Overkill for loopback at Gemma's 20-60 tok/s. | |
| Batched SSE-style inside a single frame | Framing gymnastics inside a WS frame. Not worth the complexity. | |

**User's choice:** JSON-RPC notification per chunk (Recommended)

### Q3: Cancel-in-flight semantics?

| Option | Description | Selected |
|--------|-------------|----------|
| chat/cancel notification with req_id | User clicks Cancel → UE sends {method:'chat/cancel', params:{req_id}} → NyraHost SIGTERMs subprocess for that req → emits final chat/stream with done:true, cancelled:true. Idempotent. | ✓ (Recommended) |
| Close the WebSocket | Nukes all conversations, not just the one being cancelled. Not viable. | |

**User's choice:** chat/cancel notification with req_id (Recommended)

### Q4: Error shape when NyraHost / subprocess fails mid-stream?

| Option | Description | Selected |
|--------|-------------|----------|
| JSON-RPC error + data.remediation | Codes: -32001 subprocess_failed, -32002 auth, -32003 rate_limit, -32004 model_not_loaded, -32005 gemma_not_installed, -32006 infer_oom. data.remediation is human copy the panel renders as-is. Maps to PITFALLS §9.4 transparency. | ✓ (Recommended) |
| Plain string error in stream frame | Panel can't distinguish auth from rate_limit to show right UI. | |

**User's choice:** JSON-RPC error + data.remediation (Recommended)

---

## Area 3: Python runtime distribution

### Q1: How does Python get onto the user's machine for NyraHost?

| Option | Description | Selected |
|--------|-------------|----------|
| Embedded CPython (python-build-standalone) bundled in plugin binary | Ship indygreg/astral-sh CPython 3.12 as a subdirectory of the plugin. NyraHost runs as `python.exe -m nyrahost`. ~35 MB compressed. Zero user setup. Full pip/venv support. Editable during development. Proven by VS Code Python extensions. | ✓ (Recommended) |
| PyInstaller/Nuitka one-exe | Freezes NyraHost + its deps into NyraHost.exe. Slower dev iteration (rebuild per change). Harder to ship updated deps without plugin rebuild. AV false-positives more common on frozen exes. | |
| User-managed Python | Ask user to install Python 3.12 + pip install nyrahost. Breaks DIST-04 zero-config. Path hell on Windows. Rejected. | |
| UE's bundled Python (UnrealEnginePython) | In-process Python runs inside UnrealEditor.exe. Rejected per PLUG-02 + ARCHITECTURE.md: defeats crash-isolation. Only works in-editor. | |

**User's choice:** Embedded CPython (python-build-standalone) (Recommended)

### Q2: How are NyraHost's Python dependencies bundled?

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-resolved wheel cache shipped alongside embedded Python | Plugin ships `NyraHost/wheels/*.whl` for all pinned deps + requirements.lock. First run: embedded Python creates venv, pip installs from local wheel cache offline. Reproducible. Airgap-friendly. | ✓ (Recommended) |
| Internet pip install on first run | Smaller download but needs network on first run — fails in NDA/airgap. Non-reproducible. Not acceptable. | |
| Freeze deps into site-packages directly | Plugin ships pre-installed site-packages. No venv step. Harder to upgrade individual deps. | |

**User's choice:** Pre-resolved wheel cache + requirements.lock (Recommended)

### Q3: How are NyraHost stdout/stderr and exceptions logged?

| Option | Description | Selected |
|--------|-------------|----------|
| Rotating file logs under Saved/NYRA/logs/ + tail forwarded over WS | NyraHost writes structured JSON logs (ts, level, msg, req_id) to Saved/NYRA/logs/nyrahost-YYYY-MM-DD.log with 7-day rotation. Panel has a collapsed 'Diagnostics' drawer that tails the latest errors. All uncaught exceptions captured + reported via chat/error remediation frame. | ✓ (Recommended) |
| Stderr piped to UE Output Log only | Logs lost when editor closes. Harder to debug user bug reports. | |
| No logging — exceptions only | Debugging black-box NyraHost across Fab user base is impossible. | |

**User's choice:** Rotating file logs + tail over WS (Recommended)

---

## Area 4: Gemma + llama.cpp provisioning

### Q1: Where does the 3.16 GB Gemma 3 4B IT QAT Q4_0 GGUF come from?

| Option | Description | Selected |
|--------|-------------|----------|
| Download-on-first-run with progress UI + SHA256 verify | Phase 1 plugin install is tiny (~50 MB). First time user clicks 'Enable local fallback' or first Gemma-triggering request: panel shows progress bar, downloads from HuggingFace CDN (with a pinned mirror fallback on GitHub Releases), verifies SHA256, stores under Saved/NYRA/models/. Fab-friendly. | ✓ (Recommended) |
| Bundled in plugin ZIP | Bloats plugin to 3.2 GB. Bad Fab listing UX. Wastes bandwidth for users who only use Claude. | |
| User-managed — plugin uses whatever Ollama has locally | Simpler for plugin. Breaks zero-config. Rejected as default, but keep auto-detect as fast path. | |

**User's choice:** Download-on-first-run (Recommended)

### Q2: llama.cpp server binary — bundled or auto-detected?

| Option | Description | Selected |
|--------|-------------|----------|
| Bundle pinned llama-server.exe + prefer user's Ollama if detected | Plugin ships a pinned llama.cpp build (~20 MB, CUDA + Vulkan backends) as NyraInfer.exe. On startup NyraHost probes for Ollama (localhost:11434) — if present AND has gemma3:4b-it-qat, use it (faster first-token, user already paid RAM). Else spawn bundled NyraInfer. Graceful fallback. | ✓ (Recommended) |
| Bundle only, never use Ollama | Simpler code path but wastes resources for Ollama users (two copies of same model in RAM possible). Worse UX for power users. | |
| Require Ollama | Breaks zero-config. Rejected. | |

**User's choice:** Bundle pinned llama-server.exe + Ollama auto-detect (Recommended)

### Q3: NyraInfer process lifecycle?

| Option | Description | Selected |
|--------|-------------|----------|
| Lazy spawn + 10-min idle shutdown | NyraInfer only starts when first Gemma request fires. First-token cost: ~6-12s model load. Panel shows 'Warming Gemma…' spinner. Idle timer unloads after 10 min to return RAM. Next request re-spawns transparently. | ✓ (Recommended) |
| Eager spawn when NyraHost starts | Fast first local-token. Always 2-4 GB idle RAM. Slows editor start. Bad default; opt-in via Privacy Mode only. | |
| Keep alive forever once spawned | Never recovers RAM — bad for long editor sessions. | |

**User's choice:** Lazy spawn + 10-min idle shutdown (Recommended)

### Q4: OpenAI-compatible endpoint — what's the surface?

| Option | Description | Selected |
|--------|-------------|----------|
| POST /v1/chat/completions + /v1/embeddings | llama-server and Ollama both expose these natively. NyraHost's router uses the same HTTP client for Gemma and (later) hosted API fallbacks. /v1/embeddings gated behind a second small embedder model — Phase 1 ships chat only; embeddings model loads in Phase 3 RAG. | ✓ (Recommended) |
| Chat only; no embeddings endpoint in Phase 1 | Phase 1 skeleton just needs chat round-trip. Embeddings can be deferred. | (effectively same as above — embeddings deferred to Phase 3 per D-20) |

**User's choice:** Chat + embeddings surface defined, embeddings exercised in Phase 3 (Recommended)

---

## Scope-Check Gate

After all 4 areas discussed, user was offered:
- "Ready for context" (Recommended) ← chosen
- "One more area: plugin module split scope"
- "One more area: Ring 0 success gate details"

Both additional areas were captured in CONTEXT.md `<deferred>` section rather than re-opened (D-02 already locks the module split; Ring 0 harness noted for planner to scope).

## Claude's Discretion

Areas deferred to downstream planning per user's "you decide best":
- Slate chat panel visual layout → CONTEXT.md §"Chat Panel UX (Claude's Discretion)" CD-01 through CD-06
- Conversation + attachment persistence schema → CONTEXT.md §"Conversation Persistence (Claude's Discretion)" CD-07, CD-08

Additional latitude captured inline in CONTEXT.md `<decisions>` §"Claude's Discretion (Phase 1 latitude)":
- UE-side WebSocket library choice (minimal own vs LibWebSockets wrapper)
- NyraEditor threading model (WS I/O thread → GameThread marshalling)
- NyraHost asyncio event loop choice
- Handshake-file discovery fallback path (LOCALAPPDATA primary, Saved/NYRA/ fallback)
- Conversation title autogeneration strategy

## Deferred Ideas

Scope-creep temptations, captured in CONTEXT.md `<deferred>`:
- Subscription connection status UI (→ Phase 2 CHAT-02)
- Safe-mode / dry-run preview (→ Phase 2 CHAT-04)
- FScopedTransaction wrapping (→ Phase 2 CHAT-03)
- Four-version CI matrix (→ Phase 2 PLUG-04)
- MCP server hosting + tool catalog (→ Phase 3/4)
- `/v1/embeddings` actually exercised (→ Phase 3 RAG)
- NyraRuntime module behaviour beyond empty stub (→ v2 conversation)
- Ring 0 benchmark harness as first-class `Nyra.Dev.*` subcommand (→ planner scoping; possibly Phase 2 after multi-version CI)
- EV code-signing (→ Phase 2 DIST-03)
- User-selectable force-Ollama / force-bundled setting (→ Phase 2 if needed)
- LLM-summarised conversation titles (→ Phase 3+)
