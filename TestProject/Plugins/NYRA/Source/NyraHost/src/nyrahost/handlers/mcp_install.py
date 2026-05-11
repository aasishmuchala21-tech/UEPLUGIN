"""mcp_install/* WS handlers — Phase 12-A.

Three methods:
  * mcp_install/list_targets — returns the closed set of supported IDEs
    + whether each is "detected" (config dir exists)
  * mcp_install/install — install NYRA's stdio MCP entry into one IDE
  * mcp_install/uninstall — remove the entry

Each method returns a JSON-RPC envelope (success or error) — never
raises across the WS boundary.
"""
from __future__ import annotations

from pathlib import Path
from typing import Final, Optional

import structlog

from nyrahost.mcp_installer import (
    IDETarget,
    install,
    list_targets,
    uninstall,
)

log = structlog.get_logger("nyrahost.handlers.mcp_install")

ERR_BAD_INPUT: Final[int] = -32602
ERR_UNKNOWN_TARGET: Final[int] = -32045
ERR_INSTALL_FAILED: Final[int] = -32046


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


def _target_by_key(key: str, targets: list[IDETarget]) -> IDETarget | None:
    for t in targets:
        if t.key == key:
            return t
    return None


class McpInstallHandlers:
    """Encapsulates the install paths so app.py can wire python_exe and
    mcp_script once and forget."""

    def __init__(self, *, python_exe: Path, mcp_script: Path) -> None:
        self._python_exe = Path(python_exe)
        self._mcp_script = Path(mcp_script)

    async def on_list_targets(self, params: dict, session=None, ws=None) -> dict:
        out = []
        for t in list_targets():
            out.append({
                "key": t.key,
                "display_name": t.display_name,
                "config_path": str(t.config_path),
                "detected": t.config_path.parent.exists(),
            })
        return {"targets": out}

    async def on_install(self, params: dict, session=None, ws=None) -> dict:
        key = params.get("key")
        if not isinstance(key, str) or not key:
            return _err(ERR_BAD_INPUT, "missing_field", "key")
        target = _target_by_key(key, list_targets())
        if target is None:
            return _err(
                ERR_UNKNOWN_TARGET, "unknown_target", key,
                remediation="Call mcp_install/list_targets to see allowed keys.",
            )
        try:
            written = install(
                target,
                python_exe=self._python_exe,
                mcp_script=self._mcp_script,
            )
        except (ValueError, OSError) as exc:
            return _err(ERR_INSTALL_FAILED, "install_failed", str(exc))
        return {"installed": True, "path": str(written), "ide": key}

    async def on_uninstall(self, params: dict, session=None, ws=None) -> dict:
        key = params.get("key")
        if not isinstance(key, str) or not key:
            return _err(ERR_BAD_INPUT, "missing_field", "key")
        target = _target_by_key(key, list_targets())
        if target is None:
            return _err(ERR_UNKNOWN_TARGET, "unknown_target", key)
        try:
            removed = uninstall(target)
        except (ValueError, OSError) as exc:
            return _err(ERR_INSTALL_FAILED, "uninstall_failed", str(exc))
        return {"removed": removed, "ide": key}


__all__ = [
    "McpInstallHandlers",
    "ERR_BAD_INPUT",
    "ERR_UNKNOWN_TARGET",
    "ERR_INSTALL_FAILED",
]
