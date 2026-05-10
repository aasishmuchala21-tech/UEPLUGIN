"""Phase 11-C — composer/asset_search handler tests.

Hermetic — uses a fake AssetSearchTool so we don't need a real UE
project asset index.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from nyrahost.handlers.composer import (
    ComposerHandlers,
    DEFAULT_LIMIT,
    DEFAULT_THRESHOLD,
    MAX_LIMIT,
)


@dataclass
class _FakeResult:
    ok: bool
    value: dict | None = None
    error: str | None = None


def _fake_tool(results: list[dict] | None = None, ok: bool = True, total: int = 100):
    tool = MagicMock()
    tool.execute.return_value = _FakeResult(
        ok=ok,
        value={"results": results or [], "total_indexed": total} if ok else None,
        error=None if ok else "fake_error",
    )
    return tool


def test_search_returns_slimmed_results():
    tool = _fake_tool([
        {"name": "BP_Hero", "class": "Blueprint", "path": "/Game/BP_Hero", "match_score": 92, "extra": "ignored"},
        {"name": "BP_Heroine", "class": "Blueprint", "path": "/Game/BP_Heroine", "match_score": 88},
    ])
    h = ComposerHandlers(asset_search_tool=tool)
    out = asyncio.run(h.on_asset_search({"query": "hero"}))
    assert "error" not in out
    assert len(out["results"]) == 2
    assert out["results"][0]["name"] == "BP_Hero"
    # `extra` field stripped at the wire (slim contract)
    assert "extra" not in out["results"][0]
    # Default limits + threshold are passed through
    assert out["limit"] == DEFAULT_LIMIT
    assert out["threshold"] == DEFAULT_THRESHOLD


def test_limit_is_clamped_to_max():
    tool = _fake_tool([])
    h = ComposerHandlers(asset_search_tool=tool)
    out = asyncio.run(h.on_asset_search({"query": "x", "limit": 9_999}))
    assert out["limit"] == MAX_LIMIT
    # Tool was called with the clamped value
    tool.execute.assert_called_once()
    assert tool.execute.call_args.args[0]["limit"] == MAX_LIMIT


def test_missing_query_rejected():
    h = ComposerHandlers(asset_search_tool=_fake_tool([]))
    out = asyncio.run(h.on_asset_search({}))
    assert out["error"]["code"] == -32602
    assert out["error"]["message"] == "missing_field"


def test_non_int_limit_rejected():
    h = ComposerHandlers(asset_search_tool=_fake_tool([]))
    out = asyncio.run(h.on_asset_search({"query": "x", "limit": "ten"}))
    assert out["error"]["code"] == -32602
    assert out["error"]["message"] == "limit_must_be_int"


def test_tool_failure_maps_to_search_failed():
    tool = _fake_tool(ok=False)
    h = ComposerHandlers(asset_search_tool=tool)
    out = asyncio.run(h.on_asset_search({"query": "x"}))
    assert out["error"]["code"] == -32602
    assert out["error"]["message"] == "asset_search_rejected"


def test_class_filter_passthrough():
    tool = _fake_tool([])
    h = ComposerHandlers(asset_search_tool=tool)
    asyncio.run(h.on_asset_search({"query": "x", "class_filter": "Texture2D"}))
    assert tool.execute.call_args.args[0]["class_filter"] == "Texture2D"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
