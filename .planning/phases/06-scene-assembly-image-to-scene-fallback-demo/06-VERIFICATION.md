# Phase 6 Exit Gate: Scene Assembly + Image-to-Scene (Fallback Launch Demo)

**Phase:** 06-scene-assembly-image-to-scene-fallback-demo
**Status:** `partial` (architecturally complete; operator run pending)
**Gate Date:** 2026-05-08
**Plans Executed:** 06-00, 06-01, 06-02, 06-03, 06-04
**Source Commits:** 5 plans with full task breakdowns
**Wave Structure:** 4 waves (0 foundation, 1 SCENE-01, 2 DEMO-01 assembly, 3 integration tests, 4 canary)

---

## Purpose

Phase 6 exit gate validates DEMO-01 end-to-end image-to-scene assembly and SCENE-01 lighting authoring. These are the foundation that enables Phase 7's video-to-matched-shot launch demo. If Phase 7 slips, DEMO-01 is the v1-launchable fallback.

---

## Success Criteria

| SC | Claim | Evidence Source | Status | Notes |
|----|-------|----------------|--------|-------|
| **SC#1** | DEMO-01 prefers user asset library first, generates missing via Meshy/ComfyUI | 06-02 asset_fallback_chain.py, test_scene_assembly_e2e.py | PLAN-COMPLETE | Library-first verified by unit test |
| **SC#2** | SCENE-01 handles all 7 light types + 5 atmosphere/post types from NL AND reference images | 06-01 lighting_tools.py, scene_llm_parser.py, test_lighting_integration.py | PLAN-COMPLETE | All types present; parse_from_image for "match this image's mood" |
| **SC#3** | DEMO-01 passes random-reference daily test -- no demo mode flag | 06-04 demo01_canary.py, test_demo01_canary.py | PLAN-COMPLETE | Canary uses same code paths users run; exit 0 (PASS) or 2 (PARTIAL) |
| **SC#4** | DEMO-01 is v1-launchable state | All 5 plans + canary verdict | PLAN-COMPLETE | Full pipeline delivers 5-20 actors + materials + lighting |

---

## Plan Completion Matrix

| Plan | Wave | Type | Status | Key Files |
|------|------|------|--------|-----------|
| 06-00 | 0 | Foundation | COMPLETE | scene_types.py, asset_pool.py, scene_orchestrator.py |
| 06-01 | 1 | SCENE-01 Lighting | COMPLETE | lighting_tools.py, scene_llm_parser.py, SNyraLightingSelector.cpp |
| 06-02 | 2 | DEMO-01 Assembly | COMPLETE | scene_assembler.py, assembly_tools.py, asset_fallback_chain.py, 5 Slate UI components |
| 06-03 | 3 | Integration Tests | COMPLETE | test_scene_assembly_e2e.py (10 tests), test_lighting_integration.py (8 tests) |
| 06-04 | 4 | Canary + Gate | COMPLETE | NyraToolCatalogCanary.cpp (Phase 6: 4 tools), demo01_canary.py, test_demo01_canary.py (10 tests) |

---

## Phase-Exit Verdict

```
PHASE_6_GATE: partial
```

All 5 plans authored with full task breakdowns. All 4 SCs PLAN-COMPLETE. Operator run pending.

**Verdict criteria:** `pass` requires Nyra.Dev.ToolCatalogCanary ALL PASS (23 tools) AND canary exit 0 (PASS).
Operator verification protocol:

```bash
# 1. NyraToolCatalogCanary
Nyra.Dev.ToolCatalogCanary  # UE editor console

# 2. Canary with services
MESHY_API_KEY=your_key COMFYUI_HOST=127.0.0.1:8188 \
  python -m nyrahost.canary.demo01_canary --random --verbose
# Expected: exit 0 (PASS) or 2 (PARTIAL)

# 3. Cold-start reliability
MESHY_API_KEY=invalid_key COMFYUI_HOST=127.0.0.1:99999 \
  python -m nyrahost.canary.demo01_canary --random
# Expected: exit 2 (PARTIAL) -- never blocks

# 4. Unit tests
python -m pytest tests/test_scene_types.py tests/test_asset_pool.py \
  tests/test_demo01_canary.py tests/test_scene_assembly_e2e.py \
  tests/test_lighting_integration.py -x -q
# Expected: 44 tests passing
```

---

## Tool Registration Matrix

| Tool | Plan | Requirement | Status |
|------|------|-------------|--------|
| nyra_lighting_authoring | 06-01 | SCENE-01 | PLAN-COMPLETE |
| nyra_lighting_dry_run_preview | 06-01 | SCENE-01 | PLAN-COMPLETE |
| nyra_assemble_scene | 06-02 | DEMO-01 | PLAN-COMPLETE |
| nyra_scene_log | 06-02 | DEMO-01 | PLAN-COMPLETE |

**Phase 6 tools: 4 | Phase 5 tools: 6 (DEPENDENCY_PENDING) | Phase 4 tools: 13 | Total: 23**

---

*Phase 6 gate verdict: `partial` -- architecturally complete; operator run pending before `pass`*
