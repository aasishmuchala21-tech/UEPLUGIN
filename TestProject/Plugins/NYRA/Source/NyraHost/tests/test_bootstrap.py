"""Bootstrap venv + offline wheel install tests.
VALIDATION test ID: 1-02-06
"""
from __future__ import annotations
import sys
from pathlib import Path

from nyrahost.bootstrap import ensure_venv, VENV_MARKER_FILENAME

# We use the system Python that runs pytest as the "embedded interpreter"
# for the unit-test scenarios — the real embedded CPython lives under
# Binaries/Win64/NyraHost/cpython/ and is tested by an integration test.


def test_bootstrap_idempotent(tmp_path: Path) -> None:
    venv = tmp_path / "venv"
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    reqs = tmp_path / "requirements.lock"
    reqs.write_text("")  # empty lock -> nothing to install

    p1 = ensure_venv(
        python_exe=Path(sys.executable),
        venv_dir=venv,
        wheels_dir=wheels,
        requirements_lock=reqs,
        plugin_version="0.1.0",
    )
    assert p1.exists()
    marker = venv / VENV_MARKER_FILENAME
    assert marker.read_text(encoding="utf-8").strip() == "0.1.0"

    # Second call: no-op (marker matches)
    mtime_before = marker.stat().st_mtime
    p2 = ensure_venv(
        python_exe=Path(sys.executable),
        venv_dir=venv,
        wheels_dir=wheels,
        requirements_lock=reqs,
        plugin_version="0.1.0",
    )
    assert p2 == p1
    assert marker.stat().st_mtime == mtime_before


def test_bootstrap_rebuilds_on_version_change(tmp_path: Path) -> None:
    venv = tmp_path / "venv"
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    reqs = tmp_path / "requirements.lock"
    reqs.write_text("")

    ensure_venv(
        python_exe=Path(sys.executable),
        venv_dir=venv,
        wheels_dir=wheels,
        requirements_lock=reqs,
        plugin_version="0.1.0",
    )
    # Second call with new version -> full rebuild
    ensure_venv(
        python_exe=Path(sys.executable),
        venv_dir=venv,
        wheels_dir=wheels,
        requirements_lock=reqs,
        plugin_version="0.2.0",
    )
    assert (venv / VENV_MARKER_FILENAME).read_text(encoding="utf-8").strip() == "0.2.0"
