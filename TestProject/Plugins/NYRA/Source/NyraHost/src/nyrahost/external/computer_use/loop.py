"""Computer-use orchestrator loop.

Implements the screenshot -> model -> action -> repeat cycle with hard
caps and a permission gate. The model integration is parameterised
(``ComputerUseBackend``) so tests inject a fake and Phase 5.1 can swap
between the Anthropic Messages API and the Claude CLI subprocess driver
once SC#1 clears.

Loop contract (per Phase 5 review hardening list):
  - max_iterations cap (default 20) — refuses to run forever
  - max_wall_clock_seconds cap (default 300) — same idea, time-based
  - permission_gate.await_decision(...) BEFORE every mutating action
  - Ctrl+Alt+Space pause hotkey via ``check_pause`` injection point
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional, Protocol

import structlog

from .actions import ActionResult, BoundedWindow, ScreenCapture, Win32Actions

log = structlog.get_logger("nyrahost.external.computer_use.loop")

DEFAULT_MAX_ITERATIONS = 20
DEFAULT_MAX_WALL_SECONDS = 300


class ComputerUsePaused(Exception):
    """Raised when the user pressed Ctrl+Alt+Space mid-loop."""


class ComputerUseSessionLimitExceeded(Exception):
    """Raised when iteration or wall-clock cap is hit."""


# Read-only actions don't trigger the permission gate.
READ_ONLY_ACTIONS = frozenset({"screenshot", "wait", "zoom"})


@dataclass
class LoopResult:
    """Final outcome of a computer-use session."""
    success: bool
    iterations: int
    elapsed_seconds: float
    last_message: str = ""
    actions: list[str] = field(default_factory=list)


class ComputerUseBackend(Protocol):
    """Contract for the model side of the loop.

    Implementations:
      - ``AnthropicComputerUseBackend`` — uses ``anthropic.Messages`` with
        ``computer_20251124`` tool (when ANTHROPIC_API_KEY available)
      - ``ClaudeCLIComputerUseBackend`` — drives the user's local
        ``claude`` CLI via stream-json so the user's Claude Pro
        subscription is the auth path (when SC#1 clears)
      - ``FakeBackend`` — for tests
    """

    async def step(
        self,
        screenshot_path: Path,
        history: list[dict],
        goal: str,
    ) -> dict:
        """Send the screenshot + goal + history; return the model's next action.

        Returns a dict like::

            {"action": "click", "x": 100, "y": 200, "rationale": "..."}
            {"action": "type_text", "text": "...", "rationale": "..."}
            {"action": "done", "summary": "..."}
        """
        ...


@dataclass
class ComputerUseLoop:
    """Orchestrates a bounded computer-use session over a single window.

    Construction is dependency-injected so tests can stub the model,
    actions, screenshotter, and permission gate independently.
    """
    window: BoundedWindow
    backend: ComputerUseBackend
    actions: Win32Actions
    capture: ScreenCapture
    permission_gate: Callable[[dict], Awaitable[bool]]
    check_pause: Callable[[], bool] = lambda: False
    workspace: Path = field(default_factory=lambda: Path.cwd() / ".nyra-computer-use")
    max_iterations: int = DEFAULT_MAX_ITERATIONS
    max_wall_seconds: float = DEFAULT_MAX_WALL_SECONDS

    async def run(self, goal: str) -> LoopResult:
        """Drive the loop toward ``goal``. Returns the final result.

        Raises:
            ComputerUseSessionLimitExceeded: iteration / wall-clock cap hit
            ComputerUsePaused: user pressed the pause hotkey
        """
        history: list[dict] = []
        actions_log: list[str] = []
        started = time.monotonic()
        self.workspace.mkdir(parents=True, exist_ok=True)

        for i in range(1, self.max_iterations + 1):
            elapsed = time.monotonic() - started
            if elapsed > self.max_wall_seconds:
                raise ComputerUseSessionLimitExceeded(
                    f"wall-clock {elapsed:.1f}s exceeded "
                    f"{self.max_wall_seconds}s cap"
                )
            if self.check_pause():
                raise ComputerUsePaused(
                    "Ctrl+Alt+Space — user paused the loop"
                )

            # Capture
            shot_path = self.workspace / f"step_{i:03d}.png"
            try:
                self.capture.grab(shot_path)
            except NotImplementedError:
                # Skeleton fallback — tests inject a fake capture.
                shot_path.write_bytes(b"")

            # Ask the model what to do next
            step = await self.backend.step(shot_path, history, goal)
            history.append({"step": i, "model_response": step})

            action = step.get("action", "")
            if action == "done":
                summary = step.get("summary", "")
                log.info(
                    "computer_use_done",
                    iterations=i,
                    elapsed=elapsed,
                    summary=summary,
                )
                return LoopResult(
                    success=True,
                    iterations=i,
                    elapsed_seconds=elapsed,
                    last_message=summary,
                    actions=actions_log,
                )

            # Permission gate fires before any mutating action
            if action not in READ_ONLY_ACTIONS:
                approved = await self.permission_gate(step)
                if not approved:
                    log.info(
                        "computer_use_action_rejected",
                        iteration=i,
                        action=action,
                    )
                    return LoopResult(
                        success=False,
                        iterations=i,
                        elapsed_seconds=time.monotonic() - started,
                        last_message=f"action_rejected:{action}",
                        actions=actions_log,
                    )

            result = await self._dispatch(step)
            actions_log.append(result.detail)
            history.append({"step": i, "action_result": result.detail})
            if not result.ok:
                log.warning(
                    "computer_use_action_failed",
                    iteration=i,
                    detail=result.detail,
                )

        # Iteration cap
        raise ComputerUseSessionLimitExceeded(
            f"iteration cap {self.max_iterations} hit without `done`"
        )

    async def _dispatch(self, step: dict) -> ActionResult:
        action = step.get("action", "")
        if action == "click":
            return self.actions.click(
                int(step["x"]), int(step["y"]),
                button=step.get("button", "left"),
            )
        if action == "double_click":
            return self.actions.double_click(int(step["x"]), int(step["y"]))
        if action == "move":
            return self.actions.move(int(step["x"]), int(step["y"]))
        if action == "scroll":
            return self.actions.scroll(
                int(step["x"]), int(step["y"]),
                delta=int(step.get("delta", 120)),
            )
        if action == "type_text":
            return self.actions.type_text(str(step["text"]))
        if action == "key":
            return self.actions.key(int(step["vk_code"]))
        if action == "wait":
            await asyncio.sleep(float(step.get("seconds", 1.0)))
            return ActionResult(ok=True, detail="wait")
        if action == "screenshot":
            return ActionResult(ok=True, detail="screenshot")
        return ActionResult(ok=False, detail=f"unknown_action:{action}")
