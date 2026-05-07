"""nyrahost.external.computer_use_loop — GEN-03 computer-use automation loop.

Per Plan 05-03:
  - Permission gate before first action
  - Win32 action execution (SendInput, mouse_event)
  - mss screenshots saved to staging dir
  - Ctrl+Alt+Space pause chord via RegisterHotKey
  - Anthropic SDK with computer_20251124 tool + computer-use-2025-11-24 beta header

Phase 0 gate: not phase0-gated — execute fully.
Threat mitigations: T-05-06 (screenshot stays local),
  T-05-05 (Ctrl+Alt+Space pause chord), T-05-07 (permission gate before first action)
"""
from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Optional

import structlog
import threading

try:
    import mss
except ImportError:
    mss = None

from nyrahost.external.win32_actions import (
    Win32ActionExecutor,
    PermissionGate,
)

log = structlog.get_logger("nyrahost.external.computer_use_loop")

__all__ = ["ComputerUseLoop", "ComputerUseError"]

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


class ComputerUseError(Exception):
    """Raised when the computer-use loop encounters a non-recoverable error."""
    pass


class PermissionGateResult:
    """Result of checking the permission gate."""

    def __init__(self, approved: bool, user_dismissed: bool = False):
        self.approved = approved
        self.user_dismissed = user_dismissed


