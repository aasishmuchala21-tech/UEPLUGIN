"""Tests for nyrahost.tools.niagara_tools (PARITY-05).

Coverage (Plan 08-05 Task 4):
  - Schema shape (canonical NyraTool: name / description / parameters /
    required keys per the JSON Schema).
  - Parameter validation: missing required keys / malformed values return
    err envelopes, not exceptions.
  - HAS_UNREAL=False path: every tool returns NyraToolResult.err with a
    non-empty message and the err dict round-trips through to_dict() as
    a JSON-RPC -32000 envelope (BL-01).
  - T-08-01 graceful degradation: when `unreal.NiagaraSystemFactoryNew`
    or `unreal.NyraNiagaraHelper` is missing, every tool returns
    `not_supported_on_this_ue_version`.
  - T-08-04 GPU + CPU coverage: `nyra_niagara_add_emitter` succeeds with
    `sim_target='cpu'` AND with `sim_target='gpu'`.
  - BL-12 isinstance-check: `_load_niagara_system` returns None when the
    path resolves to the wrong asset class (mocked Material).
  - BL-06 scalar readback: in-tolerance readback returns ok; out-of-tolerance
    triggers `post_condition_failed`.
  - BL-05 idempotency: a second identical call returns deduped=True.
  - sim_target enum guard rejects values outside ['cpu', 'gpu'].

Live tests against a real UE editor are deferred to
`08-05-VERIFICATION.md` (operator-run, per-UE-version).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nyrahost.tools.base import NyraToolResult, idempotent_clear
from nyrahost.tools import niagara_tools
from nyrahost.tools.niagara_tools import (
    NiagaraAddEmitterTool,
    NiagaraCreateSystemTool,
    NiagaraSetModuleParameterTool,
    _load_niagara_system,
    _resolve_factory,
    _resolve_helper,
    _resolve_system_class,
)


# ---------------------------------------------------------------------------
# autouse: clear idempotency cache between tests (BL-05 cache is process-local)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_idempotency():
    idempotent_clear()
    yield
    idempotent_clear()


# ---------------------------------------------------------------------------
# Test helpers — build a fake `unreal` namespace that the tools can drive.
# ---------------------------------------------------------------------------


class _FakeNiagaraSystem:
    """Stand-in for unreal.NiagaraSystem instances. _load_niagara_system uses
    isinstance() against the class object to reject wrong-class assets."""
    def __init__(self, path: str):
        self._path = path

    def get_path_name(self):
        return self._path


class _FakeMaterial:
    """Stand-in for the wrong-asset-class branch (BL-12 isinstance check)."""


def _build_fake_unreal(*, system_class=None, factory=None, helper=None,
                       loaded_asset=None, vector_cls=None, name_cls=None):
    """Build a MagicMock `unreal` module with the symbols the tools reach for.

    Each kwarg overrides one of the symbols; pass `None` to leave it
    absent (i.e. `hasattr(fake, '<name>')` is False) so the
    `_resolve_*` helpers see a missing symbol on this UE build.
    """
    fake = MagicMock()
    # Default to absent — del attributes that callers didn't set.
    if system_class is None:
        del fake.NiagaraSystem
    else:
        fake.NiagaraSystem = system_class
    if factory is None:
        del fake.NiagaraSystemFactoryNew
    else:
        fake.NiagaraSystemFactoryNew = factory
    if helper is None:
        del fake.NyraNiagaraHelper
    else:
        fake.NyraNiagaraHelper = helper

    # EditorAssetLibrary.load_asset always returns whatever the test set.
    fake.EditorAssetLibrary.load_asset.return_value = loaded_asset
    # save_asset is a no-op stub.
    fake.EditorAssetLibrary.save_asset.return_value = True

    # AssetToolsHelpers.get_asset_tools().create_asset returns a stub asset.
    asset_tools = MagicMock()
    asset_tools.create_asset.return_value = MagicMock(name="created_asset")
    fake.AssetToolsHelpers.get_asset_tools.return_value = asset_tools

    fake.Vector = vector_cls or MagicMock(name="VectorCtor")
    fake.Name   = name_cls   or (lambda x: x)  # identity for FName-like usage

    return fake


def _patch_unreal(fake_unreal):
    """Convenience: patch both `unreal` symbol and `HAS_UNREAL` flag."""
    return patch.multiple(
        niagara_tools,
        unreal=fake_unreal,
        HAS_UNREAL=True,
    )


# ---------------------------------------------------------------------------
# Schema shape — every NyraTool must have name / description / parameters
# with required keys per the JSON Schema, and to_dict() round-trips ok+err.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tool_cls,expected_name", [
    (NiagaraCreateSystemTool,        "nyra_niagara_create_system"),
    (NiagaraAddEmitterTool,          "nyra_niagara_add_emitter"),
    (NiagaraSetModuleParameterTool,  "nyra_niagara_set_module_parameter"),
])
def test_tool_schema_shape(tool_cls, expected_name):
    """Each tool exposes the canonical NyraTool surface."""
    t = tool_cls()
    assert t.name == expected_name
    assert isinstance(t.description, str) and t.description
    assert isinstance(t.parameters, dict)
    assert t.parameters["type"] == "object"
    assert "properties" in t.parameters
    assert "required" in t.parameters


def test_create_system_only_requires_asset_path():
    t = NiagaraCreateSystemTool()
    assert t.parameters["required"] == ["asset_path"]


def test_add_emitter_required_fields():
    t = NiagaraAddEmitterTool()
    assert set(t.parameters["required"]) == {
        "system_path", "template_path", "handle_name",
    }
    # T-08-04: sim_target enum is part of the schema (default cpu).
    sim_target = t.parameters["properties"]["sim_target"]
    assert sim_target["enum"] == ["cpu", "gpu"]
    assert sim_target["default"] == "cpu"


def test_set_module_parameter_required_fields():
    t = NiagaraSetModuleParameterTool()
    assert set(t.parameters["required"]) == {
        "system_path", "emitter_handle", "parameter_name", "value_kind",
    }
    assert t.parameters["properties"]["value_kind"]["enum"] == ["scalar", "vector"]


# ---------------------------------------------------------------------------
# HAS_UNREAL=False branch — every tool returns a clean err envelope rather
# than crashing with NameError / AttributeError.
# ---------------------------------------------------------------------------


def test_create_returns_err_when_unreal_unavailable():
    with patch.object(niagara_tools, "HAS_UNREAL", False):
        result = NiagaraCreateSystemTool().execute({"asset_path": "/Game/VFX/NS_X"})
        assert isinstance(result, NyraToolResult)
        assert result.error is not None
        # BL-01: err round-trips as JSON-RPC -32000.
        d = result.to_dict()
        assert d["error"]["code"] == -32000


def test_add_emitter_returns_err_when_unreal_unavailable():
    with patch.object(niagara_tools, "HAS_UNREAL", False):
        result = NiagaraAddEmitterTool().execute({
            "system_path":   "/Game/VFX/NS_X",
            "template_path": "/Niagara/Templates/Sprite/SpriteBurst",
            "handle_name":   "Burst1",
        })
        assert result.error is not None


def test_set_module_parameter_returns_err_when_unreal_unavailable():
    with patch.object(niagara_tools, "HAS_UNREAL", False):
        result = NiagaraSetModuleParameterTool().execute({
            "system_path":    "/Game/VFX/NS_X",
            "emitter_handle": "Burst1",
            "parameter_name": "SpawnRate",
            "value_kind":     "scalar",
            "scalar_value":   50.0,
        })
        assert result.error is not None


# ---------------------------------------------------------------------------
# T-08-01 graceful degradation: factory / system class / helper missing.
# ---------------------------------------------------------------------------


def test_create_returns_not_supported_when_factory_missing():
    fake = _build_fake_unreal(system_class=_FakeNiagaraSystem, factory=None)
    with _patch_unreal(fake):
        result = NiagaraCreateSystemTool().execute({"asset_path": "/Game/VFX/NS_X"})
        assert result.error is not None
        assert "not_supported_on_this_ue_version" in result.error


def test_create_returns_not_supported_when_system_class_missing():
    """Factory present but NiagaraSystem class absent — also degrades cleanly."""
    fake = _build_fake_unreal(system_class=None, factory=MagicMock())
    with _patch_unreal(fake):
        result = NiagaraCreateSystemTool().execute({"asset_path": "/Game/VFX/NS_X"})
        assert result.error is not None
        assert "not_supported_on_this_ue_version" in result.error


def test_add_emitter_returns_not_supported_when_helper_missing():
    fake = _build_fake_unreal(
        system_class=_FakeNiagaraSystem,
        factory=MagicMock(),
        helper=None,                               # NyraNiagaraHelper absent
        loaded_asset=_FakeNiagaraSystem("/Game/VFX/NS_X"),
    )
    with _patch_unreal(fake):
        result = NiagaraAddEmitterTool().execute({
            "system_path":   "/Game/VFX/NS_X",
            "template_path": "/Niagara/Templates/Sprite/SpriteBurst",
            "handle_name":   "Burst1",
        })
        assert result.error is not None
        assert "not_supported_on_this_ue_version" in result.error


def test_set_module_parameter_returns_not_supported_when_helper_missing():
    fake = _build_fake_unreal(
        system_class=_FakeNiagaraSystem,
        factory=MagicMock(),
        helper=None,
        loaded_asset=_FakeNiagaraSystem("/Game/VFX/NS_X"),
    )
    with _patch_unreal(fake):
        result = NiagaraSetModuleParameterTool().execute({
            "system_path":    "/Game/VFX/NS_X",
            "emitter_handle": "Burst1",
            "parameter_name": "SpawnRate",
            "value_kind":     "scalar",
            "scalar_value":   50.0,
        })
        assert result.error is not None
        assert "not_supported_on_this_ue_version" in result.error


# ---------------------------------------------------------------------------
# Parameter validation.
# ---------------------------------------------------------------------------


def test_create_rejects_malformed_asset_path():
    """asset_path without '/' is rejected with a clean envelope."""
    fake = _build_fake_unreal(
        system_class=_FakeNiagaraSystem,
        factory=MagicMock(),
    )
    with _patch_unreal(fake):
        result = NiagaraCreateSystemTool().execute({"asset_path": "no_slashes"})
        assert result.error is not None
        assert "/Game" in result.error or "asset_path" in result.error


def test_add_emitter_rejects_invalid_sim_target():
    fake = _build_fake_unreal(
        system_class=_FakeNiagaraSystem,
        factory=MagicMock(),
        helper=MagicMock(name="Helper"),
        loaded_asset=_FakeNiagaraSystem("/Game/VFX/NS_X"),
    )
    with _patch_unreal(fake):
        result = NiagaraAddEmitterTool().execute({
            "system_path":   "/Game/VFX/NS_X",
            "template_path": "/Niagara/Templates/Sprite/SpriteBurst",
            "handle_name":   "Burst1",
            "sim_target":    "metal",
        })
        assert result.error is not None
        assert "sim_target" in result.error


def test_set_module_parameter_rejects_invalid_value_kind():
    fake = _build_fake_unreal(
        system_class=_FakeNiagaraSystem,
        factory=MagicMock(),
        helper=MagicMock(),
        loaded_asset=_FakeNiagaraSystem("/Game/VFX/NS_X"),
    )
    with _patch_unreal(fake):
        result = NiagaraSetModuleParameterTool().execute({
            "system_path":    "/Game/VFX/NS_X",
            "emitter_handle": "Burst1",
            "parameter_name": "SpawnRate",
            "value_kind":     "matrix",
        })
        assert result.error is not None
        assert "value_kind" in result.error


def test_set_module_parameter_requires_scalar_value_for_scalar_kind():
    fake = _build_fake_unreal(
        system_class=_FakeNiagaraSystem,
        factory=MagicMock(),
        helper=MagicMock(),
        loaded_asset=_FakeNiagaraSystem("/Game/VFX/NS_X"),
    )
    with _patch_unreal(fake):
        result = NiagaraSetModuleParameterTool().execute({
            "system_path":    "/Game/VFX/NS_X",
            "emitter_handle": "Burst1",
            "parameter_name": "SpawnRate",
            "value_kind":     "scalar",
            # scalar_value missing on purpose
        })
        assert result.error is not None
        assert "scalar_value" in result.error


def test_set_module_parameter_requires_vector_value_for_vector_kind():
    fake = _build_fake_unreal(
        system_class=_FakeNiagaraSystem,
        factory=MagicMock(),
        helper=MagicMock(),
        loaded_asset=_FakeNiagaraSystem("/Game/VFX/NS_X"),
    )
    with _patch_unreal(fake):
        result = NiagaraSetModuleParameterTool().execute({
            "system_path":    "/Game/VFX/NS_X",
            "emitter_handle": "Burst1",
            "parameter_name": "Velocity",
            "value_kind":     "vector",
            # vector_value missing on purpose
        })
        assert result.error is not None
        assert "vector_value" in result.error


# ---------------------------------------------------------------------------
# Symbol resolvers — the three `_resolve_*` helpers tolerate missing symbols.
# ---------------------------------------------------------------------------


def test_resolve_factory_returns_none_when_no_unreal():
    with patch.object(niagara_tools, "HAS_UNREAL", False):
        assert _resolve_factory() is None


def test_resolve_system_class_returns_none_when_no_unreal():
    with patch.object(niagara_tools, "HAS_UNREAL", False):
        assert _resolve_system_class() is None


def test_resolve_helper_returns_none_when_no_unreal():
    with patch.object(niagara_tools, "HAS_UNREAL", False):
        assert _resolve_helper() is None


def test_resolve_factory_finds_symbol():
    fake_factory_cls = MagicMock(name="NiagaraSystemFactoryNew")
    fake = MagicMock()
    fake.NiagaraSystemFactoryNew = fake_factory_cls
    with _patch_unreal(fake):
        assert _resolve_factory() is fake_factory_cls


# ---------------------------------------------------------------------------
# BL-12 isinstance-check via _load_niagara_system.
# ---------------------------------------------------------------------------


def test_load_niagara_system_rejects_wrong_asset_class():
    """Passing a Material asset path returns None (BL-12)."""
    fake = _build_fake_unreal(
        system_class=_FakeNiagaraSystem,
        factory=MagicMock(),
        loaded_asset=_FakeMaterial(),  # NOT a NiagaraSystem
    )
    with _patch_unreal(fake):
        assert _load_niagara_system("/Game/Materials/M_Hero") is None


def test_load_niagara_system_returns_asset_when_correct_class():
    correct = _FakeNiagaraSystem("/Game/VFX/NS_X")
    fake = _build_fake_unreal(
        system_class=_FakeNiagaraSystem,
        factory=MagicMock(),
        loaded_asset=correct,
    )
    with _patch_unreal(fake):
        assert _load_niagara_system("/Game/VFX/NS_X") is correct


def test_set_module_parameter_rejects_wrong_asset_class():
    """End-to-end BL-12: pointing the tool at a Material path returns err."""
    fake = _build_fake_unreal(
        system_class=_FakeNiagaraSystem,
        factory=MagicMock(),
        helper=MagicMock(),
        loaded_asset=_FakeMaterial(),  # wrong class
    )
    with _patch_unreal(fake):
        result = NiagaraSetModuleParameterTool().execute({
            "system_path":    "/Game/Materials/M_Hero",
            "emitter_handle": "Burst1",
            "parameter_name": "SpawnRate",
            "value_kind":     "scalar",
            "scalar_value":   50.0,
        })
        assert result.error is not None
        assert "not found" in result.error or "wrong asset class" in result.error


# ---------------------------------------------------------------------------
# Happy path: create, add emitter (CPU + GPU), set scalar param + readback.
# ---------------------------------------------------------------------------


def test_create_system_happy_path():
    fake = _build_fake_unreal(
        system_class=_FakeNiagaraSystem,
        factory=MagicMock(name="FactoryCtor"),
        # The post-condition re-loads the asset; return a real instance.
        loaded_asset=_FakeNiagaraSystem("/Game/VFX/NS_X"),
    )
    with _patch_unreal(fake):
        result = NiagaraCreateSystemTool().execute({"asset_path": "/Game/VFX/NS_X"})
        assert result.error is None, result.error
        assert result.data["asset_path"] == "/Game/VFX/NS_X"


def test_add_emitter_cpu_path():
    """T-08-04 — sim_target='cpu' returns ok with the handle echoed back."""
    helper = MagicMock(name="NyraNiagaraHelper")
    helper.add_emitter_from_template.return_value = "SpriteBurstCPU"
    fake = _build_fake_unreal(
        system_class=_FakeNiagaraSystem,
        factory=MagicMock(),
        helper=helper,
        loaded_asset=_FakeNiagaraSystem("/Game/VFX/NS_X"),
    )
    with _patch_unreal(fake):
        result = NiagaraAddEmitterTool().execute({
            "system_path":   "/Game/VFX/NS_X",
            "template_path": "/Niagara/Templates/Sprite/SpriteBurst",
            "sim_target":    "cpu",
            "handle_name":   "SpriteBurstCPU",
        })
        assert result.error is None, result.error
        assert result.data["sim_target"] == "cpu"
        assert result.data["handle_name"] == "SpriteBurstCPU"
        helper.add_emitter_from_template.assert_called_once()


def test_add_emitter_gpu_path():
    """T-08-04 — sim_target='gpu' must succeed on the same code path."""
    helper = MagicMock(name="NyraNiagaraHelper")
    helper.add_emitter_from_template.return_value = "SpriteBurstGPU"
    fake = _build_fake_unreal(
        system_class=_FakeNiagaraSystem,
        factory=MagicMock(),
        helper=helper,
        loaded_asset=_FakeNiagaraSystem("/Game/VFX/NS_X"),
    )
    with _patch_unreal(fake):
        result = NiagaraAddEmitterTool().execute({
            "system_path":   "/Game/VFX/NS_X",
            "template_path": "/Niagara/Templates/Sprite/SpriteBurst",
            "sim_target":    "gpu",
            "handle_name":   "SpriteBurstGPU",
        })
        assert result.error is None, result.error
        assert result.data["sim_target"] == "gpu"
        assert result.data["handle_name"] == "SpriteBurstGPU"


def test_add_emitter_returns_err_when_helper_returns_empty():
    """If the C++ helper signals failure (empty string), surface as err."""
    helper = MagicMock()
    helper.add_emitter_from_template.return_value = ""
    fake = _build_fake_unreal(
        system_class=_FakeNiagaraSystem,
        factory=MagicMock(),
        helper=helper,
        loaded_asset=_FakeNiagaraSystem("/Game/VFX/NS_X"),
    )
    with _patch_unreal(fake):
        result = NiagaraAddEmitterTool().execute({
            "system_path":   "/Game/VFX/NS_X",
            "template_path": "/Niagara/Templates/Sprite/SpriteBurst",
            "sim_target":    "cpu",
            "handle_name":   "Burst1",
        })
        assert result.error is not None
        assert "empty handle" in result.error


def test_set_scalar_parameter_in_tolerance_succeeds():
    """BL-06 readback within 1e-4 of requested value -> ok."""
    helper = MagicMock(name="NyraNiagaraHelper")
    helper.set_scalar_module_parameter.return_value = True
    helper.get_scalar_module_parameter.return_value = 50.0  # exact match
    fake = _build_fake_unreal(
        system_class=_FakeNiagaraSystem,
        factory=MagicMock(),
        helper=helper,
        loaded_asset=_FakeNiagaraSystem("/Game/VFX/NS_X"),
    )
    with _patch_unreal(fake):
        result = NiagaraSetModuleParameterTool().execute({
            "system_path":    "/Game/VFX/NS_X",
            "emitter_handle": "Burst1",
            "parameter_name": "SpawnRate",
            "value_kind":     "scalar",
            "scalar_value":   50.0,
        })
        assert result.error is None, result.error
        assert result.data["parameter"] == "SpawnRate"


def test_set_scalar_parameter_out_of_tolerance_fails_post_condition():
    """BL-06 readback drifts > 1e-4 -> post_condition_failed."""
    helper = MagicMock()
    helper.set_scalar_module_parameter.return_value = True
    helper.get_scalar_module_parameter.return_value = 49.5  # drifted 0.5
    fake = _build_fake_unreal(
        system_class=_FakeNiagaraSystem,
        factory=MagicMock(),
        helper=helper,
        loaded_asset=_FakeNiagaraSystem("/Game/VFX/NS_X"),
    )
    with _patch_unreal(fake):
        result = NiagaraSetModuleParameterTool().execute({
            "system_path":    "/Game/VFX/NS_X",
            "emitter_handle": "Burst1",
            "parameter_name": "SpawnRate",
            "value_kind":     "scalar",
            "scalar_value":   50.0,
        })
        assert result.error is not None
        assert "post_condition_failed" in result.error


def test_set_scalar_parameter_helper_returns_false():
    """If the helper's set returns false, surface as err without readback."""
    helper = MagicMock()
    helper.set_scalar_module_parameter.return_value = False
    fake = _build_fake_unreal(
        system_class=_FakeNiagaraSystem,
        factory=MagicMock(),
        helper=helper,
        loaded_asset=_FakeNiagaraSystem("/Game/VFX/NS_X"),
    )
    with _patch_unreal(fake):
        result = NiagaraSetModuleParameterTool().execute({
            "system_path":    "/Game/VFX/NS_X",
            "emitter_handle": "Burst1",
            "parameter_name": "SpawnRate",
            "value_kind":     "scalar",
            "scalar_value":   50.0,
        })
        assert result.error is not None
        assert "returned false" in result.error
        helper.get_scalar_module_parameter.assert_not_called()


