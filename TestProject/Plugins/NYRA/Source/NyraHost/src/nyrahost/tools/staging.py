"""nyrahost.tools.staging — Staging manifest for external tool imports.

Per Plan 05-01:
  - Shared by Meshy (GEN-01), ComfyUI (GEN-02), and computer-use (GEN-03)
  - Every external tool result lands here before UE import
  - UUID-keyed entries for idempotent retry
  - Path traversal protection (T-05-03)

Threat mitigations:
  T-05-03: _validate_path called before any downloaded_path write
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import structlog

log = structlog.get_logger("nyrahost.tools.staging")

STAGING_VERSION = 1


class PathTraversalError(ValueError):
    """Raised when a file path resolves outside the staging directory."""
    pass


@dataclass
class JobEntry:
    """A single external tool job in the staging manifest."""
    id: str
    tool: str              # "meshy" | "comfyui" | "computer_use"
    operation: str         # "image-to-3d" | "run_workflow" | "gui_automation"
    input_ref: str         # source image path or workflow JSON hash
    input_hash: str        # sha256:<hex16> — used for idempotency dedup
    api_response: dict
    downloaded_path: Optional[str]
    ue_asset_path: Optional[str]
    ue_import_status: str  # "pending" | "importing" | "imported" | "failed" | "timeout"
    error_message: Optional[str]
    created_at: str        # ISO 8601

    @classmethod
    def from_dict(cls, d: dict) -> "JobEntry":
        """Reconstruct from dict (for manifest loading)."""
        return cls(**d)


class StagingManifest:
    """Reads and writes nyra_pending.json staging manifest.

    Every external tool result (Meshy GLB, ComfyUI PNG, computer-use screenshot)
    lands here before UE import. Entries are UUID-keyed for idempotent retry.

    Path: %LOCALAPPDATA%/NYRA/staging/nyra_pending.json on Windows,
          ~/.local/share/NYRA/staging/nyra_pending.json on Unix.
    """

    def __init__(self, staging_root: Optional[Path] = None) -> None:
        if staging_root:
            self._root = staging_root
        else:
            la = os.environ.get("LOCALAPPDATA")
            if la:
                self._root = Path(la) / "NYRA" / "staging"
            else:
                self._root = Path.home() / ".local" / "share" / "NYRA" / "staging"
        self._root.mkdir(parents=True, exist_ok=True)
        self._manifest_path = self._root / "nyra_pending.json"

    def _load(self) -> dict:
        if self._manifest_path.exists():
            return json.loads(self._manifest_path.read_text(encoding="utf-8"))
        return {"version": STAGING_VERSION, "jobs": []}

    def _save(self, data: dict) -> None:
        self._manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _compute_hash(self, input_ref: str) -> str:
        """Compute sha256:<hex16> of the input reference for idempotency."""
        path = Path(input_ref)
        if path.exists():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            # Non-file input_refs (workflow JSON strings) — hash the string
            digest = hashlib.sha256(input_ref.encode()).hexdigest()
        return f"sha256:{digest[:16]}"

    def _validate_path(self, path: str) -> None:
        """Raise PathTraversalError if path resolves outside staging root.

        T-05-03: Every downloaded_path is validated before write.
        """
        resolved = Path(path).resolve()
        if not str(resolved).startswith(str(self._root.resolve())):
            raise PathTraversalError(
                f"Path '{path}' resolves to '{resolved}' which is outside "
                f"staging root '{self._root}'. Rejected for security."
            )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def add_pending(
        self,
        job_id: str,
        tool: str,
        operation: str,
        input_ref: str,
        api_response: Optional[dict] = None,
    ) -> JobEntry:
        """Write a pending entry to the manifest BEFORE the tool returns.

        This is the Pitfall 1 mitigation: the entry exists before the API call
        starts so NyraHost crash mid-polling does not orphan a job.
        """
        data = self._load()
        entry = JobEntry(
            id=job_id,
            tool=tool,
            operation=operation,
            input_ref=input_ref,
            input_hash=self._compute_hash(input_ref),
            api_response=api_response or {},
            downloaded_path=None,
            ue_asset_path=None,
            ue_import_status="pending",
            error_message=None,
            created_at=datetime.now(timezone.utc).isoformat() + "Z",
        )
        data["jobs"].append(asdict(entry))
        self._save(data)
        log.info("staging_job_added", job_id=job_id, tool=tool, operation=operation)
        return entry

    def find_by_hash(
        self,
        tool: str,
        operation: str,
        input_hash: str,
    ) -> Optional[str]:
        """Return job_id if an existing pending/completed job matches input_hash.

        Used for idempotency — re-submit of same (tool, operation, input_hash)
        returns the existing job_id without creating a new API call.
        """
        data = self._load()
        for job in data["jobs"]:
            if (
                job["tool"] == tool
                and job["operation"] == operation
                and job["input_hash"] == input_hash
                and job["ue_import_status"] in ("pending", "completed", "imported")
            ):
                return job["id"]
        return None

    def update_job(
        self,
        job_id: str,
        api_response: Optional[dict] = None,
        downloaded_path: Optional[str] = None,
        ue_asset_path: Optional[str] = None,
        ue_import_status: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update fields on an existing job entry."""
        if downloaded_path is not None:
            self._validate_path(downloaded_path)

        data = self._load()
        for job in data["jobs"]:
            if job["id"] == job_id:
                if api_response is not None:
                    job["api_response"] = api_response
                if downloaded_path is not None:
                    job["downloaded_path"] = downloaded_path
                if ue_asset_path is not None:
                    job["ue_asset_path"] = ue_asset_path
                if ue_import_status is not None:
                    job["ue_import_status"] = ue_import_status
                if error_message is not None:
                    job["error_message"] = error_message
                break
        self._save(data)
        log.info("staging_job_updated", job_id=job_id, status=ue_import_status)

    def get_job(self, job_id: str) -> Optional[JobEntry]:
        """Return a JobEntry by id, or None if not found."""
        data = self._load()
        for job in data["jobs"]:
            if job["id"] == job_id:
                return JobEntry.from_dict(job)
        return None

    def get_pending_jobs(self, tool: Optional[str] = None) -> list[JobEntry]:
        """Return all pending jobs, optionally filtered by tool."""
        data = self._load()
        results = []
        for job in data["jobs"]:
            if job["ue_import_status"] == "pending":
                if tool is None or job["tool"] == tool:
                    results.append(JobEntry.from_dict(job))
        return results

    def cleanup_old_entries(self, max_age_days: int = 7) -> int:
        """Remove failed/timeout entries older than max_age_days. Returns count removed."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat() + "Z"
        data = self._load()
        original_count = len(data["jobs"])
        data["jobs"] = [
            j for j in data["jobs"]
            if not (
                j["ue_import_status"] in ("failed", "timeout")
                and j["created_at"] < cutoff
            )
        ]
        removed = original_count - len(data["jobs"])
        if removed:
            self._save(data)
            log.info("staging_cleanup", removed=removed)
        return removed


__all__ = ["StagingManifest", "JobEntry", "PathTraversalError", "STAGING_VERSION"]