"""nyrahost.encrypted_memory — Phase 15-A per-project encrypted memory.

Tier 2 privacy moat. Aura's per-project memory (if any) lives on
their backend; studios under NDA can't audit it. NYRA writes a
project-local ``Saved/NYRA/memory.enc`` encrypted with Fernet
(symmetric AES-128-CBC + HMAC-SHA256). The key lives in
``Saved/NYRA/.memory.key`` with owner-only DACL on Windows.

Threat mitigations:
  * T-15-01: Fernet — authenticated encryption; tamper detection.
  * T-15-02: Key file written with restrictive perms (0600 POSIX,
    owner-only DACL on Windows via the existing handshake helper).
  * T-15-03: Memory file is atomically swapped via tempfile +
    os.replace so a partial encryption never corrupts the on-disk
    state.
  * T-15-04: 1 MB memory cap so a runaway agent doesn't fill disk.
"""
from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

import structlog
from cryptography.fernet import Fernet, InvalidToken

log = structlog.get_logger("nyrahost.encrypted_memory")

KEY_FILENAME: Final[str] = ".memory.key"
MEMORY_FILENAME: Final[str] = "memory.enc"
MAX_MEMORY_BYTES: Final[int] = 1 * 1024 * 1024   # 1 MB cap (T-15-04)


def _key_path(project_dir: Path) -> Path:
    return Path(project_dir) / "Saved" / "NYRA" / KEY_FILENAME


def _memory_path(project_dir: Path) -> Path:
    return Path(project_dir) / "Saved" / "NYRA" / MEMORY_FILENAME


def _set_owner_only_perms(path: Path) -> None:
    """T-15-02 — POSIX 0600; Windows owner-only DACL via win32security
    if pywin32 is available (matches handshake.py best-effort)."""
    if sys.platform != "win32":
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
        return
    try:
        import win32security                    # type: ignore[import]
        import ntsecuritycon                    # type: ignore[import]
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
    except Exception:  # noqa: BLE001 — best-effort
        log.warning("memory_key_dacl_apply_failed")


def _ensure_key(project_dir: Path) -> bytes:
    """Return the symmetric key for this project, creating one if absent."""
    key_path = _key_path(project_dir)
    if key_path.exists():
        return key_path.read_bytes().strip()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    k = Fernet.generate_key()
    key_path.write_bytes(k)
    _set_owner_only_perms(key_path)
    log.info("memory_key_created", path=str(key_path))
    return k


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(
        mode="wb", delete=False,
        dir=str(path.parent),
        prefix=f".{path.name}.", suffix=".tmp",
    )
    try:
        tmp.write(data)
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


@dataclass
class EncryptedMemory:
    """Per-project encrypted scratch store. Treated as a free-form dict.

    R3.C2 fix from the full-codebase review: cache the decrypted dict in
    memory between operations so set_key / get_key / delete_key don't
    each do a full Fernet decrypt + JSON parse + re-encrypt + fsync
    round-trip. Three consecutive agent-loop set_key calls now perform
    one decrypt (first load) and three encrypts (one per save) instead
    of three decrypts and three encrypts.
    """

    project_dir: Path

    def __post_init__(self) -> None:
        self._key = _ensure_key(self.project_dir)
        self._cipher = Fernet(self._key)
        self._cache: dict | None = None   # R3.C2 — None means cold

    def _cold_load(self) -> dict:
        """Decrypt the on-disk blob into a fresh dict. Never consults the cache."""
        path = _memory_path(self.project_dir)
        if not path.exists():
            return {}
        try:
            blob = path.read_bytes()
            plain = self._cipher.decrypt(blob)
            data = json.loads(plain.decode("utf-8"))
        except (InvalidToken, json.JSONDecodeError, OSError) as exc:
            log.warning("memory_decrypt_failed", err=str(exc))
            return {}
        if not isinstance(data, dict):
            return {}
        return data

    def load(self) -> dict:
        """Return the decrypted store. Cached after the first call.

        Callers must not mutate the returned dict in-place — use
        set_key / delete_key / save. The dict is a live view of the
        cache, not a copy, so external mutation would silently bypass
        the encrypt-and-write step.
        """
        if self._cache is None:
            self._cache = self._cold_load()
        return self._cache

    def save(self, data: dict) -> Path:
        if not isinstance(data, dict):
            raise TypeError("memory body must be a dict")
        plain = json.dumps(data, separators=(",", ":")).encode("utf-8")
        if len(plain) > MAX_MEMORY_BYTES:
            raise ValueError(
                f"memory exceeds {MAX_MEMORY_BYTES} bytes; trim before save"
            )
        token = self._cipher.encrypt(plain)
        path = _memory_path(self.project_dir)
        _atomic_write(path, token)
        # R3.C2 — keep the cache coherent with what we just persisted.
        self._cache = data
        log.info("memory_saved", bytes=len(plain))
        return path

    def invalidate_cache(self) -> None:
        """Force the next load() to re-read from disk. Useful when an
        external process (a second NyraHost, the snapshot exporter) may
        have rewritten the file under us."""
        self._cache = None

    def set_key(self, key: str, value) -> dict:
        data = self.load()
        data[str(key)] = value
        self.save(data)
        return data

    def get_key(self, key: str, default=None):
        return self.load().get(str(key), default)

    def delete_key(self, key: str) -> bool:
        data = self.load()
        if key not in data:
            return False
        del data[key]
        self.save(data)
        return True


__all__ = [
    "EncryptedMemory",
    "KEY_FILENAME",
    "MEMORY_FILENAME",
    "MAX_MEMORY_BYTES",
]
