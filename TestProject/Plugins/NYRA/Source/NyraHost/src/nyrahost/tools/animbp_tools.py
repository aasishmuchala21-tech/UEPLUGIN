"""nyrahost.tools.animbp_tools — PARITY-07 AnimBlueprint authoring mutators.

Per Plan 08-07:
  - nyra_animbp_create:             create UAnimBlueprint asset for a Skeleton
  - nyra_animbp_add_state_machine:  add a state machine (+ optional pre-states)
  - nyra_animbp_add_transition:     add a transition between two existing states

All three follow the canonical Phase 4 mutator shape (LOCKED-03):
  - idempotent_lookup() at top
  - session_transaction("NYRA: <tool>") wraps the mutation
  - verify_post_condition() after the mutation
  - idempotent_record() before returning ok
  - NyraToolResult.ok / .err for the BL-01 envelope

The `unreal.NyraAnimBPHelper.*` calls reach the C++ helper UCLASS in
NyraEditor (see ToolHelpers/NyraAnimBPHelper.h). UE Python doesn't expose
AnimGraph node classes directly, so the helper is mandatory — these tools
fail cleanly if it's not reflected (PATTERNS.md S5 defensive coding).

Out of scope per CONTEXT.md: custom AnimNode generation. State machines +
states + transitions only.
"""
from __future__ import annotations

from typing import Any

import structlog

from nyrahost.tools.base import (
    NyraTool,
    NyraToolResult,
    idempotent_lookup,
    idempotent_record,
    session_transaction,
    verify_post_condition,
)

log = structlog.get_logger("nyrahost.tools.animbp_tools")

__all__ = [
    "AnimBPCreateTool",
    "AnimBPAddStateMachineTool",
    "AnimBPAddTransitionTool",
]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _load_animbp(path: str) -> Any:
    """Defensive load + isinstance check for AnimBlueprint assets.

    PATTERNS.md S5: returns None when the asset doesn't exist OR when it
    exists but is the wrong UClass (e.g. caller passed the path of a regular
    Blueprint by mistake). Tools surface this as `NyraToolResult.err(...)`.
    """
    try:
        import unreal  # type: ignore
    except ImportError:
        return None
    try:
        asset = unreal.EditorAssetLibrary.load_asset(path)
    except Exception as e:
        log.warning("animbp_load_failed", path=path, error=str(e))
        return None
    if asset is None:
        return None
    if not isinstance(asset, unreal.AnimBlueprint):
        return None
    return asset


def _helper_available() -> bool:
    """Return True iff the C++ UNyraAnimBPHelper is reflected on this UE.

    The helper is editor-only and lives in NyraEditor; if the plugin's
    NyraEditor module failed to load the symbol won't exist. Used as a
    register-time gate so the tool returns a clean error rather than
    raising AttributeError mid-execution.
    """
    try:
        import unreal  # type: ignore
    except ImportError:
        return False
    return hasattr(unreal, "NyraAnimBPHelper")


def _factory_available() -> bool:
    """Return True iff unreal.AnimBlueprintFactory is reflected (T-08-01)."""
    try:
        import unreal  # type: ignore
    except ImportError:
        return False
    return hasattr(unreal, "AnimBlueprintFactory")


# -----------------------------------------------------------------------------
# nyra_animbp_create
# -----------------------------------------------------------------------------


