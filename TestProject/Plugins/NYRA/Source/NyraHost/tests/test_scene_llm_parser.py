from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from nyrahost.tools.scene_llm_parser import (
    LightingLLMParser,
    SYSTEM_PROMPT,
    _params_from_dict,
)
from nyrahost.tools.scene_types import LightingParams


class _FakeRouter:
    def __init__(self, text_response=None, image_response=None, raise_on_text=False, raise_on_image=False):
        self.text_response = text_response
        self.image_response = image_response
        self.raise_on_text = raise_on_text
        self.raise_on_image = raise_on_image
        self.last_text_prompt = None
        self.last_image_path = None

    async def generate_lighting_from_text(self, prompt, system=None):
        self.last_text_prompt = prompt
        if self.raise_on_text:
            raise RuntimeError("router exploded")
        return self.text_response

    async def generate_lighting_from_image(self, image_path, system=None):
        self.last_image_path = image_path
        if self.raise_on_image:
            raise RuntimeError("vision exploded")
        return self.image_response


def test_system_prompt_documents_full_schema():
    for key in [
        "primary_light_type",
        "primary_intensity",
        "primary_color",
        "use_sky_atmosphere",
        "use_exponential_height_fog",
        "mood_tags",
    ]:
        assert key in SYSTEM_PROMPT


def test_params_from_dict_handles_lists_and_defaults():
    lp = _params_from_dict({
        "primary_light_type": "spot",
        "primary_intensity": 2.0,
        "primary_color": [0.5, 0.6, 0.7],
        "primary_direction": [10, 20, 30],
        "fog_color": [0.1, 0.2, 0.3],
        "mood_tags": ["dramatic"],
    })
    assert lp.primary_light_type == "spot"
    assert lp.primary_color == (0.5, 0.6, 0.7)
    assert lp.primary_direction == (10.0, 20.0, 30.0)
    assert lp.fog_color == (0.1, 0.2, 0.3)
    assert lp.mood_tags == ["dramatic"]
    # Defaults still hold for unspecified fields.
    assert lp.primary_temperature_k == 5500.0


def test_parse_from_text_uses_router_dict_response():
    router = _FakeRouter(text_response={
        "primary_light_type": "directional",
        "primary_intensity": 1.5,
        "primary_color": [0.95, 0.65, 0.3],
        "primary_direction_deg": [45, -30, 0],
        "mood_tags": ["warm", "low sun"],
        "confidence": 0.91,
    })
    parser = LightingLLMParser(backend_router=router)
    lp = asyncio.run(parser.parse_from_text("golden hour"))
    assert lp.primary_light_type == "directional"
    assert lp.primary_intensity == 1.5
    assert lp.primary_direction == (45.0, -30.0, 0.0)
    assert lp.confidence == 0.91
    assert lp.prompt == "golden hour"
    assert router.last_text_prompt == "golden hour"


def test_parse_from_text_unwraps_json_string_response():
    router = _FakeRouter(text_response='{"primary_light_type": "point", "mood_tags": ["cool"]}')
    parser = LightingLLMParser(backend_router=router)
    lp = asyncio.run(parser.parse_from_text("moody blue"))
    assert lp.primary_light_type == "point"
    assert lp.mood_tags == ["cool"]


def test_parse_from_text_extracts_json_from_fenced_response():
    router = _FakeRouter(text_response="```json\n{\"primary_light_type\": \"rect\"}\n```")
    parser = LightingLLMParser(backend_router=router)
    lp = asyncio.run(parser.parse_from_text("studio"))
    assert lp.primary_light_type == "rect"


def test_parse_from_text_falls_back_when_router_raises():
    router = _FakeRouter(raise_on_text=True)
    parser = LightingLLMParser(backend_router=router)
    lp = asyncio.run(parser.parse_from_text("golden hour"))
    # Rule-based golden_hour preset was matched.
    assert lp.primary_light_type == "directional"
    assert "warm" in lp.mood_tags
    assert lp.prompt == "golden hour"


def test_parse_from_text_no_router_uses_rule_based_fallback():
    parser = LightingLLMParser(backend_router=None)
    lp = asyncio.run(parser.parse_from_text("harsh overhead noon"))
    assert lp.primary_light_type == "directional"
    assert lp.primary_direction == (-90.0, 0.0, 0.0)
    assert "harsh" in lp.mood_tags


def test_parse_from_text_unknown_prompt_default_studio_fill():
    parser = LightingLLMParser(backend_router=None)
    lp = asyncio.run(parser.parse_from_text("xyzzy nonsense"))
    # Defaults to studio_fill when no token matches.
    assert lp.primary_light_type == "rect"
    assert "studio" in lp.mood_tags


def test_parse_from_image_validates_existence(tmp_path):
    parser = LightingLLMParser(backend_router=None)
    missing = tmp_path / "missing.png"
    with pytest.raises(FileNotFoundError):
        asyncio.run(parser.parse_from_image(str(missing)))


def test_parse_from_image_uses_router(tmp_path):
    fake_image = tmp_path / "ref.png"
    fake_image.write_bytes(b"\x89PNG\r\n\x1a\n")  # not a real image, just a path that exists
    router = _FakeRouter(image_response={
        "primary_light_type": "directional",
        "primary_color": [0.7, 0.5, 0.4],
        "use_sky_atmosphere": True,
        "mood_tags": ["dawn"],
    })
    parser = LightingLLMParser(backend_router=router)
    lp = asyncio.run(parser.parse_from_image(str(fake_image)))
    assert lp.primary_light_type == "directional"
    assert lp.use_sky_atmosphere is True
    assert lp.mood_tags == ["dawn"]
    assert lp.prompt == f"image:{fake_image.name}"
    assert router.last_image_path == str(fake_image)


def test_parse_from_image_falls_back_when_router_raises(tmp_path):
    fake_image = tmp_path / "ref.png"
    fake_image.write_bytes(b"\x89PNG")
    router = _FakeRouter(raise_on_image=True)
    parser = LightingLLMParser(backend_router=router)
    lp = asyncio.run(parser.parse_from_image(str(fake_image)))
    # Falls back to studio_fill default; prompt set to image: tag.
    assert lp.prompt.startswith("image:")
    assert isinstance(lp, LightingParams)


def test_parse_from_image_no_router_returns_studio_fallback(tmp_path):
    fake_image = tmp_path / "ref.png"
    fake_image.write_bytes(b"\x89PNG")
    parser = LightingLLMParser(backend_router=None)
    lp = asyncio.run(parser.parse_from_image(str(fake_image)))
    assert lp.primary_light_type == "rect"  # studio_fill default
    assert lp.prompt == f"image:{fake_image.name}"
