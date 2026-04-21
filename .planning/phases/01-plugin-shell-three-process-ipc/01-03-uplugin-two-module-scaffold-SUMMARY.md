---
phase: 01-plugin-shell-three-process-ipc
plan: 03
subsystem: infra
tags: [ue5, unreal-plugin, cpp, build-cs, uplugin, ubt, websockets, automation-spec]

requires:
  - phase: 00-legal-brand-gate
    provides: none-blocking (legal gate runs parallel; no artifacts consumed)
provides:
  - Greenfield UE 5.6 test host project (TestProject.uproject) with NYRA plugin enabled
  - NYRA.uplugin two-module descriptor (NyraEditor editor-only + NyraRuntime Runtime stub)
  - NyraEditor module C++ scaffold (Build.cs, module impl, LogNyra category)
  - NyraRuntime module FDefaultModuleImpl stub
  - RuntimeDependencies staging block for NyraHost + NyraInfer binaries (empty in Plan 03)
  - Nyra.Plugin.ModulesLoad automation spec (2 tests — VALIDATION row 1-01-01)
  - Binary distribution decision record (docs/BINARY_DISTRIBUTION.md — prebuild.ps1 with Git LFS escape hatch)
affects: [01-04-nomad-tab, 01-05-specs-handshake, 01-06-nyrahost-core, 01-08-nyrainfer-spawn, 01-10-cpp-supervisor, 01-11-cpp-markdown, 01-12-chat-panel]

tech-stack:
  added:
    - Unreal Engine 5.6 (target engine lock per D-03)
    - UBT ModuleRules with DefaultBuildSettings=V5, CppStandard=Cpp20
    - UE bundled WebSockets module (FWebSocketsModule) — declared as plugin dep
    - UE bundled HTTP, Json, JsonUtilities, DesktopPlatform, ToolMenus, UnrealEd, Slate/SlateCore modules
    - FAutomationSpec testing (BEGIN_DEFINE_SPEC) for Nyra.Plugin.ModulesLoad
  patterns:
    - Two-module plugin layout (Editor + Runtime) per .uplugin with PlatformAllowList=[Win64]
    - RuntimeDependencies staging for non-DLL plugin binaries (RESEARCH §3.8)
    - NYRAEDITOR_API + DECLARE_LOG_CATEGORY_EXTERN + DEFINE_LOG_CATEGORY for cross-module log category
    - Module lifecycle via StartupModule/ShutdownModule with TODO hooks for Plans 04 / 10
    - Guarded integration-test shell via WITH_AUTOMATION_TESTS && ENABLE_NYRA_INTEGRATION_TESTS

key-files:
  created:
    - TestProject/TestProject.uproject
    - TestProject/.gitignore
    - TestProject/Plugins/NYRA/NYRA.uplugin
    - TestProject/Plugins/NYRA/README.md
    - TestProject/Plugins/NYRA/Resources/Icon128.png
    - TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraEditor.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraEditorModule.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraLog.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditor.cpp
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraLog.cpp
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraIntegrationSpec.cpp
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTestFixtures.h
    - TestProject/Plugins/NYRA/Source/NyraRuntime/NyraRuntime.Build.cs
    - TestProject/Plugins/NYRA/Source/NyraRuntime/Public/NyraRuntime.h
    - TestProject/Plugins/NYRA/Source/NyraRuntime/Private/NyraRuntime.cpp
    - docs/BINARY_DISTRIBUTION.md
  modified: []

key-decisions:
  - "UE 5.6 locked as Phase 1 target engine (D-03). Multi-version CI (5.4/5.5/5.7) deferred to Phase 2."
  - "Two-module .uplugin layout: NyraEditor editor-only Phase-1 home; NyraRuntime empty FDefaultModuleImpl reserved for v2 runtime-world features."
  - "Binary distribution strategy: prebuild.ps1 build-time download for Phase 1 (Plan 06 authors script); Git LFS is Phase 2 Fab-packaging escape hatch. Single source of truth = assets-manifest.json."
  - "NyraEditor.Build.cs uses DefaultBuildSettings.V5 + CppStandard.Cpp20 (Phase 1 baseline; matches UE 5.6 toolchain)."
  - "RuntimeDependencies staging block conditionals on Directory.Exists to tolerate empty Binaries/Win64/NyraHost and NyraInfer subtrees during Plan 03 (populated by Plans 06 and 08)."
  - "PlatformAllowList: ['Win64'] on both modules in .uplugin — enforces Phase 1 Windows-only scope at descriptor level."