# ---------------------------------------------------------------------------
# BL-05 idempotency
# ---------------------------------------------------------------------------


def test_create_system_is_idempotent_on_repeat():
    """Second identical call returns deduped=True without invoking the factory."""
    factory_ctor = MagicMock(name="FactoryCtor")
    fake = _build_fake_unreal(
        system_class=_FakeNiagaraSystem,
        factory=factory_ctor,
        loaded_asset=_FakeNiagaraSystem("/Game/VFX/NS_Idem"),
    )
    with _patch_unreal(fake):
        params = {"asset_path": "/Game/VFX/NS_Idem"}
        r1 = NiagaraCreateSystemTool().execute(params)
        r2 = NiagaraCreateSystemTool().execute(params)
        assert r1.error is None and r2.error is None
        assert r2.data.get("deduped") is True
        # Factory only constructed once.
        assert factory_ctor.call_count == 1


def test_add_emitter_is_idempotent_on_repeat():
    helper = MagicMock()
    helper.add_emitter_from_template.return_value = "Burst1"
    fake = _build_fake_unreal(
        system_class=_FakeNiagaraSystem,
        factory=MagicMock(),
        helper=helper,
        loaded_asset=_FakeNiagaraSystem("/Game/VFX/NS_Idem"),
    )
    with _patch_unreal(fake):
        params = {
            "system_path":   "/Game/VFX/NS_Idem",
            "template_path": "/Niagara/Templates/Sprite/SpriteBurst",
            "sim_target":    "cpu",
            "handle_name":   "Burst1",
        }
        r1 = NiagaraAddEmitterTool().execute(params)
        r2 = NiagaraAddEmitterTool().execute(params)
        assert r1.error is None and r2.error is None
        assert r2.data.get("deduped") is True
        # Helper.add_emitter_from_template only called once across both runs.
        assert helper.add_emitter_from_template.call_count == 1
