"""nyrahost.tools.scene_orchestrator - Base class for Phase 6 assembly orchestrators.

SceneAssemblyOrchestrator provides:
- Backend router injection (for LLM calls)
- WebSocket notification pattern (for Slate panel updates)
- Progress callback interface (for SNyraProgressBar)

Both AssembleSceneTool (DEMO-01) and LightingAuthoringTool (SCENE-01) inherit from here.
"""
from __future__ import annotations

import structlog
from typing import Any, Callable, Optional

from nyrahost.tools.base import NyraTool, NyraToolResult
from nyrahost.tools.scene_types import (
    ActorSpec,
    AssemblyResult,
    LightingParams,
    MaterialSpec,
    ProgressUpdate,
    SceneBlueprint,
)

log = structlog.get_logger("nyrahost.tools.scene_orchestrator")

ProgressCallback = Callable[[str, int, int, str], None]


class SceneAssemblyOrchestrator:
    """Base orchestrator for scene assembly operations.

    Subclasses must implement:
      _analyze_reference_image(image_path: str) -> SceneBlueprint
      _apply_lighting(params: LightingParams) -> list[dict]

    Provides:
      - Backend router injection
      - WS notification helpers
      - Progress callback handling
    """

    def __init__(
        self,
        backend_router: Optional[Any] = None,
        ws_notifier: Optional[Callable[[dict], None]] = None,
    ):
        self._router = backend_router
        self._ws_notifier = ws_notifier or (lambda msg: None)

    @property
    def router(self) -> Any:
        """Return the backend router. Raises if not set."""
        if self._router is None:
            raise RuntimeError(
                "SceneAssemblyOrchestrator: backend_router not set. "
                "Pass backend_router=... to __init__ or set it before calling LLM methods."
            )
        return self._router

    async def generate_image_description(self, image_path: str) -> dict:
        """Call the backend router to analyze a reference image."""
        log.info("orchestrator_analyze_image", image_path=image_path)
        try:
            result = await self.router.generate_image_description(image_path)
            log.info("orchestrator_image_analysis_complete", scene_type=result.get("scene_type"))
            return result
        except Exception as e:
            log.error("orchestrator_image_analysis_failed", error=str(e))
            raise

    async def generate_lighting_from_image(self, image_path: str) -> LightingParams:
        """Call the backend router to extract lighting parameters from a reference image."""
        log.info("orchestrator_lighting_from_image", image_path=image_path)
        try:
            result = await self.router.generate_lighting_from_image(image_path)
            log.info("orchestrator_lighting_extracted", mood_tags=result.get("mood_tags", []))
            return self._dict_to_lighting_params(result)
        except Exception as e:
            log.error("orchestrator_lighting_extraction_failed", error=str(e))
            raise

    def send_ws_notification(self, msg_type: str, payload: dict) -> None:
        """Send a WebSocket notification to the Slate panel."""
        msg = {"type": msg_type, **payload}
        self._ws_notifier(msg)
        log.debug("orchestrator_ws_notification", msg_type=msg_type, payload_keys=list(payload.keys()))

    def send_progress(self, step: str, current: int, total: int, message: str = "") -> None:
        """Send a progress update to the Slate panel via WS."""
        update = ProgressUpdate(step=step, current=current, total=total, message=message)
        self.send_ws_notification("assembly_progress", update.to_ws_payload())

    def send_assembly_complete(self, result: AssemblyResult) -> None:
        """Send assembly completion notification to Slate panel."""
        summary = result.to_structured_summary()
        self.send_ws_notification("assembly_complete", summary)

    def send_error(self, error_message: str, partial_result: Optional[AssemblyResult] = None) -> None:
        """Send error notification to Slate panel."""
        payload = {
            "error_message": error_message,
        }
        if partial_result:
            payload.update(partial_result.to_structured_summary())
        self.send_ws_notification("assembly_error", payload)

    @staticmethod
    def _dict_to_scene_blueprint(d: dict) -> SceneBlueprint:
        """Convert a raw dict from the LLM to SceneBlueprint dataclass."""
        actor_specs = [ActorSpec(**a) for a in d.get("actor_specs", [])]
        material_specs = [MaterialSpec(**m) for m in d.get("material_specs", [])]
        return SceneBlueprint(
            scene_type=d.get("scene_type", "unknown"),
            actor_specs=actor_specs,
            material_specs=material_specs,
            mood_tags=d.get("mood_tags", []),
            confidence=d.get("confidence", 0.0),
        )

    @staticmethod
    def _dict_to_lighting_params(d: dict) -> LightingParams:
        """Convert a raw dict from the LLM to LightingParams dataclass."""
        primary_color = d.get("primary_color", [1.0, 1.0, 1.0])
        if isinstance(primary_color, list):
            primary_color = tuple(primary_color)  # type: ignore[assignment]
        fog_color = d.get("fog_color", [0.8, 0.85, 1.0])
        if isinstance(fog_color, list):
            fog_color = tuple(fog_color)  # type: ignore[assignment]
        primary_direction = d.get("primary_direction", [0.0, 0.0, 0.0])
        if isinstance(primary_direction, list):
            primary_direction = tuple(primary_direction)  # type: ignore[assignment]
        return LightingParams(
            primary_light_type=d.get("primary_light_type", "directional"),
            primary_intensity=d.get("primary_intensity", 1.0),
            primary_color=primary_color,
            primary_direction=primary_direction,
            primary_temperature_k=d.get("primary_temperature_k", 5500.0),
            use_shadow=d.get("use_shadow", True),
            shadow_cascades=d.get("shadow_cascades", 4),
            fill_light_type=d.get("fill_light_type", ""),
            fill_intensity=d.get("fill_intensity", 0.0),
            use_sky_atmosphere=d.get("use_sky_atmosphere", False),
            use_volumetric_cloud=d.get("use_volumetric_cloud", False),
            cloud_coverage=d.get("cloud_coverage", 0.5),
            use_exponential_height_fog=d.get("use_exponential_height_fog", False),
            fog_density=d.get("fog_density", 0.02),
            fog_height_falloff=d.get("fog_height_falloff", 0.2),
            fog_color=fog_color,
            use_volumetric_fog=d.get("use_volumetric_fog", False),
            volumetric_fog_density=d.get("volumetric_fog_density", 0.1),
            use_post_process=d.get("use_post_process", False),
            exposure_compensation=d.get("exposure_compensation", 0.0),
            contrast=d.get("contrast", 1.0),
            color_saturation=d.get("color_saturation", 1.0),
            prompt=d.get("prompt", ""),
            mood_tags=d.get("mood_tags", []),
            confidence=d.get("confidence", 0.0),
        )
