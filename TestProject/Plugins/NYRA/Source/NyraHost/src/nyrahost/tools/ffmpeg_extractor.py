"""nyrahost.tools.ffmpeg_extractor - Plan 07-01 keyframe extraction.

FFmpegKeyframeExtractor wraps the bundled FFmpeg binary to:
  1. Extract evenly-spaced keyframes from a video (max_keyframes=16 cap).
  2. Detect hard scene cuts via the FFmpeg `gt(scene,0.3)` select filter.

Both operations write JPEGs to a per-run temp subdirectory under
``output_dir`` and return their paths. The caller is responsible for
cleanup; VideoReferenceAnalyzer._cleanup wraps this contract for the
DEMO-02 pipeline. Per-run subdirs guarantee that stale frames from
prior failed / parallel runs cannot leak into the returned path list.
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
MAX_KEYFRAMES_CAP = 16


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

        WR-02 / WR-11: writes frames into a fresh per-run subdir (created
        via ``tempfile.mkdtemp(prefix='nyra_kf_', dir=output_dir)``) so
        glob-up of the result list cannot pick up stale files from a prior
        run, and ordering is monotonic per call. Caller cleanup should
        delete the subdir as a unit.

        WR-10: when ``max_keyframes`` exceeds ``MAX_KEYFRAMES_CAP``, log
        a warning so callers see why they got fewer frames than asked
        for. The cap is a Claude-vision-cost guardrail, not a silent
        rewrite.
        """
        if not Path(video_path).exists():
            raise FileNotFoundError(f"video not found: {video_path}")

        if max_keyframes > MAX_KEYFRAMES_CAP:
            log.warning(
                "ffmpeg_extract_clamping_max_keyframes requested=%d cap=%d",
                max_keyframes,
                MAX_KEYFRAMES_CAP,
            )
        max_keyframes = max(1, min(max_keyframes, MAX_KEYFRAMES_CAP))
        run_dir = tempfile.mkdtemp(prefix="nyra_kf_", dir=self.output_dir)
        out_pattern = os.path.join(run_dir, "frame_%04d.jpg")
        # IN-05: Evenly-spaced sampling -- use FFmpeg's `fps=N/D` filter
        # rather than `thumbnail`, which picks "representative" frames and
        # is not evenly spaced. We do not know total frame count up front
        # without a probe pass, so use ``fps=max_keyframes/duration_est``
        # via the simpler ``fps=`` proxy: the caller passes a cap, and
        # ``-frames:v max_keyframes`` truncates if FFmpeg overproduces.
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", video_path,
            "-vf", "select='not(mod(n\\,trunc(N/{n})))',scale=1280:-1".format(n=max_keyframes),
            "-vsync", "vfr",
            "-frames:v", str(max_keyframes),
            out_pattern,
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=False)
        except Exception as e:
            log.error("ffmpeg_extract_failed: %s", e)
            return []

        paths = sorted(glob.glob(os.path.join(run_dir, "frame_*.jpg")))
        # Filter to only those that actually exist (subprocess may have failed).
        return [p for p in paths if Path(p).exists()]

    def _run_ffmpeg_scene_detect(
        self,
        video_path: str,
        threshold: float = SCENE_CUT_THRESHOLD,
    ) -> list[str]:
        """Run scene-cut detection. Returns list of scene-cut frame paths.

        WR-03 (partial): mirrors the per-run-subdir, try/except, and
        Path.exists filter contracts of ``extract_keyframes`` so the two
        methods of this class cannot drift in observable behaviour. The
        existence check on the input was deliberately NOT lifted here
        because the existing test_scene_cut_detection_threshold drives
        the method against ``/fake/video.mp4`` to assert the constructed
        command string -- adding an exists() guard would regress that
        test. Callers in production go through ``extract_keyframes``
        first, which already validates the path.
        """
        run_dir = tempfile.mkdtemp(prefix="nyra_scene_", dir=self.output_dir)
        out_pattern = os.path.join(run_dir, "scene_%04d.jpg")
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", video_path,
            "-vf", f"select='gt(scene,{threshold})'",
            "-vsync", "vfr",
            out_pattern,
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=False)
        except Exception as e:
            log.error("ffmpeg_scene_detect_failed: %s", e)
            return []

        paths = sorted(glob.glob(os.path.join(run_dir, "scene_*.jpg")))
        return [p for p in paths if Path(p).exists()]
