"""Plan 06-04: DEMO-01 canary tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nyrahost.canary.demo01_canary import (
    CanaryResult,
    VERDICT_FAIL,
    VERDICT_PARTIAL,
    VERDICT_PASS,
    grade_verdict,
    main,
    run_canary,
)
from nyrahost.tools.base import NyraToolResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def canary_image(tmp_path: Path) -> Path:
    img = tmp_path / "canary_image.jpg"
    img.write_bytes(b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00")
    return img


class _FakeMeshy:
    def __init__(self, asset_path="/Game/Meshy/Generated.uasset", error=None):
        self.asset_path = asset_path
        self.error = error

    def execute(self, params):
        if self.error:
            return NyraToolResult.err(self.error)
        return NyraToolResult.ok({"asset_path": self.asset_path})


class _FakeComfyUI:
    def __init__(self, asset_path="/Game/ComfyUI/M_Generated.uasset"):
        self.asset_path = asset_path

    def execute(self, params):
        return NyraToolResult.ok({"asset_path": self.asset_path})


# ---------------------------------------------------------------------------
# run_canary core behaviour
# ---------------------------------------------------------------------------

def test_run_canary_missing_image_records_error(tmp_path):
    result = run_canary(test_image=tmp_path / "ghost.png")
    assert result.errors
    assert "not found" in result.errors[0]


def test_run_canary_with_library_hits_passes(canary_image, tmp_path):
    result = run_canary(
        test_image=canary_image,
        library_search=lambda hint, role: f"/Game/Library/{role}.{role}",
        asset_pool_root=tmp_path / "pool",
    )
    assert not result.errors
    assert result.actor_count >= 4
    assert result.material_count >= 1
    assert result.placeholder_actors == 0
    assert result.placeholder_materials == 0


def test_run_canary_with_meshy_only_marks_partial(canary_image, tmp_path):
    """Library miss + Meshy hit = no placeholders for actors. ComfyUI absent =
    placeholder materials. Verdict should be PARTIAL because *some* placeholders
    engaged."""
    result = run_canary(
        test_image=canary_image,
        meshy_tool=_FakeMeshy(),
        comfyui_tool=None,
        library_search=lambda h, r: None,
        asset_pool_root=tmp_path / "pool",
    )
    verdict = grade_verdict(result)
    assert verdict == VERDICT_PARTIAL
    assert result.placeholder_actors == 0
    assert result.placeholder_materials >= 1


def test_run_canary_cold_start_no_external_services_partial(canary_image, tmp_path):
    """Library miss + no Meshy + no ComfyUI = full placeholder fallback.
    Verdict is PARTIAL (acceptable degraded), not FAIL."""
    result = run_canary(
        test_image=canary_image,
        library_search=lambda h, r: None,
        asset_pool_root=tmp_path / "pool",
    )
    verdict = grade_verdict(result)
    # Counts still meet thresholds because stub blueprint guarantees actors.
    assert result.actor_count >= 4
    assert verdict == VERDICT_PARTIAL


def test_run_canary_threshold_failure_returns_fail(canary_image, tmp_path):
    result = run_canary(
        test_image=canary_image,
        library_search=lambda hint, role: f"/Game/Library/{role}.{role}",
        asset_pool_root=tmp_path / "pool",
        expect_min_actors=999,
    )
    verdict = grade_verdict(result)
    assert verdict == VERDICT_FAIL


# ---------------------------------------------------------------------------
# grade_verdict pure logic
# ---------------------------------------------------------------------------

def test_grade_verdict_clean_returns_pass():
    result = CanaryResult()
    result.actor_count = 5
    result.material_count = 2
    result.lighting_count = 1
    assert grade_verdict(result) == VERDICT_PASS


def test_grade_verdict_with_errors_returns_fail():
    result = CanaryResult()
    result.errors.append("something broke")
    assert grade_verdict(result) == VERDICT_FAIL


def test_grade_verdict_demo_mode_flag_returns_fail():
    result = CanaryResult()
    result.demo_mode_flag_present = True
    assert grade_verdict(result) == VERDICT_FAIL


def test_grade_verdict_with_placeholder_actor_returns_partial():
    result = CanaryResult()
    result.placeholder_actors = 1
    assert grade_verdict(result) == VERDICT_PARTIAL


def test_grade_verdict_with_placeholder_material_returns_partial():
    result = CanaryResult()
    result.placeholder_materials = 1
    assert grade_verdict(result) == VERDICT_PARTIAL


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def test_main_returns_partial_exit_code_on_cold_start(canary_image, capsys):
    rc = main(["--test-image", str(canary_image), "--json"])
    captured = capsys.readouterr()
    assert rc in {VERDICT_PASS, VERDICT_PARTIAL}
    # structlog may emit warnings to stdout; pull the single JSON line out.
    json_lines = [ln for ln in captured.out.splitlines() if ln.strip().startswith("{")]
    assert json_lines, f"no JSON line in stdout: {captured.out!r}"
    payload = json.loads(json_lines[-1])
    assert payload["verdict"] in {"pass", "partial"}
    assert payload["actor_count"] >= 4


def test_main_returns_fail_exit_code_on_missing_image(tmp_path, capsys):
    rc = main(["--test-image", str(tmp_path / "missing.png")])
    assert rc == VERDICT_FAIL
    captured = capsys.readouterr()
    assert "FAIL" in captured.out
