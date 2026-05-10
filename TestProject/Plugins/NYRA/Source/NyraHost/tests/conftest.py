"""Shared pytest fixtures for NyraHost.

Wave 0 placeholder bodies — Plan 08 wires real mock_llama_server and
mock_ollama_transport behaviour. The two deterministic fixtures
(tmp_project_dir, mock_handshake_file) are fully functional now so later
plans can depend on them without re-authoring.

Per CONTEXT.md:
  D-06 — Handshake schema {port, token, nyrahost_pid, ue_pid, started_at}
  CD-07 — <ProjectDir>/Saved/NYRA/ directory layout (logs/, models/, attachments/)
"""
from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Optional

import httpx
import pytest


@pytest.fixture
def tmp_project_dir(tmp_path: Path) -> Path:
    """Unique Path mirroring <ProjectDir>/Saved/NYRA/ layout.

    Returned Path is the project root (i.e. <ProjectDir>). Callers should
    compose `tmp_project_dir / "Saved" / "NYRA" / ...` to address the
    storage, logs, models, or attachments subtrees.

    Per CD-07 (SQLite sessions.db), CD-08 (attachments), D-16 (logs).
    """
    saved = tmp_path / "Saved" / "NYRA"
    (saved / "logs").mkdir(parents=True)
    (saved / "models").mkdir()
    (saved / "attachments").mkdir()
    return tmp_path


@pytest.fixture
def mock_handshake_file(tmp_path: Path) -> Path:
    """Writes a byte-exact D-06 handshake file and returns its Path.

    Shape: {"port": 54321, "token": <64-hex>, "nyrahost_pid": 11111,
             "ue_pid": 22222, "started_at": 1700000000000}

    The static port 54321 + pids 11111/22222 make grep-based assertions in
    later plans deterministic; `token` is a fresh 32-byte hex on every
    fixture invocation so Plan 06's auth tests can assert token rotation.
    """
    payload = {
        "port": 54321,
        "token": secrets.token_hex(32),
        "nyrahost_pid": 11111,
        "ue_pid": 22222,
        "started_at": 1700000000000,
    }
    f = tmp_path / "handshake-22222.json"
    f.write_text(json.dumps(payload))
    return f


@pytest.fixture
async def mock_llama_server():
    """Stub async fixture — Plan 08 wires the real mock.

    Target shape: returns an object with `.port`, `.url`, and `.stop()`
    that simulates `llama-server` printing
    `server listening at http://127.0.0.1:PORT` on stdout so the
    port-capture regex in Plan 08 (§3.3 spawn, §3.5 llama-server flags)
    can lock onto it.
    """
    return None


@pytest.fixture
def mock_ollama_transport():
    """Stub fixture — Plan 08 wires the real httpx.MockTransport.

    Target shape: returns an `httpx.MockTransport` that answers
    `GET /api/tags` with `{"models":[{"name":"gemma3:4b-it-qat",...}]}`
    so the detect-and-prefer-Ollama path (CONTEXT.md D-18) can be
    exercised without a running Ollama daemon.

    The `httpx` import is present in this file at module level to lock
    the dep at requirements-dev.lock time — once Plan 08 replaces the
    body with `httpx.MockTransport(...)` the import is already wired.
    """
    # Placeholder: reference httpx to keep the import used (mypy strict).
    _ = httpx
    return None


# =============================================================================
# Phase 5: External Tool Integration Fixtures (Plan 05-01)
# =============================================================================


def _build_mock_meshy_transport():
    """Build httpx MockTransport for Meshy API simulation.

    Returns a function that maps (method, url, headers, ...) -> (status, body).
    """
    def mock_handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path == "/api/v1/meshes":
            return httpx.Response(
                202,
                json={"id": "test-task-id-abc123", "status": "pending"},
            )
        if request.method == "GET" and path == "/api/v1/meshes/test-task-id-abc123":
            # Return "in_progress" on first poll, "completed" on second
            # httpx MockTransport doesn't maintain state between calls,
            # so we always return completed (tests that need in_progress
            # can override the fixture).
            return httpx.Response(
                200,
                json={
                    "id": "test-task-id-abc123",
                    "status": "completed",
                    "model_urls": {
                        "glb": "https://cdn.meshy.ai/models/test-task-id-abc123/model.glb"
                    },
                },
            )
        return httpx.Response(404, json={"error": "not found"})
    return mock_handler


class SlowMeshyTransport:
    """httpx MockTransport that returns in_progress forever (for timeout tests)."""
    def __init__(self, get_response: httpx.Response):
        self._response = get_response

    def __call__(self, request: httpx.Request) -> httpx.Response:
        return self._response


@pytest.fixture
def mock_meshy_api():
    """httpx MockTransport simulating Meshy API.

    POST /api/v1/meshes -> 202 task creation response
    GET  /api/v1/meshes/test-task-id-abc123 -> 200 completed response
    All other paths -> 404
    """
    transport = httpx.MockTransport(_build_mock_meshy_transport())
    return transport


@pytest.fixture
def slow_meshy_never_completes():
    """httpx MockTransport that returns status=in_progress forever (for timeout tests)."""
    in_progress_resp = httpx.Response(
        200,
        json={"id": "test-task-id-abc123", "status": "in_progress"},
    )
    transport = SlowMeshyTransport(in_progress_resp)
    return transport


@pytest.fixture
def tmp_staging_dir(tmp_path: Path) -> Path:
    """Create a real temp staging directory for manifest tests."""
    staging = tmp_path / "Staging"
    staging.mkdir(parents=True, exist_ok=True)
    return staging


@pytest.fixture
def tmp_manifest_path(tmp_staging_dir: Path) -> Path:
    """Create an empty nyra_pending.json in tmp_staging_dir."""
    manifest_path = tmp_staging_dir / "nyra_pending.json"
    manifest_path.write_text(json.dumps({"version": 1, "jobs": []}))
    return manifest_path


# ---------------------------------------------------------------------------
# Phase 6 integration fixtures (Plan 06-03)
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_reference_image(tmp_path: Path) -> Path:
    """Reference image bytes on disk for SceneAssembler.analyze_image.

    The Phase 6 pipeline only needs Path.exists() to return True before calling
    the (mocked) router; image decoding is the LLM provider's concern. We write
    a JPEG-magic-prefixed byte sequence so any future content-type sniff still
    classifies the file as an image without bloating the fixture.
    """
    img_path = tmp_path / "phase6_reference.jpg"
    img_path.write_bytes(b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00")
    return img_path


@pytest.fixture
def fake_meshy_tool():
    """Drop-in Meshy tool stub returning a deterministic asset_path."""
    from nyrahost.tools.base import NyraToolResult

    class _Tool:
        def execute(self, params):
            return NyraToolResult.ok({"asset_path": f"/Game/Meshy/{params.get('prompt', 'asset')}.uasset"})

    return _Tool()


@pytest.fixture
def fake_comfyui_tool():
    """Drop-in ComfyUI tool stub returning a deterministic asset_path."""
    from nyrahost.tools.base import NyraToolResult

    class _Tool:
        def execute(self, params):
            return NyraToolResult.ok({"asset_path": f"/Game/ComfyUI/{params.get('prompt', 'mat')}.M_Generated"})

    return _Tool()
