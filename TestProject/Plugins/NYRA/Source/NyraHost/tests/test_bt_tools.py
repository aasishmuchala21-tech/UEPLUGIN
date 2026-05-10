"""tests/test_bt_tools.py — unit tests for the PARITY-03 BT mutator tools.

Module-level skip when the live `unreal` module is not loaded keeps the
suite green on the dev box; the parametrised live-UE branches will run
in the in-editor pytest harness during Wave 0 verification.

The non-live tests below exercise:
  - schema validation (parameters dict shape)
  - required-field rejection
  - parameter type coercion / sentinel error envelopes
  - NyraToolResult contract (BL-01 — never raw dicts)
  - the "unreal module unavailable" fallback path

These tests run without the editor because every BT tool is structured
so that pre-flight validation happens BEFORE any `unreal.*` access.
"""
from __future__ import annotations

import sys

import pytest

from nyrahost.tools.base import NyraToolResult
from nyrahost.tools.bt_tools import (
    BTAddCompositeTool,
    BTAddDecoratorTool,
    BTAddTaskTool,
    BTCreateTool,
    BTSetBlackboardKeyTool,
)


# Module-level skip for the parametrised live-UE branches added inline
# to specific tests. Class-level tests below remain runnable without UE.
pytestmark_live_ue = pytest.mark.skipif(
    "unreal" not in sys.modules,
    reason="requires live UE editor (Wave 0 in-editor pytest harness)",
)


# ---------------------------------------------------------------------------
# BTCreateTool
# ---------------------------------------------------------------------------


class TestBTCreateTool:
    """Schema + validation tests for nyra_bt_create."""

    def setup_method(self):
        from nyrahost.tools.base import idempotent_clear

        idempotent_clear()
        self.tool = BTCreateTool()

    def test_name_and_description(self):
        assert self.tool.name == "nyra_bt_create"
        assert "UBehaviorTree" in self.tool.description

    def test_parameters_schema_shape(self):
        params = self.tool.parameters
        assert params["type"] == "object"
        assert "asset_path" in params["properties"]
        assert "blackboard" in params["properties"]
        assert params["required"] == ["asset_path"]

    def test_returns_nyratoolresult_not_raw_dict(self):
        # Missing required field → still returns NyraToolResult (BL-01).
        result = self.tool.execute({})
        assert isinstance(result, NyraToolResult)
        assert not result.is_ok

    def test_missing_asset_path_rejected(self):
        # No `unreal` module on dev box → the "unreal module not available"
        # error wins over the asset_path check, but either way we get
        # a NyraToolResult.err. This documents the dispatch order.
        result = self.tool.execute({})
        assert not result.is_ok
        assert result.error  # non-empty

    def test_invalid_asset_path_format_rejected(self):
        # Use a fake `unreal` module so the validation gate fires
        # rather than the "unreal not available" gate.
        import nyrahost.tools.bt_tools as bt_tools

        class _FakeFactory:
            pass

        class _FakeUnreal:
            BehaviorTreeFactory = _FakeFactory

        original = bt_tools.unreal
        bt_tools.unreal = _FakeUnreal  # type: ignore[assignment]
        try:
            result = self.tool.execute({"asset_path": "not-a-game-path"})
            assert not result.is_ok
            assert "/Game/" in (result.error or "")
        finally:
            bt_tools.unreal = original  # type: ignore[assignment]

    def test_unreal_module_unavailable_returns_err(self):
        import nyrahost.tools.bt_tools as bt_tools

        original = bt_tools.unreal
        bt_tools.unreal = None  # type: ignore[assignment]
        try:
            result = self.tool.execute({"asset_path": "/Game/AI/BT_X"})
            assert not result.is_ok
            assert "unreal module not available" in (result.error or "")
        finally:
            bt_tools.unreal = original  # type: ignore[assignment]

    def test_missing_behaviortreefactory_returns_unsupported(self):
        import nyrahost.tools.bt_tools as bt_tools

        class _FakeUnrealNoFactory:
            pass  # deliberately missing BehaviorTreeFactory

        original = bt_tools.unreal
        bt_tools.unreal = _FakeUnrealNoFactory  # type: ignore[assignment]
        try:
            result = self.tool.execute({"asset_path": "/Game/AI/BT_X"})
            assert not result.is_ok
            assert "not_supported_on_this_ue_version" in (result.error or "")
        finally:
            bt_tools.unreal = original  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# BTAddCompositeTool
