---
phase: 8
plan: 08-08
requirement: PARITY-08
type: execute
wave: 2
tier: 2
autonomous: false
depends_on: []
blocking_preconditions:
  - "Wave 0 UE Python symbol survey for unreal.MetaSound* per UE 5.4/5.5/5.6/5.7 (Task 0 below)"
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/metasound_tools.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/__init__.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_metasound_authoring.py
  - .planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/symbol-survey-metasound-{ue}.md
---

# Plan 08-08: Metasounds (Audio) Agent (PARITY-08)

> **HONEST: this is feature-surface gloss.** Per CONTEXT.md SC#8 and PROJECT-level acknowledgment: most game audio lives in Wwise/FMOD outside UE. This plan ships for marketing-comparison parity — the smallest scope, smallest test surface, lowest leverage of the eight Phase 8 plans. Tier-2; not on the LOCKED-09 mandatory list.

## Goal

Ship the `nyra_metasound_create / nyra_metasound_add_node / nyra_metasound_connect` triplet as Phase 4-shape mutators, leveraging `UMetaSoundBuilderSubsystem` (the cleanest reflected surface in the phase per RESEARCH.md). Minimal C++ helper surface — likely none, since the builder subsystem is fully Python-reflected.

## Why this matches Aura

Per CONTEXT.md SC#8 (verbatim):

> **Matches Aura on Audio (Metasounds)**: PARITY-08 ships `nyra_metasound_create / nyra_metasound_add_node / nyra_metasound_connect`. Smallest surface area; included for marketing-comparison parity. (Honest acknowledgment: most game audio lives in Wwise/FMOD outside UE, so this tool is feature-surface gloss more than usage-volume win.)

Aura's Audio Agent docs flag "Wave Player issues 5.4-5.6" (RESEARCH.md PARITY-08 §Confidence row) — the parity bar is lower than feared. NYRA's mutator-shape is the "matches" lever; the gloss-tier scope keeps the test surface tiny.

## Wave 0: UE Python Symbol Survey

**Task 0** runs the symbol-survey script on each UE version BEFORE Tasks 1-4 land:

```python
import unreal
print("MetaSound symbols (case A):", [s for s in dir(unreal) if "MetaSound" in s])
print("Metasound symbols  (case B):", [s for s in dir(unreal) if "Metasound" in s])
print("hasattr MetaSoundFactory:",            hasattr(unreal, "MetaSoundFactory"))
print("hasattr MetasoundFactory:",            hasattr(unreal, "MetasoundFactory"))
print("hasattr MetaSoundBuilderSubsystem:",   hasattr(unreal, "MetaSoundBuilderSubsystem"))
print("hasattr MetasoundBuilderSubsystem:",   hasattr(unreal, "MetasoundBuilderSubsystem"))
# Probe builder methods
if hasattr(unreal, "MetaSoundBuilderSubsystem"):
    print("methods:", [m for m in dir(unreal.MetaSoundBuilderSubsystem) if not m.startswith("_")][:30])
```

**Output:** `.planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/symbol-survey-metasound-{5.4,5.5,5.6,5.7}.md`

