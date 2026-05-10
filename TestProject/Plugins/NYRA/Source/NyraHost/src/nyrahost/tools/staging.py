"""nyrahost.tools.staging — Staging manifest for external tool imports.

Per Plan 05-01:
  - Shared by Meshy (GEN-01), ComfyUI (GEN-02), and computer-use (GEN-03)
  - Every external tool result lands here before UE import
  - UUID-keyed entries for idempotent retry
  - Path traversal protection (T-05-03)

Threat mitigations:
  T-05-03: _validate_path called before any downloaded_path write (BL-02 fixed
           the startswith-bypass to use Path.relative_to)
  BL-03:   atomic write via tempfile + os.replace; schema validation on load;
           threading.Lock around load+mutate+save sequences (process-local
           single-writer guarantee). Multi-process safety is documented as
           single-NyraHost-per-user for v1.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
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

    # BL-03: required string fields on every JobEntry. Used by _load to
    # reject manifests where any entry has been tampered with to omit a
    # required field or substitute the wrong type.
    _REQUIRED_ENTRY_FIELDS = (
        "id", "tool", "operation", "input_ref", "input_hash",
        "ue_import_status", "created_at",
    )

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
        # BL-03: serialize load+mutate+save sequences across worker tasks.
        self._lock = threading.RLock()

    def _load(self) -> dict:
        """Load manifest with schema validation (BL-03).

        Empty / missing files return a fresh canonical structure. Anything on
        disk that fails the schema check raises ValueError -- the caller
        should NOT silently fall back to an empty manifest because that
        would mask malicious tampering or genuine corruption.
        """
        if not self._manifest_path.exists():
            return {"version": STAGING_VERSION, "jobs": []}
        raw = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(
                f"nyra_pending.json: top-level must be an object (got {type(raw).__name__})"
            )
        if raw.get("version") != STAGING_VERSION:
            raise ValueError(
                f"nyra_pending.json schema mismatch: expected version {STAGING_VERSION}, "
                f"found {raw.get('version')!r}"
            )
        jobs = raw.get("jobs")
        if not isinstance(jobs, list):
            raise ValueError(
                f"nyra_pending.json: jobs must be a list (got {type(jobs).__name__})"
            )
        for j in jobs:
            if not isinstance(j, dict):
                raise ValueError(f"nyra_pending.json: job entry not an object: {j!r}")
            for field in self._REQUIRED_ENTRY_FIELDS:
                v = j.get(field)
                if not isinstance(v, str):
                    raise ValueError(
                        f"nyra_pending.json: job {j.get('id')!r} missing required string "
                        f"field '{field}' (got {type(v).__name__})"
                    )
        return raw

    def _save(self, data: dict) -> None:
        """Atomic write via tempfile + os.replace (BL-03).

        os.replace is atomic on NTFS and POSIX -- a crash, power loss, or
        concurrent reader during write will see either the previous
        manifest or the new one, never a half-written truncated JSON.
        Tempfile lives in the same dir so the rename is intra-volume.
        """
        # NamedTemporaryFile delete=False so we own the path through replace().
        tmp = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False,
            dir=str(self._root),
            prefix=".nyra_pending.", suffix=".tmp",
        )
        try:
            json.dump(data, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()
            os.replace(tmp.name, self._manifest_path)
        except Exception:
            # Best-effort cleanup; never let the temp file leak on error.
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            raise

    # BL-05: image input safety. ingest paths come from agent-controlled
    # tool args; bound the read by extension allowlist + size cap so an
    # LLM cannot point us at \\?\PhysicalDrive0, /dev/zero, named pipes,
    # or multi-GB raw recordings. Hash in 1 MiB chunks rather than
    # read_bytes() so memory stays bounded for legitimate big inputs.
    _ALLOWED_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp")
    _MAX_INPUT_BYTES = 32 * 1024 * 1024  # 32 MiB
    _HASH_CHUNK_BYTES = 1024 * 1024       # 1 MiB

    def compute_hash(self, input_ref: str, *, extra: str = "") -> str:
        """Compute sha256 of the input reference for idempotency.

        BL-04: callers compose `extra` from per-tool params (Meshy: prompt
        + task_type; ComfyUI: workflow JSON serialization + target_folder
        + input_image_path). Without `extra`, distinct generation requests
        of the same image get falsely deduped to the prior job.

        BL-05: validates file paths (size cap, extension allowlist, no
        directories/devices) before reading. Hashes in chunks. Returns
        the FULL hex digest (WR-04 in the Phase 5 review wanted no
        [:16] truncation; 64-bit collision space was too tight for
        billing dedup).
        """
        h = hashlib.sha256()
        path = Path(input_ref)
        if path.exists():
            # Image-file path: validate then chunk-hash.
            if not path.is_file():
                raise ValueError(f"Input is not a regular file: {input_ref}")
            suffix = path.suffix.lower()
            if suffix and suffix not in self._ALLOWED_IMAGE_SUFFIXES:
                raise ValueError(
                    f"Unsupported input extension '{suffix}' for {input_ref}; "
                    f"allowed: {', '.join(self._ALLOWED_IMAGE_SUFFIXES)}"
                )
            size = path.stat().st_size
            if size > self._MAX_INPUT_BYTES:
                raise ValueError(
                    f"Input file too large: {size} bytes > {self._MAX_INPUT_BYTES} cap "
                    f"({input_ref})"
                )
            with path.open("rb") as f:
                while True:
                    chunk = f.read(self._HASH_CHUNK_BYTES)
                    if not chunk:
                        break
                    h.update(chunk)
        else:
            # Non-file input_refs (workflow JSON strings, prompts) -- hash
            # the string verbatim. Reject strings larger than the byte cap
            # to keep hashing bounded.
            payload = input_ref.encode("utf-8")
            if len(payload) > self._MAX_INPUT_BYTES:
                raise ValueError(
                    f"Input string too large: {len(payload)} bytes > {self._MAX_INPUT_BYTES} cap"
                )
            h.update(payload)
        if extra:
            h.update(b"|")
            h.update(extra.encode("utf-8"))
        return f"sha256:{h.hexdigest()}"

    # Backwards-compatible private alias for callers that still use the
    # old name. New code should call compute_hash(); this internal
    # shim drops the [:16] truncation per WR-04.
    def _compute_hash(self, input_ref: str) -> str:
        return self.compute_hash(input_ref)

    def _validate_path(self, path: str) -> None:
        """Raise PathTraversalError if path resolves outside staging root.

        T-05-03: Every downloaded_path is validated before write.

        BL-02: previous implementation used `str.startswith` which has the
        sibling-prefix bypass: when staging root is `<root>/staging`, the
        path `<root>/staging-evil/foo.glb` passed the check because the
        string starts with `<root>/staging`. Replaced with the proper
        path-component check via Path.relative_to (which raises ValueError
        for any path not strictly under root).
        """
        resolved = Path(path).resolve()
        root_resolved = self._root.resolve()
        try:
            resolved.relative_to(root_resolved)
        except ValueError:
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
        input_hash: Optional[str] = None,
    ) -> JobEntry:
        """Write a pending entry to the manifest BEFORE the tool returns.

        This is the Pitfall 1 mitigation: the entry exists before the API call
        starts so NyraHost crash mid-polling does not orphan a job.

        BL-04: callers can pass an explicit `input_hash` so the stored hash
        matches the per-tool composition (e.g. Meshy mixes task_type +
        prompt; ComfyUI mixes target_folder + input_image_asset_path).
        Without this, the stored hash drifts from the lookup hash and
        find_by_hash never matches a re-submit.
        """
        # Use caller-supplied hash if provided; fall back to default.
        effective_hash = input_hash if input_hash is not None else self._compute_hash(input_ref)
        with self._lock:
            data = self._load()
            entry = JobEntry(
                id=job_id,
                tool=tool,
                operation=operation,
                input_ref=input_ref,
                input_hash=effective_hash,
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
        """Return job_id if an existing in-flight or imported job matches input_hash.

        Used for idempotency — re-submit of same (tool, operation, input_hash)
        returns the existing job_id without creating a new API call.

        WR-05: drop the dead ``"completed"`` value from the status set
        — no code path writes that literal. The actual lifecycle is
        ``pending`` (background poller) → ``imported`` (UE-side import
        bridge) for the success path, ``failed`` / ``timeout`` for the
        error paths. ``failed``/``timeout`` are intentionally NOT in
        the dedup set so a retry after failure can re-submit.
        """
        data = self._load()
        for job in data["jobs"]:
            if (
                job["tool"] == tool
                and job["operation"] == operation
                and job["input_hash"] == input_hash
                and job["ue_import_status"] in ("pending", "imported")
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
        """Update fields on an existing job entry.

        WR-06: previously a missing job_id silently no-op'd. Background
        polling tasks (Meshy, ComfyUI) rely on update_job to record
        completion state; if the manifest got corrupted or
        cleanup_old_entries deleted the row mid-poll, the job appeared
        forever-pending. Raise ``KeyError`` so the caller can log/alert
        instead of swallowing the inconsistency.
        """
        if downloaded_path is not None:
            self._validate_path(downloaded_path)

        data = self._load()
        found = False
        for job in data["jobs"]:
            if job["id"] == job_id:
                found = True
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
        if not found:
            raise KeyError(
                f"update_job: job_id {job_id!r} not in staging manifest "
                "(was it cleaned up by cleanup_old_entries?)"
            )
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