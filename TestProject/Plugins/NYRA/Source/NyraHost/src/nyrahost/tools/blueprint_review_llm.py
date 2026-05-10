"""nyrahost.tools.blueprint_review_llm — Phase 16-D LLM half of BP review.

Phase 15-F shipped the static analyzer (5 rules over a JSON BP graph).
This module is the LLM-composer half — it takes:

  * The static findings (Phase 15-F output)
  * The BP graph JSON
  * An optional diff (per-revision-control hunks)

…and composes a prompt the user's pinned model can answer with a
natural-language review. The agent itself is invocation-only — this
module renders the prompt, returns it, and the chat handler routes
to ClaudeBackend / GemmaBackend like any other chat turn.

We don't call the LLM directly here because:
  1. Routing already lives in NyraRouter / backends/*; adding a
     parallel path would duplicate that policy.
  2. Tests stay hermetic — no token spend during pytest.
"""
from __future__ import annotations

import json
from typing import Final, Optional

import structlog

from nyrahost.tools.blueprint_review import review as static_review

log = structlog.get_logger("nyrahost.tools.blueprint_review_llm")

ERR_BAD_INPUT: Final[int] = -32602
ERR_BPREVIEW_LLM_FAILED: Final[int] = -32069

# Hard caps so a huge BP doesn't blow the WS frame budget.
MAX_GRAPH_BYTES: Final[int] = 64 * 1024
MAX_DIFF_BYTES: Final[int] = 32 * 1024


SYSTEM_PROMPT: Final[str] = """\
You are a senior Unreal Engine engineer reviewing a Blueprint.

You receive:
  * A structured list of static-analysis findings (rule-based)
  * The Blueprint graph in JSON form
  * An optional revision-control diff

Produce a code review with this exact structure:
  1. SUMMARY (one paragraph)
  2. BLOCKERS (rule + node + concrete fix)
  3. WARNINGS (same shape)
  4. STYLE / CONVENTION suggestions
  5. NEXT STEPS the user should run before re-asking

Be concrete. Quote node_id values verbatim. Don't invent UE API
methods you can't cite. If a finding is a false positive, say so and
explain why — don't pad the review.
"""


def render_review_prompt(
    *,
    graph: dict,
    diff: str | None = None,
    extra_context: str = "",
) -> dict:
    """Return {system_prompt, user_prompt, static_findings}.

    The caller hands user_prompt to the chat path with the chosen
    backend. We never block on LLM output here.
    """
    if not isinstance(graph, dict):
        raise ValueError("graph must be a dict")
    graph_json = json.dumps(graph, separators=(",", ":"))
    if len(graph_json.encode("utf-8")) > MAX_GRAPH_BYTES:
        raise ValueError(
            f"BP graph exceeds {MAX_GRAPH_BYTES} bytes; reduce or split before review"
        )
    if diff is not None and len(diff.encode("utf-8")) > MAX_DIFF_BYTES:
        raise ValueError(
            f"diff exceeds {MAX_DIFF_BYTES} bytes; review one hunk at a time"
        )

    findings_report = static_review(graph)
    body_parts = [
        "## Static analyser findings",
        "```json",
        json.dumps(findings_report, indent=2),
        "```",
        "",
        "## Blueprint graph",
        "```json",
        graph_json,
        "```",
    ]
    if diff:
        body_parts.extend([
            "",
            "## Revision-control diff",
            "```",
            diff,
            "```",
        ])
    if extra_context:
        body_parts.extend(["", "## Additional context", extra_context])
    user_prompt = "\n".join(body_parts)
    return {
        "system_prompt": SYSTEM_PROMPT,
        "user_prompt": user_prompt,
        "static_findings": findings_report,
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


async def on_compose_review(params: dict, session=None, ws=None) -> dict:
    graph = params.get("graph")
    if isinstance(graph, str):
        try:
            graph = json.loads(graph)
        except json.JSONDecodeError as exc:
            return _err(ERR_BAD_INPUT, "bad_graph_json", str(exc))
    if not isinstance(graph, dict):
        return _err(ERR_BAD_INPUT, "missing_field", "graph")
    try:
        out = render_review_prompt(
            graph=graph,
            diff=params.get("diff"),
            extra_context=params.get("extra_context", ""),
        )
    except ValueError as exc:
        return _err(ERR_BAD_INPUT, "bad_request", str(exc))
    except Exception as exc:  # noqa: BLE001
        return _err(ERR_BPREVIEW_LLM_FAILED, "compose_failed", str(exc))
    return out


__all__ = [
    "on_compose_review",
    "render_review_prompt",
    "SYSTEM_PROMPT",
    "MAX_GRAPH_BYTES",
    "MAX_DIFF_BYTES",
    "ERR_BAD_INPUT",
    "ERR_BPREVIEW_LLM_FAILED",
]
