"""Phase 11-B — ChatHandlers._instructions_prefix tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from nyrahost.custom_instructions import CustomInstructions
from nyrahost.handlers.chat import ChatHandlers


class _FakeStorage:
    pass


class _FakeRouter:
    pass


def _make(tmp_path: Path, body: str | None = None) -> ChatHandlers:
    ci = None
    if body is not None:
        ci = CustomInstructions(project_dir=tmp_path)
        ci.save(body)
    return ChatHandlers(
        storage=_FakeStorage(),
        router=_FakeRouter(),
        project_saved=tmp_path / "Saved",
        custom_instructions=ci,
    )


def test_no_instructions_returns_empty(tmp_path):
    h = _make(tmp_path)
    assert h._instructions_prefix() == ""


def test_with_instructions_returns_prefix(tmp_path):
    h = _make(tmp_path, "Use British spelling.")
    out = h._instructions_prefix()
    assert "# Project custom instructions" in out
    assert "Use British spelling." in out


def test_malformed_instructions_does_not_crash(tmp_path):
    """If CustomInstructions.system_prompt_prefix raises (e.g. file
    deleted between read and use), chat must not die."""
    class _BoomCI:
        def system_prompt_prefix(self):
            raise RuntimeError("disk gone")

    h = ChatHandlers(
        storage=_FakeStorage(),
        router=_FakeRouter(),
        project_saved=tmp_path,
        custom_instructions=_BoomCI(),
    )
    assert h._instructions_prefix() == ""


def test_instructions_refresh_picks_up_new_body(tmp_path):
    """After settings/set-instructions saves a new body, the cached prefix
    seen by chat must reflect it on the next call."""
    ci = CustomInstructions(project_dir=tmp_path)
    h = ChatHandlers(
        storage=_FakeStorage(),
        router=_FakeRouter(),
        project_saved=tmp_path,
        custom_instructions=ci,
    )
    assert h._instructions_prefix() == ""
    ci.save("Naming: BP_*.")
    pref = h._instructions_prefix()
    assert "Naming: BP_*." in pref


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
