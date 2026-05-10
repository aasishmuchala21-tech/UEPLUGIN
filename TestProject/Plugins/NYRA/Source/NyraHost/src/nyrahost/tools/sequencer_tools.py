"""nyrahost.tools.sequencer_tools — SCENE-02 Sequencer MCP tools.

Phase 7 Wave 0: ULevelSequence creation, CineCamera binding, keyframe authoring, NL shot blocking.
Per ROADMAP SC#2: SCENE-02 Sequencer automation.
"""
from __future__ import annotations

import math

import structlog
from typing import Any, Optional

try:
    import unreal
    HAS_UNREAL = True
except ImportError:
    HAS_UNREAL = False


# Industry-standard 35mm sensor (Super 35 / full-frame photographic) horizontal
# width in mm. Used by _fov_degrees_to_focal_length_mm to convert from a
# horizontal FOV in degrees to a focal length in millimetres so the value can
# be fed to UE's add_keyframe_absolute_focal_length API.
_DEFAULT_SENSOR_WIDTH_MM = 36.0


def _fov_degrees_to_focal_length_mm(
    fov_degrees: float, sensor_width_mm: float = _DEFAULT_SENSOR_WIDTH_MM,
) -> float:
    """Convert a horizontal FOV (degrees) to a focal length (mm).

    Uses the standard pinhole-camera relation
    ``focal_mm = (sensor_width / 2) / tan(fov_deg * pi / 360)``. UE's
    Sequencer focal-length keyframe API expects millimetres on a CineCamera
    component; the LLM emits horizontal FOV in degrees, so every callsite
    that wants to keyframe FOV must convert first.
    """
    fov = max(min(float(fov_degrees), 179.0), 1.0)  # avoid tan(90 deg)
    half_rad = fov * math.pi / 360.0
    return (sensor_width_mm / 2.0) / math.tan(half_rad)

from nyrahost.tools.base import NyraTool, NyraToolResult
from nyrahost.tools.video_llm_parser import CameraMoveType, ShotBlock, VideoReferenceParams

log = structlog.get_logger("nyrahost.tools.sequencer_tools")

__all__ = [
    "SequencerCreateTool", "SequencerAddCameraTool",
    "SequencerSetKeyframeTool", "SequencerAuthorShotTool",
]


