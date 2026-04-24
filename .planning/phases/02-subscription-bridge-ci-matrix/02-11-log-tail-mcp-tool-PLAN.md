---
phase: 02-subscription-bridge-ci-matrix
plan: 11
slug: log-tail-mcp-tool
type: execute
wave: 2
depends_on: [02, 09]
autonomous: true
tdd: true
requirements: [ACT-07]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/log_tail.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/__init__.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/log_tail.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_log_tail.py
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Logging/FNyraOutputDeviceSink.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Logging/FNyraOutputDeviceSink.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Logging/FNyraMessageLogListener.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Logging/FNyraMessageLogListener.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraLoggingSpec.cpp
research_refs: [§8.1, §8.2, §8.3, §8.4, §8.5, §8.6, §8.7]
context_refs: [D-21, D-22, D-23, D-24]
phase0_clearance_required: false
must_haves:
  truths:
    - "FNyraOutputDeviceSink extends FOutputDevice; Serialize() filters by ENyraLogVerbosity max + category whitelist, stores FNyraLogEntry {ts, category, verbosity, message} in a bounded ring buffer (MaxEntries=2000 per D-21)"
    - "Registered via GLog->AddOutputDevice in FNyraEditorModule::StartupModule; unregistered in ShutdownModule"
    - "Public API: GetTail(since_ts, max_entries, category_whitelist, min_verbosity, regex) returns TArray<FNyraLogEntry>"
    - "FNyraMessageLogListener binds OnDataChanged for existing listings (LogBlueprint, LogPIE, LogAssetTools); registers own NYRA listing via FMessageLogModule; GetMessagesForListing(name, since_index, max_entries) returns FTokenizedMessage snapshots"
    - "FCoreDelegates::OnHandleSystemError binding flushes ring buffer to Saved/NYRA/logs/crash-<ts>.log (RESEARCH §8.7)"
    - "log/tail request handler (UE-side) consumes params per docs/JSONRPC.md §4.6; default categories exclude LogRHI/LogRenderCore; max_entries cap=200"
    - "log/message-log-list request handler consumes params per §4.7"
    - "nyra_output_log_tail MCP tool registered; maps to log/tail WS request"
    - "nyra_message_log_list MCP tool registered; maps to log/message-log-list"
    - "Default high-verbosity exclusion list: LogRHI, LogRenderCore, LogSlate, LogD3D11, LogD3D12, LogTickGroup (D-21)"
    - "NyraLoggingSpec.cpp tests: Nyra.Logging.RingBufferBounded (2000 cap), Nyra.Logging.CategoryFilter, Nyra.Logging.MinVerbosity, Nyra.Logging.MessageLogListingRegistered"
  artifacts:
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/Logging/FNyraOutputDeviceSink.h
      provides: "FOutputDevice subclass with filtering + ring buffer + GetTail API"
      exports: ["FNyraOutputDeviceSink", "FNyraLogEntry", "ENyraLogVerbosity"]
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/Logging/FNyraMessageLogListener.h
      provides: "FMessageLog bindings + NYRA listing registration + tokenized-message snapshots"
      exports: ["FNyraMessageLogListener"]
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/log_tail.py
      provides: "MCP tool handler routing to log/tail WS request"
      exports: ["LogTailHandler"]
  key_links:
    - from: nyra_output_log_tail MCP call
      to: log/tail WS request
      via: "LogTailHandler forwards params; UE-side FNyraOutputDeviceSink returns tail"
      pattern: "log/tail"
    - from: FCoreDelegates::OnHandleSystemError
      to: Saved/NYRA/logs/crash-<ts>.log
      via: "Pre-crash flush of ring buffer"
      pattern: "OnHandleSystemError"
---

<objective>
Second introspection primitive: the UE Output Log + Message Log tailing surface exposed to agents as `nyra_output_log_tail` + `nyra_message_log_list` MCP tools. Phase 4+ blueprint-debug tools (ACT-02) heavily depend on this — agent sees compile errors without needing the user to copy-paste.

Per CONTEXT.md:
- D-21: bounded ring buffer (2000 entries), category whitelist, high-verbosity default-exclude, max_entries=200 cap per call, agent polls (no subscription)
- D-22: FMessageLog listener + own NYRA listing + FCoreDelegates crash-flush
- D-23: log/tail + log/message-log-list wire contract already documented in Plan 02-02
- D-24: module-superset on NyraEditorModule.cpp + app.py

