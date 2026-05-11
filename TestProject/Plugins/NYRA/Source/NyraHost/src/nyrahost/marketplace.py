"""nyrahost.marketplace — Phase 17-B plugin marketplace client (Tier 2).

Aura is closed; users cannot extend its agent set. NYRA shipped
user-installable MCP tools in Phase 14-D (drop a .py file into
``Plugins/NYRA/UserTools/``). This Phase 17-B layers a *marketplace*
on top: browse + download + signature-verify + install tools other
NYRA users have published, with the same security gates as
hand-installed ones.

This module is the **client**. The marketplace server itself
(auth, listing CRUD, signing infrastructure) is a separate deliverable
that lives outside the plugin. The client speaks an HTTPS REST shape
we control:

  GET  ``/v1/listings``           — paginated list of published tools
  GET  ``/v1/listings/<id>``      — single listing + download URL
  GET  ``/v1/listings/<id>/blob`` — the .py file, signed via Ed25519

Signature verification uses the ``cryptography`` package (already
pulled in for Phase 15-A encrypted memory). Public keys are pinned
in ``MARKETPLACE_TRUST_ROOTS`` so a compromised server cannot mint
its own signing key.

Privacy Mode honours: every outbound call routes through the
Phase 15-E ``PRIVACY_GUARD``. If guard is on, browsing refuses with
``OutboundRefused``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Iterable, Optional

import httpx
import structlog

from nyrahost.privacy_guard import GUARD as PRIVACY_GUARD, OutboundRefused

log = structlog.get_logger("nyrahost.marketplace")

DEFAULT_BASE_URL: Final[str] = "https://marketplace.nyra.ai"
LISTING_PAGE_SIZE: Final[int] = 25
MAX_BLOB_BYTES: Final[int] = 256 * 1024   # 256 KB cap per user-tool

ERR_BAD_INPUT: Final[int] = -32602
ERR_PRIVACY_REFUSED: Final[int] = -32072
ERR_SIG_INVALID: Final[int] = -32073
ERR_NETWORK: Final[int] = -32074
ERR_TOO_LARGE: Final[int] = -32075


# Pinned public keys for the marketplace's signing keys. v0 ships a
# single trust root; future updates can rotate by appending.
MARKETPLACE_TRUST_ROOTS: Final[tuple[str, ...]] = (
    # 64-hex Ed25519 public key — placeholder until the founder
    # generates the real signing key alongside the marketplace
    # deployment (see legal/ev-cert-acquisition-runbook.md neighbours).
    # R1.I4 / R2.I2 fix from the full-codebase review: this all-zeros
    # value is detected and rejected explicitly below so the marketplace
    # handler surfaces -32073 marketplace_not_configured at the boundary
    # instead of silently failing every install with -32072
    # signature_invalid.
    "0000000000000000000000000000000000000000000000000000000000000000",
)

_TRUST_ROOT_PLACEHOLDER: Final[str] = "0" * 64

# R2.C1 fix: listing_id must be a slug-shaped token; anything else opens
# the path-traversal door (`../../.ssh/authorized_keys` etc.).
import re  # noqa: E402
_LISTING_ID_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")

# R2.I4 fix: download_url must match a small host allowlist regardless of
# Privacy Mode state. Adding to this list is a deliberate operator action.
_DOWNLOAD_URL_HOST_ALLOWLIST: Final[frozenset[str]] = frozenset({
    "marketplace.nyra.ai",
    "fab.com",
})


def _trust_roots_configured() -> bool:
    """R1.I4 / R2.I2 — return False when the trust-root list is still the
    all-zeros placeholder, so the install handler can refuse with a clear
    'not configured' error instead of letting every signature verification
    fail downstream."""
    return any(root != _TRUST_ROOT_PLACEHOLDER for root in MARKETPLACE_TRUST_ROOTS)


def _validate_listing_id(listing_id: str) -> Optional[str]:
    """Return error-detail string if invalid, None if OK."""
    if not isinstance(listing_id, str) or not listing_id:
        return "missing"
    if not _LISTING_ID_RE.match(listing_id):
        return f"listing_id={listing_id!r} must match {_LISTING_ID_RE.pattern}"
    return None


def _validate_download_url_host(url: str) -> Optional[str]:
    """R2.I4 — return error-detail string if host isn't in the allowlist."""
    from urllib.parse import urlparse
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return f"download_url={url!r} could not be parsed"
    if host not in _DOWNLOAD_URL_HOST_ALLOWLIST:
        return (
            f"download_url host {host!r} not in allowlist "
            f"{sorted(_DOWNLOAD_URL_HOST_ALLOWLIST)}"
        )
    return None


