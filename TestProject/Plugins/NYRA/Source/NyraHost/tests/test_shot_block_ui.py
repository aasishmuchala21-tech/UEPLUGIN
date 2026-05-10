"""nyrahost.tests.test_shot_block_ui — Shot block UI confirmation tests.

Phase 7 Wave 2: Tests for ShotBlockConfirmationUI and CameraMove taxonomy.
Per ROADMAP SC#3: CameraMoveType is user-confirmable.
Per PITFALLS §6.2: dolly vs truck confusion handled.
"""
from __future__ import annotations

import pytest

from nyrahost.tools.shot_block_ui import (
    ShotBlockConfirmationUI, CONFUSION_PAIRS, CAMERA_MOVE_DISPLAY,
)
from nyrahost.tools.video_llm_parser import CameraMoveType, ShotBlock, VideoReferenceParams


class TestCameraMoveType:
    """Tests for CameraMoveType enum."""

    def test_all_move_types_exist(self):
        expected = {
            "static", "pan", "tilt", "dolly", "truck",
            "crane", "zoom", "handheld", "unknown",
        }
        actual = {m.value for m in CameraMoveType}
        assert actual == expected

    def test_camera_move_display_labels(self):
        assert CAMERA_MOVE_DISPLAY[CameraMoveType.STATIC] == "Locked Off (Static)"
        assert CAMERA_MOVE_DISPLAY[CameraMoveType.DOLLY] == "Dolly (move toward/away)"
        assert CAMERA_MOVE_DISPLAY[CameraMoveType.TRUCK] == "Truck (lateral pan)"
        assert CAMERA_MOVE_DISPLAY[CameraMoveType.UNKNOWN] == "Unknown (needs confirmation)"

    def test_confusion_pairs_defined(self):
        assert CameraMoveType.DOLLY in CONFUSION_PAIRS
        assert CameraMoveType.TRUCK in CONFUSION_PAIRS
        assert CONFUSION_PAIRS[CameraMoveType.DOLLY] == CameraMoveType.TRUCK
        assert CONFUSION_PAIRS[CameraMoveType.TRUCK] == CameraMoveType.DOLLY


class TestShotBlockConfirmationUI:
    """Tests for ShotBlockConfirmationUI."""

    def test_confirm_shot_no_override(self):
        ui = ShotBlockConfirmationUI()
        shot = ShotBlock(
            shot_id="shot_001",
            camera_move_type=CameraMoveType.DOLLY,
            start_time=0.0, end_time=5.0,
            start_position=(0, 0, 100), end_position=(0, 0, 50),
            start_rotation=(0, 0, 0), end_rotation=(0, 0, 0),
            fov=35.0, focus_distance=3.0, aperture=2.8,
            nl_description="slow push-in",
        )
        confirmed = ui.confirm_shot(shot)
        assert confirmed.user_confirmed is True
        assert confirmed.user_override_move_type is None

    def test_confirm_shot_with_override_dolly_to_truck(self):
        ui = ShotBlockConfirmationUI()
        shot = ShotBlock(
            shot_id="shot_002",
            camera_move_type=CameraMoveType.DOLLY,
            start_time=0.0, end_time=5.0,
            start_position=(0, 0, 100), end_position=(-200, 0, 100),
            start_rotation=(0, 0, 0), end_rotation=(0, 0, 0),
            fov=50.0, focus_distance=5.0, aperture=4.0,
            nl_description="lateral camera move",
        )
        confirmed = ui.confirm_shot(shot, override_move_type=CameraMoveType.TRUCK)
        assert confirmed.user_confirmed is True
        assert confirmed.user_override_move_type == CameraMoveType.TRUCK

    def test_confirm_shot_with_override_truck_to_dolly(self):
        ui = ShotBlockConfirmationUI()
        shot = ShotBlock(
            shot_id="shot_003",
            camera_move_type=CameraMoveType.TRUCK,
            start_time=0.0, end_time=5.0,
            start_position=(0, 0, 100), end_position=(0, 0, 50),
            start_rotation=(0, 0, 0), end_rotation=(0, 0, 0),
            fov=35.0, focus_distance=3.0, aperture=2.8,
            nl_description="push-in camera move",
        )
        confirmed = ui.confirm_shot(shot, override_move_type=CameraMoveType.DOLLY)
        assert confirmed.user_confirmed is True
        assert confirmed.user_override_move_type == CameraMoveType.DOLLY

    def test_format_confirmation_card_dolly(self):
        ui = ShotBlockConfirmationUI()
        params = VideoReferenceParams(
            shot_blocks=[],
            subject_position=(0.5, 0.4),
            framing="close_up",
            rule_of_thirds=True,
            headroom="normal",
            lighting_mood_tags=["dramatic", "low_key"],
            primary_color=(1.0, 0.8, 0.6),
            primary_temperature_k=5600,
            fill_ratio=0.3,
            camera_move_type=CameraMoveType.DOLLY,
            camera_move_intensity="slow",
            camera_move_confidence=0.85,
            environment_type="indoor",
            time_of_day="golden_hour",
            weather="clear",
            geometry_categories=["urban", "interior"],
            clip_duration_seconds=5.0,
            keyframe_count=8,
            analysis_confidence=0.8,
        )
        card = ui.format_confirmation_card(params)
        assert card["camera_move_type"] == "dolly"
        assert card["camera_move_display"] == "Dolly (move toward/away)"
        assert card["requires_override"] is True
        assert card["possible_override"] == "Truck (lateral pan)"
        assert "DOLLY" in card["confusion_note"]
        assert card["framing"] == "close_up"
        assert card["lighting_temperature_k"] == 5600

    def test_format_confirmation_card_static(self):
        ui = ShotBlockConfirmationUI()
        params = VideoReferenceParams(
            shot_blocks=[],
            subject_position=(0.5, 0.5),
            framing="wide",
            rule_of_thirds=False,
            headroom="loose",
            lighting_mood_tags=["natural"],
            primary_color=(0.9, 0.9, 0.9),
            primary_temperature_k=6500,
            fill_ratio=0.5,
            camera_move_type=CameraMoveType.STATIC,
            camera_move_intensity="none",
            camera_move_confidence=0.95,
            environment_type="outdoor",
            time_of_day="midday",
            weather="clear",
            geometry_categories=["nature", "landscape"],
            clip_duration_seconds=3.0,
            keyframe_count=5,
            analysis_confidence=0.9,
        )
        card = ui.format_confirmation_card(params)
        assert card["camera_move_type"] == "static"
        assert card["requires_override"] is False
        assert card["confusion_note"] == ""


