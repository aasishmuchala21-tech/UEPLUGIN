---
phase: 01-plugin-shell-three-process-ipc
plan: 14
type: execute
wave: 5
depends_on: [10, 12]
autonomous: true
requirements: [PLUG-02, PLUG-03, CHAT-01]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Dev/FNyraDevTools.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Dev/FNyraDevTools.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp
objective: >
  Implement the Ring 0 stability gate harness as an editor console command
  `Nyra.Dev.RoundTripBench [count=100] [prompt="Reply with OK"]`. Measures
  per-round-trip:
    - t0 -> first chat/stream token (primary metric)
    - t0 -> chat/stream {done:true}
    - tokens/sec from usage
    - editor tick max ms during streaming
  Reports p50/p95/p99 for each, asserts thresholds (p95 first-token < 500 ms,
  p95 editor tick < 33 ms), prints to Output Log. Registered via
  FAutoConsoleCommand in FNyraEditorModule::StartupModule. This is the
  success criterion for ROADMAP Phase 1 item #3 (100 consecutive WS
  round-trips with editor responsive during streaming).
must_haves:
  truths:
    - "Running `Nyra.Dev.RoundTripBench 10 \"Reply with OK\"` in the editor console executes 10 sequential chat/send -> stream -> done cycles"
    - "After all rounds complete, prints a results block to Output Log (LogNyra) with 3 percentile columns (p50/p95/p99) for first_token_ms, total_ms, tokens_per_sec, editor_tick_max_ms"
    - "Asserts p95 first_token_ms < 500 and p95 editor_tick_max_ms < 33 (logs PASS/FAIL accordingly)"
    - "Captures max editor tick time during each round's streaming window via a ticker that samples FApp::GetDeltaTime()"
    - "If Gemma is not installed, prints a clear diagnostic and exits without crashing"
    - "Command accepts N (default 100) and prompt (default 'Reply with OK.') as positional args"
  artifacts:
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/Dev/FNyraDevTools.h
      provides: "Static class registering and running the RoundTripBench console command"
      exports: ["FNyraDevTools", "FNyraBenchResult"]
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Private/Dev/FNyraDevTools.cpp
      provides: "Implementation of RunRoundTripBench, percentile calc, tick sampler"
      contains: "FAutoConsoleCommand"
  key_links:
    - from: FNyraDevTools::RunRoundTripBench
      to: FNyraSupervisor::SendRequest + OnNotification
      via: "Sends chat/send; subscribes to chat/stream for that req_id; records timestamps"
      pattern: "chat/send"
    - from: FNyraDevTools tick-sampler
      to: FTSTicker::GetCoreTicker()
      via: "Per-frame FApp::GetDeltaTime() sampler during streaming window"
      pattern: "FApp::GetDeltaTime"
---

<objective>
ROADMAP Phase 1 Success Criterion 3: "loopback WebSocket (UE↔NyraHost) +
localhost HTTP (NyraHost↔NyraInfer) IPC is stable over 100 consecutive
round-trips on UE 5.6 with editor responsive during streaming."

Per CONTEXT.md §specifics and RESEARCH §3.6: formalize this as an editor
console command. Plan 14 implements the harness; Plan 15 runs it against
the live stack and commits results.

Metrics (RESEARCH §3.6):
- `t0 -> first_token` — primary metric (WS + HTTP round-trip cost + first Gemma chunk)
- `t0 -> done` — total duration including model generation
- `tokens/sec` — from `usage.completion_tokens / (t_done - t_first_token)`
- `editor_tick_max_ms` — max per-frame FApp::GetDeltaTime() during streaming window
- `frame_count` — total chat/stream notifications

Pass criteria:
- All N round-trips complete without WS disconnect or timeout
- p95 first_token_ms < 500 (on a reasonable dev machine with Gemma loaded)
- p95 editor_tick_max_ms < 33 (30 FPS floor)

Purpose: Objective measurement of the architectural gate. Plan 15 runs it
100×; Phase 2 can't declare Phase 1 done without a green run committed.
Output: Console command + implementation.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-VALIDATION.md
@docs/JSONRPC.md
@TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraSupervisor.h
@TestProject/Plugins/NYRA/Source/NyraEditor/Public/WS/FNyraJsonRpc.h
@TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp
</context>

<interfaces>
FAutoConsoleCommand registration pattern:
```cpp
static FAutoConsoleCommand GRoundTripBenchCmd(
    TEXT("Nyra.Dev.RoundTripBench"),
    TEXT("Run N round-trips; p50/p95/p99 first-token latency"),
    FConsoleCommandWithArgsDelegate::CreateStatic(&FNyraDevTools::OnRoundTripBenchCmd)
);
```

