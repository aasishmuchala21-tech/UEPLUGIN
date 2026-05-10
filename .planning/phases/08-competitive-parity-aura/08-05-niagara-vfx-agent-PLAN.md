---
phase: 8
plan: 08-05
requirement: PARITY-05
type: execute
wave: 2
tier: 2
autonomous: false
depends_on: []
blocking_preconditions:
  - "Wave 0 UE Python symbol survey for unreal.Niagara* per UE 5.4/5.5/5.6/5.7 (Task 0 below)"
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/niagara_tools.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/__init__.py
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/ToolHelpers/NyraNiagaraHelper.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/ToolHelpers/NyraNiagaraHelper.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_niagara_authoring.py
  - .planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/symbol-survey-niagara-{ue}.md
---

# Plan 08-05: Niagara VFX Agent (PARITY-05)

## Goal

Ship the `nyra_niagara_create_system / nyra_niagara_add_emitter / nyra_niagara_set_module_parameter` triplet — Phase 4-shape mutators that reproduce Aura's documented GPU sprite + ribbon emitter examples. C++ helper `UNyraNiagaraHelper` covers the module-parameter-set surface that UE Python doesn't reflect cleanly.

## Why this matches Aura

Per CONTEXT.md SC#5 (verbatim):

> **Matches Aura on Niagara VFX authoring**: PARITY-05 ships `nyra_niagara_create_system / nyra_niagara_add_emitter / nyra_niagara_set_module_parameter` triplet. Niagara's Python API surface is large but well-documented; the parity bar is "Aura's GPU sprite + ribbon emitter examples reproduce."

This is a **matches**. Aura's VFX docs explicitly call out 0.13.7+ transparent-material issues (RESEARCH.md Open Question 4), so NYRA's mutator-shape gives some headroom but the bar stays "matches".

## Wave 0: UE Python Symbol Survey

**Task 0** runs the symbol-survey script on each UE version BEFORE Tasks 1-5 land:

```python
import unreal
print("Niagara symbols:", [s for s in dir(unreal) if "Niagara" in s])
print("hasattr NiagaraSystemFactoryNew:", hasattr(unreal, "NiagaraSystemFactoryNew"))
print("hasattr NiagaraEditorSubsystem:",  hasattr(unreal, "NiagaraEditorSubsystem"))
print("hasattr NiagaraSystem:",           hasattr(unreal, "NiagaraSystem"))
print("hasattr NiagaraEmitter:",          hasattr(unreal, "NiagaraEmitter"))
# Check for the parameter-set surface
print("system methods:", [m for m in dir(unreal.NiagaraSystem) if not m.startswith("_")][:30] if hasattr(unreal, "NiagaraSystem") else "n/a")
```

**Output:** `.planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/symbol-survey-niagara-{5.4,5.5,5.6,5.7}.md` — one per UE version.

**Fail-fast rule:** if `NiagaraSystemFactoryNew` is missing on a shipped version, that version raises `not_supported_on_this_ue_version` at register-time. Plan does NOT abort.

## Pattern Compliance (Phase 4 mutator shape — LOCKED-03)

Per LOCKED-03 + PATTERNS.md §"Per-Plan §PARITY-05", the analog is **`material_tools.py`** (asset-create + parameter-set is the exact same shape Niagara needs).

| BL-helper | Where it's called | What it wraps |
|---|---|---|
| `idempotent_lookup(self.name, params)` | First line of `execute()` | Dedup repeats |
| `with session_transaction(f"NYRA: {self.name}"):` | Wraps every system mutation | Ctrl+Z reverts |
| `verify_post_condition(label, lambda: ...)` | After mutation | Re-load asset, isinstance-check, **scalar param readback `abs(readback - value) > 1e-4`** (mirror `material_tools.py:195-201`) |
| `idempotent_record(...)` | Last line | Cache by hash of (tool, params) |
| `NyraToolResult.ok({...})` | Always | BL-01 envelope |
| **BL-12 isinstance-check** (`material_tools.py:65-72, 173-184`) | Before mutation | `isinstance(asset, unreal.NiagaraSystem)` / `unreal.NiagaraEmitter` — refuse mutation when LLM passes wrong asset type |

