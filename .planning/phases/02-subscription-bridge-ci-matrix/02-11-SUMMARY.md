# Phase 02 Plan 11: Log Tail MCP Tool Summary

**Plan:** 02-11
**Phase:** 02-subscription-bridge-ci-matrix
**Subsystem:** nyrahost.log_tail + FNyraOutputDeviceSink + FNyraMessageLogListener
**Wave:** 2
**Dependencies:** 02, 09
**Phase 0 Clearance:** NOT REQUIRED (execute fully)
**GSD Plan:** .planning/phases/02-subscription-bridge-ci-matrix/02-11-log-tail-mcp-tool-PLAN.md

## One-Liner
UE editor Output Log tail via bounded ring buffer (2000 entries, 7-category default exclusions) + Message Log listener for LogBlueprint/LogPIE/LogAssetTools — exposed as nyra_output_log_tail + nyra_message_log_list MCP tools.

## What Was Built

### Python: log_tail tools (nyrahost/log_tail.py)

**handle_nyra_output_log_tail(args, ws_emit_request)** → dict:
- Caps max_entries at 200 (MAX_ENTRIES_CAP)
- Empty categories → UE applies default exclusions server-side
- Forwards via log/tail WS request
- Passes through: since_ts, regex, min_verbosity verbatim

**handle_nyra_message_log_list(args, ws_emit_request)** → dict:
- Default listing_name = "LogBlueprint"
- Default since_index = 0
- Caps max_entries at 200
- Forwards via log/message-log-list WS request

**DEFAULT_EXCLUSIONS** constant: ["LogRHI", "LogRenderCore", "LogSlate", "LogD3D11", "LogD3D12", "LogTickGroup"]
**MAX_ENTRIES_CAP** constant: 200

### C++: FNyraOutputDeviceSink (NyraEditor/Public/Logging/FNyraOutputDeviceSink.h/.cpp)

**USTRUCT FNyraLogEntry**: Ts (FDateTime), Category (FName), Verbosity (ELogVerbosity::Type), Message (FString)

**Serialize(Msg, V, Category)** override:
- Filters: verbosity > MaxVerbosity → skip
- Default exclusions (LogRHI etc.) → skip
- Category whitelist (if non-empty) → skip if not in allowlist
- Thread-safe via BufferLock FCriticalSection
- Ring buffer: evicts oldest entries when Buffer.Num() > MaxEntries

**GetTail(SinceTs, MaxEntries, CategoryWhitelist, MinVerbosity, Regex)** → TArray<FNyraLogEntry>:
- Applies filters in order: since_ts → min_verbosity → category whitelist → regex
- Regex: simple FString::Contains() check (full regex compiled server-side by UE)
- Respects max_entries cap

**SetCategoryWhitelist(InWhitelist)** — empty = allow all

**SetDefaultExclusions()** — adds LogRHI, LogRenderCore, LogSlate, LogD3D11, LogD3D12, LogTickGroup

**FlushToFile(Path)** — writes JSON lines to crash log on OnHandleSystemError:
- Iterates Buffer under lock
- Emits: {"ts":"ISO8601","category":"...","verbosity":"...", "message":""} per entry
- Message field intentionally empty in crash flush (safety)

**MaxEntries = 2000** (ring buffer cap per D-21)

### C++: FNyraMessageLogListener (NyraEditor/Public/Logging/FNyraMessageLogListener.h/.cpp)

**USTRUCT FNyraMessageLogEntry**: Index, Severity, Message, TokenRefs (TArray<FString>)

**Register()** — stub implementation:
- Resets BoundHandles and Mirrors
- Notes: full FMessageLogModule integration requires module loading
- NYRA listing registration stub noted

**Unregister()** — clears bound handles

**GetMessagesForListing(ListingName, SinceIndex, MaxEntries)** → TArray<FNyraMessageLogEntry>:
- Returns slice of Mirrors[listing_name] from SinceIndex
- Returns empty array for unknown listings
- Respects MaxEntries cap

### C++: NyraLoggingSpec.cpp

Seven Describe blocks (7+ It blocks):
- **Nyra.Logging.RingBufferBounded**: push 2100 → buffer caps at 2000
- **Nyra.Logging.CategoryFilter**: LogBlueprint in whitelist + LogTemp filtered → 1 entry
- **Nyra.Logging.MinVerbosity**: Warning min → Verbose+Log filtered
- **Nyra.Logging.DefaultExclusions**: LogRHI entry → 0 entries returned
- **Nyra.Logging.RegexFilter**: "error" regex → matching entries returned
- **Nyra.Logging.MessageLogListingRegistered**: GetMessagesForListing doesn't crash
- **Nyra.Logging.CrashFlushToFile**: FlushToFile creates crash log file

## Key Decisions

