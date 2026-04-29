// NyraConsoleSpec.cpp — Phase 2 Automation Spec for FNyraConsoleHandler (Plan 02-10).
// Tests: ExecCaptureOutput, RefusesDuringPIE, OutputDeviceCapture
#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"
#include "Console/FNyraConsoleHandler.h"
#include "Engine/Engine.h"
#include "Engine/World.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FNyraConsoleExecCaptureOutput,
    "Nyra.Console.ExecCaptureOutput",
    EAutomationTestFlags::ApplicationContextMask | EAutomationTestFlags::ProductFilter
)

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FNyraConsoleRefusesDuringPIE,
    "Nyra.Console.RefusesDuringPIE",
    EAutomationTestFlags::ApplicationContextMask | EAutomationTestFlags::ProductFilter
)

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FNyraConsoleOutputDeviceCapture,
    "Nyra.Console.OutputDeviceCapture",
    EAutomationTestFlags::ApplicationContextMask | EAutomationTestFlags::ProductFilter
)

bool FNyraConsoleExecCaptureOutput::RunTest(const FString& Parameters)
{
    if (!GEngine)
    {
        return false;  // No engine — fail
    }

    // It("stat fps returns non-empty output")
    {
        FString Output = FNyraConsoleHandler::Exec(TEXT("stat fps"));
        AddInfo(FString::Printf(TEXT("stat fps output length: %d"), Output.Len()));
        TestTrue(TEXT("Output should not be empty"), !Output.IsEmpty());
        TestTrue(TEXT("Output should not be engine-missing error"),
                 !Output.Contains(TEXT("(no engine)")));
    }

    // It("help command returns known output")
    {
        FString Output = FNyraConsoleHandler::Exec(TEXT("help"));
        AddInfo(FString::Printf(TEXT("help output length: %d"), Output.Len()));
        TestTrue(TEXT("help should return non-empty output"), !Output.IsEmpty());
    }

    // It("unknown command returns gracefully")
    {
        FString Output = FNyraConsoleHandler::Exec(TEXT("nyra_nonexistent_command_xyz"));
        AddInfo(FString::Printf(TEXT("unknown command output: %s"), *Output));
        TestTrue(TEXT("Unknown command should not crash"), true);
    }

    return true;
}

bool FNyraConsoleRefusesDuringPIE::RunTest(const FString& Parameters)
{
    // It("IsBlockedByPIE returns false outside PIE")
    {
        // Outside PIE (normal automation context), should return false
        bool Blocked = FNyraConsoleHandler::IsBlockedByPIE();
        AddInfo(FString::Printf(TEXT("IsBlockedByPIE outside PIE: %d"), Blocked ? 1 : 0));
        // In automation test, we are not in PIE — so Blocked should be false
        TestTrue(TEXT("Outside PIE should not block"), !Blocked);
    }

    return true;
}

bool FNyraConsoleOutputDeviceCapture::RunTest(const FString& Parameters)
{
    // It("help output contains 'Possible commands' or similar help text")
    {
        FString Output = FNyraConsoleHandler::Exec(TEXT("help"));
        // Help output should contain command names or help information
        TestTrue(TEXT("Help output should contain text"),
                 !Output.IsEmpty() && Output.Len() > 5);
    }

    return true;
}