"""nyrahost.tools.base — Base tool classes for NYRA MCP tools."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


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
