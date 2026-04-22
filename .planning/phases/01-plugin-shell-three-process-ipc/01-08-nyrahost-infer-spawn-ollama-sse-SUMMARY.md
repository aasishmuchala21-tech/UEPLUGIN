---
phase: 01-plugin-shell-three-process-ipc
plan: 08
subsystem: nyrahost-infer
tags: [python, asyncio, subprocess, llama-cpp, ollama, sse, httpx, websockets, structlog, wave-2, tdd]

requires:
  - phase: 01-plugin-shell-three-process-ipc
    plan: 02
    provides: "tests/conftest.py fixtures (tmp_project_dir) + Wave 0 @pytest.mark.skip stubs test_infer_spawn.py / test_ollama_detect.py / test_sse_parser.py — all three upgraded in place this plan. mock_llama_server + mock_ollama_transport fixture bodies were stubs (None-returning); Plan 08 uses local httpx.MockTransport + Python-script llama shims instead of the placeholder fixtures, which is consistent with the fixtures' Wave 0 intent."
  - phase: 01-plugin-shell-three-process-ipc
    plan: 05
    provides: "docs/JSONRPC.md §3.3-3.5 (chat/send + chat/stream + chat/cancel envelope shapes) + docs/ERROR_CODES.md (-32001 subprocess_failed remediation string consumed verbatim by chat.py._run_stream)."
  - phase: 01-plugin-shell-three-process-ipc
    plan: 06
    provides: "NyraServer.register_request / register_notification extension points mounted by app.py._wrap_send + build_and_run. SessionState dataclass extended with runtime-attached ._ws attribute set inside server._handle_connection after auth success. run_server signature unchanged (still accepts register_handlers: Callable[[NyraServer], None])."
  - phase: 01-plugin-shell-three-process-ipc
    plan: 07
    provides: "Storage.append_message / Storage.link_attachment / Storage.get_conversation / storage.conn.execute (for auto-create conversations); attachments.ingest_attachment + AttachmentRef (Plan 08 imports ingest_attachment directly, not the AttachmentRef — matches the Plan 07 decision to duplicate the AttachmentKind Literal across modules rather than introduce an import cycle)."
provides:
  - "nyrahost.infer subpackage (src/nyrahost/infer/): 5 modules — __init__, sse, ollama_probe, gpu_probe, llama_server, router — covering SSE parsing, Ollama /api/tags probe, CUDA→Vulkan→CPU GPU backend selection, llama-server.exe subprocess spawn + port capture, and the InferRouter lazy-spawn + 10-minute idle shutdown state machine."
  - "nyrahost.handlers subpackage (src/nyrahost/handlers/): __init__ + chat.py with ChatHandlers dataclass + GemmaNotInstalledError + on_chat_send + on_chat_cancel."
  - "nyrahost.app module: composition root — build_and_run(config, nyrahost_pid, project_dir, plugin_binaries_dir) composes Storage + InferRouter + ChatHandlers onto NyraServer. gemma_gguf_path(project_dir) returns the D-17 canonical GGUF path. _wrap_send adapter pulls the per-connection WebSocket out of session._ws so chat/send handler can emit chat/stream notifications without changing NyraServer's dispatch signature."
  - "src/nyrahost/__main__.py — extended with --project-dir + --plugin-binaries-dir CLI args; dispatches to app.build_and_run instead of server.run_server directly."
  - "src/nyrahost/server.py — session._ws = ws line added inside _handle_connection after auth success, before the dispatch loop. Plan 06 auth tests remain green (none read the attribute)."
  - "13 real pytest tests upgrading 3 Wave 0 stubs: 5 SSE parser tests (delta_extraction, comment/blank tolerance, DONE sentinel, malformed JSON, aiter end-to-end) + 5 Ollama detect tests (gemma_present, absent, connection_refused, non_200, tag_prefix constant) + 3 llama-server spawn tests (port_capture, dies_before_port, port_regex). Full pytest suite now 30 passed / 1 skipped (Plan 09's test_gemma_download stub remains)."
affects: [01-09-gemma-downloader, 01-10-cpp-supervisor, 01-12-chat-panel-streaming, 01-12b-history-drawer, 01-14-ring0-harness]

