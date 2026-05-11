"""todos/* WS handlers — Phase 19-I Aura-parity todo list MCP tools.

Aura ships ``edit_todo_list`` + ``create_new_todo_list`` as MCP tools
the IDE side can call to maintain per-project task lists. NYRA mirrors
the surface with a tiny per-project JSON store at
``<Project>/Saved/NYRA/todos.json``.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Optional

import structlog

log = structlog.get_logger("nyrahost.handlers.todos")

ERR_BAD_INPUT: Final[int] = -32602
ERR_NO_LIST: Final[int] = -32085
MAX_LISTS: Final[int] = 32
MAX_ITEMS_PER_LIST: Final[int] = 256


@dataclass(frozen=True)
class TodoItem:
    id: str
    text: str
    done: bool
    created_at: float

    def to_dict(self) -> dict:
        return {"id": self.id, "text": self.text, "done": self.done,
                "created_at": self.created_at}


@dataclass(frozen=True)
class TodoList:
    list_id: str
    title: str
    items: tuple[TodoItem, ...]
    created_at: float

    def to_dict(self) -> dict:
        return {"list_id": self.list_id, "title": self.title,
                "items": [i.to_dict() for i in self.items],
                "created_at": self.created_at}


def _err(code: int, message: str, detail: str = "") -> dict:
    out: dict = {"error": {"code": code, "message": message}}
    if detail:
        out["error"]["data"] = {"detail": detail}
    return out


@dataclass
class TodosStore:
    project_dir: Path

    @property
    def path(self) -> Path:
        return Path(self.project_dir) / "Saved" / "NYRA" / "todos.json"

    def _read(self) -> dict:
        if not self.path.exists():
            return {"lists": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"lists": []}

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False,
            dir=str(self.path.parent),
            prefix=f".{self.path.name}.", suffix=".tmp",
        )
        try:
            json.dump(data, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()
            os.replace(tmp.name, self.path)
        except Exception:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            raise

    def create_list(self, title: str) -> dict:
        data = self._read()
        if len(data.get("lists", [])) >= MAX_LISTS:
            raise ValueError(f"max_lists_reached: {MAX_LISTS}")
        list_id = str(uuid.uuid4())[:8]
        data.setdefault("lists", []).append({
            "list_id": list_id,
            "title": str(title),
            "items": [],
            "created_at": time.time(),
        })
        self._write(data)
        return data["lists"][-1]

    def edit_list(self, *, list_id: str, ops: list[dict]) -> dict | None:
        """Apply edit operations: {op:'add', text} / {op:'check', id} /
        {op:'uncheck', id} / {op:'remove', id} / {op:'rename', title}."""
        data = self._read()
        for entry in data.get("lists", []):
            if entry.get("list_id") != list_id:
                continue
            items: list = entry.get("items", [])
            for op in ops:
                kind = op.get("op")
                if kind == "add":
                    if len(items) >= MAX_ITEMS_PER_LIST:
                        raise ValueError("max_items_reached")
                    items.append({
                        "id": str(uuid.uuid4())[:8],
                        "text": str(op.get("text", "")),
                        "done": False,
                        "created_at": time.time(),
                    })
                elif kind in ("check", "uncheck"):
                    for it in items:
                        if it.get("id") == op.get("id"):
                            it["done"] = (kind == "check")
                            break
                elif kind == "remove":
                    entry["items"] = [it for it in items if it.get("id") != op.get("id")]
                    items = entry["items"]
                elif kind == "rename":
                    entry["title"] = str(op.get("title", entry["title"]))
                else:
                    raise ValueError(f"unknown op: {kind}")
            self._write(data)
            return entry
        return None

    def list_all(self) -> list[dict]:
        return list(self._read().get("lists", []))


class TodosHandlers:
    def __init__(self, store: TodosStore) -> None:
        self._store = store

    async def on_create(self, params: dict, session=None, ws=None) -> dict:
        title = params.get("title")
        if not isinstance(title, str) or not title:
            return _err(ERR_BAD_INPUT, "missing_field", "title")
        try:
            return {"list": self._store.create_list(title)}
        except ValueError as exc:
            return _err(ERR_BAD_INPUT, "bad_value", str(exc))

    async def on_edit(self, params: dict, session=None, ws=None) -> dict:
        list_id = params.get("list_id")
        ops = params.get("ops", [])
        if not isinstance(list_id, str) or not list_id:
            return _err(ERR_BAD_INPUT, "missing_field", "list_id")
        if not isinstance(ops, list):
            return _err(ERR_BAD_INPUT, "bad_value", "ops must be a list")
        try:
            entry = self._store.edit_list(list_id=list_id, ops=ops)
        except ValueError as exc:
            return _err(ERR_BAD_INPUT, "bad_value", str(exc))
        if entry is None:
            return _err(ERR_NO_LIST, "list_not_found", list_id)
        return {"list": entry}

    async def on_list_all(self, params: dict, session=None, ws=None) -> dict:
        return {"lists": self._store.list_all()}


__all__ = [
    "TodoItem", "TodoList", "TodosStore", "TodosHandlers",
    "MAX_LISTS", "MAX_ITEMS_PER_LIST",
    "ERR_BAD_INPUT", "ERR_NO_LIST",
]
