"""Phase 10-1 — tests for custom_instructions.py + handlers/instructions.py."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from nyrahost.custom_instructions import (
    CustomInstructions,
    MAX_BODY_BYTES,
    instructions_path,
)
from nyrahost.handlers.instructions import InstructionsHandlers


def test_load_empty_when_absent(tmp_path):
    inst = CustomInstructions(project_dir=tmp_path)
    assert inst.body == ""
    assert inst.system_prompt_prefix() == ""


def test_save_then_load_roundtrip(tmp_path):
    inst = CustomInstructions(project_dir=tmp_path)
    body = "Use British spelling. Prefer Lyra over Lyra-3.\n"
    path = inst.save(body)
    # File on disk
    assert path == instructions_path(tmp_path)
    assert path.read_text(encoding="utf-8") == body
    # Cache populated
    assert inst.body == body
    # New loader pulls same value
    inst2 = CustomInstructions(project_dir=tmp_path)
    assert inst2.body == body


def test_system_prompt_prefix_wraps_body(tmp_path):
    inst = CustomInstructions(project_dir=tmp_path)
    inst.save("Be concise.\n")
    pref = inst.system_prompt_prefix()
    assert pref.startswith("# Project custom instructions")
    assert "Be concise." in pref
    assert pref.endswith("---\n\n")


def test_too_large_raises(tmp_path):
    inst = CustomInstructions(project_dir=tmp_path)
    with pytest.raises(ValueError):
        inst.save("x" * (MAX_BODY_BYTES + 1))


def test_atomic_write_no_partial_on_disk(tmp_path):
    """After save() there should be no .tmp file left lying around."""
    inst = CustomInstructions(project_dir=tmp_path)
    inst.save("Hello.")
    nyra_dir = tmp_path / "Saved" / "NYRA"
    leftover = list(nyra_dir.glob(".instructions.*.tmp"))
    assert leftover == [], f"tempfile not cleaned up: {leftover}"


# --- handlers/instructions.py ---

def test_handler_get_empty(tmp_path):
    h = InstructionsHandlers(CustomInstructions(project_dir=tmp_path))
    out = asyncio.run(h.on_get({}))
    assert out["body"] == ""
    assert out["max_bytes"] == MAX_BODY_BYTES


def test_handler_set_then_get(tmp_path):
    inst = CustomInstructions(project_dir=tmp_path)
    h = InstructionsHandlers(inst)
    set_res = asyncio.run(h.on_set({"body": "Naming: BP_*."}))
    assert set_res["saved"] is True
    assert set_res["chars"] == len("Naming: BP_*.")
    # Get returns the persisted body
    get_res = asyncio.run(h.on_get({}))
    assert get_res["body"] == "Naming: BP_*."


def test_handler_set_missing_body(tmp_path):
    h = InstructionsHandlers(CustomInstructions(project_dir=tmp_path))
    out = asyncio.run(h.on_set({}))
    assert out["error"]["code"] == -32602
    assert out["error"]["message"] == "missing_field"


def test_handler_set_too_large(tmp_path):
    h = InstructionsHandlers(CustomInstructions(project_dir=tmp_path))
    out = asyncio.run(h.on_set({"body": "x" * (MAX_BODY_BYTES + 1)}))
    assert out["error"]["code"] == -32041
    assert out["error"]["message"] == "instructions_too_large"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
