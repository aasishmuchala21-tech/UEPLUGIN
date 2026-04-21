---
phase: 01-plugin-shell-three-process-ipc
plan: 01
subsystem: testing
tags: [ue5, automation-spec, test-scaffold, wave-0, cpp]

requires:
  - phase: 01-plugin-shell-three-process-ipc
    plan: 03
    provides: Plan 03 NyraEditor.Build.cs + Private/Tests/ directory + minimal NyraTestFixtures.h stub (commit 2dc2d32)
provides:
  - Nyra::Tests namespace (FNyraTempDir RAII, FNyraTestClock injection, WriteHandshakeFile D-06, MakeJsonRpcRequest D-09)
  - Nyra.Jsonrpc.* spec shell (Plan 10 fills)
  - Nyra.Markdown.* spec shell (Plan 11 fills)
  - Nyra.Supervisor.* spec shell with clock-injection hook (Plan 10 fills)
  - Nyra.Panel.* spec shell (Plans 04/12 fill)
  - Test-suite README with run command, integration opt-in, file map
affects: [01-04-nomad-tab, 01-10-cpp-supervisor, 01-11-cpp-markdown, 01-12-chat-panel]

tech-stack:
  added:
    - UE Automation Spec pattern (BEGIN_DEFINE_SPEC / END_DEFINE_SPEC)
    - namespace Nyra::Tests fixtures (RAII temp-dir, injectable clock, handshake writer, JSON-RPC envelope builder)
  patterns:
    - WITH_AUTOMATION_TESTS guard on every .cpp + the fixture body so shipping builds emit nothing
    - ENABLE_NYRA_INTEGRATION_TESTS double-guard for live-subprocess E2E specs
    - Zero-production-dep fixture contract (only UE Core headers) so Wave 0 ships before any production code lands
    - Hierarchical test paths Nyra.{Jsonrpc,Markdown,Supervisor,Panel,Integration,Plugin}.*

key-files:
  created:
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTestFixtures.cpp
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraJsonRpcSpec.cpp
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraMarkdownSpec.cpp
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraSupervisorSpec.cpp
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/README.md
  modified:
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTestFixtures.h

key-decisions:
  - "Preserved Plan 03's NyraIntegrationSpec.cpp verbatim (it already satisfied every Plan 01 acceptance criterion for that file AND hosts FNyraPluginModulesLoadSpec from PLUG-01). Rewriting would destroy shipped test coverage; non-breaking superset instead."
  - "NyraTestFixtures.h is a pure superset of Plan 03's Rule-3 stub — retained #pragma once + #include \"CoreMinimal.h\" so all existing includers keep compiling, added the full Nyra::Tests namespace inside #if WITH_AUTOMATION_TESTS."
  - "MakeJsonRpcRequest takes pre-formed ParamsJson (no escaping) so Nyra.Jsonrpc.EnvelopeRoundtrip tests can compare against byte-exact golden strings. Production framer in Plan 10 will use FJsonObject + TJsonWriter for dynamic cases; the fixture stays deterministic."
  - "FNyraTempDir scopes under FPaths::ProjectIntermediateDir()/NyraTests/<guid>/ (not Saved/, not LocalAppData) — Intermediate is writable, source-control-ignored, and cleared by UE's own clean operations, giving automatic scratch-area hygiene."

patterns-established:
  - "Fixture-first scaffold: all five spec shells include NyraTestFixtures.h even when unused so future It() blocks drop in without touching includes."
  - "Placeholder Define() bodies carry inline pointers to owning plan + VALIDATION.md test ID, giving Wave 1-5 executors a one-line find-and-replace entry point."
  - "Test-path ownership map documented in README file-map table (one row per spec file)."

requirements-completed: []

duration: 34min
completed: 2026-04-21
---

# Phase 1 Plan 01: C++ Automation Scaffold Summary

**UE 5.6 Automation Spec Wave 0 scaffold — 5 empty `BEGIN_DEFINE_SPEC` shells under `Nyra.*`, shared `Nyra::Tests` fixture namespace (temp-dir, clock, handshake, JSON-RPC envelope) in a pure-superset upgrade of Plan 03's stub, and a README locking the run command + integration opt-in flag.**

## Performance

