---
phase: 02-subscription-bridge-ci-matrix
plan: 10
slug: console-exec-mcp-tool
type: execute
wave: 2
depends_on: [02, 09]
autonomous: true
tdd: true
requirements: [ACT-06]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/console_exec.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/__init__.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/console.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_console_whitelist.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_console_handler.py
  - TestProject/Plugins/NYRA/Source/NyraEditor/Config/nyra-console-whitelist-v1.json
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Console/FNyraConsoleHandler.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Console/FNyraConsoleHandler.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraSupervisor.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraConsoleSpec.cpp
research_refs: [§7.1, §7.2, §7.3, §7.4, §7.5, §7.6, §10.5]
context_refs: [D-19, D-20, D-23]
phase0_clearance_required: false
must_haves:
  truths:
    - "nyra-console-whitelist-v1.json ships with three sections: tier_a (auto-approved), tier_b (preview-gated), tier_c (hard-blocked). tier_a includes stat/showflag/log/help/obj classes/obj hierarchy/dumpticks/memreport/r.VSync/r.ScreenPercentage. tier_b covers generic r.* cvars + profilegpu. tier_c hard-blocks quit/exit/exitnow/exec file/obj gc/gc.CollectGarbage/reloadshaders/travel/open/debugcreateplayer + default-deny for unmapped"
    - "nyrahost.handlers.console.ConsoleWhitelist loads the JSON + exposes classify(command: str) -> Literal['A','B','C'] with prefix + regex matching"
    - "nyra_console_exec MCP tool registered with schema from RESEARCH §7.4; NyraHost server-side enforcement: tier A → immediate console/exec request to UE; tier B → plan/preview with single step (Plan 02-09 wiring); tier C → return -32012 error to Claude without UE call"
    - "FNyraConsoleHandler C++ class owns GameThread-dispatched GEngine->Exec invocation + FStringOutputDevice capture; returns stdout back as request response"
    - "FNyraSupervisor registers console/exec request handler that routes into FNyraConsoleHandler on the GameThread (via AsyncTask(ENamedThreads::GameThread, ...))"
    - "Editor-world only (D-20) — uses GEditor->GetEditorWorldContext().World(); rejects if PIE active (reuses Plan 02-08 PIE gate)"
    - "NyraConsoleSpec tests: Nyra.Console.ExecCaptureOutput (runs 'stat fps' via handler, verifies non-empty output string), Nyra.Console.RefusesDuringPIE (GEngine state mocked as PIE, Exec returns error)"
    - "Python tests: whitelist tier classification matrix covers 20+ representative commands; server-side rejection of tier C before wire call"
  artifacts:
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Config/nyra-console-whitelist-v1.json
      provides: "Tiered whitelist data — live-curatable without recompile"
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/console.py
      provides: "Whitelist loader + classify + server.register_request('console/exec' response dispatch)"
      exports: ["ConsoleWhitelist", "ConsoleHandler"]
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/Console/FNyraConsoleHandler.h
      provides: "GameThread-safe console Exec + FOutputDevice capture"
      exports: ["FNyraConsoleHandler"]
  key_links:
    - from: Claude CLI MCP tool call nyra_console_exec
      to: ConsoleWhitelist.classify
      via: "Tier A → issue console/exec; Tier B → gate via Plan 02-09 preview; Tier C → -32012"
      pattern: "classify.*tier_[abc]"
    - from: NyraHost console/exec request
      to: FNyraConsoleHandler::Exec on GameThread
      via: "AsyncTask dispatch + FStringOutputDevice capture"
      pattern: "AsyncTask.*GameThread.*Exec"
---

<objective>
Ship the first of two introspection primitives that every Phase 4+ tool will consume: safe, whitelist-classified UE console command execution exposed as the `nyra_console_exec` MCP tool.

Three-tier safety model (RESEARCH §7.3):
- **Tier A (auto-approved, read-only):** stat/showflag/log/help/obj-classes — runs immediately
- **Tier B (preview-gated via Plan 02-09):** generic `r.*` + profilegpu — user approves each via SNyraPreviewCard
- **Tier C (hard-blocked):** quit/exit/exec/obj gc/reloadshaders/travel + default-deny — returns -32012 with suggestion to add to whitelist via Settings > NYRA > Console Whitelist (UI-deferred; JSON edit only in v1)

