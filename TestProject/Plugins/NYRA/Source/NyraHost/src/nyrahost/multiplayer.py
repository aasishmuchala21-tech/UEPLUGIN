"""nyrahost.multiplayer — Phase 17-C Multiplayer NYRA protocol (Tier 2).

Aura is per-developer. Studios with 5–50 engineers want NYRA's chat
threads + plan-as-markdown + audit log shared across the team so a
teammate can pick up where the lead left off. This module ships:

  * Wire-shape definitions — Room, Member, EventEnvelope (JSON)
  * Local in-process mock — LocalRoom for tests + offline runs
  * WS handlers — multiplayer/{rooms/list,rooms/join,rooms/leave,
    events/post,events/poll}

What's deferred to the eventual server:
  * Auth (OAuth or per-project token)
  * Persistence across server restarts
  * Conflict resolution beyond last-write-wins
  * End-to-end encryption (today the server sees plaintext; the
    PrivacyGuard refuses the entire multiplayer surface so studios
    under NDA have an opt-out)

This client speaks an HTTPS endpoint we control:
  POST /v1/rooms/{room_id}/events  — emit
  GET  /v1/rooms/{room_id}/events  — poll since cursor

For sandbox + tests, the LocalRoom in-memory implementation satisfies
the same MultiplayerBackend protocol, so handler tests are hermetic.
"""
from __future__ import annotations

import asyncio
import json  # R3.I4 — hoisted from deferred import inside post_event hot path
import time
import uuid
from dataclasses import dataclass, field
from typing import Final, Iterable, Optional, Protocol

import structlog

from nyrahost.privacy_guard import GUARD as PRIVACY_GUARD, OutboundRefused

log = structlog.get_logger("nyrahost.multiplayer")

ERR_BAD_INPUT: Final[int] = -32602
ERR_NO_ROOM: Final[int] = -32076
ERR_PRIVACY_REFUSED: Final[int] = -32072
ERR_BACKEND_FAILED: Final[int] = -32077

MAX_EVENTS_PER_POLL: Final[int] = 200
MAX_PAYLOAD_BYTES: Final[int] = 64 * 1024


@dataclass(frozen=True)
class Member:
    user_id: str
    display_name: str
    joined_at: float

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "joined_at": self.joined_at,
        }


@dataclass(frozen=True)
class EventEnvelope:
    """One event in a room's append-only log.

    Event kinds (closed set):
      * ``chat_turn``         — a chat message (incl. assistant response)
      * ``plan_proposed``     — a Plan markdown was emitted
      * ``plan_decision``     — Approve / Reject signal
      * ``tool_call``         — agent invoked a tool
      * ``handoff``           — explicit "@<user>, you take it from here"

    Servers MUST preserve sender / kind / payload. cursor is the
    server-assigned monotonic id (LSN-style); clients use it to poll
    only events newer than the highest cursor they've already seen.
    """

    cursor: int
    room_id: str
    sender_id: str
    kind: str
    payload: dict
    ts: float

    def to_dict(self) -> dict:
        return {
            "cursor": self.cursor,
            "room_id": self.room_id,
            "sender_id": self.sender_id,
            "kind": self.kind,
            "payload": self.payload,
            "ts": self.ts,
        }


ALLOWED_KINDS: Final[frozenset[str]] = frozenset({
    "chat_turn",
    "plan_proposed",
    "plan_decision",
    "tool_call",
    "handoff",
})


@dataclass
class Room:
    room_id: str
    title: str
    members: dict[str, Member] = field(default_factory=dict)
    events: list[EventEnvelope] = field(default_factory=list)
    _cursor: int = 0

    def to_dict(self) -> dict:
        return {
            "room_id": self.room_id,
            "title": self.title,
            "member_count": len(self.members),
            "event_count": len(self.events),
        }


class MultiplayerBackend(Protocol):
    """Protocol every multiplayer transport must satisfy."""

    async def list_rooms(self) -> list[Room]: ...
    async def join_room(self, room_id: str, member: Member) -> Room: ...
    async def leave_room(self, room_id: str, user_id: str) -> bool: ...
    async def post_event(self, room_id: str, *, sender_id: str,
                         kind: str, payload: dict) -> EventEnvelope: ...
    async def poll_events(self, room_id: str, *, since_cursor: int = 0,
                          limit: int = 50) -> list[EventEnvelope]: ...


@dataclass
class LocalRoomBackend:
    """In-memory implementation; hermetic for tests, also usable for
    single-machine teams that don't want to stand up a server."""

    _rooms: dict[str, Room] = field(default_factory=dict)
    _lock: object = None

    # L3 from PR #2 follow-up: LocalRoomBackend is instantiated inside the
    # asyncio process and its `async def` methods are awaited from the
    # event loop. The previous implementation used threading.RLock, which
    # blocks the loop thread under contention and is the wrong primitive
    # if any guarded section ever grows an `await`. Use asyncio.Lock,
    # lazily created so dataclass construction doesn't try to bind it
    # before a loop is running.
    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def list_rooms(self) -> list[Room]:
        async with self._get_lock():
            return list(self._rooms.values())

    async def join_room(self, room_id: str, member: Member) -> Room:
        async with self._get_lock():
            room = self._rooms.get(room_id)
            if room is None:
                room = Room(room_id=room_id, title=room_id)
                self._rooms[room_id] = room
            room.members[member.user_id] = member
            return room

    async def leave_room(self, room_id: str, user_id: str) -> bool:
        async with self._get_lock():
            room = self._rooms.get(room_id)
            if room is None:
                return False
            return room.members.pop(user_id, None) is not None

    async def post_event(self, room_id: str, *, sender_id: str,
                         kind: str, payload: dict) -> EventEnvelope:
        if kind not in ALLOWED_KINDS:
            raise ValueError(f"kind {kind!r} not in {sorted(ALLOWED_KINDS)}")
        # R3.I4: json is now imported at module level
        # Payload size check
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        if len(encoded) > MAX_PAYLOAD_BYTES:
            raise ValueError(f"payload exceeds {MAX_PAYLOAD_BYTES} bytes")
        async with self._get_lock():
            room = self._rooms.get(room_id)
            if room is None:
                raise KeyError(f"room {room_id!r} not found")
            room._cursor += 1
            env = EventEnvelope(
                cursor=room._cursor,
                room_id=room_id,
                sender_id=sender_id,
                kind=kind,
                payload=payload,
                ts=time.time(),
            )
            room.events.append(env)
            return env

    async def poll_events(self, room_id: str, *, since_cursor: int = 0,
                          limit: int = 50) -> list[EventEnvelope]:
        if limit <= 0 or limit > MAX_EVENTS_PER_POLL:
            limit = min(max(1, limit), MAX_EVENTS_PER_POLL)
        async with self._get_lock():
            room = self._rooms.get(room_id)
            if room is None:
                return []
            return [e for e in room.events if e.cursor > since_cursor][:limit]


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


