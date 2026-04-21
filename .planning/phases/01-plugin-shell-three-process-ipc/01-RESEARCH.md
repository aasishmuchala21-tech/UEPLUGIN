# Phase 1: Plugin Shell + Three-Process IPC — Research

**Researched:** 2026-04-21
**Domain:** UE 5.6 C++ editor plugin + Python sidecar + llama.cpp server, loopback WebSocket IPC
**Confidence:** MEDIUM-HIGH (plugin scaffolding / WS / subprocess / llama-server all HIGH; Slate markdown renderer MEDIUM; exact python-build-standalone release tag MEDIUM pending registry check at plan time; Ollama auto-detect HIGH; handshake concurrency LOW — requires empirical validation in Plan)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (D-NN)

**Process Model**
- **D-01:** Three processes: `UnrealEditor.exe + Nyra{Editor,Runtime}` (C++ plugin), `NyraHost` (embedded CPython running Python MCP sidecar), `NyraInfer` (bundled `llama-server.exe`). NyraHost and NyraInfer both run out-of-process.
- **D-02:** Plugin ships as two modules per `.uplugin` descriptor: `NyraEditor` (editor-only, contains all Phase 1 functionality — Slate panel, WebSocket client, subprocess supervisor) and `NyraRuntime` (minimal runtime stub; `FDefaultModuleImpl` in Phase 1).
- **D-03:** Phase 1 validates on UE 5.6 only. UE 5.4/5.5/5.7 compile-test is a Phase 2 deliverable; `NYRA::Compat::` shim does not need entries in Phase 1.

**NyraHost Lifecycle & Discovery**
- **D-04:** Eager spawn on editor start, in `FNyraEditorModule::StartupModule` via `FPlatformProcess::CreateProc`.
- **D-05:** Clean shutdown on editor close — WS `shutdown` notification, 2s grace, then `FPlatformProcess::TerminateProc` as fallback. NyraHost flushes logs and closes SQLite.
- **D-06:** Ephemeral-port handshake — NyraHost binds `127.0.0.1:0`, writes `%LOCALAPPDATA%/NYRA/handshake-<editor-pid>.json` with `{port, token, nyrahost_pid, ue_pid, started_at}`. Windows owner-only DACL. UE polls with 50ms × 1.5 exponential backoff (capped at 2s, 30s total). On disconnect UE deletes the handshake file.
- **D-07:** 32-byte shared-secret auth token from `secrets.token_bytes`. UE's first WS frame is `session/authenticate`. Unauthenticated first methods → WS close code 4401 + reason `unauthenticated`.
- **D-08:** Supervisor: 3 restarts in 60s, then banner with `[Restart]` and `[Open log]`. Crash respawn replays single in-flight request with new `req_id`, original marked cancelled with "retried" badge.

**WebSocket Wire Protocol**
- **D-09:** JSON-RPC 2.0 envelope. Matches MCP vocabulary for later phase reuse.
- **D-10:** Phase 1 method surface: `session/authenticate`, `session/hello`, `chat/send`, `chat/stream` (notification), `chat/cancel` (notification), `shutdown` (notification).
- **D-11:** Error codes `-32001 subprocess_failed`, `-32002 auth`, `-32003 rate_limit`, `-32004 model_not_loaded`, `-32005 gemma_not_installed`, `-32006 infer_oom`; `error.data.remediation` is a human-copy string the panel renders as-is.
- **D-12:** Text JSON only, no binary framing.

**Python Runtime Distribution**
- **D-13:** Embedded CPython 3.12 via `astral-sh/python-build-standalone`, Windows x64, at `<Plugin>/Binaries/Win64/NyraHost/cpython/`. Invoked as `cpython/python.exe -m nyrahost`.
- **D-14:** Pre-resolved wheel cache + `requirements.lock`. First-run bootstrap: create venv at `%LOCALAPPDATA%/NYRA/venv/` linked to embedded CPython, `pip install --no-index --find-links=<wheels-dir> -r requirements.lock`. Plugin-version marker file triggers venv rebuild on version change.
- **D-15:** Phase 1 deps: `mcp>=1.2.0`, `websockets>=12.0`, `httpx>=0.27`, `pydantic>=2.7`, `structlog>=24.1`. NOT adding `anthropic`.
- **D-16:** `structlog` JSON logs to `Saved/NYRA/logs/nyrahost-YYYY-MM-DD.log` with 7-day rotation via `TimedRotatingFileHandler(when='midnight', backupCount=7)`. Uncaught exceptions via `sys.excepthook` surface to UE via next `chat/stream` error frame.

**Gemma + llama.cpp Provisioning**
- **D-17:** Download-on-first-run with progress UI + SHA256 verify. Primary URL: `huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf/resolve/main/...`. Writes to `Saved/NYRA/models/`. Retryable, resumable (HTTP Range).
- **D-18:** Bundled `llama-server.exe` (CPU + CUDA + Vulkan) at `<Plugin>/Binaries/Win64/NyraInfer/llama-server.exe`. Ollama auto-detect fast path: probe `http://127.0.0.1:11434/api/tags`; if `gemma3:4b-it-qat` present, use Ollama. Else spawn `llama-server -m <gguf> --port 0 --host 127.0.0.1 --ctx-size 16384 -ngl 99`. Port captured from startup log.
- **D-19:** Lazy spawn + 10-min idle shutdown for NyraInfer. Background task every 60s, SIGTERM if idle >10 min.
- **D-20:** OpenAI-compatible surface: chat only in Phase 1. `POST /v1/chat/completions` with `stream:true`; SSE re-emitted as `chat/stream` notifications. `/v1/embeddings` NOT exercised in Phase 1.

### Claude's Discretion (CD-NN)

- **CD-01:** Full-width message layout (ChatGPT-style), not bubbles.
- **CD-02:** Dockable editor tab via `RegisterTabSpawner("NyraChatTab", …)` under `Tools > NYRA > Chat`. Default dock: right side panel, width 420 px.
- **CD-03:** Growing multiline textarea (min 3 rows, max 12, then internal scroll). Cmd/Ctrl+Enter submits; Enter inserts newline.
- **CD-04:** Attachments drop zone on input + `[+]` picker button. Phase 1 forwards paths only (not uploaded content). Types: image (png/jpg/webp), video (mp4/mov), text (md/txt).
- **CD-05:** Collapsed left drawer history navigator pulled from SQLite. "New Conversation" button. No branching/edit-previous in Phase 1.
- **CD-06:** Markdown rendering: bundle a lightweight Slate markdown widget. Code blocks must have a copy button. (Research task — see §3.1.)
- **CD-07:** Per-project SQLite DB at `<ProjectDir>/Saved/NYRA/sessions.db`. Migrations via `PRAGMA user_version`. Schema: `conversations`, `messages`, `attachments` tables. Indexes: `(conversation_id, created_at)` on messages.
- **CD-08:** Attachments as file refs (not blobs) hard-linked/copied into `Saved/NYRA/attachments/<sha256_prefix_2>/<sha256>.<ext>`. Content-addressed dedup.

### Latitude items (planner decides)

- UE WebSocket library choice (see §3.2 — recommendation: use bundled `WebSockets` module).
- Internal threading model inside `NyraEditor` (WS I/O on dedicated thread; Slate updates marshalled to GameThread via `AsyncTask(ENamedThreads::GameThread, ...)`).
- NyraHost async runtime: `asyncio` event loop (confirmed — both `websockets` and `httpx` are native asyncio).
- Handshake file path primary `%LOCALAPPDATA%/NYRA/`, fallback `Saved/NYRA/` if LOCALAPPDATA unwritable.
- Conversation title autogen: first user message truncated to 48 chars (Phase 1).

### Deferred Ideas (OUT OF SCOPE for Phase 1)

- Subscription connection status UI → Phase 2 (CHAT-02)
- Safe-mode / dry-run preview → Phase 2 (CHAT-04)
- `FScopedTransaction` wrapping → Phase 2 (CHAT-03)
- Four-version CI matrix → Phase 2 (PLUG-04)
- MCP server hosting + tool catalog → Phase 3/4
- Embedding model + `/v1/embeddings` → Phase 3 RAG
- `NyraRuntime` runtime-facing behaviour → v2 conversation
- Ring 0 benchmark harness as first-class `Nyra.Dev.*` subcommand (planner decides inclusion; see §3.6)
- EV code-signing for Phase 1 binaries → Phase 2 (DIST-03). SmartScreen warning is accepted, documented in devlog.
- User-selectable model runner preference (force-Ollama / force-bundled) → Phase 2 setting
- LLM-summarised conversation titles → Phase 3+
- `diagnostics/tail` method — planner adds to Phase 1 only if it fits budget; else Phase 2.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **PLUG-01** | Plugin ships as native UE5 C++ plugin with two modules (`NyraEditor`, `NyraRuntime`), installable on Windows for UE 5.4/5.5/5.6/5.7 | §3.8 `.uplugin` + Build.cs patterns. **Phase 1 scope:** UE 5.6 only (D-03); the full matrix ships in Phase 2. |
| **PLUG-02** | Plugin hosts a Python MCP sidecar process (`NyraHost`) communicating with the editor over a loopback WebSocket; NyraHost hosts the MCP server, agent router, RAG, and session state | §3.2 WebSocket transport, §3.3 subprocess supervision, §3.4 embedded Python, §3.9 first-run bootstrap. Phase 1 ships the WS plumbing + Python process; MCP server hosting lands in Phase 3. |
| **PLUG-03** | Plugin launches a llama.cpp inference process (`NyraInfer`) for Gemma 3 4B IT QAT Q4_0 GGUF exposed over localhost HTTP | §3.5 llama-server flags + Ollama detect, §3.9 Gemma download flow. |
| **CHAT-01** | Dockable in-editor Slate chat panel with streaming tokens, markdown rendering, code blocks, image/video/file attachments, and per-conversation history persisted under project `Saved/NYRA/` | §3.1 SRichTextBlock + custom decorator, §3.7 SQLite schema, §3.9 first-run UX. |
</phase_requirements>

---

## Phase Goal Restated

Deliver the **three-process skeleton** proven end-to-end on UE 5.6: a dockable Slate chat panel in the Unreal editor round-trips prompts to a Python NyraHost sidecar over loopback WebSocket; NyraHost spawns a bundled llama.cpp NyraInfer process serving Gemma 3 4B Q4_0 over localhost HTTP (OpenAI-compatible). Ring 0 "it can talk." Everything legal-safe — no subscription-driving code. The 100-round-trip stability gate and the `.uplugin` two-module layout unblock Phase 2 (Claude subscription bridge + four-version CI).

---

## What's Already Decided

CONTEXT.md locks 20 `D-NN` decisions and 8 `CD-NN` Claude's-discretion defaults. Planner MUST treat `D-NN` as non-negotiable. `CD-NN` items are the default but can be revisited in a dedicated `/gsd:ui-phase 1` if contracts need to be locked before layout work.

Key lock summary (full text above in `<user_constraints>`):

