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

    // Plan 10: FNyraSupervisor::Get().SpawnNyraHost()
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

#undef LOCTEXT_NAMESPACE