# ---------------------------------------------------------------------------


class TestBTAddCompositeTool:
    def setup_method(self):
        from nyrahost.tools.base import idempotent_clear

        idempotent_clear()
        self.tool = BTAddCompositeTool()

    def test_name_and_schema(self):
        assert self.tool.name == "nyra_bt_add_composite"
        params = self.tool.parameters
        assert params["required"] == ["bt_path", "parent_node", "composite_class"]
        composite_enum = params["properties"]["composite_class"]["enum"]
        assert set(composite_enum) == {"Selector", "Sequence", "SimpleParallel"}

    def test_returns_nyratoolresult(self):
        result = self.tool.execute({})
        assert isinstance(result, NyraToolResult)
        assert not result.is_ok

    def test_invalid_composite_class_rejected(self):
        import nyrahost.tools.bt_tools as bt_tools

        class _FakeUnrealWithHelper:
            class NyraBTHelper:
                pass

        original = bt_tools.unreal
        bt_tools.unreal = _FakeUnrealWithHelper  # type: ignore[assignment]
        try:
            result = self.tool.execute(
                {
                    "bt_path": "/Game/AI/BT_X",
                    "parent_node": "Root",
                    "composite_class": "NotARealComposite",
                }
            )
            assert not result.is_ok
            assert "Selector/Sequence/SimpleParallel" in (result.error or "")
        finally:
            bt_tools.unreal = original  # type: ignore[assignment]

    def test_missing_helper_uclass_returns_unsupported(self):
        import nyrahost.tools.bt_tools as bt_tools

        class _FakeUnrealNoHelper:
            BehaviorTreeFactory = type("F", (), {})

        original = bt_tools.unreal
        bt_tools.unreal = _FakeUnrealNoHelper  # type: ignore[assignment]
        try:
            result = self.tool.execute(
                {
                    "bt_path": "/Game/AI/BT_X",
                    "parent_node": "Root",
                    "composite_class": "Sequence",
                }
            )
            assert not result.is_ok
            assert "NyraBTHelper" in (result.error or "")
        finally:
            bt_tools.unreal = original  # type: ignore[assignment]

    def test_position_type_coercion_rejects_garbage(self):
        import nyrahost.tools.bt_tools as bt_tools

        class _FakeUnrealWithHelper:
            class NyraBTHelper:
                pass

        original = bt_tools.unreal
        bt_tools.unreal = _FakeUnrealWithHelper  # type: ignore[assignment]
        try:
            result = self.tool.execute(
                {
                    "bt_path": "/Game/AI/BT_X",
                    "parent_node": "Root",
                    "composite_class": "Sequence",
                    "position": {"x": "not-a-number", "y": 0},
                }
            )
            assert not result.is_ok
            assert "position.x/y must be numbers" in (result.error or "")
        finally:
            bt_tools.unreal = original  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# BTAddTaskTool
# ---------------------------------------------------------------------------


class TestBTAddTaskTool:
    def setup_method(self):
        from nyrahost.tools.base import idempotent_clear

        idempotent_clear()
        self.tool = BTAddTaskTool()

    def test_name_and_schema(self):
        assert self.tool.name == "nyra_bt_add_task"
        params = self.tool.parameters
        assert params["required"] == ["bt_path", "parent_composite", "task_class"]
        assert "position" in params["properties"]

    def test_returns_nyratoolresult(self):
        result = self.tool.execute({})
        assert isinstance(result, NyraToolResult)
        assert not result.is_ok

    def test_required_fields_individually_rejected(self):
        import nyrahost.tools.bt_tools as bt_tools

        class _FakeUnrealWithHelper:
            class NyraBTHelper:
                pass

        original = bt_tools.unreal
        bt_tools.unreal = _FakeUnrealWithHelper  # type: ignore[assignment]
        try:
            # missing parent_composite
            r = self.tool.execute({"bt_path": "/Game/AI/BT_X", "task_class": "BTTask_MoveTo"})
            assert not r.is_ok
            assert "parent_composite" in (r.error or "")

            # missing task_class
            r = self.tool.execute(
                {"bt_path": "/Game/AI/BT_X", "parent_composite": "Sequence_0"}
            )
            assert not r.is_ok
            assert "task_class" in (r.error or "")
        finally:
            bt_tools.unreal = original  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# BTAddDecoratorTool