Per CONTEXT.md:
- D-19: tiered whitelist, JSON data for live curation
- D-20: editor-world only; PIE refuses
- D-23: console/exec + nyra_console_exec (tool_result) + -32012 already documented in Plan 02-02

**TDD** on the whitelist classifier (highest-leverage test surface — 20+ commands worth of coverage) + server-side tier routing. C++ GameThread execution + capture tested via UE Automation Spec.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/02-subscription-bridge-ci-matrix/02-CONTEXT.md
@.planning/phases/02-subscription-bridge-ci-matrix/02-RESEARCH.md
@docs/JSONRPC.md
@docs/ERROR_CODES.md
@.planning/phases/02-subscription-bridge-ci-matrix/02-09-safe-mode-permission-gate-PLAN.md

<interfaces>
<!-- Whitelist JSON shape (Plan 02-10 ships v1; curatable per D-19): -->
```json
{
  "version": 1,
  "tier_a_prefixes": ["stat ", "showflag.", "log ", "help"],
  "tier_a_exact": ["help", "obj classes", "obj hierarchy", "dumpticks", "memreport -full"],
  "tier_a_regex": ["^r\\.VSync(\\s+\\d)?$", "^r\\.ScreenPercentage(\\s+\\d+)?$"],
  "tier_b_prefixes": ["r."],
  "tier_b_exact": ["profilegpu"],
  "tier_c_exact": ["quit","exit","exitnow","obj gc","gc.CollectGarbage","reloadshaders"],
  "tier_c_prefixes": ["exec ","travel ","open ","debugcreateplayer"]
}
```
<!-- Classifier priority: tier_c beats tier_b beats tier_a; default-deny on no match. -->

<!-- nyra_console_exec MCP tool schema (RESEARCH §7.4): -->
```json
{
  "name": "nyra_console_exec",
  "inputSchema": {
    "type": "object",
    "required": ["command"],
    "properties": {
      "command": {"type": "string"},
      "rationale": {"type": "string"}
    }
  }
}
```

<!-- console/exec wire method (docs/JSONRPC.md §4.5 from Plan 02-02): -->
<!--   NH→UE request -->
<!--   Params: {command: string, rationale: string, tier: "A"|"B"} -->
<!--   Result: {stdout: string, tier: "A"|"B", exit_status: "ok"|"blocked"} -->

