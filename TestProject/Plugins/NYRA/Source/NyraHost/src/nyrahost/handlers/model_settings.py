"""settings/get-model + settings/set-model handlers — Phase 10-3.

Surfaces the existing ``ModelPreference`` (per-conversation pin) over
the WS so the chat panel's model-selector pill (Aura parity) has
something to talk to. The store itself is unchanged — this is pure
plumbing.
"""
from __future__ import annotations

from typing import Final, Optional

import structlog

from nyrahost.model_preference import ModelPreference

log = structlog.get_logger("nyrahost.handlers.model_settings")

ERR_BAD_INPUT: Final[int] = -32602
ERR_UNKNOWN_MODEL: Final[int] = -32043


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


class ModelSettingsHandlers:
    """Reads + writes the per-conversation Claude model pin."""

    def __init__(self, model_preference: ModelPreference) -> None:
        self._pref = model_preference

    async def on_get(self, params: dict, session=None, ws=None) -> dict:
        """Return the current pin + the set of allowed models for the UI.

        params:
          conversation_id (str, required)
        """
        conv_id = params.get("conversation_id")
        if not isinstance(conv_id, str) or not conv_id:
            return _err(ERR_BAD_INPUT, "missing_field", "conversation_id")
        return {
            "conversation_id": conv_id,
            "model": self._pref.get_for_conversation(conv_id),
            "allowed_models": list(ModelPreference.allowed_models()),
        }

    async def on_set(self, params: dict, session=None, ws=None) -> dict:
        """Pin (or clear) a model for one conversation.

        params:
          conversation_id (str, required)
          model           (str | None) — None clears the pin
        """
        conv_id = params.get("conversation_id")
        if not isinstance(conv_id, str) or not conv_id:
            return _err(ERR_BAD_INPUT, "missing_field", "conversation_id")
        # Allow explicit null to clear; missing key = error
        if "model" not in params:
            return _err(ERR_BAD_INPUT, "missing_field", "model")
        model = params["model"]
        if model is not None and not isinstance(model, str):
            return _err(ERR_BAD_INPUT, "bad_type", "model must be str or null")
        ok = self._pref.set_for_conversation(conv_id, model)
        if not ok:
            return _err(
                ERR_UNKNOWN_MODEL, "unknown_model", str(model),
                remediation=(
                    "Pick from allowed_models in settings/get-model. "
                    "Models outside the closed set are rejected to prevent "
                    "an LLM-injected setting redirecting auth tokens."
                ),
            )
        return {
            "conversation_id": conv_id,
            "model": model,
            "saved": True,
        }


__all__ = [
    "ModelSettingsHandlers",
    "ERR_BAD_INPUT",
    "ERR_UNKNOWN_MODEL",
]
