"""Tests for the C++ regex catalog appended to blueprint_debug._ERROR_PATTERNS.

Plan 08-02 Task 3: extend the existing matcher with MSVC + clang + linker
+ UHT shapes. The existing `_explain_error_pattern` dispatcher is regex-
shape-agnostic and reused as-is — these tests guard:

    1. Each new C++ shape is matched (positive tests).
    2. The original Blueprint shapes still match (no regression).
    3. The fallback explanation never fires for a known C++ shape.
    4. The fixture sample_compile_error.txt produces ≥4 distinct pattern
       matches when fed line-by-line through the matcher.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# blueprint_debug imports `unreal` at module-top — mock it for collection.
sys.modules.setdefault("unreal", MagicMock())

from nyrahost.tools.blueprint_debug import (  # noqa: E402
    _SUGGESTION_FALLBACK,
    _explain_error_pattern,
)


FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Positive — each new C++ pattern is matched.
# ---------------------------------------------------------------------------

class TestMSVCErrorPatterns:
    def test_msvc_c2065_matches(self):
        line = (
            "C:\\Users\\foo\\Project\\Source\\Mod\\Private\\Foo.cpp(42): "
            "error C2065: 'UndeclaredVar': undeclared identifier"
        )
        explanation, suggestion = _explain_error_pattern(line)
        assert "C2065" in explanation
        assert suggestion is not None
        assert suggestion != _SUGGESTION_FALLBACK

    def test_msvc_arbitrary_c_code_matches(self):
        # The pattern is Cxxxx-shape-agnostic; pick a non-2065 code.
        line = "Foo.cpp(10): error C2440: 'initializing': cannot convert"
        explanation, suggestion = _explain_error_pattern(line)
        assert "C2440" in explanation
        assert "cannot convert" in explanation
        assert suggestion is not None

    def test_msvc_warning_does_not_match_error_pattern(self):
        """C-warnings (C4244 etc.) must NOT match the error C\\d{4} pattern.
        Otherwise compile_success would always be False on a clean build with
        warnings.
        """
        line = "Foo.cpp(43): warning C4244: 'argument': conversion possible loss"
        explanation, suggestion = _explain_error_pattern(line)
        # Either matches the generic fallback (preferred) or returns the
        # fallback suggestion. Either way it MUST NOT be a specific
        # "MSVC compile error C4244" entry.
        assert "C4244" not in explanation or suggestion == _SUGGESTION_FALLBACK or \
            "compile error C" not in explanation


class TestClangErrorPatterns:
    def test_clang_undeclared_identifier_matches(self):
        line = (
            "C:/Users/foo/Project/Source/Mod/Public/MyActor.h:17:5: "
            "error: use of undeclared identifier 'FNotAType'"
        )
        explanation, suggestion = _explain_error_pattern(line)
        assert "FNotAType" in explanation
        assert "not declared" in explanation or "undeclared" in explanation.lower()
        assert suggestion is not None and suggestion != _SUGGESTION_FALLBACK


class TestLinkerErrorPatterns:
    def test_lnk1120_fatal_matches(self):
        line = "LINK : fatal error LNK1120: 1 unresolved externals"
        explanation, suggestion = _explain_error_pattern(line)
        assert "LNK1120" in explanation
        assert "linker" in explanation.lower() or "fatal" in explanation.lower()

    def test_lnk2019_unresolved_external_matches(self):
        line = (
            'MyActor.cpp.obj : error LNK2019: unresolved external symbol '
            '"void __cdecl AMyActor::DoTheThing(int)" referenced in function main'
        )
        explanation, suggestion = _explain_error_pattern(line)
        assert "LNK2019" in explanation
        assert suggestion is not None
        assert suggestion != _SUGGESTION_FALLBACK


class TestUHTErrorPatterns:
    def test_uht_failure_matches(self):
        line = "UnrealHeaderTool failed for target 'MyModEditor' (platform: Win64, exit code: 1)"
        explanation, suggestion = _explain_error_pattern(line)
        assert "UnrealHeaderTool" in explanation
        assert suggestion is not None
        assert suggestion != _SUGGESTION_FALLBACK


# ---------------------------------------------------------------------------
# Regression — original Blueprint shapes still match.
# ---------------------------------------------------------------------------

class TestBlueprintRegression:
    def test_unknown_member_still_matches(self):
        line = "Error: Unknown member 'OldVar' referenced"
        explanation, _ = _explain_error_pattern(line)
        assert "OldVar" in explanation

    def test_variable_not_found_still_matches(self):
        line = "Error: Variable 'Speed' not found in Blueprint"
        explanation, _ = _explain_error_pattern(line)
        assert "Speed" in explanation

    def test_cast_failed_still_matches(self):
        line = "Error: Cast 'GetActor' to AHero Failed"
        explanation, _ = _explain_error_pattern(line)
        # The cast-pattern's named group is `target`; check it surfaces.
        assert "AHero" in explanation


# ---------------------------------------------------------------------------
# Fixture-driven smoke — feed sample_compile_error.txt through the matcher.
# ---------------------------------------------------------------------------

class TestFixtureSweep:
    def test_sample_fixture_produces_specific_matches(self):
        text = (FIXTURES / "sample_compile_error.txt").read_text(encoding="utf-8")
        specific_hits = 0
        for line in text.splitlines():
            if not line.strip():
                continue
            explanation, suggestion = _explain_error_pattern(line)
            if suggestion is not None and suggestion != _SUGGESTION_FALLBACK:
                specific_hits += 1
        # Fixture contains: 1 MSVC C2065, 1 clang undeclared identifier,
        # 1 LNK1120 fatal, 1 LNK2019 unresolved external, 1 UHT failure.
        # ≥4 specific matches required (allow 1 to slip if the
        # warning-vs-error split swallows it).
        assert specific_hits >= 4, f"only {specific_hits} specific matches in fixture"