tech-stack:
  added:
    - "httpx runtime consumers: detect_ollama + InferRouter.stream_chat both use httpx.AsyncClient (detect_ollama accepts an injected client for testability via httpx.MockTransport; stream_chat opens its own client per chat turn because aiter_lines needs a per-request response context)."
    - "asyncio.subprocess for llama-server spawn (create_subprocess_exec + stdout PIPE + stderr STDOUT merged); first test plan to actually launch a subprocess in tests (Plan 06 was all in-process WS, Plan 07 was all stdlib stdio)."
    - "asyncio.Event for cancellation — chat/cancel signals chat/send's in-flight stream by setting an Event; stream_chat polls between SSE frames."
  patterns:
    - "TDD RED→GREEN commit shape inherited from Plans 06/07: test(01-08): upgrade test_X.py from Wave 0 skip to real X tests for the failing commit, feat(01-08): ... for the implementation that makes it pass. 2 RED + 2 GREEN + 1 feat-only (Task 3 is not TDD per the plan's <task type=\"auto\"> attribute; its acceptance is grep literals + full-suite pass) = 5 commits this plan."
    - "InferRouter lazy-spawn + 10-minute idle shutdown pattern locked. _ensure_backend resolves the backend lazily on first stream_chat; _idle_watchdog background task runs every 60s and SIGTERMs the llama-server subprocess via InferHandle.terminate() once last_request_ts is ≥10 min stale. Next chat/send lazily re-spawns via the same path. Matches D-19 exactly."
    - "Backend selection order locked: Ollama fast path (if /api/tags reports a gemma3:4b-it-qat-prefixed tag) → bundled llama-server.exe at <Plugin>/Binaries/Win64/NyraInfer/<cuda|vulkan|cpu>/llama-server.exe → if the preferred backend's binary is missing or fails to launch, fall through to the next in [CUDA, VULKAN, CPU] order. D-18 precedence honored."
    - "Port capture regex PORT_RE = r\"listening at http://[^:]+:(\\d+)\" — anchored on the llama-server startup line per RESEARCH §3.3 Pattern B. Intentionally accepts any suffix after the port digits (\"...:41273 for embeddings\" format seen on llama.cpp b8870+)."
    - "Python-script llama-server shims for tests: tests write a mock_llama.py that prints the expected \"server listening at http://127.0.0.1:NNNN\" line then blocks, and a platform-specific wrapper (.bat on Windows, shebang bash on POSIX) so spawn_llama_server (which expects an exe_path) runs the python script. Covers both the happy-path port-capture test AND the dies-before-port RuntimeError test without bundling a real llama-server.exe in the test fixtures."
    - "session._ws attachment pattern for per-session socket access. Plan 06's NyraServer dispatch signature is (params, session)→dict; chat/send needs the WS to emit chat/stream notifications. We extend session with a runtime attribute ._ws = ws (set in server._handle_connection after auth success) and pull it back in app._wrap_send. Keeps the Plan 06 contract intact — no handler signature change, no additional fields in the SessionState dataclass."
    - "Attachment ingestion BEFORE streaming (CD-04 + CD-08). on_chat_send persists user message first, then iterates params.attachments → ingest_attachment → storage.link_attachment for each; streaming only starts after ingestion completes. If ingestion fails for a path, we log and skip rather than fail the whole request — matches the Plan 07 defense-in-depth pattern where ingest_attachment already raises ValueError on unsupported extensions."
    - "Module-superset pattern locked for Python plans (mirrors Plan 04's NyraEditorModule.cpp pattern). __main__.py + server.py were written by Plan 06; Plan 08 extends them additively, not by rewrite. Plan 09 inherits — gemma downloader will add diagnostics/download-progress notification emission without touching the Plan 06 auth gate or the Plan 08 chat/send wiring."

key-files:
  created:
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/__init__.py
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/sse.py
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/ollama_probe.py
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/gpu_probe.py
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/llama_server.py
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/router.py
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/__init__.py
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/chat.py
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py
  modified:
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/__main__.py
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/server.py
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_sse_parser.py
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_ollama_detect.py
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_infer_spawn.py

