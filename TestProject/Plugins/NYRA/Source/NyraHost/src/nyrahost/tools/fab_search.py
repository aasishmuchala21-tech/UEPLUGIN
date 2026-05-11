"""nyrahost.tools.fab_search — Phase 19-B Epic Fab marketplace search.

Aura ships "Search the FAB store for free environment assets" as a
chat-driven flow. NYRA mirrors via fab/search WS method.

Endpoint contract is best-effort against Epic's public Fab API
(api.fab.com / fab.com/api). The handler maps reliably-available
query params (text, free-only, category, page) into the request and
slims the response to name + creator + price + listing URL.

Privacy Mode honoured via Phase 15-E PRIVACY_GUARD.
Tested against a mocked HTTP layer — the field names in the live
response can drift; we keep parsing defensive.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Final, Optional

import httpx
import structlog

from nyrahost.privacy_guard import GUARD as PRIVACY_GUARD, OutboundRefused

log = structlog.get_logger("nyrahost.tools.fab_search")

DEFAULT_BASE_URL: Final[str] = "https://www.fab.com/api/listings"
DEFAULT_LIMIT: Final[int] = 20
MAX_LIMIT: Final[int] = 50

ERR_BAD_INPUT: Final[int] = -32602
ERR_FAB_FAILED: Final[int] = -32083
ERR_PRIVACY_REFUSED: Final[int] = -32072


@dataclass(frozen=True)
class FabListing:
    listing_id: str
    name: str
    creator: str
    price_usd: float | None
    free: bool
    url: str
    thumbnail_url: str | None
    categories: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "listing_id": self.listing_id,
            "name": self.name,
            "creator": self.creator,
            "price_usd": self.price_usd,
            "free": self.free,
            "url": self.url,
            "thumbnail_url": self.thumbnail_url,
            "categories": list(self.categories),
        }


def _parse_listing(item: dict) -> FabListing | None:
    """Best-effort parse against Fab's response shape.

    Field name fallbacks defend against drift — if the API renames
    `price.amount` to `pricing.amount` we still get a value.
    """
    if not isinstance(item, dict):
        return None
    try:
        listing_id = str(item.get("uid") or item.get("id") or item.get("listing_id") or "")
        if not listing_id:
            return None
        name = str(item.get("title") or item.get("name") or "")
        creator = str(
            (item.get("seller") or {}).get("name")
            or (item.get("creator") or {}).get("name")
            or item.get("seller_name")
            or ""
        )
        price_raw = (
            (item.get("price") or {}).get("amount")
            if isinstance(item.get("price"), dict) else item.get("price")
        )
        try:
            price_usd: float | None = float(price_raw) if price_raw is not None else None
        except (TypeError, ValueError):
            price_usd = None
        free = bool(item.get("free") or (price_usd is not None and price_usd == 0.0))
        url = str(item.get("url") or item.get("listing_url") or "")
        thumb = item.get("thumbnail_url") or (
            (item.get("thumbnail") or {}).get("url")
            if isinstance(item.get("thumbnail"), dict) else None
        )
        cats = tuple(
            str(c) for c in (item.get("categories") or item.get("tags") or [])
        )
        return FabListing(
            listing_id=listing_id, name=name, creator=creator,
            price_usd=price_usd, free=free, url=url,
            thumbnail_url=str(thumb) if thumb else None,
            categories=cats,
        )
    except Exception:  # noqa: BLE001 — never bubble bad responses
        return None


@dataclass
class FabSearchClient:
    base_url: str = DEFAULT_BASE_URL
    timeout_s: float = 30.0
    _http: object | None = None

    def _client(self):
        return self._http or httpx.AsyncClient(timeout=httpx.Timeout(self.timeout_s))

    async def search(self, *, query: str, free_only: bool = False,
                     category: str | None = None,
                     limit: int = DEFAULT_LIMIT) -> list[FabListing]:
        PRIVACY_GUARD.assert_allowed(self.base_url)
        limit = max(1, min(int(limit), MAX_LIMIT))
        params: dict = {"q": query, "limit": limit}
        if free_only:
            params["price"] = "free"
        if category:
            params["category"] = category
        async with self._client() as client:
            resp = await client.get(self.base_url, params=params)
            if not resp.is_success:
                raise httpx.HTTPStatusError(
                    f"HTTP {resp.status_code}", request=None, response=resp,
                )
            data = resp.json()
        items = data.get("results") or data.get("listings") or data.get("items") or []
        out: list[FabListing] = []
        for item in items:
            parsed = _parse_listing(item)
            if parsed is not None:
                out.append(parsed)
        return out


def _err(code: int, message: str, detail: str = "",
         remediation: Optional[str] = None) -> dict:
    data: dict = {}
    if detail:
        data["detail"] = detail
    if remediation:
        data["remediation"] = remediation
    out: dict = {"error": {"code": code, "message": message}}
    if data:
        out["error"]["data"] = data
    return out


class FabSearchHandlers:
    def __init__(self, client: FabSearchClient | None = None) -> None:
        self._client = client or FabSearchClient()

    async def on_search(self, params: dict, session=None, ws=None) -> dict:
        query = params.get("query") or params.get("q")
        if not isinstance(query, str) or not query:
            return _err(ERR_BAD_INPUT, "missing_field", "query")
        try:
            listings = await self._client.search(
                query=query,
                free_only=bool(params.get("free_only", False)),
                category=params.get("category"),
                limit=int(params.get("limit", DEFAULT_LIMIT)),
            )
        except OutboundRefused as exc:
            return _err(ERR_PRIVACY_REFUSED, "privacy_mode_active", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _err(ERR_FAB_FAILED, "fab_search_failed",
                        f"{type(exc).__name__}: {exc}")
        return {"query": query, "listings": [l.to_dict() for l in listings]}


__all__ = [
    "FabListing", "FabSearchClient", "FabSearchHandlers",
    "DEFAULT_BASE_URL", "DEFAULT_LIMIT", "MAX_LIMIT",
    "ERR_BAD_INPUT", "ERR_FAB_FAILED", "ERR_PRIVACY_REFUSED",
]