| Tool | post-condition (BL-06) check |
|---|---|
| `nyra_niagara_create_system` | `does_asset_exist(path)` AND `isinstance(load_asset(path), unreal.NiagaraSystem)` |
| `nyra_niagara_add_emitter` | System has new emitter handle with matching name; emitter `sim_target` equals param |
| `nyra_niagara_set_module_parameter` | Scalar/vector readback within `1e-4` of requested value (mirror MaterialSetParamTool readback pattern) |

## MCP Registration

Per PATTERNS.md §"MCP Server Registration":

**`nyrahost/mcp_server/__init__.py:_tools` dict** — slot under `# === Phase 8 PARITY-05 ===` banner:

```python
"nyra_niagara_create_system":         NiagaraCreateSystemTool(),
"nyra_niagara_add_emitter":           NiagaraAddEmitterTool(),
"nyra_niagara_set_module_parameter":  NiagaraSetModuleParameterTool(),
```

**Imports:**

```python
from nyrahost.tools.niagara_tools import (
    NiagaraCreateSystemTool, NiagaraAddEmitterTool, NiagaraSetModuleParameterTool,
)
```

**`list_tools()` schemas** — under PARITY-05 banner. Schema for `nyra_niagara_add_emitter` includes `sim_target: {"type": "string", "enum": ["cpu", "gpu"]}` per T-08-04.

## C++ Helper Surface

**File:** `NyraEditor/Public/ToolHelpers/NyraNiagaraHelper.h`

```cpp
// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "NiagaraSystem.h"
#include "NyraNiagaraHelper.generated.h"

UCLASS(MinimalAPI)
class UNyraNiagaraHelper : public UObject
{
    GENERATED_BODY()

public:
    /** Add an emitter from a template path to a system. Returns the emitter handle name; empty on failure. */
    UFUNCTION(BlueprintCallable, Category="Nyra|Niagara", meta=(ScriptMethod))
    static FString AddEmitterFromTemplate(
        UNiagaraSystem* System, FName TemplatePath, FName SimTarget /* "cpu"/"gpu" */, FName HandleName);

    /** Set a scalar module parameter on a specific emitter handle. */
    UFUNCTION(BlueprintCallable, Category="Nyra|Niagara", meta=(ScriptMethod))
    static bool SetScalarModuleParameter(
        UNiagaraSystem* System, FName EmitterHandle, FName ParameterName, float Value);

    /** Set a vector module parameter on a specific emitter handle. */
    UFUNCTION(BlueprintCallable, Category="Nyra|Niagara", meta=(ScriptMethod))
    static bool SetVectorModuleParameter(
        UNiagaraSystem* System, FName EmitterHandle, FName ParameterName, FVector Value);

    /** Read back a scalar param for BL-06 post-condition verification. */
    UFUNCTION(BlueprintCallable, Category="Nyra|Niagara", meta=(ScriptMethod))
    static float GetScalarModuleParameter(
        UNiagaraSystem* System, FName EmitterHandle, FName ParameterName);
};
```

**`NyraEditor.Build.cs`** — add to `PrivateDependencyModuleNames`: `"Niagara"`, `"NiagaraEditor"`.

## Tasks

### Task 0: Wave 0 — UE Python symbol survey for Niagara (operator-run)

**Files:**
- `.planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/symbol-survey-niagara-{5.4,5.5,5.6,5.7}.md`

**Action:** Per Wave 0 section above. Operator runs the symbol-survey script in each UE version's Python REPL; commits output verbatim with PASS/FAIL per symbol.

**Verify:** Four files committed.

**Done:** Symbol matrix known.

### Task 1: Build C++ helper UCLASS — `UNyraNiagaraHelper`

**Files:**
- `NyraEditor/Public/ToolHelpers/NyraNiagaraHelper.h`
- `NyraEditor/Private/ToolHelpers/NyraNiagaraHelper.cpp`
- `NyraEditor/NyraEditor.Build.cs`

**Action:** Per the C++ Helper Surface section above. Implementation uses `UNiagaraSystem::GetEmitterHandles()`, `FNiagaraEmitterHandle`, `UNiagaraEmitter` direct manipulation. For module parameter set, walk the emitter's stack via `UNiagaraStackEntry` API (Niagara editor module). Each function returns failure as empty FString / false / `MIN_flt`.

