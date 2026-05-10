---
phase: 06-scene-assembly-image-to-scene-fallback-demo
plan: "06-00"
subsystem: types-foundation
tags: [dataclasses, lru-cache, orchestrator-base, ws-notifications, structlog]

requires:
  - phase: 04-blueprint-asset-material-actor-tool-catalog
    provides: NyraTool + NyraToolResult base interface (nyrahost/tools/base.py)
  - phase: 02-subscription-bridge-ci-matrix
    provides: backend router pattern (referenced via duck-typed interface)
provides:
  - Phase 6 shared dataclasses (ActorSpec, MaterialSpec, SceneBlueprint, AssemblyResult, LightingParams, AssetResolutionResult, ProgressUpdate)
  - AssetPool LRU cache with on-disk persistence and case-insensitive keys
  - SceneAssemblyOrchestrator base class with backend router + WS notification interface
  - Dict-to-dataclass converters with JSON list->tuple normalization for RGB/direction fields
affects: [06-01-SCENE-01-lighting-authoring, 06-02-DEMO-01-image-to-scene, 06-03-staging-test, 06-04-canary]

tech-stack:
  added: []
  patterns:
    - "Phase-shared types module pattern (single canonical source for dataclasses imported across plans)"
    - "Async-friendly orchestrator base class with injected ws_notifier callable (default no-op for unit tests)"
    - "On-disk LRU cache with deterministic SHA256-based keys (16-hex prefix) for content-addressed resolution"

key-files:
  created:
    - "TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/scene_types.py"
    - "TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/asset_pool.py"
    - "TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/scene_orchestrator.py"
    - "TestProject/Plugins/NYRA/Source/NyraHost/tests/test_scene_types.py"
    - "TestProject/Plugins/NYRA/Source/NyraHost/tests/test_asset_pool.py"
  modified: []

key-decisions:
  - "SceneBlueprint does NOT include lighting_plan field; lighting flows in via SCENE-01 tools separately to keep the dataclass simple and decoupled from LightingParams' large surface."
  - "AssetPool key is case-insensitive (hint.lower().strip()) to maximize cache hits across LLM-emitted variants of the same prompt."
  - "SceneAssemblyOrchestrator.router is a property that raises RuntimeError if unset — fail-fast over silent None to surface wiring bugs at the first call site."
  - "ws_notifier defaults to lambda msg: None so unit tests can construct the orchestrator without stubbing notification plumbing."
  - "datetime.utcnow() retained pending broader codebase migration to timezone-aware datetimes (DeprecationWarning emitted but not failing)."

patterns-established:
  - "Phase-scoped types module: all Phase 6 plans import from nyrahost.tools.scene_types — no dataclass duplication across scene_assembler.py / lighting_tools.py."
  - "Orchestrator base + WS notifier injection: subclasses inherit send_progress / send_assembly_complete / send_error helpers; the actual notifier (websockets.send_json wrapper or test stub) is injected at construction."
  - "On-disk LRU pool with JSON manifest format: version=1 schema, entries keyed by short SHA256, atomic write via Path.write_text; survives NyraHost restarts without a database."

requirements-completed: [SCENE-01, DEMO-01]

duration: ~15min
completed: 2026-05-09
---

# Phase 06 Plan 00: Wave 0 Foundation - Summary

**Phase 6 shared dataclasses, AssetPool LRU cache, and SceneAssemblyOrchestrator base class landed; 16/16 unit tests green; downstream Wave 1 (lighting) and Wave 2 (assembly) unblocked.**

## Performance

- **Duration:** ~15 min (orchestrator-driven inline execution)
- **Started:** 2026-05-09 (orchestrator-side)
- **Completed:** 2026-05-09
- **Tasks:** 4 of 4 complete
- **Files created:** 5 (3 source + 2 test)

## Accomplishments

