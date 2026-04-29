"""Tests for Safe Mode Permission Gate (Plan 02-09)."""
from __future__ import annotations

import pytest

from nyrahost.safe_mode import (
    NyraPermissionGate,
    PlanPreviewState,
    PlanStep,
    PlanPreview,
)


class TestSafeModeDefaults:
    """Safe mode is ON by default."""

    def test_safe_mode_on_by_default(self):
        gate = NyraPermissionGate()
        assert gate.is_safe_mode() is True

    def test_default_safe_mode_not_disablable(self):
        """In v1, safe mode cannot be disabled (plan-first-by-default per D-07)."""
        gate = NyraPermissionGate()
        # No disable method — safe mode stays on
        assert gate.is_safe_mode() is True


class TestPreviewGeneration:
    """Preview generation + pending state."""

    async def test_generate_preview_creates_pending_plan(self):
        gate = NyraPermissionGate()
        preview = await gate.generate_preview("plan-123", [
            {"tool": "spawn_actor", "args": {"class": "BP_Hero"}, "impact": "Spawn BP_Hero", "risk": "reversible"}
        ])
        assert preview.plan_id == "plan-123"
        assert preview.state == PlanPreviewState.PENDING_APPROVAL
        assert len(preview.steps) == 1
        assert preview.steps[0].tool == "spawn_actor"

    async def test_generate_preview_maps_all_step_fields(self):
        gate = NyraPermissionGate()
        preview = await gate.generate_preview("plan-full", [
            {"tool": "delete_actor", "args": {"name": "Cube"}, "impact": "Delete Cube", "risk": "destructive"}
        ])
        step = preview.steps[0]
        assert step.tool == "delete_actor"
        assert step.args == {"name": "Cube"}
        assert step.risk == "destructive"

    async def test_multiple_previews_tracked_separately(self):
        gate = NyraPermissionGate()
        await gate.generate_preview("plan-a", [{"tool": "a", "args": {}, "impact": "A", "risk": "reversible"}])
        await gate.generate_preview("plan-b", [{"tool": "b", "args": {}, "impact": "B", "risk": "destructive"}])
        assert "plan-a" in gate._previews
        assert "plan-b" in gate._previews


class TestApproveReject:
    """Approve/reject decision handling."""

    async def test_approve_flips_to_approved(self):
        gate = NyraPermissionGate()
        await gate.generate_preview("plan-1", [{"tool": "x", "args": {}, "impact": "X", "risk": "reversible"}])
        result = await gate.approve("plan-1")
        assert result is True
        assert gate._previews["plan-1"].state == PlanPreviewState.APPROVED
        assert gate.is_approved("plan-1") is True

    async def test_reject_flips_to_rejected(self):
        gate = NyraPermissionGate()
        await gate.generate_preview("plan-2", [{"tool": "y", "args": {}, "impact": "Y", "risk": "destructive"}])
        result = await gate.reject("plan-2", reason="Too risky")
        assert result is True
        assert gate._previews["plan-2"].state == PlanPreviewState.REJECTED

    async def test_approve_unknown_plan_returns_false(self):
        gate = NyraPermissionGate()
        result = await gate.approve("nonexistent")
        assert result is False

    async def test_reject_unknown_plan_returns_false(self):
        gate = NyraPermissionGate()
        result = await gate.reject("nonexistent")
        assert result is False


class TestAwaitDecision:
    """Future-based decision waiting."""

    async def test_await_decision_returns_approve_result(self):
        gate = NyraPermissionGate()
        await gate.generate_preview("plan-await", [{"tool": "z", "args": {}, "impact": "Z", "risk": "reversible"}])
        # Simulate approval in background
        import asyncio
        asyncio.create_task(gate.approve("plan-await"))
        decision = await gate.await_decision("plan-await")
        assert decision["decision"] == "approved"

    async def test_await_decision_returns_reject_result(self):
        gate = NyraPermissionGate()
        await gate.generate_preview("plan-reject-await", [{"tool": "w", "args": {}, "impact": "W", "risk": "irreversible"}])
        import asyncio
        asyncio.create_task(gate.reject("plan-reject-await", "user changed mind"))
        decision = await gate.await_decision("plan-reject-await")
        assert decision["decision"] == "rejected"


class TestOnPlanDecision:
    """WS handler integration: plan/decision request."""

    async def test_on_plan_decision_approve_resolves_future(self):
        gate = NyraPermissionGate()
        await gate.generate_preview("plan-d", [{"tool": "p", "args": {}, "impact": "P", "risk": "reversible"}])
        gate.on_plan_decision({"preview_id": "plan-d", "decision": "approve"})
        import asyncio
        await asyncio.sleep(0.05)  # Let the task run
        assert gate.is_approved("plan-d") is True

    async def test_on_plan_decision_reject_resolves_future(self):
        gate = NyraPermissionGate()
        await gate.generate_preview("plan-e", [{"tool": "q", "args": {}, "impact": "Q", "risk": "destructive"}])
        gate.on_plan_decision({"preview_id": "plan-e", "decision": "reject", "reason": "user clicked reject"})
        import asyncio
        await asyncio.sleep(0.05)
        assert gate._previews["plan-e"].state == PlanPreviewState.REJECTED


class TestPlanSteps:
    """PlanStep dataclass field mapping."""

    def test_plan_step_default_risk(self):
        step = PlanStep(tool="stat", args={})
        assert step.risk == "reversible"

    def test_plan_step_all_risks_accepted(self):
        for risk in ["read-only", "reversible", "destructive", "irreversible"]:
            step = PlanStep(tool="x", args={}, risk=risk)
            assert step.risk == risk

    def test_plan_preview_state_enum_values(self):
        assert PlanPreviewState.PENDING_APPROVAL.value == "pending_approval"
        assert PlanPreviewState.APPROVED.value == "approved"
        assert PlanPreviewState.REJECTED.value == "rejected"
        assert PlanPreviewState.EXECUTED.value == "executed"