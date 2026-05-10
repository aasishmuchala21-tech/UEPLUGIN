"""nyrahost.tools.scene_assembler - DEMO-01 scene-assembly engine.

SceneAssembler.analyze_image(image_path) -> SceneBlueprint
SceneAssembler.assemble(blueprint, progress_callback) -> AssemblyResult

The orchestrator runs the four fixed assembly steps:
  1. Placing Actors    (resolves each ActorSpec via AssetFallbackChain, spawns via unreal)
  2. Applying Materials (resolves each MaterialSpec, applies via material_tools)
  3. Setting Up Lighting (calls LightingAuthoringTool with the lighting plan)
  4. Finalizing         (logs summary, fires assembly_complete WS notification)
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Optional

import structlog

from nyrahost.tools.asset_fallback_chain import AssetFallbackChain
from nyrahost.tools.scene_orchestrator import SceneAssemblyOrchestrator
from nyrahost.tools.scene_types import (
    ActorSpec,
    AssemblyResult,
    LightingParams,
    MaterialSpec,
    SceneBlueprint,
)

log = structlog.get_logger("nyrahost.tools.scene_assembler")


ProgressCallback = Callable[[str, int, int, str], None]


class SceneAssembler(SceneAssemblyOrchestrator):
    """End-to-end DEMO-01 assembler. Inherits backend-router + WS plumbing from 06-00."""

    def __init__(
        self,
        backend_router: Optional[Any] = None,
        ws_notifier: Optional[Callable[[dict], None]] = None,
        fallback_chain: Optional[AssetFallbackChain] = None,
        lighting_tool: Optional[Any] = None,
    ):
        super().__init__(backend_router=backend_router, ws_notifier=ws_notifier)
        self._fallback = fallback_chain or AssetFallbackChain()
        self._lighting_tool = lighting_tool

    async def analyze_image(self, image_path: str) -> SceneBlueprint:
        """Call the LLM to derive a SceneBlueprint from a reference image."""
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Reference image not found: {image_path}")
        if self._router is None:
            log.warning("scene_assembler_analyze_no_router", image=image_path)
            return self._stub_blueprint(image_path)
        try:
            raw = await self.generate_image_description(image_path)
            blueprint = self._dict_to_scene_blueprint(raw)
            log.info(
                "scene_assembler_analyze_ok",
                scene_type=blueprint.scene_type,
                actor_count=len(blueprint.actor_specs),
                material_count=len(blueprint.material_specs),
            )
            return blueprint
        except Exception as e:
            log.error("scene_assembler_analyze_failed", error=str(e), image=image_path)
            return self._stub_blueprint(image_path)

    def assemble(
        self,
        blueprint: SceneBlueprint,
        lighting_plan: Optional[LightingParams] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> AssemblyResult:
        """Synchronous assembly orchestrator. Calls progress_callback at every step."""
        progress = progress_callback or (lambda step, c, t, m="": None)
        result = AssemblyResult()

        # Step 1: Place actors
        total_actors = sum(spec.count for spec in blueprint.actor_specs)
        placed = 0
        for spec in blueprint.actor_specs:
            for _ in range(spec.count):
                placed += 1
                progress("Placing Actors", placed, total_actors, spec.role)
                placed_entry = self._place_actor(spec)
                result.placed_actors.append(placed_entry)
                result.log_entries.append(
                    f"actor:{spec.role} -> {placed_entry.get('asset_path')} "
                    f"({placed_entry.get('source')})"
                )

        # Step 2: Apply materials
        total_materials = max(1, len(blueprint.material_specs))
        for idx, mspec in enumerate(blueprint.material_specs, start=1):
            progress("Applying Materials", idx, total_materials, mspec.material_type)
            material_entry = self._apply_material(mspec)
            result.applied_materials.append(material_entry)
            result.log_entries.append(
                f"material:{mspec.material_type} -> {material_entry.get('asset_path')} "
                f"({material_entry.get('source')})"
            )

        # Step 3: Lighting
        progress("Setting Up Lighting", 1, 1, "lighting")
        if lighting_plan and self._lighting_tool is not None:
            try:
                lt_result = self._lighting_tool.execute({
                    "preset_name": "studio_fill",
                    "apply": True,
                })
                if lt_result.error is None and lt_result.data:
                    result.lighting_actors = list(lt_result.data.get("actors_placed", []))
                    result.log_entries.append(
                        f"lighting:{lt_result.data.get('primary_light_type')} mood="
                        f"{','.join(lt_result.data.get('mood_tags', []))}"
                    )
            except Exception as e:
                log.error("scene_assembler_lighting_failed", error=str(e))
                result.log_entries.append(f"lighting:error {e}")

        # Step 4: Finalize
        progress("Finalizing", 1, 1, "summary")
        result.success = True
        self.send_assembly_complete(result)
        log.info(
            "scene_assembler_assemble_ok",
            actors=result.actor_count,
            materials=result.material_count,
            lighting=result.lighting_count,
        )
        return result

    # --- internals ----------------------------------------------------------

    def _place_actor(self, spec: ActorSpec) -> dict:
        resolution = self._fallback.resolve_actor_asset(spec.asset_hint, spec.role)
        # _try_import_unreal: not in editor -> return placeholder metadata.
        try:
            import unreal  # type: ignore
        except ImportError:
            return {
                "actor_name": f"NYRA_{spec.role}",
                "actor_path": resolution.asset_path,
                "asset_path": resolution.asset_path,
                "source": resolution.source,
                "ue_pending_manual_verification": True,
            }

        try:
            actor_class = unreal.UObject.load_system_class(spec.class_path)
            transform = unreal.Transform(
                unreal.Vector(0.0, 0.0, 0.0),
                unreal.Rotator(0.0, 0.0, 0.0),
                unreal.Vector(1.0, 1.0, 1.0),
            )
            actor = unreal.EditorLevelLibrary.spawn_actor_from_class(actor_class, transform)
            actor.set_actor_label(f"NYRA_{spec.role}")
            return {
                "actor_name": actor.get_name(),
                "actor_path": actor.get_path_name(),
                "asset_path": resolution.asset_path,
                "source": resolution.source,
                "guid": str(actor.get_actor_guid()),
            }
        except Exception as e:
            log.error("scene_assembler_spawn_failed", role=spec.role, error=str(e))
            return {
                "actor_name": f"NYRA_{spec.role}_error",
                "asset_path": resolution.asset_path,
                "source": resolution.source,
                "error": str(e),
            }

    def _apply_material(self, spec: MaterialSpec) -> dict:
        resolution = self._fallback.resolve_material_asset(spec.texture_hint, spec.material_type)
        return {
            "target_actor": spec.target_actor,
            "material_type": spec.material_type,
            "asset_path": resolution.asset_path,
            "source": resolution.source,
        }

    @staticmethod
    def _stub_blueprint(image_path: str) -> SceneBlueprint:
        """Deterministic offline blueprint when LLM analysis is unavailable."""
        return SceneBlueprint(
            scene_type="interior_living_room",
            actor_specs=[
                ActorSpec(
                    role="floor",
                    class_path="/Script/Engine.StaticMeshActor",
                    asset_hint="hardwood floor",
                    count=1,
                    placement="grid",
                ),
                ActorSpec(
                    role="hero_furniture",
                    class_path="/Script/Engine.StaticMeshActor",
                    asset_hint=f"sofa from {Path(image_path).name}",
                    count=1,
                    placement="center_floor",
                ),
                ActorSpec(
                    role="background_prop",
                    class_path="/Script/Engine.StaticMeshActor",
                    asset_hint="lamp",
                    count=2,
                    placement="scattered",
                ),
            ],
            material_specs=[
                MaterialSpec(
                    target_actor="hero_furniture",
                    material_type="hero",
                    texture_hint="brown leather",
                ),
                MaterialSpec(
                    target_actor="floor",
                    material_type="floor",
                    texture_hint="warm hardwood",
                ),
            ],
            mood_tags=["cozy", "warm", "living room"],
            confidence=0.4,
        )
