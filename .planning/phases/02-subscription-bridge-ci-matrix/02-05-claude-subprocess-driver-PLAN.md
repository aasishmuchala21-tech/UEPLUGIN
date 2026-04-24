---
phase: 02-subscription-bridge-ci-matrix
plan: 05
slug: claude-subprocess-driver
type: execute
wave: 1
depends_on: [02, 03]
autonomous: true
tdd: true
requirements: [SUBS-01]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/claude.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/claude_stream.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/claude_mcp_config.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/__init__.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/chat.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_claude_stream.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_claude_mcp_config.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_claude_backend.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/fixtures/stream-json-init.ndjson
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/fixtures/stream-json-text-turn.ndjson
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/fixtures/stream-json-tool-use-turn.ndjson
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/fixtures/stream-json-api-retry-rate-limit.ndjson
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/fixtures/stream-json-api-retry-auth-failed.ndjson
  - TestProject/Plugins/NYRA/Source/NyraHost/pyproject.toml
  - TestProject/Plugins/NYRA/Source/NyraHost/requirements-dev.lock
research_refs: [§1.1, §1.2, §1.3, §1.4, §1.6, §10.1, §10.9]
context_refs: [D-01, D-02, D-26]
phase0_clearance_required: true
must_haves:
  truths:
    - "nyrahost.backends.claude.ClaudeBackend(AgentBackend) spawns `claude -p --output-format stream-json --verbose --include-partial-messages --mcp-config <file> --strict-mcp-config --session-id <uuid> --permission-mode dontAsk --permission-prompt-tool nyra_permission_gate [--resume <id>] [--model opus]`"
    - "Child env scrubs ANTHROPIC_API_KEY and ANTHROPIC_AUTH_TOKEN before spawn (RESEARCH §1.2 trap; preserves subscription-mode OAuth path)"
    - "--bare is NOT used — subscription mode requires OAuth which --bare skips (RESEARCH §1.1 critical caveat)"
    - "claude_stream.StreamParser parses NDJSON lines into BackendEvent stream per RESEARCH §1.3: system/init → ignored (metadata cached), stream_event.event.content_block_delta.text_delta → Delta, stream_event.event.content_block_start(tool_use) → ToolUse(id,name,input=''), stream_event.event.content_block_delta.input_json_delta → ToolUse(id,name,partial_json), stream_event.event.content_block_stop(tool_use) → ToolUse(id,name,final_json), user message with tool_result block → ToolResult, system/api_retry → Retry(attempt, delay_ms, error_category), result → Done(usage, stop_reason)"
    - "claude_mcp_config.write_mcp_config(session_id, handshake_file_path, out_path) writes a per-session JSON per RESEARCH §1.6 shape pointing to NyraHost's stdio MCP server module entry-point"
    - "ClaudeBackend.health_check() invokes `claude auth status` subprocess: exit 0 → READY, exit 1 → AUTH_DRIFT, FileNotFoundError → NOT_INSTALLED, other exceptions → UNKNOWN"
    - "ClaudeBackend.cancel(req_id) sends SIGTERM to the in-flight subprocess (Windows: signal.CTRL_C_EVENT or TerminateProcess equivalent)"
    - "Test fixtures captured from RESEARCH §1.3 worked examples; every StreamParser test uses a fixture file (no inline NDJSON strings > 3 lines)"
    - "BACKEND_REGISTRY gains 'claude': ClaudeBackend; handlers/chat.py NotImplementedError stub removed"
    - "pytest-subprocess added to requirements-dev.lock for process-spawn mocking"
  artifacts:
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/claude.py
      provides: "ClaudeBackend(AgentBackend) with subprocess lifecycle + env scrubbing"
      exports: ["ClaudeBackend"]
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/claude_stream.py
      provides: "Pure-function NDJSON line → BackendEvent parser"
      exports: ["parse_line", "StreamParser"]
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/claude_mcp_config.py
      provides: "Per-session MCP config file writer"
      exports: ["write_mcp_config"]
    - path: TestProject/Plugins/NYRA/Source/NyraHost/tests/fixtures/stream-json-*.ndjson
      provides: "Canonical NDJSON schema fixtures for regression testing across Claude CLI minor versions"
  key_links:
    - from: ClaudeBackend.send
      to: claude CLI subprocess
      via: "asyncio.create_subprocess_exec with scrubbed env + per-session mcp-config file path"
      pattern: "claude.*-p.*--output-format stream-json.*--mcp-config"
    - from: claude_stream.parse_line
      to: BackendEvent tagged-union variants
      via: "JSON type/subtype discriminator switch"
      pattern: "system/api_retry|content_block_delta|result"
    - from: claude_mcp_config.write_mcp_config output
      to: NyraHost MCP server stdio module
      via: "JSON file references python.exe + -m nyrahost.mcp_server + handshake file path"
      pattern: "nyrahost\\.mcp_server"
