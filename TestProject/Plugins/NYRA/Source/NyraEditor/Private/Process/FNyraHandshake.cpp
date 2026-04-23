// =============================================================================
// FNyraHandshake.cpp  (Phase 1 Plan 10)
// =============================================================================

#include "Process/FNyraHandshake.h"
#include "NyraLog.h"
#include "HAL/PlatformProcess.h"
#include "HAL/PlatformFileManager.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

// Polling constants locked by PLAN.md / docs/HANDSHAKE.md (D-06).
constexpr double HANDSHAKE_TOTAL_BUDGET_S = 30.0;
constexpr float  HANDSHAKE_MAX_INTERVAL_S = 2.0f;
constexpr float  HANDSHAKE_BACKOFF_MULTIPLIER = 1.5f;

void FNyraHandshake::BeginPolling(const FString& InHandshakeDir, int32 InEditorPid)
{
    HandshakeDir = InHandshakeDir;
    EditorPid = InEditorPid;
    PollingStartTime = FPlatformTime::Seconds();
    CurrentIntervalS = 0.05f;
    bPolling = true;
    TickerHandle = FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateRaw(this, &FNyraHandshake::Tick), CurrentIntervalS);
    UE_LOG(LogNyra, Log, TEXT("[NYRA] Handshake polling started: %s"), *ComputePath());
}

void FNyraHandshake::CancelPolling()
{
    if (TickerHandle.IsValid())
    {
        FTSTicker::GetCoreTicker().RemoveTicker(TickerHandle);
        TickerHandle.Reset();
    }
    bPolling = false;
}

FString FNyraHandshake::ComputePath() const
{
    return FPaths::Combine(HandshakeDir, FString::Printf(TEXT("handshake-%d.json"), EditorPid));
}

bool FNyraHandshake::Tick(float DeltaTime)
{
    if (!bPolling)
    {
        return false;  // auto-remove
    }

    const FString Path = ComputePath();
    FNyraHandshakeData Data;
    if (TryReadFile(Path, Data))
    {
        bPolling = false;
        OnReady.ExecuteIfBound(Data);
        return false;  // auto-remove
    }

    const double Elapsed = FPlatformTime::Seconds() - PollingStartTime;
    if (Elapsed >= HANDSHAKE_TOTAL_BUDGET_S)
    {
        bPolling = false;
        UE_LOG(LogNyra, Warning, TEXT("[NYRA] Handshake polling timed out after %.1fs"), Elapsed);
        OnTimeout.ExecuteIfBound();
        return false;
    }

    // Geometric backoff (50ms -> 75ms -> 112ms -> ... capped at 2s).
    CurrentIntervalS = FMath::Min(CurrentIntervalS * HANDSHAKE_BACKOFF_MULTIPLIER, HANDSHAKE_MAX_INTERVAL_S);
    // Re-add ticker with new interval (simplest API -- remove + re-add).
    FTSTicker::GetCoreTicker().RemoveTicker(TickerHandle);
    TickerHandle = FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateRaw(this, &FNyraHandshake::Tick), CurrentIntervalS);
    return false;  // the current tick is done; the re-added one runs next.
}

bool FNyraHandshake::TryReadFile(const FString& Path, FNyraHandshakeData& Out)
{
    if (!FPaths::FileExists(Path))
    {
        return false;
    }
    FString Content;
    if (!FFileHelper::LoadFileToString(Content, *Path))
    {
        return false;
    }
    if (Content.IsEmpty())
    {
        return false;
    }

    TSharedRef<TJsonReader<TCHAR>> Reader = TJsonReaderFactory<TCHAR>::Create(Content);
    TSharedPtr<FJsonObject> Root;
    if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
    {
        // Partial-read race (P1.1) -- caller's ticker retries.
        return false;
    }

    double Port = 0.0, NyraHostPid = 0.0, UeEditorPid = 0.0, StartedAt = 0.0;
    FString Token;
    if (!Root->TryGetNumberField(TEXT("port"),         Port))          return false;
    if (!Root->TryGetStringField(TEXT("token"),        Token))         return false;
    if (!Root->TryGetNumberField(TEXT("nyrahost_pid"), NyraHostPid))   return false;
    if (!Root->TryGetNumberField(TEXT("ue_pid"),       UeEditorPid))   return false;
    if (!Root->TryGetNumberField(TEXT("started_at"),   StartedAt))     return false;

    Out.Port        = static_cast<int32>(Port);
    Out.Token       = Token;
    Out.NyraHostPid = static_cast<int32>(NyraHostPid);
    Out.UeEditorPid = static_cast<int32>(UeEditorPid);
    Out.StartedAtMs = static_cast<int64>(StartedAt);
    return Out.Port > 0 && !Out.Token.IsEmpty();
}

void FNyraHandshake::DeleteFile(const FString& HandshakeDir, int32 EditorPid)
{
    const FString Path = FPaths::Combine(HandshakeDir,
        FString::Printf(TEXT("handshake-%d.json"), EditorPid));
    IFileManager::Get().Delete(*Path, /*RequireExists=*/false, /*EvenReadOnly=*/true);
}

int32 FNyraHandshake::CleanupOrphans(const FString& HandshakeDir)
{
    int32 Count = 0;
    if (!FPaths::DirectoryExists(HandshakeDir))
    {
        return 0;
    }

    TArray<FString> Files;
    IFileManager::Get().FindFiles(Files,
        *FPaths::Combine(HandshakeDir, TEXT("handshake-*.json")), true, false);

    for (const FString& Name : Files)
    {
        const FString FullPath = FPaths::Combine(HandshakeDir, Name);
        FNyraHandshakeData Data;
        if (!TryReadFile(FullPath, Data))
        {
            // Unreadable -> delete (stale / corrupt).
            IFileManager::Get().Delete(*FullPath, false, true);
            ++Count;
            continue;
        }

        // Check if UE PID still alive on this machine.
        FProcHandle Handle = FPlatformProcess::OpenProcess(static_cast<uint32>(Data.UeEditorPid));
        const bool bAlive = Handle.IsValid() && FPlatformProcess::IsProcRunning(Handle);
        if (Handle.IsValid())
        {
            FPlatformProcess::CloseProc(Handle);
        }

        if (!bAlive)
        {
            // Terminate orphaned NyraHost too (RESEARCH P1.2).
            FProcHandle NyraHandle = FPlatformProcess::OpenProcess(static_cast<uint32>(Data.NyraHostPid));
            if (NyraHandle.IsValid() && FPlatformProcess::IsProcRunning(NyraHandle))
            {
                FPlatformProcess::TerminateProc(NyraHandle, /*KillTree=*/true);
            }
            if (NyraHandle.IsValid())
            {
                FPlatformProcess::CloseProc(NyraHandle);
            }
            IFileManager::Get().Delete(*FullPath, false, true);
            ++Count;
        }
    }
    return Count;
}