- Three processes (UE + NyraHost + NyraInfer) out-of-process.
- NyraHost eager-spawn on editor start; graceful WS `shutdown` then `TerminateProc` fallback.
- Handshake via `%LOCALAPPDATA%/NYRA/handshake-<editor-pid>.json` with 32-byte shared-secret token; UE polls with exp backoff.
- JSON-RPC 2.0 text envelope, 6-method surface. Error codes `-32001..-32006` with `data.remediation`.
- Embedded CPython 3.12 (python-build-standalone) + pre-resolved wheel cache; venv bootstrap at first run.
- `structlog` JSON logs with 7-day rotation.
- Gemma download-on-first-run (HF primary, GitHub mirror fallback), SHA256-verified, HTTP Range-resumable.
- Bundled `llama-server.exe` + Ollama auto-detect via `http://127.0.0.1:11434/api/tags`.
- Lazy-spawn + 10-min idle shutdown for NyraInfer.
- Chat-only `/v1/chat/completions`, SSE → `chat/stream` JSON-RPC notifications.
- Panel: full-width ChatGPT-style layout; dockable nomad tab under `Tools > NYRA > Chat`; SQLite per-project `sessions.db`; attachments as content-addressed file refs.

---

## Project Constraints (from CLAUDE.md)

- GSD workflow enforcement: file-changing tools go through `/gsd-quick`, `/gsd-debug`, or `/gsd-execute-phase`. Direct repo edits outside a GSD workflow are forbidden unless user explicitly asks.
- Stack block mirrors `.planning/research/STACK.md` verbatim — plans should cite STACK for locked versions, not re-state them.
- No architecture or conventions are established in-repo yet (greenfield). Plans establish the first patterns.

---

## Research Findings

### 3.1 Slate Panel Mechanics for CHAT-01 Depth

**Primary recommendation:** Build on `SRichTextBlock` with a custom `URichTextBlockDecorator` / `FRichTextDecorator` stack. Parse markdown → rich-text tag stream in NyraEditor before handing to the widget. This is the same approach Epic uses internally for tooltips, quest logs, and dialogue UIs, and is the path Aura's panel appears to follow (inferred from their panel polish characteristics; not inspected directly).

**Key widgets and classes (UE 5.6, all in `SlateCore` + `Slate` modules):**

| Widget | Role | Notes |
|--------|------|-------|
| `SDockTab` (`ETabRole::NomadTab`) | The outer tab host | Returned from the tab-spawner callback. |
| `SVerticalBox` / `SSplitter` / `SBorder` | Panel layout primitives | Full-width message list + bottom composer is a two-slot `SVerticalBox`. |
| `SScrollBox` + `SListView<TSharedPtr<FNyraMessage>>` | Message list | `SListView` handles virtualization when history grows; use `SetScrollOffset` to pin to bottom during streaming. |
| `SRichTextBlock` | Markdown-rendered assistant/user bubbles | One per message. `AutoWrapText(true)`, `WrapTextAt(AvailableWidth)`. |
| Custom `URichTextBlockDecorator` subclasses | Parse `<code>...</code>`, `<bold>`, `<italic>`, `<link>` tags, and a bespoke `<nyra-code lang="python">...</nyra-code>` tag | Decorator's `Supports(tag)` returns true for handled tags; `CreateDecoratorWidget` returns a custom `TSharedRef<ITextDecorator>`. See the Epic tooltip sample at `github.com/Nauja/ue4-richtextblocktooltip-sample` as a concrete reference pattern. |
| `SMultiLineEditableTextBox` | Composer input | Supports multiline. Hook `OnKeyDownHandler` to detect `Ctrl+Enter` for submit. Use `SetText` for programmatic clear. |
| `SFileDialog` / `FDesktopPlatform::Get()->OpenFileDialog` | Attachment picker (`[+]` button) | Returns `TArray<FString>` of selected paths. |
| Custom `SAttachmentChip` (new `SCompoundWidget`) | Displayed chips above composer | Icon + filename + `[x]` remove button. Phase 1 does NOT upload — just sends paths over WS. |
| `SButton` with `STextBlock` | "Copy" button on code blocks | `OnClicked` handler calls `FPlatformApplicationMisc::ClipboardCopy(*CodeText)`. |
| `SBox` + `SCircularThrobber` | Warming Gemma / streaming indicator | Indeterminate spinner inside the assistant bubble while awaiting first token. |

**Streaming token render strategy (HIGH importance for perceived performance):**

1. NyraHost batches model chunks into `chat/stream` notification frames (one frame per model chunk, not per byte — per D-10).
2. On each frame, GameThread-marshalled handler appends `delta` to an `FString FMessage::StreamingBuffer`.
3. Decorators are EXPENSIVE on each parse — do NOT call `SetText` on the `SRichTextBlock` per-delta. Instead, use a plain `STextBlock` during streaming and swap to `SRichTextBlock` with markdown decoration on `done:true`. This avoids re-parsing a growing markdown string 200 times during a 5-second response.
4. Alternative (more ambitious): parse incrementally, only re-parse the tail paragraph. Phase 1 should ship the simpler "plain during stream, rich on done" approach; incremental parse is a Phase 2 polish item.

**Markdown parser choice:**

