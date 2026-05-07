"""tests/test_meshy_tools.py — Unit tests for Meshy MCP tools (GEN-01).

Per Plan 05-01 Task 1:
  - test_job_submission_returns_id
  - test_pending_manifest_entry_written
  - test_idempotent_dedup
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from nyrahost.tools.meshy_tools import MeshyImageTo3DTool, JobStatusTool
from nyrahost.tools.base import NyraToolResult


class TestMeshyImageTo3DTool:
    """Tests for MeshyImageTo3DTool."""

    @pytest.fixture
    def tool(self, tmp_path, monkeypatch):
        """Return tool with temp staging dir configured."""
        staging = tmp_path / "staging"
        staging.mkdir()
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        monkeypatch.setenv("MESHY_API_KEY", "test-key-123")
        return MeshyImageTo3DTool()

    def test_job_submission_returns_id(self, tool, tmp_path, monkeypatch):
        """execute() returns a job_id immediately without blocking."""
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"fake jpeg content")

        result = tool.execute({"image_path": str(img_path)})

        assert result.error is None
        assert "job_id" in result.data
        assert result.data["status"] == "pending"
        assert len(result.data["job_id"]) == 36  # UUID format

    def test_pending_manifest_entry_written(self, tool, tmp_path, monkeypatch):
        """After execute(), nyra_pending.json has a pending entry for the tool."""
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"fake jpeg content")

        result = tool.execute({"image_path": str(img_path)})

        manifest_path = tmp_path / "NYRA" / "staging" / "nyra_pending.json"
        assert manifest_path.exists(), "nyra_pending.json should be created"

        import json
        manifest = json.loads(manifest_path.read_text())
        assert len(manifest["jobs"]) == 1
        job = manifest["jobs"][0]
        assert job["tool"] == "meshy"
        assert job["operation"] == "image-to-3d"
        # Note: status may be "failed" (background task ran synchronously in test) or
        # "pending" (background task didn't run) — either way the entry was written.
        assert job["id"] == result.data["job_id"]

    def test_idempotent_dedup(self, tool, tmp_path, monkeypatch):
        """Two calls with same image_path return the SAME job_id."""
        # Prevent background polling from updating manifest between calls
        monkeypatch.setattr(
            "nyrahost.tools.meshy_tools._poll_meshy_and_update_manifest",
            lambda *args, **kwargs: None,  # noop — test runs in sync context
        )
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"fake jpeg content")

        result_1 = tool.execute({"image_path": str(img_path)})
        result_2 = tool.execute({"image_path": str(img_path)})

        assert result_1.data["job_id"] == result_2.data["job_id"], \
            "Idempotent re-submit should return existing job_id"

        # Only one entry in manifest
        manifest_path = tmp_path / "NYRA" / "staging" / "nyra_pending.json"
        import json
        manifest = json.loads(manifest_path.read_text())
        assert len(manifest["jobs"]) == 1, \
            "Manifest should have exactly one entry for idempotent re-submit"

    def test_missing_api_key_returns_error(self, tmp_path, monkeypatch):
        """execute() returns NyraToolResult.err when MESHY_API_KEY is not set."""
        monkeypatch.delenv("MESHY_API_KEY", raising=False)
        tool = MeshyImageTo3DTool()
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"fake")

        result = tool.execute({"image_path": str(img_path)})

        assert result.error is not None
        assert "MESHY_API_KEY not configured" in result.error

    def test_missing_image_path_returns_error(self, tool, tmp_path):
        """execute() returns NyraToolResult.err when image file does not exist."""
        result = tool.execute({"image_path": "/nonexistent/path/to/image.jpg"})

        assert result.error is not None
        assert "not found" in result.error.lower()


class TestJobStatusTool:
    """Tests for JobStatusTool."""

    @pytest.fixture
    def job_status_tool(self, tmp_path, monkeypatch):
        """Return JobStatusTool with temp staging dir configured."""
        staging = tmp_path / "staging"
        staging.mkdir()
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        return JobStatusTool()

    def test_returns_job_details(self, job_status_tool, tmp_path, monkeypatch):
        """nyra_job_status returns full job details for a known job_id."""
        import json
        manifest_path = tmp_path / "NYRA" / "staging" / "nyra_pending.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps({
            "version": 1,
            "jobs": [{
                "id": "test-job-abc-123",
                "tool": "meshy",
                "operation": "image-to-3d",
                "input_ref": "/tmp/test.jpg",
                "input_hash": "sha256:abcdef",
                "api_response": {},
                "downloaded_path": None,
                "ue_asset_path": None,
                "ue_import_status": "pending",
                "error_message": None,
                "created_at": "2026-05-07T12:00:00Z",
            }]
        }))

        result = job_status_tool.execute({"job_id": "test-job-abc-123"})

        assert result.error is None
        assert result.data["job_id"] == "test-job-abc-123"
        assert result.data["tool"] == "meshy"
        assert result.data["ue_import_status"] == "pending"

    def test_unknown_job_id_returns_error(self, job_status_tool):
        """nyra_job_status returns error for nonexistent job_id."""
        result = job_status_tool.execute({"job_id": "nonexistent-job-id"})

        assert result.error is not None
        assert "not found" in result.error.lower()