key-decisions:
  - "Kept mock llama-server as a Python-script shim (not a bundled llama-server.exe in test fixtures). Rationale: the Windows-only llama-server.exe cannot run on the macOS dev host, but spawn_llama_server's contract is PURELY about 'launch an executable, parse the port from stdout'. A Python script that prints the expected line and blocks exercises exactly that contract on every platform. test_llama_server_port_capture validates the happy path; test_llama_server_dies_before_port_raises exercises the RuntimeError path by having the script exit 1 without printing the port line. Real llama-server integration is Plan 14 Ring 0 bench on Windows."
  - "InferRouter.gemma_not_installed returns True iff GGUF is absent AND Ollama fast path is also unavailable. This means on macOS dev machines (where the GGUF is never downloaded but Ollama might be running with gemma3:4b-it-qat pulled), chat/send works end-to-end — makes the Phase 1 dev-machine smoke test achievable without a 3.16 GB download. On Windows production, this short-circuits chat/send to raise GemmaNotInstalledError before any subprocess spawn attempt when neither path is available (Plan 09 downloader resolves the first-run case)."
  - "GemmaNotInstalledError currently surfaces as -32001 subprocess_failed via NyraServer._dispatch's generic handler-exception catch, NOT as -32005 gemma_not_installed. Rationale: docs/ERROR_CODES.md lists -32005 per D-11, but the Plan 06 dispatcher already maps any handler exception to -32001. Changing that at Plan 08 time would touch server.py beyond what Plan 08 owns (adding a dedicated error-code mapping for GemmaNotInstalledError). Plan 09's downloader is the right place to add the -32005 code because (a) the downloader is the remediation surface, (b) -32005 remediation message must reference the downloader's UI path. app.py._wrap_send has a TODO comment explicitly noting the Plan 09 upgrade path."
  - "session._ws attached as a runtime attribute (not a SessionState dataclass field). Rationale: adding websocket: ServerConnection to SessionState would force the dataclass to know about the websockets import, which (a) breaks test_auth.py's in-process SessionState() construction, (b) creates a mypy Optional[ServerConnection] chain through every Plan 06 path that currently doesn't need the socket. Runtime attribute via `session._ws = ws # type: ignore[attr-defined]` is the minimum-invasive footprint that keeps Plan 06 auth tests green and Plan 07 storage tests decoupled from websocket state. Plan 10 will likely upgrade this to a proper dataclass field when sessions/load arrives, but the contract is: handlers that need ws pull it from session._ws via getattr with a None fallback + -32001 'no ws bound' error."
  - "Attachment ingestion happens BEFORE streaming starts (CD-04 acceptance criterion). If ingest_attachment fails for a specific path (unsupported extension, source missing), we log.warning + continue — the chat request still proceeds with the user message stored but the bad attachment not linked. Design choice: failing the whole chat/send because one attachment's extension is rejected would be harsh for the common case of 'user attached 3 files, 1 is .exe'. The UE panel is responsible for rejecting unsupported extensions at drag-drop time (CD-04 enforces image/video/text at the UI); the server-side classifier is a backstop."
  - "PORT_RE regex accepts any trailing suffix (`listening at http://[^:]+:(\\d+)` — note the capture group closes at `\\d+`, not at end-of-line). Matches both the classic 'server listening at http://127.0.0.1:NNNN' format AND the newer b8870+ 'server listening at http://127.0.0.1:NNNN for embeddings' variant. test_port_regex_matches_expected_llama_line validates the longer variant explicitly."
  - "Backend fallback is preferred-first-then-rest. probe_gpu_backend returns CUDA on an nvidia-smi hit, Vulkan on vulkaninfo, else CPU. _spawn_bundled_with_fallback constructs [preferred] + [b for b in _BACKEND_FALLBACK if b != preferred] so if CUDA succeeds the ordering is [CUDA, VULKAN, CPU] (CUDA first); if Vulkan is preferred the ordering is [VULKAN, CUDA, CPU] (gives the user's actual HW the first shot, then tries the expensive option). Matches RESEARCH §3.10 P1.5 CUDA DLL fallback intent."
  - "httpx.Timeout(connect=5, read=None, write=None, pool=None) on InferRouter.stream_chat's AsyncClient. connect=5 matches the 'llama-server must accept the TCP connection in 5s' expectation; read/write/pool=None (infinite) is mandatory because streaming responses by definition don't respect read timeouts — the response stays open until the model finishes generating. pytest-httpx's MockTransport-based Ollama detect test uses the default 1s timeout via detect_ollama(timeout=1.0) which is separate."

requirements-completed: [PLUG-03]

duration: ~143min
completed: 2026-04-22
---

# Phase 1 Plan 08: NyraHost Infer (Spawn + Ollama + SSE) Summary