- **Duration:** ~34 min (wall clock)
- **Started:** 2026-04-21T16:33:46Z
- **Completed:** 2026-04-21T17:08:37Z
- **Tasks:** 2/2 completed
- **Files created:** 6
- **Files modified:** 1 (NyraTestFixtures.h — Plan 03 stub upgraded to full fixture namespace)

## Accomplishments

- `Nyra::Tests` fixture namespace authored as a pure superset of Plan 03's Rule-3 stub:
  - `FNyraTempDir` — RAII scratch directory rooted at `Intermediate/NyraTests/<guid>/`, non-copyable, recursive delete on destruct
  - `FNyraTestClock` — header-only injectable monotonic clock (Advance / Set / Now) for deterministic supervisor 3-in-60s tests
  - `WriteHandshakeFile(...)` — writes the D-06-exact JSON `{port,token,nyrahost_pid,ue_pid,started_at}` using `FFileHelper::SaveStringToFile(ForceUTF8WithoutBOM)` so byte-identical round-trips match what the production NyraHost writer will emit
  - `MakeJsonRpcRequest(...)` — D-09 envelope builder returning byte-exact `{"jsonrpc":"2.0","id":...,"method":"...","params":...}` for Nyra.Jsonrpc.EnvelopeRoundtrip golden-string comparisons
- Four new empty-but-compilable spec shells covering every Wave 0 Nyra.* category:
  - `Nyra.Jsonrpc.*` (NyraJsonRpcSpec.cpp) — Plan 10 target
  - `Nyra.Markdown.*` (NyraMarkdownSpec.cpp) — Plan 11 target
  - `Nyra.Supervisor.*` (NyraSupervisorSpec.cpp) — Plan 10 target with explicit FNyraTestClock-injection comment
  - `Nyra.Panel.*` (NyraPanelSpec.cpp) — Plans 04 + 12 target
- `NyraIntegrationSpec.cpp` preserved verbatim from Plan 03 — already carried the guarded `FNyraIntegrationSpec`  for Plan 10 and the unguarded `FNyraPluginModulesLoadSpec` for PLUG-01 (shipped commit `2dc2d32`). Rewriting would have deleted working tests.
- Test-suite README locking: run command, filter pattern, integration opt-in via `GlobalDefinitions.Add("ENABLE_NYRA_INTEGRATION_TESTS=1")`, shared-fixture exports, and a one-row-per-spec ownership table.

## Task Commits

1. **Task 1: Shared test fixtures header + impl** — `35ed37d` (feat)
2. **Task 2: Five empty spec shells + README** — `ca182ba` (test)

_Plan metadata commit (SUMMARY + STATE + ROADMAP) follows this summary._

## Files Created/Modified

**Created (6 files, ~300 LOC including doc comments):**

- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTestFixtures.cpp` — FNyraTempDir RAII implementation, WriteHandshakeFile (D-06 schema + UTC-millis timestamp), MakeJsonRpcRequest (D-09 envelope)
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraJsonRpcSpec.cpp` — FNyraJsonRpcSpec under `Nyra.Jsonrpc` with inline Plan 10 placeholder comment
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraMarkdownSpec.cpp` — FNyraMarkdownSpec under `Nyra.Markdown` with Plan 11 placeholder
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraSupervisorSpec.cpp` — FNyraSupervisorSpec under `Nyra.Supervisor` with FNyraTestClock-injection comment
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp` — FNyraPanelSpec under `Nyra.Panel` with Plan 04 + 12 placeholder comments
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/README.md` — run command, integration opt-in, fixture exports, file map

**Modified (1 file):**

- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTestFixtures.h` — upgraded from Plan 03's 14-line stub to the full `Nyra::Tests` fixture namespace declaration (pure superset; the stub's two unguarded lines remain)

## Decisions Made

Followed PLAN.md exactly with two non-breaking adjustments logged in Deviations:

1. `NyraIntegrationSpec.cpp` already existed (Plan 03); its content satisfies every Plan 01 acceptance literal for that file, so it was left untouched rather than rewritten. Rewriting would have lost Plan 03's `FNyraPluginModulesLoadSpec` test coverage (PLUG-01, committed `2dc2d32`).
2. `NyraTestFixtures.h` was pre-existing (Plan 03 Rule-3 stub); upgraded in-place to preserve the stub's `#pragma once` + `#include "CoreMinimal.h"` symbols while wrapping the new Nyra::Tests namespace in `#if WITH_AUTOMATION_TESTS`.

Test-ID / owning-plan map (locked in README):

