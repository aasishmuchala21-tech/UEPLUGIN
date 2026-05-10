# Plan 08-05 — Wave 0 Operator Runbook (Niagara Symbol Survey)

> **Status:** `pending_manual_verification: true`
>
> This runbook is a placeholder. The four `symbol-survey-niagara-{ue}.md`
> outputs are produced by an operator, not by the autonomous executor. The
> survey can ONLY run after Task 1 (the C++ helper `UNyraNiagaraHelper`)
> has compiled into a real UE editor build. The autonomous executor cannot
> spawn UE 5.4/5.5/5.6/5.7 from this environment; the operator runs each
> version manually and commits the output.

## Pre-conditions (operator side)

1. UE editor is the version under test (5.4 / 5.5 / 5.6 / 5.7).
2. NyraEditor module has been recompiled with the Plan 08-05 changes:
   - `Source/NyraEditor/Public/ToolHelpers/NyraNiagaraHelper.h`
   - `Source/NyraEditor/Private/ToolHelpers/NyraNiagaraHelper.cpp`
   - `NyraEditor.Build.cs` `PrivateDependencyModuleNames` extended with
     `Niagara` + `NiagaraEditor` (orchestrator batches that file edit per
     LOCKED-10).
3. The plugin builds clean and the editor launches without redlines.
4. Niagara plugin is enabled in **Edit > Plugins > FX > Niagara** (default
   on for UE 5.4+; verify per version).

## Probe script (Python — paste into the UE Output Log Python REPL)

```python
import unreal

print("=" * 60)
print(f"NyraNiagaraHelper symbol survey — UE {unreal.SystemLibrary.get_engine_version()}")
print("=" * 60)

# Reflection probe — does the plain Niagara surface show up?
print("Niagara symbols on unreal.*:",
      [s for s in dir(unreal) if "Niagara" in s])
print("hasattr NiagaraSystemFactoryNew:", hasattr(unreal, "NiagaraSystemFactoryNew"))
print("hasattr NiagaraEditorSubsystem:",  hasattr(unreal, "NiagaraEditorSubsystem"))
print("hasattr NiagaraSystem:",           hasattr(unreal, "NiagaraSystem"))
print("hasattr NiagaraEmitter:",          hasattr(unreal, "NiagaraEmitter"))

if hasattr(unreal, "NiagaraSystem"):
    print("NiagaraSystem methods (first 30):",
          [m for m in dir(unreal.NiagaraSystem) if not m.startswith("_")][:30])

# UNyraNiagaraHelper reflection probe
present = hasattr(unreal, "NyraNiagaraHelper")
print("NyraNiagaraHelper reflected:", present)

if present:
    methods = [m for m in dir(unreal.NyraNiagaraHelper) if not m.startswith("_")]
    print("methods:", methods)

# Sprite + Ribbon template-path probe
sprite_template = "/Niagara/Templates/Sprite/SpriteBurst"
ribbon_template = "/Niagara/Templates/Ribbon/Ribbon"
sprite = unreal.EditorAssetLibrary.load_asset(sprite_template)
ribbon = unreal.EditorAssetLibrary.load_asset(ribbon_template)
print(f"sprite template loadable ({sprite_template}):", sprite is not None)
print(f"ribbon template loadable ({ribbon_template}):", ribbon is not None)

# T-08-04 — sim_target enum probe (different per UE major)
if hasattr(unreal, "ENiagaraSimTarget"):
    print("ENiagaraSimTarget present:", True)
    print("CPUSim:", getattr(unreal.ENiagaraSimTarget, "CPU_SIM", None))
    print("GPUComputeSim:", getattr(unreal.ENiagaraSimTarget, "GPU_COMPUTE_SIM", None))
else:
    print("ENiagaraSimTarget present:", False)
```

## Expected output template

For each UE version the operator runs the script and saves the console
output to:

- `.planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/symbol-survey-niagara-5.4.md`
- `... -5.5.md`
- `... -5.6.md`
- `... -5.7.md`

Each file uses this skeleton:

```markdown
# Niagara Symbol Survey — UE {VERSION}

**Operator:** {name/handle}
**Date:** YYYY-MM-DD
**Engine version (full):** 5.X.Y-build

## Reflection
- [ ] `unreal.NiagaraSystemFactoryNew` reflected: PASS / FAIL
- [ ] `unreal.NiagaraEditorSubsystem`  reflected: PASS / FAIL
- [ ] `unreal.NiagaraSystem`           reflected: PASS / FAIL
- [ ] `unreal.NiagaraEmitter`          reflected: PASS / FAIL
- [ ] `unreal.NyraNiagaraHelper`       reflected: PASS / FAIL
- Reflected NyraNiagaraHelper methods: ...

## Templates
- [ ] `/Niagara/Templates/Sprite/SpriteBurst` loadable: PASS / FAIL
- [ ] `/Niagara/Templates/Ribbon/Ribbon`      loadable: PASS / FAIL

## Sim-Target enum (T-08-04)
- [ ] `unreal.ENiagaraSimTarget.CPU_SIM` present: PASS / FAIL
- [ ] `unreal.ENiagaraSimTarget.GPU_COMPUTE_SIM` present: PASS / FAIL

## Verdict
- Niagara authoring usable on this version: YES / NO
- If NO: add `"5.X"` to `KNOWN_NIAGARA_BAD_VERSIONS` in
  `nyrahost/tools/niagara_tools.py`.
```

