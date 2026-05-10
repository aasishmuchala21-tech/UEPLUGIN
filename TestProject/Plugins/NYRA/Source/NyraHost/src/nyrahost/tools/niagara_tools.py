"""nyrahost.tools.niagara_tools — PARITY-05 Niagara authoring mutators.

Three Phase 4-shape mutators that reproduce Aura's documented GPU sprite +
ribbon emitter examples (PATTERNS.md §"Per-Plan §PARITY-05"):

  - nyra_niagara_create_system          : create UNiagaraSystem asset
  - nyra_niagara_add_emitter            : add emitter from a template
                                           (sim_target = "cpu" | "gpu" -- T-08-04)
  - nyra_niagara_set_module_parameter   : scalar / vector module-param set
                                           with BL-06 readback verification

Tool shape mirrors `material_tools.MaterialCreateMICTool` (asset create)
and `MaterialSetParamTool` (scalar/vector parameter set + readback). Per
LOCKED-03 every mutator wraps:
  - BL-04 session_transaction(...)         (Ctrl+Z reverts NYRA changes)
  - BL-05 idempotent_lookup / _record      (dedup repeated tool calls)
  - BL-06 verify_post_condition(...)       (re-fetch + isinstance + scalar
                                            readback within 1e-4)
  - BL-12 isinstance-check before mutation (refuse wrong asset class)

For the module-parameter set/readback the Python `unreal.*` bindings do
not reflect the Niagara editor stack-API cleanly on UE 5.4-5.7, so the
helper class `unreal.NyraNiagaraHelper` (C++ UCLASS at
`NyraEditor/Public/ToolHelpers/NyraNiagaraHelper.h`) is the actual
mutation surface. The Python tool layer translates the LLM-friendly
schema into that helper's calls.

T-08-01 graceful degradation: every tool short-circuits with
`NyraToolResult.err("not_supported_on_this_ue_version: ...")` when the
required `unreal.*` symbol is missing, rather than aborting the plan.
The Wave-0 symbol survey (`wave-0-symbol-survey/08-05-WAVE-0-PLAN.md`)
identifies bad versions for `KNOWN_NIAGARA_BAD_VERSIONS` below.
"""
from __future__ import annotations

from typing import Any

import structlog

try:
    import unreal  # type: ignore
    HAS_UNREAL = True
except ImportError:
    HAS_UNREAL = False

from nyrahost.tools.base import (
    NyraTool,
    NyraToolResult,
    idempotent_lookup,
    idempotent_record,
    session_transaction,
    verify_post_condition,
)

log = structlog.get_logger("nyrahost.tools.niagara_tools")

__all__ = [
    "NiagaraCreateSystemTool",
    "NiagaraAddEmitterTool",
    "NiagaraSetModuleParameterTool",
]


# ---------------------------------------------------------------------------
# UE-version compatibility (T-08-01)
# ---------------------------------------------------------------------------
#
# Populated by the Wave-0 symbol survey on each UE version. If an operator
# discovers that `unreal.NiagaraSystemFactoryNew` (or sibling symbols) is
# absent on a shipped engine version, they add `"5.X"` here and the three
# tools below short-circuit with `not_supported_on_this_ue_version`.
# ---------------------------------------------------------------------------

KNOWN_NIAGARA_BAD_VERSIONS: set[str] = set()


# ---------------------------------------------------------------------------
# Symbol resolvers
# ---------------------------------------------------------------------------


def _resolve_factory():
    """Resolve `unreal.NiagaraSystemFactoryNew` -- the asset factory class.

    Returns None when `unreal` is not importable (test path) or the symbol
    is not reflected on the running UE build (T-08-01 fallback).
    """
    if not HAS_UNREAL:
        return None
    return getattr(unreal, "NiagaraSystemFactoryNew", None)


def _resolve_system_class():
    """Resolve `unreal.NiagaraSystem`, used for asset-create + isinstance check."""
    if not HAS_UNREAL:
        return None
    return getattr(unreal, "NiagaraSystem", None)


def _resolve_helper():
    """Resolve `unreal.NyraNiagaraHelper` (the C++ UCLASS shipped by Plan 08-05).

    Returns None when NyraEditor has not been recompiled with the helper
    present (e.g. on a clean checkout where the C++ file was added but the
    editor binary is stale).
    """
    if not HAS_UNREAL:
        return None
    return getattr(unreal, "NyraNiagaraHelper", None)


