"""nyrahost.tools.base — Base tool classes for NYRA MCP tools."""
from __future__ import annotations

import asyncio
import concurrent.futures
from dataclasses import dataclass
from typing import Any, Awaitable, Optional, TypeVar


_T = TypeVar("_T")


def run_async_safely(coro: Awaitable[_T]) -> _T:
    """Block-and-await a coroutine from any context.

    NyraTool.execute is sync-by-contract (returns NyraToolResult, not a
    coroutine). When the calling thread is already inside a running event loop
    (e.g. NyraHost dispatches the tool from an async WebSocket handler),
    `asyncio.run` raises RuntimeError. This helper detects that case and
    runs the coroutine in a one-shot worker thread so the call always
    completes synchronously without deadlocking.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


@dataclass
class NyraToolResult:
    """Result of a NyraTool.execute() call."""

    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None

    @classmethod
    def ok(cls, data: dict[str, Any]) -> "NyraToolResult":
        return cls(data=data, error=None)

    @classmethod
    def err(cls, error: str) -> "NyraToolResult":
        return cls(data=None, error=error)

    @property
    def is_ok(self) -> bool:
        return self.error is None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-RPC-shaped dict.

        Phase 4 BL-01: mcp_server/__init__.py dispatches every tool result
        through `result.to_dict()`. Without this method, every tool call
        raised AttributeError and was wrapped as -32000 internal_error.
        Errors map to the JSON-RPC error envelope; ok results return data.
        """
        if self.error is not None:
            return {"error": {"code": -32000, "message": self.error}}
        return self.data or {}


class NyraTool:
    """Base class for all NYRA MCP tools.

    Subclasses must define:
      name: str          — MCP tool name
      description: str   — human-readable description
      parameters: dict  — JSON Schema for the tool's input

    and implement:
      execute(params: dict) -> NyraToolResult
    """

    name: str = ""
    description: str = ""
    parameters: dict = {}

    def execute(self, params: dict) -> NyraToolResult:
        raise NotImplementedError(f"{self.__class__.__name__} must implement execute()")
