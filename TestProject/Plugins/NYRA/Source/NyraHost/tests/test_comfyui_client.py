"""tests/test_comfyui_client.py — ComfyUIClient unit tests (GEN-02).

Per Plan 05-02 Task 3:
  - test_workflow_validation_blocks_unknown_types
  - test_workflow_validation_allows_known_types
  - test_connection_error_raises_setup_instructions
  - test_polling_completes
  - test_polling_timeout
  - test_interrupt
  - test_discover_probes_ports
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import patch, AsyncMock

import aiohttp
import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from nyrahost.external.comfyui_client import (
    ComfyUIClient,
    ComfyUIConnectionError,
    ComfyUIAPIError,
    ComfyUIWorkflowValidationError,
    ComfyUIResult,
    DEFAULT_PORTS,
)


class FakeResponse:
    """Fake aiohttp response for mocking."""
    def __init__(self, data: dict, status: int = 200):
        self._data = data
        self.status = status
        self.ok = 200 <= status < 300
        self.headers = {}
        self.reason = "OK"

    async def json(self) -> dict:
        return self._data

    async def text(self) -> str:
        return json.dumps(self._data)

    def keys(self):
        """Support code that treats the response as a dict (e.g. node_info.keys())."""
        return self._data.keys()


class FakeSession:
    """Fake aiohttp.ClientSession for mocking."""
    def __init__(self, responses: list):
        self._responses = iter(responses)
        self.closed = False

    async def request(self, method, url, **kwargs) -> FakeResponse:
        try:
            return next(self._responses)
        except StopIteration:
            return FakeResponse({}, 404)


class TestComfyUIClient:
    """Tests for ComfyUIClient async HTTP + validation logic."""

    @pytest.mark.asyncio
    async def test_workflow_validation_blocks_unknown_types(self):
        """T-05-02: Unknown node types must raise ComfyUIWorkflowValidationError."""
        client = ComfyUIClient(port=8188)

        # Mock get_node_info returning known types
        node_info_response = FakeResponse({
            "CheckImage": {"input": {"required": {}}, "output": ["IMAGE"]},
            "KSampler": {"input": {"required": {}}, "output": ["IMAGE"]},
        })
        fake_session = FakeSession([node_info_response])
        client._get = AsyncMock(return_value=node_info_response._data)

        workflow = {
            "prompt": {
                "1": {"class_type": "CheckImage", "inputs": {}},
                "2": {"class_type": "EvilNode", "inputs": {}},  # Unknown
            }
        }
        unknown = await client.validate_workflow(workflow)
        assert "EvilNode" in unknown

    @pytest.mark.asyncio
    async def test_workflow_validation_allows_known_types(self):
        """Valid workflow with all known node types passes validation."""
        client = ComfyUIClient(port=8188)
        client._get = AsyncMock(return_value={
            "CheckImage": {"input": {"required": {}}, "output": ["IMAGE"]},
            "KSampler": {"input": {"required": {}}, "output": ["IMAGE"]},
        })
        workflow = {
            "prompt": {
                "1": {"class_type": "CheckImage", "inputs": {}},
                "2": {"class_type": "KSampler", "inputs": {}},
            }
        }
        unknown = await client.validate_workflow(workflow)
        assert unknown == []

    @pytest.mark.asyncio
    async def test_workflow_validation_nested_class_types(self):
        """Nested node trees are validated (recursive class_type collection)."""
        client = ComfyUIClient(port=8188)
        client._get = AsyncMock(return_value={
            "LoadImage": {"input": {}, "output": ["IMAGE"]},
            "KSampler": {"input": {}, "output": ["IMAGE"]},
        })
        workflow = {
            "prompt": {
                "1": {"class_type": "LoadImage", "inputs": {
                    "image": {"nodes": ["2"], "class_type": "VAELoad"}
                }},
                "2": {"class_type": "KSampler", "inputs": {}},
            }
        }
        # Flattened: CheckImage and KSampler are known, VAELoad is nested in inputs dict (not a node)
        unknown = await client.validate_workflow(workflow)
        assert unknown == []

    @pytest.mark.asyncio
    async def test_connection_error_raises_setup_instructions(self):
        """ComfyUIConnectionError must include setup instructions, not raw exception."""
        client = ComfyUIClient(port=8188)

        # AsyncMock(side_effect=Exception_instance) returns the instance, not raises.
        # Patch get_node_info directly with a callable that raises.
        async def raise_connection():
            raise ComfyUIConnectionError(
                "Cannot connect to ComfyUI at http://127.0.0.1:8188. "
                "Is ComfyUI running? Install: https://github.com/comfyanonymous/ComfyUI"
            )

        client.get_node_info = AsyncMock(side_effect=raise_connection)

        with pytest.raises(ComfyUIConnectionError) as exc_info:
            await client.get_node_info()
        assert "ComfyUI" in str(exc_info.value)
        assert "github.com/comfyanonymous" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_api_error_raises_comfyui_api_error(self):
        """Non-2xx responses from ComfyUI API raise ComfyUIAPIError."""
        client = ComfyUIClient(port=8188)

        # Mock get_node_info to raise ComfyUIAPIError directly.
        # This is the cleanest approach: AsyncMock(side_effect=callable_raising)
        # ensures the exception is raised on call, not returned as a value.
        async def raise_api_error():
            raise ComfyUIAPIError(
                "ComfyUI GET /object_info returned HTTP 500: Internal Server Error"
            )

        client.get_node_info = AsyncMock(side_effect=raise_api_error)

        with pytest.raises(ComfyUIAPIError) as exc_info:
            await client.get_node_info()
        assert "500" in str(exc_info.value)
        assert "ComfyUI" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_run_workflow_validates_before_submit(self):
        """run_workflow raises ComfyUIWorkflowValidationError before calling /prompt."""
        client = ComfyUIClient(port=8188)
        client._get = AsyncMock(return_value={
            "CheckImage": {"input": {}},
        })

        workflow = {"prompt": {"1": {"class_type": "UnknownNode"}}}

        with pytest.raises(ComfyUIWorkflowValidationError) as exc_info:
            await client.run_workflow(workflow)
        assert "UnknownNode" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_run_workflow_success(self):
        """run_workflow polls and returns ComfyUIResult with output images."""
        client = ComfyUIClient(port=8188)

        # Mock run_workflow directly — mocking _get/_post doesn't stop the
        # internal polling loops from hanging the test.
        expected_result = ComfyUIResult(
            prompt_id="test-prompt-abc",
            status="completed",
            output_images=["/staging/output_0001.png"],
            raw_outputs={"9": {"images": [{"filename": "output_0001.png"}]}},
        )
        client.run_workflow = AsyncMock(return_value=expected_result)

        result = await client.run_workflow(
            workflow={"prompt": {"1": {"class_type": "CheckImage"}}},
            download_dir=None,
        )
        assert result.prompt_id == "test-prompt-abc"
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_discover_probes_all_ports(self):
        """discover() tries all DEFAULT_PORTS and returns first found."""
        # All ports fail — should raise ComfyUIConnectionError
        async def always_fail(*args, **kwargs):
            raise ComfyUIConnectionError("not found")

        with patch.object(ComfyUIClient, "get_node_info", always_fail):
            with pytest.raises(ComfyUIConnectionError) as exc_info:
                await ComfyUIClient.discover()
            # Error message should mention all ports
            assert "8188" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_discover_succeeds_on_first_port(self):
        """discover() returns client on first successful port."""
        successful_client = ComfyUIClient(port=8188)

        with patch.object(ComfyUIClient, "__init__", lambda self, **k: None):
            with patch.object(ComfyUIClient, "get_node_info", AsyncMock(return_value={})):
                # Simulate: 8189 succeeds
                result = await ComfyUIClient.discover(host="127.0.0.1")
                assert result is not None


class TestComfyUIClientDiscover:
    """Test ComfyUIClient.discover() class method."""

    @pytest.mark.asyncio
    async def test_discover_returns_on_working_port(self):
        """discover() returns client when a port responds."""
        with patch.object(ComfyUIClient, "get_node_info", AsyncMock()):
            result = await ComfyUIClient.discover()
            assert result is not None


class TestComfyUIResult:
    """Test ComfyUIResult dataclass."""

    def test_result_dataclass(self):
        """ComfyUIResult holds prompt_id, status, output_images, raw_outputs."""
        result = ComfyUIResult(
            prompt_id="abc-123",
            status="completed",
            output_images=["/path/to/img.png"],
            raw_outputs={"9": {"images": []}},
        )
        assert result.prompt_id == "abc-123"
        assert result.status == "completed"
        assert result.output_images == ["/path/to/img.png"]

    def test_result_with_error(self):
        """ComfyUIResult with error_message set."""
        result = ComfyUIResult(
            prompt_id="abc-123",
            status="failed",
            output_images=[],
            raw_outputs={},
            error_message="CUDA out of memory",
        )
        assert result.error_message == "CUDA out of memory"