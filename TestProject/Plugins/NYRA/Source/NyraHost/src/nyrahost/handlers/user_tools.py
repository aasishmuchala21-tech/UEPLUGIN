"""user_tools/* WS handlers — Phase 14-D."""
from __future__ import annotations

from pathlib import Path
from typing import Final, Optional

from nyrahost.user_tools import UserToolsLoader

ERR_BAD_INPUT: Final[int] = -32602
ERR_TOOL_NOT_FOUND: Final[int] = -32057
ERR_TOOL_FAILED: Final[int] = -32058


def _err(code: int, message: str, detail: str = "", remediation: Optional[str] = None) -> dict:
    data: dict = {}
    if detail:
        data["detail"] = detail
    if remediation:
        data["remediation"] = remediation
    out: dict = {"error": {"code": code, "message": message}}
    if data:
        out["error"]["data"] = data
    return out


class UserToolsHandlers:
    def __init__(self, loader: UserToolsLoader) -> None:
        self._loader = loader
        self._tools = loader.load_all()

    @property
    def loader(self) -> UserToolsLoader:
        return self._loader

    @property
    def tools(self) -> dict:
        return dict(self._tools)

    async def on_list(self, params: dict, session=None, ws=None) -> dict:
        return {
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                    "source_path": str(t.source_path),
                }
                for t in self._tools.values()
            ],
            "errors": self._loader.errors,
            "tools_dir": str(self._loader.tools_dir),
        }

    async def on_reload(self, params: dict, session=None, ws=None) -> dict:
        # Re-discover + reload from scratch.
        from nyrahost.user_tools import UserToolsLoader as _L
        new_loader = _L(tools_dir=self._loader.tools_dir)
        self._loader = new_loader
        self._tools = new_loader.load_all()
        return await self.on_list(params, session, ws)

    async def on_invoke(self, params: dict, session=None, ws=None) -> dict:
        name = params.get("name")
        if not isinstance(name, str) or not name:
            return _err(ERR_BAD_INPUT, "missing_field", "name")
        tool = self._tools.get(name)
        if tool is None:
            return _err(ERR_TOOL_NOT_FOUND, "tool_not_found", name)
        try:
            return await tool.execute(params.get("args", {}), session, ws)
        except Exception as exc:  # noqa: BLE001 — surface to user via -32058
            return _err(ERR_TOOL_FAILED, "tool_execute_failed", f"{type(exc).__name__}: {exc}")


__all__ = ["UserToolsHandlers", "ERR_BAD_INPUT", "ERR_TOOL_NOT_FOUND", "ERR_TOOL_FAILED"]
