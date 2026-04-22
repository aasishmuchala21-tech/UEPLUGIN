"""Bootstrap: create venv + install wheels offline; rebuild on version mismatch.

Implements CONTEXT.md D-14 (pre-resolved wheel cache + marker-file rebuild) and
RESEARCH §3.10 P1.3 (venv-corruption marker).

The embedded CPython from python-build-standalone (D-13) is the `python_exe`
argument. The venv lives OUTSIDE the plugin dir (default:
`%LOCALAPPDATA%/NYRA/venv/`) so Fab-updating the plugin binary folder never
nukes the user's venv state. A plugin-version marker file triggers a full
rebuild on version change.
"""
from __future__ import annotations
import os
import shutil
import subprocess
import sys
from pathlib import Path

VENV_MARKER_FILENAME = "nyra-plugin-version.txt"
NYRA_PLUGIN_VERSION = "0.1.0"  # bump to trigger venv rebuild on plugin update


def default_venv_path() -> Path:
    """Resolve the default venv location.

    On Windows (production): `%LOCALAPPDATA%/NYRA/venv/`.
    On POSIX dev machines (tests, macOS/Linux devs): `~/.local/share/NYRA/venv/`.
    """
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / "NYRA" / "venv"
    # Fallback for non-Windows dev machines running tests
    return Path.home() / ".local" / "share" / "NYRA" / "venv"


def _read_marker(venv: Path) -> str | None:
    m = venv / VENV_MARKER_FILENAME
    if not m.exists():
        return None
    return m.read_text(encoding="utf-8").strip()


def _write_marker(venv: Path, version: str) -> None:
    (venv / VENV_MARKER_FILENAME).write_text(version + "\n", encoding="utf-8")


def _venv_python_exe(venv: Path) -> Path:
    """Windows venv layout: <venv>/Scripts/python.exe; POSIX: <venv>/bin/python."""
    if sys.platform == "win32":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def ensure_venv(
    *,
    python_exe: Path,
    venv_dir: Path | None = None,
    wheels_dir: Path,
    requirements_lock: Path,
    plugin_version: str = NYRA_PLUGIN_VERSION,
) -> Path:
    """Idempotent: create venv at venv_dir, install wheels from wheels_dir,
    write marker. If marker mismatches plugin_version, rmtree and rebuild.

    Returns path to the venv's python executable (Scripts/python.exe on
    Windows, bin/python on POSIX).
    """
    venv = venv_dir or default_venv_path()
    existing = _read_marker(venv)
    if existing == plugin_version:
        # Already bootstrapped at this version — idempotent no-op
        return _venv_python_exe(venv)
    if venv.exists():
        shutil.rmtree(venv, ignore_errors=True)
    venv.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(python_exe), "-m", "venv", "--copies", str(venv)],
        check=True,
    )
    # Offline wheel install
    venv_py = _venv_python_exe(venv)
    subprocess.run(
        [
            str(venv_py), "-m", "pip", "install",
            "--no-index",
            "--find-links", str(wheels_dir),
            "-r", str(requirements_lock),
        ],
        check=True,
    )
    _write_marker(venv, plugin_version)
    return venv_py
