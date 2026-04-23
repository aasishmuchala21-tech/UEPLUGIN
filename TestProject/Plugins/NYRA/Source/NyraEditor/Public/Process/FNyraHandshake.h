#pragma once

// =============================================================================
// FNyraHandshake.h  (Phase 1 Plan 10 -- handshake file polling)
// =============================================================================
//
// Wire spec: docs/HANDSHAKE.md (D-06).
//
// UE-side reader for the NyraHost handshake file:
//   %LOCALAPPDATA%/NYRA/handshake-<ue_pid>.json
//   (fallback: <ProjectDir>/Saved/NYRA/handshake-<ue_pid>.json)
//
// Polling schedule (D-06):
//   * Initial interval: 50 ms
//   * Backoff multiplier: 1.5x
//   * Max interval: 2.0 s
//   * Total budget: 30 s -- then OnTimeout fires and polling stops.
//
// Partial-read race (RESEARCH §3.10 P1.1): between NyraHost's atomic
// temp-file write + os.replace, readers may see empty or partial JSON.
// TryReadFile returns false on any parse/validate failure; the ticker
// simply retries until the file settles or the 30s budget expires.
//
// Orphan cleanup (RESEARCH §3.10 P1.2): CleanupOrphans walks
// handshake-*.json in HandshakeDir, kills dead UE PID entries, and
// TerminateProc(KillTree=true) any abandoned NyraHost PIDs.
// =============================================================================

#include "CoreMinimal.h"
#include "Containers/Ticker.h"

/** Parsed handshake file contents (D-06 exact schema). */
struct NYRAEDITOR_API FNyraHandshakeData
{
    int32 Port = 0;
    FString Token;
    int32 NyraHostPid = 0;
    int32 UeEditorPid = 0;
    int64 StartedAtMs = 0;   // unix milliseconds
};

DECLARE_DELEGATE_OneParam(FOnHandshakeReady, const FNyraHandshakeData& /*Data*/);
DECLARE_DELEGATE(FOnHandshakeTimeout);

class NYRAEDITOR_API FNyraHandshake
{
public:
    /** Start polling for handshake-<EditorPid>.json in HandshakeDir. */
    void BeginPolling(const FString& InHandshakeDir, int32 InEditorPid);

    /** Stop polling + remove ticker. Safe to call when not polling. */
    void CancelPolling();

    /** Fires once when a valid handshake is parsed. */
    FOnHandshakeReady OnReady;

    /** Fires once when the 30s budget elapses without a valid handshake. */
    FOnHandshakeTimeout OnTimeout;

    /** Returns true and fills Out iff Path contains a valid handshake JSON
     *  (all 5 fields present, Port > 0, Token non-empty). */
    static bool TryReadFile(const FString& Path, FNyraHandshakeData& Out);

    /** Delete the handshake file (called from UE side on clean shutdown). */
    static void DeleteFile(const FString& HandshakeDir, int32 EditorPid);

    /** Walk HandshakeDir; delete handshake-*.json whose ue_pid is not
     *  running. Orphaned NyraHost PIDs are TerminateProc(KillTree=true).
     *  Returns count of files deleted. */
    static int32 CleanupOrphans(const FString& HandshakeDir);

private:
    FString ComputePath() const;
    bool Tick(float DeltaTime);

    FString HandshakeDir;
    int32 EditorPid = 0;
    FTSTicker::FDelegateHandle TickerHandle;
    double PollingStartTime = 0.0;
    float CurrentIntervalS = 0.05f;   // 50 ms start
    bool bPolling = false;
};
