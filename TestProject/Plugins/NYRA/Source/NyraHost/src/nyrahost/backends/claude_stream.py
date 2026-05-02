"""NDJSON line parser for Claude CLI --output-format stream-json (Plan 02-05).

Pure functions — no I/O. Consumes one NDJSON line and returns 0..n BackendEvent
objects. Handles all six event discriminators per RESEARCH §1.3:

  type=system, subtype=init          → cache session_id + model; emit nothing
  stream_event.event.content_block_delta(text_delta)
                                      → Delta(text=delta.text_delta)
  stream_event.event.content_block_start(tool_use)
                                      → ToolUse(id, name, input_json=''), buffered
  stream_event.event.content_block_delta(input_json_delta)
                                      → accumulate on current tool_use id
  stream_event.event.content_block_stop
                                      → emit final ToolUse with assembled input_json
  type=system, subtype=api_retry     → Retry(attempt, delay_ms, error_category)
  type=result                        → Done(usage, stop_reason)
  unknown type                        → log structlog warning, continue

Partial JSON buffering rule (D-08):
  ToolUse objects are emitted twice per invocation:
    1. on content_block_start:  input_json=''
    2. on content_block_stop:   input_json=<accumulated from all input_json_delta>
  The router layer handles assembling partial blocks for permission_gate
  (Plan 02-08); the parser emits each partial as-is.
"""
from __future__ import annotations

import json
import structlog
from typing import Literal

from nyrahost.backends.base import (
    BackendEvent,
    Delta,
    Done,
    Retry,
    ToolUse,
)

log = structlog.get_logger(__name__)

# Literal type aliases for the six known error categories carried in api_retry
_ErrorCategory = Literal[
    "authentication_failed",
    "billing_error",
    "rate_limit",
    "invalid_request",
    "server_error",
    "max_output_tokens",
    "unknown",
]


class StreamParser:
    """Stateful NDJSON line parser. Create one per subprocess stdout stream."""

    __slots__ = ("session_id", "model", "_tool_buf")

    def __init__(self) -> None:
        self.session_id: str | None = None
        """Cached from system/init lines."""

        self.model: str | None = None
        """Cached from system/init lines."""

        self._tool_buf: dict[str, dict]
        """id → {name, input_parts}. Accumulates input_json_delta pieces per id."""

        self._tool_buf = {}

    def parse_line(self, line: str) -> list[BackendEvent]:
        """Parse one NDJSON line; return 0–n BackendEvent objects.

        Raises
        ------
        ValueError
            If the line is not valid JSON (caller handles gracefully).
        """
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {line!r}") from exc

        msg_type = obj.get("type")
        if msg_type == "system":
            return self._handle_system(obj)
        elif msg_type == "stream_event":
            return self._handle_stream_event(obj)
        elif msg_type == "result":
            return self._handle_result(obj)
        else:
            log.warning("unknown_claude_stream_event_type", msg_type=msg_type, obj=obj)
            return []

    # ------------------------------------------------------------------
    # Internal dispatch
    # ------------------------------------------------------------------

    def _handle_system(self, obj: dict) -> list[BackendEvent]:
        subtype = obj.get("subtype", "")
        if subtype == "init":
            self.session_id = obj.get("session_id")
            self.model = obj.get("model")
            return []
        elif subtype == "api_retry":
            attempt: int = obj.get("attempt", 1)
            delay_ms: int = obj.get("retry_delay_ms", 0)
            raw_error: str = obj.get("error", "unknown")
            category: _ErrorCategory = _normalize_error_category(raw_error)
            return [Retry(attempt=attempt, delay_ms=delay_ms, error_category=category)]
        else:
            log.warning("unknown_system_subtype", subtype=subtype)
            return []

    def _handle_stream_event(self, obj: dict) -> list[BackendEvent]:
        event = obj.get("event", {})
        event_type = event.get("type", "")

        if event_type == "content_block_delta":
            delta_obj = event.get("delta", {})
            delta_type = delta_obj.get("type", "")
            if delta_type == "text_delta":
                return [Delta(text=delta_obj.get("text_delta", ""))]
            elif delta_type == "input_json_delta":
                return self._handle_input_json_delta(event, delta_obj)
            else:
                log.warning("unknown_delta_type", delta_type=delta_type)
                return []

        elif event_type == "content_block_start":
            return self._handle_content_block_start(event)

        elif event_type == "content_block_stop":
            return self._handle_content_block_stop(event)

        else:
            log.warning("unknown_stream_event_type", event_type=event_type)
            return []

    def _handle_content_block_start(self, event: dict) -> list[BackendEvent]:
        block = event.get("content_block", {})
        if block.get("type") == "tool_use":
            tool_id = block.get("id", "")
            tool_name = block.get("name", "")
            # Buffer the start for later accumulation
            self._tool_buf[tool_id] = {"name": tool_name, "input_parts": []}
            return [ToolUse(id=tool_id, name=tool_name, input_json="")]
        return []

    def _handle_input_json_delta(
        self, event: dict, delta_obj: dict
    ) -> list[BackendEvent]:
        # The index field identifies which block this delta belongs to
        # We track by id instead since index alone is ambiguous across block types
        partial = delta_obj.get("partial_json", "")
        # Try to find the most recently opened tool_use by scanning the buffer.
        # If not found (shouldn't happen in normal operation), discard.
        if self._tool_buf:
            # last-opened-id: maintain insertion order by popping and re-adding
            tool_ids = list(self._tool_buf.keys())
            if tool_ids:
                last_id = tool_ids[-1]
                self._tool_buf[last_id]["input_parts"].append(partial)
        return []

    def _handle_content_block_stop(self, event: dict) -> list[BackendEvent]:
        # Emit the final ToolUse with fully accumulated JSON for all buffered tools.
        # In practice Claude sends one stop per block; we emit for all open ids.
        emitted: list[BackendEvent] = []
        for tool_id, buf in list(self._tool_buf.items()):
            assembled = "".join(buf["input_parts"])
            emitted.append(
                ToolUse(id=tool_id, name=buf["name"], input_json=assembled)
            )
        self._tool_buf.clear()
        return emitted

    def _handle_result(self, obj: dict) -> list[BackendEvent]:
        usage: dict = obj.get("usage") or {}
        stop_reason: str = obj.get("stop_reason", "unknown")
        return [Done(usage=usage, stop_reason=stop_reason)]


# ------------------------------------------------------------------
# Module-level convenience function (matches test interface)
# ------------------------------------------------------------------

def parse_line(line: str) -> list[BackendEvent]:
    """Standalone parse_line() — creates a temporary StreamParser and delegates."""
    return StreamParser().parse_line(line)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _normalize_error_category(raw: str) -> _ErrorCategory:
    """Map Claude CLI error strings to the BackendEvent Retry error_category enum."""
    mapping: dict[str, _ErrorCategory] = {
        "authentication_failed": "authentication_failed",
        "billing_error": "billing_error",
        "rate_limit": "rate_limit",
        "invalid_request": "invalid_request",
        "server_error": "server_error",
        "max_output_tokens": "max_output_tokens",
    }
    return mapping.get(raw, "unknown")
