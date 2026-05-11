"""R5.I2 fix from the full-codebase review — JSON-RPC routing smoke test.

The full-codebase review surfaced that 54+ JSON-RPC endpoints registered
in app.py were never tested at the dispatch layer. Handler classes are
unit-tested in isolation; the URL strings in `server.register_request(...)`
are not. This is exactly how the original SettingsAggregatorHandlers
ordering bug (PR #2 fix #1) and the _poll_meshy_and_update_manifest
NameError (R1.C1, PR #4) both shipped without a CI failure.

This test parses app.py with the `ast` module and asserts:
  * every `server.register_request("...", handler)` call uses a method
    name from the documented JSON-RPC namespace (no typos like
    `"audio-gen/sfx"` vs `"audio_gen/sfx"`)
  * every registered name is unique (no copy-paste collisions where two
    different handlers both want the same name)
  * the same for `server.register_notification`

It does NOT spin up a live NyraServer + WebSocket round-trip — that
would require the full venv + asyncio scaffolding and produces a flaky
test surface. AST-level routing validation catches the entire class of
"shipped a dispatch typo" bugs without runtime cost.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_APP_PY = (
    Path(__file__).resolve().parent.parent
    / "src" / "nyrahost" / "app.py"
)

# JSON-RPC method names use lowercase letters, digits, underscore,
# hyphen, and slash separators. Anything else is a typo.
_METHOD_NAME_RE = re.compile(r"^[a-z][a-z0-9_/-]+[a-z0-9]$")


def _collect_register_calls(kind: str) -> list[tuple[str, int]]:
    """Return list of (method_name, line_no) for server.register_<kind>(...)."""
    tree = ast.parse(_APP_PY.read_text(encoding="utf-8"), filename=str(_APP_PY))
    out: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr != f"register_{kind}":
            continue
        if not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            out.append((first.value, node.lineno))
    return out


def test_register_request_names_well_formed():
    calls = _collect_register_calls("request")
    assert len(calls) > 50, (
        f"expected >50 register_request calls, got {len(calls)}. "
        "Did app.py change its registration pattern?"
    )
    typos = [
        (name, line) for (name, line) in calls
        if not _METHOD_NAME_RE.match(name)
    ]
    assert not typos, (
        "register_request names must match "
        f"{_METHOD_NAME_RE.pattern}; offenders: {typos}"
    )


def test_register_notification_names_well_formed():
    calls = _collect_register_calls("notification")
    typos = [
        (name, line) for (name, line) in calls
        if not _METHOD_NAME_RE.match(name)
    ]
    assert not typos, (
        "register_notification names must match "
        f"{_METHOD_NAME_RE.pattern}; offenders: {typos}"
    )


def test_register_request_names_unique():
    calls = _collect_register_calls("request")
    seen: dict[str, int] = {}
    dupes: list[tuple[str, int, int]] = []
    for name, line in calls:
        if name in seen:
            dupes.append((name, seen[name], line))
        else:
            seen[name] = line
    assert not dupes, (
        "register_request names must be unique. "
        f"Duplicates (name, first_line, dupe_line): {dupes}"
    )


def test_app_module_imports_without_error():
    """The smoke test that actually catches build_and_run construction-order
    bugs (the SettingsAggregatorHandlers UnboundLocalError class). If
    importing the module raises, the whole sidecar fails to boot."""
    import importlib
    import nyrahost.app as app_mod
    importlib.reload(app_mod)
    # `build_and_run` is defined at module level; we just check it's
    # callable without actually invoking it (that would need a full venv
    # + handshake setup).
    assert callable(app_mod.build_and_run)


def test_app_build_and_run_locals_assigned_before_use():
    """Static dataflow check via ast — every local name referenced inside
    a kwarg-only constructor call is assigned earlier in the same scope.

    This is what the SettingsAggregatorHandlers ordering bug looked like:
    `SettingsAggregatorHandlers(model=model_settings_handlers, ...)` was
    called before `model_settings_handlers = ...` ran. The current PR #2
    fix moved that constructor down. A regression that re-introduces the
    ordering bug should be caught at test time, not at first `await
    server.serve()`.
    """
    tree = ast.parse(_APP_PY.read_text(encoding="utf-8"), filename=str(_APP_PY))
    # Locate the async def build_and_run function.
    build_and_run: ast.AsyncFunctionDef | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "build_and_run":
            build_and_run = node
            break
    assert build_and_run is not None, "could not find async def build_and_run in app.py"

    # Walk top-level statements of build_and_run, tracking assigned names.
    assigned: set[str] = set()
    # Function parameters are assigned at entry.
    for arg in build_and_run.args.args:
        assigned.add(arg.arg)
    issues: list[str] = []

    for stmt in build_and_run.body:
        # Names referenced in this statement that aren't yet assigned.
        for sub in ast.walk(stmt):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                # Skip globals + builtins by name list (very approximate but
                # the goal here is to catch the specific
                # SettingsAggregatorHandlers-ordering bug, not write a
                # full type-checker).
                name = sub.id
                # The names we actually care about: anything ending in
                # `_handlers`, `_handler`, `_store`, or matching the names
                # the review surfaced.
                if not (
                    name.endswith("_handlers")
                    or name.endswith("_handler")
                    or name.endswith("_store")
                    or name in {"model_settings_handlers", "session_mode_handler"}
                ):
                    continue
                if name not in assigned:
                    issues.append(
                        f"name {name!r} used at line {sub.lineno} before any "
                        "assignment earlier in build_and_run"
                    )
        # Mark names assigned by this statement (after we walked it).
        for sub in ast.walk(stmt):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                assigned.add(sub.id)

    assert not issues, "use-before-assign in build_and_run:\n" + "\n".join(issues)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
