"""nyrahost.mcp_installer — Phase 12-A one-click MCP config installer.

Aura ships a Settings → MCP Configuration → Add to Editor button that
auto-writes its MCP server entry into Claude Code, Cursor, VS Code,
Rider, and Junie. NYRA mirrors that surface so users on those IDEs
can drive NYRA tools (asset metadata, blueprint review, image gen,
etc.) from their existing AI assistant — without paying NYRA anything.

Each IDE reads MCP server config from a slightly different file with
a slightly different schema. We model each target explicitly rather
than guess, and merge into the existing config without clobbering
unrelated entries (most users already have other MCP servers).

Threat mitigations:
  T-12-01: Refuse paths whose realpath escapes the user home dir.
  T-12-02: Atomic write via tempfile + os.replace so a crash mid-merge
           never leaves a partial JSON file behind.
  T-12-03: Existing entries with the SAME server name are overwritten
           (this is intentional — re-install updates), but unrelated
           entries are preserved verbatim.
"""
from __future__ import annotations

import json
import os
import platform
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

import structlog

log = structlog.get_logger("nyrahost.mcp_installer")

NYRA_SERVER_NAME: Final[str] = "nyra"


@dataclass(frozen=True)
class IDETarget:
    """A single IDE's MCP-config location + JSON schema shape."""

    key: str            # short slug used over the wire ("cursor", "vscode", ...)
    display_name: str   # what the panel shows
    config_path: Path
    # The JSON path inside the config file where servers live.
    # Cursor/VS Code use ``mcpServers``; Claude Code uses ``mcpServers``;
    # Aura's docs show ``servers`` for some IDEs. We model each.
    servers_key: str = "mcpServers"


def _home() -> Path:
    return Path(os.path.expanduser("~"))


def _is_windows() -> bool:
    return sys.platform.startswith("win") or platform.system() == "Windows"


def list_targets() -> list[IDETarget]:
    """All known IDE targets on this OS, regardless of whether they're
    installed. The caller's UI greys-out targets whose ``config_path``
    parent dir doesn't exist yet."""
    home = _home()
    if _is_windows():
        appdata = Path(os.environ.get("APPDATA", str(home / "AppData/Roaming")))
        return [
            IDETarget("claude_code",  "Claude Code",
                      home / ".claude" / "mcp.json"),
            IDETarget("cursor",       "Cursor",
                      home / ".cursor" / "mcp.json"),
            IDETarget("vscode_user",  "VS Code (user)",
                      appdata / "Code" / "User" / "mcp.json"),
            IDETarget("rider",        "JetBrains Rider",
                      home / ".rider-mcp.json"),
        ]
    # POSIX (macOS / Linux)
    return [
        IDETarget("claude_code", "Claude Code",
                  home / ".claude" / "mcp.json"),
        IDETarget("cursor",      "Cursor",
                  home / ".cursor" / "mcp.json"),
        IDETarget("vscode_user", "VS Code (user)",
                  home / ".config" / "Code" / "User" / "mcp.json"),
        IDETarget("rider",       "JetBrains Rider",
                  home / ".rider-mcp.json"),
    ]


def _server_entry(python_exe: Path, mcp_script: Path) -> dict:
    """The NYRA MCP server entry, identical across every IDE we support.

    Each IDE expects the same { command, args, env } stdio shape per
    the MCP 2025-11-25 spec.
    """
    return {
        "type": "stdio",
        "command": str(python_exe),
        "args": [str(mcp_script)],
    }


def _read_config(path: Path) -> dict:
    """Read existing config or return an empty shape. Raises ValueError
    on JSON parse error so the caller knows not to overwrite a corrupt
    file blind."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"existing config at {path} is not valid JSON ({exc}); "
            "fix it manually before re-running install"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError(
            f"existing config at {path} top-level is "
            f"{type(data).__name__}, expected object"
        )
    return data


def _atomic_write(path: Path, data: dict) -> None:
    """T-12-02 atomic write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False,
        dir=str(path.parent),
        prefix=f".{path.name}.", suffix=".tmp",
    )
    try:
        json.dump(data, tmp, indent=2, sort_keys=True)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, path)
    except Exception:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        raise


def install(
    target: IDETarget,
    *,
    python_exe: Path,
    mcp_script: Path,
    home_root: Path | None = None,   # injected for tests
) -> Path:
    """Merge the NYRA server entry into the given IDE's config.

    Existing servers under any other key are preserved. An existing
    ``nyra`` entry is replaced (intentional: re-install updates).

    Returns the absolute path that was written.
    """
    # T-12-01: refuse paths that resolve outside the user home dir.
    root = (home_root or _home()).resolve()
    target_resolved = target.config_path.resolve(strict=False)
    try:
        target_resolved.relative_to(root)
    except ValueError:
        raise ValueError(
            f"refusing to write {target_resolved} — outside user home {root}"
        )

    cfg = _read_config(target.config_path)
    servers = cfg.get(target.servers_key)
    if not isinstance(servers, dict):
        servers = {}
    servers[NYRA_SERVER_NAME] = _server_entry(python_exe, mcp_script)
    cfg[target.servers_key] = servers
    _atomic_write(target.config_path, cfg)
    log.info(
        "mcp_install_ok",
        ide=target.key,
        path=str(target.config_path),
    )
    return target.config_path


def uninstall(target: IDETarget) -> bool:
    """Remove the NYRA server entry from the given IDE's config.

    Returns True if anything was removed; False if the file or entry
    didn't exist.
    """
    if not target.config_path.exists():
        return False
    cfg = _read_config(target.config_path)
    servers = cfg.get(target.servers_key)
    if not isinstance(servers, dict) or NYRA_SERVER_NAME not in servers:
        return False
    del servers[NYRA_SERVER_NAME]
    cfg[target.servers_key] = servers
    _atomic_write(target.config_path, cfg)
    log.info(
        "mcp_uninstall_ok",
        ide=target.key,
        path=str(target.config_path),
    )
    return True


__all__ = [
    "IDETarget",
    "list_targets",
    "install",
    "uninstall",
    "NYRA_SERVER_NAME",
]
