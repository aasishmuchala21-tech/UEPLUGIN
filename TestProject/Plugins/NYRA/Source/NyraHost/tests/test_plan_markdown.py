"""Plan-as-editable-markdown roundtrip tests (Aura-parity sweep)."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from nyrahost.safe_mode import (
    NyraPermissionGate,
    PlanPreview,
    PlanPreviewState,
    PlanStep,
)


@pytest.fixture
def gate(tmp_path: Path) -> NyraPermissionGate:
    return NyraPermissionGate(plans_dir=tmp_path)


def _seed_preview(gate: NyraPermissionGate, plan_id: str = "abc12345") -> None:
    asyncio.get_event_loop().run_until_complete(
        gate.generate_preview(
            plan_id,
            [
                {
                    "tool": "nyra_actor_spawn",
                    "args": {"class_name": "AStaticMeshActor", "x": 10, "y": 0, "z": 0},
                    "impact": "spawn one StaticMeshActor at origin",
                    "risk": "reversible",
                },
                {
                    "tool": "nyra_material_set_param",
                    "args": {"asset_path": "/Game/M_Hero", "param": "Metallic", "value": 0.5},
                    "impact": "tune material",
                    "risk": "reversible",
                },
            ],
        )
    )


class TestWriteMarkdown:
    @pytest.mark.asyncio
    async def test_writes_file_with_frontmatter_and_steps(
        self, gate: NyraPermissionGate, tmp_path: Path
    ):
        await gate.generate_preview(
            "plan-001",
            [{"tool": "nyra_actor_spawn", "args": {"x": 1}, "risk": "reversible"}],
        )
        path = gate.write_plan_markdown("plan-001")
        assert path is not None
        assert path == tmp_path / "plan-001.md"
        body = path.read_text(encoding="utf-8")
        assert "---" in body
        assert "plan_id: plan-001" in body
        assert "## Step 1 — nyra_actor_spawn (reversible)" in body
        assert "```json" in body

    @pytest.mark.asyncio
    async def test_unknown_plan_returns_none(self, gate: NyraPermissionGate):
        assert gate.write_plan_markdown("does-not-exist") is None

    @pytest.mark.asyncio
    async def test_atomic_write_uses_tmp(
        self, gate: NyraPermissionGate, tmp_path: Path
    ):
        await gate.generate_preview(
            "plan-atomic",
            [{"tool": "nyra_actor_spawn", "args": {}, "risk": "reversible"}],
        )
        gate.write_plan_markdown("plan-atomic")
        # tmp file should not exist after rename
        assert not (tmp_path / "plan-atomic.md.tmp").exists()
        assert (tmp_path / "plan-atomic.md").exists()


class TestParseMarkdown:
    def test_roundtrips_through_write_then_parse(
        self, gate: NyraPermissionGate
    ):
        async def _go():
            await gate.generate_preview(
                "rt-001",
                [
                    {
                        "tool": "nyra_actor_spawn",
                        "args": {"class_name": "AStaticMeshActor"},
                        "risk": "reversible",
                    },
                    {
                        "tool": "nyra_material_set_param",
                        "args": {"param": "Metallic", "value": 0.5},
                        "impact": "tune material",
                        "risk": "reversible",
                    },
                ],
            )
            path = gate.write_plan_markdown("rt-001")
            body = path.read_text(encoding="utf-8")
            parsed = gate.parse_plan_markdown(body)
            return parsed

        # Python 3.12+ removed the implicit thread event loop;
        # asyncio.get_event_loop() raises RuntimeError. asyncio.run
        # creates and tears down its own loop.
        parsed = asyncio.run(_go())
        assert parsed is not None
        assert parsed.plan_id == "rt-001"
        assert len(parsed.steps) == 2
        assert parsed.steps[0].tool == "nyra_actor_spawn"
        assert parsed.steps[0].args == {"class_name": "AStaticMeshActor"}
        assert parsed.steps[1].tool == "nyra_material_set_param"
        assert parsed.steps[1].estimated_impact == "tune material"

    def test_no_frontmatter_returns_none(self, gate: NyraPermissionGate):
        body = "# Plan\n\n## Step 1 — foo (reversible)\n```json\n{}\n```\n"
        assert gate.parse_plan_markdown(body) is None

    def test_missing_json_block_returns_none(self, gate: NyraPermissionGate):
        body = (
            "---\nplan_id: x\nstate: pending_approval\n---\n\n"
            "# NYRA Plan x\n\n## Step 1 — foo (reversible)\n**Impact:** none\n"
        )
        assert gate.parse_plan_markdown(body) is None

    def test_malformed_json_returns_none(self, gate: NyraPermissionGate):
        body = (
            "---\nplan_id: x\nstate: pending_approval\n---\n\n"
            "## Step 1 — foo (reversible)\n```json\nNOT JSON\n```\n"
        )
        assert gate.parse_plan_markdown(body) is None

    def test_args_must_be_object(self, gate: NyraPermissionGate):
        body = (
            "---\nplan_id: x\nstate: pending_approval\n---\n\n"
            "## Step 1 — foo (reversible)\n```json\n[1, 2, 3]\n```\n"
        )
        assert gate.parse_plan_markdown(body) is None

    def test_zero_steps_returns_none(self, gate: NyraPermissionGate):
        body = "---\nplan_id: x\nstate: pending_approval\n---\n\n# NYRA Plan x\n"
        assert gate.parse_plan_markdown(body) is None


class TestReplaceWithEdited:
    @pytest.mark.asyncio
    async def test_drops_step_succeeds(self, gate: NyraPermissionGate):
        await gate.generate_preview(
            "drop-001",
            [
                {"tool": "a", "args": {}, "risk": "reversible"},
                {"tool": "b", "args": {}, "risk": "reversible"},
            ],
        )
        path = gate.write_plan_markdown("drop-001")
        body = path.read_text(encoding="utf-8")
        # Drop step 2 by truncating after the first json block
        edited = body.split("## Step 2")[0].rstrip() + "\n"
        ok = await gate.replace_with_edited("drop-001", edited)
        assert ok is True
        assert len(gate._previews["drop-001"].steps) == 1
        assert gate._previews["drop-001"].steps[0].tool == "a"

    @pytest.mark.asyncio
    async def test_risk_upgrade_rejected(self, gate: NyraPermissionGate):
        await gate.generate_preview(
            "risk-001",
            [{"tool": "a", "args": {}, "risk": "reversible"}],
        )
        edited = (
            "---\nplan_id: risk-001\nstate: pending_approval\n---\n\n"
            "## Step 1 — a (irreversible)\n```json\n{}\n```\n"
        )
        ok = await gate.replace_with_edited("risk-001", edited)
        assert ok is False
        # Original preserved
        assert gate._previews["risk-001"].steps[0].risk == "reversible"

    @pytest.mark.asyncio
    async def test_risk_downgrade_accepted(self, gate: NyraPermissionGate):
        await gate.generate_preview(
            "downgrade-001",
            [{"tool": "a", "args": {}, "risk": "destructive"}],
        )
        edited = (
            "---\nplan_id: downgrade-001\nstate: pending_approval\n---\n\n"
            "## Step 1 — a (reversible)\n```json\n{}\n```\n"
        )
        ok = await gate.replace_with_edited("downgrade-001", edited)
        assert ok is True
        assert gate._previews["downgrade-001"].steps[0].risk == "reversible"

    @pytest.mark.asyncio
    async def test_unknown_plan_returns_false(self, gate: NyraPermissionGate):
        ok = await gate.replace_with_edited("missing", "---\nplan_id: missing\n---\n")
        assert ok is False

    @pytest.mark.asyncio
    async def test_plan_id_mismatch_rejected(self, gate: NyraPermissionGate):
        await gate.generate_preview(
            "real",
            [{"tool": "a", "args": {}, "risk": "reversible"}],
        )
        edited = (
            "---\nplan_id: someone-else\nstate: pending_approval\n---\n\n"
            "## Step 1 — a (reversible)\n```json\n{}\n```\n"
        )
        ok = await gate.replace_with_edited("real", edited)
        assert ok is False
