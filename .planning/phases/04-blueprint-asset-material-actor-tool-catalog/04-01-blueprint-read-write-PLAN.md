---
phase: 4
plan: 04-01
type: execute
wave: 2
autonomous: true
depends_on: [03]
blocking_preconditions:
  - Phase 3 SymbolGate must be shipped (03-04) — `nyra_validate_symbol` is the pre-execution gate for any UE API touch
  - NyraHost MCP server must be running (Phase 1/2 shell exists)
---

# Plan 04-01: Blueprint Read/Write MCP Tools

## Current Status

No Blueprint MCP tools exist in NyraHost. Phase 4 delivers the core Blueprint read/write surface that ACT-01 requires. This plan covers Python-first APIs with C++ fallbacks for gaps in the `unreal` Python binding.

## Objectives

Implement `nyra_blueprint_read` and `nyra_blueprint_write` MCP tools that expose Blueprint graph topology as structured JSON and accept graph mutations (add/remove/reconnect nodes, set variable defaults, compile).

## What Will Be Built

### `NyraHost/nyra_host/tools/blueprint_tools.py`

```python
from .base import NyraTool, NyraToolResult
import unreal

class BlueprintReadTool(NyraTool):
    name = "nyra_blueprint_read"
    description = "Read a Blueprint's node graph, variables, and event graphs as structured JSON."
    parameters = {
        "type": "object",
        "properties": {
            "asset_path": {
                "type": "string",
                "description": "Full UE asset path, e.g. '/Game/Characters/Hero_BP.Hero_BP_C'"
            },
            "include_node_positions": {
                "type": "boolean",
                "default": True,
                "description": "Include node X/Y coordinates for visual layout"
            }
        },
        "required": ["asset_path"]
    }

    def execute(self, params: dict) -> NyraToolResult:
        blueprint = unreal.EditorAssetLibrary.load_asset(params["asset_path"])
        if not isinstance(blueprint, unreal.Blueprint):
            return NyraToolResult(error=f"Asset {params['asset_path']} is not a Blueprint")
        return NyraToolResult(
            data=self._blueprint_to_json(blueprint, params.get("include_node_positions", True))
        )

    def _blueprint_to_json(self, bp: unreal.Blueprint, include_positions: bool) -> dict:
        # Returns: {asset_path, class_name, functions[], events[], variables[], graph_nodes[]}
        # Node entry: {guid, type, name, pins[], pos_x, pos_y} if include_positions
        ...
```

### `nyra_blueprint_write`

```python
class BlueprintWriteTool(NyraTool):
    name = "nyra_blueprint_write"
    description = "Mutate a Blueprint: add nodes, remove nodes, reconnect pins, set defaults, recompile."
    parameters = {
        "type": "object",
        "properties": {
            "asset_path": {"type": "string"},
            "mutation": {
                "type": "object",
                "properties": {
                    "add_nodes": [{
                        "parent_graph": "string",
                        "node_class": "string",  # e.g. "K2Node_VariableSet"
                        "node_pos": {"x": 0, "y": 0},
                        "pin_values": {}  # pin_name -> value
                    }],
                    "remove_nodes": [{"guid": "string"}],
                    "reconnect_pins": [{
                        "from_node_guid": "string",
                        "from_pin": "string",
                        "to_node_guid": "string",
                        "to_pin": "string"
                    }],
                    "set_variable_defaults": {  # variable_name -> new_default_value
                        "type": "object"
                    }
                }
            },
            "recompile": {"type": "boolean", "default": True},
            "dry_run": {"type": "boolean", "default": False}
        },
        "required": ["asset_path", "mutation"]
    }

    def execute(self, params: dict) -> NyraToolResult:
        # 1. Begin FScopedTransaction (Phase 2 session super-transaction active)
        # 2. Validate all target node GUIDs exist
        # 3. Apply mutations via FKismetCompilerContext
        # 4. If recompile=True: call FBlueprintEditorUtils::RebuildBlueprint
        # 5. Return {nodes_added, nodes_removed, pins_reconnected, compile_result}
        ...
```

### Registration in `NyraHost/nyra_host/mcp_server.py`

```python
from .tools.blueprint_tools import BlueprintReadTool, BlueprintWriteTool

def register_all_tools(server: StdioServer) -> None:
    server.add_tool(BlueprintReadTool())
    server.add_tool(BlueprintWriteTool())
    # ...
```

## C++ Fallback for Node Position Gap

If `UK2Node::NodePosX/Y` is not accessible via Python `unreal` binding (known gap in UE 5.4–5.7 Python API), add:

```cpp
// NyraEditor/Source/NyraEditor/Private/NyraBlueprintReader.cpp
// Exposes node positions via UScriptStruct JSON serialization
// Accessible from Python via FPythonBinding
```

Guarded with `NYRA_UE_AT_LEAST(5, 4)` shim. Added only if Wave 1 testing confirms the gap.

## Phase 2 Console Command (Module-Superset)

`Nyra.Dev.ToolCatalogCanary 1` (added in 04-05) calls `nyra_blueprint_read` with mock data and verifies JSON structure.

## Dependencies

- Phase 3 SymbolGate (03-04): `nyra_validate_symbol` called before any `blueprint_write` — validates target Blueprint class, referenced parent classes, and node types
- Phase 2 session super-transaction (CHAT-03 D-10): `FNyraSessionTransaction::Begin` wraps all write operations

## Acceptance Criteria

- [ ] `nyra_blueprint_read` returns valid JSON with functions, events, variables, and node list
- [ ] `nyra_blueprint_read /Game/Path/Some_BP` where Some_BP does not exist returns error code `-32010 asset_not_found`
- [ ] `nyra_blueprint_write` adds a node, reconnects one pin, sets one variable default, recompiles, and returns success
- [ ] `nyra_blueprint_write` with invalid mutation (bad GUID) returns `-32011 node_not_found` and rolls back
- [ ] `nyra_validate_symbol` is called automatically before any write targeting an unknown Blueprint class
- [ ] Module-superset: Phase 1 `Nyra.Dev.RoundTripBench` + Phase 2 `Nyra.Dev.SubscriptionBridgeCanary` unchanged

## File Manifest

| File | Action |
|------|--------|
| `NyraHost/nyra_host/tools/blueprint_tools.py` | Create |
| `NyraHost/nyra_host/mcp_server.py` | Edit (add tool registrations) |
| `NyraEditor/Source/NyraEditor/Private/NyraBlueprintReader.cpp` | Create (only if Python gap confirmed) |
| `NyraEditor/Source/NyraEditor/Public/NyraBlueprintReader.h` | Create (only if Python gap confirmed) |