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


# ---------------------------------------------------------------------------
# Phase 4 BL-04 / BL-05 / BL-06 helpers
#
# Three systemic gaps the cross-phase review found in Phase 4:
#
#   BL-04: every UE-mutating tool should run inside a session transaction
#          so chat/cancel can roll back.
#   BL-05: every mutator should consult an idempotency cache keyed on
#          (tool, operation, params) so a double-call doesn't double-spawn.
#   BL-06: every mutator should re-fetch state to confirm the operation
#          succeeded before returning ok.
#
# These helpers give tools a uniform surface so the per-tool fix is a
# 3-line wrapper rather than a redesign.
# ---------------------------------------------------------------------------

import contextlib as _contextlib
import hashlib as _hashlib
import json as _json
import threading as _threading
from typing import Callable, Iterator


# Process-local idempotency cache. Key: (tool_name, params_hash). Value:
# the result dict the prior invocation returned. v1 keeps this in-memory;
# Phase 8 may persist to LOCALAPPDATA if the operator wants idempotency
# across editor restarts.
_IDEMPOTENCY_CACHE: dict[tuple[str, str], dict[str, Any]] = {}
_IDEMPOTENCY_LOCK = _threading.Lock()


def idempotency_key(tool_name: str, params: dict) -> tuple[str, str]:
    """Compute a deterministic (tool_name, params_hash) cache key.

    BL-05: hash the JSON-canonicalised params (sort_keys=True, default=str
    for non-JSON values) so the same logical input produces the same key
    regardless of dict iteration order. Hash truncated to 16 hex chars
    (64-bit collision space — fine for in-memory dedup).
    """
    payload = _json.dumps(params, sort_keys=True, default=str)
    h = _hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return (tool_name, h)


def idempotent_lookup(tool_name: str, params: dict) -> Optional[dict[str, Any]]:
    """BL-05: return the cached result for (tool, params) if present, else None."""
    key = idempotency_key(tool_name, params)
    with _IDEMPOTENCY_LOCK:
        return _IDEMPOTENCY_CACHE.get(key)


def idempotent_record(tool_name: str, params: dict, data: dict[str, Any]) -> None:
    """BL-05: record the successful result so a future identical call dedups."""
    key = idempotency_key(tool_name, params)
    with _IDEMPOTENCY_LOCK:
        _IDEMPOTENCY_CACHE[key] = data


def idempotent_clear() -> None:
    """Test/diagnostic helper to drop the in-memory idempotency cache."""
    with _IDEMPOTENCY_LOCK:
        _IDEMPOTENCY_CACHE.clear()


@_contextlib.contextmanager
def session_transaction(label: str) -> Iterator[None]:
    """BL-04: open a UE editor undo transaction around a tool's mutations.

    Tools call this as `with session_transaction("nyra_actor_spawn"):` so
    the user's Ctrl+Z reverts the whole NYRA contribution. When the
    `unreal` Python module is unavailable (e.g. inside pytest), this is
    a no-op so tests that don't exercise the editor still pass through.

    The label is what shows in UE's Edit > Undo History panel.
    """
    try:
        import unreal  # type: ignore
    except ImportError:
        yield
        return
    txn = None
    try:
        # ScopedEditorTransaction was added in 5.4+; fall back to the
        # bare yield if not present (tools still run; just no rollback).
        if hasattr(unreal, "ScopedEditorTransaction"):
            txn = unreal.ScopedEditorTransaction(label)
        yield
    finally:
        # Closing the transaction commits it. UE's UTransBuffer handles
        # rollback when the user presses Ctrl+Z. Plan 02-08's
        # NyraTransactionManager.cancel() will flow through this same
        # buffer.
        if txn is not None:
            try:
                txn.cancel = False  # commit on scope exit
            except AttributeError:
                pass


def verify_post_condition(
    label: str,
    check: Callable[[], bool],
) -> Optional[str]:
    """BL-06: run a post-condition check; return error string on failure.

    Tools call this after their mutation to confirm the world reflects
    the change before returning `ok`. Returns None on success or the
    error message ready to drop into `NyraToolResult.err(...)`.

    Example:
        err = verify_post_condition(
            "actor_spawn",
            lambda: unreal.EditorLevelLibrary.get_actor_reference(path) is not None,
        )
        if err:
            return NyraToolResult.err(err)
    """
    try:
        ok = bool(check())
    except Exception as e:
        return f"post_condition_check_raised: {label}: {e}"
    if not ok:
        return f"post_condition_failed: {label}"
    return None
