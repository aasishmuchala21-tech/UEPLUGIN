---
phase: 01-plugin-shell-three-process-ipc
plan: 03
type: execute
wave: 1
depends_on: [01]
autonomous: true
requirements: [PLUG-01]
files_modified:
  - TestProject/TestProject.uproject
  - TestProject/.gitignore
  - TestProject/Plugins/NYRA/NYRA.uplugin
  - TestProject/Plugins/NYRA/Resources/Icon128.png
  - TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraEditor.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraEditorModule.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditor.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraLog.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraLog.h
  - TestProject/Plugins/NYRA/Source/NyraRuntime/NyraRuntime.Build.cs
  - TestProject/Plugins/NYRA/Source/NyraRuntime/Public/NyraRuntime.h
  - TestProject/Plugins/NYRA/Source/NyraRuntime/Private/NyraRuntime.cpp
  - TestProject/Plugins/NYRA/README.md
  - docs/BINARY_DISTRIBUTION.md
objective: >
  Create the greenfield UE 5.6 test host project at TestProject/ and the NYRA
  plugin skeleton as two modules (NyraEditor editor-only, NyraRuntime minimal
  runtime stub) per D-02. Lock binary-artefact distribution strategy in
  docs/BINARY_DISTRIBUTION.md. Plugin loads cleanly into a freshly-generated
  UE 5.6 editor; both modules call FDefaultModuleImpl / FNyraEditorModule
  StartupModule/ShutdownModule (empty bodies other than logging). Addresses
  PLUG-01, D-01, D-02, D-03 (UE 5.6 only), D-13 (embedded Python layout
  reserved), RESEARCH §3.8 (.uplugin + Build.cs + RuntimeDependencies).
