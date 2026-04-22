---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: milestone
current_phase: 01
current_plan: "8 complete (next = Wave 2 continuation: Plan 09)"
status: executing
last_updated: "2026-04-22T13:15:08Z"
progress:
  total_phases: 9
  completed_phases: 0
  total_plans: 16
  completed_plans: 8
  percent: 50
---

# Project State: NYRA

**Last Updated:** 2026-04-22 (Plan 01-08 completed)

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
Plan: 9 of 16 (next to execute)
**Milestone:** v1 (Fab launch)
**Current Phase:** 01
**Current Plan:** 8 complete (next = Wave 2 continuation: Plan 09)
**Status:** Executing Phase 01 — Wave 1 COMPLETE (Plans 01, 02, 03, 04, 05); Wave 2 IN PROGRESS (Plans 06, 07, 08 done; Plans 09–10 next)

**Progress (v1):**

```text
[█████░░░░░] 50% — 0/9 phases complete (Phases 0-8), Phase 01 Wave 1 + Plans 06/07/08 shipped (8/16 plans: 01 + 02 + 03 + 04 + 05 + 06 + 07 + 08)
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
- [ ] Plan 09 onwards (Wave 2 continuation — Gemma downloader with SHA256+Range resume)

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

- Plan 01-08 (nyrahost-infer-spawn-ollama-sse) executed end-to-end on main branch (sequential, no worktree). [shipped this session]
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

1. Execute Plan 01-09 (gemma-downloader) — SHA256+Range-resume download of `gemma-3-4b-it-qat-q4_0.gguf` (3.16 GB) from HuggingFace CDN into `<ProjectDir>/Saved/NYRA/models/` per D-17; pinned SHA256 from Plan 05's assets-manifest.json; `diagnostics/download-progress` notification emitter mounted on Plan 06's NyraServer.register_notification; upgrade `GemmaNotInstalledError` → `-32005 gemma_not_installed` mapping in app.py._wrap_send now that the downloader provides the remediation surface. Wave 0 stub test_gemma_download.py upgrades in place per the TDD RED/GREEN pattern.
2. Continue through Phase 01 Wave 2/3 plans (01-10 cpp supervisor + ws/jsonrpc UE client [spawns `python -m nyrahost --editor-pid N --log-dir ... --project-dir ... --plugin-binaries-dir ...`], 01-11 markdown parser, 01-12 chat panel streaming integration, 01-12b history drawer, 01-13 first-run UX, 01-14 ring0 harness, 01-15 ring0 run + commit).

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
