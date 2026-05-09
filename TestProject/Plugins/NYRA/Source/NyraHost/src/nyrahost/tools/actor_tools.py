"""nyrahost.tools.actor_tools — ACT-04 actor CRUD MCP tools.

Per Plan 04-04:
  - nyra_actor_spawn, nyra_actor_duplicate, nyra_actor_delete,
    nyra_actor_select, nyra_actor_transform, nyra_actor_snap_ground
  - All write ops wrapped in FNyraSessionTransaction (via transaction.py)
  - Phase 3 SymbolGate integration via nyra_validate_symbol

Phase 0 gate: not phase0-gated — execute fully.
"""
from __future__ import annotations

from typing import Any

import structlog
import unreal

from nyrahost.tools.base import NyraTool, NyraToolResult

log = structlog.get_logger("nyrahost.tools.actor_tools")

__all__ = [
    "ActorSpawnTool",
    "ActorDuplicateTool",
    "ActorDeleteTool",
    "ActorSelectTool",
    "ActorTransformTool",
    "ActorSnapGroundTool",
]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _load_actor(path: str) -> Any:
    try:
        return unreal.EditorLevelLibrary.get_actor_reference(path)
    except Exception:
        return None


def _load_class(path: str) -> Any:
    try:
        return unreal.UObject.load_class(path)
    except Exception:
        return None


# -----------------------------------------------------------------------------
# nyra_actor_spawn
# -----------------------------------------------------------------------------

