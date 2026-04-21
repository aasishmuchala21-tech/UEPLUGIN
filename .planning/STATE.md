---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: milestone
current_phase: 01
current_plan: 4
status: executing
last_updated: "2026-04-21T21:07:00Z"
progress:
  total_phases: 9
  completed_phases: 0
  total_plans: 16
  completed_plans: 1
  percent: 6
---

# Project State: NYRA

**Last Updated:** 2026-04-21 (Plan 01-03 completed)

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
**Current Plan:** 4
**Status:** Executing Phase 01 (Plan 03 complete — two-module scaffold on disk)

**Progress (v1):**

```text
[..................] 0/9 phases complete (Phases 0-8), Phase 01 in progress (1/15 plans complete, Plan 03 shipped)
```

**Plans completed in Phase 01:**

- [x] Plan 03 — UPlugin two-module scaffold (5 tasks, 5 commits, SUMMARY on disk)
- [ ] Plan 01 — C++ automation scaffold (Wave 0, pending — overlaps with Plan 03 Tests/; partial stub written by Plan 03 Rule 3 deviation)
- [ ] Plan 02 — Python pytest scaffold (Wave 0, pending)
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

### Blockers

None at initialization. Phase 0 legal emails will be in flight Week 1.

**Deferred verifications (host-platform gap):**

- UE 5.6 compile of NyraEditor/NyraRuntime modules — deferred to Windows CI (macOS host cannot run UBT/MSVC)
- `UnrealEditor-Cmd.exe ... Automation RunTests Nyra.Plugin` — deferred to Windows CI (macOS host cannot run UnrealEditor-Cmd.exe)
- Visual confirmation of NYRA in UE Plugins browser — deferred to Windows dev-machine first open

### Phase 1 pre-start checks (awaiting orchestrator or user)

- [ ] Confirm granularity=standard acceptance of 9 phases (Phase 0 is non-code; 8 code phases within standard band)
- [ ] Ready to kick off Phase 0 + Phase 1 in parallel

---

## Session Continuity

**Last session handoff:**

- Plan 01-03 (uplugin-two-module-scaffold) executed end-to-end on main branch (sequential, no worktree).
  - 5 atomic commits: c650c84 · 1bbf4e4 · 2dd106c · 106ed82 · 2dc2d32
  - 18 files created under TestProject/, TestProject/Plugins/NYRA/, and docs/
  - SUMMARY at .planning/phases/01-plugin-shell-three-process-ipc/01-03-uplugin-two-module-scaffold-SUMMARY.md
  - 1 auto-fix deviation: minimal Rule-3 NyraTestFixtures.h stub added because Plan 01 has not yet executed
  - 5 platform-gap verification deferrals logged (host=macOS, target=Windows)

### Next session

1. Execute Plan 01-01 (cpp-automation-scaffold, Wave 0) — replaces Plan 03's Rule-3 NyraTestFixtures.h stub with the full Nyra::Tests fixture namespace
2. Execute Plan 01-02 (python-pytest-scaffold, Wave 0)
3. Continue through Phase 01 Wave 1/2/3 plans (01-04 nomad-tab, 01-05 specs, 01-06 nyrahost-core, etc.)

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
*Last update: 2026-04-21 after Plan 01-03 execution*
