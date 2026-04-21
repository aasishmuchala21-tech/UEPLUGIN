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