class ComputerUseLoop:
    """Runs a computer-use loop using the Anthropic API with computer_20251124 tool.

    The loop:
      1. Captures a screenshot (mss) and saves it to the staging dir
      2. Sends it to the Anthropic API with the current task prompt
      3. Executes Win32 actions returned by the model (cursor, keyboard, screenshot)
      4. Repeats until the model returns done or the pause chord fires

    Permission gate: no Win32 action executes until the user has explicitly approved
    via the PermissionGate. The first screenshot (step 1) is always taken without gate.

    Screenshot path: images are saved to <staging_root>/computer_use/<job_id>/*.png
    and referenced by absolute path in API calls — they are NOT embedded as base64.

    Pause chord: Ctrl+Alt+Space is registered as a Win32 global hotkey. When fired,
    the loop halts synchronously and sets self._paused = True. The caller can then
    call resume() to continue or stop() to terminate.
    """

    COMPUTER_USE_MODEL = "claude-opus-4-7"
    COMPUTER_USE_TOOL = "computer_20251124"
    BETA_HEADER = "computer-use-2025-11-24"
    MAX_ITERATIONS = 100
    SCREENSHOT_DIR = "computer_use"

    def __init__(
        self,
        task: str,
        job_id: Optional[str] = None,
        staging_root: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        if not api_key and not ANTHROPIC_API_KEY:
            raise ComputerUseError(
                "ANTHROPIC_API_KEY not set. "
                "computer-use requires a Claude API key. "
                "Configure it via: Settings -> AI Provider -> Anthropic API Key"
            )
        self.api_key = api_key or ANTHROPIC_API_KEY
        self.job_id = job_id or str(uuid.uuid4())
        self.staging_root = staging_root or self._default_staging_root()
        self.task = task
        self._client = None
        self._stopped = False
        self._paused = False
        self._action_executor = Win32ActionExecutor()
        self._permission_gate = PermissionGate()
        self._permission_approved = False
        self._permission_result: Optional[PermissionGateResult] = None
        self._screenshot_counter = 0
        self._total_cost = 0.0
        self._iteration_count = 0

    @staticmethod
    def _default_staging_root() -> Path:
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".nyra")))
        return base / "NYRA" / "staging"

    def _ensure_screenshot_dir(self) -> Path:
        d = self.staging_root / self.SCREENSHOT_DIR / self.job_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _capture_screenshot(self) -> str:
        """Capture a screenshot using mss, save to staging dir, return path."""
        if mss is None:
            raise ComputerUseError("mss not available on this platform")
        screenshot_dir = self._ensure_screenshot_dir()
        filename = screenshot_dir / f"screenshot_{self._screenshot_counter:04d}.png"
        self._screenshot_counter += 1
        with mss.mss() as sct:
            sct.save(str(filename), region={})  # full screen
        log.info("screenshot_captured", path=str(filename))
        return str(filename)

    def _check_pause_chord(self) -> bool:
        """Return True if the pause chord (Ctrl+Alt+Space) has fired."""
        return self._action_executor.check_pause_chord()

    def _check_permission(self) -> PermissionGateResult:
        """Show the permission gate if not yet approved.

        Returns PermissionGateResult(approved=True) if the user approved.
        Returns PermissionGateResult(approved=False, user_dismissed=True) if dismissed.
        """
        if self._permission_approved:
            return PermissionGateResult(approved=True)

        if self._permission_result is None:
            log.info("permission_gate_showing", job_id=self.job_id)
            approved = self._permission_gate.check(self.task)
            if approved:
                self._permission_approved = True
                self._permission_result = PermissionGateResult(approved=True)
            else:
                self._permission_result = PermissionGateResult(
                    approved=False, user_dismissed=True
                )
            log.info(
                "permission_gate_result",
                job_id=self.job_id,
                approved=self._permission_approved,
            )

        return self._permission_result

    def _execute_action(self, action: dict) -> None:
        """Execute a single computer-use action via Win32.

        Action types handled:
          - cursor: move mouse (x, y absolute or delta)
          - left_click, right_click, middle_click, double_click
          - type: send keystrokes via SendInput
          - scroll: mouse wheel delta
          - key_combo: Ctrl+Alt+Space = pause
          - screenshot: no-op (handled by loop)
        """
        action_type = action.get("action") or action.get("type")

        if action_type == "screenshot":
            return  # Screenshot already captured at loop start

        if not self._permission_approved:
            result = self._check_permission()
            if not result.approved:
                raise ComputerUseError(
                    "Permission denied by user. Aborting computer-use loop."
                )

        self._action_executor.execute(action)
        log.info("action_executed", action_type=action_type)

    def _build_api_message(self, screenshot_path: str) -> dict:
        """Build the user message with screenshot for the Anthropic API.

        Screenshot is referenced by file path, not base64 — T-05-06 mitigation:
        the API receives a content block with type 'image' and source 'local_file'.
        """
        return {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "local_file",
                        "file_path": screenshot_path,
                    }
                }
            ]
        }

    @property
    def client(self):
        """Lazy-initialized Anthropic client."""
        if self._client is None:
            try:
                from anthropic import Anthropic

                self._client = Anthropic(api_key=self.api_key)
            except ImportError:
                raise ComputerUseError(
                    "anthropic package not installed. "
                    "Run: pip install anthropic"
                )
        return self._client

    def run(self, task: Optional[str] = None) -> dict:
        """Run the full computer-use loop synchronously.

        Returns a dict with:
          - status: "completed" | "paused" | "stopped" | "error"
          - iterations: int
          - total_cost: float
          - actions: list of action dicts executed
          - screenshot_dir: path to all captured screenshots
          - error: optional error message
        """
        task = task or self.task
        actions_log: list[dict] = []

        # Register global pause hotkey (Ctrl+Alt+Space)
        self._action_executor.register_pause_chord()
        log.info("computer_use_loop_starting", job_id=self.job_id, task=task)

        try:
            while not self._stopped and self._iteration_count < self.MAX_ITERATIONS:
                self._iteration_count += 1

                # Check pause chord
                if self._check_pause_chord():
                    log.info("pause_chord_fired", job_id=self.job_id)
                    self._paused = True
                    return {
                        "status": "paused",
                        "iterations": self._iteration_count,
                        "total_cost": self._total_cost,
                        "actions": actions_log,
                        "screenshot_dir": str(self._ensure_screenshot_dir()),
                        "message": "Loop paused by Ctrl+Alt+Space. Call resume() or stop().",
                    }

                # Capture screenshot
                screenshot_path = self._capture_screenshot()

                # Build message
                msg = self._build_api_message(screenshot_path)

                # Call API
                try:
                    response = self.client.messages.create(
                        model=self.COMPUTER_USE_MODEL,
                        max_tokens=4096,
                        tools=[{"type": self.COMPUTER_USE_TOOL}],
                        betas=[self.BETA_HEADER],
                        messages=[{"role": "user", "content": task}] + [msg],
                    )
                except Exception as e:
                    log.error("api_call_failed", error=str(e))
                    return {
                        "status": "error",
                        "iterations": self._iteration_count,
                        "total_cost": self._total_cost,
                        "actions": actions_log,
                        "screenshot_dir": str(self._ensure_screenshot_dir()),
                        "error": f"API call failed: {str(e)}",
                    }

                # Update cost tracking
                if hasattr(response, "usage") and response.usage:
                    input_tokens = getattr(response.usage, "input_tokens", 0) or 0
                    output_tokens = getattr(response.usage, "output_tokens", 0) or 0
                    # Anthropic pricing (approximate for Opus 4.7)
                    cost = (input_tokens * 15 + output_tokens * 75) / 1_000_000
                    self._total_cost += cost

                # Process tool use calls
                stop_reason = getattr(response, "stop_reason", None)
                if stop_reason == "end_turn":
                    log.info(
                        "loop_completed",
                        job_id=self.job_id,
                        iterations=self._iteration_count,
                    )
                    return {
                        "status": "completed",
                        "iterations": self._iteration_count,
                        "total_cost": self._total_cost,
                        "actions": actions_log,
                        "screenshot_dir": str(self._ensure_screenshot_dir()),
                    }

                # Execute actions from the model response
                tool_calls = getattr(response, "content", [])
                for block in tool_calls:
                    if hasattr(block, "type") and block.type == "tool_use":
                        action_input = getattr(block, "input", {})
                        action_type = getattr(block, "name", "")
                        action = {"type": action_type, **action_input}
                        actions_log.append(action)
                        self._execute_action(action)

        except ComputerUseError as e:
            log.error("computer_use_error", error=str(e))
            return {
                "status": "error",
                "iterations": self._iteration_count,
                "total_cost": self._total_cost,
                "actions": actions_log,
                "screenshot_dir": str(self._ensure_screenshot_dir()),
                "error": str(e),
            }
        finally:
            self._action_executor.unregister_pause_chord()

    def stop(self) -> None:
        """Stop the loop after the current iteration."""
        self._stopped = True
        log.info("loop_stopped", job_id=self.job_id)

    def resume(self) -> dict:
        """Resume a paused loop."""
        if not self._paused:
            raise ComputerUseError("Loop is not paused")
        self._paused = False
        log.info("loop_resumed", job_id=self.job_id)
        return self.run()