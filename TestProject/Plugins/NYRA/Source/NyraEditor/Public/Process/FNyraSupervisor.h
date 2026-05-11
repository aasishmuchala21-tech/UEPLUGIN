#pragma once

// =============================================================================
// FNyraSupervisor.h  (Phase 1 Plan 10 -- process + handshake + WS composer)
// =============================================================================
//
// CONTEXT: D-04 (eager spawn on StartupModule), D-05 (graceful shutdown +
// KillTree fallback), D-08 (3-restarts-in-60s supervisor policy).
// RESEARCH: §3.3 (FMonitoredProcess + KillTree), §3.10 P1.2 (orphan cleanup),
// P1.7 (id persistence).
//
// Lifecycle:
//   Idle
//     -> Spawning            (PerformSpawn -> FMonitoredProcess::Launch)
//     -> WaitingForHandshake (BeginPolling on handshake-<editor-pid>.json)
//     -> Connecting          (handshake OnReady fires -> WsClient.Connect)
//     -> Authenticating      (WS upgrade -> first-frame session/authenticate)
//     -> Ready               (WsClient OnAuthenticated -> OnReady + replay)
//     -> Crashed             (OnCompleted while !bShutdownRequested)
//     -> Unstable            (>= 3 crashes within 60s window)
//     -> ShuttingDown        (RequestShutdown -> shutdown notif + grace + KillTree)
//
// In-flight replay (P1.7): on Ready after respawn, if InFlight is set the
// supervisor re-sends the request with a fresh id. The panel layer marks
// the original id as cancelled.
//
// Clock injection (INyraClock): production uses FNyraSystemClock
// (FPlatformTime::Seconds). Tests inject FTestClockAdapter wrapping
// Nyra::Tests::FNyraTestClock so the 3-in-60s policy can be exercised
// deterministically without wall-clock delay.
// =============================================================================

#include "CoreMinimal.h"
#include "Misc/MonitoredProcess.h"
#include "Process/FNyraHandshake.h"
#include "WS/FNyraWsClient.h"

/** Clock abstraction for deterministic supervisor policy tests. */
class NYRAEDITOR_API INyraClock
{
public:
    virtual ~INyraClock() = default;
    virtual double NowSeconds() const = 0;
};

/** Production clock: reads FPlatformTime::Seconds(). */
class NYRAEDITOR_API FNyraSystemClock : public INyraClock
{
public:
    virtual double NowSeconds() const override { return FPlatformTime::Seconds(); }
};

enum class ENyraSupervisorState : uint8
{
    Idle,
    Spawning,
    WaitingForHandshake,
    Connecting,
    Authenticating,
    Ready,
    Crashed,
    Unstable,      // 3-in-60s tripped
    ShuttingDown,
};

/** Tracks a single in-flight request for respawn replay. */
struct FNyraInFlightRequest
{
    FString Method;
    TSharedPtr<FJsonObject> Params;
    int64 OriginalId = 0;
};

// L5 from PR #2 follow-up: switched OnStateChanged / OnUnstable /
// OnNotification from single-cast TDelegate to multi-cast TMulticastDelegate
// so opening a second NYRA panel tab no longer silently overwrites the
// first tab's bindings. Each subscriber receives its own FDelegateHandle
// (returned by AddRaw / AddLambda) and is responsible for removing itself
// on destruction. OnReady + OnResponse remain single-cast: only the
// supervisor's internal startup state machine consumes them.
DECLARE_DELEGATE(FOnSupervisorReady);
DECLARE_DELEGATE_OneParam(FOnSupervisorResponse, const FNyraJsonRpcEnvelope& /*Env*/);

DECLARE_MULTICAST_DELEGATE_OneParam(FOnSupervisorStateChanged, ENyraSupervisorState /*NewState*/);
DECLARE_MULTICAST_DELEGATE(FOnSupervisorUnstable);
DECLARE_MULTICAST_DELEGATE_OneParam(FOnSupervisorNotification, const FNyraJsonRpcEnvelope& /*Env*/);

class NYRAEDITOR_API FNyraSupervisor
{
public:
    FNyraSupervisor();                                      // default: FNyraSystemClock
    explicit FNyraSupervisor(TSharedRef<INyraClock> InClock);
    ~FNyraSupervisor();

    /** Spawn NyraHost, poll handshake, connect WS, authenticate. */
    void SpawnAndConnect(
        const FString& InProjectDir,
        const FString& InPluginDir,
        const FString& InLogDir);

    /** Clean shutdown: send `shutdown` notification, wait SHUTDOWN_GRACE_S, then
     *  Cancel(bKillTree=true). Deletes own handshake file. */
    void RequestShutdown();

    /** Send a request; tracks in-flight entry so respawn can replay. */
    int64 SendRequest(const FString& Method, const TSharedRef<FJsonObject>& Params);

    /** Fire-and-forget notification. */
    void SendNotification(const FString& Method, const TSharedRef<FJsonObject>& Params);

    /** Policy-test hook: simulate a crash (records timestamp without killing
     *  an actual process). Bypasses PerformSpawn to keep the test hermetic --
     *  see NyraSupervisorSpec.cpp RestartPolicy. */
    void SimulateCrashForTest();

    ENyraSupervisorState GetState() const { return State; }

    FOnSupervisorStateChanged OnStateChanged;
    FOnSupervisorReady        OnReady;
    FOnSupervisorUnstable     OnUnstable;
    FOnSupervisorNotification OnNotification;
    FOnSupervisorResponse     OnResponse;

private:
    void SetState(ENyraSupervisorState NewState);
    void RecordCrashAndMaybeRestart();
    void PerformSpawn();

    TSharedRef<INyraClock> Clock;
    ENyraSupervisorState State = ENyraSupervisorState::Idle;

    FString ProjectDir;
    FString PluginDir;
    FString LogDir;
    FString HandshakeDir;

    TSharedPtr<FMonitoredProcess> HostProcess;
    FNyraHandshake Handshake;
    FNyraWsClient WsClient;

    FNyraHandshakeData CurrentHandshake;
    TArray<double> CrashTimestamps;        // recent crashes within 60s window
    TOptional<FNyraInFlightRequest> InFlight;

    bool bShutdownRequested = false;
    bool bTestMode = false;   // set by SimulateCrashForTest() to suppress PerformSpawn
};
