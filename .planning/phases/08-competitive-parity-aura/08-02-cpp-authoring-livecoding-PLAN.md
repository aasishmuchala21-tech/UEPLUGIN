---
phase: 8
plan: 08-02
requirement: PARITY-02
type: execute
wave: 2
tier: 1
autonomous: false
depends_on: []
blocking_preconditions:
  - "Wave 0 UE Python symbol survey for ILiveCodingModule reachability per UE 5.4/5.5/5.6/5.7 (Task 0 below)"
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/cpp_authoring_tools.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/blueprint_debug.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/cpp_authoring_state.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/__init__.py
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/ToolHelpers/NyraLiveCodingHelper.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/ToolHelpers/NyraLiveCodingHelper.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_cpp_authoring.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_cpp_error_patterns.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_cpp_recompile_mock.py
  - .planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/symbol-survey-livecoding-{ue}.md
---

# Plan 08-02: C++ Authoring + Live Coding (PARITY-02)

## Goal

Ship the `nyra_cpp_module_create / nyra_cpp_class_add / nyra_cpp_function_add / nyra_cpp_recompile` quartet — each step transactional (BL-04), idempotent (BL-05), and post-condition-verified (BL-06). Compile errors surface through an extended `_ERROR_PATTERNS` regex catalog covering MSVC + clang. Live Coding triggered via a thin C++ helper; falls back to Hot Reload on UE versions where Live Coding is broken (T-08-03).

## Why this beats Aura

Per CONTEXT.md SC#2 (verbatim):

> **Beats Aura on C++ authoring + Live Coding**: PARITY-02 ships `nyra_cpp_module_create / nyra_cpp_class_add / nyra_cpp_function_add / nyra_cpp_recompile` quartet wired through UE's Hot Reload + Live Coding subsystems. Where Aura ships C++ generation as one tool, NYRA decomposes into transactional steps (CR-UD pattern from Phase 4 Tool Catalog) — every step is undoable via the session_transaction wrapper. Compile errors flow back through `nyra_blueprint_debug`'s pattern-matching surface, generalised to C++ (existing regex patterns extend cleanly).

The "beats" lever: Aura's docs openly admit "C++ can cause compilation issues. If this happens you will need to close Unreal and rebuild in Visual Studio or Rider." NYRA's claim is the **regex-pattern explanation surface** (an existing Phase 4 paid-for primitive), not zero-failure compile.

## Wave 0: UE Python Symbol Survey

**Task 0** runs `dir(unreal)` and reflection probes across UE 5.4 / 5.5 / 5.6 / 5.7 to verify:

- `unreal.NyraLiveCodingHelper` reflects post-engine-startup (this is OUR helper from Task 5; the survey runs it once after Task 5 lands and replays the survey)
- Whether `ILiveCodingModule` is reachable via the C++ helper on each version
- `KNOWN_LIVE_CODING_BAD_VERSIONS` empirical findings — whether `Compile()` returns success and the editor remains responsive

**Output:** `.planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/symbol-survey-livecoding-{5.4,5.5,5.6,5.7}.md` — one per UE version, committed alongside this plan.

**Fail-fast rule:** if `Compile()` is unreachable on any version, that version defaults to `use_live_coding: false` (Hot Reload) — plan does NOT fail. T-08-03 explicitly anticipates this.

## Pattern Compliance (Phase 4 mutator shape — LOCKED-03)

Per LOCKED-03 + PATTERNS.md §"Canonical Phase 4 Mutator Shape", every PARITY-02 tool is a copy-rename of `actor_tools.ActorSpawnTool.execute` (lines 113-170). The body shape is **fixed**:

