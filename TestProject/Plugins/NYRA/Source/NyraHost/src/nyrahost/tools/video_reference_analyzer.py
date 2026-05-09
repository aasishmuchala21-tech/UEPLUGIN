"""nyrahost.tools.video_reference_analyzer — Video Reference Analyzer for DEMO-02.

Phase 7 Wave 1: Analyzes reference video (YouTube URL or local mp4) to produce
VideoReferenceParams for Sequencer scene assembly.

Pipeline:
  1. YouTube URL -> yt-dlp download to /tmp
  2. ffmpeg scene-cut detection + keyframe extraction (≤16 frames)
  3. Send keyframes to Claude Opus vision with analysis prompt
  4. Parse response into VideoReferenceParams
  5. Delete video file from /tmp (ephemeral processing per SC#4)

Per ROADMAP SC#3: scene-cut detection uses ffmpeg gt(scene,0.3) + semantic lighting
extraction (Claude vision, not RGB-only analysis).
Per ROADMAP SC#4: ephemeral processing — video deleted within 5 minutes of paste.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import structlog
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

from nyrahost.tools.base import NyraTool, NyraToolResult
from nyrahost.tools.ffmpeg_extractor import FFmpegKeyframeExtractor
from nyrahost.tools.video_llm_parser import (
    CameraMoveType,
    LightingParams,
    ShotBlock,
    VideoReferenceParams,
)

log = structlog.get_logger("nyrahost.tools.video_reference_analyzer")

__all__ = ["VideoReferenceAnalyzer", "VideoAnalysisTool"]

# Maximum clip duration in seconds (ROADMAP SC#1: ≤10s single-shot)
MAX_CLIP_DURATION = 10.0

# System prompt for Claude Opus vision analysis
CLAUDE_VIDEO_ANALYSIS_SYSTEM = """You are NYRA's video reference analysis engine. Given a set of keyframes
extracted from a reference video clip, analyze the cinematography and produce a
structured JSON description of the scene.

Return ONLY valid JSON. No markdown, no explanation, no preamble. The JSON schema:

{
  "camera_move_type": "static"|"pan"|"tilt"|"dolly"|"truck"|"crane"|"zoom"|"handheld"|"unknown",
  "camera_move_intensity": "slow"|"medium"|"fast",
  "camera_move_confidence": 0.0-1.0,
  "subject_position": [normalized_x_0_to_1, normalized_y_0_to_1],
  "framing": "extreme_close_up"|"close_up"|"medium"|"full"|"wide"|"establishing",
  "rule_of_thirds": true|false,
  "headroom": "tight"|"normal"|"loose",
  "lighting_mood_tags": ["warm","cool","high-contrast","soft","harsh",...],
  "primary_color": [r_0_to_1, g_0_to_1, b_0_to_1],
  "primary_temperature_k": 1000-20000,
  "fill_ratio": 0.0-1.0,
  "environment_type": "indoor"|"outdoor"|"studio"|"VFX_plate",
  "time_of_day": "dawn"|"morning"|"midday"|"golden_hour"|"dusk"|"night"|"unknown",
  "weather": "clear"|"overcast"|"rain"|"fog"|"smoke"|"unknown",
  "geometry_categories": ["hero_figure","street","building","interior","sky",...],
  "clip_duration_seconds": float,
  "keyframe_count": int,
  "shot_blocks": [{
    "shot_id": "shot_01",
    "camera_move_type": "static"|"dolly"|"pan"|"tilt"|"truck"|"unknown",
    "start_time": float_seconds,
    "end_time": float_seconds,
    "start_position": [x_cm, y_cm, z_cm],
    "end_position": [x_cm, y_cm, z_cm],
    "start_rotation": [pitch_deg, yaw_deg, roll_deg],
    "end_rotation": [pitch_deg, yaw_deg, roll_deg],
    "fov": float_degrees_35mm_equivalent,
    "focus_distance": float_meters,
    "aperture": float_fstop,
    "nl_description": "natural language description of shot",
    "user_confirmed": false
  }],
  "analysis_confidence": 0.0-1.0
}

