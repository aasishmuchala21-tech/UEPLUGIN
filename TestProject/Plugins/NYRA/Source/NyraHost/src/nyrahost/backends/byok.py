"""BYOKBackend — Bring Your Own API Key advanced-config path (Plan 02-05).

For users who do not have a Claude Code CLI subscription and instead want
to provide an Anthropic API key directly. This path is surfaced ONLY as an
"Advanced Configuration" option (not the primary v1 path per CLAUDE.md).

Key differences from ClaudeBackend:
  * Uses ``ANTHROPIC_API_KEY`` env var directly (user-provided, not scrubbed).
  * Calls the Anthropic Messages API over HTTPS, not the CLI subprocess.
  * Supports only text input (no computer-use, no MCP tools) in v1.

v1.1 roadmap: OpenAI Codex Backend follows the same pattern.

SC#1 gate: does NOT apply here — the API key path is a direct Anthropic
customer with their own account; the ToS concern in SC#1 is about third-party
products offering claude.ai login, not about users using their own API key
through a tool they configure themselves.
"""
from __future__ import annotations

from typing import Final

import httpx
import structlog

from nyrahost.attachments import AttachmentRef
from nyrahost.backends.base import (
    AgentBackend,
    BackendEvent,
    Delta,
    Done,
    Error,
    HealthState,
    Retry,
)

__all__ = ["BYOKBackend"]

log: Final = structlog.get_logger(__name__)

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
"""Anthropic Messages API base URL."""

_ERROR_CODE = -32_001


class BYOKBackend(AgentBackend):
    """Direct Anthropic API key path — advanced config only.

    Users opt in by setting ``ANTHROPIC_API_KEY`` in their
    ``%LOCALAPPDATA%/NYRA/settings.toml`` or equivalent. NYRA reads it at
    startup and instantiates this backend instead of (or alongside) ClaudeBackend.

    ``name = "byok"`` is registered in ``BACKEND_REGISTRY["byok"]``.
    """

    name: str = "byok"

    def __init__(self, api_key: str | None = None) -> None:
        # api_key None here is fine — health_check will return NOT_CONFIGURED
        # and callers will fall back gracefully.
        self._api_key: Final[str | None] = api_key
        self._client: Final[httpx.AsyncClient | None] = (
            httpx.AsyncClient(
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
            if api_key
            else None
        )

    async def send(
        self,
        conversation_id: str,
        req_id: str,
        content: str,
        attachments: list[AttachmentRef],
        mcp_config_path: Path | None,
        on_event: callable,
    ) -> None:
        """Send a message via the Anthropic Messages API and stream events."""
        if self._client is None:
            await on_event(
                Error(
                    code=_ERROR_CODE,
                    message="byok_not_configured",
                    remediation=(
                        "ANTHROPIC_API_KEY is not set. "
                        "Set it in Settings → Advanced → Anthropic API Key, "
                        "or use the Claude Code CLI path instead."
                    ),
                    retryable=False,
                )
            )
            return

        try:
            # Build request payload (stream: true → NDJSON per Anthropic spec)
            payload = {
                "model": "claude-opus-4-7-20250514",
                "messages": [{"role": "user", "content": content}],
                "max_tokens": 8192,
                "stream": True,
            }
            async with self._client.stream("POST", _ANTHROPIC_API_URL, json=payload) as resp:
                if resp.status_code == 401:
                    await on_event(
                        Error(
                            code=_ERROR_CODE,
                            message="auth_failed",
                            remediation=(
                                "ANTHROPIC_API_KEY is invalid or expired. "
                                "Check your key at console.anthropic.com/settings/keys."
                            ),
                            retryable=False,
                        )
                    )
                    return
                if resp.status_code == 429:
                    await on_event(
                        Retry(
                            attempt=1,
                            delay_ms=5_000,
                            error_category="rate_limit",
                        )
                    )
                    return

                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    raw = line[6:].strip()
                    if raw == "[DONE]":
                        break
                    # Parse SSE data line — {"type": "...", ...}
                    import json

                    try:
                        obj = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    ev_type = obj.get("type", "")
                    if ev_type == "content_block_delta":
                        delta = obj.get("delta", {})
                        if delta.get("type") == "text_delta":
                            await on_event(Delta(text=delta.get("text_delta", "")))
                    elif ev_type == "message_stop":
                        usage = obj.get("usage", {})
                        await on_event(
                            Done(
                                usage={
                                    "input_tokens": usage.get("input_tokens", 0),
                                    "output_tokens": usage.get("output_tokens", 0),
                                },
                                stop_reason=obj.get("stop_reason", "end_turn"),
                            )
                        )
        except httpx.TimeoutException:
            await on_event(
                Error(
                    code=_ERROR_CODE,
                    message="timeout",
                    remediation=(
                        "Anthropic API request timed out. Check your internet "
                        "connection or try again."
                    ),
                    retryable=True,
                )
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("byok_send_error", req_id=req_id)
            await on_event(
                Error(
                    code=_ERROR_CODE,
                    message="api_error",
                    remediation=f"Unexpected error: {type(exc).__name__}. See logs.",
                    retryable=True,
                )
            )

    async def cancel(self, req_id: str) -> None:
        # httpx streaming is not trivially cancellable mid-request without
        # closing the entire client. For v1, cancel is a no-op with a warning.
        log.warning("byok_cancel_not_implemented", req_id=req_id)

    async def health_check(self) -> HealthState:
        if self._client is None:
            return HealthState.NOT_INSTALLED
        try:
            # Light probe: send a minimal request to check key validity + quota
            resp = await self._client.post(
                _ANTHROPIC_API_URL,
                json={
                    "model": "claude-opus-4-7-20250514",
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                },
            )
            if resp.status_code == 200:
                return HealthState.READY
            if resp.status_code == 401:
                return HealthState.AUTH_DRIFT
            return HealthState.UNKNOWN
        except Exception:  # noqa: BLE001
            return HealthState.UNKNOWN