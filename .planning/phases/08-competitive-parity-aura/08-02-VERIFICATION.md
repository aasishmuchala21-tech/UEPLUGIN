# Plan 08-02 — VERIFICATION (PARITY-02 C++ Authoring + Live Coding)

> **Status:** PLACEHOLDER — `pending_manual_verification: true`
>
> The autonomous executor cannot run a real UE editor with Live Coding
> from this environment. This document is the operator runbook + result
> matrix; the operator fills in PASS/FAIL per UE version after running
> the runbook on a workstation with UE 5.4 / 5.5 / 5.6 / 5.7 installed.

## Pre-flight

1. Branch `feature/08-02-cpp-authoring-livecoding` is checked out
   AND the orchestrator has landed the LOCKED-10 batched commits:
   - `NyraEditor.Build.cs` adds `"LiveCoding"` and `"HotReload"` to
     `PrivateDependencyModuleNames`.
   - `nyrahost/mcp_server/__init__.py` registers the four
     `nyra_cpp_*` tools (imports + `_tools` dict + `list_tools()` schemas).
2. Plugin recompiles cleanly on UE 5.6 (the dev-box version).
3. Live Coding is enabled in **Edit > Editor Preferences > General > Live Coding**.

## Test plan

### Smoke (UE 5.6 dev box)

End-to-end happy path through the four tools, exercised through the NYRA
chat panel:

```
operator → NYRA chat: "create a module called TestMod and a class
                       TestActor (AActor) with a Tick method that prints hello"
```

Assertions:

- [ ] `nyra_cpp_module_create` fires; `Source/TestMod/{Public,Private,TestMod.Build.cs}` exist.
- [ ] `nyra_cpp_class_add` fires; `Public/TestActor.h` + `Private/TestActor.cpp` exist.
- [ ] `nyra_cpp_function_add` fires; the Tick method appears in both files.
- [ ] `nyra_cpp_recompile` fires; Live Coding compile completes; editor stays responsive.
- [ ] `unreal.NyraLiveCodingHelper.trigger_live_coding_compile()` returned `True`.
- [ ] Error log via `get_last_compile_output()` is empty / contains zero `error C\d{4}` lines.
- [ ] `TestActor` is spawnable from the Place Actors panel and prints "hello" on Tick.

### Negative — Out-of-Scope policy

- [ ] `nyra_cpp_recompile` with a `module_dir` containing user-authored
      (non-NYRA) `.cpp` files returns `NyraToolResult.err(...)` with
      "Out-of-Scope policy" in the error string.

### UE version matrix (T-08-01 / T-08-03)

| UE version | Live Coding | Hot Reload | NyraLiveCodingHelper reflected | Verdict |
|------------|-------------|------------|--------------------------------|---------|
| 5.4        | ?           | ?          | ?                              | TBD     |
| 5.5        | ?           | ?          | ?                              | TBD     |
| 5.6        | ?           | ?          | ?                              | TBD     |
| 5.7        | ?           | ?          | ?                              | TBD     |

For each version that fails Live Coding (hangs, returns success but the
editor is unresponsive 30 s later, or `Compile()` returns `False`):

1. Add the `"X.Y"` string to `KNOWN_LIVE_CODING_BAD_VERSIONS` in
   `nyrahost/tools/cpp_authoring_tools.py`.
2. Re-run the smoke flow on that version — expect `method='hot_reload'`
   in the recompile result.
3. Mark the row's verdict `LC-BAD / HR-OK` (or `LC-BAD / HR-BAD` if both
   paths fail; that version is unsupported for PARITY-02 in v1).

### Regex catalog spot-check

Plan 08-02 Task 3 extends `blueprint_debug._ERROR_PATTERNS` with C++
shapes. After the smoke flow, force a compile error (rename a parameter
in the .cpp without updating the .h) and verify:

- [ ] `compile_errors` array is non-empty in the `nyra_cpp_recompile` response.
- [ ] At least one entry matches a specific MSVC C\d{4} or clang
      "undeclared identifier" pattern (i.e. NOT the generic fallback).
- [ ] The `suggested_fix` field is non-null.

## Linked artefacts

- `wave-0-symbol-survey/08-02-WAVE-0-PLAN.md` — operator-run reflection
  probe.
- `wave-0-symbol-survey/symbol-survey-livecoding-{5.4,5.5,5.6,5.7}.md` —
  per-version probe outputs (committed alongside this VERIFICATION.md
  once the operator runs them).

## Sign-off

Operator fills the `Verdict` column above and signs:

- [ ] PARITY-02 closed for the dev-box version (5.6).
- [ ] PARITY-02 verified on at least one of {5.4, 5.5, 5.7}, satisfying
      LOCKED-09's "≥6 of 8 plans shipped" + `acceptance_criteria` final
      checkbox in PLAN.md.
