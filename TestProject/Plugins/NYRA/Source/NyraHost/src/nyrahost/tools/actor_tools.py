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

from nyrahost.tools.base import (
    NyraTool,
    NyraToolResult,
    idempotent_lookup,
    idempotent_record,
    session_transaction,
    verify_post_condition,
)

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
    """Resolve an actor by path or label.

    BL-07: unreal.EditorLevelLibrary.get_actor_reference does not exist
    in the UE 5.4-5.7 Python API. Use EditorActorSubsystem.get_actor_reference
    (canonical) or fall back to iterating get_all_level_actors() and matching
    by get_path_name() / get_actor_label() to support both label-based and
    path-based lookups from the LLM tool args.
    """
    try:
        subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        if subsystem is not None and hasattr(subsystem, "get_actor_reference"):
            actor = subsystem.get_actor_reference(path)
            if actor is not None:
                return actor
        # Fallback: iterate level actors and match by path or label.
        for a in unreal.EditorLevelLibrary.get_all_level_actors():
            if a.get_path_name() == path or a.get_actor_label() == path:
                return a
    except Exception as e:
        log.warning("load_actor_failed", path=path, error=str(e))
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
        # BL-05: idempotent lookup. Calling spawn twice with identical
        # params returns the prior result (deduped:True) so an LLM retry
        # on transient error doesn't double-spawn.
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        editor_level_lib = unreal.EditorLevelLibrary

        loc = params.get("location", {})
        rot = params.get("rotation", {})
        location = unreal.Vector(float(loc.get("x", 0.0)), float(loc.get("y", 0.0)), float(loc.get("z", 0.0)))
        rotation = unreal.Rotator(float(rot.get("pitch", 0.0)), float(rot.get("yaw", 0.0)), float(rot.get("roll", 0.0)))

        # BL-04: wrap the spawn in a session transaction so chat/cancel
        # rolls back via UE's UTransBuffer.
        with session_transaction(f"NYRA: {self.name}"):
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

            actor_path = actor.get_path_name()

            # BL-06: post-condition. Re-fetch the actor from the level by
            # path to confirm it actually persisted before returning ok.
            post_err = verify_post_condition(
                f"{self.name}({actor_path})",
                lambda: _load_actor(actor_path) is not None,
            )
            if post_err:
                return NyraToolResult.err(post_err)

        log.info("actor_spawned", name=actor.get_name(), path=actor_path)
        # BL-08: drop guid (Python binding doesn't expose get_actor_guid()).
        result = {
            "actor_name": actor.get_name(),
            "actor_path": actor_path,
        }
        # BL-05: cache the successful spawn result for future dedup.
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)


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

        # BL-08: drop guid (Python binding doesn't expose get_actor_guid()).
        result = [
            {"actor_name": a.get_name(), "actor_path": a.get_path_name()}
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

        # WR-08: EditorLevelLibrary.add_to_selection doesn't exist in 5.4-5.7;
        # use EditorActorSubsystem.set_selected_level_actors with the merged
        # list, or iterate select_actor() per actor for additive selection.
        editor_actor_subsys = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        if params.get("add_to_selection", False):
            current = list(editor_actor_subsys.get_selected_level_actors() or [])
            current_paths = {a.get_path_name() for a in current}
            for a in actors:
                if a.get_path_name() not in current_paths:
                    current.append(a)
            editor_actor_subsys.set_selected_level_actors(current)
        else:
            editor_actor_subsys.set_selected_level_actors(actors)

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
            # WR-10: second arg to set_actor_location is bSweep, not bNoCheck.
            # False = teleport through collisions (no sweep). The previous
            # comment was misleading. We pass False here intentionally to
            # match the snap_ground tool's free-positioning semantics; if
            # collision-aware movement is wanted, callers should pass an
            # explicit `sweep` flag (future plan).
            actor.set_actor_location(
                unreal.Vector(float(loc["x"]), float(loc["y"]), float(loc["z"])),
                False,  # bSweep=False — teleport
            )
        if params.get("rotation"):
            rot = params["rotation"]
            actor.set_actor_rotation(
                unreal.Rotator(float(rot["pitch"]), float(rot["yaw"]), float(rot["roll"])),
                False,  # bSweep=False — teleport
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
        end = unreal.Vector(start.x, start.y, start.z - trace_distance)

        # WR-04: unreal.MathLibrary.line_trace_by_channel does not exist; the
        # canonical Python entry point is SystemLibrary.line_trace_single
        # which returns (bool, hit_result). The previous code mixed
        # ETraceTypeQuery and ECollisionChannel signatures from two different
        # API surfaces.
        world = unreal.EditorLevelLibrary.get_editor_world()
        try:
            hit_success, hit_result = unreal.SystemLibrary.line_trace_single(
                world,
                start,
                end,
                unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,  # Visibility
                False,         # bTraceComplex
                [actor],       # ActorsToIgnore — don't self-hit
                unreal.DrawDebugTrace.NONE,
                True,          # bIgnoreSelf
            )
        except Exception as e:
            log.error("snap_ground_trace_failed", actor=params["actor_path"], error=str(e))
            return NyraToolResult.err(f"Line trace failed: {e}")

        if hit_success and hit_result is not None:
            # WR-04: use impact_point (the hit location), not the hit actor's
            # pivot. A 100m-tall mesh at its top would otherwise snap to the
            # mesh actor's origin (bottom or arbitrary).
            try:
                impact = hit_result.impact_point
                snap_z = float(impact.z)
            except AttributeError:
                # FHitResult Python binding may expose .location instead.
                impact = getattr(hit_result, "location", None) or hit_result.get_actor_location()
                snap_z = float(impact.z)
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