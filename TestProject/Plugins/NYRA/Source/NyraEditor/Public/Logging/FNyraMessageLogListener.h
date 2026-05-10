// FNyraMessageLogListener.h — Phase 2 Message Log listener (Plan 02-11).
// Binds to FMessageLogModule listings (LogBlueprint, LogPIE, LogAssetTools).
// Registers NYRA's own listing; mirrors messages for polling by nyra_message_log_list.
//
// WR-09: removed the bogus GENERATED_BODY() on a bare C++ class — that
// macro is reserved for UCLASS / USTRUCT / UINTERFACE. The struct is a
// plain POD so callers don't need UHT codegen for it.
#pragma once

#include "CoreMinimal.h"
#include "UObject/NameTypes.h"

struct FNyraMessageLogEntry
{
    int32 Index = 0;
    int32 Severity = 0;            // EMessageSeverity::Type cast to int
    FString Text;                  // human-readable line
    TArray<FString> TokenRefs;     // FTokenizedMessage tokens, optional
};

class NYRAEDITOR_API FNyraMessageLogListener
{
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
    void OnListingDataChanged(const FName ListingName);

    TMap<FName, TArray<FNyraMessageLogEntry>> Mirrors;
    TArray<FDelegateHandle> BoundHandles;
};