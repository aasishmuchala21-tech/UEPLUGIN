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

## Phase 9 — Aura-killer codes

| Code | Message | Module |
|---|---|---|
| -32034 | comfyui_run_failed / inpaint_failed | nyrahost.tools.inpaint_tools |
| -32035 | input_must_be_url | nyrahost.tools.rigging_tools |
| -32036 | blockout_empty | nyrahost.tools.level_design_tools |
| -32037 | blockout_too_large | nyrahost.tools.level_design_tools |
| -32038 | meshy_rig_failed | nyrahost.tools.rigging_tools |
| -32039 | retarget_render_failed | nyrahost.tools.retarget_tools |
| -32040 | blockout_render_failed | nyrahost.tools.level_design_tools |

## Phase 10–19 additions (R6.C2 backfill from the full-codebase review)

The codes below were emitted by handlers shipped in Phases 10 through 19 but
not documented here. The C++ panel's error-bubble button mapping and any
downstream MCP-host integrators rely on this table being complete.

| Code | Message | Module / Phase |
|---|---|---|
| -32041 | instructions_too_large | nyrahost.handlers.instructions (Phase 10-1) |
| -32042 | instructions_write_failed | nyrahost.handlers.instructions (Phase 10-1) |
| -32043 | unknown_model | nyrahost.handlers.model_settings (Phase 10-3) |
| -32044 | composer_search_failed | nyrahost.handlers.composer (Phase 11-C) |
| -32045 | unknown_target | nyrahost.handlers.mcp_install (Phase 12-A) |
| -32046 | install_failed | nyrahost.handlers.mcp_install (Phase 12-A) |
| -32047 | project_not_found | nyrahost.tools.headless_ue (Phase 12-B) |
| -32048 | editor_not_found | nyrahost.tools.headless_ue (Phase 12-B) |
| -32049 | launch_failed | nyrahost.tools.headless_ue (Phase 12-B) |
| -32050 | no_session | nyrahost.tools.headless_ue (Phase 12-B) |
| -32051 | thread_limit_reached | nyrahost.handlers.threads (Phase 13-A) |
| -32052 | unknown_thread | nyrahost.handlers.threads (Phase 13-A) |
| -32053 | timeline_render_failed | nyrahost.tools.timeline_tools (Phase 13-B / 19-G) |
| -32054 | hygiene_render_failed | nyrahost.tools.asset_hygiene (Phase 13-C) |
| -32055 | perf_budget_failed | nyrahost.tools.perf_budget (Phase 13-E) |
| -32056 | reproducibility_out_of_range | nyrahost.handlers.reproducibility (Phase 14-A) |
| -32057 | user_tool_not_found | nyrahost.handlers.user_tools (Phase 14-D) |
| -32058 | user_tool_failed | nyrahost.handlers.user_tools (Phase 14-D) |
| -32059 | crash_rca_failed | nyrahost.tools.crash_rca (Phase 14-E) |
| -32060 | test_gen_failed | nyrahost.tools.test_gen (Phase 14-F) |
| -32061 | doc_from_code_failed | nyrahost.tools.doc_from_code (Phase 14-G) |
| -32062 | replication_scaffold_failed | nyrahost.tools.replication_scaffolder (Phase 14-H) |
| -32063 | encrypted_memory_too_large | nyrahost.handlers.encrypted_memory (Phase 15-A) |
| -32064 | encrypted_memory_failed | nyrahost.handlers.encrypted_memory (Phase 15-A) |
| -32065 | localization_failed | nyrahost.tools.localization (Phase 15-B) |
| -32066 | cinematic_failed | nyrahost.tools.cinematic (Phase 15-C) |
| -32067 | blueprint_review_failed | nyrahost.tools.blueprint_review (Phase 15-F) |
| -32068 | pcg_scatter_failed | nyrahost.tools.pcg_scatter (Phase 16-A) |
| -32069 | blueprint_review_llm_failed | nyrahost.tools.blueprint_review_llm (Phase 16-D) |
| -32070 | local_sd_not_installed | nyrahost.external.local_sd (Phase 17-A) |
| -32071 | local_sd_infer_failed | nyrahost.external.local_sd (Phase 17-A) |
| -32072 | privacy_mode_active | shared (audio_gen, fab_search, marketplace, multiplayer, computer_use, meshy) |
| -32073 | marketplace_signature_invalid / marketplace_not_configured | nyrahost.marketplace (Phase 17-B; PR-#4 R1.I4 adds the not-configured variant) |
| -32074 | marketplace_network_failed | nyrahost.marketplace (Phase 17-B) |
| -32075 | marketplace_blob_too_large | nyrahost.marketplace (Phase 17-B) |
| -32076 | multiplayer_no_room | nyrahost.multiplayer (Phase 17-C) |
| -32077 | multiplayer_backend_failed | nyrahost.multiplayer (Phase 17-C) |
| -32078 | snapshot_failed | nyrahost.snapshot (Phase 18-B) |
| -32079 | recovery_no_resume | nyrahost.recovery (Phase 18-C) |
| -32080 | recovery_failed | nyrahost.recovery (Phase 18-C) |
| -32081 | audio_gen_auth_failed | nyrahost.tools.audio_gen (Phase 19-A) |
| -32082 | audio_gen_failed | nyrahost.tools.audio_gen (Phase 19-A) |
| -32083 | fab_search_failed | nyrahost.tools.fab_search (Phase 19-B) |
| -32084 | character_replace_failed | nyrahost.tools.character_replace (Phase 19-E) |
| -32085 | todo_list_unknown | nyrahost.handlers.todos (Phase 19-I) |

### Suggested panel-button mappings (Slate)

| Code | Button | Action |
|---|---|---|
| -32041, -32063, -32075 | `[Trim]` | Open the relevant blob (instructions / memory / marketplace listing) for trimming |
| -32045 | `[Pick another IDE]` | Re-open the IDE-target dropdown |
| -32047, -32048 | `[Set UE path]` | Open Settings → UE Engine Path |
| -32070 | `[Install local SD]` | Open the `pip install` runbook |
| -32072 | `[Disable Privacy Mode]` | Toggle Settings → Privacy Mode off (user-acknowledged) |
| -32073 | `[Open marketplace settings]` | If `marketplace_not_configured`, open the trust-root config |
| -32085 | `[Open todos]` | Open the per-project todos panel |
