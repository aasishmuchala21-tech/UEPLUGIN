# Phase 05 Plan 01: Meshy REST API Integration (GEN-01) — Summary

**Executed:** 2026-05-07
**Wave:** 1
**Requirements:** GEN-01
**Commits:** `f1bce8f` (test wave 0) · `5848749` (implementation)

---

## One-liner

Async Meshy REST client with staging manifest and two MCP tools — `nyra_meshy_image_to_3d` and `nyra_job_status` — wired into the NyraHost MCP server.

---

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| `httpx` over `aiohttp` for HTTP client | NyraHost's existing codebase uses `httpx` throughout (gemma.py, byok.py, router.py); no `aiohttp` dep in pyproject.toml. Consistency > the minor asyncio ergonomics tradeoff. |
| Sync mock in `asyncio.iscoroutine()` guard | When `_poll_meshy_and_update_manifest` is monkeypatched to a noop in tests, it's a plain function not a coroutine. The guard prevents `asyncio.run(None)` errors. |
| `httpx.AsyncClient` (not `httpx.Client`) in `MeshyClient` | All HTTP calls are async in the client; the `image_to_3d` method is `async def`. Creating a new `AsyncClient` per call avoids session management complexity. |
| `PathTraversalError` as distinct `ValueError` subclass | Enables callers to catch it specifically vs. generic `ValueError` from other validation. T-05-03 threat mitigation. |

---

## Key Files Created/Modified

| File | Role | Lines |
|------|------|-------|
| `nyrahost/tools/staging.py` | StagingManifest + JobEntry + PathTraversalError | ~220 |
| `nyrahost/external/meshy_client.py` | Async Meshy HTTP client | ~160 |
| `nyrahost/tools/meshy_tools.py` | MeshyImageTo3DTool + JobStatusTool | ~230 |
| `nyrahost/mcp_server/__init__.py` | Tool registration | modified |
| `tests/test_staging.py` | 9 unit tests | ~215 |
| `tests/test_meshy_client.py` | 11 unit tests | ~237 |
| `tests/test_meshy_tools.py` | 8 unit tests | ~190 |
| `tests/conftest.py` | 4 Phase 5 fixtures | modified |

---

## Threat Mitigations Implemented

| Threat ID | Mitigation | Where |
|-----------|------------|-------|
| T-05-01 | API key in `Authorization: Bearer` header only; error messages never include key value | `MeshyClient._headers()`, `_request()` error paths |
| T-05-03 | `PathTraversalError` raised when resolved path is outside `%LOCALAPPDATA%/NYRA/staging/` | `StagingManifest._validate_path()` |

---

## Deviations from Plan

1. **`httpx` instead of `aiohttp`** — Plan specified `aiohttp` but NyraHost has no `aiohttp` dep. Used `httpx.AsyncClient` instead, which is already in pyproject.toml. Trade: slightly less idiomatic async context management; Gain: no new dependency.

2. **`asyncio.iscoroutine()` guard** — Added to handle mock noop functions in tests (not in original plan spec). Fixes `ValueError: a coroutine was expected, got None` when `asyncio.run()` receives a sync mock.

3. **`datetime.now(timezone.utc)`** — Replaced `datetime.utcnow()` (deprecated) with `datetime.now(timezone.utc)` in staging.py and test_staging.py. Fixes deprecation warnings across all 27 tests.

---

## Test Results

```
27 passed in 8.86s
```

All tests use mocked HTTP (no live network required). Quick command:
```bash
pytest TestProject/Plugins/NYRA/Source/NyraHost/tests/test_meshy_client.py \
       TestProject/Plugins/NYRA/Source/NyraHost/tests/test_meshy_tools.py \
       TestProject/Plugins/NYRA/Source/NyraHost/tests/test_staging.py -q
```

---

## Self-Check: PASSED

- [x] All 27 test cases pass
- [x] `MeshyClient` uses `httpx` (not `aiohttp`)
- [x] `PathTraversalError` is a distinct class
- [x] `_validate_path` called before any `downloaded_path` write
- [x] API key in Bearer header only, not logged
- [x] Idempotency: `find_by_hash` checked before `add_pending`
- [x] `nyra_meshy_image_to_3d` and `nyra_job_status` registered in `mcp_server/__init__.py`
- [x] `_iscoroutine()` guard handles mock noops in tests
- [x] `datetime.now(timezone.utc)` used instead of `datetime.utcnow()`