def _load_niagara_system(path: str) -> Any:
    """Defensive lookup + isinstance check (BL-12 mirror of material_tools.py:65-72).

    Returns the asset on success, or None on:
      - asset path does not resolve
      - asset resolves but is not a `unreal.NiagaraSystem`
      - `unreal` not importable (test path)
    """
    if not HAS_UNREAL:
        return None
    NiagaraSystem = _resolve_system_class()
    if NiagaraSystem is None:
        return None
    try:
        asset = unreal.EditorAssetLibrary.load_asset(path)
    except Exception:
        return None
    if asset is None:
        return None
    # BL-12: refuse mutation when the LLM passes the wrong asset class.
    if not isinstance(asset, NiagaraSystem):
        return None
    return asset


# ---------------------------------------------------------------------------
# nyra_niagara_create_system
# ---------------------------------------------------------------------------

class NiagaraCreateSystemTool(NyraTool):
    """Create a new UNiagaraSystem asset at the given content path.

    Analog: `MaterialCreateMICTool` (material_tools.py:283-325) -- asset
    create with isinstance check + BL-04/05/06 envelope.
    """

    name = "nyra_niagara_create_system"
    description = "Create a new UNiagaraSystem asset at the given content path."
    parameters = {
        "type": "object",
        "properties": {
            "asset_path": {
                "type": "string",
                "description": (
                    "UE asset path, e.g. '/Game/VFX/NS_MyEffect'. The package "
                    "directory is the substring up to the final '/'; the asset "
                    "name is everything after."
                ),
            },
        },
        "required": ["asset_path"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        # BL-05 -- short-circuit duplicate calls.
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        if not HAS_UNREAL:
            return NyraToolResult.err(
                "unreal module unavailable (test path or sidecar not in editor)"
            )

        asset_path = params.get("asset_path")
        if not isinstance(asset_path, str) or "/" not in asset_path:
            return NyraToolResult.err(
                f"asset_path must include a '/Game/...' package path, got: {asset_path!r}"
            )

        Factory = _resolve_factory()
        SystemCls = _resolve_system_class()
        if Factory is None or SystemCls is None:
            return NyraToolResult.err(
                "not_supported_on_this_ue_version: "
                "unreal.NiagaraSystemFactoryNew or unreal.NiagaraSystem is not "
                "reflected on this UE build"
            )

        # BL-04 -- wrap mutation in editor transaction (Ctrl+Z reverts).
        with session_transaction(f"NYRA: {self.name}"):
            try:
                factory = Factory()
                asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
                pkg_path, pkg_name = asset_path.rsplit("/", 1)
                ns = asset_tools.create_asset(pkg_name, pkg_path, SystemCls, factory)
                if ns is None:
                    return NyraToolResult.err(
                        f"create_asset returned None for {asset_path}"
                    )
                unreal.EditorAssetLibrary.save_asset(asset_path)
            except Exception as e:
                log.error("niagara_create_system_failed",
                          asset_path=asset_path, error=str(e))
                return NyraToolResult.err(f"failed: {e}")

            # BL-06 -- post-condition: re-load + isinstance check.
            err = verify_post_condition(
                f"{self.name}({asset_path})",
                lambda: _load_niagara_system(asset_path) is not None,
            )
            if err:
                return NyraToolResult.err(err)

        log.info("niagara_system_created", asset_path=asset_path)
        result = {"asset_path": asset_path}
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)


# ---------------------------------------------------------------------------
# nyra_niagara_add_emitter
# ---------------------------------------------------------------------------

class NiagaraAddEmitterTool(NyraTool):
    """Add an emitter from a template (sprite / ribbon / mesh) to a system.

    Per T-08-04 the `sim_target` parameter has enum `["cpu", "gpu"]`; both
    paths are part of the parity bar. The actual GPU shader compile happens
    inside the editor when the system is opened/saved -- this tool only
    creates the emitter handle and tags it with the requested sim target.

    Analog: a hybrid of `MaterialCreateMICTool` (asset create shape) and
    `MaterialSetParamTool` (post-condition isinstance-check). Mutation is
    delegated to `unreal.NyraNiagaraHelper.add_emitter_from_template`
    because UE Python doesn't reflect the editor-side stack API for
    emitter handles.
    """

    name = "nyra_niagara_add_emitter"
    description = (
        "Add an emitter from a template (sprite / ribbon / mesh) to an existing "
        "Niagara system. Both CPU and GPU sim targets are supported."
    )
    parameters = {
        "type": "object",
        "properties": {
            "system_path": {
                "type": "string",
                "description": "UE asset path of the target Niagara system.",
            },
            "template_path": {
                "type": "string",
                "description": (
                    "Niagara emitter template, e.g. "
                    "'/Niagara/Templates/Sprite/SpriteBurst' or "
                    "'/Niagara/Templates/Ribbon/Ribbon'."
                ),
            },
            "sim_target": {
                "type": "string",
                "enum": ["cpu", "gpu"],
                "default": "cpu",
                "description": (
                    "T-08-04 -- 'gpu' selects ENiagaraSimTarget::GPUComputeSim; "
                    "'cpu' selects ENiagaraSimTarget::CPUSim. Default: cpu."
                ),
            },
            "handle_name": {
                "type": "string",
                "description": "Display name for the new emitter handle.",
            },
        },
        "required": ["system_path", "template_path", "handle_name"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        if not HAS_UNREAL:
            return NyraToolResult.err(
                "unreal module unavailable (test path or sidecar not in editor)"
            )

        system_path     = params.get("system_path")
        template_path   = params.get("template_path")
        handle_name     = params.get("handle_name")
        sim_target      = params.get("sim_target", "cpu")

        if not isinstance(system_path, str) or not system_path:
            return NyraToolResult.err("system_path is required")
        if not isinstance(template_path, str) or not template_path:
            return NyraToolResult.err("template_path is required")
        if not isinstance(handle_name, str) or not handle_name:
            return NyraToolResult.err("handle_name is required")
        if sim_target not in ("cpu", "gpu"):
            return NyraToolResult.err(
                f"sim_target must be 'cpu' or 'gpu', got: {sim_target!r}"
            )

        Helper = _resolve_helper()
        if Helper is None:
            return NyraToolResult.err(
                "not_supported_on_this_ue_version: "
                "unreal.NyraNiagaraHelper is not reflected -- recompile "
                "NyraEditor with the Plan 08-05 C++ helper present."
            )

        with session_transaction(f"NYRA: {self.name}"):
            try:
                ns = _load_niagara_system(system_path)
                if ns is None:
                    return NyraToolResult.err(
                        f"NiagaraSystem not found or wrong asset class: {system_path}"
                    )
                handle = Helper.add_emitter_from_template(
                    ns,
                    unreal.Name(template_path),
                    unreal.Name(sim_target),
                    unreal.Name(handle_name),
                )
                if not handle:
                    return NyraToolResult.err(
                        f"AddEmitterFromTemplate returned empty handle "
                        f"(template={template_path}, sim_target={sim_target})"
                    )
                unreal.EditorAssetLibrary.save_asset(system_path)
            except Exception as e:
                log.error("niagara_add_emitter_failed",
                          system_path=system_path,
                          template_path=template_path,
                          sim_target=sim_target,
                          error=str(e))
                return NyraToolResult.err(f"failed: {e}")

            err = verify_post_condition(
                f"{self.name}({system_path})",
                lambda: _load_niagara_system(system_path) is not None,
            )
            if err:
                return NyraToolResult.err(err)

        log.info("niagara_emitter_added",
                 system_path=system_path,
                 handle=str(handle),
                 sim_target=sim_target)
        result = {
            "system_path": system_path,
            "handle_name": str(handle),
            "sim_target":  sim_target,
            "template_path": template_path,
        }
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)


# ---------------------------------------------------------------------------
# nyra_niagara_set_module_parameter
# ---------------------------------------------------------------------------

class NiagaraSetModuleParameterTool(NyraTool):
    """Set a scalar or vector module parameter on a specific emitter handle.

    Analog: `MaterialSetParamTool` (material_tools.py:124-276) -- the
    scalar branch's BL-06 readback (lines 195-201) is the exact pattern
    used here: re-read the value via `get_scalar_module_parameter` and
    assert `abs(readback - value) < 1e-4`.
    """

    name = "nyra_niagara_set_module_parameter"
    description = (
        "Set a scalar or vector module parameter on a specific emitter handle. "
        "Scalar sets verify via BL-06 readback within 1e-4 tolerance; vector "
        "sets do not have a readback path on UE 5.4 -- the helper's success "
        "return is treated as the post-condition."
    )
    parameters = {
        "type": "object",
        "properties": {
            "system_path":     {"type": "string"},
            "emitter_handle":  {"type": "string"},
            "parameter_name":  {"type": "string"},
            "value_kind":      {"type": "string", "enum": ["scalar", "vector"]},
            "scalar_value":    {"type": "number"},
            "vector_value": {
                "type": "object",
                "properties": {
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "z": {"type": "number"},
                },
                "description": "Required when value_kind=='vector'.",
            },
        },
        "required": [
            "system_path", "emitter_handle", "parameter_name", "value_kind",
        ],
    }

    def execute(self, params: dict) -> NyraToolResult:
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        if not HAS_UNREAL:
            return NyraToolResult.err(
                "unreal module unavailable (test path or sidecar not in editor)"
            )

        system_path     = params.get("system_path")
        emitter_handle  = params.get("emitter_handle")
        parameter_name  = params.get("parameter_name")
        value_kind      = params.get("value_kind")

        if not isinstance(system_path, str) or not system_path:
            return NyraToolResult.err("system_path is required")
        if not isinstance(emitter_handle, str) or not emitter_handle:
            return NyraToolResult.err("emitter_handle is required")
        if not isinstance(parameter_name, str) or not parameter_name:
            return NyraToolResult.err("parameter_name is required")
        if value_kind not in ("scalar", "vector"):
            return NyraToolResult.err(
                f"value_kind must be 'scalar' or 'vector', got: {value_kind!r}"
            )
        if value_kind == "scalar" and "scalar_value" not in params:
            return NyraToolResult.err(
                "scalar_value is required when value_kind='scalar'"
            )
        if value_kind == "vector" and "vector_value" not in params:
            return NyraToolResult.err(
                "vector_value is required when value_kind='vector'"
            )

        Helper = _resolve_helper()
        if Helper is None:
            return NyraToolResult.err(
                "not_supported_on_this_ue_version: "
                "unreal.NyraNiagaraHelper is not reflected -- recompile "
                "NyraEditor with the Plan 08-05 C++ helper present."
            )

        scalar_value: float | None = None

        with session_transaction(f"NYRA: {self.name}"):
            try:
                ns = _load_niagara_system(system_path)
                if ns is None:
                    return NyraToolResult.err(
                        f"NiagaraSystem not found or wrong asset class: {system_path}"
                    )

                if value_kind == "scalar":
                    scalar_value = float(params["scalar_value"])
                    ok = Helper.set_scalar_module_parameter(
                        ns,
                        unreal.Name(emitter_handle),
                        unreal.Name(parameter_name),
                        scalar_value,
                    )
                else:
                    vv = params["vector_value"]
                    ok = Helper.set_vector_module_parameter(
                        ns,
                        unreal.Name(emitter_handle),
                        unreal.Name(parameter_name),
                        unreal.Vector(
                            float(vv.get("x", 0.0)),
                            float(vv.get("y", 0.0)),
                            float(vv.get("z", 0.0)),
                        ),
                    )
                if not ok:
                    return NyraToolResult.err(
                        f"Set{'Scalar' if value_kind == 'scalar' else 'Vector'}"
                        f"ModuleParameter returned false "
                        f"(handle={emitter_handle}, param={parameter_name})"
                    )
                unreal.EditorAssetLibrary.save_asset(system_path)
            except Exception as e:
                log.error("niagara_set_module_parameter_failed",
                          system_path=system_path,
                          emitter_handle=emitter_handle,
                          parameter_name=parameter_name,
                          error=str(e))
                return NyraToolResult.err(f"failed: {e}")

            # BL-06 readback -- mirror material_tools.py:195-201. Vector readback
            # is not surfaced by the helper on 5.4-5.7 yet; scalar is the only
            # path we verify via re-fetch.
            if value_kind == "scalar":
                expected = scalar_value
                err = verify_post_condition(
                    f"{self.name}({parameter_name})",
                    lambda: (
                        abs(
                            Helper.get_scalar_module_parameter(
                                ns,
                                unreal.Name(emitter_handle),
                                unreal.Name(parameter_name),
                            ) - expected
                        ) < 1e-4
                    ),
                )
                if err:
                    return NyraToolResult.err(err)

        log.info("niagara_module_parameter_set",
                 system_path=system_path,
                 parameter=parameter_name,
                 value_kind=value_kind)
        result = {
            "system_path":    system_path,
            "emitter_handle": emitter_handle,
            "parameter":      parameter_name,
            "value_kind":     value_kind,
        }
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)
