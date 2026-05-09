---
phase: "07"
plan: "07-01"
type: tdd
wave: 1
depends_on:
  - "07-00"
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/video_reference_analyzer.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/ffmpeg_extractor.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_video_reference_analyzer.py
autonomous: true
requirements:
  - SCENE-02
  - DEMO-02
user_setup:
  - service: ffmpeg
    why: "Video frame extraction — bundled in Phase 5 Binaries/ThirdParty/"
    env_vars:
      - name: FFMPEG_PATH
        source: "Resolves to NyraHost/Binaries/ThirdParty/ffmpeg/ffmpeg.exe (Phase 5 bundled)"
  - service: yt-dlp
    why: "YouTube video download from URL"
    env_vars:
      - name: YT_DLP_PATH
        source: "Resolves to NyraHost/Binaries/ThirdParty/yt-dlp/yt-dlp.exe (Phase 5 bundled)"
must_haves:
  truths:
    - "User pastes a YouTube URL or attaches an mp4, NYRA extracts ≤16 keyframes using ffmpeg scene-cut detection"
    - "Keyframes are sent to Claude Opus vision with the analysis prompt, and structured VideoReferenceParams JSON is returned"
    - "The video file is deleted from /tmp within 5 minutes of paste (ephemeral processing)"
    - "DEMO-02 SC#3 and SC#4: ffmpeg keyframe extraction + semantic lighting extraction + /tmp cleanup"
  artifacts:
    - path: "NyraHost/src/nyrahost/tools/ffmpeg_extractor.py"
      provides: "FFmpegKeyframeExtractor — scene-cut detection + keyframe extraction + cleanup"
      min_lines: 100
    - path: "NyraHost/src/nyrahost/tools/video_reference_analyzer.py"
      provides: "VideoReferenceAnalyzer — yt-dlp download + ffmpeg extract + Claude vision → VideoReferenceParams"
      min_lines: 120
  key_links:
    - from: "NyraHost/video_reference_analyzer.py"
      to: "NyraHost/tools/video_llm_parser.py"
      via: "returns VideoReferenceParams dataclass"
      pattern: "VideoReferenceParams|ShotBlock"
    - from: "NyraHost/ffmpeg_extractor.py"
      to: "NyraHost/backends/claude.py"
      via: "sends base64-encoded keyframes to Claude Opus"
      pattern: "claude|backend.*vision"
    - from: "NyraHost/ffmpeg_extractor.py"
      to: "/tmp"
      via: "writes keyframes to /tmp/nyra_keyframes/, deletes video after processing"
      pattern: "tmp.*delete|cleanup"
---

<objective>
Implement the Video Reference Analyzer (Wave 1): yt-dlp download, ffmpeg scene-cut keyframe extraction (≤16 keyframes), Claude Opus vision analysis returning VideoReferenceParams JSON, and ephemeral /tmp cleanup. This plan uses TDD — tests are written first.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/video_llm_parser.py
@TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/sequencer_tools.py
@TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/claude.py
</context>

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From video_llm_parser.py (Wave 0 output):
```python
@dataclass
class VideoReferenceParams:
    shot_blocks: list[ShotBlock]
    subject_position: tuple[float, float]
    framing: str  # "extreme_close_up"|"close_up"|"medium"|"full"|"wide"|"establishing"
    rule_of_thirds: bool
    headroom: str  # "tight"|"normal"|"loose"
    lighting_mood_tags: list[str]
    primary_color: tuple[float, float, float]  # RGB 0-1
    primary_temperature_k: float
    fill_ratio: float  # 0-1
    camera_move_type: CameraMoveType
    camera_move_intensity: str  # "slow"|"medium"|"fast"
    camera_move_confidence: float  # 0-1
    environment_type: str  # "indoor"|"outdoor"|"studio"|"VFX_plate"
    time_of_day: str
    weather: str
    geometry_categories: list[str]
    clip_duration_seconds: float
    keyframe_count: int
    analysis_confidence: float  # 0-1
    def requires_user_confirmation(self) -> bool: ...
    def get_primary_lighting_params(self) -> LightingParams: ...
```

