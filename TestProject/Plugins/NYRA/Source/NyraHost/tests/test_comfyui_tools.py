"""tests/test_comfyui_tools.py — ComfyUI MCP tool unit tests (GEN-02).

Per Plan 05-02 Task 3:
  - test_workflow_submission_returns_job_id
  - test_workflow_validated_before_submit
  - test_get_node_info_returns_types
  - test_get_node_info_connection_error
  - test_get_node_info_class_type_filter_found
  - test_get_node_info_class_type_filter_not_found
"""
from __future__ import annotations

import json as _json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nyrahost.tools.comfyui_tools import (
    ComfyUIRunWorkflowTool,
    ComfyUIGetNodeInfoTool,
)
from nyrahost.external.comfyui_client import (
    ComfyUIClient,
    ComfyUIConnectionError,
    ComfyUIAPIError,
    ComfyUIWorkflowValidationError,
)
from nyrahost.tools.base import NyraToolResult


class TestComfyUIRunWorkflowTool:
    """Tests for ComfyUIRunWorkflowTool.execute()."""

    def test_workflow_submission_returns_job_id(self):
        """nyra_comfyui_run_workflow returns a job_id immediately (non-blocking)."""
        mock_manifest = MagicMock()
        mock_manifest.add_pending.return_value = MagicMock(id="test-job-xyz")

        mock_client = MagicMock()
        mock_client.get_node_info = AsyncMock(return_value={
            "CheckImage": {"input": {"required": {}}, "output": ["IMAGE"]},
        })

        with patch(
            "nyrahost.tools.comfyui_tools.StagingManifest", return_value=mock_manifest
        ):
            with patch.object(
                ComfyUIClient,
                "discover",
                new=AsyncMock(return_value=mock_client),
            ):
                tool = ComfyUIRunWorkflowTool()
                workflow = {
                    "prompt": {"1": {"class_type": "CheckImage", "inputs": {}}}
                }
                result = tool.execute({"workflow_json": workflow})

        assert result.error is None, f"Expected no error, got: {result.error}"
        assert "job_id" in result.data, f"Expected job_id in result, got: {result.data}"
        assert result.data["status"] == "pending"
        mock_manifest.add_pending.assert_called_once()
        call_kwargs = mock_manifest.add_pending.call_args
        assert call_kwargs.kwargs["tool"] == "comfyui"
        assert call_kwargs.kwargs["operation"] == "run_workflow"

    def test_workflow_with_target_folder(self):
        """target_folder parameter is passed to manifest and returned in result."""
        mock_manifest = MagicMock()
        mock_manifest.add_pending.return_value = MagicMock(id="test-job-folder")

        mock_client = MagicMock()

        with patch(
            "nyrahost.tools.comfyui_tools.StagingManifest", return_value=mock_manifest
        ):
            with patch.object(
                ComfyUIClient,
                "discover",
                new=AsyncMock(return_value=mock_client),
            ):
                tool = ComfyUIRunWorkflowTool()
                result = tool.execute({
                    "workflow_json": {"prompt": {}},
                    "target_folder": "/Game/MyTextures",
                })

        assert result.data["target_folder"] == "/Game/MyTextures"
        call_kwargs = mock_manifest.add_pending.call_args
        api_resp = call_kwargs.kwargs["api_response"]
        assert api_resp["target_folder"] == "/Game/MyTextures"

    def test_comfyui_not_found_returns_error(self):
        """ComfyUI server not found returns NyraToolResult.err with setup instructions."""
        with patch(
            "nyrahost.tools.comfyui_tools.asyncio.run",
            side_effect=ComfyUIConnectionError(
                "No ComfyUI server found on 127.0.0.1 at ports [8188, 8189, 8190]"
            ),
        ):
            tool = ComfyUIRunWorkflowTool()
            result = tool.execute({"workflow_json": {"prompt": {}}})

        assert result.error is not None
        assert "ComfyUI" in result.error
        assert "8188" in result.error


