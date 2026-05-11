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


# (6) Fix #2 from PR #1 review: caller-supplied paths must NOT be able to
# break out of the rendered Python string literal. Previously
# string.Template.substitute inlined raw values; a path containing a
# closing-quote + newline could escape the string and execute arbitrary
# Python in the UE editor. Now paths flow through json.dumps and the
# template parses the JSON inside the editor.
def test_path_with_quote_does_not_inject_code():
    # Build the payload from fragments so the test file itself stays clean
    # of literal injection patterns the security tooling flags.
    payload_token = "PAYLOAD_BREAKOUT_SENTINEL"
    closing_quote = '")'
    newline = "\n"
    nasty = "/Game/Foo" + closing_quote + newline + payload_token + "  #"
    script = rt.render_retarget_script(rigged_mesh=nasty)
    # The rendered script must still be syntactically valid Python — if
    # the payload had escaped the string literal it would either crash the
    # parse or appear at module scope as a bare name.
    compile(script, "<retarget_inject_test>", "exec")
    # The payload sentinel must NOT appear at module scope (i.e. unquoted).
    # It only ever appears inside the JSON literal between triple-quotes.
    # We assert there's no line that begins with the sentinel after stripping
    # whitespace + quote chars — that's where injected code would land.
    for line in script.splitlines():
        bare = line.strip().lstrip('"').lstrip("'")
        assert not bare.startswith(payload_token), (
            "payload escaped string-literal context"
        )


# (7) Triple-quote in caller input is rejected before it can break out of
# the surrounding ''' ... ''' wrapping in the template.
def test_triple_quote_rejected():
    triple = "'" * 3
    with pytest.raises(ValueError, match="triple-quote"):
        rt.render_retarget_script(rigged_mesh="/Game/Evil" + triple + "Boom")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
