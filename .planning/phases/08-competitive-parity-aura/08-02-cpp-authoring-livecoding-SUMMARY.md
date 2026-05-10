---
phase: 8
plan: 08-02
subsystem: NyraHost (Python MCP tools) + NyraEditor (C++ Live Coding helper)
tags: [PARITY-02, cpp-authoring, live-coding, hot-reload, mutator-tools]
requires:
  - Phase 4 mutator pattern (LOCKED-03): session_transaction, idempotent_lookup/record, verify_post_condition, NyraToolResult.to_dict
  - blueprint_debug._explain_error_pattern dispatcher (existing — reused as-is)
provides:
  - nyra_cpp_module_create / nyra_cpp_class_add / nyra_cpp_function_add / nyra_cpp_recompile MCP tools
  - unreal.NyraLiveCodingHelper UCLASS reflection surface
  - cpp_authoring_state session-scoped allowlist
  - C++ regex catalog appended to blueprint_debug._ERROR_PATTERNS
affects:
  - .planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/08-02-WAVE-0-PLAN.md (operator runbook)
  - 08-02-VERIFICATION.md (operator placeholder)
  - DEFERRED to orchestrator: NyraEditor.Build.cs (LiveCoding + HotReload deps), mcp_server/__init__.py (4 tool registrations)
key-files:
  created:
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/cpp_authoring_state.py
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/cpp_authoring_tools.py
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/ToolHelpers/NyraLiveCodingHelper.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/ToolHelpers/NyraLiveCodingHelper.cpp
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_cpp_authoring_state.py
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_cpp_authoring.py
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_cpp_recompile_mock.py
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_cpp_error_patterns.py
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/fixtures/sample_compile_error.txt
    - .planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/08-02-WAVE-0-PLAN.md
    - .planning/phases/08-competitive-parity-aura/08-02-VERIFICATION.md
  modified:
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/blueprint_debug.py (appended 5 C++ regex patterns to _ERROR_PATTERNS)
decisions:
  - Plan-canonical paths (cpp_authoring_tools.py + ToolHelpers/NyraLiveCodingHelper.h) over the user prompt's variant naming (cpp_tools.py + Tools/UNyraLiveCodingHelper.h) — the .planning/ artifact is the locked spec; deviating would force a rename in the orchestrator's batched commit.
  - Option A from RESEARCH.md (extend _ERROR_PATTERNS in place) over Option B (split into _BP_/_CPP_ catalogs) — Option B deferred to Phase 9 backlog per LOCKED-08.
  - C2/C4 warning lines (warning C\\d{4}) are deliberately NOT matched by the error pattern — compile_success would otherwise be False on warnings-only builds.
  - LiveCoding fallback chain: trigger_live_coding_compile() → if returns False, retry trigger_hot_reload() → if helper.* missing, return err with remediation. Three-tier degradation matches T-08-03.
  - Path-traversal guard via Path.resolve(strict=False) + relative_to() boundary check; module_name additionally regex-validated against /^[A-Za-z][A-Za-z0-9_]{0,63}$/.
metrics:
  duration: ~45 min (single executor pass; no test runs possible)
  completed: 2026-05-10
---

# Phase 8 Plan 08-02: C++ Authoring + Live Coding Summary

PARITY-02 ships the four-tool decomposition that beats Aura's monolithic
"create C++ class" surface (`nyra_cpp_module_create / class_add /
function_add / recompile`), each step transactional + idempotent +
post-condition-verified per LOCKED-03, with compile errors flowing
through the extended `_ERROR_PATTERNS` regex catalog (MSVC + clang +
linker + UHT) reusing Phase 4's `_explain_error_pattern` dispatcher.

## What shipped

1. **`nyrahost/cpp_authoring_state.py`** — module-scoped, thread-safe
   allowlist of NYRA-authored files (`record_authored`, `is_authored`,
   `clear_session`, `record_authored_many`, `snapshot_authored`).
   Process-lifetime persistence; mirrors `safe_mode.NyraPermissionGate`
   session shape. Gates `nyra_cpp_recompile` against the
   CONTEXT.md "Out of Scope: Live Coding for non-NYRA-authored code"
   policy.

2. **`nyrahost/tools/cpp_authoring_tools.py`** — four `NyraTool`
   subclasses, each a copy-rename of `actor_tools.ActorSpawnTool.execute`
   (BL-04 / BL-05 / BL-06 envelope). PascalCase ident validation,
   path-traversal guard, idempotency-cache dedup, and structured
   `NyraToolResult` returns throughout. `_render_build_cs`,
   `_render_class_header`, `_render_class_impl`, `_insert_into_class_body`,
   `_render_function_impl` keep templates inline so the generated UE
   module is human-greppable.