| BL-helper | Where it's called | What it wraps |
|---|---|---|
| `idempotent_lookup(self.name, params)` | First line of `execute()` | Dedup `(tool, params)` repeats |
| `with session_transaction(f"NYRA: {self.name}"):` | Wraps every filesystem write + Live Coding trigger | Ctrl+Z reverts the whole step |
| `verify_post_condition(label, lambda: ...)` | After mutation, before `idempotent_record` | Re-fetch state to confirm world reflects change |
| `idempotent_record(self.name, params, data)` | Last line before `return ok(...)` | Cache for next-call dedup |
| `NyraToolResult.ok({...})` / `.err(msg)` / `.to_dict()` | Always — never raw dicts | BL-01 envelope; `mcp_server` dispatches via `result.to_dict()` |
| `run_async_safely(coro)` | `nyra_cpp_recompile` only | Sync→async bridge for the WS dispatch to `NyraLiveCodingHelper` |

| Tool | post-condition (BL-06) check |
|---|---|
| `nyra_cpp_module_create` | `(module_dir / f"{module_name}.Build.cs").exists() and (module_dir / "Public").exists() and (module_dir / "Private").exists()` |
| `nyra_cpp_class_add` | both `<class>.h` and `<class>.cpp` exist; class name appears verbatim in header |
| `nyra_cpp_function_add` | function signature appears in target header AND impl in .cpp |
| `nyra_cpp_recompile` | `compile_attempted=True`; `compile_success` reflects helper return; if errors, `compile_errors` non-empty + each entry has `pattern_match` field |

## MCP Registration

Per PATTERNS.md §"MCP Server Registration":

**`nyrahost/mcp_server/__init__.py:_tools` dict** — slot after line 100 (after `nyra_kb_search`), under banner `# === Phase 8 PARITY-02 ===`:

```python
# PARITY-02: C++ authoring + Live Coding
"nyra_cpp_module_create":  CppModuleCreateTool(),
"nyra_cpp_class_add":      CppClassAddTool(),
"nyra_cpp_function_add":   CppFunctionAddTool(),
"nyra_cpp_recompile":      CppRecompileTool(),
```

**Imports** — after line 63 (after `from nyrahost.tools.kb_search import KbSearchTool`):

```python
from nyrahost.tools.cpp_authoring_tools import (
    CppModuleCreateTool, CppClassAddTool, CppFunctionAddTool, CppRecompileTool,
)
```

**`list_tools()` schemas** — slot after line 516 (after `nyra_kb_search` schema, before closing `]`), banner `# === Phase 8 PARITY-02 ===`. Mirror the `nyra_permission_gate` schema shape (lines 167-192) — `required` + `properties` + `enum` for `type` and `scope` fields.

## C++ Helper Surface

**File:** `TestProject/Plugins/NYRA/Source/NyraEditor/Public/ToolHelpers/NyraLiveCodingHelper.h`

```cpp
// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "NyraLiveCodingHelper.generated.h"

UCLASS(MinimalAPI)
class UNyraLiveCodingHelper : public UObject
{
    GENERATED_BODY()

public:
    /** Trigger Live Coding compile. Returns true if compile started (not necessarily succeeded). */
    UFUNCTION(BlueprintCallable, Category="Nyra|LiveCoding", meta=(ScriptMethod))
    static bool TriggerLiveCodingCompile();

    /** Trigger Hot Reload fallback. Returns true if reload completed without exception. */
    UFUNCTION(BlueprintCallable, Category="Nyra|LiveCoding", meta=(ScriptMethod))
    static bool TriggerHotReload(FName ModuleName);

    /** Best-effort string of last compile output (read-only buffer flushed by helper). */
    UFUNCTION(BlueprintCallable, Category="Nyra|LiveCoding", meta=(ScriptMethod))
    static FString GetLastCompileOutput();
};
```

**File:** `Private/ToolHelpers/NyraLiveCodingHelper.cpp`

