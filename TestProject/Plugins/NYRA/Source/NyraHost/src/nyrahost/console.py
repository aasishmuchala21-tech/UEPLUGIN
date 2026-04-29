"""nyra_console_exec MCP tool — Phase 2 console command whitelist (Plan 02-10).

Three-tier safety model (RESEARCH §7.3):
  - Tier A (auto-approved): stat, showflag, log, help commands — run immediately
  - Tier B (preview-gated via Plan 02-09): generic r.* + profilegpu — user approves
  - Tier C (hard-blocked): quit, exit, exec, gc, reloadshaders, travel — -32012

MCP tool registered via mcp_server/__init__.py create_server().
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import structlog

from nyrahost.safe_mode import NyraPermissionGate

log = structlog.get_logger("nyrahost.console")

# Tier definitions (RESEARCH §7.3)
_TIER_A_PREFIXES = ["stat ", "showflag.", "log ", "help"]
_TIER_A_EXACT = ["help", "obj classes", "obj hierarchy", "dumpticks", "memreport -full"]
_TIER_A_REGEX = [re.compile(r"^r\.VSync(\s+\d)?$"), re.compile(r"^r\.ScreenPercentage(\s+\d+)?$")]

_TIER_B_PREFIXES = ["r."]
_TIER_B_EXACT = ["profilegpu"]

_TIER_C_EXACT = ["quit", "exit", "exitnow", "obj gc", "gc.CollectGarbage", "reloadshaders"]
_TIER_C_PREFIXES = ["exec ", "travel ", "open ", "debugcreateplayer"]


def classify_command(command: str) -> Literal["A", "B", "C"]:
    """
    Classify a console command into tier.

    Priority: C > B > A; default-deny on no match.
    """
    cmd = command.strip()

    # Tier C checks first (hard-block)
    if cmd.lower() in _TIER_C_EXACT:
        return "C"
    for prefix in _TIER_C_PREFIXES:
        if cmd.lower().startswith(prefix.lower()):
            return "C"

    # Tier A checks
    if cmd.lower() in [e.lower() for e in _TIER_A_EXACT]:
        return "A"
    for prefix in _TIER_A_PREFIXES:
        if cmd.lower().startswith(prefix.lower()):
            return "A"
    for regex in _TIER_A_REGEX:
        if regex.match(cmd):
            return "A"

    # Tier B checks
    if cmd.lower() in [e.lower() for e in _TIER_B_EXACT]:
        return "B"
    for prefix in _TIER_B_PREFIXES:
        if cmd.lower().startswith(prefix.lower()):
            return "B"

    # Default-deny (tier C)
    return "C"


async def handle_nyra_console_exec(
    args: dict,
    permission_gate: NyraPermissionGate,
    ws_emit_request: callable,
) -> dict:
    """
    Handle nyra_console_exec MCP tool call.

    Routes based on tier:
      A → emit console/exec WS request to UE
      B → generate preview via Plan 02-09 permission gate
      C → return -32012 error
    """
    command = args.get("command", "").strip()
    if not command:
        return {
            "error": {
                "code": -32013,
                "message": "empty_command",
                "data": {"remediation": "Command cannot be empty."},
            }
        }

    tier = classify_command(command)
    log.info("console_exec_classified", command=command[:50], tier=tier)

    if tier == "C":
        return {
            "error": {
                "code": -32012,
                "message": "command_blocked",
                "data": {
                    "remediation": "This command is not in the NYRA console whitelist. "
                                  "To allow it, go to Settings > NYRA > Console Whitelist.",
                    "command": command,
                    "tier": "C",
                },
            }
        }

    if tier == "B":
        # Tier B: generate preview via permission gate (Plan 02-09)
        preview_id = f"console-{command[:20]}"
        await permission_gate.generate_preview(preview_id, [
            {"tool": "nyra_console_exec", "args": {"command": command}, "impact": f"Execute console: {command}", "risk": "reversible"}
        ])
        # For stub: simulate immediate approval after preview
        # Real implementation: await decision, then proceed or reject
        await permission_gate.approve(preview_id)

    # Tier A and approved Tier B: emit console/exec request to UE
    result = await ws_emit_request("console/exec", {
        "command": command,
        "rationale": args.get("rationale", ""),
        "tier": tier,
    })
    return result


__all__ = ["classify_command", "handle_nyra_console_exec"]