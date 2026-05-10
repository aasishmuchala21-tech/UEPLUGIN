"""PARITY-06 — Performance Profiling tools (Plan 08-06).

Three MCP surfaces, asymmetric registration (per PATTERNS.md §"PARITY-06"):

    handle_nyra_perf_stat_read       — WS forwarder; mirrors log_tail.py:21-46
    handle_nyra_perf_insights_query  — WS forwarder + path validation;
                                        scope-narrowed per RESEARCH.md A7
                                        when Insights headless export is
                                        unavailable (returns status="unsupported"
                                        with operator remediation).
    PerfExplainHotspotTool           — `_tools` dict entry; composes
                                        KbSearchTool for LOCKED-05 mandatory
                                        citations and T-08-05 graceful degrade
                                        on `no_index_loaded`.

LOCKED-05 (CONTEXT.md): `nyra_perf_explain_hotspot` MUST emit a `citations`
field. The "beats Aura on Performance Profiling" wedge (SC#6) depends on
that field being populated when the KB index is loaded.

T-08-05 (CONTEXT.md): when the KB index is missing, the response MUST set
    citations: []
    citations_status: "no_index_loaded"
    citations_remediation: <verbatim string from KbSearchTool>
NEVER `citations: []` paired with `citations_status: "ok"`.
"""
from __future__ import annotations

import re
from pathlib import Path

import structlog

from nyrahost.tools.base import NyraTool, NyraToolResult
from nyrahost.tools.kb_search import KbSearchTool

log = structlog.get_logger("nyrahost.tools.perf_tools")

__all__ = [
    "PerfExplainHotspotTool",
    "handle_nyra_perf_stat_read",
    "handle_nyra_perf_insights_query",
    "parse_stat_unit_text",
    "MAX_DURATION_MS",
    "VALID_STATS",
]

# Cap mirrors log_tail.MAX_ENTRIES_CAP shape — bound the WS forward window.
MAX_DURATION_MS = 5000
VALID_STATS = frozenset({"unit", "unitgraph", "memory", "gpu"})


# ---------------------------------------------------------------------------
# nyra_perf_stat_read — WS forwarder (mirror log_tail.handle_nyra_output_log_tail)
# ---------------------------------------------------------------------------


async def handle_nyra_perf_stat_read(
    args: dict,
    ws_emit_request,
) -> dict:
    """Forward `stat unit / unitgraph / memory / gpu` console capture to UE.

    Read-only; same shape as `log_tail.handle_nyra_output_log_tail`
    (lines 21-46). UE side handles the actual `stat <name>` console exec
    and tails the printed lines for `duration_ms`, then returns the raw
    output text plus a parsed dict.

    Returns the WS payload verbatim. On invalid args, returns a JSON-RPC
    error envelope (matching NyraToolResult.err shape).
    """
    stat_name = args.get("stat", "unit")
    if stat_name not in VALID_STATS:
        return {
            "error": {
                "code": -32602,
                "message": f"stat must be one of {sorted(VALID_STATS)}",
            }
        }
    try:
        duration_raw = int(args.get("duration_ms", 1000))
    except (TypeError, ValueError):
        return {
            "error": {
                "code": -32602,
                "message": "duration_ms must be an integer (milliseconds)",
            }
        }
    duration_ms = max(0, min(duration_raw, MAX_DURATION_MS))

    result = await ws_emit_request(
        "perf/stat-read",
        {"stat": stat_name, "duration_ms": duration_ms},
    )
    return result


# ---------------------------------------------------------------------------
# nyra_perf_insights_query — WS forwarder + path-validation
# ---------------------------------------------------------------------------


