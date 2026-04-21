---
phase: 01-plugin-shell-three-process-ipc
plan: 01
type: execute
wave: 0
depends_on: []
autonomous: true
requirements: [PLUG-01, PLUG-02, PLUG-03, CHAT-01]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraJsonRpcSpec.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraMarkdownSpec.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraSupervisorSpec.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraIntegrationSpec.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTestFixtures.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTestFixtures.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/README.md
objective: >
  Create the C++ UE Automation Spec test scaffold under
  Plugins/NYRA/Source/NyraEditor/Private/Tests/. Each spec file contains an
  empty BEGIN_DEFINE_SPEC shell that compiles under WITH_AUTOMATION_TESTS and
  is discoverable by the UE Automation test runner with filter "Nyra.*".
  Later waves fill in the specs. Addresses RESEARCH §"Validation Architecture"
  and VALIDATION.md Wave 0 Requirements (first 5 checklist items).
must_haves:
  truths:
    - UE editor build system compiles NyraEditor with automation tests enabled
    - "Running UnrealEditor-Cmd with -ExecCmds=\"Automation RunTests Nyra\" enumerates all 5 Nyra specs"
    - Each spec file contains at minimum a BEGIN_DEFINE_SPEC macro with a valid hierarchical test path starting "Nyra."
    - NyraIntegrationSpec is guarded by ENABLE_NYRA_INTEGRATION_TESTS (default off)
  artifacts:
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraJsonRpcSpec.cpp
      provides: "JSON-RPC unit test shell, path 'Nyra.Jsonrpc'"
      contains: "BEGIN_DEFINE_SPEC(FNyraJsonRpcSpec, \"Nyra.Jsonrpc\""
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraMarkdownSpec.cpp
      provides: "Markdown parser unit test shell, path 'Nyra.Markdown'"
      contains: "BEGIN_DEFINE_SPEC(FNyraMarkdownSpec, \"Nyra.Markdown\""
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraSupervisorSpec.cpp
      provides: "Supervisor policy test shell, path 'Nyra.Supervisor'"
      contains: "BEGIN_DEFINE_SPEC(FNyraSupervisorSpec, \"Nyra.Supervisor\""
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp
      provides: "Slate widget test shell, path 'Nyra.Panel'"
      contains: "BEGIN_DEFINE_SPEC(FNyraPanelSpec, \"Nyra.Panel\""
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraIntegrationSpec.cpp
      provides: "Integration (E2E) test shell, path 'Nyra.Integration'"
      contains: "#if ENABLE_NYRA_INTEGRATION_TESTS"
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTestFixtures.h
      provides: "Shared test helpers (temp dir, mock clock, handshake helpers)"
      exports: ["FNyraTempDir", "FNyraTestClock"]
  key_links:
    - from: NyraEditor.Build.cs (created in Plan 03)
      to: Private/Tests/*.cpp files
      via: PCHUsage + automation test discovery
      pattern: "bBuildDeveloperTools"
---

<objective>
Create an empty-but-compilable UE Automation Spec scaffold for Phase 1. This
is Wave 0 test infrastructure that must land before any production code, so
later tasks can cite specific test IDs in their acceptance criteria.

Addresses VALIDATION.md rows 1-01-01, 1-02-01, 1-02-02, 1-02-03, 1-04-01,
1-04-02, 1-04-03, 1-04-04, 1-04-05 (all C++ automation/unit tests). Per
CONTEXT.md D-02 and RESEARCH §3.8 the NyraEditor module is editor-only and
the Tests directory lives at Private/Tests/.

Purpose: Wave 0 test scaffold so every executor in Waves 1-5 can add specific
It() blocks without first creating the harness.
Output: 5 .cpp spec files, 1 shared fixture header/impl, 1 README documenting
how to run the suite.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-VALIDATION.md
</context>

<interfaces>
UE Automation Spec canonical pattern (UE 5.6):

```cpp
#include "Misc/AutomationTest.h"

#if WITH_AUTOMATION_TESTS

BEGIN_DEFINE_SPEC(FNyraJsonRpcSpec,
                   "Nyra.Jsonrpc",
                   EAutomationTestFlags::EditorContext |
                   EAutomationTestFlags::EngineFilter)
END_DEFINE_SPEC(FNyraJsonRpcSpec)

void FNyraJsonRpcSpec::Define()
{
    // Describe("Envelope", [this]() { It("encodes/decodes roundtrip", [this]() { ... }); });
    // Filled in by Plan 10 (JSON-RPC implementation).
}

#endif // WITH_AUTOMATION_TESTS
```

Test flags reference (from UE 5.6 `Misc/AutomationTest.h`):
- `EAutomationTestFlags::EditorContext` — runs only in editor builds
- `EAutomationTestFlags::EngineFilter` — enumerated under "Engine Tests"
- `EAutomationTestFlags::ProductFilter` — alternative for product-level tests

Integration spec pattern with guard:

```cpp
#if WITH_AUTOMATION_TESTS && ENABLE_NYRA_INTEGRATION_TESTS

BEGIN_DEFINE_SPEC(FNyraIntegrationSpec,
                   "Nyra.Integration",
                   EAutomationTestFlags::EditorContext |
                   EAutomationTestFlags::ProductFilter)
END_DEFINE_SPEC(FNyraIntegrationSpec)

void FNyraIntegrationSpec::Define() { /* Plan 10 fills */ }

