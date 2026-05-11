"""nyrahost.external.audio_gen_client — Phase 19-A audio generation.

Aura ships text-to-audio for SFX, ambient soundscapes, music loops,
and voiceover. NYRA mirrors the surface via an external provider:

  * Default: ElevenLabs SFX API (https://api.elevenlabs.io/v1/sound-generation)
    — 0.5..22 second clips, MP3 output
  * Future drop-in: Suno (music), MiniMax / FishAudio (voice)

Auth: ``ELEVENLABS_API_KEY`` env (mirroring Meshy's MESHY_API_KEY).
Privacy Mode honoured via Phase 15-E PRIVACY_GUARD.
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

import httpx
import structlog

from nyrahost.privacy_guard import GUARD as PRIVACY_GUARD, OutboundRefused

log = structlog.get_logger("nyrahost.external.audio_gen_client")

ELEVENLABS_SFX_URL: Final[str] = "https://api.elevenlabs.io/v1/sound-generation"
MIN_DURATION_S: Final[float] = 0.5
MAX_DURATION_S: Final[float] = 22.0
DEFAULT_DURATION_S: Final[float] = 5.0
DEFAULT_PROMPT_INFLUENCE: Final[float] = 0.3


class AudioGenAuthError(Exception): pass
class AudioGenRateLimitError(Exception): pass
class AudioGenAPIError(Exception): pass
class AudioGenTimeoutError(Exception): pass


@dataclass(frozen=True)
class AudioGenResult:
    file_path: str
    duration_s: float
    prompt: str
    provider: str


class AudioGenClient:
    """ElevenLabs SFX API client.

    Returns one MP3 file per call. ``duration_s`` is clamped to
    [0.5, 22.0] silently — over/under is the API's hard cap.
    """

    def __init__(self, *, api_key: str | None = None,
                 base_url: str | None = None,
                 timeout: float = 120.0) -> None:
        self._api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        if not self._api_key:
            raise ValueError(
                "ELEVENLABS_API_KEY not set; pass api_key= or set env var."
            )
        self._base_url = base_url or ELEVENLABS_SFX_URL
        self._timeout = timeout

    def _headers(self) -> dict:
        # T-19-01: API key in xi-api-key header per ElevenLabs docs;
        # never log the key value.
        return {"xi-api-key": self._api_key, "Content-Type": "application/json"}

    async def generate_sfx(
        self,
        *,
        prompt: str,
        duration_s: float = DEFAULT_DURATION_S,
        prompt_influence: float = DEFAULT_PROMPT_INFLUENCE,
        output_path: Path,
    ) -> AudioGenResult:
        PRIVACY_GUARD.assert_allowed(self._base_url)
        d = max(MIN_DURATION_S, min(float(duration_s), MAX_DURATION_S))
        body = {
            "text": prompt,
            "duration_seconds": d,
            "prompt_influence": float(prompt_influence),
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(self._timeout)) as client:
            resp = await client.post(self._base_url, headers=self._headers(), json=body)
            if resp.status_code == 401:
                raise AudioGenAuthError(
                    "ElevenLabs API key invalid or missing entitlement. "
                    "Check the SFX product is enabled on your plan."
                )
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", "60"))
                raise AudioGenRateLimitError(
                    f"ElevenLabs rate limit; retry after {retry_after}s."
                )
            if not resp.is_success:
                raise AudioGenAPIError(
                    f"ElevenLabs SFX HTTP {resp.status_code}: {resp.reason_phrase}"
                )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(resp.content)
        log.info("audio_gen_ok", path=str(output_path), duration_s=d,
                 chars=len(prompt))
        return AudioGenResult(
            file_path=str(output_path),
            duration_s=d,
            prompt=prompt,
            provider="elevenlabs_sfx",
        )


__all__ = [
    "AudioGenClient", "AudioGenResult",
    "AudioGenAuthError", "AudioGenRateLimitError",
    "AudioGenAPIError", "AudioGenTimeoutError",
    "ELEVENLABS_SFX_URL", "MIN_DURATION_S", "MAX_DURATION_S",
    "DEFAULT_DURATION_S",
]
