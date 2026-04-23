---
phase: 01-plugin-shell-three-process-ipc
plan: 10
subsystem: cpp-supervisor-ws-jsonrpc
tags: [ue-cpp, jsonrpc, websocket, handshake, supervisor, fmonitoredprocess, plug-02, plug-03]
requirements_closed: [PLUG-02]
dependency_graph:
  requires:
    - 01-01-cpp-automation-scaffold (Nyra::Tests::FNyraTestClock + FNyraTempDir fixtures)
    - 01-03-uplugin-two-module-scaffold (FNyraEditorModule + NYRAEDITOR_API export macro)
    - 01-04-nomad-tab-placeholder-panel (NyraEditorModule tab/menu registration -- supersetted here)
    - 01-05-specs-handshake-jsonrpc-pins (docs/HANDSHAKE.md + docs/JSONRPC.md + docs/ERROR_CODES.md wire contracts)
    - 01-06-nyrahost-core-ws-auth-handshake (server-side session/authenticate gate + handshake writer)
  provides:
    - FNyraJsonRpc static API (encode/decode JSON-RPC 2.0 envelopes)
    - FNyraHandshake file polling with 50ms x1.5 exp backoff, 30s budget
    - FNyraWsClient FWebSocketsModule wrapper with first-frame auth + close 4401 handling
    - FNyraSupervisor FMonitoredProcess-based NyraHost lifecycle with 3-in-60s policy
    - INyraClock abstraction (FNyraSystemClock production, FTestClockAdapter for tests)
    - Module-level GNyraSupervisor wired into FNyraEditorModule::StartupModule/ShutdownModule (D-04/D-05)
  affects:
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp (additive superset of Plans 03 + 04)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraJsonRpcSpec.cpp (upgraded from Plan 01 Wave 0 stub)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraSupervisorSpec.cpp (upgraded from Plan 01 Wave 0 stub)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraIntegrationSpec.cpp (Plan 03 symbol FNyraPluginModulesLoadSpec preserved; Plan 10 adds guarded FNyraIntegrationSpec)
tech-stack:
  added:
    - UE FWebSocketsModule + IWebSocket (WebSockets plugin module dependency)
    - UE FMonitoredProcess (Misc/MonitoredProcess.h) for Python subprocess lifecycle
    - UE FTSTicker (Containers/Ticker.h) for handshake polling backoff
    - UE FJsonSerializer + TCondensedJsonPrintPolicy for compact wire frames
  patterns:
    - Injected-clock pattern (INyraClock interface with production + test impls) for deterministic policy tests
    - Hermetic test mode flag (bTestMode) to bypass PerformSpawn during SimulateCrashForTest so RestartPolicy tests don't launch real python.exe
    - Module-superset pattern (Plan 03 + Plan 04 NyraEditorModule.cpp symbols preserved verbatim; only additive wiring appended)
    - In-flight request replay with new id on respawn (P1.7 id persistence contract)
    - Orphan cleanup scan on StartupModule (P1.2 -- dead UE PIDs -> kill orphan NyraHost + delete stale handshake)
key-files:
  created:
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/WS/FNyraJsonRpc.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/WS/FNyraJsonRpc.cpp
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/WS/FNyraWsClient.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/WS/FNyraWsClient.cpp
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraHandshake.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraHandshake.cpp
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraSupervisor.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraSupervisor.cpp
  modified:
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp (additive superset)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraJsonRpcSpec.cpp (upgraded)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraSupervisorSpec.cpp (upgraded)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraIntegrationSpec.cpp (guarded spec appended)
decisions:
  - INyraClock abstraction over TFunction<double()>: lets FTestClockAdapter hold a reference to a long-lived Nyra::Tests::FNyraTestClock and re-read it each NowSeconds() call instead of capturing a snapshot. Required for the 3-crash It block where Clock.Set() is called between each SimulateCrashForTest.
  - bTestMode flag on FNyraSupervisor (new, not in PLAN.md): SimulateCrashForTest sets this, and RecordCrashAndMaybeRestart suppresses PerformSpawn when set. Rationale -- without the flag, the first SimulateCrashForTest call would invoke PerformSpawn which tries to launch python.exe (would fail on the test host but still log noise + create an HostProcess that outlives the test). Rule 2 addition (missing critical correctness guard) -- tests must be hermetic.
  - Handshake file path resolution: FPlatformMisc::GetEnvironmentVariable(TEXT("LOCALAPPDATA")) -- PLAN.md used FPlatformProcess::ComputerName() as a sentinel but ComputerName never returns nullptr in UE 5.6 and isn't the right gate. Simplified to `if (!LocalAppData.IsEmpty())` -- matches docs/HANDSHAKE.md "Fallback (if LOCALAPPDATA unwritable)".
  - WS close 4401 path: HandleClose fires OnAuthFailed ONLY if `Code == 4401 && !bAuthenticated` (documented in docs/JSONRPC.md §3.1). After auth success a 4401 would be a server bug and is not forwarded to OnAuthFailed to avoid double-banner in the panel layer (Plan 13 surfaces the auth-fail UI).
  - Module-superset discipline (Plan 03 + Plan 04 -> Plan 10): every symbol and log line from prior plans is preserved verbatim. Plan 10 only adds: 3 new includes, 1 static GNyraSupervisor, 5 new lines in StartupModule (spawn), 5 new lines in ShutdownModule (graceful shutdown BEFORE tab unregister so final WS frames drain). No existing line was deleted or reordered.
