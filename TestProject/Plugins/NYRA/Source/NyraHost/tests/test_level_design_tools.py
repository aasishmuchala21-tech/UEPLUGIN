"""Phase 9 LDA-01 — tests for nyrahost.tools.level_design_tools."""
from __future__ import annotations

import asyncio
import json

import pytest

from nyrahost.tools import level_design_tools as ld
from nyrahost.tools.blockout_primitives import (
    BlockoutSpec,
    BlockoutValidationError,
    MAX_ROOMS_PER_BLOCKOUT,
)


def _two_room_with_door() -> dict:
    return {
        "rooms": [
            {"width_cm": 800, "depth_cm": 600, "height_cm": 300,
             "door_wall": "north", "door_w": 100, "door_h": 220},
            {"width_cm": 600, "depth_cm": 400, "height_cm": 280,
             "door_wall": "none"},
        ],
        "staircases": [{"steps": 12, "step_w": 120, "step_h": 18, "step_d": 30}],
        "spawn_at": {"x": 0, "y": 0, "z": 0},
    }


# (1) BlockoutSpec.from_dict validates input types
def test_from_dict_validates_types():
    bad = {"rooms": "not a list"}
    with pytest.raises(BlockoutValidationError):
        BlockoutSpec.from_dict(bad)
    bad2 = {"rooms": [{"door_wall": "diagonal"}]}
    with pytest.raises(BlockoutValidationError):
        BlockoutSpec.from_dict(bad2)


# (2) Template renders with no leftover ${...} for the canonical spec
def test_template_renders_no_leftovers():
    spec = BlockoutSpec.from_dict(_two_room_with_door())
    script = ld.render_blockout_script(spec)
    assert "${" not in script, "unrendered placeholder remains"
    # JSON literal embedded looks valid
    start = script.index("'''") + 3
    end = script.index("'''", start)
    parsed = json.loads(script[start:end])
    assert len(parsed["rooms"]) == 2


# (3) Generated script syntax-checks (compile() does not raise)
def test_template_compiles():
    spec = BlockoutSpec.from_dict(_two_room_with_door())
    script = ld.render_blockout_script(spec)
    compile(script, "<blockout_test>", "exec")


# (4) Async handler returns the right JSON-RPC shape on success
def test_handler_success():
    result = asyncio.run(ld.on_blockout(_two_room_with_door()))
    assert "error" not in result, result
    assert result["language"] == "python"
    assert result["rooms_count"] == 2
    assert result["staircases_count"] == 1
    assert "main(" in result["script"]


# (5) Empty rooms list returns -32036 blockout_empty
def test_empty_rooms_rejected():
    result = asyncio.run(ld.on_blockout({"rooms": []}))
    assert result["error"]["code"] == -32036
    assert result["error"]["message"] == "blockout_empty"


# (6) Too-large blockout returns -32037
def test_too_many_rooms_rejected():
    rooms = [{"width_cm": 100, "depth_cm": 100, "height_cm": 100,
              "door_wall": "none"}] * (MAX_ROOMS_PER_BLOCKOUT + 1)
    result = asyncio.run(ld.on_blockout({"rooms": rooms}))
    assert result["error"]["code"] == -32037
    assert result["error"]["message"] == "blockout_too_large"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