**Verify:** UE editor builds clean on UE 5.6.

**Done:** `unreal.NyraNiagaraHelper.add_emitter_from_template(...)` callable from Python.

### Task 2: Build three `nyra_niagara_*` mutator tools

**Files:** `nyrahost/tools/niagara_tools.py`

**Action — copy-rename of `material_tools.MaterialCreateMICTool` + `MaterialSetParamTool` (PATTERNS.md §"PARITY-05 Pattern lift"):**

```python
"""
PARITY-05 — Niagara authoring mutators.

Tool shape mirrors material_tools.MaterialCreateMICTool (asset create) and
MaterialSetParamTool (scalar/vector parameter set + readback verification).
"""
import structlog
from nyrahost.tools.base import (
    NyraTool, NyraToolResult,
    session_transaction, idempotent_lookup, idempotent_record,
    verify_post_condition,
)

log = structlog.get_logger("nyrahost.tools.niagara_tools")

__all__ = ["NiagaraCreateSystemTool", "NiagaraAddEmitterTool", "NiagaraSetModuleParameterTool"]


def _load_niagara_system(path: str):
    """Defensive lookup + isinstance check — BL-12 from material_tools.py:65-72."""
    import unreal
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if asset is None:
        return None
    if not isinstance(asset, unreal.NiagaraSystem):
        return None
    return asset


class NiagaraCreateSystemTool(NyraTool):
    name = "nyra_niagara_create_system"
    description = "Create a new UNiagaraSystem asset at the given content path."
    parameters = {
        "type": "object",
        "properties": {
            "asset_path": {"type": "string", "description": "/Game/VFX/NS_MyEffect"},
        },
        "required": ["asset_path"],
    }

    def execute(self, params):
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        with session_transaction(f"NYRA: {self.name}"):
            try:
                import unreal
                if not hasattr(unreal, "NiagaraSystemFactoryNew"):
                    return NyraToolResult.err(
                        "unreal.NiagaraSystemFactoryNew not reflected on this UE version"
                    )
                factory = unreal.NiagaraSystemFactoryNew()
                asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
                pkg_path, pkg_name = params["asset_path"].rsplit("/", 1)
                ns = asset_tools.create_asset(pkg_name, pkg_path, unreal.NiagaraSystem, factory)
                if ns is None:
                    return NyraToolResult.err(f"create_asset returned None for {params['asset_path']}")
                unreal.EditorAssetLibrary.save_asset(params["asset_path"])
            except Exception as e:
                log.error("niagara_create_system_failed", error=str(e))
                return NyraToolResult.err(f"failed: {e}")

            err = verify_post_condition(
                f"{self.name}({params['asset_path']})",
                lambda: _load_niagara_system(params["asset_path"]) is not None,
            )
            if err:
                return NyraToolResult.err(err)

        result = {"asset_path": params["asset_path"]}
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)


class NiagaraAddEmitterTool(NyraTool):
    name = "nyra_niagara_add_emitter"
    description = "Add an emitter from a template (sprite / ribbon / mesh) to a system."
    parameters = {
        "type": "object",
        "properties": {
            "system_path":   {"type": "string"},
            "template_path": {"type": "string", "description": "Niagara emitter template, e.g. /Niagara/Templates/Sprite/SpriteBurst"},
            "sim_target":    {"type": "string", "enum": ["cpu", "gpu"], "default": "cpu"},
            "handle_name":   {"type": "string"},
        },
        "required": ["system_path", "template_path", "handle_name"],
    }

    def execute(self, params):
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        with session_transaction(f"NYRA: {self.name}"):
            try:
                import unreal
                ns = _load_niagara_system(params["system_path"])
                if ns is None:
                    return NyraToolResult.err(f"NiagaraSystem not found: {params['system_path']}")
                handle = unreal.NyraNiagaraHelper.add_emitter_from_template(
                    ns,
                    unreal.Name(params["template_path"]),
                    unreal.Name(params["sim_target"]),
                    unreal.Name(params["handle_name"]),
                )
                if not handle:
                    return NyraToolResult.err("AddEmitterFromTemplate returned empty handle")
                unreal.EditorAssetLibrary.save_asset(params["system_path"])
            except Exception as e:
                log.error("niagara_add_emitter_failed", error=str(e))
                return NyraToolResult.err(f"failed: {e}")

            err = verify_post_condition(
                f"{self.name}({params['system_path']})",
                lambda: _load_niagara_system(params["system_path"]) is not None,
            )
            if err:
                return NyraToolResult.err(err)

        result = {
            "system_path": params["system_path"],
            "handle_name": handle,
            "sim_target":  params["sim_target"],
        }
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)


class NiagaraSetModuleParameterTool(NyraTool):
    name = "nyra_niagara_set_module_parameter"
    description = "Set a scalar or vector module parameter on a specific emitter."
    parameters = {
        "type": "object",
        "properties": {
            "system_path":     {"type": "string"},
            "emitter_handle":  {"type": "string"},
            "parameter_name":  {"type": "string"},
            "value_kind":      {"type": "string", "enum": ["scalar", "vector"]},
            "scalar_value":    {"type": "number"},
            "vector_value":    {
                "type": "object",
                "properties": {"x": {"type": "number"}, "y": {"type": "number"}, "z": {"type": "number"}},
            },
        },
        "required": ["system_path", "emitter_handle", "parameter_name", "value_kind"],
    }

    def execute(self, params):
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        with session_transaction(f"NYRA: {self.name}"):
            try:
                import unreal
                ns = _load_niagara_system(params["system_path"])
                if ns is None:
                    return NyraToolResult.err(f"NiagaraSystem not found: {params['system_path']}")
                if params["value_kind"] == "scalar":
                    val = float(params["scalar_value"])
                    ok = unreal.NyraNiagaraHelper.set_scalar_module_parameter(
                        ns,
                        unreal.Name(params["emitter_handle"]),
                        unreal.Name(params["parameter_name"]),
                        val,
                    )
                else:
                    vv = params["vector_value"]
                    ok = unreal.NyraNiagaraHelper.set_vector_module_parameter(
                        ns,
                        unreal.Name(params["emitter_handle"]),
                        unreal.Name(params["parameter_name"]),
                        unreal.Vector(vv["x"], vv["y"], vv["z"]),
                    )
                if not ok:
                    return NyraToolResult.err("Set*ModuleParameter returned false")
                unreal.EditorAssetLibrary.save_asset(params["system_path"])
            except Exception as e:
                log.error("niagara_set_module_parameter_failed", error=str(e))
                return NyraToolResult.err(f"failed: {e}")

            # BL-06 readback — mirror material_tools.py:195-201
            if params["value_kind"] == "scalar":
                err = verify_post_condition(
                    f"{self.name}({params['parameter_name']})",
                    lambda: abs(unreal.NyraNiagaraHelper.get_scalar_module_parameter(
                        ns, unreal.Name(params["emitter_handle"]), unreal.Name(params["parameter_name"])
                    ) - val) < 1e-4,
                )
                if err:
                    return NyraToolResult.err(err)

        result = {"system_path": params["system_path"], "parameter": params["parameter_name"], "value_kind": params["value_kind"]}
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)
```

