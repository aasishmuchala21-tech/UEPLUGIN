"""nyrahost.tools.material_tools — ACT-05 material instance MCP tools.

Per Plan 04-06:
  - nyra_material_get_param: read scalar/vector/texture params via UKismetMaterialLibrary
  - nyra_material_set_param: write scalar/vector/texture params; auto-creates MIC
  - nyra_material_create_mic: create a MaterialInstanceDynamic from a parent Material

Phase 0 gate: not phase0-gated — execute fully.
"""
from __future__ import annotations

import structlog
import unreal

from nyrahost.tools.base import NyraTool, NyraToolResult

log = structlog.get_logger("nyrahost.tools.material_tools")

__all__ = ["MaterialGetParamTool", "MaterialSetParamTool", "MaterialCreateMICTool"]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _load_material(path: str):
    try:
        return unreal.EditorAssetLibrary.load_asset(path)
    except Exception:
        return None


# -----------------------------------------------------------------------------
# nyra_material_get_param
# -----------------------------------------------------------------------------

class MaterialGetParamTool(NyraTool):
    name = "nyra_material_get_param"
    description = (
        "Read scalar, vector, or texture parameter values from a Material Instance "
        "(or any material that exposes parameter collections)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "material_path": {
                "type": "string",
                "description": "UE asset path, e.g. '/Game/Materials/M_Hero_C.M_Hero_C'",
            },
            "param_name": {"type": "string"},
            "param_type": {
                "type": "string",
                "enum": ["scalar", "vector", "texture"],
                "description": "Type of parameter to read",
            },
        },
        "required": ["material_path", "param_name", "param_type"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        mat = _load_material(params["material_path"])
        if mat is None:
            return NyraToolResult.err(f"Material not found: {params['material_path']}")

        mat_lib = unreal.KismetMaterialLibrary
        param_name = params["param_name"]
        param_type = params["param_type"]

        try:
            if param_type == "scalar":
                value = mat_lib.get_scalar_parameter_value(mat, param_name)
                return NyraToolResult.ok({
                    "material_path": params["material_path"],
                    "param_name": param_name,
                    "param_type": "scalar",
                    "value": float(value),
                })

            elif param_type == "vector":
                value = mat_lib.get_vector_parameter_value(mat, param_name)
                return NyraToolResult.ok({
                    "material_path": params["material_path"],
                    "param_name": param_name,
                    "param_type": "vector",
                    "r": float(value.r),
                    "g": float(value.g),
                    "b": float(value.b),
                    "a": float(value.a),
                })

            elif param_type == "texture":
                tex = mat_lib.get_texture_parameter_value(mat, param_name)
                return NyraToolResult.ok({
                    "material_path": params["material_path"],
                    "param_name": param_name,
                    "param_type": "texture",
                    "texture_path": tex.get_path_name() if tex else None,
                })

            else:
                return NyraToolResult.err(f"Unknown param_type: {param_type}")

        except Exception as e:
            log.error("material_get_param_failed", path=params["material_path"],
                      param=param_name, error=str(e))
            return NyraToolResult.err(f"Failed to get param '{param_name}': {e}")


# -----------------------------------------------------------------------------
# nyra_material_set_param
# -----------------------------------------------------------------------------

class MaterialSetParamTool(NyraTool):
    name = "nyra_material_set_param"
    description = (
        "Write scalar, vector, or texture parameter values on a Material Instance. "
        "Creates a dynamic Material Instance if the parent material is not already a MIC."
    )
    parameters = {
        "type": "object",
        "properties": {
            "material_path": {"type": "string"},
            "param_name": {"type": "string"},
            "param_type": {"type": "string", "enum": ["scalar", "vector", "texture"]},
            "scalar_value": {"type": "number"},
            "vector_value": {
                "type": "object",
                "properties": {
                    "r": {"type": "number"},
                    "g": {"type": "number"},
                    "b": {"type": "number"},
                    "a": {"type": "number"},
                },
            },
            "texture_value": {
                "type": "string",
                "description": "UE asset path of UTexture2D",
            },
            "actor_path": {
                "type": "string",
                "description": "Optional: apply this MIC to a specific actor's static mesh component",
            },
            "component_index": {
                "type": "integer",
                "default": 0,
                "description": "Mesh component index on the target actor",
            },
        },
        "required": ["material_path", "param_name", "param_type"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        mat = _load_material(params["material_path"])
        if mat is None:
            return NyraToolResult.err(f"Material not found: {params['material_path']}")

        # If material is not a MIC, create one dynamically
        if not isinstance(mat, unreal.MaterialInstance):
            parent = _load_material(params["material_path"])
            mat = unreal.MaterialInstanceDynamic.create(parent)

        mat_lib = unreal.KismetMaterialLibrary
        param_name = params["param_name"]
        param_type = params["param_type"]

        try:
            if param_type == "scalar":
                if "scalar_value" not in params:
                    return NyraToolResult.err("scalar_value is required for param_type=scalar")
                mat_lib.set_scalar_parameter_value(mat, param_name, float(params["scalar_value"]))

            elif param_type == "vector":
                v = params.get("vector_value", {})
                color = unreal.LinearColor(
                    float(v.get("r", 0.0)),
                    float(v.get("g", 0.0)),
                    float(v.get("b", 0.0)),
                    float(v.get("a", 1.0)),
                )
                mat_lib.set_vector_parameter_value(mat, param_name, color)

            elif param_type == "texture":
                if "texture_value" not in params:
                    return NyraToolResult.err("texture_value is required for param_type=texture")
                tex = _load_material(params["texture_value"])
                if tex is None:
                    return NyraToolResult.err(f"Texture not found: {params['texture_value']}")
                mat_lib.set_texture_parameter_value(mat, param_name, tex)

            else:
                return NyraToolResult.err(f"Unknown param_type: {param_type}")

        except Exception as e:
            log.error("material_set_param_failed", path=params["material_path"],
                      param=param_name, error=str(e))
            return NyraToolResult.err(f"Failed to set param '{param_name}': {e}")

        # Optionally apply MIC to an actor's mesh component
        if params.get("actor_path"):
            try:
                actor = unreal.EditorLevelLibrary.get_actor_reference(params["actor_path"])
                idx = params.get("component_index", 0)
                mesh = actor.get_component_by_class(unreal.StaticMeshComponent)
                if mesh:
                    mesh.set_material(idx, mat)
                    log.info("material_applied_to_actor", actor=params["actor_path"], mat=mat.get_path_name())
            except Exception as e:
                log.warning("material_apply_to_actor_failed", actor=params["actor_path"], error=str(e))

        return NyraToolResult.ok({
            "material_path": mat.get_path_name(),
            "param_name": param_name,
            "param_type": param_type,
            "status": "applied",
        })

    # _create_mic logic inlined into execute() — keep separate for clarity
    @staticmethod
    def _create_mic(parent_path: str):
        parent = _load_material(parent_path)
        if parent is None:
            return None
        return unreal.MaterialInstanceDynamic.create(parent)


# -----------------------------------------------------------------------------
# nyra_material_create_mic
# -----------------------------------------------------------------------------

class MaterialCreateMICTool(NyraTool):
    name = "nyra_material_create_mic"
    description = "Create a dynamic Material Instance (MIC) from a parent Material."
    parameters = {
        "type": "object",
        "properties": {
            "parent_material": {
                "type": "string",
                "description": "UE asset path of the parent Material",
            },
            "mic_name": {
                "type": "string",
                "description": "Optional actor label for the new MIC (visible in world outliner)",
            },
        },
        "required": ["parent_material"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        parent = _load_material(params["parent_material"])
        if parent is None:
            return NyraToolResult.err(f"Parent material not found: {params['parent_material']}")

        try:
            mic = unreal.MaterialInstanceDynamic.create(parent)
            if params.get("mic_name"):
                mic.set_actor_label(params["mic_name"])
            log.info("mic_created", mic=mic.get_path_name(), parent=params["parent_material"])
            return NyraToolResult.ok({
                "mic_path": mic.get_path_name(),
                "parent_path": params["parent_material"],
            })
        except Exception as e:
            log.error("mic_create_failed", parent=params["parent_material"], error=str(e))
            return NyraToolResult.err(f"Failed to create MIC: {e}")