# ---------------------------------------------------------------------------


class TestBTAddDecoratorTool:
    def setup_method(self):
        from nyrahost.tools.base import idempotent_clear

        idempotent_clear()
        self.tool = BTAddDecoratorTool()

    def test_name_and_schema(self):
        assert self.tool.name == "nyra_bt_add_decorator"
        params = self.tool.parameters
        assert params["required"] == ["bt_path", "target_node", "decorator_class"]

    def test_returns_nyratoolresult(self):
        result = self.tool.execute({})
        assert isinstance(result, NyraToolResult)
        assert not result.is_ok

    def test_string_type_validation(self):
        import nyrahost.tools.bt_tools as bt_tools

        class _FakeUnrealWithHelper:
            class NyraBTHelper:
                pass

        original = bt_tools.unreal
        bt_tools.unreal = _FakeUnrealWithHelper  # type: ignore[assignment]
        try:
            result = self.tool.execute(
                {
                    "bt_path": "/Game/AI/BT_X",
                    "target_node": 12345,  # not a string
                    "decorator_class": "BTDecorator_Blackboard",
                }
            )
            assert not result.is_ok
            assert "target_node must be a string" in (result.error or "")
        finally:
            bt_tools.unreal = original  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# BTSetBlackboardKeyTool
# ---------------------------------------------------------------------------


class TestBTSetBlackboardKeyTool:
    def setup_method(self):
        from nyrahost.tools.base import idempotent_clear

        idempotent_clear()
        self.tool = BTSetBlackboardKeyTool()

    def test_name_and_schema(self):
        assert self.tool.name == "nyra_bt_set_blackboard_key"
        params = self.tool.parameters
        assert params["required"] == ["blackboard_path", "key_name", "key_type"]
        assert set(params["properties"]["key_type"]["enum"]) == {
            "Bool",
            "Int",
            "Float",
            "String",
            "Vector",
            "Object",
        }

    def test_returns_nyratoolresult(self):
        result = self.tool.execute({})
        assert isinstance(result, NyraToolResult)
        assert not result.is_ok

    def test_empty_key_name_rejected(self):
        import nyrahost.tools.bt_tools as bt_tools

        class _FakeUnrealWithHelper:
            class NyraBTHelper:
                pass

        original = bt_tools.unreal
        bt_tools.unreal = _FakeUnrealWithHelper  # type: ignore[assignment]
        try:
            result = self.tool.execute(
                {
                    "blackboard_path": "/Game/AI/BB_X",
                    "key_name": "",
                    "key_type": "Bool",
                }
            )
            assert not result.is_ok
            assert "key_name must be a non-empty string" in (result.error or "")
        finally:
            bt_tools.unreal = original  # type: ignore[assignment]

    def test_invalid_key_type_rejected(self):
        import nyrahost.tools.bt_tools as bt_tools

        class _FakeUnrealWithHelper:
            class NyraBTHelper:
                pass

        original = bt_tools.unreal
        bt_tools.unreal = _FakeUnrealWithHelper  # type: ignore[assignment]
        try:
            result = self.tool.execute(
                {
                    "blackboard_path": "/Game/AI/BB_X",
                    "key_name": "TargetActor",
                    "key_type": "NotARealType",
                }
            )
            assert not result.is_ok
            assert "key_type must be one of" in (result.error or "")
        finally:
            bt_tools.unreal = original  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Live UE editor branches (skipped on dev box; run in Wave 0 in-editor pytest)
# ---------------------------------------------------------------------------


@pytestmark_live_ue
class TestLiveUEPaths:
    """Smoke tests gated on a real `unreal` module being importable."""

    def test_create_then_add_composite_round_trip(self):
        """Pure live-UE happy path. Requires editor + Wave 0 helper UCLASS registered."""
        import unreal  # noqa: F401  — referenced for pytest skip decorator only.

        bt_path = "/Game/Tests/BT_NyraSmoke"
        create_result = BTCreateTool().execute({"asset_path": bt_path})
        assert create_result.is_ok, create_result.error
        comp_result = BTAddCompositeTool().execute(
            {
                "bt_path": bt_path,
                "parent_node": "Root",
                "composite_class": "Sequence",
            }
        )
        assert comp_result.is_ok, comp_result.error
        assert comp_result.data and comp_result.data.get("node_name")