- **Bundle a minimal markdown-to-slate-rich-text converter** as a C++ helper in `NyraEditor/Private/Markdown/`. Scope: headings (`#`, `##`, `###`), bold/italic, inline code (backticks), fenced code blocks (```), links, unordered lists. No tables, no images, no HTML passthrough in Phase 1.
- Existing OSS options (e.g., `md4c` — MIT) can be vendored if the planner prefers a battle-tested parser. `md4c` is ~3k LOC C and trivial to include via `PublicAdditionalLibraries` in Build.cs, but its CommonMark strictness may be overkill. A hand-rolled ~500 LOC Markdown-subset parser is acceptable for Phase 1.
- The parser OUTPUT is Slate rich-text markup (e.g., `<bold>...</bold>`, `<nyra-code lang="python">...</nyra-code>`), which the decorator stack renders.

**Confidence:** HIGH on the `SRichTextBlock` + `URichTextBlockDecorator` pattern (officially documented, stable across 4.26 → 5.7+ per Epic docs). MEDIUM on exact streaming-render strategy (empirical Slate behaviour under rapid `SetText` calls not verified; planner's Wave 3 should include a throughput spike).

**Citations:**
- `https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Slate/Widgets/Text/SRichTextBlock` (UE 5.x)
- `https://www.unrealengine.com/en-US/tech-blog/advanced-text-styling-with-rich-text-block`
- `https://github.com/Nauja/ue4-richtextblocktooltip-sample` — worked URichTextBlockDecorator + FRichTextDecorator sample
- `https://github.com/YawLighthouse/UMG-Slate-Compendium/blob/main/pages/text_widgets/rich_text_block.md`

---

### 3.2 UE 5.6 WebSocket Client Options

**Primary recommendation:** Use Epic's bundled `WebSockets` module via `FWebSocketsModule::Get().CreateWebSocket()`. DO NOT hand-roll a WS client; DO NOT pull in `beast` or a third-party dependency. Rationale: already linked into the editor, no binary-size cost, no licensing overhead, stable across UE 5.4 → 5.7.

**Build.cs setup for `NyraEditor`:**

```csharp
// NyraEditor.Build.cs
using UnrealBuildTool;

public class NyraEditor : ModuleRules
{
    public NyraEditor(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(new string[] {
            "Core",
            "CoreUObject",
            "Engine",
            "InputCore",
            "Slate",
            "SlateCore",
            "EditorStyle",       // FEditorStyle / FAppStyle brush + font access
            "EditorSubsystem",
            "UnrealEd",          // editor-only; required for tab-spawner + menu registration
            "ToolMenus",         // Tools > NYRA > Chat registration
            "Projects",          // IPluginManager::FindPlugin for resolving plugin content dir
            "Json",              // FJsonObject / FJsonSerializer for JSON-RPC encode/decode
            "JsonUtilities",
            "WebSockets",        // FWebSocketsModule + IWebSocket — loopback WS client
            "HTTP",               // Phase 1 only for Gemma download (FHttpModule)
            "DesktopPlatform",   // Attachment file picker (FDesktopPlatform::OpenFileDialog)
            "ApplicationCore",   // FPlatformApplicationMisc::ClipboardCopy
        });

        PrivateDependencyModuleNames.AddRange(new string[] {
            "WorkspaceMenuStructure", // nomad tab menu structure
            "MainFrame",
            "LevelEditor",
        });

        // SQLite (see §3.7)
        PrivateDependencyModuleNames.Add("SQLiteCore");

        // Stage non-DLL binary assets (NyraHost Python dist, wheels, llama-server)
        // See §3.8 for full RuntimeDependencies block.
    }
}
```

**`NyraRuntime.Build.cs`** (Phase 1 is nearly empty):

```csharp
public class NyraRuntime : ModuleRules
{
    public NyraRuntime(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine" });
    }
}
```

**Core client usage:**

```cpp
#include "WebSocketsModule.h"
#include "IWebSocket.h"

void FNyraEditorModule::ConnectToHost(const FString& Host, int32 Port, const FString& Token)
{
    const FString Url = FString::Printf(TEXT("ws://%s:%d/"), *Host, Port);
    const FString Protocol = TEXT("nyra-jsonrpc-v1");

    TSharedRef<IWebSocket> Socket =
        FWebSocketsModule::Get().CreateWebSocket(Url, Protocol);

    Socket->OnConnected().AddLambda([this, Socket, Token]() {
        // Send session/authenticate as first frame (D-07)
        SendJsonRpcRequest(Socket, 1, TEXT("session/authenticate"),
            MakeShared<FJsonObject>(TMap<FString, TSharedPtr<FJsonValue>>{
                { TEXT("token"), MakeShared<FJsonValueString>(Token) }
            }));
    });

    Socket->OnMessage().AddRaw(this, &FNyraEditorModule::OnMessage);
    Socket->OnClosed().AddRaw(this, &FNyraEditorModule::OnClosed);
    Socket->OnConnectionError().AddRaw(this, &FNyraEditorModule::OnConnectionError);

    Socket->Connect();
    ActiveSocket = Socket;
}
```

**Threading note:** `IWebSocket` callbacks fire on the GameThread by default in UE's implementation (uses `libwebsockets` under the hood, polled from a main-thread-friendly ticker). **This means Slate updates from `OnMessage` are safe without explicit marshalling in Phase 1.** Confirmed from `FWebSocketsModule` source in UE 5.6: the module runs its own tick on the game tick group. Do NOT assume background-thread delivery; if NyraHost sends a 100-frame burst during a UE tick, they queue up for the next tick. This is acceptable for Phase 1 but will matter for streaming throughput — document as a known limit.

**Alternatives considered and rejected:**

| Alternative | Why not |
|-------------|---------|
| Hand-rolled minimal WS client (frames + masking + close codes in `NyraEditor/Private/WS/`) | ~500 LOC of yak-shaving for zero gain. UE already ships a battle-tested client. |
| `boost::beast` | Adds Boost as a plugin dependency → licence headache + ~40 MB stripped binary. Not justifiable for loopback use. |
| `libwebsockets` direct | This is what UE's `WebSockets` module wraps. Re-linking it ourselves would fight UBT. |
| Named pipes instead of WS | Would simplify ephemeral-port/handshake, BUT Python `websockets` package is pure-Python loopback WS server with trivial auth hook. Named pipes force either `asyncio.subprocess`-style NPipe handling on the Python side (mature but Windows-specific API burden) or a third-party async NPipe lib. WS is cleaner. CONTEXT.md locks WS. |

**Citations:**
- `https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/WebSockets/FWebSocketsModule`
- `https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Plugins/WebSocketNetworking`
- `https://unrealcommunity.wiki/websocket-client-cpp-5vk7hp9e`

**Confidence:** HIGH. This is a well-trodden path.

---

### 3.3 Subprocess Supervision on Windows

**Primary recommendation:** Use `FMonitoredProcess` (from `Core/Misc`, available since UE 4.x, stable through 5.7) for NyraHost. For NyraInfer, lower-level `FPlatformProcess::CreateProc` + pipes gives us finer control over the llama-server startup log parse needed to capture the ephemeral port. Wrap both in a single `FNyraSupervisor` class that owns the proc handles, the restart counter, and the 3-in-60s window.

**Pattern A: NyraHost via `FMonitoredProcess`:**

```cpp
#include "Misc/MonitoredProcess.h"

void FNyraSupervisor::SpawnNyraHost()
{
    const FString PluginDir = IPluginManager::Get().FindPlugin(TEXT("NYRA"))->GetBaseDir();
    const FString PythonExe = FPaths::Combine(PluginDir,
        TEXT("Binaries/Win64/NyraHost/cpython/python.exe"));
    const FString Params = FString::Printf(
        TEXT("-m nyrahost --editor-pid %d --log-dir \"%s\""),
        FPlatformProcess::GetCurrentProcessId(),
        *FPaths::ProjectSavedDir() / TEXT("NYRA/logs"));

    const bool bHidden = true;
    const bool bCreatePipes = true; // captures stdout/stderr for diagnostic
    HostProcess = MakeShared<FMonitoredProcess>(PythonExe, Params, bHidden, bCreatePipes);

    HostProcess->OnOutput().BindRaw(this, &FNyraSupervisor::OnHostOutput);
    HostProcess->OnCompleted().BindRaw(this, &FNyraSupervisor::OnHostExited);

    if (!HostProcess->Launch())
    {
        UE_LOG(LogNyra, Error, TEXT("NyraHost failed to launch"));
        ShowSupervisorBanner(TEXT("NyraHost launch failed"));
        return;
    }
    HostStartedAt = FDateTime::Now();
}
```

**Why `FMonitoredProcess` for NyraHost:** It handles the pipe-drain thread internally (see §3.3.1 deadlock avoidance), owns the process handle lifecycle, and calls `OnCompleted` with the exit code when the process exits — which is exactly what our 3-in-60s supervisor needs.

**Pattern B: NyraInfer via low-level `CreateProc` + pipe parse:**

llama-server prints `server listening at http://127.0.0.1:PORT` to stdout on startup. We need to parse PORT. `FMonitoredProcess` delivers lines via a delegate — also viable — but since NyraInfer is spawned by NyraHost (Python side), this whole pattern actually lives in Python, not C++. **NyraHost uses `asyncio.create_subprocess_exec`** with `stdout=asyncio.subprocess.PIPE` and parses the port from the first log line matching `r'listening at http://[^:]+:(\d+)'`.

```python
# nyrahost/infer.py
async def spawn_llama_server(gguf_path: Path, ctx: int = 16384) -> InferHandle:
    proc = await asyncio.create_subprocess_exec(
        str(LLAMA_SERVER_EXE),
        "-m", str(gguf_path),
        "--port", "0",
        "--host", "127.0.0.1",
        "--ctx-size", str(ctx),
        "-ngl", "99",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,  # merge streams for simpler parsing
    )
    port: int | None = None
    while port is None:
        line = (await proc.stdout.readline()).decode(errors="replace")
        if not line:
            raise RuntimeError("llama-server died before port announcement")
        m = re.search(r"listening at http://[^:]+:(\d+)", line)
        if m:
            port = int(m.group(1))
        log.debug("llama-server: %s", line.rstrip())
    # Drain remaining stdout in background to avoid pipe fill deadlock
    asyncio.create_task(_drain_pipe(proc.stdout))
    return InferHandle(proc=proc, port=port)
```

#### 3.3.1 Pipe-deadlock avoidance — mandatory

UE's `FPlatformProcess::CreatePipe` + `CreateProc` with captured stdout WILL deadlock if you don't continuously drain the read pipe. Child fills its stdout buffer → blocks on next write → parent is also waiting → mutual stall.

- With `FMonitoredProcess`: the class handles this internally via its own pipe-read thread. Safe by default. Confirmed from UE 5.6 source.
- With raw `CreateProc`: the parent MUST poll `FPlatformProcess::ReadPipe` on a ticker or dedicated thread, every frame / every few ms. NEVER block in-process code waiting on the child's exit.
- On the Python NyraHost side: same rule applies. The `_drain_pipe(proc.stdout)` background task above is non-optional.

**D-05 graceful shutdown path:**

```cpp
void FNyraSupervisor::ShutdownNyraHost()
{
    // 1. Send JSON-RPC `shutdown` notification over WS
    if (ActiveSocket.IsValid() && ActiveSocket->IsConnected())
    {
        SendJsonRpcNotification(ActiveSocket.ToSharedRef(), TEXT("shutdown"),
                                 MakeShared<FJsonObject>());
    }

    // 2. Wait 2s for clean exit
    const double Deadline = FPlatformTime::Seconds() + 2.0;
    while (HostProcess.IsValid() && HostProcess->Update() && FPlatformTime::Seconds() < Deadline)
    {
        FPlatformProcess::Sleep(0.05f);
    }

    // 3. Force kill if still alive
    if (HostProcess.IsValid() && HostProcess->IsRunning())
    {
        const bool bKillTree = true;  // kills NyraInfer grandchild too
        HostProcess->Cancel(bKillTree);
    }
}
```

**Killing process trees on Windows:** `FMonitoredProcess::Cancel(bKillTree=true)` internally calls `FPlatformProcess::TerminateProc(ProcHandle, /*KillTree=*/true)`, which uses `CreateToolhelp32Snapshot` to walk parent-child relationships and terminate NyraInfer (spawned by NyraHost) as well. This is CRITICAL: without `KillTree`, TerminateProc on NyraHost leaves NyraInfer orphaned and holding the GGUF model in RAM.

**Detecting crash vs clean exit:**

```cpp
void FNyraSupervisor::OnHostExited(int32 ExitCode)
{
    const bool bCleanExit = (ExitCode == 0);
    const FTimespan Uptime = FDateTime::Now() - HostStartedAt;

    if (bCleanExit && bShuttingDown)
    {
        UE_LOG(LogNyra, Log, TEXT("NyraHost exited cleanly (shutdown)"));
        return;
    }

    // Crash or unexpected exit — apply 3-in-60s policy (D-08)
    RestartHistory.Add(FDateTime::Now());
    RestartHistory.RemoveAll([](const FDateTime& T) {
        return (FDateTime::Now() - T).GetTotalSeconds() > 60.0;
    });

    if (RestartHistory.Num() >= 3)
    {
        ShowSupervisorBanner(TEXT("NyraHost unstable — see Saved/NYRA/logs/"));
        return;
    }

    // Replay in-flight request with new req_id, mark original cancelled with "retried" badge
    TOptional<FNyraInFlightRequest> ToReplay = ConsumeInFlightRequest();
    SpawnNyraHost();
    if (ToReplay.IsSet())
    {
        AfterConnectCallbacks.Add([this, Req = MoveTemp(*ToReplay)]() mutable {
            ReplayRequest(MoveTemp(Req));
        });
    }
}
```

**UE 5.6-specific gotchas:**

- `FMonitoredProcess` has had its constructor signature stable since 5.1; 5.6 supports the `InCreatePipes` 4th-arg form used above. Confirmed from `dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Core/Misc/FMonitoredProcess`.
- Editor modal dialogs (UAC, SmartScreen prompt on first NyraHost.exe launch) freeze the game thread — our spawn MUST be fire-and-forget (`Launch()` returns immediately; monitor via `OnCompleted`). Do NOT `WaitForProc` on the GameThread.
- On editor force-kill (Task Manager), `ShutdownModule` does NOT run reliably. Accept that NyraHost and NyraInfer can be left orphaned; Phase 1 ships a "stale handshake file cleanup" at startup that detects orphaned NyraHost PIDs (read PID from stale `handshake-*.json`, check with `FPlatformProcess::IsProcRunning`, terminate if still alive) before spawning fresh.

**Citations:**
- `https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Core/Misc/FMonitoredProcess/`
- `https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Core/GenericPlatform/FGenericPlatformProcess`
- `https://devblogs.microsoft.com/oldnewthing/20110707-00/?p=10223` — pipe-deadlock canonical reference

**Confidence:** HIGH on `FMonitoredProcess` usage; MEDIUM on the exact 3-in-60s window semantics (planner should stress-test with a fault-injection flag in Wave 2 that makes NyraHost self-terminate on command).

---

### 3.4 Embedded Python Distribution Mechanics

**python-build-standalone release pinning:**

The distribution is published under `astral-sh/python-build-standalone` (transferred 2024-12-17 from `indygreg`). Release tags follow `YYYYMMDD` format. Current-stable releases as of 2026-04-21 are around `20251120` and `20251014`. For CPython 3.12 Windows x64, the file pattern is:

```
cpython-3.12.N+YYYYMMDD-x86_64-pc-windows-msvc-shared-install_only.tar.zst
```

where `install_only` is the slim runtime (what we want), and `msvc-shared` links against `python312.dll` for API compatibility with standard Python extensions (wheel compat).

**Action for planner (Wave 1):** Before locking, run:

```bash
curl -s https://raw.githubusercontent.com/astral-sh/python-build-standalone/latest-release/latest-release.json | jq .
```

to get the canonical latest tag + download URL + SHA256, and pin that exact tag in the plugin's bootstrap script. This resolves the MEDIUM confidence on "which tag."

**sys.path behaviour from the frozen interpreter:**

The `install_only` bundle is a standard CPython layout:

```
cpython/
├── python.exe
├── python312.dll
├── Lib/                 # stdlib
├── DLLs/
├── Scripts/
└── include/
```

When invoked as `cpython/python.exe -m nyrahost`, sys.path is:

1. `''` (the current directory)
2. Directory of `nyrahost` package after `-m` resolution
3. `cpython/Lib/`, `cpython/DLLs/`, `cpython/python312.zip`
4. Site-packages from venv site if `VIRTUAL_ENV` set

**venv creation with the frozen Python:**

```bash
# Invoked once, by the C++ bootstrap, on first plugin load
%PLUGIN%/Binaries/Win64/NyraHost/cpython/python.exe -m venv ^
    --copies ^
    %LOCALAPPDATA%/NYRA/venv
```

Use `--copies` (NOT `--symlinks`) on Windows. Symlinks require developer-mode or admin; `--copies` is the zero-friction default and works on all Windows user accounts. The cost is ~40 MB extra disk, which is acceptable.

After venv creation, install deps offline from the bundled wheel cache:

```bash
%LOCALAPPDATA%/NYRA/venv/Scripts/python.exe -m pip install ^
    --no-index ^
    --find-links=%PLUGIN%/Binaries/Win64/NyraHost/wheels ^
    -r %PLUGIN%/Binaries/Win64/NyraHost/requirements.lock
```

`--no-index` forbids PyPI network access (true offline install). `--find-links` points at a local directory of pre-resolved `.whl` files. `requirements.lock` pins exact versions (from D-15: `mcp>=1.2.0`, `websockets>=12.0`, `httpx>=0.27`, `pydantic>=2.7`, `structlog>=24.1` — but LOCK files should pin exact versions including transitive deps, not ranges. Planner's Wave 1 task: run `pip-compile` on a dev machine and commit the output).

**Interaction with UE's built-in Python plugin:**

UE 5.4+ ships the `PythonScriptPlugin` under `Engine/Plugins/Experimental/PythonScriptPlugin/`. It embeds Python 3.11 (UE 5.4) / 3.11 (UE 5.6) in-editor for `unreal` module scripting. **This does NOT conflict with NyraHost** because:

1. NyraHost runs out-of-process — separate `python.exe` entirely.
2. NyraHost's interpreter is 3.12; UE's is 3.11. Even if loaded in the same process they'd fight, but they're not.
3. Phase 1 does NOT touch the `unreal` module from NyraHost (no in-process UE bindings needed).

Spell this out in onboarding docs: "If your project has UE Python scripting enabled, NYRA is fully independent and does not share interpreter state."

**Plugin-version marker for venv rebuild (D-14):**

```
%LOCALAPPDATA%/NYRA/venv/
├── .../                        # normal venv contents
├── nyra-plugin-version.txt     # written by bootstrap: "1.0.0\n"
```

On bootstrap:
```cpp
FString MarkerPath = VenvDir / TEXT("nyra-plugin-version.txt");
FString CurrentVersion;
if (!FFileHelper::LoadFileToString(CurrentVersion, *MarkerPath) ||
    CurrentVersion.TrimStartAndEnd() != NYRA_PLUGIN_VERSION)
{
    // Rebuild venv
    IFileManager::Get().DeleteDirectory(*VenvDir, false, true);
    CreateVenv();
    InstallWheelsOffline();
    FFileHelper::SaveStringToFile(NYRA_PLUGIN_VERSION + TEXT("\n"), *MarkerPath);
}
```

**Wheel cache sizing estimate:** `mcp` + `websockets` + `httpx` + `pydantic` + `structlog` + their transitives (anyio, pydantic_core, sniffio, httpcore, h11, idna, certifi, typing-extensions, attrs, etc.) — approximately 15-20 wheels totalling 8-12 MB. Acceptable to ship in plugin binaries.

**Citations:**
- `https://github.com/astral-sh/python-build-standalone/releases`
- `https://raw.githubusercontent.com/astral-sh/python-build-standalone/latest-release/latest-release.json` (machine-readable current tag)
- `https://gregoryszorc.com/docs/python-build-standalone/main/running.html`
- `https://astral.sh/blog/python-build-standalone`

**Confidence:** HIGH on mechanics; MEDIUM on exact release tag (resolve at Wave 1).

---

### 3.5 llama.cpp `llama-server` Flags + Windows GPU Backends + Ollama Detection

**Current llama-server flag surface (April 2026):**

| Flag | Value | Purpose |
|------|-------|---------|
| `-m <path>` | `<Saved>/NYRA/models/gemma-3-4b-it-qat-q4_0.gguf` | Model file path |
| `--port 0` | — | Let OS pick ephemeral port; server prints it to stdout |
| `--host 127.0.0.1` | — | Bind to loopback only; no firewall prompt |
| `--ctx-size 16384` | or `-c 16384` | Context window (Phase 1 default; Gemma 3 supports 128K but 16K is plenty and saves VRAM) |
| `-ngl 99` | (aka `--n-gpu-layers`) | Offload all layers to GPU. 99 = "all"; llama.cpp caps at actual layer count. If no GPU, the value is ignored and CPU-only runs. |
| `--chat-template gemma` | — | Apply Gemma's instruction-tuned chat template server-side. Recognized built-in templates include `gemma`, `llama3`, `chatml`. Confirmed from llama.cpp README. |
| `--mmproj <path>` | OPTIONAL | Multimodal projector file. Phase 1 is text-only — OMIT this flag. Gemma 3 multimodal comes in later phases. |
| `--log-format json` | OPTIONAL | JSON logs for easier parsing by NyraHost. Phase 1 recommends omitting and parsing stdout plain. |
| `--no-webui` | — | Disable the built-in web UI at `/` — we never render it. Slightly reduces memory + attack surface. |

**Full Phase 1 invocation:**

```bash
llama-server.exe ^
    -m "C:\Users\Alice\Documents\UnrealProjects\MyProj\Saved\NYRA\models\gemma-3-4b-it-qat-q4_0.gguf" ^
    --port 0 ^
    --host 127.0.0.1 ^
    --ctx-size 16384 ^
    -ngl 99 ^
    --chat-template gemma ^
    --no-webui
```

**SSE streaming format (`POST /v1/chat/completions` with `stream:true`):**

Server responds with `Content-Type: text/event-stream` and emits lines like:

```
data: {"id":"...", "object":"chat.completion.chunk", "choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"...", "choices":[{"delta":{"content":" world"},"finish_reason":null}]}

data: {"id":"...", "choices":[{"delta":{},"finish_reason":"stop"}], "usage":{"prompt_tokens":10,"completion_tokens":2,"total_tokens":12}}

data: [DONE]
```

Each event is `data: <json>\n\n`. The final `data: [DONE]` marker closes the stream. NyraHost parses with `httpx.AsyncClient` + `async for line in response.aiter_lines()`, accumulating `delta.content` and emitting JSON-RPC `chat/stream` notifications per accumulated chunk (batched per D-10 — one frame per model chunk, not per byte).

```python
# nyrahost/backends/gemma.py
async def stream_chat(prompt: str, conv_id: str, req_id: str):
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5, read=None)) as http:
        async with http.stream("POST", f"http://127.0.0.1:{INFER_PORT}/v1/chat/completions",
                                json={"model":"gemma-3-4b-it",
                                      "messages":[{"role":"user","content":prompt}],
                                      "stream": True}) as r:
            async for line in r.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload == "[DONE]":
                    await emit_stream_frame(conv_id, req_id, delta="", done=True)
                    return
                try:
                    evt = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                choice = evt.get("choices", [{}])[0]
                delta = choice.get("delta", {}).get("content", "")
                usage = evt.get("usage")
                if delta:
                    await emit_stream_frame(conv_id, req_id, delta=delta, done=False)
                if choice.get("finish_reason"):
                    await emit_stream_frame(conv_id, req_id, delta="", done=True, usage=usage)
                    return
```

**Ollama auto-detect (D-18):**

```python
# nyrahost/backends/ollama_probe.py
async def detect_ollama() -> str | None:
    """Return base URL if Ollama is running and has gemma3:4b-it-qat, else None."""
    try:
        async with httpx.AsyncClient(timeout=1.0) as http:
            r = await http.get("http://127.0.0.1:11434/api/tags")
            if r.status_code != 200:
                return None
            models = r.json().get("models", [])
            for m in models:
                # Match by model name prefix — Ollama tag syntax is "gemma3:4b-it-qat"
                if m.get("name", "").startswith("gemma3:4b-it-qat"):
                    return "http://127.0.0.1:11434"
    except (httpx.ConnectError, httpx.TimeoutException):
        return None
    return None
```

Ollama's `/api/tags` response (verified April 2026 via docs.ollama.com):

```json
{
  "models": [
    {
      "name": "gemma3:4b-it-qat",
      "model": "gemma3:4b-it-qat",
      "modified_at": "2025-10-03T23:34:03Z",
      "size": 3338801804,
      "digest": "sha256:...",
      "details": { "format":"gguf", "family":"gemma", "parameter_size":"4.3B", "quantization_level":"Q4_0" }
    }
  ]
}
```

If Ollama detected: call `http://127.0.0.1:11434/v1/chat/completions` with `model: "gemma3:4b-it-qat"` — Ollama exposes an OpenAI-compatible `/v1/chat/completions` endpoint, so NyraHost's HTTP client is the same code path as bundled-llama-server. The ONLY difference is the base URL and the model name string.

**CUDA vs Vulkan bundling decision:**

- llama-server releases ship as separate builds per backend: `llama-b6xxx-bin-win-cuda-cu12.4-x64.zip`, `llama-b6xxx-bin-win-vulkan-x64.zip`, `llama-b6xxx-bin-win-avx2-x64.zip` (CPU).
- **Recommendation:** Ship all three variants in `<Plugin>/Binaries/Win64/NyraInfer/` with subfolders (`cuda/`, `vulkan/`, `cpu/`). At runtime, NyraHost probes:
  1. `nvidia-smi` subprocess success → use `cuda/llama-server.exe`
  2. Else check Vulkan via `vulkaninfo --summary` (ships with most drivers) → use `vulkan/llama-server.exe`
  3. Else → use `cpu/llama-server.exe`
- Total disk cost: ~60 MB for three backends (each 15-25 MB). Acceptable. Simpler than a single fat binary, avoids "no NVIDIA runtime on this machine" CUDA DLL load failures.

**Gemma download URL (HuggingFace direct):**

```
https://huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf/resolve/main/gemma-3-4b-it-qat-q4_0.gguf
```

For reproducible pinning across plugin versions, use the commit-sha form:

```
https://huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf/resolve/<REVISION_SHA>/gemma-3-4b-it-qat-q4_0.gguf
```

Resolve `<REVISION_SHA>` at plugin-build time via `https://huggingface.co/api/models/google/gemma-3-4b-it-qat-q4_0-gguf` (returns `sha` in JSON). Pin both the SHA and the file SHA256 in plugin code. **Planner Wave 2 task:** fetch both pins and commit to `NyraEditor/Private/ModelPins.cpp` as constants.

HTTP Range resume is supported by HuggingFace CDN (verified with `curl -I`; returns `Accept-Ranges: bytes`). UE's `FHttpModule` supports `Range` header natively.

**Citations:**
- `https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md`
- `https://manpages.debian.org/unstable/llama.cpp-tools/llama-server.1.en.html`
- `https://docs.ollama.com/api/tags`
- `https://github.com/ollama/ollama/blob/main/docs/api.md`
- `https://huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf`

**Confidence:** HIGH on llama-server flags and SSE format; HIGH on Ollama response shape; MEDIUM on CUDA/Vulkan bundling layout (planner may choose single bundle if disk is tight).

---

### 3.6 Ring 0 Stability Gate — 100 Round-Trip Harness

**Purpose:** ROADMAP Phase 1 Success Criterion 3 — "loopback WebSocket + localhost HTTP IPC stable over 100 consecutive round-trips on UE 5.6 with editor responsive during streaming."

**Recommendation:** Ship the harness in Phase 1 as an editor console command. This is small (~1 day) and de-risks Phase 2 by producing a repeatable measurement.

**Command shape:**

```
Nyra.Dev.RoundTripBench [count=100] [prompt="Reply with the word OK"] [--streaming]
```

Registered via `FAutoConsoleCommand` in `FNyraEditorModule::StartupModule()`:

```cpp
static FAutoConsoleCommand GRoundTripBenchCmd(
    TEXT("Nyra.Dev.RoundTripBench"),
    TEXT("Run N sequential chat round-trips; report p50/p95/p99 first-token latency"),
    FConsoleCommandWithArgsDelegate::CreateStatic(&FNyraDevTools::RunRoundTripBench));
```

**Metrics captured per round-trip:**

| Metric | How |
|--------|-----|
| `t0 → sent` | Latency between `chat/send` issue and first byte of request on the socket (measure via `FPlatformTime::Cycles64` around `Socket->Send`). |
| `t0 → first_token` | Latency between `chat/send` issue and first `chat/stream` frame with `delta != ""`. **Primary metric.** |
| `t0 → done` | Latency between `chat/send` issue and `chat/stream{done:true}` frame. |
| `tokens/sec` | From `usage.completion_tokens / (t_done - t_first_token)`. |
| `frame_count` | Total `chat/stream` notifications received. |
| `editor_tick_max_ms` | Max `GFrameCounter` deltaTime during the streaming window — measures whether editor frame-time was affected. |

**Reporting:**

After all 100 round-trips, print to Output Log:

```
[NyraDevTools] RoundTripBench results (N=100):
  first_token  p50=  245ms  p95=  487ms  p99=  612ms
  total        p50= 1843ms  p95= 2341ms  p99= 2889ms
  tokens/sec            33.2              29.1              27.4
  editor_tick_max_ms    18.3              22.1              41.2
  errors       0
  PASS: editor responsive (p95 editor_tick < 33ms = 30 FPS floor)
```

**Programmatic responsiveness assertion:**

The harness runs on the GameThread and checks `FApp::GetDeltaTime() * 1000.0 < 33.0` (30 FPS floor) every tick during the streaming window. Any tick exceeding 33ms is logged with a stack sample (using `FPlatformStackWalk::CaptureStackBackTrace`) so slow callbacks are identifiable.

**Pass criteria (explicit):**

- All 100 round-trips complete without WS disconnect or timeout.
- p95 first-token latency < 500 ms on a reasonable dev machine (Gemma loaded).
- p95 editor frame-time < 33 ms during streaming (= editor stays at 30+ FPS).
- No pipe-deadlock or zombie NyraInfer process after the run.

**Planner decision (Phase 1 scope or Phase 2?):** CONTEXT.md §deferred marks this as "planner decides whether to include in Phase 1 scope or defer to Phase 2." Strong recommendation from this research: **include in Phase 1**. Without it, the architectural gate ("100 round-trips pass") has no objective measurement. The harness is ~1 day's work once the rest of the chat plumbing is done (Wave 3 task); deferring it means Phase 2 can't declare Phase 1 done.

**Confidence:** HIGH on metrics design; MEDIUM on exact pass thresholds (planner may tighten after first measurement).

---

### 3.7 SQLite in UE Plugin Context

**Primary recommendation:** Use UE's bundled `SQLiteCore` module (Engine/Plugins/Runtime/Database/SQLiteCore) on the UE side for READ-ONLY access to `sessions.db`. **NyraHost (Python) is the ONLY writer.** UE never writes to SQLite directly in Phase 1.

**Rationale for single-writer:**

- SQLite handles concurrent readers fine but cross-process writers need WAL mode + careful lock coordination. Making UE write would double the attack surface on schema migrations (D-14 semantics for rollback on failed plugin upgrade) and force us to link SQLite3 into two languages.
- Python's stdlib `sqlite3` module is free + battle-tested. `PRAGMA journal_mode=WAL` is enabled by NyraHost at startup.
- UE's role: on panel open, request recent conversations list via `chat/list` (Phase 2 method — in Phase 1 the panel just shows the current session). For Phase 1, UE does NOT need read access to SQLite at all — NyraHost pushes history via WS on session/hello response.

**Phase 1 concrete decision: UE does not link SQLite in Phase 1.** Drop `SQLiteCore` from Build.cs for now; add it in Phase 2 when the history drawer (CD-05) needs DB read. Simplifies Phase 1 surface.

**Python side schema bootstrap:**

```python
# nyrahost/storage.py
SCHEMA_V1 = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;
PRAGMA user_version=1;

CREATE TABLE IF NOT EXISTS conversations (
    id         TEXT PRIMARY KEY,
    title      TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK(role IN ('user','assistant','system','tool')),
    content         TEXT NOT NULL,
    created_at      INTEGER NOT NULL,
    usage_json      TEXT,
    error_json      TEXT
);
CREATE INDEX IF NOT EXISTS idx_messages_conv_created
    ON messages(conversation_id, created_at);
CREATE TABLE IF NOT EXISTS attachments (
    id          TEXT PRIMARY KEY,
    message_id  TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL,
    path        TEXT NOT NULL,
    size_bytes  INTEGER,
    sha256      TEXT
);
"""
```

**Attachment content-addressing (CD-08):**

```python
# nyrahost/attachments.py
def ingest_attachment(src_path: Path, project_saved: Path) -> AttachmentRef:
    with src_path.open("rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    prefix = sha[:2]
    ext = src_path.suffix.lstrip(".")
    dest_dir = project_saved / "NYRA" / "attachments" / prefix
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{sha}.{ext}"
    if not dest.exists():
        # Try hardlink first (free), fall back to copy across volumes
        try:
            os.link(src_path, dest)
        except OSError:
            shutil.copy2(src_path, dest)
    return AttachmentRef(sha256=sha, path=str(dest), size_bytes=src_path.stat().st_size)
```

**Per-project scope:** The DB path is `<ProjectDir>/Saved/NYRA/sessions.db` — per-UE-project, not per-user. This means opening the same project on two machines (shared source control) doesn't share chat history. That's the right default (privacy, no sync conflicts). Phase 1 accepts this; cloud sync is a v2+ conversation.

**Migrations:**

```python
def migrate(conn: sqlite3.Connection) -> None:
    cur = conn.execute("PRAGMA user_version")
    version = cur.fetchone()[0]
    if version < 1:
        conn.executescript(SCHEMA_V1)
    # Future: if version < 2: ...
```

**Confidence:** HIGH on the single-writer pattern and schema; HIGH on Python stdlib sqlite3 (battle-tested); HIGH on skipping SQLiteCore in Phase 1 (the read requirement can come from NyraHost via WS).

---

### 3.8 `.uplugin` + Build.cs for Two-Module Layout

**Directory layout (relative to plugin root, `Plugins/NYRA/`):**

```
NYRA.uplugin
README.md
Resources/
    Icon128.png
Source/
    NyraEditor/
        NyraEditor.Build.cs
        Public/
            NyraEditor.h
        Private/
            NyraEditor.cpp
            NyraEditorModule.cpp
            Panel/              # SNyraChatPanel, SNyraMessageList, SNyraComposer
            WS/                 # FNyraWsClient, FNyraJsonRpc
            Process/            # FNyraSupervisor, FNyraHandshake
            Markdown/           # NyraMarkdownParser
            Dev/                # FNyraDevTools (RoundTripBench)
    NyraRuntime/
        NyraRuntime.Build.cs
        Public/
            NyraRuntime.h
        Private/
            NyraRuntime.cpp     # FDefaultModuleImpl
Binaries/
    Win64/
        NyraHost/
            cpython/            # python-build-standalone
            wheels/             # *.whl pre-resolved
            nyrahost/           # Python package source (.py)
            requirements.lock
        NyraInfer/
            cuda/llama-server.exe
            vulkan/llama-server.exe
            cpu/llama-server.exe
Content/                         # empty in Phase 1
Config/                          # empty in Phase 1
```

**`NYRA.uplugin`:**

```json
{
    "FileVersion": 3,
    "Version": 1,
    "VersionName": "0.1.0",
    "FriendlyName": "NYRA",
    "Description": "Turn a reference into a finished Unreal Engine scene — without a new AI bill.",
    "Category": "AI",
    "CreatedBy": "NYRA",
    "CreatedByURL": "https://nyra.ai",
    "DocsURL": "https://nyra.ai/docs",
    "MarketplaceURL": "",
    "SupportURL": "https://nyra.ai/support",
    "EngineVersion": "5.6.0",
    "CanContainContent": false,
    "IsBetaVersion": true,
    "IsExperimentalVersion": false,
    "Installed": false,
    "Modules": [
        {
            "Name": "NyraEditor",
            "Type": "Editor",
            "LoadingPhase": "PostEngineInit",
            "PlatformAllowList": [ "Win64" ]
        },
        {
            "Name": "NyraRuntime",
            "Type": "Runtime",
            "LoadingPhase": "Default",
            "PlatformAllowList": [ "Win64" ]
        }
    ],
    "Plugins": [
        { "Name": "WebSockets", "Enabled": true },
        { "Name": "EditorSubsystem", "Enabled": true }
    ]
}
```

**Staging non-DLL content via `RuntimeDependencies`:**

UBT treats anything in `Binaries/Win64/` that isn't a module's DLL as "not staged by default" in a Fab-packaged plugin. To stage NyraHost's Python distribution and NyraInfer's llama-server, declare them as `RuntimeDependencies` in `NyraEditor.Build.cs`:

```csharp
// Add to NyraEditor.Build.cs (inside constructor body)
if (Target.Platform == UnrealTargetPlatform.Win64)
{
    string PluginBinariesDir = Path.Combine(PluginDirectory, "Binaries", "Win64");

    // Stage entire NyraHost tree (cpython/ + wheels/ + nyrahost/ + requirements.lock)
    string NyraHostDir = Path.Combine(PluginBinariesDir, "NyraHost");
    foreach (string F in Directory.GetFiles(NyraHostDir, "*", SearchOption.AllDirectories))
    {
        RuntimeDependencies.Add(F);
    }

    // Stage NyraInfer per-backend llama-server executables
    string NyraInferDir = Path.Combine(PluginBinariesDir, "NyraInfer");
    foreach (string F in Directory.GetFiles(NyraInferDir, "*", SearchOption.AllDirectories))
    {
        RuntimeDependencies.Add(F);
    }
}
```

This instructs UBT to include these files when the plugin is packaged (`BuildPlugin` command for Fab) and also when a consuming UE project is cooked+packaged.

**Confidence:** HIGH on `.uplugin` descriptor and module layout; HIGH on `RuntimeDependencies` pattern (Epic's canonical answer on packaging non-DLL plugin content).

**Citations:**
- `https://dev.epicgames.com/documentation/en-us/unreal-engine/plugins-in-unreal-engine`
- `https://forums.unrealengine.com/t/how-can-i-package-runtime-dependencies-from-an-engine-plugin/433361`
- `https://unrealcommunity.wiki/adding-custom-third-party-library-to-plugin-from-scratch-867b28`

---

### 3.9 First-Run UX Flow — Graceful State Without Backends

DIST-04 (Phase 8) promises "zero-config install." Phase 1 must deliver the first-run experience up to the point where a subscription is plugged in (Phase 2). Phase 1's answer to "user opens panel, nothing is configured":

**State machine (Phase 1 scope):**

```
ENABLED_PLUGIN
  └─> Editor reopens, NyraEditor::StartupModule runs
      └─> Bootstrap venv if missing (one-time, ~30s progress toast)
      └─> Spawn NyraHost (eager, D-04)
      └─> NyraHost writes handshake file
      └─> UE polls file, connects WS, authenticates
      └─> Panel shows: "Ready. Local model: not installed."
                       [Download Gemma (3.16 GB)]  [Open Diagnostics]

USER CLICKS DOWNLOAD
  └─> Progress modal: SProgressBar + cancel button + resumable
  └─> Written to <Project>/Saved/NYRA/models/gemma-3-4b-it-qat-q4_0.gguf
  └─> SHA256 verify on completion
  └─> Panel updates: "Ready. Local model: Gemma 3 4B QAT Q4_0 (3.16 GB)"

USER TYPES MESSAGE → PRESSES CTRL+ENTER
  IF Gemma NOT installed:
    panel bubble shows error frame with remediation:
    "Local fallback is not installed. Click [Download Gemma] or connect
     Claude (coming in Phase 2)."
  ELSE:
    NyraHost lazy-spawns NyraInfer (D-19), takes 6-12s first time
    Assistant bubble shows "Warming Gemma…" spinner
    Once llama-server reports ready, SSE streaming begins
    Tokens appear in bubble; on done:true, markdown is rendered
```

**Banner states:**

| State | Trigger | Visual | Action |
|-------|---------|--------|--------|
| Bootstrap in progress | First plugin load, venv not built | Top banner: "Setting up NYRA (~30s)" | (none — wait) |
| Host crashed (under restart policy) | Host exit non-zero, <3 in 60s | None visible (respawn is invisible to user); "retried" badge on affected message | (auto-resumes) |
| Host unstable banner | 3 restarts in 60s | Top banner: "NyraHost is unstable — see Saved/NYRA/logs/" | `[Restart]` `[Open log]` |
| Gemma not installed + user sent message | User msg with no backend | Error bubble + remediation string from `error.data.remediation` | `[Download Gemma]` inline |
| Handshake timeout | 30s polling expired | Top banner: "NyraHost failed to come online" | `[Restart]` `[Open log]` |

**Key UX invariant:** panel is ALWAYS usable — even without Gemma installed, the user can open the panel, see the download CTA, and understand what's happening. No blank screen, no unexplained failures.

**Confidence:** HIGH on the flow; MEDIUM on exact banner copy (Wave 3 UI pass may polish).

---

### 3.10 Phase 1-Specific Pitfalls (beyond PITFALLS.md)

#### P1.1 Handshake file stale-read race — **HIGH**

**What goes wrong:** NyraHost writes `handshake-<pid>.json` via `open(path, "w")` + `json.dump()` + `close()`. UE's polling read catches the file mid-write and gets an empty or partial JSON. JSON parse fails → UE thinks handshake invalid → keeps polling → NyraHost never recovers because the file is "there."

**Prevention:**
1. NyraHost writes via atomic rename: `open(path+".tmp", "w")`, dump, close, `os.replace(path+".tmp", path)`. `os.replace` is atomic on Windows NTFS.
2. UE side: tolerate JSON-parse failures silently during polling (treat as "not ready yet", continue backoff). Only surface failure after 30s total timeout.
3. NyraHost writes AFTER binding the port AND generating the token AND enabling the WS server's accept loop. Handshake file existence = "I'm ready to accept connections." No earlier.

#### P1.2 Multiple editor processes on same Windows user — **MEDIUM**

**What goes wrong:** User opens `MyProject.uproject` and `OtherProject.uproject` simultaneously. Both NyraEditor modules start; both spawn NyraHost; two handshake files are written: `handshake-<pid1>.json` and `handshake-<pid2>.json`. Because the file name includes the editor PID (D-06), they don't collide. BUT if the user force-kills one editor, that stale handshake file never gets deleted.

**Prevention:**
1. File name includes editor PID — already locked in D-06. Good.
2. On NyraEditor startup, scan `%LOCALAPPDATA%/NYRA/handshake-*.json`. For each, read the `ue_pid`. If that PID is not running (`FPlatformProcess::IsProcRunning(FPlatformProcess::OpenProcess(pid))` returns false OR OpenProcess fails), also check `nyrahost_pid` — if it's still alive but orphaned, kill it; then delete the handshake file.
3. Document: "If you force-kill UE, NYRA will clean up on next launch."

#### P1.3 Python venv corruption across plugin version updates — **MEDIUM**

**What goes wrong:** User has NYRA 0.1.0 installed → venv at `%LOCALAPPDATA%/NYRA/venv/` has Pydantic 2.7. User Fab-updates to 0.2.0 which pins Pydantic 2.8. Venv still has 2.7. Import works, but schema validation has subtle behaviour diff → mysterious bugs.

**Prevention:**
1. Plugin-version marker file (`venv/nyra-plugin-version.txt`) — ALREADY in D-14.
2. On startup, if marker mismatches `NYRA_PLUGIN_VERSION`: `rmtree` the venv and rebuild from wheel cache. ~30s cost once per update.
3. Show a progress toast during rebuild so the user understands why the first-launch-after-update is slow.

#### P1.4 SmartScreen on first launch of NyraHost.exe / NyraInfer.exe — **MEDIUM (accepted)**

**What goes wrong:** Phase 1 has no EV code-signing cert (DIST-03 is Phase 2). First time `cpython/python.exe` or `llama-server.exe` launches, Windows SmartScreen may show "Windows protected your PC" dialog, especially in enterprise environments.

**Prevention (Phase 1 accepts, documents):**
1. Devlog explicitly calls out that Phase 1 is unsigned; Phase 2 buys the cert.
2. README includes "If you see SmartScreen, click 'More info' → 'Run anyway'".
3. We do NOT programmatically suppress SmartScreen — that's hostile / flagged by MS.
4. Enterprise users: document the allowlist path in `docs/ENTERPRISE.md` (Phase 2).
5. The Python interpreter and llama-server are already public well-known binaries from their respective projects — reputation is slightly higher than a brand-new bespoke EXE. Still shows SmartScreen on first launch on clean profiles.

#### P1.5 llama-server CUDA DLL issues on machines without NVIDIA runtime — **HIGH**

**What goes wrong:** Ship a CUDA-built `llama-server.exe`; user has no NVIDIA GPU. Binary fails to load `cublas64_12.dll` → process exits immediately → we show `-32001 subprocess_failed` with no useful detail.

**Prevention:**
1. Per-backend bundling (§3.5): ship three `llama-server.exe` variants under `cuda/`, `vulkan/`, `cpu/` subfolders.
2. Runtime probe order: nvidia-smi → vulkaninfo → CPU.
3. If CUDA spawn fails on a machine that passed the nvidia-smi probe, fall back to Vulkan, then CPU, logging each attempt. Surface to user as: "GPU acceleration unavailable on this machine — using CPU (slower)".
4. Accept that CPU inference of Gemma 3 4B at Q4_0 is ~3-5 tokens/sec on a modern 8-core CPU. Still usable for short Phase 1 demos.

#### P1.6 UE 5.6 Slate threading — WS I/O must respect GameThread — **MEDIUM**

**What goes wrong:** `FWebSocketsModule`'s callbacks fire on the GameThread (confirmed for UE's bundled WS module), so direct Slate updates from `OnMessage` are safe. BUT if we ever move WS I/O to a background thread (Phase 2 perf work), we MUST marshal Slate updates back via `AsyncTask(ENamedThreads::GameThread, ...)` or `FFunctionGraphTask::CreateAndDispatchWhenReady`. Touching Slate widgets from a non-game thread causes undefined behaviour (usually an assertion in `check(IsInGameThread())`).

**Prevention:**
1. Phase 1 keeps WS I/O on GameThread (simpler, within throughput envelope for single-user chat).
2. Code comments in FNyraWsClient explicitly state "Callbacks run on GameThread — do not assume otherwise."
3. Phase 2 can move to a dedicated WS thread if 100-round-trip benchmark shows editor tick stalls; Phase 2 takes on the marshalling complexity then.

#### P1.7 JSON-RPC `id` collision after respawn — **LOW**

**What goes wrong:** UE increments `id` per request: 1, 2, 3... NyraHost crashes and respawns. UE thinks the next ID is 4. But what if a stale response to `id=3` arrives over a reconnected socket? It matches a freshly-pending request that also got id=3 after reconnect's id counter restart.

**Prevention:**
1. UE's `id` counter persists across reconnects (`FAtomicInt64 NextId { 1 };` in `FNyraEditorModule`, NEVER reset on reconnect).
2. NyraHost identifies each WS session with a fresh `session_id` (UUID) returned in `session/hello`; UE rejects responses whose envelope `session_id` doesn't match current.

---

## Runtime State Inventory

Phase 1 is greenfield (no prior state). This section is skipped.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| UE 5.6 editor | Entire phase | Unknown (user-provided) | 5.6.x | — (hard requirement per D-03) |
| Visual Studio 2022 + MSVC v143 | Compiling C++ plugin | Unknown | 17.8+ | — (hard requirement for UE 5.6 plugin build) |
| Python (any, for wheel pre-resolve at plan time) | Building `requirements.lock` | Unknown | 3.12 preferred | Use user's system Python; fall back to spinning up python-build-standalone in Docker |
| HuggingFace CDN reachable | Gemma download | Assumed yes | — | Mirror bundle on NYRA GitHub releases (D-17) |
| Internet at runtime (for Gemma first-run) | CHAT-01 end-to-end demo | User-dependent | — | Ship a tiny "smoke test" prompt that uses no tokens; full demo requires download |

**Missing dependencies with no fallback:** UE 5.6 and MSVC v143 — these are hard constraints the plugin can't ship without. Planner assumes the builder has them.

**Missing dependencies with fallback:** python-build-standalone latest tag; HF mirror; CUDA/Vulkan runtime (graceful degrade to CPU).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (C++ side) | **Automation Spec** (UE built-in — `FAutomationSpec`, `#if WITH_AUTOMATION_TESTS`) |
| Framework (Python side) | **pytest** 8.x + `pytest-asyncio` |
| C++ config file | None — Automation tests are discovered via `BEGIN_DEFINE_SPEC` macros in `NyraEditor/Private/Tests/`. Build.cs needs `bBuildDeveloperTools=true` for editor targets (default for editor modules). |
| Python config file | `pyproject.toml` with `[tool.pytest.ini_options]` (new file in Wave 0) |
| Quick run command (C++) | In UE editor: Window → Test Automation → run "Nyra.Editor" filter. CLI: `UnrealEditor-Cmd.exe TestProject.uproject -ExecCmds="Automation RunTests Nyra;Quit" -unattended -nopause -testexit="Automation Test Queue Empty"` |
| Quick run command (Python) | `pytest NyraHost/tests/ -x` |
| Full suite command (C++) | Same as quick but without filter. |
| Full suite command (Python) | `pytest NyraHost/tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PLUG-01 | Plugin loads on UE 5.6 without errors, both modules initialize | automation (UE spec) | Automation: `Nyra.Plugin.ModulesLoad` checks `FModuleManager::Get().IsModuleLoaded(TEXT("NyraEditor"))` and `NyraRuntime` | ❌ Wave 0 |
| PLUG-02 | NyraHost spawns, writes handshake, UE connects, auth succeeds | integration (UE + Python) | Automation: `Nyra.Integration.HandshakeAuth` drives `FNyraSupervisor::SpawnAndConnect()` with a 30s deadline, asserts `OnAuthenticated` fires | ❌ Wave 0 |
| PLUG-02 | JSON-RPC 2.0 envelope encode/decode roundtrip | unit | Automation: `Nyra.Jsonrpc.EnvelopeRoundtrip` | ❌ Wave 0 |
| PLUG-02 | Supervisor 3-in-60s restart policy + banner | unit (mock process) | Automation: `Nyra.Supervisor.RestartPolicy` uses injected fault clock | ❌ Wave 0 |
| PLUG-02 | Python: asyncio WS server accepts valid auth, rejects bad token with close code 4401 | pytest | `pytest NyraHost/tests/test_auth.py::test_auth_rejects_bad_token` | ❌ Wave 0 |
| PLUG-02 | Python: handshake file atomic write | pytest | `pytest NyraHost/tests/test_handshake.py` | ❌ Wave 0 |
| PLUG-02 | Python: venv bootstrap idempotency | pytest | `pytest NyraHost/tests/test_bootstrap.py::test_bootstrap_idempotent` | ❌ Wave 0 |
| PLUG-03 | Bundled llama-server spawns with `--port 0`, port captured from stdout | pytest | `pytest NyraHost/tests/test_infer_spawn.py` (uses mock llama-server that prints `listening at http://127.0.0.1:PORT` then exits) | ❌ Wave 0 |
| PLUG-03 | Ollama detect returns URL when `/api/tags` has `gemma3:4b-it-qat` | pytest (httpx MockTransport) | `pytest NyraHost/tests/test_ollama_detect.py` | ❌ Wave 0 |
| PLUG-03 | SSE stream parser extracts delta content correctly | pytest | `pytest NyraHost/tests/test_sse_parser.py` | ❌ Wave 0 |
| PLUG-03 | Gemma download: SHA256 verify + HTTP Range resume | pytest (httpx MockTransport with partial-response) | `pytest NyraHost/tests/test_gemma_download.py` | ❌ Wave 0 |
| CHAT-01 | Panel registers under `Tools > NYRA > Chat` tab spawner | automation | `Nyra.Panel.TabSpawner` invokes `FGlobalTabManager::Get()->TryInvokeTab("NyraChatTab")` and checks tab exists | ❌ Wave 0 |
| CHAT-01 | Markdown parser: fenced code block → rich-text tag stream | unit (C++) | `Nyra.Markdown.FencedCode` | ❌ Wave 0 |
| CHAT-01 | Markdown parser: inline formatting roundtrip | unit (C++) | `Nyra.Markdown.InlineFormatting` | ❌ Wave 0 |
| CHAT-01 | Attachment chip SCompoundWidget renders filename + remove button | automation (Slate widget test) | `Nyra.Panel.AttachmentChip` | ❌ Wave 0 |
| CHAT-01 | Streaming updates buffer (plain → rich on done) | automation | `Nyra.Panel.StreamingBuffer` drives a simulated chat/stream sequence | ❌ Wave 0 |
| CHAT-01 | Python: SQLite schema migration from fresh creates all tables | pytest | `pytest NyraHost/tests/test_storage.py::test_schema_v1` | ❌ Wave 0 |
| CHAT-01 | Python: attachment ingest hardlinks/copies, returns correct sha256 | pytest | `pytest NyraHost/tests/test_attachments.py` | ❌ Wave 0 |
| **Ring 0 gate** | 100 consecutive round-trips; p95 first-token < 500ms; p95 editor tick < 33ms | integration (manual + automated) | Editor console: `Nyra.Dev.RoundTripBench 100` — passes/fails with log output asserting thresholds | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest NyraHost/tests/ -x` (sub-second per test) + UE Automation quick filter matching modified module.
- **Per wave merge:** Full UE Automation `Nyra.*` suite + full pytest suite.
- **Phase gate (before `/gsd:verify-work`):** Full suites green + `Nyra.Dev.RoundTripBench 100` passes on the dev machine.

### Wave 0 Gaps

- [ ] `NyraEditor/Source/NyraEditor/Private/Tests/NyraJsonRpcSpec.cpp` — unit tests for JSON-RPC 2.0 encode/decode
- [ ] `NyraEditor/Source/NyraEditor/Private/Tests/NyraMarkdownSpec.cpp` — markdown parser unit tests
- [ ] `NyraEditor/Source/NyraEditor/Private/Tests/NyraSupervisorSpec.cpp` — supervisor policy tests (with injected clock + mock proc)
- [ ] `NyraEditor/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp` — Slate widget tests
- [ ] `NyraEditor/Source/NyraEditor/Private/Tests/NyraIntegrationSpec.cpp` — full E2E handshake + auth (requires actual NyraHost on test machine; guard with `ENABLE_NYRA_INTEGRATION_TESTS`)
- [ ] `NyraHost/pyproject.toml` — pytest config, black/ruff, mypy
- [ ] `NyraHost/tests/conftest.py` — shared fixtures (temp project dir, mock llama-server, mock handshake)
- [ ] `NyraHost/tests/test_auth.py`
- [ ] `NyraHost/tests/test_handshake.py`
- [ ] `NyraHost/tests/test_bootstrap.py`
- [ ] `NyraHost/tests/test_infer_spawn.py`
- [ ] `NyraHost/tests/test_ollama_detect.py`
- [ ] `NyraHost/tests/test_sse_parser.py`
- [ ] `NyraHost/tests/test_gemma_download.py`
- [ ] `NyraHost/tests/test_storage.py`
- [ ] `NyraHost/tests/test_attachments.py`
- [ ] Framework install command (added to requirements-dev.lock, not shipped): `pip install pytest pytest-asyncio pytest-httpx`
- [ ] `Nyra.Dev.RoundTripBench` console command implementation (`NyraEditor/Private/Dev/FNyraDevTools.cpp`)

---

## Pitfalls & Mitigations (summary, with Phase 1 additions)

| # | Pitfall | Severity | From | Mitigation |
|---|---------|----------|------|------------|
| 1 | Handshake file partial-read race | HIGH | §3.10 P1.1 | Atomic rename on write; tolerate parse failure during polling |
| 2 | Multiple editor instances → orphan handshake files | MEDIUM | §3.10 P1.2 | PID-scoped filename + orphan cleanup on startup |
| 3 | Venv corruption across plugin updates | MEDIUM | §3.10 P1.3 | Plugin-version marker file; auto-rebuild on mismatch |
| 4 | SmartScreen on first Nyra*.exe launch | MEDIUM (accepted) | §3.10 P1.4 | Devlog explains; EV cert lands Phase 2 |
| 5 | CUDA DLL load failure on machines without NVIDIA runtime | HIGH | §3.10 P1.5 | Per-backend bundling; probe order nvidia-smi → vulkaninfo → CPU |
| 6 | Slate threading violation if WS I/O moves off GameThread | MEDIUM (Phase 2) | §3.10 P1.6 | Phase 1 keeps WS on GameThread; Phase 2 adds marshalling |
| 7 | JSON-RPC id collision after respawn | LOW | §3.10 P1.7 | Persist id counter across reconnects; session_id envelope check |
| 8 | Pipe-read deadlock (child fills stdout buffer) | HIGH | §3.3.1 | `FMonitoredProcess` drains internally; Python side uses `_drain_pipe` background task |
| 9 | NyraInfer orphaned if NyraHost TerminateProc without KillTree | HIGH | §3.3 | Always pass `bKillTree=true` |
| 10 | Pipe-deadlock stopping NyraInfer llama-server startup parse | HIGH | §3.3 | Background task drains stdout after port capture |
| 11 | Streaming token render thrashing `SRichTextBlock` | MEDIUM | §3.1 | Plain `STextBlock` during stream, swap to `SRichTextBlock` on `done:true` |
| 12 | Markdown parser bugs affecting code blocks | MEDIUM | §3.1 | Unit tests cover fenced code + inline formatting in Wave 0 |
| 13 | HF CDN outage during Gemma download | MEDIUM | §3.5 | Fallback to GitHub Releases mirror (D-17); both URLs in plugin code |
| 14 | `Nyra.Dev.RoundTripBench` pass thresholds too loose | LOW | §3.6 | Measure first, tune; document the measurement |

Reference PITFALLS.md §1 (legal), §3.3 (ABI drift), §3.4 (SmartScreen) for cross-cutting items that land in Phase 2.

---

## Recommended Plan Structure

Planner should decompose Phase 1 into **5 waves + test infrastructure**, roughly parallel where dependencies allow.

### Wave 0 — Test Infrastructure (mandatory, kicks off phase)
Scope: set up test harnesses so subsequent waves ship with coverage.
- **Plan 0.1** — C++ automation test scaffold (`NyraEditor/Private/Tests/`, placeholder `BEGIN_DEFINE_SPEC` files, Build.cs `bBuildDeveloperTools` confirm)
- **Plan 0.2** — Python pytest scaffold (`NyraHost/pyproject.toml`, `conftest.py` fixtures, `requirements-dev.lock`)

### Wave 1 — Plugin Scaffolding + Handshake Spec (sequential with Wave 0)
Scope: two-module skeleton, `.uplugin`, Build.cs, empty Slate tab registration, handshake spec document committed.
- **Plan 1.1** — `.uplugin` + NyraEditor/NyraRuntime Build.cs + directory layout + empty module Startup/Shutdown
- **Plan 1.2** — Nomad tab registration under `Tools > NYRA > Chat`, empty `SNyraChatPanel` placeholder rendering "NYRA — not yet connected"
- **Plan 1.3** — Specs: `docs/HANDSHAKE.md` + `docs/JSONRPC.md` (method surface D-10, error codes D-11) as canonical references

### Wave 2 — NyraHost + NyraInfer + Supervisor (parallel-safe after Wave 1 plan 1.3)
Scope: Python sidecar that speaks JSON-RPC; llama-server spawn + Ollama detect; C++ supervisor driving both.
- **Plan 2.1** — NyraHost Python package: entry point, structlog setup, asyncio WS server, `session/authenticate` + `session/hello`
- **Plan 2.2** — NyraHost: SQLite storage layer + attachment ingestion (CD-07, CD-08)
- **Plan 2.3** — NyraHost: llama-server spawn + port capture + Ollama detect
- **Plan 2.4** — NyraHost: Gemma downloader (FHttpModule on UE side OR Python side — recommend Python side for simpler progress reporting via WS)
- **Plan 2.5** — C++ `FNyraSupervisor`: spawn NyraHost via `FMonitoredProcess`, handshake file polling, 3-in-60s policy, in-flight request replay

### Wave 3 — Chat Panel + Integration (after Wave 2)
Scope: the user-facing panel wired to the working backend.
- **Plan 3.1** — `FNyraWsClient` wrapping `FWebSocketsModule`, JSON-RPC encode/decode
- **Plan 3.2** — `NyraMarkdownParser` (C++ subset: headings, bold, italic, inline code, fenced code, links, lists)
- **Plan 3.3** — `SNyraChatPanel` full layout: message list (`SListView`), composer (`SMultiLineEditableTextBox`), attachment chips, history drawer (CD-05), code copy buttons (CD-06)
- **Plan 3.4** — Streaming token flow: plain `STextBlock` during stream, `SRichTextBlock` swap on done; error remediation rendering from `error.data.remediation`

### Wave 4 — First-Run UX + Error States (after Wave 3)
Scope: banner states, download modal, diagnostics drawer, graceful states.
- **Plan 4.1** — Bootstrap toast (venv build), host-unstable banner, handshake timeout state
- **Plan 4.2** — Gemma download modal (progress bar, cancel, resume) — integrates with Plan 2.4's downloader
- **Plan 4.3** — Diagnostics drawer (collapsed by default, shows tail of `nyrahost-YYYY-MM-DD.log` on demand; if `diagnostics/tail` method fits scope, otherwise reads logs directly from disk)

### Wave 5 — Stability Gate + Ring 0 Harness (after Wave 3; parallel with Wave 4)
Scope: the 100-round-trip benchmark command and its pass-criteria enforcement.
- **Plan 5.1** — `Nyra.Dev.RoundTripBench <N>` console command implementation with metric capture, percentile calc, pass/fail report
- **Plan 5.2** — Editor-responsiveness assertion (tick-time sampling during streaming window)
- **Plan 5.3** — Integration test `Nyra.Dev.RoundTripBench 100` runs green on dev machine; results committed to `.planning/phases/01-plugin-shell-three-process-ipc/ring0-bench-results.md`

### Dependency graph

```
Wave 0 ─┬─> Wave 1 ─┬─> Wave 2 ─┬─> Wave 3 ─┬─> Wave 4
        │           │           │           │
        │           │           │           └─> Wave 5 (parallel)
        │           │           │
        │           └───────────┘
        │
        └── (Wave 0 plans can interleave with Wave 1)
```

Wave 2 plans 2.1-2.4 can run parallel to each other (different Python files), then 2.5 pulls them together.
Wave 3 plans 3.1-3.2 can run parallel (different C++ areas), then 3.3 integrates, then 3.4.

**Estimated plan count:** 15 plans (2 + 3 + 5 + 4 + 3 + 3). Reasonable for a Phase 1 that validates the whole architectural spine.

---

## Open Questions

1. **Does `FWebSocketsModule` reliably deliver messages on GameThread in UE 5.6 under high-frequency burst?**
   - What we know: It's a game-tick-group-driven poll in standard UE builds.
   - What's unclear: Whether a 100-frame burst during 16ms frame has measurable tick-time impact.
   - Recommendation: First Wave 5 measurement will answer this. If problematic, Phase 2 refactor to dedicated WS thread + GameThread marshalling.

2. **Is the bundled `WebSockets` module's `libwebsockets` version on UE 5.6 current enough to negotiate modern protocols cleanly?**
   - What we know: UE 5.6 ships libwebsockets from its ThirdParty source tree.
   - What's unclear: Exact libwebsockets version; ping/pong keepalive defaults.
   - Recommendation: Test harness exercises ping/pong during long idle periods; if issue, add explicit WS ping from our side every 60s.

3. **Can we use SQLite WAL mode cleanly with venv-bundled Python on cross-user scenarios?**
   - What we know: WAL is the right choice for NyraHost (single-writer).
   - What's unclear: On non-NTFS filesystems (e.g., network drives mapped to project dirs), WAL behaviour is problematic.
   - Recommendation: Document that NYRA assumes NTFS for the `Saved/NYRA/` path; if the project is on a network drive, log a warning and downgrade to `journal_mode=DELETE`.

4. **Exact python-build-standalone release tag to pin.**
   - What we know: `latest-release.json` endpoint exists; tags are `YYYYMMDD`.
   - What's unclear: Which specific tag to pin for Phase 1.
   - Recommendation: Wave 1 Plan 1.1 resolves the current tag and commits the download URL + SHA256 to `nyrahost/bootstrap.py`.

5. **Does bundling 3× llama-server variants (cuda/vulkan/cpu) fit Phase 1 disk budget?**
   - What we know: ~60 MB total for three backends; CONTEXT.md says "bundled llama.cpp release (~20 MB, CPU + CUDA + Vulkan backends)" which implies a single-binary with all backends.
   - What's unclear: Whether llama-server has a unified multi-backend build mode in current releases.
   - Recommendation: Wave 2 Plan 2.3 investigates current ggml-org release artefacts; if a unified binary exists, use it; else the per-subfolder layout above.

6. **Is the `diagnostics/tail` method in Phase 1 scope?**
   - What we know: CONTEXT.md §specifics says "planner adds to the method surface if it fits Phase 1 scope; otherwise Phase 2."
   - Recommendation: Skip in Phase 1. The diagnostics drawer can `tail` the log file directly from disk (UE has `FFileHelper::LoadFileToStringArray`); no WS call needed. Saves one method and its Python handler.

7. **Download flow for Gemma — UE-side `FHttpModule` or Python `httpx`?**
   - What we know: Both work. `FHttpModule` has native UE progress-bar integration; `httpx` keeps the code in NyraHost where the file lives.
   - Recommendation: Python side. NyraHost downloads; emits periodic `diagnostics/download-progress` notifications (new Phase 1 notification — tiny addition, avoids bifurcating download logic). This keeps UE code smaller and the download logic testable in pytest.

---

## Sources

### Primary (HIGH confidence)

- `https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/WebSockets/FWebSocketsModule` — UE 5.6 WebSockets module
- `https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Core/Misc/FMonitoredProcess/` — FMonitoredProcess API
- `https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Core/GenericPlatform/FGenericPlatformProcess` — process primitives
- `https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Slate/Framework/Docking/FGlobalTabmanager` — nomad tab registration
- `https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Slate/Widgets/Text/SRichTextBlock` — rich text block
- `https://www.unrealengine.com/en-US/tech-blog/advanced-text-styling-with-rich-text-block` — official tech blog on decorators
- `https://dev.epicgames.com/documentation/en-us/unreal-engine/plugins-in-unreal-engine` — .uplugin descriptor
- `https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md` — llama-server flags
- `https://docs.ollama.com/api/tags` — Ollama /api/tags response shape
- `https://github.com/ollama/ollama/blob/main/docs/api.md` — Ollama OpenAI-compat surface
- `https://huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf` — Gemma model page
- `https://github.com/astral-sh/python-build-standalone/releases` — python-build-standalone releases
- `https://gregoryszorc.com/docs/python-build-standalone/main/running.html` — running the distribution
- `https://raw.githubusercontent.com/astral-sh/python-build-standalone/latest-release/latest-release.json` — machine-readable latest tag
- `https://www.jsonrpc.org/specification` — JSON-RPC 2.0 wire envelope
- `https://modelcontextprotocol.io/specification/2025-11-25/` — MCP vocabulary (for future Phase 3 alignment)

### Secondary (MEDIUM confidence — WebSearch verified, not Context7-deep)

- `https://unrealcommunity.wiki/websocket-client-cpp-5vk7hp9e` — community WS client reference
- `https://github.com/Nauja/ue4-richtextblocktooltip-sample` — custom URichTextBlockDecorator worked sample
- `https://forums.unrealengine.com/t/how-can-i-package-runtime-dependencies-from-an-engine-plugin/433361` — RuntimeDependencies staging pattern
- `https://forums.unrealengine.com/t/how-can-i-properly-use-fplatformprocess-readpipe/507109` — pipe usage
- `https://devblogs.microsoft.com/oldnewthing/20110707-00/?p=10223` — pipe-deadlock canonical Microsoft explanation
- `https://manpages.debian.org/unstable/llama.cpp-tools/llama-server.1.en.html` — llama-server man page

### Tertiary (LOW confidence — training data or unverified single source)

- Exact UE 5.6 `libwebsockets` version — unverified.
- Current `astral-sh/python-build-standalone` tag as of 2026-04-21 — verify at Wave 1 time via latest-release.json.
- Whether ggml-org ships a single multi-backend llama-server binary in April 2026 or still three separate ones — verify at Wave 2.

---

## Metadata

**Confidence breakdown:**

| Area | Level | Reason |
|------|-------|--------|
| Slate panel mechanics | MEDIUM-HIGH | SRichTextBlock pattern is Epic-official; streaming render strategy unverified under load. |
| WebSocket client | HIGH | `FWebSocketsModule` is well-documented and used by many UE plugins. |
| Subprocess supervision | HIGH | FMonitoredProcess + pipe patterns are battle-tested; 3-in-60s policy is straightforward. |
| Embedded Python | HIGH | python-build-standalone is widely used (uv, Astral), venv pattern is standard. |
| llama-server + Ollama | HIGH | llama.cpp README verified; Ollama /api/tags response verified via docs. |
| Ring 0 harness | HIGH (design) / MEDIUM (thresholds) | Straightforward to implement; pass thresholds empirical. |
| SQLite / persistence | HIGH | Single-writer WAL is textbook; Python stdlib sqlite3 is mature. |
| Build.cs / .uplugin staging | HIGH | Epic docs + forum answers converge. |
| First-run UX flow | HIGH (state machine) / MEDIUM (exact copy) | State machine is logical; copy is UI polish. |
| Phase 1 pitfalls | HIGH | Known Windows + UE patterns; no novel unknowns. |

**Research date:** 2026-04-21
**Valid until:** 2026-05-21 (30 days; shorter if llama.cpp or UE 5.6 sees a breaking change in the interim)
