// =============================================================================
// NyraIntegrationSpec.cpp  (Phase 1 Plan 01 + Plan 10)
// =============================================================================
//
// Hosts TWO spec classes:
//
//   * FNyraPluginModulesLoadSpec -- Nyra.Plugin.ModulesLoad
//       Owned by Plan 03 (closes PLUG-01 -- UPlugin two-module load).
//       Runs in every UE build; no gates.
//
//   * FNyraIntegrationSpec -- Nyra.Integration.HandshakeAuth
//       Owned by Plan 10 (VALIDATION row 1-02-01).
//       Guarded by ENABLE_NYRA_INTEGRATION_TESTS because it spawns a real
//       NyraHost python subprocess and expects the Plan 06 handshake +
//       session/hello endpoints to be reachable.
// =============================================================================

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

// Integration spec (guarded -- requires live NyraHost).
#if WITH_AUTOMATION_TESTS && ENABLE_NYRA_INTEGRATION_TESTS

#include "Process/FNyraSupervisor.h"
#include "Interfaces/IPluginManager.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"

BEGIN_DEFINE_SPEC(FNyraIntegrationSpec,
                   "Nyra.Integration",
                   EAutomationTestFlags::EditorContext |
                   EAutomationTestFlags::ProductFilter)
END_DEFINE_SPEC(FNyraIntegrationSpec)

void FNyraIntegrationSpec::Define()
{
    LatentIt("HandshakeAuth -- spawn NyraHost, authenticate, receive session/hello",
             30.0f,
             [this](const FDoneDelegate& Done)
    {
        // Requires:
        //   Plugins/NYRA/Binaries/Win64/NyraHost/cpython/python.exe
        //   Plugins/NYRA/Source/NyraHost/src/nyrahost/__main__.py reachable
        // Intended for dev-machine execution with prebuild.ps1 already run.
        FNyraSupervisor* Sup = new FNyraSupervisor();
        Sup->OnReady.BindLambda([this, Sup, Done]()
        {
            TSharedRef<FJsonObject> Empty = MakeShared<FJsonObject>();
            const int64 Id = Sup->SendRequest(TEXT("session/hello"), Empty);
            Sup->OnResponse.BindLambda([this, Sup, Done, Id](const FNyraJsonRpcEnvelope& Env)
            {
                TestEqual(TEXT("response id matches"), Env.Id, Id);
                TestTrue(TEXT("result has phase field"),
                         Env.Result.IsValid() && Env.Result->HasField(TEXT("phase")));
                Sup->RequestShutdown();
                delete Sup;
                Done.Execute();
            });
        });

        const FString PluginDir  = IPluginManager::Get().FindPlugin(TEXT("NYRA"))->GetBaseDir();
        const FString ProjectDir = FPaths::ProjectDir();
        const FString LogDir     = FPaths::Combine(ProjectDir, TEXT("Saved"), TEXT("NYRA"), TEXT("logs"));
        Sup->SpawnAndConnect(ProjectDir, PluginDir, LogDir);
    });
}

#endif
