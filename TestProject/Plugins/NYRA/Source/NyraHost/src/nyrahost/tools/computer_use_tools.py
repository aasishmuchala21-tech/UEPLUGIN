"""nyrahost.tools.computer_use_tools — GEN-03 computer-use MCP tools.

Per Plan 05-03:
  - nyra_computer_use: start the computer-use loop for a task
  - nyra_computer_use_status: get current status / pause / resume / stop

Threat mitigations: T-05-05 (permission gate shown before first action),
  T-05-06 (screenshots saved to local staging dir, not exfiltrated),
  T-05-07 (pause chord Ctrl+Alt+Space registered via Win32 RegisterHotKey)
"""
from __future__ import annotations

import os
import threading
import uuid
from typing import Optional

import structlog

from nyrahost.tools.base import NyraTool, NyraToolResult
from nyrahost.external.computer_use_loop import (
    ComputerUseLoop,
    ComputerUseError,
)
from nyrahost.tools.staging import StagingManifest

log = structlog.get_logger("nyrahost.tools.computer_use_tools")

__all__ = ["ComputerUseTool", "ComputerUseStatusTool"]


# Global loop registry (keyed by job_id) — allows status tool to reach running loops
_loop_registry: dict[str, ComputerUseLoop] = {}
_loop_lock = threading.Lock()


def _register_loop(loop: ComputerUseLoop) -> None:
    with _loop_lock:
        _loop_registry[loop.job_id] = loop


def _get_loop(job_id: str) -> Optional[ComputerUseLoop]:
    with _loop_lock:
        return _loop_registry.get(job_id)


class ComputerUseTool(NyraTool):
    """Start a computer-use automation loop.

    The loop captures screenshots, sends them to the Anthropic API with the
    computer_20251124 tool, and executes Win32 actions returned by the model.

    Permission gate: a dialog is shown on the first action. The user must click OK
    before any mouse or keyboard action is performed.

    Pause: press Ctrl+Alt+Space at any time to halt the loop.
    Use nyra_computer_use_status to check status or resume.
    """

    name = "nyra_computer_use"
    description = (
        "Start a computer-use automation loop using Claude Opus 4.7's "
        "computer_20251124 tool. NYRA will control the mouse and keyboard to "
        "automate tasks in external apps (Substance 3D Sampler, etc.). "
        "A permission dialog appears before any mouse/keyboard action. "
        "Press Ctrl+Alt+Space to pause at any time. "
        "Requires ANTHROPIC_API_KEY to be configured."
    )
    parameters = {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": (
                    "Natural language description of the task to automate. "
                    "Be specific: name the app, the menu, the button. "
                    "NYRA will figure out the exact steps."
                ),
            },
            "job_id": {
                "type": "string",
                "description": (
                    "Optional job ID. If omitted, a new UUID is generated. "
                    "Use an existing job_id to resume a paused loop."
                ),
            },
        },
        "required": ["task"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        task = params.get("task", "")
        job_id = params.get("job_id") or str(uuid.uuid4())

        # Check API key
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return NyraToolResult.err(
                "ANTHROPIC_API_KEY not configured. "
                "computer-use requires a Claude API key. "
                "Configure it in NYRA settings or set the ANTHROPIC_API_KEY env var."
            )

        # Write pending manifest entry before starting
        manifest = StagingManifest()
        manifest.add_pending(
            job_id=job_id,
            tool="computer_use",
            operation="run_loop",
            input_ref=task,
            api_response={"task": task, "status": "running"},
        )

        # Create and register loop
        try:
            loop = ComputerUseLoop(
                task=task,
                job_id=job_id,
                api_key=api_key,
            )
        except ComputerUseError as e:
            return NyraToolResult.err(str(e))

        _register_loop(loop)

        # Start in a background thread so the MCP call returns immediately
        result_holder: dict = {}

        def run_loop():
            try:
                result = loop.run()
                result_holder["result"] = result
                manifest.update_job(
                    job_id=job_id,
                    api_response=result,
                    ue_import_status="pending",
                )
                log.info(
                    "computer_use_loop_finished",
                    job_id=job_id,
                    status=result.get("status"),
                )
            except Exception as e:
                result_holder["result"] = {
                    "status": "error",
                    "error": str(e),
                }
                manifest.update_job(
                    job_id=job_id,
                    ue_import_status="failed",
                    error_message=str(e),
                )
                log.exception("computer_use_loop_error", job_id=job_id)

        thread = threading.Thread(target=run_loop, daemon=True)
        thread.start()

        return NyraToolResult.ok({
            "job_id": job_id,
            "status": "started",
            "message": (
                f"Computer-use loop started (job_id={job_id}). "
                f"Task: {task[:100]}...\n"
                "Use nyra_computer_use_status to check progress or pause/resume."
            ),
            "pause_instruction": "Press Ctrl+Alt+Space at any time to pause.",
        })


class ComputerUseStatusTool(NyraTool):
    """Check status of a running or paused computer-use job, or pause/resume/stop it."""

    name = "nyra_computer_use_status"
    description = (
        "Check the status of a computer-use job started with nyra_computer_use, "
        "or send control commands (pause, resume, stop)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "job_id": {
                "type": "string",
                "description": "Job ID returned by nyra_computer_use.",
            },
            "action": {
                "type": "string",
                "enum": ["status", "pause", "resume", "stop"],
                "default": "status",
                "description": (
                    "Action: 'status' (default) returns current status; "
                    "'pause' halts the loop after current iteration; "
                    "'resume' continues a paused loop; "
                    "'stop' terminates immediately."
                ),
            },
        },
        "required": ["job_id"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        job_id = params.get("job_id", "")
        action = params.get("action", "status")

        loop = _get_loop(job_id)
        if loop is None:
            return NyraToolResult.err(
                f"Job {job_id} not found. "
                "Start a new computer-use job with nyra_computer_use first."
            )

        if action == "stop":
            loop.stop()
            return NyraToolResult.ok({
                "job_id": job_id,
                "status": "stopped",
                "message": "Loop stopped.",
            })

        if action == "pause":
            loop.stop()  # Stops after current iteration
            return NyraToolResult.ok({
                "job_id": job_id,
                "status": "paused",
                "message": "Loop paused after current iteration. Use 'resume' to continue.",
            })

        if action == "resume":
            if not loop._paused:
                return NyraToolResult.err(
                    f"Job {job_id} is not paused. Use action='pause' to pause first."
                )
            try:
                result = loop.resume()
                return NyraToolResult.ok({
                    "job_id": job_id,
                    "status": result.get("status", "unknown"),
                    "iterations": result.get("iterations", 0),
                    "total_cost": result.get("total_cost", 0.0),
                })
            except ComputerUseError as e:
                return NyraToolResult.err(str(e))

        # action == "status"
        status = "paused" if loop._paused else ("running" if not loop._stopped else "stopped")
        return NyraToolResult.ok({
            "job_id": job_id,
            "status": status,
            "iteration_count": loop._iteration_count,
            "total_cost": loop._total_cost,
            "task": loop.task,
        })