async def handle_nyra_perf_insights_query(
    args: dict,
    ws_emit_request,
) -> dict:
    """Parse a `.utrace` file via `UnrealInsights.exe -ExportCSV`.

    RESEARCH.md A7: if Insights headless export is unavailable on the
    operator's UE version, the UE-side helper returns
    {status: "unsupported", remediation: ...} which we surface verbatim.
    NEVER silent no-op (T-08-05 lesson generalised).

    Path validation (Security V4 — RESEARCH.md §Threat Model):
      - resolve to absolute path
      - reject non-existent files with status="no_trace_loaded"
      - reject paths whose suffix is not `.utrace`

    NOTE: as of v1, `.utrace` parsing is **deferred to v1.1** when
    `UnrealInsights.exe -?` confirms no headless export mode on the
    targeted UE versions. The handler is wired so the v1.1 enablement
    is purely a UE-side change (the WS endpoint exists; stub returns
    status="unsupported" with the operator remediation pointing at
    `stat unit` + `nyra_perf_explain_hotspot` as the working surface).
    """
    trace_path = args.get("trace_path")
    if not isinstance(trace_path, str) or not trace_path.strip():
        return {
            "error": {
                "code": -32602,
                "message": "trace_path required (path to a .utrace file)",
            }
        }

    p = Path(trace_path).resolve()
    if not p.exists():
        return {
            "status": "no_trace_loaded",
            "trace_path": str(p),
            "remediation": (
                f"Trace file not found: {trace_path}. Capture a session "
                "via UE editor `Trace > Recording`, then pass the path "
                "under <ProjectDir>/Saved/Profiling/."
            ),
        }
    if p.suffix.lower() != ".utrace":
        return {
            "error": {
                "code": -32602,
                "message": "trace_path must end with .utrace",
            }
        }

    result = await ws_emit_request(
        "perf/insights-export",
        {
            "trace_path": str(p),
            "output_path": str(p.with_suffix(".csv")),
        },
    )
    return result


# ---------------------------------------------------------------------------
# nyra_perf_explain_hotspot — composes KbSearchTool for LOCKED-05 citations
# ---------------------------------------------------------------------------


# Used inside `_compose_explanation` to avoid KeyError when an LLM passes
# placeholders the heuristic doesn't fill — copied from blueprint_debug.py:107-110.
class _DefaultDict(dict):
    def __missing__(self, key: str) -> str:
        return f"<{key}>"


class PerfExplainHotspotTool(NyraTool):
    """Explain a perf hotspot with citations to Epic UE5 docs.

    Composes Phase 3 `KbSearchTool`. The "beats Aura" claim (SC#6) is that
    Aura's profiling agent has no separate docs RAG — NYRA cites Epic
    docs by file path so users can verify the explanation against
    primary sources.

    LOCKED-05 output schema (mandatory six fields):
        hotspot_label:         str
        hotspot_metric:        str | None
        explanation:           str
        citations:             list[str]
        citations_status:      "ok" | "no_index_loaded"
        citations_remediation: str | None
    """

    name = "nyra_perf_explain_hotspot"
    description = (
        "Explain a UE perf hotspot in plain English with citations to "
        "Epic UE5 docs. Cross-references Phase 3 nyra_kb_search results — "
        "Aura has no docs RAG, so this surface is the 'beats Aura on "
        "Performance Profiling' lever (CONTEXT.md SC#6, LOCKED-05)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "hotspot_label": {
                "type": "string",
                "description": (
                    "Hotspot identifier from a stat read or Insights "
                    "export (e.g. 'DrawIndexedPrimitive', 'StaticMesh "
                    "DrawCalls', 'GameThread Tick')."
                ),
            },
            "hotspot_metric": {
                "type": "string",
                "description": (
                    "Optional context metric the LLM saw (e.g. '12.5 ms', "
                    "'48% gpu'). Carried verbatim into the response so "
                    "downstream UI can show the original measurement next "
                    "to the explanation."
                ),
            },
            "limit": {
                "type": "integer",
                "default": 4,
                "description": "Max citations to return (1..10).",
            },
        },
        "required": ["hotspot_label"],
    }

    def __init__(self) -> None:
        super().__init__()
        # Compose, do not subclass — mirrors kb_search.py:108-159 reuse.
        self._kb = KbSearchTool()

    def execute(self, params: dict) -> NyraToolResult:
        label = params.get("hotspot_label")
        if not isinstance(label, str) or not label.strip():
            return NyraToolResult.err("hotspot_label_required")
        if len(label) > 256:
            return NyraToolResult.err("hotspot_label_too_long_max_256")

        metric = params.get("hotspot_metric")
        if metric is not None and not isinstance(metric, str):
            return NyraToolResult.err("hotspot_metric_must_be_string")

        try:
            limit = max(1, min(10, int(params.get("limit", 4))))
        except (TypeError, ValueError):
            limit = 4

        # Compose a query that biases the KB toward optimisation guidance.
        query = f"{label} performance optimization Unreal Engine 5"
        kb_result = self._kb.execute(
            {"query": query, "limit": limit, "min_score": 0.3}
        )

        if not kb_result.is_ok:
            log.warning(
                "perf_explain_kb_error",
                hotspot_label=label,
                error=kb_result.error,
            )
            return NyraToolResult.err(f"kb_search_failed: {kb_result.error}")

        kb_data = kb_result.data or {}
        kb_status = kb_data.get("status", "ok")

        # T-08-05 — graceful degrade. NEVER silently empty citations.
        if kb_status == "no_index_loaded":
            log.info("perf_explain_no_index", hotspot_label=label)
            return NyraToolResult.ok(
                {
                    "hotspot_label": label,
                    "hotspot_metric": metric,
                    "explanation": (
                        f"Hotspot '{label}' identified. UE5 docs index "
                        "is not loaded on this machine, so the "
                        "explanation is heuristic-only without docs "
                        "citations. Load the index to unlock the "
                        "'beats Aura' citation surface."
                    ),
                    "citations": [],
                    "citations_status": "no_index_loaded",
                    "citations_remediation": kb_data.get(
                        "remediation",
                        "Run nyra_kb_index_build (Phase 3) or download "
                        "the UE5 knowledge index via NYRA settings.",
                    ),
                }
            )

        results = kb_data.get("results", []) or []
        # De-dup citation paths while preserving order — same source file
        # may produce multiple chunks; the citation surface should list
        # each docs path once.
        seen: set[str] = set()
        citations: list[str] = []
        for r in results:
            src = r.get("source_path")
            if isinstance(src, str) and src and src not in seen:
                seen.add(src)
                citations.append(src)

        return NyraToolResult.ok(
            {
                "hotspot_label": label,
                "hotspot_metric": metric,
                "explanation": _compose_explanation(label, results),
                "citations": citations,
                "citations_status": "ok",
                "citations_remediation": None,
            }
        )