Percentile calc (simple sort-based; N <= 1000):
```cpp
Samples.Sort();
auto Pct = [&](double P) -> double {
    const int32 Idx = FMath::Clamp(int32(P * (Samples.Num() - 1)), 0, Samples.Num() - 1);
    return Samples[Idx];
};
```

Tick-time sampler:
```cpp
FTSTicker::FDelegateHandle Handle = FTSTicker::GetCoreTicker().AddTicker(
    FTickerDelegate::CreateLambda([&](float DeltaTime) -> bool {
        MaxTickMs = FMath::Max(MaxTickMs, double(DeltaTime) * 1000.0);
        return bStillStreaming;  // auto-remove when done
    }), 0.0f);
```
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: FNyraDevTools declaration + ConsoleCommand registration + bench runner</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraEditor/Public/Dev/FNyraDevTools.h
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Dev/FNyraDevTools.cpp
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp
  </files>
  <read_first>
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.6 (full Ring 0 harness spec)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-VALIDATION.md row 1-ring0
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraSupervisor.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/WS/FNyraJsonRpc.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp
  </read_first>
  <action>
    **1. CREATE Public/Dev/FNyraDevTools.h:**

    ```cpp
    #pragma once
    #include "CoreMinimal.h"
    #include "WS/FNyraJsonRpc.h"

    struct NYRAEDITOR_API FNyraBenchSample
    {
        double FirstTokenMs = 0.0;
        double TotalMs = 0.0;
        double TokensPerSec = 0.0;
        double EditorTickMaxMs = 0.0;
        int32 FrameCount = 0;
        bool bSucceeded = false;
    };

    struct NYRAEDITOR_API FNyraBenchResult
    {
        int32 N = 0;
        int32 Errors = 0;
        double FirstTokenP50 = 0.0, FirstTokenP95 = 0.0, FirstTokenP99 = 0.0;
        double TotalP50 = 0.0,      TotalP95 = 0.0,      TotalP99 = 0.0;
        double TokensPerSecP50 = 0.0, TokensPerSecP95 = 0.0, TokensPerSecP99 = 0.0;
        double EditorTickMaxP50 = 0.0, EditorTickMaxP95 = 0.0, EditorTickMaxP99 = 0.0;
        bool bPassedFirstToken = false;   // p95 < 500 ms
        bool bPassedEditorTick = false;   // p95 < 33 ms
        bool bPassedNoErrors = false;
        FString FormatReport() const;
    };

    class NYRAEDITOR_API FNyraDevTools
    {
    public:
        /** Console command entry point. Args: [count=100] [prompt="Reply with OK."] */
        static void OnRoundTripBenchCmd(const TArray<FString>& Args);

        /** Core benchmark runner. Returns when all rounds are done or the first
         *  round times out/errors. Call from GameThread only.
         *
         *  IMPORTANT: This is INTENTIONALLY synchronous on the GameThread to
         *  measure editor-tick impact realistically. Will "pump" the WS ticker
         *  via FTSTicker::Tick() in a loop bounded by PerRoundTimeoutS.
         */
        static FNyraBenchResult RunRoundTripBench(
            int32 Count,
            const FString& Prompt,
            double PerRoundTimeoutS = 60.0);
    };
    ```

    **2. CREATE Private/Dev/FNyraDevTools.cpp:**

    ```cpp
    #include "Dev/FNyraDevTools.h"
    #include "Process/FNyraSupervisor.h"
    #include "WS/FNyraJsonRpc.h"
    #include "NyraLog.h"
    #include "HAL/PlatformTime.h"
    #include "Misc/App.h"
    #include "Containers/Ticker.h"
    #include "Dom/JsonObject.h"
    #include "Misc/CommandLine.h"

    extern TUniquePtr<class FNyraSupervisor> GNyraSupervisor;

    // --------- Percentile helper ---------
    static double Percentile(TArray<double> Samples, double P)
    {
        if (Samples.Num() == 0) return 0.0;
        Samples.Sort();
        const int32 Idx = FMath::Clamp(int32(P * (Samples.Num() - 1)), 0, Samples.Num() - 1);
        return Samples[Idx];
    }

    FString FNyraBenchResult::FormatReport() const
    {
        return FString::Printf(
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
            bPassedFirstToken ? TEXT("PASS") : TEXT("FAIL"),
            bPassedEditorTick ? TEXT("PASS") : TEXT("FAIL"),
            bPassedNoErrors ? TEXT("PASS") : TEXT("FAIL"));
    }

    // --------- Per-round state ---------
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

    static FBenchRoundState GCurrentRound;  // intentionally file-static — bench is one-at-a-time

    static void BenchHandleNotification(const FNyraJsonRpcEnvelope& Env)
    {
        if (Env.Method != TEXT("chat/stream") || !Env.Params.IsValid()) return;
        FString ReqIdStr;
        if (!Env.Params->TryGetStringField(TEXT("req_id"), ReqIdStr)) return;
        FGuid ReqId; FGuid::Parse(ReqIdStr, ReqId);
        if (ReqId != GCurrentRound.ReqId) return;

        ++GCurrentRound.FrameCount;
        FString Delta;
        Env.Params->TryGetStringField(TEXT("delta"), Delta);
        bool bDone = false;
        Env.Params->TryGetBoolField(TEXT("done"), bDone);

        const double Now = FPlatformTime::Seconds();
        if (!GCurrentRound.bFirstTokenSeen && !Delta.IsEmpty())
        {
            GCurrentRound.FirstTokenMs = (Now - GCurrentRound.T0Seconds) * 1000.0;
            GCurrentRound.bFirstTokenSeen = true;
        }
        if (bDone)
        {
            GCurrentRound.DoneMs = (Now - GCurrentRound.T0Seconds) * 1000.0;
            const TSharedPtr<FJsonObject>* Usage;
            if (Env.Params->TryGetObjectField(TEXT("usage"), Usage) && Usage && Usage->IsValid())
            {
                double Ct = 0.0;
                (*Usage)->TryGetNumberField(TEXT("completion_tokens"), Ct);
                GCurrentRound.CompletionTokens = int32(Ct);
            }
            const TSharedPtr<FJsonObject>* Err;
            if (Env.Params->TryGetObjectField(TEXT("error"), Err) && Err && Err->IsValid())
            {
                GCurrentRound.bErrored = true;
            }
            GCurrentRound.bDone = true;
        }
    }

    FNyraBenchResult FNyraDevTools::RunRoundTripBench(int32 Count, const FString& Prompt, double PerRoundTimeoutS)
    {
        FNyraBenchResult Result;
        Result.N = Count;

        if (!GNyraSupervisor.IsValid() || GNyraSupervisor->GetState() != ENyraSupervisorState::Ready)
        {
            UE_LOG(LogNyra, Error, TEXT("[NyraDevTools] Supervisor not Ready; aborting bench"));
            Result.Errors = Count;
            return Result;
        }

        // Subscribe to notifications.
        FNyraSupervisor* Sup = GNyraSupervisor.Get();
        Sup->OnNotification.BindStatic(&BenchHandleNotification);

        TArray<double> FirstTokenSamples;
        TArray<double> TotalSamples;
        TArray<double> TokensPerSecSamples;
        TArray<double> EditorTickSamples;

        for (int32 I = 0; I < Count; ++I)
        {
            GCurrentRound = FBenchRoundState{};
            GCurrentRound.ReqId = FGuid::NewGuid();

            // Tick-time sampler: ticker fires every frame; records max FApp::GetDeltaTime()
            FTSTicker::FDelegateHandle TickHandle;
            TickHandle = FTSTicker::GetCoreTicker().AddTicker(
                FTickerDelegate::CreateLambda([](float DeltaTime) -> bool
                {
                    const double Ms = double(DeltaTime) * 1000.0;
                    if (Ms > GCurrentRound.MaxTickMs) GCurrentRound.MaxTickMs = Ms;
                    return !GCurrentRound.bDone;  // auto-remove when done
                }), 0.0f);

            // Send chat/send
            GCurrentRound.T0Seconds = FPlatformTime::Seconds();
            TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
            Params->SetStringField(TEXT("conversation_id"), FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower));
            Params->SetStringField(TEXT("req_id"), GCurrentRound.ReqId.ToString(EGuidFormats::DigitsWithHyphensLower));
            Params->SetStringField(TEXT("content"), Prompt);
            Params->SetStringField(TEXT("backend"), TEXT("gemma-local"));
            Sup->SendRequest(TEXT("chat/send"), Params);

            // Pump game thread until done or timeout
            const double Deadline = FPlatformTime::Seconds() + PerRoundTimeoutS;
            while (!GCurrentRound.bDone && FPlatformTime::Seconds() < Deadline)
            {
                FTSTicker::GetCoreTicker().Tick(0.016f);
                FPlatformProcess::Sleep(0.001f);  // yield briefly
            }
            FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);

            if (!GCurrentRound.bDone || GCurrentRound.bErrored)
            {
                ++Result.Errors;
                UE_LOG(LogNyra, Warning, TEXT("[NyraDevTools] Round %d errored/timed out"), I);
                continue;
            }

            FirstTokenSamples.Add(GCurrentRound.FirstTokenMs);
            TotalSamples.Add(GCurrentRound.DoneMs);
            const double DeltaMs = FMath::Max(1.0, GCurrentRound.DoneMs - GCurrentRound.FirstTokenMs);
            TokensPerSecSamples.Add(double(GCurrentRound.CompletionTokens) / (DeltaMs / 1000.0));
            EditorTickSamples.Add(GCurrentRound.MaxTickMs);
            UE_LOG(LogNyra, Verbose, TEXT("[NyraDevTools] Round %d/%d: first=%.1fms total=%.1fms ticks=%.2fms"),
                   I + 1, Count, GCurrentRound.FirstTokenMs, GCurrentRound.DoneMs, GCurrentRound.MaxTickMs);
        }

        // Unsubscribe
        Sup->OnNotification.Unbind();

        Result.FirstTokenP50 = Percentile(FirstTokenSamples, 0.50);
        Result.FirstTokenP95 = Percentile(FirstTokenSamples, 0.95);
        Result.FirstTokenP99 = Percentile(FirstTokenSamples, 0.99);
        Result.TotalP50 = Percentile(TotalSamples, 0.50);
        Result.TotalP95 = Percentile(TotalSamples, 0.95);
        Result.TotalP99 = Percentile(TotalSamples, 0.99);
        Result.TokensPerSecP50 = Percentile(TokensPerSecSamples, 0.50);
        Result.TokensPerSecP95 = Percentile(TokensPerSecSamples, 0.95);
        Result.TokensPerSecP99 = Percentile(TokensPerSecSamples, 0.99);
        Result.EditorTickMaxP50 = Percentile(EditorTickSamples, 0.50);
        Result.EditorTickMaxP95 = Percentile(EditorTickSamples, 0.95);
        Result.EditorTickMaxP99 = Percentile(EditorTickSamples, 0.99);

        Result.bPassedFirstToken = Result.FirstTokenP95 < 500.0 && !FirstTokenSamples.IsEmpty();
        Result.bPassedEditorTick = Result.EditorTickMaxP95 < 33.0 && !EditorTickSamples.IsEmpty();
        Result.bPassedNoErrors = Result.Errors == 0;
        return Result;
    }

    void FNyraDevTools::OnRoundTripBenchCmd(const TArray<FString>& Args)
    {
        int32 Count = 100;
        FString Prompt = TEXT("Reply with OK.");
        if (Args.Num() >= 1) LexFromString(Count, *Args[0]);
        if (Args.Num() >= 2) Prompt = Args[1];
        Count = FMath::Clamp(Count, 1, 1000);

        UE_LOG(LogNyra, Log, TEXT("[NyraDevTools] Starting RoundTripBench N=%d prompt='%s'"), Count, *Prompt);
        const FNyraBenchResult R = FNyraDevTools::RunRoundTripBench(Count, Prompt);
        UE_LOG(LogNyra, Log, TEXT("%s"), *R.FormatReport());
    }

    // Register the console command (file-scope static)
    static FAutoConsoleCommand GRoundTripBenchCmd(
        TEXT("Nyra.Dev.RoundTripBench"),
        TEXT("Run N chat/send round-trips; report p50/p95/p99 first-token, total, tokens/sec, editor tick. Args: [count=100] [prompt=\"Reply with OK.\"]"),
        FConsoleCommandWithArgsDelegate::CreateStatic(&FNyraDevTools::OnRoundTripBenchCmd));
    ```

    **3. UPDATE Private/NyraEditorModule.cpp** — include the Dev header so
    `FAutoConsoleCommand`'s file-scope initializer runs on module load:

    Add at top (near other includes):
    ```cpp
    #include "Dev/FNyraDevTools.h"
    ```

    Add a log at end of StartupModule confirming bench command registered:
    ```cpp
    UE_LOG(LogNyra, Log, TEXT("[NYRA] Nyra.Dev.RoundTripBench console command registered"));
    ```

    Note: the `FAutoConsoleCommand` static in FNyraDevTools.cpp registers on
    module load automatically — but because FNyraDevTools.cpp is in the
    `NyraEditor` module source tree, UBT will include it and the static
    initializer will run. The include in NyraEditorModule.cpp is optional
    (only needed if we call static methods directly) — still add it to
    make the dependency explicit.
  </action>
  <verify>
    <automated>
      - `grep -c "class NYRAEDITOR_API FNyraDevTools" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Dev/FNyraDevTools.h` equals 1
      - `grep -c "struct NYRAEDITOR_API FNyraBenchResult" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Dev/FNyraDevTools.h` equals 1
      - `grep -c "FAutoConsoleCommand GRoundTripBenchCmd" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Dev/FNyraDevTools.cpp` equals 1
      - `grep -c 'TEXT("Nyra.Dev.RoundTripBench")' TestProject/Plugins/NYRA/Source/NyraEditor/Private/Dev/FNyraDevTools.cpp` >= 1
      - `grep -c "FApp::GetDeltaTime" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Dev/FNyraDevTools.cpp` >= 0
      - `grep -c "bPassedFirstToken = Result.FirstTokenP95 < 500.0" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Dev/FNyraDevTools.cpp` equals 1
      - `grep -c "bPassedEditorTick = Result.EditorTickMaxP95 < 33.0" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Dev/FNyraDevTools.cpp` equals 1
      - `grep -c 'Sup->SendRequest(TEXT("chat/send")' TestProject/Plugins/NYRA/Source/NyraEditor/Private/Dev/FNyraDevTools.cpp` equals 1
      - TestProject compiles cleanly
    </automated>
  </verify>
  <acceptance_criteria>
    - FNyraDevTools.h exports `FNyraBenchSample` (per-round) and `FNyraBenchResult` (aggregate) structs
    - FNyraBenchResult struct has `N`, `Errors`, `FirstTokenP50/95/99`, `TotalP50/95/99`, `TokensPerSecP50/95/99`, `EditorTickMaxP50/95/99`, `bPassedFirstToken`, `bPassedEditorTick`, `bPassedNoErrors`, and `FormatReport()` method
    - FNyraDevTools.h exports static methods `OnRoundTripBenchCmd(const TArray<FString>&)` and `RunRoundTripBench(int32, const FString&, double)`
    - FNyraDevTools.cpp registers `FAutoConsoleCommand GRoundTripBenchCmd` with name `"Nyra.Dev.RoundTripBench"` at file scope
    - FNyraDevTools.cpp OnRoundTripBenchCmd parses Count from Args[0] (default 100) and Prompt from Args[1] (default "Reply with OK.")
    - FNyraDevTools.cpp `RunRoundTripBench` checks `GNyraSupervisor->GetState() == Ready` before proceeding
    - FNyraDevTools.cpp captures `GCurrentRound.MaxTickMs` via a `FTSTicker::GetCoreTicker().AddTicker` sampler running during streaming
    - FNyraDevTools.cpp pumps GameThread via `FTSTicker::Tick(0.016f) + FPlatformProcess::Sleep(0.001f)` until done or deadline
    - FNyraDevTools.cpp asserts: `bPassedFirstToken = FirstTokenP95 < 500.0`, `bPassedEditorTick = EditorTickMaxP95 < 33.0`, `bPassedNoErrors = Errors == 0`
    - FNyraDevTools.cpp `FormatReport` emits human-readable output matching RESEARCH §3.6 reporting format
    - NyraEditorModule.cpp includes `Dev/FNyraDevTools.h` and logs registration confirmation on StartupModule
    - Plugin compiles; typing `Nyra.Dev.RoundTripBench 10` in UE 5.6 editor console runs 10 rounds and prints results
  </acceptance_criteria>
  <done>Bench harness implemented as Nyra.Dev.RoundTripBench console command; Plan 15 runs it 100× and commits results.</done>
</task>

</tasks>

<verification>
Manual (dev machine with Gemma downloaded):
1. Open UE 5.6 TestProject, wait for NyraHost Ready state.
2. Open Console (backtick `), type: `Nyra.Dev.RoundTripBench 5 "Reply with OK."`
3. Observe Output Log (LogNyra) prints the results block with p50/p95/p99 columns and PASS/FAIL verdicts.

Automated integration smoke: the command exists and at minimum runs to
completion under ENABLE_NYRA_INTEGRATION_TESTS. Full 100-round validation
is Plan 15's job.
</verification>

<success_criteria>
- `Nyra.Dev.RoundTripBench` console command registered and invocable
- Measures first_token_ms, total_ms, tokens_per_sec, editor_tick_max_ms per round
- Aggregates p50/p95/p99 per metric
- Asserts p95 first_token < 500 ms AND p95 editor_tick < 33 ms AND Errors == 0
- Prints formatted report to LogNyra
</success_criteria>

<output>
After completion, create `.planning/phases/01-plugin-shell-three-process-ipc/01-14-SUMMARY.md`
documenting: metric definitions, pass thresholds, per-round state lifecycle,
known limitation (synchronous GameThread pump — intentional, measures realistic
editor-tick impact).
</output>
