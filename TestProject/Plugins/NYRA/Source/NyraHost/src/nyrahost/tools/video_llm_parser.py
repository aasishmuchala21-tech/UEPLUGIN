"""nyrahost.tools.video_llm_parser — VideoReferenceParams + CameraMove taxonomy.

Phase 7 Wave 0: Shared types for video analysis -> Sequencer pipeline.
CameraMoveTaxonomy enum per ROADMAP SC#3.
"""
from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from nyrahost.tools.lighting_tools import LightingParams

log = structlog.get_logger("nyrahost.tools.video_llm_parser")

__all__ = ["CameraMoveType", "ShotBlock", "VideoReferenceParams"]


class CameraMoveType(str, Enum):
    """Canonical camera movement taxonomy per ROADMAP SC#3."""
    STATIC = "static"          # Camera does not move
    PAN = "pan"                # Horizontal rotation around a fixed point
    TILT = "tilt"             # Vertical rotation around a fixed point
    DOLLY = "dolly"           # Camera moves along Z-axis (toward/away from subject)
    TRUCK = "truck"            # Camera moves along X or Y axis (lateral, parallel to frame)
    CRANE = "crane"            # Camera moves on multiple axes (complex)
    ZOOM = "zoom"              # FOV change only, camera does not move physically
    HANDHELD = "handheld"      # Organic jitter — simulated with noise
    UNKNOWN = "unknown"         # Requires user confirmation


@dataclass
class ShotBlock:
    """Describes one camera shot within a video reference."""
    shot_id: str
    camera_move_type: CameraMoveType
    start_time: float          # seconds in the sequence
    end_time: float            # seconds
    start_position: tuple[float, float, float]  # world-space XYZ (cm)
    end_position: tuple[float, float, float]     # world-space XYZ (cm)
    start_rotation: tuple[float, float, float]   # pitch, yaw, roll in degrees
    end_rotation: tuple[float, float, float]     # pitch, yaw, roll in degrees
    fov: float                 # horizontal FOV in degrees (35mm equivalent)
    focus_distance: float      # meters
    aperture: float            # f-stop (e.g. 2.8)
    nl_description: str         # e.g. "slow push-in, then cut wide"
    user_confirmed: bool = False
    user_override_move_type: Optional[CameraMoveType] = None


