"""Phase 12-A — tests for mcp_installer + handlers/mcp_install."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from nyrahost import mcp_installer as mi
from nyrahost.handlers.mcp_install import McpInstallHandlers


def _fake_target(tmp_path: Path, key: str = "fake") -> mi.IDETarget:
    return mi.IDETarget(
        key=key,
        display_name="Fake IDE",
        config_path=tmp_path / ".fake" / "mcp.json",
    )


def test_list_targets_returns_known_set():
    targets = mi.list_targets()
    keys = {t.key for t in targets}
    assert "claude_code" in keys
    assert "cursor" in keys
    assert "vscode_user" in keys


def test_install_creates_file_with_nyra_entry(tmp_path):
    target = _fake_target(tmp_path)
    mi.install(target,
               python_exe=Path("/usr/bin/python3"),
               mcp_script=Path("/opt/nyra/mcp.py"),
               home_root=tmp_path)
    written = json.loads(target.config_path.read_text())
    assert "mcpServers" in written
    nyra = written["mcpServers"]["nyra"]
    assert nyra["type"] == "stdio"
    assert nyra["command"] == "/usr/bin/python3"
    assert nyra["args"] == ["/opt/nyra/mcp.py"]


def test_install_preserves_unrelated_servers(tmp_path):
    target = _fake_target(tmp_path)
    target.config_path.parent.mkdir(parents=True)
    target.config_path.write_text(json.dumps({
        "mcpServers": {
            "other": {"type": "stdio", "command": "x"},
        },
        "version": 1,
    }))
    mi.install(target,
               python_exe=Path("/p"), mcp_script=Path("/s"),
               home_root=tmp_path)
    written = json.loads(target.config_path.read_text())
    assert "other" in written["mcpServers"]
    assert "nyra" in written["mcpServers"]
    # unrelated top-level keys preserved
    assert written.get("version") == 1


def test_install_overwrites_existing_nyra_entry(tmp_path):
    target = _fake_target(tmp_path)
    mi.install(target, python_exe=Path("/p"), mcp_script=Path("/s1"),
               home_root=tmp_path)
    mi.install(target, python_exe=Path("/p"), mcp_script=Path("/s2"),
               home_root=tmp_path)
    written = json.loads(target.config_path.read_text())
    assert written["mcpServers"]["nyra"]["args"] == ["/s2"]


def test_install_rejects_path_outside_home(tmp_path, monkeypatch):
    """T-12-01 — config_path that resolves outside home is refused."""
    target = mi.IDETarget(
        key="evil",
        display_name="Bad",
        config_path=Path("/etc/passwd"),  # outside any home
    )
    with pytest.raises(ValueError, match="outside user home"):
        mi.install(target, python_exe=Path("/p"), mcp_script=Path("/s"),
                   home_root=tmp_path)


def test_install_rejects_corrupt_json(tmp_path):
    target = _fake_target(tmp_path)
    target.config_path.parent.mkdir(parents=True)
    target.config_path.write_text("this is not json {")
    with pytest.raises(ValueError, match="not valid JSON"):
        mi.install(target, python_exe=Path("/p"), mcp_script=Path("/s"),
                   home_root=tmp_path)


def test_uninstall_removes_only_nyra_entry(tmp_path):
    target = _fake_target(tmp_path)
    mi.install(target, python_exe=Path("/p"), mcp_script=Path("/s"),
               home_root=tmp_path)
    # Add an unrelated server
    cfg = json.loads(target.config_path.read_text())
    cfg["mcpServers"]["other"] = {"type": "stdio", "command": "x"}
    target.config_path.write_text(json.dumps(cfg))
    # Uninstall
    removed = mi.uninstall(target)
    assert removed is True
    cfg = json.loads(target.config_path.read_text())
    assert "nyra" not in cfg["mcpServers"]
    assert "other" in cfg["mcpServers"]


def test_uninstall_returns_false_when_absent(tmp_path):
    target = _fake_target(tmp_path)
    assert mi.uninstall(target) is False


# --- handler layer ---

def test_handler_list_targets():
    h = McpInstallHandlers(
        python_exe=Path("/p"), mcp_script=Path("/s"),
    )
    out = asyncio.run(h.on_list_targets({}))
    assert "targets" in out
    keys = {t["key"] for t in out["targets"]}
    assert "claude_code" in keys


def test_handler_install_success(tmp_path, monkeypatch):
    fake = _fake_target(tmp_path, key="myide")
    # Patch BOTH module references — handlers/mcp_install.py imports
    # list_targets by name, so the bound reference in that module needs
    # patching too.
    monkeypatch.setattr(mi, "list_targets", lambda: [fake])
    from nyrahost.handlers import mcp_install as mih
    monkeypatch.setattr(mih, "list_targets", lambda: [fake])
    h = McpInstallHandlers(
        python_exe=tmp_path / "py.exe",
        mcp_script=tmp_path / "mcp.py",
    )
    # The installer's home-root check still uses the real home dir;
    # patch it so our fake target (under tmp_path) passes.
    with patch.object(mi, "_home", lambda: tmp_path):
        out = asyncio.run(h.on_install({"key": "myide"}))
    assert out.get("installed") is True


def test_handler_unknown_target():
    h = McpInstallHandlers(python_exe=Path("/p"), mcp_script=Path("/s"))
    out = asyncio.run(h.on_install({"key": "atom"}))
    assert out["error"]["code"] == -32045
    assert out["error"]["message"] == "unknown_target"


def test_handler_missing_key():
    h = McpInstallHandlers(python_exe=Path("/p"), mcp_script=Path("/s"))
    out = asyncio.run(h.on_install({}))
    assert out["error"]["code"] == -32602


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
