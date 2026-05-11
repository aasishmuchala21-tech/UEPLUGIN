"""Custom Instructions — Phase 10-1 Aura parity.

Aura's Advanced Settings page documents a Custom Instructions field that
gets prepended to every prompt. NYRA mirrors the convention but stores
per-project to keep teams from leaking style guides across projects.

Storage: ``<ProjectDir>/Saved/NYRA/instructions.md`` — Markdown so the
user can author it in their favourite editor and version-control it.

Loader contract:
  * ``CustomInstructions.load(project_dir)`` reads on demand; cheap
    (single short Markdown file). Returns "" when absent.
  * ``CustomInstructions.save(project_dir, body)`` atomic-writes via
    tempfile + os.replace (mirrors handshake.py / staging.py BL-03
    convention for crash-safe persistence).
  * The chat handler should prepend the body to every system prompt;
    safe_mode.NyraPermissionGate is unaffected (instructions are
    non-destructive context, not bypass).

Anti-patterns:
  * Don't read inside the dispatch loop on every chat — cache on
    handler init, refresh on the set-instructions write path.
  * Don't store secrets/API-keys here — instructions.md is plain text
    and may be checked into project git. Document this on the UI side.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import structlog

log = structlog.get_logger("nyrahost.custom_instructions")

INSTRUCTIONS_FILENAME: Final[str] = "instructions.md"
MAX_BODY_BYTES: Final[int] = 64 * 1024   # 64 KB — Aura caps similarly


def instructions_path(project_dir: Path) -> Path:
    """Canonical Saved/NYRA/instructions.md path."""
    return Path(project_dir) / "Saved" / "NYRA" / INSTRUCTIONS_FILENAME


@dataclass
class CustomInstructions:
    """Per-project custom instructions loader + writer.

    Caches the body in memory so chat dispatch never blocks on a file
    read. Refresh via ``reload()`` after a write.
    """

    project_dir: Path
    _body: str = ""

    def __post_init__(self) -> None:
        self._body = self._read_disk()

    def _read_disk(self) -> str:
        p = instructions_path(self.project_dir)
        if not p.exists():
            return ""
        try:
            return p.read_text(encoding="utf-8")[:MAX_BODY_BYTES]
        except OSError as exc:
            log.warning("instructions_read_failed", err=str(exc))
            return ""

    @property
    def body(self) -> str:
        return self._body

    def reload(self) -> str:
        self._body = self._read_disk()
        return self._body

    def save(self, body: str) -> Path:
        """Atomic write the new body, refresh cache, return the path."""
        if not isinstance(body, str):
            raise TypeError(f"body must be str, got {type(body).__name__}")
        if len(body.encode("utf-8")) > MAX_BODY_BYTES:
            raise ValueError(
                f"instructions exceed {MAX_BODY_BYTES} bytes; trim and retry"
            )
        target = instructions_path(self.project_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        # tempfile + os.replace — mirrors handshake.py / staging.py
        tmp = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False,
            dir=str(target.parent),
            prefix=".instructions.", suffix=".tmp",
        )
        try:
            tmp.write(body)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()
            os.replace(tmp.name, target)
        except Exception:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            raise
        self._body = body[:MAX_BODY_BYTES]
        log.info("instructions_saved", chars=len(self._body))
        return target

    def system_prompt_prefix(self) -> str:
        """Return the body wrapped for prepending to the system prompt.

        Empty string when the file is missing/blank so callers can
        unconditionally concatenate without a guard.
        """
        b = self._body.strip()
        if not b:
            return ""
        return f"# Project custom instructions\n\n{b}\n\n---\n\n"


__all__ = [
    "CustomInstructions",
    "instructions_path",
    "INSTRUCTIONS_FILENAME",
    "MAX_BODY_BYTES",
]