@dataclass(frozen=True)
class Listing:
    listing_id: str
    name: str
    author: str
    version: str
    description: str
    download_url: str
    signature_hex: str
    public_key_hex: str
    sha256: str

    def to_dict(self) -> dict:
        return {
            "listing_id": self.listing_id,
            "name": self.name,
            "author": self.author,
            "version": self.version,
            "description": self.description,
            "download_url": self.download_url,
            "signature_hex": self.signature_hex,
            "public_key_hex": self.public_key_hex,
            "sha256": self.sha256,
        }


def verify_blob_signature(*, blob: bytes, signature_hex: str,
                          public_key_hex: str,
                          trust_roots: Iterable[str] = MARKETPLACE_TRUST_ROOTS) -> bool:
    """Verify Ed25519 signature against a pinned trust root."""
    if public_key_hex not in trust_roots:
        log.warning("marketplace_untrusted_key", key=public_key_hex)
        return False
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (   # noqa: PLC0415
            Ed25519PublicKey,
        )
        from cryptography.exceptions import InvalidSignature              # noqa: PLC0415
    except ModuleNotFoundError:
        log.warning("marketplace_cryptography_missing")
        return False
    try:
        key_bytes = bytes.fromhex(public_key_hex)
        sig_bytes = bytes.fromhex(signature_hex)
    except ValueError:
        return False
    try:
        Ed25519PublicKey.from_public_bytes(key_bytes).verify(sig_bytes, blob)
        return True
    except InvalidSignature:
        return False
    except Exception:  # noqa: BLE001
        return False


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


@dataclass
class MarketplaceClient:
    base_url: str = DEFAULT_BASE_URL
    timeout_s: float = 30.0
    _http: object | None = None   # injected for tests

    def _client(self):
        return self._http or httpx.AsyncClient(timeout=httpx.Timeout(self.timeout_s))

    async def list_listings(self, *, page: int = 0,
                            search: str | None = None) -> list[Listing]:
        PRIVACY_GUARD.assert_allowed(self.base_url)
        url = f"{self.base_url}/v1/listings"
        params: dict = {"page": page, "page_size": LISTING_PAGE_SIZE}
        if search:
            params["q"] = str(search)
        async with self._client() as client:
            resp = await client.get(url, params=params)
            if not resp.is_success:
                raise httpx.HTTPStatusError(
                    f"HTTP {resp.status_code}", request=None, response=resp,
                )
            data = resp.json()
        out: list[Listing] = []
        for item in data.get("listings", []):
            if not isinstance(item, dict):
                continue
            try:
                out.append(Listing(
                    listing_id=str(item["listing_id"]),
                    name=str(item["name"]),
                    author=str(item.get("author", "")),
                    version=str(item.get("version", "0.0.0")),
                    description=str(item.get("description", "")),
                    download_url=str(item.get("download_url", "")),
                    signature_hex=str(item.get("signature_hex", "")),
                    public_key_hex=str(item.get("public_key_hex", "")),
                    sha256=str(item.get("sha256", "")),
                ))
            except KeyError:
                continue
        return out

    async def download_blob(self, listing: Listing) -> bytes:
        PRIVACY_GUARD.assert_allowed(listing.download_url)
        async with self._client() as client:
            resp = await client.get(listing.download_url)
            if not resp.is_success:
                raise httpx.HTTPStatusError(
                    f"HTTP {resp.status_code}", request=None, response=resp,
                )
            blob = resp.content
        if len(blob) > MAX_BLOB_BYTES:
            raise ValueError(
                f"blob exceeds {MAX_BLOB_BYTES} bytes; refusing oversized tool"
            )
        if not verify_blob_signature(
            blob=blob,
            signature_hex=listing.signature_hex,
            public_key_hex=listing.public_key_hex,
        ):
            raise PermissionError("signature_invalid")
        return blob

    async def install_listing(self, listing: Listing, *,
                              user_tools_dir: Path) -> Path:
        # R2.C1 fix: belt-and-suspenders. Even if a caller bypassed the
        # handler-layer slug validation, ensure the resolved target lives
        # inside user_tools_dir.
        detail = _validate_listing_id(listing.listing_id)
        if detail is not None:
            raise ValueError(detail)
        blob = await self.download_blob(listing)
        user_tools_dir.mkdir(parents=True, exist_ok=True)
        target = user_tools_dir / f"market_{listing.listing_id}.py"
        resolved_target = target.resolve()
        resolved_root = user_tools_dir.resolve()
        try:
            resolved_target.relative_to(resolved_root)
        except ValueError:
            raise ValueError(
                f"listing_id={listing.listing_id!r} resolves outside user_tools_dir"
            )
        target.write_bytes(blob)
        log.info("marketplace_installed", listing_id=listing.listing_id, target=str(target))
        return target


