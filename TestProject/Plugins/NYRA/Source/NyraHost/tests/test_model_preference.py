"""Model preference tests — closed-set validation + cli_args wiring."""
from __future__ import annotations

import pytest

from nyrahost.model_preference import (
    ALLOWED_MODELS,
    ModelPreference,
)


class TestAllowedModels:
    def test_returns_known_claude_slugs(self):
        models = ModelPreference.allowed_models()
        # Order: cheap → expensive (cost-aware default selection)
        assert models[0] == "claude-haiku-4-5"
        assert "claude-sonnet-4-6" in models
        assert "claude-opus-4-7" in models

    def test_all_returned_are_in_allowed_set(self):
        for m in ModelPreference.allowed_models():
            assert m in ALLOWED_MODELS


class TestSetForConversation:
    def test_known_model_accepted(self):
        pref = ModelPreference()
        ok = pref.set_for_conversation("conv-1", "claude-opus-4-7")
        assert ok is True
        assert pref.get_for_conversation("conv-1") == "claude-opus-4-7"

    def test_unknown_model_rejected(self):
        pref = ModelPreference()
        ok = pref.set_for_conversation("conv-1", "gpt-5-supremo")
        assert ok is False
        assert pref.get_for_conversation("conv-1") is None

    def test_none_clears_pin(self):
        pref = ModelPreference()
        pref.set_for_conversation("conv-1", "claude-sonnet-4-6")
        assert pref.get_for_conversation("conv-1") == "claude-sonnet-4-6"
        pref.set_for_conversation("conv-1", None)
        assert pref.get_for_conversation("conv-1") is None

    def test_empty_conv_id_rejected(self):
        pref = ModelPreference()
        assert pref.set_for_conversation("", "claude-opus-4-7") is False

    def test_isolation_between_conversations(self):
        pref = ModelPreference()
        pref.set_for_conversation("a", "claude-opus-4-7")
        pref.set_for_conversation("b", "claude-haiku-4-5")
        assert pref.get_for_conversation("a") == "claude-opus-4-7"
        assert pref.get_for_conversation("b") == "claude-haiku-4-5"


class TestCliArgs:
    def test_no_pin_returns_empty_list(self):
        pref = ModelPreference()
        assert pref.cli_args("conv-1") == []

    def test_pin_returns_model_flag(self):
        pref = ModelPreference()
        pref.set_for_conversation("conv-1", "claude-opus-4-7")
        assert pref.cli_args("conv-1") == ["--model", "claude-opus-4-7"]

    def test_unrelated_conversation_unaffected(self):
        pref = ModelPreference()
        pref.set_for_conversation("conv-1", "claude-opus-4-7")
        # Different conv — no pin → empty
        assert pref.cli_args("conv-2") == []


class TestClearAll:
    def test_drops_every_pin(self):
        pref = ModelPreference()
        pref.set_for_conversation("a", "claude-opus-4-7")
        pref.set_for_conversation("b", "claude-sonnet-4-6")
        pref.clear_all()
        assert pref.get_for_conversation("a") is None
        assert pref.get_for_conversation("b") is None