patterns-established:
  - "Module lifecycle pattern: FNyraEditorModule::StartupModule / ShutdownModule with explicit Plan 04 / Plan 10 TODO markers for forward-referenced subsystem boot (RegisterTabSpawner, FNyraSupervisor)."
  - "Log category pattern: NYRAEDITOR_API-exported LogNyra category (DECLARE_LOG_CATEGORY_EXTERN in Public/NyraLog.h, DEFINE in Private/NyraLog.cpp). Consumers UE_LOG(LogNyra, Log, TEXT(\"[NYRA] ...\"))."
  - "Build.cs dependency pattern: Public = Core/CoreUObject/Engine + Slate + editor-scope (UnrealEd/ToolMenus/EditorSubsystem) + integrations (WebSockets/HTTP/Json/DesktopPlatform/ApplicationCore). Private = WorkspaceMenuStructure/MainFrame/LevelEditor for nomad tab + level-editor extension."
  - "Automation-test dual-spec pattern: unguarded Nyra.Plugin (runs on dev machines) + guarded Nyra.Integration (ENABLE_NYRA_INTEGRATION_TESTS, requires live NyraHost)."

requirements-completed: [PLUG-01]

duration: 28min
completed: 2026-04-21
---

# Phase 1 Plan 03: UPlugin Two-Module Scaffold Summary

**UE 5.6 test host project + NYRA plugin two-module skeleton (NyraEditor editor-only, NyraRuntime FDefaultModuleImpl) with RuntimeDependencies staging, LogNyra category, and Nyra.Plugin.ModulesLoad automation spec.**

## Performance

- **Duration:** ~28 min (wall clock, including the pre-existing Task 1 commit from earlier session)
- **Started:** 2026-04-21T19:21:00Z (Task 1 commit c650c84)
- **Completed:** 2026-04-21T21:07:00Z
- **Tasks:** 5/5 completed
- **Files created:** 18
- **Files modified:** 0

## Accomplishments

- UE 5.6 test host descriptor (`TestProject.uproject`) with NYRA plugin enabled and Windows-only .gitignore
- `NYRA.uplugin` v3 descriptor with two modules (NyraEditor Editor/PostEngineInit/Win64, NyraRuntime Runtime/Default/Win64) and WebSockets plugin dep declared
- `NyraEditor.Build.cs` with the full RESEARCH §3.2 dependency list, V5 build settings, Cpp20, and a RuntimeDependencies staging block for `Binaries/Win64/NyraHost/` and `Binaries/Win64/NyraInfer/`
- `FNyraEditorModule` IModuleInterface implementation with StartupModule/ShutdownModule logging hooks and inline markers for Plan 04 (tab spawner) and Plan 10 (supervisor)
- `LogNyra` log category exported via `NYRAEDITOR_API` for consumption by later-phase headers
- `NyraRuntime` minimal FDefaultModuleImpl stub — zero behaviour, Core/CoreUObject/Engine deps only
- `FNyraPluginModulesLoadSpec` automation spec under `Nyra.Plugin.ModulesLoad` with two It() blocks verifying both modules report IsModuleLoaded=true
- Guarded `FNyraIntegrationSpec` shell for Plan 10 to populate with Handshake/Auth E2E tests
- Binary distribution strategy LOCKED in `docs/BINARY_DISTRIBUTION.md`: prebuild.ps1 build-time download for Phase 1; Git LFS as the Phase 8 Fab-packaging escape hatch; `assets-manifest.json` as single source of truth for artefact URLs + SHA256 pins

## Task Commits

1. **Task 1: Greenfield test host + gitignore + binary distribution doc** — `c650c84` (feat)
2. **Task 2: NYRA.uplugin + Icon128 + plugin README** — `1bbf4e4` (feat)
3. **Task 3: NyraEditor module (Build.cs + module + LogNyra)** — `2dd106c` (feat)
4. **Task 4: NyraRuntime module (FDefaultModuleImpl stub)** — `106ed82` (feat)
5. **Task 5: Nyra.Plugin.ModulesLoad automation spec** — `2dc2d32` (test)

_Plan metadata commit (SUMMARY + STATE + ROADMAP) follows this summary._

## Files Created/Modified

**Created (18 files, ~425 LOC including descriptors and docs):**

