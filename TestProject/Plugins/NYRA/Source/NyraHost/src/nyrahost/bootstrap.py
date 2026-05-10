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


class BootstrapError(RuntimeError):
    """Raised when venv creation or wheel install fails.

    WR-11: provides a structured surface (stage, command, stderr,
    remediation) so the supervisor can map the failure to a JSON-RPC
    error envelope without scraping subprocess output. ``stage`` is one
    of ``"create_venv" | "install_wheels"`` so UE-side telemetry can
    distinguish a missing python_exe from a corrupted wheel cache.
    """

    def __init__(
        self,
        stage: str,
        *,
        command: list[str],
        returncode: int,
        stderr: str,
        remediation: str,
    ) -> None:
        super().__init__(f"bootstrap_failed[{stage}]: rc={returncode}")
        self.stage = stage
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        self.remediation = remediation


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
    create_cmd = [str(python_exe), "-m", "venv", "--copies", str(venv)]
    create_result = subprocess.run(
        create_cmd, capture_output=True, text=True,
    )
    if create_result.returncode != 0:
        raise BootstrapError(
            "create_venv",
            command=create_cmd,
            returncode=create_result.returncode,
            stderr=(create_result.stderr or "")[-2000:],
            remediation=(
                "NyraHost could not create its Python venv. Verify the "
                "bundled python.exe under Binaries/Win64/NyraHost/python/ "
                "is intact (Fab updates can occasionally damage it) and "
                "that %LOCALAPPDATA%/NYRA/ is writable."
            ),
        )
    venv_py = _venv_python_exe(venv)
    install_cmd = [
        str(venv_py), "-m", "pip", "install",
        "--no-index",
        "--find-links", str(wheels_dir),
        "-r", str(requirements_lock),
    ]
    install_result = subprocess.run(
        install_cmd, capture_output=True, text=True,
    )
    if install_result.returncode != 0:
        raise BootstrapError(
            "install_wheels",
            command=install_cmd,
            returncode=install_result.returncode,
            stderr=(install_result.stderr or "")[-2000:],
            remediation=(
                "NyraHost could not install its bundled wheel cache. "
                "Run 'NYRA: Repair Plugin' from the editor, or delete "
                "%LOCALAPPDATA%/NYRA/venv/ and reopen the project."
            ),
        )
    _write_marker(venv, plugin_version)
    return venv_py
