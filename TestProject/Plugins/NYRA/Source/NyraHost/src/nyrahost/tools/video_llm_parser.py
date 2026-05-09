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
