"""nyrahost.snapshot — Phase 18-B reproduce-on-fresh-editor snapshot export.

Aura's chat-export feature is for support tickets. NYRA's wedge: a
self-contained zip of the per-project chat + audit + settings state
the user can DM to the founder for repro. Everything in the zip is
local — no network round-trip, no SaaS upload.

Snapshot contents (all under Saved/NYRA/snapshots/<id>.zip):
  * chat_history.json — last N conversations from sessions.db
  * audit.jsonl       — full audit log
  * instructions.md   — Custom Instructions
  * settings.json     — model pin + repro pin + privacy state + version
  * crash_logs/       — every UE crash log under Saved/Crashes/
  * README.txt        — human-readable index

Threat mitigations:
  * T-18-01: Secrets in audit are already redacted by Phase 13-D's
    SECRET_FIELDS filter; the snapshot inherits that.
  * T-18-02: instructions.md is plain text — flagged in README.txt
    so the user knows not to paste an API key into it.
"""
from __future__ import annotations

import io
import json
import os
import time
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Iterable, Optional

import structlog

log = structlog.get_logger("nyrahost.snapshot")

ERR_BAD_INPUT: Final[int] = -32602
ERR_SNAPSHOT_FAILED: Final[int] = -32078

SNAPSHOTS_DIRNAME: Final[str] = "snapshots"
MAX_SNAPSHOT_BYTES: Final[int] = 32 * 1024 * 1024   # 32 MB cap


@dataclass
class Snapshot:
    snapshot_id: str
    path: Path
    bytes_written: int
    entries: int
    created_at: float


def _safe_read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _safe_read_bytes(p: Path) -> bytes:
    try:
        return p.read_bytes()
    except OSError:
        return b""


def _readme_text(*, snapshot_id: str, project_dir: Path) -> str:
    return (
        f"NYRA project snapshot {snapshot_id}\n"
        f"Generated at: {time.strftime('%Y-%m-%dT%H:%M:%S')}\n"
        f"Project: {project_dir}\n\n"
        "Contents:\n"
        "  chat_history.json — recent conversations + messages from sessions.db\n"
        "  audit.jsonl       — append-only audit log (secrets redacted)\n"
        "  instructions.md   — Custom Instructions (plain text)\n"
        "  settings.json     — model pin + repro pin + privacy state\n"
        "  crash_logs/       — UE crash dumps under Saved/Crashes\n\n"
        "PRIVACY NOTE: this zip may contain user prompts in plain text.\n"
        "Audit log strips Authorization / api_key / token / password.\n"
        "instructions.md is whatever the user wrote — if you pasted\n"
        "secrets into it, they will be in this zip. Always review before sharing.\n"
    )


