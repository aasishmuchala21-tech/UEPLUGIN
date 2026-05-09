"""nyrahost.tools.demo02_cli_tool — Demo02 CLI entry point.

Phase 7 Wave 2: Command-line interface for Demo 02 orchestration.
Provides: video reference analyze, shot block confirm, sequencer author, pipeline run.
"""
from __future__ import annotations

import json
import structlog
from typing import Optional

from nyrahost.tools.base import NyraTool, NyraToolResult
from nyrahost.tools.video_llm_parser import CameraMoveType, ShotBlock, VideoReferenceParams
from nyrahost.tools.shot_block_ui import ShotBlockConfirmationUI
from nyrahost.tools.demo02_orchestrator import Demo02Orchestrator

log = structlog.get_logger("nyrahost.tools.demo02_cli_tool")

__all__ = ["Demo02PipelineCLITool"]


class Demo02PipelineCLITool(NyraTool):
    """CLI entry point for Demo 02: video reference to Sequencer authoring pipeline."""
    name = "nyra_demo02_cli"
    description = (
        "Run the Demo 02 pipeline: video reference analysis -> shot block confirmation -> "
        "Sequencer shot authoring. Use for rapid NL-to-Sequencer iteration."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["analyze_reference", "confirm_shots", "author_sequence", "run_pipeline"],
                "description": "Which action to perform",
            },
            "video_reference_json": {
                "type": "string",
                "description": "JSON string of VideoReferenceParams from video analysis",
            },
            "sequence_path": {"type": "string"},
            "binding_path": {"type": "string"},
            "nl_shot_description": {
                "type": "string",
                "description": "NL description of shot ('slow push-in, then cut wide')",
            },
            "shot_overrides": {
                "type": "array",
                "description": "Array of {shot_id, override_move_type} for confirmed shots",
            },
        },
        "required": ["action"],
    }

    def __init__(self):
        super().__init__()
        self.orchestrator = Demo02Orchestrator()
        self.shot_confirm_ui = ShotBlockConfirmationUI()

    def execute(self, params: dict) -> NyraToolResult:
        action = params["action"]
        log.info("demo02_cli_action", action=action)

        if action == "analyze_reference":
            return self._analyze_reference(params)
        elif action == "confirm_shots":
            return self._confirm_shots(params)
        elif action == "author_sequence":
            return self._author_sequence(params)
        elif action == "run_pipeline":
            return self._run_pipeline(params)
        else:
            return NyraToolResult.err(f"[-32050] Unknown action: {action}")

    def _analyze_reference(self, params: dict) -> NyraToolResult:
        """Format video reference params for review."""
        if not params.get("video_reference_json"):
            return NyraToolResult.err("[-32051] video_reference_json required for analyze_reference")
        try:
            ref = VideoReferenceParams.from_json(params["video_reference_json"])
        except Exception as e:
            return NyraToolResult.err(f"[-32052] Failed to parse video_reference_json: {e}")
        card = self.shot_confirm_ui.format_confirmation_card(ref)
        return NyraToolResult.ok({
            "action": "analyze_reference",
            "confirmation_card": card,
            "requires_confirmation": ref.requires_user_confirmation(),
            "shot_count": len(ref.shot_blocks),
            "camera_move_type": ref.camera_move_type.value,
            "camera_move_confidence": ref.camera_move_confidence,
            "message": (
                "Video reference analyzed. "
                + ("User confirmation required." if ref.requires_user_confirmation() else "Ready to author.")
            ),
        })

    def _confirm_shots(self, params: dict) -> NyraToolResult:
        """Confirm shot blocks with optional camera-move overrides."""
        if not params.get("video_reference_json"):
            return NyraToolResult.err("[-32051] video_reference_json required for confirm_shots")
        try:
            ref = VideoReferenceParams.from_json(params["video_reference_json"])
        except Exception as e:
            return NyraToolResult.err(f"[-32052] Failed to parse video_reference_json: {e}")
        overrides = {item["shot_id"]: item["override_move_type"]
                     for item in (params.get("shot_overrides") or [])}
        confirmed_blocks = []
        for shot in ref.shot_blocks:
            override = CameraMoveType(overrides[shot.shot_id]) if shot.shot_id in overrides else None
            confirmed = self.shot_confirm_ui.confirm_shot(shot, override_move_type=override)
            confirmed_blocks.append(confirmed)
        return NyraToolResult.ok({
            "action": "confirm_shots",
            "confirmed_count": len(confirmed_blocks),
            "shot_ids": [sb.shot_id for sb in confirmed_blocks],
            "message": f"Confirmed {len(confirmed_blocks)} shot blocks",
        })

    def _author_sequence(self, params: dict) -> NyraToolResult:
        """Author confirmed shots to the level sequence."""
        if not params.get("sequence_path") or not params.get("binding_path"):
            return NyraToolResult.err("[-32053] sequence_path and binding_path required for author_sequence")
        if not params.get("video_reference_json") and not params.get("nl_shot_description"):
            return NyraToolResult.err("[-32054] video_reference_json or nl_shot_description required")
        from nyrahost.tools.sequencer_tools import SequencerAuthorShotTool
        tool = SequencerAuthorShotTool()
        result = tool.execute({
            "sequence_path": params["sequence_path"],
            "binding_path": params["binding_path"],
            "video_reference_json": params.get("video_reference_json"),
            "nl_description": params.get("nl_shot_description"),
        })
        return result

    def _run_pipeline(self, params: dict) -> NyraToolResult:
        """Run the full pipeline: analyze -> confirm -> author."""
        if not params.get("video_reference_json"):
            return NyraToolResult.err("[-32051] video_reference_json required for run_pipeline")
        try:
            ref = VideoReferenceParams.from_json(params["video_reference_json"])
        except Exception as e:
            return NyraToolResult.err(f"[-32052] Failed to parse video_reference_json: {e}")
        if not params.get("sequence_path") or not params.get("binding_path"):
            return NyraToolResult.err("[-32053] sequence_path and binding_path required for run_pipeline")
        overrides = {item["shot_id"]: item["override_move_type"]
                     for item in (params.get("shot_overrides") or [])}
        confirmed_blocks = []
        for shot in ref.shot_blocks:
            override = CameraMoveType(overrides[shot.shot_id]) if shot.shot_id in overrides else None
            confirmed = self.shot_confirm_ui.confirm_shot(shot, override_move_type=override)
            confirmed_blocks.append(confirmed)
        ref_with_confirmed = ref.__class__(
            **{**ref.__dict__, "shot_blocks": confirmed_blocks}
        )
        result = self.orchestrator.run_with_confirmation(
            ref_with_confirmed,
            params["sequence_path"],
            params["binding_path"],
            confirmed_blocks,
        )
        return NyraToolResult.ok(result)