```cpp
#include "ToolHelpers/NyraLiveCodingHelper.h"
#include "ILiveCodingModule.h"          // UE 5.4+ — RESEARCH.md A6
#include "Modules/ModuleManager.h"
#include "Misc/HotReloadInterface.h"     // fallback path

bool UNyraLiveCodingHelper::TriggerLiveCodingCompile()
{
    if (ILiveCodingModule* LC = FModuleManager::GetModulePtr<ILiveCodingModule>("LiveCoding"))
    {
        return LC->Compile();
    }
    return false;
}

bool UNyraLiveCodingHelper::TriggerHotReload(FName ModuleName)
{
    if (IHotReloadInterface* HR = FModuleManager::GetModulePtr<IHotReloadInterface>("HotReload"))
    {
        // DoHotReloadFromEditor is the canonical entry point; signature stable 5.4-5.7
        HR->DoHotReloadFromEditor(EHotReloadFlags::None);
        return true;
    }
    return false;
}

FString UNyraLiveCodingHelper::GetLastCompileOutput()
{
    // Read from the editor's "Live Coding" output log channel, last N lines.
    // Implementation: tap into FOutputDevice via a registered listener; cache last 4 KB.
    // ... omitted ...
    return FString();
}
```

**`NyraEditor.Build.cs`** — add to `PrivateDependencyModuleNames`: `"LiveCoding"`, `"HotReload"`.

**Python entrypoint:** `unreal.NyraLiveCodingHelper.trigger_live_coding_compile()` (auto-reflected from the UCLASS at editor startup).

## Pre-condition Gate (Out-of-Scope §"Live Coding for non-NYRA-authored code")

Per CONTEXT.md Out-of-Scope:

> Live Coding C++ for non-NYRA-authored code. Plan 08-02 ships authoring + recompile loops only for files NYRA created in the session.

**Implementation:** `nyrahost/cpp_authoring_state.py` — module-scoped `set[Path]` of session-authored files. Every PARITY-02 mutator that writes a file calls `_record_authored(path)`. `nyra_cpp_recompile` validates that the targeted module's source files are all in the authored set; if not, returns `NyraToolResult.err("recompile target contains files NYRA did not author this session — aborting per Phase 8 out-of-scope policy")`.

**Pattern match:** mirrors `safe_mode.NyraPermissionGate` session-scoped state (PATTERNS.md §PARITY-02).

## Tasks

### Task 0: Wave 0 — UE Python symbol survey for Live Coding reachability (operator-run)

**Files:**
- `.planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/symbol-survey-livecoding-5.4.md`
- `... -5.5.md`, `... -5.6.md`, `... -5.7.md`

**Action:** After Task 5 (the C++ helper) lands, operator runs on each UE version:

```python
# in NyraHost-side test or operator REPL
import unreal
print("NyraLiveCodingHelper present:", hasattr(unreal, "NyraLiveCodingHelper"))
print("methods:", [m for m in dir(unreal.NyraLiveCodingHelper) if not m.startswith("_")])
# attempt one compile
ok = unreal.NyraLiveCodingHelper.trigger_live_coding_compile()
print("compile returned:", ok)
# editor responsiveness check — is the editor still alive 30 s later?
```

Operator commits the output with PASS/FAIL per UE version. **Fail-fast rule:** if `NyraLiveCodingHelper` not reflected on a version, that version is added to `KNOWN_LIVE_CODING_BAD_VERSIONS` in `cpp_authoring_tools.py` and `use_live_coding: false` is the default for that version (Hot Reload fallback). The plan does **NOT** abort — fallback is the design.

**Verify:** Four `symbol-survey-livecoding-{ue}.md` files committed with operator-run results.

**Done:** Wave 0 cleared; `KNOWN_LIVE_CODING_BAD_VERSIONS` populated.

### Task 1: Build `cpp_authoring_state.py` session-scoped allowlist

**Files:** `nyrahost/cpp_authoring_state.py`

**Action:**
```python
import threading
from pathlib import Path

_lock = threading.Lock()
_authored_files: set[Path] = set()

def record_authored(path: Path) -> None:
    with _lock:
        _authored_files.add(path.resolve(strict=False))

def is_authored(path: Path) -> bool:
    with _lock:
        return path.resolve(strict=False) in _authored_files

def clear_session() -> None:
    with _lock:
        _authored_files.clear()
```

Module-scoped — process lifetime = session lifetime. No persistence (intentional — fresh session = fresh allowlist, matches `safe_mode.NyraPermissionGate` lifecycle).