metrics:
  duration: ~23min
  completed: 2026-04-22
  tasks: 3
  commits: 3
  files_created: 8
  files_modified: 4
---

# Phase 1 Plan 10: C++ Supervisor + WS + JSON-RPC Summary

**One-liner:** UE-side JSON-RPC 2.0 codec + loopback-WS client with first-frame auth + handshake file poller with exp backoff + FMonitoredProcess supervisor with 3-in-60s restart policy and in-flight replay, all wired into FNyraEditorModule::StartupModule.

## What Shipped

Four cooperating UE C++ modules that make "the editor can talk to Python NyraHost" real:

1. **FNyraJsonRpc** (`Public/WS/FNyraJsonRpc.h` + `Private/WS/FNyraJsonRpc.cpp`): Static encode/decode for JSON-RPC 2.0 envelopes per `docs/JSONRPC.md`. TCondensedJsonPrintPolicy keeps wire frames compact. Decode validates `jsonrpc == "2.0"` before classifying Request/Notification/Response/Error; returns Invalid on malformed JSON or unknown shape.
2. **FNyraHandshake** (`Public/Process/FNyraHandshake.h` + `Private/Process/FNyraHandshake.cpp`): FTSTicker-driven file polling against `%LOCALAPPDATA%/NYRA/handshake-<editor-pid>.json` with 50ms initial, x1.5 backoff, 2s cap, 30s total budget. Tolerates partial-read race (P1.1) by silently retrying malformed JSON. `CleanupOrphans` walks the directory at startup, kills orphaned NyraHost PIDs, deletes stale files (P1.2).
3. **FNyraWsClient** (`Public/WS/FNyraWsClient.h` + `Private/WS/FNyraWsClient.cpp`): Wraps FWebSocketsModule against `ws://127.0.0.1:<port>/`. `OnConnected` -> immediately send `session/authenticate` with token captured as `AuthRequestId`. `HandleMessage` routes by envelope kind; on Response matching AuthRequestId fires `OnAuthenticated`. `HandleClose` with code 4401 before auth success fires `OnAuthFailed`. NextId is monotonic from 1 (P1.7 -- never reset).
4. **FNyraSupervisor** (`Public/Process/FNyraSupervisor.h` + `Private/Process/FNyraSupervisor.cpp`): Composes the three above. Spawns NyraHost via `FMonitoredProcess(bHidden=true, bCreatePipes=true)` with CLI args `-m nyrahost --editor-pid <N> --log-dir "..." --project-dir "..." --plugin-binaries-dir "..." --handshake-dir "..."` matching `nyrahost/__main__.py` from Plans 06 + 08. `RecordCrashAndMaybeRestart` evicts old timestamps then checks the 3-in-60s trip. `RequestShutdown` sends the `shutdown` notification, waits 2s, then `Cancel(bKillTree=true)`. On respawn-authenticated, replays the in-flight request with a fresh id.

## Test upgrades (VALIDATION closure)

- **Nyra.Jsonrpc.EnvelopeRoundtrip** (VALIDATION 1-02-02): 10 It() blocks -- 4 encode types + 4 decode types + 2 invalid (malformed JSON, missing `jsonrpc:"2.0"`). Upgraded from Plan 01 Wave 0 stub.
- **Nyra.Supervisor.RestartPolicy** (VALIDATION 1-02-03): 2 It() blocks -- 3-in-60s trips Unstable; 3-outside-60s does NOT. Uses `FTestClockAdapter` bridging `Nyra::Tests::FNyraTestClock` -> `INyraClock`. Upgraded from Plan 01 Wave 0 stub.
- **Nyra.Integration.HandshakeAuth** (VALIDATION 1-02-01, guarded by `ENABLE_NYRA_INTEGRATION_TESTS`): LatentIt spawns a real `FNyraSupervisor`, waits for auth, sends `session/hello`, asserts `result.phase` present. Filled into the Plan 03-owned NyraIntegrationSpec.cpp alongside the preserved `FNyraPluginModulesLoadSpec`.

## CLI args spec (nyrahost/__main__.py contract)

