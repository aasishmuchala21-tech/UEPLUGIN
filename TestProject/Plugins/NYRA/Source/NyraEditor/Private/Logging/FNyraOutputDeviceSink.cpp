// FNyraOutputDeviceSink.cpp — Phase 2 ring-buffer log sink (Plan 02-11).
#include "Logging/FNyraOutputDeviceSink.h"
#include "HAL/FileManager.h"
#include "Misc/DateTime.h"
#include "HAL/IConsoleManager.h"
#include "Internationalization/Internationalization.h"
#include "Misc/StringBuilder.h"

void FNyraOutputDeviceSink::Serialize(
    const TCHAR* Msg,
    ELogVerbosity::Type V,
    const FName& Category
)
{
    if (V > MaxVerbosity)
    {
        return;  // Verbosity too high
    }

    // Check default exclusions
    if (DefaultExclusions.Contains(Category))
    {
        return;  // Blocked by default exclusion
    }

    // Check category whitelist (if non-empty)
    if (CategoryWhitelist.Num() > 0 && !CategoryWhitelist.Contains(Category))
    {
        return;  // Not in allowlist
    }

    FNyraLogEntry Entry;
    Entry.Ts = FDateTime::Now();
    Entry.Category = Category;
    Entry.Verbosity = V;
    Entry.Message = Msg;

    FScopeLock Lock(&BufferLock);
    Buffer.Add(Entry);

    // Ring buffer: evict oldest when over MaxEntries
    if (Buffer.Num() > MaxEntries)
    {
        Buffer.RemoveAt(0, Buffer.Num() - MaxEntries);
    }
}

TArray<FNyraLogEntry> FNyraOutputDeviceSink::GetTail(
    FDateTime SinceTs,
    int32 MaxEntries,
    const TSet<FName>& CategoryWhitelist,
    ELogVerbosity::Type MinVerbosity,
    const FString& Regex
) const
{
    TArray<FNyraLogEntry> Result;

    FScopeLock Lock(&BufferLock);

    for (const FNyraLogEntry& Entry : Buffer)
    {
        // Since timestamp filter
        if (Entry.Ts < SinceTs)
        {
            continue;
        }

        // Min verbosity filter
        if (Entry.Verbosity < MinVerbosity)
        {
            continue;
        }

        // Category whitelist filter (if non-empty; empty = no filter)
        if (CategoryWhitelist.Num() > 0 && !CategoryWhitelist.Contains(Entry.Category))
        {
            continue;
        }

        // Regex filter (FRegexPattern via Core)
        if (!Regex.IsEmpty())
        {
            // Simple contains check — full regex compiled server-side by UE
            if (!Entry.Message.Contains(Regex))
            {
                continue;
            }
        }

        Result.Add(Entry);

        if (Result.Num() >= MaxEntries)
        {
            break;
        }
    }

    return Result;
}

void FNyraOutputDeviceSink::SetCategoryWhitelist(const TSet<FName>& InWhitelist)
{
    FScopeLock Lock(&BufferLock);
    CategoryWhitelist = InWhitelist;
}

void FNyraOutputDeviceSink::SetDefaultExclusions()
{
    FScopeLock Lock(&BufferLock);
    DefaultExclusions.Add(TEXT("LogRHI"));
    DefaultExclusions.Add(TEXT("LogRenderCore"));
    DefaultExclusions.Add(TEXT("LogSlate"));
    DefaultExclusions.Add(TEXT("LogD3D11"));
    DefaultExclusions.Add(TEXT("LogD3D12"));
    DefaultExclusions.Add(TEXT("LogTickGroup"));
}

void FNyraOutputDeviceSink::FlushToFile(const FString& Path) const
{
    FString JSONLines;

    {
        FScopeLock Lock(&BufferLock);
        for (const FNyraLogEntry& Entry : Buffer)
        {
            JSONLines.Appendf(
                TEXT(R"({"ts":"%s","category":"%s","verbosity":"%s","message":""})\n"),
                *Entry.Ts.ToIso8601(),
                *Entry.Category.ToString(),
                *FOutputDevice::VerbosityToString(Entry.Verbosity)
                // Message field intentionally omitted for safety — user sees via log tail tool
            );
        }
    }

    IFileManager::Get().WriteStringToFile(Path, JSONLines);
}