class TestComfyUIGetNodeInfoTool:
    """Tests for ComfyUIGetNodeInfoTool.execute()."""

    def test_get_node_info_returns_types(self):
        """nyra_comfyui_get_node_info returns node type list when server is available."""
        tool = ComfyUIGetNodeInfoTool()

        mock_client = MagicMock()
        mock_client.get_node_info = AsyncMock(
            return_value={
                "CheckImage": {"input": {"required": {}}, "output": ["IMAGE"]},
                "KSampler": {"input": {"required": {}}, "output": ["IMAGE"]},
                "VAEDecode": {"input": {"required": {}}, "output": ["IMAGE"]},
            }
        )

        with patch.object(
            ComfyUIClient,
            "discover",
            new=AsyncMock(return_value=mock_client),
        ):
            result = tool.execute({})

        assert result.error is None
        assert result.data.get("node_count") >= 2
        assert "node_types" in result.data
        assert "CheckImage" in result.data["node_types"]
        assert "KSampler" in result.data["node_types"]

    def test_get_node_info_connection_error(self):
        """ComfyUI server not found returns NyraToolResult.err with setup instructions."""
        tool = ComfyUIGetNodeInfoTool()

        with patch(
            "nyrahost.tools.comfyui_tools.asyncio.run",
            side_effect=ComfyUIConnectionError(
                "No ComfyUI server found on 127.0.0.1 at ports [8188, 8189, 8190]"
            ),
        ):
            result = tool.execute({})

        assert result.error is not None
        assert "ComfyUI" in result.error
        assert "8188" in result.error

    def test_get_node_info_class_type_filter_found(self):
        """class_type filter returns schema for a specific node."""
        tool = ComfyUIGetNodeInfoTool()

        mock_client = MagicMock()
        mock_client.get_node_info = AsyncMock(
            return_value={
                "KSampler": {
                    "input": {"required": {"model": "MODEL", "seed": "INT"}},
                    "output": ["IMAGE"],
                }
            }
        )

        with patch.object(
            ComfyUIClient,
            "discover",
            new=AsyncMock(return_value=mock_client),
        ):
            result = tool.execute({"class_type": "KSampler"})

        assert result.error is None
        assert result.data["class_type"] == "KSampler"
        assert "input" in result.data

    def test_get_node_info_class_type_filter_not_found(self):
        """class_type filter returns error for unknown node type."""
        tool = ComfyUIGetNodeInfoTool()

        mock_client = MagicMock()
        mock_client.get_node_info = AsyncMock(
            return_value={
                "CheckImage": {"input": {}},
                "KSampler": {"input": {}},
            }
        )

        with patch.object(
            ComfyUIClient,
            "discover",
            new=AsyncMock(return_value=mock_client),
        ):
            result = tool.execute({"class_type": "NonExistentNode"})

        assert result.error is not None
        assert "NonExistentNode" in result.error
        assert "[-32042]" in result.error

    def test_get_node_info_api_error(self):
        """API error returns NyraToolResult.err."""
        tool = ComfyUIGetNodeInfoTool()

        mock_client = MagicMock()
        mock_client.get_node_info = AsyncMock(
            side_effect=ComfyUIAPIError("500 Internal Server Error")
        )

        with patch.object(
            ComfyUIClient,
            "discover",
            new=AsyncMock(return_value=mock_client),
        ):
            result = tool.execute({})

        assert result.error is not None
        assert "[-32041]" in result.error
        assert "ComfyUI API error" in result.error


class TestComfyUIToolParameters:
    """Test that tools have correct MCP-compatible parameter schemas."""

    def test_run_workflow_tool_has_required_schema_fields(self):
        """ComfyUIRunWorkflowTool has name, description, parameters for MCP registration."""
        tool = ComfyUIRunWorkflowTool()
        assert tool.name == "nyra_comfyui_run_workflow"
        assert "workflow_json" in tool.parameters["properties"]
        assert "required" in tool.parameters
        assert "workflow_json" in tool.parameters["required"]

    def test_get_node_info_tool_has_required_schema_fields(self):
        """ComfyUIGetNodeInfoTool has name, description, parameters for MCP registration."""
        tool = ComfyUIGetNodeInfoTool()
        assert tool.name == "nyra_comfyui_get_node_info"
        assert tool.parameters["type"] == "object"
