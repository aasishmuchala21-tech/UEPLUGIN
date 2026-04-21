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

## 4. Reserved (not in Phase 1)

- `diagnostics/tail` — log tailing. **Phase 2 addition.** Phase 1 panel
  reads `Saved/NYRA/logs/nyrahost-YYYY-MM-DD.log` directly via
  `FFileHelper::LoadFileToStringArray`.

## 5. Error codes

See `docs/ERROR_CODES.md` for the canonical table.
