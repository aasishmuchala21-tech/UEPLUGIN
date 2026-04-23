// =============================================================================
// FNyraDevTools.cpp  (Phase 1 Plan 14 -- Ring 0 stability gate bench harness)
// =============================================================================
//
// Implements the `Nyra.Dev.RoundTripBench` editor console command.
//
// Flow per round (RESEARCH §3.6):
//   1. Reset GCurrentRound and allocate a fresh req_id (FGuid).
//   2. Install an FTSTicker editor-tick sampler that records
//      max(FApp::GetDeltaTime()*1000) until bDone; returns false to
//      self-remove when the round finishes.
//   3. Stamp t0 (FPlatformTime::Seconds) and emit chat/send via
//      GNyraSupervisor->SendRequest. The request goes through Plan 10's
//      FNyraWsClient over the loopback WS.
//   4. Pump FTSTicker::Tick(0.016f) + Sleep(1ms) in a loop until either
//      bDone == true or the PerRoundTimeoutS deadline passes. Notifications
//      arrive on the GameThread via BenchHandleNotification which records
//      first_token, done, and usage.completion_tokens into GCurrentRound.
//   5. On success: append to per-metric sample arrays. On timeout/error:
//      bump Result.Errors and continue to the next round.
//
// After all rounds: compute p50/p95/p99 via Percentile() and evaluate the
// three pass criteria (p95 first-token < 500 ms, p95 editor tick < 33 ms,
// zero errors).
//
// COMPLIANCE GATE (PLAN.md must_haves truth #7 + acceptance criterion
// "FNyraDevTools.cpp FormatReport prepends NON-COMPLIANT header AND forces
// overall PASS verdicts to FAIL when N < 100"):
//   * ROADMAP Phase 1 SC#3 explicitly requires N >= 100 round-trips.
//   * Short sanity runs ("Nyra.Dev.RoundTripBench 5") are allowed as a dev
//     convenience but MUST NOT look like they satisfied SC#3.
//   * FormatReport detects N < 100, prepends a [NON-COMPLIANT: ...] header,
//     and forces every PASS verdict to FAIL. This keeps the Plan 15
//     deliverable (a committed green run) honest: the committed log must
//     show PASS, which requires N >= 100.
// =============================================================================

#include "Dev/FNyraDevTools.h"

#include "Process/FNyraSupervisor.h"
#include "WS/FNyraJsonRpc.h"
#include "NyraLog.h"

#include "HAL/PlatformTime.h"
#include "HAL/PlatformProcess.h"
#include "Misc/App.h"
#include "Containers/Ticker.h"
#include "Dom/JsonObject.h"
#include "Misc/Guid.h"
#include "Math/UnrealMathUtility.h"

// Forward-declare the module-level supervisor pointer defined in
// NyraEditorModule.cpp. Plan 10 established this extern pattern; Plan 12
// promoted it from static to non-static for panel use.
extern TUniquePtr<class FNyraSupervisor> GNyraSupervisor;

// -----------------------------------------------------------------------------
// Percentile helper (sort-based; suitable for N <= 1000 per PLAN.md clamp).
// Uses FMath::Clamp on the index so p100 and empty-array callers don't
// deref out-of-bounds. Returns 0.0 for empty samples.
// -----------------------------------------------------------------------------
static double Percentile(TArray<double> Samples, double P)
{
    if (Samples.Num() == 0)
    {
        return 0.0;
    }
    Samples.Sort();
    const int32 Idx = FMath::Clamp(int32(P * (Samples.Num() - 1)), 0, Samples.Num() - 1);
    return Samples[Idx];
}

