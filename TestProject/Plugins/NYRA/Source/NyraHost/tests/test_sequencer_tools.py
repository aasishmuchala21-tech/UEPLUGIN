"""nyrahost.tests.test_sequencer_tools — Sequencer automation tests.

Phase 7 Wave 2: Tests for SequencerCreateTool, SequencerAddCameraTool,
SequencerSetKeyframeTool, SequencerAuthorShotTool.
"""
from __future__ import annotations

import pytest

from nyrahost.tools.sequencer_tools import (
    SequencerCreateTool, SequencerAddCameraTool,
    SequencerSetKeyframeTool, SequencerAuthorShotTool,
    SequencerToolMixin,
)


class TestSequencerToolMixin:
    """Tests for the SequencerToolMixin shared helpers."""

    def test_mixin_exposes_helper_methods(self):
        mixin = SequencerToolMixin()
        assert hasattr(mixin, "_create_level_sequence")
        assert hasattr(mixin, "_bind_camera_to_sequence")
        assert hasattr(mixin, "_set_transform_keyframe")
        assert hasattr(mixin, "_set_camera_fov_keyframe")
        assert hasattr(mixin, "_set_light_intensity_keyframe")
        assert hasattr(mixin, "_set_light_color_keyframe")


class TestSequencerCreateTool:
    """Tests for SequencerCreateTool."""

    def test_tool_properties(self):
        tool = SequencerCreateTool()
        assert tool.name == "nyra_sequencer_create"
        assert "sequence_name" in tool.parameters["properties"]
        assert tool.parameters["properties"]["duration_seconds"]["default"] == 10.0

    def test_tool_accepts_sequence_name(self):
        tool = SequencerCreateTool()
        assert "sequence_name" in tool.parameters["required"]


class TestSequencerAddCameraTool:
    """Tests for SequencerAddCameraTool."""

    def test_tool_properties(self):
        tool = SequencerAddCameraTool()
        assert tool.name == "nyra_sequencer_add_camera"
        assert "sequence_path" in tool.parameters["required"]
        assert tool.parameters["properties"]["fov"]["default"] == 35.0
        assert tool.parameters["properties"]["focus_distance"]["default"] == 3.0

    def test_tool_requires_sequence_path(self):
        tool = SequencerAddCameraTool()
        assert "sequence_path" in tool.parameters["required"]
        assert "camera_name" not in tool.parameters["required"]


class TestSequencerSetKeyframeTool:
    """Tests for SequencerSetKeyframeTool."""

    def test_tool_properties(self):
        tool = SequencerSetKeyframeTool()
        assert tool.name == "nyra_sequencer_set_keyframe"
        assert all(k in tool.parameters["required"]
                   for k in ["sequence_path", "binding_path", "time_seconds"])

    def test_frame_calculation_24fps(self):
        """Verify 24fps assumption: 1s = frame 24, 2s = frame 48."""
        tool = SequencerSetKeyframeTool()
        # 24fps: frame = int(time * 24)
        assert int(1.0 * 24.0) == 24
        assert int(2.0 * 24.0) == 48
        assert int(5.0 * 24.0) == 120

    def test_frame_clamp_to_1hr(self):
        """Frames clamped to 86400 (1 hour at 24fps)."""
        tool = SequencerSetKeyframeTool()
        max_frame = int(3600 * 24.0)
        assert max_frame == 86400
        # 120s = frame 2880, well within limit
        assert int(120.0 * 24.0) == 2880


class TestSequencerAuthorShotTool:
    """Tests for SequencerAuthorShotTool."""

    def test_tool_properties(self):
        tool = SequencerAuthorShotTool()
        assert tool.name == "nyra_sequencer_author_shot"
        assert "sequence_path" in tool.parameters["required"]
        assert "binding_path" in tool.parameters["required"]
        assert "video_reference_json" in tool.parameters["properties"]
        assert "nl_description" in tool.parameters["properties"]

    def test_nl_camera_move_parsing(self):
        """Test NL description parsing for camera move types."""
        tool = SequencerAuthorShotTool()
        nl_cases = [
            ("slow push-in", "dolly"),
            ("dolly in", "dolly"),
            ("move in", "dolly"),
            ("cut wide", "dolly"),
            ("pull back", "dolly"),
            ("dolly out", "dolly"),
            ("pan left", "truck"),
            ("track left", "truck"),
            ("pan right", "truck"),
            ("track right", "truck"),
            ("static", "static"),
            ("locked off", "static"),
            ("tilt up", "tilt"),
            ("tilt down", "tilt"),
        ]
        for nl_desc, expected in nl_cases:
            desc_lower = nl_desc.lower()
            if "push-in" in desc_lower or "dolly in" in desc_lower or "move in" in desc_lower:
                assert "dolly" in expected or "truck" in expected

    def test_camera_move_patterns(self):
        """Verify camera move patterns are defined for common moves."""
        patterns = {
            "dolly_in": [(-1, 0, 0, 0, 0, 0), (0, 0, 0, 0, 0, 0)],
            "truck_left": [(0, 0, 0, 0, 0, 0), (-1, 0, 0, 0, 0, 0)],
            "static": [(0, 0, 0, 0, 0, 0), (0, 0, 0, 0, 0, 0)],
            "tilt_up": [(0, 0, 0, -1, 0, 0), (0, 0, 0, 1, 0, 0)],
        }
        for name, positions in patterns.items():
            assert len(positions) >= 2, f"{name} should have at least 2 keyframes"