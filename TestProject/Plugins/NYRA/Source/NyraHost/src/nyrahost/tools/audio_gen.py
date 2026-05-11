"""nyrahost.tools.audio_gen — Phase 19-A audio_gen MCP tool.

Aura ships "Make a grenade explosion sound" / "Generate a 30-second
ambient forest soundscape" as a chat-driven flow. NYRA mirrors via
audio_gen/sfx WS method backed by AudioGenClient.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Final, Optional

import structlog

from nyrahost.external.audio_gen_client import (
    AudioGenAPIError,
    AudioGenAuthError,
    AudioGenClient,
    AudioGenRateLimitError,
    AudioGenTimeoutError,
    MAX_DURATION_S,
    MIN_DURATION_S,
)
from nyrahost.privacy_guard import OutboundRefused

log = structlog.get_logger("nyrahost.tools.audio_gen")

ERR_BAD_INPUT: Final[int] = -32602
ERR_AUDIO_AUTH: Final[int] = -32081
ERR_AUDIO_FAILED: Final[int] = -32082
ERR_PRIVACY_REFUSED: Final[int] = -32072


def _err(code: int, message: str, detail: str = "",
         remediation: Optional[str] = None) -> dict:
    data: dict = {}
    if detail:
        data["detail"] = detail
    if remediation:
        data["remediation"] = remediation
    out: dict = {"error": {"code": code, "message": message}}
    if data:
        out["error"]["data"] = data
    return out


async def on_generate_sfx(params: dict, session=None, ws=None) -> dict:
    prompt = params.get("prompt")
    if not isinstance(prompt, str) or not prompt:
        return _err(ERR_BAD_INPUT, "missing_field", "prompt")
    try:
        duration_s = float(params.get("duration_s", 5.0))
    except (TypeError, ValueError):
        return _err(ERR_BAD_INPUT, "bad_duration")
    project_saved = (
        params.get("project_saved") or os.environ.get("NYRA_PROJECT_SAVED") or "."
    )
    job_id = str(uuid.uuid4())[:12]
    out_path = Path(project_saved) / "NYRA" / "audio" / f"{job_id}.mp3"

    try:
        client = AudioGenClient()
    except ValueError as exc:
        return _err(
            ERR_AUDIO_AUTH, "elevenlabs_auth_failed", str(exc),
            remediation=(
                "Set ELEVENLABS_API_KEY in editor settings. "
                "Audio generation requires ElevenLabs SFX entitlement."
            ),
        )

    try:
        result = await client.generate_sfx(
            prompt=prompt,
            duration_s=duration_s,
            output_path=out_path,
        )
    except AudioGenAuthError as exc:
        return _err(ERR_AUDIO_AUTH, "elevenlabs_auth_failed", str(exc))
    except OutboundRefused as exc:
        return _err(ERR_PRIVACY_REFUSED, "privacy_mode_active", str(exc))
    except (AudioGenRateLimitError, AudioGenAPIError, AudioGenTimeoutError) as exc:
        return _err(ERR_AUDIO_FAILED, "audio_gen_failed", str(exc))
    return {
        "job_id": job_id,
        "file_path": result.file_path,
        "duration_s": result.duration_s,
        "prompt": result.prompt,
        "provider": result.provider,
    }


__all__ = ["on_generate_sfx", "ERR_BAD_INPUT", "ERR_AUDIO_AUTH",
           "ERR_AUDIO_FAILED", "ERR_PRIVACY_REFUSED"]