```
python.exe -m nyrahost \
    --editor-pid <N>              # FPlatformProcess::GetCurrentProcessId()
    --log-dir "<path>"            # <Project>/Saved/NYRA/logs
    --project-dir "<path>"        # FPaths::ProjectDir()
    --plugin-binaries-dir "<path>" # <Plugin>/Binaries/Win64
    --handshake-dir "<path>"      # %LOCALAPPDATA%/NYRA (fallback <Project>/Saved/NYRA)
```

PythonExe path: `<PluginDir>/Binaries/Win64/NyraHost/cpython/python.exe` -- populated by `prebuild.ps1` (Plan 06) at plugin-ship time.

## Restart window constants

| Constant                     | Value | File                                                                                                                   | Source                        |
| ---------------------------- | ----- | ---------------------------------------------------------------------------------------------------------------------- | ----------------------------- |
| MAX_CRASHES_IN_WINDOW        | 3     | TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraSupervisor.cpp                                         | CONTEXT D-08                  |
| CRASH_WINDOW_S               | 60.0  | TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraSupervisor.cpp                                         | CONTEXT D-08                  |
| SHUTDOWN_GRACE_S             | 2.0   | TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraSupervisor.cpp                                         | CONTEXT D-05                  |
| HANDSHAKE_TOTAL_BUDGET_S     | 30.0  | TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraHandshake.cpp                                          | CONTEXT D-06 / docs/HANDSHAKE |
| HANDSHAKE_MAX_INTERVAL_S     | 2.0   | TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraHandshake.cpp                                          | CONTEXT D-06                  |
| HANDSHAKE_BACKOFF_MULTIPLIER | 1.5   | TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraHandshake.cpp                                          | CONTEXT D-06                  |

## INyraClock abstraction