class SequencerToolMixin:
    """Mix-in providing Unreal Sequencer scripting API helpers."""

    def _create_level_sequence(self, sequence_name: str) -> Any:
        """Create a new ULevelSequence in the current level."""
        if not HAS_UNREAL:
            return None
        return unreal.LevelSequenceEditorBlueprintLibrary.create_level_sequence(sequence_name)

    def _bind_camera_to_sequence(self, sequence: Any, camera_actor: Any) -> Any:
        """Bind a CineCamera or CameraActor to the level sequence."""
        if not HAS_UNREAL:
            return None
        subsystem = unreal.get_editor_subsystem(unreal.LevelSequenceEditorSubsystem)
        return subsystem.add_possible_binding_to_sequence(sequence, camera_actor)

    def _set_transform_keyframe(
        self,
        sequence: Any,
        binding: Any,
        frame_number: int,
        location: tuple[float, float, float],
        rotation: tuple[float, float, float],
        scale: tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> None:
        """Set a transform keyframe (location + rotation) on a binding."""
        if not HAS_UNREAL:
            return
        pos = unreal.Vector(location[0], location[1], location[2])
        rot = unreal.Rotator(rotation[0], rotation[1], rotation[2])
        sc = unreal.Vector(scale[0], scale[1], scale[2])
        unreal.LevelSequenceEditorBlueprintLibrary.add_keyframe_absolute_transform(
            binding, sequence, pos, rot, sc, float(frame_number)
        )

    def _set_camera_fov_keyframe(
        self, sequence: Any, binding: Any, frame_number: int, fov_degrees: float,
    ) -> None:
        """Set a focal-length keyframe on a CineCameraComponent.

        Input is horizontal FOV in degrees (LLM-emitted, 35mm-equivalent).
        UE's Sequencer scripting API exposes
        ``add_keyframe_absolute_focal_length`` which takes millimetres on a
        CineCameraComponent's current_focal_length channel; convert before
        the call. (There is no add_keyframe_absolute_focal_focus -- the
        previous name was a typo and would AttributeError at runtime.)
        """
        if not HAS_UNREAL:
            return
        focal_mm = _fov_degrees_to_focal_length_mm(fov_degrees)
        unreal.LevelSequenceEditorBlueprintLibrary.add_keyframe_absolute_focal_length(
            binding, sequence, focal_mm, float(frame_number)
        )

    def _set_light_intensity_keyframe(
        self, sequence: Any, binding: Any, frame_number: int, intensity: float,
    ) -> None:
        """Set a light intensity keyframe."""
        if not HAS_UNREAL:
            return
        unreal.LevelSequenceEditorBlueprintLibrary.add_keyframe_absolute_light_intensity(
                binding, sequence, intensity, float(frame_number))

    def _set_light_color_keyframe(
        self, sequence: Any, binding: Any, frame_number: int,
        color_rgb: tuple[float, float, float],
    ) -> None:
        """Set a light color keyframe."""
        if not HAS_UNREAL:
            return
        color = unreal.LinearColor(color_rgb[0], color_rgb[1], color_rgb[2], 1.0)
        unreal.LevelSequenceEditorBlueprintLibrary.add_keyframe_absolute_light_color(
            binding, sequence, color, float(frame_number))


class SequencerCreateTool(SequencerToolMixin, NyraTool):
    """Create a new ULevelSequence in the current editor level."""
    name = "nyra_sequencer_create"
    description = (
        "Create a new ULevelSequence in the current editor level. "
        "The sequence is ready to receive CineCameras, lights, and shot blocks."
    )
    parameters = {
        "type": "object",
        "properties": {
            "sequence_name": {
                "type": "string",
                "description": "Name for the level sequence asset (e.g. 'Shot_001')",
            },
            "duration_seconds": {
                "type": "number",
                "default": 10.0,
                "description": "Duration in seconds (default 10s for demo clips)",
            },
        },
        "required": ["sequence_name"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        seq = self._create_level_sequence(params["sequence_name"])
        if seq is None:
            return NyraToolResult.err(f"[-32040] Failed to create level sequence '{params['sequence_name']}'")
        log.info("sequencer_created", name=params["sequence_name"], path=seq.get_path_name())
        return NyraToolResult.ok({
            "sequence_name": params["sequence_name"],
            "sequence_path": seq.get_path_name(),
            "duration_seconds": params.get("duration_seconds", 10.0),
            "message": f"Level sequence '{params['sequence_name']}' created",
        })


class SequencerAddCameraTool(SequencerToolMixin, NyraTool):
    """Add a CineCamera actor to a level sequence and bind it."""
    name = "nyra_sequencer_add_camera"
    description = (
        "Add a CineCamera actor to a level sequence and bind it. "
        "The camera is placed at world origin by default; use nyra_sequencer_set_keyframe to position it."
    )
    parameters = {
        "type": "object",
        "properties": {
            "sequence_path": {"type": "string", "description": "Path to the ULevelSequence asset"},
            "camera_name": {
                "type": "string",
                "default": "NYRA_SequencerCam",
                "description": "Label for the camera actor in the World Outliner",
            },
            "location": {
                "type": "object",
                "properties": {"x": {"type": "number"}, "y": {"type": "number"}, "z": {"type": "number"}},
                "default": {"x": 0.0, "y": 0.0, "z": 100.0},
            },
            "fov": {"type": "number", "default": 35.0, "description": "Horizontal FOV in degrees (35mm equivalent)"},
            "focus_distance": {"type": "number", "default": 3.0, "description": "Focus distance in meters"},
        },
        "required": ["sequence_path"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        if not HAS_UNREAL:
            return NyraToolResult.err("[-32001] Unreal module not available")
        from nyrahost.tools.actor_tools import ActorSpawnTool
        camera_tool = ActorSpawnTool()
        spawn_result = camera_tool.execute({
            "class_name": "CineCameraActor",
            "name": params.get("camera_name", "NYRA_SequencerCam"),
            "location": params.get("location", {"x": 0.0, "y": 0.0, "z": 100.0}),
        })
        if not spawn_result.is_ok:
            return NyraToolResult.err(f"Failed to spawn CineCamera: {spawn_result.error}")
        seq = unreal.EditorAssetLibrary.load_asset(params["sequence_path"])
        if seq is None:
            return NyraToolResult.err(f"Level sequence not found: {params['sequence_path']}")
        # LevelSequenceEditorSubsystem.add_possible_binding_to_sequence requires a
        # UObject Actor, NOT a path string. ActorSpawnTool returns actor_path as
        # a string identifier; resolve it back to the actor object before
        # binding. (In the no-unreal test path this branch is unreachable
        # because we returned early above; operator wiring inside UE editor
        # resolves the path to the spawned CineCameraActor.)
        actor_path = spawn_result.data["actor_path"]
        actor_obj = unreal.EditorAssetLibrary.load_asset(actor_path)
        if actor_obj is None:
            return NyraToolResult.err(
                f"Failed to resolve spawned camera actor at path: {actor_path}"
            )
        binding = self._bind_camera_to_sequence(seq, actor_obj)
        if binding is None:
            return NyraToolResult.err("Failed to bind camera to sequence")
        log.info("camera_added_to_sequence",
                 camera=spawn_result.data["actor_name"], sequence=params["sequence_path"])
        return NyraToolResult.ok({
            "camera_actor_name": spawn_result.data["actor_name"],
            "camera_actor_path": spawn_result.data["actor_path"],
            "camera_actor_guid": spawn_result.data["guid"],
            "sequence_path": params["sequence_path"],
            "fov": params.get("fov", 35.0),
            "focus_distance_m": params.get("focus_distance", 3.0),
            "message": f"CineCamera '{spawn_result.data['actor_name']}' added and bound to sequence",
        })


class SequencerSetKeyframeTool(SequencerToolMixin, NyraTool):
    """Set a keyframe on a CineCamera or light in a level sequence."""
    name = "nyra_sequencer_set_keyframe"
    description = (
        "Set a keyframe on a CineCamera or light in a level sequence. "
        "Time is specified in seconds (24fps assumed)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "sequence_path": {"type": "string"},
            "binding_path": {"type": "string"},
            "time_seconds": {"type": "number", "description": "Time in seconds"},
            "transform": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "number"},
                            "y": {"type": "number"},
                            "z": {"type": "number"},
                        },
                        "required": ["x", "y", "z"],
                    },
                    "rotation": {
                        "type": "object",
                        "properties": {
                            "pitch": {"type": "number"},
                            "yaw": {"type": "number"},
                            "roll": {"type": "number"},
                        },
                        "required": ["pitch", "yaw", "roll"],
                    },
                },
            },
            "fov_degrees": {"type": "number"},
            "focus_distance_m": {"type": "number"},
            "light_intensity": {"type": "number"},
            "light_color": {"type": "array", "items": {"type": "number"}, "description": "RGB 0-1"},
        },
        "required": ["sequence_path", "binding_path", "time_seconds"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        if not HAS_UNREAL:
            return NyraToolResult.err("[-32001] Unreal module not available")
        seq = unreal.EditorAssetLibrary.load_asset(params["sequence_path"])
        if seq is None:
            return NyraToolResult.err(f"Level sequence not found: {params['sequence_path']}")
        binding = self._find_binding_for_actor(seq, params["binding_path"])
        if binding is None:
            return NyraToolResult.err(f"Actor not bound to sequence: {params['binding_path']}")
        frame = int(min(max(params["time_seconds"], 0) * 24.0, 86400))  # clamp to 1hr max
        # WR-05: explicit "is not None" so a legitimate value of 0 (e.g. dim
        # a light to 0 over time, set a 0 deg FOV adjustment) is not silently
        # treated as "skip this channel".
        if params.get("transform") is not None:
            t = params["transform"]
            loc = (t["location"]["x"], t["location"]["y"], t["location"]["z"])
            rot = (t["rotation"]["pitch"], t["rotation"]["yaw"], t["rotation"]["roll"])
            self._set_transform_keyframe(seq, binding, frame, loc, rot)
        if params.get("fov_degrees") is not None:
            self._set_camera_fov_keyframe(seq, binding, frame, params["fov_degrees"])
        if params.get("light_intensity") is not None:
            self._set_light_intensity_keyframe(seq, binding, frame, params["light_intensity"])
        if params.get("light_color") is not None:
            self._set_light_color_keyframe(seq, binding, frame, tuple(params["light_color"]))
        log.info("keyframe_set", binding=params["binding_path"],
                 time_s=params["time_seconds"], frame=frame)
        return NyraToolResult.ok({
            "status": "keyframe_set",
            "sequence_path": params["sequence_path"],
            "binding_path": params["binding_path"],
            "time_seconds": params["time_seconds"],
            "frame": frame,
        })

    def _find_binding_for_actor(self, sequence: Any, actor_path: str) -> Any:
        """Find the movie scene binding for an actor in the sequence."""
        if not HAS_UNREAL:
            return None
        editor = unreal.get_editor_subsystem(unreal.LevelSequenceEditorSubsystem)
        bindings = editor.get_possible_bindings(sequence)
        for binding in bindings:
            if binding.get_name() == actor_path or actor_path in binding.get_name():
                return binding
        return None


class SequencerAuthorShotTool(SequencerToolMixin, NyraTool):
    """Author a shot block from NL or VideoReferenceParams."""
    name = "nyra_sequencer_author_shot"
    description = (
        "Author a shot block from natural language or VideoReferenceParams. "
        "Parses NL description ('slow push-in, then cut wide') and converts to keyframes."
    )
    parameters = {
        "type": "object",
        "properties": {
            "sequence_path": {"type": "string"},
            "binding_path": {"type": "string"},
            "video_reference_json": {"type": "string", "description": "JSON string of VideoReferenceParams from video analysis"},
            "nl_description": {"type": "string", "description": "Natural language shot description"},
            "duration_seconds": {"type": "number", "default": 5.0},
            "start_time_seconds": {"type": "number", "default": 0.0},
        },
        "required": ["sequence_path", "binding_path"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        if not HAS_UNREAL:
            return NyraToolResult.err("[-32001] Unreal module not available")
        import json
        seq = unreal.EditorAssetLibrary.load_asset(params["sequence_path"])
        if seq is None:
            return NyraToolResult.err(f"Level sequence not found: {params['sequence_path']}")
        binding = self._find_binding_for_actor(seq, params["binding_path"])
        if binding is None:
            return NyraToolResult.err(f"Actor not bound to sequence: {params['binding_path']}")
        duration = params.get("duration_seconds", 5.0)
        start = params.get("start_time_seconds", 0.0)
        end = start + duration
        if params.get("video_reference_json"):
            ref = VideoReferenceParams.from_json(params["video_reference_json"])
            return self._author_from_video_reference(seq, binding, ref, start, end, params)
        elif params.get("nl_description"):
            return self._author_from_nl(seq, binding, params["nl_description"], start, end, params)
        else:
            return NyraToolResult.err("[-32030] Either video_reference_json or nl_description required")

    def _author_from_video_reference(
        self, seq: Any, binding: Any, ref: VideoReferenceParams,
        start: float, end: float, params: dict,
    ) -> NyraToolResult:
        """Convert VideoReferenceParams to keyframes."""
        for shot in ref.shot_blocks:
            if not shot.user_confirmed and shot.camera_move_type == CameraMoveType.UNKNOWN:
                log.warning("shot_not_confirmed", shot_id=shot.shot_id)
                continue
            pattern = self._camera_move_to_keyframe_pattern(shot, start, end)
            for keyframe in pattern:
                frame = int(min(max(keyframe["time"], 0) * 24.0, 86400))
                self._set_transform_keyframe(seq, binding, frame, keyframe["location"], keyframe["rotation"])
                if keyframe.get("fov"):
                    self._set_camera_fov_keyframe(seq, binding, frame, keyframe["fov"])
        return NyraToolResult.ok({
            "status": "shot_authored", "video_reference": True,
            "shot_count": len(ref.shot_blocks), "start_time": start, "end_time": end,
            "camera_move": ref.camera_move_type.value,
        })

    def _author_from_nl(
        self, seq: Any, binding: Any, nl_desc: str,
        start: float, end: float, params: dict,
    ) -> NyraToolResult:
        """Parse NL shot description and convert to keyframes."""
        desc = nl_desc.lower()
        camera_move = CameraMoveType.UNKNOWN
        keyframes = []
        if "push-in" in desc or "dolly in" in desc or "move in" in desc:
            camera_move = CameraMoveType.DOLLY
            keyframes = [
                {"time": start, "location": (0, 0, 100), "rotation": (0, 0, 0)},
                {"time": end, "location": (0, 0, 50), "rotation": (0, 0, 0)},
            ]
        elif "cut wide" in desc or "pull back" in desc or "dolly out" in desc:
            camera_move = CameraMoveType.DOLLY
            keyframes = [
                {"time": start, "location": (0, 0, 50), "rotation": (0, 0, 0)},
                {"time": end, "location": (0, 0, 100), "rotation": (0, 0, 0)},
            ]
        elif "pan left" in desc or "track left" in desc:
            camera_move = CameraMoveType.TRUCK
            keyframes = [
                {"time": start, "location": (0, 0, 100), "rotation": (0, 0, 0)},
                {"time": end, "location": (-200, 0, 100), "rotation": (0, 0, 0)},
            ]
        elif "pan right" in desc or "track right" in desc:
            camera_move = CameraMoveType.TRUCK
            keyframes = [
                {"time": start, "location": (0, 0, 100), "rotation": (0, 0, 0)},
                {"time": end, "location": (200, 0, 100), "rotation": (0, 0, 0)},
            ]
        elif "static" in desc or "locked off" in desc:
            camera_move = CameraMoveType.STATIC
            keyframes = [
                {"time": start, "location": (0, 0, 100), "rotation": (0, 0, 0)},
                {"time": end, "location": (0, 0, 100), "rotation": (0, 0, 0)},
            ]
        elif "tilt up" in desc:
            camera_move = CameraMoveType.TILT
            keyframes = [
                {"time": start, "location": (0, 0, 100), "rotation": (-10, 0, 0)},
                {"time": end, "location": (0, 0, 100), "rotation": (10, 0, 0)},
            ]
        elif "tilt down" in desc:
            camera_move = CameraMoveType.TILT
            keyframes = [
                {"time": start, "location": (0, 0, 100), "rotation": (10, 0, 0)},
                {"time": end, "location": (0, 0, 100), "rotation": (-10, 0, 0)},
            ]
        else:
            camera_move = CameraMoveType.UNKNOWN
            keyframes = [
                {"time": start, "location": (0, 0, 100), "rotation": (0, 0, 0)},
                {"time": end, "location": (0, 0, 75), "rotation": (0, 0, 0)},
            ]
        for kf in keyframes:
            frame = int(min(max(kf["time"], 0) * 24.0, 86400))
            self._set_transform_keyframe(seq, binding, frame, kf["location"], kf["rotation"])
        log.info("shot_authored_from_nl", nl_description=nl_desc,
                 camera_move=camera_move.value, keyframe_count=len(keyframes))
        return NyraToolResult.ok({
            "status": "shot_authored", "nl_description": nl_desc,
            "camera_move_type": camera_move.value, "keyframe_count": len(keyframes),
            "start_time": start, "end_time": end,
        })

    def _camera_move_to_keyframe_pattern(
        self, shot: ShotBlock, start: float, end: float,
    ) -> list[dict]:
        """Convert a ShotBlock to keyframe dicts based on CameraMoveType."""
        move_type = shot.user_override_move_type or shot.camera_move_type
        times = [start, start + (end - start) / 3, start + 2 * (end - start) / 3, end]
        if move_type == CameraMoveType.STATIC:
            base_loc = shot.start_position
            return [{"time": t, "location": base_loc, "rotation": shot.start_rotation} for t in times]
        elif move_type in (CameraMoveType.DOLLY, CameraMoveType.TRUCK):
            return [
                {"time": start, "location": shot.start_position, "rotation": shot.start_rotation},
                {"time": end, "location": shot.end_position, "rotation": shot.end_rotation},
            ]
        else:
            return [
                {"time": start, "location": shot.start_position, "rotation": shot.start_rotation},
                {"time": end, "location": shot.end_position, "rotation": shot.end_rotation},
            ]

    def _find_binding_for_actor(self, sequence: Any, actor_path: str) -> Any:
        if not HAS_UNREAL:
            return None
        editor = unreal.get_editor_subsystem(unreal.LevelSequenceEditorSubsystem)
        bindings = editor.get_possible_bindings(sequence)
        for binding in bindings:
            if binding.get_name() == actor_path or actor_path in binding.get_name():
                return binding
        return None
