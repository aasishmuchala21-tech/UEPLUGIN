"""Plan 05-03 backend + screenshot encoder tests.

Covers:
  - PNG encoder produces valid PNG bytes (signature + IEND chunk)
  - Nearest-neighbour resize preserves total dim
  - Anthropic response → ComputerUseLoop action translator handles every
    documented computer_20251124 action shape
"""
from __future__ import annotations

import io
import struct
from types import SimpleNamespace

import pytest

from nyrahost.external.computer_use.actions import (
    _encode_png_rgba,
    _resize_nearest,
)
from nyrahost.external.computer_use.backend_anthropic import (
    _translate_response,
)


class TestPngEncoder:
    def test_signature_and_iend(self):
        rgba = bytes([255, 0, 0, 255] * 4)  # 2x2 red
        png = _encode_png_rgba(rgba, 2, 2)
        # PNG signature
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        # IEND chunk at end
        assert png[-12:] == (
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    def test_ihdr_dimensions_round_trip(self):
        png = _encode_png_rgba(bytes([0, 0, 0, 255] * 6), 3, 2)
        # IHDR chunk starts at offset 8 (after signature)
        # length(4) + tag(4) + data(13) layout
        ihdr_data_offset = 8 + 4 + 4
        w, h = struct.unpack(">II", png[ihdr_data_offset:ihdr_data_offset + 8])
        assert (w, h) == (3, 2)


class TestResizeNearest:
    def test_4x_to_2x_halves_dim(self):
        # 4x1 RGBA: red, green, blue, white
        src = bytes([
            255, 0, 0, 255,
            0, 255, 0, 255,
            0, 0, 255, 255,
            255, 255, 255, 255,
        ])
        out = _resize_nearest(src, 4, 1, 2, 1)
        assert len(out) == 2 * 1 * 4

    def test_identity_returns_input(self):
        src = bytes([10, 20, 30, 255] * 4)
        out = _resize_nearest(src, 2, 2, 2, 2)
        assert out == src


class TestTranslateAnthropicResponse:
    def test_no_tool_use_returns_done_with_summary(self):
        resp = SimpleNamespace(content=[
            SimpleNamespace(type="text", text="DONE — task complete."),
        ])
        out = _translate_response(resp)
        assert out["action"] == "done"
        assert "DONE" in out["summary"]

    def test_left_click_translated(self):
        tool_use = SimpleNamespace(
            type="tool_use",
            name="computer",
            input={"action": "left_click", "coordinate": [123, 456]},
        )
        resp = SimpleNamespace(content=[tool_use])
        out = _translate_response(resp)
        assert out == {
            "action": "click", "x": 123, "y": 456, "button": "left",
        }

    def test_right_click_translated(self):
        tool_use = SimpleNamespace(
            type="tool_use",
            name="computer",
            input={"action": "right_click", "coordinate": [10, 20]},
        )
        out = _translate_response(SimpleNamespace(content=[tool_use]))
        assert out["action"] == "click"
        assert out["button"] == "right"

    def test_double_click_translated(self):
        tool_use = SimpleNamespace(
            type="tool_use",
            name="computer",
            input={"action": "double_click", "coordinate": [50, 60]},
        )
        out = _translate_response(SimpleNamespace(content=[tool_use]))
        assert out == {"action": "double_click", "x": 50, "y": 60}

    def test_scroll_up_translated(self):
        tool_use = SimpleNamespace(
            type="tool_use",
            name="computer",
            input={
                "action": "scroll",
                "coordinate": [100, 100],
                "scroll_amount": 3,
                "scroll_direction": "up",
            },
        )
        out = _translate_response(SimpleNamespace(content=[tool_use]))
        assert out["action"] == "scroll"
        assert out["delta"] == 3 * 120  # positive = up

    def test_scroll_down_negative_delta(self):
        tool_use = SimpleNamespace(
            type="tool_use",
            name="computer",
            input={
                "action": "scroll",
                "coordinate": [0, 0],
                "scroll_amount": 2,
                "scroll_direction": "down",
            },
        )
        out = _translate_response(SimpleNamespace(content=[tool_use]))
        assert out["delta"] == -2 * 120

    def test_type_translated(self):
        tool_use = SimpleNamespace(
            type="tool_use",
            name="computer",
            input={"action": "type", "text": "hello"},
        )
        out = _translate_response(SimpleNamespace(content=[tool_use]))
        assert out == {"action": "type_text", "text": "hello", "vk_code": 0}

    def test_wait_translated(self):
        tool_use = SimpleNamespace(
            type="tool_use",
            name="computer",
            input={"action": "wait", "duration": 2.5},
        )
        out = _translate_response(SimpleNamespace(content=[tool_use]))
        assert out == {"action": "wait", "seconds": 2.5}

    def test_screenshot_translated(self):
        tool_use = SimpleNamespace(
            type="tool_use",
            name="computer",
            input={"action": "screenshot"},
        )
        out = _translate_response(SimpleNamespace(content=[tool_use]))
        assert out == {"action": "screenshot"}

    def test_unknown_action_returns_done(self):
        tool_use = SimpleNamespace(
            type="tool_use",
            name="computer",
            input={"action": "wave_hello"},
        )
        out = _translate_response(SimpleNamespace(content=[tool_use]))
        assert out["action"] == "done"
        assert "wave_hello" in out["summary"]