**TDD** on the Python-side tool routing + UE Automation Spec on the C++ sink + filter logic.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/02-subscription-bridge-ci-matrix/02-CONTEXT.md
@.planning/phases/02-subscription-bridge-ci-matrix/02-RESEARCH.md
@docs/JSONRPC.md

<interfaces>
<!-- FNyraOutputDeviceSink (RESEARCH §8.2): -->
```cpp
USTRUCT()
struct FNyraLogEntry
{
    FDateTime Ts;
    FName Category;
    ELogVerbosity::Type Verbosity;
    FString Message;
};

class NYRAEDITOR_API FNyraOutputDeviceSink : public FOutputDevice
{
public:
    virtual void Serialize(const TCHAR* Msg, ELogVerbosity::Type V, const FName& Category) override;
    TArray<FNyraLogEntry> GetTail(FDateTime SinceTs, int32 MaxEntries,
                                  const TSet<FName>& CategoryWhitelist,
                                  ELogVerbosity::Type MinVerbosity,
                                  const FString& Regex) const;
    void SetCategoryWhitelist(const TSet<FName>& InWhitelist);
    void SetDefaultExclusions();  // adds LogRHI, LogRenderCore, LogSlate, LogD3D11, LogD3D12, LogTickGroup
    void FlushToFile(const FString& Path) const;  // OnHandleSystemError consumer
private:
    mutable FCriticalSection BufferLock;
    TArray<FNyraLogEntry> Buffer;
    TSet<FName> CategoryWhitelist;  // empty = allow all; non-empty = allowlist
    TSet<FName> DefaultExclusions;  // always blocked unless explicitly whitelisted
    ELogVerbosity::Type MaxVerbosity = ELogVerbosity::Log;
    int32 MaxEntries = 2000;
};
```

<!-- FNyraMessageLogListener (RESEARCH §8.3): -->
```cpp
class NYRAEDITOR_API FNyraMessageLogListener
{
public:
    void Register();    // Loads FMessageLogModule; registers own FName("NYRA") listing; binds OnDataChanged for LogBlueprint/LogPIE/LogAssetTools
    void Unregister();
    TArray<FNyraMessageLogEntry> GetMessagesForListing(const FName& ListingName, int32 SinceIndex, int32 MaxEntries) const;
private:
    TMap<FName, TArray<FNyraMessageLogEntry>> Mirrors;   // local copy; FMessageLog doesn't expose historical read
    TArray<FDelegateHandle> BoundHandles;
};
```

<!-- log/tail request (docs/JSONRPC.md §4.6) — UE is the server, NH is the client. Request:
     {categories?: [str], min_verbosity?: str, since_ts?: ISO-8601, max_entries: int ≤200, regex?: str}
     Response:
     {entries: [{ts, category, verbosity, message}], truncated: bool, last_ts: str} -->