// -----------------------------------------------------------------------------
// FNyraBenchResult::FormatReport
//
// Output Log block matching RESEARCH §3.6 "Reporting" exactly. The only
// runtime-derived additions are the three PASS/FAIL verdicts and the
// NON-COMPLIANT compliance header.
//
// Compliance (PLAN.md truth #7): when N < 100, prepend
//   [NON-COMPLIANT: requires N>=100 per ROADMAP Phase 1 SC#3]\n
// and force the three overall PASS verdicts to FAIL even if the individual
// thresholds passed on the shorter run.
// -----------------------------------------------------------------------------
FString FNyraBenchResult::FormatReport() const
{
    const bool bCompliant = N >= 100;
    const TCHAR* FirstTokenVerdict = (bCompliant && bPassedFirstToken) ? TEXT("PASS") : TEXT("FAIL");
    const TCHAR* EditorTickVerdict = (bCompliant && bPassedEditorTick) ? TEXT("PASS") : TEXT("FAIL");
    const TCHAR* NoErrorsVerdict   = (bCompliant && bPassedNoErrors)   ? TEXT("PASS") : TEXT("FAIL");

    const FString NonCompliantHeader = bCompliant
        ? FString()
        : FString(TEXT("[NON-COMPLIANT: requires N>=100 per ROADMAP Phase 1 SC#3]\n"));

    return NonCompliantHeader + FString::Printf(
        TEXT("\n[NyraDevTools] RoundTripBench results (N=%d):\n")
        TEXT("  first_token  p50=%7.1fms  p95=%7.1fms  p99=%7.1fms\n")
        TEXT("  total        p50=%7.1fms  p95=%7.1fms  p99=%7.1fms\n")
        TEXT("  tokens/sec   p50=%7.2f    p95=%7.2f    p99=%7.2f\n")
        TEXT("  editor_tick_max_ms  p50=%7.2f  p95=%7.2f  p99=%7.2f\n")
        TEXT("  errors=%d\n")
        TEXT("  %s first-token p95 < 500 ms\n")
        TEXT("  %s editor_tick p95 < 33 ms\n")
        TEXT("  %s zero errors\n"),
        N,
        FirstTokenP50, FirstTokenP95, FirstTokenP99,
        TotalP50, TotalP95, TotalP99,
        TokensPerSecP50, TokensPerSecP95, TokensPerSecP99,
        EditorTickMaxP50, EditorTickMaxP95, EditorTickMaxP99,
        Errors,
        FirstTokenVerdict,
        EditorTickVerdict,
        NoErrorsVerdict);
}

// -----------------------------------------------------------------------------
// Per-round state (file-static; bench is one-at-a-time per PLAN.md).
//
// Rationale for file-static rather than TLS or member-of-FNyraDevTools:
//   * The bench runs synchronously on the GameThread; only one round can
//     be active at a time, so global state is safe.
//   * BenchHandleNotification is a free-function bound to
//     FOnSupervisorNotification::BindStatic, which cannot capture a
//     per-instance pointer.
//   * The editor-tick sampler lambda also references GCurrentRound
//     directly to avoid dangling captures across the Launch/Cancel cycle.
// -----------------------------------------------------------------------------
struct FBenchRoundState
{
    FGuid ReqId;
    double T0Seconds = 0.0;
    double FirstTokenMs = 0.0;
    double DoneMs = 0.0;
    double MaxTickMs = 0.0;
    int32 FrameCount = 0;
    int32 CompletionTokens = 0;
    bool bFirstTokenSeen = false;
    bool bDone = false;
    bool bErrored = false;
};

static FBenchRoundState GCurrentRound;

