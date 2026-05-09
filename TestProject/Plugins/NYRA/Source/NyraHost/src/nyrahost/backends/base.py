"""AgentBackend ABC + BackendEvent tagged union (Plan 02-03).

Defines the abstract interface every reasoning backend (Claude, Gemma, Codex)
must implement. Phase 1's Gemma/InferRouter path becomes GemmaBackend —
a drop-in adapter. Plan 02-04 fills in ClaudeBackend once SC#1 clears.
"""
from __future__ import annotations

import abc
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal, Union

from nyrahost.attachments import AttachmentRef


class HealthState(str, Enum):
    """JSON-friendly health state for diagnostics/backend-state notification."""

    READY = "ready"
    NOT_INSTALLED = "not-installed"
    AUTH_DRIFT = "auth-drift"
    RATE_LIMITED = "rate-limited"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Delta:
    """A single text chunk streamed from the model."""

    text: str


@dataclass(frozen=True)
class ToolUse:
    """Model invoked a tool."""

    id: str
    name: str
    input_json: str  # partial or complete JSON string


@dataclass(frozen=True)
class ToolResult:
    """Result returned from a tool call."""

    id: str
    output: str


@dataclass(frozen=True)
class Done:
    """Terminal event — stream completed successfully."""

    usage: dict       # e.g. {"input_tokens": 1, "output_tokens": 2}
    stop_reason: str  # "end_turn" | "tool_use" | "max_tokens" | "error" | "cancelled"


@dataclass(frozen=True)
class Error:
    """Non-retryable or exhausted-retry error."""

    code: int          # JSON-RPC error code (see ERROR_CODES.md)
    message: str       # short programmatic name
    remediation: str   # user-facing remediation string
    retryable: bool    # true if a retry with backoff may succeed


@dataclass(frozen=True)
class Retry:
    """Retryable error — model is asking the caller to retry after a delay."""

    attempt: int
    delay_ms: int
    error_category: Literal[
        "authentication_failed",
        "billing_error",
        "rate_limit",
        "invalid_request",
        "server_error",
        "max_output_tokens",
        "unknown",
    ]


# Tagged union — all six event variants.
BackendEvent = Union[Delta, ToolUse, ToolResult, Done, Error, Retry]


class AgentBackend(abc.ABC):
    """Abstract base class for every reasoning backend (Claude, Gemma, Codex).

    Subclasses MUST implement:
        name          : class-level str ("gemma-local" | "claude" | ...)
        send(...)     : emit BackendEvent objects via on_event; MUST end with Done or Error
        cancel(...)   : cancel the in-flight request
        health_check(): return current HealthState
    """

    name: str  # "claude" | "gemma-local" | "codex" (v1.1)

    @abc.abstractmethod
    async def send(
        self,
        conversation_id: str,
        req_id: str,
        content: str,
        attachments: list[AttachmentRef],
        mcp_config_path: Path | None,
        on_event: Callable[[BackendEvent], Awaitable[None]],
    ) -> None:
        """Emit BackendEvent objects via ``on_event``; MUST end with Done or Error."""

    @abc.abstractmethod
    async def cancel(self, req_id: str) -> None:
        """Cancel the in-flight request matching ``req_id``."""

    @abc.abstractmethod
    async def health_check(self) -> HealthState:
        """Return the backend's current readiness state."""
