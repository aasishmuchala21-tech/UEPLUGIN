---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: milestone
current_phase: 01
current_plan: "10 complete (next = Wave 3: Plan 11 cpp-markdown-parser)"
status: executing
last_updated: "2026-04-22T23:00:00Z"
progress:
  total_phases: 9
  completed_phases: 0
  total_plans: 16
  completed_plans: 10
  percent: 62
---

# Project State: NYRA

**Last Updated:** 2026-04-22 (Plan 01-10 completed)

---

## Project Reference

**See:** `.planning/PROJECT.md` for locked decisions, Quality Bar, Constraints, Key Decisions, and Out-of-Scope list.
**See:** `.planning/ROADMAP.md` for phase structure, success criteria, dependency graph, and kill cut-lines.
**See:** `.planning/REQUIREMENTS.md` for all 34 v1 REQ-IDs and phase traceability.
**See:** `.planning/research/SUMMARY.md` for synthesized research (STACK, FEATURES, ARCHITECTURE, PITFALLS).

**Core Value:** Turn a reference (image, video, prompt) into a finished Unreal Engine scene — without the user paying a new AI bill or leaving the editor.

**Quality Bar:** Every phase's success criteria must beat a named competitor on a measurable dimension, or be an architectural gate that unblocks a future competitor-beating feature. Parity with Nwiro, Aura/Telos 2.0, Ultimate Engine CoPilot, Ludus, or the OSS MCP long tail is a failure state.

**Current Focus:** Phase 01 — plugin-shell-three-process-ipc

---

## Current Position

Phase: 01 (plugin-shell-three-process-ipc) — EXECUTING
Plan: 11 of 16 (next to execute)
**Milestone:** v1 (Fab launch)
**Current Phase:** 01
**Current Plan:** 10 complete (next = Wave 3: Plan 11 cpp-markdown-parser)
**Status:** Executing Phase 01 — Wave 1 COMPLETE; Wave 2 Python-side COMPLETE (Plans 06, 07, 08, 09); Wave 2 UE-side COMPLETE (Plan 10); Wave 3 NEXT (Plans 11, 12, 12b, 13, 14, 15)

**Progress (v1):**

```text
[██████░░░░] 62% — 0/9 phases complete (Phases 0-8), Phase 01 Wave 1 + Plans 06/07/08/09/10 shipped (10/16 plans: 01 + 02 + 03 + 04 + 05 + 06 + 07 + 08 + 09 + 10)
```

**Plans completed in Phase 01:**