**Verify:** `pytest tests/test_niagara_authoring.py -x -q`.

**Done:** All three tools subclass `NyraTool`, follow canonical shape.

### Task 3: MCP registration

**Files:** `nyrahost/mcp_server/__init__.py`

**Action:** Per the MCP Registration section above. Three entries under PARITY-05 banner.

**Verify:** `pytest tests/test_mcp_server.py::test_list_tools_includes_phase_8_parity_05 -x -q`.

**Done:** Three tools in `mcp_server.list_tools()`.

### Task 4: Build Niagara unit tests with mocked `unreal`

**Files:** `tests/test_niagara_authoring.py`

**Action — minimum coverage:**
- `nyra_niagara_create_system("/Game/VFX/NS_X")` succeeds with mocked `unreal.NiagaraSystemFactoryNew + AssetTools`.
- Idempotent: second call returns `deduped: True`.
- `nyra_niagara_add_emitter` with `sim_target: "cpu"` and `sim_target: "gpu"` both succeed (T-08-04).
- BL-12 isinstance-check: passing a Material asset path to `nyra_niagara_set_module_parameter` returns `err`.
- Mocked scalar readback within `1e-4` tolerance triggers `ok`; out-of-tolerance triggers `err`.
- Missing `NiagaraSystemFactoryNew` symbol → register-time `err`.