From backends/claude.py (Claude backend interface):
```python
class ClaudeBackend:
    async def generate(self, prompt: str, images: list[dict] = None) -> str: ...
    # images = [{"path": str, "base64": str}] — passed as message content
```
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: RED — Write failing tests for VideoReferenceAnalyzer</name>
  <files>TestProject/Plugins/NYRA/Source/NyraHost/tests/test_video_reference_analyzer.py</files>
  <behavior>
    - Test 1: FFmpegKeyframeExtractor.extract_keyframes() returns a list of keyframe file paths for a valid video file
    - Test 2: FFmpegKeyframeExtractor.extract_keyframes() raises FileNotFoundError for a non-existent video path
    - Test 3: VideoReferenceAnalyzer.analyze() returns VideoReferenceParams with camera_move_type set for a static clip
    - Test 4: VideoReferenceAnalyzer.analyze() returns VideoReferenceParams with requires_user_confirmation=True for low-confidence analysis
    - Test 5: VideoReferenceAnalyzer._cleanup() deletes the video file from /tmp after analysis
    - Test 6: VideoReferenceAnalyzer._cleanup() deletes keyframes from /tmp after analysis
    - Test 7: FFmpegKeyframeExtractor._detect_scene_cuts() uses ffmpeg scene detection with threshold 0.3
    - Test 8: VideoReferenceAnalyzer rejects clips longer than 10 seconds
    - Test 9: VideoReferenceAnalyzer handles YouTube URL via yt-dlp download
    - Test 10: VideoReferenceAnalyzer handles local mp4 attachment directly
  </behavior>
  <action>
Create `tests/test_video_reference_analyzer.py` with the TDD RED test cases.

**Key behaviors to test:**

```python
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

        # Create a mock video file (just a temp file for path testing)
        video_path = tmp_path / "test_video.mp4"
        video_path.write_bytes(b"fake_video_data")  # Not a real video, but exists

        extractor = FFmpegKeyframeExtractor(ffmpeg_path="ffmpeg")
        # We mock the subprocess to simulate ffmpeg output
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="frame=001\nframe=002\nframe=003\n",
                stderr="",
            )
            with patch("shutil.copy") as mock_copy:
                def copy_side(src, dst):
                    Path(dst).write_bytes(b"fake_frame")
                mock_copy.side_effect = copy_side

                # Create fake keyframe output files
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
            # Verify the ffmpeg command includes gt(scene,0.3)
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

        with patch.object(analyzer, "_analyze_with_claude", new_callable=AsyncMock,
                          return_value=mock_claude_response):
            with patch.object(analyzer, "_extract_keyframes", return_value=["/tmp/kf1.jpg", "/tmp/kf2.jpg"]):
                with patch.object(analyzer, "_cleanup"):
                    params = analyzer.analyze(
                        source="https://youtube.com/watch?v=test",
                        source_type="youtube_url",
                    )
                    assert isinstance(params, VideoReferenceParams)
                    assert params.camera_move_type.value == "static"
                    assert params.requires_user_confirmation() is False

    def test_analyze_requires_confirmation_for_low_confidence(self):
        """analyze() sets requires_user_confirmation=True when confidence < 0.7."""
        from nyrahost.tools.video_reference_analyzer import VideoReferenceAnalyzer
        from nyrahost.tools.video_llm_parser import CameraMoveType

        analyzer = VideoReferenceAnalyzer(claude_backend=MagicMock())

        mock_claude_response = {
            "camera_move_type": "unknown",
            "camera_move_intensity": "unknown",
            "camera_move_confidence": 0.4,  # below 0.7 threshold
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

        with patch.object(analyzer, "_analyze_with_claude", new_callable=AsyncMock,
                          return_value=mock_claude_response):
            with patch.object(analyzer, "_extract_keyframes", return_value=["/tmp/kf1.jpg"]):
                with patch.object(analyzer, "_cleanup"):
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

        keyframe_paths = [
            str(tmp_path / "kf_001.jpg"),
            str(tmp_path / "kf_002.jpg"),
        ]
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

        with patch.object(analyzer, "_download_youtube", new_callable=AsyncMock,
                          return_value="/tmp/downloaded_video.mp4"):
            with patch.object(analyzer, "_get_video_duration", return_value=5.0):
                with patch.object(analyzer, "_extract_keyframes", return_value=["/tmp/kf1.jpg"]):
                    with patch.object(analyzer, "_analyze_with_claude", new_callable=AsyncMock,
                                      return_value={"camera_move_type": "static", "camera_move_intensity": "slow", "camera_move_confidence": 0.9, "subject_position": [0.5, 0.5], "framing": "medium", "rule_of_thirds": True, "headroom": "normal", "lighting_mood_tags": ["neutral"], "primary_color": [1,1,1], "primary_temperature_k": 5500, "fill_ratio": 0.5, "environment_type": "indoor", "time_of_day": "unknown", "weather": "unknown", "geometry_categories": [], "clip_duration_seconds": 5.0, "keyframe_count": 8, "shot_blocks": [], "analysis_confidence": 0.9}):
                        with patch.object(analyzer, "_cleanup"):
                            analyzer.analyze(
                                source="https://youtube.com/watch?v=test123",
                                source_type="youtube_url",
                            )
                            analyzer._download_youtube.assert_called_once()

    def test_handles_local_mp4_directly(self):
        """analyze() handles local mp4 files without yt-dlp."""
        from nyrahost.tools.video_reference_analyzer import VideoReferenceAnalyzer

        analyzer = VideoReferenceAnalyzer(claude_backend=MagicMock())

        with patch.object(analyzer, "_get_video_duration", return_value=5.0):
            with patch.object(analyzer, "_extract_keyframes", return_value=["/tmp/kf1.jpg"]):
                with patch.object(analyzer, "_analyze_with_claude", new_callable=AsyncMock,
                                  return_value={"camera_move_type": "dolly", "camera_move_intensity": "slow", "camera_move_confidence": 0.9, "subject_position": [0.5, 0.5], "framing": "medium", "rule_of_thirds": True, "headroom": "normal", "lighting_mood_tags": ["warm"], "primary_color": [0.9,0.6,0.3], "primary_temperature_k": 3500, "fill_ratio": 0.3, "environment_type": "outdoor", "time_of_day": "golden_hour", "weather": "clear", "geometry_categories": ["figure"], "clip_duration_seconds": 5.0, "keyframe_count": 8, "shot_blocks": [], "analysis_confidence": 0.9}):
                    with patch.object(analyzer, "_cleanup"):
                        with patch.object(analyzer, "_download_youtube",
                                          new_callable=AsyncMock) as mock_dl:
                            analyzer.analyze(
                                source="/Users/test/my_clip.mp4",
                                source_type="file",
                            )
                            mock_dl.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-q"])
```
</action>
  <verify>
    <automated>cd "/Users/aasish/CLAUDE PROJECTS/UEPLUG/UEPLUGIN/TestProject/Plugins/NYRA/Source/NyraHost" && python -m pytest tests/test_video_reference_analyzer.py -x -q 2>&1 | head -30</automated>
  </verify>
  <done>Tests written — expect 10+ failures until VideoReferenceAnalyzer and FFmpegKeyframeExtractor are implemented (RED phase)</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: GREEN — Implement FFmpegKeyframeExtractor and VideoReferenceAnalyzer</name>
  <files>TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/ffmpeg_extractor.py, TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/video_reference_analyzer.py</files>
  <behavior>
    - FFmpegKeyframeExtractor.extract_keyframes() returns list of keyframe paths, raises FileNotFoundError for invalid input
    - FFmpegKeyframeExtractor uses ffmpeg scene-cut detection with gt(scene,0.3) threshold
    - VideoReferenceAnalyzer.analyze() returns VideoReferenceParams, rejects clips >10s
    - VideoReferenceAnalyzer handles YouTube URL (yt-dlp download) and local mp4 (direct)
    - VideoReferenceAnalyzer._cleanup() deletes video + keyframes from /tmp
  </behavior>
  <action>