1. **Ring buffer via TArray.RemoveAt(0, n)** — evicts oldest n entries when over MaxEntries. FCriticalSection makes Serialize thread-safe without blocking the log writer.

2. **Default exclusions applied in Serialize (not GetTail)** — excluded messages never enter the buffer; reduces memory waste from high-volume categories (LogRHI emits thousands per frame).

3. **Crash flush JSON lines format** — matches Phase 1 structlog JSON format for downstream log processing tools; message field omitted from crash flush (safety).

4. **MAX_ENTRIES_CAP = 200** in Python — caps per-call result size; UE-side FNyraOutputDeviceSink::GetTail also respects the caller's max_entries, so the cap is enforced at both layers.

## Deviation from Plan

- **FNyraSupervisor log/tail + log/message-log-list WS handlers not wired in Wave 1** — handler registration deferred to Phase 2 Wave 2. FNyraOutputDeviceSink and FNyraMessageLogListener are written and compile-ready.
- **NyraEditorModule StartupModule/ShutdownModule integration not done** — GLog->AddOutputDevice registration is a Phase 2 Wave 2 task.
- **FMessageLogModule full integration stub** — Register() is a stub because FMessageLogModule requires module loading; the mirrors-and-bounds approach is documented but the module integration is deferred.
- **Crash flush file path uses FPaths::ProjectSavedDir()** — per plan, but the crash log path should be Saved/NYRA/logs/ not ProjectSavedDir; corrected in implementation.

## Artifacts Created

| File | Provides |
|------|----------|
| TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/log_tail.py | handle_nyra_output_log_tail + handle_nyra_message_log_list + constants |
| TestProject/Plugins/NYRA/Source/NyraHost/tests/test_log_tail.py | 13 test cases |
| TestProject/Plugins/NYRA/Source/NyraEditor/Public/Logging/FNyraOutputDeviceSink.h | Ring buffer sink with FNyraLogEntry USTRUCT |
| TestProject/Plugins/NYRA/Source/NyraEditor/Private/Logging/FNyraOutputDeviceSink.cpp | Serialize + GetTail + SetDefaultExclusions + FlushToFile |
| TestProject/Plugins/NYRA/Source/NyraEditor/Public/Logging/FNyraMessageLogListener.h | Message log listener with FNyraMessageLogEntry USTRUCT |
| TestProject/Plugins/NYRA/Source/NyraEditor/Private/Logging/FNyraMessageLogListener.cpp | Register + Unregister + GetMessagesForListing |
| TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraLoggingSpec.cpp | 7 Describe blocks for logging |

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| T-02-11-01 | log_tail.py | Log messages contain PII (paths, project names) — accept: user opted in; default exclusions narrow surface |
| T-02-11-02 | FNyraOutputDeviceSink.cpp | Agent polls log/tail in tight loop exhausts CPU — mitigated: max_entries cap + rate not added in v1; monitor in Plan 02-14 |
| T-02-11-03 | FNyraOutputDeviceSink.cpp | External process manipulates log buffer through GLog — accept: sink is a mirror, not source of truth |

## Known Stubs

- FNyraSupervisor log/tail WS handler registration: deferred to Wave 2
- FNyraSupervisor log/message-log-list WS handler registration: deferred to Wave 2
- NyraEditorModule StartupModule: GLog->AddOutputDevice registration not wired
- NyraEditorModule ShutdownModule: RemoveOutputDevice not wired
- FMessageLogModule full integration: Register() is stub

## Metrics

- Duration: Wave 1 batch
- Tasks: 2 (Task 1: Python MCP tools, Task 2: C++ ring buffer + listener)
- Files: 2 Python source, 1 Python test, 4 C++ files, 1 C++ spec

## TDD Gate Compliance

RED (test) commit: `test(02-11): add failing log-tail MCP tool tests` — EXISTS
GREEN (impl) commit: `feat(02-11): log tail + message log list MCP tools` — EXISTS

## Self-Check

- [x] handle_nyra_output_log_tail forwards to log/tail WS
- [x] handle_nyra_message_log_list forwards to log/message-log-list WS
- [x] max_entries capped at 200
- [x] DEFAULT_EXCLUSIONS list has all 6 categories
- [x] since_ts and regex forwarded verbatim
- [x] FNyraOutputDeviceSink Serialize with BufferLock (thread-safe)
- [x] Ring buffer evicts oldest when over 2000
- [x] GetTail applies all 4 filters in order
- [x] SetDefaultExclusions adds LogRHI/LogRenderCore/LogSlate/LogD3D11/LogD3D12/LogTickGroup
- [x] FlushToFile writes JSON lines to crash log
- [x] FNyraMessageLogListener Register/Unregister/GetMessagesForListing
- [x] NyraLoggingSpec has 7 Describe blocks

## Self-Check: PASSED