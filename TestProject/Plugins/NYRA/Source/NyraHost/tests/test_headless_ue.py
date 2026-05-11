"""Phase 12-B — tests for tools.headless_ue (HeadlessUEManager)."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nyrahost.tools import headless_ue as hu


def test_no_uproject_returns_error(tmp_path):
    mgr = hu.HeadlessUEManager()
    out = asyncio.run(mgr.launch({"cwd": str(tmp_path)}))
    assert out["error"]["code"] == -32047
    assert out["error"]["message"] == "no_uproject_in_cwd"


def test_invalid_project_path_returns_error(tmp_path):
    mgr = hu.HeadlessUEManager()
    out = asyncio.run(mgr.launch({"project_path": str(tmp_path / "nope.uproject")}))
    assert out["error"]["code"] == -32047
    assert out["error"]["message"] == "project_not_found"


def test_multiple_uprojects_returns_error(tmp_path):
    (tmp_path / "A.uproject").write_text("{}")
    (tmp_path / "B.uproject").write_text("{}")
    mgr = hu.HeadlessUEManager()
    out = asyncio.run(mgr.launch({"cwd": str(tmp_path)}))
    assert out["error"]["code"] == -32047
    assert out["error"]["message"] == "multiple_uprojects"


def test_editor_not_found_returns_error(tmp_path, monkeypatch):
    proj = tmp_path / "Game.uproject"
    proj.write_text("{}")
    # No editor on PATH; no UE_56_DIR
    monkeypatch.delenv("UE_56_DIR", raising=False)
    monkeypatch.delenv("UE_INSTALL_DIR", raising=False)
    with patch.object(hu.shutil, "which", return_value=None):
        mgr = hu.HeadlessUEManager()
        out = asyncio.run(mgr.launch({"project_path": str(proj)}))
    assert out["error"]["code"] == -32048


def test_launch_success_returns_pid(tmp_path):
    proj = tmp_path / "Game.uproject"
    proj.write_text("{}")
    fake_proc = MagicMock()
    fake_proc.pid = 4242
    fake_proc.returncode = None

    async def fake_create(*argv, **k):
        return fake_proc

    fake_editor = tmp_path / "UnrealEditor-Cmd.exe"
    fake_editor.write_text("#fake")

    with patch.object(hu, "_resolve_editor_exe", return_value=fake_editor), \
         patch.object(asyncio, "create_subprocess_exec", side_effect=fake_create):
        mgr = hu.HeadlessUEManager()
        out = asyncio.run(mgr.launch({"project_path": str(proj)}))

    assert out.get("launched") is True
    assert out["pid"] == 4242
    assert out["project_path"] == str(proj)


def test_already_running_short_circuits(tmp_path):
    """Calling launch twice without shutdown returns already_running."""
    proj = tmp_path / "Game.uproject"
    proj.write_text("{}")
    fake_proc = MagicMock()
    fake_proc.pid = 4242
    fake_proc.returncode = None

    async def fake_create(*argv, **k):
        return fake_proc

    fake_editor = tmp_path / "UnrealEditor-Cmd.exe"
    fake_editor.write_text("#fake")

    with patch.object(hu, "_resolve_editor_exe", return_value=fake_editor), \
         patch.object(asyncio, "create_subprocess_exec", side_effect=fake_create):
        mgr = hu.HeadlessUEManager()
        asyncio.run(mgr.launch({"project_path": str(proj)}))
        out = asyncio.run(mgr.launch({"project_path": str(proj)}))
    assert out.get("already_running") is True


def test_status_when_not_running():
    mgr = hu.HeadlessUEManager()
    out = asyncio.run(mgr.status({}))
    assert out == {"running": False}


def test_status_when_exited(tmp_path):
    fake_proc = MagicMock()
    fake_proc.pid = 4242
    fake_proc.returncode = 0
    mgr = hu.HeadlessUEManager()
    mgr._session = hu.HeadlessSession(
        pid=4242, project_path="/x.uproject", editor_exe="/ue.exe",
        proc=fake_proc,
    )
    out = asyncio.run(mgr.status({}))
    assert out["running"] is False
    assert out["exited"] is True
    assert out["exit_code"] == 0
    # Session cleared
    assert mgr._session is None


def test_shutdown_with_no_session():
    mgr = hu.HeadlessUEManager()
    out = asyncio.run(mgr.shutdown({}))
    assert out["error"]["code"] == -32050


def test_shutdown_terminates_running_process():
    mgr = hu.HeadlessUEManager()
    fake_proc = MagicMock()
    fake_proc.pid = 4242
    fake_proc.returncode = None
    fake_proc.terminate = MagicMock()
    fake_proc.wait = AsyncMock(return_value=0)
    fake_proc.returncode = None  # still

    # After terminate + wait, simulate clean exit
    async def waiter():
        fake_proc.returncode = 0
        return 0
    fake_proc.wait = AsyncMock(side_effect=waiter)

    mgr._session = hu.HeadlessSession(
        pid=4242, project_path="/x.uproject", editor_exe="/ue.exe",
        proc=fake_proc,
    )
    out = asyncio.run(mgr.shutdown({}))
    assert out["shutdown"] is True
    assert mgr._session is None
    fake_proc.terminate.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
