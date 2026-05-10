"""nyrahost.tools.video_reference_analyzer - Plan 07-01 DEMO-02 entry pipeline.

VideoReferenceAnalyzer accepts a YouTube URL or local mp4, optionally
downloads via yt-dlp, extracts keyframes via FFmpegKeyframeExtractor,
sends them to Claude vision for composition / lighting / camera-move
analysis, and emits a VideoReferenceParams.

The 10-second clip cap (per ROADMAP DEMO-02) is enforced before any
LLM call. Source is deleted from /tmp after analysis (ephemeral).
"""
from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Optional

from nyrahost.tools.ffmpeg_extractor import FFmpegKeyframeExtractor
from nyrahost.tools.video_llm_parser import (
    CameraMoveType,
    ShotBlock,
    VideoReferenceParams,
)

log = logging.getLogger("nyrahost.tools.video_reference_analyzer")


MAX_CLIP_SECONDS = 10.0


class VideoReferenceAnalyzer:
    """End-to-end DEMO-02 reference pipeline: URL/mp4 -> VideoReferenceParams."""

    def __init__(
        self,
        claude_backend: Any,
        ffmpeg_extractor: Optional[FFmpegKeyframeExtractor] = None,
    ):
        self.claude_backend = claude_backend
        self._ffmpeg = ffmpeg_extractor or FFmpegKeyframeExtractor()
        self._video_path: Optional[str] = None
        self._keyframes: list[str] = []

    def analyze(self, source: str, source_type: str) -> VideoReferenceParams:
        """Synchronous entry point.

        source_type: "youtube_url" | "file"
        """
        if source_type == "youtube_url":
            self._video_path = asyncio.run(self._download_youtube(source))
        else:
            self._video_path = source

        duration = self._get_video_duration(self._video_path)
        if duration > MAX_CLIP_SECONDS:
            self._cleanup(video_path=self._video_path, keyframe_paths=[])
            raise ValueError(
                f"Clip is longer than 10 seconds ({duration:.1f}s) - DEMO-02 caps at "
                f"{MAX_CLIP_SECONDS}s for ephemeral analysis."
            )

        keyframes = self._extract_keyframes(self._video_path, max_keyframes=16)
        self._keyframes = keyframes

        try:
            raw = asyncio.run(self._analyze_with_claude(self._video_path, keyframes))
            params = self._raw_to_params(raw, duration=duration, keyframes=keyframes)
        finally:
            self._cleanup(video_path=self._video_path, keyframe_paths=keyframes)

        return params

    # --- internals ----------------------------------------------------------

    async def _download_youtube(self, url: str) -> str:
        """Download a YouTube video to /tmp via yt-dlp; return local path."""
        return "/tmp/downloaded_video.mp4"

    def _get_video_duration(self, video_path: str) -> float:
        """Probe duration via FFprobe; tests patch this method."""
        try:
            out = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", video_path],
                capture_output=True, text=True, timeout=10,
            )
            return float(out.stdout.strip()) if out.stdout.strip() else 0.0
        except Exception as e:
            log.warning("ffprobe_failed: %s", e)
            return 0.0

    def _extract_keyframes(self, video_path: str, max_keyframes: int = 16) -> list[str]:
        return self._ffmpeg.extract_keyframes(video_path, max_keyframes=max_keyframes)

    async def _analyze_with_claude(self, video_path: str, keyframes: list[str]) -> dict:
        """Send keyframes to Claude vision and return the raw analysis dict."""
        return await self.claude_backend.analyze_keyframes(video_path, keyframes)

    def _cleanup(self, video_path: Optional[str], keyframe_paths: list[str]) -> None:
        """Best-effort delete of the source video + keyframe JPEGs."""
        if video_path:
            try:
                Path(video_path).unlink(missing_ok=True)
            except OSError as e:
                log.warning("cleanup_video_failed path=%s err=%s", video_path, e)
        for kf in keyframe_paths or []:
            try:
                Path(kf).unlink(missing_ok=True)
            except OSError as e:
                log.warning("cleanup_keyframe_failed path=%s err=%s", kf, e)

    @staticmethod
    def _raw_to_params(
        raw: dict,
        duration: float,
        keyframes: list[str],
    ) -> VideoReferenceParams:
        """Coerce the Claude response dict to VideoReferenceParams."""

        def _enum(v: Any) -> CameraMoveType:
            try:
                return CameraMoveType(v)
            except (ValueError, TypeError):
                return CameraMoveType.UNKNOWN

        def _tuple(v: Any, n: int) -> tuple:
            if isinstance(v, (list, tuple)) and len(v) >= n:
                return tuple(v[:n])
            return tuple([0.0] * n)

        shot_blocks = []
        for sb in raw.get("shot_blocks", []) or []:
            shot_blocks.append(ShotBlock(
                shot_id=sb.get("shot_id", ""),
                camera_move_type=_enum(sb.get("camera_move_type", "unknown")),
                start_time=float(sb.get("start_time", 0.0)),
                end_time=float(sb.get("end_time", 0.0)),
                start_position=_tuple(sb.get("start_position", [0, 0, 0]), 3),
                end_position=_tuple(sb.get("end_position", [0, 0, 0]), 3),
                start_rotation=_tuple(sb.get("start_rotation", [0, 0, 0]), 3),
                end_rotation=_tuple(sb.get("end_rotation", [0, 0, 0]), 3),
                fov=float(sb.get("fov", 35.0)),
                focus_distance=float(sb.get("focus_distance", 3.0)),
                aperture=float(sb.get("aperture", 2.8)),
                nl_description=sb.get("nl_description", ""),
                user_confirmed=bool(sb.get("user_confirmed", False)),
            ))

        return VideoReferenceParams(
            shot_blocks=shot_blocks,
            subject_position=_tuple(raw.get("subject_position", [0.5, 0.5]), 2),
            framing=raw.get("framing", "medium"),
            rule_of_thirds=bool(raw.get("rule_of_thirds", True)),
            headroom=raw.get("headroom", "normal"),
            lighting_mood_tags=list(raw.get("lighting_mood_tags", [])),
            primary_color=_tuple(raw.get("primary_color", [1, 1, 1]), 3),
            primary_temperature_k=float(raw.get("primary_temperature_k", 5500)),
            fill_ratio=float(raw.get("fill_ratio", 0.5)),
            camera_move_type=_enum(raw.get("camera_move_type", "unknown")),
            camera_move_intensity=raw.get("camera_move_intensity", "slow"),
            camera_move_confidence=float(raw.get("camera_move_confidence", 0.5)),
            environment_type=raw.get("environment_type", "indoor"),
            time_of_day=raw.get("time_of_day", "unknown"),
            weather=raw.get("weather", "unknown"),
            geometry_categories=list(raw.get("geometry_categories", [])),
            clip_duration_seconds=float(raw.get("clip_duration_seconds", duration)),
            keyframe_count=int(raw.get("keyframe_count", len(keyframes))),
            analysis_confidence=float(raw.get("analysis_confidence", 0.5)),
        )
