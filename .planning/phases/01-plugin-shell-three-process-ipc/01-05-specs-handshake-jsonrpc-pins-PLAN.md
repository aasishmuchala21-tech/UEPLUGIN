---
phase: 01-plugin-shell-three-process-ipc
plan: 05
type: execute
wave: 1
depends_on: []
autonomous: true
requirements: [PLUG-02, PLUG-03]
files_modified:
  - docs/HANDSHAKE.md
  - docs/JSONRPC.md
  - docs/ERROR_CODES.md
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/ModelPins.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/ModelPins.cpp
  - TestProject/Plugins/NYRA/Source/NyraHost/assets-manifest.json
objective: >
  Lock the three canonical wire contracts for Phase 1 as versioned documents
  so every later plan (Python Plan 06 AND C++ Plan 10) writes against the
  SAME spec:

  1. `docs/HANDSHAKE.md` — file path, schema, atomic-write protocol, PID
     scope, stale cleanup (D-06, §3.10 P1.1, §3.10 P1.2).
  2. `docs/JSONRPC.md` — method surface, envelopes, streaming semantics
     (D-09 through D-12).
  3. `docs/ERROR_CODES.md` — the -32001..-32006 table with remediation
     strings (D-11).

  Additionally, commit MODEL PINS (C++ constants) for the Gemma GGUF SHA256
  + HF revision SHA + python-build-standalone tag + llama.cpp release tag,
  and an `assets-manifest.json` that Plan 06's prebuild.ps1 reads. Resolves
  RESEARCH Open Questions 4 (python-build-standalone tag pin) and 5
  (llama-server variant strategy).
must_haves:
  truths:
    - "docs/HANDSHAKE.md describes exactly one handshake file path, one JSON schema, and the atomic rename + PID cleanup protocol"
    - "docs/JSONRPC.md describes each of the 6 locked methods (D-10) with full envelope + example frames"
    - "docs/ERROR_CODES.md lists all 6 codes -32001..-32006 with machine-readable name AND user-facing remediation template"
    - "ModelPins.h exports const FStringView for Gemma model URL, Gemma SHA256, HF revision SHA, python-build-standalone tag, llama.cpp release tag — ready for Plan 06/08/09 to import"
    - "assets-manifest.json lists every artefact prebuild.ps1 must fetch with url + sha256 + dest"
    - "All three doc files are cross-linked (JSONRPC -> ERROR_CODES references, HANDSHAKE -> JSONRPC references)"
  artifacts:
    - path: docs/HANDSHAKE.md
      provides: "Canonical handshake-file protocol spec"
      contains: "%LOCALAPPDATA%/NYRA/handshake-<editor-pid>.json"
    - path: docs/JSONRPC.md
      provides: "Canonical wire-protocol spec for all 6 methods"
      contains: "session/authenticate"
    - path: docs/ERROR_CODES.md
      provides: "Canonical error code table for panel remediation rendering"
      contains: "-32001"
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/ModelPins.h
      provides: "C++ constants Plan 06/08/09 consume to avoid duplicating URLs"
      exports: ["GemmaGgufUrl", "GemmaGgufSha256", "PythonBuildStandaloneTag", "LlamaCppReleaseTag"]
    - path: TestProject/Plugins/NYRA/Source/NyraHost/assets-manifest.json
      provides: "Machine-readable manifest for prebuild.ps1"
      contains: "gemma-3-4b-it-qat-q4_0.gguf"
  key_links:
    - from: docs/JSONRPC.md §3 method surface
      to: docs/ERROR_CODES.md
      via: "cross-reference for each method's potential error codes"
      pattern: "ERROR_CODES.md"
    - from: ModelPins.h
      to: assets-manifest.json
      via: "C++ constants mirror the manifest values"
      pattern: "GemmaGgufUrl"
    - from: docs/HANDSHAKE.md
      to: docs/JSONRPC.md
      via: "describes that first frame after WS upgrade must be session/authenticate"
      pattern: "session/authenticate"
---

<objective>
Ship the three canonical wire-format specs + model pins so Plans 06 (Python
NyraHost), 08 (llama-server spawn), 09 (Gemma downloader), and 10 (C++ WS
client + supervisor) all compile against the SAME shared contract.

Per RESEARCH Open Questions:
- Q4: python-build-standalone tag pin — resolved here by curl'ing
  `latest-release.json` and committing the exact tag + download URL +
  SHA256 as a C++ constant.
- Q5: llama-server bundle strategy — investigated; PICK (ship per-backend
  subfolders cuda/ vulkan/ cpu/ with 3 distinct binaries; RESEARCH §3.5).
- Q6: diagnostics/tail method — SKIP in Phase 1 (log tail read directly
  from disk via FFileHelper). Documented in JSONRPC.md as "Phase 2 addition."
- Q7: Gemma download — Python-side with diagnostics/download-progress
  notification. Documented in JSONRPC.md.

