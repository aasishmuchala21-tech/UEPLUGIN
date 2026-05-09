"""Tests for claude_mcp_config.py — per-session MCP config writer (Plan 02-05)."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest


class TestWriteMcpConfig:
    """Unit tests for write_mcp_config() — pure function, no subprocess needed."""

    def test_writes_valid_json(self, tmp_path: Path):
        """Output file is valid JSON + schema-conformant (mcpServers.nyra.command, args, env)."""
        from nyrahost.backends.claude_mcp_config import write_mcp_config

        out = tmp_path / "test-session.json"
        write_mcp_config(
            session_id="sid-abc",
            conversation_id="cid-xyz",
            python_exe=Path("C:/bin/python.exe"),
            handshake_file=Path("C:/handshake.json"),
            out_path=out,
        )

        data = json.loads(out.read_text())
        assert "mcpServers" in data
        assert "nyra" in data["mcpServers"]
        nyra = data["mcpServers"]["nyra"]
        assert "command" in nyra
        assert "args" in nyra
        assert "env" in nyra

    def test_command_points_to_bundled_python(self, tmp_path: Path):
        """command field is the python_exe argument."""
        from nyrahost.backends.claude_mcp_config import write_mcp_config

        out = tmp_path / "test.json"
        write_mcp_config(
            session_id="sid",
            conversation_id="cid",
            python_exe=Path("D:/Nyra/Binaries/Win64/NyraHost/python/python.exe"),
            handshake_file=Path("D:/handshake.json"),
            out_path=out,
        )

        data = json.loads(out.read_text())
        assert (
            data["mcpServers"]["nyra"]["command"]
            == "D:/Nyra/Binaries/Win64/NyraHost/python/python.exe"
        )

    def test_args_include_handshake_file_flag(self, tmp_path: Path):
        """args list contains -m, nyrahost.mcp_server, --handshake-file, <path>."""
        from nyrahost.backends.claude_mcp_config import write_mcp_config

        out = tmp_path / "test.json"
        write_mcp_config(
            session_id="sid",
            conversation_id="cid",
            python_exe=Path("python"),
            handshake_file=Path("D:/Project/Saved/NYRA/handshake.json"),
            out_path=out,
        )

        args = json.loads(out.read_text())["mcpServers"]["nyra"]["args"]
        assert "-m" in args
        assert "nyrahost.mcp_server" in args
        assert "--handshake-file" in args
        # The handshake-file path comes after --handshake-file
        idx = args.index("--handshake-file")
        assert args[idx + 1] == "D:/Project/Saved/NYRA/handshake.json"

    def test_env_includes_session_and_conversation_ids(self, tmp_path: Path):
        """NYRA_SESSION_ID and NYRA_CONVERSATION_ID populated."""
        from nyrahost.backends.claude_mcp_config import write_mcp_config

        out = tmp_path / "test.json"
        write_mcp_config(
            session_id="my-session-123",
            conversation_id="my-conv-456",
            python_exe=Path("python"),
            handshake_file=Path("D:/hs.json"),
            out_path=out,
        )

        env = json.loads(out.read_text())["mcpServers"]["nyra"]["env"]
        assert env["NYRA_SESSION_ID"] == "my-session-123"
        assert env["NYRA_CONVERSATION_ID"] == "my-conv-456"

    def test_writes_to_localappdata_mcp_configs_dir(self, tmp_path: Path):
        """Out path under tmp_path is respected (DI path)."""
        from nyrahost.backends.claude_mcp_config import write_mcp_config

        out = tmp_path / "subdir" / "sid-abc.json"
        write_mcp_config(
            session_id="sid-abc",
            conversation_id="cid",
            python_exe=Path("python"),
            handshake_file=Path("D:/hs.json"),
            out_path=out,
        )
        assert out.is_file()
        data = json.loads(out.read_text())
        assert data["mcpServers"]["nyra"]["env"]["NYRA_SESSION_ID"] == "sid-abc"


class TestCleanupStaleConfigs:
    """Tests for cleanup_stale_configs() — stale-file GC helper."""

    def test_deletes_files_older_than_max_age(self, tmp_path: Path):
        """Files with mtime > max_age_seconds are deleted; newer ones are untouched."""
        from nyrahost.backends.claude_mcp_config import cleanup_stale_configs

        old = tmp_path / "old-session.json"
        old.write_text('{"mcpServers":{}}')
        new = tmp_path / "new-session.json"
        new.write_text('{"mcpServers":{}}')

        # Age the old file by setting its mtime to 2 days ago
        two_days_ago = time.time() - 172_800
        os.utime(old, times=(two_days_ago, two_days_ago))

        deleted = cleanup_stale_configs(tmp_path, max_age_seconds=86_400)
        assert deleted == 1
        assert not old.is_file()
        assert new.is_file()

    def test_does_not_delete_recent_files(self, tmp_path: Path):
        """Files modified within max_age_seconds are preserved."""
        from nyrahost.backends.claude_mcp_config import cleanup_stale_configs

        recent = tmp_path / "recent.json"
        recent.write_text('{"mcpServers":{}}')

        deleted = cleanup_stale_configs(tmp_path, max_age_seconds=86_400)
        assert deleted == 0
        assert recent.is_file()

    def test_returns_zero_when_dir_missing(self, tmp_path: Path):
        """Returns 0 and does not raise when mcp_configs_dir does not exist."""
        from nyrahost.backends.claude_mcp_config import cleanup_stale_configs

        missing = tmp_path / "nonexistent"
        assert cleanup_stale_configs(missing) == 0