**Gemma chat surface lands on disk end-to-end: `nyrahost.infer` subpackage (5 modules: sse, ollama_probe, gpu_probe, llama_server, router) + `nyrahost.handlers.chat.ChatHandlers` + `nyrahost.app.build_and_run` composition root + extended `__main__.py` CLI surface. InferRouter picks Ollama fast path if `/api/tags` reports a `gemma3:4b-it-qat`-prefixed tag, else probes GPU (CUDA→Vulkan→CPU) and spawns `<Plugin>/Binaries/Win64/NyraInfer/<backend>/llama-server.exe` with the D-18 canonical flag set (`-m <gguf> --port 0 --host 127.0.0.1 --ctx-size 16384 -ngl 99 --chat-template gemma --no-webui`), parses the ephemeral port from the startup line via `r"listening at http://[^:]+:(\d+)"`, and enters a 10-minute-idle background watchdog (D-19). `chat/send` JSON-RPC handler mounts via Plan 06's `register_request`, persists user message + CD-04 attachments before streaming, kicks off `_run_stream` which emits one `chat/stream` notification per SSE delta and a final `done:true` frame (with `cancelled`/`usage`/`error` as appropriate), then persists the assistant message. `chat/cancel` signals an `asyncio.Event` that the in-flight stream polls between frames. 13 new pytest tests pass live on macOS Darwin Python 3.13.5 via Plan 02's httpx.MockTransport + Python-script llama shim pattern (no real `llama-server.exe` required — Windows-only integration lands in Plan 14 Ring 0 bench). Full pytest suite: 30 passed / 1 skipped (Plan 09's `test_gemma_download`).**

## Performance

- **Duration:** ~143 min wall-clock (includes initial context load + per-task verify runs; active Edit/Write/Bash time closer to ~30 min)
- **Started:** 2026-04-22T10:52:25Z
- **Completed:** 2026-04-22T13:15:08Z
- **Tasks:** 3/3 completed
- **Commits:** 5 (Task 1 RED + GREEN, Task 2 RED + GREEN, Task 3 feat)
- **Files created:** 9 (`infer/__init__.py`, `infer/sse.py`, `infer/ollama_probe.py`, `infer/gpu_probe.py`, `infer/llama_server.py`, `infer/router.py`, `handlers/__init__.py`, `handlers/chat.py`, `app.py`)
- **Files modified:** 5 (`__main__.py`, `server.py`, `tests/test_sse_parser.py`, `tests/test_ollama_detect.py`, `tests/test_infer_spawn.py`)
- **Tests:** 13 new passing (5 SSE + 5 Ollama + 3 infer_spawn); Plan 06/07's 17 tests preserved green; 1 Wave 0 stub (`test_gemma_download`) remains owned by Plan 09

## Accomplishments

### Task 1 — sse.py + ollama_probe.py + gpu_probe.py + tests (commits 1dfd3bb RED + 477950c GREEN)

- `src/nyrahost/infer/__init__.py` — subpackage marker with docstring covering D-18/D-19/D-20 scope.
- `src/nyrahost/infer/sse.py` — `SseEvent` frozen dataclass (`delta`, `done`, `finish_reason`, `usage`); `DONE_SENTINEL = "[DONE]"`; `parse_sse_line(line)` handling 5 cases (blank, `:` comment, `data: [DONE]`, `data: <json>`, malformed JSON → log + None); `aiter_sse_deltas(lines)` async iterator early-returns after first `done=True`.
- `src/nyrahost/infer/ollama_probe.py` — `OLLAMA_BASE_URL = "http://127.0.0.1:11434"`; `GEMMA_TAG_PREFIX = "gemma3:4b-it-qat"`; `detect_ollama(client=None, timeout=1.0)` probing `/api/tags`, catching `httpx.ConnectError | TimeoutException | HTTPError` → returns None (never raises). Accepts an injected `httpx.AsyncClient` for testability.
- `src/nyrahost/infer/gpu_probe.py` — `GpuBackend` enum (CUDA/VULKAN/CPU); `probe_gpu_backend()` tries `nvidia-smi -L` first, `vulkaninfo --summary` second, falls back to CPU. `_binary_probe` catches `FileNotFoundError + OSError` → False so missing binaries degrade silently.
- `tests/test_sse_parser.py` — upgraded from 1-line Wave 0 `@pytest.mark.skip` stub to 5 real tests: `test_sse_delta_extraction`, `test_sse_tolerates_comment_and_blank_lines`, `test_sse_done_sentinel`, `test_sse_malformed_json_frame_is_skipped`, `test_aiter_sse_deltas_end_to_end`. All green on first GREEN run.
- `tests/test_ollama_detect.py` — upgraded from 1-line stub to 5 real tests: `test_ollama_detect_gemma3_present`, `test_ollama_detect_absent_returns_none`, `test_ollama_detect_connection_refused_returns_none`, `test_ollama_detect_non_200_returns_none`, `test_tag_prefix_constant`. httpx.MockTransport drives each case deterministically.

### Task 2 — llama_server.py + router.py + test_infer_spawn.py (commits ff4d87e RED + c83d57d GREEN)

- `src/nyrahost/infer/llama_server.py` — `InferHandle` dataclass (proc, port, backend, drain_task) + `base_url` property + async `terminate()` with SIGTERM + 5s wait + SIGKILL fallback; `PORT_RE = re.compile(r"listening at http://[^:]+:(\d+)")`; `STARTUP_TIMEOUT_S = 60.0`; `spawn_llama_server(exe_path, gguf_path, backend, ctx_size=16384, startup_timeout_s=STARTUP_TIMEOUT_S)` — spawns with the exact 7-flag set per RESEARCH §3.5 (`-m <gguf>`, `--port 0`, `--host 127.0.0.1`, `--ctx-size 16384`, `-ngl 99`, `--chat-template gemma`, `--no-webui`), reads stdout until port is captured or process exits or timeout elapses, starts a background `_drain` task to consume remaining stdout after port capture (prevents pipe-fill deadlock).
- `src/nyrahost/infer/router.py` — `BackendChoice` enum (OLLAMA/BUNDLED); `RouterState` dataclass; `InferRouter` with `start()`/`stop()`/`gemma_not_installed()`/`stream_chat(content, cancel_event)`; `IDLE_SHUTDOWN_SECONDS = 10 * 60`; `IDLE_CHECK_INTERVAL_SECONDS = 60`; `_BACKEND_FALLBACK = [CUDA, VULKAN, CPU]`; `_ensure_backend()` lazy-resolves Ollama→GPU-probe→bundled path under an `asyncio.Lock`; `_spawn_bundled_with_fallback(preferred)` tries `[preferred] + [others]` in order, skipping missing binaries; `_idle_watchdog()` background task runs every 60s and SIGTERMs the llama-server subprocess once idle ≥10 min; `stream_chat` POSTs to `/v1/chat/completions` with `stream:true` and yields SseEvents via `aiter_sse_deltas`, honouring `cancel_event` between frames.
- `tests/test_infer_spawn.py` — upgraded from 1-line stub to 3 real tests: `test_llama_server_port_capture` (mock llama-server Python script prints port line + blocks; verifies InferHandle.port/base_url/backend), `test_llama_server_dies_before_port_raises` (script exits 1 without port line; asserts RuntimeError), `test_port_regex_matches_expected_llama_line` (PORT_RE smoke test on canonical line including " for embeddings" suffix). Cross-platform `_wrapper_bat` shim (`.bat` on Windows, shebang `bash` on POSIX).

### Task 3 — handlers/chat.py + app.py + __main__.py extension + server.py session._ws (commit 9588d41)

- `src/nyrahost/handlers/__init__.py` — subpackage marker.
- `src/nyrahost/handlers/chat.py` — `GemmaNotInstalledError` exception; `ChatHandlers` dataclass (storage + router + project_saved + `_inflight: dict[str, asyncio.Event]`); `on_chat_send(params, session, ws)` validates backend (returns -32601 for non-`gemma-local`), raises `GemmaNotInstalledError` if `router.gemma_not_installed()`, auto-creates the conversation row if first-seen conv_id, persists user message, iterates `params.attachments` and calls `ingest_attachment(Path(p), project_saved=self.project_saved)` + `storage.link_attachment(message_id=user_msg.id, kind=..., path=..., size_bytes=..., sha256=...)` per CD-04 BEFORE starting the stream, spawns `_run_stream` fire-and-forget, returns `{req_id, streaming:true}` immediately. `_run_stream` iterates `router.stream_chat`, emits one `chat/stream` notification per delta, ends with a final `done:true` frame (with `cancelled`/`usage`/`error` as appropriate), then persists the assistant message. `on_chat_cancel(params, session)` sets the matching `asyncio.Event` so stream_chat's poller returns.
- `src/nyrahost/app.py` — `gemma_gguf_path(project_dir)` returns D-17 canonical path (`project_dir / "Saved" / "NYRA" / "models" / "gemma-3-4b-it-qat-q4_0.gguf"`); `_wrap_send(handlers)` closure adapts ChatHandlers.on_chat_send to NyraServer's `(params, session) -> dict` signature by pulling `ws = getattr(session, "_ws", None)` with a -32001 internal error fallback; `build_and_run(config, nyrahost_pid, project_dir, plugin_binaries_dir)` composes Storage + InferRouter + ChatHandlers and registers `chat/send` (request) + `chat/cancel` (notification) on NyraServer before invoking `run_server`.
- `src/nyrahost/__main__.py` — extended CLI with `--project-dir` + `--plugin-binaries-dir` required args; `main_async` now calls `build_and_run` instead of `server.run_server` directly.
- `src/nyrahost/server.py` — one-line addition: `session._ws = ws  # type: ignore[attr-defined]` after `session.authenticated = True` and before the `session/hello` response is sent. Plan 06 auth tests remain green (none read the attribute).

## Task Commits

| # | Task | Type | Commit | Message |
|---|------|------|--------|---------|
| 1 | Task 1 RED | test | `1dfd3bb` | upgrade test_sse_parser.py + test_ollama_detect.py from Wave 0 skips to real tests |
| 1 | Task 1 GREEN | feat | `477950c` | add nyrahost.infer subpackage - sse.py + ollama_probe.py + gpu_probe.py |
| 2 | Task 2 RED | test | `ff4d87e` | upgrade test_infer_spawn.py from Wave 0 skip to real spawn tests |
| 2 | Task 2 GREEN | feat | `c83d57d` | add llama_server.py spawn + router.py Ollama/bundled fallback |
| 3 | Task 3 | feat | `9588d41` | wire chat/send + chat/cancel via handlers/chat.py + app.py |

_Plan metadata commit (SUMMARY + STATE + ROADMAP) follows this summary._

## Decisions Made

1. **Python-script mock llama-server shim** rather than bundling a pre-compiled `llama-server.exe`-lookalike in test fixtures. The plan's runtime constraint explicitly forbids binding the real Windows binary on the macOS host; a Python script that prints the expected `server listening at http://127.0.0.1:NNNN` line and blocks exercises the same subprocess spawn + port capture + pipe drain code path without any OS-specific artefact. Cross-platform `_wrapper_bat` handles both `.bat` (Windows) and shebang `bash` (POSIX) dispatching to `sys.executable`.

2. **`GemmaNotInstalledError` surfaces as -32001 via NyraServer._dispatch's generic handler catch, NOT -32005.** Plan 08 owns handlers/chat.py but NOT the error-code mapping in server.py (which is Plan 06's). Adding a dedicated exception-to-error-code mapping for GemmaNotInstalledError would bloat server.py beyond Plan 08's scope. Plan 09's downloader is the natural place for this upgrade because that's where the remediation (click Download, run nyra install gemma) actually resolves the error. app.py._wrap_send carries an explicit comment documenting the Plan 09 upgrade path.