// -----------------------------------------------------------------------------
// Notification handler -- bound to GNyraSupervisor->OnNotification for the
// duration of the bench run. Filters chat/stream frames matching the
// current round's req_id, records first_token on the first non-empty delta,
// and on done:true captures usage.completion_tokens + error presence.
//
// All other notification methods are ignored (download progress, etc.).
// Non-matching req_ids are also ignored so any stray chat/stream from a
// pre-bench request drains without corrupting the measurement.
// -----------------------------------------------------------------------------
static void BenchHandleNotification(const FNyraJsonRpcEnvelope& Env)
{
    if (Env.Method != TEXT("chat/stream") || !Env.Params.IsValid())
    {
        return;
    }

    FString ReqIdStr;
    if (!Env.Params->TryGetStringField(TEXT("req_id"), ReqIdStr))
    {
        return;
    }

    FGuid ReqId;
    FGuid::Parse(ReqIdStr, ReqId);
    if (ReqId != GCurrentRound.ReqId)
    {
        return;
    }

    ++GCurrentRound.FrameCount;

    FString Delta;
    Env.Params->TryGetStringField(TEXT("delta"), Delta);
    bool bDone = false;
    Env.Params->TryGetBoolField(TEXT("done"), bDone);

    const double Now = FPlatformTime::Seconds();

    // First non-empty delta marks t0 -> first_token (primary metric).
    if (!GCurrentRound.bFirstTokenSeen && !Delta.IsEmpty())
    {
        GCurrentRound.FirstTokenMs = (Now - GCurrentRound.T0Seconds) * 1000.0;
        GCurrentRound.bFirstTokenSeen = true;
    }

    if (bDone)
    {
        GCurrentRound.DoneMs = (Now - GCurrentRound.T0Seconds) * 1000.0;

        const TSharedPtr<FJsonObject>* Usage = nullptr;
        if (Env.Params->TryGetObjectField(TEXT("usage"), Usage) && Usage && Usage->IsValid())
        {
            double Ct = 0.0;
            (*Usage)->TryGetNumberField(TEXT("completion_tokens"), Ct);
            GCurrentRound.CompletionTokens = int32(Ct);
        }

        const TSharedPtr<FJsonObject>* Err = nullptr;
        if (Env.Params->TryGetObjectField(TEXT("error"), Err) && Err && Err->IsValid())
        {
            GCurrentRound.bErrored = true;
        }

        GCurrentRound.bDone = true;
    }
}

