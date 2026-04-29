// FNyraConsoleHandler.cpp — Phase 2 GameThread-safe console Exec (Plan 02-10).
#include "Console/FNyraConsoleHandler.h"
#include "FStringOutputDevice.h"

FString FNyraConsoleHandler::Exec(const FString& Command)
{
    if (!GEngine)
    {
        return TEXT("(no engine)");
    }

    FStringOutputDevice Ar;
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    GEngine->Exec(World, *Command, Ar);
    return TruncateOutput(Ar);
}

bool FNyraConsoleHandler::IsBlockedByPIE()
{
    return GEditor && GEditor->PlayWorld != nullptr;
}

FString FNyraConsoleHandler::TruncateOutput(const FString& Raw)
{
    if (Raw.Len() <= MaxOutputChars)
    {
        return Raw;
    }

    FString Truncated = Raw.Left(MaxOutputChars);
    Truncated.Append(TEXT("\n... [truncated]"));
    return Truncated;
}