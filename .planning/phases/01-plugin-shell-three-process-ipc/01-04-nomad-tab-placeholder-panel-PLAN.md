---
phase: 01-plugin-shell-three-process-ipc
plan: 04
type: execute
wave: 1
depends_on: [01, 03]
autonomous: true
requirements: [CHAT-01]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraChatPanel.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraChatTabNames.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp
objective: >
  Register a dockable nomad tab under `Tools -> NYRA -> Chat` (CD-02) backed by
  a placeholder SNyraChatPanel that renders the string "NYRA — not yet
  connected" centred in the panel. No WebSocket, no streaming, no SQLite — pure
  Slate + tab manager + tool menu wiring. Verifies CHAT-01 tab-spawner scaffold
  via automation test `Nyra.Panel.TabSpawner` (VALIDATION row 1-04-01).
must_haves:
  truths:
    - "Tools menu contains 'NYRA' submenu with 'Chat' entry when NyraEditor loads"
    - "Clicking Tools -> NYRA -> Chat invokes the tab spawner and a nomad tab appears, docked right side panel (default), 420px wide"
    - "Panel renders 'NYRA — not yet connected' placeholder text"
    - "FGlobalTabManager::Get()->TryInvokeTab(FName('NyraChatTab')) returns a valid TSharedPtr<SDockTab> after StartupModule"
    - "Tab closes cleanly on ShutdownModule (UnregisterNomadTabSpawner)"
    - "Nyra.Panel.TabSpawner automation test passes"
  artifacts:
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraChatTabNames.h
      provides: "Canonical FName constants for tab id and menu names"
      exports: ["NyraChatTabId", "NyraToolsMenuName"]
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraChatPanel.h
      provides: "SNyraChatPanel SCompoundWidget declaration (Phase 1 placeholder)"
      contains: "class SNyraChatPanel : public SCompoundWidget"
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp
      provides: "Placeholder Construct method rendering the not-connected text"
      contains: "NYRA — not yet connected"
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp
      provides: "Updated StartupModule registering the tab spawner and tool menu entry"
      contains: "RegisterNomadTabSpawner"
  key_links:
    - from: NyraEditorModule.cpp StartupModule
      to: FGlobalTabManager
      via: "RegisterNomadTabSpawner with FName('NyraChatTab')"
      pattern: "FGlobalTabManager::Get\\(\\)->RegisterNomadTabSpawner"
    - from: NyraEditorModule.cpp StartupModule
      to: UToolMenus
      via: "UToolMenus::Get()->ExtendMenu('LevelEditor.MainMenu.Tools')"
      pattern: "ExtendMenu.*Tools"
---

