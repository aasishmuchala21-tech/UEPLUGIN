"""Phase 9 RIG-01 — tests for nyrahost.tools.rigging_tools (auto-rig)."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from nyrahost.tools import rigging_tools as rt
from nyrahost.external.meshy_client import (
    MeshyAPIError,
    MeshyAuthError,
    MeshyClient,
)


def _params(tmp_path) -> dict:
    return {
        "input_glb_url": "https://example.com/test_humanoid.glb",
        "height_meters": 1.7,
        "project_saved": str(tmp_path),
    }


@pytest.fixture(autouse=True)
def _set_meshy_key(monkeypatch):
    monkeypatch.setenv("MESHY_API_KEY", "test-key-not-real")
    yield


# (1) success: auto_rig is called with the right body, GLB downloads, response shape
def test_auto_rig_success(tmp_path, monkeypatch):
    async def fake_auto_rig(self, *, model_url, height_meters, **k):
        assert model_url == "https://example.com/test_humanoid.glb"
        assert height_meters == 1.7
        return "https://cdn.example.com/rigged_xyz.glb"

    class FakeResp:
        is_success = True
        status_code = 200
        content = b"FAKE_GLB"
        def raise_for_status(self): pass

    class FakeAsyncClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url): return FakeResp()

    with patch.object(MeshyClient, "auto_rig", new=fake_auto_rig), \
         patch.object(httpx, "AsyncClient", FakeAsyncClient):
        result = asyncio.run(rt.on_auto_rig(_params(tmp_path)))

    assert "error" not in result, result
    assert result["rigged_glb_path"].endswith(".glb")
    assert result["rigged_glb_url"] == "https://cdn.example.com/rigged_xyz.glb"


# (2) local-path input is rejected with -32035
def test_local_path_rejected(tmp_path):
    bad = _params(tmp_path)
    bad["input_glb_url"] = "/Users/foo/mesh.glb"
    with patch.object(MeshyClient, "auto_rig", new=AsyncMock(side_effect=AssertionError)):
        result = asyncio.run(rt.on_auto_rig(bad))
    assert result["error"]["code"] == -32035
    assert result["error"]["message"] == "input_must_be_url"


# (3) Meshy 401 maps to -32030 meshy_auth_failed
def test_auth_error_maps_to_minus32030(tmp_path):
    async def fake_auto_rig(self, **k):
        raise MeshyAuthError("invalid key")
    with patch.object(MeshyClient, "auto_rig", new=fake_auto_rig):
        result = asyncio.run(rt.on_auto_rig(_params(tmp_path)))
    assert result["error"]["code"] == -32030
    assert result["error"]["message"] == "meshy_auth_failed"


# (4) Meshy API error during rigging maps to -32038 meshy_rig_failed
def test_api_error_maps_to_minus32038(tmp_path):
    async def fake_auto_rig(self, **k):
        raise MeshyAPIError("HTTP 500 from Meshy")
    with patch.object(MeshyClient, "auto_rig", new=fake_auto_rig):
        result = asyncio.run(rt.on_auto_rig(_params(tmp_path)))
    assert result["error"]["code"] == -32038
    assert result["error"]["message"] == "meshy_rig_failed"


# (5) Missing input_glb_url returns -32602 missing_field
def test_missing_url_rejected(tmp_path):
    bad = _params(tmp_path)
    del bad["input_glb_url"]
    result = asyncio.run(rt.on_auto_rig(bad))
    assert result["error"]["code"] == -32602
    assert result["error"]["message"] == "missing_field"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
