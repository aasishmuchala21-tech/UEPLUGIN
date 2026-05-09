"""tests/test_demo02_cli_tool.py — TDD tests for DEMO-02 CLI tool."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

import sys
mock_unreal = MagicMock()
sys.modules['unreal'] = mock_unreal


class TestDemo02CLITool:
    def test_rejects_clips_longer_than_10_seconds(self):
        """Tool rejects clips >10s with user-facing error."""
        from nyrahost.tools.demo02_cli_tool import Demo02CLITool

        tool = Demo02CLITool(claude_backend=MagicMock())

        with patch.object(tool, '_validate_file_duration', return_value=False):
            result = tool.execute({
                "source": "https://youtube.com/watch?v=longvideo",
                "source_type": "youtube_url",
            })
            assert not result.is_ok
            assert "10" in result.error

    def test_accepts_youtube_url(self):
        """Tool accepts YouTube URL."""
        from nyrahost.tools.demo02_cli_tool import Demo02CLITool

        tool = Demo02CLITool(claude_backend=MagicMock())

        with patch.object(tool, '_run_pipeline', new_callable=AsyncMock,
                          return_value={"requires_confirmation": False, "sequence_path": "/Game/Shot_001"}):
            result = tool.execute({
                "source": "https://youtube.com/watch?v=demo123",
                "source_type": "youtube_url",
            })
            assert result.is_ok
            assert result.data["source_type"] == "youtube_url"

    def test_accepts_local_mp4(self):
        """Tool accepts local mp4."""
        from nyrahost.tools.demo02_cli_tool import Demo02CLITool

        tool = Demo02CLITool(claude_backend=MagicMock())

        with patch.object(tool, '_run_pipeline', new_callable=AsyncMock,
                          return_value={"requires_confirmation": False, "sequence_path": "/Game/Shot_001"}):
            result = tool.execute({
                "source": "/Users/founder/my_clip.mp4",
                "source_type": "file",
            })
            assert result.is_ok
            assert result.data["source_type"] == "file"

    def test_returns_confirmation_required_true(self):
        """Returns requires_confirmation=True when orchestrator needs confirmation."""
        from nyrahost.tools.demo02_cli_tool import Demo02CLITool

        tool = Demo02CLITool(claude_backend=MagicMock())

        with patch.object(tool, '_run_pipeline', new_callable=AsyncMock,
                          return_value={
                              "requires_confirmation": True,
                              "confirmation_card": {"camera_move_type": "unknown"},
                              "message": "Confirm camera movement?",
                          }):
            result = tool.execute({
                "source": "/test.mp4",
                "source_type": "file",
            })
            assert result.is_ok
            assert result.data["requires_confirmation"] is True
            assert "confirmation_card" in result.data

    def test_returns_confirmation_required_false_with_sequence(self):
        """Returns sequence_path when assembly is complete."""
        from nyrahost.tools.demo02_cli_tool import Demo02CLITool

        tool = Demo02CLITool(claude_backend=MagicMock())

        with patch.object(tool, '_run_pipeline', new_callable=AsyncMock,
                          return_value={
                              "requires_confirmation": False,
                              "sequence_path": "/Game/NYRA_Demo02_outdoor",
                              "camera_actor_path": "/Game/NYRA_Demo02_Camera",
                              "camera_move_type": "dolly",
                              "lighting_mood_tags": ["golden", "warm"],
                              "message": "DEMO-02 complete",
                          }):
            result = tool.execute({
                "source": "/test.mp4",
                "source_type": "file",
            })
            assert result.is_ok
            assert result.data["requires_confirmation"] is False
            assert "sequence_path" in result.data
            assert result.data["camera_move_type"] == "dolly"

    def test_surfaces_ephemeral_disclaimer(self):
        """Tool surfaces ephemeral processing disclaimer."""
        from nyrahost.tools.demo02_cli_tool import Demo02CLITool

        tool = Demo02CLITool(claude_backend=MagicMock())
        assert "ephemeral" in tool.EPHEMERAL_DISCLAIMER.lower()
        assert "deleted after analysis" in tool.EPHEMERAL_DISCLAIMER

    def test_handles_youtube_download_failure(self):
        """YouTube download failure returns user-friendly error."""
        from nyrahost.tools.demo02_cli_tool import Demo02CLITool

        tool = Demo02CLITool(claude_backend=MagicMock())

        async def fail_download(*args, **kwargs):
            raise RuntimeError("[-32037] yt-dlp download failed: Connection refused")

        with patch.object(tool, '_run_pipeline', fail_download):
            result = tool.execute({
                "source": "https://youtube.com/watch?v=test",
                "source_type": "youtube_url",
            })
            assert not result.is_ok
            assert "download" in result.error.lower() or "32037" in result.error

    def test_handles_ffmpeg_extraction_failure(self):
        """ffmpeg extraction failure returns user-friendly error."""
        from nyrahost.tools.demo02_cli_tool import Demo02CLITool

        tool = Demo02CLITool(claude_backend=MagicMock())

        async def fail_extract(*args, **kwargs):
            raise RuntimeError("[-32036] Failed to extract any keyframes from")

        with patch.object(tool, '_run_pipeline', fail_extract):
            result = tool.execute({
                "source": "/test.mp4",
                "source_type": "file",
            })
            assert not result.is_ok
            assert "keyframe" in result.error.lower() or "32036" in result.error

    def test_handles_claude_analysis_failure(self):
        """Claude vision analysis failure returns user-friendly error."""
        from nyrahost.tools.demo02_cli_tool import Demo02CLITool

        tool = Demo02CLITool(claude_backend=MagicMock())

        async def fail_analysis(*args, **kwargs):
            raise RuntimeError("[-32040] Claude vision analysis failed")

        with patch.object(tool, '_run_pipeline', fail_analysis):
            result = tool.execute({
                "source": "/test.mp4",
                "source_type": "file",
            })
            assert not result.is_ok
            assert "Claude" in result.error or "32040" in result.error

    def test_auto_detects_youtube_url(self):
        """Auto-detect identifies YouTube URLs."""
        from nyrahost.tools.demo02_cli_tool import Demo02CLITool

        tool = Demo02CLITool(claude_backend=MagicMock())

        assert tool._detect_source_type("https://youtube.com/watch?v=test123") == "youtube_url"
        assert tool._detect_source_type("https://youtu.be/abc123") == "youtube_url"
        assert tool._detect_source_type("/Users/test/my_clip.mp4") == "file"
        assert tool._detect_source_type("C:\\Videos\\demo.mp4") == "file"


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-q"])