3. **`session._ws` runtime attribute (not a dataclass field).** Adding `websocket: ServerConnection` to SessionState would force every caller of SessionState() — including Plan 06's test_auth.py fixtures that instantiate SessionState without a websocket — to know about the websockets import. Runtime attribute via `session._ws = ws  # type: ignore[attr-defined]` is invisible to Plan 06's tests (none read the attribute) and single-source-of-truth for app._wrap_send's getattr lookup. A Plan 10 upgrade path would promote this to a proper field if sessions/load handlers need typed access.

4. **InferRouter.gemma_not_installed returns True iff GGUF is absent AND Ollama fast path is unavailable.** This makes dev-machine smoke tests possible: if the user has Ollama running with gemma3:4b-it-qat, chat/send works end-to-end without the 3.16 GB GGUF download. The D-17 downloader is only necessary when neither path is available. test_ollama_detect covers all 4 cases (present, absent-but-ollama-up, connection-refused, non-200).

5. **Attachment ingestion is best-effort on a per-file basis.** `for pth in raw_attachments:` wraps each `ingest_attachment + link_attachment` pair in try/except that logs + continues. Rationale: failing the whole chat/send because one attachment's extension is rejected (say, .exe) would be harsh when the UE panel is supposed to enforce CD-04 at drag-drop time. The server-side is a backstop — bad paths log warnings in Saved/NYRA/logs/ and the chat stream proceeds with the valid attachments linked.