class TestVideoReferenceParamsRequiresConfirmation:
    """Tests for VideoReferenceParams.requires_user_confirmation()."""

    def test_low_confidence_requires_confirmation(self):
        params = VideoReferenceParams(
            shot_blocks=[],
            subject_position=(0.5, 0.5), framing="medium",
            rule_of_thirds=True, headroom="normal",
            lighting_mood_tags=["test"], primary_color=(1, 1, 1),
            primary_temperature_k=6500, fill_ratio=0.5,
            camera_move_type=CameraMoveType.STATIC,
            camera_move_intensity="slow",
            camera_move_confidence=0.65,  # < 0.7 threshold
            environment_type="indoor", time_of_day="midday",
            weather="clear", geometry_categories=[],
            clip_duration_seconds=5.0, keyframe_count=5,
            analysis_confidence=0.7,
        )
        assert params.requires_user_confirmation() is True

    def test_unknown_shot_requires_confirmation(self):
        shot = ShotBlock(
            shot_id="shot_unk", camera_move_type=CameraMoveType.UNKNOWN,
            start_time=0.0, end_time=5.0,
            start_position=(0, 0, 100), end_position=(0, 0, 100),
            start_rotation=(0, 0, 0), end_rotation=(0, 0, 0),
            fov=35.0, focus_distance=3.0, aperture=2.8,
            nl_description="ambiguous",
        )
        params = VideoReferenceParams(
            shot_blocks=[shot],
            subject_position=(0.5, 0.5), framing="medium",
            rule_of_thirds=True, headroom="normal",
            lighting_mood_tags=["test"], primary_color=(1, 1, 1),
            primary_temperature_k=6500, fill_ratio=0.5,
            camera_move_type=CameraMoveType.STATIC,
            camera_move_intensity="slow",
            camera_move_confidence=0.9,
            environment_type="indoor", time_of_day="midday",
            weather="clear", geometry_categories=[],
            clip_duration_seconds=5.0, keyframe_count=5,
            analysis_confidence=0.9,
        )
        assert params.requires_user_confirmation() is True

    def test_confirmed_unknown_shot_does_not_require_confirmation(self):
        shot = ShotBlock(
            shot_id="shot_confirmed", camera_move_type=CameraMoveType.UNKNOWN,
            start_time=0.0, end_time=5.0,
            start_position=(0, 0, 100), end_position=(0, 0, 100),
            start_rotation=(0, 0, 0), end_rotation=(0, 0, 0),
            fov=35.0, focus_distance=3.0, aperture=2.8,
            nl_description="ambiguous",
            user_confirmed=True,
        )
        params = VideoReferenceParams(
            shot_blocks=[shot],
            subject_position=(0.5, 0.5), framing="medium",
            rule_of_thirds=True, headroom="normal",
            lighting_mood_tags=["test"], primary_color=(1, 1, 1),
            primary_temperature_k=6500, fill_ratio=0.5,
            camera_move_type=CameraMoveType.STATIC,
            camera_move_intensity="slow",
            camera_move_confidence=0.9,
            environment_type="indoor", time_of_day="midday",
            weather="clear", geometry_categories=[],
            clip_duration_seconds=5.0, keyframe_count=5,
            analysis_confidence=0.9,
        )
        assert params.requires_user_confirmation() is False

    def test_all_known_high_confidence_non_confusion_pair_no_confirmation(self):
        # WR-07: post-fix, DOLLY and TRUCK ALWAYS require confirmation per
        # PITFALLS Section 6.2. This test exercises the no-confirmation path
        # using PAN, which is not in CONFUSION_PAIRS.
        shot = ShotBlock(
            shot_id="shot_known", camera_move_type=CameraMoveType.PAN,
            start_time=0.0, end_time=5.0,
            start_position=(0, 0, 100), end_position=(0, 0, 100),
            start_rotation=(0, 0, 0), end_rotation=(0, 30, 0),
            fov=35.0, focus_distance=3.0, aperture=2.8,
            nl_description="slow pan right",
        )
        params = VideoReferenceParams(
            shot_blocks=[shot],
            subject_position=(0.5, 0.5), framing="medium",
            rule_of_thirds=True, headroom="normal",
            lighting_mood_tags=["test"], primary_color=(1, 1, 1),
            primary_temperature_k=6500, fill_ratio=0.5,
            camera_move_type=CameraMoveType.PAN,
            camera_move_intensity="medium",
            camera_move_confidence=0.9,
            environment_type="outdoor", time_of_day="golden_hour",
            weather="clear", geometry_categories=["urban"],
            clip_duration_seconds=5.0, keyframe_count=5,
            analysis_confidence=0.9,
        )
        assert params.requires_user_confirmation() is False

    def test_high_confidence_dolly_still_requires_confirmation(self):
        # WR-07: even at 0.9 confidence, DOLLY trips the confusion-pair
        # guard so the operator gets a "did you mean TRUCK?" override card.
        shot = ShotBlock(
            shot_id="shot_dolly_high", camera_move_type=CameraMoveType.DOLLY,
            start_time=0.0, end_time=5.0,
            start_position=(0, 0, 100), end_position=(0, 0, 50),
            start_rotation=(0, 0, 0), end_rotation=(0, 0, 0),
            fov=35.0, focus_distance=3.0, aperture=2.8,
            nl_description="push-in",
        )
        params = VideoReferenceParams(
            shot_blocks=[shot],
            subject_position=(0.5, 0.5), framing="medium",
            rule_of_thirds=True, headroom="normal",
            lighting_mood_tags=["test"], primary_color=(1, 1, 1),
            primary_temperature_k=6500, fill_ratio=0.5,
            camera_move_type=CameraMoveType.DOLLY,
            camera_move_intensity="medium",
            camera_move_confidence=0.9,
            environment_type="outdoor", time_of_day="golden_hour",
            weather="clear", geometry_categories=["urban"],
            clip_duration_seconds=5.0, keyframe_count=5,
            analysis_confidence=0.9,
        )
        assert params.requires_user_confirmation() is True

    def test_high_confidence_truck_still_requires_confirmation(self):
        # WR-07: TRUCK is the other half of the DOLLY/TRUCK confusion pair.
        params = VideoReferenceParams(
            shot_blocks=[],
            subject_position=(0.5, 0.5), framing="wide",
            rule_of_thirds=True, headroom="normal",
            lighting_mood_tags=["test"], primary_color=(1, 1, 1),
            primary_temperature_k=6500, fill_ratio=0.5,
            camera_move_type=CameraMoveType.TRUCK,
            camera_move_intensity="medium",
            camera_move_confidence=0.95,
            environment_type="outdoor", time_of_day="midday",
            weather="clear", geometry_categories=["urban"],
            clip_duration_seconds=5.0, keyframe_count=5,
            analysis_confidence=0.95,
        )
        assert params.requires_user_confirmation() is True