| Test path              | Owning plan | VALIDATION row      |
| ---------------------- | ----------- | ------------------- |
| Nyra.Jsonrpc.*         | 10          | 1-02-02             |
| Nyra.Markdown.*        | 11          | 1-04-02, 1-04-03    |
| Nyra.Supervisor.*      | 10          | 1-02-03             |
| Nyra.Panel.*           | 04, 12      | 1-04-01, 1-04-04, 1-04-05 |
| Nyra.Integration.*     | 10          | 1-02-01             |
| Nyra.Plugin.ModulesLoad| 03 (shipped)| 1-01-01             |

## Deviations from Plan

### Non-breaking reconciliations with Plan 03

**1. [Rule 1 / non-breaking superset] Preserved Plan 03's `NyraIntegrationSpec.cpp` verbatim**

- **Found during:** Task 2 setup — Plan 01 frontmatter lists `NyraIntegrationSpec.cpp` as a file it creates, but Plan 03 (commit `2dc2d32`) had already shipped a 48-line version containing two specs (FNyraPluginModulesLoadSpec + FNyraIntegrationSpec).
- **Why preserving is correct:** Plan 01's acceptance criteria for this file are satisfied by Plan 03's version:
  - `#if WITH_AUTOMATION_TESTS && ENABLE_NYRA_INTEGRATION_TESTS` — present (line 33)
  - `BEGIN_DEFINE_SPEC(FNyraIntegrationSpec, "Nyra.Integration"` — present (lines 35–38)
  - `#include "Misc/AutomationTest.h"` + `#include "NyraTestFixtures.h"` + `EAutomationTestFlags::EditorContext` — all present
- **Risk of rewriting:** Would delete `FNyraPluginModulesLoadSpec` which satisfies VALIDATION row 1-01-01 (PLUG-01) and was committed as `test(01-03): add Nyra.Plugin.ModulesLoad automation spec`. Destroying working test coverage for the sake of matching a plan's `files_modified` list would have been a regression.
- **Fix:** Left file untouched. Task 2 acceptance criteria for this file verified against the existing content (all pass).
- **Files modified:** none.
- **Verification:** All 5 grep-level acceptance literals for NyraIntegrationSpec.cpp pass against the unchanged file (see Task 2 verify output).
- **Committed in:** n/a (no change made).

**2. [Rule 1 / non-breaking superset] Upgraded `NyraTestFixtures.h` in place from Plan 03's Rule-3 stub to the full Nyra::Tests namespace**

- **Found during:** Task 1 setup — the file pre-existed (Plan 03 commit `2dc2d32` authored a 14-line minimal stub as a Rule-3 unblocking dependency with an explicit comment: "Plan 01 will replace this file with the full fixture set").
- **Fix:** Replaced the stub body with the full Nyra::Tests fixture namespace, but kept the stub's two unguarded symbols (`#pragma once` + `#include "CoreMinimal.h"`) at the top of the file. The full namespace is now inside `#if WITH_AUTOMATION_TESTS`. Plan 03's `NyraIntegrationSpec.cpp` `#include "NyraTestFixtures.h"` resolves identically before and after.
- **Files modified:** `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTestFixtures.h`.
- **Verification:** All 5 Plan 01 Task 1 acceptance literals pass (`namespace Nyra::Tests`, `class FNyraTempDir`, `class FNyraTestClock`, `FString WriteHandshakeFile`, `#if WITH_AUTOMATION_TESTS`); the two Plan 03 stub symbols (`pragma once`, `CoreMinimal.h`) remain in the file.
- **Committed in:** `35ed37d` (Task 1 commit).

### Platform-gap deferrals (host is macOS, target is Windows)

Per `<runtime_constraints>` in the execution prompt, every UE-compile-gated and UE-automation-execution-gated verify step is deferred to Windows CI:

- **Task 1 verify (compile fixtures under WITH_AUTOMATION_TESTS):** Deferred — macOS host lacks UE 5.6 UBT / MSVC. IDE diagnostic on save ("`CoreMinimal.h` file not found") is expected; the Clangd LSP has no UE SDK include paths. Source-level acceptance criteria all pass via grep.
- **Task 2 verify (spec discovery via `Automation RunTests Nyra.;Quit`):** Deferred — `UnrealEditor-Cmd.exe` is Windows-only. Source-level acceptance criteria all pass via grep.
- **Overall plan verification (enumerate 5 Nyra.* specs without compile error):** Deferred to the first Windows dev-machine open of `TestProject.uproject`, at which point UBT compiles NyraEditor including all six test .cpp files and the automation runner enumerates the specs.