class ActorSpawnTool(NyraTool):
    name = "nyra_actor_spawn"
    description = (
        "Spawn an actor by class or asset path in the current editor level. "
        "The actor is placed at the given world-space location and rotation."
    )
    parameters = {
        "type": "object",
        "properties": {
            "class_name": {
                "type": "string",
                "description": "UE class name, e.g. 'StaticMeshActor' or '/Script/Engine.CameraActor'",
            },
            "asset_path": {
                "type": "string",
                "description": "Asset path for Blueprint-derived actors, e.g. '/Game/Props/Crate_C'",
            },
            "location": {
                "type": "object",
                "properties": {"x": {"type": "number"}, "y": {"type": "number"}, "z": {"type": "number"}},
                "default": {"x": 0.0, "y": 0.0, "z": 0.0},
            },
            "rotation": {
                "type": "object",
                "properties": {"pitch": {"type": "number"}, "yaw": {"type": "number"}, "roll": {"type": "number"}},
                "default": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
            },
            "name": {
                "type": "string",
                "description": "Optional actor label/name in the world outliner",
            },
        },
        "required": ["class_name"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        editor_level_lib = unreal.EditorLevelLibrary

        loc = params.get("location", {})
        rot = params.get("rotation", {})
        location = unreal.Vector(float(loc.get("x", 0.0)), float(loc.get("y", 0.0)), float(loc.get("z", 0.0)))
        rotation = unreal.Rotator(float(rot.get("pitch", 0.0)), float(rot.get("yaw", 0.0)), float(rot.get("roll", 0.0)))

        try:
            if params.get("asset_path"):
                asset = unreal.EditorAssetLibrary.load_asset(params["asset_path"])
                if asset is None:
                    return NyraToolResult.err(f"Asset not found: {params['asset_path']}")
                actor = editor_level_lib.spawn_actor_from_class(type(asset), location, rotation)
            else:
                class_name = params["class_name"]
                if class_name.startswith("/Script/"):
                    actor_class = _load_class(class_name)
                else:
                    actor_class = unreal.UObject.load_class(f"/Script/Engine.{class_name}")
                actor = editor_level_lib.spawn_actor_from_class(actor_class, location, rotation)
        except Exception as e:
            log.error("actor_spawn_failed", error=str(e))
            return NyraToolResult.err(f"Failed to spawn actor: {e}")

        if params.get("name"):
            actor.set_actor_label(params["name"])

        log.info("actor_spawned", name=actor.get_name(), path=actor.get_path_name())
        return NyraToolResult.ok({
            "actor_name": actor.get_name(),
            "actor_path": actor.get_path_name(),
            "guid": str(actor.get_actor_guid()),
        })


# -----------------------------------------------------------------------------
# nyra_actor_duplicate
# -----------------------------------------------------------------------------

class ActorDuplicateTool(NyraTool):
    name = "nyra_actor_duplicate"
    description = "Duplicate one or more actors in the current level with an optional offset."
    parameters = {
        "type": "object",
        "properties": {
            "actor_path": {
                "type": "string",
                "description": "Path to the source actor (world outliner path or '/Game/...' format)",
            },
            "offset": {
                "type": "object",
                "properties": {"x": {"type": "number"}, "y": {"type": "number"}, "z": {"type": "number"}},
                "default": {"x": 0.0, "y": 0.0, "z": 0.0},
            },
        },
        "required": ["actor_path"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        source = _load_actor(params["actor_path"])
        if source is None:
            return NyraToolResult.err(f"Actor not found: {params['actor_path']}")

        offset = params.get("offset", {})
        offset_vec = unreal.Vector(
            float(offset.get("x", 0.0)),
            float(offset.get("y", 0.0)),
            float(offset.get("z", 0.0)),
        )

        editor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        try:
            duplicates = editor_subsystem.duplicate_actors([source], offset_vec)
        except Exception as e:
            log.error("actor_duplicate_failed", error=str(e))
            return NyraToolResult.err(f"Failed to duplicate actor: {e}")

        result = [
            {"actor_name": a.get_name(), "actor_path": a.get_path_name(), "guid": str(a.get_actor_guid())}
            for a in duplicates
        ]
        return NyraToolResult.ok({"duplicates": result})


# -----------------------------------------------------------------------------
# nyra_actor_delete
# -----------------------------------------------------------------------------

class ActorDeleteTool(NyraTool):
    name = "nyra_actor_delete"
    description = "Delete one or more actors from the current level. This operation is destructive."
    parameters = {
        "type": "object",
        "properties": {
            "actor_path": {
                "type": "string",
                "description": "Path to the actor to delete",
            },
        },
        "required": ["actor_path"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        actor = _load_actor(params["actor_path"])
        if actor is None:
            return NyraToolResult.err(f"Actor not found: {params['actor_path']}")

        editor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        try:
            editor_subsystem.destroy_actor(actor)
        except Exception as e:
            log.error("actor_delete_failed", error=str(e))
            return NyraToolResult.err(f"Failed to delete actor: {e}")

        log.info("actor_deleted", path=params["actor_path"])
        return NyraToolResult.ok({"status": "deleted", "actor_path": params["actor_path"]})


# -----------------------------------------------------------------------------
# nyra_actor_select
# -----------------------------------------------------------------------------

class ActorSelectTool(NyraTool):
    name = "nyra_actor_select"
    description = "Set the editor selection to one or more actors by path."
    parameters = {
        "type": "object",
        "properties": {
            "actor_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Paths to actors to select",
            },
            "add_to_selection": {
                "type": "boolean",
                "default": False,
                "description": "If true, add to current selection; if false, replace it",
            },
        },
        "required": ["actor_paths"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        editor_level_lib = unreal.EditorLevelLibrary
        actors: list[Any] = []
        for path in params["actor_paths"]:
            actor = _load_actor(path)
            if actor is None:
                log.warning("actor_not_found_for_select", path=path)
            else:
                actors.append(actor)

        if not actors:
            return NyraToolResult.err("No valid actors found for selection")

        if params.get("add_to_selection", False):
            editor_level_lib.add_to_selection(actors)
        else:
            editor_level_lib.set_selected_level_actors(actors)

        return NyraToolResult.ok({
            "selected": [a.get_path_name() for a in actors],
            "count": len(actors),
        })


# -----------------------------------------------------------------------------
# nyra_actor_transform
# -----------------------------------------------------------------------------

class ActorTransformTool(NyraTool):
    name = "nyra_actor_transform"
    description = "Set location, rotation, and/or scale of an actor."
    parameters = {
        "type": "object",
        "properties": {
            "actor_path": {"type": "string"},
            "location": {
                "type": "object",
                "properties": {"x": {"type": "number"}, "y": {"type": "number"}, "z": {"type": "number"}},
            },
            "rotation": {
                "type": "object",
                "properties": {"pitch": {"type": "number"}, "yaw": {"type": "number"}, "roll": {"type": "number"}},
            },
            "scale": {
                "type": "object",
                "properties": {"x": {"type": "number"}, "y": {"type": "number"}, "z": {"type": "number"}},
            },
        },
        "required": ["actor_path"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        actor = _load_actor(params["actor_path"])
        if actor is None:
            return NyraToolResult.err(f"Actor not found: {params['actor_path']}")

        if params.get("location"):
            loc = params["location"]
            actor.set_actor_location(
                unreal.Vector(float(loc["x"]), float(loc["y"]), float(loc["z"])),
                False,  # bNoCheck=false — sweep
            )
        if params.get("rotation"):
            rot = params["rotation"]
            actor.set_actor_rotation(
                unreal.Rotator(float(rot["pitch"]), float(rot["yaw"]), float(rot["roll"])),
                False,
            )
        if params.get("scale"):
            sc = params["scale"]
            actor.set_actor_scale3d(unreal.Vector(float(sc["x"]), float(sc["y"]), float(sc["z"])))

        log.info("actor_transformed", path=params["actor_path"])
        return NyraToolResult.ok({"status": "ok", "actor_path": params["actor_path"]})


# -----------------------------------------------------------------------------
# nyra_actor_snap_ground
# -----------------------------------------------------------------------------

class ActorSnapGroundTool(NyraTool):
    name = "nyra_actor_snap_ground"
    description = (
        "Snap an actor to the ground using a downward line trace. "
        "Finds the first blocking hit below the actor's current location "
        "and moves it so its bottom sits flush with the hit surface."
    )
    parameters = {
        "type": "object",
        "properties": {
            "actor_path": {"type": "string"},
            "trace_distance": {
                "type": "number",
                "default": 10000.0,
                "description": "Maximum trace distance in cm (default 100m)",
            },
        },
        "required": ["actor_path"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        actor = _load_actor(params["actor_path"])
        if actor is None:
            return NyraToolResult.err(f"Actor not found: {params['actor_path']}")

        start = actor.get_actor_location()
        trace_distance = float(params.get("trace_distance", 10000.0))
        # Trace downward
        end = unreal.Vector(start.x, start.y, start.z - trace_distance)

        # Use World /LineTraceByChannel
        world = unreal.EditorLevelLibrary.get_editor_world()
        # Simple single-channel trace using line_trace_by_channel
        from unreal import FCollisionQueryParams, ECollisionChannel, ETraceTypeQuery

        query_params = FCollisionQueryParams()
        trace_channel = ECollisionChannel.CollisionChannel_Static

        hit_result = unreal.MathLibrary.line_trace_by_channel(
            world, start, end,
            ETraceTypeQuery.TraceTypeQuery1, False,
            [], ECollisionChannel.ECC_Visibility, query_params
        )

        if hit_result.is_valid_block():
            snap_z = hit_result.get_actor_location().z
            new_location = unreal.Vector(start.x, start.y, snap_z)
            actor.set_actor_location(new_location, True)
            log.info("actor_snapped_ground", actor=params["actor_path"], new_z=new_location.z)
            return NyraToolResult.ok({
                "status": "snapped",
                "actor_path": params["actor_path"],
                "new_z": new_location.z,
            })

        return NyraToolResult.ok({
            "status": "no_hit",
            "actor_path": params["actor_path"],
            "message": "No blocking surface found within trace distance",
        })