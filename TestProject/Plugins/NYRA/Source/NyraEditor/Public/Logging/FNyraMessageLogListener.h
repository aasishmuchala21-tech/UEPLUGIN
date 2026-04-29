// FNyraMessageLogListener.h — Phase 2 Message Log listener (Plan 02-11).
// Binds to FMessageLogModule listings (LogBlueprint, LogPIE, LogAssetTools).
// Registers NYRA's own listing; mirrors messages for polling by nyra_message_log_list.
#pragma once

#include "CoreMinimal.h"
#include "UObject/NameTypes.h"
#include "Logging/FNyraMessageLogListener.generated.h"

USTRUCT()
struct FNyraMessageLogEntry
{
    GENERATED_BODY()
    int32 Index;
    FString Severity;
    FString Message;
    TArray<FString> TokenRefs;
};

class NYRAEDITOR_API FNyraMessageLogListener
{
    GENERATED_BODY()

public:
    /** Register with FMessageLogModule; bind to LogBlueprint, LogPIE, LogAssetTools. */
    void Register();

    /** Unregister listeners. Call from ShutdownModule. */
    void Unregister();

    /** Get messages for a listing since the given index. */
    TArray<FNyraMessageLogEntry> GetMessagesForListing(
        const FName& ListingName,
        int32 SinceIndex,
        int32 MaxEntries
    ) const;

private:
    TMap<FName, TArray<FNyraMessageLogEntry>> Mirrors;
    TArray<FDelegateHandle> BoundHandles;
};