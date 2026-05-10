"""nyrahost.tools.bt_tools — Behavior Tree authoring mutators (PARITY-03).

Every tool here is a copy-rename of `actor_tools.ActorSpawnTool` per
LOCKED-03 + PATTERNS.md §"Per-Plan §PARITY-03": same five-step canonical
Phase 4 mutator shape (BL-04 session_transaction, BL-05 idempotent_lookup
/ idempotent_record, BL-06 verify_post_condition, BL-01 NyraToolResult
envelope).

UE Python entrypoints used:
    unreal.BehaviorTreeFactory                — asset creation
    unreal.AssetToolsHelpers.get_asset_tools  — generic asset wrapper
    unreal.EditorAssetLibrary                 — load / save / does_asset_exist
    unreal.NyraBTHelper                       — UCLASS bridge for graph
                                                node spawn (EdGraph node
                                                creation surface is NOT
                                                reflected directly to
                                                Python; the C++ helper
                                                is mandatory per
                                                RESEARCH.md A1).

The `unreal` module import is wrapped in try/except so this file
loads cleanly under pytest without an editor process. Per S5 defensive
coding, every `unreal.*` symbol access at execute-time is guarded with
`hasattr` and degrades to `not_supported_on_this_ue_version`-style
errors rather than silent no-ops.
"""
from __future__ import annotations

import structlog

from nyrahost.tools.base import (
    NyraTool,
    NyraToolResult,
    idempotent_lookup,
    idempotent_record,
    session_transaction,
    verify_post_condition,
)

try:  # pragma: no cover — UE editor-only import
    import unreal  # type: ignore
except ImportError:  # pytest path
    unreal = None  # type: ignore[assignment]


log = structlog.get_logger("nyrahost.tools.bt_tools")


