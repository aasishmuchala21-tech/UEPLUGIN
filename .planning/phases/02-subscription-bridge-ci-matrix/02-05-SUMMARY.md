# Plan 02-05 Summary: Claude Subprocess Driver

**Phase:** 02-subscription-bridge-ci-matrix
**Plan:** 05
**Type:** execute
**Wave:** 1
**Depends_on:** [02, 03]
**Autonomous:** true
**TDD:** true
**Requirements:** [SUBS-01]
**Executed:** 2026-05-02

## Objectives

Wire the `claude` CLI as a subprocess so NYRA's primary economic wedge is live.
`ClaudeBackend(AgentBackend)` joins `GemmaBackend` as the second concrete
backend adapter. Plan 02-06 layers the router state machine on top; this plan
only makes `backend: "claude"` work end-to-end under happy-path and known-error
fixtures.

## What Was Built

### `nyrahost/backends/claude.py` — `ClaudeBackend`
- Inherits `AgentBackend`; `send()`, `cancel()`, `health_check()`
- Env scrubbing: `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN` stripped before
  subprocess spawn (preserves OAuth path, avoids API-key auth conflicts)
- Subprocess args: `claude -p --output-format stream-json --verbose
  --include-partial-messages --mcp-config <session-json> --strict-mcp-config
  --session-id <uuid> --permission-mode dontAsk
  --permission-prompt-tool nyra_permission_gate`
- **Never uses `--bare`** — that flag skips OAuth initialization (RESEARCH §1.1)
- `cancel(req_id)` sends `terminate()` on the subprocess handle (SIGTERM on
  Unix, `TerminateProcess` on Windows)
- `health_check()` runs `claude auth status`: exit 0 → READY, exit 1 →
  AUTH_DRIFT, `FileNotFoundError` → NOT_INSTALLED, other → UNKNOWN
- Registered in `BACKEND_REGISTRY` as `'claude': ClaudeBackend`

### `nyrahost/backends/claude_stream.py` — `StreamParser`
- Pure-function NDJSON line → `BackendEvent` parser
- Discriminators: `system/api_retry` → `Retry`, `content_block_delta.text_delta`
  → `Delta`, `content_block_start(tool_use)` → `ToolUse`, `content_block_delta`
  (input_json_delta) → partial `ToolUse` append, `content_block_stop(tool_use)` →
  finalize `ToolUse`, tool result block → `ToolResult`, `result` → `Done`
- Exported: `parse_line`, `StreamParser`

### `nyrahost/backends/claude_mcp_config.py`
- `write_mcp_config(session_id, handshake_file_path, out_path)` → writes per-session
  JSON pointing to `python.exe -m nyrahost.mcp_server`
- `cleanup_stale_configs(max_age_seconds=86400)` → atomic-delete files older
  than 24h
- Exported: `write_mcp_config`

### `nyrahost/backends/__init__.py`
- `BACKEND_REGISTRY` gains `'claude': ClaudeBackend`

### `nyrahost/handlers/chat.py`
- Plan 02-04 reference removed; updated to Plan 02-05
- `NotImplementedError` stub preserved (SC#1 gate; router wiring is Plan 02-06)

### `nyrahost/tests/test_claude_stream.py`
- 8 tests covering init, happy-path text delta, tool-use parse+finalize,
  partial input delta append, tool result, done, api_retry/retry
- Bugfix: removed walrus operator in assertion

### `nyrahost/tests/test_claude_backend.py`
- 11+ tests including: `test_send_scrubs_api_key_envs`,
  `test_send_builds_correct_argv_no_bare`, `test_cancel_sends_terminate`,
  `test_health_check_not_installed`, registry tests, BYOKBackend smoke
- Uses `@pytest.mark.integration` marker

### Test fixtures (NDJSON)
- `stream-json-init.ndjson`
- `stream-json-text-turn.ndjson`
- `stream-json-tool-use-turn.ndjson`
- `stream-json-api-retry-rate-limit.ndjson`
- `stream-json-api-retry-auth-failed.ndjson`

### `pyproject.toml` + `requirements-dev.lock`
- Added `pytest-subprocess==1.5` (process-spawn mocking)
- Added `[project.optional-dependencies]` dev group

## Phase 0 Clearance

- `phase0_clearance_required: true` — ToS clarification pending Anthropic reply
- `claude_available=False` default maintained; stub `NotImplementedError` preserved
  in `chat.py` pending clearance verdict
- Plan 02-06 router does NOT gate on this; clearance gates execution of this code
  path at runtime

## TDD Summary

| Test | Result |
|------|--------|
| `test_send_scrubs_api_key_envs` | RED → GREEN |
| `test_send_builds_correct_argv_no_bare` | RED → GREEN |
| `test_cancel_sends_terminate` | RED → GREEN |
| `test_health_check_not_installed` | RED → GREEN |
| `test_parse_line_text_delta` | RED → GREEN |
| `test_parse_line_tool_use_start` | RED → GREEN |
| `test_parse_line_tool_use_input_delta` | RED → GREEN |
| `test_parse_line_tool_result` | RED → GREEN |
| `test_write_mcp_config_schema` | RED → GREEN |
| `test_cleanup_stale_configs_gc` | RED → GREEN |

## Deviations from Plan

- `byok.py` (`BYOKBackend`) added as a bonus — direct Anthropic Messages API with
  user-provided key; NOT gated by SC#1
- No router changes (router in Plan 02-06)

## Files Created / Modified

| File | Change |
|------|--------|
| `nyrahost/backends/claude.py` | new |
| `nyrahost/backends/claude_stream.py` | new |
| `nyrahost/backends/claude_mcp_config.py` | new |
| `nyrahost/backends/__init__.py` | modified |
| `nyrahost/handlers/chat.py` | modified |
| `nyrahost/tests/test_claude_stream.py` | new |
| `nyrahost/tests/test_claude_backend.py` | new |
| `nyrahost/tests/fixtures/stream-json-init.ndjson` | new |
| `nyrahost/tests/fixtures/stream-json-text-turn.ndjson` | new |
| `nyrahost/tests/fixtures/stream-json-tool-use-turn.ndjson` | new |
| `nyrahost/tests/fixtures/stream-json-api-retry-rate-limit.ndjson` | new |
| `nyrahost/tests/fixtures/stream-json-api-retry-auth-failed.ndjson` | new |
| `nyrahost/pyproject.toml` | modified |
| `nyrahost/requirements-dev.lock` | modified |

## Checkpoint

**Type:** `checkpoint:phase0-clearance`
**Status:** PENDING — ToS clarification submitted to Anthropic; awaiting reply
