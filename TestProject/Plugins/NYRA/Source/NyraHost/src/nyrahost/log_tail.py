"""nyra_output_log_tail + nyra_message_log_list MCP tools — Plan 02-11.

Per D-21: bounded ring buffer (2000 entries), category whitelist,
default high-verbosity exclusions, max_entries=200 cap per call.

Per docs/JSONRPC.md §4.6 + §4.7 wire contracts.
"""
from __future__ import annotations

import structlog

log = structlog.get_logger("nyrahost.log_tail")

# Default high-verbosity exclusion list (D-21)
DEFAULT_EXCLUSIONS = [
    "LogRHI", "LogRenderCore", "LogSlate", "LogD3D11", "LogD3D12", "LogTickGroup"
]
MAX_ENTRIES_CAP = 200


async def handle_nyra_output_log_tail(
    args: dict,
    ws_emit_request: callable,
) -> dict:
    """
    Handle nyra_output_log_tail MCP tool.

    Forwards to UE via log/tail WS request.
    Caps max_entries at 200 per call.
    Applies default exclusions when categories omitted.
    """
    categories = args.get("categories", [])
    max_entries = min(args.get("max_entries", 50), MAX_ENTRIES_CAP)
    since_ts = args.get("since_ts")
    regex = args.get("regex")
    min_verbosity = args.get("min_verbosity", "log")

    # If no categories provided, leave empty (UE applies default exclusions server-side)
    result = await ws_emit_request("log/tail", {
        "categories": categories,
        "max_entries": max_entries,
        "since_ts": since_ts,
        "regex": regex,
        "min_verbosity": min_verbosity,
    })
    return result


async def handle_nyra_message_log_list(
    args: dict,
    ws_emit_request: callable,
) -> dict:
    """
    Handle nyra_message_log_list MCP tool.

    Forwards to UE via log/message-log-list WS request.
    """
    listing_name = args.get("listing_name", "LogBlueprint")
    since_index = args.get("since_index", 0)
    max_entries = min(args.get("max_entries", 50), MAX_ENTRIES_CAP)

    result = await ws_emit_request("log/message-log-list", {
        "listing_name": listing_name,
        "since_index": since_index,
        "max_entries": max_entries,
    })
    return result


__all__ = [
    "handle_nyra_output_log_tail",
    "handle_nyra_message_log_list",
    "DEFAULT_EXCLUSIONS",
    "MAX_ENTRIES_CAP",
]