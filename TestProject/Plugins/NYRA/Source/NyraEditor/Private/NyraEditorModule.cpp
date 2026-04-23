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

// Plan 10: supervisor lifecycle (D-04 eager spawn + D-05 graceful shutdown).
#include "Process/FNyraSupervisor.h"
#include "Interfaces/IPluginManager.h"
#include "Misc/Paths.h"

// Plan 14: Ring 0 bench harness -- include makes the FNyraDevTools dependency
// explicit. The file-scope FAutoConsoleCommand in FNyraDevTools.cpp registers
// `Nyra.Dev.RoundTripBench` on module load automatically; the include here
// documents the relationship and lets us log a confirmation line below.
#include "Dev/FNyraDevTools.h"

IMPLEMENT_MODULE(FNyraEditorModule, NyraEditor)

// Plan 10: module-level singleton holding the NyraHost supervisor.
// Plan 12: non-static so SNyraChatPanel.cpp's `extern TUniquePtr<class
// FNyraSupervisor> GNyraSupervisor;` link succeeds. Storage still lives
// entirely in this translation unit; the panel only reads through the extern.
TUniquePtr<FNyraSupervisor> GNyraSupervisor;

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

    // 1. Register nomad tab spawner under Tools workspace category (CD-02).
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
            if (!ToolsMenu)
            {
                return;
            }
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

    // Plan 10: D-04 eager spawn NyraHost on editor start (AFTER tab registration).
    GNyraSupervisor = MakeUnique<FNyraSupervisor>();
    const FString PluginDir  = IPluginManager::Get().FindPlugin(TEXT("NYRA"))->GetBaseDir();
    const FString ProjectDir = FPaths::ProjectDir();
    const FString LogDir     = FPaths::Combine(ProjectDir, TEXT("Saved"), TEXT("NYRA"), TEXT("logs"));
    GNyraSupervisor->SpawnAndConnect(ProjectDir, PluginDir, LogDir);

    // Plan 14: confirm the file-scope FAutoConsoleCommand in FNyraDevTools.cpp
    // wired itself in via module-load static init. The command is usable from
    // the UE 5.6 editor console as `Nyra.Dev.RoundTripBench [count=100] [prompt]`.
    UE_LOG(LogNyra, Log, TEXT("[NYRA] Nyra.Dev.RoundTripBench console command registered"));
}

void FNyraEditorModule::ShutdownModule()
{
    UE_LOG(LogNyra, Log, TEXT("[NYRA] NyraEditor module shutting down"));

    // Plan 10: D-05 clean shutdown -- send shutdown notif, wait 2s, TerminateProc(KillTree).
    // Must run BEFORE the tab unregister below so any final WS frames can drain.
    if (GNyraSupervisor.IsValid())
    {
        GNyraSupervisor->RequestShutdown();
        GNyraSupervisor.Reset();
    }

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
