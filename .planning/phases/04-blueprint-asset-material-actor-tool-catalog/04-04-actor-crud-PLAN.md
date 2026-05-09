---
phase: 4
plan: 04-04
type: execute
wave: 1
autonomous: true
depends_on: []
blocking_preconditions: []
---

# Plan 04-04: Actor CRUD MCP Tools

## Current Status

No actor CRUD tools exist in NyraHost. `UEditorActorSubsystem` and `EditorLevelLibrary` are available via the `unreal` Python binding. This plan builds all Actor operations from ACT-04.

## Objectives

Implement the full Actor CRUD suite: `nyra_actor_spawn`, `nyra_actor_duplicate`, `nyra_actor_delete`, `nyra_actor_select`, `nyra_actor_transform`, and `nyra_actor_snap_ground`.

## What Will Be Built

### `NyraHost/nyra_host/tools/actor_tools.py`

```python
from .base import NyraTool, NyraToolResult
import unreal

class ActorSpawnTool(NyraTool):
    name = "nyra_actor_spawn"
    description = "Spawn an actor by class or asset path in the current editor level."
    parameters = {
        "type": "object",
        "properties": {
            "class_name": {
                "type": "string",
                "description": "UE class name, e.g. 'StaticMeshActor' or '/Script/Engine.CameraActor'"
            },
            "asset_path": {
                "type": "string",
                "description": "Asset path for blueprint-derived actors, e.g. '/Game/Props/Crate_C'"
            },
            "location": {"type": "object", "properties": {"x": 0.0, "y": 0.0, "z": 0.0}},
            "rotation": {"type": "object", "properties": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0}},
            "name": {"type": "string", "description": "Optional actor label/name in world outliner"}
        },
        "required": ["class_name"]
    }

    def execute(self, params: dict) -> NyraToolResult:
        editor_level_lib = unreal.EditorLevelLibrary
        actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

        if params.get("asset_path"):
            actor_class = unreal.EditorAssetLibrary.load_asset(params["asset_path"])
        else:
            # Resolve class name to UClass
            actor_class = unreal.UObject.load_system_class(params["class_name"])

        transform = unreal.Transform(
            unreal.Vector(params["location"]["x"], params["location"]["y"], params["location"]["z"]),
            unreal.Rotator(params["rotation"]["pitch"], params["rotation"]["yaw"], params["rotation"]["roll"]),
            unreal.Vector(1.0, 1.0, 1.0)
        )
        actor = editor_level_lib.spawn_actor_from_class(actor_class, transform)

        if params.get("name"):
            actor.set_actor_label(params["name"])

        return NyraToolResult(data={
            "actor_name": actor.get_name(),
            "actor_path": actor.get_path_name(),
            "guid": str(actor.get_actor_guid())
        })
```

### Additional Actor Tools

```python
class ActorDuplicateTool(NyraTool):
    name = "nyra_actor_duplicate"
    # Uses EditorActorSubsystem.duplicate_actors(source_actors, offset_location)
    ...

class ActorDeleteTool(NyraTool):
    name = "nyra_actor_delete"
    # Uses EditorActorSubsystem.destroy_actor(actor)
    ...

class ActorSelectTool(NyraTool):
    name = "nyra_actor_select"
    # Uses EditorLevelLibrary.set_selected_level_actors([actor])
    ...

class ActorTransformTool(NyraTool):
    name = "nyra_actor_transform"
    description = "Set location, rotation, and/or scale of an actor."
    parameters = {
        "properties": {
            "actor_path": {"type": "string"},
            "location": {"type": "object"},
            "rotation": {"type": "object"},
            "scale": {"type": "object"}
        }
    }
    def execute(self, params):
        actor = unreal.EditorLevelLibrary.get_actor_reference(params["actor_path"])
        if params.get("location"):
            actor.set_actor_location(unreal.Vector(**params["location"]), False)
        if params.get("rotation"):
            actor.set_actor_rotation(unreal.Rotator(**params["rotation"]), False)
        if params.get("scale"):
            actor.set_actor_scale3d(unreal.Vector(**params["scale"]))
        return NyraToolResult(data={"status": "ok"})
    ...

class ActorSnapGroundTool(NyraTool):
    name = "nyra_actor_snap_ground"
    description = "Snap an actor to the ground using a downward line trace."
    ...
```

### Tool Registration

All tools registered in `mcp_server.py`:
```python
from .tools.actor_tools import (
    ActorSpawnTool, ActorDuplicateTool, ActorDeleteTool,
    ActorSelectTool, ActorTransformTool, ActorSnapGroundTool
)

def register_all_tools(server: StdioServer) -> None:
    server.add_tool(ActorSpawnTool())
    server.add_tool(ActorDuplicateTool())
    server.add_tool(ActorDeleteTool())
    server.add_tool(ActorSelectTool())
    server.add_tool(ActorTransformTool())
    server.add_tool(ActorSnapGroundTool())
```

## Transaction Discipline

All write tools (spawn, duplicate, delete, transform, snap_ground) call `FNyraSessionTransaction::Begin` + `actor.Modify()` before mutation. Delete operations set `risk: destructive` in the permission gate.

## Phase 3 SymbolGate Integration

`nyra_validate_symbol` is called before any `spawn` operation where an asset path is provided — validates the Blueprint class exists in the user's UE version.

## Acceptance Criteria

- [ ] `nyra_actor_spawn class_name="StaticMeshActor"` places an actor at the origin
- [ ] `nyra_actor_transform actor_path="StaticMeshActor_0" location={x:100,y:0,z:200}` moves the actor
- [ ] `nyra_actor_delete` removes the actor from the level
- [ ] `nyra_actor_snap_ground` correctly snaps an actor to the first blocking hit below it
- [ ] All write ops wrapped in `FNyraSessionTransaction` — Ctrl+Z rolls back
- [ ] Phase 1/2 commands unchanged

## File Manifest

| File | Action |
|------|--------|
| `NyraHost/nyra_host/tools/actor_tools.py` | Create |
| `NyraHost/nyra_host/mcp_server.py` | Edit (register new tools) |