// FNyraMessageLogListener.cpp — Phase 2 Message Log listener (Plan 02-11).
#include "Logging/FNyraMessageLogListener.h"
#include "MessageLog.h"
#include "Modules/ModuleManager.h"

void FNyraMessageLogListener::Register()
{
    // Register NYRA's own listing via FMessageLogModule
    // FMessageLogInitializationOptions opts;
    // opts.bShowFilters = true;
    // opts.bShowPages = false;
    // opts.bAllowClear = true;
    // FMessageLogModule::Get()..CreateLogListing(FName("NYRA"), opts);

    // Bind to existing listings
    // For now, stub registration — full implementation requires FMessageLogModule access
    // which is editor-only. Mirrors map is populated on message log changes.
    BoundHandles.Reset();
    Mirrors.Reset();

    // Stub: register NYRA listing
    // TSharedRef<IMessageLogListing> NYRAListing =
    //     FMessageLogModule::Get().GetLogListing(FName("NYRA"));
    // NYRAListing->OnDataChanged().AddRaw(this, &FNyraMessageLogListener::OnDataChanged);

    // Bind to existing standard listings
    // TSharedRef<IMessageLogListing> BlueprintListing =
    //     FMessageLogModule::Get().GetLogListing(FName("LogBlueprint"));
    // BlueprintListing->OnDataChanged().AddRaw(this, &FNyraMessageLogListener::OnBlueprintDataChanged);
}

void FNyraMessageLogListener::Unregister()
{
    for (FDelegateHandle& Handle : BoundHandles)
    {
        // Handle.Remove();  // Unbind delegates
    }
    BoundHandles.Reset();
}

TArray<FNyraMessageLogEntry> FNyraMessageLogListener::GetMessagesForListing(
    const FName& ListingName,
    int32 SinceIndex,
    int32 MaxEntries
) const
{
    TArray<FNyraMessageLogEntry> Result;

    const TArray<FNyraMessageLogEntry>* Mirror = Mirrors.Find(ListingName);
    if (!Mirror)
    {
        return Result;  // Unknown listing — return empty
    }

    const TArray<FNyraMessageLogEntry>& Entries = *Mirror;
    for (int32 i = SinceIndex; i < Entries.Num() && Result.Num() < MaxEntries; ++i)
    {
        Result.Add(Entries[i]);
    }

    return Result;
}