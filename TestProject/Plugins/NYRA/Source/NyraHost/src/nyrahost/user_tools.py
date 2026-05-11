"""nyrahost.user_tools — Phase 14-D user-installable MCP tools (Tier 2 moat).

Aura is closed; users cannot extend its agent. NYRA exposes a
contract: drop a Python file under
``TestProject/Plugins/NYRA/UserTools/<your_tool>.py`` and on next
NyraHost spawn the tool is auto-discovered, gated through
NyraPermissionGate, and callable from Claude / Gemma like any other
MCP tool.

Contract (each user tool file declares):

    NYRA_TOOL = {
        "name": "my_tool",
        "description": "What it does, one line.",
        "input_schema": { ... JSON-Schema ... },
    }

    async def execute(params: dict, session=None, ws=None) -> dict:
        ...

The loader:
  * Walks UserToolsDir for *.py
  * Skips files that don't define both NYRA_TOOL and execute
  * Refuses tools whose name collides with a built-in (closed-set check)
  * Logs each load decision with a structured event so the audit log
    captures "user-tool X loaded at startup"

Threat model:
  * T-14-01: tools live OUTSIDE the plugin's source tree (under a
    user-writable UserTools dir), so the user accepts that they
    can run arbitrary code. The README explicitly tells users not
    to drop someone else's code there blind.
  * T-14-02: tools cannot mutate UE state without going through the
    NyraPermissionGate — same gate the built-in tools obey.
  * T-14-03: the loader catches ALL exceptions during import so a
    broken user tool never breaks NyraHost startup; the offending
    file is logged + skipped.
"""
from __future__ import annotations

import importlib.util
import inspect
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Final, Iterable

import structlog

log = structlog.get_logger("nyrahost.user_tools")

# Names reserved for built-in tools — colliding user tools refused.
RESERVED_NAMES: Final[frozenset[str]] = frozenset({
    "nyra_console_exec",
    "nyra_blockout_room",
    "nyra_auto_rig_mesh",
    "meshy_image_to_3d",
    "comfyui_run_workflow",
    "asset_search",
    "perf_profile",
    "blueprint_review",
    # Phase 13 additions
    "hygiene_run",
    "perf_budget_check",
    "timeline_add",
})


@dataclass
class UserTool:
    name: str
    description: str
    input_schema: dict
    execute: Callable[..., Awaitable[dict]]
    source_path: Path


@dataclass
class UserToolsLoader:
    """Discovers + loads user tools from a directory."""

    tools_dir: Path
    _loaded: dict[str, UserTool] = field(default_factory=dict)
    _errors: list[dict] = field(default_factory=list)

    def discover(self) -> list[Path]:
        if not self.tools_dir.exists():
            return []
        return sorted(p for p in self.tools_dir.glob("*.py") if p.is_file())

    def load_all(self) -> dict[str, UserTool]:
        for path in self.discover():
            self._try_load_one(path)
        return dict(self._loaded)

    @property
    def errors(self) -> list[dict]:
        """Return non-fatal load errors for surfacing in the UI."""
        return list(self._errors)

    def _try_load_one(self, path: Path) -> None:
        mod_name = f"nyra_user_tool__{path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(mod_name, path)
            if spec is None or spec.loader is None:
                self._errors.append({"path": str(path), "error": "spec_from_file_location_failed"})
                return
            module = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = module
            spec.loader.exec_module(module)   # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001 — T-14-03
            self._errors.append({"path": str(path), "error": f"{type(exc).__name__}: {exc}"})
            return

        meta = getattr(module, "NYRA_TOOL", None)
        ex = getattr(module, "execute", None)
        if not isinstance(meta, dict):
            self._errors.append({"path": str(path), "error": "missing_NYRA_TOOL"})
            return
        if not callable(ex):
            self._errors.append({"path": str(path), "error": "missing_execute"})
            return
        if not inspect.iscoroutinefunction(ex):
            self._errors.append({
                "path": str(path),
                "error": "execute_must_be_async",
            })
            return
        name = meta.get("name")
        if not isinstance(name, str) or not name:
            self._errors.append({"path": str(path), "error": "NYRA_TOOL.name_missing"})
            return
        if name in RESERVED_NAMES:
            self._errors.append({
                "path": str(path),
                "error": f"name_reserved: {name}",
            })
            return
        if name in self._loaded:
            self._errors.append({
                "path": str(path),
                "error": f"duplicate_name: {name}",
            })
            return
        self._loaded[name] = UserTool(
            name=name,
            description=str(meta.get("description", "")),
            input_schema=dict(meta.get("input_schema", {})),
            execute=ex,
            source_path=path,
        )
        log.info("user_tool_loaded", name=name, source=str(path))


__all__ = [
    "UserTool",
    "UserToolsLoader",
    "RESERVED_NAMES",
]
