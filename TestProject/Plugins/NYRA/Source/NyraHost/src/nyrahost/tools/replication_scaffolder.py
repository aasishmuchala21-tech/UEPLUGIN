"""nyrahost.tools.replication_scaffolder — Phase 14-H Replication Scaffolder.

Tier 2 whole-project moat. Takes a Blueprint (or C++ class) header
+ a list of properties the user wants replicated, and emits:

  * Per-property ``UPROPERTY(Replicated, ...)`` annotations (with
    optional Cond_OwnerOnly / Cond_SkipOwner)
  * RepNotify scaffolding (``OnRep_<Prop>`` declarations + bodies)
  * ``GetLifetimeReplicatedProps`` registration
  * Optional Server/Client RPC stubs for state-changing methods

Aura ships per-domain agents; whole-project replication audit /
scaffolding requires walking every actor, which Aura's per-event SaaS
pricing makes cost-prohibitive at studio scale.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Iterable, Optional

import structlog

log = structlog.get_logger("nyrahost.tools.replication_scaffolder")

ERR_BAD_INPUT: Final[int] = -32602
ERR_REPL_FAILED: Final[int] = -32062

ALLOWED_CONDS: Final[frozenset[str]] = frozenset({
    "None",
    "Cond_OwnerOnly",
    "Cond_SkipOwner",
    "Cond_InitialOnly",
    "Cond_SimulatedOnly",
})


@dataclass(frozen=True)
class ReplicatedProperty:
    name: str
    type_decl: str         # e.g. "int32", "TArray<FVector>"
    rep_notify: bool = False
    condition: str = "None"  # one of ALLOWED_CONDS

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type_decl": self.type_decl,
            "rep_notify": self.rep_notify,
            "condition": self.condition,
        }


def render_uproperty(p: ReplicatedProperty) -> str:
    flags: list[str] = []
    if p.rep_notify:
        flags.append(f"ReplicatedUsing=OnRep_{p.name}")
    else:
        flags.append("Replicated")
    flags.append("BlueprintReadOnly")
    return f"UPROPERTY({', '.join(flags)})\n{p.type_decl} {p.name};"


def render_get_lifetime(class_name: str, props: list[ReplicatedProperty]) -> str:
    """Render the GetLifetimeReplicatedProps body."""
    lines = [
        f"void {class_name}::GetLifetimeReplicatedProps(",
        f"    TArray<FLifetimeProperty>& OutLifetimeProps) const",
        f"{{",
        f"    Super::GetLifetimeReplicatedProps(OutLifetimeProps);",
    ]
    for p in props:
        if p.condition == "None":
            lines.append(f"    DOREPLIFETIME({class_name}, {p.name});")
        else:
            lines.append(
                f"    DOREPLIFETIME_CONDITION({class_name}, {p.name}, {p.condition});"
            )
    lines.append("}")
    return "\n".join(lines)


def render_rep_notify_body(class_name: str, p: ReplicatedProperty) -> str:
    return (
        f"void {class_name}::OnRep_{p.name}()\n"
        f"{{\n"
        f"    // Phase 14-H scaffold — fill in client-side reaction to {p.name}.\n"
        f"    // E.g. fire a delegate, refresh a UMG widget, retrigger a VFX cue.\n"
        f"}}"
    )


def render_rpc_stub(method_name: str, kind: str = "Server") -> str:
    """Generate a Server/Client RPC pair (declaration + impl skeleton)."""
    if kind not in {"Server", "Client", "NetMulticast"}:
        raise ValueError(f"unsupported RPC kind: {kind}")
    spec = "Server, Reliable, WithValidation" if kind == "Server" else f"{kind}, Reliable"
    decl = (
        f"UFUNCTION({spec}, BlueprintCallable)\n"
        f"void {method_name}();"
    )
    impl = (
        f"void A<YourClass>::{method_name}_Implementation()\n"
        f"{{\n"
        f"    // Phase 14-H scaffold — server-authoritative work goes here.\n"
        f"}}"
    )
    if kind == "Server":
        impl = impl + (
            f"\n\nbool A<YourClass>::{method_name}_Validate()\n"
            f"{{\n"
            f"    return true;   // tighten per Anti-cheat policy.\n"
            f"}}"
        )
    return f"// header:\n{decl}\n\n// impl:\n{impl}"


def scaffold_class(
    class_name: str,
    *,
    properties: list[ReplicatedProperty],
    rpcs: list[tuple[str, str]] | None = None,
) -> dict:
    """Return a structured scaffold dict the panel renders."""
    if not isinstance(class_name, str) or not class_name:
        raise ValueError("class_name must be a non-empty string")
    for p in properties:
        if p.condition not in ALLOWED_CONDS:
            raise ValueError(f"unsupported condition {p.condition!r}")
    rpcs = rpcs or []
    return {
        "class_name": class_name,
        "uproperty_decls": [render_uproperty(p) for p in properties],
        "get_lifetime_body": render_get_lifetime(class_name, properties),
        "rep_notify_bodies": [
            render_rep_notify_body(class_name, p)
            for p in properties if p.rep_notify
        ],
        "rpc_stubs": [render_rpc_stub(name, kind) for name, kind in rpcs],
    }


def _err(code: int, message: str, detail: str = "", remediation: Optional[str] = None) -> dict:
    data: dict = {}
    if detail:
        data["detail"] = detail
    if remediation:
        data["remediation"] = remediation
    out: dict = {"error": {"code": code, "message": message}}
    if data:
        out["error"]["data"] = data
    return out


class ReplicationScaffolderHandlers:
    async def on_scaffold(self, params: dict, session=None, ws=None) -> dict:
        class_name = params.get("class_name")
        if not isinstance(class_name, str) or not class_name:
            return _err(ERR_BAD_INPUT, "missing_field", "class_name")
        props_raw = params.get("properties", []) or []
        if not isinstance(props_raw, list):
            return _err(ERR_BAD_INPUT, "properties_must_be_list")
        try:
            props = [
                ReplicatedProperty(
                    name=str(p["name"]),
                    type_decl=str(p["type_decl"]),
                    rep_notify=bool(p.get("rep_notify", False)),
                    condition=str(p.get("condition", "None")),
                )
                for p in props_raw
            ]
        except (KeyError, TypeError) as exc:
            return _err(ERR_BAD_INPUT, "bad_property_shape", str(exc))
        rpcs_raw = params.get("rpcs", []) or []
        if not isinstance(rpcs_raw, list):
            return _err(ERR_BAD_INPUT, "rpcs_must_be_list")
        try:
            rpcs = [(str(r["name"]), str(r.get("kind", "Server"))) for r in rpcs_raw]
        except (KeyError, TypeError) as exc:
            return _err(ERR_BAD_INPUT, "bad_rpc_shape", str(exc))
        try:
            return scaffold_class(class_name, properties=props, rpcs=rpcs)
        except ValueError as exc:
            return _err(ERR_BAD_INPUT, "bad_value", str(exc))


__all__ = [
    "ReplicatedProperty",
    "ReplicationScaffolderHandlers",
    "ALLOWED_CONDS",
    "render_uproperty",
    "render_get_lifetime",
    "render_rep_notify_body",
    "render_rpc_stub",
    "scaffold_class",
    "ERR_BAD_INPUT",
    "ERR_REPL_FAILED",
]