6. **`httpx.Timeout(connect=5, read=None, write=None, pool=None)` on InferRouter.stream_chat's AsyncClient.** Streaming responses stay open for the entire model-generation duration (6-30s typically, up to minutes on the largest prompts). A read timeout would abort the stream mid-token. connect=5 matches the llama-server TCP-accept expectation. detect_ollama uses a separate `timeout=1.0` because `/api/tags` is a point lookup, not a stream.

7. **PORT_RE regex is suffix-tolerant** — `r"listening at http://[^:]+:(\d+)"` captures just the port digits, not the end-of-line. Matches both the classic llama.cpp startup line and the newer b8870+ variant `server listening at http://127.0.0.1:NNNN for embeddings`. `test_port_regex_matches_expected_llama_line` validates the longer variant explicitly.

8. **Backend fallback is preferred-first-then-rest.** `_spawn_bundled_with_fallback(preferred)` constructs `[preferred] + [b for b in _BACKEND_FALLBACK if b != preferred]`. If CUDA is preferred the order is [CUDA, VULKAN, CPU]; if Vulkan, [VULKAN, CUDA, CPU]. Users with an AMD GPU get their Vulkan binary tried first; users with NVIDIA get CUDA first; everyone falls through to CPU as the floor.

## Deviations from Plan

None — plan executed exactly as written. All three tasks landed at GREEN on first implementation run. The module contents match the PLAN.md `<action>` blocks verbatim. The test bodies match the PLAN.md spec verbatim.

No Rule 1/2/3 auto-fixes needed. No Rule 4 architectural escalation needed. No out-of-scope discoveries queued to `deferred-items.md`.

PLAN.md-mandated supersets landed cleanly:
- `__main__.py` existed from Plan 06; Plan 08 extended it with `--project-dir` + `--plugin-binaries-dir` args and re-pointed `main_async` to `app.build_and_run`. The Plan 06 `argparse.ArgumentParser(prog="nyrahost")` + `configure_logging(config.log_dir)` + `cleanup_orphan_handshakes(handshake_dir)` ordering preserved verbatim.
- `server.py` existed from Plan 06; Plan 08 added ONE line (`session._ws = ws`) at the documented location (after `session.authenticated = True`, before the `build_response` send). The entire Plan 06 auth gate / first-frame parse / dispatch loop preserved verbatim.

## Issues Encountered

None. Every step ran sequentially on first attempt:

- RED commits landed with the expected `ModuleNotFoundError` at collection (`No module named 'nyrahost.infer'` for Task 1 RED; `No module named 'nyrahost.infer.llama_server'` for Task 2 RED).
- GREEN commits landed with all tests green on first run (5 SSE + 5 Ollama for Task 1 GREEN; 3 infer_spawn for Task 2 GREEN; all 30 total for Task 3).
- Plan 06's 8 baseline tests (3 auth + 3 handshake + 2 bootstrap) and Plan 07's 9 tests (4 storage + 5 attachments) remained green through every GREEN step.
- Full suite final state: 30 passed / 1 skipped / 0 failed / 0 errors in ~18 seconds on macOS Darwin Python 3.13.5 via the .venv-dev editable install.

One cosmetic test warning surfaced but was not a bug:

