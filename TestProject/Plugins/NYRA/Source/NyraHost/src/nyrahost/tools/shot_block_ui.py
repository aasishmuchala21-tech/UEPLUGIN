"""nyrahost.tools.shot_block_ui — User-confirmable camera-move taxonomy.

Phase 7 Wave 2: Shot confirmation logic for Slate widget.
Per ROADMAP SC#3: camera-move taxonomy is user-confirmable.
Per PITFALLS §6.2: dolly vs truck confusion — users can override.
"""
from __future__ import annotations

import structlog
from dataclasses import replace
from typing import Optional

from nyrahost.tools.video_llm_parser import CameraMoveType, ShotBlock, VideoReferenceParams

log = structlog.get_logger("nyrahost.tools.shot_block_ui")

__all__ = ["ShotBlockConfirmationUI", "CONFUSION_PAIRS", "CAMERA_MOVE_DISPLAY"]

CAMERA_MOVE_DISPLAY = {
    CameraMoveType.STATIC: "Locked Off (Static)",
    CameraMoveType.PAN: "Pan (horizontal rotation)",
    CameraMoveType.TILT: "Tilt (vertical rotation)",
    CameraMoveType.DOLLY: "Dolly (move toward/away)",
    CameraMoveType.TRUCK: "Truck (lateral pan)",
    CameraMoveType.CRANE: "Crane (multi-axis)",
    CameraMoveType.ZOOM: "Zoom (FOV change)",
    CameraMoveType.HANDHELD: "Handheld (organic jitter)",
    CameraMoveType.UNKNOWN: "Unknown (needs confirmation)",
}

CONFUSION_PAIRS = {
    CameraMoveType.DOLLY: CameraMoveType.TRUCK,
    CameraMoveType.TRUCK: CameraMoveType.DOLLY,
}


class ShotBlockConfirmationUI:
    """Handles shot block confirmation and camera-move override logic.

    The actual Slate UI (SMyrShotConfirmDialog) lives in C++ NyraEditor
    module and calls into this Python module via WS messages.
    """

    def __init__(self, confusion_pairs: Optional[dict] = None):
        self.confusion_pairs = confusion_pairs or CONFUSION_PAIRS

    def _format_confirmation_message(self, shot: ShotBlock) -> str:
        """Format a human-readable shot confirmation message."""
        display_type = CAMERA_MOVE_DISPLAY.get(shot.camera_move_type, "Unknown")
        lines = [
            f"Shot: {shot.shot_id}",
            f"Camera movement: {display_type}",
            f"FOV: {shot.fov:.0f}mm equivalent",
            f"Focus: {shot.focus_distance:.1f}m / f{shot.aperture}",
            f"Description: {shot.nl_description}",
            f"Duration: {shot.end_time - shot.start_time:.1f}s",
        ]
        if shot.camera_move_type in self.confusion_pairs:
            override_type = self.confusion_pairs[shot.camera_move_type]
            override_display = CAMERA_MOVE_DISPLAY.get(override_type, str(override_type))
            lines.append("")
            lines.append(
                f"[NOTE] This could also be: {override_display}. "
                "Use 'Override' if the camera moves sideways (truck) rather than forward (dolly)."
            )
        return "\n".join(lines)

    def confirm_shot(
        self,
        shot: ShotBlock,
        override_move_type: Optional[CameraMoveType] = None,
        override_confirmed: bool = True,
    ) -> ShotBlock:
        """Mark a shot as confirmed by the user."""
        if override_move_type is not None:
            confirmed = replace(
                shot,
                user_confirmed=override_confirmed,
                user_override_move_type=override_move_type,
            )
            log.info("shot_confirmed_with_override",
                     shot_id=shot.shot_id,
                     original_move=shot.camera_move_type.value,
                     override_move=override_move_type.value)
        else:
            confirmed = replace(shot, user_confirmed=override_confirmed)
            log.info("shot_confirmed", shot_id=shot.shot_id, camera_move=shot.camera_move_type.value)
        return confirmed

    def format_confirmation_card(self, params: VideoReferenceParams) -> dict:
        """Format a full shot confirmation card from VideoReferenceParams."""
        primary_shot = params.shot_blocks[0] if params.shot_blocks else None
        return {
            "camera_move_type": params.camera_move_type.value,
            "camera_move_display": CAMERA_MOVE_DISPLAY.get(params.camera_move_type, "Unknown"),
            "confidence": params.camera_move_confidence,
            "framing": params.framing,
            "subject_position": list(params.subject_position),
            "rule_of_thirds": params.rule_of_thirds,
            "lighting_mood_tags": params.lighting_mood_tags,
            "lighting_temperature_k": params.primary_temperature_k,
            "environment_type": params.environment_type,
            "time_of_day": params.time_of_day,
            "weather": params.weather,
            "geometry_categories": params.geometry_categories,
            "duration_s": params.clip_duration_seconds,
            "keyframe_count": params.keyframe_count,
            "analysis_confidence": params.analysis_confidence,
            "shot_count": len(params.shot_blocks),
            "primary_shot_nl_description": primary_shot.nl_description if primary_shot else "",
            "requires_override": params.camera_move_type in self.confusion_pairs,
            "possible_override": CAMERA_MOVE_DISPLAY.get(
                self.confusion_pairs.get(params.camera_move_type, CameraMoveType.UNKNOWN), ""),
            "confusion_note": (
                "NYRA detected this as DOLLY. If the camera moves sideways (lateral), "
                "select TRUCK instead."
                if params.camera_move_type == CameraMoveType.DOLLY else
                "NYRA detected this as TRUCK. If the camera moves forward/back, "
                "select DOLLY instead."
                if params.camera_move_type == CameraMoveType.TRUCK else
                ""
            ),
        }
