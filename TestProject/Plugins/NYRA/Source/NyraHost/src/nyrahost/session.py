"""Per-WS-connection session state.

One SessionState per WS connection; NyraServer instantiates in
_handle_connection and threads it through the dispatch loop so handlers
can see authentication status, their own session_id, and the set of
conversation_ids seen on this socket.
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field


@dataclass
class SessionState:
    authenticated: bool = False
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conversation_ids_seen: set[str] = field(default_factory=set)
