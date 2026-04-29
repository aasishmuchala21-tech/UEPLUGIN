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

The first frame UE sends after the WS upgrade MUST be `session/authenticate`
(see §3.1). Any other first method triggers a WS close code 4401 with
reason `"unauthenticated"` — never an error-response envelope.

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

Emitted once per model chunk (NOT per byte — D-10; **one frame per model chunk**). Panel coalesces before
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

## 4. Phase 2 Additions

**D-23 / D-24 (module-superset discipline):** §1–§3 Phase 1 content is
preserved verbatim. Additions only. No deletions, no renumbering.

### 4.1 `chat/send` — backend parameter extension

The `params.backend` field now accepts `"claude"` in addition to
`"gemma-local"` (Phase 1). Backwards-compatible: all Phase 1
`"gemma-local"` examples remain valid.

| Value        | Engine        | Reference          |
|--------------|---------------|--------------------|
| `"gemma-local"` | llama.cpp / Ollama (Phase 1, D-10) | §3.3 |
| `"claude"`      | Claude Code CLI subprocess (Plan 02-04) | D-01 |

**New valid request:**

```json
{"jsonrpc":"2.0","id":3,"method":"chat/send","params":{
  "conversation_id":"<uuid>",
  "req_id":"<uuid>",
  "content":"List all actors in the current level",
  "backend":"claude"
}}
```

### 4.2 `session/set-mode` — Request (UE → NyraHost)

Switches NyraHost between Normal and Privacy modes (D-05). Privacy
Mode blocks all network egress; Gemma-only is the only available
backend while active.

**Request:**

```json
{"jsonrpc":"2.0","id":6,"method":"session/set-mode","params":{"mode":"privacy"}}
```

`mode` ∈ `{"normal", "privacy"}`

**Success response:**

```json
{"jsonrpc":"2.0","id":6,"result":{"mode_applied":"privacy","backends_available":["gemma-local"]}}
```

**Error if backend unavailable in Privacy Mode:**

```json
{"jsonrpc":"2.0","id":6,"error":{"code":-32010,"message":"privacy_mode_blocked","data":{"remediation":"This action requires internet access. Exit Privacy Mode to continue."}}}
```

Cross-reference: CONTEXT.md D-05, RESEARCH §4.3.

---

### 4.3 `plan/preview` — Notification (NyraHost → UE)

Structured plan summary emitted by the router (Plan 02-05) before the
Claude agent executes a high-risk sequence. Provides the user a chance
to preview, approve, reject, or edit.

**Notification frame (no response expected):**

```json
{"jsonrpc":"2.0","method":"plan/preview","params":{
  "conversation_id":"<uuid>",
  "req_id":"<uuid>",
  "preview_id":"prev-abc123",
  "summary":"Create 12 Material instances and assign to 47 StaticMesh actors",
  "steps":[
    {"tool":"create_materials","args":{"count":12},"rationale":"Blueprinted wall surfaces","risk":"low"},
    {"tool":"assign_materials","args":{"actors":["Sphere_001","Sphere_002"]},"rationale":"Apply to level geometry","risk":"medium"}
  ],
  "estimated_duration_seconds":45,
  "affects_files":["Content/Materials/Wall_Mat.uasset","Content/Props/Sphere.uasset"]
}}
```

Fields:

| Field | Type | Description |
|-------|------|-------------|
| `conversation_id` | string | Active conversation UUID |
| `req_id` | string | Request correlation ID |
| `preview_id` | string | Stable opaque ID for the `plan/decision` response |
| `summary` | string | Human-readable one-liner |
| `steps` | array | Sequence of planned tool invocations |
| `steps[].tool` | string | Tool / function name |
| `steps[].args` | object | Tool arguments (may contain file paths, PII) |
| `steps[].rationale` | string | Why this step is needed |
| `steps[].risk` | string | `"low"` / `"medium"` / `"high"` |
| `estimated_duration_seconds` | integer | Rough wall-clock estimate |
| `affects_files` | array[string] | Asset paths this plan will modify |

