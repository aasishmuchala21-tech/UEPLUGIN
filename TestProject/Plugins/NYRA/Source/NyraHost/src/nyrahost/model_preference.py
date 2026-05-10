"""Model preference — per-conversation Claude model override (Aura parity).

Aura ships an in-UI model selector showing relative cost between Sonnet
and Opus. NYRA's wedge is "no new bill", but a power user with a Claude
subscription that has both Sonnet (cheap, fast) and Opus (slow, smart)
still wants runtime control.

Surface:
  - ``ModelPreference.allowed_models()`` — the closed set of recognized
    Claude CLI model strings. Closed-set is deliberate; arbitrary model
    strings would let an LLM-injected setting redirect to a model the
    user didn't authorize.
  - ``ModelPreference.set_for_conversation(conv_id, model)`` — record a
    preference; persisted in-memory for now (CD-07 storage extension is
    a future migration when settings need to survive restarts).
  - ``ModelPreference.cli_args(conv_id)`` — emit the ``--model X`` argv
    fragment for ClaudeBackend.send to splice into its argv list. Empty
    list means "use Claude CLI's default" (preserves "no new bill"
    semantics — we don't force a model that costs more than the user's
    subscription tier covers).

Why this isn't just a global setting: a UE editor session may have
multiple chats running concurrently (per Phase 8 multi-thread parity
work; see also `_inflight` in chat handlers). Each conversation can pin
its own model so a user can A/B Sonnet-cheap vs Opus-quality side by
side.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Iterable

import structlog

log = structlog.get_logger("nyrahost.model_preference")

__all__ = ["ModelPreference", "ALLOWED_MODELS", "DEFAULT_MODEL_HINT"]

# Closed set per CLAUDE.md tech-stack. Keep this list short and explicit;
# anything unrecognized routes to the CLI default rather than failing.
# Format matches what `claude --model` accepts (slug, not full ID).
ALLOWED_MODELS: Final[frozenset[str]] = frozenset(
    {
        "claude-sonnet-4-6",
        "claude-opus-4-7",
        "claude-haiku-4-5",
    }
)

# What the UI surfaces by default (no implicit upgrade). None means
# "let the CLI pick whatever the subscription tier defaults to".
DEFAULT_MODEL_HINT: Final[str | None] = None


@dataclass
class ModelPreference:
    """In-memory per-conversation model pin."""

    _by_conv: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def allowed_models() -> tuple[str, ...]:
        """Return the closed set in stable display order."""
        # Cheap first → expensive last to nudge cost-aware default selection.
        ordered = (
            "claude-haiku-4-5",
            "claude-sonnet-4-6",
            "claude-opus-4-7",
        )
        # Filter to allowed in case ALLOWED_MODELS changes.
        return tuple(m for m in ordered if m in ALLOWED_MODELS)

    def set_for_conversation(self, conv_id: str, model: str | None) -> bool:
        """Pin a model for one conversation. Returns True on success.

        ``model=None`` clears the pin (back to CLI default).
        Unknown models log a warning and return False — never silently
        accept an unrecognized model string.
        """
        if not isinstance(conv_id, str) or not conv_id:
            log.warning("model_preference_bad_conv_id", conv_id=conv_id)
            return False
        if model is None:
            self._by_conv.pop(conv_id, None)
            log.info("model_preference_cleared", conv_id=conv_id)
            return True
        if model not in ALLOWED_MODELS:
            log.warning("model_preference_unknown_model", model=model)
            return False
        self._by_conv[conv_id] = model
        log.info("model_preference_set", conv_id=conv_id, model=model)
        return True

    def get_for_conversation(self, conv_id: str) -> str | None:
        """Return the pinned model or None if no pin (use CLI default)."""
        return self._by_conv.get(conv_id)

    def cli_args(self, conv_id: str) -> list[str]:
        """Return the argv fragment to splice into ClaudeBackend.send.

        Empty list when no pin is set — caller passes through whatever
        the Claude CLI defaults to under the user's auth.
        """
        model = self._by_conv.get(conv_id)
        if model is None:
            return []
        return ["--model", model]

    def clear_all(self) -> None:
        """Test/diagnostic helper to drop every pin."""
        self._by_conv.clear()
