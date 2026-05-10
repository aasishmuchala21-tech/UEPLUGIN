"""Safe Mode Permission Gate — Phase 2 plan-first preview (Plan 02-09).

Per RESEARCH §4.2 schema:
  - nyra_permission_gate MCP tool registered in mcp_server
  - PreviewHandler tracks pending previews with asyncio.Future
  - plan/decision request resolves futures
  - Safe mode ON by default (CHAT-04); user cannot silently disable

Phase 0 clearance required: live execution after SC#1 verdict.
Implementation is fully functional for testing; live plan-first gate
activates once SC#1 clears.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from enum import Enum
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

    def __init__(self) -> None:
        self._previews: dict[str, PlanPreview] = {}
        self._futures: dict[str, asyncio.Future] = {}
        self._safe_mode_default = True  # CHAT-04: safe-mode is DEFAULT

    def is_safe_mode(self) -> bool:
        """Safe mode is always True in v1 — plan-first-by-default cannot be disabled."""
        return self._safe_mode_default

    async def generate_preview(
        self,
        plan_id: str,
        steps: list[dict],
    ) -> PlanPreview:
        """
        Register a new plan for user approval.

        Creates a Future so the caller can await the user's decision.
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
        self._futures[plan_id] = asyncio.Future()
        log.info("preview_generated", plan_id=plan_id, steps=len(steps))
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
        """
        if plan_id not in self._futures:
            plan_id = str(uuid.uuid4())  # Auto-generate for new preview
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


__all__ = ["NyraPermissionGate", "PlanPreview", "PlanStep", "PlanPreviewState"]