<!-- FNyraConsoleHandler (GameThread-safe, RESEARCH §7.5): -->
```cpp
class FNyraConsoleHandler
{
public:
    // MUST be called on GameThread.
    static FString Exec(const FString& Command)
    {
        if (!GEngine) return TEXT("(no engine)");
        FStringOutputDevice Ar;
        UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
        GEngine->Exec(World, *Command, Ar);
        return Ar;
    }
    // Refuses during PIE (GEditor->PlayWorld != nullptr)
    static bool IsBlockedByPIE() { return GEditor && GEditor->PlayWorld != nullptr; }
};
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1 (RED+GREEN): Whitelist JSON + classifier + console MCP tool + ConsoleHandler</name>
  <files>TestProject/Plugins/NYRA/Source/NyraEditor/Config/nyra-console-whitelist-v1.json, TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/console.py, TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/console_exec.py, TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/__init__.py, TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py, TestProject/Plugins/NYRA/Source/NyraHost/tests/test_console_whitelist.py, TestProject/Plugins/NYRA/Source/NyraHost/tests/test_console_handler.py</files>
  <behavior>
    test_console_whitelist.py:
    - test_tier_a_stat — 'stat fps', 'stat unit', 'stat scenerendering' classify as A
    - test_tier_a_showflag — 'showflag.bones 1', 'showflag.bones 0' classify as A
    - test_tier_a_log_verbosity — 'log LogTemp verbose', 'log list' classify as A
    - test_tier_a_exact_help — 'help' classifies as A; 'help something' classifies as A (prefix)
    - test_tier_a_r_vsync_regex — 'r.VSync', 'r.VSync 1' classify as A
    - test_tier_b_generic_r — 'r.FogDensity 2', 'r.Something' classify as B (not in tier_a regex)
    - test_tier_b_profilegpu — 'profilegpu' classifies as B
    - test_tier_c_quit — 'quit', 'exit', 'exitnow' classify as C
    - test_tier_c_exec_file — 'exec hack.txt' classifies as C (prefix 'exec ')
    - test_tier_c_reloadshaders — 'reloadshaders' classifies as C
    - test_unmapped_default_deny — 'viewmode shadercomplexity' classifies as C (default deny)
    - test_tier_precedence_c_beats_b — 'r.Something.Destroyworld' that somehow matches multiple rules — verify tier_c wins (explicitly add a precedence test)

    test_console_handler.py:
    - test_nyra_console_exec_tier_a_routes_to_console_exec_request — Claude tool call with 'stat fps' produces a console/exec WS request with tier=A
    - test_nyra_console_exec_tier_b_routes_through_plan_preview — tool call with 'r.FogDensity 5' emits a plan/preview with single step risk=reversible; on approve proceeds; on reject returns -32011
    - test_nyra_console_exec_tier_c_returns_minus_32012 — tool call with 'quit' returns MCP tool error with code=-32012 including suggested-remediation string
    - test_tier_c_remediation_text_includes_whitelist_path — error data contains "Settings > NYRA > Console Whitelist" string per RESEARCH §10.5

  </behavior>
  <action>
    RED: commit test(02-10): add failing console-whitelist classifier + handler tests

    GREEN:
    1. Ship `nyra-console-whitelist-v1.json` under NyraEditor/Config/ per interfaces block. Tier A covers RESEARCH §7.3 list; Tier B lists `r.*` prefix + profilegpu; Tier C hard-blocks quit/exit/exec/reloadshaders/travel/open/debugcreateplayer + default-deny.
    2. `nyrahost/handlers/console.py`:
       - `ConsoleWhitelist` dataclass-style class with `load_from_json(path)` class method + `classify(command: str) -> Literal['A','B','C']`. Precedence: exact matches beat prefix matches beat regex matches; Tier C beats B beats A; default 'C' (deny) on no match.
       - `ConsoleHandler`: combines whitelist + preview gate + WS client. `async def on_nyra_console_exec(tool_call_args, preview_handler, ws_emit_request)` — the top-level MCP tool handler. Routes per tier. Returns tool_result dict.
    3. `nyrahost/mcp_server/console_exec.py`: registers `nyra_console_exec` tool with the MCP server; tool handler delegates to ConsoleHandler.on_nyra_console_exec.
    4. Update `nyrahost/mcp_server/__init__.py` `create_server()` to register the console tool alongside the permission-gate tool.
    5. Update `app.py` to construct ConsoleHandler + pass it to the MCP server factory. Module-superset discipline (D-24).

    Commit: feat(02-10): add console whitelist + nyra_console_exec MCP tool + three-tier routing
  </action>
  <verify>
    <automated>cd TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest tests/test_console_whitelist.py tests/test_console_handler.py -v 2>&1 | tail -5 | grep -E "passed|failed"</automated>
  </verify>
  <done>
    - Whitelist JSON loaded at NyraHost startup + classifier tests pass across 12+ command patterns
    - nyra_console_exec MCP tool routes Tier A → console/exec, Tier B → plan/preview, Tier C → -32012
    - Plan 02-09 preview integration exercised via Tier B test path
    - Full pytest green
  </done>
</task>

<task type="auto">
  <name>Task 2: FNyraConsoleHandler C++ + console/exec request handler + NyraConsoleSpec</name>
  <files>TestProject/Plugins/NYRA/Source/NyraEditor/Public/Console/FNyraConsoleHandler.h, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Console/FNyraConsoleHandler.cpp, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraSupervisor.cpp, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraConsoleSpec.cpp</files>
  <action>
    Create `FNyraConsoleHandler` per interfaces block. Key specifics:
    - Static methods on the class; no instance state (except possibly a recent-commands ring buffer for debug — skip for v1)
    - `Exec(const FString& Command)` uses `FStringOutputDevice` (captures Serialize calls into FString)
    - `IsBlockedByPIE()` returns true when `GEditor && GEditor->PlayWorld != nullptr` — caller short-circuits

    Register console/exec request handler in FNyraSupervisor (module-superset on FNyraSupervisor.cpp — D-24):
    - In the method-registration phase (mirrors Phase 1 Plan 10's pattern), add:
      ```cpp
      WsClient->RegisterRequestHandler("console/exec", [](const FString& Params, TFunction<void(const FString& Response)> Reply) {
          // Parse params, dispatch to GameThread:
          AsyncTask(ENamedThreads::GameThread, [Params, Reply]() {
              if (FNyraConsoleHandler::IsBlockedByPIE()) {
                  Reply(TEXT(R"({"stdout":"","tier":"A","exit_status":"blocked"})"));
                  return;
              }
              FString Command = ExtractCommand(Params);
              FString Stdout = FNyraConsoleHandler::Exec(Command);
              Reply(FString::Printf(TEXT(R"({"stdout":"%s","tier":"A","exit_status":"ok"})"), *EscapeJsonString(Stdout)));
          });
      });
      ```
    - Preserve every other FNyraSupervisor line verbatim.

    NyraConsoleSpec.cpp:
    - `Nyra.Console.ExecCaptureOutput`: spawn a transient world, run FNyraConsoleHandler::Exec("stat fps"), verify returned string is non-empty and contains 'FPS' or 'Frames' or 'fps' (case-insensitive substring)
    - `Nyra.Console.RefusesDuringPIE`: mock `GEditor->PlayWorld` via test fixture (OR use an actual PIE spawn if the automation test harness allows); call Exec; verify IsBlockedByPIE returned true path taken
    - `Nyra.Console.OutputDeviceCapture`: register a custom output via ULog or direct GEngine->Exec("help"); verify output contains 'Possible commands' or similar help text

    Commit: feat(02-10): add FNyraConsoleHandler + console/exec UE handler + NyraConsoleSpec
  </action>
  <verify>
    <automated>test -f TestProject/Plugins/NYRA/Source/NyraEditor/Public/Console/FNyraConsoleHandler.h && grep -q "FStringOutputDevice" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Console/FNyraConsoleHandler.cpp && grep -q "console/exec" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraSupervisor.cpp && grep -q "Nyra.Console" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraConsoleSpec.cpp</automated>
  </verify>
  <done>
    - FNyraConsoleHandler compiles cleanly on all four UE versions (via CI matrix)
    - console/exec UE-side handler dispatched on GameThread with PIE gate
    - NyraConsoleSpec has 3+ It blocks
    - Phase 1 tests still green (module-superset preserved)
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Claude-issued command string → UE console Exec | Untrusted string crosses into GEngine->Exec; whitelist is the ONLY defense |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-10-01 | Elevation of Privilege | Tier A regex allows injection bypass (`stat fps; quit`) | mitigate | Commands are passed as single strings to GEngine->Exec which doesn't shell-parse. UE console parser does NOT split on semicolons by default. Whitelist regex anchors (`^...$`) prevent prefix-stuffing. Test test_tier_a_r_vsync_regex verifies. |
| T-02-10-02 | Denial of Service | Tier A command triggers huge output ('obj list' on large project) | mitigate | Output cap: FNyraConsoleHandler truncates captured FString to 32768 chars + marker '... [truncated]'. Bench verification in Plan 02-14. |
| T-02-10-03 | Tampering | Local user edits nyra-console-whitelist-v1.json to widen Tier A | accept | Local user has already full editor access; whitelist protects against Claude agents, not the installed user. Documented in README-whitelist. |
| T-02-10-04 | Information Disclosure | 'memreport -full' output contains memory addresses + mod paths | accept | User opted into NYRA; running diagnostics is in-scope. Structured log redaction not needed for console output. |
</threat_model>

<verification>
- `cd TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest -v` — all passed
- `test -f TestProject/Plugins/NYRA/Source/NyraEditor/Config/nyra-console-whitelist-v1.json` + valid JSON
- `grep -q "FStringOutputDevice" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Console/FNyraConsoleHandler.cpp`
- Automation: Nyra.Console.* — 3+ It blocks pass on dev host
</verification>

<success_criteria>
- Whitelist classifier routes 12+ representative commands into correct tier
- Tier A runs via GameThread Exec + FStringOutputDevice capture
- Tier B integrates with Plan 02-09 preview card (single-step plan)
- Tier C returns -32012 with whitelist-editing remediation hint
- PIE gate blocks Exec; editor-world-only enforced
- Phase 4+ tool plans can issue nyra_console_exec for cvar queries / stat dumps without re-implementing safety
</success_criteria>

<output>
After completion, create `.planning/phases/02-subscription-bridge-ci-matrix/02-10-SUMMARY.md`
</output>
