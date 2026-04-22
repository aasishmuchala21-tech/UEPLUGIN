"""Server-Sent Events (SSE) parser for OpenAI-compatible chat streams.

llama-server + Ollama both emit: each event is ``data: <json>\\n\\n``,
terminated by ``data: [DONE]``. See RESEARCH §3.5.

Parser rules (from Plan 08 <interfaces>):
- Blank line -> None
- Line starting with ':' (SSE comment / keep-alive) -> None
- Line starting with 'data: [DONE]' -> SseEvent(delta="", done=True)
- Line starting with 'data: ' + JSON -> extract choices[0].delta.content;
  done=True iff choice carries a finish_reason
- Malformed JSON after 'data: ' -> log warning and return None (do NOT raise)
- Any other prefix (event:, id:, unprefixed) -> None
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import AsyncIterator

import structlog

log = structlog.get_logger("nyrahost.sse")


@dataclass(frozen=True)
class SseEvent:
    delta: str
    done: bool = False
    finish_reason: str | None = None
    usage: dict | None = None


DONE_SENTINEL = "[DONE]"


def parse_sse_line(line: str) -> SseEvent | None:
    """Return SseEvent if the line produces one, else None (ignore).

    See module docstring for the full rule set. Never raises on malformed
    frames — the stream must keep going when the server drops a bad line.
    """
    if not line or line.startswith(":"):
        return None
    if not line.startswith("data: "):
        return None
    payload = line[6:].strip()
    if payload == DONE_SENTINEL:
        return SseEvent(delta="", done=True)
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError:
        log.warning("sse_malformed_frame", payload=payload[:120])
        return None
    choices = obj.get("choices") or []
    choice = choices[0] if choices else {}
    delta_obj = choice.get("delta") or {}
    content = delta_obj.get("content") or ""
    finish = choice.get("finish_reason")
    usage = obj.get("usage")
    done = finish is not None
    return SseEvent(
        delta=content,
        done=done,
        finish_reason=finish,
        usage=usage,
    )


async def aiter_sse_deltas(lines: AsyncIterator[str]) -> AsyncIterator[SseEvent]:
    """Consume an async line iterator and yield SseEvent instances.

    Stops after emitting the first ``done=True`` event — the llama-server
    SSE contract guarantees a finish_reason frame precedes ``data: [DONE]``,
    so downstream readers never need to see the sentinel itself.
    """
    async for raw in lines:
        ev = parse_sse_line(raw.rstrip("\n"))
        if ev is None:
            continue
        yield ev
        if ev.done:
            return