def export_snapshot(
    *,
    project_dir: Path,
    sessions_db_path: Path | None = None,
    audit_path: Path | None = None,
    instructions_path: Path | None = None,
    extra_files: dict[str, bytes] | None = None,
    settings: dict | None = None,
    last_n_conversations: int = 10,
) -> Snapshot:
    """Build the zip; return Snapshot. Pure-function — no global state."""
    snapshot_id = str(uuid.uuid4())[:12]
    target_dir = Path(project_dir) / "Saved" / "NYRA" / SNAPSHOTS_DIRNAME
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{snapshot_id}.zip"

    entries = 0
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # README first so it's the user's first hit on extract
        zf.writestr("README.txt", _readme_text(
            snapshot_id=snapshot_id, project_dir=project_dir,
        ))
        entries += 1

        # Chat history — SQLite reader is heavy; we let the caller pass
        # a pre-rendered JSON if they have one (the chat handler does).
        # If neither, write an empty stub so the schema is stable.
        history_json = _safe_read_text(
            Path(project_dir) / "Saved" / "NYRA" / "chat_history_export.json"
        )
        if not history_json:
            history_json = json.dumps({"conversations": [], "messages": [],
                                       "note": "no pre-rendered export"})
        zf.writestr("chat_history.json", history_json)
        entries += 1

        if audit_path is None:
            audit_path = Path(project_dir) / "Saved" / "NYRA" / "audit.jsonl"
        audit_blob = _safe_read_bytes(audit_path)
        if audit_blob:
            zf.writestr("audit.jsonl", audit_blob)
            entries += 1

        if instructions_path is None:
            instructions_path = (
                Path(project_dir) / "Saved" / "NYRA" / "instructions.md"
            )
        instr_blob = _safe_read_bytes(instructions_path)
        if instr_blob:
            zf.writestr("instructions.md", instr_blob)
            entries += 1

        settings_dump = settings or {}
        zf.writestr("settings.json",
                    json.dumps(settings_dump, indent=2, sort_keys=True))
        entries += 1

        # Crash logs
        crashes_root = Path(project_dir) / "Saved" / "Crashes"
        if crashes_root.exists():
            for log_path in crashes_root.rglob("*.log"):
                rel = log_path.relative_to(crashes_root)
                # L1: refuse arc names containing ".." or absolute parts —
                # a crafted log filename or symlinked crash subdir could
                # otherwise escape the `crash_logs/` prefix when extracted
                # by a tool that resolves `..` in archive entries.
                rel_parts = rel.parts
                if any(p in ("..", "") for p in rel_parts) or rel.is_absolute():
                    log.warning(
                        "snapshot_skipped_unsafe_arcname",
                        rel=str(rel),
                    )
                    continue
                blob = _safe_read_bytes(log_path)
                if blob:
                    arc = "crash_logs/" + "/".join(rel_parts)
                    zf.writestr(arc, blob)
                    entries += 1
                if buf.tell() > MAX_SNAPSHOT_BYTES:
                    log.warning("snapshot_max_size_hit",
                                snapshot_id=snapshot_id,
                                bytes=buf.tell())
                    break

        # Caller-supplied extras (e.g. recent UE Saved/Logs tail).
        # L1: the caller composes `name`; refuse the same unsafe-arc
        # patterns so an LLM-driven extras handoff cannot pop out of
        # `extras/`. The slim conformant shape is bare-filename or
        # `subdir/file`.
        for name, blob in (extra_files or {}).items():
            if not isinstance(name, str) or not name:
                continue
            normalized = name.replace("\\", "/")
            parts = [p for p in normalized.split("/") if p]
            if any(p == ".." for p in parts) or normalized.startswith("/"):
                log.warning(
                    "snapshot_skipped_unsafe_extras_name",
                    name=name,
                )
                continue
            arc = "extras/" + "/".join(parts)
            zf.writestr(arc, blob)
            entries += 1

    payload = buf.getvalue()
    if len(payload) > MAX_SNAPSHOT_BYTES:
        raise ValueError(
            f"snapshot exceeds {MAX_SNAPSHOT_BYTES} bytes; "
            "trim crash logs or extra_files and retry"
        )
    target.write_bytes(payload)
    return Snapshot(
        snapshot_id=snapshot_id,
        path=target,
        bytes_written=len(payload),
        entries=entries,
        created_at=time.time(),
    )


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


class SnapshotHandlers:
    def __init__(self, *, project_dir: Path) -> None:
        self._project_dir = Path(project_dir)

    async def on_export(self, params: dict, session=None, ws=None) -> dict:
        last_n = int(params.get("last_n_conversations", 10))
        try:
            snap = export_snapshot(
                project_dir=self._project_dir,
                last_n_conversations=last_n,
                settings=params.get("settings"),
            )
        except (ValueError, OSError) as exc:
            return _err(ERR_SNAPSHOT_FAILED, "snapshot_failed", str(exc))
        return {
            "snapshot_id": snap.snapshot_id,
            "path": str(snap.path),
            "bytes": snap.bytes_written,
            "entries": snap.entries,
            "created_at": snap.created_at,
        }

    async def on_list(self, params: dict, session=None, ws=None) -> dict:
        target = self._project_dir / "Saved" / "NYRA" / SNAPSHOTS_DIRNAME
        if not target.exists():
            return {"snapshots": []}
        # R3.I1 fix from the full-codebase review: previously this called
        # p.stat() twice per file — once inside the sort key lambda and
        # again inside the loop. Cache it once. Bonus: caching closes the
        # TOCTOU window where the file could be deleted between the two
        # stat calls.
        cached: list[tuple[Path, "os.stat_result"]] = []
        for p in target.glob("*.zip"):
            try:
                cached.append((p, p.stat()))
            except OSError:
                continue
        cached.sort(key=lambda pair: pair[1].st_mtime, reverse=True)
        out = [
            {
                "snapshot_id": p.stem,
                "path": str(p),
                "bytes": st.st_size,
                "created_at": st.st_mtime,
            }
            for (p, st) in cached
        ]
        return {"snapshots": out}


__all__ = [
    "Snapshot",
    "SnapshotHandlers",
    "export_snapshot",
    "SNAPSHOTS_DIRNAME",
    "MAX_SNAPSHOT_BYTES",
    "ERR_BAD_INPUT",
    "ERR_SNAPSHOT_FAILED",
]