**Total deviations:** 2 non-breaking superset reconciliations with Plan 03's early scaffold + 3 platform-gap deferrals (not deviations per se; mandated by runtime constraints). Zero auto-fixes against bugs in Plan 01 content itself — the plan was followed exactly.

**Impact on plan:** Zero scope creep. Both reconciliations are mechanical: Plan 03 deliberately left work for Plan 01 and flagged it inline (stub file comment + SUMMARY deviation section); Plan 01 is the declared owner and has now completed the upgrade non-destructively.

## Issues Encountered

- **No blockers.** Execution was sequential and uneventful; the two Plan 03 pre-existing files (NyraTestFixtures.h stub + NyraIntegrationSpec.cpp with dual-spec content) were expected and handled as documented above.

## TDD Gate Compliance

Plan 01 is `type: execute` (Wave 0 scaffold), not `type: tdd`. No RED/GREEN/REFACTOR gate applies. The two commits follow conventional-commit types: `feat(...)` for the fixture namespace (new C++ API surface) and `test(...)` for the spec shells (test-file scaffolding). This matches Plan 03's pattern precisely.

## Known Stubs

None introduced by this plan. The spec Define() bodies are empty-but-compilable placeholders with inline comments pointing to the owning plan — these are **intentional Wave 0 scaffolds**, not stubs, and the plan's goal is precisely to land them empty for later waves to populate. No UI surface, no data flow, no user-visible behaviour is being stubbed.

## Threat Flags

No new security-relevant surface introduced. The Nyra::Tests helpers only touch:

- `Intermediate/NyraTests/<guid>/` (writable scratch under the project's intermediate directory)
- Non-networked string builders (MakeJsonRpcRequest returns a string; no transport)

No new auth path, no new file-system access outside Intermediate, no schema change. The D-06 handshake schema referenced by `WriteHandshakeFile` is test-only emission; the real production enforcement happens in Plans 05/06/10.

## Self-Check: PASSED

All claimed files exist on disk:

- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTestFixtures.h` FOUND
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTestFixtures.cpp` FOUND
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraJsonRpcSpec.cpp` FOUND
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraMarkdownSpec.cpp` FOUND
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraSupervisorSpec.cpp` FOUND
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp` FOUND
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/README.md` FOUND

All claimed commits exist in `git log --oneline`:

- `35ed37d` FOUND — Task 1 (fixture namespace superset)
- `ca182ba` FOUND — Task 2 (5 spec shells + README)

## User Setup Required

None — Wave 0 scaffold is source-only. First Windows dev-machine compile of NyraEditor will exercise the fixtures; the first run of `Automation RunTests Nyra.` will enumerate the 6 specs (5 new shells + Plan 03's `FNyraPluginModulesLoadSpec`) and report 2 passing (PLUG-01) + 4 empty-but-valid Define() bodies.

## Next Phase Readiness

- **01-02 (python-pytest-scaffold):** Ready. Parallel Wave 0 deliverable with its own Python-side fixtures; no C++ coupling.
- **01-04 (nomad-tab-placeholder-panel):** Ready. Plan 04's Nyra.Panel.TabSpawner It() block drops into `NyraPanelSpec.cpp::Define()` without touching includes.
- **01-10 (cpp-supervisor-ws-jsonrpc):** Ready. `FNyraSupervisor` ctor accepts a `TFunction<double()>` clock parameter; tests pass `[&Clock]() { return Clock.Now(); }` where `Clock` is a `Nyra::Tests::FNyraTestClock` — explicitly documented inline in `NyraSupervisorSpec.cpp`.
- **01-11 (cpp-markdown-parser):** Ready. Describe/It blocks drop into `NyraMarkdownSpec.cpp::Define()`.
- **01-12 (chat-panel-streaming-integration):** Ready. Nyra.Panel.AttachmentChip + Nyra.Panel.StreamingBuffer both have declared homes in `NyraPanelSpec.cpp` with inline owner-plan comments.

---

*Phase: 01-plugin-shell-three-process-ipc*
*Plan: 01-cpp-automation-scaffold*
*Completed: 2026-04-21*