<objective>
Wave 1 UI scaffold: the user sees a real NYRA tab immediately on opening the
project, even without a working backend. This unblocks Plan 12's chat panel
(which replaces SNyraChatPanel's Construct body).

Per CONTEXT.md CD-02: "Dockable as a standard editor tab via
`RegisterTabSpawner("NyraChatTab", …)` under the `Tools -> NYRA -> Chat` menu.
Default dock: right side panel, width 420 px."

Per RESEARCH §3.1 (widgets list: SDockTab as NomadTab, SVerticalBox for layout),
§3.9 "ENABLED_PLUGIN" state machine (panel is ALWAYS usable — no blank screen).

Purpose: Earliest visible NYRA artifact in the editor. Locks the nomad tab
contract so Plan 12 just extends SNyraChatPanel in place.
Output: `Tools -> NYRA -> Chat` menu entry; clickable nomad tab showing "NYRA
— not yet connected"; Nyra.Panel.TabSpawner test green.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-VALIDATION.md
@TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp
@TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp
</context>

<interfaces>
UE 5.6 nomad tab registration canonical pattern:

```cpp
#include "Framework/Docking/TabManager.h"
#include "Widgets/Docking/SDockTab.h"
#include "WorkspaceMenuStructure.h"
#include "WorkspaceMenuStructureModule.h"

FGlobalTabManager::Get()->RegisterNomadTabSpawner(
    TabId,                           // FName("NyraChatTab")
    FOnSpawnTab::CreateStatic(&FNyraEditorModule::SpawnChatTab))
    .SetDisplayName(NSLOCTEXT("NYRA","NyraChatTab","NYRA Chat"))
    .SetTooltipText(NSLOCTEXT("NYRA","NyraChatTabTip","Open the NYRA chat panel"))
    .SetGroup(WorkspaceMenu::GetMenuStructure().GetToolsCategory())
    .SetIcon(FSlateIcon(FAppStyle::GetAppStyleSetName(), "LevelEditor.Tabs.Details"));

// Unregister in ShutdownModule:
FGlobalTabManager::Get()->UnregisterNomadTabSpawner(TabId);
```

ToolMenus extension (`Tools -> NYRA -> Chat`):

```cpp
#include "ToolMenus.h"

UToolMenu* ToolsMenu = UToolMenus::Get()->ExtendMenu("LevelEditor.MainMenu.Tools");
FToolMenuSection& Section = ToolsMenu->FindOrAddSection("NYRA", NSLOCTEXT("NYRA","NyraMenuHeader","NYRA"));
Section.AddMenuEntry(
    "NyraChat",
    NSLOCTEXT("NYRA","NyraChatLabel","Chat"),
    NSLOCTEXT("NYRA","NyraChatTip","Open the NYRA Chat tab"),
    FSlateIcon(),
    FUIAction(FExecuteAction::CreateLambda([]()
    {
        FGlobalTabManager::Get()->TryInvokeTab(FName("NyraChatTab"));
    })));
```

Nomad tab default position (right side panel, 420 px) — UE 5.6 supports
`SetDisplayName` + default size hint via `FTabSpawnerEntry` but precise
docking area (right side vs center) is usually user-overrideable. The
DEFAULT is a floating tab; achieve "right side panel" via the tab manager's
`DockOn(ERelativeDocking::RightSide)` during spawn, or accept floating-default
for Phase 1 and re-evaluate in Plan 12.
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: NyraChatTabNames.h + SNyraChatPanel placeholder</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraChatTabNames.h
    TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraChatPanel.h
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp
  </files>
  <read_first>
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraEditorModule.h (from Plan 03)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md CD-02, CD-03
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.1 (widgets) and §3.9 (first-run UX state machine — "NYRA — not yet connected" text)
  </read_first>
  <action>
    Create `Public/NyraChatTabNames.h`:
    ```cpp
    #pragma once
    #include "CoreMinimal.h"

    namespace Nyra
    {
        /** Tab manager id for the NYRA chat panel (registered in FNyraEditorModule::StartupModule). */
        inline const FName NyraChatTabId(TEXT("NyraChatTab"));

        /** Main editor tools menu name used to register the NYRA submenu. */
        inline const FName NyraToolsMenuExtensionPoint(TEXT("LevelEditor.MainMenu.Tools"));

        /** Section name inside the Tools menu. */
        inline const FName NyraMenuSectionName(TEXT("NYRA"));
    }
    ```

    Create `Public/Panel/SNyraChatPanel.h`:
    ```cpp
    #pragma once
    #include "CoreMinimal.h"
    #include "Widgets/SCompoundWidget.h"
    #include "Widgets/DeclarativeSyntaxSupport.h"

    /**
     * Phase 1 placeholder for the NYRA chat panel. Renders
     * "NYRA — not yet connected" centred in the tab. Plan 12 replaces
     * the Construct body with the full chat UI (message list, composer,
     * attachment chips, streaming, markdown).
     */
    class NYRAEDITOR_API SNyraChatPanel : public SCompoundWidget
    {
    public:
        SLATE_BEGIN_ARGS(SNyraChatPanel) {}
        SLATE_END_ARGS()

        void Construct(const FArguments& InArgs);
    };
    ```

    Create `Private/Panel/SNyraChatPanel.cpp`:
    ```cpp
    #include "Panel/SNyraChatPanel.h"
    #include "Widgets/Layout/SBox.h"
    #include "Widgets/Text/STextBlock.h"
    #include "Widgets/SBoxPanel.h"
    #include "Styling/AppStyle.h"

    #define LOCTEXT_NAMESPACE "NyraChatPanel"

    void SNyraChatPanel::Construct(const FArguments& InArgs)
    {
        ChildSlot
        [
            SNew(SBox)
            .HAlign(HAlign_Center)
            .VAlign(VAlign_Center)
            .Padding(32.f)
            [
                SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
                [
                    SNew(STextBlock)
                    .Text(LOCTEXT("NotConnectedHeader", "NYRA — not yet connected"))
                    .Font(FAppStyle::GetFontStyle(TEXT("BoldFont")))
                ]
                + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 12, 0, 0)
                [
                    SNew(STextBlock)
                    .Text(LOCTEXT("NotConnectedSub",
                        "Plan 12 replaces this panel with the full chat UI."))
                    .ColorAndOpacity(FLinearColor(0.7f, 0.7f, 0.7f))
                ]
            ]
        ];
    }

    #undef LOCTEXT_NAMESPACE
    ```

    Note the literal "NYRA — not yet connected" uses `—` (em-dash). The
    acceptance criterion greps for ASCII fallback `NYRA -- not yet connected`
    OR the LOCTEXT key string; to avoid encoding issues the grep checks the
    LOCTEXT key.
  </action>
  <verify>
    <automated>
      - `grep -c 'NyraChatTabId(TEXT("NyraChatTab"))' TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraChatTabNames.h` equals 1
      - `grep -c "class NYRAEDITOR_API SNyraChatPanel : public SCompoundWidget" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraChatPanel.h` equals 1
      - `grep -c "SLATE_BEGIN_ARGS(SNyraChatPanel)" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraChatPanel.h` equals 1
      - `grep -c "NotConnectedHeader" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp` equals 1
      - `grep -c "void SNyraChatPanel::Construct" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp` equals 1
    </automated>
  </verify>
  <acceptance_criteria>
    - File NyraChatTabNames.h contains literal text `namespace Nyra` AND `NyraChatTabId(TEXT("NyraChatTab"))` AND `NyraToolsMenuExtensionPoint(TEXT("LevelEditor.MainMenu.Tools"))` AND `NyraMenuSectionName(TEXT("NYRA"))`
    - File Public/Panel/SNyraChatPanel.h contains literal text `class NYRAEDITOR_API SNyraChatPanel : public SCompoundWidget`
    - File Public/Panel/SNyraChatPanel.h contains literal text `SLATE_BEGIN_ARGS(SNyraChatPanel) {}` AND `void Construct(const FArguments& InArgs);`
    - File Private/Panel/SNyraChatPanel.cpp contains literal text `void SNyraChatPanel::Construct(const FArguments& InArgs)`
    - File Private/Panel/SNyraChatPanel.cpp contains literal text `NotConnectedHeader` (LOCTEXT key)
    - File Private/Panel/SNyraChatPanel.cpp contains literal text `NotConnectedSub` (LOCTEXT key)
    - File Private/Panel/SNyraChatPanel.cpp contains literal text `#define LOCTEXT_NAMESPACE "NyraChatPanel"`
    - File Private/Panel/SNyraChatPanel.cpp includes `STextBlock.h` and `SBoxPanel.h`
  </acceptance_criteria>
  <done>Placeholder widget compiles in isolation; includes only Slate + AppStyle primitives (no backend deps).</done>
</task>

<task type="auto">
  <name>Task 2: Update NyraEditorModule.cpp with tab spawner + Tools menu extension</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp
  </files>
  <read_first>
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp (current state from Plan 03 — empty StartupModule/ShutdownModule with log calls only)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraChatTabNames.h (just created)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraChatPanel.h (just created)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.1 (SDockTab with ETabRole::NomadTab)
  </read_first>
  <action>
    REPLACE `NyraEditorModule.cpp` with this content — preserving the Plan 03
    StartupModule log line, adding tab-spawner registration and menu extension:

    ```cpp
    #include "NyraEditorModule.h"
    #include "NyraLog.h"
    #include "NyraChatTabNames.h"
    #include "Panel/SNyraChatPanel.h"

    #include "Modules/ModuleManager.h"
    #include "Framework/Docking/TabManager.h"
    #include "Widgets/Docking/SDockTab.h"
    #include "WorkspaceMenuStructure.h"
    #include "WorkspaceMenuStructureModule.h"
    #include "ToolMenus.h"
    #include "Styling/AppStyle.h"

    IMPLEMENT_MODULE(FNyraEditorModule, NyraEditor)

    #define LOCTEXT_NAMESPACE "NyraEditor"

    static TSharedRef<SDockTab> SpawnNyraChatTab(const FSpawnTabArgs& Args)
    {
        return SNew(SDockTab)
            .TabRole(ETabRole::NomadTab)
            .Label(LOCTEXT("NyraChatTabLabel", "NYRA Chat"))
            [
                SNew(SNyraChatPanel)
            ];
    }

    void FNyraEditorModule::StartupModule()
    {
        UE_LOG(LogNyra, Log, TEXT("[NYRA] NyraEditor module starting (Phase 1 skeleton)"));

        // 1. Register nomad tab spawner under Tools workspace category.
        FGlobalTabManager::Get()
            ->RegisterNomadTabSpawner(
                Nyra::NyraChatTabId,
                FOnSpawnTab::CreateStatic(&SpawnNyraChatTab))
            .SetDisplayName(LOCTEXT("NyraChatTabDisplay", "NYRA Chat"))
            .SetTooltipText(LOCTEXT("NyraChatTabTooltip", "Open the NYRA chat panel"))
            .SetGroup(WorkspaceMenu::GetMenuStructure().GetToolsCategory())
            .SetIcon(FSlateIcon(FAppStyle::GetAppStyleSetName(), "LevelEditor.Tabs.Details"));

        // 2. Extend Tools menu with "NYRA -> Chat" entry (CD-02).
        UToolMenus::RegisterStartupCallback(
            FSimpleMulticastDelegate::FDelegate::CreateLambda([]()
            {
                UToolMenu* ToolsMenu = UToolMenus::Get()->ExtendMenu(Nyra::NyraToolsMenuExtensionPoint);
                if (!ToolsMenu) return;
                FToolMenuSection& Section = ToolsMenu->FindOrAddSection(
                    Nyra::NyraMenuSectionName,
                    LOCTEXT("NyraMenuHeader", "NYRA"));
                Section.AddMenuEntry(
                    FName("NyraChat"),
                    LOCTEXT("NyraChatMenuLabel", "Chat"),
                    LOCTEXT("NyraChatMenuTip", "Open the NYRA Chat tab"),
                    FSlateIcon(FAppStyle::GetAppStyleSetName(), "LevelEditor.Tabs.Details"),
                    FUIAction(FExecuteAction::CreateLambda([]()
                    {
                        FGlobalTabManager::Get()->TryInvokeTab(Nyra::NyraChatTabId);
                    })));
            }));
    }

    void FNyraEditorModule::ShutdownModule()
    {
        UE_LOG(LogNyra, Log, TEXT("[NYRA] NyraEditor module shutting down"));

        if (FGlobalTabManager::Get())
        {
            FGlobalTabManager::Get()->UnregisterNomadTabSpawner(Nyra::NyraChatTabId);
        }
        if (UObjectInitialized())
        {
            UToolMenus::UnregisterOwner(this);
        }
    }

    FNyraEditorModule& FNyraEditorModule::Get()
    {
        return FModuleManager::LoadModuleChecked<FNyraEditorModule>("NyraEditor");
    }

    bool FNyraEditorModule::IsAvailable()
    {
        return FModuleManager::Get().IsModuleLoaded("NyraEditor");
    }

    #undef LOCTEXT_NAMESPACE
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "RegisterNomadTabSpawner" TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp` equals 1
      - `grep -c "Nyra::NyraChatTabId" TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp` >= 3
      - `grep -c "UToolMenus::RegisterStartupCallback" TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp` equals 1
      - `grep -c "UnregisterNomadTabSpawner" TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp` equals 1
      - `grep -c "TryInvokeTab(Nyra::NyraChatTabId)" TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp` equals 1
    </automated>
  </verify>
  <acceptance_criteria>
    - File NyraEditorModule.cpp contains literal text `#include "NyraChatTabNames.h"`
    - File NyraEditorModule.cpp contains literal text `#include "Panel/SNyraChatPanel.h"`
    - File NyraEditorModule.cpp contains literal text `#include "Framework/Docking/TabManager.h"`
    - File NyraEditorModule.cpp contains literal text `#include "WorkspaceMenuStructure.h"`
    - File NyraEditorModule.cpp contains literal text `#include "ToolMenus.h"`
    - File NyraEditorModule.cpp contains literal text `RegisterNomadTabSpawner(`
    - File NyraEditorModule.cpp contains literal text `.SetGroup(WorkspaceMenu::GetMenuStructure().GetToolsCategory())`
    - File NyraEditorModule.cpp contains literal text `UToolMenus::RegisterStartupCallback`
    - File NyraEditorModule.cpp contains literal text `FToolMenuSection& Section = ToolsMenu->FindOrAddSection`
    - File NyraEditorModule.cpp contains literal text `FGlobalTabManager::Get()->TryInvokeTab(Nyra::NyraChatTabId)`
    - File NyraEditorModule.cpp contains literal text `UnregisterNomadTabSpawner(Nyra::NyraChatTabId)` (in ShutdownModule)
    - File NyraEditorModule.cpp contains literal text `IMPLEMENT_MODULE(FNyraEditorModule, NyraEditor)` (preserved from Plan 03)
    - File NyraEditorModule.cpp contains literal text `ETabRole::NomadTab`
    - File NyraEditorModule.cpp still contains literal text `UE_LOG(LogNyra, Log, TEXT("[NYRA] NyraEditor module starting (Phase 1 skeleton)"))` (preserved from Plan 03)
  </acceptance_criteria>
  <done>Tools menu shows "NYRA -> Chat" on editor launch; clicking opens the placeholder panel.</done>
</task>

<task type="auto">
  <name>Task 3: Fill NyraPanelSpec with Nyra.Panel.TabSpawner test</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp
  </files>
  <read_first>
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp (placeholder from Plan 01)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraChatTabNames.h (just created)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-VALIDATION.md row 1-04-01 (Nyra.Panel.TabSpawner)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §"Validation Architecture" — C++ test framework
  </read_first>
  <action>
    Replace the placeholder Define() body in NyraPanelSpec.cpp with the
    TabSpawner test. KEEP the placeholder comments for the other tests
    (`Nyra.Panel.AttachmentChip`, `Nyra.Panel.StreamingBuffer`) — Plan 12 fills those.

    ```cpp
    #include "Misc/AutomationTest.h"
    #include "NyraTestFixtures.h"
    #include "NyraChatTabNames.h"
    #include "Framework/Docking/TabManager.h"
    #include "Widgets/Docking/SDockTab.h"

    #if WITH_AUTOMATION_TESTS

    BEGIN_DEFINE_SPEC(FNyraPanelSpec,
                       "Nyra.Panel",
                       EAutomationTestFlags::EditorContext |
                       EAutomationTestFlags::EngineFilter)
    END_DEFINE_SPEC(FNyraPanelSpec)

    void FNyraPanelSpec::Define()
    {
        Describe("TabSpawner", [this]()
        {
            It("registers NyraChatTab so TryInvokeTab returns a valid SDockTab", [this]()
            {
                TSharedPtr<SDockTab> Tab = FGlobalTabManager::Get()->TryInvokeTab(Nyra::NyraChatTabId);
                TestTrue(TEXT("TryInvokeTab returns valid ptr"), Tab.IsValid());
                if (Tab.IsValid())
                {
                    TestEqual(TEXT("Tab role is NomadTab"), Tab->GetTabRole(), ETabRole::NomadTab);
                    Tab->RequestCloseTab();
                }
            });
        });

        // Plan 12 populates:
        //   Describe("AttachmentChip", ...) — test ID Nyra.Panel.AttachmentChip (VALIDATION row 1-04-04)
        //   Describe("StreamingBuffer", ...) — test ID Nyra.Panel.StreamingBuffer (VALIDATION row 1-04-05)
    }

    #endif // WITH_AUTOMATION_TESTS
    ```
  </action>
  <verify>
    <automated>
      - `grep -c 'Describe("TabSpawner"' TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp` equals 1
      - `grep -c "TryInvokeTab(Nyra::NyraChatTabId)" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp` equals 1
      - `grep -c "ETabRole::NomadTab" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp` equals 1
      - After build: `UnrealEditor-Cmd.exe TestProject/TestProject.uproject -ExecCmds="Automation RunTests Nyra.Panel.TabSpawner;Quit" -unattended -nopause` exits 0
    </automated>
  </verify>
  <acceptance_criteria>
    - File NyraPanelSpec.cpp contains literal text `BEGIN_DEFINE_SPEC(FNyraPanelSpec, "Nyra.Panel"`
    - File NyraPanelSpec.cpp contains literal text `Describe("TabSpawner"`
    - File NyraPanelSpec.cpp contains literal text `It("registers NyraChatTab so TryInvokeTab returns a valid SDockTab"`
    - File NyraPanelSpec.cpp contains literal text `TryInvokeTab(Nyra::NyraChatTabId)`
    - File NyraPanelSpec.cpp contains literal text `ETabRole::NomadTab`
    - File NyraPanelSpec.cpp contains literal text `#include "NyraChatTabNames.h"`
    - File NyraPanelSpec.cpp preserves placeholder comments for `Nyra.Panel.AttachmentChip` and `Nyra.Panel.StreamingBuffer` (referencing Plan 12)
    - Running `UnrealEditor-Cmd.exe TestProject/TestProject.uproject -ExecCmds="Automation RunTests Nyra.Panel.TabSpawner;Quit" -unattended -nopause -testexit="Automation Test Queue Empty"` exits 0
  </acceptance_criteria>
  <done>Nyra.Panel.TabSpawner automation test passes — CHAT-01 tab-spawner contract verified (VALIDATION 1-04-01 green).</done>
</task>

</tasks>

<verification>
Manual: Open TestProject/TestProject.uproject → confirm `Tools -> NYRA -> Chat`
menu entry exists → click it → nomad tab opens showing "NYRA — not yet connected"
placeholder panel.

Automated: `UnrealEditor-Cmd.exe TestProject/TestProject.uproject -ExecCmds="Automation RunTests Nyra.Panel;Quit" -unattended -nopause` passes (at least the TabSpawner test green; AttachmentChip/StreamingBuffer placeholders unexecuted).
</verification>

<success_criteria>
- NyraChatTabNames.h exports Nyra::NyraChatTabId = FName("NyraChatTab")
- SNyraChatPanel placeholder renders "NYRA — not yet connected" text
- Tab spawner registered in StartupModule, unregistered in ShutdownModule
- Tools menu extension creates NYRA submenu on editor startup
- Nyra.Panel.TabSpawner automation test passes
</success_criteria>

<output>
After completion, create `.planning/phases/01-plugin-shell-three-process-ipc/01-04-SUMMARY.md`
documenting: chosen tab id (NyraChatTab), default dock hint used, decision
about floating-vs-side-panel default, any UE 5.6 ToolMenus API gotchas encountered.
</output>