---

<objective>
Phase 2's flagship plan: wire the `claude` CLI subprocess so NYRA's economic wedge is literally alive. `ClaudeBackend` joins `GemmaBackend` as the second concrete in Plan 02-03's registry. Plan 02-06 layers the router state machine ON TOP of this adapter (deciding *when* to use Claude vs fall back); this plan only makes `backend: "claude"` work end-to-end under happy-path + known-error fixtures.

Per CONTEXT.md:
- D-01: ClaudeBackend slots into `AgentBackend` ABC (no router changes)
- D-02: subprocess-drive CLI, never embed SDK; scrub API-key envs; never use `--bare` in subscription mode
- D-26: phase0_clearance_required — this plan EXECUTES only after written ToS clearance from Anthropic is on file. Planning proceeds now; execute-plan enforces the gate.

**TDD:** three RED/GREEN pairs — stream parser (pure function, highest-leverage), MCP config writer (pure function), ClaudeBackend adapter (integration with mocked subprocess via `pytest-subprocess`).

No router logic here. No rate-limit fallback decisions. Those land in Plan 02-06.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/02-subscription-bridge-ci-matrix/02-CONTEXT.md
@.planning/phases/02-subscription-bridge-ci-matrix/02-RESEARCH.md
@docs/JSONRPC.md
@docs/ERROR_CODES.md

<interfaces>
<!-- From Plan 02-03's AgentBackend (already landed in Wave 0): -->
<!--   AgentBackend.send(conversation_id, req_id, content, attachments, mcp_config_path, on_event) → None -->
<!--   AgentBackend.cancel(req_id) → None -->
<!--   AgentBackend.health_check() → HealthState -->
<!--   BackendEvent = Delta | ToolUse | ToolResult | Done | Error | Retry -->

<!-- ClaudeBackend spawns with argv (RESEARCH §1.1): -->
<!--   argv = [claude_path, '-p', '--output-format', 'stream-json', '--verbose', '--include-partial-messages', -->
<!--          '--mcp-config', <path>, '--strict-mcp-config', -->
<!--          '--session-id', <uuid>, '--permission-mode', 'dontAsk', -->
<!--          '--permission-prompt-tool', 'nyra_permission_gate'] -->
<!--   optional: '--resume', <prior-session-id>     for conversation continuity -->
<!--   optional: '--model', 'opus'                  for explicit Opus 4.7 (default when STACK pins) -->
<!--   optional: '--debug-file', <log-path>         for support triage (RESEARCH §1.1 table) -->
<!--   argv += [prompt_string]                      last positional -->

