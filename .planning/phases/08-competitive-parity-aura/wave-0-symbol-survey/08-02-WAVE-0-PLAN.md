# Plan 08-02 — Wave 0 Operator Runbook (Live Coding Symbol Survey)

> **Status:** `pending_manual_verification: true`
>
> This runbook is a placeholder. The four `symbol-survey-livecoding-{ue}.md`
> outputs are produced by an operator, not by the autonomous executor. The
> survey can ONLY run after Task 4 (the C++ helper `UNyraLiveCodingHelper`)
> has compiled into a real UE editor build. The autonomous executor cannot
> spawn UE 5.4/5.5/5.6/5.7 from this environment; the operator runs each
> version manually and commits the output.

## Pre-conditions (operator side)

1. UE editor is the version under test (5.4 / 5.5 / 5.6 / 5.7).
2. NyraEditor module has been recompiled with the Plan 08-02 changes:
   - `Source/NyraEditor/Public/ToolHelpers/NyraLiveCodingHelper.h`
   - `Source/NyraEditor/Private/ToolHelpers/NyraLiveCodingHelper.cpp`
   - `NyraEditor.Build.cs` PrivateDependencyModuleNames extended with
     `LiveCoding` + `HotReload` (orchestrator batches that file edit per
     LOCKED-10).
3. The plugin builds clean and the editor launches without redlines.
4. Live Coding is enabled in **Edit > Editor Preferences > General > Live Coding**
   for the Live Coding probe; for the Hot Reload probe, the `HotReload`
   module must be loadable on the version under test.

## Probe script (Python — paste into the UE Output Log Python REPL)

```python
import unreal
import time

print("=" * 60)
print(f"NyraLiveCodingHelper symbol survey — UE {unreal.SystemLibrary.get_engine_version()}")
print("=" * 60)

# Reflection probe — does the UCLASS show up in the Python bindings?
present = hasattr(unreal, "NyraLiveCodingHelper")
print("NyraLiveCodingHelper present:", present)

if present:
    methods = [m for m in dir(unreal.NyraLiveCodingHelper) if not m.startswith("_")]
    print("methods:", methods)

    # Live Coding compile probe
    try:
        ok = unreal.NyraLiveCodingHelper.trigger_live_coding_compile()
        print("trigger_live_coding_compile returned:", ok)
    except Exception as e:
        print("trigger_live_coding_compile RAISED:", type(e).__name__, str(e))

    # Hot Reload fallback probe
    try:
        ok = unreal.NyraLiveCodingHelper.trigger_hot_reload("NyraEditor")
        print("trigger_hot_reload returned:", ok)
    except Exception as e:
        print("trigger_hot_reload RAISED:", type(e).__name__, str(e))

    # Last-output probe
    try:
        out = unreal.NyraLiveCodingHelper.get_last_compile_output()
        print("get_last_compile_output bytes:", len(out or ""))
    except Exception as e:
        print("get_last_compile_output RAISED:", type(e).__name__, str(e))

# Editor responsiveness check — wait 30s and confirm the editor is still alive.
print("Sleeping 30s; if the editor freezes, mark this version BAD.")
time.sleep(30)
print("Editor responsive after 30s.")
```

## Expected output template

For each UE version the operator runs the script and saves the console
output to:

- `.planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/symbol-survey-livecoding-5.4.md`
- `... -5.5.md`
- `... -5.6.md`
- `... -5.7.md`

Each file uses this skeleton:

```markdown
# Live Coding Symbol Survey — UE {VERSION}

**Operator:** {name/handle}
**Date:** YYYY-MM-DD
**Engine version (full):** 5.X.Y-build

## Reflection
- [ ] `unreal.NyraLiveCodingHelper` reflected: PASS / FAIL
- Reflected methods: ...

## Live Coding
- [ ] `trigger_live_coding_compile()` returned: True / False / RAISED
- [ ] Editor responsive 30s after call: YES / NO
- Compile output captured (bytes): N

## Hot Reload
- [ ] `trigger_hot_reload("NyraEditor")` returned: True / False / RAISED

## Verdict
- Live Coding usable on this version: YES / NO
- Hot Reload usable on this version: YES / NO
- If NO for Live Coding: add `"5.X"` to `KNOWN_LIVE_CODING_BAD_VERSIONS`
  in `nyrahost/tools/cpp_authoring_tools.py`.
```

## Fail-fast rule

Per PLAN.md §"Fail-fast rule": if `NyraLiveCodingHelper` is **not reflected**
on a given version, the version is added to `KNOWN_LIVE_CODING_BAD_VERSIONS`
in the Python tool module and `use_live_coding=False` becomes the default
for that version (Hot Reload fallback). The plan does **NOT** abort —
fallback is the design (T-08-03).

## Build.cs deps that the orchestrator must add

Per LOCKED-10 the executor does NOT modify `NyraEditor.Build.cs`; the
orchestrator batches all Phase 8 plan deps in plan-number order in a single
commit at the end of the wave. Plan 08-02 needs **two** entries appended
to `PrivateDependencyModuleNames`:

```csharp
"LiveCoding",   // ILiveCodingModule (UE 5.4+)
"HotReload",    // IHotReloadInterface fallback path
```

Rationale:
- `LiveCoding`: `UNyraLiveCodingHelper::TriggerLiveCodingCompile()` calls
  `FModuleManager::GetModulePtr<ILiveCodingModule>("LiveCoding")->Compile()`.
  Header `ILiveCodingModule.h` is in this module.
- `HotReload`: `UNyraLiveCodingHelper::TriggerHotReload()` calls
  `IHotReloadInterface::DoHotReloadFromEditor`. Header
  `Misc/HotReloadInterface.h` is in this module.

## mcp_server entries that the orchestrator must add

Per LOCKED-10 the executor does NOT modify
`nyrahost/mcp_server/__init__.py`. Plan 08-02 needs the orchestrator to
batch the following edits:

### Imports (after the existing `from nyrahost.tools.kb_search import KbSearchTool` line):

```python
from nyrahost.tools.cpp_authoring_tools import (
    CppModuleCreateTool, CppClassAddTool, CppFunctionAddTool, CppRecompileTool,
)
```

### `_tools` dict entries (under a `# === Phase 8 PARITY-02 ===` banner, after `nyra_kb_search`):

```python
# PARITY-02: C++ authoring + Live Coding
"nyra_cpp_module_create":  CppModuleCreateTool(),
"nyra_cpp_class_add":      CppClassAddTool(),
"nyra_cpp_function_add":   CppFunctionAddTool(),
"nyra_cpp_recompile":      CppRecompileTool(),
```

### `list_tools()` schemas (mirror the `nyra_permission_gate` exemplar)

The four schemas must mirror the `tool.parameters` JSON Schemas declared
on each NyraTool subclass. The schema bodies are sourced verbatim from
the tool classes themselves; the orchestrator can copy `tool.parameters`
into the `inputSchema` field of each `Tool(...)` entry.

Tool names (for the schema list):
- `nyra_cpp_module_create`
- `nyra_cpp_class_add`
- `nyra_cpp_function_add`
- `nyra_cpp_recompile`

## Why this lives outside the autonomous flow

The dev box (`C:\Users\aasis\UEPLUGIN`) does not have the four UE versions
side-by-side; the survey is genuinely operator-bound. The autonomous
executor produced this runbook (a) as proof Task 0 was considered, and
(b) so the operator has a paste-ready Python probe.