Per CONTEXT.md:
- D-06: handshake file format
- D-07: session/authenticate first-frame protocol
- D-09/D-10: JSON-RPC 2.0 envelope + 6-method surface
- D-11: error codes with remediation

Purpose: Unambiguous source of truth for later plans. "Is session/hello a
notification or a request?" → check docs/JSONRPC.md, no debate.
Output: Three .md specs + ModelPins.h/.cpp + assets-manifest.json.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md
</context>

<interfaces>
JSON-RPC 2.0 envelope canonical forms (D-09):

```
// Request
{"jsonrpc":"2.0","id":<number>,"method":"<name>","params":<object>}

// Success response
{"jsonrpc":"2.0","id":<number>,"result":<object>}

// Error response
{"jsonrpc":"2.0","id":<number>,"error":{"code":<number>,"message":"<str>","data":{"remediation":"<str>"}}}

// Notification (no id)
{"jsonrpc":"2.0","method":"<name>","params":<object>}
```

Phase 1 method surface (D-10) — six methods exactly:

| Method | Direction | Shape | Purpose |
|--------|-----------|-------|---------|
| session/authenticate | UE -> NyraHost (request) | params: `{token: string}` → result: `{authenticated: true, session_id: string}` | First WS frame; rejects with close 4401 if bad |
| session/hello | UE -> NyraHost (request) | params: `{}` → result: `{backends: ["gemma-local"], phase: 1, session_id: string}` | Capability discovery |
| chat/send | UE -> NyraHost (request) | params: `{conversation_id, req_id, content, backend?}` → result: `{req_id, streaming: true}` | Start a chat; tokens stream via chat/stream |
| chat/stream | NyraHost -> UE (notification) | params: `{conversation_id, req_id, delta, done, cancelled?, usage?, error?}` | Token delta (one frame per model chunk) |
| chat/cancel | UE -> NyraHost (notification) | params: `{conversation_id, req_id}` | Idempotent cancel |
| shutdown | UE -> NyraHost (notification) | params: `{}` | Graceful close |
| sessions/list | UE -> NyraHost (request) | params: `{limit?: int}` → result: `{conversations: [{id, title, updated_at, message_count}, …]}` | History drawer list (CD-05, Plan 12b) |
| sessions/load | UE -> NyraHost (request) | params: `{conversation_id, limit?: int}` → result: `{conversation_id, messages: [{id, role, content, created_at, attachments}, …]}` | Load a past conversation (CD-05, Plan 12b) |

Plus one ADDITIONAL notification (resolves Open Question 7):

| diagnostics/download-progress | NyraHost -> UE (notification) | params: `{asset: string, bytes_done, bytes_total, status: "downloading"\|"verifying"\|"done"\|"error", error?: {...}}` | Gemma + future model download progress |

Error codes (D-11):