Cross-reference: CONTEXT.md D-06 (path B: `--permission-prompt-tool nyra_permission_gate`).

**Note:** In Privacy Mode, `plan/preview` is emitted only for Gemma-local
operations; Claude operations are blocked (→ -32010 privacy_mode_blocked).

---

### 4.4 `plan/decision` — Request (UE → NyraHost)

User verdict on a `plan/preview`. Must reference the `preview_id`.
`reject` causes NyraHost to surface `-32011 plan_rejected` back to
Claude as the tool result.

**Request:**

```json
{"jsonrpc":"2.0","id":7,"method":"plan/decision","params":{
  "preview_id":"prev-abc123",
  "decision":"approve"
}}
```

`decision` ∈ `{"approve", "reject", "edit"}`

- `approve` — NyraHost resumes the plan. Router emits a `plan/decision`
  result and forwards to the agent.
- `reject` — NyraHost cancels the plan and emits `-32011 plan_rejected`
  as the tool result back to Claude.
- `edit` — client sends back a modified plan payload (future extension;
  v1 treats `edit` as `reject` with a note).

**Response (acknowledge, execution continues asynchronously):**

```json
{"jsonrpc":"2.0","id":7,"result":{"acknowledged":true}}
```

**On `decision: reject` (NyraHost → UE notification back to Claude):**

```json
{"jsonrpc":"2.0","method":"chat/stream","params":{
  "conversation_id":"<uuid>",
  "req_id":"<uuid>",
  "delta":"",
  "done":true,
  "error":{"code":-32011,"message":"plan_rejected","data":{"remediation":"Plan rejected by user."}}
}}
```

Cross-reference: CONTEXT.md D-09 (verdict carries approve/reject/edit).

---

### 4.5 `console/exec` — Request (NyraHost → UE)

Router (Plan 02-05) sends this to UE after classifying an agent's
`nyra_console_exec` MCP call as Tier A or Tier B-approved. Captures
console output + tier classification.

**Request:**

```json
{"jsonrpc":"2.0","id":8,"method":"console/exec","params":{
  "command":"GetAll /Script/Engine.StaticMeshActor -Property bHidden",
  "rationale":"Inventory check before bulk-hide operation"
}}
```

**Success response:**

```json
{"jsonrpc":"2.0","id":8,"result":{
  "stdout":"Actor.Label\tHidden\nCubeActor_0\tFalse\nSphereActor_1\tTrue",
  "tier":"A",
  "exit_status":"ok"
}}
```

**Blocked Tier C / unknown command:**

```json
{"jsonrpc":"2.0","id":8,"error":{"code":-32012,"message":"console_command_blocked","data":{"remediation":"Console command 'BadCommand' is not in the safe-mode whitelist."}}}
```

`tier` ∈ `{"A", "B"}` — Tier C commands are rejected without this wire
call; NyraHost returns -32012 directly in the MCP tool result.

Cross-reference: RESEARCH §8.5, Plan 02-09.

---

### 4.6 `log/tail` — Request (NyraHost → UE)

Reads the last N entries from the NYRA log file. Useful for the
diagnostics drawer when UE-side log reading is not available.

**Request:**

