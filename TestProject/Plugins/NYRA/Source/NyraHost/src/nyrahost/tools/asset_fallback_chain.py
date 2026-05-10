"""nyrahost.tools.asset_fallback_chain - DEMO-01 asset resolution fallback.

Resolves an actor or material asset by trying, in order:
  1. user library (existing /Game assets via duck-typed library_search callable)
  2. Meshy (3D generation for actors only)
  3. ComfyUI (texture generation for materials only)
  4. placeholder (deterministic /Engine fallback)

The chain never raises - every call returns AssetResolutionResult.
AssetPool from Plan 06-00 is consulted before any external call so
identical (hint, role) tuples short-circuit to the cached result.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

import structlog

from nyrahost.tools.asset_pool import AssetPool
from nyrahost.tools.scene_types import AssetResolutionResult

log = structlog.get_logger("nyrahost.tools.asset_fallback_chain")


PLACEHOLDER_ACTOR_PATH = "/Engine/BasicShapes/Cube.Cube"
PLACEHOLDER_MATERIAL_PATH = "/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"


class AssetFallbackChain:
    """Resolve an asset hint through library -> Meshy -> ComfyUI -> placeholder."""

    def __init__(
        self,
        asset_pool: Optional[AssetPool] = None,
        library_search: Optional[Callable[[str, str], Optional[str]]] = None,
        meshy_tool: Optional[Any] = None,
        comfyui_tool: Optional[Any] = None,
    ):
        self.pool = asset_pool or AssetPool()
        self._library_search = library_search or (lambda hint, role: None)
        self._meshy_tool = meshy_tool
        self._comfyui_tool = comfyui_tool

    def resolve_actor_asset(self, hint: str, role: str) -> AssetResolutionResult:
        """Resolve a 3D actor asset path through the fallback chain."""
        cached = self.pool.get(hint, role)
        if cached is not None:
            return cached

        # Step 1: library
        lib_path = self._library_search(hint, role)
        if lib_path:
            res = AssetResolutionResult(asset_path=lib_path, source="library", quality_score=0.9)
            self.pool.put(hint, role, res)
            log.info("asset_fallback_library_hit", hint=hint, role=role, path=lib_path)
            return res

        # Step 2: Meshy (only if available)
        if self._meshy_tool is not None:
            res = self._call_meshy(hint, role)
            if res is not None:
                self.pool.put(hint, role, res)
                return res

        # Step 4: placeholder (skip 3 — ComfyUI is for materials, not actors)
        res = AssetResolutionResult(
            asset_path=PLACEHOLDER_ACTOR_PATH,
            source="placeholder",
            quality_score=0.3,
        )
        self.pool.put(hint, role, res)
        log.info("asset_fallback_placeholder_actor", hint=hint, role=role)
        return res

    def resolve_material_asset(self, hint: str, role: str) -> AssetResolutionResult:
        """Resolve a material asset path through the fallback chain."""
        cached = self.pool.get(hint, role)
        if cached is not None:
            return cached

        lib_path = self._library_search(hint, role)
        if lib_path:
            res = AssetResolutionResult(asset_path=lib_path, source="library", quality_score=0.9)
            self.pool.put(hint, role, res)
            log.info("asset_fallback_library_hit_material", hint=hint, role=role, path=lib_path)
            return res

        if self._comfyui_tool is not None:
            res = self._call_comfyui(hint, role)
            if res is not None:
                self.pool.put(hint, role, res)
                return res

        res = AssetResolutionResult(
            asset_path=PLACEHOLDER_MATERIAL_PATH,
            source="placeholder",
            quality_score=0.3,
        )
        self.pool.put(hint, role, res)
        log.info("asset_fallback_placeholder_material", hint=hint, role=role)
        return res

    def _call_meshy(self, hint: str, role: str) -> Optional[AssetResolutionResult]:
        try:
            t0 = time.time()
            result = self._meshy_tool.execute({"prompt": hint, "role": role})
            if result.error:
                log.warning("asset_fallback_meshy_error", hint=hint, error=result.error)
                return None
            data = result.data or {}
            asset_path = data.get("asset_path") or data.get("imported_path")
            if not asset_path:
                log.warning("asset_fallback_meshy_no_path", hint=hint, data=list(data.keys()))
                return None
            return AssetResolutionResult(
                asset_path=asset_path,
                source="meshy",
                quality_score=0.75,
                generation_time=time.time() - t0,
            )
        except Exception as e:
            log.error("asset_fallback_meshy_exception", hint=hint, error=str(e))
            return None

    def _call_comfyui(self, hint: str, role: str) -> Optional[AssetResolutionResult]:
        try:
            t0 = time.time()
            result = self._comfyui_tool.execute({"prompt": hint, "role": role})
            if result.error:
                log.warning("asset_fallback_comfyui_error", hint=hint, error=result.error)
                return None
            data = result.data or {}
            asset_path = data.get("asset_path") or data.get("imported_path")
            if not asset_path:
                log.warning("asset_fallback_comfyui_no_path", hint=hint, data=list(data.keys()))
                return None
            return AssetResolutionResult(
                asset_path=asset_path,
                source="comfyui",
                quality_score=0.65,
                generation_time=time.time() - t0,
            )
        except Exception as e:
            log.error("asset_fallback_comfyui_exception", hint=hint, error=str(e))
            return None
