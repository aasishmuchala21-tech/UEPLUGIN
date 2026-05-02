"""Tests for claude_stream.py — NDJSON line parser for Claude CLI stream-json output.

RED phase: all tests fail because nyrahost.backends.claude_stream does not exist yet.
Tests use fixture files from tests/fixtures/ (no inline NDJSON > 3 lines).
"""
from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestStreamParser:
    """Pure-function NDJSON line -> BackendEvent[] parser."""

    def _parser(self):
        from nyrahost.backends.claude_stream import StreamParser
        return StreamParser()

    def test_parse_init_caches_metadata(self):
        """system/init line populates parser.session_id and parser.model but emits nothing."""
        parser = self._parser()
        line = '{"type": "system", "subtype": "init", "model": "claude-opus-4-7-20250514", "session_id": "session_abc"}'
        events = parser.parse_line(line)
        assert events == []
        assert parser.session_id == "session_abc"
        assert parser.model == "claude-opus-4-7-20250514"

    def test_parse_text_delta_emits_delta(self):
        """content_block_delta(text_delta) yields a Delta event."""
        parser = self._parser()
        line = '{"type": "stream_event", "event": {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text_delta": "Hello"}}}'
        events = parser.parse_line(line)
        assert len(events) == 1
        from nyrahost.backends.base import Delta
        assert isinstance(events[0], Delta)
        assert events[0].text == "Hello"

    def test_parse_tool_use_start_emits_tool_use_with_empty_input(self):
        """content_block_start(tool_use) yields ToolUse with empty input_json."""
        parser = self._parser()
        line = '{"type": "stream_event", "event": {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "toolu_001", "name": "Read", "input_json": ""}}}'
        events = parser.parse_line(line)
        assert len(events) == 1
        from nyrahost.backends.base import ToolUse
        assert isinstance(events[0], ToolUse)
        assert events[0].id == "toolu_001"
        assert events[0].name == "Read"
        assert events[0].input_json == ""

    def test_parse_input_json_delta_accumulates_on_tool_use(self):
        """Successive input_json_delta lines accumulate; ToolUse emitted only on content_block_stop with is_final=True."""
        parser = self._parser()
        # Start block
        start_line = '{"type": "stream_event", "event": {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "toolu_002", "name": "Write", "input_json": ""}}}'
        events = parser.parse_line(start_line)
        assert len(events) == 1
        from nyrahost.backends.base import ToolUse
        tu = events[0]
        assert isinstance(tu, ToolUse)
        assert tu.id == "toolu_002"
        # Partial deltas — accumulate internally, no new emission
        parser.parse_line('{"type": "stream_event", "event": {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": "{\\""}}')
        parser.parse_line('{"type": "stream_event", "event": {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": "file\\": \\"out.txt"}}}')
        # Stop — final ToolUse emitted with full accumulated JSON
        stop_line = '{"type": "stream_event", "event": {"type": "content_block_stop", "index": 0}}'
        events = parser.parse_line(stop_line)
        assert len(events) == 1
        assert isinstance(events[0], ToolUse)
        assert events[0].id == "toolu_002"
        assert "out.txt" in events[0].input_json

    def test_parse_api_retry_rate_limit_emits_retry(self):
        """system/api_retry with error=rate_limit yields Retry with error_category='rate_limit'."""
        parser = self._parser()
        line = '{"type": "system", "subtype": "api_retry", "attempt": 2, "retry_delay_ms": 5000, "error": "rate_limit"}'
        events = parser.parse_line(line)
        assert len(events) == 1
        from nyrahost.backends.base import Retry
        assert isinstance(events[0], Retry)
        assert events[0].attempt == 2
        assert events[0].delay_ms == 5000
        assert events[0].error_category == "rate_limit"

    def test_parse_api_retry_auth_failed_emits_retry_auth(self):
        """system/api_retry with error=authentication_failed yields Retry with error_category='authentication_failed'."""
        parser = self._parser()
        line = '{"type": "system", "subtype": "api_retry", "attempt": 1, "retry_delay_ms": 0, "error": "authentication_failed"}'
        events = parser.parse_line(line)
        assert len(events) == 1
        from nyrahost.backends.base import Retry
        assert isinstance(events[0], Retry)
        assert events[0].attempt == 1
        assert events[0].error_category == "authentication_failed"

    def test_parse_result_emits_done(self):
        """type=result yields Done with usage and stop_reason."""
        parser = self._parser()
        line = '{"type": "result", "stop_reason": "end_turn", "usage": {"input_tokens": 10, "output_tokens": 20}}'
        events = parser.parse_line(line)
        assert len(events) == 1
        from nyrahost.backends.base import Done
        assert isinstance(events[0], Done)
        assert events[0].stop_reason == "end_turn"
        assert events[0].usage == {"input_tokens": 10, "output_tokens": 20}

    def test_parse_unknown_type_logs_and_continues(self):
        """Unknown type does NOT raise; parser continues processing subsequent lines."""
        parser = self._parser()
        # Unknown type — no exception
        events = parser.parse_line('{"type": "unknown_type", "data": 123}')
        assert events == []
        # Parser is still usable after unknown type
        events = parser.parse_line('{"type": "stream_event", "event": {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text_delta": "still works"}}}')
        assert len(events) == 1
        from nyrahost.backends.base import Delta
        assert isinstance(events[0], Delta)
        assert events[0].text == "still works"

    def test_parse_malformed_json_raises_json_decode_error(self):
        """Malformed JSON line raises JSONDecodeError (caller handles gracefully)."""
        parser = self._parser()
        with pytest.raises(ValueError):
            parser.parse_line("this is not json")

    def test_parse_line_function(self):
        """Standalone parse_line() function dispatches to StreamParser.parse_line."""
        from nyrahost.backends.claude_stream import parse_line
        events = parse_line('{"type": "stream_event", "event": {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text_delta": "hi"}}}'  )
        from nyrahost.backends.base import Delta
        assert len(events) == 1
        assert isinstance(events[0], Delta)
        assert events[0].text == "hi"


