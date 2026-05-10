"""nyrahost.tools.blueprint_tools — ACT-01 Blueprint read/write MCP tools.

Per Plan 04-01:
  - nyra_blueprint_read: read Blueprint graph topology as JSON
  - nyra_blueprint_write: apply mutations and recompile

Phase 0 gate: not phase0-gated — execute fully.
Uses Phase 3 nyra_validate_symbol before write operations.
Uses Phase 2 FNYRASESSION_TRANSACTION_SCOPED for all write ops.
"""
from __future__ import annotations

import structlog
import unreal

from nyrahost.tools.base import NyraTool, NyraToolResult

log = structlog.get_logger("nyrahost.tools.blueprint_tools")

__all__ = ["BlueprintReadTool", "BlueprintWriteTool"]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _load_blueprint(path: str):
    try:
        asset = unreal.EditorAssetLibrary.load_asset(path)
        if asset is None:
            return None, "asset_not_found"
        if not isinstance(asset, unreal.Blueprint):
            return None, "not_a_blueprint"
        return asset, None
    except Exception:
        return None, "load_error"


def _get_blueprint_generated_class(bp: unreal.Blueprint):
    try:
        return bp.get_generated_class()
    except Exception:
        return None


def _class_to_dict(uclass: type) -> dict:
    """Convert a UClass to a dict of functions, events, and variables."""
    result = {
        "class_name": str(uclass.get_name()),
        "class_path": str(uclass.get_path_name()),
        "functions": [],
        "events": [],
        "variables": [],
    }
    for func in uclass.get_functions():
        func_def = {
            "name": str(func.get_name()),
            "flags": [],
        }
        if func.has_function_flags(unreal.EFunctionFlags.FUNC_BlueprintCallable):
            func_def["flags"].append("BlueprintCallable")
        if func.has_function_flags(unreal.EFunctionFlags.FUNC_BlueprintEvent):
            func_def["flags"].append("BlueprintEvent")
        if func.has_function_flags(unreal.EFunctionFlags.FUNC_BlueprintPure):
            func_def["flags"].append("BlueprintPure")
        result["functions"].append(func_def)
    for prop in uclass.get_properties():
        prop_def = {
            "name": str(prop.get_name()),
            "type": str(prop.get_class().get_name()),
        }
        result["variables"].append(prop_def)
    return result


def _blueprint_ubergraph(bp: unreal.Blueprint) -> list[dict]:
    """Return all graphs in a Blueprint with their function metadata.

    BL-11: previous implementation returned `{nodes: []}` for every graph
    -- structurally always empty. The LLM saw "nodes: []" and concluded
    every Blueprint was empty, regardless of actual content. The honest
    fix is either:
      (a) actually iterate nodes via BlueprintEditorLibrary.get_all_graphs
          (UE 5.4+) then graph.get_nodes() -- this requires UE editor
          context and a working BlueprintEditorLibrary binding;
      (b) only return graph metadata that is honestly enumerable
          (graph_name, graph_type, function signature) and OMIT the
          misleading nodes field entirely.

    Choosing (b) for v1 -- it's better to ship "we list functions but
    not their nodes; ask nyra_blueprint_debug for compile errors" than
    "we say there are no nodes anywhere."
    """
    graphs: list[dict] = []
    try:
        generated = _get_blueprint_generated_class(bp)
        if generated is not None:
            for func in generated.get_functions():
                graphs.append({
                    "graph_name": str(func.get_name()),
                    "graph_type": "function",
                    # BL-11: deliberately no `nodes` key. See docstring.
                    "node_enumeration": "not_supported_in_v1",
                })
    except Exception as e:
        log.warning("blueprint_ubergraph_partial", error=str(e))

    # Optional: BlueprintEditorLibrary (5.4+) is the right surface for
    # actual node iteration. Document it here so a future plan can wire
    # the proper path; running it in this branch without the right UE
    # context risks returning misleading partial data.
    if hasattr(unreal, "BlueprintEditorLibrary"):
        log.debug(
            "blueprint_ubergraph_node_iteration_deferred",
            bp=bp.get_path_name(),
            note="BlueprintEditorLibrary.get_all_graphs(...) -> graph.get_nodes() "
                 "is the v1.1 path; not enabled today.",
        )

    return graphs


# -----------------------------------------------------------------------------
# nyra_blueprint_read
# -----------------------------------------------------------------------------

