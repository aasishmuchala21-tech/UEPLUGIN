"""nyrahost.tools.metasound_tools — PARITY-08 Metasounds authoring mutators.

Smallest scope of Phase 8 — gloss-tier per CONTEXT.md SC#8. Three tools:

  - nyra_metasound_create   — create a MetaSoundSource asset
  - nyra_metasound_add_node — add a node to a Metasound graph
  - nyra_metasound_connect  — connect two pins between Metasound nodes

Pattern lift identical to PARITY-05 (Niagara) per PATTERNS.md:
LOCKED-03 BL-04 / BL-05 / BL-06 / BL-12 mutator shape via
`session_transaction`, `idempotent_lookup` / `idempotent_record`,
`verify_post_condition`, and `NyraToolResult.to_dict()`.

Capitalisation note (RESEARCH.md A4): UE may expose either
'MetaSound' or 'Metasound' spellings across UE 5.4-5.7 — the
`_resolve_*` helpers probe BOTH spellings and pick whichever is
present. This is the single most-likely real-world failure mode
for Plan 08-08.

Builder reflection note (RESEARCH.md Q1 RESOLVED-DEFERRED-TO-WAVE-0):
if `UMetaSoundBuilderSubsystem` is NOT Python-reflected on a shipped
UE version, `nyra_metasound_add_node` and `nyra_metasound_connect`
return `not_supported_on_this_ue_version` and only
`nyra_metasound_create` is usable. The graceful-degradation path
is the design — the plan does NOT abort.

This is the only Wave-2 plan in Phase 8 with NO C++ helper module.
"""
from __future__ import annotations

import structlog

try:
    import unreal  # type: ignore
    HAS_UNREAL = True
except ImportError:
    HAS_UNREAL = False

from nyrahost.tools.base import (
    NyraTool,
    NyraToolResult,
    idempotent_lookup,
    idempotent_record,
    session_transaction,
    verify_post_condition,
)

log = structlog.get_logger("nyrahost.tools.metasound_tools")

__all__ = [
    "MetasoundCreateTool",
    "MetasoundAddNodeTool",
    "MetasoundConnectTool",
]


# ---------------------------------------------------------------------------
# Capitalisation-drift defense (RESEARCH.md A4)
#
# UE 5.4-5.7 has been observed to expose Metasounds APIs under either
# 'MetaSound*' or 'Metasound*' spellings (the C++ surface is consistent
# 'MetaSound' but Python binding generation has historically lower-cased
# the second 'S' on some 5.x builds). Each `_resolve_*` helper probes
# BOTH spellings and returns the first hit. If NEITHER is reflected,
# the helper returns None and the tool's execute() returns a clean
# `not_supported_on_this_ue_version` envelope.
# ---------------------------------------------------------------------------


def _resolve_factory():
    """Resolve the asset factory class (asset creation).

    RESEARCH.md A4: probes both capitalisation spellings + the
    pre-5.6 `MetaSoundFactory` short form vs the 5.6+
    `MetaSoundSourceFactory` long form. Returns None when neither
    is reflected.
    """
    if not HAS_UNREAL:
        return None
    for name in ("MetaSoundSourceFactory", "MetaSoundFactory", "MetasoundFactory"):
        if hasattr(unreal, name):
            return getattr(unreal, name)
    return None


def _resolve_asset_class():
    """Resolve the created asset class (BL-12 isinstance target).

    Probes MetaSoundSource first, then the lower-case spelling, then
    MetaSoundPatch as a last-resort fallback (a Patch is a graph-only
    Metasound, less common but still reflectable).
    """
    if not HAS_UNREAL:
        return None
    for name in ("MetaSoundSource", "MetasoundSource", "MetaSoundPatch"):
        if hasattr(unreal, name):
            return getattr(unreal, name)
    return None


def _resolve_builder_subsystem():
    """Resolve the graph mutation subsystem instance (add_node / connect).

    Returns the live editor-subsystem singleton, NOT the class. Returns
    None when neither capitalisation is reflected — the caller maps that
    to `not_supported_on_this_ue_version`.
    """
    if not HAS_UNREAL:
        return None
    for name in ("MetaSoundBuilderSubsystem", "MetasoundBuilderSubsystem"):
        if hasattr(unreal, name):
            try:
                return unreal.get_editor_subsystem(getattr(unreal, name))
            except Exception:
                # Class is reflected but subsystem instance fetch failed;
                # bubble up as None so the tool returns a clean error envelope.
                return None
    return None


def _load_metasound(path: str):
    """Defensive lookup + isinstance check (BL-12).

    Returns None when the asset is missing OR is not a MetaSound
    subclass. Caller distinguishes between "missing" and "wrong class"
    by inspecting EditorAssetLibrary.does_asset_exist separately if
    needed — but for the post-condition verification the combined
    "loadable AND correct class" check is what matters.
    """
    if not HAS_UNREAL:
        return None
    try:
        asset = unreal.EditorAssetLibrary.load_asset(path)
    except Exception:
        return None
    if asset is None:
        return None
    cls = _resolve_asset_class()
    if cls is not None and not isinstance(asset, cls):
        return None
    return asset