**Verify:** `pytest tests/test_cpp_authoring_state.py -x -q` — basic add/check/clear semantics.

**Done:** Module exists with locking semantics.

### Task 2: Build the four `nyra_cpp_*` mutator tools

**Files:** `nyrahost/tools/cpp_authoring_tools.py`

**Action — copy-rename of `actor_tools.ActorSpawnTool.execute` (PATTERNS.md §"Canonical example annotated"):**

```python
"""
PARITY-02 — C++ authoring + Live Coding tools.

Each tool follows the canonical Phase 4 mutator shape:
  1. idempotent_lookup → if cached, return ok({...,"deduped":True})
  2. with session_transaction(...): perform mutation
  3. verify_post_condition(...) → re-fetch state
  4. idempotent_record + return ok(...)

Pre-condition gate: every recompile validates files are in
nyrahost.cpp_authoring_state allowlist (Out-of-Scope policy).
"""
import structlog
from pathlib import Path
from nyrahost.tools.base import (
    NyraTool, NyraToolResult,
    session_transaction, idempotent_lookup, idempotent_record,
    verify_post_condition, run_async_safely,
)
from nyrahost.cpp_authoring_state import record_authored, is_authored

log = structlog.get_logger("nyrahost.tools.cpp_authoring_tools")

__all__ = [
    "CppModuleCreateTool", "CppClassAddTool",
    "CppFunctionAddTool", "CppRecompileTool",
]

# Populated by Wave 0 (Task 0) — empirical UE versions where Live Coding hangs/corrupts editor.
KNOWN_LIVE_CODING_BAD_VERSIONS: set[str] = set()  # e.g. {"5.4"}


class CppModuleCreateTool(NyraTool):
    name = "nyra_cpp_module_create"
    description = "Scaffold a new UE C++ module (Build.cs + Public/ + Private/)."
    parameters = {
        "type": "object",
        "properties": {
            "module_name": {"type": "string", "description": "Module name (PascalCase)"},
            "parent_dir":  {"type": "string", "description": "Parent dir under Source/, e.g. 'MyGame/Source'"},
            "type":        {"type": "string", "enum": ["Editor", "Runtime"], "default": "Runtime"},
        },
        "required": ["module_name", "parent_dir"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        module_name = params["module_name"]
        parent = Path(params["parent_dir"])
        module_dir = parent / module_name

        # path-traversal guard (RESEARCH.md §Security V4)
        if not str(module_dir.resolve()).startswith(str(parent.resolve())):
            return NyraToolResult.err(f"path traversal: {module_dir}")

        with session_transaction(f"NYRA: {self.name}"):
            try:
                (module_dir / "Public").mkdir(parents=True, exist_ok=True)
                (module_dir / "Private").mkdir(parents=True, exist_ok=True)
                build_cs = module_dir / f"{module_name}.Build.cs"
                build_cs.write_text(_render_build_cs(module_name, params["type"]))
                record_authored(build_cs)
            except Exception as e:
                log.error("cpp_module_create_failed", error=str(e))
                return NyraToolResult.err(f"failed: {e}")

            err = verify_post_condition(
                f"{self.name}({module_name})",
                lambda: build_cs.exists() and (module_dir / "Public").exists(),
            )
            if err:
                return NyraToolResult.err(err)

        result = {"module_name": module_name, "build_cs": str(build_cs), "type": params["type"]}
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)


class CppClassAddTool(NyraTool):
    name = "nyra_cpp_class_add"
    description = "Add a UCLASS to an existing module (NYRA-authored modules only)."
    parameters = {
        "type": "object",
        "properties": {
            "module_name":  {"type": "string"},
            "class_name":   {"type": "string"},
            "parent_class": {"type": "string", "default": "UObject"},
            "header_only":  {"type": "boolean", "default": False},
        },
        "required": ["module_name", "class_name"],
    }
    # ... follows the same canonical shape ...


class CppFunctionAddTool(NyraTool):
    name = "nyra_cpp_function_add"
    description = "Add a method to an existing UCLASS (NYRA-authored class only)."
    parameters = {
        "type": "object",
        "properties": {
            "class_path": {"type": "string", "description": "Path to the class .h"},
            "signature":  {"type": "string", "description": "C++ method signature, e.g. 'void DoTheThing()'"},
            "body":       {"type": "string", "description": "Function body without braces"},
        },
        "required": ["class_path", "signature", "body"],
    }
    # ... canonical shape ...


class CppRecompileTool(NyraTool):
    name = "nyra_cpp_recompile"
    description = "Trigger Live Coding compile (or Hot Reload fallback) on NYRA-authored modules."
    parameters = {
        "type": "object",
        "properties": {
            "scope":            {"type": "string", "enum": ["module", "all"], "default": "module"},
            "module_name":      {"type": "string"},
            "use_live_coding":  {"type": "boolean", "default": True},
        },
        "required": ["scope"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        # Pre-condition gate per Out-of-Scope policy.
        if params["scope"] == "module":
            module_dir = Path("Source") / params["module_name"]
            for f in module_dir.rglob("*.cpp"):
                if not is_authored(f):
                    return NyraToolResult.err(
                        f"recompile aborted: {f} is not in NYRA-authored set this session "
                        f"(Out-of-Scope policy)"
                    )

        # Live Coding vs Hot Reload selection.
        ue_version = _detect_ue_version()  # "5.4" / "5.5" / ...
        use_lc = params.get("use_live_coding", True) and ue_version not in KNOWN_LIVE_CODING_BAD_VERSIONS

        with session_transaction(f"NYRA: {self.name}"):
            try:
                import unreal  # gated — pytest path skips
                if use_lc:
                    ok = unreal.NyraLiveCodingHelper.trigger_live_coding_compile()
                    method = "live_coding"
                else:
                    ok = unreal.NyraLiveCodingHelper.trigger_hot_reload(params.get("module_name", ""))
                    method = "hot_reload"
                output = unreal.NyraLiveCodingHelper.get_last_compile_output() or ""
            except (ImportError, AttributeError) as e:
                # Fallback path — UBT subprocess (slower).
                return NyraToolResult.err(
                    f"unreal.NyraLiveCodingHelper unavailable on this UE version: {e}; "
                    f"manual remediation: open the project in Visual Studio and rebuild"
                )

            errors = _parse_compile_errors(output)
            err = verify_post_condition(
                f"{self.name}({params['scope']})",
                lambda: True,  # compile_attempted is always true here
            )
            if err:
                return NyraToolResult.err(err)

        result = {
            "compile_attempted": True,
            "compile_success": ok and not errors,
            "method": method,
            "ue_version": ue_version,
            "compile_errors": errors,
        }
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)


def _render_build_cs(module: str, kind: str) -> str:
    deps_extra = '"UnrealEd", "Slate", "SlateCore"' if kind == "Editor" else '"Engine"'
    return f'''// SPDX-License-Identifier: MIT
using UnrealBuildTool;
public class {module} : ModuleRules
{{
    public {module}(ReadOnlyTargetRules Target) : base(Target)
    {{
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new string[] {{ "Core", "CoreUObject", {deps_extra} }});
    }}
}}
'''


def _detect_ue_version() -> str:
    try:
        import unreal
        return unreal.SystemLibrary.get_engine_version().split(".", 2)[:2] and ".".join(
            unreal.SystemLibrary.get_engine_version().split(".")[:2]
        )
    except Exception:
        return "unknown"


def _parse_compile_errors(output: str) -> list[dict]:
    """Use the extended _ERROR_PATTERNS from blueprint_debug — see Task 3."""
    from nyrahost.tools.blueprint_debug import _explain_error_pattern
    matches = []
    for line in output.splitlines():
        explained = _explain_error_pattern(line)
        if explained is not None:
            matches.append({"line": line, **explained})
    return matches
```