<!-- log/message-log-list (§4.7):
     Request: {listing_name: str, since_index?: int, max_entries: int ≤200}
     Response: {entries: [{index, severity, message, token_refs: [str]}], total: int} -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1 (RED+GREEN): MCP tool wiring + log_tail Python handler</name>
  <files>TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/log_tail.py, TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/__init__.py, TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/log_tail.py, TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py, TestProject/Plugins/NYRA/Source/NyraHost/tests/test_log_tail.py</files>
  <behavior>
    - test_nyra_output_log_tail_forwards_to_log_tail_ws_request — tool call with {categories:['LogBlueprint'], max_entries:50} emits WS log/tail with matching params
    - test_max_entries_cap_at_200 — tool call with max_entries=500 is capped at 200 before forwarding
    - test_since_ts_required_when_not_initial_call — first call without since_ts is fine (returns from buffer start); subsequent calls omitting since_ts log a warning and default to now-minus-5-minutes
    - test_default_exclusion_categories — if categories is empty AND no exclusion override, exclusions (LogRHI etc.) applied server-side
    - test_nyra_message_log_list_forwards_correctly — tool call with {listing_name:'LogBlueprint', max_entries:20} emits log/message-log-list
    - test_regex_filter_passed_through — regex is forwarded verbatim (UE side compiles)
    - test_tool_result_shape — success case returns {entries: [...], truncated: bool, last_ts: str} from UE's response; error case returns MCP error
  </behavior>
  <action>
    RED: commit test(02-11): add failing log-tail MCP tool tests

    GREEN:
    1. `nyrahost/handlers/log_tail.py`: `LogTailHandler` class with `async def on_nyra_output_log_tail(tool_args, ws_emit_request)` — caps max_entries, applies default exclusions if user omits categories, forwards WS log/tail request, returns the response as tool_result. `async def on_nyra_message_log_list(tool_args, ws_emit_request)` same pattern.
    2. `nyrahost/mcp_server/log_tail.py` registers both tools with the MCP server from Plan 02-09.
    3. `nyrahost/mcp_server/__init__.py` create_server() now registers all three Phase 2 tools: nyra_permission_gate (Plan 02-09), nyra_console_exec (Plan 02-10), nyra_output_log_tail + nyra_message_log_list (Plan 02-11). Module-superset preserved.
    4. `app.py` constructs LogTailHandler + passes into mcp_server factory. Module-superset (D-24).

    Commit: feat(02-11): add nyra_output_log_tail + nyra_message_log_list MCP tools
  </action>
  <verify>
    <automated>cd TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest tests/test_log_tail.py -v 2>&1 | tail -5 | grep -E "passed|failed"</automated>
  </verify>
  <done>
    - Python tool handlers route to log/tail + log/message-log-list WS requests
    - max_entries=200 cap enforced
    - Default high-verbosity exclusions applied when user omits categories
    - MCP server registers all four Phase 2 tools (permission_gate + console_exec + two log tools)
  </done>
</task>