- Established the canonical Phase 6 type contracts: `ActorSpec`, `MaterialSpec`, `SceneBlueprint`, `AssemblyResult`, `LightingParams`, `AssetResolutionResult`, `ProgressUpdate` — all importable from one module so 06-01 / 06-02 / 06-03 cannot diverge.
- Built `AssetPool` with LRU eviction at MAX_ENTRIES=200, on-disk JSON persistence at `%LOCALAPPDATA%/NYRA/asset_pool.json`, and case-insensitive SHA256 keys. Persistence verified via test_pool_persistence.
- Built `SceneAssemblyOrchestrator` base class with backend router injection, WebSocket notification helpers (progress / complete / error), and dict-to-dataclass converters that normalize JSON lists to tuples for RGB and direction fields.
- 16/16 unit tests pass on Python 3.12 / Windows in 0.08s.

## Task Commits

Each task was committed atomically on `main`:

1. **Task 1: scene_types.py shared dataclasses** — `4f70c6d` (feat)
2. **Task 2: asset_pool.py LRU resolution cache** — `0f3ccba` (feat)
3. **Task 3: scene_orchestrator.py base class** — `fc2c11a` (feat)
4. **Task 4: Wave 0 unit tests (16 tests)** — `e0ec0b8` (test)

**Plan metadata:** to be appended (this SUMMARY commit)

## Files Created

- `nyrahost/tools/scene_types.py` (180 lines) - All Phase 6 shared dataclasses + helper methods (`to_structured_summary`, `to_ue_params`, `to_ws_payload`).
- `nyrahost/tools/asset_pool.py` (141 lines) - `AssetPool` LRU cache + `PoolEntry` dataclass; persists to LOCALAPPDATA.
- `nyrahost/tools/scene_orchestrator.py` (159 lines) - `SceneAssemblyOrchestrator` base class with router property, async LLM-call wrappers, WS notification helpers, dict->dataclass converters.
- `tests/test_scene_types.py` (90 lines) - 9 tests covering dataclass defaults, structured summaries, to_ue_params output, property counts.
- `tests/test_asset_pool.py` (90 lines) - 7 tests covering put/get, LRU eviction, miss, case-insensitivity, persistence, clear, stats.

## Verification

```text
cd TestProject/Plugins/NYRA/Source/NyraHost
python -m pytest tests/test_scene_types.py tests/test_asset_pool.py -v
================================ 16 passed, 11 warnings in 0.08s ================================
```

The 11 warnings are `DeprecationWarning: datetime.datetime.utcnow()` — non-blocking, deferred to a future codebase-wide timezone-aware migration. All 16 assertions pass cleanly.

## Truths Established (Phase 6 contract)

- `SceneBlueprint`, `ActorSpec`, `MaterialSpec`, `AssemblyResult`, `LightingParams` are importable from `scene_types.py` across all Phase 6 plans. ✅
- `AssetPool` tracks resolved assets with LRU eviction and prevents duplicate imports. ✅
- `SceneAssemblyOrchestrator` provides the backend-router interface and WS notification pattern used by both SCENE-01 and DEMO-01. ✅

## Threats Mitigated

- **T-06-10 DoS via unbounded AssetPool growth** — MAX_ENTRIES=200 cap + LRU eviction enforced; verified by `test_pool_lru_eviction`.
- **T-06-11 Tampering of asset_pool.json** — file holds only user-resolvable asset paths (no credentials); tampering causes a cache miss, not a security event.

## Downstream Unblocked

- **Plan 06-01 (SCENE-01 lighting authoring)** — can now `from nyrahost.tools.scene_types import LightingParams` and `from nyrahost.tools.scene_orchestrator import SceneAssemblyOrchestrator`.
- **Plan 06-02 (DEMO-01 image-to-scene)** — can now `from nyrahost.tools.scene_types import SceneBlueprint, ActorSpec, MaterialSpec, AssemblyResult` and inherit `SceneAssemblyOrchestrator`.
- **Plan 06-03 (staging tests)** — can now exercise the full Wave 0 surface in integration tests.

## Open Items

- `datetime.utcnow()` deprecation warning (Python 3.12+) — defer to a project-wide datetime migration sweep, not a Phase 6 concern.
- AssetPool thread-safety: NyraHost is single-process async, so the current non-locking implementation is correct. If Phase 7+ introduces multi-process inference workers that share the pool file, add a fcntl/msvcrt advisory lock.

## Status

✅ **Plan 06-00 COMPLETE at source+docs+tests layer.** Wave 1 (06-01 lighting) and Wave 2 (06-02 assembly) are unblocked.
