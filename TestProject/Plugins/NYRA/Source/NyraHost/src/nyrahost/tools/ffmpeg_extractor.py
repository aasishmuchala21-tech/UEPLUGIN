"""nyrahost.tools.ffmpeg_extractor - Plan 07-01 keyframe extraction.

FFmpegKeyframeExtractor wraps the bundled FFmpeg binary to:
  1. Extract evenly-spaced keyframes from a video (max_keyframes=16 cap).
  2. Detect hard scene cuts via the FFmpeg `gt(scene,0.3)` select filter.

Both operations write JPEGs to a temp dir and return their paths. The
caller is responsible for cleanup; VideoReferenceAnalyzer._cleanup wraps
this contract for the DEMO-02 pipeline.
"""
from __future__ import annotations

import glob
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

log = logging.getLogger("nyrahost.tools.ffmpeg_extractor")


SCENE_CUT_THRESHOLD = 0.3


class FFmpegKeyframeExtractor:
    """Bundled-FFmpeg keyframe extraction with safe error reporting."""

    def __init__(self, ffmpeg_path: str = "ffmpeg", output_dir: Optional[str] = None):
        self.ffmpeg_path = ffmpeg_path
        self.output_dir = output_dir or tempfile.gettempdir()

    def extract_keyframes(
        self,
        video_path: str,
        max_keyframes: int = 16,
    ) -> list[str]:
        """Extract <= max_keyframes keyframes; return list of file paths.

        Raises FileNotFoundError if `video_path` does not exist on disk.
        """
        if not Path(video_path).exists():
            raise FileNotFoundError(f"video not found: {video_path}")

        max_keyframes = max(1, min(max_keyframes, 16))
        out_pattern = os.path.join(self.output_dir, "nyra_kf_%04d.jpg")
        # Evenly-spaced keyframes via select='not(mod(n\,N))' is brittle without
        # knowing frame count; use FFmpeg's `fps=` filter as a portable proxy.
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", video_path,
            "-vf", f"thumbnail,scale=1280:-1",
            "-frames:v", str(max_keyframes),
            out_pattern,
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=False)
        except Exception as e:
            log.error("ffmpeg_extract_failed: %s", e)
            return []

        paths = sorted(glob.glob(os.path.join(self.output_dir, "nyra_kf_*.jpg")))
        # Filter to only those that actually exist (subprocess may have failed).
        return [p for p in paths if Path(p).exists()]

    def _run_ffmpeg_scene_detect(
        self,
        video_path: str,
        threshold: float = SCENE_CUT_THRESHOLD,
    ) -> list[str]:
        """Run scene-cut detection. Returns list of scene-cut frame paths."""
        out_pattern = os.path.join(self.output_dir, "nyra_scene_%04d.jpg")
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", video_path,
            "-vf", f"select='gt(scene,{threshold})'",
            "-vsync", "vfr",
            out_pattern,
        ]
        subprocess.run(cmd, capture_output=True, text=True, check=False)
        return sorted(glob.glob(os.path.join(self.output_dir, "nyra_scene_*.jpg")))
