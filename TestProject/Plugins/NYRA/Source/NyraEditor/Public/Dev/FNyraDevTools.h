#pragma once

// =============================================================================
// FNyraDevTools.h  (Phase 1 Plan 14 -- Ring 0 stability gate bench harness)
// =============================================================================
//
// PURPOSE: ROADMAP Phase 1 Success Criterion 3 -- "loopback WebSocket
// (UE<->NyraHost) + localhost HTTP (NyraHost<->NyraInfer) IPC is stable over
// 100 consecutive round-trips on UE 5.6 with editor responsive during
// streaming." This file implements the editor console command that makes
// that success criterion objectively measurable.
//
// CONTEXT:  CONTEXT.md <specifics> "Ring 0 stability gate"
// RESEARCH: 01-RESEARCH.md §3.6 "Ring 0 Stability Gate -- 100 Round-Trip
//           Harness" (full metric + reporting spec).
// VALIDATION: 01-VALIDATION.md row 1-ring0 (editor console
//             `Nyra.Dev.RoundTripBench 100` -- p95 first-token < 500ms;
//             p95 editor tick < 33ms).
//
// Registration (file-scope static in FNyraDevTools.cpp):
//   static FAutoConsoleCommand GRoundTripBenchCmd(
//       TEXT("Nyra.Dev.RoundTripBench"),
//       TEXT("Run N chat/send round-trips; report p50/p95/p99 first-token..."),
//       FConsoleCommandWithArgsDelegate::CreateStatic(
//           &FNyraDevTools::OnRoundTripBenchCmd));
//
// Pass thresholds (RESEARCH §3.6 "Pass criteria (explicit)"):
//   * All N round-trips complete without WS disconnect or timeout
//   * p95 first-token latency < 500 ms
//   * p95 editor tick (FApp::GetDeltaTime * 1000) < 33 ms (30 FPS floor)
//
// Compliance gate (PLAN.md must_haves truth #7):
//   * ROADMAP Phase 1 SC#3 requires N>=100. Running with a smaller N is a
//     legitimate dev-cycle shortcut ("Nyra.Dev.RoundTripBench 5" for a
//     sanity pass) but the report must prepend a NON-COMPLIANT header and
//     force every overall PASS verdict to FAIL regardless of threshold
//     results so no one accidentally commits a 10-round result as the
//     Plan-15 deliverable.
//
// Plan 15 runs this 100x on Windows against the live stack and commits
// results to .planning/phases/01-plugin-shell-three-process-ipc/.
// =============================================================================

#include "CoreMinimal.h"
#include "WS/FNyraJsonRpc.h"

/**
 * Per-round-trip measurement captured by the bench harness.
 *
 * Populated by BenchHandleNotification during the streaming window and
 * consumed by RunRoundTripBench to build the aggregate FNyraBenchResult.
 *
 * RESEARCH §3.6 metrics table:
 *   t0 -> first_token  (primary metric -- WS + HTTP round-trip + first chunk)
 *   t0 -> done         (total duration including model generation)
 *   tokens/sec         (usage.completion_tokens / (t_done - t_first_token))
 *   editor_tick_max_ms (max FApp::GetDeltaTime * 1000 during streaming)
 *   frame_count        (total chat/stream notifications received)
 */
struct NYRAEDITOR_API FNyraBenchSample
{
    double FirstTokenMs = 0.0;
    double TotalMs = 0.0;
    double TokensPerSec = 0.0;
    double EditorTickMaxMs = 0.0;
    int32 FrameCount = 0;
    bool bSucceeded = false;
};

/**
 * Aggregated bench result across N rounds with p50/p95/p99 percentiles per
 * metric and boolean PASS flags for the three Ring 0 pass criteria.
 *
 * FormatReport() produces the human-readable Output Log block per
 * RESEARCH §3.6 "Reporting" (see FNyraDevTools.cpp for exact format).
 *
 * Compliance (N>=100 per ROADMAP Phase 1 SC#3): FormatReport prepends a
 * NON-COMPLIANT header and forces overall PASS -> FAIL when N < 100, so
 * short sanity runs cannot be accidentally committed as the Plan-15
 * deliverable.
 */
struct NYRAEDITOR_API FNyraBenchResult
{
    int32 N = 0;
    int32 Errors = 0;
    double FirstTokenP50 = 0.0,    FirstTokenP95 = 0.0,    FirstTokenP99 = 0.0;
    double TotalP50 = 0.0,         TotalP95 = 0.0,         TotalP99 = 0.0;
    double TokensPerSecP50 = 0.0,  TokensPerSecP95 = 0.0,  TokensPerSecP99 = 0.0;
    double EditorTickMaxP50 = 0.0, EditorTickMaxP95 = 0.0, EditorTickMaxP99 = 0.0;
    bool bPassedFirstToken = false;   // p95 < 500 ms
    bool bPassedEditorTick = false;   // p95 < 33 ms (30 FPS floor)
    bool bPassedNoErrors = false;

    /** Format the human-readable Output Log block. Prepends a NON-COMPLIANT
     *  header and forces overall PASS verdicts to FAIL when N < 100. */
    FString FormatReport() const;
};

/**
 * Ring 0 bench harness -- editor console command `Nyra.Dev.RoundTripBench`.
 *
 * Registered in FNyraDevTools.cpp via a file-scope FAutoConsoleCommand
 * static initializer; UBT auto-includes the cpp file in the NyraEditor
 * module so the registration runs on module load.
 *
 * All public methods are GameThread-only. RunRoundTripBench is
 * INTENTIONALLY synchronous on the GameThread (it pumps FTSTicker::Tick in
 * a loop while waiting for each round's done frame) because the whole
 * point of the bench is to measure editor-tick impact under realistic
 * load -- running the bench off-thread would invalidate
 * editor_tick_max_ms.
 */
class NYRAEDITOR_API FNyraDevTools
{
public:
    /**
     * Console command entry point. Parses args and calls RunRoundTripBench.
     *
     * Args: [count=100] [prompt="Reply with OK."]
     *   - count  : number of round-trips (clamped 1..1000). Default 100.
     *   - prompt : prompt text sent as chat/send.content. Default "Reply with OK."
     *
     * Emits a single UE_LOG(LogNyra, Log, ...) block via FormatReport() on
     * the Output Log at completion.
     */
    static void OnRoundTripBenchCmd(const TArray<FString>& Args);

    /**
     * Core benchmark runner. Returns when all rounds are done or each round
     * that times out/errors has been counted.
     *
     * GameThread only. Synchronous by design -- pumps FTSTicker::Tick in a
     * loop bounded by PerRoundTimeoutS so the editor's own tick pipeline
     * drives the WS ticker and our editor-tick sampler.
     *
     * Requires GNyraSupervisor to be Ready (bound, auth'd, and paired with
     * a live NyraHost); otherwise returns Errors=Count and logs a clear
     * diagnostic. Callers are responsible for ensuring the supervisor is
     * Ready (first-launch UX and Gemma download complete) before calling.
     */
    static FNyraBenchResult RunRoundTripBench(
        int32 Count,
        const FString& Prompt,
        double PerRoundTimeoutS = 60.0);
};