class MultiplayerHandlers:
    def __init__(self, backend: MultiplayerBackend, *,
                 default_user_id: str = "local",
                 default_display: str = "You") -> None:
        self._backend = backend
        self._user_id = default_user_id
        self._display = default_display

    async def on_list_rooms(self, params: dict, session=None, ws=None) -> dict:
        try:
            rooms = await self._backend.list_rooms()
        except OutboundRefused as exc:
            return _err(ERR_PRIVACY_REFUSED, "privacy_mode_active", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _err(ERR_BACKEND_FAILED, "backend_failed", str(exc))
        return {"rooms": [r.to_dict() for r in rooms]}

    async def on_join(self, params: dict, session=None, ws=None) -> dict:
        room_id = params.get("room_id")
        if not isinstance(room_id, str) or not room_id:
            return _err(ERR_BAD_INPUT, "missing_field", "room_id")
        member = Member(
            user_id=str(params.get("user_id", self._user_id)),
            display_name=str(params.get("display_name", self._display)),
            joined_at=time.time(),
        )
        try:
            room = await self._backend.join_room(room_id, member)
        except OutboundRefused as exc:
            return _err(ERR_PRIVACY_REFUSED, "privacy_mode_active", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _err(ERR_BACKEND_FAILED, "backend_failed", str(exc))
        return {"joined": True, "room": room.to_dict(),
                "member": member.to_dict()}

    async def on_leave(self, params: dict, session=None, ws=None) -> dict:
        room_id = params.get("room_id")
        if not isinstance(room_id, str) or not room_id:
            return _err(ERR_BAD_INPUT, "missing_field", "room_id")
        user_id = str(params.get("user_id", self._user_id))
        try:
            removed = await self._backend.leave_room(room_id, user_id)
        except Exception as exc:  # noqa: BLE001
            return _err(ERR_BACKEND_FAILED, "backend_failed", str(exc))
        return {"removed": removed, "room_id": room_id, "user_id": user_id}

    async def on_post_event(self, params: dict, session=None, ws=None) -> dict:
        room_id = params.get("room_id")
        kind = params.get("kind")
        payload = params.get("payload", {})
        if not isinstance(room_id, str) or not room_id:
            return _err(ERR_BAD_INPUT, "missing_field", "room_id")
        if not isinstance(kind, str) or kind not in ALLOWED_KINDS:
            return _err(ERR_BAD_INPUT, "bad_kind",
                        f"kind must be one of {sorted(ALLOWED_KINDS)}")
        if not isinstance(payload, dict):
            return _err(ERR_BAD_INPUT, "bad_payload", "payload must be object")
        sender_id = str(params.get("sender_id", self._user_id))
        try:
            env = await self._backend.post_event(
                room_id, sender_id=sender_id, kind=kind, payload=payload,
            )
        except KeyError:
            return _err(ERR_NO_ROOM, "room_not_found", room_id)
        except ValueError as exc:
            return _err(ERR_BAD_INPUT, "bad_event", str(exc))
        except OutboundRefused as exc:
            return _err(ERR_PRIVACY_REFUSED, "privacy_mode_active", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _err(ERR_BACKEND_FAILED, "backend_failed", str(exc))
        return {"event": env.to_dict()}

    async def on_poll_events(self, params: dict, session=None, ws=None) -> dict:
        room_id = params.get("room_id")
        if not isinstance(room_id, str) or not room_id:
            return _err(ERR_BAD_INPUT, "missing_field", "room_id")
        try:
            since = int(params.get("since_cursor", 0))
            limit = int(params.get("limit", 50))
        except (TypeError, ValueError):
            return _err(ERR_BAD_INPUT, "since_or_limit_must_be_int")
        try:
            events = await self._backend.poll_events(
                room_id, since_cursor=since, limit=limit,
            )
        except OutboundRefused as exc:
            return _err(ERR_PRIVACY_REFUSED, "privacy_mode_active", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _err(ERR_BACKEND_FAILED, "backend_failed", str(exc))
        return {
            "events": [e.to_dict() for e in events],
            "high_water": max((e.cursor for e in events), default=since),
        }


__all__ = [
    "Member",
    "EventEnvelope",
    "Room",
    "MultiplayerBackend",
    "LocalRoomBackend",
    "MultiplayerHandlers",
    "ALLOWED_KINDS",
    "MAX_EVENTS_PER_POLL",
    "MAX_PAYLOAD_BYTES",
    "ERR_BAD_INPUT", "ERR_NO_ROOM", "ERR_PRIVACY_REFUSED", "ERR_BACKEND_FAILED",
]