- [x] Plan 03 — UPlugin two-module scaffold (5 tasks, 5 commits, SUMMARY on disk)
- [x] Plan 01 — C++ automation scaffold (Wave 0, 2 tasks, 2 commits, SUMMARY on disk — upgraded Plan 03 Rule-3 NyraTestFixtures.h stub to full Nyra::Tests namespace; added 4 new spec shells + README)
- [x] Plan 02 — Python pytest scaffold (Wave 0, 2 tasks, 2 commits, SUMMARY on disk — pyproject.toml + requirements-dev.lock + conftest.py with 4 fixtures + 9 @pytest.mark.skip test shells + README; pytest verified live on macOS host 9 skipped/0 failed/0 errors)
- [x] Plan 04 — Nomad tab placeholder panel (Wave 1, 3 tasks, 3 commits, SUMMARY on disk — Nyra::NyraChatTabId + SNyraChatPanel placeholder + Tools > NYRA > Chat menu wiring + Nyra.Panel.TabSpawner automation It block closing VALIDATION 1-04-01)
- [x] Plan 05 — Specs handshake + JSON-RPC + model pins (Wave 1, 2 tasks, 2 commits, SUMMARY on disk — docs/HANDSHAKE.md + docs/JSONRPC.md + docs/ERROR_CODES.md canonical wire specs; ModelPins.h/.cpp + assets-manifest.json with live-resolved python-build-standalone + Gemma 3 4B GGUF + llama.cpp b8870 pins)
- [x] Plan 06 — NyraHost core WS + auth + handshake (Wave 2, 3 tasks TDD=true, 6 commits [3 RED + 3 GREEN], SUMMARY on disk — 8-module `nyrahost` Python package [`bootstrap`, `config`, `logging_setup`, `handshake`, `jsonrpc`, `server`, `session`, `__main__`] + `requirements.lock` + `TestProject/Plugins/NYRA/prebuild.ps1` + 8 real passing pytest tests [3 auth + 3 handshake + 2 bootstrap] upgrading Plan 02's Wave 0 stubs; `python -m nyrahost` binds `127.0.0.1:<ephemeral-port>`, writes atomic handshake, enforces first-frame `session/authenticate` gate with WS close 4401 on token mismatch; `NyraServer.register_request` / `register_notification` extension points land for Plans 07/08/09)
- [x] Plan 07 — NyraHost storage + attachments (Wave 2, 2 tasks TDD=true, 4 commits [2 RED + 2 GREEN], SUMMARY on disk — `nyrahost.storage` [Storage + Conversation/Message dataclasses + SCHEMA_V1 DDL + CURRENT_SCHEMA_VERSION=1 + db_path_for_project] and `nyrahost.attachments` [ingest_attachment + AttachmentRef + ALLOWED_EXTENSIONS + os.link-with-shutil.copy2-fallback] modules + 9 real pytest tests [4 storage + 5 attachments] upgrading Plan 02's last 2 Wave 0 persistence stubs; SQLite per-project sessions.db at `<ProjectDir>/Saved/NYRA/sessions.db` in WAL + foreign_keys=ON with CHECK role IN ('user','assistant','system','tool'); attachments content-addressed to `Saved/NYRA/attachments/<sha[:2]>/<sha>.<ext>` per CD-08; full pytest suite 17 passed / 4 skipped on macOS Darwin Python 3.13.5)
- [x] Plan 08 — NyraHost infer spawn + Ollama detect + SSE (Wave 2, 3 tasks [Task 1+2 TDD=true, Task 3 type=auto], 5 commits [2 RED + 2 GREEN + 1 feat], SUMMARY on disk — `nyrahost.infer` subpackage [sse.py + ollama_probe.py + gpu_probe.py + llama_server.py + router.py] + `nyrahost.handlers.chat` [ChatHandlers + GemmaNotInstalledError + on_chat_send + on_chat_cancel] + `nyrahost.app` [build_and_run + gemma_gguf_path + _wrap_send adapter] + extended `__main__.py` with --project-dir + --plugin-binaries-dir + one-line `session._ws = ws` addition to server.py; InferRouter picks Ollama fast path else spawns bundled llama-server.exe with CUDA→Vulkan→CPU fallback + 10-min idle shutdown watchdog; chat/send persists user msg + ingests attachments via Plan 07 CD-04 BEFORE streaming then emits per-delta chat/stream notifications + final done:true frame; 13 real pytest tests [5 SSE + 5 Ollama + 3 infer_spawn] upgrading 3 Wave 0 stubs; full pytest suite 30 passed / 1 skipped [Plan 09 test_gemma_download stub remains])
- [x] Plan 09 — Gemma downloader (Wave 2, 2 tasks [Task 1 TDD=true, Task 2 type=auto], 3 commits [1 RED + 1 GREEN + 1 feat], SUMMARY on disk — `nyrahost.downloader` subpackage [__init__.py + progress.py with ProgressReporter + RATE_LIMIT_MS=500 + RATE_LIMIT_BYTES=10*1024*1024 + gemma.py with GemmaSpec + GemmaDownloader + download_gemma async helper + GEMMA_FILENAME constant] + `nyrahost.handlers.download.DownloadHandlers` + additive superset of app.py [_load_gemma_spec helper + DownloadHandlers instantiation + one extra server.register_request("diagnostics/download-gemma", ...) call]; GemmaDownloader streams HuggingFace CDN with HTTP Range-resume [206 Partial Content + 200 OK restart fallback] + pre-hashes existing .partial bytes + atomic Path.replace rename + SHA256 verify against ModelPins-pinned hash + GitHub Releases mirror fallback on primary failure; on_download_gemma fire-and-forget asyncio.Task emits diagnostics/download-progress per docs/JSONRPC.md §3.7 notifications; one Rule 1 auto-fix during GREEN [httpx.Timeout default param required on httpx 0.32]; 4 real pytest tests upgrading Plan 02's LAST Wave 0 stub [test_sha256_verify_and_range_resume + test_fallback_to_mirror_on_primary_404 + test_both_urls_fail_raises_and_emits_error_progress + test_progress_rate_limited]; full pytest suite 34 passed / 0 skipped — Plan 02's Wave 0 stub pipeline FULLY LIQUIDATED)
- [x] Plan 10 — C++ supervisor + WS + JSON-RPC (Wave 2 UE-side, 3 tasks, 3 commits, SUMMARY on disk — FNyraJsonRpc encode/decode [10 It block EnvelopeRoundtrip spec, VALIDATION 1-02-02] + FNyraHandshake polling [50ms x1.5 backoff, 2s cap, 30s budget, partial-read tolerant, CleanupOrphans for P1.2] + FNyraWsClient [FWebSocketsModule wrap, session/authenticate first frame, 4401 close-code OnAuthFailed, NextId monotonic from 1 per P1.7] + FNyraSupervisor [FMonitoredProcess bHidden+bCreatePipes, CLI args matching nyrahost/__main__.py parse_args exactly, INyraClock injectable via FNyraSystemClock/FTestClockAdapter, 3-in-60s restart policy with window eviction, in-flight replay with fresh id, RequestShutdown -> shutdown notif -> 2s grace -> Cancel(bKillTree=true)] + NyraEditorModule.cpp additive superset (Plans 03+04 symbols/log lines preserved verbatim; GNyraSupervisor TUniquePtr wired into StartupModule after tab registration [D-04] and ShutdownModule BEFORE tab unregister [D-05]) + NyraSupervisorSpec.cpp RestartPolicy 2-It block [3-in-60s trips / 3-outside-60s does NOT, VALIDATION 1-02-03] + NyraIntegrationSpec.cpp guarded HandshakeAuth LatentIt [VALIDATION 1-02-01 opt-in])
- [ ] Plan 11 onwards (Wave 3: markdown parser, chat panel streaming integration, history drawer, first-run UX, Ring 0 harness + run)

**Progress by phase (REQ-ID coverage):**

| Phase | Name | REQs Mapped | Status |
|-------|------|-------------|--------|
| 0 | Legal & Brand Gate | 1 (PLUG-05) | Not started |
| 1 | Plugin Shell + Three-Process IPC | 4 (PLUG-01, PLUG-02, PLUG-03, CHAT-01) | Not started |
| 2 | Subscription Bridge + Four-Version CI Matrix | 9 (PLUG-04, SUBS-01, SUBS-02, SUBS-03, CHAT-02, CHAT-03, CHAT-04, ACT-06, ACT-07) | Not started |
| 3 | UE5 Knowledge RAG | 4 (KNOW-01, KNOW-02, KNOW-03, KNOW-04) | Not started |
| 4 | Blueprint + Asset + Material + Actor Tool Catalog | 5 (ACT-01, ACT-02, ACT-03, ACT-04, ACT-05) | Not started |
| 5 | External Tool Integrations (API-First) | 3 (GEN-01, GEN-02, GEN-03) | Not started |
| 6 | Scene Assembly + Image-to-Scene (Fallback Launch Demo) | 2 (SCENE-01, DEMO-01) | Not started |
| 7 | Sequencer + Video-to-Matched-Shot (LAUNCH DEMO) | 2 (SCENE-02, DEMO-02) | Not started |
| 8 | Fab Launch Prep | 4 (DIST-01, DIST-02, DIST-03, DIST-04) | Not started |

**Coverage:** 34/34 v1 requirements mapped. No orphans. No duplicates.

---

## Performance Metrics

Populated as phases complete. Tracks:

- **Competitor-beating dimensions landed:** 0/N (each phase's success criteria contributes)
- **Architectural gates cleared:** 0 (Phase 0 legal clearance, Phase 1 three-process IPC, Phase 2 four-version CI + EV cert + subscription bridge, Phase 5 computer-use reliability spike, Phase 7 cold-start release gate)
- **Cut-lines triggered:** 0 (see `ROADMAP.md#kill-cut-lines`)
- **Timeline consumed:** 0 weeks of 26-39 week budget (6-9 months)

### Per-plan execution metrics

| Phase | Plan | Name                             | Tasks | Files | Duration | Commits                                           |
| ----- | ---- | -------------------------------- | ----- | ----- | -------- | ------------------------------------------------- |
| 01    | 03   | uplugin-two-module-scaffold      | 5     | 18    | ~28min   | c650c84 · 1bbf4e4 · 2dd106c · 106ed82 · 2dc2d32   |
| 01    | 01   | cpp-automation-scaffold          | 2     | 7     | ~34min   | 35ed37d · ca182ba                                 |
| 01    | 02   | python-pytest-scaffold           | 2     | 14    | ~9min    | 1465d8d · 0cbfe95                                 |
| 01    | 04   | nomad-tab-placeholder-panel      | 3     | 5     | ~8min    | 224ffa7 · 628de82 · cf3ab9c                       |
| 01    | 05   | specs-handshake-jsonrpc-pins     | 2     | 6     | ~21min   | 7aa83af · fa2d8f9                                 |
| 01    | 06   | nyrahost-core-ws-auth-handshake  | 3     | 15    | ~42min   | 4400ae0 · e890a52 · 9cef418 · ef91a6f · bbea561 · 125ce46 |
| 01    | 07   | nyrahost-storage-attachments     | 2     | 4     | ~15min   | 5cb4c8f · f6c29b5 · 89e1c49 · 861aa35             |
| 01    | 08   | nyrahost-infer-spawn-ollama-sse  | 3     | 14    | ~143min  | 1dfd3bb · 477950c · ff4d87e · c83d57d · 9588d41   |
| 01    | 09   | gemma-downloader                 | 2     | 6     | ~209min  | c1d8b37 · 4c5eac1 · 269c251                       |
| 01    | 10   | cpp-supervisor-ws-jsonrpc        | 3     | 12    | ~23min   | 048d667 · 475f613 · f89d772                       |

---

## Accumulated Context

### Decisions (from PROJECT.md — locked)

- Three-process architecture (UE plugin + Python NyraHost + llama.cpp NyraInfer) — crash isolation, plugin never sees Claude auth tokens
- Python sidecar (not Rust / TypeScript) — MCP Python SDK is most mature, can drive UE's `unreal` Python module
- Subprocess-drive Claude Code CLI (not embed Agent SDK) — Anthropic ToS prohibits third-party claude.ai login embedding
- Drop Codex from v1, defer to v1.1 — halves CLI integration + legal + auth surface; router designed multi-backend for clean drop-in
- Gemma 3 4B IT QAT Q4_0 GGUF (multimodal) as local fallback — 3.16 GB, 128K context, text+image
- API-first external integrations; computer-use reserved for Substance Sampler + UE modal dialogs only
- Pre-code legal gate (Phase 0) runs in parallel with Phase 1 plugin-shell work per founder decision
- Free Fab plugin for v1; Dual SKU (paid Pro tier) deferred until usage signal justifies
- UE 5.4-5.7 support with four-version CI on day one of Phase 2
- Windows-only for v1
- Launch demo = reference video → matched UE shot (DEMO-02). Image → scene (DEMO-01) is the fallback demo if timeline slips.
- Claude-only for v1 reasoning; v1.1 adds Codex for expanded economic wedge

### Open TODOs (cross-cutting, carry into every phase)

- [ ] Public devlog started from Month 1 (PITFALLS §7.4 — competitor-preempts-demo mitigation)
- [ ] Weekly self-retrospective: "what's in Active that's not on the critical path to DEMO-02?" (PITFALLS §7.1 scope discipline)
- [ ] Random-reference daily test from Phase 6 Day 1 (PITFALLS §7.2 — demo-driven-development-trap mitigation)
- [ ] Symbol-validation step is a pre-execution gate for every Phase 4+ action (PITFALLS §4.1, §4.4)
- [ ] Every NYRA session wrapped in a super-transaction; cleanup-session menu option tags all NYRA-created assets (PITFALLS §9.2)

### Decisions from Plan 02 (python-pytest-scaffold, 2026-04-21)

- Pinned pytest-asyncio 0.24.0 for all Phase 1 Python plans — 0.25+ introduces breaking fixture-scope default changes; 0.24 matches PLAN.md's MAJOR.MINOR pin and gives a consistent deprecation-warning surface across future plans.
- Dev-only Python deps live in requirements-dev.lock; runtime deps stay in a separate requirements.lock (authored in Plan 06) per CONTEXT.md D-13/D-14 shipping discipline — embedded CPython + pre-resolved wheels for users; pytest/black/ruff/mypy never ship.
- Did NOT silence pytest-asyncio's `asyncio_default_fixture_loop_scope` deprecation warning — PLAN.md's `<interfaces>` specifies EXACT contents and the key is Optional per Context7 docs. Plan 06 (first real async test writer) is the right place to pick a fixture loop scope.
- Kept `mock_llama_server` async-signatured with a `None`-returning body (instead of making it sync) — locks the callsite shape `await mock_llama_server` for all Plan 06/07 callers today; Plan 08 swaps the body without breaking any caller.

### Decisions from Plan 06 (nyrahost-core-ws-auth-handshake, 2026-04-22)

- TDD RED/GREEN commit pattern locked for Phase 1 Python plans: `test(NN-NN): upgrade test_X.py from Wave 0 skip to real ...` for failing test, then `feat(NN-NN): add nyrahost.X ...` for the implementation that makes it pass. Each Wave 0 @pytest.mark.skip stub is upgraded in its own RED commit; the implementation module lands in a follow-on GREEN commit. Plans 07/08/09 inherit this exact sequence.
- `NyraServer.register_request(method, handler)` / `register_notification(method, handler)` extension-point pattern locked. Downstream plans (07/08/09/10) NEVER modify `_handle_connection` or `_dispatch` directly — they register their method surfaces by name. Default handler `session/hello` stays owned by `server.py`; phase-specific handlers live in phase-specific modules. Keeps the auth gate as a single source of truth.
- Handshake write sequence (hard order, RESEARCH §3.10 P1.1): `websockets.serve` → capture port via `ws_server.sockets[0].getsockname()[1]` → `write_handshake` → `ws_server.serve_forever()`. The port MUST be known before the file appears or the UE poller races and reads zero/stale data.
- Runtime-vs-dev lockfile split: runtime deps in `requirements.lock` (D-14 wheel cache bundles these), dev deps in `requirements-dev.lock` (dev machines only). Any future runtime dep bump touches `pyproject.toml [project].dependencies` + `requirements.lock` in the same commit; version drift between the two is a Rule 1 bug.
- Caught `OverflowError` alongside `OSError` in `handshake._pid_running` POSIX branch — macOS `os.kill(pid, 0)` raises `OverflowError` (not `OSError`) for pid > 2^31-1 (32-bit `pid_t`). Such a PID cannot be alive, so returning False is correct; `test_handshake_cleanup_orphans` deliberately exercises this with pid=3,999,999,999. Rule 1 fix; landed in Task 2 GREEN (`ef91a6f`).
- `websockets.server.ServerConnection` import path preserved — works on both pinned `websockets==12.0` and the test-time installed 16.0. If a future bump removes it, fallback is `websockets.asyncio.server.ServerConnection`.
- `*.egg-info/` + `build/` + `dist/` appended to `TestProject/.gitignore` — `pip install -e .` (required so `from nyrahost.X import ...` resolves during pytest) writes the egg-info dir; Plans 07/08/09 also need editable installs.

### Decisions from Plan 10 (cpp-supervisor-ws-jsonrpc, 2026-04-22)

- INyraClock is a full virtual abstract class (`virtual double NowSeconds() const = 0`) with `FNyraSystemClock` (production) and `FTestClockAdapter` (test, wraps `Nyra::Tests::FNyraTestClock`) as impls. Replaced PLAN.md's initial sketch of `TFunction<double()>` because the test callsite calls `Clock.Set(t)` between `SimulateCrashForTest` invocations and needs the adapter to re-read the underlying clock on each `NowSeconds()` call — a function-snapshot approach would freeze the first captured value. Plans 12 + 13 inherit the INyraClock abstraction for any future rate-limit / stream-timeout policy tests.
- Rule 2 addition: `bool bTestMode = false` on FNyraSupervisor. `SimulateCrashForTest` sets it; `RecordCrashAndMaybeRestart` suppresses `PerformSpawn` when true. Required for hermetic unit tests — without the flag the first `SimulateCrashForTest` invocation would call `PerformSpawn -> FMonitoredProcess::Launch("python.exe")` which either fails spuriously or leaks a background process on the test host. Production code never sets the flag, so the D-08 respawn path is unchanged.
- Rule 1 auto-fix: PLAN.md's handshake-dir sentinel `if (FPlatformProcess::ComputerName() && !(LocalAppData = ...).IsEmpty())` was a bug — `ComputerName()` returns a `const TCHAR*` that's never null on a real host. Simplified to `if (!LocalAppData.IsEmpty())` which directly matches docs/HANDSHAKE.md's "Primary vs Fallback (if LOCALAPPDATA unwritable)" contract.
- Module-superset discipline (Plan 03 + 04 → Plan 10): every Plan 03/04 symbol and log line in NyraEditorModule.cpp is preserved VERBATIM — `IMPLEMENT_MODULE(FNyraEditorModule, NyraEditor)`, Plan 03's include order, Plan 04's `[NYRA] NyraEditor module starting (Phase 1 skeleton)` log line, Plan 04's `RegisterNomadTabSpawner` + `UToolMenus::RegisterStartupCallback` + Tools-menu extension, Plan 04's `UnregisterNomadTabSpawner` + `UnregisterOwner(this)`. Plan 10 only adds: 3 new includes (FNyraSupervisor.h + IPluginManager.h + Paths.h), 1 `static TUniquePtr<FNyraSupervisor> GNyraSupervisor`, 5 lines in StartupModule (spawn AFTER tab registration per D-04), 5 lines in ShutdownModule (graceful shutdown BEFORE tab unregister so final WS frames drain per D-05). Plans 12/13 inherit this same additive-only contract.
- WS close-code 4401 handling is a one-shot gate: `HandleClose` only fires `OnAuthFailed` when `Code == 4401 && !bAuthenticated`. After auth success, a 4401 would be a server bug; forwarding it to OnAuthFailed would double-surface the panel's auth-error banner. `OnClosed` is always fired so the supervisor's crash+respawn path sees every close regardless of reason.
- `NextId` in FNyraWsClient starts at 1 and is a per-object counter; it is NEVER reset. Reconnects happen one layer up (FNyraSupervisor constructs a fresh FNyraWsClient after respawn). The supervisor's in-flight replay calls `SendRequest` under the NEW WsClient which issues a fresh id, and the panel layer (Plan 12) marks the original id as cancelled. Matches docs/JSONRPC.md §2 id-policy / RESEARCH P1.7.
- `SimulateCrashForTest` path does NOT fire `OnStateChanged` for the pre-unstable transitions through `Crashed` — the test explicitly asserts on `GetState() == Unstable` at the end. This keeps the unit test focused on the policy-trip invariant; Plan 12's panel-level tests can cover the full state-transition sequence through a real subprocess if/when needed.

### Decisions from Plan 09 (gemma-downloader, 2026-04-22)

- Rule 1 auto-fix: `httpx.Timeout(connect=10, read=60)` raises `ValueError: httpx.Timeout must either include a default, or set all four parameters explicitly.` on httpx 0.32. Plan 08's `InferRouter.stream_chat` uses `httpx.Timeout(connect=5, read=None, write=None, pool=None)` which is legal (all four explicit with None meaning unbounded). Plan 09's GemmaDownloader needs finite read/write/pool timeouts for the CDN transfer; fix is `httpx.Timeout(HTTP_READ_TIMEOUT, connect=..., read=..., write=..., pool=...)` — provides default AND all four explicit. Folded into Task 1 GREEN commit `4c5eac1`.
- GemmaSpec is independent of assets-manifest.json structure (Plan 05's manifest stores `gemma_model_note` as free-form only because Gemma is a runtime-download artefact, NOT a prebuild). `_load_gemma_spec(manifest_path)` reads a structured `gemma` block if present (future-proofing) and otherwise falls back to compile-time constants matching `ModelPins::GemmaGgufUrl` / `GemmaGgufMirrorUrl` shapes. Plan 13's first-run UX is the right place to wire the real ModelPins-sourced URL + pinned SHA via a manifest writer.
- Hard-coded default URLs in `_load_gemma_spec` use the qat-prefixed filename per `ModelPins::GemmaGgufFilename` acceptance literal, NOT the ACTUAL HF filename `ModelPins::GemmaGgufActualFilename` (which lacks `-qat-`). This will 404 against real HF without a manifest, which is ACCEPTABLE because (a) tests use `httpx.MockTransport`, (b) Plan 13 writes a proper manifest with the real URL before the UE panel invokes `diagnostics/download-gemma`, (c) production users' `prebuild.ps1` populates the manifest. Plan 13 closes the loop.
- Rate-limit policy (500ms OR 10MB) gates ONLY `downloading` frames. Terminal frames (`verifying`, `done`, `error`) always emit regardless of state. Rationale: a 'stuck at 100%' UX bug would occur if the last downloading frame and the done frame fell in the same 500ms window — the panel would dismiss progress only when the next chat arrived.
- 200 OK with Range header → restart hasher + truncate `.partial`. Some CDNs ignore Range and return the full body with status 200; `_download_from` branches on `resp.status_code`: if 206, parses Content-Range for total + appends; if 200, resets `hashlib.sha256()`, sets offset=0, opens the partial in `'wb'` (truncate) mode. Degenerate case — user 'wastes' already-downloaded bytes — but SHA correctness demands restart-from-zero.
- `DownloadHandlers._inflight` is `Optional[asyncio.Task]`, not a dict. At most 1 concurrent download per server instance; re-invoking during an in-flight download returns `{started:false, already_running:true}`. Rationale: 3.16 GB × 2 concurrent downloads would double disk I/O and network bandwidth, and both would race to write the same `.partial` file. Generalizes to a dict when Phase 2+ adds LanceDB index + computer-use tool asset downloads.
- Shallow `dest.exists()` short-circuit in `on_download_gemma` (NOT full SHA verify). Hashing 3.16 GB takes ~10s; doing so on every panel 'Is Gemma ready?' probe would be painfully slow. Full SHA verify only runs inside `GemmaDownloader.download()` when the user EXPLICITLY invokes `download-gemma` AND the file exists (the 'retry corrupt GGUF' path). Plan 13's UI surfaces a 'Re-download' button for the recovery case.
- Best-effort emit in `on_download_gemma`'s closure. `emit(params)` wraps `ws.send` in try/except and silently drops on failure. Rationale: download runs in a background asyncio.Task; if the WS session dies, there's no back-channel to surface the error (the original request already returned `{started:true}`). Silent drop is the correct UX — user reconnects, re-invokes `download-gemma`, gets `{already_present:true}` once the download completes.
- Plan 02's Wave 0 stub pipeline FULLY LIQUIDATED with Plan 09. `test_gemma_download.py` was the LAST `@pytest.mark.skip` in the NyraHost test suite. Full pytest 34 passed / 0 skipped / 0 failed. Phase 1 Wave 2 Python-side complete; Wave 2/3 UE-side work begins in Plan 10.

### Decisions from Plan 08 (nyrahost-infer-spawn-ollama-sse, 2026-04-22)

- Python-script mock llama-server shim locked for test harness. Plan 08's runtime constraint is that `llama-server.exe` is Windows-only and cannot run on the macOS dev host. Tests write a local `mock_llama.py` that prints the canonical `"server listening at http://127.0.0.1:NNNN"` line and blocks; a platform-specific wrapper (`.bat` on Windows, shebang `bash` on POSIX) dispatches `sys.executable`. This exercises `spawn_llama_server`'s contract (launch exe, parse port, start drain task) on both platforms without bundling real `llama-server.exe` in test fixtures. Real llama-server integration lives at Plan 14 Ring 0 bench on Windows.
- `GemmaNotInstalledError` maps to `-32001 subprocess_failed` via NyraServer._dispatch's generic handler catch in Plan 08, NOT to `-32005 gemma_not_installed` per docs/ERROR_CODES.md. Rationale: the Plan 06 dispatcher already routes handler exceptions to -32001, and adding dedicated exception-to-code mapping would push Plan 08 beyond its file scope (would need to modify server.py's _dispatch). Plan 09 (Gemma downloader) is the natural owner of the -32005 upgrade because (a) the downloader provides the remediation surface, (b) the -32005 remediation string references downloader UI. `app.py._wrap_send` carries an explicit comment documenting the Plan 09 upgrade path.
- `session._ws` attached as a **runtime attribute** (not a `SessionState` dataclass field). Rationale: adding `websocket: ServerConnection` to the Plan 06 dataclass would force all callers including test_auth.py's in-process `SessionState()` construction to know about the websockets import, bloat the typing chain with `Optional[ServerConnection]`, and break tests that instantiate SessionState without a socket. Runtime attribute via `session._ws = ws  # type: ignore[attr-defined]` (in server.py after auth success) + `getattr(session, "_ws", None)` (in app.py._wrap_send) is the minimum-invasive footprint that keeps Plan 06 auth tests green and Plan 07 storage tests decoupled. Plan 10 may promote this to a proper field when `sessions/load` arrives.
- Attachment ingestion (CD-04) happens BEFORE streaming starts, with **best-effort per-file error handling**. on_chat_send persists the user message, then iterates `params.attachments` calling `ingest_attachment` + `storage.link_attachment` for each path; failures (unsupported extension, missing source) log `attachment_ingest_failed` and continue. Rationale: the UE panel (CD-04) is the primary validator (it enforces image/video/text at drag-drop); the server is a backstop and shouldn't reject an entire conversation because one path in a batch of three has an unsupported extension.
- `PORT_RE = re.compile(r"listening at http://[^:]+:(\d+)")` is **suffix-tolerant** — the capture group closes at `\d+`, not at end-of-line. Matches both classic llama.cpp startup (`server listening at http://127.0.0.1:NNNN`) and the b8870+ variant (`server listening at http://127.0.0.1:NNNN for embeddings`). `test_port_regex_matches_expected_llama_line` validates the longer form.
- Backend fallback order is **preferred-first-then-rest**. `_spawn_bundled_with_fallback(preferred)` constructs `[preferred] + [b for b in _BACKEND_FALLBACK if b != preferred]`. If CUDA is preferred the order is `[CUDA, VULKAN, CPU]`; if Vulkan (AMD users), the order is `[VULKAN, CUDA, CPU]`. Everyone's actual HW gets first shot, then tries the other discrete-GPU backend, then falls through to CPU. Matches RESEARCH §3.10 P1.5 CUDA DLL fallback intent.
- `InferRouter.gemma_not_installed()` returns True iff **GGUF is absent AND Ollama fast path is also unavailable**. This makes dev-machine chat smoke-testable on macOS without the 3.16 GB download: if Ollama is running with `gemma3:4b-it-qat`, chat/send works end-to-end. On Windows production with neither path available, this short-circuits chat/send to raise GemmaNotInstalledError before any subprocess spawn.
- `httpx.Timeout(connect=5, read=None, write=None, pool=None)` on `InferRouter.stream_chat`'s AsyncClient. Streaming responses stay open for the entire model-generation duration; a read timeout would abort mid-token. `connect=5` matches the llama-server TCP-accept expectation; other limits are unbounded because streaming must not respect them. `detect_ollama` uses a separate `timeout=1.0` because `/api/tags` is a point lookup, not a stream.
- Module-superset pattern locked for Python plans (mirrors Plan 04's NyraEditorModule.cpp precedent). `__main__.py` existed from Plan 06; Plan 08 appended CLI args and re-pointed `main_async` to `app.build_and_run` while preserving every Plan 06 line (`argparse.ArgumentParser(prog="nyrahost")`, `configure_logging`, `cleanup_orphan_handshakes`) verbatim. `server.py` gained exactly ONE line (`session._ws = ws`) at the documented location. Plan 09 inherits — gemma downloader will add `diagnostics/download-progress` notification emission without touching the Plan 06 auth gate or the Plan 08 chat wiring.

### Decisions from Plan 07 (nyrahost-storage-attachments, 2026-04-22)

- Re-asserted `PRAGMA foreign_keys=ON` + `PRAGMA synchronous=NORMAL` on every new `Storage()` connection inside `_migrate` (not just first-open). WAL persists in the DB file header, but FK + synchronous are per-connection runtime state; silent FK-off on a reconnect would disable CASCADE delete and corrupt the message/conversation relationship without any error surface. `test_schema_v1_idempotent` exercises the reconnect path implicitly (second `Storage(db_path)` call on the same file).
- `AttachmentRef.path` is absolute (`str(dest.resolve())`) NOT project-relative. UE C++ readers (FFileHelper::LoadFileToString, FMediaTexture) expect absolute paths when the working directory is the editor's binary dir; making path resolution the responsibility of `ingest_attachment` (not every caller) eliminates a class of "who resolves the path?" bugs in Plan 12 chat panel code. If a user moves their UE project directory later, a Plan 12b repair action will fix up stale absolute paths.
- Enabled `detect_types=sqlite3.PARSE_DECLTYPES` at day one even though schema v1 uses no custom types. Plan 12b's future FTS tsvector BLOB column will need this flag; enabling it now avoids a schema v2 migration later just to flip the Connection constructor flag. Zero cost today, one future migration saved.
- `os.link`-first-with-`shutil.copy2`-fallback pattern locked for attachment ingestion (CD-08). Hardlink is O(1) metadata on NTFS/APFS/ext4 (common case); copy2 is the escape hatch for cross-device, FAT32, network mount, or CI runner without hardlink perms. Tested via `patch("nyrahost.attachments.os.link", side_effect=OSError)`. This same pattern re-applies to any future file-ingest surface (Plan 12b attachment-archive export, e.g.).
- `SCHEMA_V1` lives as a single triple-quoted string constant passed to `executescript` (not split into separate `CREATE TABLE` calls or a `migrations/` directory). Future schema v2 adds a parallel `SCHEMA_V1_TO_V2` constant and branches on `user_version` inside `_migrate` (`elif version == 1: conn.executescript(SCHEMA_V1_TO_V2)`). Simpler than a migrations framework for 3 tables; keeps the shape grep-able for the UE C++ audit tools in Phase 2 when SQLiteCore links.
- `AttachmentKind` Literal duplicated (3 lines) in both `storage.py` and `attachments.py` rather than imported from one into the other. Avoids an import cycle risk when Plan 10 mounts `sessions/load` handlers that reach into both modules. The duplication is 3 words; drift would be caught by either the `CHECK(role IN (...))` constraint or the `_classify` ValueError raise.

### Decisions from Plan 04 (nomad-tab-placeholder-panel, 2026-04-21)

- Accepted UE 5.6 nomad-tab floating-default dock over explicit right-side 420px placement. UE 5.6 FTabSpawnerEntry does not expose a stable `SetDefaultDockArea` API; enforcing right-side placement requires `FTabManager::FLayout` which needs a saved layout to already exist (chicken-and-egg at StartupModule time). Plan 12 revisits via `FLayoutExtender` when the panel gains persistent layout config.
- Named FName constants (Nyra::NyraChatTabId etc.) in a canonical header (Public/NyraChatTabNames.h) instead of inline FName literals — single source of truth shared by module registrar, unregistrar, Tools-menu FUIAction callback, and automation test.
- UToolMenus::RegisterStartupCallback (not direct ExtendMenu during StartupModule) — LoadingPhase PostEngineInit fires before the level editor menu tree is fully populated; the callback queues the extension until UToolMenus signals ready. Matches how FLevelEditorModule registers its own extensions.
- LOCTEXT namespace split: "NyraEditor" for module-owned strings (tab/menu labels), "NyraChatPanel" for widget-owned strings (panel copy). Plan 12 extends "NyraChatPanel" without touching module labels — separates localizer surfaces.
- Module-superset pattern locked: every plan that modifies NyraEditorModule.cpp MUST preserve prior plans' symbols and log lines verbatim (Plan 04 preserved Plan 03's IMPLEMENT_MODULE line and StartupModule log line per explicit acceptance criteria). New wiring only appends. Plans 10/12/13 inherit this contract.

### Blockers

None at initialization. Phase 0 legal emails will be in flight Week 1.

**Deferred verifications (host-platform gap):**

- UE 5.6 compile of NyraEditor/NyraRuntime modules — deferred to Windows CI (macOS host cannot run UBT/MSVC)
- `UnrealEditor-Cmd.exe ... Automation RunTests Nyra.Plugin` — deferred to Windows CI (macOS host cannot run UnrealEditor-Cmd.exe)
- Visual confirmation of NYRA in UE Plugins browser — deferred to Windows dev-machine first open
- `UnrealEditor-Cmd.exe ... Automation RunTests Nyra.;Quit` enumerates all 5 Nyra.* spec shells from Plan 01 — deferred to Windows CI (same constraint as above)
- Compile of NyraTestFixtures.cpp + 4 new Nyra.* spec .cpp files against UE 5.6 headers — deferred to Windows CI
- UE 5.6 compile of SNyraChatPanel + updated NyraEditorModule.cpp with new UE include surface (Framework/Docking/TabManager.h, Widgets/Docking/SDockTab.h, WorkspaceMenuStructure, WorkspaceMenuStructureModule, ToolMenus, Styling/AppStyle.h) — deferred to Windows CI (Plan 04)
- `UnrealEditor-Cmd.exe ... Automation RunTests Nyra.Panel.TabSpawner;Quit` exit 0 — deferred to Windows CI (Plan 04, VALIDATION 1-04-01 closes here)
- Manual verification: Tools -> NYRA -> Chat menu entry appears on editor launch + clicking it spawns a nomad tab rendering "NYRA — not yet connected" — deferred to Windows dev-machine first open (Plan 04)

**Plan 02 (python-pytest-scaffold): ZERO platform-gap deferrals.** Full pytest verification (`pytest tests/ -v` 9 skipped / 0 failed / 0 errors) was executed live on macOS Darwin with Python 3.13.5 and a dev venv pinned to pytest 8.3.3 + pytest-asyncio 0.24.0 + pytest-httpx 0.32.0 + httpx.

**Plan 06 (nyrahost-core-ws-auth-handshake): 3 platform-gap deferrals (all Windows-only):**

- `prebuild.ps1` authored and grep-verified for the required literals (`Get-Content $ManifestPath`, `ConvertFrom-Json`, `Get-FileHash $Path -Algorithm SHA256`, `Invoke-WebRequest`), but actually downloading python-build-standalone + llama.cpp zips + extracting to `Binaries/Win64/` is deferred to Windows dev machine or CI (PowerShell is not natively runnable on macOS).
- Runtime wheel cache population (`pip download -r requirements.lock -d Binaries/Win64/NyraHost/wheels/`) deferred to Windows dev machine; `ensure_venv` is unit-tested with empty wheels dir + empty requirements.lock to exercise idempotency + version-rebuild logic without depending on an actual wheel cache.
- Windows DACL lockdown in `handshake._apply_owner_only_dacl` is best-effort try/except wrapped with pywin32 import — runtime verification (actual SetFileSecurity on NTFS) deferred to Windows.

**Plan 06 positive result:** All 8 real tests (3 auth + 3 handshake + 2 bootstrap) ran LIVE on macOS Darwin Python 3.13.5 against production code (`python -m nyrahost` entrypoint with `asyncio` WS server, `secrets.compare_digest` token gate, `os.replace` atomic handshake write, `os.kill(pid, 0)` orphan detection). 8 passed / 0 failed / 0 errors. Plan 02's 6 downstream-owned Wave 0 stubs preserved skipped.

**Plan 07 (nyrahost-storage-attachments): ZERO platform-gap deferrals.** Pure Python stdlib (sqlite3 + hashlib + os + shutil + pathlib + dataclasses + typing) with zero new runtime deps beyond Plan 06's. 9 new tests (4 storage + 5 attachments) + Plan 06's 8 tests all run LIVE on macOS Darwin Python 3.13.5 → final full-suite state: 17 passed / 4 skipped / 0 failed / 0 errors in ~9 seconds. The cross-device-fallback path in `ingest_attachment` is exercised via `patch("nyrahost.attachments.os.link", side_effect=OSError("cross-device"))` — no second volume required. `os.link` + `shutil.copy2` both work natively on macOS APFS and Windows NTFS. Windows-specific caveat for later: `os.link` requires SeCreateSymbolicLinkPrivilege on some policies; `shutil.copy2` fallback handles it.

**Plan 10 (cpp-supervisor-ws-jsonrpc): 6 platform-gap deferrals (all Windows-only, consistent with Plans 01/03/04/05 posture):**

- UE 5.6 compile of FNyraJsonRpc + FNyraWsClient + FNyraHandshake + FNyraSupervisor + updated NyraEditorModule.cpp — deferred to Windows CI (macOS host cannot run UBT/MSVC).
- `UnrealEditor-Cmd.exe TestProject/TestProject.uproject -ExecCmds="Automation RunTests Nyra.Jsonrpc;Quit" -unattended -nopause -testexit="Automation Test Queue Empty"` exit 0 with ≥10 It blocks (VALIDATION 1-02-02) — deferred to Windows CI.
- `UnrealEditor-Cmd.exe ... Automation RunTests Nyra.Supervisor.RestartPolicy;Quit` exit 0 with 2 It blocks (VALIDATION 1-02-03) — deferred to Windows CI.
- `UnrealEditor-Cmd.exe ... Automation RunTests Nyra.Integration.HandshakeAuth;Quit` with `ENABLE_NYRA_INTEGRATION_TESTS=1` in the Target.cs (VALIDATION 1-02-01, opt-in) — deferred to Windows dev machine AFTER Plan 06's `prebuild.ps1` populates `Plugins/NYRA/Binaries/Win64/NyraHost/cpython/python.exe`.
- Manual editor launch verification: NyraHost process in Task Manager within 5s of editor start; `[NYRA] NyraEditor module starting` + `[NYRA] Spawning NyraHost: ...` in Output Log; clean editor close triggers `[NYRA] NyraHost exited code=0` + `[NYRA] WS closed code=1000 ...` — deferred to Windows dev-machine first open.
- Compile against UBT auto-generated NyraEditor include graph (UBT may flag a missing forward declaration) — deferred to Windows CI; grep-level verification confirms every UE header referenced by Plan 10 files exists in UE 5.6 (WebSocketsModule.h, IWebSocket.h, Misc/MonitoredProcess.h, Containers/Ticker.h, Serialization/JsonWriter.h, Policies/CondensedJsonPrintPolicy.h, Interfaces/IPluginManager.h).

**Plan 10 positive result:** All 28 PLAN.md grep acceptance literals pass across the 3 tasks. Build.cs already had every required dependency (WebSockets, Json, JsonUtilities, Projects) from Plan 03 — no NyraEditor.Build.cs change required. Plan 01's Wave 0 NyraJsonRpcSpec.cpp + NyraSupervisorSpec.cpp placeholders upgraded in place to real assertion-carrying specs; Plan 03's FNyraPluginModulesLoadSpec in NyraIntegrationSpec.cpp preserved verbatim while Plan 10 added the guarded FNyraIntegrationSpec HandshakeAuth LatentIt. NyraEditorModule.cpp additive-only update carries Plan 03's IMPLEMENT_MODULE line, Plan 04's tab/menu registration, and Plan 04's ShutdownModule unregister sequence verbatim — Plan 10's 5 new StartupModule lines spawn GNyraSupervisor AFTER tab registration per D-04; 5 new ShutdownModule lines RequestShutdown BEFORE tab unregister per D-05. PLUG-02 closed end-to-end: UE side can now spawn NyraHost, poll handshake, connect via WS, authenticate with first-frame session/authenticate, receive session/hello responses and chat/stream notifications, and gracefully shut down with KillTree fallback.

**Plan 09 (gemma-downloader): ZERO platform-gap deferrals.** All Plan 09 code paths exercised live on macOS Darwin Python 3.13.5:

- Downloader core (`downloader/progress.py` + `downloader/gemma.py`): pure-Python using `hashlib`, `pathlib`, `asyncio.to_thread`, and `httpx.AsyncClient` streaming. `Path.replace()` is atomic on both NTFS (Windows) and APFS (macOS) + ext4 (Linux).
- Tests (`tests/test_gemma_download.py`): `httpx.MockTransport` for deterministic 200/206/404/500 responses + Range-header parsing — NO real HuggingFace call. Pre-existing `.partial` file synthesized via `Path.write_bytes`; SHA256 verification uses stdlib `hashlib`. All 4 tests pass in ~0.07s.
- Download handler (`handlers/download.py`): asyncio + `websockets.server.ServerConnection` — same wire path as Plan 06's auth tests.
- app.py wiring: pure Python import + instantiation; no runtime behavioural change unless `build_and_run` is invoked (which requires a live WS server — covered by Plan 06's auth tests indirectly).
- Full suite: 34 passed / 0 skipped / 0 failed / 0 errors in ~16 seconds. Plan 02's Wave 0 stub pipeline FULLY LIQUIDATED — `test_gemma_download.py` was the last `@pytest.mark.skip`.

Windows-specific runtime caveats: `Path.replace()` on Windows fails with `PermissionError` if the destination is open in another process (unlikely for the .gguf but possible with antivirus); `GemmaDownloader.download` catches `OSError` in its outer loop. Windows Defender can scan the 3.16 GB GGUF on write, extending download+verify by ~30s. HuggingFace CDN returns 302→cloudfront.net; `follow_redirects=True` handles this. Gemma repo is gated (per ModelPins.h note) — Plan 13's UX surfaces the HF token remediation for the 401 path.

**Plan 08 (nyrahost-infer-spawn-ollama-sse): ZERO platform-gap deferrals.** All Plan 08 code paths exercised live on macOS Darwin Python 3.13.5:

- SSE parser (sse.py): pure-Python; zero platform deps.
- Ollama probe (ollama_probe.py): httpx.MockTransport drives all 5 detect cases deterministically, no running Ollama required.
- GPU probe (gpu_probe.py): `asyncio.create_subprocess_exec("nvidia-smi", "-L")` + `("vulkaninfo", "--summary")` both raise FileNotFoundError on macOS (caught silently) so `probe_gpu_backend()` returns `GpuBackend.CPU` — correct behaviour for the macOS dev host.
- llama-server spawn (llama_server.py): Windows-only `llama-server.exe` is mocked via a Python-script shim (`mock_llama.py` prints the canonical port-announcement line + blocks) wrapped by a platform-conditional `.bat` (Windows) or shebang-bash (POSIX) executable. Subprocess spawn + port capture via `PORT_RE` regex + pipe drain via background task all exercised identically to Windows.
- InferRouter.stream_chat: not directly exercised by a test (no end-to-end HTTP stream test in Plan 08); production integration lands at Plan 14 Ring 0 bench on Windows with real `llama-server.exe` + real Gemma GGUF.
- chat/send + chat/cancel handlers (handlers/chat.py): asyncio + `websockets.server.ServerConnection` — same wire path as Plan 06's auth tests, which already run LIVE on macOS. No new websocket test in Plan 08; end-to-end wire integration deferred to Plan 14.
- Full suite: 30 passed / 1 skipped / 0 failed / 0 errors (17 P06/P07 + 13 new P08 tests; Plan 09's test_gemma_download stub remains).

Windows-specific caveats for downstream plans: `llama-server.exe` path resolution via `llama_server_executable_path(plugin_binaries_dir, backend)` expects `<Plugin>/Binaries/Win64/NyraInfer/<cuda|vulkan|cpu>/llama-server.exe` — Plan 02's `prebuild.ps1` + assets-manifest.json populate these folders. `asyncio.subprocess.Process.terminate()` on Windows maps to TerminateProcess (not SIGTERM); `kill()` maps to the same API. `InferHandle.terminate`'s 5s-wait-then-kill contract works identically on both platforms. Windows Defender can scan the Gemma GGUF on first load, extending cold start to ~30s; `STARTUP_TIMEOUT_S = 60.0` gives headroom.

### Phase 1 pre-start checks (awaiting orchestrator or user)

- [ ] Confirm granularity=standard acceptance of 9 phases (Phase 0 is non-code; 8 code phases within standard band)
- [ ] Ready to kick off Phase 0 + Phase 1 in parallel

---

## Session Continuity

**Last session handoff:**

- Plan 01-10 (cpp-supervisor-ws-jsonrpc) executed end-to-end on main branch (sequential, no worktree). [shipped this session]
  - 3 atomic commits: 048d667 (feat Task 1 JSON-RPC + spec) · 475f613 (feat Task 2 Handshake + WsClient) · f89d772 (feat Task 3 Supervisor + wiring + specs)
  - 8 files created under TestProject/Plugins/NYRA/Source/NyraEditor/: Public/WS/FNyraJsonRpc.h + Private/WS/FNyraJsonRpc.cpp + Public/WS/FNyraWsClient.h + Private/WS/FNyraWsClient.cpp + Public/Process/FNyraHandshake.h + Private/Process/FNyraHandshake.cpp + Public/Process/FNyraSupervisor.h + Private/Process/FNyraSupervisor.cpp
  - 4 files modified: NyraEditorModule.cpp (additive superset of Plans 03+04 — GNyraSupervisor TUniquePtr wired into StartupModule/ShutdownModule) + NyraJsonRpcSpec.cpp (upgraded from Plan 01 Wave 0 stub to 10 It() blocks) + NyraSupervisorSpec.cpp (upgraded from Plan 01 Wave 0 stub to 2 It() blocks via FTestClockAdapter→INyraClock) + NyraIntegrationSpec.cpp (preserved Plan 03's FNyraPluginModulesLoadSpec, added guarded FNyraIntegrationSpec HandshakeAuth LatentIt)
  - SUMMARY at .planning/phases/01-plugin-shell-three-process-ipc/01-10-cpp-supervisor-ws-jsonrpc-SUMMARY.md
  - 2 Rule-1/Rule-2 auto-fixed deviations: (Rule 2) added bTestMode flag on FNyraSupervisor so SimulateCrashForTest does NOT invoke PerformSpawn (hermetic unit tests never launch python.exe); (Rule 1) simplified PLAN.md's bogus `FPlatformProcess::ComputerName() && !(LocalAppData).IsEmpty()` handshake-dir sentinel to `!LocalAppData.IsEmpty()` which directly matches docs/HANDSHAKE.md Primary-vs-Fallback contract.
  - 6 platform-gap deferrals logged (all Windows-only, consistent with Plans 01/03/04/05): UE 5.6 UBT/MSVC compile + 3 Automation test runs (Nyra.Jsonrpc / Nyra.Supervisor.RestartPolicy / Nyra.Integration.HandshakeAuth [opt-in]) + manual editor-launch visual verification + UBT auto-generated include-graph check. All 28 PLAN.md grep acceptance literals pass source-level.
  - PLUG-02 closed end-to-end on the UE side: editor can now spawn NyraHost, poll handshake with 50ms×1.5 exp backoff + 30s budget, connect via FWebSocketsModule to ws://127.0.0.1:<port>/, send session/authenticate as first frame, receive auth OK + session/hello responses, route chat/stream notifications, and gracefully shut down with 2s grace + Cancel(bKillTree=true) fallback. Plan 12 (chat panel) can now consume GNyraSupervisor->OnNotification / OnResponse / SendRequest / SendNotification to wire the Slate chat UI.

- Plan 01-09 (gemma-downloader) executed end-to-end on main branch (sequential, no worktree). [shipped previous session]
  - 3 atomic commits: c1d8b37 (test Task1 RED) · 4c5eac1 (feat Task1 GREEN) · 269c251 (feat Task2)
  - 4 files created under TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/: downloader/__init__.py, downloader/progress.py, downloader/gemma.py, handlers/download.py
  - 2 files modified: src/nyrahost/app.py (additive superset — imports json + GEMMA_FILENAME + GemmaSpec + DownloadHandlers; adds _load_gemma_spec helper; routes gemma_gguf_path through GEMMA_FILENAME constant; wires DownloadHandlers + register_request("diagnostics/download-gemma", ...) into build_and_run alongside Plan 08's chat/send + chat/cancel) + tests/test_gemma_download.py (Plan 02's LAST Wave 0 @pytest.mark.skip stub → 4 real passing tests)
  - SUMMARY at .planning/phases/01-plugin-shell-three-process-ipc/01-09-gemma-downloader-SUMMARY.md
  - ONE Rule 1 auto-fix: httpx.Timeout(connect=10, read=60) raises ValueError on httpx 0.32 — fix provides both default + all four explicit. Folded into Task 1 GREEN commit 4c5eac1.
  - ZERO platform-gap deferrals — httpx.MockTransport pattern (inherited from Plan 08) means every code path runs live on macOS without any real HuggingFace CDN or GitHub mirror call. Real 3.16 GB download integration validates at Plan 14 Ring 0 bench on Windows.
  - 4 real passing pytest tests (test_sha256_verify_and_range_resume + test_fallback_to_mirror_on_primary_404 + test_both_urls_fail_raises_and_emits_error_progress + test_progress_rate_limited) upgrade Plan 02's LAST Wave 0 stub; full pytest suite 34 passed / 0 skipped (!!!) / 0 failed / 0 errors in ~16s. Plan 02's Wave 0 stub pipeline FULLY LIQUIDATED.
  - PLUG-03 requirement further reinforced on the Python side (download path now provides the first-run UX gate for chat/send when neither GGUF nor Ollama is present). UE-side consumption lands in Plan 13 (first-run UX banners + diagnostics).

- Plan 01-08 (nyrahost-infer-spawn-ollama-sse) executed end-to-end on main branch (sequential, no worktree). [shipped previous session]
  - 5 atomic commits: 1dfd3bb (test Task1 RED) · 477950c (feat Task1 GREEN) · ff4d87e (test Task2 RED) · c83d57d (feat Task2 GREEN) · 9588d41 (feat Task3)
  - 9 files created under TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/: infer/__init__.py, infer/sse.py, infer/ollama_probe.py, infer/gpu_probe.py, infer/llama_server.py, infer/router.py, handlers/__init__.py, handlers/chat.py, app.py
  - 5 files modified: src/nyrahost/__main__.py (CLI args + build_and_run entry), src/nyrahost/server.py (session._ws = ws one-liner), tests/test_sse_parser.py + tests/test_ollama_detect.py + tests/test_infer_spawn.py (Wave 0 stubs → full test bodies)
  - SUMMARY at .planning/phases/01-plugin-shell-three-process-ipc/01-08-nyrahost-infer-spawn-ollama-sse-SUMMARY.md
  - ZERO Rule-1/2/3/4 deviations — plan content followed exactly (every module / test body / CLI arg / session wiring matches PLAN.md `<action>` blocks verbatim); 2 PLAN.md-mandated additive supersets landed cleanly (__main__.py appends --project-dir + --plugin-binaries-dir while preserving Plan 06's argparse + logging + cleanup_orphan_handshakes call ordering verbatim; server.py adds exactly ONE line `session._ws = ws` at the documented location)
  - ZERO platform-gap deferrals — Python-script mock llama shim + httpx.MockTransport + platform-conditional _wrapper_bat means every code path runs live on macOS; Plan 14 Ring 0 bench validates real llama-server.exe + real Gemma GGUF on Windows
  - 13 real passing pytest tests (5 SSE + 5 Ollama + 3 infer_spawn) upgrade Plan 02's last 3 infer Wave 0 stubs; full pytest suite 30 passed / 1 skipped (Plan 09's test_gemma_download remains) / 0 failed / 0 errors in ~18s on macOS Darwin Python 3.13.5
  - PLUG-03 requirement satisfied on the Python side (chat/send + chat/cancel + chat/stream wiring through InferRouter → llama-server or Ollama). UE-side PLUG-03 completion (cpp supervisor spawning nyrahost + ws/jsonrpc client) lands in Plan 10.

- Plan 01-07 (nyrahost-storage-attachments) executed end-to-end on main branch (sequential, no worktree). [shipped previous session]
  - 4 atomic commits (TDD RED→GREEN pairs, one per task): 5cb4c8f (test) · f6c29b5 (feat) · 89e1c49 (test) · 861aa35 (feat)
  - 2 files created under TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/ (storage.py, attachments.py)
  - 2 files modified: tests/test_storage.py and tests/test_attachments.py — both upgraded from Plan 02's Wave 0 @pytest.mark.skip stubs to real test bodies (4 + 5 = 9 new passing tests)
  - SUMMARY at .planning/phases/01-plugin-shell-three-process-ipc/01-07-nyrahost-storage-attachments-SUMMARY.md
  - ZERO Rule-1/2/3/4 deviations — plan content was followed exactly (storage.py + attachments.py match PLAN.md `<action>` blocks verbatim; test bodies match PLAN.md spec verbatim)
  - ZERO platform-gap deferrals — pure Python stdlib, full pytest verification live on macOS Darwin Python 3.13.5. Full suite final state: 17 passed / 4 skipped / 0 failed / 0 errors (9 new P07 tests + 8 preserved P06 tests; 4 Wave 0 stubs for Plans 08/09 remain skipped)
  - CHAT-01 requirement satisfied on the Python side (sessions.db per-project persistence + content-addressed attachment store). UE-side CHAT-01 completion (chat panel reading/writing via WS) lands in Plans 10 + 12

- Plan 01-06 (nyrahost-core-ws-auth-handshake) executed end-to-end on main branch (sequential, no worktree). [shipped previous session]
  - 6 atomic commits (TDD RED→GREEN pairs, one per task): 4400ae0 (test) · e890a52 (feat) · 9cef418 (test) · ef91a6f (feat) · bbea561 (test) · 125ce46 (feat)
  - 11 files created under TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/ + TestProject/Plugins/NYRA/Source/NyraHost/requirements.lock + TestProject/Plugins/NYRA/prebuild.ps1
  - 4 files modified: pyproject.toml (appended [project].dependencies + [tool.setuptools.packages.find]), 3 test files upgraded from @pytest.mark.skip stubs to real tests, TestProject/.gitignore (added *.egg-info/, build/, dist/)
  - SUMMARY at .planning/phases/01-plugin-shell-three-process-ipc/01-06-nyrahost-core-ws-auth-handshake-SUMMARY.md
  - 2 auto-fixed deviations: Rule 1 (OverflowError in _pid_running on macOS for test-deliberate huge PID) + Rule 3 (egg-info/build/dist gitignore — matches Plan 02 Python cache-ignore discipline)
  - 3 platform-gap deferrals logged (all Windows-only): prebuild.ps1 execution, wheel cache population, DACL lockdown runtime verification
  - 8 real pytest tests pass live on macOS Darwin Python 3.13.5 + websockets 16.0 + structlog 25.4.0 + pydantic 2.12.4 (dev machine resolves latest compatible; requirements.lock pins production at 12.0/24.1.0/2.7.4)
  - NyraServer.register_request / register_notification extension points land — Plans 07/08/09/10 can now bind their method surfaces without modifying the first-frame auth gate

- Plan 01-04 (nomad-tab-placeholder-panel) executed end-to-end on main branch (sequential, prior session). [shipped previous session]
  - 3 atomic commits: 224ffa7 · 628de82 · cf3ab9c
  - 3 files created (NyraChatTabNames.h, SNyraChatPanel.h, SNyraChatPanel.cpp) + 2 modified (NyraEditorModule.cpp additive superset of Plan 03, NyraPanelSpec.cpp additive superset of Plan 01)
  - SUMMARY at .planning/phases/01-plugin-shell-three-process-ipc/01-04-nomad-tab-placeholder-panel-SUMMARY.md
  - ZERO Rule-1/2/3/4 deviations — plan content was followed exactly. 2 PLAN.md-mandated non-breaking supersets (NyraEditorModule.cpp preserves Plan 03's IMPLEMENT_MODULE line and StartupModule log line verbatim per Task 2 acceptance criteria; NyraPanelSpec.cpp preserves Plan 01's BEGIN_DEFINE_SPEC signature + #if WITH_AUTOMATION_TESTS guard + Plan 12 placeholder comments).
  - 4 platform-gap deferrals logged (UE 5.6 UBT/MSVC compile of the new Slate + ToolMenus surface; UnrealEditor-Cmd.exe Nyra.Panel.TabSpawner run; Tools -> NYRA -> Chat menu visual confirmation; nomad tab spawn manual verification — all Windows-only).
  - All 29 grep-level acceptance literals across Tasks 1+2+3 pass.

- Plan 01-02 (python-pytest-scaffold) executed end-to-end on main branch (sequential, no worktree). [shipped previous session]
  - 2 atomic commits: 1465d8d · 0cbfe95
  - 14 files created under TestProject/Plugins/NYRA/Source/NyraHost/ + 1 modified (TestProject/.gitignore — Python dev-tooling ignores appended)
  - SUMMARY at .planning/phases/01-plugin-shell-three-process-ipc/01-02-python-pytest-scaffold-SUMMARY.md
  - 1 Rule-3 deviation: added Python dev-tooling ignores (`__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.venv-dev/`, `*.py[cod]`) to Plan 03's `TestProject/.gitignore` so Python plans (06/07/08/09) can't leak generated caches
  - ZERO platform-gap deferrals — full `pytest tests/ -v` verification ran live on macOS Darwin with Python 3.13.5 + dev venv (pytest 8.3.3 / pytest-asyncio 0.24.0 / pytest-httpx 0.32.0 / httpx)
  - 9 tests collected, 9 skipped, 0 failed, 0 errors, exit 0

- Plan 01-01 (cpp-automation-scaffold) executed end-to-end on main branch (sequential, no worktree). [shipped previous session]
  - 2 atomic commits: 35ed37d · ca182ba
  - 6 files created + 1 modified under TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/
  - SUMMARY at .planning/phases/01-plugin-shell-three-process-ipc/01-01-cpp-automation-scaffold-SUMMARY.md
  - 2 non-breaking reconciliations with Plan 03: (a) NyraTestFixtures.h stub upgraded in place to full Nyra::Tests namespace (superset — Plan 03 symbols preserved); (b) NyraIntegrationSpec.cpp left untouched because Plan 03's version already satisfied every Plan 01 acceptance literal AND hosts FNyraPluginModulesLoadSpec (PLUG-01)
  - 3 platform-gap verification deferrals logged (host=macOS, target=Windows — UE 5.6 UBT/MSVC + UnrealEditor-Cmd.exe unavailable)

- Plan 01-03 (uplugin-two-module-scaffold) executed end-to-end on main branch (sequential, no worktree). [shipped previous session]
  - 5 atomic commits: c650c84 · 1bbf4e4 · 2dd106c · 106ed82 · 2dc2d32
  - 18 files created under TestProject/, TestProject/Plugins/NYRA/, and docs/
  - SUMMARY at .planning/phases/01-plugin-shell-three-process-ipc/01-03-uplugin-two-module-scaffold-SUMMARY.md

### Next session

1. Execute Plan 01-11 (cpp-markdown-parser) — FNyraMarkdown UE C++ incremental streaming markdown renderer (Slate widgets) that consumes chat/stream delta text and produces renderable blocks (paragraphs, fenced code, bullets, emphasis). Closes VALIDATION 1-03-* (Nyra.Markdown.* spec).
2. Continue through Phase 01 Wave 3 plans (01-12 chat panel streaming integration [wires SNyraChatPanel to GNyraSupervisor OnNotification + SendRequest], 01-12b history drawer [Saved/NYRA/sessions.db reader from Plan 07], 01-13 first-run UX banners + diagnostics [consumes Plan 09's diagnostics/download-gemma surface], 01-14 ring0 harness, 01-15 ring0 run + commit).

**Files-on-disk checkpoint (all present):**

- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md` ← written in this session
- `.planning/STATE.md` ← written in this session
- `.planning/config.json`
- `.planning/research/SUMMARY.md`
- `.planning/research/STACK.md`
- `.planning/research/FEATURES.md`
- `.planning/research/ARCHITECTURE.md`
- `.planning/research/PITFALLS.md`

---

*State initialized: 2026-04-21 after roadmap creation*
*Last update: 2026-04-22 after Plan 01-08 execution*