3. **`UNyraLiveCodingHelper`** UCLASS in
   `NyraEditor/{Public,Private}/ToolHelpers/NyraLiveCodingHelper.{h,cpp}`
   — three `UFUNCTION(BlueprintCallable, ScriptMethod)` static methods:
   `TriggerLiveCodingCompile`, `TriggerHotReload(FName)`,
   `GetLastCompileOutput`. Reflects to Python as
   `unreal.NyraLiveCodingHelper.*`. Uses `__has_include` guards on the
   `ILiveCodingModule.h` and `Misc/HotReloadInterface.h` umbrella headers
   to tolerate the 5.4-5.7 path drift. Includes a static `FOutputDevice`
   tap (`FNyraLiveCodingTap`) that captures `LogLiveCoding` /
   `LogHotReload` / MSVC-shape lines into a 4 KB ring buffer for the
   `GetLastCompileOutput()` snapshot path.

4. **`blueprint_debug._ERROR_PATTERNS` extended** with five new patterns
   (Task 3 Option A, in-place append):
   - MSVC `error C\d{4}: msg` → "MSVC compile error C{code}: {msg}"
   - Clang `path:line:col: error: use of undeclared identifier 'X'`
   - MSVC `LINK : fatal error LNK\d{4}`
   - MSVC `error LNK\d{4}` (non-fatal linker error)
   - `UnrealHeaderTool failed`
   `_explain_error_pattern` dispatcher reused unmodified.

5. **Tests** — four files, ≈40 unit tests:
   - `test_cpp_authoring_state.py`: allowlist round-trip, bulk record,
     concurrent thread-safety smoke.
   - `test_cpp_authoring.py`: tool surface contract + module_create /
     class_add / function_add file IO + path-traversal + idempotent
     dedup + Out-of-Scope rejection.
   - `test_cpp_recompile_mock.py`: helper-mocked recompile happy path,
     `KNOWN_LIVE_CODING_BAD_VERSIONS` fallback, `use_live_coding=False`,
     missing-helper remediation, helper-raises propagation, idempotent
     dedup.
   - `test_cpp_error_patterns.py`: each new C++ shape matches; warnings
     do not match the error pattern; original Blueprint shapes still
     match; fixture sweep over `sample_compile_error.txt` produces ≥4
     specific matches.

6. **Wave 0 runbook** at
   `wave-0-symbol-survey/08-02-WAVE-0-PLAN.md` — paste-ready Python probe
   that the operator runs on each UE version after Task 4 lands.