@dataclass
class VideoReferenceParams:
    """Output of Claude Opus vision analysis on video keyframes."""
    # Shot structure
    shot_blocks: list[ShotBlock]

    # Composition
    subject_position: tuple[float, float]   # normalized 0-1 (x=horizontal, y=vertical)
    framing: str                            # extreme_close_up|close_up|medium|full|wide|establishing
    rule_of_thirds: bool
    headroom: str                          # tight|normal|loose

    # Lighting (extends LightingParams fields)
    lighting_mood_tags: list[str]
    primary_color: tuple[float, float, float]
    primary_temperature_k: float
    fill_ratio: float                      # 0-1, fill_light / key_light intensity

    # Camera
    camera_move_type: CameraMoveType
    camera_move_intensity: str              # slow|medium|fast
    camera_move_confidence: float            # 0-1

    # Scene understanding
    environment_type: str                  # indoor|outdoor|studio|VFX_plate
    time_of_day: str                       # dawn|morning|midday|golden_hour|dusk|night|unknown
    weather: str                            # clear|overcast|rain|fog|smoke|unknown
    geometry_categories: list[str]

    # Metadata
    clip_duration_seconds: float
    keyframe_count: int
    analysis_confidence: float              # 0-1

    def get_shot_blocks_for_sequencer(self) -> list[ShotBlock]:
        """Return shot blocks that should be authored in Sequencer."""
        return [sb for sb in self.shot_blocks if sb.user_confirmed or sb.camera_move_type != CameraMoveType.UNKNOWN]

    def get_primary_lighting_params(self) -> LightingParams:
        """Map lighting fields to LightingParams for LightingAuthoringTool."""
        return LightingParams(
            primary_light_type="directional" if self.environment_type == "outdoor" else "point",
            primary_intensity=3.0,
            primary_color=self.primary_color,
            primary_direction=(0.5, -0.5, -1.0),
            primary_temperature=self.primary_temperature_k,
            use_sky_atmosphere=self.environment_type == "outdoor" and self.time_of_day != "night",
            use_exponential_height_fog=self.weather in ("fog", "rain"),
            fog_density=0.1 if self.weather == "fog" else 0.0,
            fog_color=self.primary_color,
            use_post_process=True,
            exposure_compensation=0.5 if self.time_of_day == "golden_hour" else 0.0,
            mood_tags=self.lighting_mood_tags,
            confidence=self.analysis_confidence,
        )

    def requires_user_confirmation(self) -> bool:
        """Return True if any shot is UNKNOWN or confidence < 0.7."""
        if self.camera_move_confidence < 0.7:
            log.warning("video_ref_low_confidence",
                       confidence=self.camera_move_confidence,
                       camera_move=self.camera_move_type.value)
            return True
        for sb in self.shot_blocks:
            if sb.camera_move_type == CameraMoveType.UNKNOWN and not sb.user_confirmed:
                log.warning("video_ref_unknown_shot", shot_id=sb.shot_id)
                return True
        return False

    def to_json(self) -> str:
        """Serialize to a JSON string for cross-tool transport.

        Tuples are emitted as lists (JSON has no tuple); enums emit their value.
        Demo02Orchestrator passes the result to SequencerAuthorShotTool's
        video_reference_json parameter, which round-trips it via json.loads.
        """
        import json

        def _shot(sb: ShotBlock) -> dict:
            return {
                "shot_id": sb.shot_id,
                "camera_move_type": sb.camera_move_type.value,
                "start_time": sb.start_time,
                "end_time": sb.end_time,
                "start_position": list(sb.start_position),
                "end_position": list(sb.end_position),
                "start_rotation": list(sb.start_rotation),
                "end_rotation": list(sb.end_rotation),
                "fov": sb.fov,
                "focus_distance": sb.focus_distance,
                "aperture": sb.aperture,
                "nl_description": sb.nl_description,
                "user_confirmed": sb.user_confirmed,
                "user_override_move_type": (
                    sb.user_override_move_type.value if sb.user_override_move_type else None
                ),
            }

        payload = {
            "shot_blocks": [_shot(sb) for sb in self.shot_blocks],
            "subject_position": list(self.subject_position),
            "framing": self.framing,
            "rule_of_thirds": self.rule_of_thirds,
            "headroom": self.headroom,
            "lighting_mood_tags": list(self.lighting_mood_tags),
            "primary_color": list(self.primary_color),
            "primary_temperature_k": self.primary_temperature_k,
            "fill_ratio": self.fill_ratio,
            "camera_move_type": self.camera_move_type.value,
            "camera_move_intensity": self.camera_move_intensity,
            "camera_move_confidence": self.camera_move_confidence,
            "environment_type": self.environment_type,
            "time_of_day": self.time_of_day,
            "weather": self.weather,
            "geometry_categories": list(self.geometry_categories),
            "clip_duration_seconds": self.clip_duration_seconds,
            "keyframe_count": self.keyframe_count,
            "analysis_confidence": self.analysis_confidence,
        }
        return json.dumps(payload)

    @classmethod
    def from_json(cls, payload: str) -> "VideoReferenceParams":
        """Deserialize a JSON payload produced by ``to_json`` into a VideoReferenceParams.

        Symmetric inverse of ``to_json``: lists are coerced back into tuples for
        position / rotation / color fields, and the camera_move_type strings
        are coerced back into the CameraMoveType enum (UNKNOWN on bad input).

        Demo02Orchestrator -> SequencerAuthorShotTool round-trips through this
        method; it must accept any output of ``to_json`` without raising.
        """
        import json

        def _enum(v: object) -> "CameraMoveType":
            try:
                return CameraMoveType(v)
            except (ValueError, TypeError):
                return CameraMoveType.UNKNOWN

        def _tuple(v: object, n: int, fill: float = 0.0) -> tuple:
            if isinstance(v, (list, tuple)) and len(v) >= n:
                return tuple(float(x) for x in v[:n])
            return tuple([fill] * n)

        def _opt_enum(v: object) -> Optional["CameraMoveType"]:
            if v is None:
                return None
            return _enum(v)

        d = json.loads(payload)

        shot_blocks: list[ShotBlock] = []
        for sb in d.get("shot_blocks", []) or []:
            shot_blocks.append(ShotBlock(
                shot_id=str(sb.get("shot_id", "")),
                camera_move_type=_enum(sb.get("camera_move_type", "unknown")),
                start_time=float(sb.get("start_time", 0.0)),
                end_time=float(sb.get("end_time", 0.0)),
                start_position=_tuple(sb.get("start_position"), 3),
                end_position=_tuple(sb.get("end_position"), 3),
                start_rotation=_tuple(sb.get("start_rotation"), 3),
                end_rotation=_tuple(sb.get("end_rotation"), 3),
                fov=float(sb.get("fov", 35.0)),
                focus_distance=float(sb.get("focus_distance", 3.0)),
                aperture=float(sb.get("aperture", 2.8)),
                nl_description=str(sb.get("nl_description", "")),
                user_confirmed=bool(sb.get("user_confirmed", False)),
                user_override_move_type=_opt_enum(sb.get("user_override_move_type")),
            ))

        return cls(
            shot_blocks=shot_blocks,
            subject_position=_tuple(d.get("subject_position"), 2, fill=0.5),
            framing=str(d.get("framing", "medium")),
            rule_of_thirds=bool(d.get("rule_of_thirds", True)),
            headroom=str(d.get("headroom", "normal")),
            lighting_mood_tags=list(d.get("lighting_mood_tags", []) or []),
            primary_color=_tuple(d.get("primary_color"), 3, fill=1.0),
            primary_temperature_k=float(d.get("primary_temperature_k", 5500.0)),
            fill_ratio=float(d.get("fill_ratio", 0.5)),
            camera_move_type=_enum(d.get("camera_move_type", "unknown")),
            camera_move_intensity=str(d.get("camera_move_intensity", "slow")),
            camera_move_confidence=float(d.get("camera_move_confidence", 0.5)),
            environment_type=str(d.get("environment_type", "indoor")),
            time_of_day=str(d.get("time_of_day", "unknown")),
            weather=str(d.get("weather", "unknown")),
            geometry_categories=list(d.get("geometry_categories", []) or []),
            clip_duration_seconds=float(d.get("clip_duration_seconds", 0.0)),
            keyframe_count=int(d.get("keyframe_count", 0)),
            analysis_confidence=float(d.get("analysis_confidence", 0.5)),
        )
