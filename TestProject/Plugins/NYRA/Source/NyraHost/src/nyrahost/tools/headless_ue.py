"""nyrahost.tools.headless_ue — Phase 12-B headless UE launch tools.

Aura's IDE/MCP integration ships three tools that let a user driving
NYRA from outside the editor (Claude Code, Cursor) launch + monitor
+ shut down a headless UE process. NYRA mirrors the surface so the
same flow works.

Three tools:

  * ``launch_unreal_project`` — spawn ``UnrealEditor-Cmd.exe <project>
    -StdOut -Unattended -NoSplash -nopause`` as a subprocess. Returns
    the PID + a session handle.
  * ``get_headless_status`` — return whether the spawned editor is
    still alive plus its uptime.
  * ``shutdown_headless`` — TerminateProc(KillTree=true) the spawned
    editor.

The supervisor's existing FNyraSupervisor logic on the C++ side is
the inverse: UE spawns NyraHost. This module is the dual — NyraHost
spawns UE.

Auto-discovery: when ``project_path`` is omitted, search the cwd and
its ancestors for a single ``*.uproject`` file. If zero or multiple
match, return -32047 with a helpful diagnostic.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Optional

import structlog

log = structlog.get_logger("nyrahost.tools.headless_ue")

ERR_BAD_INPUT: Final[int] = -32602
ERR_PROJECT_NOT_FOUND: Final[int] = -32047
ERR_EDITOR_NOT_FOUND: Final[int] = -32048
ERR_LAUNCH_FAILED: Final[int] = -32049
ERR_NO_SESSION: Final[int] = -32050


@dataclass
class HeadlessSession:
    """One running headless UE editor."""

    pid: int
    project_path: str
    editor_exe: str
    started_at: float = field(default_factory=time.time)
    proc: "asyncio.subprocess.Process | None" = None


def _err(code: int, message: str, detail: str = "", remediation: Optional[str] = None) -> dict:
    data: dict = {}
    if detail:
        data["detail"] = detail
    if remediation:
        data["remediation"] = remediation
    out: dict = {"error": {"code": code, "message": message}}
    if data:
        out["error"]["data"] = data
    return out


def _discover_uproject(start: Path) -> list[Path]:
    """Walk cwd → parents → look for .uproject files. Returns all matches
    so the caller can disambiguate."""
    p = start.resolve()
    matches: list[Path] = []
    for ancestor in [p, *p.parents]:
        try:
            for entry in ancestor.iterdir():
                if entry.is_file() and entry.suffix == ".uproject":
                    matches.append(entry)
            if matches:
                return matches
        except (OSError, PermissionError):
            continue
    return matches


def _resolve_editor_exe(ue_root: Path | None) -> Path | None:
    """Resolve UnrealEditor-Cmd.exe (Windows) / UnrealEditor (POSIX).

    Search order: explicit ``ue_root`` → UE_56_DIR env var → PATH.
    """
    candidates: list[Path] = []
    if ue_root is not None:
        candidates.append(ue_root / "Engine" / "Binaries" / "Win64" / "UnrealEditor-Cmd.exe")
        candidates.append(ue_root / "Engine" / "Binaries" / "Mac" / "UnrealEditor")
        candidates.append(ue_root / "Engine" / "Binaries" / "Linux" / "UnrealEditor")
    env_root = os.environ.get("UE_56_DIR") or os.environ.get("UE_INSTALL_DIR")
    if env_root:
        candidates.append(Path(env_root) / "Engine" / "Binaries" / "Win64" / "UnrealEditor-Cmd.exe")
    for c in candidates:
        if c.exists():
            return c
    # Fallback to PATH
    for name in ("UnrealEditor-Cmd.exe", "UnrealEditor", "UnrealEditor-Cmd"):
        on_path = shutil.which(name)
        if on_path:
            return Path(on_path)
    return None


class HeadlessUEManager:
    """Tracks at most one headless UE session per process.

    Phase 9 RIG-XX could later allow multiple sessions, but a solo
    developer almost never wants two headless editors competing for
    the same SQLite db / log dir.
    """

    def __init__(self) -> None:
        self._session: HeadlessSession | None = None

    async def launch(
        self,
        params: dict,
    ) -> dict:
        """``launch_unreal_project`` MCP tool entry."""
        if self._session is not None and self._session.proc is not None:
            if self._session.proc.returncode is None:
                return {
                    "already_running": True,
                    "pid": self._session.pid,
                    "project_path": self._session.project_path,
                    "uptime_s": time.time() - self._session.started_at,
                }

        # Resolve project
        project_param = params.get("project_path")
        if project_param:
            project = Path(str(project_param)).resolve()
            if not project.exists() or project.suffix != ".uproject":
                return _err(
                    ERR_PROJECT_NOT_FOUND, "project_not_found",
                    f"{project}",
                    remediation="Pass a valid .uproject path.",
                )
        else:
            cwd = Path(params.get("cwd") or os.getcwd())
            matches = _discover_uproject(cwd)
            if not matches:
                return _err(
                    ERR_PROJECT_NOT_FOUND, "no_uproject_in_cwd",
                    f"searched from {cwd}",
                    remediation="Run from a UE project dir or pass project_path.",
                )
            if len(matches) > 1:
                return _err(
                    ERR_PROJECT_NOT_FOUND, "multiple_uprojects",
                    ", ".join(str(m) for m in matches),
                    remediation="Multiple .uproject files found; pass project_path explicitly.",
                )
            project = matches[0]

        # Resolve editor
        ue_root = params.get("ue_root")
        editor = _resolve_editor_exe(Path(ue_root).resolve() if ue_root else None)
        if editor is None:
            return _err(
                ERR_EDITOR_NOT_FOUND, "ue_editor_not_found",
                "UnrealEditor-Cmd.exe not on PATH",
                remediation=(
                    "Set UE_56_DIR to your Unreal Engine install root, "
                    "or pass ue_root in params."
                ),
            )

        # Build argv
        argv = [
            str(editor),
            str(project),
            "-Unattended",
            "-NoSplash",
            "-nopause",
            "-StdOut",
        ]
        # Pass through optional ExecCmds
        exec_cmds = params.get("exec_cmds")
        if exec_cmds:
            argv.append(f"-ExecCmds={exec_cmds}")
        if params.get("nullrhi", False):
            argv.append("-nullrhi")

        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except (FileNotFoundError, OSError) as exc:
            return _err(ERR_LAUNCH_FAILED, "launch_failed", str(exc))

        sess = HeadlessSession(
            pid=proc.pid,
            project_path=str(project),
            editor_exe=str(editor),
            proc=proc,
        )
        self._session = sess
        log.info("headless_launched", pid=proc.pid, project=str(project))
        return {
            "launched": True,
            "pid": proc.pid,
            "project_path": str(project),
            "editor_exe": str(editor),
        }

    async def status(self, params: dict) -> dict:
        """``get_headless_status`` MCP tool entry."""
        if self._session is None or self._session.proc is None:
            return {"running": False}
        rc = self._session.proc.returncode
        if rc is not None:
            # The process exited; return the rc and clear our session pointer.
            out = {
                "running": False,
                "exited": True,
                "exit_code": rc,
                "pid": self._session.pid,
                "project_path": self._session.project_path,
            }
            self._session = None
            return out
        return {
            "running": True,
            "pid": self._session.pid,
            "project_path": self._session.project_path,
            "uptime_s": time.time() - self._session.started_at,
        }

    async def shutdown(self, params: dict) -> dict:
        """``shutdown_headless`` MCP tool entry."""
        if self._session is None or self._session.proc is None:
            return _err(ERR_NO_SESSION, "no_session_active")
        proc = self._session.proc
        if proc.returncode is None:
            try:
                proc.terminate()
            except ProcessLookupError:
                pass
            # Give it 5s to exit cleanly, then kill.
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                await proc.wait()
        out = {
            "shutdown": True,
            "pid": self._session.pid,
            "exit_code": proc.returncode,
        }
        self._session = None
        log.info("headless_shutdown", pid=out["pid"], rc=out["exit_code"])
        return out


__all__ = [
    "HeadlessUEManager",
    "HeadlessSession",
    "ERR_BAD_INPUT",
    "ERR_PROJECT_NOT_FOUND",
    "ERR_EDITOR_NOT_FOUND",
    "ERR_LAUNCH_FAILED",
    "ERR_NO_SESSION",
]
