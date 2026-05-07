"""nyrahost.tools.staging — Staging manifest for pending/confirmed imports.

Tracks computer-use jobs and their import status for UE asset pipeline.
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, Optional

import structlog

log = structlog.get_logger("nyrahost.tools.staging")


class StagingManifest:
    """Manages a manifest file tracking pending/confirmed import jobs.

    Stores entries at <staging_root>/nyra_pending.json by default.
    Each entry maps job_id -> {api_response, ue_import_status, input_ref, ...}
    """

    def __init__(self, manifest_path: Optional[str] = None) -> None:
        self._manifest_path = manifest_path or self._default_manifest_path()
        self._cache: dict[str, dict[str, Any]] = {}
        self._load()

    @staticmethod
    def _default_manifest_path() -> str:
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".nyra")))
        return str(base / "NYRA" / "staging" / "nyra_pending.json")

    def _load(self) -> None:
        if os.path.exists(self._manifest_path):
            try:
                with open(self._manifest_path) as f:
                    self._cache = json.load(f)
            except Exception:
                self._cache = {}
        else:
            self._cache = {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._manifest_path), exist_ok=True)
        with open(self._manifest_path, "w") as f:
            json.dump(self._cache, f, indent=2)

    def add_pending(
        self,
        job_id: str,
        tool: str,
        operation: str,
        input_ref: str,
        api_response: Optional[dict[str, Any]] = None,
    ) -> None:
        """Add a new pending job entry."""
        self._cache[job_id] = {
            "job_id": job_id,
            "tool": tool,
            "operation": operation,
            "input_ref": input_ref,
            "api_response": api_response or {},
            "ue_import_status": "pending",
        }
        self._save()
        log.info("staging_manifest_added", job_id=job_id, tool=tool)

    def update_job(
        self,
        job_id: str,
        api_response: Optional[dict[str, Any]] = None,
        ue_import_status: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update an existing job entry."""
        if job_id in self._cache:
            if api_response is not None:
                self._cache[job_id]["api_response"] = api_response
            if ue_import_status is not None:
                self._cache[job_id]["ue_import_status"] = ue_import_status
            if error_message is not None:
                self._cache[job_id]["error_message"] = error_message
            self._save()
            log.info("staging_manifest_updated", job_id=job_id, status=ue_import_status)

    def get_job(self, job_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a job entry by job_id."""
        return self._cache.get(job_id)

    def list_jobs(self, tool: Optional[str] = None) -> list[dict[str, Any]]:
        """List all jobs, optionally filtered by tool."""
        jobs = list(self._cache.values())
        if tool:
            jobs = [j for j in jobs if j.get("tool") == tool]
        return jobs
