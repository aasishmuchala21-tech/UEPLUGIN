"""nyrahost.tools.scene_types - Phase 6 shared dataclasses.

All Phase 6 components (SCENE-01 lighting, DEMO-01 assembly) import from here.
Do not duplicate these definitions in scene_llm_parser.py or scene_assembler.py.

WR-05: LIGHTING_PRESETS and PRESET_TOKENS are the single source of truth for
the preset library. lighting_tools._PRESETS and scene_llm_parser._FALLBACK_PRESETS
both reference these tables now.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Scene assembly types
# ---------------------------------------------------------------------------

@dataclass
class ActorSpec:
    """Specification for a single actor to be placed in the scene."""
    role: str
    class_path: str
    asset_hint: str
    count: int = 1
    placement: str = "scattered"
    transform_hint: str = ""
    source: str = "library"


@dataclass
class MaterialSpec:
    """Specification for a material to apply to one or more actors."""
    target_actor: str
    material_type: str
    texture_hint: str
    source: str = "library"
    asset_path: str = ""
    fallback_path: str = ""


@dataclass
class SceneBlueprint:
    """Structured output from LLM image analysis - the scene assembly plan."""
    scene_type: str
    actor_specs: list[ActorSpec]
    material_specs: list[MaterialSpec]
    mood_tags: list[str]
    confidence: float = 0.0


@dataclass
class AssemblyResult:
    """Result of a full scene assembly run."""
    placed_actors: list[dict] = field(default_factory=list)
    applied_materials: list[dict] = field(default_factory=list)
    lighting_actors: list[dict] = field(default_factory=list)
    log_entries: list[str] = field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None

    @property
    def actor_count(self) -> int:
        return len(self.placed_actors)

    @property
    def material_count(self) -> int:
        return len(self.applied_materials)

    @property
    def lighting_count(self) -> int:
        return len(self.lighting_actors)

    def to_structured_summary(self) -> dict:
        """Returns the dict used for success copy in SNyraLogDrawer."""
        return {
            "success": self.success,
            "actor_count": self.actor_count,
            "material_count": self.material_count,
            "lighting_count": self.lighting_count,
            "message": (
                f"{self.actor_count} actors placed, "
                f"{self.material_count} materials applied, "
                f"{self.lighting_count} light setup configured."
            ),
            "log_entries": self.log_entries,
        }


# ---------------------------------------------------------------------------
# Lighting types (shared between SCENE-01 and DEMO-01)
# ---------------------------------------------------------------------------

@dataclass
class LightingParams:
    """Structured lighting parameters derived from NL prompts or reference images."""
    primary_light_type: str = "directional"
    primary_intensity: float = 1.0
    primary_color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    primary_direction: tuple[float, float, float] = (0.0, 0.0, 0.0)
    primary_temperature_k: float = 5500.0
    use_shadow: bool = True
    shadow_cascades: int = 4

    fill_light_type: str = ""
    fill_intensity: float = 0.0
    fill_color: tuple[float, float, float] = (0.5, 0.5, 0.5)

    use_sky_atmosphere: bool = False
    sky_atmosphere_composition: str = "earth"
    use_volumetric_cloud: bool = False
    cloud_coverage: float = 0.5
    use_exponential_height_fog: bool = False
    fog_density: float = 0.02
    fog_height_falloff: float = 0.2
    fog_color: tuple[float, float, float] = (0.8, 0.85, 1.0)
    use_volumetric_fog: bool = False
    volumetric_fog_density: float = 0.1

    use_post_process: bool = False
    exposure_compensation: float = 0.0
    contrast: float = 1.0
    color_saturation: float = 1.0

    prompt: str = ""
    mood_tags: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_ue_params(self) -> dict:
        """Return a flat dict of UE-compatible parameter values."""
        return {
            "primary_light_type": self.primary_light_type,
            "primary_intensity": self.primary_intensity,
            "primary_color_r": self.primary_color[0],
            "primary_color_g": self.primary_color[1],
            "primary_color_b": self.primary_color[2],
            "primary_direction_pitch": self.primary_direction[0],
            "primary_direction_yaw": self.primary_direction[1],
            "primary_direction_roll": self.primary_direction[2],
            "primary_temperature_k": self.primary_temperature_k,
            "use_shadow": self.use_shadow,
            "use_sky_atmosphere": self.use_sky_atmosphere,
            "use_volumetric_cloud": self.use_volumetric_cloud,
            "use_exponential_height_fog": self.use_exponential_height_fog,
            "fog_density": self.fog_density,
            "fog_color_r": self.fog_color[0],
            "fog_color_g": self.fog_color[1],
            "fog_color_b": self.fog_color[2],
            "use_post_process": self.use_post_process,
            "exposure_compensation": self.exposure_compensation,
            "mood_tags": self.mood_tags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LightingParams":
        """Coerce a JSON-style dict (lists for tuples, missing keys ok) into LightingParams.

        WR-03: public API for cross-module use. scene_llm_parser._params_from_dict
        delegates here so the canonical conversion lives next to the dataclass.
        """
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

        return cls(
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


# ---------------------------------------------------------------------------
# Asset resolution types
# ---------------------------------------------------------------------------

@dataclass
class AssetResolutionResult:
    """Result of resolving an asset through the fallback chain."""
    asset_path: str
    source: str
    quality_score: float
    generation_time: Optional[float] = None


@dataclass
class ProgressUpdate:
    """A single progress update for WS streaming to Slate panel."""
    step: str
    current: int
    total: int
    message: str = ""

    def to_ws_payload(self) -> dict:
        return {
            "type": "assembly_progress",
            "step": self.step,
            "current": self.current,
            "total": self.total,
            "message": self.message,
        }


# ---------------------------------------------------------------------------
# Canonical lighting preset library (WR-05)
# ---------------------------------------------------------------------------
#
# Single source of truth for the SCENE-01 / DEMO-01 preset library. Both
# lighting_tools._PRESETS (for direct preset->params application) and
# scene_llm_parser._FALLBACK_PRESETS (for token-keyed rule-based fallback)
# now reference these dicts so they cannot drift.

LIGHTING_PRESETS: dict[str, "LightingParams"] = {
    "golden_hour": LightingParams(
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
    ),
    "harsh_overhead": LightingParams(
        primary_light_type="directional",
        primary_intensity=2.5,
        primary_color=(1.0, 1.0, 1.0),
        primary_direction=(-90.0, 0.0, 0.0),
        primary_temperature_k=5500.0,
        use_shadow=True,
        shadow_cascades=4,
        use_exponential_height_fog=False,
        mood_tags=["harsh", "overhead", "high-contrast"],
    ),
    "moody_blue": LightingParams(
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
    ),
    "studio_fill": LightingParams(
        primary_light_type="rect",
        primary_intensity=1.0,
        primary_color=(1.0, 0.95, 0.9),
        primary_direction=(0.0, 0.0, 0.0),
        fill_light_type="point",
        fill_intensity=0.3,
        fill_color=(0.6, 0.7, 1.0),
        use_shadow=True,
        mood_tags=["neutral", "soft fill", "studio"],
    ),
    "dawn": LightingParams(
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
    ),
}

# Token keyword index for the rule-based parser fallback. Keep aligned with
# LIGHTING_PRESETS keys.
PRESET_TOKENS: dict[str, list[str]] = {
    "golden_hour": ["golden hour", "sunset", "magic hour", "warm sun"],
    "harsh_overhead": ["harsh", "overhead", "noon", "midday", "studio harsh"],
    "moody_blue": ["moody", "blue", "cool", "night", "dim"],
    "studio_fill": ["studio", "fill", "neutral", "even"],
    "dawn": ["dawn", "morning", "sunrise", "pink", "first light"],
}
