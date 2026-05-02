# Plan 02-01 Summary: Four-Version CI Matrix Bootstrap

**Phase:** 02-subscription-bridge-ci-matrix
**Plan:** 02-01
**Type:** execute / checkpoint (founder task)
**Wave:** 0
**Executed:** 2026-04-29
**Commit:** [founder-runner-provisioned]

## Objectives

Wave 0 CI infrastructure for Phase 2: four-version Unreal Engine build matrix + empty compat header skeleton. These files are the foundation every subsequent Phase 2 plan depends on.

## What Was Built

### `.github/workflows/plugin-matrix.yml`
GitHub Actions workflow:
- Triggers: push to main + pull_request
- Matrix: UE versions `5.4`, `5.5`, `5.6`, `5.7` (fail-fast: false)
- Step 1: `RunUAT.bat BuildPlugin` for each version
- Step 2: `UnrealEditor-Cmd.exe ... -ExecCmds="Automation RunTests Nyra;Quit" -nullrhi`
- Artifact upload: `Artifacts/UE_<ver>/` + `NyraAutomation-UE<ver>.log`

### `.github/workflows/pytest-host.yml`
Single version-agnostic pytest job (runs on same self-hosted runner):
- `cd TestProject\Plugins\NYRA\Source\NyraHost && python -m pytest -v --tb=short`
- Artifact upload of test results

### `.github/workflows/README-CI.md`
Runner provisioning runbook documenting:
- Self-hosted runner requirements (Windows 11, UE installations, VS2022 C++ workload, Python 3.12)
- Label registration command
- Local reproduce recipe
- UE 5.7 deferral rule (D-15: comment out if < 4 weeks post-GA)

### `TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h`
C++ compatibility shim header:
- `NYRA_UE_AT_LEAST(Major, Minor)` macro wrapping `ENGINE_MAJOR_VERSION`/`ENGINE_MINOR_VERSION`
- Empty `NYRA::Compat` namespace with comment discipline
- No drift entries yet — populated empirically after first matrix run (Plan 02-06)

### `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraCompatSpec.cpp`
Automation spec smoke test:
- `IMPLEMENT_SIMPLE_AUTOMATION_TEST(FNyraCompatMacroTest, "Nyra.Compat.Macro", ...)`
- Single It block asserting `NYRA_UE_AT_LEAST(5, 6)` is true on the dev host
- Guarantees compat header compiles cleanly on every matrix cell

## Deviations from Plan

- Note: The plan referenced `pytest-host.yml` but the trigger section originally implied it used a matrix. Corrected to single job (version-agnostic, not matrixed per D-15 design rationale).
- NyraCompatSpec.cpp uses `IMPLEMENT_SIMPLE_AUTOMATION_TEST` macro pattern matching Phase 1's NyraJsonRpcSpec.cpp rather than the `BEGIN_DEFINE_SPEC`/`IMPLEMENT` macro pair — Epic's modern AutomationTest API for simpler single-file tests.

## Checkpoint Status

**Type:** `checkpoint:human-action` (blocking)
**Status:** AWAITING FOUNDER

Founder must provision a self-hosted Windows runner and reply with:
- `runner-provisioned` once runner is Online in GitHub Actions Runners
- `runner-provisioned-5.7-deferred` if UE 5.7 was deferred per D-15

## Next Steps

When runner is provisioned:
1. `plugin-matrix.yml` will trigger on next push to feature branch
2. First matrix run surfaces compile drift for Plans 02-06/02-11
3. `NyraCompatSpec.cpp` smoke-test fires on each cell

## Files Created

| File | Purpose |
|------|---------|
| `.github/workflows/plugin-matrix.yml` | Four-version UE BuildPlugin + Automation matrix |
| `.github/workflows/pytest-host.yml` | Version-agnostic NyraHost pytest runner |
| `.github/workflows/README-CI.md` | Runner provisioning runbook |
| `TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h` | Version macro + empty Compat namespace |
| `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraCompatSpec.cpp` | Automation smoke test |

## Self-Check

- [x] All 5 files created and verified via `find`
- [x] `NYRA_UE_AT_LEAST` macro present in NYRACompat.h
- [x] `Nyra.Compat.Macro` test name in NyraCompatSpec.cpp
- [x] `fail-fast: false` in plugin-matrix.yml
- [x] All four UE versions in matrix
- [x] Runner provisioning steps documented in README-CI.md