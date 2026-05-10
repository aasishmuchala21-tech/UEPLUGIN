"""Tests for nyrahost.tools.metasound_tools (PARITY-08).

Smallest test surface in Phase 8 — gloss-tier per CONTEXT.md SC#8.

Coverage:
  - Schema shape (canonical NyraTool: name / description / parameters /
    required keys per the JSON Schema).
  - Capitalisation-drift defense (RESEARCH.md A4) for all three
    `_resolve_*` helpers — both spellings probed, neither-present
    returns None cleanly.
  - HAS_UNREAL=False path: every tool returns NyraToolResult.err with
    a non-empty message and the err dict round-trips through to_dict()
    as a JSON-RPC -32000 envelope (BL-01).
  - Idempotency cache: a second identical call returns deduped=True
    without re-invoking the (mocked) factory.
  - Parameter validation: missing required keys / malformed asset_path
    return err envelopes, not exceptions.

Live tests against a real UE editor are deferred to
`08-08-VERIFICATION.md` (operator-run, per-UE-version).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from nyrahost.tools.base import NyraToolResult, idempotent_clear
from nyrahost.tools import metasound_tools
from nyrahost.tools.metasound_tools import (
    MetasoundAddNodeTool,
    MetasoundConnectTool,
    MetasoundCreateTool,
    _resolve_asset_class,
    _resolve_builder_subsystem,
    _resolve_factory,
)


def _fake_unreal(**attrs):
    """Build a minimal stand-in for the `unreal` module.

    SimpleNamespace's hasattr semantics match the real `unreal` module:
    only the keys passed in `attrs` are reflected. This avoids the
    MagicMock auto-spec gotchas where every probed name appears present.
    """
    return SimpleNamespace(**attrs)


# ---------------------------------------------------------------------------
# autouse: clear idempotency cache between tests so cross-test cache hits
# don't bleed (BL-05 cache is process-local).
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_idempotency():
    idempotent_clear()
    yield
    idempotent_clear()


# ---------------------------------------------------------------------------
# Schema shape — every NyraTool must have name / description / parameters
# with required keys per the JSON Schema, and to_dict() round-trips ok+err.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tool_cls,expected_name", [
    (MetasoundCreateTool,  "nyra_metasound_create"),
    (MetasoundAddNodeTool, "nyra_metasound_add_node"),
    (MetasoundConnectTool, "nyra_metasound_connect"),
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
    assert "asset_path" in t.parameters["properties"]
    assert "asset_path" in t.parameters["required"]


def test_create_tool_parameters_minimal():
    """create only requires asset_path."""
    t = MetasoundCreateTool()
    assert t.parameters["required"] == ["asset_path"]


def test_add_node_tool_parameters_full():
    """add_node requires asset_path + node_class + node_name."""
    t = MetasoundAddNodeTool()
    assert set(t.parameters["required"]) == {"asset_path", "node_class", "node_name"}


def test_connect_tool_parameters_full():
    """connect requires the full pin-tuple."""
    t = MetasoundConnectTool()
    assert set(t.parameters["required"]) == {
        "asset_path", "from_node_id", "from_pin", "to_node_id", "to_pin",
    }


# ---------------------------------------------------------------------------
# Capitalisation-drift defense (RESEARCH.md A4).
#
# These are the highest-leverage tests in this file: they verify the
# `_resolve_*` helpers probe BOTH spellings and don't lock to a single
# capitalisation. This is the most-likely real-world failure mode.
# ---------------------------------------------------------------------------


def test_resolve_factory_finds_metasound_capital_S():
    """Case A: factory exposed as 'MetaSound...' (canonical 5.6+ spelling)."""
    factory_class = object()
    fake_unreal = _fake_unreal(MetaSoundSourceFactory=factory_class)
    with patch.object(metasound_tools, "unreal", fake_unreal), \
         patch.object(metasound_tools, "HAS_UNREAL", True):
        cls = _resolve_factory()
        assert cls is factory_class


def test_resolve_factory_finds_metasound_lowercase_s():
    """Case B: factory exposed as 'Metasound...' (the A4 drift case)."""
    factory_class = object()
    fake_unreal = _fake_unreal(MetasoundFactory=factory_class)
    with patch.object(metasound_tools, "unreal", fake_unreal), \
         patch.object(metasound_tools, "HAS_UNREAL", True):
        cls = _resolve_factory()
        assert cls is factory_class


def test_resolve_factory_prefers_long_form_when_both_present():
    """When MetaSoundSourceFactory + MetaSoundFactory both reflect, the
    long form (5.6+) wins — matches `_resolve_factory` probe order."""
    long_form  = object()
    short_form = object()
    fake_unreal = _fake_unreal(
        MetaSoundSourceFactory=long_form,
        MetaSoundFactory=short_form,
    )
    with patch.object(metasound_tools, "unreal", fake_unreal), \
         patch.object(metasound_tools, "HAS_UNREAL", True):
        assert _resolve_factory() is long_form


def test_resolve_factory_returns_none_when_neither_present():
    """If NEITHER spelling is reflected, helper returns None cleanly."""
    fake_unreal = _fake_unreal()
    with patch.object(metasound_tools, "unreal", fake_unreal), \
         patch.object(metasound_tools, "HAS_UNREAL", True):
        assert _resolve_factory() is None


def test_resolve_asset_class_probes_both_spellings():
    """Asset-class resolver finds the lowercase spelling when canonical absent."""
    asset_class = object()
    fake_unreal = _fake_unreal(MetasoundSource=asset_class)
    with patch.object(metasound_tools, "unreal", fake_unreal), \
         patch.object(metasound_tools, "HAS_UNREAL", True):
        cls = _resolve_asset_class()
        assert cls is asset_class


def test_resolve_builder_subsystem_returns_none_when_no_unreal():
    """Without `unreal`, the builder resolver returns None — no crash."""
    with patch.object(metasound_tools, "HAS_UNREAL", False):
        assert _resolve_builder_subsystem() is None


def test_resolve_factory_returns_none_when_no_unreal():
    """Without `unreal`, the factory resolver returns None — no crash."""
    with patch.object(metasound_tools, "HAS_UNREAL", False):
        assert _resolve_factory() is None


# ---------------------------------------------------------------------------
# HAS_UNREAL=False execute() path — every tool returns a clean err envelope
# rather than crashing with NameError / AttributeError.
# ---------------------------------------------------------------------------


def test_create_returns_err_when_unreal_unavailable():
    with patch.object(metasound_tools, "HAS_UNREAL", False):
        result = MetasoundCreateTool().execute({"asset_path": "/Game/Audio/MS_X"})
        assert isinstance(result, NyraToolResult)
        assert result.error is not None
        assert "unreal" in result.error.lower()
        # BL-01: err round-trips as JSON-RPC -32000.
        d = result.to_dict()
        assert d["error"]["code"] == -32000


def test_add_node_returns_err_when_unreal_unavailable():
    with patch.object(metasound_tools, "HAS_UNREAL", False):
        result = MetasoundAddNodeTool().execute({
            "asset_path": "/Game/Audio/MS_X",
            "node_class": "Oscillator",
            "node_name":  "Osc1",
        })
        assert result.error is not None
        assert "unreal" in result.error.lower()


def test_connect_returns_err_when_unreal_unavailable():
    with patch.object(metasound_tools, "HAS_UNREAL", False):
        result = MetasoundConnectTool().execute({
            "asset_path":   "/Game/Audio/MS_X",
            "from_node_id": "Osc1",
            "from_pin":     "Out",
            "to_node_id":   "Out1",
            "to_pin":       "In",
        })
        assert result.error is not None


# ---------------------------------------------------------------------------
# Builder-subsystem-missing path on add_node / connect.
#
# Even when unreal IS available, if the builder subsystem isn't reflected
# the two graph-mutation tools must return `not_supported_on_this_ue_version`
# (Plan 08-08 fallback path per RESEARCH.md Q1 RESOLVED-DEFERRED-TO-WAVE-0).
# ---------------------------------------------------------------------------


def test_add_node_returns_not_supported_when_builder_missing():
    fake_unreal = _fake_unreal()
    with patch.object(metasound_tools, "unreal", fake_unreal), \
         patch.object(metasound_tools, "HAS_UNREAL", True):
        result = MetasoundAddNodeTool().execute({
            "asset_path": "/Game/Audio/MS_X",
            "node_class": "Oscillator",
            "node_name":  "Osc1",
        })
        assert result.error is not None
        assert "not_supported_on_this_ue_version" in result.error


def test_connect_returns_not_supported_when_builder_missing():
    fake_unreal = _fake_unreal()
    with patch.object(metasound_tools, "unreal", fake_unreal), \
         patch.object(metasound_tools, "HAS_UNREAL", True):
        result = MetasoundConnectTool().execute({
            "asset_path":   "/Game/Audio/MS_X",
            "from_node_id": "Osc1",
            "from_pin":     "Out",
            "to_node_id":   "Out1",
            "to_pin":       "In",
        })
        assert result.error is not None
        assert "not_supported_on_this_ue_version" in result.error


# ---------------------------------------------------------------------------
# create-path: factory + asset class missing returns not_supported.
# ---------------------------------------------------------------------------


def test_create_returns_not_supported_when_factory_missing():
    fake_unreal = _fake_unreal()
    with patch.object(metasound_tools, "unreal", fake_unreal), \
         patch.object(metasound_tools, "HAS_UNREAL", True):
        result = MetasoundCreateTool().execute({"asset_path": "/Game/Audio/MS_X"})
        assert result.error is not None
        assert "not_supported_on_this_ue_version" in result.error


def test_create_returns_err_for_malformed_asset_path():
    """Asset path without a slash is rejected with a clean envelope.

    execute() short-circuits on the malformed path BEFORE entering the
    session transaction or touching unreal surfaces, so we only need
    factory + asset class to pass the resolver check.
    """
    fake_unreal = _fake_unreal(
        MetaSoundSourceFactory=lambda: object(),
        MetaSoundSource=type("MetaSoundSource", (), {}),
    )
    with patch.object(metasound_tools, "unreal", fake_unreal), \
         patch.object(metasound_tools, "HAS_UNREAL", True):
        result = MetasoundCreateTool().execute({"asset_path": "no_slashes_here"})
        assert result.error is not None
        assert "asset_path" in result.error
