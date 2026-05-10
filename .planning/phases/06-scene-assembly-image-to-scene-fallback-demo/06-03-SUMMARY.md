---
phase: 06-scene-assembly-image-to-scene-fallback-demo
plan: "06-03"
subsystem: integration-tests
tags: [demo-01, scene-01, e2e, cold-start, mocked-router, asset-fallback, regression]

requires:
  - phase: "06-00"
    provides: SceneBlueprint / ActorSpec / MaterialSpec / LightingParams / AssetPool / SceneAssemblyOrchestrator
  - phase: "06-01"
    provides: LightingLLMParser, LightingAuthoringTool, LightingDryRunTool, _PRESETS
  - phase: "06-02"
    provides: AssetFallbackChain, SceneAssembler, AssembleSceneTool
provides:
  - test_scene_assembly_e2e.py (8 tests; full DEMO-01 pipeline + 5 cold-start cases)
  - test_lighting_integration.py (6 tests; SCENE-01 parser <-> tool handshake + assembler integration)
  - conftest.py Phase 6 fixtures (sample_reference_image, fake_meshy_tool, fake_comfyui_tool)
affects: [06-04-canary, 07-00-foundation]

key-files:
  created:
    - "TestProject/Plugins/NYRA/Source/NyraHost/tests/test_scene_assembly_e2e.py"
    - "TestProject/Plugins/NYRA/Source/NyraHost/tests/test_lighting_integration.py"
  modified:
    - "TestProject/Plugins/NYRA/Source/NyraHost/tests/conftest.py (additive Phase 6 fixture block)"

key-decisions:
  - "sample_reference_image fixture writes a JPEG-magic-prefixed byte sequence (not a full encoded image). The Phase 6 pipeline only needs Path.exists() for validation; image decoding is the LLM provider's concern. Initial fixture used a base64 1x1 JPEG that decoded incorrectly across machines - simplified to magic-prefix bytes for portability."
  - "All cold-start tests use the synchronous assembler.assemble path with the stub blueprint, so they exercise the placeholder fallback chain even when the LLM is mocked or absent. This is the pattern the Plan 06-04 canary will reuse for offline assertions."
  - "test_all_phase_6_modules_import_together is a deliberately cheap canary against circular imports. If a future refactor inverts the dependency direction (e.g. moves SceneBlueprint into scene_assembler.py), this test catches it first."

requirements-completed: [DEMO-01, SCENE-01]

duration: ~10min
completed: 2026-05-10
---

# Phase 06 Plan 03: Integration Tests - Summary

**14/14 Phase 6 integration tests green: full DEMO-01 pipeline (8 e2e + cold-start cases), SCENE-01 parser/tool handshake (6 cases). All cold-start failure modes (Meshy down, Meshy errors, ComfyUI down, router raises, no router at all) verified to deliver a complete scene via the placeholder chain.**

## Performance

- **Duration:** ~10 min inline
- **Tasks:** 3 of 3 complete
- **Files created:** 2 test files; 1 conftest fixture-block append

## Verification

```text
cd TestProject/Plugins/NYRA/Source/NyraHost
python -m pytest tests/test_scene_assembly_e2e.py tests/test_lighting_integration.py -v
================================= 14 passed in 0.09s =================================
```

## Truths Established

- End-to-end smoke test passes: image -> blueprint -> 4 actors placed + 2 materials applied + lighting configured. ✅
- Cold-start reliability verified across 5 failure modes: Meshy unavailable, Meshy errors, ComfyUI unavailable, router exception, no router. ✅
- All Phase 6 components load together with no circular imports. ✅
- DEMO-01 + SCENE-01 are both verifiable via automated tests. ✅

## Status

✅ **Plan 06-03 COMPLETE.** 14/14 tests green. Wave 4 (06-04 canary) can now be authored against a verified-green baseline.
