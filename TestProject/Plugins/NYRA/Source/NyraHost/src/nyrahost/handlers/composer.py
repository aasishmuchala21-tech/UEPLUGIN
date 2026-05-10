"""composer/asset_search handler — Phase 11-C.

Aura's @-search composer mention surface, ported. The chat composer
intercepts the user typing ``@<query>``, fires this handler with the
in-flight prefix, and renders the top-N matching assets so the user
can pick one to attach as context.

Design contract:
  * Reuses ``tools.asset_search.AssetSearchTool`` so the index lives in
    one place. AssetSearchTool itself is the canonical authority for
    the project-wide asset index (Phase 04-XX); the WS handler is a
    thin async wrapper.
  * Bounded request shape (mirrors AssetSearchTool's threshold + limit
    caps from §Phase 4 WR-01).
  * Returns up to MAX_LIMIT results (10 by default, hard cap 50) so a
    typo-fast user can't flood the panel.
"""
from __future__ import annotations

from typing import Final, Optional

import structlog

# AssetSearchTool transitively imports the UE editor's `unreal` module,
# which is only available inside a running UE editor. Import lazily so
# unit tests with an injected fake tool never trip on it.
AssetSearchTool = None  # type: ignore[assignment]

log = structlog.get_logger("nyrahost.handlers.composer")

ERR_BAD_INPUT: Final[int] = -32602
ERR_SEARCH_FAILED: Final[int] = -32044

DEFAULT_LIMIT: Final[int] = 10
MAX_LIMIT: Final[int] = 50
DEFAULT_THRESHOLD: Final[int] = 60   # lower than the tool's default 70 so partial-typed
                                     # queries surface candidates the user can finish typing.


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


class ComposerHandlers:
    """``composer/asset_search`` WS handler.

    Holds a single ``AssetSearchTool`` so the index is shared across
    every composer keypress.
    """

    def __init__(self, asset_search_tool: object | None = None) -> None:
        if asset_search_tool is not None:
            self._tool = asset_search_tool
        else:
            # Lazy import so unit tests that inject a fake never trip
            # the unreal-only AssetSearchTool import chain.
            from nyrahost.tools.asset_search import AssetSearchTool as _AST  # noqa: PLC0415
            self._tool = _AST()

    async def on_asset_search(self, params: dict, session=None, ws=None) -> dict:
        """Handle ``composer/asset_search`` requests.

        params:
          query        (str, required, ≤256 chars)
          class_filter (str, optional, ≤128 chars)
          limit        (int, default 10, max 50)
          threshold    (int, default 60)
        """
        query = params.get("query")
        if not isinstance(query, str):
            return _err(ERR_BAD_INPUT, "missing_field", "query")

        # Clamp limit at the handler boundary so AssetSearchTool sees a
        # safe value regardless of what the panel sent.
        try:
            limit_raw = int(params.get("limit", DEFAULT_LIMIT))
        except (TypeError, ValueError):
            return _err(ERR_BAD_INPUT, "limit_must_be_int")
        limit = max(1, min(limit_raw, MAX_LIMIT))

        try:
            threshold = int(params.get("threshold", DEFAULT_THRESHOLD))
        except (TypeError, ValueError):
            return _err(ERR_BAD_INPUT, "threshold_must_be_int")

        tool_params = {
            "query": query,
            "limit": limit,
            "threshold": threshold,
        }
        if "class_filter" in params:
            tool_params["class_filter"] = params["class_filter"]

        try:
            result = self._tool.execute(tool_params)
        except Exception as exc:  # noqa: BLE001
            log.exception("composer_asset_search_failed", err=str(exc))
            return _err(ERR_SEARCH_FAILED, "asset_search_failed", str(exc))

        if not result.ok:
            return _err(
                ERR_BAD_INPUT, "asset_search_rejected",
                result.error or "(no detail)",
            )

        # Surface only the fields the composer needs — keep the wire small.
        slim = [
            {
                "name": r.get("name"),
                "class": r.get("class"),
                "path": r.get("path"),
                "match_score": r.get("match_score", 0),
            }
            for r in result.value.get("results", [])
        ]
        return {
            "query": query,
            "total_indexed": result.value.get("total_indexed", 0),
            "results": slim,
            "limit": limit,
            "threshold": threshold,
        }


__all__ = [
    "ComposerHandlers",
    "DEFAULT_LIMIT",
    "MAX_LIMIT",
    "DEFAULT_THRESHOLD",
    "ERR_BAD_INPUT",
    "ERR_SEARCH_FAILED",
]
