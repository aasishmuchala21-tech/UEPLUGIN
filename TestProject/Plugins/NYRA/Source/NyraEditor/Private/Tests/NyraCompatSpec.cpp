// NyraCompatSpec.cpp
// Smoke-test for NYRACompat.h compile-time macros.
// This spec guarantees the compat header compiles cleanly on every matrix
// cell. When CI lights up on 5.4/5.5/5.6/5.7, compile failures surface here
// first. Plan 02-06 extends this spec with one It block per drift entry.

#include "CoreTypes.h"
#include "Misc/AutomationTest.h"

#include "NYRACompat.h"

#if WITH_DEV_AUTOMATION_TESTS

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FNyraCompatMacroTest,
    "Nyra.Compat.Macro",
    EAutomationTestFlags::ApplicationContextMask | EAutomationTestFlags::ProductFilter
)

void FNyraCompatMacroTest::GetTests(
    TArray<FString>& OutBeautifiedNames,
    TArray<FString>& OutTestCommands
) const
{
    // No additional test discovery needed — IMPLEMENT_SIMPLE_AUTOMATION_TEST
    // registers this test with the Automation system.
}

bool FNyraCompatMacroTest::RunTest(
    const FString& Parameters
)
{
    // It block: "NYRA_UE_AT_LEAST(5, 6) is true on the dev host"
    // D-15: UE 5.6 is the current stable baseline for NYRA v1 development.
    // This assertion fires if compiled against < 5.6 (should not happen in CI).
    TestTrue(
        TEXT("NYRA_UE_AT_LEAST(5, 6) must be true on the dev host"),
        NYRA_UE_AT_LEAST(5, 6)
    );

    return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS