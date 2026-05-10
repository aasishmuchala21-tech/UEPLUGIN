"""tests/test_animbp_authoring.py — Plan 08-07 / PARITY-07 unit tests.

Coverage per PLAN.md §"Task 4":
  - nyra_animbp_create returns ok with mocked unreal.AnimBlueprintFactory
  - Idempotent: second call dedupes (deduped=True)
  - Non-Skeleton skeleton_path → err
  - Missing AnimBlueprintFactory symbol → register-time err
  - nyra_animbp_add_state_machine on missing AnimBP → err
  - nyra_animbp_add_transition with helper returning false → err

The `unreal` module is fabricated in-process via SimpleNamespace + dummy
classes (the same pattern as test_actor_tools / test_meshy_tools). Live
UE round-trip lives in 08-07-VERIFICATION.md (operator runbook).

Per PLAN.md, live tests are operator-bound — no live pytest invocation
hits a real UE editor in this file.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# Make the package importable when pytest is run from the tests/ dir.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nyrahost.tools import base as tools_base


# -----------------------------------------------------------------------------
# Shared fixtures
# -----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_idempotency():
    """Reset the process-local idempotency cache between tests so each
    test sees a cold dedup state (BL-05).
    """
    tools_base.idempotent_clear()
    yield
    tools_base.idempotent_clear()


def _make_unreal_module(*, with_factory: bool = True, with_helper: bool = True,
                       skeleton_is_correct_class: bool = True,
                       create_asset_returns: object = "OK",
                       helper_add_machine_returns: str = "Locomotion",
                       helper_add_state_returns: str = "Idle",
                       helper_add_transition_returns: bool = True):
    """Build a fake `unreal` module with just the symbols animbp_tools touches.

    Patched into sys.modules and stripped after the test. Each parameter
    flips one branch of the tools' control flow.
    """

    # Dummy classes for isinstance checks
    class AnimBlueprint:
        pass

    class Skeleton:
        pass

    class WrongAsset:
        pass

    skeleton_instance = Skeleton() if skeleton_is_correct_class else WrongAsset()
    abp_instance = AnimBlueprint()

    # The asset library: load_asset returns skeleton or AnimBP based on path.
    def _load_asset(path: str):
        if "Skeleton" in path:
            return skeleton_instance
        if "ABP" in path or "Anim" in path:
            return abp_instance
        return None

    EditorAssetLibrary = SimpleNamespace(
        load_asset=MagicMock(side_effect=_load_asset),
        save_asset=MagicMock(return_value=True),
    )

    # The asset-tools factory shim used by AnimBPCreateTool.
    asset_tools = SimpleNamespace(
        create_asset=MagicMock(return_value=create_asset_returns),
    )
    AssetToolsHelpers = SimpleNamespace(
        get_asset_tools=MagicMock(return_value=asset_tools),
    )

    # AnimBlueprintFactory is omitted entirely when with_factory=False so the
    # tool's `hasattr(unreal, "AnimBlueprintFactory")` gate fires.
    AnimBlueprintFactory = MagicMock(
        return_value=SimpleNamespace(set_editor_property=MagicMock())
    )

    # NyraAnimBPHelper exposes three static methods the tools call.
    NyraAnimBPHelper = SimpleNamespace(
        add_state_machine=MagicMock(return_value=helper_add_machine_returns),
        add_state=MagicMock(return_value=helper_add_state_returns),
        add_transition=MagicMock(return_value=helper_add_transition_returns),
    )

    # ScopedEditorTransaction is consulted by session_transaction(); the
    # helper's no-op fallback handles its absence, but expose it so the
    # production code path runs end-to-end.
    class _Txn:
        def __init__(self, label):
            self.label = label
            self.cancel = True

    fake = SimpleNamespace(
        AnimBlueprint=AnimBlueprint,
        Skeleton=Skeleton,
        EditorAssetLibrary=EditorAssetLibrary,
        AssetToolsHelpers=AssetToolsHelpers,
        Vector2D=lambda x, y: SimpleNamespace(x=x, y=y),
        Name=lambda s: s,  # unreal.Name is a wrapper; treat as identity for tests.
        ScopedEditorTransaction=_Txn,
    )
    if with_factory:
        fake.AnimBlueprintFactory = AnimBlueprintFactory
    if with_helper:
        fake.NyraAnimBPHelper = NyraAnimBPHelper

    # Stash key mocks on the module so tests can assert on them.
    fake._mocks = SimpleNamespace(
        AnimBlueprintFactory=AnimBlueprintFactory,
        NyraAnimBPHelper=NyraAnimBPHelper,
        EditorAssetLibrary=EditorAssetLibrary,
        asset_tools=asset_tools,
        skeleton_instance=skeleton_instance,
        abp_instance=abp_instance,
    )
    return fake


@pytest.fixture
def fake_unreal(monkeypatch):
    """Install a default `unreal` mock + fresh import of animbp_tools."""
    fake = _make_unreal_module()
    monkeypatch.setitem(sys.modules, "unreal", fake)
    # Force a re-import so module-level state (if any) sees the fake.
    sys.modules.pop("nyrahost.tools.animbp_tools", None)
    from nyrahost.tools import animbp_tools  # noqa: WPS433 — local import is intentional
    return fake, animbp_tools


# -----------------------------------------------------------------------------
# Schema sanity (no live unreal needed)
# -----------------------------------------------------------------------------


def test_tool_schemas_have_required_fields(fake_unreal):
    _, animbp_tools = fake_unreal
    create = animbp_tools.AnimBPCreateTool()
    addsm = animbp_tools.AnimBPAddStateMachineTool()
    addtr = animbp_tools.AnimBPAddTransitionTool()

    assert create.name == "nyra_animbp_create"
    assert addsm.name == "nyra_animbp_add_state_machine"
    assert addtr.name == "nyra_animbp_add_transition"

    assert "asset_path" in create.parameters["required"]
    assert "skeleton_path" in create.parameters["required"]
    assert "animbp_path" in addsm.parameters["required"]
    assert "machine_name" in addsm.parameters["required"]
    for k in ("animbp_path", "machine_name", "from_state", "to_state"):
        assert k in addtr.parameters["required"]


# -----------------------------------------------------------------------------
# AnimBPCreateTool
# -----------------------------------------------------------------------------


def test_create_succeeds_with_factory_and_skeleton(fake_unreal):
    _, animbp_tools = fake_unreal
    tool = animbp_tools.AnimBPCreateTool()
    res = tool.execute({
        "asset_path": "/Game/Anim/ABP_Hero",
        "skeleton_path": "/Game/Anim/SK_Hero_Skeleton",
    })
    assert res.error is None, res.error
    assert res.data["asset_path"] == "/Game/Anim/ABP_Hero"
    assert res.data["skeleton"] == "/Game/Anim/SK_Hero_Skeleton"


def test_create_idempotent_dedups(fake_unreal):
    _, animbp_tools = fake_unreal
    tool = animbp_tools.AnimBPCreateTool()
    params = {
        "asset_path": "/Game/Anim/ABP_Hero",
        "skeleton_path": "/Game/Anim/SK_Hero_Skeleton",
    }
    r1 = tool.execute(params)
    r2 = tool.execute(params)
    assert r1.error is None
    assert r2.error is None
    assert r2.data.get("deduped") is True


def test_create_wrong_skeleton_class_returns_err(monkeypatch):
    fake = _make_unreal_module(skeleton_is_correct_class=False)
    monkeypatch.setitem(sys.modules, "unreal", fake)
    sys.modules.pop("nyrahost.tools.animbp_tools", None)
    from nyrahost.tools import animbp_tools  # noqa: WPS433

    tool = animbp_tools.AnimBPCreateTool()
    res = tool.execute({
        "asset_path": "/Game/Anim/ABP_Hero",
        "skeleton_path": "/Game/Anim/SK_Hero_Skeleton",
    })
    assert res.error is not None
    assert "USkeleton" in res.error


def test_create_missing_factory_symbol_returns_err(monkeypatch):
    fake = _make_unreal_module(with_factory=False)
    monkeypatch.setitem(sys.modules, "unreal", fake)
    sys.modules.pop("nyrahost.tools.animbp_tools", None)
    from nyrahost.tools import animbp_tools  # noqa: WPS433

    tool = animbp_tools.AnimBPCreateTool()
    res = tool.execute({
        "asset_path": "/Game/Anim/ABP_Hero",
        "skeleton_path": "/Game/Anim/SK_Hero_Skeleton",
    })
    assert res.error is not None
    assert "AnimBlueprintFactory" in res.error


def test_create_skeleton_not_found_returns_err(monkeypatch):
    fake = _make_unreal_module()
    fake.EditorAssetLibrary.load_asset = MagicMock(return_value=None)
    monkeypatch.setitem(sys.modules, "unreal", fake)
    sys.modules.pop("nyrahost.tools.animbp_tools", None)
    from nyrahost.tools import animbp_tools  # noqa: WPS433

    tool = animbp_tools.AnimBPCreateTool()
    res = tool.execute({
        "asset_path": "/Game/Anim/ABP_Hero",
        "skeleton_path": "/Game/Missing/Skel",
    })
    assert res.error is not None
    assert "not found" in res.error.lower()


# -----------------------------------------------------------------------------
# AnimBPAddStateMachineTool
# -----------------------------------------------------------------------------


def test_add_state_machine_succeeds(fake_unreal):
    fake, animbp_tools = fake_unreal
    tool = animbp_tools.AnimBPAddStateMachineTool()
    res = tool.execute({
        "animbp_path": "/Game/Anim/ABP_Hero",
        "machine_name": "Locomotion",
        "states": ["Idle", "Walk", "Run"],
    })
    assert res.error is None, res.error
    assert res.data["machine_name"] == "Locomotion"
    # The fake helper returns "Idle" each time so we expect 3 entries (idempotency at the C++ level).
    assert len(res.data["states"]) == 3
    # Each call to add_state should have been made.
    assert fake._mocks.NyraAnimBPHelper.add_state.call_count == 3


def test_add_state_machine_missing_animbp_returns_err(monkeypatch):
    fake = _make_unreal_module()
    # load_asset returns None for any path
    fake.EditorAssetLibrary.load_asset = MagicMock(return_value=None)
    monkeypatch.setitem(sys.modules, "unreal", fake)
    sys.modules.pop("nyrahost.tools.animbp_tools", None)
    from nyrahost.tools import animbp_tools  # noqa: WPS433

    tool = animbp_tools.AnimBPAddStateMachineTool()
    res = tool.execute({
        "animbp_path": "/Game/Anim/Missing",
        "machine_name": "Locomotion",
    })
    assert res.error is not None
    assert "AnimBP not found" in res.error


def test_add_state_machine_missing_helper_returns_err(monkeypatch):
    fake = _make_unreal_module(with_helper=False)
    monkeypatch.setitem(sys.modules, "unreal", fake)
    sys.modules.pop("nyrahost.tools.animbp_tools", None)
    from nyrahost.tools import animbp_tools  # noqa: WPS433

    tool = animbp_tools.AnimBPAddStateMachineTool()
    res = tool.execute({
        "animbp_path": "/Game/Anim/ABP_Hero",
        "machine_name": "Locomotion",
    })
    assert res.error is not None
    assert "NyraAnimBPHelper" in res.error


def test_add_state_machine_helper_returns_empty_name_is_err(monkeypatch):
    fake = _make_unreal_module(helper_add_machine_returns="")
    monkeypatch.setitem(sys.modules, "unreal", fake)
    sys.modules.pop("nyrahost.tools.animbp_tools", None)
    from nyrahost.tools import animbp_tools  # noqa: WPS433

    tool = animbp_tools.AnimBPAddStateMachineTool()
    res = tool.execute({
        "animbp_path": "/Game/Anim/ABP_Hero",
        "machine_name": "Locomotion",
    })
    assert res.error is not None
    assert "empty name" in res.error.lower() or "no AnimGraph" in res.error


# -----------------------------------------------------------------------------
# AnimBPAddTransitionTool
# -----------------------------------------------------------------------------


def test_add_transition_succeeds(fake_unreal):
    fake, animbp_tools = fake_unreal
    tool = animbp_tools.AnimBPAddTransitionTool()
    res = tool.execute({
        "animbp_path": "/Game/Anim/ABP_Hero",
        "machine_name": "Locomotion",
        "from_state": "Idle",
        "to_state": "Walk",
    })
    assert res.error is None, res.error
    assert res.data["from_state"] == "Idle"
    assert res.data["to_state"] == "Walk"
    fake._mocks.NyraAnimBPHelper.add_transition.assert_called_once()


def test_add_transition_helper_refuses_returns_err(monkeypatch):
    fake = _make_unreal_module(helper_add_transition_returns=False)
    monkeypatch.setitem(sys.modules, "unreal", fake)
    sys.modules.pop("nyrahost.tools.animbp_tools", None)
    from nyrahost.tools import animbp_tools  # noqa: WPS433

    tool = animbp_tools.AnimBPAddTransitionTool()
    res = tool.execute({
        "animbp_path": "/Game/Anim/ABP_Hero",
        "machine_name": "Locomotion",
        "from_state": "Bogus",
        "to_state": "Walk",
    })
    assert res.error is not None
    assert "AddTransition refused" in res.error


def test_add_transition_idempotent_dedups(fake_unreal):
    _, animbp_tools = fake_unreal
    tool = animbp_tools.AnimBPAddTransitionTool()
    params = {
        "animbp_path": "/Game/Anim/ABP_Hero",
        "machine_name": "Locomotion",
        "from_state": "Idle",
        "to_state": "Walk",
    }
    r1 = tool.execute(params)
    r2 = tool.execute(params)
    assert r1.error is None
    assert r2.error is None
    assert r2.data.get("deduped") is True


def test_add_transition_missing_helper_returns_err(monkeypatch):
    fake = _make_unreal_module(with_helper=False)
    monkeypatch.setitem(sys.modules, "unreal", fake)
    sys.modules.pop("nyrahost.tools.animbp_tools", None)
    from nyrahost.tools import animbp_tools  # noqa: WPS433

    tool = animbp_tools.AnimBPAddTransitionTool()
    res = tool.execute({
        "animbp_path": "/Game/Anim/ABP_Hero",
        "machine_name": "Locomotion",
        "from_state": "Idle",
        "to_state": "Walk",
    })
    assert res.error is not None
    assert "NyraAnimBPHelper" in res.error
