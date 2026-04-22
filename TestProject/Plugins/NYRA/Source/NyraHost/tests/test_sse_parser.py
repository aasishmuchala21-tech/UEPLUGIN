"""SSE parser tests.
VALIDATION test ID: 1-03-03
"""
from __future__ import annotations
import pytest
from nyrahost.infer.sse import parse_sse_line, aiter_sse_deltas, SseEvent


def test_sse_delta_extraction() -> None:
    e = parse_sse_line('data: {"choices":[{"delta":{"content":"Hello"}}]}')
    assert e is not None
    assert e.delta == "Hello"
    assert e.done is False

    e2 = parse_sse_line(
        'data: {"choices":[{"delta":{},"finish_reason":"stop"}],'
        '"usage":{"prompt_tokens":3,"completion_tokens":2,"total_tokens":5}}'
    )
    assert e2 is not None
    assert e2.delta == ""
    assert e2.done is True
    assert e2.finish_reason == "stop"
    assert e2.usage == {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}


def test_sse_tolerates_comment_and_blank_lines() -> None:
    assert parse_sse_line("") is None
    assert parse_sse_line(": keep-alive") is None
    assert parse_sse_line("event: message") is None  # not prefixed "data: "


def test_sse_done_sentinel() -> None:
    e = parse_sse_line("data: [DONE]")
    assert e is not None
    assert e.done is True


def test_sse_malformed_json_frame_is_skipped() -> None:
    # Should NOT raise; returns None and logs (logger tested separately)
    assert parse_sse_line("data: not-json") is None


@pytest.mark.asyncio
async def test_aiter_sse_deltas_end_to_end() -> None:
    async def source():
        yield 'data: {"choices":[{"delta":{"content":"Hello"}}]}\n'
        yield "\n"  # blank
        yield 'data: {"choices":[{"delta":{"content":" world"}}]}\n'
        yield (
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}],'
            '"usage":{"prompt_tokens":3,"completion_tokens":2}}\n'
        )
        yield "data: [DONE]\n"  # should not be reached

    out: list[SseEvent] = []
    async for ev in aiter_sse_deltas(source()):
        out.append(ev)
    # Expect: "Hello", " world", final with done=True
    assert len(out) == 3
    assert out[0].delta == "Hello"
    assert out[1].delta == " world"
    assert out[2].done is True
    assert out[2].finish_reason == "stop"
