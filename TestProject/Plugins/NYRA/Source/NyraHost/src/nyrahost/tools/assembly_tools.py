"""nyrahost.tools.assembly_tools - DEMO-01 nyra_assemble_scene MCP tool.

AssembleSceneTool is the user-facing entry point: takes an image path or
NL prompt, runs SceneAssembler.analyze_image + assemble, streams progress
updates to the Slate panel via the WS notifier, returns an AssemblyResult.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

import structlog

from nyrahost.tools.base import NyraTool, NyraToolResult, run_async_safely
from nyrahost.tools.scene_assembler import SceneAssembler
from nyrahost.tools.scene_llm_parser import LightingLLMParser

log = structlog.get_logger("nyrahost.tools.assembly_tools")


class AssembleSceneTool(NyraTool):
    """nyra_assemble_scene - DEMO-01 image-to-scene entry point."""

    name = "nyra_assemble_scene"
    description = (
        "Assemble a UE scene from a reference image: analyze the image, place 5-20 "
        "actors using the user's library first (Meshy / ComfyUI fallback), apply hero "
        "materials, configure lighting. Streams assembly_progress notifications to the "
        "Slate panel through every step."
    )
    parameters = {
        "type": "object",
        "properties": {
            "reference_image_path": {
                "type": "string",
                "description": "Absolute path to the reference image. Required.",
            },
            "lighting_preset": {
                "type": "string",
                "description": "Optional named lighting preset to use directly.",
            },
        },
        "required": ["reference_image_path"],
    }

    def __init__(
        self,
        backend_router: Optional[Any] = None,
        ws_notifier: Optional[Callable[[dict], None]] = None,
        assembler: Optional[SceneAssembler] = None,
    ):
        self._router = backend_router
        self._ws_notifier = ws_notifier or (lambda msg: None)
        self._assembler = assembler or SceneAssembler(
            backend_router=backend_router,
            ws_notifier=ws_notifier,
        )

    def execute(self, params: dict) -> NyraToolResult:
        image_path = params.get("reference_image_path")
        if not image_path:
            return NyraToolResult.err("[-32030] reference_image_path is required.")

        try:
            blueprint = run_async_safely(self._assembler.analyze_image(image_path))
        except FileNotFoundError as e:
            return NyraToolResult.err(f"[-32030] {e}")
        except Exception as e:
            log.error("assemble_scene_analyze_failed", error=str(e), image=image_path)
            return NyraToolResult.err(f"[-32099] Image analysis failed: {e}")

        def _emit_progress(step: str, current: int, total: int, message: str = "") -> None:
            self._ws_notifier({
                "type": "assembly_progress",
                "step": step,
                "current": current,
                "total": total,
                "message": message,
            })

        # CR-02: derive a LightingParams from the same image (or fall back to
        # the rule-based default inside LightingLLMParser if no router) so the
        # assembler honors SC#2 ("match this image's mood") instead of always
        # firing studio_fill.
        lighting_plan = None
        try:
            lighting_plan = run_async_safely(
                LightingLLMParser(backend_router=self._router).parse_from_image(image_path)
            )
        except Exception as e:
            log.warning(
                "assemble_scene_lighting_plan_failed",
                error=str(e),
                image=image_path,
            )

        result = self._assembler.assemble(
            blueprint=blueprint,
            lighting_plan=lighting_plan,
            progress_callback=_emit_progress,
        )

        return NyraToolResult.ok({
            "scene_type": blueprint.scene_type,
            "actor_count": result.actor_count,
            "material_count": result.material_count,
            "lighting_count": result.lighting_count,
            "mood_tags": blueprint.mood_tags,
            "log_entries": result.log_entries,
            "summary": result.to_structured_summary(),
        })