- `TestProject/TestProject.uproject` — FileVersion 3, EngineAssociation 5.6, Plugins=[NYRA enabled]
- `TestProject/.gitignore` — excludes UE build artefacts and plugin `Binaries/Win64/NyraHost/{cpython,wheels}/`, `Binaries/Win64/NyraInfer/`, and `UnrealEditor-*.dll/pdb`
- `TestProject/Plugins/NYRA/NYRA.uplugin` — v3 manifest, 5.6.0, two modules, WebSockets dep, Win64 only, IsBetaVersion=true
- `TestProject/Plugins/NYRA/README.md` — Phase 1 scope, build steps, dependencies, binary artefacts pointer
- `TestProject/Plugins/NYRA/Resources/Icon128.png` — 128×128 8-bit RGBA placeholder for Plugins browser tile
- `TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs` — ModuleRules with full dep list + RuntimeDependencies staging
- `TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraEditor.h` — reserved public header
- `TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraEditorModule.h` — FNyraEditorModule IModuleInterface declaration + Get/IsAvailable
- `TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraLog.h` — LogNyra extern declaration with NYRAEDITOR_API
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditor.cpp` — empty passthrough
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp` — IMPLEMENT_MODULE + StartupModule/ShutdownModule logging
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraLog.cpp` — LogNyra category definition
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraIntegrationSpec.cpp` — FNyraPluginModulesLoadSpec (unguarded) + FNyraIntegrationSpec (guarded shell)
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTestFixtures.h` — minimal Rule-3 stub (Plan 01 replaces with full fixture namespace)
- `TestProject/Plugins/NYRA/Source/NyraRuntime/NyraRuntime.Build.cs` — minimal ModuleRules (Core/CoreUObject/Engine)
- `TestProject/Plugins/NYRA/Source/NyraRuntime/Public/NyraRuntime.h` — empty placeholder
- `TestProject/Plugins/NYRA/Source/NyraRuntime/Private/NyraRuntime.cpp` — IMPLEMENT_MODULE(FDefaultModuleImpl, NyraRuntime)
- `docs/BINARY_DISTRIBUTION.md` — locked decision record with comparison table and Phase 8 Git LFS migration plan

## Decisions Made

Followed PLAN.md and CONTEXT.md D-01/D-02/D-03/D-13 exactly. No new decisions introduced; all locked upstream.

Two implementation nuances worth logging:

- Chose `DefaultBuildSettings = BuildSettingsVersion.V5` + `CppStandard = CppStandardVersion.Cpp20` for both modules — matches UE 5.6 toolchain defaults; ensures forward-compatibility when Phase 2 extends CI to 5.7.
- `NyraEditor.Build.cs` RuntimeDependencies staging block uses `Directory.Exists(NyraHostDir)` guards so the module compiles cleanly in Plan 03 even with the Binaries/Win64 subtrees empty. Plans 06 (CPython + wheels) and 08 (llama-server.exe variants) populate those subtrees; the same staging block then auto-registers every file under them without code changes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Created minimal NyraTestFixtures.h stub because Plan 01 (Wave 0 test scaffold) has not yet executed on this branch**

- **Found during:** Task 5 (automation spec creation)
- **Issue:** Task 5's canonical source starts with `#include "NyraTestFixtures.h"` and the plan's `<read_first>` references Plan 01's output `NyraTestFixtures.h`, but Plan 01 was never committed to this branch (STATE.md still shows `current_plan: 1`, and Plan 01's files don't exist on disk). The include would fail to resolve and block UBT compilation of Task 5's spec.
- **Fix:** Authored a minimal `NyraTestFixtures.h` containing only `#pragma once` + `#include "CoreMinimal.h"` plus a comment documenting that Plan 01 will replace it with the full `Nyra::Tests` fixture namespace (`FNyraTempDir`, `FNyraTestClock`, `WriteHandshakeFile`, `MakeJsonRpcRequest`). The Nyra.Plugin.ModulesLoad spec does not use any fixture helpers (it only calls `FModuleManager::IsModuleLoaded` directly), so the empty stub is correct-by-construction for Plan 03 and will be transparently upgraded when Plan 01 executes.
- **Files modified:** `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTestFixtures.h` (new)
- **Verification:** All grep-level acceptance criteria in Plan 03 Task 5 pass. Plan 01 Task 1 acceptance criteria (require `namespace Nyra::Tests`, `class FNyraTempDir`, etc.) will re-verify the stub and Plan 01 will replace it.
- **Committed in:** `2dc2d32` (Task 5 commit)

### Platform-gap deferrals (host is macOS, target is Windows)

Per `<runtime_constraints>` in the execution prompt, every UE-compile-gated and UE-automation-execution-gated verify step is deferred to Windows CI:

- **Task 2 verify:** Opening TestProject.uproject in UE 5.6 to confirm NYRA appears in Plugins browser under "AI" — deferred.
- **Task 3 verify:** UBT compilation of NyraEditor.Build.cs against UE 5.6 headers — deferred. All grep-based automated checks in the plan pass.
- **Task 4 verify:** UBT compilation of NyraRuntime — deferred. Grep-based checks pass.
- **Task 5 verify:** `UnrealEditor-Cmd.exe TestProject.uproject -ExecCmds="Automation RunTests Nyra.Plugin;Quit" -unattended -nopause -testexit="Automation Test Queue Empty"` producing exit 0 with 2 tests passing — deferred. Source-level acceptance criteria all pass; the spec will be exercised on the first Windows dev-machine compile.
- **Overall success criteria #1–2:** "Both modules compile on UE 5.6 with MSVC v143" and "Nyra.Plugin.ModulesLoad passes" — deferred to the Phase 1 Ring 0 gate (Plan 15) when a Windows CI/dev machine is available.

