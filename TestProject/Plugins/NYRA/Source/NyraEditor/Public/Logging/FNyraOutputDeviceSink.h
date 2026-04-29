// FNyraOutputDeviceSink.h — Phase 2 ring-buffer log sink (Plan 02-11).
// Extends FOutputDevice; captures UE editor log output into a bounded ring buffer.
// Registered via GLog->AddOutputDevice in NyraEditorModule::StartupModule.
#pragma once

#include "CoreMinimal.h"
#include "Containers/Array.h"
#include "Containers/Map.h"
#include "Containers/Set.h"
#include "UObject/NameTypes.h"
#include "HAL/OutputDevice.h"
#include "Logging/FNyraOutputDeviceSink.generated.h"

USTRUCT()
struct FNyraLogEntry
{
    GENERATED_BODY()
    FDateTime Ts;
    FName Category;
    ELogVerbosity::Type Verbosity;
    FString Message;
};

class NYRAEDITOR_API FNyraOutputDeviceSink : public FOutputDevice
{
    GENERATED_BODY()

public:
    /** Serialize is called by GLog for every log message. Thread-safe via BufferLock. */
    virtual void Serialize(
        const TCHAR* Msg,
        ELogVerbosity::Type V,
        const FName& Category
    ) override;

    /** Get the last N entries matching the given filters. */
    TArray<FNyraLogEntry> GetTail(
        FDateTime SinceTs,
        int32 MaxEntries,
        const TSet<FName>& CategoryWhitelist,
        ELogVerbosity::Type MinVerbosity,
        const FString& Regex
    ) const;

    /** Set category whitelist (empty = allow all). */
    void SetCategoryWhitelist(const TSet<FName>& InWhitelist);

    /** Apply default high-verbosity exclusions (LogRHI, LogRenderCore, LogSlate, ...). */
    void SetDefaultExclusions();

    /** Flush ring buffer to a crash log file on OnHandleSystemError. */
    void FlushToFile(const FString& Path) const;

    /** Maximum entries in the ring buffer (default 2000 per D-21). */
    static constexpr int32 MaxEntries = 2000;

private:
    mutable FCriticalSection BufferLock;
    TArray<FNyraLogEntry> Buffer;
    TSet<FName> CategoryWhitelist;   // empty = allow all
    TSet<FName> DefaultExclusions;   // always blocked unless whitelisted
    ELogVerbosity::Type MaxVerbosity = ELogVerbosity::Log;
};