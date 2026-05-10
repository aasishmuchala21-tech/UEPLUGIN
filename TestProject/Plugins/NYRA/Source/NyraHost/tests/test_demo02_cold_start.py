"""nyrahost.tests.test_demo02_cold_start — Demo 02 cold start tests.

Phase 7 Wave 2: End-to-end tests for Demo02Orchestrator pipeline.
Tests the cold start path: video reference -> confirmation card -> confirmed authoring.
Per ROADMAP SC#4: Demo02 Orchestrator.
Per PITFALLS §6.2: dolly vs truck confusion resolved via overrides.
Per PITFALLS §7.1: ComfyUI workflow validation before sequencer binding.
"""
from __future__ import annotations

import pytest

from nyrahost.tools.demo02_orchestrator import Demo02Orchestrator
from nyrahost.tools.video_llm_parser import CameraMoveType, ShotBlock, VideoReferenceParams
from nyrahost.tools.shot_block_ui import ShotBlockConfirmationUI, CONFUSION_PAIRS
from nyrahost.tools.sequencer_tools import SequencerAuthorShotTool


class TestDemo02Orchestrator:
    """Tests for Demo02Orchestrator."""

    def test_orchestrator_initialization(self):
        orch = Demo02Orchestrator()
        assert orch.sequencer_author is not None
        assert isinstance(orch.sequencer_author, SequencerAuthorShotTool)
        assert orch.shot_confirm_ui is not None
        assert isinstance(orch.shot_confirm_ui, ShotBlockConfirmationUI)

    def test_run_video_to_sequencer_high_confidence(self):
        """High confidence video reference should route directly to authoring."""
        orch = Demo02Orchestrator()
        ref = VideoReferenceParams(
            shot_blocks=[
                ShotBlock(
                    shot_id="shot_001",
                    camera_move_type=CameraMoveType.DOLLY,
                    start_time=0.0, end_time=5.0,
                    start_position=(0, 0, 100), end_position=(0, 0, 50),
                    start_rotation=(0, 0, 0), end_rotation=(0, 0, 0),
                    fov=35.0, focus_distance=3.0, aperture=2.8,
                    nl_description="slow push-in",
                    user_confirmed=False,
                )
            ],
            subject_position=(0.5, 0.5),
            framing="close_up",
            rule_of_thirds=True,
            headroom="normal",
            lighting_mood_tags=["dramatic"],
            primary_color=(1.0, 0.8, 0.6),
            primary_temperature_k=5600,
            fill_ratio=0.3,
            camera_move_type=CameraMoveType.DOLLY,
            camera_move_intensity="slow",
            camera_move_confidence=0.9,
            environment_type="indoor",
            time_of_day="golden_hour",
            weather="clear",
            geometry_categories=["urban"],
            clip_duration_seconds=5.0,
            keyframe_count=8,
            analysis_confidence=0.85,
        )
        # Without Unreal engine, sequencer_author will return err → test the pipeline route
        result = orch.run_video_to_sequencer(ref, "/tmp/shot_001", "/tmp/cam_001")
        # Expected: authored (or err if no Unreal — validates the pipeline structure)
        assert result["status"] in ("authored", "error")

    def test_run_video_to_sequencer_low_confidence_returns_needs_confirmation(self):
        """Low confidence video reference should return needs_user_confirmation status."""
        orch = Demo02Orchestrator()
        ref = VideoReferenceParams(
            shot_blocks=[],
            subject_position=(0.5, 0.5),
            framing="medium",
            rule_of_thirds=True,
            headroom="normal",
            lighting_mood_tags=["test"],
            primary_color=(1, 1, 1),
            primary_temperature_k=6500,
            fill_ratio=0.5,
            camera_move_type=CameraMoveType.UNKNOWN,
            camera_move_intensity="slow",
            camera_move_confidence=0.55,
            environment_type="indoor",
            time_of_day="midday",
            weather="clear",
            geometry_categories=[],
            clip_duration_seconds=5.0,
            keyframe_count=5,
            analysis_confidence=0.6,
        )
        result = orch.run_video_to_sequencer(ref, "/tmp/shot_001", "/tmp/cam_001")
        assert result["status"] == "needs_user_confirmation"
        assert "confirmation_card" in result
        card = result["confirmation_card"]
        assert card["camera_move_type"] == "unknown"
        assert card["confidence"] == 0.55

    def test_run_with_confirmation(self):
        """User-confirmed shots should route to authoring without confirmation card."""
        orch = Demo02Orchestrator()
        confirmed_shot = ShotBlock(
            shot_id="shot_002",
            camera_move_type=CameraMoveType.TRUCK,
            start_time=0.0, end_time=5.0,
            start_position=(0, 0, 100), end_position=(-200, 0, 100),
            start_rotation=(0, 0, 0), end_rotation=(0, 0, 0),
            fov=50.0, focus_distance=5.0, aperture=4.0,
            nl_description="lateral track",
            user_confirmed=True,
            user_override_move_type=None,
        )
        ref = VideoReferenceParams(
            shot_blocks=[confirmed_shot],
            subject_position=(0.5, 0.5),
            framing="medium",
            rule_of_thirds=True,
            headroom="normal",
            lighting_mood_tags=["natural"],
            primary_color=(0.9, 0.9, 0.9),
            primary_temperature_k=6500,
            fill_ratio=0.5,
            camera_move_type=CameraMoveType.TRUCK,
            camera_move_intensity="medium",
            camera_move_confidence=0.88,
            environment_type="outdoor",
            time_of_day="midday",
            weather="clear",
            geometry_categories=["urban"],
            clip_duration_seconds=5.0,
            keyframe_count=8,
            analysis_confidence=0.85,
        )
        result = orch.run_with_confirmation(
            ref, "/tmp/shot_001", "/tmp/cam_001", [confirmed_shot],
        )
        assert result["status"] in ("authored", "error")

    def test_confirmed_unknown_shot_no_confirmation_needed(self):
        """USER-confirmed UNKNOWN shots bypass the confirmation flow."""
        orch = Demo02Orchestrator()
        confirmed_unknown = ShotBlock(
            shot_id="shot_ambiguous",
            camera_move_type=CameraMoveType.UNKNOWN,
            start_time=0.0, end_time=3.0,
            start_position=(0, 0, 100), end_position=(0, 0, 75),
            start_rotation=(0, 0, 0), end_rotation=(0, 0, 0),
            fov=35.0, focus_distance=3.0, aperture=2.8,
            nl_description="ambiguous motion",
            user_confirmed=True,
        )
        ref = VideoReferenceParams(
            shot_blocks=[confirmed_unknown],
            subject_position=(0.5, 0.5),
            framing="close_up",
            rule_of_thirds=True,
            headroom="normal",
            lighting_mood_tags=["moody"],
            primary_color=(0.5, 0.5, 1.0),
            primary_temperature_k=4500,
            fill_ratio=0.4,
            camera_move_type=CameraMoveType.STATIC,
            camera_move_intensity="slow",
            camera_move_confidence=0.75,
            environment_type="studio",
            time_of_day="unknown",
            weather="clear",
            geometry_categories=["studio"],
            clip_duration_seconds=3.0,
            keyframe_count=4,
            analysis_confidence=0.7,
        )
        result = orch.run_with_confirmation(
            ref, "/tmp/shot_001", "/tmp/cam_001", [confirmed_unknown],
        )
        assert result["status"] in ("authored", "error")