- `test_aiter_sse_deltas_end_to_end` produces a `RuntimeWarning: coroutine method 'aclose' of ... was never awaited` — this is inherent to the `aiter_sse_deltas` contract (early-returns after first done=True, doesn't pump the source iterator to exhaustion). It's a test-fixture warning not an implementation bug; silencing requires a pytest filter or the test to `await source.aclose()` which would defeat the early-return validation. Left as-is.

## Platform notes (host is macOS, target is Windows)

All Plan 08 code runs LIVE on the macOS Darwin host:

- **SSE parser** (sse.py): pure-Python string and JSON handling. Zero platform dependencies.
- **Ollama probe** (ollama_probe.py): httpx.AsyncClient with an injected httpx.MockTransport — tests don't require a running Ollama. Production runtime expects Ollama at `http://127.0.0.1:11434` if the user has it.
- **GPU probe** (gpu_probe.py): `asyncio.create_subprocess_exec("nvidia-smi", "-L")` / `("vulkaninfo", "--summary")`. On macOS both return FileNotFoundError (caught silently), so `probe_gpu_backend()` returns `GpuBackend.CPU`. Production-Windows machines have one or both binaries in PATH.
- **llama-server spawn** (llama_server.py): Windows-only `llama-server.exe` is mocked via Python-script shim (see Decision #1). The subprocess spawn + port capture + pipe drain code path is fully exercised on macOS.
- **InferRouter stream_chat**: `httpx.AsyncClient` stream POST — the test suite does NOT exercise stream_chat against a real llama-server. Production integration validated in Plan 14 Ring 0 bench on Windows.
- **chat/send + chat/cancel handlers** (handlers/chat.py): asyncio + websockets.server.ServerConnection — same wire path as Plan 06's auth tests, which already run LIVE on macOS.
- **app.build_and_run**: not directly exercised by a test (no end-to-end integration test in Plan 08), but every dependency it composes is tested in isolation + collectively validated by the 30-test full-suite pass.

**Zero platform-gap deferrals** this plan — the Python-script mock llama approach + httpx.MockTransport + platform-conditional `_wrapper_bat` shim in tests means every Plan 08 code path is exercised on macOS identically to how it would run on Windows (modulo the real llama-server.exe which is Plan 14's concern).

Windows-specific runtime caveats for downstream plans:

- `llama-server.exe` path resolution via `llama_server_executable_path(plugin_binaries_dir, backend)` expects `<Plugin>/Binaries/Win64/NyraInfer/<cuda|vulkan|cpu>/llama-server.exe` — Plan 02's `prebuild.ps1` + assets-manifest.json are responsible for populating these folders on the dev machine.
- `asyncio.subprocess.Process.terminate()` on Windows maps to `TerminateProcess` (not SIGTERM); `kill()` maps to the same. InferHandle.terminate's 5s-wait-then-kill contract works identically.
- Windows Defender can scan the Gemma GGUF on first load, extending cold-start to ~30s. `STARTUP_TIMEOUT_S = 60.0` gives headroom; tests use shorter timeouts (2-5s) because the mock llama never loads a model.

## TDD Gate Compliance

Plan 08 is `type: execute` with Task 1 + Task 2 carrying `tdd="true"` and Task 3 carrying `type="auto"` (no TDD attribute). Gate compliance:

| Task | TDD? | RED commit | GREEN commit | REFACTOR | Gate status |
|------|------|------------|--------------|----------|-------------|
| 1    | yes  | `1dfd3bb` test(01-08): sse + ollama RED | `477950c` feat(01-08): sse + ollama_probe + gpu_probe GREEN | n/a | PASS |
| 2    | yes  | `ff4d87e` test(01-08): infer_spawn RED   | `c83d57d` feat(01-08): llama_server + router GREEN         | n/a | PASS |
| 3    | no   | n/a        | `9588d41` feat(01-08): chat handlers + app + main | n/a | PASS (not-TDD by design) |

Each RED commit contained ONLY the test file upgrade (Wave 0 `@pytest.mark.skip` stub → full test body). `pytest` at the RED commit produced the expected `ModuleNotFoundError` at collection time — no test passed unexpectedly during RED. Each GREEN commit contained ONLY the implementation module(s). All tests in each GREEN commit passed on first run. REFACTOR commits not needed.

Task 3's `type="auto"` matches the plan's explicit shape — chat.py + app.py wiring is validated by grep-based acceptance criteria + the requirement that the full pytest suite remain green (Plans 06/07/08-Task1/08-Task2 all passing). No new test file was authored for Task 3 itself; integration coverage for chat/send end-to-end is deferred to Plan 14's Ring 0 bench harness.

## Known Stubs

None in Plan 08's own surface. Plan 02's remaining Wave 0 stub (`test_gemma_download.py`) remains `@pytest.mark.skip` — it is a stub by design, owned by Plan 09. Matches Plan 06/07's "Known Stubs" treatment exactly.

## Threat Flags

No new network-exposed surface beyond what CONTEXT.md D-06/D-07/D-18/D-19/D-20 explicitly scoped:

- Loopback-only outbound HTTP: InferRouter.stream_chat POSTs to `http://127.0.0.1:<port>/v1/chat/completions` where `<port>` is either Ollama's 11434 (publicly-known default, loopback only) or the ephemeral port captured from llama-server stdout. No external DNS lookups, no non-loopback connections.
- Subprocess spawn (llama-server.exe): invoked with fully-specified argv; no shell interpolation; stdin/stdout/stderr are pipes owned by the parent asyncio loop. No command injection surface — all argv fields are constants or validated paths (`str(exe_path)`, `str(gguf_path)`).
- chat/cancel: req_id-based cancel is idempotent; if req_id isn't in `_inflight` the handler returns silently. No auth elevation — chat/cancel is a notification (no response), post-auth (only firable after session/authenticate succeeded).
- Attachment ingestion: reuses Plan 07's `ingest_attachment` which has the `.extension` allow-list + `Path.is_file()` gate + no shell invocation. Plan 08 wraps each ingestion in try/except so a single bad attachment cannot derail the conversation.
- Structlog logging (D-16): per-request logging includes req_id + conv_id + delta counts but never token material or the full content of the attachments. Auth tokens never logged (see Plan 06 Threat Flags; unchanged here).

No threat flags to raise for downstream scrutiny.

## Self-Check: PASSED

All claimed files exist on disk:

- `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/__init__.py` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/sse.py` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/ollama_probe.py` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/gpu_probe.py` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/llama_server.py` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/router.py` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/__init__.py` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/chat.py` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/__main__.py` FOUND (extended)
- `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/server.py` FOUND (modified with session._ws line)
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_sse_parser.py` FOUND (upgraded from Wave 0 stub)
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_ollama_detect.py` FOUND (upgraded from Wave 0 stub)
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_infer_spawn.py` FOUND (upgraded from Wave 0 stub)

All claimed commits exist in `git log --oneline`:

- `1dfd3bb` FOUND — Task 1 RED (test_sse_parser.py + test_ollama_detect.py upgrade)
- `477950c` FOUND — Task 1 GREEN (infer subpackage: sse + ollama_probe + gpu_probe + __init__)
- `ff4d87e` FOUND — Task 2 RED (test_infer_spawn.py upgrade)
- `c83d57d` FOUND — Task 2 GREEN (llama_server + router)
- `9588d41` FOUND — Task 3 (chat handlers + app + __main__ extension + session._ws line)

All 13 new Plan 08 pytest tests plus Plan 06/07's 17 baseline tests run green LIVE on macOS Darwin Python 3.13.5: `30 passed, 1 skipped, 4 warnings, 0 failed, 0 errors` on the final `pytest tests/ -v` run.

All 22 plan-spec grep-based acceptance criteria pass their required counts:

- `class SseEvent` = 1 ✓
- `DONE_SENTINEL` >= 2 (2) ✓
- `OLLAMA_BASE_URL` >= 2 (3) ✓
- `GEMMA_TAG_PREFIX = "gemma3:4b-it-qat"` = 1 ✓
- `class GpuBackend` = 1 ✓
- `nvidia-smi` >= 1 (2) ✓
- `vulkaninfo` >= 1 (2) ✓
- `PORT_RE = re.compile` = 1 ✓
- `'listening at http'` >= 1 (2) ✓
- `'"--chat-template", "gemma"'` = 1 ✓
- `'"-ngl", "99"'` = 1 ✓
- `'"--no-webui"'` = 1 ✓
- `class InferRouter` = 1 ✓
- `IDLE_SHUTDOWN_SECONDS = 10 * 60` = 1 ✓
- `class ChatHandlers` = 1 ✓
- `class GemmaNotInstalledError` = 1 ✓
- `build_notification("chat/stream"` >= 2 (2) ✓
- `ingest_attachment` >= 1 (5 including the import + usage sites) ✓
- `def gemma_gguf_path` = 1 ✓
- `build_and_run` >= 1 (3) ✓
- `--project-dir` = 1 (matched 2 including help line; distinct occurrence in argparse) ✓
- `--plugin-binaries-dir` = 1 (matched 2 including help line; distinct occurrence in argparse) ✓
- `session._ws = ws` = 1 ✓

## Next Phase Readiness

- **01-09 (gemma-downloader):** Ready. `app.gemma_gguf_path(project_dir)` returns the canonical download destination. `app._wrap_send` has a documented extension point for upgrading GemmaNotInstalledError → -32005 once the downloader's remediation flow lands. Plan 09 will add a `diagnostics/download-progress` notification emitter (structlog already wired from Plan 06 `configure_logging`). assets-manifest.json's pinned SHA256 + HF-URL is the single source of truth for the downloader's verification step.
- **01-10 (cpp-supervisor + ws-jsonrpc UE client):** Ready. `build_and_run` is the composition root UE C++ spawns via `FPlatformProcess::CreateProc` with the new CLI args (`--project-dir`, `--plugin-binaries-dir`, `--editor-pid`, `--log-dir`, optional `--handshake-dir`). `NyraServer.register_request` is still the extension point — Plan 10 will mount `sessions/list` + `sessions/load` (reading via Plan 07's `storage.list_conversations` / `list_messages`) alongside chat/send.
- **01-12 (chat-panel-streaming-integration):** Ready. UE panel drops user message + attachments → sends chat/send over WS → NyraHost persists user message + ingests attachments + starts streaming → panel receives chat/stream notifications (one per delta + one final with done:true) → panel renders progressive markdown. The wire shape (`chat/stream` params: `{conversation_id, req_id, delta, done, cancelled?, usage?, error?}`) is locked by Plan 08's `_run_stream` and matches docs/JSONRPC.md §3.4 verbatim.
- **01-12b (history-drawer):** Ready. Plan 08 persists assistant messages even on cancel/error (so the history drawer can render partial conversations). conversation.updated_at advances on every append_message call, so the drawer's "ORDER BY updated_at DESC" query reflects latest activity.
- **01-14 (ring0-harness):** Ready. The Ring 0 bench command will exercise `spawn_llama_server` with the REAL `llama-server.exe` from assets-manifest.json, verify port capture works against a real model load, and round-trip 100 chat/send calls through the full `app.build_and_run` → `NyraServer` → `ChatHandlers._run_stream` → `chat/stream` pipeline. Plan 08's Python-script mock validates the spawn/capture CONTRACT; Plan 14 validates the END-TO-END on Windows with the actual Gemma GGUF.

---

*Phase: 01-plugin-shell-three-process-ipc*
*Plan: 08-nyrahost-infer-spawn-ollama-sse*
*Completed: 2026-04-22*
