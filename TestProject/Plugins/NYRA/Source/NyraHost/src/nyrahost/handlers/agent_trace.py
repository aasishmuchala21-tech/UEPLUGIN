"""trace/* WS handlers — Phase 14-C "show me what the agent saw".

Tier 2 moat. Reads the per-project audit.jsonl and returns a
structured per-conversation trace so the user can debug "why did
the agent do that?".

Aura is closed SaaS — they own the trace and ship a chat-export
button for support tickets. NYRA's audit.jsonl is local-only; this
handler is the structured-read API on top of it.
"""
from __future__ import annotations

from pathlib import Path
from typing import Final, Iterable, Optional

import structlog

from nyrahost.audit import AuditLog

log = structlog.get_logger("nyrahost.handlers.agent_trace")

ERR_BAD_INPUT: Final[int] = -32602
DEFAULT_LIMIT: Final[int] = 200
MAX_LIMIT: Final[int] = 5000


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


def filter_trace(
    records: Iterable[dict],
    *,
    conversation_id: str | None = None,
    kinds: list[str] | None = None,
    since_ts: float | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[dict]:
    """Pure filter — easy to test without a real audit log."""
    out: list[dict] = []
    kind_set = set(kinds) if kinds else None
    for r in records:
        if since_ts is not None and float(r.get("ts", 0)) < since_ts:
            continue
        if kind_set is not None and r.get("kind") not in kind_set:
            continue
        if conversation_id is not None:
            if r.get("conversation_id") != conversation_id:
                continue
        out.append(r)
        if len(out) >= limit:
            break
    return out


class AgentTraceHandlers:
    def __init__(self, audit_log: AuditLog) -> None:
        self._audit = audit_log

    async def on_get(self, params: dict, session=None, ws=None) -> dict:
        try:
            limit_raw = int(params.get("limit", DEFAULT_LIMIT))
        except (TypeError, ValueError):
            return _err(ERR_BAD_INPUT, "limit_must_be_int")
        limit = max(1, min(limit_raw, MAX_LIMIT))
        kinds = params.get("kinds")
        if kinds is not None and not isinstance(kinds, list):
            return _err(ERR_BAD_INPUT, "kinds_must_be_list")
        since = params.get("since_ts")
        try:
            since_f = None if since is None else float(since)
        except (TypeError, ValueError):
            return _err(ERR_BAD_INPUT, "since_ts_must_be_number")
        conv = params.get("conversation_id")
        records = self._audit.read_all()
        out = filter_trace(
            records,
            conversation_id=conv if isinstance(conv, str) else None,
            kinds=kinds,
            since_ts=since_f,
            limit=limit,
        )
        return {
            "records": out,
            "count": len(out),
            "limit": limit,
        }


__all__ = [
    "AgentTraceHandlers",
    "filter_trace",
    "DEFAULT_LIMIT",
    "MAX_LIMIT",
    "ERR_BAD_INPUT",
]