Rules:
- camera_move_type: "dolly" = camera moves toward/away from subject (Z axis, forward/back).
  "truck" = camera moves laterally parallel to the frame (X or Y axis, left/right).
  "pan" = horizontal rotation around a fixed point (no camera position change).
  "tilt" = vertical rotation around a fixed point.
- lighting analysis must consider SEMANTIC content (window light, lamps, sun angle,
  sky color) not just RGB values — LUTs and color grading can mislead RGB analysis.
- geometry_categories: describe object TYPES present, not specific assets (e.g. "wet_asphalt"
  not "/Game/Props/Street/Asphalt_Sunken_Var2_C;1")
- clip_duration_seconds: duration of the full reference clip in seconds
- keyframe_count: how many keyframes were sent for analysis
- analysis_confidence: your overall confidence in this analysis (0.0-1.0)
"""


class VideoReferenceAnalyzer:
    """Analyzes reference video (YouTube URL or local mp4) to VideoReferenceParams.

    Ephemeral processing per ROADMAP SC#4:
    - Video file downloaded to /tmp
    - Keyframes extracted to /tmp/nyra_keyframes/
    - After analysis, video file is deleted within 5 minutes
    - Keyframes are kept for audit trail (not full video, less copyright risk)

    SC#1: Clips must be ≤10 seconds.
    SC#3: Uses ffmpeg scene-cut detection + Claude Opus vision (not RGB analysis).
    """

    def __init__(self, claude_backend: Any = None, ffmpeg_path: Optional[str] = None):
        """Initialize the analyzer.

        Args:
            claude_backend: Backend router supporting vision. Must implement:
                async def generate(prompt: str, images: list[dict]) -> str
                where images = [{"path": str}]
            ffmpeg_path: Path to ffmpeg binary (default: bundled or system PATH)
        """
        self.claude_backend = claude_backend
        self.ffmpeg_extractor = FFmpegKeyframeExtractor(ffmpeg_path=ffmpeg_path)
        self._temp_dir: Optional[str] = None
        self._video_path: Optional[str] = None
        self._keyframe_paths: list[str] = []
        self._analysis_start_time: Optional[float] = None

    async def analyze(
        self,
        source: str,
        source_type: str = "file",
    ) -> VideoReferenceParams:
        """Analyze a reference video and return VideoReferenceParams.

        Args:
            source: Either a YouTube URL or local file path
            source_type: "youtube_url" or "file"

        Returns:
            VideoReferenceParams dataclass ready for Sequencer authoring

        Raises:
            ValueError: If clip duration > 10 seconds or source not found
            RuntimeError: If video analysis fails
        """
        self._analysis_start_time = time.time()

        # Step 1: Download or locate the video file
        if source_type == "youtube_url":
            self._video_path = await self._download_youtube(source)
            log.info("youtube_downloaded", url=source, path=self._video_path)
        else:
            self._video_path = source
            if not Path(self._video_path).exists():
                raise FileNotFoundError(f"Video file not found: {self._video_path}")

        # Step 2: Verify duration is ≤10 seconds
        duration = self._get_video_duration(self._video_path)
        if duration > MAX_CLIP_DURATION:
            raise ValueError(
                f"[-32035] Clip duration {duration:.1f}s exceeds maximum {MAX_CLIP_DURATION}s. "
                f"DEMO-02 supports single-shot ≤10s clips. Please provide a shorter clip."
            )

        # Step 3: Create temp directory for keyframes
        self._temp_dir = tempfile.mkdtemp(prefix="nyra_keyframes_")

        # Step 4: Extract keyframes using ffmpeg
        self._keyframe_paths = self.ffmpeg_extractor.extract_keyframes(
            self._video_path,
            max_keyframes=16,
            output_dir=self._temp_dir,
        )

        if not self._keyframe_paths:
            raise RuntimeError(
                f"[-32036] Failed to extract any keyframes from {self._video_path}. "
                f"Ensure ffmpeg is installed and the video is valid."
            )

        log.info("keyframes_extracted",
                video=self._video_path,
                keyframe_count=len(self._keyframe_paths),
                duration_s=duration)

        # Step 5: Analyze with Claude Opus vision
        analysis_result = await self._analyze_with_claude()

        # Step 6: Parse into VideoReferenceParams
        params = self._parse_claude_response(analysis_result, duration)

        # Step 7: Schedule ephemeral cleanup (video file only, keyframes kept for audit)
        self._schedule_cleanup()

        return params

    async def _download_youtube(self, url: str) -> str:
        """Download a YouTube video using yt-dlp.

        Uses Phase 5 bundled yt-dlp path or system PATH.
        Downloads best format ≤720p to keep file size manageable.

        Args:
            url: YouTube video URL

        Returns:
            Absolute path to downloaded video file in /tmp

        Raises:
            RuntimeError: If yt-dlp download fails
        """
        yt_dlp_path = self._resolve_yt_dlp_path()
        output_template = "/tmp/nyra_video_%(id)s.%(ext)s"

        cmd = [
            yt_dlp_path,
            "-f", "best[height<=720]/best",  # ≤720p to keep size reasonable
            "--no-playlist",
            "-o", output_template,
            "--no-warnings",
            url,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout for download
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"[-32037] yt-dlp download failed: {result.stderr[:500]}"
            )

        # yt-dlp outputs the filename to stdout
        downloaded_path = result.stdout.strip().split("\n")[-1]
        if not Path(downloaded_path).exists():
            # Try common patterns
            url_id = url.split("v=")[-1].split("&")[0] if "v=" in url else "video"
            fallback = f"/tmp/nyra_video_{url_id}.mp4"
            if Path(fallback).exists():
                downloaded_path = fallback
            else:
                raise RuntimeError(
                    f"[-32038] yt-dlp succeeded but output file not found at {downloaded_path}"
                )

        return downloaded_path

    def _resolve_yt_dlp_path(self) -> str:
        """Resolve yt-dlp path: plugin bundled -> system PATH."""
        bundled = Path(__file__).parent.parent.parent.parent.parent.parent / \
                  "Binaries" / "ThirdParty" / "yt-dlp" / "yt-dlp.exe"
        if bundled.exists():
            return str(bundled)
        return "yt-dlp"  # Fall back to system PATH

    def _get_video_duration(self, video_path: str) -> float:
        """Get video duration in seconds."""
        return self.ffmpeg_extractor._get_video_duration(video_path)

    async def _analyze_with_claude(self) -> dict[str, Any]:
        """Send keyframes to Claude Opus vision and get structured analysis.

        Sends all keyframes as images in one turn (Claude Opus 4.7 handles 20+
        images per turn gracefully per STACK.md).

        Args:
            None (uses self._keyframe_paths)

        Returns:
            Dict parsed from Claude's JSON response
        """
        if not self.claude_backend:
            raise RuntimeError(
                "[-32039] No claude_backend configured. "
                "VideoReferenceAnalyzer requires a Claude backend for vision analysis."
            )

        prompt = (
            "Analyze these keyframes from a reference video clip. "
            "Describe the cinematography, lighting, composition, camera movement, "
            "and scene content. Focus on what a UE scene would need to replicate this shot: "
            "camera placement, light setup, sky state, and environment type.\n\n"
            "Return ONLY valid JSON matching this schema."
        )

        images = [{"path": path} for path in self._keyframe_paths]

        try:
            response_text = await self.claude_backend.generate(prompt, images=images)
        except Exception as e:
            log.error("claude_vision_analysis_failed", error=str(e))
            raise RuntimeError(f"[-32040] Claude vision analysis failed: {e}")

        # Parse JSON from response
        # Claude may wrap JSON in markdown code blocks
        response_text = response_text.strip()
        if response_text.startswith("```"):
            # Strip markdown code fence
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            log.error("claude_json_parse_failed", response=response_text[:200], error=str(e))
            raise RuntimeError(f"[-32041] Failed to parse Claude response as JSON: {e}")

    def _parse_claude_response(
        self, response: dict[str, Any], duration: float
    ) -> VideoReferenceParams:
        """Parse Claude's response dict into VideoReferenceParams."""
        # Parse shot blocks
        shot_blocks = []
        for shot_data in response.get("shot_blocks", []):
            move_str = shot_data.get("camera_move_type", "unknown")
            try:
                move_type = CameraMoveType(move_str)
            except ValueError:
                move_type = CameraMoveType.UNKNOWN

            shot = ShotBlock(
                shot_id=shot_data.get("shot_id", "shot_01"),
                camera_move_type=move_type,
                start_time=float(shot_data.get("start_time", 0.0)),
                end_time=float(shot_data.get("end_time", duration)),
                start_position=tuple(shot_data.get("start_position", [0, 0, 100])),
                end_position=tuple(shot_data.get("end_position", [0, 0, 100])),
                start_rotation=tuple(shot_data.get("start_rotation", [0, 0, 0])),
                end_rotation=tuple(shot_data.get("end_rotation", [0, 0, 0])),
                fov=float(shot_data.get("fov", 35.0)),
                focus_distance=float(shot_data.get("focus_distance", 3.0)),
                aperture=float(shot_data.get("aperture", 2.8)),
                nl_description=shot_data.get("nl_description", ""),
                user_confirmed=shot_data.get("user_confirmed", False),
            )
            shot_blocks.append(shot)

        # Parse camera move type
        move_str = response.get("camera_move_type", "unknown")
        try:
            camera_move_type = CameraMoveType(move_str)
        except ValueError:
            camera_move_type = CameraMoveType.UNKNOWN

        params = VideoReferenceParams(
            shot_blocks=shot_blocks,
            subject_position=tuple(response.get("subject_position", [0.5, 0.5])),
            framing=response.get("framing", "medium"),
            rule_of_thirds=response.get("rule_of_thirds", False),
            headroom=response.get("headroom", "normal"),
            lighting_mood_tags=response.get("lighting_mood_tags", []),
            primary_color=tuple(response.get("primary_color", [1.0, 1.0, 1.0])),
            primary_temperature_k=float(response.get("primary_temperature_k", 5500)),
            fill_ratio=float(response.get("fill_ratio", 0.5)),
            camera_move_type=camera_move_type,
            camera_move_intensity=response.get("camera_move_intensity", "slow"),
            camera_move_confidence=float(response.get("camera_move_confidence", 0.7)),
            environment_type=response.get("environment_type", "unknown"),
            time_of_day=response.get("time_of_day", "unknown"),
            weather=response.get("weather", "unknown"),
            geometry_categories=response.get("geometry_categories", []),
            clip_duration_seconds=duration,
            keyframe_count=len(self._keyframe_paths),
            analysis_confidence=float(response.get("analysis_confidence", 0.7)),
        )

        if params.requires_user_confirmation():
            log.warning("video_analysis_requires_confirmation",
                       confidence=params.camera_move_confidence,
                       move_type=params.camera_move_type)

        return params

    def _schedule_cleanup(self) -> None:
        """Schedule ephemeral cleanup of the video file.

        Per ROADMAP SC#4: video file deleted within 5 minutes of paste.
        Keyframes are kept for audit trail (no full video = less copyright risk).

        Runs in background; logs completion.
        """
        if self._video_path and Path(self._video_path).exists():
            try:
                Path(self._video_path).unlink()
                log.info("ephemeral_video_deleted",
                        video=self._video_path,
                        elapsed_s=time.time() - self._analysis_start_time
                        if self._analysis_start_time else 0,
                        message="Video file deleted (keyframes retained for audit)")
            except OSError as e:
                log.warning("ephemeral_cleanup_failed", video=self._video_path, error=str(e))

    def _cleanup(self, video_path: Optional[str], keyframe_paths: list[str]) -> None:
        """Manual cleanup for testing.

        Args:
            video_path: Path to video file to delete
            keyframe_paths: List of keyframe paths to delete
        """
        if video_path:
            p = Path(video_path)
            if p.exists():
                p.unlink()
                log.info("cleanup_deleted_video", path=video_path)

        for kf in keyframe_paths:
            p = Path(kf)
            if p.exists():
                p.unlink()

        if self._temp_dir and Path(self._temp_dir).exists():
            shutil.rmtree(self._temp_dir)


