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

# CR-06: bound the cumulative size of buffered partial_json strings per
# tool block, and the number of simultaneously open tool blocks. Without
# these caps a malicious or misbehaving LLM emitting megabytes of
# input_json_delta events without a closing content_block_stop will OOM
# the NyraHost process.
_MAX_TOOL_INPUT_BYTES = 1 * 1024 * 1024  # 1 MiB
_MAX_OPEN_TOOL_BLOCKS = 8


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
            # CR-07: Claude CLI emits this field as `delay_ms`, not
            # `retry_delay_ms`. The previous accessor returned 0 on
            # every real retry event so the router's backoff fired
            # with no delay. Read both forms so a future CLI rename
            # in either direction doesn't silently regress to 0.
            delay_ms: int = int(
                obj.get("delay_ms")
                or obj.get("retry_delay_ms")
                or 0
            )
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
                # CR-07: Anthropic Messages SSE schema puts the text
                # under `delta.text`, not `delta.text_delta`. The
                # previous accessor returned "" for every real text
                # delta so the chat panel saw zero tokens. Read both
                # so a fixture / older CLI wire shape still flows.
                text_value = delta_obj.get("text") or delta_obj.get("text_delta") or ""
                return [Delta(text=text_value)]
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
            # CR-06: cap the number of simultaneously open tool blocks so
            # an adversary cannot omit content_block_stop and accumulate
            # unbounded buffers. Drop new opens past the cap; the dropped
            # tool_use's deltas will land on a no-existing-block path
            # below and be silently discarded (acceptable; the ToolUse
            # event is already emitted with empty input).
            if len(self._tool_buf) >= _MAX_OPEN_TOOL_BLOCKS:
                log.warning(
                    "tool_block_open_cap",
                    open_count=len(self._tool_buf),
                    cap=_MAX_OPEN_TOOL_BLOCKS,
                )
                return [ToolUse(id=tool_id, name=tool_name, input_json="")]
            self._tool_buf[tool_id] = {
                "name": tool_name,
                "input_parts": [],
                "_size": 0,  # CR-06: cumulative byte counter
            }
            return [ToolUse(id=tool_id, name=tool_name, input_json="")]
        return []

    def _handle_input_json_delta(
        self, event: dict, delta_obj: dict
    ) -> list[BackendEvent]:
        # The index field identifies which block this delta belongs to.
        # WR-10 fix: prefer event.index → tool_id mapping at content_block_start
        # time over "last-opened" heuristic, but maintain backwards-compat
        # with single-block streams.
        partial = delta_obj.get("partial_json", "")
        if not isinstance(partial, str):
            return []
        if not self._tool_buf:
            return []
        # Map by index when available.
        idx = event.get("index")
        target_id: str | None = None
        if isinstance(idx, int):
            for tid, buf in self._tool_buf.items():
                if buf.get("_index") == idx:
                    target_id = tid
                    break
        if target_id is None:
            # Fallback: most-recently-opened tool block.
            tool_ids = list(self._tool_buf.keys())
            if tool_ids:
                target_id = tool_ids[-1]
        if target_id is None:
            return []
        buf = self._tool_buf[target_id]
        # CR-06: cap the cumulative input bytes per tool block. Once a
        # buffer exceeds the cap, silently drop further deltas and emit
        # a one-time warning per block. The block's eventual ToolUse
        # event will carry whatever was accumulated up to the cap.
        size_now = buf.get("_size", 0)
        chunk = partial.encode("utf-8")
        if size_now + len(chunk) > _MAX_TOOL_INPUT_BYTES:
            if not buf.get("_capped"):
                log.warning(
                    "tool_input_too_large",
                    tool_id=target_id,
                    size=size_now,
                    cap=_MAX_TOOL_INPUT_BYTES,
                )
                buf["_capped"] = True
            return []
        buf["input_parts"].append(partial)
        buf["_size"] = size_now + len(chunk)
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