## Fail-fast rule

Per PLAN.md §"Fail-fast rule": if `NiagaraSystemFactoryNew` is **not
reflected** on a given version, the version is added to
`KNOWN_NIAGARA_BAD_VERSIONS` in the Python tool module and every tool
returns `not_supported_on_this_ue_version` at register-time. The plan
does **NOT** abort — graceful degradation is the design (T-08-01).

## T-08-04: GPU vs CPU emitter coverage

Both code paths must be exercised in operator verification (08-05-VERIFICATION.md):

1. Sprite emitter with `sim_target="cpu"` → must compile and tick on CPU.
2. Sprite emitter with `sim_target="gpu"` → must trigger the shader
   compile pass and tick on GPU.
3. Ribbon emitter with `sim_target="cpu"` → must render the trail.

If GPU compile fails on a version (Niagara has parallel API surfaces for
CPU and GPU emitters; module-parameter setters may differ), document the
divergence in the result row's Notes column and surface a
`sim_target_supported: ["cpu"]` field in the tool's startup banner.

## Build.cs deps that the orchestrator must add

Per LOCKED-10 the executor does NOT modify `NyraEditor.Build.cs`; the
orchestrator batches all Phase 8 plan deps in plan-number order in a
single commit at the end of the wave. Plan 08-05 needs **two** entries
appended to `PrivateDependencyModuleNames`:

```csharp
"Niagara",        // UNiagaraSystem, UNiagaraEmitter, FNiagaraEmitterHandle
"NiagaraEditor",  // module-parameter stack-API (UE editor-only)
```

Rationale:
- `Niagara`: `UNyraNiagaraHelper::AddEmitterFromTemplate` calls into
  `UNiagaraSystem::GetEmitterHandles()` and `FNiagaraEmitterHandle`.
  Headers `NiagaraSystem.h`, `NiagaraEmitter.h`, `NiagaraEmitterHandle.h`
  ship in this module.
- `NiagaraEditor`: `UNyraNiagaraHelper::SetScalarModuleParameter` walks
  the emitter's authoring stack via the editor-only parameter-set
  surface. This module is editor-only — gate it behind
  `Target.bBuildEditor == true` if NyraEditor ever ships a runtime
  configuration (currently it does not).

## mcp_server entries that the orchestrator must add

Per LOCKED-10 the executor does NOT modify
`nyrahost/mcp_server/__init__.py`. Plan 08-05 needs the orchestrator to
batch the following edits:

### Imports (after the existing `from nyrahost.tools.kb_search import KbSearchTool` line):

```python
from nyrahost.tools.niagara_tools import (
    NiagaraCreateSystemTool, NiagaraAddEmitterTool, NiagaraSetModuleParameterTool,
)
```

### `_tools` dict entries (under a `# === Phase 8 PARITY-05 ===` banner, after `nyra_kb_search`):

```python
# PARITY-05: Niagara
"nyra_niagara_create_system":         NiagaraCreateSystemTool(),
"nyra_niagara_add_emitter":           NiagaraAddEmitterTool(),
"nyra_niagara_set_module_parameter":  NiagaraSetModuleParameterTool(),
```

### `list_tools()` schemas (mirror the `nyra_permission_gate` exemplar)

The three schemas must mirror the `tool.parameters` JSON Schemas
declared on each NyraTool subclass. The schema for `nyra_niagara_add_emitter`
includes the `sim_target` enum (`["cpu", "gpu"]`) per T-08-04. The schema
bodies are sourced verbatim from the tool classes themselves; the
orchestrator can copy `tool.parameters` into the `inputSchema` field of
each `Tool(...)` entry.

Tool names (for the schema list):
- `nyra_niagara_create_system`
- `nyra_niagara_add_emitter`
- `nyra_niagara_set_module_parameter`

## Why this lives outside the autonomous flow

The dev box (`C:\Users\aasis\UEPLUGIN`) does not have the four UE
versions side-by-side; the survey is genuinely operator-bound. The
autonomous executor produced this runbook (a) as proof Task 0 was
considered, and (b) so the operator has a paste-ready Python probe that
covers the GPU vs CPU coverage requirement (T-08-04).