must_haves:
  truths:
    - Opening TestProject/TestProject.uproject in UE 5.6 succeeds with NYRA plugin enabled and no module-load errors
    - Both modules appear in `Editor -> Plugins` pane (NyraEditor type=Editor, NyraRuntime type=Runtime) and are enabled
    - `Nyra.Plugin.ModulesLoad` automation test passes (both FModuleManager::Get().IsModuleLoaded return true)
    - NyraEditor.Build.cs declares PublicDependencyModuleNames including WebSockets, HTTP, Json, JsonUtilities, Slate, SlateCore, UnrealEd, ToolMenus, Projects, DesktopPlatform, ApplicationCore
    - NyraEditor.Build.cs stages Binaries/Win64/NyraHost and Binaries/Win64/NyraInfer via RuntimeDependencies (even though those folders are empty in Plan 03; Plans 06/08 populate them)
    - Binary distribution strategy is documented (build-time prebuild.ps1 downloading + committing via Git LFS as escape hatch)
    - TestProject/.gitignore excludes Binaries/, Intermediate/, DerivedDataCache/, Saved/ (build artefacts, NOT the plugin's Binaries/Win64/ which is staged content)
  artifacts:
    - path: TestProject/TestProject.uproject
      provides: "UE 5.6 test host project descriptor enabling NYRA plugin"
      contains: "\"EngineAssociation\": \"5.6\""
    - path: TestProject/Plugins/NYRA/NYRA.uplugin
      provides: "Plugin manifest with two modules, FileVersion 3, EngineVersion 5.6.0"
      contains: "\"EngineVersion\": \"5.6.0\""
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs
      provides: "NyraEditor build rules + RuntimeDependencies + automation test flag"
      contains: "bBuildDeveloperTools"
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp
      provides: "FNyraEditorModule with StartupModule/ShutdownModule hooks"
      contains: "IMPLEMENT_MODULE(FNyraEditorModule, NyraEditor)"
    - path: TestProject/Plugins/NYRA/Source/NyraRuntime/Private/NyraRuntime.cpp
      provides: "FDefaultModuleImpl runtime stub (Phase 1: empty)"
      contains: "IMPLEMENT_MODULE(FDefaultModuleImpl, NyraRuntime)"
    - path: docs/BINARY_DISTRIBUTION.md
      provides: "Canonical decision record: Git LFS + prebuild.ps1"
      contains: "Build-time download via prebuild.ps1"
  key_links:
    - from: TestProject/TestProject.uproject
      to: TestProject/Plugins/NYRA/NYRA.uplugin
      via: "Plugins array with Name: NYRA Enabled: true"
      pattern: "\"Name\": \"NYRA\""
    - from: NyraEditor.Build.cs
      to: TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/ (Plan 01)
      via: bBuildDeveloperTools enables automation discovery
      pattern: "bBuildDeveloperTools = true"
---

<objective>
Greenfield UE 5.6 project + NYRA plugin two-module skeleton. This is the
structural backbone every later plan writes into. Nothing here connects to
a sidecar yet; that lands in Plan 06. Binary-artefact strategy is LOCKED here
(Wave 1) so Plans 06-09 know whether to commit wheels/CPython via LFS or
fetch at build time.

**Binary Distribution Strategy (LOCKED in this plan):**
- **Build-time downloaded** by `TestProject/Plugins/NYRA/prebuild.ps1` invoked from an `ExternalBuildTool`-style step in NyraEditor.Build.cs on first compile.
- Artefacts live under `TestProject/Plugins/NYRA/Binaries/Win64/` AFTER prebuild runs.
- Git tracks only: the prebuild.ps1 script, manifest JSON with URLs + SHA256s.
- `.gitignore` excludes `Plugins/NYRA/Binaries/Win64/NyraHost/cpython/` + `Plugins/NYRA/Binaries/Win64/NyraInfer/`.
- **Escape hatch for Fab packaging**: once Phase 1 stabilises, migrate to Git LFS for reproducible Fab CI (documented in docs/BINARY_DISTRIBUTION.md but deferred to Phase 2).

Addresses:
- PLUG-01 (plugin ships as C++ two-module plugin for UE 5.4-5.7; Phase 1 = 5.6 only per D-03)
- D-01 (three-process architecture — Plan 03 only creates module 1/3 structure)
- D-02 (two modules NyraEditor editor-only + NyraRuntime minimal)
- D-03 (Phase 1 = UE 5.6 only)
- D-13 (embedded CPython path reserved at Binaries/Win64/NyraHost/cpython/)
- CONTEXT.md §code_context (Plugin lives at TestProject/Plugins/NYRA/ under a UE 5.6 test host)
- RESEARCH §3.2 (NyraEditor.Build.cs deps), §3.8 (.uplugin + RuntimeDependencies)

Purpose: Every later C++ plan writes into this directory skeleton.
Output: Openable UE 5.6 project, plugin visible in Plugins panel, first
automation test `Nyra.Plugin.ModulesLoad` passes.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/REQUIREMENTS.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-VALIDATION.md
</context>

<interfaces>
.uplugin v3 exact structure (RESEARCH §3.8):

```json
{
    "FileVersion": 3,
    "Version": 1,
    "VersionName": "0.1.0",
    "FriendlyName": "NYRA",
    "Description": "Turn a reference into a finished Unreal Engine scene — without a new AI bill.",
    "Category": "AI",
    "CreatedBy": "NYRA",
    "CreatedByURL": "https://nyra.ai",
    "DocsURL": "https://nyra.ai/docs",
    "MarketplaceURL": "",
    "SupportURL": "https://nyra.ai/support",
    "EngineVersion": "5.6.0",
    "CanContainContent": false,
    "IsBetaVersion": true,
    "IsExperimentalVersion": false,
    "Installed": false,
    "Modules": [
        { "Name": "NyraEditor",  "Type": "Editor",  "LoadingPhase": "PostEngineInit", "PlatformAllowList": ["Win64"] },
        { "Name": "NyraRuntime", "Type": "Runtime", "LoadingPhase": "Default",        "PlatformAllowList": ["Win64"] }
    ],
    "Plugins": [
        { "Name": "WebSockets", "Enabled": true }
    ]
}
```

.uproject descriptor (UE 5.6) expected shape:

```json
{
    "FileVersion": 3,
    "EngineAssociation": "5.6",
    "Category": "",
    "Description": "NYRA test host project",
    "Modules": [
        { "Name": "TestProject", "Type": "Runtime", "LoadingPhase": "Default" }
    ],
    "Plugins": [
        { "Name": "NYRA", "Enabled": true }
    ]
}
```

Note: This plan does NOT create a C++ target for TestProject itself (blank
Blueprint project shell that only exists to host the plugin). If UBT requires
a Source/TestProject/ to compile the plugin, add a minimal empty module.
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Greenfield test host project + .gitignore + binary distribution decision doc</name>
  <files>
    TestProject/TestProject.uproject
    TestProject/.gitignore
    docs/BINARY_DISTRIBUTION.md
  </files>
  <read_first>
    - .planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md §code_context ("greenfield UE plugin ... TestProject/") and §specifics
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.8 (.uplugin format), §3.4 (CPython layout)
    - CLAUDE.md (GSD workflow enforcement — avoid direct edits outside workflow)
  </read_first>
  <action>
    Create `TestProject/TestProject.uproject` with exact content from
    `<interfaces>` block (FileVersion 3, EngineAssociation "5.6", Modules array
    with one `TestProject` Runtime module, Plugins array enabling `NYRA`).

    Create `TestProject/.gitignore` containing exactly:
    ```
    # UE build artefacts
    /Binaries/
    /Intermediate/
    /DerivedDataCache/
    /Saved/
    *.sln
    *.VC.db
    *.opendb
    *.suo
    .vs/

    # Plugin binary artefacts (fetched by prebuild.ps1, NOT committed)
    /Plugins/NYRA/Binaries/Win64/NyraHost/cpython/
    /Plugins/NYRA/Binaries/Win64/NyraHost/wheels/
    /Plugins/NYRA/Binaries/Win64/NyraInfer/

    # Plugin-build outputs (compiled DLLs)
    /Plugins/NYRA/Binaries/Win64/UnrealEditor-*.dll
    /Plugins/NYRA/Binaries/Win64/UnrealEditor-*.pdb
    /Plugins/NYRA/Intermediate/
    ```

    Create `docs/BINARY_DISTRIBUTION.md` documenting the chosen strategy:
    ```markdown
    # NYRA Binary Distribution Strategy

    **Locked in Phase 1 Plan 03.** Revisit in Phase 8 before Fab submission.

    ## The Problem

    NYRA ships ~200 MB of non-UE binary artefacts:
    - `Plugins/NYRA/Binaries/Win64/NyraHost/cpython/` — python-build-standalone CPython 3.12 Windows x64 (~120 MB installed)
    - `Plugins/NYRA/Binaries/Win64/NyraHost/wheels/` — pre-resolved wheel cache for Phase 1 deps (~10 MB)
    - `Plugins/NYRA/Binaries/Win64/NyraInfer/cuda/llama-server.exe` (~25 MB)
    - `Plugins/NYRA/Binaries/Win64/NyraInfer/vulkan/llama-server.exe` (~20 MB)
    - `Plugins/NYRA/Binaries/Win64/NyraInfer/cpu/llama-server.exe` (~15 MB)

    Three options considered:

    | Option | Pros | Cons | Decision |
    |--------|------|------|----------|
    | Commit via Git LFS | Reproducible; Fab-CI friendly | Requires LFS pointer config; free LFS quotas small | Phase 2 migration target |
    | Bootstrap-downloaded on first launch | Small repo; user-visible progress | Offline-hostile; first-launch 200 MB hit; trust issue on enterprise | Rejected |
    | **Build-time downloaded by prebuild.ps1** | Small repo; dev machine fetches once; developer-facing | Requires PowerShell on Windows build hosts | **CHOSEN for Phase 1** |

    ## Phase 1 Implementation

    1. `TestProject/Plugins/NYRA/prebuild.ps1` (created in Plan 06) reads a manifest:
       ```
       TestProject/Plugins/NYRA/Source/NyraHost/assets-manifest.json
       ```
       which lists `{url, sha256, dest}` triples for each artefact.
    2. NyraEditor.Build.cs invokes prebuild.ps1 via an `ExternalDependencies`
       entry OR a conditional-on-missing-files pre-build step in a custom
       `NyraEditor.Target.cs` override.
    3. After prebuild, `RuntimeDependencies.Add(...)` includes every file under
       `Binaries/Win64/NyraHost/` and `Binaries/Win64/NyraInfer/` for
       packaging.

    ## Phase 8 Migration (Fab Prep)

    Switch to Git LFS with tracked `.gitattributes`:
    ```
    Plugins/NYRA/Binaries/Win64/NyraHost/cpython/** filter=lfs diff=lfs merge=lfs -text
    Plugins/NYRA/Binaries/Win64/NyraInfer/** filter=lfs diff=lfs merge=lfs -text
    ```
    Rationale: Fab packaging pipeline must reproduce builds without external
    network fetches; LFS gives us this.
    ```
  </action>
  <verify>
    <automated>
      - `test -f TestProject/TestProject.uproject` (file exists)
      - `grep -c '"EngineAssociation": "5.6"' TestProject/TestProject.uproject` equals 1
      - `grep -c '"Name": "NYRA"' TestProject/TestProject.uproject` equals 1
      - `grep -c "/Binaries/" TestProject/.gitignore` >= 1
      - `grep -c "cpython/" TestProject/.gitignore` == 1
      - `test -f docs/BINARY_DISTRIBUTION.md`
      - `grep -c "prebuild.ps1" docs/BINARY_DISTRIBUTION.md` >= 2
    </automated>
  </verify>
  <acceptance_criteria>
    - File TestProject/TestProject.uproject contains literal text `"EngineAssociation": "5.6"`
    - File TestProject/TestProject.uproject contains literal text `"Name": "NYRA"` within a Plugins array with `"Enabled": true`
    - File TestProject/TestProject.uproject contains literal text `"FileVersion": 3`
    - File TestProject/.gitignore contains literal text `/Plugins/NYRA/Binaries/Win64/NyraHost/cpython/`
    - File TestProject/.gitignore contains literal text `/Plugins/NYRA/Binaries/Win64/NyraInfer/`
    - File TestProject/.gitignore contains literal text `/Intermediate/`
    - File docs/BINARY_DISTRIBUTION.md contains literal text `Build-time download via prebuild.ps1` OR `Build-time downloaded by prebuild.ps1`
    - File docs/BINARY_DISTRIBUTION.md contains literal text `Git LFS` (Phase 8 migration mention)
    - File docs/BINARY_DISTRIBUTION.md contains literal text `assets-manifest.json`
  </acceptance_criteria>
  <done>Test host project descriptor + gitignore + distribution decision record on disk.</done>
</task>

<task type="auto">
  <name>Task 2: NYRA.uplugin + Resources icon placeholder + plugin README</name>
  <files>
    TestProject/Plugins/NYRA/NYRA.uplugin
    TestProject/Plugins/NYRA/Resources/Icon128.png
    TestProject/Plugins/NYRA/README.md
  </files>
  <read_first>
    - TestProject/TestProject.uproject (just created)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.8 for the exact JSON
    - .planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md D-02, D-03
  </read_first>
  <action>
    Create `TestProject/Plugins/NYRA/NYRA.uplugin` with EXACT content from the
    `<interfaces>` block above. Fields:
    - `"FileVersion": 3`
    - `"Version": 1`
    - `"VersionName": "0.1.0"`
    - `"FriendlyName": "NYRA"`
    - `"Description": "Turn a reference into a finished Unreal Engine scene — without a new AI bill."`
    - `"Category": "AI"`
    - `"CreatedBy": "NYRA"`
    - `"EngineVersion": "5.6.0"` (D-03: UE 5.6 only in Phase 1)
    - `"CanContainContent": false`
    - `"IsBetaVersion": true`
    - `"Installed": false`
    - Modules: two entries — NyraEditor (Editor, PostEngineInit, Win64) and NyraRuntime (Runtime, Default, Win64)
    - Plugins: `[{ "Name": "WebSockets", "Enabled": true }]` (required by Plan 10 and locked by D-09)

    Create `TestProject/Plugins/NYRA/Resources/Icon128.png`: a 128x128
    placeholder PNG. Use any existing transparent 128x128 PNG, or generate a
    solid-colour PNG with ImageMagick/PowerShell:
    ```powershell
    Add-Type -AssemblyName System.Drawing
    $bmp = New-Object System.Drawing.Bitmap 128, 128
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.Clear([System.Drawing.Color]::FromArgb(255, 30, 30, 40))
    $g.DrawString("NYRA", (New-Object System.Drawing.Font("Arial", 24)), [System.Drawing.Brushes]::White, 20, 48)
    $bmp.Save("TestProject/Plugins/NYRA/Resources/Icon128.png")
    ```
    File must be a valid PNG (magic bytes `89 50 4E 47`).

    Create `TestProject/Plugins/NYRA/README.md`:
    ```markdown
    # NYRA — Unreal Engine 5 Plugin

    Free UE5 plugin (Fab distribution) that drives the user's Claude subscription
    via three-process architecture. See `.planning/PROJECT.md` for the full vision.

    ## Phase 1 Scope

    Plugin shell + three-process IPC skeleton on UE 5.6. No subscription driving yet
    (Phase 2). Modules:

    - `NyraEditor` (Editor-only, PostEngineInit): Slate chat panel, WebSocket client,
      NyraHost supervisor, `Nyra.Dev.*` console commands.
    - `NyraRuntime` (Runtime, Default): empty stub. Future home of runtime-world
      hooks.

    ## Build

    1. Open `TestProject/TestProject.uproject` — UE prompts to rebuild the plugin
       the first time.
    2. Compile succeeds → plugin appears under `Edit -> Plugins -> AI -> NYRA`.
    3. Chat tab: `Tools -> NYRA -> Chat` (added in Plan 04).

    ## Dependencies

    - UE 5.6 (Phase 1 locked; UE 5.4/5.5/5.7 CI in Phase 2 per D-03)
    - MSVC v143 (Visual Studio 2022 17.8+)
    - Windows 10 22H2+ / Windows 11
    ```
  </action>
  <verify>
    <automated>
      - `grep -c '"FileVersion": 3' TestProject/Plugins/NYRA/NYRA.uplugin` equals 1
      - `grep -c '"EngineVersion": "5.6.0"' TestProject/Plugins/NYRA/NYRA.uplugin` equals 1
      - `grep -c '"Name": "NyraEditor"' TestProject/Plugins/NYRA/NYRA.uplugin` equals 1
      - `grep -c '"Name": "NyraRuntime"' TestProject/Plugins/NYRA/NYRA.uplugin` equals 1
      - `grep -c '"Name": "WebSockets"' TestProject/Plugins/NYRA/NYRA.uplugin` equals 1
      - `grep -c '"LoadingPhase": "PostEngineInit"' TestProject/Plugins/NYRA/NYRA.uplugin` equals 1
      - `xxd TestProject/Plugins/NYRA/Resources/Icon128.png | head -1 | grep "8950 4e47"` matches (PNG magic)
    </automated>
  </verify>
  <acceptance_criteria>
    - File NYRA.uplugin contains literal text `"FileVersion": 3`
    - File NYRA.uplugin contains literal text `"EngineVersion": "5.6.0"`
    - File NYRA.uplugin contains literal text `"Name": "NyraEditor"` AND literal text `"Type": "Editor"` AND literal text `"LoadingPhase": "PostEngineInit"`
    - File NYRA.uplugin contains literal text `"Name": "NyraRuntime"` AND `"Type": "Runtime"`
    - File NYRA.uplugin contains literal text `"PlatformAllowList": ["Win64"]` for BOTH modules
    - File NYRA.uplugin contains literal text `"Name": "WebSockets"` with `"Enabled": true`
    - File Resources/Icon128.png exists AND `file TestProject/Plugins/NYRA/Resources/Icon128.png` output contains "PNG image data" AND dimensions 128x128
    - File README.md contains literal text `Tools -> NYRA -> Chat`
  </acceptance_criteria>
  <done>.uplugin descriptor valid per Epic schema; icon loads in Plugins browser; plugin metadata visible.</done>
</task>

<task type="auto">
  <name>Task 3: NyraEditor module (Build.cs + module source)</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs
    TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraEditor.h
    TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraEditorModule.h
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditor.cpp
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp
    TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraLog.h
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraLog.cpp
  </files>
  <read_first>
    - TestProject/Plugins/NYRA/NYRA.uplugin (just created)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.2 (exact Build.cs PublicDependencyModuleNames list) and §3.8 (RuntimeDependencies staging pattern)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md D-04, D-05 (lifecycle hooks; Plan 10 fills actual supervisor)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTestFixtures.h (from Plan 01; automation flag must be enabled)
  </read_first>
  <action>
    Create `NyraEditor.Build.cs` containing EXACTLY (module declaration with the
    full dependency list from RESEARCH §3.2):

    ```csharp
    // Copyright NYRA. All rights reserved.
    using UnrealBuildTool;
    using System.IO;

    public class NyraEditor : ModuleRules
    {
        public NyraEditor(ReadOnlyTargetRules Target) : base(Target)
        {
            PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
            bUseUnity = false;
            DefaultBuildSettings = BuildSettingsVersion.V5;
            CppStandard = CppStandardVersion.Cpp20;

            PublicIncludePaths.Add(Path.Combine(ModuleDirectory, "Public"));
            PrivateIncludePaths.Add(Path.Combine(ModuleDirectory, "Private"));

            PublicDependencyModuleNames.AddRange(new string[]
            {
                "Core",
                "CoreUObject",
                "Engine",
                "InputCore",
                "Slate",
                "SlateCore",
                "EditorStyle",
                "EditorSubsystem",
                "UnrealEd",
                "ToolMenus",
                "Projects",
                "Json",
                "JsonUtilities",
                "WebSockets",
                "HTTP",
                "DesktopPlatform",
                "ApplicationCore",
            });

            PrivateDependencyModuleNames.AddRange(new string[]
            {
                "WorkspaceMenuStructure",
                "MainFrame",
                "LevelEditor",
            });

            // Stage NyraHost + NyraInfer binaries when the plugin is packaged.
            // Folders may be empty in Plan 03; Plans 06 and 08 populate them.
            if (Target.Platform == UnrealTargetPlatform.Win64)
            {
                string PluginBinariesDir = Path.Combine(PluginDirectory, "Binaries", "Win64");

                string NyraHostDir = Path.Combine(PluginBinariesDir, "NyraHost");
                if (Directory.Exists(NyraHostDir))
                {
                    foreach (string F in Directory.GetFiles(NyraHostDir, "*", SearchOption.AllDirectories))
                    {
                        RuntimeDependencies.Add(F);
                    }
                }

                string NyraInferDir = Path.Combine(PluginBinariesDir, "NyraInfer");
                if (Directory.Exists(NyraInferDir))
                {
                    foreach (string F in Directory.GetFiles(NyraInferDir, "*", SearchOption.AllDirectories))
                    {
                        RuntimeDependencies.Add(F);
                    }
                }
            }
        }
    }
    ```

    Note `bBuildDeveloperTools` is NOT set here — for editor targets UBT
    enables `WITH_AUTOMATION_TESTS` by default. Confirm empirically in Task 5.
    If automation tests don't link, add: `PublicDefinitions.Add("WITH_AUTOMATION_TESTS=1");`
    inside the `Target.Configuration == UnrealTargetConfiguration.Debug || Target.Configuration == UnrealTargetConfiguration.Development` guard.

    Create `Public/NyraLog.h`:
    ```cpp
    #pragma once
    #include "CoreMinimal.h"
    #include "Logging/LogMacros.h"

    NYRAEDITOR_API DECLARE_LOG_CATEGORY_EXTERN(LogNyra, Log, All);
    ```

    Create `Private/NyraLog.cpp`:
    ```cpp
    #include "NyraLog.h"
    DEFINE_LOG_CATEGORY(LogNyra);
    ```

    Create `Public/NyraEditor.h`:
    ```cpp
    #pragma once
    #include "CoreMinimal.h"
    ```
    (empty public header reserved for later)

    Create `Public/NyraEditorModule.h`:
    ```cpp
    #pragma once
    #include "CoreMinimal.h"
    #include "Modules/ModuleInterface.h"

    class NYRAEDITOR_API FNyraEditorModule : public IModuleInterface
    {
    public:
        virtual void StartupModule() override;
        virtual void ShutdownModule() override;

        static FNyraEditorModule& Get();
        static bool IsAvailable();
    };
    ```

    Create `Private/NyraEditor.cpp`:
    ```cpp
    #include "NyraEditor.h"
    // Empty — module implementation lives in NyraEditorModule.cpp
    ```

    Create `Private/NyraEditorModule.cpp`:
    ```cpp
    #include "NyraEditorModule.h"
    #include "NyraLog.h"
    #include "Modules/ModuleManager.h"

    IMPLEMENT_MODULE(FNyraEditorModule, NyraEditor)

    void FNyraEditorModule::StartupModule()
    {
        UE_LOG(LogNyra, Log, TEXT("[NYRA] NyraEditor module starting (Phase 1 skeleton)"));
        // Plan 04: RegisterTabSpawner("NyraChatTab", ...)
        // Plan 10: FNyraSupervisor::Get().SpawnNyraHost()
    }

    void FNyraEditorModule::ShutdownModule()
    {
        UE_LOG(LogNyra, Log, TEXT("[NYRA] NyraEditor module shutting down"));
        // Plan 04: UnregisterTabSpawner("NyraChatTab")
        // Plan 10: FNyraSupervisor::Get().ShutdownNyraHost()
    }

    FNyraEditorModule& FNyraEditorModule::Get()
    {
        return FModuleManager::LoadModuleChecked<FNyraEditorModule>("NyraEditor");
    }

    bool FNyraEditorModule::IsAvailable()
    {
        return FModuleManager::Get().IsModuleLoaded("NyraEditor");
    }
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "\"WebSockets\"" TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs` equals 1
      - `grep -c "\"HTTP\"" TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs` equals 1
      - `grep -c "\"ToolMenus\"" TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs` equals 1
      - `grep -c "\"DesktopPlatform\"" TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs` equals 1
      - `grep -c "RuntimeDependencies.Add" TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs` >= 2
      - `grep -c "IMPLEMENT_MODULE(FNyraEditorModule, NyraEditor)" TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp` equals 1
      - `grep -c "DEFINE_LOG_CATEGORY(LogNyra)" TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraLog.cpp` equals 1
    </automated>
  </verify>
  <acceptance_criteria>
    - File NyraEditor.Build.cs contains literal text `public class NyraEditor : ModuleRules`
    - File NyraEditor.Build.cs contains literal text `"Core"`, `"CoreUObject"`, `"Engine"`, `"Slate"`, `"SlateCore"`, `"UnrealEd"`, `"ToolMenus"`, `"Projects"`, `"Json"`, `"JsonUtilities"`, `"WebSockets"`, `"HTTP"`, `"DesktopPlatform"`, `"ApplicationCore"` (all in PublicDependencyModuleNames.AddRange)
    - File NyraEditor.Build.cs contains literal text `"WorkspaceMenuStructure"` AND `"MainFrame"` AND `"LevelEditor"` (in PrivateDependencyModuleNames)
    - File NyraEditor.Build.cs contains literal text `RuntimeDependencies.Add`
    - File NyraEditor.Build.cs contains literal text `CppStandard = CppStandardVersion.Cpp20`
    - File NyraEditor.Build.cs contains literal text `"NyraHost"` AND `"NyraInfer"` (the staging paths)
    - File Public/NyraLog.h contains literal text `DECLARE_LOG_CATEGORY_EXTERN(LogNyra`
    - File Private/NyraLog.cpp contains literal text `DEFINE_LOG_CATEGORY(LogNyra)`
    - File Private/NyraEditorModule.cpp contains literal text `IMPLEMENT_MODULE(FNyraEditorModule, NyraEditor)`
    - File Private/NyraEditorModule.cpp contains literal text `FModuleManager::LoadModuleChecked<FNyraEditorModule>("NyraEditor")`
    - File Public/NyraEditorModule.h contains literal text `class NYRAEDITOR_API FNyraEditorModule : public IModuleInterface`
    - File Public/NyraEditorModule.h contains literal text `virtual void StartupModule() override`
    - File Public/NyraEditorModule.h contains literal text `virtual void ShutdownModule() override`
  </acceptance_criteria>
  <done>NyraEditor module compiles with UE 5.6 UBT; StartupModule/ShutdownModule log entries visible on editor launch.</done>
</task>

<task type="auto">
  <name>Task 4: NyraRuntime module (minimal FDefaultModuleImpl stub)</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraRuntime/NyraRuntime.Build.cs
    TestProject/Plugins/NYRA/Source/NyraRuntime/Public/NyraRuntime.h
    TestProject/Plugins/NYRA/Source/NyraRuntime/Private/NyraRuntime.cpp
  </files>
  <read_first>
    - TestProject/Plugins/NYRA/NYRA.uplugin (module entry `NyraRuntime`)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md D-02 ("empty FDefaultModuleImpl in Phase 1")
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.2 (NyraRuntime.Build.cs example)
  </read_first>
  <action>
    Create `NyraRuntime.Build.cs`:
    ```csharp
    // Copyright NYRA. All rights reserved.
    using UnrealBuildTool;
    using System.IO;

    public class NyraRuntime : ModuleRules
    {
        public NyraRuntime(ReadOnlyTargetRules Target) : base(Target)
        {
            PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
            DefaultBuildSettings = BuildSettingsVersion.V5;
            CppStandard = CppStandardVersion.Cpp20;

            PublicIncludePaths.Add(Path.Combine(ModuleDirectory, "Public"));
            PrivateIncludePaths.Add(Path.Combine(ModuleDirectory, "Private"));

            PublicDependencyModuleNames.AddRange(new string[]
            {
                "Core",
                "CoreUObject",
                "Engine",
            });
        }
    }
    ```

    Create `Public/NyraRuntime.h`:
    ```cpp
    #pragma once
    #include "CoreMinimal.h"
    // Phase 1: runtime module is an empty placeholder. Reserved for v2 runtime-world
    // features (in-game dev console chat, etc.) per CONTEXT.md §deferred.
    ```

    Create `Private/NyraRuntime.cpp`:
    ```cpp
    #include "NyraRuntime.h"
    #include "Modules/ModuleManager.h"

    IMPLEMENT_MODULE(FDefaultModuleImpl, NyraRuntime)
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "public class NyraRuntime : ModuleRules" TestProject/Plugins/NYRA/Source/NyraRuntime/NyraRuntime.Build.cs` equals 1
      - `grep -c "IMPLEMENT_MODULE(FDefaultModuleImpl, NyraRuntime)" TestProject/Plugins/NYRA/Source/NyraRuntime/Private/NyraRuntime.cpp` equals 1
    </automated>
  </verify>
  <acceptance_criteria>
    - File NyraRuntime.Build.cs contains literal text `public class NyraRuntime : ModuleRules`
    - File NyraRuntime.Build.cs contains literal text `"Core"`, `"CoreUObject"`, `"Engine"` in PublicDependencyModuleNames
    - File NyraRuntime.Build.cs contains literal text `CppStandard = CppStandardVersion.Cpp20`
    - File Private/NyraRuntime.cpp contains literal text `IMPLEMENT_MODULE(FDefaultModuleImpl, NyraRuntime)`
    - File Public/NyraRuntime.h exists and contains literal text `#pragma once`
  </acceptance_criteria>
  <done>NyraRuntime compiles as FDefaultModuleImpl — zero behaviour, zero extra deps beyond Core/CoreUObject/Engine.</done>
</task>

<task type="auto">
  <name>Task 5: Nyra.Plugin.ModulesLoad automation test</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraIntegrationSpec.cpp
  </files>
  <read_first>
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraIntegrationSpec.cpp (created in Plan 01 as empty)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp (just created)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-VALIDATION.md row 1-01-01 (Nyra.Plugin.ModulesLoad)
  </read_first>
  <action>
    Replace the placeholder NyraIntegrationSpec.cpp body with a concrete test.
    Add a SECOND non-guarded spec `Nyra.Plugin.ModulesLoad` (NOT integration-test
    gated — modules-load is pure unit-level automation that runs on every dev
    machine). Keep the existing integration-test-guarded `Nyra.Integration.*` spec
    stub untouched (Plan 10 fills it).

    Resulting file structure:

    ```cpp
    #include "Misc/AutomationTest.h"
    #include "NyraTestFixtures.h"
    #include "Modules/ModuleManager.h"

    #if WITH_AUTOMATION_TESTS

    BEGIN_DEFINE_SPEC(FNyraPluginModulesLoadSpec,
                       "Nyra.Plugin",
                       EAutomationTestFlags::EditorContext |
                       EAutomationTestFlags::EngineFilter)
    END_DEFINE_SPEC(FNyraPluginModulesLoadSpec)

    void FNyraPluginModulesLoadSpec::Define()
    {
        Describe("ModulesLoad", [this]()
        {
            It("NyraEditor module is loaded", [this]()
            {
                TestTrue(TEXT("NyraEditor module loaded"),
                         FModuleManager::Get().IsModuleLoaded(TEXT("NyraEditor")));
            });
            It("NyraRuntime module is loaded", [this]()
            {
                TestTrue(TEXT("NyraRuntime module loaded"),
                         FModuleManager::Get().IsModuleLoaded(TEXT("NyraRuntime")));
            });
        });
    }

    #endif // WITH_AUTOMATION_TESTS

    // Integration spec (guarded — requires live NyraHost; Plan 10 fills Define body)
    #if WITH_AUTOMATION_TESTS && ENABLE_NYRA_INTEGRATION_TESTS

    BEGIN_DEFINE_SPEC(FNyraIntegrationSpec,
                       "Nyra.Integration",
                       EAutomationTestFlags::EditorContext |
                       EAutomationTestFlags::ProductFilter)
    END_DEFINE_SPEC(FNyraIntegrationSpec)

    void FNyraIntegrationSpec::Define()
    {
        // Plan 10 populates: Describe("HandshakeAuth", ...) — test ID Nyra.Integration.HandshakeAuth (VALIDATION row 1-02-01)
    }

    #endif
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "BEGIN_DEFINE_SPEC(FNyraPluginModulesLoadSpec" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraIntegrationSpec.cpp` equals 1
      - `grep -c "IsModuleLoaded(TEXT(\"NyraEditor\"))" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraIntegrationSpec.cpp` equals 1
      - `grep -c "IsModuleLoaded(TEXT(\"NyraRuntime\"))" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraIntegrationSpec.cpp` equals 1
      - After building TestProject: `UnrealEditor-Cmd.exe TestProject/TestProject.uproject -ExecCmds="Automation RunTests Nyra.Plugin;Quit" -unattended -nopause -testexit="Automation Test Queue Empty"` passes with 2 tests green
    </automated>
  </verify>
  <acceptance_criteria>
    - File NyraIntegrationSpec.cpp contains literal text `BEGIN_DEFINE_SPEC(FNyraPluginModulesLoadSpec,` followed by literal text `"Nyra.Plugin"`
    - File NyraIntegrationSpec.cpp contains literal text `Describe("ModulesLoad"`
    - File NyraIntegrationSpec.cpp contains literal text `It("NyraEditor module is loaded"`
    - File NyraIntegrationSpec.cpp contains literal text `It("NyraRuntime module is loaded"`
    - File NyraIntegrationSpec.cpp contains literal text `IsModuleLoaded(TEXT("NyraEditor"))`
    - File NyraIntegrationSpec.cpp contains literal text `IsModuleLoaded(TEXT("NyraRuntime"))`
    - File NyraIntegrationSpec.cpp preserves the integration-test guard `#if WITH_AUTOMATION_TESTS && ENABLE_NYRA_INTEGRATION_TESTS` for the Plan 10 portion
    - Running `UnrealEditor-Cmd.exe TestProject/TestProject.uproject -ExecCmds="Automation RunTests Nyra.Plugin;Quit" -unattended -nopause -testexit="Automation Test Queue Empty"` exits 0 with 2 tests passing
  </acceptance_criteria>
  <done>Both modules load; `Nyra.Plugin.ModulesLoad` reports PASS; PLUG-01 requirement verifiable.</done>
</task>

</tasks>

<verification>
End-to-end: `UnrealEditor-Cmd.exe TestProject/TestProject.uproject -ExecCmds="Automation RunTests Nyra.Plugin;Quit" -unattended -nopause -testexit="Automation Test Queue Empty"` → exit 0, 2 tests PASS.
Manual: Open TestProject.uproject in UE 5.6 editor → plugin appears in Plugins browser under "AI" category, both modules show as enabled.
</verification>

<success_criteria>
- Both modules compile on UE 5.6 with MSVC v143
- Nyra.Plugin.ModulesLoad automation test passes (VALIDATION 1-01-01 green)
- RuntimeDependencies staging block exists for NyraHost + NyraInfer folders (even though empty in this plan)
- Binary distribution strategy recorded in docs/BINARY_DISTRIBUTION.md
- TestProject.uproject opens cleanly with NYRA plugin enabled
</success_criteria>

<output>
After completion, create `.planning/phases/01-plugin-shell-three-process-ipc/01-03-SUMMARY.md`
documenting: final file layout, chosen binary distribution strategy,
DefaultBuildSettings/CppStandard versions, known warnings (if any), and
pointer to prebuild.ps1 location for Plan 06.
</output>
