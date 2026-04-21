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
