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

## Phase 2 Additions (D-23)

> **-32003 / -32009 relationship:** Phase 1 `-32003 rate_limit` remains a
> generic rate-limit code (Gemma / Ollama backend can still emit it).
> Phase 2 `-32009 claude_rate_limited` is Claude-specific and carries
> `rate_limit_resets_at` in `error.data`. Both populate
> `error.data.remediation`.

| Code    | Name                       | When emitted                                                                   | Remediation template                                                                                   |
|---------|----------------------------|--------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| -32007  | claude_not_installed       | `which claude` / `where claude` fails on NyraHost boot                          | "Claude Code CLI not found. Install from code.claude.com."                                              |
| -32008  | claude_auth_drift          | `claude auth status` exits 1 mid-session OR `api_retry error=authentication_failed` | "Claude session expired. Run `claude auth login` in a terminal."                                      |
| -32009  | claude_rate_limited        | `system/api_retry error=rate_limit` exhausted attempts                         | "Claude rate-limited. Resume at {time}, or switch to local Gemma ([Switch])."                          |
| -32010  | privacy_mode_blocked       | Router in Privacy Mode; agent/user attempts action requiring network egress     | "This action requires internet access. Exit Privacy Mode to continue."                                 |
| -32011  | plan_rejected              | User clicked Reject on a `plan/preview` card                                    | "Plan rejected by user."                                                                              |
| -32012  | console_command_blocked    | Tier C console command OR unmapped command via `nyra_console_exec`               | "Console command '{cmd}' is not in the safe-mode whitelist."                                           |
| -32013  | transaction_already_active | Another NYRA session active (plugin hot-reload corner case)                     | "Another NYRA session is already running. End it before starting a new one."                           |
| -32014  | pie_active                 | chat/send received while PIE is running                                         | "NYRA cannot mutate while Play-In-Editor is running. Stop PIE and retry."                               |

### Usage by Phase 2 plan

| Plan | Owns error codes |
|------|-----------------|
| 02-04 (Claude driver) | -32007, -32008, -32009 |
| 02-05 (Router)        | -32010, -32014 |
| 02-08 (Permission gate) | -32011 |
| 02-09 (Console exec)  | -32012 |
| 02-07 (Super-transaction) | -32013 |

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
