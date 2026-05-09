"""tests/test_video_reference_analyzer.py — TDD tests for Wave 1 Video Reference Analyzer.

RED phase: These tests define the expected behavior.
They will FAIL until VideoReferenceAnalyzer and FFmpegKeyframeExtractor are implemented.
"""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from dataclasses import asdict

import sys
mock_unreal = MagicMock()
sys.modules['unreal'] = mock_unreal


class TestFFmpegKeyframeExtractor:
    """Tests for FFmpegKeyframeExtractor."""

    def test_extract_keyframes_returns_list_of_paths(self, tmp_path):
        """extract_keyframes() returns a list of keyframe file paths."""
        from nyrahost.tools.ffmpeg_extractor import FFmpegKeyframeExtractor

        video_path = tmp_path / "test_video.mp4"
        video_path.write_bytes(b"fake_video_data")

        extractor = FFmpegKeyframeExtractor(ffmpeg_path="ffmpeg")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="frame=001\nframe=002\nframe=003\n",
                stderr="",
            )
            with patch("glob.glob", return_value=[
                str(tmp_path / "nyra_kf_0001.jpg"),
                str(tmp_path / "nyra_kf_0002.jpg"),
                str(tmp_path / "nyra_kf_0003.jpg"),
            ]):
                with patch.object(Path, "exists", return_value=True):
                    keyframes = extractor.extract_keyframes(str(video_path), max_keyframes=16)
                    assert isinstance(keyframes, list)
                    assert len(keyframes) == 3

    def test_extract_keyframes_nonexistent_file_raises(self):
        """extract_keyframes() raises FileNotFoundError for non-existent video."""
        from nyrahost.tools.ffmpeg_extractor import FFmpegKeyframeExtractor

        extractor = FFmpegKeyframeExtractor(ffmpeg_path="ffmpeg")
        with pytest.raises(FileNotFoundError):
            extractor.extract_keyframes("/nonexistent/video.mp4")

    def test_scene_cut_detection_threshold(self):
        """Scene-cut detection uses threshold 0.3 per ROADMAP SC#3."""
        from nyrahost.tools.ffmpeg_extractor import FFmpegKeyframeExtractor

        extractor = FFmpegKeyframeExtractor(ffmpeg_path="ffmpeg")
        with patch("subprocess.run") as mock_run:
            extractor._run_ffmpeg_scene_detect("/fake/video.mp4", threshold=0.3)
            call_args = mock_run.call_args
            cmd_str = " ".join(call_args[0][0])
            assert "gt(scene,0.3)" in cmd_str


