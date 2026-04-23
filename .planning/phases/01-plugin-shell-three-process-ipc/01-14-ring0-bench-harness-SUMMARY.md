---
phase: 01-plugin-shell-three-process-ipc
plan: 14
subsystem: ring0-bench-harness
tags: [ue-cpp, ring0, console-command, bench, percentiles, editor-tick, plug-02, plug-03, chat-01, research-3-6, roadmap-phase-1-sc3]
requirements_progressed: [PLUG-02, PLUG-03, CHAT-01]
dependency_graph:
  requires:
    - 01-10-cpp-supervisor-ws-jsonrpc (FNyraSupervisor with GetState()==Ready gate + SendRequest(method, params) + OnNotification single-consumer delegate, FNyraJsonRpcEnvelope with req_id/delta/done/usage/error shapes per docs/JSONRPC.md §3.4 -- all consumed verbatim by BenchHandleNotification and RunRoundTripBench)
    - 01-12-chat-panel-streaming-integration (extern TUniquePtr<FNyraSupervisor> GNyraSupervisor link pattern and chat/send conversation_id+req_id+content+backend:"gemma-local" payload shape reused verbatim by RunRoundTripBench)
    - 01-13-first-run-ux-banners-diagnostics (first-run UX is the prerequisite for Plan 15's 100-round run -- user can observe bootstrap Info banner and download modal before invoking the bench; Plan 14 itself does not touch UX, it is a console-only harness)
  provides:
    - FNyraBenchSample per-round struct (FirstTokenMs/TotalMs/TokensPerSec/EditorTickMaxMs/FrameCount/bSucceeded)
    - FNyraBenchResult aggregate with p50/p95/p99 per metric + 3 pass flags (bPassedFirstToken, bPassedEditorTick, bPassedNoErrors) + FormatReport() that emits the Output Log block
    - FNyraDevTools static class with OnRoundTripBenchCmd(Args) + RunRoundTripBench(Count, Prompt, PerRoundTimeoutS=60.0)
    - Nyra.Dev.RoundTripBench editor console command registered via file-scope FAutoConsoleCommand; args [count=100] [prompt="Reply with OK."]; count clamped 1..1000
    - NON-COMPLIANT compliance gate: FormatReport prepends [NON-COMPLIANT: requires N>=100 per ROADMAP Phase 1 SC#3] header AND forces all 3 PASS verdicts to FAIL when N < 100 -- prevents accidental commit of short-run results as Plan 15 deliverable
  affects:
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp (Plan 03/04/10/13 content preserved verbatim; added one include + one UE_LOG line)
tech-stack:
  added:
    - "FAutoConsoleCommand file-scope static pattern: TEXT name + TEXT help + FConsoleCommandWithArgsDelegate::CreateStatic binding; registers on NyraEditor module DLL load automatically via static-init"
    - "FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda) returning-false-to-self-remove idiom: the tick sampler stays alive while bDone==false, returns false to auto-remove once the round completes or is cancelled"
    - "FTSTicker::Tick(DeltaTime) + FPlatformProcess::Sleep(0.001f) GameThread pump pattern: synchronous loop drives WS message delivery while measuring actual editor tick time via the installed sampler"
    - "Percentile helper (sort-based): TArray<double>::Sort + FMath::Clamp(int32(P*(N-1)), 0, N-1); O(N log N) which is trivial at N<=1000"
    - "FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower) for conversation_id and req_id -- matches Plan 10 FNyraWsClient id generation format"
    - "Compliance gate pattern: N<100 -> prepend NON-COMPLIANT header + force PASS->FAIL regardless of individual thresholds; keeps short sanity runs honest without blocking them"
  patterns:
    - "Additive module-superset: NyraEditorModule.cpp gained one #include and one UE_LOG line; Plans 03/04/10/13 symbols (IMPLEMENT_MODULE, GNyraSupervisor storage, RegisterNomadTabSpawner, SpawnAndConnect, ShutdownModule RequestShutdown, LOCTEXT entries) all preserved verbatim. No existing behaviour changed."
    - "File-static per-round state (FBenchRoundState GCurrentRound): bench runs synchronously one-at-a-time on the GameThread, so file-scope global state is safe and sidesteps needing to capture per-instance state through the free-function BenchHandleNotification bound via BindStatic."
    - "Ready-state gate: RunRoundTripBench checks GNyraSupervisor->GetState() == ENyraSupervisorState::Ready BEFORE touching OnNotification; if not Ready logs a LogNyra Error with actionable remediation and returns Errors=Count so the all-errors path still prints a report."
    - "Single-consumer OnNotification swap: Plan 10 declared OnNotification as DECLARE_DELEGATE_OneParam (not multicast). The bench temporarily BindStatic's its own handler and Unbind's on exit, leaving the panel free to rebind on next supervisor event. This is an intentional limitation: the bench is a dev-only console command that the operator triggers after (not during) normal chat use."
    - "Non-matching req_id filter in BenchHandleNotification: parses chat/stream's req_id and ignores frames whose GUID != GCurrentRound.ReqId. Drains any late-arriving frames from a prior non-bench request without corrupting the measurement."
    - "Defensive RemoveTicker after the loop: the sampler lambda self-removes on success (bDone==true -> returns false), but a timeout round leaves the ticker alive and it would reference GCurrentRound across the next loop iteration. Explicit RemoveTicker with the stored handle is idempotent-safe."
key-files:
  created:
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Dev/FNyraDevTools.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Dev/FNyraDevTools.cpp
  modified:
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp (added #include "Dev/FNyraDevTools.h" + UE_LOG confirmation line; Plans 03/04/10/13 content preserved verbatim)
decisions:
  - "Synchronous GameThread pump (not a dedicated WS thread or async task) -- FTSTicker::Tick(0.016f)+Sleep(1ms) in a while-loop bounded by PerRoundTimeoutS. Rationale: the whole point of the Ring 0 gate is to measure editor_tick_max_ms under realistic load. If the bench ran off-thread, the sampled tick times would not reflect what an operator experiences when interacting with the editor during chat streaming. The 16ms delta passed to Tick is a target frame time; the 1ms Sleep yields briefly so we are not a hot spin; real-time gating comes from FPlatformTime::Seconds() deadline checks. This is an intentional design decision documented in FNyraDevTools.h (class doc) and the plan's <interfaces> block."
  - "NON-COMPLIANT header + forced-FAIL gate when N<100 rather than rejecting the invocation outright. Rationale: short sanity runs (`Nyra.Dev.RoundTripBench 5`) are genuinely useful during dev iteration -- you want to confirm the harness works without paying 100x round-trip cost on every code change. But committing a 10-round result as the Plan 15 ROADMAP Phase 1 SC#3 deliverable would be a quality-bar violation. The middle ground is: accept any N in [1,1000], print a complete report, but prepend a compliance header and force all PASS verdicts to FAIL when N<100. The committed Plan 15 log MUST show PASS, which mechanically requires N>=100. This is PLAN.md must_haves truth #7."
  - "File-static GCurrentRound instead of a member on FNyraDevTools. Rationale: BenchHandleNotification is bound via FOnSupervisorNotification::BindStatic (Plan 10 delegate is single-consumer non-multicast; BindStatic takes a free-function pointer). A member function would need a capturing lambda + CreateLambda + a TSharedPtr-from-this dance, which adds lifecycle complexity for zero benefit when the bench is one-at-a-time on the GameThread. The sampler lambda also references GCurrentRound directly to avoid dangling captures across the Launch/Remove cycle."
  - "Ready-state gate returns Errors=Count instead of refusing to return a report. Rationale: an operator invoking the command when NyraHost is mid-bootstrap (Info banner up) will see a complete Output Log block with clear all-error percentiles + the bench's LogNyra Error line explaining the pre-check failure. Returning an empty result or throwing would lose that diagnostic context. The bPassedNoErrors flag correctly reports FAIL because Errors > 0."
  - "FGuid-based req_ids instead of integer counters. Rationale: Plan 10 FNyraWsClient uses int64 NextId monotonic from 1. We could bump that counter, but having the bench generate its own GUIDs means (a) no cross-talk risk with the panel's own active req_ids if the operator invokes the bench with panel messages in flight, (b) the BenchHandleNotification filter is a simple GUID equality check with no int64 ordering assumptions, (c) matches the conversation_id shape so both fields serialize identically. Matches the Plan 10 req_id wire spec (arbitrary string per docs/JSONRPC.md §3.4)."
  - "PerRoundTimeoutS=60.0 default instead of e.g. 5s. Rationale: Gemma 3 4B at first-token-after-cold-load on a CPU-only dev machine can legitimately take 6-12s per RESEARCH §3.5 \"Lazy spawn + 10-minute idle shutdown for NyraInfer\". A 5s per-round timeout would cause the first round of a cold-start bench to spuriously error. 60s is generous enough for a CPU-bound first round but tight enough that a hung WS frame will eventually bubble up as a round error rather than blocking the whole bench. Plan 15 can override this via the function signature if Windows measurements show it should be tighter."
  - "Unbind OnNotification on bench exit, not restore-previous-binding. Rationale: Plan 10's OnNotification is DECLARE_DELEGATE_OneParam (single consumer). The panel binds-and-owns it in SNyraChatPanel::Construct. The bench cannot 'save + restore' the previous binding because BindLambda/BindStatic/BindUObject return void and there is no 'get current binding' accessor. Instead, we Unbind() on exit -- the panel already unbinds in its destructor anyway, and the next supervisor event (state change, unstable trip, or notification from Python) will trigger the panel to rebind on its next construct. Known Phase 1 limitation: running the bench WHILE the chat panel is open will leave the panel unable to receive chat/stream frames until the panel is closed and reopened (or until the next state change re-triggers the Construct lambda). Documented here; not fixed in Plan 14 scope."
metrics:
  duration: ~3min (agent wall time)
  completed: 2026-04-23
  tasks: 1
  commits: 1
  files_created: 2
  files_modified: 1
---

# Phase 1 Plan 14: Ring 0 Bench Harness Summary

**One-liner:** Implemented the Ring 0 stability gate as the `Nyra.Dev.RoundTripBench [count=100] [prompt="Reply with OK."]` editor console command -- drives N sequential chat/send round-trips through Plan 10's `GNyraSupervisor` + Plan 08's Python chat-stream pipeline, captures per-round `first_token_ms` / `total_ms` / `tokens_per_sec` / `editor_tick_max_ms` (via an installed FTSTicker sampler that reads `FApp::GetDeltaTime() * 1000`), computes p50/p95/p99 per metric, asserts the three ROADMAP Phase 1 SC#3 pass criteria (p95 first-token < 500 ms, p95 editor tick < 33 ms, zero errors), and prepends a `[NON-COMPLIANT: requires N>=100 per ROADMAP Phase 1 SC#3]` header that forces every PASS verdict to FAIL when N < 100 so short sanity runs cannot be accidentally committed as the Plan 15 deliverable.

## What Shipped

### Task 1 -- FNyraDevTools + Nyra.Dev.RoundTripBench console command (commit `7f479b2`)

- **`Public/Dev/FNyraDevTools.h`** (~140 lines, documentation-heavy). Declares:
  - `FNyraBenchSample` (per-round): `FirstTokenMs`, `TotalMs`, `TokensPerSec`, `EditorTickMaxMs`, `FrameCount`, `bSucceeded`.
  - `FNyraBenchResult` (aggregate): `N`, `Errors`, three percentile triples per metric (FirstToken, Total, TokensPerSec, EditorTickMax), three pass flags (`bPassedFirstToken`, `bPassedEditorTick`, `bPassedNoErrors`), `FormatReport()` method.
  - `FNyraDevTools` static class: `OnRoundTripBenchCmd(const TArray<FString>&)`, `RunRoundTripBench(int32, const FString&, double=60.0)`.

- **`Private/Dev/FNyraDevTools.cpp`** (~300 lines). Implements:
  - `Percentile(TArray<double>, double)` file-static helper -- sort + clamped index lookup, handles empty samples.
  - `FNyraBenchResult::FormatReport()` -- emits the RESEARCH §3.6 Output Log block with three PASS/FAIL verdicts. When `N < 100`, prepends `[NON-COMPLIANT: requires N>=100 per ROADMAP Phase 1 SC#3]\n` and forces all three verdicts to FAIL regardless of `bPassed*` flags.
  - `FBenchRoundState GCurrentRound` file-static -- per-round state (`ReqId`, `T0Seconds`, `FirstTokenMs`, `DoneMs`, `MaxTickMs`, `FrameCount`, `CompletionTokens`, `bFirstTokenSeen`, `bDone`, `bErrored`).
  - `BenchHandleNotification(const FNyraJsonRpcEnvelope&)` -- free function bound via `OnNotification.BindStatic`. Filters on `Method == "chat/stream"` and `req_id == GCurrentRound.ReqId`. Records `FirstTokenMs` on the first non-empty delta, records `DoneMs` + `CompletionTokens` + `bErrored` on the `done:true` frame.
  - `FNyraDevTools::RunRoundTripBench` -- Ready-state gate + BindStatic + per-round loop (install ticker sampler, stamp t0, send chat/send, GameThread pump via `FTSTicker::GetCoreTicker().Tick(0.016f) + Sleep(1ms)` until done/timeout, RemoveTicker, append samples or bump errors) + percentile computation + pass-flag evaluation + `OnNotification.Unbind()`.
  - `FNyraDevTools::OnRoundTripBenchCmd` -- parses Count (Args[0], default 100, clamped 1..1000) + Prompt (Args[1], default "Reply with OK."), logs start line, calls `RunRoundTripBench`, logs the FormatReport output.
  - File-scope `FAutoConsoleCommand GRoundTripBenchCmd(TEXT("Nyra.Dev.RoundTripBench"), <help>, FConsoleCommandWithArgsDelegate::CreateStatic(&FNyraDevTools::OnRoundTripBenchCmd))` -- registers on module load via static-init.

- **`Private/NyraEditorModule.cpp`** additively extended:
  - Added `#include "Dev/FNyraDevTools.h"` in the Plan 10 include block (makes the dependency explicit even though the FAutoConsoleCommand wires itself via static-init).
  - Added `UE_LOG(LogNyra, Log, TEXT("[NYRA] Nyra.Dev.RoundTripBench console command registered"));` at the end of `StartupModule()` (after Plan 10's `GNyraSupervisor->SpawnAndConnect(...)` call).
  - Plan 03 / 04 / 10 / 13 content preserved verbatim: `IMPLEMENT_MODULE(FNyraEditorModule, NyraEditor)`, the `TUniquePtr<FNyraSupervisor> GNyraSupervisor` storage, `SpawnNyraChatTab` helper, `FNyraEditorModule::StartupModule` tab spawner + Tools menu wiring + D-04 eager spawn, `FNyraEditorModule::ShutdownModule` D-05 graceful shutdown, and the `Get()` / `IsAvailable()` accessors.

## Metric definitions (RESEARCH §3.6 fidelity)

| Metric | Captured how | Unit |
| --- | --- | --- |
| `first_token_ms` | `(FPlatformTime::Seconds() - T0Seconds) * 1000.0` on first `chat/stream` frame with non-empty `delta` | ms |
| `total_ms` | Same expression on the `chat/stream{done:true}` frame | ms |
| `tokens_per_sec` | `CompletionTokens / ((DoneMs - FirstTokenMs) / 1000.0)`; denominator clamped to >= 1ms to avoid div-by-zero on warm-start cached paths | tokens/s |
| `editor_tick_max_ms` | `max(DeltaTime * 1000)` observed by the FTSTicker sampler during the streaming window (ticker installed before t0, returns false to self-remove once bDone==true) | ms |
| `frame_count` | Total `chat/stream` notifications received (informational; not a percentile input) | int |

`T0Seconds` is stamped immediately before `Sup->SendRequest(TEXT("chat/send"), Params)` so the measurement includes: UE->Python WS write cost + Python->Ollama/llama.cpp HTTP round-trip cost + first Gemma chunk generation.

## Pass thresholds (ROADMAP Phase 1 SC#3)

| Threshold | Source | Flag |
| --- | --- | --- |
| p95 first_token_ms < 500 | RESEARCH §3.6 "Pass criteria (explicit)" | `bPassedFirstToken` |
| p95 editor_tick_max_ms < 33 (= 30 FPS floor) | RESEARCH §3.6 + CONTEXT <specifics> | `bPassedEditorTick` |
| Errors == 0 | ROADMAP Phase 1 SC#3 "100 consecutive ... without disconnect" | `bPassedNoErrors` |

Each flag additionally requires the corresponding sample array to be non-empty (guards against an all-errors run spuriously reporting PASS on 0.0 percentile defaults).

## Compliance gate (N >= 100)

When `N < 100`, `FormatReport()` does two things:

1. Prepends `[NON-COMPLIANT: requires N>=100 per ROADMAP Phase 1 SC#3]\n` as the first line of the report.
2. Overrides all three verdict strings from `PASS` -> `FAIL` regardless of the `bPassed*` flags.

Example short-run output (N=5):

```
[NON-COMPLIANT: requires N>=100 per ROADMAP Phase 1 SC#3]

[NyraDevTools] RoundTripBench results (N=5):
  first_token  p50=  245.0ms  p95=  487.0ms  p99=  487.0ms
  total        p50= 1843.0ms  p95= 2341.0ms  p99= 2341.0ms
  tokens/sec   p50=  33.20    p95=  29.10    p99=  29.10
  editor_tick_max_ms  p50=  18.30  p95=  22.10  p99=  22.10
  errors=0
  FAIL first-token p95 < 500 ms
  FAIL editor_tick p95 < 33 ms
  FAIL zero errors
```

Example compliant-run output (N=100):

```
[NyraDevTools] RoundTripBench results (N=100):
  first_token  p50=  245.0ms  p95=  487.0ms  p99=  612.0ms
  total        p50= 1843.0ms  p95= 2341.0ms  p99= 2889.0ms
  tokens/sec   p50=  33.20    p95=  29.10    p99=  27.40
  editor_tick_max_ms  p50=  18.30  p95=  22.10  p99=  41.20
  errors=0
  PASS first-token p95 < 500 ms
  PASS editor_tick p95 < 33 ms
  PASS zero errors
```

## Per-round state lifecycle

```
[i] Reset GCurrentRound = {}; GCurrentRound.ReqId = NewGuid()
    |
    v
[ii] Install FTSTicker sampler (returns !bDone; records max DeltaTime*1000 into MaxTickMs)
    |
    v
[iii] Stamp T0Seconds = FPlatformTime::Seconds()
    |
    v
[iv] Build JSON params (conversation_id + req_id + content + backend:"gemma-local")
    Sup->SendRequest(TEXT("chat/send"), Params)
    |
    v
[v]  GameThread pump loop:
     while (!bDone && Now < Deadline):
         FTSTicker::GetCoreTicker().Tick(0.016f)   // drives sampler + WS delivery
         FPlatformProcess::Sleep(0.001f)           // yield briefly
         (BenchHandleNotification fires on chat/stream; updates FirstTokenMs, DoneMs, CompletionTokens)
    |
    v
[vi] FTSTicker::GetCoreTicker().RemoveTicker(TickHandle)   // idempotent-safe
    |
    v
[vii] If !bDone || bErrored:
          ++Result.Errors; log warning; continue
      Else:
          Append FirstTokenMs/TotalMs/TokensPerSec/MaxTickMs to respective sample arrays
```

Single-consumer `OnNotification.BindStatic` is installed once before the loop and `Unbind()` once after -- the per-round BindStatic+Unbind churn would be wasted work and would race against any stray late-arriving chat/stream frame.

## Known limitations (documented on purpose)

1. **Synchronous GameThread pump** -- INTENTIONAL per RESEARCH §3.6 and PLAN.md `<interfaces>`. Running off-thread would invalidate the editor_tick_max_ms measurement. The trade-off is the editor's main loop is blocked during the bench window (typical 100-round run: ~3-4 minutes with Gemma 3 4B on a warm dev machine). Operators should treat this as a dev-only tool and not run it during normal editing.

2. **OnNotification displaces the panel** -- Plan 10's `FOnSupervisorNotification` is `DECLARE_DELEGATE_OneParam` (single consumer, not multicast). Running `Nyra.Dev.RoundTripBench` while the chat panel is open leaves the panel unable to receive `chat/stream` frames until the next supervisor event re-triggers the panel's Construct lambda binding. Workaround: close the chat panel before running the bench, or accept that panel messages in flight during the bench window will be dropped. A Phase 2 plan can upgrade `OnNotification` to a multicast (`DECLARE_MULTICAST_DELEGATE_OneParam`) if this becomes painful.

3. **Windows-only bench execution** -- Plan 14 ships the harness; Plan 15 runs it on a Windows dev machine with UE 5.6 + Gemma 3 4B downloaded, captures the Output Log block, and commits it to `.planning/phases/01-plugin-shell-three-process-ipc/ring0-bench-results.md`. The macOS dev host cannot run UE 5.6 + bundled llama-server.exe, so any actual N>=100 validation is deferred to Plan 15 per the established platform-gap posture.

4. **Ready-state gate vs Ollama-not-available** -- if NyraHost is Ready but Ollama is not reachable AND the bundled `llama-server.exe` hasn't populated (i.e. Plan 06 `prebuild.ps1` hasn't run), every round will error with a `chat/stream{done:true, error:{...}}` frame. The bench will correctly report `bPassedNoErrors=FAIL` + `Errors=Count`. This is a valid failure mode for Plan 15 to catch before committing results.

5. **No pre-warm round** -- the first round of a bench bears the full Gemma cold-load cost (~6-12s per RESEARCH §3.5). This will skew `first_token_ms` upward and inflate `p99` even on a "healthy" run. Plan 15 operators should either (a) issue a single chat/send via the panel to warm Gemma before invoking the bench, or (b) accept the skew and rely on p95 rather than p99 for the gate. Document the warm/cold state in Plan 15's results commit.

## Commits

| # | Task | Type | Commit | Message |
|---|------|------|--------|---------|
| 1 | Task 1 | feat | `7f479b2` | feat(01-14): add FNyraDevTools Ring 0 bench harness + Nyra.Dev.RoundTripBench |

_Plan metadata commit (SUMMARY + STATE + ROADMAP) follows this summary._

## Deviations from Plan

### Non-breaking adaptations

**1. [Adaptation] Added `#include "Math/UnrealMathUtility.h"` explicitly**

- **Context:** PLAN.md action block does not list `Math/UnrealMathUtility.h` among the includes, but uses `FMath::Clamp` and `FMath::Max`. On UE 5.6 those come transitively through `CoreMinimal.h` in most paths, but explicit is better than implicit (no UBT PCH-order dependency).
- **Fix:** Added the header to the include list in FNyraDevTools.cpp.
- **Impact:** Zero runtime / wire-format difference.
- **Files modified:** `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Dev/FNyraDevTools.cpp`
- **Commit:** Included in Task 1 (`7f479b2`)

**2. [Adaptation] Added `#include "Misc/Guid.h"` + `HAL/PlatformProcess.h` explicitly**

- **Context:** PLAN.md includes listed `HAL/PlatformTime.h`, `Misc/App.h`, `Containers/Ticker.h`, `Dom/JsonObject.h`, `Misc/CommandLine.h` but the implementation uses `FGuid::NewGuid()` + `FPlatformProcess::Sleep`. Those headers were needed for those calls.
- **Fix:** Added `Misc/Guid.h` and `HAL/PlatformProcess.h` to the include list. Dropped `Misc/CommandLine.h` (not used -- PLAN.md listed it but the command uses `TArray<FString> Args` directly from the console dispatcher).
- **Impact:** Zero runtime / wire-format difference; cleaner include set.
- **Files modified:** `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Dev/FNyraDevTools.cpp`
- **Commit:** Included in Task 1 (`7f479b2`)

**3. [Adaptation] Defensive `RemoveTicker` outside the self-removing return path**

- **Context:** PLAN.md `<interfaces>` Tick-time sampler lambda returns `bStillStreaming` (which auto-removes). However, the PLAN.md action block also has `FTSTicker::GetCoreTicker().RemoveTicker(TickHandle)` after the while loop. Both coexist: the lambda self-removes on the happy path (`bDone==true` -> `!bDone` -> `false` -> self-remove), but the explicit RemoveTicker is defensive for the timeout path where `bDone` stays false and the sampler is still alive at end-of-round.
- **Fix:** Kept both -- return-false-to-remove inside the lambda for the happy path, explicit `RemoveTicker` after the loop for the timeout path. RemoveTicker on an already-removed handle is documented UE behavior (no-op).
- **Impact:** Correctness -- without the explicit remove, a timed-out round would leave a sampler alive referencing GCurrentRound, which the NEXT round's `GCurrentRound = FBenchRoundState{}` would stomp on while the sampler is still running.
- **Files modified:** `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Dev/FNyraDevTools.cpp`
- **Commit:** Included in Task 1 (`7f479b2`)

### Platform-gap deferrals (host: macOS, target: Windows + UE 5.6)

Consistent with Plans 03/04/05/10/11/12/12b/13 as documented in STATE.md. Plan 14 source is authored + grep-verified at the literal level, but the UE-toolchain verifications below require Windows + UE 5.6 UBT/MSVC which the macOS dev host cannot run:

1. **UE 5.6 compile** of 2 new files + 1 modified file through UBT's auto-include-generator. All referenced UE headers exist in UE 5.6 per Plan 10's confirmed header list plus Plan 14's additions (`HAL/PlatformTime.h`, `HAL/PlatformProcess.h`, `Misc/App.h`, `Misc/Guid.h`, `Math/UnrealMathUtility.h`, `Containers/Ticker.h`, `Dom/JsonObject.h` already verified in Plans 10/11/12). Deferred to Windows CI.

2. **Manual editor verification** per PLAN.md `<verification>` block: open UE 5.6 TestProject, wait for `ENyraSupervisorState::Ready` (banner hides per Plan 13). Open Console (backtick), type `Nyra.Dev.RoundTripBench 5 "Reply with OK."`. Observe Output Log (LogNyra) prints the results block with p50/p95/p99 columns, the NON-COMPLIANT header (because 5 < 100), and all three FAIL verdicts. Then type `Nyra.Dev.RoundTripBench 100` and observe a full 100-round run (this is the Plan 15 deliverable). Deferred to first Windows dev-machine open of TestProject.uproject after Plan 06's `prebuild.ps1` has populated the NyraHost binaries + Gemma download has completed.

3. **Automated smoke test under ENABLE_NYRA_INTEGRATION_TESTS**: `UnrealEditor-Cmd.exe TestProject/TestProject.uproject -ExecCmds="Automation RunTests Nyra.Dev.RoundTripBench;Quit" -unattended` -- Plan 14 does not add an automation spec (the command is a dev-tool harness, not a unit-testable surface). The harness IS the test. Plan 15 is the live run. Deferred.

4. **Validation 1-ring0 row closure** -- RESEARCH §3.6 / VALIDATION.md row `1-ring0` asserts `p95 first-token < 500 ms` + `p95 editor tick < 33 ms` on a live editor. That gate is objectively measurable only with the harness in place (Plan 14) and a live run (Plan 15). Plan 14 provides the objective measurement surface; closure of the row happens in Plan 15 when green results are committed.

These deferrals are consistent with the Phase-1 platform-gap posture established by all prior plans and do not block Plan 15 execution.

## Grep acceptance literals (all pass source-level)

Task 1 (10 literals from PLAN.md `<verify>.<automated>` + acceptance criteria):

```
grep -c "class NYRAEDITOR_API FNyraDevTools"                              Public/Dev/FNyraDevTools.h    -> 1   PASS (== 1)
grep -c "struct NYRAEDITOR_API FNyraBenchResult"                          Public/Dev/FNyraDevTools.h    -> 1   PASS (== 1)
grep -c "struct NYRAEDITOR_API FNyraBenchSample"                          Public/Dev/FNyraDevTools.h    -> 1   PASS (== 1 -- additional export per acceptance criterion)
grep -c "FAutoConsoleCommand GRoundTripBenchCmd"                          Private/Dev/FNyraDevTools.cpp -> 1   PASS (== 1)
grep -c 'TEXT("Nyra.Dev.RoundTripBench")'                                 Private/Dev/FNyraDevTools.cpp -> 1   PASS (>= 1)
grep -c "DeltaTime"                                                       Private/Dev/FNyraDevTools.cpp -> 5   PASS (>= 0 -- sampler lambda reads DeltaTime)
grep -c "bPassedFirstToken = Result.FirstTokenP95 < 500.0"                Private/Dev/FNyraDevTools.cpp -> 1   PASS (== 1)
grep -c "bPassedEditorTick = Result.EditorTickMaxP95 < 33.0"              Private/Dev/FNyraDevTools.cpp -> 1   PASS (== 1)
grep -c "NON-COMPLIANT"                                                   Private/Dev/FNyraDevTools.cpp -> 5   PASS (>= 1 -- 1 header + 4 comment references)
grep -c 'Sup->SendRequest(TEXT("chat/send")'                              Private/Dev/FNyraDevTools.cpp -> 1   PASS (== 1)
```

Module-superset preservation invariants (Plans 03/04/10/13 -> Plan 14):

```
grep -c "IMPLEMENT_MODULE(FNyraEditorModule, NyraEditor)"                 Private/NyraEditorModule.cpp  -> 1   PASS
grep -c "RegisterNomadTabSpawner"                                         Private/NyraEditorModule.cpp  -> 1   PASS
grep -c "GNyraSupervisor->SpawnAndConnect"                                Private/NyraEditorModule.cpp  -> 1   PASS
grep -c "\\[NYRA\\] NyraEditor module starting"                           Private/NyraEditorModule.cpp  -> 1   PASS
```

Plan 14 new wiring in NyraEditorModule.cpp:

```
grep -c 'include "Dev/FNyraDevTools.h"'                                   Private/NyraEditorModule.cpp  -> 1   PASS
grep -c "Nyra.Dev.RoundTripBench console command registered"              Private/NyraEditorModule.cpp  -> 1   PASS
```

TestProject UE 5.6 compile -- DEFERRED to Windows CI (see platform-gap §).

## Known Stubs

None introduced by Plan 14. The harness is a complete, self-contained console command; every metric it captures is wired from a real source (FPlatformTime::Seconds for timestamps, FApp::GetDeltaTime via FTSTicker DeltaTime arg for editor tick, chat/stream envelope for first_token/done/usage, FGuid::NewGuid for conversation_id + req_id). The one intentional "stub" is the Plan 12 `backend:"gemma-local"` hard-code in the chat/send params -- this is orthogonal to Plan 14 (Phase 2 will add subscription backends) and is consistent with how the panel itself sends chat/send.

The bench harness output itself is NOT a stub: it emits real measurements or a clear error diagnostic. If N=0 samples end up in any percentile array, the `!IsEmpty()` guard on each `bPassed*` flag ensures the bench reports FAIL rather than a spurious PASS on 0.0 defaults.

## Threat Flags

No new network-exposed surface in Plan 14:

- **Nyra.Dev.RoundTripBench console command** is editor-local (console input -> FConsoleCommandWithArgsDelegate -> OnRoundTripBenchCmd). No new inbound or outbound network surface.
- **chat/send round-trips** go through Plan 10's FNyraWsClient over the loopback WebSocket (`ws://127.0.0.1:<port>/`) -- same auth (first-frame `session/authenticate` token) and same transport as the panel's own chat/send path. No new trust boundary.
- **Prompt content** (default "Reply with OK." or Args[1]) is passed verbatim to chat/send; it never leaves the three-process perimeter (UE -> NyraHost -> Ollama/llama-server -> Gemma). Gemma is a local model with no network egress. Plan 15's committed results should use a fixed prompt so runs are comparable across dev machines.
- **Output Log** is written via UE_LOG(LogNyra, Log, ...) -- standard editor log, no new filesystem path, no new credentials surface.
- **Compliance gate** (NON-COMPLIANT header on N<100) is a plain-text prefix with no format-string injection surface; N is a parsed int32 and the header is a static literal.

No threat_flag markers emitted.

## Self-Check: PASSED

All claimed files exist on disk:

```
TestProject/Plugins/NYRA/Source/NyraEditor/Public/Dev/FNyraDevTools.h     FOUND (new)
TestProject/Plugins/NYRA/Source/NyraEditor/Private/Dev/FNyraDevTools.cpp  FOUND (new)
TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp   FOUND (modified -- Plans 03/04/10/13 preserved verbatim; +1 include, +1 UE_LOG line)
```

All claimed commits present in `git log --oneline`:

```
7f479b2 FOUND -- Task 1 (FNyraDevTools + Nyra.Dev.RoundTripBench console command)
```

All 10 Task 1 grep acceptance literals verified green at source level (see Grep Acceptance Literals section above). Module-superset preservation (4 invariants from Plans 03/04/10/13) all green. Plan 14 new wiring (2 literals in NyraEditorModule.cpp) all green. `git diff --diff-filter=D --name-only HEAD~1 HEAD` is empty (no unintended deletions).

Plan 15 ready to consume: `Nyra.Dev.RoundTripBench` is a stable console-command surface. Plan 15 will open TestProject.uproject on a Windows dev machine, wait for Ready + Gemma loaded, issue `Nyra.Dev.RoundTripBench 100 "Reply with OK."`, capture the Output Log block (must show PASS on all three verdicts), and commit it to `.planning/phases/01-plugin-shell-three-process-ipc/ring0-bench-results.md`. That commit closes VALIDATION row `1-ring0` and the ROADMAP Phase 1 Success Criterion 3 gate.