#endif
```
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Create shared test fixtures header + impl</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTestFixtures.h
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTestFixtures.cpp
  </files>
  <read_first>
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.3 (for supervisor clock injection pattern) and §"Validation Architecture" (for Wave 0 Gaps list)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-VALIDATION.md (test ID names in Per-Task Verification Map)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md D-06, D-07, D-08 (handshake + supervisor contracts fixtures emulate)
  </read_first>
  <action>
    Create `NyraTestFixtures.h` declaring:

    ```cpp
    #pragma once

    #include "CoreMinimal.h"
    #include "HAL/PlatformFileManager.h"
    #include "Misc/Paths.h"
    #include "Misc/Guid.h"

    #if WITH_AUTOMATION_TESTS

    namespace Nyra::Tests
    {
        /** RAII temp directory under FPaths::ProjectIntermediateDir()/NyraTests/<guid>/ */
        class FNyraTempDir
        {
        public:
            FNyraTempDir();
            ~FNyraTempDir();
            const FString& Path() const { return DirPath; }
            FString File(const FString& Name) const { return DirPath / Name; }
        private:
            FString DirPath;
        };

        /** Injectable monotonic clock for supervisor 3-in-60s tests (D-08). */
        class FNyraTestClock
        {
        public:
            FNyraTestClock() : NowSeconds(0.0) {}
            void Advance(double Seconds) { NowSeconds += Seconds; }
            void Set(double Seconds) { NowSeconds = Seconds; }
            double Now() const { return NowSeconds; }
        private:
            double NowSeconds;
        };

        /** Write a valid handshake JSON file matching D-06 schema. */
        FString WriteHandshakeFile(
            const FString& Dir,
            int32 EditorPid,
            int32 NyraHostPid,
            int32 Port,
            const FString& Token);

        /** Build a sample JSON-RPC 2.0 request envelope as FString. */
        FString MakeJsonRpcRequest(int64 Id, const FString& Method, const FString& ParamsJson);
    }

    #endif // WITH_AUTOMATION_TESTS
    ```

    Create matching `NyraTestFixtures.cpp` implementing the three helpers using
    `FPlatformFileManager::Get().GetPlatformFile()` for dir create/delete and
    `FFileHelper::SaveStringToFile` for the handshake writer. The handshake
    JSON must match D-06 exactly: `{"port":<port>,"token":"<token>","nyrahost_pid":<pid>,"ue_pid":<pid>,"started_at":<unix-millis>}`.

    `MakeJsonRpcRequest` returns the string:
    `{"jsonrpc":"2.0","id":<id>,"method":"<method>","params":<params>}`.
    No dependencies on not-yet-existing Nyra production headers; only CoreMinimal
    + FFileHelper + FGuid + FDateTime from UE Core.
  </action>
  <verify>
    <automated>
      After Plan 03 creates NyraEditor.Build.cs:
      `UnrealEditor-Cmd.exe TestProject.uproject -ExecCmds="Automation RunTests Nyra.;Quit" -unattended -nopause`
      enumerates specs without compile error. For Wave 0 standalone, verify
      file exists and parses:
      `grep -c "namespace Nyra::Tests" NyraTestFixtures.h` returns 1
    </automated>
  </verify>
  <acceptance_criteria>
    - File NyraTestFixtures.h exists and contains literal text `namespace Nyra::Tests`
    - File NyraTestFixtures.h contains literal text `class FNyraTempDir`
    - File NyraTestFixtures.h contains literal text `class FNyraTestClock`
    - File NyraTestFixtures.h contains literal text `FString WriteHandshakeFile`
    - File NyraTestFixtures.h contains literal text `#if WITH_AUTOMATION_TESTS`
    - File NyraTestFixtures.cpp exists
    - File NyraTestFixtures.cpp contains literal text `FFileHelper::SaveStringToFile`
    - File NyraTestFixtures.cpp contains literal text `"jsonrpc":"2.0"` (the request envelope literal)
    - Neither file includes headers from `Plugins/NYRA/Source/NyraEditor/Public/` that do not yet exist (no production deps)
  </acceptance_criteria>
  <done>Fixtures compile in isolation under WITH_AUTOMATION_TESTS; symbols available to all later spec files.</done>
