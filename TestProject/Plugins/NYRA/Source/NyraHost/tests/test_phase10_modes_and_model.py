"""Phase 10-2 + 10-3 — operating mode + model selector handlers."""
from __future__ import annotations


import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from nyrahost.handlers.session_mode import (
    AURA_MODES,
    BACKEND_MODES,
    SessionModeHandler,
)
from nyrahost.safe_mode import NyraPermissionGate
from nyrahost.model_preference import ModelPreference, ALLOWED_MODELS


# ---------- 10-2 three-mode toggle ----------

def _make_handler(with_gate: bool = True) -> SessionModeHandler:
    router = MagicMock()
    router.enter_privacy_mode = AsyncMock()
    router.exit_privacy_mode = AsyncMock()
    gate = NyraPermissionGate() if with_gate else None
    return SessionModeHandler(router=router, permission_gate=gate)


def test_set_operating_ask():
    h = _make_handler()
    out = asyncio.run(h.on_set_mode({"mode": "ask"}))
    assert out["mode_applied"] is True
    assert out["operating_mode"] == "ask"
    assert h.operating_mode == "ask"


def test_set_operating_plan_then_agent():
    h = _make_handler()
    asyncio.run(h.on_set_mode({"mode": "plan"}))
    assert h.operating_mode == "plan"
    asyncio.run(h.on_set_mode({"mode": "agent"}))
    assert h.operating_mode == "agent"


def test_backend_privacy_path_routed():
    h = _make_handler()
    out = asyncio.run(h.on_set_mode({"mode": "privacy"}))
    assert out["backend_mode"] == "privacy"
    h._router.enter_privacy_mode.assert_awaited_once()


def test_explicit_two_axis_set():
    h = _make_handler()
    out = asyncio.run(h.on_set_mode(
        {"operating_mode": "agent", "backend_mode": "normal"}
    ))
    assert out["operating_mode"] == "agent"
    assert out["backend_mode"] == "normal"
    h._router.exit_privacy_mode.assert_awaited_once()


def test_invalid_mode_raises():
    h = _make_handler()
    with pytest.raises(ValueError):
        asyncio.run(h.on_set_mode({"mode": "yolo"}))


def test_gate_state_is_propagated():
    h = _make_handler()
    asyncio.run(h.on_set_mode({"mode": "agent"}))
    assert h._gate.operating_mode == "agent"
    asyncio.run(h.on_set_mode({"mode": "ask"}))
    assert h._gate.operating_mode == "ask"


def test_operating_modes_constant_matches_aura_set():
    assert AURA_MODES == frozenset({"ask", "plan", "agent"})
    assert "privacy" in BACKEND_MODES


# ---------- 10-3 model selector ----------

def test_allowed_models_stable_order():
    models = ModelPreference.allowed_models()
    # cheap → expensive
    assert models[0] == "claude-haiku-4-5"
    assert models[-1] == "claude-opus-4-7"
    assert set(models).issubset(ALLOWED_MODELS)


def test_set_and_read_pin():
    pref = ModelPreference()
    assert pref.set_for_conversation("conv-1", "claude-opus-4-7") is True
    args = pref.cli_args("conv-1")
    assert "--model" in args
    assert "claude-opus-4-7" in args


def test_set_unknown_model_returns_false():
    pref = ModelPreference()
    assert pref.set_for_conversation("conv-1", "claude-omega") is False


def test_clear_pin_with_none():
    pref = ModelPreference()
    pref.set_for_conversation("conv-1", "claude-opus-4-7")
    pref.set_for_conversation("conv-1", None)
    assert pref.cli_args("conv-1") == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# ---------- 10-3 settings/get-model + settings/set-model handlers ----------

from nyrahost.handlers.model_settings import ModelSettingsHandlers


def test_settings_get_returns_allowed_models():
    h = ModelSettingsHandlers(ModelPreference())
    out = asyncio.run(h.on_get({"conversation_id": "c-1"}))
    assert out["model"] is None
    assert out["allowed_models"][0] == "claude-haiku-4-5"


def test_settings_set_then_get():
    pref = ModelPreference()
    h = ModelSettingsHandlers(pref)
    set_res = asyncio.run(h.on_set(
        {"conversation_id": "c-2", "model": "claude-opus-4-7"}
    ))
    assert set_res["saved"] is True
    get_res = asyncio.run(h.on_get({"conversation_id": "c-2"}))
    assert get_res["model"] == "claude-opus-4-7"


def test_settings_set_null_clears_pin():
    pref = ModelPreference()
    h = ModelSettingsHandlers(pref)
    asyncio.run(h.on_set({"conversation_id": "c-3", "model": "claude-opus-4-7"}))
    asyncio.run(h.on_set({"conversation_id": "c-3", "model": None}))
    out = asyncio.run(h.on_get({"conversation_id": "c-3"}))
    assert out["model"] is None


def test_settings_set_unknown_model_returns_minus32043():
    h = ModelSettingsHandlers(ModelPreference())
    out = asyncio.run(h.on_set(
        {"conversation_id": "c-4", "model": "claude-omega"}
    ))
    assert out["error"]["code"] == -32043
    assert out["error"]["message"] == "unknown_model"


def test_settings_set_missing_conversation_id():
    h = ModelSettingsHandlers(ModelPreference())
    out = asyncio.run(h.on_set({"model": "claude-opus-4-7"}))
    assert out["error"]["code"] == -32602
