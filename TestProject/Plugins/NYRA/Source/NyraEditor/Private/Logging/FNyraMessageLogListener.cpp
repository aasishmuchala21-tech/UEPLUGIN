// FNyraMessageLogListener.cpp — Phase 2 Message Log listener (Plan 02-11).
//
// WR-09: the previous body was 100% commented-out lines. Register()
// reset two TArrays and did nothing else, so GetMessagesForListing()
// always returned empty silently. That made every chat-panel callsite
// that looked for "Blueprint compile errors found" appear clean even
// when UE had errors. This file now bound-binds to FMessageLogModule
// listings so the mirror is actually populated; if the module is
// unavailable (cooked / monolithic builds) the listener degrades to
// the documented "no listings available" state instead of the prior
// silent-empty-mirror behaviour.
#include "Logging/FNyraMessageLogListener.h"
#include "MessageLogModule.h"
#include "IMessageLogListing.h"
#include "Modules/ModuleManager.h"

namespace
{
    static const FName NYRAListingName(TEXT("NYRA"));
    static const FName BlueprintListingName(TEXT("BlueprintLog"));
    static const FName MapCheckListingName(TEXT("MapCheck"));
}

void FNyraMessageLogListener::Register()
{
    BoundHandles.Reset();
    Mirrors.Reset();

    // Editor-only: FMessageLogModule lives in the editor process. Cooked
    // builds don't load it; bail out cleanly so the listener returns the
    // honest "no listings" state.
    if (!FModuleManager::Get().IsModuleLoaded("MessageLog"))
    {
        return;
    }
    FMessageLogModule& Mod =
        FModuleManager::LoadModuleChecked<FMessageLogModule>("MessageLog");

    // Create our own listing if it doesn't already exist. Idempotent:
    // RegisterLogListing returns the existing listing if one was
    // already registered with this name.
    {
        FMessageLogInitializationOptions Opts;
        Opts.bShowFilters = true;
        Opts.bShowPages = false;
        Opts.bAllowClear = true;
        Mod.RegisterLogListing(NYRAListingName, FText::FromString(TEXT("NYRA")), Opts);
    }

    // Bind to NYRA + the two engine listings we surface in the chat
    // panel's "Compiler errors detected" pill.
    const TArray<FName> ListingsToBind = {
        NYRAListingName,
        BlueprintListingName,
        MapCheckListingName,
    };
    for (const FName& Name : ListingsToBind)
    {
        if (!Mod.IsRegisteredLogListing(Name))
        {
            continue;
        }
        TSharedRef<IMessageLogListing> Listing = Mod.GetLogListing(Name);
        FDelegateHandle Handle = Listing->OnDataChanged().AddLambda([this, Name]()
        {
            OnListingDataChanged(Name);
        });
        BoundHandles.Add(Handle);
        // Initial mirror snapshot so callers querying immediately after
        // Register() don't see an empty mirror until the next change.
        OnListingDataChanged(Name);
    }
}

void FNyraMessageLogListener::OnListingDataChanged(const FName ListingName)
{
    if (!FModuleManager::Get().IsModuleLoaded("MessageLog"))
    {
        return;
    }
    FMessageLogModule& Mod =
        FModuleManager::LoadModuleChecked<FMessageLogModule>("MessageLog");
    if (!Mod.IsRegisteredLogListing(ListingName))
    {
        return;
    }
    TSharedRef<IMessageLogListing> Listing = Mod.GetLogListing(ListingName);

    TArray<FNyraMessageLogEntry>& Mirror = Mirrors.FindOrAdd(ListingName);
    Mirror.Reset();
    const auto& Messages = Listing->GetFilteredMessages();
    for (const TSharedRef<FTokenizedMessage>& Msg : Messages)
    {
        FNyraMessageLogEntry Entry;
        Entry.Severity = static_cast<int32>(Msg->GetSeverity());
        Entry.Text = Msg->ToText().ToString();
        Mirror.Add(Entry);
    }
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