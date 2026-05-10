"""nyrahost.privacy_guard — Phase 15-E outbound-HTTP guard for Privacy Mode.

Tier 2 privacy moat — the "air-gapped install" assertion. When
Privacy Mode is on (NyraRouter.BackendState.PRIVACY_MODE), no
outbound HTTP to Anthropic / Meshy / ComfyUI / OpenAI is allowed.
Existing PrivacyMode work in router.py governs which BACKEND
serves the chat; this module is the cross-cutting check that
catches anything that tries to bypass the router (e.g. a third-party
user tool reaching for ``httpx.AsyncClient`` directly).

Implementation: a closed-set allowlist of hosts that are *always*
permitted (loopback) plus a runtime-toggled "privacy_mode" flag
that, when True, refuses every other outbound request.

The guard is opt-in for callers: they MUST consult
``privacy_guard.assert_allowed(url)`` before issuing the request.
For NYRA's built-in clients (MeshyClient, ComfyUIClient, etc.) the
guard is wired at the request boundary; user-installable MCP tools
that bypass the guard are at the user's risk — the next phase
adds a startup banner explaining this.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Final, Iterable, Optional
from urllib.parse import urlparse

import structlog

log = structlog.get_logger("nyrahost.privacy_guard")

# Always-allowed hosts — loopback and the user's own machine. These
# stay reachable in Privacy Mode so local Gemma / local ComfyUI /
# local llama-server keep working.
ALWAYS_ALLOWED_HOSTS: Final[frozenset[str]] = frozenset({
    "127.0.0.1",
    "::1",
    "localhost",
    "0.0.0.0",
})


class OutboundRefused(RuntimeError):
    """Raised by assert_allowed when Privacy Mode would forbid the call."""


@dataclass
class PrivacyGuard:
    """Process-wide flag; thread-safe set."""

    _lock: threading.RLock = None  # type: ignore[assignment]
    _privacy_mode: bool = False
    _refusal_count: int = 0

    def __post_init__(self) -> None:
        # Late-bind the lock so dataclass field-default works on 3.10.
        object.__setattr__(self, "_lock", threading.RLock())

    @property
    def privacy_mode(self) -> bool:
        return self._privacy_mode

    def enable(self) -> None:
        with self._lock:
            self._privacy_mode = True
        log.info("privacy_guard_enabled")

    def disable(self) -> None:
        with self._lock:
            self._privacy_mode = False
        log.info("privacy_guard_disabled")

    def assert_allowed(self, url: str) -> None:
        """Raise OutboundRefused when Privacy Mode is on and url is not
        loopback. Always returns silently when Privacy Mode is off."""
        with self._lock:
            pm = self._privacy_mode
        if not pm:
            return
        host = _host_of(url)
        if host in ALWAYS_ALLOWED_HOSTS:
            return
        with self._lock:
            self._refusal_count += 1
        log.warning("privacy_guard_refused", url=url, host=host)
        raise OutboundRefused(
            f"privacy_mode_active: outbound HTTP to {host!r} blocked; "
            "disable Privacy Mode in the panel to allow this request"
        )

    def stats(self) -> dict:
        with self._lock:
            return {
                "privacy_mode": self._privacy_mode,
                "refusal_count": self._refusal_count,
            }


def _host_of(url: str) -> str:
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
    except ValueError:
        host = ""
    return host.lower()


# Process-wide singleton so any module can import and consult it.
GUARD: Final[PrivacyGuard] = PrivacyGuard()


__all__ = [
    "PrivacyGuard",
    "OutboundRefused",
    "ALWAYS_ALLOWED_HOSTS",
    "GUARD",
]
