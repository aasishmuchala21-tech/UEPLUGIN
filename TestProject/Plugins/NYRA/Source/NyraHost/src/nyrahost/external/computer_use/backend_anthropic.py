"""AnthropicComputerUseBackend — drives the Anthropic Messages API.

Uses the ``computer_20251124`` tool with Claude Opus 4.7 per CLAUDE.md
(beta header ``computer-use-2025-11-24``). Loaded only when the user has
``ANTHROPIC_API_KEY`` set or passes an explicit api_key — the loop's
DI surface lets v1.1 swap to a Claude-CLI subprocess driver once SC#1
clears, without changing the orchestrator.

Why ``anthropic`` is an optional dep, not a hard one:
  - It pulls httpx + tokenizers + a few hundred KB of helpers into the
    offline wheel cache.
  - The bundle is justified by image_to_3d, scene_orchestrator, and now
    computer-use, so this module imports it lazily so tests / offline
    paths still load.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Optional

import structlog

log = structlog.get_logger("nyrahost.external.computer_use.backend_anthropic")

# computer_20251124 long-edge cap (Opus 4.7) — matches actions.py.
ANTHROPIC_MODEL = "claude-opus-4-7"
COMPUTER_USE_BETA_HEADER = "computer-use-2025-11-24"
COMPUTER_USE_TOOL_TYPE = "computer_20251124"
DEFAULT_MAX_TOKENS = 1024


class AnthropicComputerUseBackend:
    """ComputerUseBackend implementation backed by Anthropic Messages."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        display_width_px: int = 1920,
        display_height_px: int = 1080,
        model: str = ANTHROPIC_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not configured. Set it via the editor "
                "Settings panel or pass api_key=... to the backend."
            )
        try:
            import anthropic  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "anthropic package not installed; v1.1 will bundle it. "
                "For now `pip install anthropic` in the venv."
            ) from exc
        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=self._api_key)
        self._display_w = display_width_px
        self._display_h = display_height_px
        self._model = model
        self._max_tokens = max_tokens

    async def step(
        self,
        screenshot_path: Path,
        history: list[dict],
        goal: str,
    ) -> dict:
        """Send the screenshot + goal to Claude; map its response to a
        ComputerUseLoop action dict."""
        try:
            png_bytes = screenshot_path.read_bytes()
        except OSError as exc:
            return {
                "action": "done",
                "summary": f"screenshot_read_failed: {exc}",
            }

        b64 = base64.b64encode(png_bytes).decode("ascii")
        user_content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": b64,
                },
            },
            {
                "type": "text",
                "text": (
                    f"Goal: {goal}\n\n"
                    "Use the computer tool to make progress. "
                    "When the goal is fully met, stop calling the tool "
                    "and end your reply with the word DONE."
                ),
            },
        ]
        try:
            resp = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                tools=[
                    {
                        "type": COMPUTER_USE_TOOL_TYPE,
                        "name": "computer",
                        "display_width_px": self._display_w,
                        "display_height_px": self._display_h,
                    }
                ],
                messages=[{"role": "user", "content": user_content}],
                extra_headers={"anthropic-beta": COMPUTER_USE_BETA_HEADER},
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("anthropic_step_failed", err=str(exc))
            return {"action": "done", "summary": f"anthropic_error: {exc}"}

        return _translate_response(resp)


def _translate_response(resp: Any) -> dict:
    """Map an Anthropic Messages response to a ComputerUseLoop action.

    Picks the first tool_use block with name=='computer' and translates
    its ``input.action`` to the loop's vocabulary. If no tool_use is
    present (model said DONE / asked a clarifying question), returns
    ``{"action": "done"}``.
    """
    tool_uses = [
        block for block in getattr(resp, "content", [])
        if getattr(block, "type", "") == "tool_use"
        and getattr(block, "name", "") == "computer"
    ]
    if not tool_uses:
        # Pull a summary line from the text blocks
        text_blocks = [
            getattr(b, "text", "")
            for b in getattr(resp, "content", [])
            if getattr(b, "type", "") == "text"
        ]
        summary = " ".join(t.strip() for t in text_blocks if t)
        return {"action": "done", "summary": summary[:280] or "no_tool_use"}

    action_input = getattr(tool_uses[0], "input", {}) or {}
    raw_action = action_input.get("action", "")

    # computer_20251124 vocabulary -> our internal one
    if raw_action == "screenshot":
        return {"action": "screenshot"}
    if raw_action == "wait":
        return {"action": "wait", "seconds": float(action_input.get("duration", 1.0))}
    if raw_action == "left_click":
        coord = action_input.get("coordinate", [0, 0])
        return {
            "action": "click",
            "x": int(coord[0]), "y": int(coord[1]),
            "button": "left",
        }
    if raw_action == "right_click":
        coord = action_input.get("coordinate", [0, 0])
        return {
            "action": "click",
            "x": int(coord[0]), "y": int(coord[1]),
            "button": "right",
        }
    if raw_action == "double_click":
        coord = action_input.get("coordinate", [0, 0])
        return {
            "action": "double_click",
            "x": int(coord[0]), "y": int(coord[1]),
        }
    if raw_action == "mouse_move":
        coord = action_input.get("coordinate", [0, 0])
        return {
            "action": "move",
            "x": int(coord[0]), "y": int(coord[1]),
        }
    if raw_action == "scroll":
        coord = action_input.get("coordinate", [0, 0])
        scroll_amount = int(action_input.get("scroll_amount", 1))
        direction = action_input.get("scroll_direction", "down")
        delta = scroll_amount * (120 if direction == "up" else -120)
        return {
            "action": "scroll",
            "x": int(coord[0]), "y": int(coord[1]),
            "delta": delta,
        }
    if raw_action in ("type", "key"):
        return {
            "action": "type_text" if raw_action == "type" else "key",
            "text": action_input.get("text", ""),
            "vk_code": action_input.get("vk_code", 0),
        }
    return {"action": "done", "summary": f"unknown_anthropic_action:{raw_action}"}