Implement the two source files to make the tests pass.

**ffmpeg_extractor.py:**

```python
"""nyrahost.tools.ffmpeg_extractor — FFmpeg keyframe extraction for video analysis.

Phase 7 Wave 1: Extracts scene-cut keyframes from video files using ffmpeg.
Used by VideoReferenceAnalyzer to prepare frames for Claude Opus vision analysis.
"""
from __future__ import annotations

import os
import shutil
import structlog
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

log = structlog.get_logger("nyrahost.tools.ffmpeg_extractor")

__all__ = ["FFmpegKeyframeExtractor"]


class FFmpegKeyframeExtractor:
    """Extracts keyframes from video using ffmpeg scene-cut detection.

    Uses ffmpeg scene-change detection (`select='gt(scene,0.3)'`) to find
    visually distinct frames, then extracts them as JPEG files.

    Ephemeral output: all files written to /tmp/nyra_keyframes/ and cleaned
    up by VideoReferenceAnalyzer._cleanup() after analysis.
    """

    def __init__(self, ffmpeg_path: Optional[str] = None):
        """Initialize with path to ffmpeg binary.

        Args:
            ffmpeg_path: Path to ffmpeg executable. If None, resolves from
                Binaries/ThirdParty/ffmpeg/ or system PATH.
        """
        self.ffmpeg_path = ffmpeg_path or self._resolve_ffmpeg_path()

    def _resolve_ffmpeg_path(self) -> str:
        """Resolve ffmpeg path: plugin bundled -> system PATH."""
        # Try bundled path first (Phase 5 pattern)
        bundled = Path(__file__).parent.parent.parent.parent.parent.parent / \
                  "Binaries" / "ThirdParty" / "ffmpeg" / "ffmpeg.exe"
        if bundled.exists():
            log.info("ffmpeg_resolved", path=str(bundled), source="bundled")
            return str(bundled)

        # Fall back to system PATH
        log.info("ffmpeg_resolved", path="ffmpeg", source="system_path")
        return "ffmpeg"

    def _run_ffmpeg_scene_detect(
        self, video_path: str, threshold: float = 0.3
    ) -> list[float]:
        """Run ffmpeg scene detection and return scene-change timestamps.

        Args:
            video_path: Path to input video file
            threshold: Scene-change threshold (0.0-1.0), default 0.3 per ROADMAP SC#3

        Returns:
            List of timestamps (seconds) where scene changes were detected
        """
        cmd = [
            self.ffmpeg_path,
            "-i", video_path,
            "-vf", f"select='gt(scene,{threshold})',showinfo",
            "-f", "null",
            "-",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        timestamps = []
        for line in result.stderr.split("\n"):
            if "showinfo" in line and "pts_time:" in line:
                try:
                    ts_str = line.split("pts_time:")[1].split()[0]
                    timestamps.append(float(ts_str))
                except (IndexError, ValueError):
                    pass

        log.info("scene_detection_complete", video=video_path,
                 scene_changes=len(timestamps), threshold=threshold)
        return timestamps

    def _run_ffmpeg_keyframe_extract(
        self, video_path: str, timestamps: list[float], output_dir: str
    ) -> list[str]:
        """Extract specific frames at given timestamps.

        Args:
            video_path: Path to input video file
            timestamps: List of timestamps in seconds
            output_dir: Directory to write keyframe files

        Returns:
            List of absolute paths to extracted keyframe files
        """
        keyframe_paths = []
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)

        for i, ts in enumerate(timestamps):
            output_path = output_dir_path / f"nyra_kf_{i+1:04d}.jpg"
            cmd = [
                self.ffmpeg_path,
                "-ss", str(ts),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",  # Quality: 2 = high quality
                "-y",  # Overwrite
                str(output_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0 and output_path.exists():
                keyframe_paths.append(str(output_path))
                log.info("keyframe_extracted", index=i+1, timestamp=ts,
                         output=str(output_path))
            else:
                log.warning("keyframe_extract_failed", index=i+1, timestamp=ts,
                            stderr=result.stderr[:200])

        return keyframe_paths

    def extract_keyframes(
        self,
        video_path: str,
        max_keyframes: int = 16,
        output_dir: Optional[str] = None,
    ) -> list[str]:
        """Extract up to max_keyframes from a video file.

        Uses ffmpeg scene-cut detection to find visually distinct frames,
        then extracts them as high-quality JPEGs.

        Args:
            video_path: Path to input video file (mp4, mkv, webm, etc.)
            max_keyframes: Maximum number of keyframes to extract (default 16)
            output_dir: Directory for keyframe output. If None, uses /tmp/nyra_keyframes/

        Returns:
            List of absolute paths to extracted keyframe JPEG files

        Raises:
            FileNotFoundError: If video_path does not exist
            RuntimeError: If ffmpeg extraction fails
        """
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if output_dir is None:
            output_dir = "/tmp/nyra_keyframes"

        # 1. Run scene detection
        timestamps = self._run_ffmpeg_scene_detect(video_path, threshold=0.3)

        # 2. If not enough scene changes, supplement with evenly-spaced frames
        if len(timestamps) < 3:
            log.info("insufficient_scene_changes", detected=len(timestamps),
                     supplementing=True)
            # Fall back to uniform sampling at ~2s intervals
            duration_cmd = [
                self.ffmpeg_path,
                "-i", video_path,
                "-f", "null",
                "-",
            ]
            # Get duration via ffprobe
            duration = self._get_video_duration(video_path)
            interval = max(2.0, duration / max_keyframes)
            timestamps = [i * interval for i in range(max_keyframes)]

        # 3. Limit to max_keyframes
        timestamps = timestamps[:max_keyframes]

        # 4. Extract frames
        keyframe_paths = self._run_ffmpeg_keyframe_extract(
            video_path, timestamps, output_dir
        )

        log.info("keyframe_extraction_complete",
                 video=video_path,
                 keyframes_extracted=len(keyframe_paths),
                 max_requested=max_keyframes)

        return keyframe_paths

    def _get_video_duration(self, video_path: str) -> float:
        """Get video duration in seconds using ffprobe."""
        cmd = [
            self.ffmpeg_path.replace("ffmpeg", "ffprobe"),
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ]
        # Try ffprobe first, fall back to ffmpeg
        probe_path = self.ffmpeg_path.replace("ffmpeg", "ffprobe")
        if Path(probe_path).exists():
            result = subprocess.run([probe_path] + cmd[1:], capture_output=True, text=True, timeout=30)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        try:
            return float(result.stdout.strip())
        except (ValueError, subprocess.CalledProcessError):
            return 10.0  # Default fallback

    def cleanup(self, output_dir: str) -> None:
        """Delete all keyframe files in the output directory.

        Called by VideoReferenceAnalyzer after analysis is complete.
        """
        output_dir_path = Path(output_dir)
        if output_dir_path.exists():
            shutil.rmtree(output_dir_path)
            log.info("keyframe_cleanup_complete", output_dir=output_dir)