class MarketplaceHandlers:
    """marketplace/* WS handlers."""

    def __init__(self, client: MarketplaceClient, *, user_tools_dir: Path) -> None:
        self._client = client
        self._dir = user_tools_dir

    async def on_list(self, params: dict, session=None, ws=None) -> dict:
        try:
            listings = await self._client.list_listings(
                page=int(params.get("page", 0)),
                search=params.get("search"),
            )
        except OutboundRefused as exc:
            return _err(ERR_PRIVACY_REFUSED, "privacy_mode_active", str(exc))
        except Exception as exc:  # noqa: BLE001 — never bubble across WS
            return _err(ERR_NETWORK, "marketplace_list_failed", f"{type(exc).__name__}: {exc}")
        return {"listings": [l.to_dict() for l in listings]}

    async def on_install(self, params: dict, session=None, ws=None) -> dict:
        # R1.I4 fix: refuse with a clear error if the trust roots haven't
        # been provisioned. Better than letting every install fail
        # downstream with -32072 signature_invalid.
        if not _trust_roots_configured():
            return _err(
                -32073,
                "marketplace_not_configured",
                "MARKETPLACE_TRUST_ROOTS still holds the all-zeros placeholder; "
                "set a real Ed25519 public key before enabling marketplace installs.",
            )
        # The panel sends the entire Listing it picked, so we don't re-fetch.
        try:
            listing = Listing(
                listing_id=str(params["listing_id"]),
                name=str(params.get("name", "")),
                author=str(params.get("author", "")),
                version=str(params.get("version", "0.0.0")),
                description=str(params.get("description", "")),
                download_url=str(params["download_url"]),
                signature_hex=str(params["signature_hex"]),
                public_key_hex=str(params["public_key_hex"]),
                sha256=str(params.get("sha256", "")),
            )
        except KeyError as exc:
            return _err(ERR_BAD_INPUT, "missing_field", str(exc))

        # R2.C1 fix: slug-shape listing_id before it touches the filesystem.
        detail = _validate_listing_id(listing.listing_id)
        if detail is not None:
            return _err(ERR_BAD_INPUT, "invalid_listing_id", detail)

        # R2.I4 fix: download_url must be on the allowlist regardless of
        # Privacy Mode state — Privacy Mode is an additional gate, not the
        # only one. Refuses SSRF to cloud-metadata endpoints, internal
        # services, file://, etc.
        detail = _validate_download_url_host(listing.download_url)
        if detail is not None:
            return _err(ERR_BAD_INPUT, "invalid_download_url", detail)
        try:
            path = await self._client.install_listing(listing,
                                                       user_tools_dir=self._dir)
        except OutboundRefused as exc:
            return _err(ERR_PRIVACY_REFUSED, "privacy_mode_active", str(exc))
        except ValueError as exc:
            return _err(ERR_TOO_LARGE, "blob_too_large", str(exc))
        except PermissionError:
            return _err(ERR_SIG_INVALID, "signature_invalid",
                        f"{listing.public_key_hex!r}")
        except (httpx.HTTPError, OSError) as exc:
            return _err(ERR_NETWORK, "install_failed", str(exc))
        return {"installed": True, "path": str(path),
                "listing_id": listing.listing_id}

    async def on_uninstall(self, params: dict, session=None, ws=None) -> dict:
        listing_id = params.get("listing_id")
        if not isinstance(listing_id, str) or not listing_id:
            return _err(ERR_BAD_INPUT, "missing_field", "listing_id")
        # R2.C1 fix: same slug-shape gate as on_install. Without it, an
        # uninstall call could delete arbitrary files via crafted
        # listing_id like '../../some/important.py'.
        detail = _validate_listing_id(listing_id)
        if detail is not None:
            return _err(ERR_BAD_INPUT, "invalid_listing_id", detail)
        target = self._dir / f"market_{listing_id}.py"
        # Belt-and-suspenders: ensure resolved target stays inside _dir.
        try:
            target.resolve().relative_to(self._dir.resolve())
        except ValueError:
            return _err(ERR_BAD_INPUT, "invalid_listing_id",
                        f"listing_id={listing_id!r} resolves outside user_tools_dir")
        if not target.exists():
            return {"removed": False, "listing_id": listing_id}
        try:
            target.unlink()
        except OSError as exc:
            return _err(ERR_NETWORK, "uninstall_failed", str(exc))
        return {"removed": True, "listing_id": listing_id}


__all__ = [
    "Listing",
    "MarketplaceClient",
    "MarketplaceHandlers",
    "verify_blob_signature",
    "DEFAULT_BASE_URL",
    "LISTING_PAGE_SIZE",
    "MAX_BLOB_BYTES",
    "MARKETPLACE_TRUST_ROOTS",
    "ERR_BAD_INPUT", "ERR_PRIVACY_REFUSED", "ERR_SIG_INVALID",
    "ERR_NETWORK", "ERR_TOO_LARGE",
]
