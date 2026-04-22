---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: milestone
current_phase: 01
current_plan: 6
status: executing
last_updated: "2026-04-22T05:42:50Z"
progress:
  total_phases: 9
  completed_phases: 0
  total_plans: 16
  completed_plans: 6
  percent: 37
---

# Project State: NYRA

**Last Updated:** 2026-04-22 (Plan 01-06 completed)

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
Plan: 6 of 16 (next to execute)
**Milestone:** v1 (Fab launch)
**Current Phase:** 01
**Current Plan:** 6 complete (next = Wave 2 continuation: Plan 07)
**Status:** Executing Phase 01 — Wave 1 COMPLETE (Plans 01, 02, 03, 04, 05); Wave 2 IN PROGRESS (Plan 06 done; Plans 07–10 next)

**Progress (v1):**

```text
[████░░░░░░] 37% — 0/9 phases complete (Phases 0-8), Phase 01 Wave 1+Plan 06 shipped (6/16 plans: 01 + 02 + 03 + 04 + 05 + 06)
```

**Plans completed in Phase 01:**

- [x] Plan 03 — UPlugin two-module scaffold (5 tasks, 5 commits, SUMMARY on disk)
- [x] Plan 01 — C++ automation scaffold (Wave 0, 2 tasks, 2 commits, SUMMARY on disk — upgraded Plan 03 Rule-3 NyraTestFixtures.h stub to full Nyra::Tests namespace; added 4 new spec shells + README)
- [x] Plan 02 — Python pytest scaffold (Wave 0, 2 tasks, 2 commits, SUMMARY on disk — pyproject.toml + requirements-dev.lock + conftest.py with 4 fixtures + 9 @pytest.mark.skip test shells + README; pytest verified live on macOS host 9 skipped/0 failed/0 errors)
- [x] Plan 04 — Nomad tab placeholder panel (Wave 1, 3 tasks, 3 commits, SUMMARY on disk — Nyra::NyraChatTabId + SNyraChatPanel placeholder + Tools > NYRA > Chat menu wiring + Nyra.Panel.TabSpawner automation It block closing VALIDATION 1-04-01)
- [x] Plan 05 — Specs handshake + JSON-RPC + model pins (Wave 1, 2 tasks, 2 commits, SUMMARY on disk — docs/HANDSHAKE.md + docs/JSONRPC.md + docs/ERROR_CODES.md canonical wire specs; ModelPins.h/.cpp + assets-manifest.json with live-resolved python-build-standalone + Gemma 3 4B GGUF + llama.cpp b8870 pins)
- [x] Plan 06 — NyraHost core WS + auth + handshake (Wave 2, 3 tasks TDD=true, 6 commits [3 RED + 3 GREEN], SUMMARY on disk — 8-module `nyrahost` Python package [`bootstrap`, `config`, `logging_setup`, `handshake`, `jsonrpc`, `server`, `session`, `__main__`] + `requirements.lock` + `TestProject/Plugins/NYRA/prebuild.ps1` + 8 real passing pytest tests [3 auth + 3 handshake + 2 bootstrap] upgrading Plan 02's Wave 0 stubs; `python -m nyrahost` binds `127.0.0.1:<ephemeral-port>`, writes atomic handshake, enforces first-frame `session/authenticate` gate with WS close 4401 on token mismatch; `NyraServer.register_request` / `register_notification` extension points land for Plans 07/08/09)
- [ ] Plan 07 onwards (Wave 2 continuation)

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

### Phase 1 pre-start checks (awaiting orchestrator or user)

- [ ] Confirm granularity=standard acceptance of 9 phases (Phase 0 is non-code; 8 code phases within standard band)
- [ ] Ready to kick off Phase 0 + Phase 1 in parallel

---

## Session Continuity

**Last session handoff:**

- Plan 01-06 (nyrahost-core-ws-auth-handshake) executed end-to-end on main branch (sequential, no worktree). [shipped this session]
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

1. Execute Plan 01-07 (nyrahost-storage-attachments) — SQLite sessions.db schema + migrations, attachments hash-and-hardlink, sessions/list + sessions/load method handlers mounted via NyraServer.register_request. Wave 0 stubs for test_storage.py + test_attachments.py upgrade in place per the Plan 06 TDD RED/GREEN pattern.
2. Continue through Phase 01 Wave 2/3 plans (01-08 infer spawn + Ollama detect + SSE parser, 01-09 gemma downloader, 01-10 cpp supervisor + ws/jsonrpc, 01-11 markdown parser, 01-12 chat panel streaming, 01-12b history drawer, 01-13 first-run UX, 01-14 ring0 harness, 01-15 ring0 run + commit).

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
*Last update: 2026-04-21 after Plan 01-04 execution*
