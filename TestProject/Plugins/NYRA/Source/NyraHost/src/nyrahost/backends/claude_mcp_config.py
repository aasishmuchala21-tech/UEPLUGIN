"""Per-session MCP config file writer for the Claude CLI (Plan 02-05).

Writes a JSON file that the Claude CLI consumes via ``--mcp-config <path>``.
The file is placed in ``%LOCALAPPDATA%/NYRA/mcp-configs/`` with a filename of
``<session-id>.json`` (session-scoped isolation; no cross-session pollution).

Cleanup is aggressive (24 h) so stale configs don't accumulate on a developer's
machine across months of use. The MCP config writer is a pure function --
testable without filesystem mocks by injecting the output path as a DI parameter.

Per RESEARCH §1.6 literal shape::

    {
      "mcpServers": {
        "nyra": {
          "command": "<python.exe>",
          "args": ["-m", "nyrahost.mcp_server", "--handshake-file", "<path>"],
          "env": {
            "NYRA_SESSION_ID": "<uuid>",
            "NYRA_CONVERSATION_ID": "<uuid>"
          }
        }
      }
    }
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Final

import structlog

__all__ = ["write_mcp_config", "cleanup_stale_configs"]

log: Final = structlog.get_logger(__name__)

_DEFAULT_APP_DATA: Final = (
    Path(os.environ["LOCALAPPDATA"])
    if "LOCALAPPDATA" in os.environ
    else Path.home() / ".local" / "share"
)
MCP_CONFIGS_DIR: Final = _DEFAULT_APP_DATA / "NYRA" / "mcp-configs"
"""Fixed location — always under %LOCALAPPDATA% so the file is user-scoped."""


def write_mcp_config(
    session_id: str,
    conversation_id: str,
    python_exe: Path,
    handshake_file: Path,
    out_path: Path,
) -> None:
    """Write a per-session MCP config JSON file consumed by ``claude --mcp-config``.

    Parameters
    ----------
    session_id
        UUID identifying the *Claude CLI session*, not the NYRA conversation.
        Becomes ``NYRA_SESSION_ID`` in the subprocess env so the MCP server
        can tag its log entries.
    conversation_id
        UUID of the NYRA conversation driving this turn. Passed as
        ``NYRA_CONVERSATION_ID`` so the MCP server can bind its context.
    python_exe
        Absolute path to the bundled Python interpreter that runs the
        ``nyrahost.mcp_server`` entry point. On Windows this is the
        ``python.exe`` bundled under ``Binaries/Win64/NyraHost/``.
    handshake_file
        Absolute path to the NyraHost handshake file written by Plan 06's
        handshake module. The MCP server uses this to discover the WS port
        + auth token before accepting connections.
    out_path
        Destination file path. Caller is responsible for placing this under
        ``MCP_CONFIGS_DIR/<session-id>.json`` or equivalent. Existence of the
        parent directory is NOT guaranteed; the caller should ensure it exists.
    """
    payload = {
        "mcpServers": {
            "nyra": {
                "command": str(python_exe),
                "args": [
                    "-m",
                    "nyrahost.mcp_server",
                    "--handshake-file",
                    str(handshake_file),
                ],
                "env": {
                    "NYRA_SESSION_ID": session_id,
                    "NYRA_CONVERSATION_ID": conversation_id,
                },
            }
        }
    }
    _atomic_write(out_path, json.dumps(payload, indent=2))
    log.debug("mcp_config_written", path=str(out_path), session_id=session_id)


def cleanup_stale_configs(
    mcp_configs_dir: Path,
    max_age_seconds: int = 86_400,
) -> int:
    """Delete MCP config files older than ``max_age_seconds``.

    Safe to call on every NyraHost startup so a developer's
    ``%LOCALAPPDATA%/NYRA/mcp-configs/`` directory does not accumulate
    hundreds of stale JSON files over months.

    Parameters
    ----------
    mcp_configs_dir
        Directory to scan. Unchanged if it does not exist.
    max_age_seconds
        Age threshold in seconds. Defaults to 86 400 s = 24 h.
        Files modified more recently than this are untouched.

    Returns
    -------
    int
        Number of files deleted. 0 if the directory does not exist or is empty.
    """
    import time

    if not mcp_configs_dir.is_dir():
        return 0

    now = time.time()
    deleted = 0
    for path in mcp_configs_dir.iterdir():
        if path.is_file() and path.suffix == ".json":
            try:
                if now - path.stat().st_mtime > max_age_seconds:
                    path.unlink(missing_ok=True)
                    deleted += 1
            except OSError as exc:
                log.warning("mcp_config_cleanup_skip", path=str(path), err=str(exc))

    if deleted:
        log.debug("mcp_configs_cleaned", deleted=deleted)
    return deleted


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _atomic_write(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` atomically (temp-file-then-rename).

    Same pattern as Plan 06's handshake module. On Windows this eliminates
    the risk of a concurrent ``claude --mcp-config`` read seeing a
    half-written file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
    except Exception:  # noqa: BLE001
        if tmp.is_file():
            tmp.unlink(missing_ok=True)
        raise