__all__ = [
    "BTCreateTool",
    "BTAddCompositeTool",
    "BTAddTaskTool",
    "BTAddDecoratorTool",
    "BTSetBlackboardKeyTool",
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _require_unreal() -> "object | None":
    """Return the live `unreal` module or None.

    Centralises the "are we inside the editor" branch. Every tool's
    `execute()` calls this first and short-circuits with
    `not_supported_on_this_ue_version` if the module is missing — never
    silently no-ops (PATTERNS.md §S5).
    """
    return unreal


def _load_bt_asset(path: str):
    """Defensive UE 5.4–5.7 BT-asset lookup; mirrors actor_tools._load_actor."""
    if unreal is None:
        return None
    try:
        asset = unreal.EditorAssetLibrary.load_asset(path)
    except Exception as e:  # pragma: no cover — editor-only failure
        log.warning("bt_load_asset_failed", path=path, error=str(e))
        return None
    if asset is None:
        return None
    if not isinstance(asset, unreal.BehaviorTree):
        return None
    return asset


def _load_blackboard_asset(path: str):
    """Defensive Blackboard asset lookup."""
    if unreal is None:
        return None
    try:
        asset = unreal.EditorAssetLibrary.load_asset(path)
    except Exception as e:  # pragma: no cover
        log.warning("bb_load_asset_failed", path=path, error=str(e))
        return None
    if asset is None:
        return None
    if not isinstance(asset, unreal.BlackboardData):
        return None
    return asset


# ---------------------------------------------------------------------------
# nyra_bt_create
# ---------------------------------------------------------------------------


class BTCreateTool(NyraTool):
    name = "nyra_bt_create"
    description = (
        "Create a new UBehaviorTree asset at the given content path, "
        "optionally binding an existing BlackboardData asset."
    )
    parameters = {
        "type": "object",
        "properties": {
            "asset_path": {
                "type": "string",
                "description": "Content path (e.g. /Game/AI/BT_GuardPatrol).",
            },
            "blackboard": {
                "type": "string",
                "description": (
                    "Optional /Game/... path to an existing UBlackboardData "
                    "asset. Bound to the new BT's blackboard_asset field."
                ),
            },
        },
        "required": ["asset_path"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        # BL-05 — short-circuit duplicate calls.
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        ue = _require_unreal()
        if ue is None:
            return NyraToolResult.err(
                "unreal module not available; nyra_bt_create requires the UE editor"
            )
        if not hasattr(ue, "BehaviorTreeFactory"):
            return NyraToolResult.err(
                "unreal.BehaviorTreeFactory not reflected on this UE version "
                "(see Wave 0 symbol survey); not_supported_on_this_ue_version"
            )

        asset_path = params.get("asset_path")
        if not isinstance(asset_path, str) or not asset_path.startswith("/Game/"):
            return NyraToolResult.err(
                f"asset_path must be a /Game/... content path, got {asset_path!r}"
            )

        blackboard_path = params.get("blackboard")
        if blackboard_path is not None and not isinstance(blackboard_path, str):
            return NyraToolResult.err(
                f"blackboard must be a string content path or omitted, got {blackboard_path!r}"
            )

        with session_transaction(f"NYRA: {self.name}"):
            try:
                factory = ue.BehaviorTreeFactory()
                asset_tools = ue.AssetToolsHelpers.get_asset_tools()
                pkg_path, pkg_name = asset_path.rsplit("/", 1)
                bt = asset_tools.create_asset(
                    pkg_name, pkg_path, ue.BehaviorTree, factory
                )
                if bt is None:
                    return NyraToolResult.err(
                        f"create_asset returned None for {asset_path}"
                    )

                if blackboard_path:
                    bb = _load_blackboard_asset(blackboard_path)
                    if bb is None:
                        return NyraToolResult.err(
                            f"BlackboardData not found at {blackboard_path}"
                        )
                    # property name differs across UE versions — try both
                    try:
                        bt.set_editor_property("blackboard_asset", bb)
                    except Exception:  # pragma: no cover
                        bt.blackboard_asset = bb  # type: ignore[attr-defined]

                ue.EditorAssetLibrary.save_asset(asset_path)
            except Exception as e:
                log.error("bt_create_failed", error=str(e), path=asset_path)
                return NyraToolResult.err(f"failed to create BT: {e}")

            # BL-06 — re-load and confirm class.
            post_err = verify_post_condition(
                f"{self.name}({asset_path})",
                lambda: _load_bt_asset(asset_path) is not None,
            )
            if post_err:
                return NyraToolResult.err(post_err)

        log.info("bt_created", path=asset_path, blackboard=blackboard_path)
        result = {
            "asset_path": asset_path,
            "blackboard": blackboard_path,
        }
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)


# ---------------------------------------------------------------------------
# nyra_bt_add_composite
# ---------------------------------------------------------------------------


class BTAddCompositeTool(NyraTool):
    name = "nyra_bt_add_composite"
    description = (
        "Add a composite node (Selector / Sequence / SimpleParallel) under "
        "the BT root or a named parent composite."
    )
    parameters = {
        "type": "object",
        "properties": {
            "bt_path": {"type": "string", "description": "/Game/... BT asset path"},
            "parent_node": {
                "type": "string",
                "description": "'Root' or the FName of an existing composite node",
            },
            "composite_class": {
                "type": "string",
                "enum": ["Selector", "Sequence", "SimpleParallel"],
            },
            "node_name": {
                "type": "string",
                "description": "Optional FName for the new node",
            },
            "position": {
                "type": "object",
                "properties": {
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                },
                "default": {"x": 0, "y": 0},
            },
        },
        "required": ["bt_path", "parent_node", "composite_class"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        ue = _require_unreal()
        if ue is None:
            return NyraToolResult.err(
                "unreal module not available; nyra_bt_add_composite requires the UE editor"
            )
        if not hasattr(ue, "NyraBTHelper"):
            return NyraToolResult.err(
                "unreal.NyraBTHelper not registered (NyraEditor module not loaded?); "
                "not_supported_on_this_ue_version"
            )

        bt_path = params.get("bt_path")
        parent_node = params.get("parent_node")
        composite_class = params.get("composite_class")
        if not isinstance(bt_path, str):
            return NyraToolResult.err(f"bt_path must be a string, got {bt_path!r}")
        if not isinstance(parent_node, str):
            return NyraToolResult.err(
                f"parent_node must be a string, got {parent_node!r}"
            )
        if composite_class not in ("Selector", "Sequence", "SimpleParallel"):
            return NyraToolResult.err(
                f"composite_class must be one of Selector/Sequence/SimpleParallel, "
                f"got {composite_class!r}"
            )

        pos = params.get("position") or {"x": 0, "y": 0}
        try:
            pos_x = float(pos.get("x", 0))
            pos_y = float(pos.get("y", 0))
        except (TypeError, ValueError) as e:
            return NyraToolResult.err(f"position.x/y must be numbers: {e}")

        created_name = ""
        with session_transaction(f"NYRA: {self.name}"):
            try:
                bt = _load_bt_asset(bt_path)
                if bt is None:
                    return NyraToolResult.err(f"BT not found at {bt_path}")
                created_name = ue.NyraBTHelper.add_composite_node(
                    bt,
                    f"BTComposite_{composite_class}",
                    parent_node,
                    ue.Vector2D(pos_x, pos_y),
                )
                if not created_name:
                    return NyraToolResult.err(
                        "AddCompositeNode helper returned empty name "
                        "(parent_node not found, or class mismatch)"
                    )
                ue.EditorAssetLibrary.save_asset(bt_path)
            except Exception as e:
                log.error("bt_add_composite_failed", error=str(e), bt=bt_path)
                return NyraToolResult.err(f"failed to add composite: {e}")

            post_err = verify_post_condition(
                f"{self.name}({bt_path}:{created_name})",
                lambda: _load_bt_asset(bt_path) is not None,
            )
            if post_err:
                return NyraToolResult.err(post_err)

        log.info(
            "bt_composite_added",
            bt=bt_path,
            parent=parent_node,
            cls=composite_class,
            node=created_name,
        )
        result = {
            "bt_path": bt_path,
            "parent_node": parent_node,
            "composite_class": composite_class,
            "node_name": created_name,
        }
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)


# ---------------------------------------------------------------------------
# nyra_bt_add_task
# ---------------------------------------------------------------------------


class BTAddTaskTool(NyraTool):
    name = "nyra_bt_add_task"
    description = "Add a task node (e.g. BTTask_MoveTo) under a parent composite."
    parameters = {
        "type": "object",
        "properties": {
            "bt_path": {"type": "string"},
            "parent_composite": {
                "type": "string",
                "description": "FName of the composite to attach the task under",
            },
            "task_class": {
                "type": "string",
                "description": "FName like 'BTTask_MoveTo' or '/Script/AIModule.BTTask_RunBehavior'",
            },
            "position": {
                "type": "object",
                "properties": {
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                },
                "default": {"x": 0, "y": 0},
            },
        },
        "required": ["bt_path", "parent_composite", "task_class"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        ue = _require_unreal()
        if ue is None:
            return NyraToolResult.err(
                "unreal module not available; nyra_bt_add_task requires the UE editor"
            )
        if not hasattr(ue, "NyraBTHelper"):
            return NyraToolResult.err(
                "unreal.NyraBTHelper not registered (NyraEditor not loaded?); "
                "not_supported_on_this_ue_version"
            )

        bt_path = params.get("bt_path")
        parent_composite = params.get("parent_composite")
        task_class = params.get("task_class")
        if not isinstance(bt_path, str):
            return NyraToolResult.err(f"bt_path must be a string, got {bt_path!r}")
        if not isinstance(parent_composite, str):
            return NyraToolResult.err(
                f"parent_composite must be a string, got {parent_composite!r}"
            )
        if not isinstance(task_class, str):
            return NyraToolResult.err(
                f"task_class must be a string, got {task_class!r}"
            )

        pos = params.get("position") or {"x": 0, "y": 0}
        try:
            pos_x = float(pos.get("x", 0))
            pos_y = float(pos.get("y", 0))
        except (TypeError, ValueError) as e:
            return NyraToolResult.err(f"position.x/y must be numbers: {e}")

        created_name = ""
        with session_transaction(f"NYRA: {self.name}"):
            try:
                bt = _load_bt_asset(bt_path)
                if bt is None:
                    return NyraToolResult.err(f"BT not found at {bt_path}")
                created_name = ue.NyraBTHelper.add_task_node(
                    bt,
                    task_class,
                    parent_composite,
                    ue.Vector2D(pos_x, pos_y),
                )
                if not created_name:
                    return NyraToolResult.err(
                        "AddTaskNode helper returned empty name "
                        "(parent not found, or task_class invalid)"
                    )
                ue.EditorAssetLibrary.save_asset(bt_path)
            except Exception as e:
                log.error("bt_add_task_failed", error=str(e), bt=bt_path)
                return NyraToolResult.err(f"failed to add task: {e}")

            post_err = verify_post_condition(
                f"{self.name}({bt_path}:{created_name})",
                lambda: _load_bt_asset(bt_path) is not None,
            )
            if post_err:
                return NyraToolResult.err(post_err)

        log.info(
            "bt_task_added",
            bt=bt_path,
            parent=parent_composite,
            cls=task_class,
            node=created_name,
        )
        result = {
            "bt_path": bt_path,
            "parent_composite": parent_composite,
            "task_class": task_class,
            "node_name": created_name,
        }
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)


# ---------------------------------------------------------------------------
# nyra_bt_add_decorator
# ---------------------------------------------------------------------------


class BTAddDecoratorTool(NyraTool):
    name = "nyra_bt_add_decorator"
    description = (
        "Attach a decorator (e.g. BTDecorator_Blackboard) to an existing "
        "task or composite node."
    )
    parameters = {
        "type": "object",
        "properties": {
            "bt_path": {"type": "string"},
            "target_node": {
                "type": "string",
                "description": "FName of the node to decorate",
            },
            "decorator_class": {
                "type": "string",
                "description": "FName like 'BTDecorator_Blackboard'",
            },
        },
        "required": ["bt_path", "target_node", "decorator_class"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        ue = _require_unreal()
        if ue is None:
            return NyraToolResult.err(
                "unreal module not available; nyra_bt_add_decorator requires the UE editor"
            )
        if not hasattr(ue, "NyraBTHelper"):
            return NyraToolResult.err(
                "unreal.NyraBTHelper not registered (NyraEditor not loaded?); "
                "not_supported_on_this_ue_version"
            )

        bt_path = params.get("bt_path")
        target_node = params.get("target_node")
        decorator_class = params.get("decorator_class")
        if not isinstance(bt_path, str):
            return NyraToolResult.err(f"bt_path must be a string, got {bt_path!r}")
        if not isinstance(target_node, str):
            return NyraToolResult.err(
                f"target_node must be a string, got {target_node!r}"
            )
        if not isinstance(decorator_class, str):
            return NyraToolResult.err(
                f"decorator_class must be a string, got {decorator_class!r}"
            )

        ok = False
        with session_transaction(f"NYRA: {self.name}"):
            try:
                bt = _load_bt_asset(bt_path)
                if bt is None:
                    return NyraToolResult.err(f"BT not found at {bt_path}")
                ok = bool(
                    ue.NyraBTHelper.add_decorator_node(
                        bt, decorator_class, target_node
                    )
                )
                if not ok:
                    return NyraToolResult.err(
                        "AddDecoratorNode helper returned false "
                        "(target_node not found or decorator_class invalid)"
                    )
                ue.EditorAssetLibrary.save_asset(bt_path)
            except Exception as e:
                log.error("bt_add_decorator_failed", error=str(e), bt=bt_path)
                return NyraToolResult.err(f"failed to add decorator: {e}")

            post_err = verify_post_condition(
                f"{self.name}({bt_path}:{target_node}/{decorator_class})",
                lambda: _load_bt_asset(bt_path) is not None,
            )
            if post_err:
                return NyraToolResult.err(post_err)

        log.info(
            "bt_decorator_added",
            bt=bt_path,
            target=target_node,
            cls=decorator_class,
        )
        result = {
            "bt_path": bt_path,
            "target_node": target_node,
            "decorator_class": decorator_class,
            "applied": ok,
        }
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)


# ---------------------------------------------------------------------------
# nyra_bt_set_blackboard_key
# ---------------------------------------------------------------------------


class BTSetBlackboardKeyTool(NyraTool):
    name = "nyra_bt_set_blackboard_key"
    description = (
        "Add or update a key on a UBlackboardData asset. Idempotent — "
        "running with the same (path, name, type) returns deduped:True."
    )
    parameters = {
        "type": "object",
        "properties": {
            "blackboard_path": {
                "type": "string",
                "description": "/Game/... path to a UBlackboardData asset",
            },
            "key_name": {"type": "string"},
            "key_type": {
                "type": "string",
                "enum": ["Bool", "Int", "Float", "String", "Vector", "Object"],
            },
        },
        "required": ["blackboard_path", "key_name", "key_type"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        ue = _require_unreal()
        if ue is None:
            return NyraToolResult.err(
                "unreal module not available; nyra_bt_set_blackboard_key requires the UE editor"
            )
        if not hasattr(ue, "NyraBTHelper"):
            return NyraToolResult.err(
                "unreal.NyraBTHelper not registered (NyraEditor not loaded?); "
                "not_supported_on_this_ue_version"
            )

        bb_path = params.get("blackboard_path")
        key_name = params.get("key_name")
        key_type = params.get("key_type")
        if not isinstance(bb_path, str):
            return NyraToolResult.err(
                f"blackboard_path must be a string, got {bb_path!r}"
            )
        if not isinstance(key_name, str) or not key_name:
            return NyraToolResult.err(
                f"key_name must be a non-empty string, got {key_name!r}"
            )
        if key_type not in ("Bool", "Int", "Float", "String", "Vector", "Object"):
            return NyraToolResult.err(
                f"key_type must be one of Bool/Int/Float/String/Vector/Object, "
                f"got {key_type!r}"
            )

        applied = False
        with session_transaction(f"NYRA: {self.name}"):
            try:
                bb = _load_blackboard_asset(bb_path)
                if bb is None:
                    return NyraToolResult.err(
                        f"BlackboardData not found at {bb_path}"
                    )
                applied = bool(
                    ue.NyraBTHelper.set_blackboard_key(bb, key_name, key_type)
                )
                if not applied:
                    return NyraToolResult.err(
                        "SetBlackboardKey helper returned false "
                        "(unknown key_type or write failure)"
                    )
                ue.EditorAssetLibrary.save_asset(bb_path)
            except Exception as e:
                log.error("bt_set_bb_key_failed", error=str(e), bb=bb_path)
                return NyraToolResult.err(f"failed to set blackboard key: {e}")

            post_err = verify_post_condition(
                f"{self.name}({bb_path}:{key_name}:{key_type})",
                lambda: _load_blackboard_asset(bb_path) is not None,
            )
            if post_err:
                return NyraToolResult.err(post_err)

        log.info(
            "bt_blackboard_key_set",
            bb=bb_path,
            key=key_name,
            type=key_type,
        )
        result = {
            "blackboard_path": bb_path,
            "key_name": key_name,
            "key_type": key_type,
            "applied": applied,
        }
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)
