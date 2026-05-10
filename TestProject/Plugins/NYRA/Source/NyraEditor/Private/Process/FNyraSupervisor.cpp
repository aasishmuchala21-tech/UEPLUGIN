// =============================================================================
// FNyraSupervisor.cpp  (Phase 1 Plan 10)
// =============================================================================

#include "Process/FNyraSupervisor.h"
#include "NyraLog.h"
#include "HAL/PlatformProcess.h"
#include "HAL/PlatformFileManager.h"
#include "HAL/FileManager.h"
#include "Interfaces/IPluginManager.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Misc/MonitoredProcess.h"
#include "Dom/JsonObject.h"

// Policy constants locked by PLAN.md / docs CONTEXT D-08, D-05.
constexpr int32  MAX_CRASHES_IN_WINDOW = 3;
constexpr double CRASH_WINDOW_S        = 60.0;
constexpr double SHUTDOWN_GRACE_S      = 2.0;

FNyraSupervisor::FNyraSupervisor()
    : Clock(MakeShared<FNyraSystemClock>()) {}

FNyraSupervisor::FNyraSupervisor(TSharedRef<INyraClock> InClock)
    : Clock(InClock) {}

FNyraSupervisor::~FNyraSupervisor() = default;

void FNyraSupervisor::SetState(ENyraSupervisorState NewState)
{
    State = NewState;
    OnStateChanged.ExecuteIfBound(NewState);
}

void FNyraSupervisor::SpawnAndConnect(const FString& InProjectDir, const FString& InPluginDir, const FString& InLogDir)
{
    ProjectDir = InProjectDir;
    PluginDir  = InPluginDir;
    LogDir     = InLogDir;

    // Resolve handshake dir: %LOCALAPPDATA%/NYRA primary, <Project>/Saved/NYRA fallback.
    FString LocalAppData = FPlatformMisc::GetEnvironmentVariable(TEXT("LOCALAPPDATA"));
    if (!LocalAppData.IsEmpty())
    {
        HandshakeDir = FPaths::Combine(LocalAppData, TEXT("NYRA"));
    }
    else
    {
        HandshakeDir = FPaths::Combine(ProjectDir, TEXT("Saved"), TEXT("NYRA"));
    }
    IFileManager::Get().MakeDirectory(*HandshakeDir, /*Tree=*/true);

    // Orphan cleanup (P1.2) before we write a fresh handshake.
    const int32 Cleaned = FNyraHandshake::CleanupOrphans(HandshakeDir);
    if (Cleaned > 0)
    {
        UE_LOG(LogNyra, Log, TEXT("[NYRA] Cleaned %d orphan handshake file(s)"), Cleaned);
    }

    PerformSpawn();
}

void FNyraSupervisor::PerformSpawn()
{
    SetState(ENyraSupervisorState::Spawning);

    const FString PythonExe = FPaths::Combine(PluginDir, TEXT("Binaries"), TEXT("Win64"),
        TEXT("NyraHost"), TEXT("cpython"), TEXT("python.exe"));
    const FString PluginBinariesDir = FPaths::Combine(PluginDir, TEXT("Binaries"), TEXT("Win64"));
    const int32 EditorPid = FPlatformProcess::GetCurrentProcessId();

    // CLI args MUST match nyrahost/__main__.py parse_args() (Plan 06 + Plan 08).
    const FString Args = FString::Printf(
        TEXT("-m nyrahost --editor-pid %d --log-dir \"%s\" --project-dir \"%s\" --plugin-binaries-dir \"%s\" --handshake-dir \"%s\""),
        EditorPid, *LogDir, *ProjectDir, *PluginBinariesDir, *HandshakeDir);

    UE_LOG(LogNyra, Log, TEXT("[NYRA] Spawning NyraHost: %s %s"), *PythonExe, *Args);

    HostProcess = MakeShared<FMonitoredProcess>(PythonExe, Args, /*bHidden=*/true, /*bCreatePipes=*/true);
    HostProcess->OnOutput().BindLambda([](const FString& Line)
    {
        UE_LOG(LogNyra, Verbose, TEXT("[NyraHost] %s"), *Line);
    });
    HostProcess->OnCompleted().BindLambda([this](int32 ExitCode)
    {
        UE_LOG(LogNyra, Log, TEXT("[NYRA] NyraHost exited code=%d"), ExitCode);
        if (!bShutdownRequested)
        {
            RecordCrashAndMaybeRestart();
        }
    });

    if (!HostProcess->Launch())
    {
        UE_LOG(LogNyra, Error, TEXT("[NYRA] NyraHost failed to launch"));
        SetState(ENyraSupervisorState::Crashed);
        RecordCrashAndMaybeRestart();
        return;
    }

    // BL-04: ensure no stale handshake file from a previous (crashed)
    // NyraHost can be misread as the new one. Cancel any in-flight
    // polling, delete the previous PID-derived handshake file, and run
    // CleanupOrphans so a recycled PID can never deadlock the new
    // editor's bind. Also record the spawn timestamp so the polling
    // OnReady can reject any handshake whose started_at predates this
    // spawn (defense-in-depth against PID reuse).
    Handshake.CancelPolling();
    const int32 EditorPid = FPlatformProcess::GetCurrentProcessId();
    FNyraHandshake::DeleteFile(HandshakeDir, EditorPid);
    FNyraHandshake::CleanupOrphans(HandshakeDir);
    const int64 SpawnedAt = FDateTime::UtcNow().ToUnixTimestamp() * 1000;

    // Begin polling for the handshake file.
    SetState(ENyraSupervisorState::WaitingForHandshake);
    Handshake = FNyraHandshake{};
    Handshake.OnReady.BindLambda([this, SpawnedAt](const FNyraHandshakeData& Data)
    {
        // BL-04: reject handshake files whose started_at predates this
        // spawn. A NyraHost that began before our PerformSpawn cannot have
        // emitted this file -- it must be a stale leftover from a prior
        // editor that the orphan cleanup somehow missed (PID race,
        // antivirus delay).
        if (Data.StartedAt > 0 && Data.StartedAt < SpawnedAt)
        {
            UE_LOG(LogNyra, Warning,
                TEXT("[NYRA] Rejecting stale handshake (started_at=%lld < spawned_at=%lld); waiting for fresh"),
                Data.StartedAt, SpawnedAt);
            return;
        }
        CurrentHandshake = Data;
        SetState(ENyraSupervisorState::Connecting);

        WsClient.OnAuthenticated.BindLambda([this]()
        {
            SetState(ENyraSupervisorState::Ready);
            OnReady.ExecuteIfBound();

            // P1.7 in-flight replay: re-send the last in-flight request with a fresh id.
            if (InFlight.IsSet())
            {
                const FNyraInFlightRequest Req = InFlight.GetValue();
                InFlight.Reset();
                SendRequest(Req.Method, Req.Params.ToSharedRef());
            }
        });
        WsClient.OnAuthFailed.BindLambda([this](int32 Code, const FString& Reason)
        {
            UE_LOG(LogNyra, Error, TEXT("[NYRA] WS auth failed code=%d reason=%s"), Code, *Reason);
        });
        WsClient.OnNotification.BindLambda([this](const FNyraJsonRpcEnvelope& E)
        {
            OnNotification.ExecuteIfBound(E);
        });
        WsClient.OnResponse.BindLambda([this](const FNyraJsonRpcEnvelope& E)
        {
            OnResponse.ExecuteIfBound(E);
        });

        SetState(ENyraSupervisorState::Authenticating);
        WsClient.Connect(TEXT("127.0.0.1"), CurrentHandshake.Port, CurrentHandshake.Token);
    });
    Handshake.OnTimeout.BindLambda([this]()
    {
        UE_LOG(LogNyra, Warning, TEXT("[NYRA] Handshake timeout"));
        SetState(ENyraSupervisorState::Crashed);
        RecordCrashAndMaybeRestart();
    });
    Handshake.BeginPolling(HandshakeDir, FPlatformProcess::GetCurrentProcessId());
}

