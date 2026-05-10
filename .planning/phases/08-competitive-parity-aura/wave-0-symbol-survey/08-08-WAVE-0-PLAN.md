# Plan 08-08 — Wave 0 Operator Runbook (Metasounds Symbol Survey)

> **Status:** `pending_manual_verification: true`
>
> This runbook is a placeholder. The four `symbol-survey-metasound-{ue}.md`
> outputs are produced by an operator, not by the autonomous executor. Unlike
> 08-02/05/07, **08-08 needs no C++ helper** — `UMetaSoundBuilderSubsystem`
> (5.3+) is fully Python-reflected, so the survey can run as soon as the NYRA
> plugin loads on the target UE version. The autonomous executor cannot
> spawn UE 5.4/5.5/5.6/5.7 from this environment; the operator runs each
> version manually and commits the output.
>
> **HONEST: this is gloss-tier scope** (CONTEXT.md SC#8). Most game audio
> lives in Wwise/FMOD outside UE. Plan 08-08 exists for marketing-comparison
> parity and is the smallest plan in Phase 8.

## Pre-conditions (operator side)

1. UE editor is the version under test (5.4 / 5.5 / 5.6 / 5.7).
2. NyraEditor module loads cleanly on that engine (no Plan-08-08 C++
   changes — there is no Build.cs delta and no helper UCLASS).
3. The plugin builds clean and the editor launches without redlines.
4. **MetaSounds plugin is enabled** in **Edit > Plugins > Audio > MetaSounds**
   (default on for UE 5.4+; verify per version).
5. (Optional) the operator has a target Content folder where a test
   asset can be created without polluting the project — e.g.
   `/Game/Audio/Wave0/`.

## Probe script (Python — paste into the UE Output Log Python REPL)

```python
import unreal

print("=" * 60)
print(f"Metasounds symbol survey — UE {unreal.SystemLibrary.get_engine_version()}")
print("=" * 60)

# --- Capitalisation drift probe (RESEARCH.md A4) ----------------------
# UE may expose either 'MetaSound' or 'Metasound' spellings; this is the
# single most likely real-world failure mode for Plan 08-08.
print("MetaSound symbols (case A):", [s for s in dir(unreal) if "MetaSound" in s][:30])
print("Metasound symbols  (case B):", [s for s in dir(unreal) if "Metasound" in s][:30])

# --- Factory class (asset creation) -----------------------------------
print("hasattr MetaSoundSourceFactory:", hasattr(unreal, "MetaSoundSourceFactory"))
print("hasattr MetaSoundFactory:",       hasattr(unreal, "MetaSoundFactory"))
print("hasattr MetasoundFactory:",       hasattr(unreal, "MetasoundFactory"))

# --- Asset class (isinstance check / BL-12) ---------------------------
print("hasattr MetaSoundSource:",  hasattr(unreal, "MetaSoundSource"))
print("hasattr MetasoundSource:",  hasattr(unreal, "MetasoundSource"))
print("hasattr MetaSoundPatch:",   hasattr(unreal, "MetaSoundPatch"))

# --- Builder subsystem (graph mutation surface) -----------------------
print("hasattr MetaSoundBuilderSubsystem:", hasattr(unreal, "MetaSoundBuilderSubsystem"))
print("hasattr MetasoundBuilderSubsystem:", hasattr(unreal, "MetasoundBuilderSubsystem"))

builder_cls = (
    getattr(unreal, "MetaSoundBuilderSubsystem", None)
    or getattr(unreal, "MetasoundBuilderSubsystem", None)
)
if builder_cls is not None:
    methods = [m for m in dir(builder_cls) if not m.startswith("_")]
    print("Builder subsystem methods (first 40):", methods[:40])
    # Probe for the specific surface Plan 08-08 needs
    has_create_source_builder = any("source_builder" in m.lower() for m in methods)
    has_add_node              = any(m.lower().startswith("add_node") for m in methods)
    has_connect               = any("connect" in m.lower() for m in methods)
    print("has create_*_source_builder:", has_create_source_builder)
    print("has add_node*:",               has_add_node)
    print("has connect*:",                has_connect)
else:
    print("BUILDER NOT REFLECTED — Plan 08-08 reduces to nyra_metasound_create only.")
```

## Expected output template

For each UE version the operator runs the script and saves the console
output to:

- `.planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/symbol-survey-metasound-5.4.md`
- `... -5.5.md`
- `... -5.6.md`
- `... -5.7.md`

Each file uses this skeleton:

```markdown
# Metasounds Symbol Survey — UE {VERSION}

**Operator:** {name/handle}
**Date:** YYYY-MM-DD
**Engine version (full):** 5.X.Y-build

## Capitalisation drift (RESEARCH.md A4 — most likely failure mode)
- Case A `MetaSound*` symbols present: YES / NO   (count: N)
- Case B `Metasound*` symbols present: YES / NO   (count: N)
- Winning spelling on this version: `MetaSound` / `Metasound` / mixed

## Factory class
- [ ] `unreal.MetaSoundSourceFactory` reflected: PASS / FAIL
- [ ] `unreal.MetaSoundFactory`       reflected: PASS / FAIL
- [ ] `unreal.MetasoundFactory`       reflected: PASS / FAIL
- Factory class chosen by `_resolve_factory()` on this version: ____

## Asset class
- [ ] `unreal.MetaSoundSource` reflected: PASS / FAIL
- [ ] `unreal.MetasoundSource` reflected: PASS / FAIL
- [ ] `unreal.MetaSoundPatch`  reflected: PASS / FAIL
- Asset class chosen by `_resolve_asset_class()` on this version: ____

## Builder subsystem
- [ ] `unreal.MetaSoundBuilderSubsystem` reflected: PASS / FAIL
- [ ] `unreal.MetasoundBuilderSubsystem` reflected: PASS / FAIL
- [ ] Has `add_node*` method: PASS / FAIL
- [ ] Has `connect*` method:  PASS / FAIL
- First 40 reflected methods: ____

## Verdict
- `nyra_metasound_create`     usable on this version: YES / NO
- `nyra_metasound_add_node`   usable on this version: YES / NO
- `nyra_metasound_connect`    usable on this version: YES / NO
- If builder subsystem reflected but methods are NOT what 08-08 assumes:
  add `"5.X"` to `KNOWN_METASOUND_BUILDER_BAD_VERSIONS` in
  `nyrahost/tools/metasound_tools.py` and limit shipped surface to
  `nyra_metasound_create` only on this version.
- If neither factory spelling is present: add `"5.X"` to
  `KNOWN_METASOUND_BAD_VERSIONS` and every tool returns
  `not_supported_on_this_ue_version` at register-time.
```

## Decision tree (per UE version)

```
                ┌─ both spellings absent? ───── mark version unsupported
                │                                (KNOWN_METASOUND_BAD_VERSIONS)
                │
factory present ┤
                │
                └─ at least one spelling present
                       │
                       ├─ builder subsystem reflected, has add_node + connect?
                       │      └─ YES → ship all three tools (Python-only path)
                       │      └─ NO  → ship `nyra_metasound_create` only on
                       │               this version; add to
                       │               KNOWN_METASOUND_BUILDER_BAD_VERSIONS
                       │
                       └─ done — no C++ helper needed regardless
```

Per RESEARCH.md PARITY-08 §"UE Python entry point", the most likely
finding is "all four versions reflect the builder subsystem cleanly".
The fallback exists because A4 + A5 capitalisation/reflection drift is
the documented risk.

## Fail-fast rule

Per PLAN.md §"Fail-fast rule": if **neither** spelling of the factory
is present on a given version, the version is added to
`KNOWN_METASOUND_BAD_VERSIONS` in the Python tool module and every tool
returns `not_supported_on_this_ue_version` at register-time. The plan
does **NOT** abort — graceful degradation is the design (T-08-01).

If the factory IS present but the builder subsystem is NOT (or has the
wrong method shape), the version ships ONLY `nyra_metasound_create` and
the other two tools return `not_supported_on_this_ue_version`. This is
the partial-degradation path RESEARCH.md Q1 RESOLVED-DEFERRED-TO-WAVE-0
calls out.

## Build.cs deps

**None.** Plan 08-08 ships **no C++ helper**. The orchestrator does
NOT modify `NyraEditor.Build.cs` for this plan. This is the only
Wave-2 plan in Phase 8 with a zero-line Build.cs delta — by design,
because `UMetaSoundBuilderSubsystem` is fully Python-reflected.

## mcp_server entries that the orchestrator must add

Per LOCKED-10 the executor does NOT modify
`nyrahost/mcp_server/__init__.py`. Plan 08-08 needs the orchestrator
to batch the following edits in plan-number order at end of wave:

### Imports (after the existing `from nyrahost.tools.kb_search import KbSearchTool` line):

```python
from nyrahost.tools.metasound_tools import (
    MetasoundCreateTool, MetasoundAddNodeTool, MetasoundConnectTool,
)
```

### `_tools` dict entries (under a `# === Phase 8 PARITY-08 ===` banner):

```python
# PARITY-08: Metasounds (audio) — gloss-tier per CONTEXT.md SC#8
"nyra_metasound_create":   MetasoundCreateTool(),
"nyra_metasound_add_node": MetasoundAddNodeTool(),
"nyra_metasound_connect":  MetasoundConnectTool(),
```

### `list_tools()` schemas (mirror the `nyra_permission_gate` exemplar)

The three schemas mirror the `tool.parameters` JSON Schemas declared
on each NyraTool subclass. The schema bodies are sourced verbatim from
the tool classes; the orchestrator copies `tool.parameters` into the
`inputSchema` field of each `Tool(...)` entry.

Tool names (for the schema list):
- `nyra_metasound_create`
- `nyra_metasound_add_node`
- `nyra_metasound_connect`

## Why this lives outside the autonomous flow

The dev box (`C:\Users\aasis\UEPLUGIN`) does not have the four UE
versions side-by-side; the survey is genuinely operator-bound. The
autonomous executor produced this runbook (a) as proof Task 0 was
considered, (b) so the operator has a paste-ready Python probe that
covers the A4 capitalisation-drift risk explicitly, and (c) so the
fallback decision tree is decided BEFORE the operator runs the live
oscillator-to-output round-trip in `08-08-VERIFICATION.md`.
