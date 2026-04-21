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
    // Plan 10 populates: Describe("HandshakeAuth", ...) — test ID
    // Nyra.Integration.HandshakeAuth (VALIDATION row 1-02-01)
}

#endif
