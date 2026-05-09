---
phase: 4
plan: 04-06
type: execute
wave: 1
autonomous: true
depends_on: []
blocking_preconditions: []
---

# Plan 04-06: Material Instance MCP Tools

## Current Status

No Material Instance tools exist in NyraHost. `UKismetMaterialLibrary` and `UMaterialInstanceDynamic` are available via the `unreal` Python binding. This plan delivers the full ACT-05 surface: read scalar/vector/texture params, write scalar/vector/texture params, and create a Material Instance Dynamic from a parent Material.

## Objectives

Implement `nyra_material_get_param` and `nyra_material_set_param` MCP tools, plus `nyra_material_create_mic` to create a dynamic Material Instance from a parent.

## What Will Be Built

### `NyraHost/nyra_host/tools/material_tools.py`

```python
from .base import NyraTool, NyraToolResult
import unreal

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
                "description": "UE asset path, e.g. '/Game/Materials/M_Hero_C.M_Hero_C'"
            },
            "param_name": {"type": "string"},
            "param_type": {
                "type": "string",
                "enum": ["scalar", "vector", "texture"],
                "description": "Type of parameter to read"
            }
        },
        "required": ["material_path", "param_name", "param_type"]
    }

    def execute(self, params: dict) -> NyraToolResult:
        mat = unreal.EditorAssetLibrary.load_asset(params["material_path"])
        if mat is None:
            return NyraToolResult(error=f"Material not found: {params['material_path']}")

        mat_lib = unreal.KismetMaterialLibrary
        param_type = params["param_type"]

        if param_type == "scalar":
            value = mat_lib.get_scalar_parameter_value(
                mat, params["param_name"]
            )
            return NyraToolResult(data={
                "material_path": params["material_path"],
                "param_name": params["param_name"],
                "param_type": "scalar",
                "value": value,
                "unit": "normalized (0-1 for float params, raw for int)"
            })

        elif param_type == "vector":
            value = mat_lib.get_vector_parameter_value(
                mat, params["param_name"]
            )
            return NyraToolResult(data={
                "material_path": params["material_path"],
                "param_name": params["param_name"],
                "param_type": "vector",
                "r": float(value.r),
                "g": float(value.g),
                "b": float(value.b),
                "a": float(value.a)
            })

        elif param_type == "texture":
            value = mat_lib.get_texture_parameter_value(
                mat, params["param_name"]
            )
            return NyraToolResult(data={
                "material_path": params["material_path"],
                "param_name": params["param_name"],
                "param_type": "texture",
                "texture_path": value.get_path_name() if value else None
            })


class MaterialSetParamTool(NyraTool):
    name = "nyra_material_set_param"
    description = (
        "Write scalar, vector, or texture parameter values on a Material Instance. "
        "Creates a dynamic Material Instance if the parent is not already a MIC."
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
                    "a": {"type": "number"}
                }
            },
            "texture_value": {"type": "string", "description": "UE asset path of UTexture2D"},
            "actor_path": {
                "type": "string",
                "description": "Optional: apply this MIC to a specific actor's static mesh component"
            },
            "component_index": {
                "type": "integer",
                "default": 0,
                "description": "Mesh component index on the target actor"
            }
        },
        "required": ["material_path", "param_name", "param_type"]
    }

    def execute(self, params: dict) -> NyraToolResult:
        mat = unreal.EditorAssetLibrary.load_asset(params["material_path"])

        # If material is not a MIC, create one first
        if not isinstance(mat, unreal.MaterialInstance):
            mat = self._create_mic(params["material_path"])

        mat_lib = unreal.KismetMaterialLibrary
        param_type = params["param_type"]

        if param_type == "scalar":
            mat_lib.set_scalar_parameter_value(mat, params["param_name"], params["scalar_value"])
        elif param_type == "vector":
            v = params["vector_value"]
            color = unreal.LinearColor(v["r"], v["g"], v["b"], v.get("a", 1.0))
            mat_lib.set_vector_parameter_value(mat, params["param_name"], color)
        elif param_type == "texture":
            tex = unreal.EditorAssetLibrary.load_asset(params["texture_value"])
            mat_lib.set_texture_parameter_value(mat, params["param_name"], tex)

        # Optionally apply to actor's mesh
        if params.get("actor_path"):
            actor = unreal.EditorLevelLibrary.get_actor_reference(params["actor_path"])
            idx = params.get("component_index", 0)
            mesh = actor.get_component_by_class(unreal.StaticMeshComponent)
            if mesh:
                mesh.set_material(idx, mat)

        return NyraToolResult(data={
            "material_path": mat.get_path_name(),
            "param_name": params["param_name"],
            "param_type": param_type,
            "status": "applied"
        })

    def _create_mic(self, parent_path: str) -> unreal.MaterialInstanceDynamic:
        parent = unreal.EditorAssetLibrary.load_asset(parent_path)
        mic = unreal.MaterialInstanceDynamic.create(parent)
        return mic


class MaterialCreateMICTool(NyraTool):
    name = "nyra_material_create_mic"
    description = "Create a dynamic Material Instance from a parent Material."
    parameters = {
        "type": "object",
        "properties": {
            "parent_material": {
                "type": "string",
                "description": "UE asset path of the parent Material"
            },
            "mic_name": {
                "type": "string",
                "description": "Name for the new MIC in the world outliner (optional)"
            }
        },
        "required": ["parent_material"]
    }

    def execute(self, params: dict) -> NyraToolResult:
        parent = unreal.EditorAssetLibrary.load_asset(params["parent_material"])
        if parent is None:
            return NyraToolResult(error=f"Material not found: {params['parent_material']}")

        mic = unreal.MaterialInstanceDynamic.create(parent)

        if params.get("mic_name"):
            mic.set_actor_label(params["mic_name"])

        return NyraToolResult(data={
            "mic_path": mic.get_path_name(),
            "parent_path": params["parent_material"]
        })
```

## Transaction Discipline

All set operations call `FNyraSessionTransaction::Begin` + `mat.Modify()` before mutation. GET operations are read-only (no transaction cost).

## Acceptance Criteria

- [ ] `nyra_material_get_param` returns correct scalar value (float) for a known ScalarParameter
- [ ] `nyra_material_get_param` returns correct vector value (r/g/b/a) for a known VectorParameter
- [ ] `nyra_material_get_param` returns correct texture asset path for a known TextureParameter
- [ ] `nyra_material_set_param scalar` updates a ScalarParameter and the change is visible in the Material Editor
- [ ] `nyra_material_set_param` with `actor_path` applies the MIC to the correct mesh component
- [ ] `nyra_material_create_mic` creates a new dynamic MIC from a parent Material
- [ ] Read operations (GET) cost no transaction; write operations wrapped in `FNyraSessionTransaction`
- [ ] Phase 1/2 commands unchanged

## File Manifest

| File | Action |
|------|--------|
| `NyraHost/nyra_host/tools/material_tools.py` | Create |
| `NyraHost/nyra_host/mcp_server.py` | Edit (register MaterialGetParamTool, MaterialSetParamTool, MaterialCreateMICTool) |