</task>

<task type="auto">
  <name>Task 2: Create five empty spec files + README</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraJsonRpcSpec.cpp
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraMarkdownSpec.cpp
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraSupervisorSpec.cpp
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraIntegrationSpec.cpp
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/README.md
  </files>
  <read_first>
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTestFixtures.h (created in Task 1)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-VALIDATION.md (test IDs that will live in each spec)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §"Validation Architecture" Wave 0 Gaps list
  </read_first>
  <action>
    Create 5 spec .cpp files, all identical shape except name and test-path.

    NyraJsonRpcSpec.cpp (test path `Nyra.Jsonrpc`):
    ```cpp
    #include "Misc/AutomationTest.h"
    #include "NyraTestFixtures.h"

    #if WITH_AUTOMATION_TESTS

    BEGIN_DEFINE_SPEC(FNyraJsonRpcSpec,
                       "Nyra.Jsonrpc",
                       EAutomationTestFlags::EditorContext |
                       EAutomationTestFlags::EngineFilter)
    END_DEFINE_SPEC(FNyraJsonRpcSpec)

    void FNyraJsonRpcSpec::Define()
    {
        // Plan 10 (FNyraJsonRpc) fills this with:
        //   Describe("EnvelopeRoundtrip", [this]() { It("encodes request correctly", ...); });
        //   Test ID: Nyra.Jsonrpc.EnvelopeRoundtrip (per VALIDATION row 1-02-02)
    }

    #endif // WITH_AUTOMATION_TESTS
    ```

    NyraMarkdownSpec.cpp (test path `Nyra.Markdown`) — placeholder comment references
    test IDs `Nyra.Markdown.FencedCode` and `Nyra.Markdown.InlineFormatting` filled by
    Plan 11.

    NyraSupervisorSpec.cpp (test path `Nyra.Supervisor`) — placeholder comment references
    `Nyra.Supervisor.RestartPolicy` filled by Plan 10; mentions FNyraTestClock
    injection from NyraTestFixtures.h.

    NyraPanelSpec.cpp (test path `Nyra.Panel`) — placeholder for `Nyra.Panel.TabSpawner`
    (Plan 04), `Nyra.Panel.AttachmentChip` (Plan 12), `Nyra.Panel.StreamingBuffer`
    (Plan 12).

    NyraIntegrationSpec.cpp (test path `Nyra.Integration`) — GUARDED with
    `#if WITH_AUTOMATION_TESTS && ENABLE_NYRA_INTEGRATION_TESTS`; references
    `Nyra.Integration.HandshakeAuth` (Plan 10) and `Nyra.Plugin.ModulesLoad`
    (Plan 03 but runs here since it touches both modules).

    README.md content:
    ```markdown
    # NYRA Automation Tests

    Test paths (EAutomationTestFlags::EditorContext):

    - `Nyra.Jsonrpc.*` — unit tests for JSON-RPC 2.0 envelope (Plan 10)
    - `Nyra.Markdown.*` — unit tests for the Slate markdown parser (Plan 11)
    - `Nyra.Supervisor.*` — supervisor 3-in-60s policy w/ FNyraTestClock (Plan 10)
    - `Nyra.Panel.*` — Slate widget / tab spawner tests (Plan 04, 12)
    - `Nyra.Integration.*` — E2E handshake+auth, guarded by ENABLE_NYRA_INTEGRATION_TESTS
    - `Nyra.Plugin.ModulesLoad` — both NyraEditor and NyraRuntime IsModuleLoaded (Plan 03)

    ## Run

    From repo root:
    ```
    UnrealEditor-Cmd.exe TestProject/TestProject.uproject \
        -ExecCmds="Automation RunTests Nyra;Quit" -unattended -nopause \
        -testexit="Automation Test Queue Empty"
    ```

    ## Integration-test opt-in

    Integration specs require a live NyraHost. Enable with a `.Target.cs` flag:
    ```
    GlobalDefinitions.Add("ENABLE_NYRA_INTEGRATION_TESTS=1");
    ```
    Default: off.
    ```
  </action>
  <verify>
    <automated>
      - `grep -l "BEGIN_DEFINE_SPEC" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/*.cpp | wc -l` equals 5
      - `grep -c "\"Nyra.Jsonrpc\"" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraJsonRpcSpec.cpp` equals 1
      - `grep -c "ENABLE_NYRA_INTEGRATION_TESTS" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraIntegrationSpec.cpp` is >= 1
    </automated>
  </verify>
  <acceptance_criteria>
    - File NyraJsonRpcSpec.cpp contains literal text `BEGIN_DEFINE_SPEC(FNyraJsonRpcSpec, "Nyra.Jsonrpc"`
    - File NyraMarkdownSpec.cpp contains literal text `BEGIN_DEFINE_SPEC(FNyraMarkdownSpec, "Nyra.Markdown"`
    - File NyraSupervisorSpec.cpp contains literal text `BEGIN_DEFINE_SPEC(FNyraSupervisorSpec, "Nyra.Supervisor"`
    - File NyraPanelSpec.cpp contains literal text `BEGIN_DEFINE_SPEC(FNyraPanelSpec, "Nyra.Panel"`
    - File NyraIntegrationSpec.cpp contains literal text `#if WITH_AUTOMATION_TESTS && ENABLE_NYRA_INTEGRATION_TESTS`
    - File NyraIntegrationSpec.cpp contains literal text `BEGIN_DEFINE_SPEC(FNyraIntegrationSpec, "Nyra.Integration"`
    - All 5 spec files `#include "Misc/AutomationTest.h"` and `#include "NyraTestFixtures.h"`
    - All 5 spec files contain literal text `EAutomationTestFlags::EditorContext`
    - README.md contains literal text `ENABLE_NYRA_INTEGRATION_TESTS`
    - README.md contains literal text `UnrealEditor-Cmd.exe` (exact run command)
  </acceptance_criteria>
  <done>All five spec files and README are on disk. Each spec discoverable via Nyra.* filter after Plan 03 makes the module buildable.</done>
</task>

</tasks>

<verification>
Phase-level: After Plan 03 makes the module buildable, running
`UnrealEditor-Cmd.exe TestProject/TestProject.uproject -ExecCmds="Automation RunTests Nyra;Quit" -unattended -nopause`
must enumerate 0 failing tests (empty specs pass trivially). This file is a
Wave 0 deliverable and is not expected to run standalone.
</verification>

<success_criteria>
- 5 spec .cpp files + fixtures .h/.cpp + README.md on disk at the exact paths listed
- Every later plan can write It("...") blocks by including NyraTestFixtures.h
- Sampling rate targets (per VALIDATION.md) are achievable: sub-second per Spec after Define() populated
</success_criteria>

<output>
After completion, create `.planning/phases/01-plugin-shell-three-process-ipc/01-01-SUMMARY.md`
documenting file paths, chosen namespace, and the test-ID mapping to later plans.
</output>
