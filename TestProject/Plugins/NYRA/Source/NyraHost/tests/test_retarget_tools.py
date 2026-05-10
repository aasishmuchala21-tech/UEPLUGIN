"""Phase 9 RIG-02 — tests for nyrahost.tools.retarget_tools (template renderer)."""
from __future__ import annotations

import asyncio

import pytest

from nyrahost.tools import retarget_tools as rt


# (1) Template renders with no leftover ${...} placeholders
def test_template_renders_no_leftovers():
    script = rt.render_retarget_script(
        rigged_mesh="/Game/NYRA/Rigged/SK_Hero",
    )
    assert "${" not in script, "unrendered placeholder remains"
    # Spot-check the canonical Phase 0.B mappings landed
    assert "set_retarget_root(\"pelvis\")" in script
    assert 'add_retarget_chain("LeftArm",   "upperarm_l","hand_l",   "hand_l_goal")' in script
    assert "IKRetargetBatchOperation.duplicate_and_retarget" in script


# (2) Generated script syntax-checks
def test_template_compiles():
    script = rt.render_retarget_script(rigged_mesh="/Game/NYRA/Rigged/SK_Hero")
    compile(script, "<retarget_test>", "exec")  # raises SyntaxError on bad render


# (3) Custom asset paths flow through
def test_custom_paths():
    script = rt.render_retarget_script(
        rigged_mesh="/Game/Custom/SK_Robot",
        source_mesh="/Game/Custom/SK_OldRobot",
        source_rig="/Game/Custom/IK_OldRobot",
        out_path="/Game/Custom/Retargeted",
    )
    assert "/Game/Custom/SK_Robot" in script
    assert "/Game/Custom/SK_OldRobot" in script
    assert "/Game/Custom/IK_OldRobot" in script
    assert "/Game/Custom/Retargeted" in script


# (4) Async handler returns rendered script in the JSON-RPC envelope
def test_handler_success():
    result = asyncio.run(rt.on_retarget({"rigged_mesh": "/Game/NYRA/SK_Hero"}))
    assert "error" not in result
    assert result["language"] == "python"
    assert "auto_rig_and_retarget" in result["script"]


# (5) Missing rigged_mesh returns -32602 missing_field
def test_missing_rigged_mesh():
    result = asyncio.run(rt.on_retarget({}))
    assert result["error"]["code"] == -32602
    assert result["error"]["message"] == "missing_field"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