**Total deviations:** 1 auto-fixed (Rule 3 — unblocking include dependency) + 5 platform-gap deferrals (not deviations per se; mandated by runtime constraints).

**Impact on plan:** Zero scope creep. Rule 3 stub was the minimum necessary to keep Task 5 correct-by-construction; the stub is self-documenting and will be replaced by Plan 01 without modification.

## Issues Encountered

- **Sequencing drift vs. Wave plan:** PLAN.md declares `depends_on: [01]`, but Plans 01 and 02 (Wave 0 test scaffolds) had not yet executed when this plan was launched. Handled via the Rule 3 stub above so Plan 03 remains standalone-executable. No reordering of downstream plans required.

## TDD Gate Compliance

Plan 03 is `type: execute`, not `type: tdd`. No RED/GREEN/REFACTOR gate applies. Task 5 does write a test file (the Nyra.Plugin.ModulesLoad spec), but that is a `test(...)` conventional-commit type, not a TDD gate commit — no implementation follows in this plan since the modules already scaffold their own load behaviour as part of UE's plugin loader.

## Threat Flags

No new security-relevant surface introduced in this plan. Binary-distribution decision record flags the SHA256-pinning requirement on `assets-manifest.json` (future Plan 06 surface), but no network/filesystem/auth boundaries are crossed by Plan 03 artefacts.

## Self-Check: PASSED

All claimed files exist on disk:

- `TestProject/TestProject.uproject` FOUND
- `TestProject/.gitignore` FOUND
- `TestProject/Plugins/NYRA/NYRA.uplugin` FOUND
- `TestProject/Plugins/NYRA/Resources/Icon128.png` FOUND (PNG image data, 128x128, 8-bit/color RGBA)
- `TestProject/Plugins/NYRA/README.md` FOUND
- `TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs` FOUND
- `TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraEditor.h` FOUND
- `TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraEditorModule.h` FOUND
- `TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraLog.h` FOUND
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditor.cpp` FOUND
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp` FOUND
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraLog.cpp` FOUND
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraIntegrationSpec.cpp` FOUND
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTestFixtures.h` FOUND
- `TestProject/Plugins/NYRA/Source/NyraRuntime/NyraRuntime.Build.cs` FOUND
- `TestProject/Plugins/NYRA/Source/NyraRuntime/Public/NyraRuntime.h` FOUND
- `TestProject/Plugins/NYRA/Source/NyraRuntime/Private/NyraRuntime.cpp` FOUND
- `docs/BINARY_DISTRIBUTION.md` FOUND

All claimed commits exist in `git log --oneline`:

- `c650c84` FOUND — Task 1 (greenfield descriptor + gitignore + binary distribution doc)
- `1bbf4e4` FOUND — Task 2 (NYRA.uplugin + icon + README)
- `2dd106c` FOUND — Task 3 (NyraEditor module)
- `106ed82` FOUND — Task 4 (NyraRuntime module)
- `2dc2d32` FOUND — Task 5 (Nyra.Plugin.ModulesLoad spec)

## User Setup Required

None — Phase 1 shell is legal-safe and needs no external service configuration. First Windows dev-machine open of `TestProject.uproject` will prompt UBT to compile the plugin; subsequent plans (06, 08) populate the binary artefact subtrees.

## Next Phase Readiness

- **01-04 (nomad-tab-placeholder-panel):** Ready. `FNyraEditorModule::StartupModule` TODO marker is the injection point for `RegisterTabSpawner("NyraChatTab", ...)`.
- **01-05 (specs-handshake-jsonrpc-pins):** Ready. .uplugin already declares WebSockets dep; NyraEditor.Build.cs already lists WebSockets in PublicDependencyModuleNames.
- **01-06 (nyrahost-core-ws-auth-handshake):** Ready. Binaries/Win64/NyraHost/ subtree is staged by RuntimeDependencies (conditional on Directory.Exists); Plan 06 populates the tree via prebuild.ps1 without Build.cs changes. `docs/BINARY_DISTRIBUTION.md` confirms the strategy.
- **01-08 (nyrahost-infer-spawn-ollama-sse):** Ready. Same staging story for Binaries/Win64/NyraInfer/.
- **01-10 (cpp-supervisor-ws-jsonrpc):** Ready. `FNyraEditorModule::StartupModule` TODO marker matches the planned `FNyraSupervisor::Get().SpawnNyraHost()` injection point.
- **01-01 (cpp-automation-scaffold):** Can still execute standalone — will replace the Rule-3 NyraTestFixtures.h stub with the full fixture namespace (pure superset; no conflict).

---

*Phase: 01-plugin-shell-three-process-ipc*
*Plan: 03-uplugin-two-module-scaffold*
*Completed: 2026-04-21*