class TestStreamParserFixtures:
    """Integration: parse full fixture files and verify event sequences."""

    def test_fixture_text_turn(self):
        """stream-json-text-turn.ndjson yields Delta + Done in correct order."""
        from nyrahost.backends.claude_stream import StreamParser
        from nyrahost.backends.base import Delta, Done

        parser = StreamParser()
        events = []
        for line in (FIXTURES_DIR / "stream-json-text-turn.ndjson").read_text().splitlines():
            if line.strip():
                events.extend(parser.parse_line(line))

        deltas = [e for e in events if isinstance(e, Delta)]
        dones = [e for e in events if isinstance(e, Done)]
        assert len(deltas) == 2
        assert "".join(d.text for d in deltas) == "Hello, world!"
        assert len(dones) == 1
        assert dones[0].stop_reason == "end_turn"

    def test_fixture_tool_use_turn(self):
        """stream-json-tool-use-turn.ndjson yields Delta + ToolUse + Done."""
        from nyrahost.backends.claude_stream import StreamParser
        from nyrahost.backends.base import Delta, Done, ToolUse

        parser = StreamParser()
        events = []
        for line in (FIXTURES_DIR / "stream-json-tool-use-turn.ndjson").read_text().splitlines():
            if line.strip():
                events.extend(parser.parse_line(line))

        deltas = [e for e in events if isinstance(e, Delta)]
        tools = [e for e in events if isinstance(e, ToolUse)]
        dones = [e for e in events if isinstance(e, Done)]
        assert len(deltas) == 1
        assert "I'll read that file" in deltas[0].text
        assert len(tools) == 2  # start + stop (with accumulated JSON)
        assert tools[0].name == "Read"
        assert tools[1].name == "Read"
        assert "path" in tools[1].input_json
        assert len(dones) == 1
        assert dones[0].stop_reason == "tool_use"

    def test_fixture_rate_limit_retry(self):
        """stream-json-api-retry-rate-limit.ndjson yields Retry + Done."""
        from nyrahost.backends.claude_stream import StreamParser
        from nyrahost.backends.base import Done, Retry

        parser = StreamParser()
        events = []
        for line in (FIXTURES_DIR / "stream-json-api-retry-rate-limit.ndjson").read_text().splitlines():
            if line.strip():
                events.extend(parser.parse_line(line))

        retries = [e for e in events if isinstance(e, Retry)]
        dones = [e for e in events if isinstance(e, Done)]
        assert len(retries) == 1
        assert retries[0].error_category == "rate_limit"
        assert retries[0].delay_ms == 5000
        assert len(dones) == 1

    def test_fixture_auth_failed_retry(self):
        """stream-json-api-retry-auth-failed.ndjson yields Retry with error_category=authentication_failed."""
        from nyrahost.backends.claude_stream import StreamParser
        from nyrahost.backends.base import Retry

        parser = StreamParser()
        events = []
        for line in (FIXTURES_DIR / "stream-json-api-retry-auth-failed.ndjson").read_text().splitlines():
            if line.strip():
                events.extend(parser.parse_line(line))

        retries = [e for e in events if isinstance(e, Retry)]
        assert len(retries) == 1
        assert retries[0].error_category == "authentication_failed"