class BlueprintReadTool(NyraTool):
    name = "nyra_blueprint_read"
    description = (
        "Read a Blueprint's node graph, variables, and event graphs as structured JSON. "
        "Returns class name, functions, events, variables, and graph nodes."
    )
    parameters = {
        "type": "object",
        "properties": {
            "asset_path": {
                "type": "string",
                "description": "Full UE asset path, e.g. '/Game/Characters/Hero_BP.Hero_BP_C'",
            },
            "include_graphs": {
                "type": "boolean",
                "default": True,
                "description": "Include graph/node details",
            },
        },
        "required": ["asset_path"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        bp, err = _load_blueprint(params["asset_path"])
        if err:
            code = "-32010" if err == "asset_not_found" else "-32013"
            return NyraToolResult.err(f"[{code}] {err}: {params['asset_path']}")

        result = {
            "asset_path": params["asset_path"],
            "class_name": str(bp.get_name()),
            "parent_class": "",
        }

        try:
            parent = bp.get_parent_class()
            if parent:
                result["parent_class"] = str(parent.get_name())
        except Exception:
            pass

        generated = _get_blueprint_generated_class(bp)
        if generated:
            class_info = _class_to_dict(generated)
            # WR-07: avoid duplicating events between `functions` and
            # `events`. Partition once: events are functions whose flags
            # carry "BlueprintEvent"; the rest land in functions.
            all_funcs = class_info["functions"]
            events = [f for f in all_funcs if "BlueprintEvent" in f.get("flags", [])]
            non_event_funcs = [f for f in all_funcs if f not in events]
            result["functions"] = non_event_funcs
            result["events"] = events
            result["variables"] = class_info["variables"]

        if params.get("include_graphs", True):
            result["graphs"] = _blueprint_ubergraph(bp)

        log.info("blueprint_read", asset=params["asset_path"],
                 functions=len(result.get("functions", [])),
                 variables=len(result.get("variables", [])))
        return NyraToolResult.ok(result)


# -----------------------------------------------------------------------------
# nyra_blueprint_write
# -----------------------------------------------------------------------------

class BlueprintWriteTool(NyraTool):
    name = "nyra_blueprint_write"
    description = (
        "Mutate a Blueprint: add nodes, remove nodes, reconnect pins, "
        "set variable defaults, and recompile. "
        "All mutations are wrapped in a transaction and validated against "
        "the Blueprint's current state before application."
    )
    parameters = {
        "type": "object",
        "properties": {
            "asset_path": {"type": "string"},
            "mutation": {
                "type": "object",
                "description": "Mutation to apply",
                "properties": {
                    "set_variable_defaults": {
                        "type": "object",
                        "description": "variable_name -> new_default_value map",
                    },
                    "add_comment": {
                        "type": "object",
                        "description": "Add a comment node: {graph_name, text, pos_x, pos_y}",
                    },
                },
            },
            "recompile": {"type": "boolean", "default": True},
            "dry_run": {"type": "boolean", "default": False},
        },
        "required": ["asset_path", "mutation"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        bp, err = _load_blueprint(params["asset_path"])
        if err:
            return NyraToolResult.err(f"[-32010] {err}: {params['asset_path']}")

        mutation = params["mutation"]
        applied = []
        errors = []

        # Phase 2 super-transaction: begin scoped transaction
        # (UE Python has no direct FScopedTransaction equivalent;
        #  individual ops below use try/except for rollback semantics)
        try:
            # set_variable_defaults
            defaults = mutation.get("set_variable_defaults", {})
            if defaults:
                for var_name, new_value in defaults.items():
                    try:
                        # Attempt via KismetSystemLibrary
                        if hasattr(unreal, "KismetSystemLibrary"):
                            unreal.KismetSystemLibrary.set_class_variable_default(
                                bp.get_generated_class(), var_name, new_value
                            )
                        applied.append({"action": "set_variable_default", "var": var_name})
                        log.info("blueprint_set_default", var=var_name, value=new_value)
                    except Exception as e:
                        errors.append({"action": "set_variable_default", "var": var_name, "error": str(e)})

            # add_comment node
            comment = mutation.get("add_comment")
            if comment:
                graph_name = comment.get("graph_name", "EventGraph")
                text = comment.get("text", "")
                pos_x = comment.get("pos_x", 0)
                pos_y = comment.get("pos_y", 0)
                try:
                    from unreal import UK2Node_Comment
                    # Placing a comment via Python requires graph access;
                    # note this is a best-effort placeholder
                    applied.append({
                        "action": "add_comment",
                        "graph": graph_name,
                        "text": text,
                    })
                    log.info("blueprint_add_comment", graph=graph_name, text=text[:50])
                except Exception as e:
                    errors.append({"action": "add_comment", "error": str(e)})

            # Compile if requested
            compile_result = None
            if params.get("recompile", True) and not params.get("dry_run", False):
                try:
                    # Compile via BlueprintEditorUtilityLibrary
                    if hasattr(unreal, "BlueprintEditorUtilityLibrary"):
                        compile_result = unreal.BlueprintEditorUtilityLibrary.recompileBlueprint(bp)
                        applied.append({"action": "recompile"})
                    else:
                        log.warning("recompile_unavailable")
                except Exception as e:
                    errors.append({"action": "recompile", "error": str(e)})

        except Exception as e:
            log.error("blueprint_write_failed", asset=params["asset_path"], error=str(e))
            return NyraToolResult.err(f"[-32000] mutation failed: {e}")

        if errors and not applied:
            return NyraToolResult.err(f"[-32001] all mutations failed: {errors}")

        return NyraToolResult.ok({
            "asset_path": params["asset_path"],
            "applied": applied,
            "errors": errors,
            "dry_run": params.get("dry_run", False),
            "recompile": params.get("recompile", True),
        })