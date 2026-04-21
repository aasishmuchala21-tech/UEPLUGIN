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
import secrets
from pathlib import Path

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