<task type="auto">
  <name>Task 2: FNyraOutputDeviceSink + FNyraMessageLogListener + module integration + NyraLoggingSpec</name>
  <files>TestProject/Plugins/NYRA/Source/NyraEditor/Public/Logging/FNyraOutputDeviceSink.h, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Logging/FNyraOutputDeviceSink.cpp, TestProject/Plugins/NYRA/Source/NyraEditor/Public/Logging/FNyraMessageLogListener.h, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Logging/FNyraMessageLogListener.cpp, TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraSupervisor.cpp, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraLoggingSpec.cpp</files>
  <action>
    Create FNyraOutputDeviceSink per interfaces block. Key specifics:
    - `Serialize` uses a lock-guarded ring buffer: when buffer.size() > MaxEntries, RemoveAt(0, size-MaxEntries)
    - `GetTail` applies the four filter criteria in order: since_ts → min_verbosity → category whitelist (+ default exclusions) → regex. Regex uses FRegexPattern + FRegexMatcher (Core regex is sufficient; no external dep).
    - `FlushToFile` is called from FCoreDelegates::OnHandleSystemError; writes JSON lines to Saved/NYRA/logs/crash-<ts>.log (Phase 1 structlog JSON format for consistency).

    Create FNyraMessageLogListener per interfaces block. Key specifics:
    - `Register` loads FMessageLogModule, registers NYRA listing with FMessageLogInitializationOptions {bShowFilters=true, bShowPages=false, bAllowClear=true}
    - For LogBlueprint / LogPIE / LogAssetTools: `TSharedRef<IMessageLogListing> L = MLM.GetLogListing(FName("LogXxx")); L->OnDataChanged().AddRaw(this, ...)` — binding captures snapshots of new messages into the Mirrors map.
    - `GetMessagesForListing` returns a slice of Mirrors[listing_name] from index since_index.

    NyraEditorModule.cpp (module-superset discipline — D-24):
    - In StartupModule AFTER Plan 10's supervisor spawn but BEFORE tab ready: `FNyraOutputDeviceSink* Sink = new FNyraOutputDeviceSink(); Sink->SetDefaultExclusions(); GLog->AddOutputDevice(Sink); GNyraLogSink = Sink;` + `GNyraMessageLogListener = MakeUnique<FNyraMessageLogListener>(); GNyraMessageLogListener->Register(); FCoreDelegates::OnHandleSystemError.AddLambda([]() { if (GNyraLogSink) GNyraLogSink->FlushToFile(...); });`
    - In ShutdownModule BEFORE Plan 13 cleanup: `if (GNyraLogSink) { GLog->RemoveOutputDevice(GNyraLogSink); delete GNyraLogSink; GNyraLogSink = nullptr; } GNyraMessageLogListener.Reset();`
    - Preserve EVERY other line from Plans 03/04/10/13 + Plan 02-08.

    FNyraSupervisor.cpp additions (module-superset — D-24):
    - Register WS handlers for `log/tail` and `log/message-log-list` that dispatch to GNyraLogSink->GetTail and GNyraMessageLogListener->GetMessagesForListing respectively. Return JSON per docs/JSONRPC.md §4.6/§4.7 shape.

    NyraLoggingSpec.cpp:
    - `Nyra.Logging.RingBufferBounded` — push 2100 entries, verify buffer.Num() == 2000 (oldest 100 evicted)
    - `Nyra.Logging.CategoryFilter` — Sink with whitelist {LogBlueprint}; push entries in LogBlueprint + LogSlate; GetTail returns only LogBlueprint
    - `Nyra.Logging.MinVerbosity` — Sink MaxVerbosity=Warning; Verbose + Log entries filtered out at Serialize
    - `Nyra.Logging.DefaultExclusions` — push LogRHI entry; verify filtered (default exclusion list active)
    - `Nyra.Logging.RegexFilter` — GetTail with regex "error.*"; returns only matching
    - `Nyra.Logging.MessageLogListingRegistered` — after Register, MLM.IsRegisteredLogListing(FName("NYRA")) returns true
    - `Nyra.Logging.CrashFlushToFile` — call Sink->FlushToFile(temp path); verify file exists + contains JSON lines

    Commit: feat(02-11): add FNyraOutputDeviceSink + FNyraMessageLogListener + wire log/tail + log/message-log-list
  </action>
  <verify>
    <automated>test -f TestProject/Plugins/NYRA/Source/NyraEditor/Public/Logging/FNyraOutputDeviceSink.h && test -f TestProject/Plugins/NYRA/Source/NyraEditor/Public/Logging/FNyraMessageLogListener.h && grep -q "GLog->AddOutputDevice" TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp && grep -q "OnHandleSystemError" TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp</automated>
  </verify>
  <done>
    - FNyraOutputDeviceSink + FNyraMessageLogListener compile cleanly
    - Module startup registers sink + listener + crash-flush delegate
    - Module shutdown unregisters cleanly
    - log/tail + log/message-log-list WS handlers return filtered entries
    - NyraLoggingSpec has 7+ It blocks
    - Phase 1 tests still green; module-superset intact
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| UE GLog sink → NyraHost → Claude | Sensitive log messages (asset paths, stack traces) flow outward when the agent calls nyra_output_log_tail |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-11-01 | Information Disclosure | Log messages contain PII (user home path, project names) | accept | User opted in by requesting log tail; default category exclusions narrow surface. Privacy Mode (D-05) blocks Claude egress entirely; log still local. |
| T-02-11-02 | Denial of Service | Agent polls log/tail in tight loop, exhausting editor CPU | mitigate | max_entries=200 cap + per-call overhead bounded; Phase 1 Plan 13 diagnostics drawer already demonstrates the file-tail pattern. Rate-limit not added in v1; monitor in Plan 02-14 bench. |
| T-02-11-03 | Tampering | External process manipulates log buffer through GLog directly | accept | Any in-editor code can write to GLog; sink is a mirror, not the source of truth. Crash-flush captures whatever actually flowed. |
</threat_model>

<verification>
- `cd TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest -v` — all passed
- `test -f TestProject/Plugins/NYRA/Source/NyraEditor/Public/Logging/FNyraOutputDeviceSink.h`
- `grep -q "GLog->AddOutputDevice" TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp`
- Automation: `Automation RunTests Nyra.Logging` — 7+ It blocks pass
</verification>

<success_criteria>
- Agent can retrieve filtered Output Log tail with category + verbosity + regex filters
- Agent can retrieve Message Log entries for standard listings (LogBlueprint etc.)
- Default high-verbosity categories are excluded until explicitly opted in
- Ring buffer caps memory at 2000 entries
- Crash flush preserves last session's logs for post-mortem
- Phase 4+ ACT-02 Blueprint debug tool can consume compile errors without new plumbing
</success_criteria>

<output>
After completion, create `.planning/phases/02-subscription-bridge-ci-matrix/02-11-SUMMARY.md`
</output>
