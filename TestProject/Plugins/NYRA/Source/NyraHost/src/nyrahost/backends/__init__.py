"""nyrahost.backends — pluggable backend abstraction (Plan 02-03).

Exports:
    AgentBackend     : ABC for all reasoning backends
    BackendEvent    : tagged union — Delta | ToolUse | ToolResult | Done | Error | Retry
    Delta           : text chunk from model
    ToolUse         : model invoked a tool
    ToolResult      : result of a tool call
    Done            : final event with usage metadata
    Error           : error with code + remediation
    Retry           : retry attempt with delay + category
    HealthState     : str Enum — ready | not-installed | auth-drift | rate-limited | offline | unknown
    GemmaBackend    : Phase 1 Gemma adapter wrapping InferRouter
    ClaudeBackend   : Phase 2 Claude Code CLI subprocess driver (SC#1 gated)
    BACKEND_REGISTRY: dict[str, type[AgentBackend]]
    get_backend(name) -> type[AgentBackend]
"""
from __future__ import annotations

from nyrahost.backends.base import (
    AgentBackend,
    BackendEvent,
    Delta,
    Done,
    Error,
    HealthState,
    Retry,
    ToolResult,
    ToolUse,
)
from nyrahost.backends.gemma import GemmaBackend
from nyrahost.backends.claude import ClaudeBackend

BACKEND_REGISTRY: dict[str, type[AgentBackend]] = {
    "gemma-local": GemmaBackend,
    "claude": ClaudeBackend,
}


def get_backend(name: str) -> type[AgentBackend]:
    """Factory: return the registered backend class for ``name``."""
    try:
        return BACKEND_REGISTRY[name]
    except KeyError as e:
        raise ValueError(
            f"Unknown backend: {name!r}. Registered: {list(BACKEND_REGISTRY)}"
        ) from e


__all__ = [
    "AgentBackend",
    "BackendEvent",
    "Delta",
    "Done",
    "Error",
    "GemmaBackend",
    "HealthState",
    "Retry",
    "ToolResult",
    "ToolUse",
    "BACKEND_REGISTRY",
    "get_backend",
]
