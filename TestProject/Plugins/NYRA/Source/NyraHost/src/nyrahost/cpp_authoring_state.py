"""nyrahost.cpp_authoring_state — Plan 08-02 PARITY-02 session-scoped allowlist.

Per CONTEXT.md §"Out of Scope":
    Live Coding C++ for non-NYRA-authored code. Plan 08-02 ships authoring
    + recompile loops only for files NYRA created in the session.

This module is the runtime gate. Every PARITY-02 mutator that writes a file
calls `record_authored(path)`; `nyra_cpp_recompile` validates the targeted
module's source files against `is_authored(path)` before triggering a
compile. Files NYRA did NOT author this session abort the recompile with
the Out-of-Scope explanation.

Module-scoped — process lifetime = session lifetime. No persistence
(intentional — fresh session = fresh allowlist; matches
`safe_mode.NyraPermissionGate` lifecycle).

Pattern reference: PATTERNS.md §PARITY-02 + RESEARCH.md §Pre-condition gate.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Iterable

__all__ = [
    "record_authored",
    "is_authored",
    "clear_session",
    "snapshot_authored",
]


_lock = threading.Lock()
_authored_files: set[Path] = set()


def _normalize(path: Path | str) -> Path:
    """Resolve to absolute, casefold-normalised Path.

    Windows is case-insensitive; we normalise via `Path.resolve(strict=False)`
    so `C:/Foo/Bar.cpp` and `c:\\foo\\bar.cpp` collapse to the same key. The
    `strict=False` form tolerates not-yet-created files: the mutator records
    the path *after* writing, so the file exists at record time, but
    `is_authored` may be queried before the file has flushed to disk on
    slow filesystems — `resolve(strict=False)` doesn't raise in that case.
    """
    return Path(path).resolve(strict=False)


def record_authored(path: Path | str) -> None:
    """Mark `path` as authored by NYRA in the current session."""
    with _lock:
        _authored_files.add(_normalize(path))


def is_authored(path: Path | str) -> bool:
    """Return True iff `path` is in the session-scoped NYRA-authored set."""
    with _lock:
        return _normalize(path) in _authored_files


def clear_session() -> None:
    """Reset the allowlist. Used by tests; intentionally not exposed to MCP."""
    with _lock:
        _authored_files.clear()


def snapshot_authored() -> frozenset[Path]:
    """Return an immutable snapshot for diagnostics / testing."""
    with _lock:
        return frozenset(_authored_files)


def record_authored_many(paths: Iterable[Path | str]) -> None:
    """Bulk-record helper used by `nyra_cpp_module_create` (which writes
    several files in one transaction)."""
    with _lock:
        for p in paths:
            _authored_files.add(_normalize(p))
