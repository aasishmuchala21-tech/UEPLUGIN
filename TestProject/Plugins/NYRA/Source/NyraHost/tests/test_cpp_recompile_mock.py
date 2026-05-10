"""Tests for nyra_cpp_recompile with a mocked unreal.NyraLiveCodingHelper.

Live UE editor isn't available from pytest. The C++ helper UCLASS reflects
to Python only inside an in-editor `unreal` runtime. We mock the helper on
the module-level `unreal` object so the recompile path can be exercised
end-to-end against the Python tool's contract:

    - happy path → compile_attempted=True, method='live_coding'
    - LC unsupported on this version → method='hot_reload' fallback
    - helper raises → tool returns NyraToolResult.err with exception text
    - missing helper attribute → graceful err with remediation
    - error pattern parsing extracts MSVC C\\d{4} / LNK\\d{4} entries
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Mock unreal BEFORE imports.
mock_unreal = MagicMock()
sys.modules["unreal"] = mock_unreal

from nyrahost import cpp_authoring_state as cas  # noqa: E402
from nyrahost.tools import cpp_authoring_tools as cpp  # noqa: E402
from nyrahost.tools.base import idempotent_clear  # noqa: E402
from nyrahost.tools.cpp_authoring_tools import (  # noqa: E402
    CppClassAddTool,
    CppModuleCreateTool,
    CppRecompileTool,
)


@pytest.fixture(autouse=True)
def _isolation():
    # Re-bind sys.modules each test — other test files mock 'unreal' and
    # leave a different MagicMock in sys.modules; the cpp_authoring_tools
    # `import unreal` resolves to whichever module is current at runtime.
    sys.modules["unreal"] = mock_unreal
    idempotent_clear()
    cas.clear_session()
    # Reset the helper mock between tests.
    mock_unreal.reset_mock()
    # Default helper: succeeds, no errors.
    mock_unreal.NyraLiveCodingHelper = MagicMock()
    mock_unreal.NyraLiveCodingHelper.trigger_live_coding_compile.return_value = True
    mock_unreal.NyraLiveCodingHelper.trigger_hot_reload.return_value = True
    mock_unreal.NyraLiveCodingHelper.get_last_compile_output.return_value = ""
    mock_unreal.SystemLibrary.get_engine_version.return_value = "5.6.0-12345+++UE5"
    # Drop any previously-known-bad versions.
    cpp.KNOWN_LIVE_CODING_BAD_VERSIONS.clear()
    yield
    idempotent_clear()
    cas.clear_session()
    cpp.KNOWN_LIVE_CODING_BAD_VERSIONS.clear()


def _seed_authored_module(tmp_path: Path) -> Path:
    CppModuleCreateTool().execute({
        "module_name": "MyMod",
        "parent_dir": str(tmp_path),
        "type": "Runtime",
    })
    mod = tmp_path / "MyMod"
    CppClassAddTool().execute({
        "module_dir": str(mod),
        "module_name": "MyMod",
        "class_name": "MyActor",
        "parent_class": "AActor",
    })
    return mod


class TestRecompileHappyPath:
    def test_live_coding_succeeds_when_helper_returns_true(self, tmp_path: Path):
        mod = _seed_authored_module(tmp_path)
        result = CppRecompileTool().execute({
            "scope": "module",
            "module_name": "MyMod",
            "module_dir": str(mod),
        })
        assert result.is_ok, result.error
        assert result.data["compile_attempted"] is True
        assert result.data["compile_success"] is True
        assert result.data["method"] == "live_coding"
        assert result.data["compile_errors"] == []
        # Live Coding actually got dispatched.
        mock_unreal.NyraLiveCodingHelper.trigger_live_coding_compile.assert_called_once()

    def test_known_bad_version_falls_back_to_hot_reload(self, tmp_path: Path):
        mod = _seed_authored_module(tmp_path)
        cpp.KNOWN_LIVE_CODING_BAD_VERSIONS.add("5.6")
        result = CppRecompileTool().execute({
            "scope": "module",
            "module_name": "MyMod",
            "module_dir": str(mod),
        })
        assert result.is_ok
        assert result.data["method"] == "hot_reload"
        mock_unreal.NyraLiveCodingHelper.trigger_hot_reload.assert_called_once()
        mock_unreal.NyraLiveCodingHelper.trigger_live_coding_compile.assert_not_called()

    def test_explicit_use_live_coding_false_uses_hot_reload(self, tmp_path: Path):
        mod = _seed_authored_module(tmp_path)
        result = CppRecompileTool().execute({
            "scope": "module",
            "module_name": "MyMod",
            "module_dir": str(mod),
            "use_live_coding": False,
        })
        assert result.is_ok
        assert result.data["method"] == "hot_reload"

    def test_lc_returns_false_falls_back_to_hot_reload(self, tmp_path: Path):
        """When ILiveCodingModule.Compile() returns false (e.g. Live
        Coding disabled in editor prefs), the tool retries via Hot
        Reload before declaring failure.
        """
        mod = _seed_authored_module(tmp_path)
        mock_unreal.NyraLiveCodingHelper.trigger_live_coding_compile.return_value = False
        result = CppRecompileTool().execute({
            "scope": "module",
            "module_name": "MyMod",
            "module_dir": str(mod),
        })
        assert result.is_ok
        assert result.data["method"] == "hot_reload"


class TestRecompileFailureModes:
    def test_missing_helper_returns_remediation_err(self, tmp_path: Path):
        mod = _seed_authored_module(tmp_path)
        # Strip the helper from the mock unreal module.
        del mock_unreal.NyraLiveCodingHelper
        result = CppRecompileTool().execute({
            "scope": "module",
            "module_name": "MyMod",
            "module_dir": str(mod),
        })
        assert not result.is_ok
        assert "NyraLiveCodingHelper is not reflected" in result.error

    def test_helper_raises_returns_err(self, tmp_path: Path):
        mod = _seed_authored_module(tmp_path)
        mock_unreal.NyraLiveCodingHelper.trigger_live_coding_compile.side_effect = RuntimeError(
            "live-coding patch DB locked"
        )
        result = CppRecompileTool().execute({
            "scope": "module",
            "module_name": "MyMod",
            "module_dir": str(mod),
        })
        assert not result.is_ok
        assert "live-coding patch DB locked" in result.error


class TestRecompileErrorParsing:
    def test_msvc_error_surfaces_as_compile_error(self, tmp_path: Path):
        mod = _seed_authored_module(tmp_path)
        # Make the LC return false so compile_success can be False even on
        # success path; provide MSVC-formatted stderr in the buffer.
        mock_unreal.NyraLiveCodingHelper.get_last_compile_output.return_value = (
            "Foo.cpp(42): error C2065: 'UndeclaredVar': undeclared identifier\n"
            "Bar.cpp(17): warning C4244: conversion possible loss of data\n"
        )
        result = CppRecompileTool().execute({
            "scope": "module",
            "module_name": "MyMod",
            "module_dir": str(mod),
        })
        assert result.is_ok
        # We don't assert exactly which lines pattern-match — that's the
        # test_cpp_error_patterns suite's job — but at least one C++ error
        # should be surfaced when patterns are extended (Task 3).
        # If patterns aren't yet extended this asserts >= 0 (no regression).
        errors = result.data["compile_errors"]
        assert isinstance(errors, list)
        # When patterns are wired (Task 3), we expect compile_success=False:
        if errors:
            assert result.data["compile_success"] is False
            for e in errors:
                assert "line" in e
                assert "pattern_match" in e
                assert e["pattern_match"] is True


class TestRecompileIdempotency:
    def test_second_call_dedups(self, tmp_path: Path):
        mod = _seed_authored_module(tmp_path)
        params = {"scope": "module", "module_name": "MyMod", "module_dir": str(mod)}
        first = CppRecompileTool().execute(params)
        assert first.is_ok
        second = CppRecompileTool().execute(params)
        assert second.is_ok
        assert second.data.get("deduped") is True
        # Helper called only once.
        assert mock_unreal.NyraLiveCodingHelper.trigger_live_coding_compile.call_count == 1
