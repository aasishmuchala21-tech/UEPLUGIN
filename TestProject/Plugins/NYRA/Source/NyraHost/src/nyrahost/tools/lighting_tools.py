"""nyrahost.tools.lighting_tools - SCENE-01 lighting authoring MCP tools.

LightingAuthoringTool (nyra_lighting_authoring) configures UE lights, atmosphere,
and post-process from a natural-language prompt, reference image, or named
preset. LightingDryRunTool (nyra_lighting_dry_run_preview) emits a WS preview
notification without spawning permanent actors.

Threat mitigations:
- T-06-01: image paths validated via Path.exists() inside LightingLLMParser.
- T-06-02: every spawned actor is labeled with the NYRA_ prefix so the user
  can `Ctrl+Z` / mass-delete the entire NYRA contribution.
- T-06-03: NL prompts flow only to the LLM, never to a direct Unreal command.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Optional

import structlog

from nyrahost.tools.base import NyraTool, NyraToolResult, run_async_safely
from nyrahost.tools.scene_llm_parser import LightingLLMParser
from nyrahost.tools.scene_types import LIGHTING_PRESETS, LightingParams

log = structlog.get_logger("nyrahost.tools.lighting_tools")


# WR-05: single source of truth for the preset library lives in scene_types.
# Keep the local _PRESETS alias to minimize churn at call sites in this file.
_PRESETS: dict[str, LightingParams] = LIGHTING_PRESETS


_LIGHT_CLASS = {
    "directional": "/Script/Engine.DirectionalLight",
    "spot": "/Script/Engine.SpotLight",
    "point": "/Script/Engine.PointLight",
    "rect": "/Script/Engine.RectLight",
    "sky": "/Script/Engine.SkyLight",
}


def _try_import_unreal():
    """Return the unreal module if running inside UE editor, else None."""
    try:
        import unreal  # type: ignore
        return unreal
    except ImportError:
        return None


class LightingAuthoringTool(NyraTool):
    """nyra_lighting_authoring — primary SCENE-01 entry point."""

    name = "nyra_lighting_authoring"
    description = (
        "Configure scene lighting in the current UE level: directional/point/spot/rect/sky lights, "
        "SkyAtmosphere, VolumetricCloud, ExponentialHeightFog, PostProcessVolume, and exposure curves. "
        "Use 'reference_image_path' to have Claude analyze a reference image and derive lighting params. "
        "Use 'apply' = false for a dry-run preview before committing."
    )
    parameters = {
        "type": "object",
        "properties": {
            "nl_prompt": {
                "type": "string",
                "description": "Natural-language lighting description, e.g. 'golden hour', 'harsh overhead studio'.",
            },
            "reference_image_path": {
                "type": "string",
                "description": "Absolute path to a reference image. If provided, nl_prompt is ignored.",
            },
            "preset_name": {
                "type": "string",
                "description": "Named preset: golden_hour | harsh_overhead | moody_blue | studio_fill | dawn",
            },
            "lighting_params_json": {
                "type": "string",
                "description": "JSON string of a fully-formed LightingParams (used by SceneAssembler to forward an upstream plan).",
            },
            "apply": {
                "type": "boolean",
                "default": True,
                "description": "If False, dry-run preview only (no actors placed).",
            },
        },
    }

    def __init__(
        self,
        backend_router: Optional[Any] = None,
        ws_notifier: Optional[Callable[[dict], None]] = None,
    ):
        self._router = backend_router
        self._ws_notifier = ws_notifier or (lambda msg: None)

    def execute(self, params: dict) -> NyraToolResult:
        try:
            lp = self._resolve_lighting_params(params)
        except FileNotFoundError as e:
            return NyraToolResult.err(f"[-32030] {e}")
        except ValueError as e:
            return NyraToolResult.err(f"[-32030] {e}")

        if params.get("apply", True):
            actors_placed = self._apply_lighting_params(lp)
            log.info("lighting_applied", actors=len(actors_placed), mood_tags=lp.mood_tags)
            return NyraToolResult.ok({
                "actors_placed": actors_placed,
                "actor_count": len(actors_placed),
                "mood_tags": lp.mood_tags,
                "primary_light_type": lp.primary_light_type,
                "exposure_compensation": lp.exposure_compensation,
                "message": (
                    f"Lighting applied: {lp.primary_light_type} with mood "
                    f"{', '.join(lp.mood_tags) if lp.mood_tags else 'neutral'}."
                ),
            })
        self._send_dry_run_notification(lp)
        return NyraToolResult.ok({
            "dry_run": True,
            "mood_tags": lp.mood_tags,
            "primary_light_type": lp.primary_light_type,
            "message": "Dry-run preview active. Click 'Apply Lighting' to commit.",
        })

    # --- Resolution ---------------------------------------------------------

    def _resolve_lighting_params(self, params: dict) -> LightingParams:
        if params.get("lighting_params_json"):
            try:
                d = json.loads(params["lighting_params_json"])
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid lighting_params_json: {e}")
            return LightingParams.from_dict(d)
        if params.get("reference_image_path"):
            parser = LightingLLMParser(backend_router=self._router)
            return run_async_safely(parser.parse_from_image(params["reference_image_path"]))
        if params.get("preset_name"):
            return self._preset_to_params(params["preset_name"])
        if params.get("nl_prompt"):
            parser = LightingLLMParser(backend_router=self._router)
            return run_async_safely(parser.parse_from_text(params["nl_prompt"]))
        raise ValueError("Either nl_prompt, reference_image_path, preset_name, or lighting_params_json must be provided.")

    @staticmethod
    def _preset_to_params(preset_name: str) -> LightingParams:
        # WR-04: don't silently substitute studio_fill for typos. The dry-run
        # tool and the apply tool both pass through here, so a mistyped
        # preset would otherwise quietly produce the wrong lighting and
        # report "Lighting applied" as if everything matched.
        if preset_name not in _PRESETS:
            raise ValueError(
                f"Unknown lighting preset '{preset_name}'. "
                f"Valid: {sorted(_PRESETS)}"
            )
        return _PRESETS[preset_name]

    # --- Application --------------------------------------------------------

    def _apply_lighting_params(self, lp: LightingParams) -> list[dict]:
        unreal = _try_import_unreal()
        if unreal is None:
            log.warning("lighting_apply_no_unreal", reason="not_in_editor")
            return [{
                "actor_name": f"NYRA_Primary_{lp.primary_light_type}",
                "actor_path": f"/Engine/Transient.NYRA_Primary_{lp.primary_light_type}",
                "ue_pending_manual_verification": True,
            }]

        placed: list[dict] = []

        primary_class_path = _LIGHT_CLASS.get(lp.primary_light_type, _LIGHT_CLASS["directional"])
        placed.append(self._spawn_actor(
            unreal,
            class_name=primary_class_path,
            label=f"NYRA_Primary_{lp.primary_light_type}",
            location=(0.0, 0.0, 500.0),
            rotation=lp.primary_direction,
        ))

        if lp.fill_light_type:
            fill_class_path = _LIGHT_CLASS.get(lp.fill_light_type, _LIGHT_CLASS["point"])
            placed.append(self._spawn_actor(
                unreal,
                class_name=fill_class_path,
                label=f"NYRA_Fill_{lp.fill_light_type}",
                location=(200.0, 0.0, 200.0),
                rotation=(0.0, 0.0, 0.0),
            ))

        if lp.use_sky_atmosphere:
            placed.append(self._spawn_actor(
                unreal,
                # WR-07: SkyAtmosphere actor lives at /Script/Engine.SkyAtmosphere
                # in 5.4-5.7. Confirmed actor class.
                class_name="/Script/Engine.SkyAtmosphere",
                label="NYRA_SkyAtmosphere",
            ))
        if lp.use_volumetric_cloud:
            placed.append(self._spawn_actor(
                unreal,
                class_name="/Script/Engine.VolumetricCloud",
                label="NYRA_VolumetricCloud",
            ))
        if lp.use_exponential_height_fog:
            placed.append(self._spawn_actor(
                unreal,
                # WR-07: actor class is ExponentialHeightFog (the *Actor* suffix
                # variant in older docs is the C++ symbol AExponentialHeightFog;
                # the reflected actor path that load_system_class resolves is
                # /Script/Engine.ExponentialHeightFog in UE 5.4-5.7).
                class_name="/Script/Engine.ExponentialHeightFog",
                label="NYRA_ExpHeightFog",
            ))
        if lp.use_post_process:
            placed.append(self._spawn_actor(
                unreal,
                class_name="/Script/Engine.PostProcessVolume",
                label="NYRA_PostProcessVolume",
            ))
        return placed

    @staticmethod
    def _spawn_actor(unreal, class_name: str, label: str,
                     location: tuple[float, float, float] = (0.0, 0.0, 0.0),
                     rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> dict:
        actor_class = unreal.UObject.load_system_class(class_name)
        transform = unreal.Transform(
            unreal.Vector(*location),
            unreal.Rotator(*rotation),
            unreal.Vector(1.0, 1.0, 1.0),
        )
        # WR-07: EditorLevelLibrary is deprecated in UE 5.5+. Prefer
        # EditorActorSubsystem.spawn_actor_from_class. Fall back to the legacy
        # API on UE 5.4 where the subsystem may not yet expose the method.
        actor = None
        get_subsystem = getattr(unreal, "get_editor_subsystem", None)
        editor_actor_subsystem_cls = getattr(unreal, "EditorActorSubsystem", None)
        if get_subsystem and editor_actor_subsystem_cls:
            try:
                subsystem = get_subsystem(editor_actor_subsystem_cls)
                if subsystem is not None:
                    actor = subsystem.spawn_actor_from_class(actor_class, transform.translation)
            except Exception:
                actor = None
        if actor is None:
            actor = unreal.EditorLevelLibrary.spawn_actor_from_class(actor_class, transform)
        actor.set_actor_label(label)
        return {
            "actor_name": actor.get_name(),
            "actor_path": actor.get_path_name(),
            "guid": str(actor.get_actor_guid()),
        }

    # --- WS notifications ---------------------------------------------------

    def _send_dry_run_notification(self, lp: LightingParams) -> None:
        msg = {
            "type": "dry_run_preview",
            "primary_light_type": lp.primary_light_type,
            "mood_tags": lp.mood_tags,
            "lighting_params": lp.to_ue_params(),
        }
        try:
            self._ws_notifier(msg)
        except Exception as e:  # WS failures must never escape into UE
            log.warning("lighting_dry_run_ws_failed", error=str(e))


class LightingDryRunTool(NyraTool):
    """nyra_lighting_dry_run_preview — viewport hover preview, no actor spawn."""

    name = "nyra_lighting_dry_run_preview"
    description = (
        "Preview a lighting configuration in the UE viewport without placing actors. "
        "Triggered by hovering a preset card in SNyraLightingSelector."
    )
    parameters = {
        "type": "object",
        "properties": {
            "preset_name": {"type": "string"},
            "lighting_params_json": {
                "type": "string",
                "description": "JSON string of LightingParams if custom (not from preset).",
            },
        },
    }

    def __init__(self, ws_notifier: Optional[Callable[[dict], None]] = None):
        self._ws_notifier = ws_notifier or (lambda msg: None)

    def execute(self, params: dict) -> NyraToolResult:
        if params.get("preset_name"):
            try:
                lp = LightingAuthoringTool._preset_to_params(params["preset_name"])
            except ValueError as e:
                return NyraToolResult.err(f"[-32030] {e}")
        elif params.get("lighting_params_json"):
            try:
                d = json.loads(params["lighting_params_json"])
            except json.JSONDecodeError as e:
                return NyraToolResult.err(f"[-32030] Invalid lighting_params_json: {e}")
            lp = LightingParams.from_dict(d)
        else:
            return NyraToolResult.err("[-32030] Either preset_name or lighting_params_json must be provided.")

        msg = {
            "type": "dry_run_preview",
            "primary_light_type": lp.primary_light_type,
            "mood_tags": lp.mood_tags,
            "lighting_params": lp.to_ue_params(),
        }
        try:
            self._ws_notifier(msg)
        except Exception as e:
            log.warning("lighting_dry_run_ws_failed", error=str(e))
        return NyraToolResult.ok({"dry_run": True, "preset": params.get("preset_name", "custom")})
