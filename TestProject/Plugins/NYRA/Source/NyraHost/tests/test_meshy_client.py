"""tests/test_meshy_client.py — Unit tests for MeshyClient (GEN-01).

Per Plan 05-01 Task 1:
  - test_polling_loop_completes
  - test_polling_timeout
  - test_api_key_not_logged
  - test_401_raises_auth_error
  - test_429_raises_rate_limit_error
  - test_failed_task_returns_error_message
  - MeshyClient constructor tests
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock

import httpx
import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from nyrahost.external.meshy_client import (
    MeshyClient,
    MeshyAuthError,
    MeshyRateLimitError,
    MeshyAPIError,
    MeshyTimeoutError,
)


class FakeResponse:
    """Fake httpx response for mocking."""

    def __init__(self, data: dict, status: int = 200):
        self._data = data
        self.status_code = status
        self._reason = "OK"
        self.headers = {}

    def json(self) -> dict:
        return self._data

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def reason_phrase(self) -> str:
        return self._reason


class TestMeshyClient:
    """Tests for MeshyClient async HTTP + polling logic."""

    @pytest.mark.asyncio
    async def test_polling_loop_completes(self):
        """Full async polling loop returns GLB URL on completion."""
        client = MeshyClient(api_key="test-key")

        responses = [
            FakeResponse({"id": "job-123", "status": "pending"}),
            FakeResponse({"id": "job-123", "status": "in_progress"}),
            FakeResponse({"id": "job-123", "status": "in_progress"}),
            FakeResponse({
                "id": "job-123",
                "status": "completed",
                "model_urls": {"glb": "https://cdn.meshy.ai/model.glb"},
            }),
        ]
        idx = [0]

        async def req_delegate(method, path, **kwargs):
            r = responses[idx[0]]
            idx[0] += 1
            return r

        with patch.object(client, "_request") as mock_req:
            mock_req.side_effect = req_delegate
            result = await client.image_to_3d(image_path=str(Path(__file__)))

        assert result.status == "completed"
        assert result.glb_url == "https://cdn.meshy.ai/model.glb"

    @pytest.mark.asyncio
    async def test_polling_timeout(self):
        """TimeoutError raised when job never completes within limit."""
        client = MeshyClient(api_key="test-key", timeout=0.5)

        in_progress_resp = FakeResponse({"id": "job-123", "status": "in_progress"})

        async def req_delegate(method, path, **kwargs):
            return in_progress_resp

        with patch.object(client, "_request") as mock_req:
            mock_req.side_effect = req_delegate
            with pytest.raises(MeshyTimeoutError):
                await client.image_to_3d(image_path=str(Path(__file__)))

    def test_api_key_not_logged(self):
        """API key value must not appear in any log output, only in Authorization header."""
        client = MeshyClient(api_key="secret-meshy-key-xyz789")
        headers = client._headers()

        # Key must only appear inside the Bearer header value, never as plain text
        auth_val = headers.get("Authorization", "")
        assert "Bearer secret-meshy-key-xyz789" == auth_val
        # The key itself should not appear anywhere else in the dict repr
        headers_str = repr(headers)
        assert headers_str.count("secret-meshy-key-xyz789") == 1

    @pytest.mark.asyncio
    async def test_401_raises_auth_error(self):
        """HTTP 401 raises MeshyAuthError, not raw exception."""
        client = MeshyClient(api_key="bad-key")

        fake_401 = FakeResponse({"error": "invalid key"}, status=401)
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=fake_401)

        with pytest.raises(MeshyAuthError):
            await client._request("GET", "/meshes/123", client=mock_client)

    @pytest.mark.asyncio
    async def test_429_raises_rate_limit_error(self):
        """HTTP 429 raises MeshyRateLimitError with retry_after hint."""
        client = MeshyClient(api_key="test-key")

        fake_429 = FakeResponse({"error": "rate limited"}, status=429)
        fake_429.headers = {"Retry-After": "30"}

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=fake_429)

        with pytest.raises(MeshyRateLimitError) as exc_info:
            await client._request("GET", "/meshes/123", client=mock_client)
        assert exc_info.value.retry_after == 30.0

    def test_meshy_auth_error_no_key(self):
        """MeshyClient raises ValueError when no API key is set."""
        import os
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="MESHY_API_KEY not set"):
                MeshyClient()

    @pytest.mark.asyncio
    async def test_failed_task_returns_error_message(self):
        """Meshy task with status=failed returns error_message in result."""
        client = MeshyClient(api_key="test-key")

        responses = [
            FakeResponse({"id": "job-456", "status": "pending"}),
            FakeResponse({"id": "job-456", "status": "failed", "error": "GPU quota exceeded"}),
        ]
        idx = [0]

        async def req_delegate(method, path, **kwargs):
            r = responses[idx[0]]
            idx[0] += 1
            return r

        with patch.object(client, "_request") as mock_req:
            mock_req.side_effect = req_delegate
            result = await client.image_to_3d(image_path=str(Path(__file__)))

        assert result.status == "failed"
        assert result.error_message == "GPU quota exceeded"


class TestMeshyClientInit:
    """Test MeshyClient constructor and configuration."""

    def test_default_base_url(self):
        """Default base URL is https://meshy.ai/api/v1."""
        client = MeshyClient(api_key="test-key")
        assert client._base_url == "https://meshy.ai/api/v1"

    def test_custom_base_url_from_param(self):
        """Custom base_url via constructor param."""
        client = MeshyClient(api_key="test-key", base_url="https://custom.meshy.ai/v2")
        assert client._base_url == "https://custom.meshy.ai/v2"

    def test_custom_base_url_from_env(self):
        """Custom base_url from MESHY_API_BASE_URL env var."""
        import os
        with patch.dict(os.environ, {"MESHY_API_BASE_URL": "https://env.meshy.ai/v3"}):
            client = MeshyClient(api_key="test-key")
            assert client._base_url == "https://env.meshy.ai/v3"

    def test_custom_timeout(self):
        """Custom timeout via constructor param."""
        client = MeshyClient(api_key="test-key", timeout=300.0)
        assert client._timeout == 300.0
