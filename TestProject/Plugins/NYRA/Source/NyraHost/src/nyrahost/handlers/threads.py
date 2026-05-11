"""chat/threads/* WS handlers — Phase 13-A multi-thread parallel chats.

Aura ships up to ~4 concurrent chat threads in the same panel. The user
can run a 3D-model gen in one thread while planning a Blueprint in
another. NYRA mirrors the surface so the same workflow works.

Backend model (kept tiny — most of the heavy lifting is already done by
ChatHandlers._inflight which maps req_id -> Event):
  * ThreadRegistry tracks active thread_ids with a hard MAX_THREADS cap
  * Each thread has metadata: title, created_at, last_active_at,
    in_flight (req_id of the currently-streaming response, or None)
  * chat/send is unaffected — the existing surface already accepts
    conversation_id; threads are purely a UI organizer that maps 1-1
    onto conversation_id.

The WS surface:
  * chat/threads/list   — return all active thread metadata
  * chat/threads/create — open a new thread; -32051 if MAX_THREADS hit
  * chat/threads/close  — drop a thread (does NOT delete the
    Storage-level conversation; just closes the panel tab)
  * chat/threads/touch  — bump last_active_at (called by chat handler
    on each chat/send so the LRU-evict-eligible set is maintained)
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Final, Optional

import structlog

log = structlog.get_logger("nyrahost.handlers.threads")

# Aura's documented threshold ("up to ~4"). 4 is the smallest safe
# concurrent count given Claude CLI subprocess weight + UE editor
# responsiveness on a single-developer machine.
MAX_THREADS: Final[int] = 4

ERR_BAD_INPUT: Final[int] = -32602
ERR_THREAD_LIMIT: Final[int] = -32051
ERR_UNKNOWN_THREAD: Final[int] = -32052


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


@dataclass
class ChatThread:
    thread_id: str
    title: str = ""
    created_at: float = field(default_factory=time.time)
    last_active_at: float = field(default_factory=time.time)
    in_flight_req_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "thread_id": self.thread_id,
            "title": self.title,
            "created_at": self.created_at,
            "last_active_at": self.last_active_at,
            "in_flight": self.in_flight_req_id is not None,
        }


class ThreadRegistry:
    """In-memory thread tracker. Single-process, no persistence —
    threads close on NyraHost shutdown by design (the user's panel
    re-creates them from Storage on next launch via sessions/list)."""

    def __init__(self, *, max_threads: int = MAX_THREADS) -> None:
        self._max = max_threads
        self._threads: dict[str, ChatThread] = {}

    @property
    def count(self) -> int:
        return len(self._threads)

    @property
    def max_threads(self) -> int:
        return self._max

    def list(self) -> list[ChatThread]:
        return sorted(self._threads.values(), key=lambda t: -t.last_active_at)

    def create(self, *, title: str = "") -> ChatThread:
        if len(self._threads) >= self._max:
            raise ValueError(
                f"thread_limit_reached: {self._max} concurrent threads max"
            )
        t = ChatThread(thread_id=str(uuid.uuid4())[:8], title=title)
        self._threads[t.thread_id] = t
        log.info("thread_created", thread_id=t.thread_id, title=title)
        return t

    def close(self, thread_id: str) -> bool:
        if thread_id not in self._threads:
            return False
        del self._threads[thread_id]
        log.info("thread_closed", thread_id=thread_id)
        return True

    def touch(self, thread_id: str, *, in_flight_req_id: str | None = None) -> bool:
        t = self._threads.get(thread_id)
        if t is None:
            return False
        t.last_active_at = time.time()
        if in_flight_req_id is not None:
            t.in_flight_req_id = in_flight_req_id
        return True

    def clear_in_flight(self, thread_id: str) -> bool:
        t = self._threads.get(thread_id)
        if t is None:
            return False
        t.in_flight_req_id = None
        return True


class ThreadHandlers:
    def __init__(self, registry: ThreadRegistry | None = None) -> None:
        self._reg = registry or ThreadRegistry()

    @property
    def registry(self) -> ThreadRegistry:
        return self._reg

    async def on_list(self, params: dict, session=None, ws=None) -> dict:
        return {
            "max_threads": self._reg.max_threads,
            "count": self._reg.count,
            "threads": [t.to_dict() for t in self._reg.list()],
        }

    async def on_create(self, params: dict, session=None, ws=None) -> dict:
        title = params.get("title", "")
        if not isinstance(title, str):
            return _err(ERR_BAD_INPUT, "bad_type", "title must be str")
        try:
            t = self._reg.create(title=title)
        except ValueError as exc:
            return _err(
                ERR_THREAD_LIMIT, "thread_limit_reached", str(exc),
                remediation=(
                    f"Close an existing thread before opening another. "
                    f"Hard cap is {self._reg.max_threads} per Aura parity."
                ),
            )
        return {"thread": t.to_dict()}

    async def on_close(self, params: dict, session=None, ws=None) -> dict:
        thread_id = params.get("thread_id")
        if not isinstance(thread_id, str) or not thread_id:
            return _err(ERR_BAD_INPUT, "missing_field", "thread_id")
        ok = self._reg.close(thread_id)
        if not ok:
            return _err(ERR_UNKNOWN_THREAD, "unknown_thread", thread_id)
        return {"closed": True, "thread_id": thread_id}

    async def on_touch(self, params: dict, session=None, ws=None) -> dict:
        thread_id = params.get("thread_id")
        if not isinstance(thread_id, str) or not thread_id:
            return _err(ERR_BAD_INPUT, "missing_field", "thread_id")
        in_flight = params.get("in_flight_req_id")
        ok = self._reg.touch(thread_id, in_flight_req_id=in_flight)
        if not ok:
            return _err(ERR_UNKNOWN_THREAD, "unknown_thread", thread_id)
        return {"touched": True, "thread_id": thread_id}


__all__ = [
    "ChatThread",
    "ThreadRegistry",
    "ThreadHandlers",
    "MAX_THREADS",
    "ERR_BAD_INPUT",
    "ERR_THREAD_LIMIT",
    "ERR_UNKNOWN_THREAD",
]
