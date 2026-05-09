"""nyrahost.tools.demo02_orchestrator — Phase 7 orchestrator.

Phase 7 Wave 2: Orchestrates VideoReference -> SequencerAuthoring pipeline.
Per ROADMAP SC#4: Demo02 Orchestrator (video reference -> shot blocking).
Per ROADMAP SC#3: CameraMove taxonomy, user confirmation.
Per PITFALLS §6.2: dolly vs truck confusion handled via ShotBlockConfirmationUI.
Per PITFALLS §7.1: ComfyUI workflow validation before sequencer binding.
"""
from __future__ import annotations

import structlog
from typing import Optional

from nyrahost.tools.video_llm_parser import VideoReferenceParams
from nyrahost.tools.shot_block_ui import ShotBlockConfirmationUI
from nyrahost.tools.sequencer_tools import SequencerAuthorShotTool

log = structlog.get_logger("nyrahost.tools.demo02_orchestrator")

__all__ = ["Demo02Orchestrator"]


class Demo02Orchestrator:
    """Orchestrates the Demo 02 pipeline: video reference -> shot blocking -> Sequencer."""

    def __init__(
        self,
        sequencer_author_tool: Optional[SequencerAuthorShotTool] = None,
        shot_confirm_ui: Optional[ShotBlockConfirmationUI] = None,
    ):
        self.sequencer_author = sequencer_author_tool or SequencerAuthorShotTool()
        self.shot_confirm_ui = shot_confirm_ui or ShotBlockConfirmationUI()

    def run_video_to_sequencer(
        self,
        video_reference_params: VideoReferenceParams,
        sequence_path: str,
        binding_path: str,
    ) -> dict:
        """Run the full video -> sequencer pipeline.

        Steps:
        1. Check if any shots need user confirmation
        2. If no UNKNOWN shots: author directly
        3. If UNKNOWN: format confirmation card for Slate UI
        4. After user confirms: author confirmed shots

        Returns a dict with status, data, and next steps.
        """
        log.info("demo02_orchestrator_start",
                 shot_count=len(video_reference_params.shot_blocks),
                 requires_confirmation=video_reference_params.requires_user_confirmation())

        if video_reference_params.requires_user_confirmation():
            card = self.shot_confirm_ui.format_confirmation_card(video_reference_params)
            log.warning("demo02_orchestrator_needs_confirmation",
                        confidence=video_reference_params.camera_move_confidence,
                        camera_move=video_reference_params.camera_move_type.value)
            return {
                "status": "needs_user_confirmation",
                "confirmation_card": card,
                "message": (
                    "Camera move type requires user confirmation. "
                    "Show the Slate confirmation widget to the user, "
                    "then call run_with_confirmation() with the confirmed params."
                ),
            }

        return self._author_shots(video_reference_params, sequence_path, binding_path)

    def run_with_confirmation(
        self,
        video_reference_params: VideoReferenceParams,
        sequence_path: str,
        binding_path: str,
        confirmed_shot_blocks: list,
    ) -> dict:
        """Author shots after user has confirmed the camera move taxonomy."""
        log.info("demo02_orchestrator_confirmed_run",
                 shot_count=len(confirmed_shot_blocks))
        for idx, confirmed_shot in enumerate(confirmed_shot_blocks):
            log.info("shot_confirmed_by_user",
                     shot_id=confirmed_shot.shot_id,
                     override_move=(
                         confirmed_shot.user_override_move_type.value
                         if confirmed_shot.user_override_move_type
                         else confirmed_shot.camera_move_type.value
                     ))
        return self._author_shots(video_reference_params, sequence_path, binding_path)

    def _author_shots(
        self,
        params: VideoReferenceParams,
        sequence_path: str,
        binding_path: str,
    ) -> dict:
        """Author all confirmed shot blocks to the sequence."""
        result = self.sequencer_author.execute({
            "sequence_path": sequence_path,
            "binding_path": binding_path,
            "video_reference_json": params.to_json(),
            "duration_seconds": params.clip_duration_seconds,
        })
        if not result.is_ok:
            log.error("demo02_orchestrator_author_failed", error=result.error)
            return {"status": "error", "error": result.error}
        log.info("demo02_orchestrator_complete",
                 camera_move=params.camera_move_type.value,
                 shot_count=len(params.shot_blocks),
                 duration_s=params.clip_duration_seconds)
        return {
            "status": "authored",
            "camera_move_type": params.camera_move_type.value,
            "shot_count": len(params.shot_blocks),
            "duration_seconds": params.clip_duration_seconds,
            "lighting_mood_tags": params.lighting_mood_tags,
            "framing": params.framing,
            "environment_type": params.environment_type,
            "time_of_day": params.time_of_day,
            "message": f"Successfully authored {len(params.shot_blocks)} shots to Sequencer",
        }