class VideoAnalysisTool(NyraTool):
    """MCP tool wrapper around VideoReferenceAnalyzer.

    Provides: nyra_video_analyze
    User provides: YouTube URL or local mp4 path
    Returns: VideoReferenceParams JSON
    """
    name = "nyra_video_analyze"
    description = (
        "Analyze a reference video (YouTube URL or local mp4) and produce scene parameters "
        "for UE scene assembly. Extracts keyframes, analyzes cinematography with Claude Opus vision, "
        "returns composition, lighting, camera movement, and geometry categories. "
        "For clips ≤10s only. Video file is deleted after analysis (ephemeral processing)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "description": "YouTube URL or absolute path to local mp4 file",
            },
            "source_type": {
                "type": "string",
                "enum": ["youtube_url", "file"],
                "default": "file",
                "description": "Whether source is a YouTube URL or local file",
            },
        },
        "required": ["source"],
    }

    def __init__(self, claude_backend: Any = None):
        super().__init__()
        self.claude_backend = claude_backend

    def execute(self, params: dict) -> NyraToolResult:
        import asyncio

        source = params["source"]
        source_type = params.get("source_type", "file")

        analyzer = VideoReferenceAnalyzer(claude_backend=self.claude_backend)

        try:
            # Run the async analyze() in a sync context
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(
                analyzer.analyze(source=source, source_type=source_type)
            )
            loop.close()

            return NyraToolResult.ok({
                "video_reference_params": {
                    "camera_move_type": result.camera_move_type.value,
                    "camera_move_intensity": result.camera_move_intensity,
                    "camera_move_confidence": result.camera_move_confidence,
                    "subject_position": list(result.subject_position),
                    "framing": result.framing,
                    "rule_of_thirds": result.rule_of_thirds,
                    "headroom": result.headroom,
                    "lighting_mood_tags": result.lighting_mood_tags,
                    "primary_color": list(result.primary_color),
                    "primary_temperature_k": result.primary_temperature_k,
                    "fill_ratio": result.fill_ratio,
                    "environment_type": result.environment_type,
                    "time_of_day": result.time_of_day,
                    "weather": result.weather,
                    "geometry_categories": result.geometry_categories,
                    "clip_duration_seconds": result.clip_duration_seconds,
                    "keyframe_count": result.keyframe_count,
                    "shot_blocks": [
                        {
                            "shot_id": sb.shot_id,
                            "camera_move_type": sb.camera_move_type.value,
                            "start_time": sb.start_time,
                            "end_time": sb.end_time,
                            "start_position": list(sb.start_position),
                            "end_position": list(sb.end_position),
                            "fov": sb.fov,
                            "nl_description": sb.nl_description,
                            "user_confirmed": sb.user_confirmed,
                        }
                        for sb in result.shot_blocks
                    ],
                    "requires_user_confirmation": result.requires_user_confirmation(),
                    "analysis_confidence": result.analysis_confidence,
                },
                "message": (
                    f"Video analyzed: {result.camera_move_type.value} shot, "
                    f"confidence={result.analysis_confidence:.0%}, "
                    f"{result.keyframe_count} keyframes. "
                    + ("User confirmation recommended." if result.requires_user_confirmation() else "")
                ),
            })

        except ValueError as e:
            return NyraToolResult.err(str(e))
        except RuntimeError as e:
            return NyraToolResult.err(str(e))
        except Exception as e:
            log.error("video_analysis_unexpected_error", error=str(e))
            return NyraToolResult.err(f"[-32050] Unexpected error during video analysis: {e}")
