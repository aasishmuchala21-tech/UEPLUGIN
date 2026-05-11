"""tests/test_staging.py — Unit tests for StagingManifest (GEN-01, GEN-02, GEN-03).

Per Plan 05-01 Task 1:
  - test_manifest_schema_v1
  - test_add_pending_writes_entry
  - test_idempotent_dedup_by_input_hash
  - test_import_meshes_pending
  - test_path_traversal_blocked
  - test_get_pending_jobs
  - test_cleanup_old_entries
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from nyrahost.tools.staging import (
    StagingManifest,
    PathTraversalError,
    STAGING_VERSION,
)


class TestStagingManifest:
    """Tests for StagingManifest class."""

    def test_manifest_schema_v1(self, tmp_staging_dir, monkeypatch):
        """Minimal manifest has version==1 and jobs is a list."""
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_staging_dir.parent))
        manifest = StagingManifest(staging_root=tmp_staging_dir)
        data = manifest._load()
        assert data["version"] == STAGING_VERSION
        assert isinstance(data["jobs"], list)

    def test_add_pending_writes_entry(self, tmp_staging_dir, monkeypatch):
        """add_pending writes entry with ue_import_status=pending and input_hash."""
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_staging_dir.parent))
        manifest = StagingManifest(staging_root=tmp_staging_dir)

        entry = manifest.add_pending(
            job_id="job-001",
            tool="meshy",
            operation="image-to-3d",
            input_ref=str(tmp_staging_dir / "test.jpg"),
        )

        assert entry.id == "job-001"
        assert entry.tool == "meshy"
        assert entry.operation == "image-to-3d"
        assert entry.ue_import_status == "pending"
        assert entry.input_hash.startswith("sha256:")
        assert tmp_staging_dir.joinpath("nyra_pending.json").exists()

        # Verify file content
        raw = json.loads(tmp_staging_dir.joinpath("nyra_pending.json").read_text())
        assert len(raw["jobs"]) == 1
        assert raw["jobs"][0]["id"] == "job-001"
        assert raw["jobs"][0]["tool"] == "meshy"

    def test_idempotent_dedup_by_input_hash(self, tmp_staging_dir, monkeypatch):
        """Second add_pending with same input_hash returns existing job_id."""
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_staging_dir.parent))
        manifest = StagingManifest(staging_root=tmp_staging_dir)

        # Create a real file to hash
        img_path = tmp_staging_dir / "ref.jpg"
        img_path.write_bytes(b"fake image bytes for hashing")

        # First submission
        job_id_1 = "job-first"
        manifest.add_pending(
            job_id=job_id_1,
            tool="meshy",
            operation="image-to-3d",
            input_ref=str(img_path),
        )

        # Second submission with same input -> dedup
        existing = manifest.find_by_hash(
            tool="meshy",
            operation="image-to-3d",
            # R5.I1 fix from the full-codebase review: call the public
            # compute_hash() instead of the _compute_hash shim.
            input_hash=manifest.compute_hash(str(img_path)),
        )

        assert existing == job_id_1
        # Only one entry in manifest
        raw = json.loads(tmp_staging_dir.joinpath("nyra_pending.json").read_text())
        assert len(raw["jobs"]) == 1

    def test_update_job_meshes_pending(self, tmp_staging_dir, monkeypatch):
        """update_job sets ue_import_status on an existing entry."""
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_staging_dir.parent))
        manifest = StagingManifest(staging_root=tmp_staging_dir)

        manifest.add_pending(
            job_id="job-002",
            tool="meshy",
            operation="image-to-3d",
            input_ref="/tmp/fake.jpg",
        )

        manifest.update_job(
            job_id="job-002",
            ue_import_status="importing",
        )

        job = manifest.get_job("job-002")
        assert job is not None
        assert job.ue_import_status == "importing"

    def test_path_traversal_blocked(self, tmp_staging_dir, monkeypatch):
        """Absolute path outside staging root raises PathTraversalError."""
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_staging_dir.parent))
        manifest = StagingManifest(staging_root=tmp_staging_dir)

        with pytest.raises(PathTraversalError):
            manifest.update_job(
                job_id="job-evil",
                downloaded_path="C:/Windows/System32/evil.txt",
            )

        # Also test that a relative path that resolves outside is blocked
        with pytest.raises(PathTraversalError):
            manifest.update_job(
                job_id="job-evil2",
                downloaded_path=str(tmp_staging_dir.parent.parent / "evil.txt"),
            )

    def test_get_pending_jobs(self, tmp_staging_dir, monkeypatch):
        """get_pending_jobs returns only entries with status=pending."""
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_staging_dir.parent))
        manifest = StagingManifest(staging_root=tmp_staging_dir)

        # 1) job-pending stays in "pending" status (should be returned)
        manifest.add_pending("job-pending", "meshy", "image-to-3d", "/tmp/p.jpg")
        # 2) job-pending2 is also "pending" (should be returned)
        manifest.add_pending("job-pending2", "comfyui", "run_workflow", "/tmp/w.json")
        # 3) job-failed is set to "failed" (should NOT be returned)
        manifest.add_pending("job-failed", "meshy", "image-to-3d", "/tmp/f.jpg")
        manifest.update_job("job-failed", ue_import_status="failed")

        pending = manifest.get_pending_jobs()
        pending_ids = [j.id for j in pending]
        assert "job-pending" in pending_ids
        assert "job-pending2" in pending_ids
        # Failed should NOT be in pending
        assert "job-failed" not in pending_ids

    def test_cleanup_old_entries(self, tmp_staging_dir, monkeypatch):
        """cleanup_old_entries removes failed/timeout entries older than max_age_days."""
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_staging_dir.parent))
        manifest = StagingManifest(staging_root=tmp_staging_dir)

        # Fresh entry (today)
        manifest.add_pending("job-fresh", "meshy", "image-to-3d", "/tmp/fresh.jpg")
        manifest.update_job("job-fresh", ue_import_status="completed")

        # Old failed entry (10 days ago)
        manifest.add_pending("job-old-failed", "meshy", "image-to-3d", "/tmp/old.jpg")
        # Manually set created_at to 10 days ago
        old_data = manifest._load()
        for job in old_data["jobs"]:
            if job["id"] == "job-old-failed":
                old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat() + "Z"
                job["created_at"] = old_time
                job["ue_import_status"] = "failed"
        manifest._save(old_data)

        removed = manifest.cleanup_old_entries(max_age_days=7)

        assert removed == 1
        remaining_ids = [j["id"] for j in manifest._load()["jobs"]]
        assert "job-fresh" in remaining_ids
        assert "job-old-failed" not in remaining_ids

    def test_get_job_returns_entry(self, tmp_staging_dir, monkeypatch):
        """get_job returns a JobEntry by id, or None for missing."""
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_staging_dir.parent))
        manifest = StagingManifest(staging_root=tmp_staging_dir)

        manifest.add_pending("job-xyz", "comfyui", "run_workflow", "/tmp/w.json")
        job = manifest.get_job("job-xyz")

        assert job is not None
        assert job.id == "job-xyz"
        assert job.tool == "comfyui"
        assert job.operation == "run_workflow"

        missing = manifest.get_job("nonexistent")
        assert missing is None

    def test_find_by_hash_nonexistent(self, tmp_staging_dir, monkeypatch):
        """find_by_hash returns None when no matching entry exists."""
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_staging_dir.parent))
        manifest = StagingManifest(staging_root=tmp_staging_dir)

        result = manifest.find_by_hash(
            tool="meshy",
            operation="image-to-3d",
            input_hash="sha256:0000000000000000",
        )
        assert result is None