<!-- Env scrub (RESEARCH §1.2): -->
<!--   child_env = {k: v for k, v in os.environ.items() if k not in ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN')} -->
<!--   NyraHost NEVER reads CLAUDE_CODE_OAUTH_TOKEN — it's Claude-scoped (RESEARCH §10.9) -->

<!-- StreamParser event discriminators (RESEARCH §1.3): -->
<!--   type=system, subtype=init → swallow (cache model/session_id as metadata) -->
<!--   type=stream_event, event.type=content_block_delta, delta.type=text_delta → Delta(text=delta.text) -->
<!--   type=stream_event, event.type=content_block_start, content_block.type=tool_use → ToolUse(id, name, input_json='') -->
<!--   type=stream_event, event.type=content_block_delta, delta.type=input_json_delta → ToolUse(id, name, partial_json=delta.partial_json)  [same id carries] -->
<!--   type=stream_event, event.type=content_block_stop → nothing OR final ToolUse emission with assembled JSON -->
<!--   type=user (message with tool_result blocks) → ToolResult(id, output) -->
<!--   type=system, subtype=api_retry → Retry(attempt, delay_ms=retry_delay_ms, error_category=error) -->
<!--   type=result → Done(usage, stop_reason) -->
<!--   unknown type → log warning, continue -->

<!-- MCP config JSON (RESEARCH §1.6 literal): -->
<!--   { -->
<!--     "mcpServers": { -->
<!--       "nyra": { -->
<!--         "command": "<path to bundled python.exe>", -->
<!--         "args": ["-m", "nyrahost.mcp_server", "--handshake-file", "<nyrahost handshake path>"], -->
<!--         "env": {"NYRA_SESSION_ID": "<uuid>", "NYRA_CONVERSATION_ID": "<uuid>"} -->
<!--       } -->
<!--     } -->
<!--   } -->
<!-- File path: %LOCALAPPDATA%/NYRA/mcp-configs/<session-id>.json    cleanup older than 24h on startup (RESEARCH §10.7) -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1 (RED+GREEN): NDJSON stream parser with fixture-driven tests</name>
  <files>TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/claude_stream.py, TestProject/Plugins/NYRA/Source/NyraHost/tests/test_claude_stream.py, TestProject/Plugins/NYRA/Source/NyraHost/tests/fixtures/stream-json-init.ndjson, TestProject/Plugins/NYRA/Source/NyraHost/tests/fixtures/stream-json-text-turn.ndjson, TestProject/Plugins/NYRA/Source/NyraHost/tests/fixtures/stream-json-tool-use-turn.ndjson, TestProject/Plugins/NYRA/Source/NyraHost/tests/fixtures/stream-json-api-retry-rate-limit.ndjson, TestProject/Plugins/NYRA/Source/NyraHost/tests/fixtures/stream-json-api-retry-auth-failed.ndjson</files>
  <behavior>
    - test_parse_init_caches_metadata — system/init line yields nothing but parser.session_id / parser.model populated
    - test_parse_text_delta_emits_delta — text_delta line yields Delta(text=...)
    - test_parse_tool_use_start_emits_tool_use_with_empty_input — content_block_start tool_use line yields ToolUse(id, name, input_json='')
    - test_parse_input_json_delta_appends_partial — successive input_json_delta lines accumulate on the same id; emitted only on content_block_stop per D-08 partial-JSON buffering rule (EXCEPTION: router-layer buffering for permission_gate is Plan 02-08; parser-layer emits each partial as-is with `is_final=False` and the final complete JSON with `is_final=True`)
    - test_parse_api_retry_rate_limit_emits_retry — emits Retry(attempt=N, delay_ms=M, error_category='rate_limit')
    - test_parse_api_retry_auth_failed_emits_retry_auth — error_category='authentication_failed'
    - test_parse_result_emits_done — type=result emits Done(usage={...}, stop_reason='end_turn')
    - test_parse_unknown_type_logs_and_continues — unknown type does NOT raise; structlog warning recorded
    - test_parse_malformed_json_raises_or_emits_error — non-JSON line handled gracefully
  </behavior>
  <action>
    RED first: write the test file + capture fixture NDJSON files by hand from RESEARCH §1.3 worked examples. Each fixture file is ≤10 lines of NDJSON covering one scenario. Commit:
      test(02-05): add failing claude stream parser tests + canonical NDJSON fixtures

    GREEN: implement `nyrahost/backends/claude_stream.py` as a `StreamParser` class with `parse_line(line: str) -> list[BackendEvent]` (returns 0..n events per line because tool-use final emission needs paired start+stop). Pure — no I/O. Small state: `session_id`, `model`, current `tool_use_buffer: dict[id, dict]`. Internal logger is `structlog.get_logger(__name__)`. Follows Phase 1 Plan 08's SSE parser style (see `nyrahost/infer/sse.py`) as a model.

    Commit: feat(02-05): add Claude stream-json parser
  </action>
  <verify>
    <automated>cd TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest tests/test_claude_stream.py -v 2>&1 | tail -5 | grep -E "passed|failed"</automated>
  </verify>
  <done>
    - Five fixture files committed with RESEARCH-derived NDJSON
    - test_claude_stream.py has ≥ 8 tests covering all discriminators
    - StreamParser implementation passes all tests
    - RED/GREEN commit pair landed
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2 (RED+GREEN): MCP config writer</name>
  <files>TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/claude_mcp_config.py, TestProject/Plugins/NYRA/Source/NyraHost/tests/test_claude_mcp_config.py</files>
  <behavior>
    - test_writes_valid_json — output file is valid JSON + schema-conformant (mcpServers.nyra.command, args, env)
    - test_command_points_to_bundled_python — `command` is the bundled python.exe path from plugin_binaries_dir (DI parameter)
    - test_args_include_handshake_file_flag — args list contains `-m`, `nyrahost.mcp_server`, `--handshake-file`, `<path>`
    - test_env_includes_session_and_conversation_ids — NYRA_SESSION_ID and NYRA_CONVERSATION_ID populated
    - test_writes_to_localappdata_mcp_configs_dir — out_path under %LOCALAPPDATA%/NYRA/mcp-configs/<session-id>.json (abstracted via DI for testability)
    - test_cleanup_older_than_24h — helper cleanup_stale_configs(dir) removes configs whose mtime is > 24h ago; newer ones untouched
  </behavior>
  <action>
    RED: commit test(02-05): add failing mcp-config writer tests

    GREEN: implement `write_mcp_config(session_id, conversation_id, python_exe, handshake_file, out_path)` and `cleanup_stale_configs(mcp_configs_dir, max_age_seconds=86400)`. Uses `json.dumps(..., indent=2)` + atomic write (write to temp then rename) — same pattern as Phase 1 Plan 06's handshake.py.

    Commit: feat(02-05): add per-session MCP config writer with stale-file GC
  </action>
  <verify>
    <automated>cd TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest tests/test_claude_mcp_config.py -v 2>&1 | tail -5 | grep -E "passed|failed"</automated>
  </verify>
  <done>
    - MCP config writer with atomic-write + stale-file GC
    - All 6 tests pass
    - Output JSON shape matches RESEARCH §1.6 literal
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3 (RED+GREEN): ClaudeBackend adapter + registry wiring</name>
  <files>TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/claude.py, TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/__init__.py, TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/chat.py, TestProject/Plugins/NYRA/Source/NyraHost/tests/test_claude_backend.py, TestProject/Plugins/NYRA/Source/NyraHost/pyproject.toml, TestProject/Plugins/NYRA/Source/NyraHost/requirements-dev.lock</files>
  <behavior>
    - test_send_scrubs_api_key_envs — spawned subprocess env does NOT contain ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN even if parent has them set
    - test_send_builds_correct_argv — argv matches the RESEARCH §1.1 locked flag set (verified element-by-element); `--bare` is absent
    - test_send_emits_events_from_parser — given mock stdout yielding fixture NDJSON, on_event receives the expected sequence
    - test_send_handles_process_crash — subprocess exits with non-zero; emits Error event with code=-32001, retryable=False
    - test_cancel_sends_sigterm — cancel(req_id) terminates the subprocess (mock asserts TerminateProcess/signal call)
    - test_health_check_returns_ready_on_exit_0 — mock `claude auth status` exit 0 → READY
    - test_health_check_returns_auth_drift_on_exit_1 — exit 1 → AUTH_DRIFT
    - test_health_check_returns_not_installed_when_binary_missing — FileNotFoundError on spawn → NOT_INSTALLED
    - test_registry_has_claude — BACKEND_REGISTRY['claude'] is ClaudeBackend
    - test_chat_handlers_no_longer_raises_for_claude — invoking chat/send with backend='claude' does NOT raise NotImplementedError (Plan 02-03's placeholder removed)
  </behavior>
  <action>
    Add `pytest-subprocess>=1.5` to pyproject.toml [project.optional-dependencies].dev AND requirements-dev.lock (use the lockfile-additive pattern from Phase 1 D-14/D-15).

    RED: commit test(02-05): add failing ClaudeBackend integration tests with pytest-subprocess

    GREEN: implement `nyrahost/backends/claude.py`:
      class ClaudeBackend(AgentBackend):
        name = "claude"
        def __init__(self, claude_path: str = "claude", python_exe: Path = ..., handshake_file: Path = ..., plugin_binaries_dir: Path = ...):
            self._claude_path = claude_path
            self._python_exe = python_exe
            self._handshake_file = handshake_file
            self._inflight: dict[str, asyncio.subprocess.Process] = {}
            self._parser_factory = StreamParser
        async def send(...):
            # 1. write per-session MCP config via claude_mcp_config.write_mcp_config
            # 2. build argv (interfaces block)
            # 3. child_env = os.environ.copy(); for k in ('ANTHROPIC_API_KEY','ANTHROPIC_AUTH_TOKEN'): child_env.pop(k, None)
            # 4. proc = await asyncio.create_subprocess_exec(*argv, env=child_env, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            # 5. self._inflight[req_id] = proc
            # 6. parser = self._parser_factory()
            # 7. async for line in proc.stdout: events = parser.parse_line(line); for ev in events: await on_event(ev)
            # 8. await proc.wait(); on non-zero: emit Error; always: emit Done (parser-final if not already)
            # 9. finally: del self._inflight[req_id]; cleanup_stale_configs(...)
        async def cancel(req_id):
            proc = self._inflight.get(req_id); if proc: proc.terminate()  # Windows auto-maps to CTRL_C_EVENT for the leaf
        async def health_check():
            try: p = await asyncio.create_subprocess_exec(self._claude_path, 'auth', 'status', stdout=DEVNULL); await p.wait(); return READY if p.returncode==0 else AUTH_DRIFT
            except FileNotFoundError: return NOT_INSTALLED

    Update `nyrahost/backends/__init__.py`: add `from .claude import ClaudeBackend`; `BACKEND_REGISTRY['claude'] = ClaudeBackend`.

    Update `handlers/chat.py.ChatHandlers.on_chat_send`: replace the NotImplementedError('Plan 02-04') branch from Plan 02-03 with actual dispatch — `backend_cls = BACKEND_REGISTRY[backend_name]; backend = backend_cls(...DI...); await backend.send(...)`. Preserve every other line of chat.py verbatim (D-24).

    Commit: feat(02-05): add ClaudeBackend subprocess driver + wire into backend registry
  </action>
  <verify>
    <automated>cd TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest -v 2>&1 | tail -5 | grep -E "passed|failed"</automated>
  </verify>
  <done>
    - ClaudeBackend spawns claude with the exact locked flag set, env-scrubbed
    - StreamParser drives event emission; cancel/health_check wired
    - BACKEND_REGISTRY['claude'] is ClaudeBackend
    - ChatHandlers dispatches backend='claude' without raising
    - Full pytest suite green — Phase 1's 34 + Plan 02-03's new tests + 3 Plan 02-05 test files all passing
    - pytest-subprocess dependency in pyproject + lockfile
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| NyraHost ↔ claude CLI subprocess | stdout/stderr pipes carry user-impacting content; child process inherits (scrubbed) env |
| claude CLI ↔ user's OAuth token | Token lives in %USERPROFILE%\.claude\ACLs; NyraHost NEVER reads it |
| NyraHost ↔ MCP config file | %LOCALAPPDATA%/NYRA/mcp-configs/ is current-user ACL; Claude's subprocess reads only |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-05-01 | Information Disclosure | CLAUDE_CODE_OAUTH_TOKEN leaks to NyraHost log sinks | mitigate | NyraHost never reads the env var; structlog redaction pattern excludes any key matching r'(?i)(TOKEN\|KEY\|SECRET\|AUTH)'. Runbook in `docs/THREAT_MODEL.md` (Phase 2 polish doc). |
| T-02-05-02 | Tampering | Attacker sets ANTHROPIC_API_KEY in env to redirect Claude calls to attacker's account | mitigate | env scrub at spawn removes both ANTHROPIC_API_KEY and ANTHROPIC_AUTH_TOKEN (RESEARCH §1.2 trap mitigation). CHAT-02 status pill surfaces warning banner if these vars are detected pre-scrub (Plan 02-12). |
| T-02-05-03 | Denial of Service | Malicious prompt returns gigabytes of text; streaming parser OOMs | mitigate | StreamParser state is O(current tool-use block bytes); text deltas flow through without buffering. Per-message cap enforced in chat.py response path (Phase 1 inherits). |
| T-02-05-04 | Tampering | Different local process impersonates the MCP config path | mitigate | File written under per-user %LOCALAPPDATA% ACLs; config path passed as absolute CLI arg so Claude does not search $PATH. Session UUID filename prevents collision. |
</threat_model>

<verification>
- `cd TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest -v` → all passed (≥34 Phase 1 + Plan 02-03 tests + Plan 02-05 tests)
- `grep -q "ClaudeBackend" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/__init__.py` — registered
- `grep -q "pytest-subprocess" TestProject/Plugins/NYRA/Source/NyraHost/requirements-dev.lock` — dep pinned
- argv assertion test asserts exact flag set including `--mcp-config`, `--strict-mcp-config`, `--permission-mode dontAsk`, `--permission-prompt-tool nyra_permission_gate`
</verification>

<success_criteria>
- `claude -p` spawns with locked flag set, env-scrubbed, MCP config injected, session UUID passed
- NDJSON parser handles all six event variants per RESEARCH §1.3
- `--bare` is absent (subscription mode)
- Full suite green; Plan 02-03's NotImplementedError stub removed
- Plan 02-06 can layer router state machine transitions on top of emitted Retry / Error events
</success_criteria>

<output>
After completion, create `.planning/phases/02-subscription-bridge-ci-matrix/02-05-SUMMARY.md`
</output>