class TestVideoReferenceAnalyzer:
    """Tests for VideoReferenceAnalyzer."""

    def test_analyze_returns_video_reference_params(self):
        """analyze() returns a VideoReferenceParams instance."""
        from nyrahost.tools.video_reference_analyzer import VideoReferenceAnalyzer
        from nyrahost.tools.video_llm_parser import VideoReferenceParams

        analyzer = VideoReferenceAnalyzer(claude_backend=MagicMock())

        mock_claude_response = {
            "camera_move_type": "static",
            "camera_move_intensity": "slow",
            "camera_move_confidence": 0.9,
            "subject_position": [0.5, 0.5],
            "framing": "medium",
            "rule_of_thirds": True,
            "headroom": "normal",
            "lighting_mood_tags": ["warm", "golden"],
            "primary_color": [0.9, 0.6, 0.3],
            "primary_temperature_k": 3500,
            "fill_ratio": 0.3,
            "environment_type": "outdoor",
            "time_of_day": "golden_hour",
            "weather": "clear",
            "geometry_categories": ["figure", "street"],
            "clip_duration_seconds": 5.0,
            "keyframe_count": 8,
            "shot_blocks": [{
                "shot_id": "shot_01",
                "camera_move_type": "static",
                "start_time": 0.0, "end_time": 5.0,
                "start_position": [0, 0, 100], "end_position": [0, 0, 100],
                "start_rotation": [0, 0, 0], "end_rotation": [0, 0, 0],
                "fov": 35.0, "focus_distance": 3.0, "aperture": 2.8,
                "nl_description": "locked off",
                "user_confirmed": True,
            }],
            "analysis_confidence": 0.9,
        }

        async def mock_analyze(*args, **kwargs):
            return mock_claude_response

        with patch.object(analyzer, "_analyze_with_claude", mock_analyze):
            with patch.object(analyzer, "_extract_keyframes", return_value=["/tmp/kf1.jpg", "/tmp/kf2.jpg"]):
                with patch.object(analyzer, "_cleanup"):
                    with patch.object(analyzer, "_get_video_duration", return_value=5.0):
                        params = analyzer.analyze(source="/fake/video.mp4", source_type="file")
                        assert isinstance(params, VideoReferenceParams)
                        assert params.camera_move_type.value == "static"
                        assert params.requires_user_confirmation() is False

    def test_analyze_requires_confirmation_for_low_confidence(self):
        """analyze() sets requires_user_confirmation=True when confidence < 0.7."""
        from nyrahost.tools.video_reference_analyzer import VideoReferenceAnalyzer

        analyzer = VideoReferenceAnalyzer(claude_backend=MagicMock())

        mock_claude_response = {
            "camera_move_type": "unknown",
            "camera_move_intensity": "unknown",
            "camera_move_confidence": 0.4,
            "subject_position": [0.5, 0.5],
            "framing": "unknown",
            "rule_of_thirds": False,
            "headroom": "normal",
            "lighting_mood_tags": ["unknown"],
            "primary_color": [1, 1, 1],
            "primary_temperature_k": 5500,
            "fill_ratio": 0.5,
            "environment_type": "unknown",
            "time_of_day": "unknown",
            "weather": "unknown",
            "geometry_categories": [],
            "clip_duration_seconds": 5.0,
            "keyframe_count": 8,
            "shot_blocks": [{
                "shot_id": "shot_01",
                "camera_move_type": "unknown",
                "start_time": 0.0, "end_time": 5.0,
                "start_position": [0, 0, 0], "end_position": [0, 0, 0],
                "start_rotation": [0, 0, 0], "end_rotation": [0, 0, 0],
                "fov": 35.0, "focus_distance": 3.0, "aperture": 2.8,
                "nl_description": "unclear",
                "user_confirmed": False,
            }],
            "analysis_confidence": 0.4,
        }

        async def mock_analyze(*args, **kwargs):
            return mock_claude_response

        with patch.object(analyzer, "_analyze_with_claude", mock_analyze):
            with patch.object(analyzer, "_extract_keyframes", return_value=["/tmp/kf1.jpg"]):
                with patch.object(analyzer, "_cleanup"):
                    with patch.object(analyzer, "_get_video_duration", return_value=5.0):
                        params = analyzer.analyze(source="/fake/video.mp4", source_type="file")
                        assert params.requires_user_confirmation() is True

    def test_cleanup_deletes_video_file(self, tmp_path):
        """_cleanup() deletes the video file from /tmp after analysis."""
        from nyrahost.tools.video_reference_analyzer import VideoReferenceAnalyzer

        analyzer = VideoReferenceAnalyzer(claude_backend=MagicMock())

        video_file = tmp_path / "test_video.mp4"
        video_file.write_bytes(b"video_data")

        analyzer._cleanup(video_path=str(video_file), keyframe_paths=[])

        assert not video_file.exists(), "Video file should be deleted after cleanup"

    def test_cleanup_deletes_keyframe_files(self, tmp_path):
        """_cleanup() deletes keyframe files from /tmp after analysis."""
        from nyrahost.tools.video_reference_analyzer import VideoReferenceAnalyzer

        analyzer = VideoReferenceAnalyzer(claude_backend=MagicMock())

        keyframe_paths = [str(tmp_path / "kf_001.jpg"), str(tmp_path / "kf_002.jpg")]
        for kf in keyframe_paths:
            Path(kf).write_bytes(b"frame_data")

        analyzer._cleanup(video_path=None, keyframe_paths=keyframe_paths)

        for kf in keyframe_paths:
            assert not Path(kf).exists(), f"Keyframe {kf} should be deleted"

    def test_rejects_clips_longer_than_10_seconds(self):
        """analyze() raises ValueError for clips longer than 10 seconds."""
        from nyrahost.tools.video_reference_analyzer import VideoReferenceAnalyzer

        analyzer = VideoReferenceAnalyzer(claude_backend=MagicMock())

        with patch.object(analyzer, "_get_video_duration", return_value=15.0):
            with pytest.raises(ValueError, match="[Ll]onger than 10"):
                analyzer.analyze(source="/fake/video.mp4", source_type="file")

    def test_handles_youtube_url(self):
        """analyze() handles YouTube URLs by downloading via yt-dlp."""
        from nyrahost.tools.video_reference_analyzer import VideoReferenceAnalyzer

        analyzer = VideoReferenceAnalyzer(claude_backend=MagicMock())

        async def mock_download(*args, **kwargs):
            return "/tmp/downloaded_video.mp4"

        mock_claude_response = {
            "camera_move_type": "static", "camera_move_intensity": "slow",
            "camera_move_confidence": 0.9, "subject_position": [0.5, 0.5],
            "framing": "medium", "rule_of_thirds": True, "headroom": "normal",
            "lighting_mood_tags": ["neutral"], "primary_color": [1, 1, 1],
            "primary_temperature_k": 5500, "fill_ratio": 0.5, "environment_type": "indoor",
            "time_of_day": "unknown", "weather": "unknown", "geometry_categories": [],
            "clip_duration_seconds": 5.0, "keyframe_count": 8, "shot_blocks": [],
            "analysis_confidence": 0.9,
        }

        async def mock_analyze(*args, **kwargs):
            return mock_claude_response

        with patch.object(analyzer, "_download_youtube", mock_download):
            with patch.object(analyzer, "_get_video_duration", return_value=5.0):
                with patch.object(analyzer, "_extract_keyframes", return_value=["/tmp/kf1.jpg"]):
                    with patch.object(analyzer, "_analyze_with_claude", mock_analyze):
                        with patch.object(analyzer, "_cleanup"):
                            analyzer.analyze(source="https://youtube.com/watch?v=test123",
                                             source_type="youtube_url")
                            assert analyzer._video_path == "/tmp/downloaded_video.mp4"

    def test_handles_local_mp4_directly(self):
        """analyze() handles local mp4 files without yt-dlp."""
        from nyrahost.tools.video_reference_analyzer import VideoReferenceAnalyzer

        analyzer = VideoReferenceAnalyzer(claude_backend=MagicMock())

        mock_claude_response = {
            "camera_move_type": "dolly", "camera_move_intensity": "slow",
            "camera_move_confidence": 0.9, "subject_position": [0.5, 0.5],
            "framing": "medium", "rule_of_thirds": True, "headroom": "normal",
            "lighting_mood_tags": ["warm"], "primary_color": [0.9, 0.6, 0.3],
            "primary_temperature_k": 3500, "fill_ratio": 0.3, "environment_type": "outdoor",
            "time_of_day": "golden_hour", "weather": "clear", "geometry_categories": ["figure"],
            "clip_duration_seconds": 5.0, "keyframe_count": 8, "shot_blocks": [],
            "analysis_confidence": 0.9,
        }

        async def mock_analyze(*args, **kwargs):
            return mock_claude_response

        with patch.object(analyzer, "_get_video_duration", return_value=5.0):
            with patch.object(analyzer, "_extract_keyframes", return_value=["/tmp/kf1.jpg"]):
                with patch.object(analyzer, "_analyze_with_claude", mock_analyze):
                    with patch.object(analyzer, "_cleanup"):
                        with patch.object(analyzer, "_download_youtube",
                                          new_callable=AsyncMock) as mock_dl:
                            analyzer.analyze(source="/Users/test/my_clip.mp4", source_type="file")
                            mock_dl.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-q"])
