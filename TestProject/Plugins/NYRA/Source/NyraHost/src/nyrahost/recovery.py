"""nyrahost.recovery — Phase 18-C crash recovery resume.

Phase 2's NyraTransactionManager wraps every chat session in a UE
super-transaction so an editor crash mid-tool-call doesn't leave the
project in an inconsistent state. Phase 18-C adds the user-facing
half: on next editor launch, the panel offers "we were doing X when
you crashed — want to resume?".

Resume state is stored as ``<ProjectDir>/Saved/NYRA/resume.json`` —
a single record updated on each tool-call boundary. The chat handler
writes; the recovery handler reads + clears on confirm.

Shape:
  {
    "session_id":      str (UUIDv4),
    "conversation_id": str,
    "last_tool":       str (name of last tool the agent was running),
    "last_prompt":     str (truncated to MAX_PROMPT_PREVIEW),
    "stage":           str ("planning" | "running" | "committing"),
    "ts":              float,
  }
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Optional

import structlog

log = structlog.get_logger("nyrahost.recovery")

RESUME_FILENAME: Final[str] = "resume.json"
MAX_PROMPT_PREVIEW: Final[int] = 4096
ERR_BAD_INPUT: Final[int] = -32602
ERR_NO_RESUME: Final[int] = -32079
ERR_RECOVERY_FAILED: Final[int] = -32080


def _resume_path(project_dir: Path) -> Path:
    return Path(project_dir) / "Saved" / "NYRA" / RESUME_FILENAME


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False,
        dir=str(path.parent),
        prefix=f".{path.name}.", suffix=".tmp",
    )
    try:
        json.dump(data, tmp, separators=(",", ":"))
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
class ResumeRecord:
    session_id: str
    conversation_id: str
    last_tool: str
    last_prompt: str
    stage: str
    ts: float

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "last_tool": self.last_tool,
            "last_prompt": self.last_prompt,
            "stage": self.stage,
            "ts": self.ts,
        }


@dataclass
class RecoveryStore:
    """Per-project resume.json writer/reader."""

    project_dir: Path

    @property
    def path(self) -> Path:
        return _resume_path(self.project_dir)

    def save(self, *, session_id: str, conversation_id: str,
             last_tool: str, last_prompt: str, stage: str, ts: float) -> ResumeRecord:
        rec = ResumeRecord(
            session_id=session_id,
            conversation_id=conversation_id,
            last_tool=last_tool,
            last_prompt=last_prompt[:MAX_PROMPT_PREVIEW],
            stage=stage,
            ts=ts,
        )
        _atomic_write(self.path, rec.to_dict())
        log.info("recovery_saved", stage=stage, conv=conversation_id)
        return rec

    def load(self) -> ResumeRecord | None:
        if not self.path.exists():
            return None
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        try:
            return ResumeRecord(
                session_id=str(raw["session_id"]),
                conversation_id=str(raw["conversation_id"]),
                last_tool=str(raw.get("last_tool", "")),
                last_prompt=str(raw.get("last_prompt", "")),
                stage=str(raw.get("stage", "")),
                ts=float(raw.get("ts", 0.0)),
            )
        except (KeyError, TypeError, ValueError):
            return None

    def clear(self) -> bool:
        if not self.path.exists():
            return False
        try:
            self.path.unlink()
            return True
        except OSError:
            return False


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


class RecoveryHandlers:
    def __init__(self, store: RecoveryStore) -> None:
        self._store = store

    async def on_check(self, params: dict, session=None, ws=None) -> dict:
        rec = self._store.load()
        if rec is None:
            return {"has_resume": False}
        return {"has_resume": True, "record": rec.to_dict()}

    async def on_resume(self, params: dict, session=None, ws=None) -> dict:
        rec = self._store.load()
        if rec is None:
            return _err(ERR_NO_RESUME, "no_resume_record")
        # Caller is expected to drive the actual chat replay; we just
        # surface the record and clear the file once accepted.
        try:
            self._store.clear()
        except Exception as exc:  # noqa: BLE001
            return _err(ERR_RECOVERY_FAILED, "clear_failed", str(exc))
        return {"resumed": True, "record": rec.to_dict()}

    async def on_dismiss(self, params: dict, session=None, ws=None) -> dict:
        cleared = self._store.clear()
        return {"cleared": cleared}


__all__ = [
    "ResumeRecord",
    "RecoveryStore",
    "RecoveryHandlers",
    "RESUME_FILENAME",
    "MAX_PROMPT_PREVIEW",
    "ERR_BAD_INPUT",
    "ERR_NO_RESUME",
    "ERR_RECOVERY_FAILED",
]