**Critical:** RESEARCH.md A4 explicitly flags MetaSoundFactory **capitalisation drift** (Aura's docs imply "MetaSoundFactory" but the Python binding could be "MetasoundFactory"). The tool init code MUST probe BOTH spellings and pick whichever is present.

**Fail-fast rule:** if neither spelling is present on a shipped version, that version raises `not_supported_on_this_ue_version` at register-time. Plan does NOT abort.

## Pattern Compliance (Phase 4 mutator shape — LOCKED-03)

Per LOCKED-03 + PATTERNS.md §"PARITY-08 Closest analog: PARITY-05 (Niagara)":

> Same asset+nodes+connect pattern, smaller surface. Pattern lift identical to PARITY-05: MaterialCreateMICTool shape for `_create`, MaterialSetParamTool shape for `_add_node` + `_connect` (the latter sets `from_node_id`/`from_pin`/`to_node_id`/`to_pin` instead of `param_name`/`value`, but the BL-04/05/06 envelope is the same).

| BL-helper | Where it's called | What it wraps |
|---|---|---|
| `idempotent_lookup(self.name, params)` | First line of `execute()` | Dedup repeats |
| `with session_transaction(...)`: | Wraps every Metasound graph mutation | Ctrl+Z reverts |
| `verify_post_condition(...)` | After mutation | Re-load asset, isinstance check, confirm node/connection exists |
| `idempotent_record(...)` | Last line | Cache by hash |
| `NyraToolResult.ok({...})` / `.err(msg)` | Always | BL-01 envelope |
| **BL-12 isinstance-check** | Before mutation | `isinstance(asset, unreal.MetaSoundSource)` / `unreal.MetaSoundPatch` |

| Tool | post-condition (BL-06) check |
|---|---|
| `nyra_metasound_create` | `does_asset_exist(path)` AND isinstance check (correct asset class) |
| `nyra_metasound_add_node` | After mutation, builder subsystem reports a node with the requested name |
| `nyra_metasound_connect` | After mutation, the builder subsystem reports the connection between the two pins |

## MCP Registration

**`nyrahost/mcp_server/__init__.py:_tools` dict** — slot under `# === Phase 8 PARITY-08 ===` banner:

```python
"nyra_metasound_create":   MetasoundCreateTool(),
"nyra_metasound_add_node": MetasoundAddNodeTool(),
"nyra_metasound_connect":  MetasoundConnectTool(),
```

**Imports:**

```python
from nyrahost.tools.metasound_tools import (
    MetasoundCreateTool, MetasoundAddNodeTool, MetasoundConnectTool,
)
```

**`list_tools()` schemas** — under PARITY-08 banner. Each tool's parameters block follows `material_tools.MaterialSetParamTool` shape.

## C++ Helper Surface

**Likely none** — RESEARCH.md PARITY-08 §"UE Python entry point" and §"Architectural Responsibility Map":

> Plan 08-08 is the smallest helper surface in the phase — `UMetaSoundBuilderSubsystem` (5.3+) IS Python-reflected and is the cleanest surface in the phase.

**However:** if Wave 0 (Task 0) finds the builder-subsystem methods are not Python-reflected (a real risk per RESEARCH.md Open Question 1), Task 1.5 below adds a thin `UNyraMetaSoundHelper` UCLASS to bridge. Default plan assumes no helper needed; helper is a contingent fallback only if survey demands it.

## Tasks

### Task 0: Wave 0 — UE Python symbol survey for Metasounds (operator-run)

**Files:**
- `.planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/symbol-survey-metasound-{5.4,5.5,5.6,5.7}.md`

**Action:** Per Wave 0 section above. Operator runs in each UE version's Python REPL. **MUST probe BOTH MetaSound and Metasound capitalisations** per RESEARCH.md A4. Operator records:
1. Which capitalisation is correct on this version
2. Whether `MetaSoundBuilderSubsystem` is reflected
3. Whether `add_node` / `connect_nodes` builder methods are reflected

**Output decision tree:**
- If builder subsystem fully reflected → proceed to Task 1 (Python-only path)
- If builder subsystem methods NOT reflected → escalate to Task 1.5 (add `UNyraMetaSoundHelper` C++ helper)
- If `MetaSoundFactory` (either spelling) NOT reflected at all → mark version unsupported

**Verify:** Four files committed.

**Done:** Symbol matrix known + path forward decided per UE version.

### Task 1: Build three `nyra_metasound_*` mutator tools (Python-only path)

**Files:** `nyrahost/tools/metasound_tools.py`

**Action — copy-rename of `niagara_tools.py` (PATTERNS.md §"PARITY-08 Pattern lift identical to PARITY-05"):**

```python
"""
PARITY-08 — Metasounds authoring mutators.

Smallest scope of Phase 8 — gloss-tier per CONTEXT.md SC#8. Three tools:
create, add_node, connect. Tool shape mirrors niagara_tools.py.

Capitalisation note (RESEARCH.md A4): UE may expose either
'MetaSoundFactory' or 'MetasoundFactory' — _resolve_factory() probes both.
"""
import structlog
from nyrahost.tools.base import (
    NyraTool, NyraToolResult,
    session_transaction, idempotent_lookup, idempotent_record,
    verify_post_condition,
)

log = structlog.get_logger("nyrahost.tools.metasound_tools")

__all__ = ["MetasoundCreateTool", "MetasoundAddNodeTool", "MetasoundConnectTool"]


def _resolve_factory():
    """Per RESEARCH.md A4 — probe both capitalisation spellings."""
    import unreal
    for name in ("MetaSoundSourceFactory", "MetaSoundFactory", "MetasoundFactory"):
        if hasattr(unreal, name):
            return getattr(unreal, name)
    return None


def _resolve_asset_class():
    """The created asset class — usually MetaSoundSource."""
    import unreal
    for name in ("MetaSoundSource", "MetasoundSource", "MetaSoundPatch"):
        if hasattr(unreal, name):
            return getattr(unreal, name)
    return None


def _resolve_builder_subsystem():
    """The graph mutation surface — required for add_node + connect."""
    import unreal
    for name in ("MetaSoundBuilderSubsystem", "MetasoundBuilderSubsystem"):
        if hasattr(unreal, name):
            return unreal.get_editor_subsystem(getattr(unreal, name))
    return None


def _load_metasound(path: str):
    """Defensive lookup + isinstance check (BL-12)."""
    import unreal
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if asset is None:
        return None
    cls = _resolve_asset_class()
    if cls is not None and not isinstance(asset, cls):
        return None
    return asset


class MetasoundCreateTool(NyraTool):
    name = "nyra_metasound_create"
    description = "Create a new MetaSoundSource asset at the given content path."
    parameters = {
        "type": "object",
        "properties": {
            "asset_path": {"type": "string", "description": "/Game/Audio/MS_MyEffect"},
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
                factory_cls = _resolve_factory()
                asset_cls = _resolve_asset_class()
                if factory_cls is None or asset_cls is None:
                    return NyraToolResult.err(
                        "MetaSound factory/source class not reflected on this UE version "
                        "(checked both capitalisations); see Wave 0 symbol survey"
                    )
                factory = factory_cls()
                asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
                pkg_path, pkg_name = params["asset_path"].rsplit("/", 1)
                ms = asset_tools.create_asset(pkg_name, pkg_path, asset_cls, factory)
                if ms is None:
                    return NyraToolResult.err(f"create_asset returned None for {params['asset_path']}")
                unreal.EditorAssetLibrary.save_asset(params["asset_path"])
            except Exception as e:
                log.error("metasound_create_failed", error=str(e))
                return NyraToolResult.err(f"failed: {e}")

            err = verify_post_condition(
                f"{self.name}({params['asset_path']})",
                lambda: _load_metasound(params["asset_path"]) is not None,
            )
            if err:
                return NyraToolResult.err(err)

        result = {"asset_path": params["asset_path"]}
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)


class MetasoundAddNodeTool(NyraTool):
    name = "nyra_metasound_add_node"
    description = "Add a node (oscillator, wave-player, mixer, etc.) to a Metasound graph."
    parameters = {
        "type": "object",
        "properties": {
            "asset_path": {"type": "string"},
            "node_class": {"type": "string", "description": "e.g. 'Oscillator', 'WavePlayer'"},
            "node_name":  {"type": "string"},
        },
        "required": ["asset_path", "node_class", "node_name"],
    }

    def execute(self, params):
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        with session_transaction(f"NYRA: {self.name}"):
            try:
                import unreal
                builder = _resolve_builder_subsystem()
                if builder is None:
                    return NyraToolResult.err(
                        "MetaSoundBuilderSubsystem not reflected on this UE version "
                        "(checked both capitalisations)"
                    )
                ms = _load_metasound(params["asset_path"])
                if ms is None:
                    return NyraToolResult.err(f"MetaSound not found: {params['asset_path']}")
                # Builder API: subsystem-specific; pseudo-call here, exact signature
                # finalised after Wave 0 dump confirms method names.
                ok = builder.add_node(ms, params["node_class"], params["node_name"])
                if not ok:
                    return NyraToolResult.err(f"add_node returned false for {params['node_name']}")
                unreal.EditorAssetLibrary.save_asset(params["asset_path"])
            except Exception as e:
                log.error("metasound_add_node_failed", error=str(e))
                return NyraToolResult.err(f"failed: {e}")

            err = verify_post_condition(
                f"{self.name}({params['asset_path']})",
                lambda: _load_metasound(params["asset_path"]) is not None,
            )
            if err:
                return NyraToolResult.err(err)

        result = {"asset_path": params["asset_path"], "node_name": params["node_name"], "node_class": params["node_class"]}
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)


class MetasoundConnectTool(NyraTool):
    name = "nyra_metasound_connect"
    description = "Connect two pins between Metasound nodes."
    parameters = {
        "type": "object",
        "properties": {
            "asset_path":   {"type": "string"},
            "from_node_id": {"type": "string"},
            "from_pin":     {"type": "string"},
            "to_node_id":   {"type": "string"},
            "to_pin":       {"type": "string"},
        },
        "required": ["asset_path", "from_node_id", "from_pin", "to_node_id", "to_pin"],
    }
    # ... follows the same canonical shape, calls builder.connect_pins(...) ...
```

**Verify:** `pytest tests/test_metasound_authoring.py -x -q` (Task 3).

**Done:** Three tools subclass `NyraTool`, follow canonical shape. Capitalisation drift handled defensively.

### Task 1.5 (CONTINGENT — only if Wave 0 surfaces builder-subsystem reflection gap)

**Files (only created if needed):**
- `NyraEditor/Public/ToolHelpers/NyraMetaSoundHelper.h`
- `NyraEditor/Private/ToolHelpers/NyraMetaSoundHelper.cpp`
- `NyraEditor/NyraEditor.Build.cs` (add `MetasoundEngine`, `MetasoundEditor`)

**Action:** UCLASS with `AddNode(UMetaSoundSource*, FName, FName)` + `ConnectPins(...)` matching the contracts in Task 1's Python tools. Only built if Wave 0 confirms the builder subsystem methods aren't Python-reflected.

**Verify:** UE 5.6 builds clean.

**Done (or N/A):** Either helper added or task is skipped per Wave 0 outcome.

### Task 2: MCP registration

**Files:** `nyrahost/mcp_server/__init__.py`

**Action:** Per the MCP Registration section above. Three entries under PARITY-08 banner.

**Verify:** `pytest tests/test_mcp_server.py::test_list_tools_includes_phase_8_parity_08 -x -q`.

**Done:** Three tools in `mcp_server.list_tools()`.

### Task 3: Build Metasound unit tests with mocked `unreal`

**Files:** `tests/test_metasound_authoring.py`

**Action — minimum coverage (smallest test surface in Phase 8):**
- `nyra_metasound_create("/Game/Audio/MS_X")` succeeds with mocked factory.
- Idempotent: second call returns `deduped: True`.
- `_resolve_factory` finds the factory under EITHER capitalisation; returns None when neither present (regression for A4 risk).
- BL-12 isinstance-check: passing wrong asset class returns `err`.
- `add_node` / `connect` return `NyraToolResult` envelope; missing builder subsystem → `err`.

**Verify:** `pytest tests/test_metasound_authoring.py -x -q` is green.

**Done:** Unit tests pass on dev box.

### Task 4: Operator-run verification — `pending_manual_verification: true`

**Files:** `08-08-VERIFICATION.md`

**Operator runbook (per UE version 5.4/5.5/5.6/5.7):**
1. UE editor with NYRA enabled
2. `nyra_metasound_create("/Game/Audio/MS_TestTone")`
3. `nyra_metasound_add_node(asset_path, node_class="Oscillator", node_name="Osc1")`
4. `nyra_metasound_add_node(asset_path, node_class="OutputAudio", node_name="Out1")` (if needed; the asset may have a default output)
5. `nyra_metasound_connect(asset_path, from_node_id="Osc1", from_pin="Out", to_node_id="Out1", to_pin="In")`
6. Open the Metasound asset in editor; play preview — assert audio plays
7. Note any per-version capitalisation drift in the VERIFICATION.md so Task 1.5 (if applicable) can be sized correctly

**Done:** VERIFICATION.md filled with PASS/FAIL per UE version + capitalisation findings.

## Tests

| Test file | What it verifies | Pending manual? |
|---|---|---|
| `tests/test_metasound_authoring.py` | Three tools' execute paths with mocked `unreal`; capitalisation drift handling | No |
| `tests/test_mcp_server.py::test_list_tools_includes_phase_8_parity_08` | MCP registration | No |
| `08-08-VERIFICATION.md` | Live oscillator+output+connect on UE 5.4/5.5/5.6/5.7 | **Yes** |

## Threats addressed

- **T-08-01** (UE Python API drift): `_resolve_factory` / `_resolve_asset_class` / `_resolve_builder_subsystem` defensive coding probes BOTH capitalisations + falls back to `not_supported_on_this_ue_version` when neither present.
- **A4 capitalisation drift** (RESEARCH.md): explicit dual-spelling probe; tested in unit tests.
- **A5 builder subsystem reflection risk**: Wave 0 (Task 0) outcome decides whether Task 1.5 (C++ helper) is needed. Plan does NOT silently fail if reflection is incomplete.

## Acceptance criteria

- [ ] Three `nyra_metasound_*` tools registered in `mcp_server.list_tools()` (`pytest tests/test_mcp_server.py::test_list_tools_includes_phase_8_parity_08 -x` passes).
- [ ] `pytest tests/test_metasound_authoring.py -x -q` is green — every tool returns `NyraToolResult`, dedup works, missing-symbol returns `err` cleanly, capitalisation-drift dual-probe works.
- [ ] Wave 0 symbol survey artifacts (`symbol-survey-metasound-{ue}.md`) committed for each shipped UE version.
- [ ] `08-08-VERIFICATION.md` operator-run: oscillator → output connection produces playable audio in UE 5.6 + at least one of {5.4, 5.5, 5.7}.
- [ ] Either Task 1.5 was skipped (builder subsystem reflected) OR `UNyraMetaSoundHelper` UCLASS landed and reflects from Python.

## Honest acknowledgments

- **THIS PLAN IS GLOSS.** Per CONTEXT.md SC#8 and the user's own framing — most game audio lives in Wwise/FMOD outside UE. PARITY-08 is the lowest-leverage plan in Phase 8. It's tier-2 and not on the LOCKED-09 mandatory list. It exists so the marketing-comparison table doesn't have a blank cell next to "Audio" — that's the entire claim.
- **`pending_manual_verification: true`** for the live audio-graph round-trip — Wave 0 + operator runbook required.
- **Smallest test surface in Phase 8** — three unit tests + one operator runbook entry. Right-sized for the leverage.
- **`UMetaSoundBuilderSubsystem` may not actually have the methods** assumed by Task 1's pseudo-API (`add_node`, `connect_pins`). Wave 0 (Task 0) confirms before Task 1 commits to the Python-only path.
- **A4 capitalisation drift** (`MetaSound` vs `Metasound`) is the most likely real-world failure mode. The dual-probe handles it.
- **If LOCKED-09's "≥2 of {05,06,07,08}" bar slips**, this plan is the first to drop — it's the intended bottom of the priority stack.
