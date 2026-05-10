from __future__ import annotations

from nyrahost.tools.lighting_tools import (
    LightingAuthoringTool,
    LightingDryRunTool,
    _PRESETS,
)
from nyrahost.tools.scene_types import LightingParams


# -- Preset coverage ---------------------------------------------------------

def test_all_five_presets_present_and_well_formed():
    expected_keys = {"golden_hour", "harsh_overhead", "moody_blue", "studio_fill", "dawn"}
    assert set(_PRESETS.keys()) == expected_keys
    for name, lp in _PRESETS.items():
        assert isinstance(lp, LightingParams)
        assert lp.mood_tags  # every preset must label its mood
        assert lp.primary_light_type in {"directional", "spot", "point", "rect", "sky"}


def test_preset_to_params_known_returns_expected_preset():
    lp = LightingAuthoringTool._preset_to_params("moody_blue")
    assert lp.primary_light_type == "point"
    assert lp.use_exponential_height_fog is True
    assert "cool" in lp.mood_tags


def test_preset_to_params_unknown_raises_value_error():
    """WR-04: unknown preset names must raise instead of silently substituting
    studio_fill. The apply path catches ValueError and returns [-32030] so
    the user sees the typo instead of unintended lighting."""
    import pytest
    with pytest.raises(ValueError, match="Unknown lighting preset"):
        LightingAuthoringTool._preset_to_params("not_a_real_preset")


# -- LightingAuthoringTool.execute (no UE editor present) --------------------

def test_execute_apply_with_preset_returns_actor_metadata():
    tool = LightingAuthoringTool()
    result = tool.execute({"preset_name": "golden_hour", "apply": True})
    assert result.error is None
    assert result.data is not None
    assert result.data["primary_light_type"] == "directional"
    assert "warm" in result.data["mood_tags"]
    # When no unreal module is available, we land on the placeholder with the
    # NYRA_Primary_directional label. When other tests have injected a fake
    # unreal MagicMock into sys.modules, the real spawn code path runs - we
    # accept either path so long as some primary actor entry came back.
    placed = result.data["actors_placed"]
    assert len(placed) >= 1


def test_execute_apply_with_nl_prompt_uses_fallback_when_no_router():
    tool = LightingAuthoringTool()
    result = tool.execute({"nl_prompt": "harsh overhead studio", "apply": True})
    assert result.error is None
    assert result.data["primary_light_type"] == "directional"
    assert "harsh" in result.data["mood_tags"]


def test_execute_dry_run_emits_ws_notification_and_does_not_place():
    received = []
    tool = LightingAuthoringTool(ws_notifier=received.append)
    result = tool.execute({"preset_name": "moody_blue", "apply": False})
    assert result.error is None
    assert result.data["dry_run"] is True
    assert len(received) == 1
    notif = received[0]
    assert notif["type"] == "dry_run_preview"
    assert notif["primary_light_type"] == "point"
    assert "lighting_params" in notif


def test_execute_returns_error_when_no_input_provided():
    tool = LightingAuthoringTool()
    result = tool.execute({})
    assert result.error is not None
    assert "-32030" in result.error


def test_execute_image_path_missing_returns_error():
    tool = LightingAuthoringTool()
    result = tool.execute({"reference_image_path": "C:/does/not/exist.png", "apply": True})
    assert result.error is not None
    assert "-32030" in result.error


# -- LightingDryRunTool ------------------------------------------------------

def test_dry_run_tool_with_preset_emits_notification():
    received = []
    tool = LightingDryRunTool(ws_notifier=received.append)
    result = tool.execute({"preset_name": "dawn"})
    assert result.error is None
    assert result.data["dry_run"] is True
    assert result.data["preset"] == "dawn"
    assert len(received) == 1
    assert received[0]["primary_light_type"] == "directional"


def test_dry_run_tool_with_custom_json_emits_notification():
    received = []
    tool = LightingDryRunTool(ws_notifier=received.append)
    payload = '{"primary_light_type": "spot", "primary_intensity": 1.2, "mood_tags": ["dramatic"]}'
    result = tool.execute({"lighting_params_json": payload})
    assert result.error is None
    assert received[0]["primary_light_type"] == "spot"
    assert "dramatic" in received[0]["mood_tags"]


def test_dry_run_tool_invalid_json_returns_error():
    tool = LightingDryRunTool()
    result = tool.execute({"lighting_params_json": "{not valid"})
    assert result.error is not None
    assert "-32030" in result.error


def test_dry_run_tool_no_input_returns_error():
    tool = LightingDryRunTool()
    result = tool.execute({})
    assert result.error is not None
    assert "-32030" in result.error
