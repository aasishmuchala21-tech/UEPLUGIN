---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: milestone
current_phase: 01
current_plan: 3
status: executing
last_updated: "2026-04-21T17:31:14Z"
progress:
  total_phases: 9
  completed_phases: 0
  total_plans: 16
  completed_plans: 3
  percent: 19
---

# Project State: NYRA

**Last Updated:** 2026-04-21 (Plan 01-02 completed)

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
Plan: 4 of 16 (next to execute)
**Milestone:** v1 (Fab launch)
**Current Phase:** 01
**Current Plan:** 3 (incrementing toward 04-nomad-tab)
**Status:** Executing Phase 01 (Plans 01, 02, 03 complete — Wave 0 C++ + Python test scaffolds and two-module scaffold all on disk; Plan 04 nomad-tab next)

**Progress (v1):**

```text
[██░░░░░░░░] 19% — 0/9 phases complete (Phases 0-8), Phase 01 in progress (3/16 plans complete, Plans 01 + 02 + 03 shipped)
```

**Plans completed in Phase 01:**

- [x] Plan 03 — UPlugin two-module scaffold (5 tasks, 5 commits, SUMMARY on disk)
- [x] Plan 01 — C++ automation scaffold (Wave 0, 2 tasks, 2 commits, SUMMARY on disk — upgraded Plan 03 Rule-3 NyraTestFixtures.h stub to full Nyra::Tests namespace; added 4 new spec shells + README)
- [x] Plan 02 — Python pytest scaffold (Wave 0, 2 tasks, 2 commits, SUMMARY on disk — pyproject.toml + requirements-dev.lock + conftest.py with 4 fixtures + 9 @pytest.mark.skip test shells + README; pytest verified live on macOS host 9 skipped/0 failed/0 errors)
- [ ] Plan 04 onwards

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

| Phase | Plan | Name                         | Tasks | Files | Duration | Commits                                           |
| ----- | ---- | ---------------------------- | ----- | ----- | -------- | ------------------------------------------------- |
| 01    | 03   | uplugin-two-module-scaffold  | 5     | 18    | ~28min   | c650c84 · 1bbf4e4 · 2dd106c · 106ed82 · 2dc2d32   |
| 01    | 01   | cpp-automation-scaffold      | 2     | 7     | ~34min   | 35ed37d · ca182ba                                 |
| 01    | 02   | python-pytest-scaffold       | 2     | 14    | ~9min    | 1465d8d · 0cbfe95                                 |

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

### Blockers

None at initialization. Phase 0 legal emails will be in flight Week 1.

**Deferred verifications (host-platform gap):**

- UE 5.6 compile of NyraEditor/NyraRuntime modules — deferred to Windows CI (macOS host cannot run UBT/MSVC)
- `UnrealEditor-Cmd.exe ... Automation RunTests Nyra.Plugin` — deferred to Windows CI (macOS host cannot run UnrealEditor-Cmd.exe)
- Visual confirmation of NYRA in UE Plugins browser — deferred to Windows dev-machine first open
- `UnrealEditor-Cmd.exe ... Automation RunTests Nyra.;Quit` enumerates all 5 Nyra.* spec shells from Plan 01 — deferred to Windows CI (same constraint as above)
- Compile of NyraTestFixtures.cpp + 4 new Nyra.* spec .cpp files against UE 5.6 headers — deferred to Windows CI

**Plan 02 (python-pytest-scaffold): ZERO platform-gap deferrals.** Full pytest verification (`pytest tests/ -v` 9 skipped / 0 failed / 0 errors) was executed live on macOS Darwin with Python 3.13.5 and a dev venv pinned to pytest 8.3.3 + pytest-asyncio 0.24.0 + pytest-httpx 0.32.0 + httpx.

### Phase 1 pre-start checks (awaiting orchestrator or user)

- [ ] Confirm granularity=standard acceptance of 9 phases (Phase 0 is non-code; 8 code phases within standard band)
- [ ] Ready to kick off Phase 0 + Phase 1 in parallel

---

## Session Continuity

**Last session handoff:**

- Plan 01-02 (python-pytest-scaffold) executed end-to-end on main branch (sequential, no worktree). [shipped this session]
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

1. Execute Plan 01-04 (nomad-tab-placeholder-panel, Wave 1) — first UI-layer C++ plan; registers the `NyraChatTab` tab spawner and lands the empty SDockTab shell. The Plan 01 NyraPanelSpec.cpp is ready to accept the TabSpawner It() block.
2. Continue through Phase 01 Wave 1/2/3 plans (01-05 specs, 01-06 nyrahost-core, etc.)

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
*Last update: 2026-04-21 after Plan 01-02 execution*
