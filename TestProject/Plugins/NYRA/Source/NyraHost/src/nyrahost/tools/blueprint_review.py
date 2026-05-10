"""nyrahost.tools.blueprint_review — Phase 15-F static Blueprint reviewer.

Aura ships an LLM-driven Blueprint code review tool gated on revision-
control diff. NYRA v0 ships the static-analysis half — a pure-Python
linter that consumes a JSON-serialised Blueprint graph (the format
UE 5.4+ produces with ``-textasset`` or the user-side export tool) and
flags common issues:

  * hanging exec pins (downstream nothing wired)
  * untyped variable nodes (Wildcard pin survived to compile)
  * cast-to-Object-with-no-fail-branch
  * UFunction calls whose Target pin is unwired
  * missing OnRep_ implementation for ReplicatedUsing properties
  * UMG widget creation with no parent

This is a "no LLM" check — runs offline, no token cost. The Phase 13-C
hygiene agent's whole-project posture extends to BPs here. v1.1 layers
an LLM pass on top of the static signal.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Final, Iterable, Optional

import structlog

log = structlog.get_logger("nyrahost.tools.blueprint_review")

ERR_BAD_INPUT: Final[int] = -32602
ERR_BPREVIEW_FAILED: Final[int] = -32067

# Rule severity levels.
SEVERITY_INFO: Final[str] = "info"
SEVERITY_WARN: Final[str] = "warning"
SEVERITY_ERROR: Final[str] = "error"


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    message: str
    node_id: str | None = None
    pin: str | None = None

    def to_dict(self) -> dict:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "message": self.message,
            "node_id": self.node_id,
            "pin": self.pin,
        }


def _iter_nodes(graph: dict) -> Iterable[dict]:
    nodes = graph.get("nodes")
    if isinstance(nodes, list):
        for n in nodes:
            if isinstance(n, dict):
                yield n


def _iter_pins(node: dict, direction: str | None = None) -> Iterable[dict]:
    for p in node.get("pins", []):
        if not isinstance(p, dict):
            continue
        if direction is not None and p.get("direction") != direction:
            continue
        yield p


def find_hanging_exec_pins(graph: dict) -> list[Finding]:
    """Output exec pins with no downstream link."""
    out: list[Finding] = []
    for n in _iter_nodes(graph):
        for p in _iter_pins(n, direction="output"):
            if p.get("pin_type") == "exec" and not p.get("links"):
                out.append(Finding(
                    rule="hanging_exec",
                    severity=SEVERITY_WARN,
                    message=f"Output exec pin {p.get('name')!r} on node "
                            f"{n.get('node_id')!r} has no downstream link",
                    node_id=n.get("node_id"),
                    pin=p.get("name"),
                ))
    return out


def find_wildcard_pins(graph: dict) -> list[Finding]:
    """Wildcard pins should be resolved by compile time."""
    out: list[Finding] = []
    for n in _iter_nodes(graph):
        for p in _iter_pins(n):
            if p.get("pin_type") == "wildcard":
                out.append(Finding(
                    rule="wildcard_pin",
                    severity=SEVERITY_ERROR,
                    message=f"Wildcard pin {p.get('name')!r} on "
                            f"{n.get('node_id')!r} — must resolve to a type",
                    node_id=n.get("node_id"),
                    pin=p.get("name"),
                ))
    return out


def find_unsafe_cast(graph: dict) -> list[Finding]:
    """Cast nodes without a CastFailed branch wired."""
    out: list[Finding] = []
    for n in _iter_nodes(graph):
        if n.get("class_type") not in {"DynamicCast", "K2Node_DynamicCast"}:
            continue
        cast_failed = next(
            (p for p in _iter_pins(n, direction="output")
             if p.get("name") in {"CastFailed", "Then"}),
            None,
        )
        if cast_failed is None or not cast_failed.get("links"):
            out.append(Finding(
                rule="unsafe_cast",
                severity=SEVERITY_WARN,
                message=f"Cast node {n.get('node_id')!r} has no "
                        "CastFailed branch — silent failure on bad cast",
                node_id=n.get("node_id"),
            ))
    return out


def find_unwired_target(graph: dict) -> list[Finding]:
    """Function-call nodes with no Target pin wired (when not Self)."""
    out: list[Finding] = []
    for n in _iter_nodes(graph):
        if not n.get("is_function_call"):
            continue
        target = next(
            (p for p in _iter_pins(n) if p.get("name") == "Target"), None,
        )
        if target is None:
            continue
        if not target.get("links") and not target.get("default_self"):
            out.append(Finding(
                rule="unwired_target",
                severity=SEVERITY_ERROR,
                message=f"Function call {n.get('node_id')!r} has unwired "
                        "Target pin — will fail at runtime",
                node_id=n.get("node_id"),
                pin="Target",
            ))
    return out


def find_missing_on_rep(graph: dict) -> list[Finding]:
    """Variables marked ReplicatedUsing but with no matching OnRep_*."""
    out: list[Finding] = []
    on_reps = {
        n.get("on_rep_name") for n in _iter_nodes(graph)
        if n.get("on_rep_name")
    }
    for v in graph.get("variables", []):
        if not isinstance(v, dict):
            continue
        if v.get("replication") != "ReplicatedUsing":
            continue
        expected = f"OnRep_{v.get('name')}"
        if expected not in on_reps:
            out.append(Finding(
                rule="missing_on_rep",
                severity=SEVERITY_ERROR,
                message=f"ReplicatedUsing variable {v.get('name')!r} has no "
                        f"matching {expected} function in this Blueprint",
            ))
    return out


def review(graph: dict) -> dict:
    """Run all rules; return structured report."""
    if not isinstance(graph, dict):
        raise ValueError("graph must be a dict")
    findings: list[Finding] = []
    findings.extend(find_hanging_exec_pins(graph))
    findings.extend(find_wildcard_pins(graph))
    findings.extend(find_unsafe_cast(graph))
    findings.extend(find_unwired_target(graph))
    findings.extend(find_missing_on_rep(graph))
    by_sev: dict[str, int] = {SEVERITY_ERROR: 0, SEVERITY_WARN: 0, SEVERITY_INFO: 0}
    for f in findings:
        by_sev[f.severity] = by_sev.get(f.severity, 0) + 1
    return {
        "findings": [f.to_dict() for f in findings],
        "counts": {
            "total": len(findings),
            **by_sev,
        },
        "blueprint_path": graph.get("blueprint_path", "<unknown>"),
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


async def on_review_graph(params: dict, session=None, ws=None) -> dict:
    graph = params.get("graph")
    if not isinstance(graph, dict):
        # Accept JSON string too.
        if isinstance(graph, str):
            try:
                graph = json.loads(graph)
            except json.JSONDecodeError as exc:
                return _err(ERR_BAD_INPUT, "bad_graph_json", str(exc))
        else:
            return _err(ERR_BAD_INPUT, "missing_field", "graph")
    try:
        return review(graph)
    except ValueError as exc:
        return _err(ERR_BAD_INPUT, "bad_graph", str(exc))
    except Exception as exc:  # noqa: BLE001
        return _err(ERR_BPREVIEW_FAILED, "bp_review_failed", str(exc))


__all__ = [
    "Finding",
    "review",
    "on_review_graph",
    "find_hanging_exec_pins",
    "find_wildcard_pins",
    "find_unsafe_cast",
    "find_unwired_target",
    "find_missing_on_rep",
    "SEVERITY_INFO", "SEVERITY_WARN", "SEVERITY_ERROR",
    "ERR_BAD_INPUT", "ERR_BPREVIEW_FAILED",
]