// -----------------------------------------------------------------------------
// FNyraDevTools::RunRoundTripBench
//
// GameThread-only, synchronous (intentionally -- see file header). See the
// per-round flow description at the top of this file.
//
// Pre-check: GNyraSupervisor must be valid AND GetState() == Ready. If
// not, returns Result.Errors=Count with a clear LogNyra Error diagnostic.
// Callers (OnRoundTripBenchCmd) still print the (all-error) report so the
// operator sees the Ready-state gate failure in the Output Log rather
// than silently nothing happening.
// -----------------------------------------------------------------------------
FNyraBenchResult FNyraDevTools::RunRoundTripBench(int32 Count, const FString& Prompt, double PerRoundTimeoutS)
{
    FNyraBenchResult Result;
    Result.N = Count;

    if (!GNyraSupervisor.IsValid() || GNyraSupervisor->GetState() != ENyraSupervisorState::Ready)
    {
        UE_LOG(LogNyra, Error,
            TEXT("[NyraDevTools] Supervisor not Ready; aborting bench. ")
            TEXT("Ensure NyraHost is running and Gemma is downloaded before running the bench."));
        Result.Errors = Count;
        return Result;
    }

    // Subscribe to chat/stream notifications for the bench window. Plan
    // 10's OnNotification is a single-consumer delegate (DECLARE_DELEGATE_*,
    // not multicast); binding BenchHandleNotification here temporarily
    // displaces the panel's HandleNotification. We restore it to unbound
    // on bench exit -- the panel can rebind on next supervisor event.
    FNyraSupervisor* Sup = GNyraSupervisor.Get();
    Sup->OnNotification.BindStatic(&BenchHandleNotification);

    TArray<double> FirstTokenSamples;
    TArray<double> TotalSamples;
    TArray<double> TokensPerSecSamples;
    TArray<double> EditorTickSamples;
    FirstTokenSamples.Reserve(Count);
    TotalSamples.Reserve(Count);
    TokensPerSecSamples.Reserve(Count);
    EditorTickSamples.Reserve(Count);

    for (int32 I = 0; I < Count; ++I)
    {
        // Reset per-round state + allocate a fresh req_id.
        GCurrentRound = FBenchRoundState{};
        GCurrentRound.ReqId = FGuid::NewGuid();

        // Install the editor-tick sampler. Returns true to stay alive until
        // bDone, false to auto-remove. Reads FApp::GetDeltaTime via the
        // DeltaTime arg passed by FTSTicker -- this is the authoritative
        // per-frame tick time used by editor draw code and matches
        // RESEARCH §3.6's "editor_tick_max_ms" definition.
        FTSTicker::FDelegateHandle TickHandle = FTSTicker::GetCoreTicker().AddTicker(
            FTickerDelegate::CreateLambda([](float DeltaTime) -> bool
            {
                const double Ms = double(DeltaTime) * 1000.0;
                if (Ms > GCurrentRound.MaxTickMs)
                {
                    GCurrentRound.MaxTickMs = Ms;
                }
                return !GCurrentRound.bDone;   // keep ticking until bench round done
            }), 0.0f);

        // Stamp t0 and send chat/send.
        GCurrentRound.T0Seconds = FPlatformTime::Seconds();
        TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
        Params->SetStringField(TEXT("conversation_id"),
            FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower));
        Params->SetStringField(TEXT("req_id"),
            GCurrentRound.ReqId.ToString(EGuidFormats::DigitsWithHyphensLower));
        Params->SetStringField(TEXT("content"), Prompt);
        Params->SetStringField(TEXT("backend"), TEXT("gemma-local"));
        Sup->SendRequest(TEXT("chat/send"), Params);

        // GameThread pump: Tick the core ticker (drives WS message
        // delivery via Plan 10's FNyraWsClient) until the round completes
        // or we hit the timeout. The 1 ms sleep yields briefly so we're
        // not a hot spin; the 16 ms delta passed to Tick is a target
        // frame time, not a real-time wait -- actual timing comes from
        // FPlatformProcess::Sleep and the while-loop deadline check.
        const double Deadline = FPlatformTime::Seconds() + PerRoundTimeoutS;
        while (!GCurrentRound.bDone && FPlatformTime::Seconds() < Deadline)
        {
            FTSTicker::GetCoreTicker().Tick(0.016f);
            FPlatformProcess::Sleep(0.001f);
        }

        // Defensive remove -- the ticker lambda returns false once bDone is
        // true (self-removing), but a timeout round leaves the ticker
        // alive and it would reference GCurrentRound through the next loop
        // iteration. RemoveTicker is idempotent-safe on an already-removed
        // handle (documented UE behavior).
        FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);

        if (!GCurrentRound.bDone || GCurrentRound.bErrored)
        {
            ++Result.Errors;
            UE_LOG(LogNyra, Warning,
                TEXT("[NyraDevTools] Round %d/%d errored/timed out (bDone=%d bErrored=%d)"),
                I + 1, Count, GCurrentRound.bDone ? 1 : 0, GCurrentRound.bErrored ? 1 : 0);
            continue;
        }

        FirstTokenSamples.Add(GCurrentRound.FirstTokenMs);
        TotalSamples.Add(GCurrentRound.DoneMs);

        // tokens/sec: guard DeltaMs >= 1.0 to avoid divide-by-~zero when
        // the round's model-generation window is trivially small (e.g.
        // cached warm-start that emits first_token and done in the same
        // frame). completion_tokens==0 correctly yields 0.0 samples.
        const double DeltaMs = FMath::Max(1.0, GCurrentRound.DoneMs - GCurrentRound.FirstTokenMs);
        TokensPerSecSamples.Add(double(GCurrentRound.CompletionTokens) / (DeltaMs / 1000.0));
        EditorTickSamples.Add(GCurrentRound.MaxTickMs);

        UE_LOG(LogNyra, Verbose,
            TEXT("[NyraDevTools] Round %d/%d: first=%.1fms total=%.1fms tick_max=%.2fms frames=%d"),
            I + 1, Count,
            GCurrentRound.FirstTokenMs, GCurrentRound.DoneMs,
            GCurrentRound.MaxTickMs, GCurrentRound.FrameCount);
    }

    // Unbind our notification handler. Single-consumer delegate returns to
    // unbound state; the panel's HandleNotification can re-bind as usual.
    Sup->OnNotification.Unbind();

    // Compute aggregate percentiles.
    Result.FirstTokenP50     = Percentile(FirstTokenSamples, 0.50);
    Result.FirstTokenP95     = Percentile(FirstTokenSamples, 0.95);
    Result.FirstTokenP99     = Percentile(FirstTokenSamples, 0.99);
    Result.TotalP50          = Percentile(TotalSamples, 0.50);
    Result.TotalP95          = Percentile(TotalSamples, 0.95);
    Result.TotalP99          = Percentile(TotalSamples, 0.99);
    Result.TokensPerSecP50   = Percentile(TokensPerSecSamples, 0.50);
    Result.TokensPerSecP95   = Percentile(TokensPerSecSamples, 0.95);
    Result.TokensPerSecP99   = Percentile(TokensPerSecSamples, 0.99);
    Result.EditorTickMaxP50  = Percentile(EditorTickSamples, 0.50);
    Result.EditorTickMaxP95  = Percentile(EditorTickSamples, 0.95);
    Result.EditorTickMaxP99  = Percentile(EditorTickSamples, 0.99);

    // Pass criteria (RESEARCH §3.6). IsEmpty() guard ensures an all-errors
    // run does not spuriously report PASS on 0.0 percentile defaults.
    Result.bPassedFirstToken = Result.FirstTokenP95 < 500.0 && !FirstTokenSamples.IsEmpty();
    Result.bPassedEditorTick = Result.EditorTickMaxP95 < 33.0 && !EditorTickSamples.IsEmpty();
    Result.bPassedNoErrors   = Result.Errors == 0;

    return Result;
}