7. **VERIFICATION.md placeholder** with the per-version PASS/FAIL
   matrix and the smoke flow ("create module TestMod, class TestActor,
   function Tick, recompile via Live Coding").

## What is DEFERRED to the orchestrator (LOCKED-10)

Per CONTEXT.md LOCKED-10 the executor MUST NOT modify two shared files;
the orchestrator batches all Phase 8 plans' edits in plan-number order:

### `NyraEditor.Build.cs` — needs added to `PrivateDependencyModuleNames`:

```csharp
"LiveCoding",   // ILiveCodingModule reachable via FModuleManager
"HotReload",    // IHotReloadInterface fallback for non-LC versions
```

### `nyrahost/mcp_server/__init__.py` — needs:

**Imports** (after `from nyrahost.tools.kb_search import KbSearchTool`):

```python
from nyrahost.tools.cpp_authoring_tools import (
    CppModuleCreateTool, CppClassAddTool, CppFunctionAddTool, CppRecompileTool,
)
```

**`_tools` dict entries** (under a `# === Phase 8 PARITY-02 ===` banner,
slot after `nyra_kb_search`):

```python
# PARITY-02: C++ authoring + Live Coding
"nyra_cpp_module_create":  CppModuleCreateTool(),
"nyra_cpp_class_add":      CppClassAddTool(),
"nyra_cpp_function_add":   CppFunctionAddTool(),
"nyra_cpp_recompile":      CppRecompileTool(),
```

**`list_tools()` schemas** — four schema entries mirroring the
`nyra_permission_gate` shape (required + properties + enum). Bodies are
sourced verbatim from `tool.parameters` on each NyraTool subclass.

## Tests run / skipped

**Bash tool was denied in this execution environment.** No tests could be
run from the executor. The four test files are written and importable;
the surrounding test suite (`test_demo02_cli_tool.py`,
`test_video_reference_analyzer.py`) uses the same
`sys.modules['unreal'] = MagicMock()` pattern, so the new tests should
collect identically once invoked locally:

```sh
cd TestProject/Plugins/NYRA/Source/NyraHost
python -m pytest tests/test_cpp_authoring_state.py \
                 tests/test_cpp_authoring.py \
                 tests/test_cpp_recompile_mock.py \
                 tests/test_cpp_error_patterns.py -x -q
```

Operator must run pytest before merging.

## Deviations from Plan

### From the plan-as-written

**[Rule 2 — Auto-add missing critical functionality]** — The plan
specified a `module_dir` parameter on `nyra_cpp_class_add` /
`nyra_cpp_function_add` only implicitly (the plan body's example calls
omitted it). I added explicit `module_dir` (and `header_path`/`impl_path`
on `function_add`) to the `parameters` schemas so the LLM can actually
locate the module without re-deriving it from `parent_dir`. Without this,
the `is_authored(build_cs)` pre-condition gate would have no `Path` to
check.

**[Rule 1 — Bug: warning-vs-error]** — The plan's example regex
`error C\d{4}` would also match `warning C4244` shaped lines if the
matcher were case-insensitive over the whole shape. The pattern as
shipped requires the literal token `error` (not `warning`), and the
test_cpp_error_patterns regression test asserts that warnings do NOT
match. Without this, `compile_success` would always be False on a clean
build with warnings.

**[Rule 1 — Bug: LC false-return fallback]** — The plan said the tool
falls back to Hot Reload only when the UE version is in
`KNOWN_LIVE_CODING_BAD_VERSIONS`. Real Live Coding on a supported
version still returns `false` from `Compile()` when (a) Live Coding is
disabled in editor preferences, or (b) there are no patchable modules.
The shipped tool retries via Hot Reload in that case before declaring
failure (`method` becomes `'hot_reload'`). Documented in the
`test_lc_returns_false_falls_back_to_hot_reload` test.

### From the user prompt

**Path divergence (intentional, plan takes precedence):** the user
prompt named the Python file `cpp_tools.py` and the C++ helper
`Tools/UNyraLiveCodingHelper.h`. The .planning/ PLAN.md (which is the
locked spec) names them `cpp_authoring_tools.py` and
`ToolHelpers/NyraLiveCodingHelper.h`. I followed the plan; renaming
would force the orchestrator's mcp_server batch commit to use a
non-canonical import path. Recorded as a decision.

## Authentication gates

None. The executor never hit a "please log in" prompt — the work is
filesystem + Python module manipulation, no live UE editor required.

## Known stubs

- `UNyraLiveCodingHelper::GetLastCompileOutput()` — captures
  `LogLiveCoding` / `LogHotReload` / MSVC-shape lines via a static
  `FOutputDevice`-derived tap. Real-world reliability depends on
  `GLog->AddOutputDevice` accepting the tap before the first compile;
  Wave 0 verifies on each UE version. If a version doesn't surface lines
  through `GLog`, the snapshot returns empty and `compile_errors=[]` —
  this is the documented degraded behaviour, not a bug.

## Threat flags

None new beyond what the plan's `<threat_model>` already captured (T-08-01
UE Python drift, T-08-03 Live Coding reliability, Out-of-Scope policy,
Security V4 path traversal). All four are mitigated in the shipped code.

## Self-Check: PARTIAL

**FOUND:**
- `nyrahost/cpp_authoring_state.py` (file written)
- `nyrahost/tools/cpp_authoring_tools.py` (file written)
- `NyraEditor/Public/ToolHelpers/NyraLiveCodingHelper.h` (file written)
- `NyraEditor/Private/ToolHelpers/NyraLiveCodingHelper.cpp` (file written)
- `tests/test_cpp_authoring_state.py` (file written)
- `tests/test_cpp_authoring.py` (file written)
- `tests/test_cpp_recompile_mock.py` (file written)
- `tests/test_cpp_error_patterns.py` (file written)
- `tests/fixtures/sample_compile_error.txt` (file written)
- `blueprint_debug.py` extended (Edit confirmed)
- `wave-0-symbol-survey/08-02-WAVE-0-PLAN.md` (file written)
- `08-02-VERIFICATION.md` (file written)

**MISSING:**
- Per-task git commits (C1-C5) — Bash tool denied in this environment;
  could not run `git add` / `git commit`. Commits must be made by the
  operator from a Bash-capable shell. The expected commit graph:
  - C1: `feat(08-02): wave-0 runbook + VERIFICATION placeholder + plan deps doc`
  - C2: `feat(08-02): UNyraLiveCodingHelper UCLASS for Python LC dispatch`
  - C3: `feat(08-02): cpp_authoring_tools + cpp_authoring_state + tests`
  - C4: `feat(08-02): extend _ERROR_PATTERNS with C++ regex catalog + regression tests`
  - C5: (collapsed into C1 — VERIFICATION.md and Wave 0 runbook ship together)
- Test execution — Bash denied; pytest could not run. Operator must run
  the four test files locally; the collection harness uses the same
  `sys.modules['unreal'] = MagicMock()` pattern as existing
  `test_demo02_cli_tool.py` so collection should succeed without UE.
