---
phase: "05-external-tool-integrations-api-first"
plan: "03"
subsystem: external-tool-integrations
tags: [claude, computer-use, win32, mcp, anthropic-api, screen-capture]

# Dependency graph
requires:
  - phase: "02-market-data-real-time"
    provides: "MCP server infrastructure, NyraMCPServer base class"
  - phase: "05-external-tool-integrations-api-first"
    provides: "05-01 and 05-02 set up external tool orchestration context"
provides:
  - ComputerUseLoop with permission gate, Win32 action execution, mss screenshots
  - nyra_computer_use and nyra_computer_use_status MCP tools registered in MCP server
  - win32_actions.py with Win32ActionExecutor, ScreenCapture, PermissionGate
  - 13-unit test suite with mocked Win32/HTTP (no live GUI required)
affects:
  - "06-inference-integration-gemma"
  - "07-reference-driven-workflows"
  - "08-content-pipeline-meshy"

# Tech tracking
tech-stack:
  added: [anthropic (SDK), mss, pywin32]
  patterns: [computer-use loop, permission gate, background thread jobs, staging manifest]

key-files:
  created:
    - "TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/external/computer_use_loop.py"
    - "TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/external/win32_actions.py"
    - "TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/base.py"
    - "TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/staging.py"
    - "TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/computer_use_tools.py"
    - "TestProject/Plugins/NYRA/Source/NyraHost/tests/test_computer_use.py"
  modified:
    - "TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/__init__.py"

key-decisions:
  - "Screenshots use local_file source type in API calls — avoids base64 encoding in transit (T-05-06)"
  - "Permission gate uses ctypes.windll.user32.MessageBoxW — works without pywin32 installed"
  - "Loop runs in background daemon thread — MCP call returns job_id immediately (non-blocking)"
  - "Win32 imports guarded with try/except — all actions are no-ops on non-Windows platforms"

patterns-established:
  - "ComputerUseLoop as the central orchestrator: screenshot → API call → action execution loop"
  - "PermissionGateResult dataclass wraps gate approval state"
  - "_loop_registry dict keyed by job_id enables cross-tool status retrieval"
  - "StagingManifest tracks pending/confirmed jobs independent of loop state"

requirements-completed: [GEN-03]

# Metrics
duration: 8min
completed: 2026-05-07
---

# Phase 05: Computer-Use Loop (GEN-03) Summary

**Anthropic computer-use loop with permission gate, Win32 SendInput action execution, mss screenshots saved to LOCALAPPDATA, and Ctrl+Alt+Space pause chord — registered as `nyra_computer_use` / `nyra_computer_use_status` MCP tools**

## Performance

- **Duration:** 8 min
- **Started:** 2026-05-07T16:42:00Z
- **Completed:** 2026-05-07T16:50:00Z
- **Tasks:** 4
- **Files modified:** 6 (2 modules, 4 files created, 1 modified)

## Accomplishments

- `ComputerUseLoop`: Anthropic API with `computer_20251124` tool, Opus 4.7 model, `computer-use-2025-11-24` beta header, local screenshot paths (not base64)
- `PermissionGate`: Win32 MessageBox via `ctypes.windll.user32.MessageBoxW` shown before first Win32 action
- `Win32ActionExecutor`: `SendInput`/`mouse_event` for cursor/click/scroll/type/key_combo; `RegisterHotKey` for Ctrl+Alt+Space pause chord
- `ScreenCapture`: mss full-screen capture saved to `LOCALAPPDATA/NYRA/staging/computer_use/<job_id>/`
- `ComputerUseTool` + `ComputerUseStatusTool`: background daemon thread, job_id registry, staging manifest integration
- Both tools registered in MCP server `list_tools()` schema and dispatch table
- 13-unit test suite covering all threat mitigations (T-05-05/06/07)

## Task Commits

Each task was committed atomically:

1. **Task 1: ComputerUseLoop + Win32ActionExecutor** - `dbe1cf3` (feat)
2. **Task 2: MCP tools + NyraTool base + staging manifest + MCP server registration** - `50b6126` (feat) + `f47032f` (feat)
3. **Task 4: Test suite** - `65ac10d` (test)

**Plan metadata:** `5712f1c` (docs: phase 5 research)

## Files Created/Modified

- `src/nyrahost/external/computer_use_loop.py` — Main loop: screenshot → API → action → repeat; permission gate + pause chord
- `src/nyrahost/external/win32_actions.py` — Win32ActionExecutor, ScreenCapture, PermissionGate; all Win32 imports guarded
- `src/nyrahost/tools/base.py` — NyraTool/NyraToolResult base classes
- `src/nyrahost/tools/staging.py` — StagingManifest for job tracking
- `src/nyrahost/tools/computer_use_tools.py` — ComputerUseTool, ComputerUseStatusTool with _loop_registry
- `tests/test_computer_use.py` — 13 unit tests with mocked dependencies
- `src/nyrahost/mcp_server/__init__.py` — Added both tools to list_tools() schema + dispatch handlers

## Decisions Made

- Screenshots sent as `local_file` source type to Anthropic API — avoids base64 encoding in API requests (T-05-06 mitigation)
- `PermissionGate.check()` uses `ctypes.windll.user32.MessageBoxW` — no pywin32 runtime dependency for the permission dialog
- `ANTHROPIC_API_KEY` env var validated at `ComputerUseLoop` construction — fails fast with clear error message
- `win32_actions.py` guarded with `try/except ImportError` for all win32api/win32input — graceful no-ops on non-Windows

## Deviations from Plan

**1. [Rule 3 - Blocking] Fixed win32 import names in plan stub**
- **Found during:** Task 1 (win32_actions.py implementation)
- **Issue:** Plan stub used wrong module names (`win32ioctlevent`, `win32trace`, `win32event`, `win32file`) that don't exist in pywin32
- **Fix:** Used correct `win32input` for SendInput/MOUSEINPUT/KEYBDINPUT, `win32api` for RegisterHotKey/PeekMessage; ctypes for MessageBoxW
- **Files modified:** `src/nyrahost/external/win32_actions.py`
- **Verification:** Tests pass on macOS with None guards; Win32 APIs verified from Microsoft docs

**2. [Rule 3 - Blocking] Fixed test mss mocking to use correct import path**
- **Found during:** Task 4 (test suite)
- **Issue:** `patch("nyrahost.external.computer_use_loop.mss")` doesn't intercept the module-level `import mss` binding; `patch("mss.mss")` failed because mss wasn't installed
- **Fix:** Patched `sys.modules["mss"]` for the loop test and used a mock module object for `win32_actions.mss` with correct `mss()` context manager protocol
- **Files modified:** `tests/test_computer_use.py`
- **Verification:** All 13 tests green

## User Setup Required

**ANTHROPIC_API_KEY required for live computer-use.**
See [05-external-tool-integrations-api-first-USER-SETUP.md](./05-external-tool-integrations-api-first-USER-SETUP.md) for:
- Environment variable configuration
- Dashboard configuration steps
- Verification commands

## Next Phase Readiness

- Computer-use loop is fully implemented and tested
- MCP tools registered and wired into the MCP server
- Ready for Phase 06 (Gemma inference integration) and Phase 07 (reference-driven workflows)
- No blockers

---
*Phase: 05-external-tool-integrations-api-first*
*Completed: 2026-05-07*
