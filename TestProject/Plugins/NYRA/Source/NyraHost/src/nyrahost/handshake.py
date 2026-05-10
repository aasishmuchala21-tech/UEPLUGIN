"""Handshake file protocol (docs/HANDSHAKE.md).

Atomic rename + Windows owner-only DACL + orphan cleanup.

Implements:
  - D-06: handshake-<ue_pid>.json with {port, token, nyrahost_pid, ue_pid, started_at}
  - RESEARCH §3.10 P1.1: atomic-rename race (json.dump → f.flush → os.fsync → os.replace)
  - RESEARCH §3.10 P1.2: orphan handshake cleanup on editor PID absence
"""
from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path
from typing import TypedDict


class HandshakePayload(TypedDict):
    port: int
    token: str
    nyrahost_pid: int
    ue_pid: int
    started_at: int  # ms since epoch


def handshake_file_path(handshake_dir: Path, ue_pid: int) -> Path:
    return handshake_dir / f"handshake-{ue_pid}.json"


def write_handshake(
    handshake_dir: Path,
    *,
    port: int,
    token: str,
    nyrahost_pid: int,
    ue_pid: int,
) -> Path:
    """Atomic write per docs/HANDSHAKE.md. Returns final path.

    Protocol: open <final>.tmp → json.dump → flush → fsync → close
    → os.replace(tmp, final) [atomic on NTFS + POSIX].
    """
    handshake_dir.mkdir(parents=True, exist_ok=True)
    final = handshake_file_path(handshake_dir, ue_pid)
    tmp = final.with_suffix(final.suffix + ".tmp")
    payload: HandshakePayload = {
        "port": port,
        "token": token,
        "nyrahost_pid": nyrahost_pid,
        "ue_pid": ue_pid,
        "started_at": int(time.time() * 1000),
    }
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, final)  # atomic on NTFS + POSIX
    if sys.platform == "win32":
        _apply_owner_only_dacl(final)
    return final


def _apply_owner_only_dacl(path: Path) -> None:
    """Restrict DACL to current user SID on Windows. Best-effort —
    if pywin32 missing or call fails, log and continue (file still exists
    and is usable; this is defence-in-depth, not a hard guarantee)."""
    try:
        import win32security  # type: ignore[import-not-found]
        import ntsecuritycon  # type: ignore[import-not-found]
        # Get current user SID
        user_token = win32security.OpenProcessToken(
            win32security.GetCurrentProcess(),
            win32security.TOKEN_QUERY,
        )
        user_sid = win32security.GetTokenInformation(
            user_token, win32security.TokenUser,
        )[0]
        dacl = win32security.ACL()
        dacl.AddAccessAllowedAce(
            win32security.ACL_REVISION,
            ntsecuritycon.FILE_GENERIC_READ
            | ntsecuritycon.FILE_GENERIC_WRITE
            | ntsecuritycon.DELETE,
            user_sid,
        )
        sd = win32security.SECURITY_DESCRIPTOR()
        sd.SetSecurityDescriptorDacl(1, dacl, 0)
        win32security.SetFileSecurity(
            str(path),
            win32security.DACL_SECURITY_INFORMATION,
            sd,
        )
    except Exception:  # noqa: BLE001 — best effort
        pass


def cleanup_orphan_handshakes(handshake_dir: Path) -> list[int]:
    """Scan handshake-*.json; return PIDs cleaned up.
    Orphan = ue_pid not running. Caller should also terminate orphan
    nyrahost_pid (supervisor concern — UE side; Python does not kill
    other editors' NyraHosts)."""
    if not handshake_dir.exists():
        return []
    cleaned: list[int] = []
    for f in handshake_dir.glob("handshake-*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            ue_pid = data["ue_pid"]
            if not _pid_running(int(ue_pid)):
                f.unlink(missing_ok=True)
                cleaned.append(int(ue_pid))
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            # Corrupt; ignore
            continue
    return cleaned


def _pid_running(pid: int) -> bool:
    if sys.platform == "win32":
        # BL-06: OpenProcess succeeds for terminated-but-not-reaped processes
        # (zombies) AND for recycled PIDs (the OS reassigned the integer to a
        # new unrelated process). Always check GetExitCodeProcess for
        # STILL_ACTIVE (259); otherwise orphan handshake cleanup is broken
        # and a recycled PID locks out the new editor.
        STILL_ACTIVE = 259
        h = None
        try:
            import win32api  # type: ignore[import-not-found]
            import win32con  # type: ignore[import-not-found]
            import win32process  # type: ignore[import-not-found]
            h = win32api.OpenProcess(
                win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid
            )
            exit_code = win32process.GetExitCodeProcess(h)
            return exit_code == STILL_ACTIVE
        except Exception:
            return False
        finally:
            if h is not None:
                try:
                    win32api.CloseHandle(h)
                except Exception:
                    pass
    # POSIX
    try:
        os.kill(pid, 0)
        return True
    except (OSError, OverflowError):
        # OverflowError: pid exceeds platform pid_t range (e.g. 32-bit pid_t
        # on macOS rejecting > 2^31-1). Such a PID cannot be alive — treat as
        # not-running so orphan-cleanup can unlink the stale handshake file.
        return False