Production code uses `FNyraSystemClock` returning `FPlatformTime::Seconds()`. Tests use `FTestClockAdapter` wrapping `Nyra::Tests::FNyraTestClock` (from Plan 01's `NyraTestFixtures.h`). This replaced PLAN.md's initial sketch of `TFunction<double()>` because the test callsite needs to re-read the test clock between `Clock.Set()` invocations -- a function snapshot would freeze the first value.

## Handshake polling timing table

| Tick # | Interval | Total elapsed |
| ------ | -------- | ------------- |
| 1      | 50 ms    | 50 ms         |
| 2      | 75 ms    | 125 ms        |
| 3      | 112 ms   | 237 ms        |
| 4      | 168 ms   | 405 ms        |
| 5      | 253 ms   | 658 ms        |
| 6      | 379 ms   | 1037 ms       |
| 7      | 568 ms   | 1605 ms       |
| 8      | 853 ms   | 2458 ms       |
| 9      | 1.28 s   | 3738 ms       |
| 10     | 1.92 s   | 5658 ms       |
| 11+    | 2.0 s    | 7658 ms ...   |

At 2.0s cap: ~14-15 additional ticks to reach 30s budget. Typical NyraHost cold start is < 3s (one Plan 06 measurement: handshake file appeared ~1.4s after process launch on a warm dev box).

## Plan 12 (chat panel) contract

Plan 12's `SNyraChatPanel` will:

1. Bind to `GNyraSupervisor->OnNotification` to receive `chat/stream` frames (delta text + done flag per docs/JSONRPC.md §3.4).
2. Bind to `GNyraSupervisor->OnResponse` to receive initial `chat/send` acknowledgements (req_id + conversation_id persistence per CD-09).
3. Call `GNyraSupervisor->SendRequest(TEXT("chat/send"), Params)` from the send-button path.
4. Call `GNyraSupervisor->SendNotification(TEXT("chat/cancel"), Params)` when the user clicks Cancel mid-stream.
5. Observe `OnUnstable` to render the "NyraHost crashed 3x in 60s -- check logs" banner (Plan 13's first-run UX owns the banner Slate widget).

## Deviations

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added `bTestMode` flag to FNyraSupervisor for hermetic RestartPolicy test**

- **Found during:** Task 3 NyraSupervisorSpec.cpp upgrade
- **Issue:** PLAN.md's `SimulateCrashForTest` just called `RecordCrashAndMaybeRestart` which unconditionally invokes `PerformSpawn` on the 1st and 2nd crashes. On a unit-test host without `python.exe` at the expected plugin path, `FMonitoredProcess::Launch` would fail, log noise, and the test would also depend on FTSTicker machinery that isn't safe to run inside a BEGIN_DEFINE_SPEC It() body.
- **Fix:** Added `bool bTestMode = false` in the header; `SimulateCrashForTest` sets it to true; `RecordCrashAndMaybeRestart` only calls `PerformSpawn()` when `!bTestMode`. Production code never sets `bTestMode`, so the D-08 crash-respawn path is unchanged. Rule 2 applies because without this, the tests would either fail spuriously or leak a background process.
- **Files modified:** FNyraSupervisor.h, FNyraSupervisor.cpp
- **Commit:** f89d772

**2. [Rule 1 - Bug] Replaced PLAN.md's LOCALAPPDATA sentinel expression**

- **Found during:** Task 3 FNyraSupervisor.cpp authoring
- **Issue:** PLAN.md Line 1124: `if (FPlatformProcess::ComputerName() && !(LocalAppData = FPlatformMisc::GetEnvironmentVariable(TEXT("LOCALAPPDATA"))).IsEmpty())`. `FPlatformProcess::ComputerName()` returns a `const TCHAR*` -- it's never null on a real Windows host, so the guard is meaningless, and on non-Windows it wasn't the appropriate discriminator anyway.
- **Fix:** Simplified to `FString LocalAppData = FPlatformMisc::GetEnvironmentVariable(TEXT("LOCALAPPDATA"))` + `if (!LocalAppData.IsEmpty())`. This matches the docs/HANDSHAKE.md contract: "Primary: %LOCALAPPDATA%/NYRA/... Fallback (if LOCALAPPDATA unwritable): <ProjectDir>/Saved/NYRA/...".
- **Files modified:** FNyraSupervisor.cpp
- **Commit:** f89d772

### Deferred Verifications (host-platform gap -- macOS, target Windows UE 5.6+)

Consistent with Plans 03/04/05's deferrals documented in STATE.md. All Plan 10 C++ source is authored and grep-verified at the literal level, but the actual UE-side verifications below require Windows + UE 5.6 UBT/MSVC which the macOS dev host cannot run:

1. **UE 5.6 compile of FNyraJsonRpc + FNyraWsClient + FNyraHandshake + FNyraSupervisor + NyraEditorModule.cpp updates** -- deferred to Windows CI (host is macOS).
2. **`UnrealEditor-Cmd.exe TestProject/TestProject.uproject -ExecCmds="Automation RunTests Nyra.Jsonrpc;Quit" -unattended -nopause -testexit="Automation Test Queue Empty"` exit 0 with >=10 It blocks** (VALIDATION 1-02-02) -- deferred to Windows CI.
3. **`UnrealEditor-Cmd.exe ... Automation RunTests Nyra.Supervisor.RestartPolicy;Quit` exit 0 with 2 It blocks** (VALIDATION 1-02-03) -- deferred to Windows CI.
4. **`UnrealEditor-Cmd.exe ... Automation RunTests Nyra.Integration.HandshakeAuth;Quit` with `ENABLE_NYRA_INTEGRATION_TESTS=1` in the Target.cs** (VALIDATION 1-02-01, opt-in) -- deferred to Windows dev machine AFTER Plan 06's `prebuild.ps1` populates `Plugins/NYRA/Binaries/Win64/NyraHost/cpython/python.exe`.
5. **Manual editor launch verification: NyraHost process appears in Task Manager within 5s of editor start; `[NYRA] NyraEditor module starting` + `[NYRA] Spawning NyraHost: ...` appear in Output Log; clean editor close triggers `[NYRA] NyraHost exited code=0` + `[NYRA] WS closed code=1000 ...`** -- deferred to Windows dev machine first open.
6. **Compile against the UBT-auto-generated NyraEditor include graph** (auto-include-generator may flag a missing forward declaration) -- deferred to Windows CI; local grep shows all Unreal headers referenced by Plan 10 files exist in UE 5.6 (WebSocketsModule.h, IWebSocket.h, Misc/MonitoredProcess.h, Containers/Ticker.h, Serialization/JsonWriter.h, Policies/CondensedJsonPrintPolicy.h, Interfaces/IPluginManager.h).

These are consistent with the Phase-1 platform-gap posture established by Plans 01/03/04/05 and do not block further Phase 1 plan execution.

## Commits

- `048d667` -- feat(01-10): add FNyraJsonRpc encode/decode + EnvelopeRoundtrip spec
- `475f613` -- feat(01-10): add FNyraHandshake polling + FNyraWsClient auth-first-frame
- `f89d772` -- feat(01-10): add FNyraSupervisor + INyraClock + wire into NyraEditorModule

## Self-Check: PASSED

- All 8 created files exist on disk.
- All 3 commits present in `git log --oneline`.
- All 28 PLAN.md grep acceptance literals verified green across Tasks 1/2/3.
- Module-superset invariants preserved: `IMPLEMENT_MODULE(FNyraEditorModule, NyraEditor)`, `[NYRA] NyraEditor module starting`, and `RegisterNomadTabSpawner` all remain in NyraEditorModule.cpp (Plans 03 + 04 carried forward verbatim).