class AnimBPCreateTool(NyraTool):
    name = "nyra_animbp_create"
    description = (
        "Create a new UAnimBlueprint asset bound to the given USkeleton. "
        "Returns the asset path. Idempotent: re-creating with identical "
        "params returns the existing AnimBP (deduped:True)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "asset_path": {
                "type": "string",
                "description": "UE asset path for the new AnimBP, e.g. '/Game/Anim/ABP_Hero'",
            },
            "skeleton_path": {
                "type": "string",
                "description": "Path to an existing USkeleton, e.g. '/Game/Mannequin/Mannequin_Skeleton'",
            },
        },
        "required": ["asset_path", "skeleton_path"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        # BL-05: dedup re-spawn on retries.
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        # T-08-01: register-time symbol gate. If AnimBlueprintFactory isn't
        # reflected on this UE version, bail before any side effects.
        if not _factory_available():
            return NyraToolResult.err(
                "unreal.AnimBlueprintFactory not reflected on this UE version"
            )

        try:
            import unreal  # type: ignore
        except ImportError:
            return NyraToolResult.err("unreal module not available (run inside UE editor)")

        with session_transaction(f"NYRA: {self.name}"):
            try:
                skeleton = unreal.EditorAssetLibrary.load_asset(params["skeleton_path"])
                if skeleton is None:
                    return NyraToolResult.err(f"Skeleton not found: {params['skeleton_path']}")
                if not isinstance(skeleton, unreal.Skeleton):
                    return NyraToolResult.err(
                        f"skeleton_path must reference a USkeleton: {params['skeleton_path']}"
                    )

                factory = unreal.AnimBlueprintFactory()
                factory.set_editor_property("target_skeleton", skeleton)

                asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
                pkg_path, pkg_name = params["asset_path"].rsplit("/", 1)
                abp = asset_tools.create_asset(
                    pkg_name, pkg_path, unreal.AnimBlueprint, factory
                )
                if abp is None:
                    return NyraToolResult.err(
                        f"create_asset returned None for {params['asset_path']}"
                    )
                unreal.EditorAssetLibrary.save_asset(params["asset_path"])
            except Exception as e:
                log.error("animbp_create_failed", error=str(e))
                return NyraToolResult.err(f"AnimBP create failed: {e}")

            # BL-06: post-condition — re-load and isinstance-check.
            err = verify_post_condition(
                f"{self.name}({params['asset_path']})",
                lambda: _load_animbp(params["asset_path"]) is not None,
            )
            if err:
                return NyraToolResult.err(err)

        result = {
            "asset_path": params["asset_path"],
            "skeleton": params["skeleton_path"],
        }
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)


# -----------------------------------------------------------------------------
# nyra_animbp_add_state_machine
# -----------------------------------------------------------------------------


class AnimBPAddStateMachineTool(NyraTool):
    name = "nyra_animbp_add_state_machine"
    description = (
        "Add a state machine to an existing AnimBlueprint. Optionally pre-creates "
        "named states inside the new machine. Idempotent on (animbp_path, "
        "machine_name) — calling twice returns the existing machine."
    )
    parameters = {
        "type": "object",
        "properties": {
            "animbp_path": {
                "type": "string",
                "description": "UE asset path of the target AnimBlueprint",
            },
            "machine_name": {
                "type": "string",
                "description": "Display name of the new state machine, e.g. 'Locomotion'",
            },
            "states": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional: state names to pre-create inside the machine",
            },
            "position": {
                "type": "object",
                "properties": {"x": {"type": "number"}, "y": {"type": "number"}},
                "description": "Graph-space node position (defaults to 0,0)",
            },
        },
        "required": ["animbp_path", "machine_name"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        if not _helper_available():
            return NyraToolResult.err(
                "unreal.NyraAnimBPHelper not reflected — NyraEditor not loaded "
                "or this UE version doesn't expose the AnimGraph helper"
            )

        try:
            import unreal  # type: ignore
        except ImportError:
            return NyraToolResult.err("unreal module not available (run inside UE editor)")

        created_name = ""
        states_created: list[str] = []
        with session_transaction(f"NYRA: {self.name}"):
            try:
                abp = _load_animbp(params["animbp_path"])
                if abp is None:
                    return NyraToolResult.err(
                        f"AnimBP not found: {params['animbp_path']}"
                    )
                pos = params.get("position") or {}
                pos_vec = unreal.Vector2D(
                    float(pos.get("x", 0.0)), float(pos.get("y", 0.0))
                )

                created_name = unreal.NyraAnimBPHelper.add_state_machine(
                    abp,
                    unreal.Name(params["machine_name"]),
                    pos_vec,
                )
                if not created_name:
                    return NyraToolResult.err(
                        "AddStateMachine helper returned empty name "
                        "(AnimBP may have no AnimGraph)"
                    )

                # Pre-declared states
                for state_name in params.get("states") or []:
                    s = unreal.NyraAnimBPHelper.add_state(
                        abp,
                        unreal.Name(params["machine_name"]),
                        unreal.Name(state_name),
                        unreal.Vector2D(0.0, 0.0),
                    )
                    if s:
                        states_created.append(s)
                    else:
                        log.warning(
                            "animbp_add_state_failed",
                            machine=params["machine_name"],
                            state=state_name,
                        )

                unreal.EditorAssetLibrary.save_asset(params["animbp_path"])
            except Exception as e:
                log.error("animbp_add_state_machine_failed", error=str(e))
                return NyraToolResult.err(f"AnimBP add_state_machine failed: {e}")

            # BL-06: post-condition — AnimBP still loadable + non-empty machine name.
            err = verify_post_condition(
                f"{self.name}({params['animbp_path']})",
                lambda: _load_animbp(params["animbp_path"]) is not None
                and bool(created_name),
            )
            if err:
                return NyraToolResult.err(err)

        result = {
            "animbp_path": params["animbp_path"],
            "machine_name": created_name,
            "states": states_created,
        }
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)