| Code | Name | Remediation hint template |
|------|------|--------------------------|
| -32001 | subprocess_failed | "A background NYRA process stopped unexpectedly. Click [Restart] or see Saved/NYRA/logs/." |
| -32002 | auth | "Authentication to NyraHost failed. Restart the editor or delete the handshake file at %LOCALAPPDATA%/NYRA/." |
| -32003 | rate_limit | "Claude rate limit reached. Switching to Gemma local. (Phase 2)" |
| -32004 | model_not_loaded | "Model not yet loaded — warming up. Retry in a moment." |
| -32005 | gemma_not_installed | "Gemma model missing. Click [Download Gemma] in Settings." |
| -32006 | infer_oom | "Gemma ran out of memory. Try a shorter prompt or close other GPU workloads." |
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: docs/HANDSHAKE.md + docs/JSONRPC.md + docs/ERROR_CODES.md</name>
  <files>
    docs/HANDSHAKE.md
    docs/JSONRPC.md
    docs/ERROR_CODES.md
  </files>
  <read_first>
    - .planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md D-06, D-07, D-09, D-10, D-11, D-12
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.10 P1.1 (atomic rename), P1.2 (PID cleanup), P1.7 (JSON-RPC id persistence + session_id envelope check)
  </read_first>
  <action>
    Create `docs/HANDSHAKE.md`:

    ```markdown
    # NYRA Handshake Protocol

    **Status:** Locked in Phase 1 Plan 05. See CONTEXT.md D-06, D-07.

    ## File path

    - **Primary:** `%LOCALAPPDATA%/NYRA/handshake-<editor-pid>.json`
    - **Fallback (if LOCALAPPDATA unwritable):** `<ProjectDir>/Saved/NYRA/handshake-<editor-pid>.json`
    - **Permissions (Windows NTFS):** DACL restricted to the current user SID (owner only read/write). NyraHost applies ACL after atomic rename.

    ## JSON schema (D-06 exact)

    ```json
    {
        "port":          <integer>,       // ephemeral TCP port NyraHost bound via 127.0.0.1:0
        "token":         "<hex-string>",  // 64 hex chars (32 bytes from secrets.token_bytes)
        "nyrahost_pid":  <integer>,       // PID of python.exe running `-m nyrahost`
        "ue_pid":        <integer>,       // PID of the UE editor process that spawned NyraHost
        "started_at":    <integer>        // unix timestamp in MILLISECONDS (ms since epoch)
    }
    ```

    ## Writer protocol (NyraHost side)

    1. Bind `127.0.0.1:0` and capture assigned port.
    2. Generate token via `secrets.token_bytes(32).hex()` -> 64 hex chars.
    3. Start WS server's accept loop.
    4. Open `%LOCALAPPDATA%/NYRA/handshake-<ue_pid>.json.tmp` for write.
    5. `json.dump(payload, f)`, `f.flush()`, `os.fsync(f.fileno())`, `f.close()`.
    6. `os.replace(tmp_path, final_path)` — **atomic on Windows NTFS**.
    7. Apply owner-only DACL via `pywin32` `win32security.SetNamedSecurityInfo`.

    **Why atomic rename:** readers may poll between steps 4 and 6 and see an
    empty or partial JSON. `os.replace` guarantees readers see either the
    old file (or nothing) or the complete new file — never a half-written state.

    ## Reader protocol (UE side)

    ```cpp
    // FNyraHandshake::Poll() — called from a ticker
    // Initial delay 50ms, ×1.5 backoff, capped at 2s, total budget 30s.
    ```

    1. Stat `%LOCALAPPDATA%/NYRA/handshake-<our-pid>.json`.
    2. If not present, continue backoff.
    3. If present, read via `FFileHelper::LoadFileToString`.
    4. Parse as JSON. **If parse fails, treat as not-ready and continue backoff**
       (tolerates mid-write race per RESEARCH §3.10 P1.1).
    5. Validate all 5 fields present and types match. If validation fails,
       treat as corrupt; continue backoff up to 30s deadline.
    6. On valid: connect `ws://127.0.0.1:<port>/` and send
       `session/authenticate` as first frame (see docs/JSONRPC.md §3.1).

    ## Disconnect / cleanup

    - **UE clean shutdown:** UE deletes its own `handshake-<our-pid>.json` during
      `FNyraEditorModule::ShutdownModule`, AFTER the graceful `shutdown` JSON-RPC
      notification and NyraHost exit acknowledgement.
    - **UE force-kill:** handshake file leaks; next NyraEditor startup scans
      `%LOCALAPPDATA%/NYRA/handshake-*.json`, reads `ue_pid`, checks
      `FPlatformProcess::IsProcRunning` (or `OpenProcess` failing); if dead,
      also checks `nyrahost_pid` and `TerminateProc(KillTree=true)` if the
      orphaned NyraHost is still alive. Then deletes the stale file.

    ## Multiple editor instances

    Because filename includes `<ue_pid>`, concurrent editors do not collide.
    Each editor only reads/deletes its own PID-scoped file.

    ## Related specs

    - First WS frame protocol: `docs/JSONRPC.md` §3.1
    - Error code -32002 (auth) if handshake token rejected: `docs/ERROR_CODES.md`
    ```

    Create `docs/JSONRPC.md`:

    ```markdown
    # NYRA JSON-RPC 2.0 Wire Protocol (Phase 1)

    **Status:** Locked in Phase 1 Plan 05. See CONTEXT.md D-09 through D-12.
    **Transport:** Loopback WebSocket `ws://127.0.0.1:<port>/` (port from handshake).
    **Framing:** Text JSON only (D-12). One JSON object per WS text frame.
    **Envelope:** JSON-RPC 2.0 (https://www.jsonrpc.org/specification).

    ## 1. Envelopes

    ### 1.1 Request
    ```json
    {"jsonrpc":"2.0","id":<integer>,"method":"<string>","params":<object>}
    ```

    ### 1.2 Success response
    ```json
    {"jsonrpc":"2.0","id":<integer>,"result":<object>}
    ```

    ### 1.3 Error response
    ```json
    {"jsonrpc":"2.0","id":<integer>,"error":{"code":<integer>,"message":"<string>","data":{"remediation":"<string>"}}}
    ```

    ### 1.4 Notification (no id, no response)
    ```json
    {"jsonrpc":"2.0","method":"<string>","params":<object>}
    ```

    ## 2. Id policy (P1.7)

    - UE maintains one monotonic `FAtomicInt64 NextId { 1 }` counter for the
      lifetime of the editor process. NEVER reset on WS reconnect.
    - NyraHost returns one fresh `session_id` (UUID) in every `session/hello`
      response. UE tags each outgoing request with the CURRENT session_id as
      an implicit wrapper (stored in params for request methods that care,
      or tracked client-side for correlation). Responses with mismatched
      session_id are discarded.

    ## 3. Method surface (Phase 1)

    All methods are sent over the loopback WS in UTF-8 JSON text frames.

    ### 3.1 `session/authenticate` — Request (UE → NyraHost)

    **MUST be the first frame** UE sends after `Connection: Upgrade`.

    Request:
    ```json
    {"jsonrpc":"2.0","id":1,"method":"session/authenticate","params":{"token":"<64-hex>"}}
    ```
    Success response:
    ```json
    {"jsonrpc":"2.0","id":1,"result":{"authenticated":true,"session_id":"<uuid>"}}
    ```
    Failure behaviour: NyraHost closes the WS with **close code 4401**,
    reason `"unauthenticated"` (not an error response — a close frame).

    ### 3.2 `session/hello` — Request (UE → NyraHost)

    Request:
    ```json
    {"jsonrpc":"2.0","id":2,"method":"session/hello","params":{}}
    ```
    Response:
    ```json
    {"jsonrpc":"2.0","id":2,"result":{"backends":["gemma-local"],"phase":1,"session_id":"<uuid>"}}
    ```

    ### 3.3 `chat/send` — Request (UE → NyraHost)

    Request:
    ```json
    {"jsonrpc":"2.0","id":3,"method":"chat/send","params":{
      "conversation_id":"<uuid>",
      "req_id":"<uuid>",
      "content":"user text here",
      "backend":"gemma-local"
    }}
    ```
    Immediate response (does NOT wait for tokens):
    ```json
    {"jsonrpc":"2.0","id":3,"result":{"req_id":"<uuid>","streaming":true}}
    ```
    Tokens arrive via `chat/stream` notifications (§3.4).

    On error before streaming begins:
    ```json
    {"jsonrpc":"2.0","id":3,"error":{"code":-32005,"message":"gemma_not_installed","data":{"remediation":"Gemma model missing. Click [Download Gemma] in Settings."}}}
    ```
    See `docs/ERROR_CODES.md` for full table.

    ### 3.4 `chat/stream` — Notification (NyraHost → UE)

    Emitted once per model chunk (NOT per byte — D-10). Panel coalesces before
    markdown render.

    ```json
    {"jsonrpc":"2.0","method":"chat/stream","params":{
      "conversation_id":"<uuid>",
      "req_id":"<uuid>",
      "delta":"Hello",
      "done":false
    }}
    ```
    Final frame:
    ```json
    {"jsonrpc":"2.0","method":"chat/stream","params":{
      "conversation_id":"<uuid>",
      "req_id":"<uuid>",
      "delta":"",
      "done":true,
      "usage":{"prompt_tokens":10,"completion_tokens":2,"total_tokens":12}
    }}
    ```
    Cancelled frame (after chat/cancel was received):
    ```json
    {"jsonrpc":"2.0","method":"chat/stream","params":{
      "conversation_id":"<uuid>",
      "req_id":"<uuid>",
      "delta":"",
      "done":true,
      "cancelled":true
    }}
    ```
    Error frame (mid-stream failure):
    ```json
    {"jsonrpc":"2.0","method":"chat/stream","params":{
      "conversation_id":"<uuid>",
      "req_id":"<uuid>",
      "delta":"",
      "done":true,
      "error":{"code":-32006,"message":"infer_oom","data":{"remediation":"..."}}
    }}
    ```

    ### 3.5 `chat/cancel` — Notification (UE → NyraHost)

    ```json
    {"jsonrpc":"2.0","method":"chat/cancel","params":{"conversation_id":"<uuid>","req_id":"<uuid>"}}
    ```
    Idempotent. NyraHost SIGTERMs the llama-server request (or closes the
    HTTP stream) and emits a final `chat/stream` with `done:true, cancelled:true`.

    ### 3.6 `shutdown` — Notification (UE → NyraHost)

    ```json
    {"jsonrpc":"2.0","method":"shutdown","params":{}}
    ```
    NyraHost flushes logs, closes SQLite, SIGTERMs NyraInfer, exits with code 0.

    ### 3.7 `diagnostics/download-progress` — Notification (NyraHost → UE)

    ```json
    {"jsonrpc":"2.0","method":"diagnostics/download-progress","params":{
      "asset":"gemma-3-4b-it-qat-q4_0.gguf",
      "bytes_done":1073741824,
      "bytes_total":3391733760,
      "status":"downloading"
    }}
    ```
    `status` ∈ `{"downloading","verifying","done","error"}`. When
    `status=="error"`, an `error` field is present with the same shape as
    chat/stream's error field.

    ### 3.8 `sessions/list` — Request (UE → NyraHost)

    Returns recent conversations for the history drawer (CD-05).

    Request:
    ```json
    {"jsonrpc":"2.0","id":4,"method":"sessions/list","params":{"limit":50}}
    ```
    Response (`params.limit` optional, default 50; sorted by `updated_at` DESC):
    ```json
    {"jsonrpc":"2.0","id":4,"result":{"conversations":[
      {"id":"<uuid>","title":"Fix lighting","updated_at":1713690000000,"message_count":12}
    ]}}
    ```

    ### 3.9 `sessions/load` — Request (UE → NyraHost)

    Loads the last N messages for a conversation (default N=200).

    Request:
    ```json
    {"jsonrpc":"2.0","id":5,"method":"sessions/load","params":{"conversation_id":"<uuid>","limit":200}}
    ```
    Response:
    ```json
    {"jsonrpc":"2.0","id":5,"result":{
      "conversation_id":"<uuid>",
      "messages":[
        {"id":"<uuid>","role":"user","content":"hi","created_at":1713689999000,"attachments":[]},
        {"id":"<uuid>","role":"assistant","content":"hello","created_at":1713690000000,"attachments":[]}
      ]
    }}
    ```

    ## 4. Reserved (not in Phase 1)

    - `diagnostics/tail` — log tailing. **Phase 2 addition.** Phase 1 panel
      reads `Saved/NYRA/logs/nyrahost-YYYY-MM-DD.log` directly via
      `FFileHelper::LoadFileToStringArray`.

    ## 5. Error codes

    See `docs/ERROR_CODES.md` for the canonical table.
    ```

    Create `docs/ERROR_CODES.md`:

    ```markdown
    # NYRA JSON-RPC Error Codes

    **Status:** Locked in Phase 1 Plan 05. See CONTEXT.md D-11.

    Machine-readable codes live in Phase 1 methods that can return them
    (chat/send response, chat/stream error field). User-facing remediation
    strings come from `error.data.remediation` — the panel renders this
    verbatim inside an error bubble.

    ## Canonical table

    | Code   | Name                  | When                                                  | Remediation template                                                                                           |
    |--------|-----------------------|-------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
    | -32001 | subprocess_failed     | NyraHost or NyraInfer exited unexpectedly mid-request | "A background NYRA process stopped unexpectedly. Click [Restart] or see Saved/NYRA/logs/."                     |
    | -32002 | auth                  | session/authenticate token mismatch                   | "Authentication to NyraHost failed. Restart the editor or delete the handshake file at %LOCALAPPDATA%/NYRA/."  |
    | -32003 | rate_limit            | **Phase 2 placeholder** (Claude 429)                  | "Claude rate limit reached. Switching to Gemma local. (Phase 2)"                                               |
    | -32004 | model_not_loaded      | llama-server still warming                            | "Model not yet loaded — warming up. Retry in a moment."                                                        |
    | -32005 | gemma_not_installed   | chat/send with backend=gemma-local, no .gguf on disk  | "Gemma model missing. Click [Download Gemma] in Settings or run `nyra install gemma`."                         |
    | -32006 | infer_oom             | llama-server returns OOM / closes 5xx stream          | "Gemma ran out of memory. Try a shorter prompt or close other GPU workloads."                                  |

    ## Wire shape

    ```json
    {"error":{"code":-32005,"message":"gemma_not_installed","data":{"remediation":"Gemma model missing. Click [Download Gemma] in Settings or run `nyra install gemma`."}}}
    ```

    ## Panel rendering rules

    1. The panel NEVER renders `error.message` verbatim (that's programmatic).
    2. The panel DOES render `error.data.remediation` verbatim as Markdown
       inside a red-accent bubble.
    3. Buttons referenced as `[Download Gemma]`, `[Restart]`, `[Open log]`
       are mapped to real Slate buttons by the panel — the remediation text
       may contain up to 2 bracketed button hints per message.
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "%LOCALAPPDATA%/NYRA/handshake-" docs/HANDSHAKE.md` >= 2
      - `grep -c "os.replace" docs/HANDSHAKE.md` >= 1
      - `grep -c "session/authenticate" docs/JSONRPC.md` >= 3
      - `grep -c "session/hello" docs/JSONRPC.md` >= 2
      - `grep -c "chat/send" docs/JSONRPC.md` >= 2
      - `grep -c "chat/stream" docs/JSONRPC.md` >= 3
      - `grep -c "chat/cancel" docs/JSONRPC.md` >= 2
      - `grep -c "shutdown" docs/JSONRPC.md` >= 2
      - `grep -c "diagnostics/download-progress" docs/JSONRPC.md` >= 2
      - `grep -c "sessions/list" docs/JSONRPC.md` >= 2
      - `grep -c "sessions/load" docs/JSONRPC.md` >= 2
      - `grep -c "^| -32001" docs/ERROR_CODES.md` equals 1
      - `grep -c "^| -32002" docs/ERROR_CODES.md` equals 1
      - `grep -c "^| -32003" docs/ERROR_CODES.md` equals 1
      - `grep -c "^| -32004" docs/ERROR_CODES.md` equals 1
      - `grep -c "^| -32005" docs/ERROR_CODES.md` equals 1
      - `grep -c "^| -32006" docs/ERROR_CODES.md` equals 1
    </automated>
  </verify>
  <acceptance_criteria>
    - File docs/HANDSHAKE.md contains literal text `%LOCALAPPDATA%/NYRA/handshake-<editor-pid>.json`
    - File docs/HANDSHAKE.md contains literal text `os.replace(tmp_path, final_path)` AND literal text `atomic on Windows NTFS`
    - File docs/HANDSHAKE.md contains literal text `secrets.token_bytes(32).hex()`
    - File docs/HANDSHAKE.md contains literal text `close code 4401` (via cross-ref to JSONRPC.md)
    - File docs/HANDSHAKE.md contains literal text `FFileHelper::LoadFileToString`
    - File docs/JSONRPC.md contains literal text `## Method: session/authenticate` OR `### 3.1 \`session/authenticate\``
    - File docs/JSONRPC.md contains all 6 locked method names: `session/authenticate`, `session/hello`, `chat/send`, `chat/stream`, `chat/cancel`, `shutdown`
    - File docs/JSONRPC.md contains literal text `sessions/list` and `sessions/load` (history drawer methods, per Plan 12b)
    - File docs/JSONRPC.md contains literal text `diagnostics/download-progress`
    - File docs/JSONRPC.md contains literal text `close code 4401`
    - File docs/JSONRPC.md contains literal text `{"jsonrpc":"2.0"`
    - File docs/JSONRPC.md contains literal text `one frame per model chunk`
    - File docs/JSONRPC.md contains literal text `FAtomicInt64 NextId { 1 }` (id policy)
    - File docs/ERROR_CODES.md contains a table row for each of `-32001`, `-32002`, `-32003`, `-32004`, `-32005`, `-32006`
    - File docs/ERROR_CODES.md contains literal text `subprocess_failed`, `auth`, `rate_limit`, `model_not_loaded`, `gemma_not_installed`, `infer_oom`
    - File docs/ERROR_CODES.md contains literal text `error.data.remediation`
  </acceptance_criteria>
  <done>Three spec .md files on disk; every later plan has an unambiguous wire contract to write against.</done>
</task>

<task type="auto">
  <name>Task 2: ModelPins.h/.cpp + assets-manifest.json (python-build-standalone, Gemma, llama.cpp)</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraEditor/Public/ModelPins.h
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/ModelPins.cpp
    TestProject/Plugins/NYRA/Source/NyraHost/assets-manifest.json
  </files>
  <read_first>
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.4 (python-build-standalone latest-release.json), §3.5 (Gemma GGUF URL + HF revision, llama.cpp release naming pattern)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md D-13, D-17, D-18
    - docs/BINARY_DISTRIBUTION.md (created in Plan 03)
  </read_first>
  <action>
    **At execute time, RESOLVE live values** by running:

    ```bash
    # python-build-standalone latest tag
    curl -s https://raw.githubusercontent.com/astral-sh/python-build-standalone/latest-release/latest-release.json > /tmp/pbs.json

    # Gemma GGUF HF revision
    curl -s https://huggingface.co/api/models/google/gemma-3-4b-it-qat-q4_0-gguf > /tmp/gemma.json
    ```

    Extract:
    - `pbs.json .tag` -> PBS_TAG (e.g. `20251120`)
    - `pbs.json .asset_urls[] | select(.|contains("cpython-3.12") and contains("x86_64-pc-windows-msvc-shared-install_only"))` -> PBS_URL
    - fetch the corresponding .sha256 from the release's checksums file
    - `gemma.json .sha` -> GEMMA_REV_SHA
    - Gemma GGUF file SHA256: download the `.gguf` file's sidecar hash or use
      HF's `blob.lfs.oid` via `https://huggingface.co/api/models/google/gemma-3-4b-it-qat-q4_0-gguf/tree/main` and pull the GGUF's `lfs.oid` (format `sha256:<hex>`)

    If network is unavailable at execute time, the executor MUST leave
    SENTINEL values in place (`TEXT("TODO_RESOLVE_AT_BUILD")`) AND flag this
    in the Plan 05 SUMMARY.md as a blocker — but the executor MUST still
    create the files with the correct structure.

    Create `TestProject/Plugins/NYRA/Source/NyraEditor/Public/ModelPins.h`:

    ```cpp
    #pragma once
    #include "CoreMinimal.h"

    /**
     * Model + binary distribution pins. Values committed at Plan 05 execution
     * time from python-build-standalone/latest-release.json and the HuggingFace
     * API. Update in coordination with the plugin's major version bump.
     */
    namespace Nyra::ModelPins
    {
        // -------- python-build-standalone --------
        // Tag pattern YYYYMMDD. See RESEARCH §3.4.
        inline const TCHAR* PythonBuildStandaloneTag = TEXT("TODO_RESOLVE_AT_BUILD");
        inline const TCHAR* PythonBuildStandaloneUrl =
            TEXT("https://github.com/astral-sh/python-build-standalone/releases/download/TODO_RESOLVE_AT_BUILD/cpython-3.12.x+TODO_RESOLVE_AT_BUILD-x86_64-pc-windows-msvc-shared-install_only.tar.zst");
        inline const TCHAR* PythonBuildStandaloneSha256 = TEXT("TODO_RESOLVE_AT_BUILD");

        // -------- Gemma 3 4B IT QAT Q4_0 GGUF --------
        // HuggingFace: google/gemma-3-4b-it-qat-q4_0-gguf. See RESEARCH §3.5.
        inline const TCHAR* GemmaHfRepo = TEXT("google/gemma-3-4b-it-qat-q4_0-gguf");
        inline const TCHAR* GemmaHfRevisionSha = TEXT("TODO_RESOLVE_AT_BUILD");
        inline const TCHAR* GemmaGgufFilename = TEXT("gemma-3-4b-it-qat-q4_0.gguf");
        inline const TCHAR* GemmaGgufUrl =
            TEXT("https://huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf/resolve/TODO_RESOLVE_AT_BUILD/gemma-3-4b-it-qat-q4_0.gguf");
        // SHA256 of the .gguf file itself (LFS oid). ~3.16 GB download.
        inline const TCHAR* GemmaGgufSha256 = TEXT("TODO_RESOLVE_AT_BUILD");
        // Fallback mirror on NYRA GitHub Releases (D-17 primary/fallback strategy).
        inline const TCHAR* GemmaGgufMirrorUrl =
            TEXT("https://github.com/nyra-ai/nyra/releases/download/models-v1/gemma-3-4b-it-qat-q4_0.gguf");

        // -------- llama.cpp / llama-server --------
        // Release tag pattern `bNNNN`. See RESEARCH §3.5, §3.10 P1.5.
        inline const TCHAR* LlamaCppReleaseTag = TEXT("TODO_RESOLVE_AT_BUILD");
        // Per-backend ZIPs — three separate assets under the same release.
        inline const TCHAR* LlamaServerCudaZipUrl = TEXT("TODO_RESOLVE_AT_BUILD");
        inline const TCHAR* LlamaServerVulkanZipUrl = TEXT("TODO_RESOLVE_AT_BUILD");
        inline const TCHAR* LlamaServerCpuZipUrl = TEXT("TODO_RESOLVE_AT_BUILD");
        inline const TCHAR* LlamaServerCudaSha256 = TEXT("TODO_RESOLVE_AT_BUILD");
        inline const TCHAR* LlamaServerVulkanSha256 = TEXT("TODO_RESOLVE_AT_BUILD");
        inline const TCHAR* LlamaServerCpuSha256 = TEXT("TODO_RESOLVE_AT_BUILD");
    }
    ```

    Create `TestProject/Plugins/NYRA/Source/NyraEditor/Private/ModelPins.cpp`:

    ```cpp
    #include "ModelPins.h"
    // ModelPins exposes compile-time constants only; no runtime logic here yet.
    // Plan 09 (Gemma downloader) wires these into FHttpModule requests on the
    // Python side via the assets-manifest.json mirror.
    ```

    Create `TestProject/Plugins/NYRA/Source/NyraHost/assets-manifest.json` —
    this is the machine-readable form that `prebuild.ps1` (Plan 06) parses:

    ```json
    {
        "$schema_version": 1,
        "comment": "Values must mirror ModelPins.h. Update both in same commit.",
        "python_build_standalone": {
            "tag": "TODO_RESOLVE_AT_BUILD",
            "url": "https://github.com/astral-sh/python-build-standalone/releases/download/TODO_RESOLVE_AT_BUILD/cpython-3.12.x+TODO_RESOLVE_AT_BUILD-x86_64-pc-windows-msvc-shared-install_only.tar.zst",
            "sha256": "TODO_RESOLVE_AT_BUILD",
            "dest": "Binaries/Win64/NyraHost/cpython/"
        },
        "llama_server_cuda": {
            "tag": "TODO_RESOLVE_AT_BUILD",
            "url": "TODO_RESOLVE_AT_BUILD",
            "sha256": "TODO_RESOLVE_AT_BUILD",
            "dest": "Binaries/Win64/NyraInfer/cuda/",
            "extract": "llama-server.exe"
        },
        "llama_server_vulkan": {
            "tag": "TODO_RESOLVE_AT_BUILD",
            "url": "TODO_RESOLVE_AT_BUILD",
            "sha256": "TODO_RESOLVE_AT_BUILD",
            "dest": "Binaries/Win64/NyraInfer/vulkan/",
            "extract": "llama-server.exe"
        },
        "llama_server_cpu": {
            "tag": "TODO_RESOLVE_AT_BUILD",
            "url": "TODO_RESOLVE_AT_BUILD",
            "sha256": "TODO_RESOLVE_AT_BUILD",
            "dest": "Binaries/Win64/NyraInfer/cpu/",
            "extract": "llama-server.exe"
        },
        "gemma_model_note": "Gemma GGUF is NOT a prebuild artefact — downloaded at runtime to <ProjectDir>/Saved/NYRA/models/ per D-17. See ModelPins::GemmaGgufUrl."
    }
    ```

    After writing the template, attempt resolution via curl commands above and
    REPLACE `TODO_RESOLVE_AT_BUILD` placeholders with actual values in BOTH
    files. If network unavailable, leave placeholders + document blocker in
    SUMMARY.md.
  </action>
  <verify>
    <automated>
      - `grep -c "PythonBuildStandaloneTag" TestProject/Plugins/NYRA/Source/NyraEditor/Public/ModelPins.h` equals 1
      - `grep -c "GemmaGgufUrl" TestProject/Plugins/NYRA/Source/NyraEditor/Public/ModelPins.h` equals 1
      - `grep -c "GemmaGgufSha256" TestProject/Plugins/NYRA/Source/NyraEditor/Public/ModelPins.h` equals 1
      - `grep -c "LlamaServerCudaZipUrl" TestProject/Plugins/NYRA/Source/NyraEditor/Public/ModelPins.h` equals 1
      - `grep -c "LlamaServerVulkanZipUrl" TestProject/Plugins/NYRA/Source/NyraEditor/Public/ModelPins.h` equals 1
      - `grep -c "LlamaServerCpuZipUrl" TestProject/Plugins/NYRA/Source/NyraEditor/Public/ModelPins.h` equals 1
      - `python -c "import json; json.load(open('TestProject/Plugins/NYRA/Source/NyraHost/assets-manifest.json'))"` returns no exception
      - `grep -c "gemma-3-4b-it-qat-q4_0" TestProject/Plugins/NYRA/Source/NyraHost/assets-manifest.json` >= 1
    </automated>
  </verify>
  <acceptance_criteria>
    - File ModelPins.h contains literal text `namespace Nyra::ModelPins`
    - File ModelPins.h contains literal text `PythonBuildStandaloneTag`, `PythonBuildStandaloneUrl`, `PythonBuildStandaloneSha256`
    - File ModelPins.h contains literal text `GemmaHfRepo = TEXT("google/gemma-3-4b-it-qat-q4_0-gguf")`
    - File ModelPins.h contains literal text `GemmaHfRevisionSha`, `GemmaGgufFilename`, `GemmaGgufUrl`, `GemmaGgufSha256`, `GemmaGgufMirrorUrl`
    - File ModelPins.h contains literal text `LlamaCppReleaseTag`, `LlamaServerCudaZipUrl`, `LlamaServerVulkanZipUrl`, `LlamaServerCpuZipUrl`, `LlamaServerCudaSha256`, `LlamaServerVulkanSha256`, `LlamaServerCpuSha256`
    - File ModelPins.cpp exists and `#include "ModelPins.h"`
    - File assets-manifest.json is valid JSON (parses with python json.load)
    - File assets-manifest.json contains top-level keys `python_build_standalone`, `llama_server_cuda`, `llama_server_vulkan`, `llama_server_cpu`
    - File assets-manifest.json entry `python_build_standalone.dest` equals the literal string `Binaries/Win64/NyraHost/cpython/` (trailing slash included)
    - File assets-manifest.json entry `llama_server_cuda.dest` equals the literal string `Binaries/Win64/NyraInfer/cuda/` (trailing slash included)
    - File assets-manifest.json entry `llama_server_vulkan.dest` equals the literal string `Binaries/Win64/NyraInfer/vulkan/` (trailing slash included)
    - File assets-manifest.json entry `llama_server_cpu.dest` equals the literal string `Binaries/Win64/NyraInfer/cpu/` (trailing slash included)
    - File assets-manifest.json contains the literal text `gemma-3-4b-it-qat-q4_0.gguf`
    - Either: (a) all `TODO_RESOLVE_AT_BUILD` replaced with real values in both files, OR (b) SUMMARY.md documents network-offline blocker and lists the curl commands needed to resolve
  </acceptance_criteria>
  <done>Shared pins in C++ + JSON; Plans 06/08/09 import from one authoritative source.</done>
</task>

</tasks>

<verification>
- All docs/*.md grep checks pass
- ModelPins.h compiles with UE 5.6 UBT (is a header-only namespace of `const TCHAR*`, no module deps)
- assets-manifest.json parses cleanly
</verification>

<success_criteria>
- docs/HANDSHAKE.md, docs/JSONRPC.md, docs/ERROR_CODES.md committed
- ModelPins.h + .cpp + assets-manifest.json committed
- `grep -r "TODO_RESOLVE_AT_BUILD" TestProject/Plugins/NYRA/Source/NyraHost/assets-manifest.json` returns 0 matches IF network was available at execute time (otherwise blocker logged)
- Plan 05 SUMMARY lists resolved pin values
</success_criteria>

<output>
After completion, create `.planning/phases/01-plugin-shell-three-process-ipc/01-05-SUMMARY.md`
with the resolved pin values (or the network-unavailable blocker), the full
list of 6 methods documented, and a link to each spec file.
</output>
