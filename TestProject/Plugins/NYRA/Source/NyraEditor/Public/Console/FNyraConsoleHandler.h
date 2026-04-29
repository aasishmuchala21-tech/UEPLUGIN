// FNyraConsoleHandler.h — Phase 2 GameThread-safe console Exec (Plan 02-10).
// Executes UE console commands with FStringOutputDevice capture.
// Tier A commands run immediately; Tier B gated via Plan 02-09; Tier C blocked.
#pragma once

#include "CoreMinimal.h"

class NYRAEDITOR_API FNyraConsoleHandler
{
public:
    /** Execute a console command on the GameThread. Returns captured stdout.
     *  Must be called from GameThread; use AsyncTask(ENamedThreads::GameThread, ...)
     *  for dispatch from other threads. */
    static FString Exec(const FString& Command);

    /** True if the editor is in PIE mode — Exec should be blocked. */
    static bool IsBlockedByPIE();

    /** Maximum output length to prevent runaway captures (32768 chars + truncation marker). */
    static constexpr int32 MaxOutputChars = 32768;

    /** Truncate output to MaxOutputChars and append truncation marker if needed. */
    static FString TruncateOutput(const FString& Raw);
};