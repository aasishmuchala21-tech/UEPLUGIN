"""nyrahost.mcp_server — stdio MCP server exposing NYRA tools.

Exposes Phase 2 tools via MCP (2025-11-25 spec):
  - nyra_permission_gate (Plan 02-09): plan-first preview gate
  - nyra_console_exec (Plan 02-10): console command whitelist
  - nyra_output_log_tail (Plan 02-11): UE output log tail
  - nyra_message_log_list (Plan 02-11): UE message log entries

Exposes Phase 4 tools via MCP (Plans 04-01, 04-02, 04-03, 04-04, 04-06):
  - nyra_asset_search: fuzzy asset registry search
  - nyra_actor_spawn/duplicate/delete/select/transform/snap_ground: actor CRUD
  - nyra_material_get_param/set_param/create_mic: material instance control
  - nyra_blueprint_read/write/debug: Blueprint graph read, mutation, and debug loop

Exposes Phase 5 tools via MCP (Plans 05-01, 05-02, 05-03):
  - nyra_meshy_image_to_3d / nyra_job_status: Meshy REST
  - nyra_comfyui_run_workflow / nyra_comfyui_get_node_info: ComfyUI HTTP
  - nyra_computer_use / nyra_computer_use_status: computer-use loop

Entry point: python -m nyrahost.mcp_server --handshake-file <path>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
except ImportError:
    # Graceful fallback if mcp package not installed in dev env
    Server = None

from nyrahost.safe_mode import NyraPermissionGate
from nyrahost.console import classify_command, handle_nyra_console_exec
from nyrahost.log_tail import (
    handle_nyra_output_log_tail,
    handle_nyra_message_log_list,
)
from nyrahost.tools.asset_search import AssetSearchTool
from nyrahost.tools.actor_tools import (
    ActorSpawnTool,
    ActorDuplicateTool,
    ActorDeleteTool,
    ActorSelectTool,
    ActorTransformTool,
    ActorSnapGroundTool,
)
from nyrahost.tools.material_tools import (
    MaterialGetParamTool,
    MaterialSetParamTool,
    MaterialCreateMICTool,
)
from nyrahost.tools.blueprint_tools import BlueprintReadTool, BlueprintWriteTool
from nyrahost.tools.blueprint_debug import BlueprintDebugTool
from nyrahost.tools.meshy_tools import MeshyImageTo3DTool, JobStatusTool
from nyrahost.tools.comfyui_tools import (
    ComfyUIRunWorkflowTool,
    ComfyUIGetNodeInfoTool,
)
from nyrahost.tools.kb_search import KbSearchTool
# Phase 8 PARITY-02..08 — Competitive parity vs Aura
from nyrahost.tools.cpp_authoring_tools import (
    CppModuleCreateTool,
    CppClassAddTool,
    CppFunctionAddTool,
    CppRecompileTool,
)
from nyrahost.tools.bt_tools import (
    BTCreateTool,
    BTAddCompositeTool,
    BTAddTaskTool,
    BTAddDecoratorTool,
    BTSetBlackboardKeyTool,
)
from nyrahost.tools.niagara_tools import (
    NiagaraCreateSystemTool,
    NiagaraAddEmitterTool,
    NiagaraSetModuleParameterTool,
)
from nyrahost.tools.perf_tools import PerfExplainHotspotTool
from nyrahost.tools.animbp_tools import (
    AnimBPCreateTool,
    AnimBPAddStateMachineTool,
    AnimBPAddTransitionTool,
)
from nyrahost.tools.metasound_tools import (
    MetasoundCreateTool,
    MetasoundAddNodeTool,
    MetasoundConnectTool,
)


__version__ = "0.1.0"
TOOL_HANDLERS: dict = {}


class NyraMCPServer:
    """MCP server exposing NYRA tools over stdio."""

    def __init__(self) -> None:
        self._gate = NyraPermissionGate()
        self._ws_emit = lambda method, params: None  # Stub — set during init
        # Phase 4 + Phase 5 tools routed through self._tools dict
        self._tools = {
            # Phase 4: Asset/Actor/Material/Blueprint tools
            "nyra_asset_search": AssetSearchTool(),
            "nyra_actor_spawn": ActorSpawnTool(),
            "nyra_actor_duplicate": ActorDuplicateTool(),
            "nyra_actor_delete": ActorDeleteTool(),
            "nyra_actor_select": ActorSelectTool(),
            "nyra_actor_transform": ActorTransformTool(),
            "nyra_actor_snap_ground": ActorSnapGroundTool(),
            "nyra_material_get_param": MaterialGetParamTool(),
            "nyra_material_set_param": MaterialSetParamTool(),
            "nyra_material_create_mic": MaterialCreateMICTool(),
            "nyra_blueprint_read": BlueprintReadTool(),
            "nyra_blueprint_write": BlueprintWriteTool(),
            "nyra_blueprint_debug": BlueprintDebugTool(),
            # Phase 5: External Tool Integrations
            # GEN-01: Meshy REST
            "nyra_meshy_image_to_3d": MeshyImageTo3DTool(),
            "nyra_job_status": JobStatusTool(),
            # GEN-02: ComfyUI HTTP
            "nyra_comfyui_run_workflow": ComfyUIRunWorkflowTool(),
            "nyra_comfyui_get_node_info": ComfyUIGetNodeInfoTool(),
            # Phase 3: UE5 Knowledge RAG (BM25 floor; LanceDB-compatible)
            "nyra_kb_search": KbSearchTool(),
            # === Phase 8: Competitive Parity vs Aura ===
            # PARITY-02: C++ authoring + Live Coding
            "nyra_cpp_module_create": CppModuleCreateTool(),
            "nyra_cpp_class_add": CppClassAddTool(),
            "nyra_cpp_function_add": CppFunctionAddTool(),
            "nyra_cpp_recompile": CppRecompileTool(),
            # PARITY-03: Behavior Tree authoring
            "nyra_bt_create": BTCreateTool(),
            "nyra_bt_add_composite": BTAddCompositeTool(),
            "nyra_bt_add_task": BTAddTaskTool(),
            "nyra_bt_add_decorator": BTAddDecoratorTool(),
            "nyra_bt_set_blackboard_key": BTSetBlackboardKeyTool(),
            # PARITY-05: Niagara VFX authoring
            "nyra_niagara_create_system": NiagaraCreateSystemTool(),
            "nyra_niagara_add_emitter": NiagaraAddEmitterTool(),
            "nyra_niagara_set_module_parameter": NiagaraSetModuleParameterTool(),
            # PARITY-06: Performance profiling (only explain_hotspot lives in
            # _tools; stat_read + insights_query are WS-forwarders dispatched
            # via handle_tool_call's elif chain — see 08-06-MCP-REGISTRATION.md)
            "nyra_perf_explain_hotspot": PerfExplainHotspotTool(),
            # PARITY-07: Animation Blueprint authoring
            "nyra_animbp_create": AnimBPCreateTool(),
            "nyra_animbp_add_state_machine": AnimBPAddStateMachineTool(),
            "nyra_animbp_add_transition": AnimBPAddTransitionTool(),
            # PARITY-08: Metasounds (audio) — gloss-tier, smallest surface
            "nyra_metasound_create": MetasoundCreateTool(),
            "nyra_metasound_add_node": MetasoundAddNodeTool(),
            "nyra_metasound_connect": MetasoundConnectTool(),
        }

    def set_ws_emit(self, emit_fn: callable) -> None:
        """Set the WebSocket emit function for WS requests."""
        self._ws_emit = emit_fn

    async def handle_tool_call(self, tool_name: str, arguments: dict) -> dict:
        """Dispatch to the appropriate tool handler."""
        if tool_name == "nyra_permission_gate":
            return await self._handle_permission_gate(arguments)
        elif tool_name == "nyra_console_exec":
            return await self._handle_console_exec(arguments)
        elif tool_name == "nyra_output_log_tail":
            return await self._handle_log_tail(arguments)
        elif tool_name == "nyra_message_log_list":
            return await self._handle_msg_log_list(arguments)
        elif tool_name in self._tools:
            tool = self._tools[tool_name]
            try:
                result = tool.execute(arguments)
                return result.to_dict()
            except Exception as e:
                return {"error": {"code": -32000, "message": str(e)}}
        else:
            return {"error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}}

    async def _handle_permission_gate(self, args: dict) -> dict:
        """nyra_permission_gate: generate preview and await user decision."""
        plan_id = args.get("plan_id", "")
        steps = args.get("steps", [])
        if not plan_id:
            plan_id = f"plan-{len(steps)}"
        await self._gate.generate_preview(plan_id, steps)
        try:
            decision = await self._gate.await_decision(plan_id)
            return {"approved": decision.get("decision") == "approved", "plan_id": plan_id}
        except Exception:
            return {"error": {"code": -32011, "message": "plan_rejected", "remediation": "User rejected plan."}}

    async def _handle_console_exec(self, args: dict) -> dict:
        """nyra_console_exec: classify and route command."""
        return await handle_nyra_console_exec(args, self._gate, self._ws_emit)

    async def _handle_log_tail(self, args: dict) -> dict:
        """nyra_output_log_tail: forward to UE log/tail."""
        return await handle_nyra_output_log_tail(args, self._ws_emit)

    async def _handle_msg_log_list(self, args: dict) -> dict:
        """nyra_message_log_list: forward to UE log/message-log-list."""
        return await handle_nyra_message_log_list(args, self._ws_emit)


def create_server() -> Server:
    """Factory: create and configure an MCP Server with all phases' tools."""
    if Server is None:
        return None  # type: ignore[return-value]

    server = Server(name="nyra-mcp-server", version=__version__)

    mcp_server = NyraMCPServer()

    @server.list_tools()
    async def list_tools():
        return [
            # === Phase 2 tools ===
            # nyra_permission_gate per RESEARCH §4.2
            {
                "name": "nyra_permission_gate",
                "description": "Request user approval for a planned sequence of UE mutations. MUST be called before any destructive tool (spawn_actor, edit_blueprint, modify_material, delete_*).",
                "inputSchema": {
                    "type": "object",
                    "required": ["summary", "steps"],
                    "properties": {
                        "summary": {"type": "string"},
                        "steps": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["tool", "args", "rationale"],
                                "properties": {
                                    "tool": {"type": "string"},
                                    "args": {"type": "object"},
                                    "rationale": {"type": "string"},
                                    "risk": {"type": "string", "enum": ["read-only", "reversible", "destructive", "irreversible"]},
                                },
                            },
                        },
                        "estimated_duration_seconds": {"type": "number"},
                        "affects_files": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            # nyra_console_exec per RESEARCH §7.4
            {
                "name": "nyra_console_exec",
                "description": "Execute a UE console command with whitelist safety classification.",
                "inputSchema": {
                    "type": "object",
                    "required": ["command"],
                    "properties": {
                        "command": {"type": "string"},
                        "rationale": {"type": "string"},
                    },
                },
            },
            # nyra_output_log_tail
            {
                "name": "nyra_output_log_tail",
                "description": "Retrieve the last N lines of the UE editor Output Log.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "categories": {"type": "array", "items": {"type": "string"}},
                        "max_entries": {"type": "integer", "default": 50, "maximum": 200},
                        "since_ts": {"type": "string"},
                        "regex": {"type": "string"},
                        "min_verbosity": {"type": "string", "default": "log"},
                    },
                },
            },
            # nyra_message_log_list
            {
                "name": "nyra_message_log_list",
                "description": "Retrieve entries from a UE Message Log listing.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "listing_name": {"type": "string", "default": "LogBlueprint"},
                        "since_index": {"type": "integer", "default": 0},
                        "max_entries": {"type": "integer", "default": 50, "maximum": 200},
                    },
                },
            },
            # === Phase 4 tools ===
            # nyra_asset_search per Plan 04-03
            {
                "name": "nyra_asset_search",
                "description": "Search the current UE project asset registry using fuzzy string matching. Searches asset names, tags, and class names. Returns ranked results with match scores.",
                "inputSchema": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string", "description": "Search query string (e.g. 'hero material', 'character skeletal')"},
                        "class_filter": {"type": "string", "description": "Optional: restrict to a specific UClass name (e.g. 'Material', 'StaticMesh')"},
                        "limit": {"type": "integer", "default": 20, "description": "Maximum number of results to return"},
                        "threshold": {"type": "integer", "default": 70, "description": "Minimum fuzzy match score (0-100)"},
                        "include_tags": {"type": "boolean", "default": True, "description": "Include asset tags in match"},
                    },
                },
            },
            # nyra_actor_spawn per Plan 04-04
            {
                "name": "nyra_actor_spawn",
                "description": "Spawn an actor by class or asset path in the current editor level. The actor is placed at the given world-space location and rotation.",
                "inputSchema": {
                    "type": "object",
                    "required": ["class_name"],
                    "properties": {
                        "class_name": {"type": "string", "description": "UE class name, e.g. 'StaticMeshActor' or '/Script/Engine.CameraActor'"},
                        "asset_path": {"type": "string", "description": "Asset path for Blueprint-derived actors, e.g. '/Game/Props/Crate_C'"},
                        "location": {"type": "object", "properties": {"x": {"type": "number"}, "y": {"type": "number"}, "z": {"type": "number"}}, "default": {"x": 0.0, "y": 0.0, "z": 0.0}},
                        "rotation": {"type": "object", "properties": {"pitch": {"type": "number"}, "yaw": {"type": "number"}, "roll": {"type": "number"}}, "default": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0}},
                        "name": {"type": "string", "description": "Optional actor label/name in the world outliner"},
                    },
                },
            },
            # nyra_actor_duplicate per Plan 04-04
            {
                "name": "nyra_actor_duplicate",
                "description": "Duplicate one or more actors in the current level with an optional offset.",
                "inputSchema": {
                    "type": "object",
                    "required": ["actor_path"],
                    "properties": {
                        "actor_path": {"type": "string", "description": "Path to the source actor (world outliner path or '/Game/...' format)"},
                        "offset": {"type": "object", "properties": {"x": {"type": "number"}, "y": {"type": "number"}, "z": {"type": "number"}}, "default": {"x": 0.0, "y": 0.0, "z": 0.0}},
                    },
                },
            },
            # nyra_actor_delete per Plan 04-04
            {
                "name": "nyra_actor_delete",
                "description": "Delete one or more actors from the current level. This operation is destructive.",
                "inputSchema": {
                    "type": "object",
                    "required": ["actor_path"],
                    "properties": {
                        "actor_path": {"type": "string", "description": "Path to the actor to delete"},
                    },
                },
            },
            # nyra_actor_select per Plan 04-04
            {
                "name": "nyra_actor_select",
                "description": "Set the editor selection to one or more actors by path.",
                "inputSchema": {
                    "type": "object",
                    "required": ["actor_paths"],
                    "properties": {
                        "actor_paths": {"type": "array", "items": {"type": "string"}, "description": "Paths to actors to select"},
                        "add_to_selection": {"type": "boolean", "default": False, "description": "If true, add to current selection; if false, replace it"},
                    },
                },
            },
            # nyra_actor_transform per Plan 04-04
            {
                "name": "nyra_actor_transform",
                "description": "Set location, rotation, and/or scale of an actor.",
                "inputSchema": {
                    "type": "object",
                    "required": ["actor_path"],
                    "properties": {
                        "actor_path": {"type": "string"},
                        "location": {"type": "object", "properties": {"x": {"type": "number"}, "y": {"type": "number"}, "z": {"type": "number"}}},
                        "rotation": {"type": "object", "properties": {"pitch": {"type": "number"}, "yaw": {"type": "number"}, "roll": {"type": "number"}}},
                        "scale": {"type": "object", "properties": {"x": {"type": "number"}, "y": {"type": "number"}, "z": {"type": "number"}}},
                    },
                },
            },
            # nyra_actor_snap_ground per Plan 04-04
            {
                "name": "nyra_actor_snap_ground",
                "description": "Snap an actor to the ground using a downward line trace. Finds the first blocking hit below the actor's current location and moves it so its bottom sits flush with the hit surface.",
                "inputSchema": {
                    "type": "object",
                    "required": ["actor_path"],
                    "properties": {
                        "actor_path": {"type": "string"},
                        "trace_distance": {"type": "number", "default": 10000.0, "description": "Maximum trace distance in cm (default 100m)"},
                    },
                },
            },
            # nyra_material_get_param per Plan 04-06
            {
                "name": "nyra_material_get_param",
                "description": "Read scalar, vector, or texture parameter values from a Material Instance (or any material that exposes parameter collections).",
                "inputSchema": {
                    "type": "object",
                    "required": ["material_path", "param_name", "param_type"],
                    "properties": {
                        "material_path": {"type": "string", "description": "UE asset path, e.g. '/Game/Materials/M_Hero_C.M_Hero_C'"},
                        "param_name": {"type": "string"},
                        "param_type": {"type": "string", "enum": ["scalar", "vector", "texture"], "description": "Type of parameter to read"},
                    },
                },
            },
            # nyra_material_set_param per Plan 04-06
            {
                "name": "nyra_material_set_param",
                "description": "Write scalar, vector, or texture parameter values on a Material Instance. Creates a dynamic Material Instance if the parent material is not already a MIC.",
                "inputSchema": {
                    "type": "object",
                    "required": ["material_path", "param_name", "param_type"],
                    "properties": {
                        "material_path": {"type": "string"},
                        "param_name": {"type": "string"},
                        "param_type": {"type": "string", "enum": ["scalar", "vector", "texture"]},
                        "scalar_value": {"type": "number"},
                        "vector_value": {"type": "object", "properties": {"r": {"type": "number"}, "g": {"type": "number"}, "b": {"type": "number"}, "a": {"type": "number"}}},
                        "texture_value": {"type": "string", "description": "UE asset path of UTexture2D"},
                        "actor_path": {"type": "string", "description": "Optional: apply this MIC to a specific actor's static mesh component"},
                        "component_index": {"type": "integer", "default": 0, "description": "Mesh component index on the target actor"},
                    },
                },
            },
            # nyra_material_create_mic per Plan 04-06
            {
                "name": "nyra_material_create_mic",
                "description": "Create a dynamic Material Instance (MIC) from a parent Material.",
                "inputSchema": {
                    "type": "object",
                    "required": ["parent_material"],
                    "properties": {
                        "parent_material": {"type": "string", "description": "UE asset path of the parent Material"},
                        "mic_name": {"type": "string", "description": "Optional actor label for the new MIC (visible in world outliner)"},
                    },
                },
            },
            # nyra_blueprint_read per Plan 04-01
            {
                "name": "nyra_blueprint_read",
                "description": "Read a Blueprint's node graph, variables, and event graphs as structured JSON. Returns class name, functions, events, variables, and graph nodes.",
                "inputSchema": {
                    "type": "object",
                    "required": ["asset_path"],
                    "properties": {
                        "asset_path": {"type": "string", "description": "Full UE asset path, e.g. '/Game/Characters/Hero_BP.Hero_BP_C'"},
                        "include_graphs": {"type": "boolean", "default": True, "description": "Include graph/node details"},
                    },
                },
            },
            # nyra_blueprint_write per Plan 04-01
            {
                "name": "nyra_blueprint_write",
                "description": "Mutate a Blueprint: add nodes, remove nodes, reconnect pins, set variable defaults, and recompile. All mutations are wrapped in a transaction and validated against the Blueprint's current state before application.",
                "inputSchema": {
                    "type": "object",
                    "required": ["asset_path", "mutation"],
                    "properties": {
                        "asset_path": {"type": "string"},
                        "mutation": {
                            "type": "object",
                            "description": "Mutation to apply",
                            "properties": {
                                "set_variable_defaults": {"type": "object", "description": "variable_name -> new_default_value map"},
                                "add_comment": {"type": "object", "description": "Add a comment node: {graph_name, text, pos_x, pos_y}"},
                            },
                        },
                        "recompile": {"type": "boolean", "default": True},
                        "dry_run": {"type": "boolean", "default": False},
                    },
                },
            },
            # nyra_blueprint_debug per Plan 04-02
            {
                "name": "nyra_blueprint_debug",
                "description": "Debug a Blueprint's compile errors: reads the compile log, parses errors, explains each in plain English, and returns structured diffs to fix them. Returns status=clean if the Blueprint has no errors. The diffs returned are valid mutation inputs for nyra_blueprint_write.",
                "inputSchema": {
                    "type": "object",
                    "required": ["asset_path"],
                    "properties": {
                        "asset_path": {"type": "string", "description": "Full UE asset path, e.g. '/Game/Characters/Hero_BP.Hero_BP_C'"},
                        "include_warnings": {"type": "boolean", "default": False, "description": "Include warnings in the errors list"},
                        "include_suggestions": {"type": "boolean", "default": True, "description": "Include suggested_fix in each error entry"},
                    },
                },
            },
            # === Phase 5 tools ===
            # nyra_meshy_image_to_3d per Plan 05-01 (GEN-01)
            {
                "name": "nyra_meshy_image_to_3d",
                "description": "Generate a 3D mesh from a reference image using Meshy AI. Uploads the image, polls until the job completes, downloads the GLB, and stages it for UE import as UStaticMesh with LODs and collision. Submitting the same image twice returns the existing job_id (idempotent, no duplicate imports).",
                "inputSchema": {
                    "type": "object",
                    "required": ["image_path"],
                    "properties": {
                        "image_path": {"type": "string", "description": "Absolute path to the reference image on disk (JPG, PNG, WebP)"},
                        "prompt": {"type": "string", "description": "Optional natural-language guidance for mesh generation, e.g. 'low-poly stylized'"},
                        "task_type": {"type": "string", "default": "meshy-image-to-3d-reMeshed", "description": "Meshy task type"},
                        "target_folder": {"type": "string", "default": "/Game/NYRA/Meshes", "description": "UE Content Browser destination folder"},
                    },
                },
            },
            # nyra_job_status per Plan 05-01 (GEN-01)
            {
                "name": "nyra_job_status",
                "description": "Poll the status of a NYRA staging job by its job_id. Works for Meshy, ComfyUI, and computer-use jobs.",
                "inputSchema": {
                    "type": "object",
                    "required": ["job_id"],
                    "properties": {
                        "job_id": {"type": "string", "description": "The job_id returned by nyra_meshy_image_to_3d or nyra_comfyui_run_workflow"},
                    },
                },
            },
            # nyra_comfyui_run_workflow per Plan 05-02 (GEN-02)
            {
                "name": "nyra_comfyui_run_workflow",
                "description": "Run a ComfyUI image generation workflow and stage results for UE import as UTexture2D. The workflow JSON is validated against the server's node registry before submission. Use nyra_job_status to poll for completion.",
                "inputSchema": {
                    "type": "object",
                    "required": ["workflow_json"],
                    "properties": {
                        "workflow_json": {
                            "type": "object",
                            "description": "ComfyUI workflow in API JSON format (export from ComfyUI UI using the 'API' button).",
                        },
                        "input_image_asset_path": {
                            "type": "string",
                            "description": "Optional UE asset path of a UTexture2D to inject as input to the workflow.",
                        },
                        "target_folder": {
                            "type": "string",
                            "default": "/Game/NYRA/Textures",
                            "description": "UE Content Browser destination folder for generated textures.",
                        },
                    },
                },
            },
            # nyra_comfyui_get_node_info per Plan 05-02 (GEN-02)
            {
                "name": "nyra_comfyui_get_node_info",
                "description": "Probe the ComfyUI server's available node types. Use to validate workflows before submission or discover installed custom nodes.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "class_type": {
                            "type": "string",
                            "description": "Optional: filter to a specific node type. If omitted, returns all node types.",
                        },
                    },
                },
            },
            # === Phase 3 tools ===
            # nyra_kb_search — UE5 knowledge BM25 retrieval
            {
                "name": "nyra_kb_search",
                "description": (
                    "Search the bundled UE5 knowledge index for documentation, "
                    "tutorials, and forum guidance relevant to a natural-language "
                    "query. Returns ranked passages with source paths so Claude "
                    "can cite them. Use this BEFORE asking the user about UE "
                    "behavior — the index is built from current UE 5.x docs and "
                    "is more reliable than the model's training cutoff."
                ),
                "inputSchema": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 6},
                        "min_score": {"type": "number", "default": 0.5},
                        "index_path": {"type": "string"},
                    },
                },
            },
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        return await mcp_server.handle_tool_call(name, arguments)

    return server


async def main(handshake_path: str | None = None) -> None:
    """Run the stdio MCP server."""
    if Server is None:
        print("ERROR: mcp package not installed. Install with: pip install mcp>=1.2.0", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(description="NYRA MCP stdio server")
    parser.add_argument("--handshake-file", type=str, help="Path to handshake JSON")
    args = parser.parse_args()

    server = create_server()
    if server is None:
        sys.exit(1)

    # If handshake file provided, load token and connect back to NyraHost
    if args.handshake_file:
        try:
            handshake = json.loads(Path(args.handshake_file).read_text())
            # Store for later WS connection — for now, use stub emit
            pass
        except Exception:
            pass

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())