"""nyrahost.tools.scene_llm_parser - LLM-powered lighting parameter extractor.

LightingLLMParser turns NL prompts ("golden hour", "moody blue", etc.) or
reference images into structured LightingParams. Falls back to a rule-based
preset matcher when the backend router is unavailable (offline/Gemma mode).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

import structlog

from nyrahost.tools.scene_types import LightingParams

log = structlog.get_logger("nyrahost.tools.scene_llm_parser")


SYSTEM_PROMPT = """You are NYRA's lighting analysis engine. Given a scene description or reference image, output a JSON object describing the lighting setup.

Schema:
{
  "primary_light_type": "directional|spot|point|rect|sky",
  "primary_intensity": float,
  "primary_color": [r, g, b],
  "primary_direction_deg": [pitch, yaw, roll],
  "primary_temperature_k": float,
  "use_shadow": bool,
  "fill_light_type": "",
  "fill_intensity": float,
  "use_sky_atmosphere": bool,
  "sky_composition": "earth|urban|clear",
  "use_volumetric_cloud": bool,
  "cloud_coverage": float,
  "use_exponential_height_fog": bool,
  "fog_density": float,
  "fog_color": [r, g, b],
  "use_post_process": bool,
  "exposure_compensation": float,
  "mood_tags": ["warm", "high-contrast"],
  "confidence": float
}

