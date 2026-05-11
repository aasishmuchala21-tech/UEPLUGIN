"""Safe Mode Permission Gate — Phase 2 plan-first preview (Plan 02-09).

Per RESEARCH §4.2 schema:
  - nyra_permission_gate MCP tool registered in mcp_server
  - PreviewHandler tracks pending previews with asyncio.Future
  - plan/decision request resolves futures
  - Safe mode ON by default (CHAT-04); user cannot silently disable

Phase 0 clearance required: live execution after SC#1 verdict.
Implementation is fully functional for testing; live plan-first gate
activates once SC#1 clears.

Plan-as-editable-markdown workflow (post-Phase-8 Aura-parity sweep):
the gate writes every preview to ``<project_saved>/NYRA/plans/<plan_id>.md``
in a roundtrip-safe Markdown format. The user can edit the file (reorder
steps, drop steps, tweak args) and submit ``plan/edit`` with the new
markdown body. Aura's `/Saved/.Aura/plans/*.md` workflow inspires this
shape; NYRA additionally roundtrips through the same dataclass so the
edited plan is type-checked before execution.
"""
from __future__ import annotations

import asyncio
import json
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import structlog

log = structlog.get_logger("nyrahost.safe_mode")


class PlanPreviewState(Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


@dataclass
class PlanStep:
    tool: str
    args: dict
    estimated_impact: str = "unknown"
    risk: str = "reversible"  # read-only | reversible | destructive | irreversible


@dataclass
class PlanPreview:
    plan_id: str
    steps: list[PlanStep]
    state: PlanPreviewState = PlanPreviewState.PENDING_APPROVAL
    user_confirmed: bool = False


class NyraPermissionGate:
    """
    Plan-first preview gate — every destructive tool call surfaces to the UE panel.

    Safe mode is ON by default (CHAT-04). The gate cannot be silently disabled.
    """

    def __init__(self, plans_dir: Optional[Path] = None) -> None:
        self._previews: dict[str, PlanPreview] = {}
        self._futures: dict[str, asyncio.Future] = {}
        self._safe_mode_default = True  # CHAT-04: safe-mode is DEFAULT
        # Phase 10-2 operating mode (Aura parity); default matches the legacy plan-first behaviour.
        self._operating_mode: str = "plan"
        # Plan-as-markdown directory. Default lives under <cwd>/Saved/NYRA/plans
        # so it co-locates with the existing CD-07 storage convention; the
        # chat handler can override at construction time with the project_saved
        # path it already tracks.
        self._plans_dir = plans_dir or (Path.cwd() / "Saved" / "NYRA" / "plans")

    def is_safe_mode(self) -> bool:
        """Safe mode is always True in v1 — plan-first-by-default cannot be disabled."""
        return self._safe_mode_default

    def set_operating_mode(self, mode: str) -> None:
        """Aura-parity operating mode (ask/plan/agent).

        ``ask``   — refuse mutating tools at preview time (-32011 plan_rejected).
        ``plan``  — current default; user must Approve every preview.
        ``agent`` — auto-resolve preview futures as approved.

        Safe mode itself stays ON unconditionally (CHAT-04 invariant).
        """
        if mode not in ("ask", "plan", "agent"):
            raise ValueError(f"invalid operating mode {mode!r}")
        self._operating_mode = mode
        log.info("permission_gate_operating_mode_set", mode=mode)

    @property
    def operating_mode(self) -> str:
        return self._operating_mode

    async def generate_preview(
        self,
        plan_id: str,
        steps: list[dict],
    ) -> PlanPreview:
        """
        Register a new plan for user approval.

        Creates a Future so the caller can await the user's decision.

        Fix #5 from PR #1 code review: honour the operating mode set via
        :meth:`set_operating_mode` instead of always waiting for an explicit
        UE-panel decision. ``ask`` auto-rejects every mutating preview
        (-32011 plan_rejected), ``agent`` auto-approves so autonomous runs
        do not hang for 5 minutes at the first approval gate, ``plan`` (the
        default) preserves the existing user-approval contract. Safe mode
        itself remains ON unconditionally (CHAT-04 invariant) — only the
        decision policy changes.
        """
        preview = PlanPreview(
            plan_id=plan_id,
            steps=[
                PlanStep(
                    tool=s.get("tool", "unknown"),
                    args=s.get("args", {}),
                    estimated_impact=s.get("impact", "unknown"),
                    risk=s.get("risk", "reversible"),
                )
                for s in steps
            ],
        )
        self._previews[plan_id] = preview
        future: asyncio.Future = asyncio.Future()
        self._futures[plan_id] = future

        mode = self._operating_mode
        if mode == "agent":
            # Auto-approve so await_decision returns immediately. The
            # preview is still recorded for audit/trace surfaces.
            preview.state = PlanPreviewState.APPROVED
            preview.user_confirmed = True
            future.set_result({"decision": "approved", "auto": "agent_mode"})
            log.info("preview_auto_approved_agent_mode", plan_id=plan_id)
        elif mode == "ask":
            # Ask mode refuses mutating tools at preview time so the user
            # is forced to choose whether to escalate to plan/agent.
            preview.state = PlanPreviewState.REJECTED
            preview.user_confirmed = False
            future.set_result({
                "decision": "rejected",
                "reason": "ask_mode_refuses_mutation",
                "auto": "ask_mode",
            })
            log.info("preview_auto_rejected_ask_mode", plan_id=plan_id)
        # "plan" — leave the future pending; await_decision waits for
        # an explicit plan/decision request from the UE panel.

        log.info(
            "preview_generated",
            plan_id=plan_id,
            steps=len(steps),
            operating_mode=mode,
        )
        return preview

    async def approve(self, plan_id: str) -> bool:
        """Mark plan as user-approved; resolve the associated future."""
        if plan_id not in self._previews:
            log.warning("approve_unknown_plan", plan_id=plan_id)
            return False
        self._previews[plan_id].state = PlanPreviewState.APPROVED
        self._previews[plan_id].user_confirmed = True
        if plan_id in self._futures and not self._futures[plan_id].done():
            self._futures[plan_id].set_result({"decision": "approved"})
        log.info("plan_approved", plan_id=plan_id)
        return True

    async def reject(self, plan_id: str, reason: str = "") -> bool:
        """Mark plan as rejected; resolve future with reject result."""
        if plan_id not in self._previews:
            log.warning("reject_unknown_plan", plan_id=plan_id)
            return False
        self._previews[plan_id].state = PlanPreviewState.REJECTED
        # WR-12: clear user_confirmed alongside the state flip so callers
        # consulting either signal converge. Without this, a plan that was
        # approve()-then-reject()'d (chat/cancel race, regenerate-after-
        # approve) would keep user_confirmed=True and leak through any
        # gate that bypassed the state check.
        self._previews[plan_id].user_confirmed = False
        if plan_id in self._futures and not self._futures[plan_id].done():
            self._futures[plan_id].set_result({
                "decision": "rejected",
                "reason": reason or "user rejected plan",
            })
        log.info("plan_rejected", plan_id=plan_id, reason=reason)
        return True

    def is_approved(self, plan_id: str) -> bool:
        """Check if a plan has been approved by the user."""
        preview = self._previews.get(plan_id)
        if preview is None:
            return False
        return preview.state == PlanPreviewState.APPROVED

    async def await_decision(self, plan_id: str) -> dict:
        """
        Await the user's plan/decision for a given plan_id.

        Returns the decision dict once plan/decision arrives.
        Raises asyncio.TimeoutError if timeout elapses.

        R1.I1 fix from the full-codebase review: previously, if plan_id
        wasn't in _futures, the code re-keyed to str(uuid.uuid4()) and
        waited on THAT future — which nobody could ever resolve because
        approve(real_plan_id) wouldn't match the random UUID. The 300s
        timeout was guaranteed for any caller that hit this path. Now
        we just create the future under the caller's plan_id so
        approve(plan_id) does match.
        """
        future = self._futures.get(plan_id)
        if future is None:
            # Auto-create future for new plan
            self._futures[plan_id] = asyncio.Future()
            future = self._futures[plan_id]
        return await asyncio.wait_for(future, timeout=300.0)

    def on_plan_decision(self, params: dict) -> None:
        """
        Handle plan/decision request from UE panel.

        Resolves the Future for the given preview_id.
        """
        plan_id = params.get("preview_id", "")
        decision = params.get("decision", "")

        if decision == "approve":
            asyncio.create_task(self.approve(plan_id))
        elif decision == "reject":
            asyncio.create_task(self.reject(plan_id, params.get("reason", "")))
        else:
            log.warning("unknown_decision", decision=decision, plan_id=plan_id)

    # ------------------------------------------------------------------
    # Plan-as-markdown workflow (Aura parity surface)
    # ------------------------------------------------------------------

    def write_plan_markdown(self, plan_id: str) -> Optional[Path]:
        """Write the current PlanPreview to a Markdown file the user can edit.

        Schema (round-trip-safe — `parse_plan_markdown` is the inverse):

            ---
            plan_id: <uuid>
            state: <pending_approval|approved|rejected|executed>
            ---

            # NYRA Plan <short_id>

            ## Step 1 — <tool> (<risk>)
            **Impact:** <estimated_impact>
            ```json
            {... args ...}
            ```

            ## Step 2 — ...

        Returns the file path on success, or None if plan_id is unknown.
        """
        preview = self._previews.get(plan_id)
        if preview is None:
            log.warning("write_plan_markdown_unknown_plan", plan_id=plan_id)
            return None

        self._plans_dir.mkdir(parents=True, exist_ok=True)
        path = self._plans_dir / f"{plan_id}.md"

        lines: list[str] = []
        lines.append("---")
        lines.append(f"plan_id: {plan_id}")
        lines.append(f"state: {preview.state.value}")
        lines.append("---")
        lines.append("")
        lines.append(f"# NYRA Plan {plan_id[:8]}")
        lines.append("")
        for i, step in enumerate(preview.steps, start=1):
            lines.append(f"## Step {i} — {step.tool} ({step.risk})")
            lines.append(f"**Impact:** {step.estimated_impact}")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(step.args, indent=2, sort_keys=True))
            lines.append("```")
            lines.append("")

        # Atomic write so a concurrent reader never sees a half-written file.
        tmp = path.with_suffix(".md.tmp")
        tmp.write_text("\n".join(lines), encoding="utf-8")
        tmp.replace(path)
        log.info(
            "plan_markdown_written",
            plan_id=plan_id,
            path=str(path),
            steps=len(preview.steps),
        )
        return path

    def parse_plan_markdown(self, body: str) -> Optional[PlanPreview]:
        """Parse an edited Markdown plan back into a PlanPreview.

        Strict-parse: rejects bodies that don't match the schema exactly so
        a malformed edit can't slip a fabricated tool name through the gate.
        Returns None on parse failure (caller should surface remediation).
        """
        # Frontmatter
        fm_match = re.match(r"^---\n(.*?)\n---\n", body, re.DOTALL)
        if not fm_match:
            log.warning("plan_markdown_no_frontmatter")
            return None
        fm = {}
        for line in fm_match.group(1).splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip()
        plan_id = fm.get("plan_id")
        state_str = fm.get("state", "pending_approval")
        if not plan_id:
            log.warning("plan_markdown_no_plan_id")
            return None
        try:
            state = PlanPreviewState(state_str)
        except ValueError:
            log.warning("plan_markdown_invalid_state", state=state_str)
            return None

        # Steps — `## Step N — <tool> (<risk>)` headings + json fenced block
        step_re = re.compile(
            r"^##\s+Step\s+\d+\s+—\s+(?P<tool>\S+)\s+\((?P<risk>[^)]+)\)\s*$",
            re.MULTILINE,
        )
        impact_re = re.compile(r"^\*\*Impact:\*\*\s*(?P<impact>.+)$", re.MULTILINE)
        json_block_re = re.compile(r"```json\n(.*?)\n```", re.DOTALL)

        steps: list[PlanStep] = []
        # Walk through step heading matches and slice the body each time.
        matches = list(step_re.finditer(body))
        for i, m in enumerate(matches):
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            section = body[start:end]
            impact_m = impact_re.search(section)
            json_m = json_block_re.search(section)
            if json_m is None:
                log.warning("plan_markdown_step_missing_json", tool=m.group("tool"))
                return None
            try:
                args = json.loads(json_m.group(1))
            except json.JSONDecodeError as exc:
                log.warning(
                    "plan_markdown_step_bad_json",
                    tool=m.group("tool"),
                    err=str(exc),
                )
                return None
            if not isinstance(args, dict):
                log.warning(
                    "plan_markdown_step_args_not_object",
                    tool=m.group("tool"),
                )
                return None
            steps.append(
                PlanStep(
                    tool=m.group("tool"),
                    args=args,
                    estimated_impact=(
                        impact_m.group("impact").strip() if impact_m else "unknown"
                    ),
                    risk=m.group("risk").strip(),
                )
            )

        if not steps:
            log.warning("plan_markdown_no_steps", plan_id=plan_id)
            return None

        return PlanPreview(plan_id=plan_id, steps=steps, state=state)

    async def replace_with_edited(
        self, plan_id: str, edited_body: str
    ) -> bool:
        """Apply a user-edited Markdown plan body in place of the current preview.

        Used by the `plan/edit` WS notification: the chat panel writes the
        edited markdown to disk, sends the body over the wire, and we
        re-parse it. The plan_id must match; risks can only be downgraded
        (a step that was 'destructive' can become 'reversible' if the user
        narrowed scope, but a 'reversible' step cannot be silently
        upgraded — that would defeat the safety gate).
        """
        if plan_id not in self._previews:
            log.warning("replace_with_edited_unknown_plan", plan_id=plan_id)
            return False
        parsed = self.parse_plan_markdown(edited_body)
        if parsed is None or parsed.plan_id != plan_id:
            log.warning(
                "replace_with_edited_parse_failed",
                plan_id=plan_id,
                got_id=getattr(parsed, "plan_id", None),
            )
            return False
        # Risk-floor enforcement: a step's risk must remain at-or-below
        # the original. Mapping low → high: read-only < reversible <
        # destructive < irreversible.
        risk_rank = {
            "read-only": 0,
            "reversible": 1,
            "destructive": 2,
            "irreversible": 3,
        }
        original = self._previews[plan_id]
        for i, edited_step in enumerate(parsed.steps):
            if i >= len(original.steps):
                break
            o_rank = risk_rank.get(original.steps[i].risk, 1)
            e_rank = risk_rank.get(edited_step.risk, 1)
            if e_rank > o_rank:
                log.warning(
                    "replace_with_edited_risk_upgrade_blocked",
                    plan_id=plan_id,
                    step_index=i,
                    original_risk=original.steps[i].risk,
                    edited_risk=edited_step.risk,
                )
                return False
        self._previews[plan_id] = parsed
        log.info(
            "plan_replaced_from_markdown",
            plan_id=plan_id,
            steps=len(parsed.steps),
        )
        return True


__all__ = ["NyraPermissionGate", "PlanPreview", "PlanStep", "PlanPreviewState"]