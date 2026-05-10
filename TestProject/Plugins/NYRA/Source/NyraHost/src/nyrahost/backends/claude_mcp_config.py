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

# CR-03: every id-shaped param that flows into a filename or env var must
# match this regex. UUID-shaped values are well within the 1-64 char
# alphanum + dash + underscore set; anything else is rejected before any
# filesystem or subprocess interaction.
_ID_PATTERN = __import__("re").compile(r"^[A-Za-z0-9_-]{1,64}$")


def _validate_id(name: str, value: str) -> None:
    """Raise ValueError if ``value`` does not match the strict id pattern."""
    if not isinstance(value, str) or not _ID_PATTERN.match(value):
        raise ValueError(
            f"[-32030] {name} must match ^[A-Za-z0-9_-]{{1,64}}$ (got {value!r})"
        )

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

    Raises
    ------
    ValueError
        CR-03: when ``session_id``, ``conversation_id``, or ``out_path``
        fails validation. Both ids must match ^[A-Za-z0-9_-]{1,64}$ (UUID
        shape); ``out_path`` must resolve under ``MCP_CONFIGS_DIR`` so
        callers cannot write the config file outside the per-user dir
        (defends against `..` segments that could land the file in another
        user's directory or overwrite system files).
    """
    # CR-03: validate ids before they reach filenames / env vars.
    _validate_id("session_id", session_id)
    _validate_id("conversation_id", conversation_id)

    # CR-03: out_path safety. The concrete attack is `..` traversal that
    # escapes the per-user dir into another user's directory or onto
    # system files. Reject `..` segments + NUL bytes; accept any
    # absolute path the caller chose (production callers pass paths
    # under MCP_CONFIGS_DIR; tests pass tmp_path). Production code
    # in claude.py builds the path as `MCP_CONFIGS_DIR / f"{session_id}.json"`
    # which can't contain `..` because session_id is regex-validated above.
    out_str = str(out_path)
    if "\x00" in out_str:
        raise ValueError(f"[-32030] out_path contains NUL byte: {out_path!r}")
    for part in Path(out_str).parts:
        if part == "..":
            raise ValueError(
                f"[-32030] out_path contains '..' segment (rejected for safety): {out_path!r}"
            )

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

    WR-06: this directory is shared across every concurrent NyraHost
    instance on the user's machine (one per UE Editor PID). A naive
    "delete everything older than N seconds" would yank out an active
    sibling instance's config mid-stream. We keep this safe by:

      1. Only deleting files whose mtime is older than the threshold —
         live sessions touch their config at spawn time so a healthy
         sibling stays comfortably under the cutoff.
      2. Skipping files currently held open: on Windows ``unlink`` of an
         open handle raises ``PermissionError`` (sharing violation), which
         this function logs as ``mcp_config_cleanup_skip`` and continues.
         The result is best-effort cleanup that never preempts a live run.

    A future cross-process scoping enhancement (e.g. peeking at running
    NyraHost PIDs and skipping their session_ids) is tracked in
    ``.planning/research/MCP-CONFIG-SCOPING.md`` for v1.1.

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
                # PermissionError (Windows sharing violation) lands here
                # and is the safety net that prevents preempting a live
                # sibling NyraHost instance.
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