Only output JSON. Do not add explanation."""


# Rule-based fallback presets keyed by token matches in the NL prompt.
_FALLBACK_PRESETS: dict[str, dict[str, Any]] = {
    "golden_hour": {
        "tokens": ["golden hour", "sunset", "magic hour", "warm sun"],
        "params": dict(
            primary_light_type="directional",
            primary_intensity=1.5,
            primary_color=(0.95, 0.65, 0.3),
            primary_direction=(45.0, -30.0, 0.0),
            primary_temperature_k=3500.0,
            use_shadow=True,
            use_sky_atmosphere=True,
            use_exponential_height_fog=True,
            fog_density=0.01,
            fog_color=(0.8, 0.7, 0.6),
            use_post_process=True,
            exposure_compensation=0.5,
            mood_tags=["warm", "low sun", "soft shadow"],
            confidence=0.6,
        ),
    },
    "harsh_overhead": {
        "tokens": ["harsh", "overhead", "noon", "midday", "studio harsh"],
        "params": dict(
            primary_light_type="directional",
            primary_intensity=2.5,
            primary_color=(1.0, 1.0, 1.0),
            primary_direction=(-90.0, 0.0, 0.0),
            primary_temperature_k=5500.0,
            use_shadow=True,
            shadow_cascades=4,
            use_exponential_height_fog=False,
            mood_tags=["harsh", "overhead", "high-contrast"],
            confidence=0.6,
        ),
    },
    "moody_blue": {
        "tokens": ["moody", "blue", "cool", "night", "dim"],
        "params": dict(
            primary_light_type="point",
            primary_intensity=0.5,
            primary_color=(0.4, 0.5, 0.9),
            primary_direction=(0.0, 0.0, 0.0),
            use_shadow=False,
            use_exponential_height_fog=True,
            fog_density=0.04,
            fog_color=(0.5, 0.6, 0.9),
            use_post_process=True,
            exposure_compensation=-1.5,
            mood_tags=["cool", "moody", "low-key"],
            confidence=0.6,
        ),
    },
    "studio_fill": {
        "tokens": ["studio", "fill", "neutral", "even"],
        "params": dict(
            primary_light_type="rect",
            primary_intensity=1.0,
            primary_color=(1.0, 0.95, 0.9),
            primary_direction=(0.0, 0.0, 0.0),
            fill_light_type="point",
            fill_intensity=0.3,
            fill_color=(0.6, 0.7, 1.0),
            use_shadow=True,
            mood_tags=["neutral", "soft fill", "studio"],
            confidence=0.6,
        ),
    },
    "dawn": {
        "tokens": ["dawn", "morning", "sunrise", "pink", "first light"],
        "params": dict(
            primary_light_type="directional",
            primary_intensity=0.8,
            primary_color=(0.7, 0.5, 0.4),
            primary_direction=(15.0, -60.0, 0.0),
            primary_temperature_k=2800.0,
            use_shadow=True,
            use_sky_atmosphere=True,
            use_exponential_height_fog=True,
            fog_density=0.03,
            fog_color=(0.6, 0.5, 0.5),
            use_post_process=True,
            exposure_compensation=0.3,
            mood_tags=["dawn", "pink", "diffuse"],
            confidence=0.6,
        ),
    },
}


def _params_from_dict(d: dict[str, Any]) -> LightingParams:
    """Coerce a JSON-style dict (lists for tuples) into LightingParams."""
    def to_tuple(v, default):
        if v is None:
            return default
        if isinstance(v, (list, tuple)):
            return tuple(float(x) for x in v)
        return default

    primary_color = to_tuple(d.get("primary_color"), (1.0, 1.0, 1.0))
    primary_direction = to_tuple(
        d.get("primary_direction") or d.get("primary_direction_deg"),
        (0.0, 0.0, 0.0),
    )
    fog_color = to_tuple(d.get("fog_color"), (0.8, 0.85, 1.0))

    return LightingParams(
        primary_light_type=d.get("primary_light_type", "directional"),
        primary_intensity=float(d.get("primary_intensity", 1.0)),
        primary_color=primary_color,
        primary_direction=primary_direction,
        primary_temperature_k=float(d.get("primary_temperature_k", 5500.0)),
        use_shadow=bool(d.get("use_shadow", True)),
        shadow_cascades=int(d.get("shadow_cascades", 4)),
        fill_light_type=d.get("fill_light_type", ""),
        fill_intensity=float(d.get("fill_intensity", 0.0)),
        use_sky_atmosphere=bool(d.get("use_sky_atmosphere", False)),
        sky_atmosphere_composition=d.get("sky_composition", d.get("sky_atmosphere_composition", "earth")),
        use_volumetric_cloud=bool(d.get("use_volumetric_cloud", False)),
        cloud_coverage=float(d.get("cloud_coverage", 0.5)),
        use_exponential_height_fog=bool(d.get("use_exponential_height_fog", False)),
        fog_density=float(d.get("fog_density", 0.02)),
        fog_color=fog_color,
        use_post_process=bool(d.get("use_post_process", False)),
        exposure_compensation=float(d.get("exposure_compensation", 0.0)),
        mood_tags=list(d.get("mood_tags", [])),
        confidence=float(d.get("confidence", 0.0)),
    )


class LightingLLMParser:
    """Convert NL prompts or reference images into structured LightingParams.

    The backend router is duck-typed — anything with awaitable
    `generate_lighting_from_text(prompt, system) -> dict` and
    `generate_lighting_from_image(image_path, system) -> dict` works.
    """

    def __init__(self, backend_router: Optional[Any] = None):
        self.router = backend_router

    async def parse_from_text(self, nl_prompt: str) -> LightingParams:
        """Parse a natural-language lighting description into LightingParams."""
        if self.router is None:
            log.warning("scene_llm_parser_fallback", reason="no_router", prompt=nl_prompt)
            return self._rule_based_fallback(nl_prompt)
        try:
            raw = await self.router.generate_lighting_from_text(nl_prompt, system=SYSTEM_PROMPT)
            params = _params_from_dict(self._coerce_to_dict(raw))
            params.prompt = nl_prompt
            log.info("scene_llm_parser_text_ok", mood_tags=params.mood_tags, confidence=params.confidence)
            return params
        except Exception as e:
            log.error("scene_llm_parser_text_failed", error=str(e), prompt=nl_prompt)
            fallback = self._rule_based_fallback(nl_prompt)
            fallback.prompt = nl_prompt
            return fallback

    async def parse_from_image(self, image_path: str) -> LightingParams:
        """Parse lighting parameters from a reference image via vision LLM."""
        # T-06-01: validate image_path exists before sending to LLM.
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Reference image not found: {image_path}")
        if self.router is None:
            log.warning("scene_llm_parser_fallback", reason="no_router", image_path=image_path)
            fallback = self._rule_based_fallback("studio fill")
            fallback.prompt = f"image:{Path(image_path).name}"
            return fallback
        try:
            raw = await self.router.generate_lighting_from_image(image_path, system=SYSTEM_PROMPT)
            params = _params_from_dict(self._coerce_to_dict(raw))
            params.prompt = f"image:{Path(image_path).name}"
            log.info("scene_llm_parser_image_ok", mood_tags=params.mood_tags, image=Path(image_path).name)
            return params
        except Exception as e:
            log.error("scene_llm_parser_image_failed", error=str(e), image_path=image_path)
            fallback = self._rule_based_fallback("studio fill")
            fallback.prompt = f"image:{Path(image_path).name}"
            return fallback

    @staticmethod
    def _coerce_to_dict(raw: Any) -> dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                # Strip code fences if the model wrapped JSON.
                m = re.search(r"\{.*\}", raw, re.DOTALL)
                if m:
                    return json.loads(m.group(0))
                raise
        raise TypeError(f"LLM router returned unexpected type {type(raw).__name__}")

    @staticmethod
    def _rule_based_fallback(nl_prompt: str) -> LightingParams:
        prompt_lower = (nl_prompt or "").lower()
        for preset_key, preset in _FALLBACK_PRESETS.items():
            if any(token in prompt_lower for token in preset["tokens"]):
                log.info("scene_llm_parser_fallback_match", preset=preset_key, prompt=nl_prompt)
                return _params_from_dict(preset["params"])
        # Default: studio fill as the safest neutral choice.
        log.info("scene_llm_parser_fallback_default", prompt=nl_prompt)
        return _params_from_dict(_FALLBACK_PRESETS["studio_fill"]["params"])