# -----------------------------------------------------------------------------
# nyra_animbp_add_transition
# -----------------------------------------------------------------------------


class AnimBPAddTransitionTool(NyraTool):
    name = "nyra_animbp_add_transition"
    description = (
        "Add a transition between two existing states in a state machine. "
        "Idempotent: a transition between the same source/target is not "
        "duplicated."
    )
    parameters = {
        "type": "object",
        "properties": {
            "animbp_path": {"type": "string"},
            "machine_name": {
                "type": "string",
                "description": "Name of the state machine (must exist; create via nyra_animbp_add_state_machine)",
            },
            "from_state": {
                "type": "string",
                "description": "Source state name (must exist in the machine)",
            },
            "to_state": {
                "type": "string",
                "description": "Destination state name (must exist in the machine)",
            },
        },
        "required": ["animbp_path", "machine_name", "from_state", "to_state"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        if not _helper_available():
            return NyraToolResult.err(
                "unreal.NyraAnimBPHelper not reflected — NyraEditor not loaded "
                "or this UE version doesn't expose the AnimGraph helper"
            )

        try:
            import unreal  # type: ignore
        except ImportError:
            return NyraToolResult.err("unreal module not available (run inside UE editor)")

        ok = False
        with session_transaction(f"NYRA: {self.name}"):
            try:
                abp = _load_animbp(params["animbp_path"])
                if abp is None:
                    return NyraToolResult.err(
                        f"AnimBP not found: {params['animbp_path']}"
                    )

                ok = bool(unreal.NyraAnimBPHelper.add_transition(
                    abp,
                    unreal.Name(params["machine_name"]),
                    unreal.Name(params["from_state"]),
                    unreal.Name(params["to_state"]),
                ))
                if not ok:
                    return NyraToolResult.err(
                        f"AddTransition refused: machine={params['machine_name']!r} "
                        f"from={params['from_state']!r} to={params['to_state']!r} — "
                        "one or both states may not exist, or schema rejected the connection"
                    )
                unreal.EditorAssetLibrary.save_asset(params["animbp_path"])
            except Exception as e:
                log.error("animbp_add_transition_failed", error=str(e))
                return NyraToolResult.err(f"AnimBP add_transition failed: {e}")

            # BL-06: post-condition — AnimBP still loadable, helper said ok.
            err = verify_post_condition(
                f"{self.name}({params['animbp_path']})",
                lambda: _load_animbp(params["animbp_path"]) is not None and ok,
            )
            if err:
                return NyraToolResult.err(err)

        result = {
            "animbp_path": params["animbp_path"],
            "machine_name": params["machine_name"],
            "from_state": params["from_state"],
            "to_state": params["to_state"],
            "status": "added",
        }
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)
