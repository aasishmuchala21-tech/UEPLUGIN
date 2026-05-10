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

from nyrahost.tools.scene_types import LIGHTING_PRESETS, PRESET_TOKENS, LightingParams

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


# WR-05: Rule-based fallback presets are now derived from the canonical
# LIGHTING_PRESETS + PRESET_TOKENS tables in scene_types so the apply path
# and the parser fallback path cannot drift.
def _build_fallback_presets() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for key, lp in LIGHTING_PRESETS.items():
        out[key] = {
            "tokens": PRESET_TOKENS.get(key, []),
            "lighting_params": lp,
        }
    return out


_FALLBACK_PRESETS: dict[str, dict[str, Any]] = _build_fallback_presets()


def _params_from_dict(d: dict[str, Any]) -> LightingParams:
    """Backwards-compatible alias for LightingParams.from_dict (WR-03).

    The canonical conversion now lives on the dataclass itself; this
    private function is preserved so any existing import sites keep
    working without churn.
    """
    return LightingParams.from_dict(d)


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
                return _clone_with_confidence(preset["lighting_params"], 0.6)
        # Default: studio fill as the safest neutral choice.
        log.info("scene_llm_parser_fallback_default", prompt=nl_prompt)
        return _clone_with_confidence(_FALLBACK_PRESETS["studio_fill"]["lighting_params"], 0.6)


def _clone_with_confidence(lp: LightingParams, confidence: float) -> LightingParams:
    """Return a copy of `lp` with a different confidence (rule-based fallback marker).

    Avoids mutating the canonical LIGHTING_PRESETS entries.
    """
    from dataclasses import replace
    return replace(lp, confidence=confidence)