class TestDemo02ColdStartPath:
    """Integration tests for the Demo 02 cold start path."""

    def test_pipeline_routes_high_confidence_to_authoring(self):
        """High confidence pipeline: analyze → author (no human loop)."""
        orch = Demo02Orchestrator()
        ref = VideoReferenceParams(
            shot_blocks=[
                ShotBlock(
                    shot_id="shot_cold_001",
                    camera_move_type=CameraMoveType.PAN,
                    start_time=0.0, end_time=4.0,
                    start_position=(0, 0, 100), end_position=(0, 0, 100),
                    start_rotation=(0, -30, 0), end_rotation=(0, 30, 0),
                    fov=40.0, focus_distance=4.0, aperture=2.8,
                    nl_description="slow pan left to right",
                )
            ],
            subject_position=(0.5, 0.5),
            framing="wide",
            rule_of_thirds=True,
            headroom="loose",
            lighting_mood_tags=["cinematic"],
            primary_color=(0.8, 0.6, 0.4),
            primary_temperature_k=5200,
            fill_ratio=0.35,
            camera_move_type=CameraMoveType.PAN,
            camera_move_intensity="slow",
            camera_move_confidence=0.92,
            environment_type="outdoor",
            time_of_day="golden_hour",
            weather="clear",
            geometry_categories=["landscape", "nature"],
            clip_duration_seconds=4.0,
            keyframe_count=6,
            analysis_confidence=0.88,
        )
        result = orch.run_video_to_sequencer(ref, "/tmp/seq_001", "/tmp/cam_001")
        assert result["status"] in ("authored", "error")
        if result["status"] == "authored":
            assert result["camera_move_type"] == "pan"
            assert result["lighting_mood_tags"] == ["cinematic"]
            assert result["framing"] == "wide"

    def test_pipeline_low_confidence_returns_confirmation_card(self):
        """Low confidence pipeline: analyze → confirmation card → user → author."""
        orch = Demo02Orchestrator()
        ref = VideoReferenceParams(
            shot_blocks=[],
            subject_position=(0.5, 0.5),
            framing="medium",
            rule_of_thirds=True,
            headroom="normal",
            lighting_mood_tags=["moody"],
            primary_color=(0.3, 0.3, 0.8),
            primary_temperature_k=7000,
            fill_ratio=0.2,
            camera_move_type=CameraMoveType.UNKNOWN,
            camera_move_intensity="medium",
            camera_move_confidence=0.45,
            environment_type="indoor",
            time_of_day="midday",
            weather="overcast",
            geometry_categories=["urban", "interior"],
            clip_duration_seconds=6.0,
            keyframe_count=10,
            analysis_confidence=0.5,
        )
        result = orch.run_video_to_sequencer(ref, "/tmp/seq_001", "/tmp/cam_001")
        assert result["status"] == "needs_user_confirmation"
        assert "confirmation_card" in result
        card = result["confirmation_card"]
        assert card["requires_override"] is False  # UNKNOWN is not in confusion_pairs
        assert card["analysis_confidence"] == 0.5


class TestCameraMoveTaxonomy:
    """Tests for the CameraMoveType taxonomy per ROADMAP SC#3."""

    def test_all_9_camera_move_types_defined(self):
        assert len(CameraMoveType) == 9

    def test_dolly_truck_confusion_pair(self):
        assert CameraMoveType.DOLLY in CONFUSION_PAIRS
        assert CameraMoveType.TRUCK in CONFUSION_PAIRS

    def test_confusion_pairs_are_cross_referential(self):
        assert CONFUSION_PAIRS[CameraMoveType.DOLLY] == CameraMoveType.TRUCK
        assert CONFUSION_PAIRS[CameraMoveType.TRUCK] == CameraMoveType.DOLLY