def _compose_explanation(label: str, kb_results: list[dict]) -> str:
    """Heuristic 1-2 sentence synthesis from top KB results.

    Per the plan's "Honest acknowledgments" — real LLM-grade rewriting
    happens at the chat layer; this tool's job is to surface citations
    plus a baseline explanation that's better than "see citations."
    """
    parts: list[str] = []
    for r in kb_results[:3]:
        body = r.get("body") or r.get("excerpt") or ""
        body = body.strip()
        if not body:
            continue
        # First sentence — split on `. ` first to avoid breaking on
        # decimals ("0.5 ms"), fall back to the first 200 chars.
        for sep in (". ", ".\n", "\n"):
            if sep in body:
                first = body.split(sep, 1)[0].strip()
                break
        else:
            first = body[:200].strip()
        if first:
            parts.append(first)
    if not parts:
        return f"{label}: see citations for primary-source guidance."
    # Use _DefaultDict-safe formatter shape — no .format() here, so no
    # KeyError exposure; this is plain concatenation.
    return f"{label}: " + ". ".join(parts) + "."


# ---------------------------------------------------------------------------
# stat-line parser — exposed for unit testing the regex without WS
# ---------------------------------------------------------------------------


# `stat unit` lines look like: "Frame: 16.7 ms (60 FPS)" / "Game: 8.2 ms" /
# "Draw: 4.1 ms" / "GPU: 12.5 ms" / "RHIT: 1.2 ms" / "DynRes: 1080p" — the
# regex captures `<bucket>: <ms> ms` (and the optional FPS group on Frame).
_STAT_RE = re.compile(
    r"^\s*(?P<bucket>[A-Za-z][A-Za-z0-9_]*)\s*:\s*"
    r"(?P<ms>\d+(?:\.\d+)?)\s*ms"
    r"(?:\s*\(\s*(?P<fps>\d+(?:\.\d+)?)\s*FPS\s*\))?",
    re.IGNORECASE,
)


def parse_stat_unit_text(text: str) -> dict:
    """Parse multi-line `stat unit` console output to {bucket: ms, ...}.

    Returns:
        Dict mapping bucket name (lowercased) to milliseconds (float).
        Frame line additionally contributes `fps` if present.
        Empty input or no matches → {}. Malformed lines are skipped
        without raising.
    """
    if not isinstance(text, str) or not text:
        return {}
    out: dict[str, float] = {}
    for line in text.splitlines():
        m = _STAT_RE.search(line)
        if not m:
            continue
        bucket = m.group("bucket").lower()
        try:
            out[bucket] = float(m.group("ms"))
        except (TypeError, ValueError):
            continue
        fps = m.group("fps")
        if fps is not None:
            try:
                out["fps"] = float(fps)
            except (TypeError, ValueError):
                pass
    return out