**Verify:** `pytest tests/test_niagara_authoring.py -x -q` is green.

**Done:** Unit tests pass on dev box without UE editor.

### Task 5: Operator-run verification — `pending_manual_verification: true`

**Files:** `08-05-VERIFICATION.md`

**Operator runbook (per UE version 5.4/5.5/5.6/5.7):**
1. UE editor with NYRA enabled
2. `nyra_niagara_create_system("/Game/VFX/NS_TestSparks")`
3. `nyra_niagara_add_emitter(system_path, template_path="/Niagara/Templates/Sprite/SpriteBurst", sim_target="cpu", handle_name="SpriteBurstCPU")` — assert handle exists
4. Repeat with `sim_target="gpu"` (T-08-04 GPU+CPU dual coverage)
5. Add ribbon emitter: template `/Niagara/Templates/Ribbon/Ribbon`
6. `nyra_niagara_set_module_parameter(handle="SpriteBurstCPU", parameter_name="SpawnRate", value_kind="scalar", scalar_value=50.0)` — open the system in editor; assert SpawnRate reads 50.0
7. Drop the system into a level and play — sprite + ribbon should render

**Done:** VERIFICATION.md filled with PASS/FAIL per UE version + sim_target.

## Tests

| Test file | What it verifies | Pending manual? |
|---|---|---|
| `tests/test_niagara_authoring.py` | Three tools' execute paths with mocked `unreal`; BL-06 readback; BL-12 isinstance | No |
| `tests/test_mcp_server.py::test_list_tools_includes_phase_8_parity_05` | MCP registration | No |
| `08-05-VERIFICATION.md` | Live sprite-CPU + sprite-GPU + ribbon emitter on UE 5.4/5.5/5.6/5.7 | **Yes** |

## Threats addressed

- **T-08-01** (UE Python API drift): Wave 0 symbol survey + `hasattr(unreal, "NiagaraSystemFactoryNew")` register-time check.
- **T-08-04** (Niagara emitter API GPU vs CPU split): tool param `sim_target` with `enum: ["cpu", "gpu"]`; both paths covered in Task 5 verification + Task 4 unit tests.
- **BL-12 isinstance-check**: refuses mutation when LLM passes wrong asset class.

## Acceptance criteria

- [ ] Three `nyra_niagara_*` tools registered in `mcp_server.list_tools()` (`pytest tests/test_mcp_server.py::test_list_tools_includes_phase_8_parity_05 -x` passes).
- [ ] `pytest tests/test_niagara_authoring.py -x -q` is green — every tool returns `NyraToolResult`, dedup works, BL-12 isinstance reject works, scalar readback within `1e-4` works.
- [ ] `unreal.NyraNiagaraHelper.add_emitter_from_template(...)` callable from Python in UE 5.6 editor.
- [ ] Wave 0 symbol survey artifacts (`symbol-survey-niagara-{ue}.md`) committed for each shipped UE version.
- [ ] `08-05-VERIFICATION.md` operator-run: GPU sprite + CPU sprite + ribbon emitter examples reproduce on UE 5.6 + at least one of {5.4, 5.5, 5.7}.

## Honest acknowledgments

- **`pending_manual_verification: true`** for the live emitter rendering — Wave 0 + the operator runbook are the only paths to verifying GPU vs CPU on each UE version.
- **C++ helper required for module-parameter set** — RESEARCH.md A2 + Niagara stack-API surface is the riskiest of the Phase 8 helpers. Plan reserves the helper but accepts that the helper's `SetScalarModuleParameter` may need adjustment per UE version.
- **No custom-module DSL authoring** — CONTEXT.md Out-of-Scope. Plan only ships system + emitter + module-parameter-set on EXISTING module classes.
- **0.13.7+ transparent-material issues** (Aura's documented limitation per RESEARCH.md Open Question 4) are not in scope for this plan; reproducing standard sprite + ribbon emitters is the parity bar, and that's what the verification runbook checks.
