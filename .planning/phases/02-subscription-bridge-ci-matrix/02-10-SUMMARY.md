# Phase 02 Plan 10: Console Exec MCP Tool Summary

**Plan:** 02-10
**Phase:** 02-subscription-bridge-ci-matrix
**Subsystem:** nyrahost.console + FNyraConsoleHandler
**Wave:** 2
**Dependencies:** 02, 09
**Phase 0 Clearance:** NOT REQUIRED (execute fully)
**GSD Plan:** .planning/phases/02-subscription-bridge-ci-matrix/02-10-console-exec-mcp-tool-PLAN.md

## One-Liner
Three-tier console command whitelist (A=auto-approved, B=preview-gated, C=hard-blocked with -32012) + GameThread-safe UE console Exec with FStringOutputDevice capture.

## What Was Built

### Python: console classifier (nyrahost/console.py)

**classify_command(command: str) → Literal["A", "B", "C"]**

Tier A (auto-approved): stat *, showflag.*, log *, help, obj classes, obj hierarchy, dumpticks, memreport -full, r.VSync, r.ScreenPercentage
Tier B (preview-gated): r.* (generic cvars), profilegpu
Tier C (hard-blocked): quit, exit, exitnow, exec *, travel *, open *, debugcreateplayer, obj gc, gc.CollectGarbage, reloadshaders
Default-deny: any command not matching → Tier C

Precedence: C > B > A (checked in order)
Case-insensitive matching; whitespace stripped

**handle_nyra_console_exec(args, permission_gate, ws_emit_request)** → dict:
- Empty command → -32013 error
- Tier C → -32012 error with remediation text "Settings > NYRA > Console Whitelist"
- Tier B → generate preview via permission_gate (Plan 02-09), auto-approve stub
- Tier A + approved Tier B → emit console/exec WS request to UE

### C++: FNyraConsoleHandler (NyraEditor/Public/Console/FNyraConsoleHandler.h/.cpp)

**static Exec(Command)** — GameThread-safe:
- Uses FStringOutputDevice to capture GEngine->Exec output
- Returns "(no engine)" if GEngine absent
- Truncates to MaxOutputChars + "... [truncated]" marker
- Uses GEditor->GetEditorWorldContext().World() for context

**static IsBlockedByPIE()** → bool:
- Returns GEditor && GEditor->PlayWorld != nullptr

**static TruncateOutput(Raw)** → FString

### C++: NyraConsoleSpec.cpp

Three Describe blocks (3+ It blocks):
- **Nyra.Console.ExecCaptureOutput**: stat fps returns non-empty, help returns non-empty, unknown command doesn't crash
- **Nyra.Console.RefusesDuringPIE**: IsBlockedByPIE returns false outside PIE (automation context)
- **Nyra.Console.OutputDeviceCapture**: help output non-empty, >5 chars

## Key Decisions

1. **Hard-block as error, not exception**: Tier C returns MCP tool error dict with -32012 code and remediation hint — Claude tool-use protocol handles this gracefully without crashing the agent.

2. **Tier B auto-approval stub**: handle_nyra_console_exec immediately approves Tier B previews — Phase 2 Wave 2 wires real Plan 02-09 preview card interaction.

3. **Command string not shell-parsed**: UE console parser doesn't split on semicolons — injection via `stat fps; quit` is not possible in practice.

4. **Static methods on FNyraConsoleHandler**: no instance state; GameThread dispatch responsibility is on the caller (FNyraSupervisor registers AsyncTask(ENamedThreads::GameThread, ...) in Wave 2).

## Deviation from Plan

- **No nyra-console-whitelist-v1.json file in NyraEditor/Config/** — whitelist is hard-coded in Python (easier to iterate, no JSON parse at startup). JSON curation deferred to Phase 2 Wave 2.
- **FNyraSupervisor console/exec request handler not wired in Wave 1** — FNyraConsoleHandler.cpp written but WS registration deferred to Phase 2 Wave 2.
- **Tier B preview-gating stub**: immediate approval rather than waiting for user — Phase 2 Wave 2 completes the Plan 02-09 integration.

## Artifacts Created

| File | Provides |
|------|----------|
| TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/console.py | classify_command() + handle_nyra_console_exec() |
| TestProject/Plugins/NYRA/Source/NyraHost/tests/test_console_whitelist.py | 24 test cases (Tier A 13, Tier B 2, Tier C 9, default-deny 2, precedence 2) |
| TestProject/Plugins/NYRA/Source/NyraEditor/Public/Console/FNyraConsoleHandler.h | GameThread-safe static Exec + IsBlockedByPIE |
| TestProject/Plugins/NYRA/Source/NyraEditor/Private/Console/FNyraConsoleHandler.cpp | FStringOutputDevice capture + TruncateOutput |
| TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraConsoleSpec.cpp | 3 Describe blocks for console execution |

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| T-02-10-01 | console.py | Tier A regex injection — mitigated: UE console doesn't shell-parse; whitelist regex anchors prevent prefix-stuffing |
| T-02-10-02 | FNyraConsoleHandler.cpp | Tier A command output overflow — mitigated: 32768 char cap + "... [truncated]" marker |
| T-02-10-03 | console.py | Local user widens Tier A in code — accept: local user has editor access; whitelist protects against Claude agents |
| T-02-10-04 | console.py | memreport output contains memory addresses — accept: user opted into NYRA diagnostics |

## Known Stubs

- Tier B auto-approval: immediate approve rather than awaiting UE panel decision
- FNyraSupervisor console/exec WS handler not registered yet
- nyra-console-whitelist-v1.json not yet shipped

## Metrics

- Duration: Wave 1 batch
- Tasks: 2 (Task 1: Python whitelist + MCP tool, Task 2: C++ handler)
- Files: 2 Python source, 1 Python test, 2 C++ source, 1 C++ spec

## TDD Gate Compliance

RED (test) commit: `test(02-10): add failing console-whitelist classifier + handler tests` — EXISTS
GREEN (impl) commit: `feat(02-10): console exec MCP tool + command whitelist` — EXISTS

## Self-Check

- [x] classify_command() routes 24+ test patterns to correct tier
- [x] Tier C returns -32012 with remediation text
- [x] Tier A → console/exec WS request
- [x] Tier B → generates preview (stub approval)
- [x] Empty command → -32013
- [x] FNyraConsoleHandler::Exec uses FStringOutputDevice
- [x] FNyraConsoleHandler::IsBlockedByPIE checks GEditor->PlayWorld
- [x] FNyraConsoleHandler::TruncateOutput caps at 32768 + marker
- [x] NyraConsoleSpec has 3 Describe blocks

## Self-Check: PASSED