// -----------------------------------------------------------------------------
// FNyraDevTools::OnRoundTripBenchCmd
//
// Console command entry point. Parses Count + Prompt from Args, clamps
// Count to [1,1000] (PLAN.md <interfaces> "simple sort-based; N <= 1000"),
// runs the bench, and prints the report to Output Log via LogNyra.
// -----------------------------------------------------------------------------
void FNyraDevTools::OnRoundTripBenchCmd(const TArray<FString>& Args)
{
    int32 Count = 100;
    FString Prompt = TEXT("Reply with OK.");

    if (Args.Num() >= 1)
    {
        LexFromString(Count, *Args[0]);
    }
    if (Args.Num() >= 2)
    {
        Prompt = Args[1];
    }
    Count = FMath::Clamp(Count, 1, 1000);

    UE_LOG(LogNyra, Log,
        TEXT("[NyraDevTools] Starting RoundTripBench N=%d prompt='%s'"),
        Count, *Prompt);

    const FNyraBenchResult R = FNyraDevTools::RunRoundTripBench(Count, Prompt);
    UE_LOG(LogNyra, Log, TEXT("%s"), *R.FormatReport());
}

// -----------------------------------------------------------------------------
// File-scope static -- registers `Nyra.Dev.RoundTripBench` on module load.
//
// FAutoConsoleCommand's constructor wires the command into the global
// console-variable manager at static-init time. Because this translation
// unit lives inside the NyraEditor module's source tree, UBT includes it
// in the build automatically and the initializer runs when the module's
// DLL loads.
// -----------------------------------------------------------------------------
static FAutoConsoleCommand GRoundTripBenchCmd(
    TEXT("Nyra.Dev.RoundTripBench"),
    TEXT("Run N chat/send round-trips; report p50/p95/p99 first-token, total, tokens/sec, editor tick. Args: [count=100] [prompt=\"Reply with OK.\"]"),
    FConsoleCommandWithArgsDelegate::CreateStatic(&FNyraDevTools::OnRoundTripBenchCmd));
