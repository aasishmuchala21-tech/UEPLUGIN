"""nyrahost.mcp_server — stdio MCP server exposing NYRA tools.

Exposes Phase 2 tools via MCP (2025-11-25 spec):
  - nyra_permission_gate (Plan 02-09): plan-first preview gate
  - nyra_console_exec (Plan 02-10): console command whitelist
  - nyra_output_log_tail (Plan 02-11): UE output log tail
  - nyra_message_log_list (Plan 02-11): UE message log entries

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
from nyrahost.tools.computer_use_tools import (
    ComputerUseTool,
    ComputerUseStatusTool,
)

__version__ = "0.1.0"
TOOL_HANDLERS: dict = {}


class NyraMCPServer:
    """MCP server exposing NYRA tools over stdio."""

    def __init__(self) -> None:
        self._gate = NyraPermissionGate()
        self._ws_emit = lambda method, params: None  # Stub — set during init

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
        elif tool_name == "nyra_computer_use":
            return await self._handle_computer_use(arguments)
        elif tool_name == "nyra_computer_use_status":
            return await self._handle_computer_use_status(arguments)
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

    async def _handle_computer_use(self, args: dict) -> dict:
        """nyra_computer_use: start computer-use loop in background thread."""
        tool = ComputerUseTool()
        result = tool.execute(args)
        if result.is_ok:
            return result.data or {}
        return {"error": {"code": -32011, "message": result.error}}

    async def _handle_computer_use_status(self, args: dict) -> dict:
        """nyra_computer_use_status: check status or control a computer-use job."""
        tool = ComputerUseStatusTool()
        result = tool.execute(args)
        if result.is_ok:
            return result.data or {}
        return {"error": {"code": -32011, "message": result.error}}


def create_server() -> Server:
    """Factory: create and configure an MCP Server with all Phase 2 tools."""
    if Server is None:
        return None  # type: ignore[return-value]

    server = Server(name="nyra-mcp-server", version=__version__)

    mcp_server = NyraMCPServer()

    @server.list_tools()
    async def list_tools():
        return [
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
            # nyra_computer_use (Plan 05-03 Task 2)
            {
                "name": "nyra_computer_use",
                "description": "Start a computer-use automation loop using Claude Opus 4.7 with computer_20251124. NYRA will control mouse/keyboard to automate tasks in external apps (Substance 3D Sampler, UE modals). Permission dialog shown before first action. Press Ctrl+Alt+Space to pause at any time.",
                "inputSchema": {
                    "type": "object",
                    "required": ["task"],
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "Natural language description of the task to automate. Be specific: name the app, menu, and button.",
                        },
                        "job_id": {
                            "type": "string",
                            "description": "Optional job ID. Omit to generate a new UUID. Use existing job_id to resume a paused loop.",
                        },
                    },
                },
            },
            # nyra_computer_use_status (Plan 05-03 Task 2)
            {
                "name": "nyra_computer_use_status",
                "description": "Check status of, pause, resume, or stop a computer-use job started with nyra_computer_use.",
                "inputSchema": {
                    "type": "object",
                    "required": ["job_id"],
                    "properties": {
                        "job_id": {"type": "string", "description": "Job ID returned by nyra_computer_use."},
                        "action": {
                            "type": "string",
                            "enum": ["status", "pause", "resume", "stop"],
                            "default": "status",
                            "description": "Action: 'status' returns current status; 'pause' halts after current iteration; 'resume' continues a paused loop; 'stop' terminates immediately.",
                        },
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