# ---------------------------------------------------------------------------
# nyra_metasound_create
# ---------------------------------------------------------------------------


class MetasoundCreateTool(NyraTool):
    """Create a new MetaSoundSource asset at the given content path."""

    name = "nyra_metasound_create"
    description = (
        "Create a new MetaSoundSource asset at the given UE content path. "
        "Returns the asset path; idempotent on (asset_path) — a repeat call "
        "returns deduped: True without re-creating the asset."
    )
    parameters = {
        "type": "object",
        "properties": {
            "asset_path": {
                "type": "string",
                "description": "UE content path, e.g. '/Game/Audio/MS_TestTone'",
            },
        },
        "required": ["asset_path"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        if not HAS_UNREAL:
            return NyraToolResult.err(
                "unreal module not available — Metasound tools only run inside UE editor"
            )

        factory_cls = _resolve_factory()
        asset_cls = _resolve_asset_class()
        if factory_cls is None or asset_cls is None:
            return NyraToolResult.err(
                "not_supported_on_this_ue_version: MetaSound factory/source class "
                "not reflected (checked both 'MetaSound*' and 'Metasound*' "
                "capitalisations); see Wave 0 symbol survey"
            )

        asset_path = params["asset_path"]

        # Validate path shape BEFORE entering the transaction / touching UE
        # surfaces so a malformed path returns a clean envelope without
        # spurious "failed: AttributeError on AssetToolsHelpers" noise.
        if "/" not in asset_path:
            return NyraToolResult.err(
                f"asset_path must be a /Game/... path; got {asset_path!r}"
            )

        with session_transaction(f"NYRA: {self.name}"):
            try:
                factory = factory_cls()
                asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
                # Split "/Game/Audio/MS_TestTone" -> ("/Game/Audio", "MS_TestTone")
                pkg_path, pkg_name = asset_path.rsplit("/", 1)
                ms = asset_tools.create_asset(pkg_name, pkg_path, asset_cls, factory)
                if ms is None:
                    return NyraToolResult.err(
                        f"create_asset returned None for {asset_path}"
                    )
                unreal.EditorAssetLibrary.save_asset(asset_path)
            except Exception as e:
                log.error("metasound_create_failed", path=asset_path, error=str(e))
                return NyraToolResult.err(f"failed: {e}")

            err = verify_post_condition(
                f"{self.name}({asset_path})",
                lambda: _load_metasound(asset_path) is not None,
            )
            if err:
                return NyraToolResult.err(err)

        result = {"asset_path": asset_path}
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)


# ---------------------------------------------------------------------------
# nyra_metasound_add_node
# ---------------------------------------------------------------------------


class MetasoundAddNodeTool(NyraTool):
    """Add a node (oscillator, wave-player, mixer, etc.) to a Metasound graph."""

    name = "nyra_metasound_add_node"
    description = (
        "Add a node (oscillator, wave-player, mixer, etc.) to a Metasound graph. "
        "Requires UMetaSoundBuilderSubsystem to be Python-reflected on the "
        "current UE version; returns not_supported_on_this_ue_version otherwise."
    )
    parameters = {
        "type": "object",
        "properties": {
            "asset_path": {
                "type": "string",
                "description": "UE content path of an existing MetaSoundSource",
            },
            "node_class": {
                "type": "string",
                "description": "Node-class name, e.g. 'Oscillator', 'WavePlayer', 'OutputAudio'",
            },
            "node_name": {
                "type": "string",
                "description": "Author-friendly name for the new node, e.g. 'Osc1'",
            },
        },
        "required": ["asset_path", "node_class", "node_name"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        if not HAS_UNREAL:
            return NyraToolResult.err(
                "unreal module not available — Metasound tools only run inside UE editor"
            )

        builder = _resolve_builder_subsystem()
        if builder is None:
            return NyraToolResult.err(
                "not_supported_on_this_ue_version: MetaSoundBuilderSubsystem "
                "not reflected (checked both capitalisations); ship "
                "nyra_metasound_create only on this version"
            )

        asset_path = params["asset_path"]
        node_class = params["node_class"]
        node_name = params["node_name"]

        ms = _load_metasound(asset_path)
        if ms is None:
            return NyraToolResult.err(f"MetaSound not found or wrong class: {asset_path}")

        with session_transaction(f"NYRA: {self.name}"):
            try:
                # Builder API surface: subsystem-specific. The signature is
                # finalised by Wave 0 Task 0's symbol survey — historically
                # `add_node(graph, class_name, node_name)` on 5.6+. If a
                # different signature is present on the shipped version,
                # this raise() flows up into the err envelope.
                if hasattr(builder, "add_node"):
                    ok = builder.add_node(ms, node_class, node_name)
                elif hasattr(builder, "add_node_to_graph"):
                    ok = builder.add_node_to_graph(ms, node_class, node_name)
                else:
                    return NyraToolResult.err(
                        "builder subsystem reflected but no add_node* method "
                        "(checked add_node, add_node_to_graph) — see Wave 0 dump"
                    )
                if not ok:
                    return NyraToolResult.err(
                        f"add_node returned false for {node_name} (class={node_class})"
                    )
                unreal.EditorAssetLibrary.save_asset(asset_path)
            except Exception as e:
                log.error(
                    "metasound_add_node_failed",
                    path=asset_path,
                    node_name=node_name,
                    node_class=node_class,
                    error=str(e),
                )
                return NyraToolResult.err(f"failed: {e}")

            err = verify_post_condition(
                f"{self.name}({asset_path}, node={node_name})",
                lambda: _load_metasound(asset_path) is not None,
            )
            if err:
                return NyraToolResult.err(err)

        result = {
            "asset_path": asset_path,
            "node_name": node_name,
            "node_class": node_class,
        }
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)


# ---------------------------------------------------------------------------
# nyra_metasound_connect
# ---------------------------------------------------------------------------


class MetasoundConnectTool(NyraTool):
    """Connect two pins between Metasound nodes."""

    name = "nyra_metasound_connect"
    description = (
        "Connect two pins between Metasound nodes (e.g. Oscillator.Out -> "
        "OutputAudio.In). Requires UMetaSoundBuilderSubsystem to be "
        "Python-reflected on the current UE version."
    )
    parameters = {
        "type": "object",
        "properties": {
            "asset_path":   {"type": "string"},
            "from_node_id": {"type": "string", "description": "Source node name (e.g. 'Osc1')"},
            "from_pin":     {"type": "string", "description": "Source pin name (e.g. 'Out')"},
            "to_node_id":   {"type": "string", "description": "Sink node name (e.g. 'Out1')"},
            "to_pin":       {"type": "string", "description": "Sink pin name (e.g. 'In')"},
        },
        "required": ["asset_path", "from_node_id", "from_pin", "to_node_id", "to_pin"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        if not HAS_UNREAL:
            return NyraToolResult.err(
                "unreal module not available — Metasound tools only run inside UE editor"
            )

        builder = _resolve_builder_subsystem()
        if builder is None:
            return NyraToolResult.err(
                "not_supported_on_this_ue_version: MetaSoundBuilderSubsystem "
                "not reflected (checked both capitalisations); ship "
                "nyra_metasound_create only on this version"
            )

        asset_path = params["asset_path"]
        from_node_id = params["from_node_id"]
        from_pin = params["from_pin"]
        to_node_id = params["to_node_id"]
        to_pin = params["to_pin"]

        ms = _load_metasound(asset_path)
        if ms is None:
            return NyraToolResult.err(f"MetaSound not found or wrong class: {asset_path}")

        with session_transaction(f"NYRA: {self.name}"):
            try:
                # Same survey-driven dispatch as add_node — exact method name
                # confirmed by Wave 0. Common spellings in observed UE
                # versions are connect_pins / connect_nodes / connect.
                if hasattr(builder, "connect_pins"):
                    ok = builder.connect_pins(ms, from_node_id, from_pin, to_node_id, to_pin)
                elif hasattr(builder, "connect_nodes"):
                    ok = builder.connect_nodes(ms, from_node_id, from_pin, to_node_id, to_pin)
                elif hasattr(builder, "connect"):
                    ok = builder.connect(ms, from_node_id, from_pin, to_node_id, to_pin)
                else:
                    return NyraToolResult.err(
                        "builder subsystem reflected but no connect* method "
                        "(checked connect_pins, connect_nodes, connect) — see Wave 0 dump"
                    )
                if not ok:
                    return NyraToolResult.err(
                        f"connect returned false for "
                        f"{from_node_id}.{from_pin} -> {to_node_id}.{to_pin}"
                    )
                unreal.EditorAssetLibrary.save_asset(asset_path)
            except Exception as e:
                log.error(
                    "metasound_connect_failed",
                    path=asset_path,
                    src=f"{from_node_id}.{from_pin}",
                    dst=f"{to_node_id}.{to_pin}",
                    error=str(e),
                )
                return NyraToolResult.err(f"failed: {e}")

            err = verify_post_condition(
                f"{self.name}({asset_path}, {from_node_id}.{from_pin} -> {to_node_id}.{to_pin})",
                lambda: _load_metasound(asset_path) is not None,
            )
            if err:
                return NyraToolResult.err(err)

        result = {
            "asset_path": asset_path,
            "from_node_id": from_node_id,
            "from_pin": from_pin,
            "to_node_id": to_node_id,
            "to_pin": to_pin,
        }
        idempotent_record(self.name, params, result)
        return NyraToolResult.ok(result)