```json
{"jsonrpc":"2.0","id":9,"method":"log/tail","params":{
  "max_entries":50,
  "regex":"error|warning",
  "min_verbosity":"warning"
}}
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `max_entries` | integer | No | 100 | Cap 1–200 |
| `regex` | string | No | null | Filter on message text |
| `min_verbosity` | string | No | `"info"` | `"debug"` / `"info"` / `"warning"` / `"error"` |
| `since_ts` | integer | No | null | Unix ms timestamp floor |

**Response:**

```json
{"jsonrpc":"2.0","id":9,"result":{
  "entries":[
    {"ts":1713690015000,"category":"nyrahost.router","verbosity":"warning","message":"llama_server_spawn_failed backend=cuda"},
    {"ts":1713690016000,"category":"nyrahost.router","verbosity":"info","message":"backend_chosen choice=bundled port=54321"}
  ],
  "truncated":false,
  "last_ts":1713690016000
}}
```

`truncated: true` if more than `max_entries` entries matched.

Cross-reference: RESEARCH §8.5, Plan 02-10.

---

### 4.7 `log/message-log-list` — Request (NyraHost → UE)

Lists entries from the structured Message Log for the UE panel's log
viewer.

**Request:**

```json
{"jsonrpc":"2.0","id":10,"method":"log/message-log-list","params":{
  "listing_name":"default",
  "max_entries":100,
  "since_index":0
}}
```

**Response:**

```json
{"jsonrpc":"2.0","id":10,"result":{
  "entries":[
    {"index":42,"severity":"info","message":"Chat send initiated","token_refs":["req-abc"]},
    {"index":43,"severity":"warning","message":"Ollama not detected; falling back to bundled","token_refs":[]}
  ],
  "total":87
}}
```

`token_refs` are opaque string IDs UE resolves into navigation actions
in a future Phase 4 plan.

Cross-reference: RESEARCH §8.5.

---

### 4.8 `diagnostics/backend-state` — Notification (NyraHost → UE)

Emitted on every router state transition (Plan 02-05). Allows the UE
panel to display a live backend status indicator.

**Notification frame:**

```json
{"jsonrpc":"2.0","method":"diagnostics/backend-state","params":{
  "claude":{"installed":true,"version":"2.1.111","auth":"valid","state":"ready","rate_limit_resets_at":null},
  "gemma":{"model_present":true,"runtime":"ollama","state":"ready"},
  "computer_use":{"state":"available"},
  "mode":"normal",
  "updated_at":1713690017000
}}
```

`claude.state` ∈ `{"ready", "rate-limited", "auth-drift", "offline"}`
`gemma.state` ∈ `{"ready", "downloading", "loading", "not-installed"}`
`mode` ∈ `{"normal", "privacy-mode"}`
`computer_use.state` ∈ `{"available", "unavailable", "active"}`

Cross-reference: CONTEXT.md D-03 (router states ↔ `claude.state` enum),
RESEARCH §9.2.

---

### 4.9 `diagnostics/pie-state` — Notification (UE → NyraHost)

Fired by UE when PIE (Play-In-Editor) starts or stops. Allows NyraHost
router to refuse `chat/send` while PIE is active.

**When PIE starts:**

```json
{"jsonrpc":"2.0","method":"diagnostics/pie-state","params":{"active":true}}
```

**When PIE stops:**

```json
{"jsonrpc":"2.0","method":"diagnostics/pie-state","params":{"active":false}}
```

Router behaviour: while `active == true`, any `chat/send` returns:

```json
{"jsonrpc":"2.0","id":3,"error":{"code":-32014,"message":"pie_active","data":{"remediation":"NYRA cannot mutate while Play-In-Editor is running. Stop PIE and retry."}}}
```

Cross-reference: RESEARCH Open Q #5 resolved by Plan 02-05 router.

---

### 4.10 `claude/auth-status` — Notification (NyraHost → UE)

Emitted on NyraHost startup, on every 5-minute TTL refresh, and on
router transitions into or out of `auth-drift`. Fine-grained to drive the
first-run auth wizard.

**Notification frame:**

```json
{"jsonrpc":"2.0","method":"claude/auth-status","params":{
  "installed":true,
  "auth":"valid",
  "tier":"pro",
  "remediation_hint":null
}}
```

`auth` ∈ `{"valid", "expired", "missing"}`

When `auth != "valid"`:
```json
{"jsonrpc":"2.0","method":"claude/auth-status","params":{
  "installed":true,
  "auth":"expired",
  "remediation_hint":"Run `claude auth login` in a terminal."
}}
```

Cross-reference: RESEARCH §3.9.

---

### Change Log

- **Phase 2 (D-23):** §4 additions only. Phase 1 §1–§3 preserved verbatim.

## 5. Error codes

See `docs/ERROR_CODES.md` for the canonical table.