void FNyraSupervisor::RecordCrashAndMaybeRestart()
{
    SetState(ENyraSupervisorState::Crashed);

    const double Now = Clock->NowSeconds();
    CrashTimestamps.Add(Now);
    // Evict entries older than the 60s window.
    CrashTimestamps.RemoveAll([&](double T) { return (Now - T) > CRASH_WINDOW_S; });

    if (CrashTimestamps.Num() >= MAX_CRASHES_IN_WINDOW)
    {
        UE_LOG(LogNyra, Error, TEXT("[NYRA] NyraHost unstable: %d crashes in %.0fs window"),
               CrashTimestamps.Num(), CRASH_WINDOW_S);
        SetState(ENyraSupervisorState::Unstable);
        OnUnstable.ExecuteIfBound();
        return;
    }

    UE_LOG(LogNyra, Warning, TEXT("[NYRA] NyraHost crash %d/%d in window -- respawning"),
           CrashTimestamps.Num(), MAX_CRASHES_IN_WINDOW);

    // Hermetic test hook: SimulateCrashForTest sets bTestMode so unit tests
    // can drive RestartPolicy without actually calling PerformSpawn (which
    // would try to launch python.exe on the test host).
    if (!bTestMode)
    {
        PerformSpawn();
    }
}

void FNyraSupervisor::RequestShutdown()
{
    bShutdownRequested = true;
    SetState(ENyraSupervisorState::ShuttingDown);

    if (WsClient.IsConnected())
    {
        TSharedRef<FJsonObject> Empty = MakeShared<FJsonObject>();
        WsClient.SendNotification(TEXT("shutdown"), Empty);
    }

    // Wait up to SHUTDOWN_GRACE_S for the process to exit cleanly.
    const double Deadline = FPlatformTime::Seconds() + SHUTDOWN_GRACE_S;
    while (HostProcess.IsValid() && HostProcess->Update() && FPlatformTime::Seconds() < Deadline)
    {
        FPlatformProcess::Sleep(0.05f);
    }
    if (HostProcess.IsValid() && HostProcess->IsRunning())
    {
        UE_LOG(LogNyra, Warning, TEXT("[NYRA] NyraHost did not exit within %.1fs -- TerminateProc KillTree"), SHUTDOWN_GRACE_S);
        HostProcess->Cancel(/*bKillTree=*/true);
    }

    WsClient.Disconnect();
    FNyraHandshake::DeleteFile(HandshakeDir, FPlatformProcess::GetCurrentProcessId());
    SetState(ENyraSupervisorState::Idle);
}

int64 FNyraSupervisor::SendRequest(const FString& Method, const TSharedRef<FJsonObject>& Params)
{
    // Track as in-flight (Phase 1: at most one at a time; dict to come with Plan 12).
    FNyraInFlightRequest Req;
    Req.Method = Method;
    Req.Params = Params;
    const int64 Id = WsClient.SendRequest(Method, Params);
    Req.OriginalId = Id;
    InFlight = Req;
    return Id;
}

void FNyraSupervisor::SendNotification(const FString& Method, const TSharedRef<FJsonObject>& Params)
{
    WsClient.SendNotification(Method, Params);
}

void FNyraSupervisor::SimulateCrashForTest()
{
    bTestMode = true;
    RecordCrashAndMaybeRestart();
}
