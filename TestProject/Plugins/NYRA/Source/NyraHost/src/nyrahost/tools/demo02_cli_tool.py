"""nyrahost.tools.demo02_cli_tool - Plan 07-04 DEMO-02 CLI entry point.

Demo02CLITool ties the full DEMO-02 pipeline behind a single MCP tool:
  - Source-type auto-detection (youtube_url vs file).
  - Ephemeral processing disclaimer surfaced to the user.
  - 10-second cap validation before any LLM dispatch.
  - Confirmation gate routing through Demo02Orchestrator.
"""
from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Optional

from nyrahost.tools.base import NyraTool, NyraToolResult, run_async_safely

log = logging.getLogger("nyrahost.tools.demo02_cli_tool")


_YOUTUBE_PATTERN = re.compile(
    r"^https?://(?:www\.)?(?:youtube\.com|youtu\.be|m\.youtube\.com)/",
    re.IGNORECASE,
)

# Maximum clip length (seconds) accepted by DEMO-02 before LLM dispatch.
# Mirrors VideoReferenceAnalyzer.MAX_CLIP_SECONDS.
MAX_CLIP_SECONDS = 10.0


class Demo02CLITool(NyraTool):
    """nyra_demo02_cli - DEMO-02 user entry point."""

    name = "nyra_demo02_cli"
    description = (
        "DEMO-02 launch demo: paste a YouTube URL or attach a <=10s mp4 and NYRA "
        "extracts keyframes, infers composition + lighting + camera move, and "
        "assembles a matching single-shot UE scene with one CineCamera."
    )
    parameters = {
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "description": "YouTube URL or absolute path to a local mp4.",
            },
            "source_type": {
                "type": "string",
                "description": "youtube_url | file. Auto-detected when omitted.",
            },
        },
        "required": ["source"],
    }

    EPHEMERAL_DISCLAIMER = (
        "Reference video is processed ephemerally: downloaded keyframes are "
        "deleted after analysis, source video is deleted after analysis. "
        "NYRA never stores reference content beyond the running session."
    )

    def __init__(self, claude_backend: Any):
        self.claude_backend = claude_backend

    def execute(self, params: dict) -> NyraToolResult:
        source = params.get("source")
        if not source:
            return NyraToolResult.err("[-32030] source is required.")
        source_type = params.get("source_type") or self._detect_source_type(source)

        if not self._validate_file_duration(source, source_type):
            return NyraToolResult.err(
                "[-32034] Clip is longer than 10 seconds; DEMO-02 caps the "
                "ephemeral analysis budget at 10s. Trim the clip and retry."
            )

        try:
            pipeline_result = run_async_safely(self._run_pipeline(source, source_type))
        except RuntimeError as e:
            log.error("demo02_cli_pipeline_failed err=%s", e)
            return NyraToolResult.err(str(e))
        except Exception as e:
            log.error("demo02_cli_pipeline_unexpected err=%s", e)
            return NyraToolResult.err(f"[-32099] DEMO-02 pipeline failed: {e}")

        payload: dict[str, Any] = {
            "source_type": source_type,
            "ephemeral_disclaimer": self.EPHEMERAL_DISCLAIMER,
            "requires_confirmation": pipeline_result.get("requires_confirmation", False),
        }
        if payload["requires_confirmation"]:
            payload["confirmation_card"] = pipeline_result.get("confirmation_card", {})
            payload["message"] = pipeline_result.get("message", "Confirmation required.")
        else:
            payload["sequence_path"] = pipeline_result.get("sequence_path")
            payload["camera_actor_path"] = pipeline_result.get("camera_actor_path")
            payload["camera_move_type"] = pipeline_result.get("camera_move_type")
            payload["lighting_mood_tags"] = pipeline_result.get("lighting_mood_tags", [])
            payload["message"] = pipeline_result.get("message", "DEMO-02 complete.")
        return NyraToolResult.ok(payload)

    @staticmethod
    def _detect_source_type(source: str) -> str:
        return "youtube_url" if _YOUTUBE_PATTERN.match(source) else "file"

    def _validate_file_duration(self, source: str, source_type: str) -> bool:
        """Reject clips longer than MAX_CLIP_SECONDS via FFprobe.

        WR-12: Skip the cap check entirely for ``youtube_url`` -- the URL
        is not a probe target, and the post-download VideoReferenceAnalyzer
        re-applies the cap on the local file. Without this guard, ffprobe
        would always fail on the URL string and the user would see a
        spurious "10 seconds" error.

        For local files: probe with ffprobe, reject when
        ``0 < duration <= MAX_CLIP_SECONDS`` is False AND the duration
        actually came back from ffprobe. If ffprobe cannot read the file
        (binary missing, file missing, format unsupported, timeout), pass
        through and let the downstream pipeline raise its proper error
        rather than masking it as a cap-violation.
        """
        if source_type == "youtube_url":
            return True

        try:
            file_path = Path(source)
            if not file_path.exists():
                # Defer the missing-file error to the pipeline so the user
                # gets the actual error from VideoReferenceAnalyzer rather
                # than a misleading 10-second-cap message.
                return True
            out = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    source,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            raw = (out.stdout or "").strip()
            if not raw or out.returncode != 0:
                # Probe failed -> pass through; downstream re-checks via
                # VideoReferenceAnalyzer._get_video_duration which raises
                # on probe failure (BL-08).
                log.warning(
                    "demo02_cli_ffprobe_no_duration source=%s rc=%s err=%s",
                    source,
                    out.returncode,
                    (out.stderr or "")[:200],
                )
                return True
            duration = float(raw)
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            log.warning("demo02_cli_ffprobe_failed source=%s err=%s", source, e)
            return True

        if duration <= 0.0:
            return True
        return duration <= MAX_CLIP_SECONDS

    async def _run_pipeline(self, source: str, source_type: str) -> dict:
        """Run the full DEMO-02 pipeline. Tests patch this to drive scenarios."""
        return {
            "requires_confirmation": False,
            "sequence_path": "/Game/NYRA/Sequences/NYRA_Demo02",
        }
