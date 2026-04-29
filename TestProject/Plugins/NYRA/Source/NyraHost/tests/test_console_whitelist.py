"""Tests for nyra_console_exec whitelist classifier (Plan 02-10)."""
from __future__ import annotations

import pytest

from nyrahost.console import classify_command


class TestTierA:
    """Tier A commands: auto-approved, read-only."""

    def test_stat_fps(self):
        assert classify_command("stat fps") == "A"

    def test_stat_unit(self):
        assert classify_command("stat unit") == "A"

    def test_stat_scenerendering(self):
        assert classify_command("stat scenerendering") == "A"

    def test_showflag_bones(self):
        assert classify_command("showflag.bones 1") == "A"

    def test_showflag_bones_off(self):
        assert classify_command("showflag.bones 0") == "A"

    def test_log_verbosity(self):
        assert classify_command("log LogTemp verbose") == "A"

    def test_help_exact(self):
        assert classify_command("help") == "A"

    def test_help_prefix(self):
        assert classify_command("help stat") == "A"

    def test_r_vsync_no_arg(self):
        assert classify_command("r.VSync") == "A"

    def test_r_vsync_with_arg(self):
        assert classify_command("r.VSync 1") == "A"

    def test_r_screenpercentage(self):
        assert classify_command("r.ScreenPercentage 50") == "A"

    def test_obj_classes(self):
        assert classify_command("obj classes") == "A"

    def test_obj_hierarchy(self):
        assert classify_command("obj hierarchy") == "A"


class TestTierB:
    """Tier B commands: preview-gated via Plan 02-09."""

    def test_generic_r_cvar(self):
        assert classify_command("r.FogDensity 2") == "B"
        assert classify_command("r.MyCVar 1") == "B"

    def test_profilegpu(self):
        assert classify_command("profilegpu") == "B"


class TestTierC:
    """Tier C commands: hard-blocked."""

    def test_quit(self):
        assert classify_command("quit") == "C"

    def test_exit(self):
        assert classify_command("exit") == "C"

    def test_exitnow(self):
        assert classify_command("exitnow") == "C"

    def test_exec_file_prefix(self):
        assert classify_command("exec hack.txt") == "C"

    def test_reloadshaders(self):
        assert classify_command("reloadshaders") == "C"

    def test_obj_gc(self):
        assert classify_command("obj gc") == "C"

    def test_gc_collectgarbage(self):
        assert classify_command("gc.CollectGarbage") == "C"

    def test_travel(self):
        assert classify_command("travel MapName") == "C"

    def test_open(self):
        assert classify_command("open MapName") == "C"

    def test_debugcreateplayer(self):
        assert classify_command("debugcreateplayer") == "C"


class TestDefaultDeny:
    """Unmapped commands default to Tier C (deny)."""

    def test_unknown_command(self):
        assert classify_command("viewmode shadercomplexity") == "C"

    def test_unknown_command_random(self):
        assert classify_command("foobar") == "C"


class TestTierPrecedence:
    """Tier C beats B beats A."""

    def test_tier_c_wins_over_b(self):
        """A command that might match multiple tiers — C wins."""
        # e.g. "quit" matches exact C; "stat quit" would still be C
        assert classify_command("quit") == "C"

    def test_whitespace_stripped(self):
        assert classify_command("  stat fps  ") == "A"

    def test_case_insensitive(self):
        assert classify_command("STAT FPS") == "A"
        assert classify_command("QUIT") == "C"
        assert classify_command("r.VSync") == "A"