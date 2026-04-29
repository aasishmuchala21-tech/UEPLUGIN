"""Tests for nyra_output_log_tail + nyra_message_log_list MCP tools (Plan 02-11)."""
from __future__ import annotations

import pytest

from nyrahost.log_tail import MAX_ENTRIES_CAP, DEFAULT_EXCLUSIONS


class TestLogTailDefaults:
    """Default cap and exclusion list."""

    def test_max_entries_cap_is_200(self):
        assert MAX_ENTRIES_CAP == 200

    def test_default_exclusions_list(self):
        assert "LogRHI" in DEFAULT_EXCLUSIONS
        assert "LogRenderCore" in DEFAULT_EXCLUSIONS
        assert "LogSlate" in DEFAULT_EXCLUSIONS
        assert "LogD3D11" in DEFAULT_EXCLUSIONS
        assert "LogD3D12" in DEFAULT_EXCLUSIONS
        assert "LogTickGroup" in DEFAULT_EXCLUSIONS


class TestLogTailHandler:
    """nyra_output_log_tail handler logic."""

    async def test_max_entries_cap_at_200(self):
        """Tool call with max_entries > 200 is capped."""
        from nyrahost.log_tail import handle_nyra_output_log_tail
        capped_calls = []

        async def mock_emit(method, params):
            capped_calls.append(params)

        # Call with 500 — should be capped to 200
        result = await handle_nyra_output_log_tail(
            {"max_entries": 500, "categories": ["LogBlueprint"]},
            mock_emit,
        )
        assert capped_calls[0]["max_entries"] <= MAX_ENTRIES_CAP

    async def test_default_categories_empty_pass_through(self):
        """When categories omitted, empty list passes through (UE applies defaults)."""
        from nyrahost.log_tail import handle_nyra_output_log_tail
        calls = []

        async def mock_emit(method, params):
            calls.append(params)

        await handle_nyra_output_log_tail(
            {"max_entries": 50},
            mock_emit,
        )
        # Empty categories = UE applies default exclusions
        assert calls[0]["categories"] == []
        assert calls[0]["max_entries"] == 50

    async def test_since_ts_passed_through(self):
        """since_ts forwarded verbatim to UE."""
        from nyrahost.log_tail import handle_nyra_output_log_tail
        calls = []

        async def mock_emit(method, params):
            calls.append(params)

        await handle_nyra_output_log_tail(
            {"max_entries": 50, "since_ts": "2026-04-29T00:00:00Z"},
            mock_emit,
        )
        assert calls[0]["since_ts"] == "2026-04-29T00:00:00Z"

    async def test_regex_passed_through(self):
        """regex forwarded verbatim to UE for server-side compilation."""
        from nyrahost.log_tail import handle_nyra_output_log_tail
        calls = []

        async def mock_emit(method, params):
            calls.append(params)

        await handle_nyra_output_log_tail(
            {"max_entries": 50, "regex": "error.*"},
            mock_emit,
        )
        assert calls[0]["regex"] == "error.*"

    async def test_emit_calls_log_tail_ws_method(self):
        """nyra_output_log_tail emits log/tail WS request."""
        from nyrahost.log_tail import handle_nyra_output_log_tail
        calls = []

        async def mock_emit(method, params):
            calls.append({"method": method, "params": params})

        await handle_nyra_output_log_tail(
            {"max_entries": 50, "categories": ["LogBlueprint"]},
            mock_emit,
        )
        assert calls[0]["method"] == "log/tail"


class TestMessageLogHandler:
    """nyra_message_log_list handler logic."""

    async def test_listing_name_default_logblueprint(self):
        """Default listing is LogBlueprint."""
        from nyrahost.log_tail import handle_nyra_message_log_list
        calls = []

        async def mock_emit(method, params):
            calls.append(params)

        await handle_nyra_message_log_list({}, mock_emit)
        assert calls[0]["listing_name"] == "LogBlueprint"

    async def test_since_index_default_zero(self):
        from nyrahost.log_tail import handle_nyra_message_log_list
        calls = []

        async def mock_emit(method, params):
            calls.append(params)

        await handle_nyra_message_log_list({}, mock_emit)
        assert calls[0]["since_index"] == 0

    async def test_max_entries_capped(self):
        from nyrahost.log_tail import handle_nyra_message_log_list
        calls = []

        async def mock_emit(method, params):
            calls.append(params)

        await handle_nyra_message_log_list(
            {"max_entries": 500, "listing_name": "LogPIE"},
            mock_emit,
        )
        assert calls[0]["max_entries"] <= MAX_ENTRIES_CAP

    async def test_emit_calls_message_log_list_ws_method(self):
        """nyra_message_log_list emits log/message-log-list WS request."""
        from nyrahost.log_tail import handle_nyra_message_log_list
        calls = []

        async def mock_emit(method, params):
            calls.append({"method": method, "params": params})

        await handle_nyra_message_log_list(
            {"listing_name": "LogBlueprint", "max_entries": 20},
            mock_emit,
        )
        assert calls[0]["method"] == "log/message-log-list"