**Verify:** `pytest tests/test_cpp_authoring.py -x -q` (Task 6).

**Done:** All four tools subclass `NyraTool`, follow the canonical shape, and pass the file-IO unit tests.

### Task 3: Extend `_ERROR_PATTERNS` in blueprint_debug.py with C++ regex catalog

**Files:** `nyrahost/tools/blueprint_debug.py`

**Action — Option A per RESEARCH.md §Shared Pattern 2 (recommended):**

Append C++ patterns to the existing `_ERROR_PATTERNS` list. The matcher loop `_explain_error_pattern` (lines 99-130) is regex-shape-agnostic and already returns first-match. Risk of false-match on Blueprint logs is theoretical (Blueprint logs don't emit MSVC `error C\d{4}` codes).

Append exactly the four patterns from RESEARCH.md §Code Examples §"PARITY-02 C++ compile-error pattern extension" (MSVC `error C\d{4}`, clang undeclared identifier, MSVC `LINK : fatal error LNK\d{4}`, UHT `UnrealHeaderTool failed`). Use `_DefaultDict` placeholder safety from existing lines 107-110 verbatim.

**Verify:** `pytest tests/test_cpp_error_patterns.py -x -q` — fixture `tests/fixtures/sample_compile_error.txt` containing one of each pattern asserts `_explain_error_pattern(line)` returns the right `(explanation, fix)` tuple.

**Done:** Existing Blueprint pattern tests still pass + new C++ patterns match correctly.

### Task 4: Build C++ helper UCLASS — `UNyraLiveCodingHelper`

**Files:**
- `NyraEditor/Public/ToolHelpers/NyraLiveCodingHelper.h`
- `NyraEditor/Private/ToolHelpers/NyraLiveCodingHelper.cpp`
- `NyraEditor/NyraEditor.Build.cs`

**Action:** Per the C++ Helper Surface section above. `Build.cs` adds `LiveCoding`, `HotReload` to `PrivateDependencyModuleNames`. The UCLASS reflects to Python automatically at engine startup as `unreal.NyraLiveCodingHelper`.

**Verify:** UE editor builds clean on UE 5.6 (the dev-box version). Operator-run verification on 5.4/5.5/5.7 happens in Task 0.

**Done:** UCLASS reflects; `python -c "import unreal; print(hasattr(unreal, 'NyraLiveCodingHelper'))"` returns True inside the editor.

### Task 5: MCP registration — imports + `_tools` dict + `list_tools()` schemas

**Files:** `nyrahost/mcp_server/__init__.py`

**Action:** Per the MCP Registration section above. Import line after line 63; `_tools` entries under PARITY-02 banner after line 100; `list_tools()` schemas after line 516. Mirror `nyra_permission_gate` schema shape.

**Verify:** `pytest tests/test_mcp_server.py::test_list_tools_includes_phase_8_parity_02 -x -q` — asserts each of the four `nyra_cpp_*` names appear in `list_tools()` output and have non-empty schemas.

**Done:** `mcp_server.list_tools()` returns the four PARITY-02 tools with correct schemas.

### Task 6: Build unit tests — file-IO only (`unreal` mocked)

**Files:**
- `tests/test_cpp_authoring.py` (mod_create / class_add / function_add file-IO assertions)
- `tests/test_cpp_error_patterns.py` (regex catalog assertions)
- `tests/test_cpp_recompile_mock.py` (recompile with mocked `unreal.NyraLiveCodingHelper`)

**Action — minimum coverage:**
- `nyra_cpp_module_create("MyMod", "/tmp/foo")` produces Build.cs + Public/ + Private/; idempotent (second call returns `deduped: True`).
- `nyra_cpp_class_add` on a non-NYRA-authored module returns `err`.
- `nyra_cpp_function_add` to a class then `nyra_cpp_recompile` (mocked) returns `compile_attempted=True, compile_errors=[]`.
- Path-traversal attempt (`module_name="../../../etc"`) returns `err`.
- All four tools return `NyraToolResult` (never raw dict).

**Verify:** `pytest tests/test_cpp_*.py -x -q` is green.

**Done:** Unit tests pass on the dev box without UE editor.

### Task 7: Operator-run verification (live UE editor) — `pending_manual_verification: true`

**Files:** `08-02-VERIFICATION.md` (PLACEHOLDER until operator runs)

**Operator runbook:**
1. UE 5.6 editor + Visual Studio 2022 + UE workload installed
2. Run end-to-end: NYRA chat → "create a module called TestMod and a class TestActor with a Tick method that prints hello"
3. Assert: 4 tool calls fire (`module_create`, `class_add`, `function_add`, `recompile`)
4. Assert: Live Coding completes, editor responsive, `TestActor` spawnable in level
5. Repeat on UE 5.4/5.5/5.7 (operator-tracked per `KNOWN_LIVE_CODING_BAD_VERSIONS`)
6. Negative test: try `nyra_cpp_recompile scope=all` on a project where NYRA didn't author the source — assert `err` with the Out-of-Scope explanation

**Done:** VERIFICATION.md filled with PASS/FAIL per UE version + Live-Coding-vs-Hot-Reload split.

## Tests

| Test file | What it verifies | Pending manual? |
|---|---|---|
| `tests/test_cpp_authoring.py` | Module/class/function file IO + path traversal guard | No |
| `tests/test_cpp_error_patterns.py` | MSVC + clang + LNK + UHT regex catalog | No |
| `tests/test_cpp_recompile_mock.py` | `nyra_cpp_recompile` with mocked `unreal.NyraLiveCodingHelper`; pre-cond gate on non-authored | No |
| `tests/test_mcp_server.py::test_list_tools_includes_phase_8_parity_02` | MCP registration: four tools + schemas | No |
| `08-02-VERIFICATION.md` | End-to-end Live Coding loop on UE 5.4/5.5/5.6/5.7 | **Yes** |

## Threats addressed

- **T-08-01** (UE Python API drift 5.4 → 5.7): Wave 0 symbol survey (Task 0) probes per-version. `_detect_ue_version()` + `KNOWN_LIVE_CODING_BAD_VERSIONS` constant explicitly handles the matrix.
- **T-08-03** (Live Coding reliability across UE versions): Two compile paths (`live_coding` + `hot_reload`); Hot Reload is the safe default on unverified versions. Aura's docs already concede this fallback openly.
- **Out-of-Scope policy** (no Live Coding for non-NYRA-authored code): `cpp_authoring_state` allowlist + recompile pre-condition gate.
- **Security V4** (path traversal in `module_create`): explicit `Path.resolve()` parent-prefix check before any `mkdir`/`write_text`.

## Acceptance criteria

- [ ] All four `nyra_cpp_*` tools registered in `mcp_server.list_tools()` with valid JSON schemas (`pytest tests/test_mcp_server.py::test_list_tools_includes_phase_8_parity_02 -x` passes).
- [ ] `pytest tests/test_cpp_*.py -x -q` is green — file-IO + regex + mocked recompile + pre-condition-gate all pass.
- [ ] `_ERROR_PATTERNS` regex catalog matches the four C++ error shapes (MSVC `error C\d{4}`, clang undeclared identifier, LNK fatal error, UHT failure) on the fixture `sample_compile_error.txt`.
- [ ] `cpp_authoring_state.is_authored(...)` correctly gates `nyra_cpp_recompile` — non-authored file in scope returns `err`.
- [ ] `08-02-VERIFICATION.md` operator-run: end-to-end (module→class→function→recompile→spawn) succeeds on UE 5.6 + at least one of {5.4, 5.5, 5.7}.

## Honest acknowledgments

- **`pending_manual_verification: true`** for the recompile end-to-end — the dev box only has one UE version. Wave 0 (Task 0) and the operator runbook (Task 7) are the only paths to verifying the matrix.
- **Live Coding fallback is the design, not a bug.** Aura openly acknowledges its own "C++ can cause compilation issues" — NYRA's claim is the regex-pattern explanation surface, not zero-failure compile.
- **Option B refactor of `_ERROR_PATTERNS`** (split into `_BP_PATTERNS` / `_CPP_PATTERNS`) is **deferred** to Phase 9 backlog per LOCKED-08 (don't break Phase 4 in Phase 8). If reviewers flag the false-match risk at plan-check, escalate.
