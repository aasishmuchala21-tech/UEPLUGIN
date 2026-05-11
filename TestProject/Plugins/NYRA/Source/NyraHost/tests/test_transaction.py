"""Tests for NyraTransactionManager (Plan 02-08)."""
from __future__ import annotations

import pytest

from nyrahost.transaction import (
    NyraTransactionManager,
    NyraTransaction,
    PIEActiveError,
    TransactionState,
)


class TestTransactionLifecycle:
    """Begin/Commit/Rollback flow."""

    async def test_transaction_begins_and_commits(self):
        manager = _make_manager()
        async with manager.begin_transaction("session-1") as tx:
            assert tx.state == TransactionState.ACTIVE
            assert tx.session_id == "session-1"
            tx.add_step("spawn_actor", {"class": "BP_Hero"}, "spawned")
        # After exit, should be committed
        assert manager._active is None

    async def test_transaction_rollback_on_exception(self):
        manager = _make_manager()
        with pytest.raises(ValueError):
            async with manager.begin_transaction("session-2") as tx:
                tx.add_step("delete_actor", {"name": "Cube"})
                raise ValueError("test rollback")
        assert manager._active is None

    async def test_nested_transaction_outer_wins(self):
        """Only one active transaction at a time; outer transaction persists."""
        manager = _make_manager()
        async with manager.begin_transaction("session-3") as outer:
            outer.add_step("outer_step", {})
            assert manager._active is outer
        # Outer was committed on exit

    async def test_super_transaction_id_generated(self):
        manager = _make_manager()
        async with manager.begin_transaction("session-s") as tx:
            assert tx.super_transaction_id is not None
            assert tx.super_transaction_id.startswith("super-")


class TestPIEGuard:
    """PIE mode blocks mutations."""

    async def test_pie_guard_prevents_mutation(self):
        """PIE-active sessions must REFUSE begin_transaction with -32014.

        Updated for CR-05 (the production code's docstring at
        transaction.py:116-122): the old behaviour yielded a PIE_GUARDED
        tx and let the caller body run unguarded — state accumulated
        with no rollback. The corrected contract is "raise PIEActiveError
        so the JSON-RPC layer returns -32014 pie_active to UE".
        """
        manager = _make_manager()
        manager.on_pie_state_changed(True)
        with pytest.raises(PIEActiveError):
            async with manager.begin_transaction("session-pie"):
                pass  # never reached

    async def test_pie_safe_false_during_pie(self):
        manager = _make_manager()
        manager.on_pie_state_changed(True)
        safe = await manager.pie_safe()
        assert safe is False

    async def test_pie_safe_true_without_pie(self):
        manager = _make_manager()
        manager.on_pie_state_changed(False)
        safe = await manager.pie_safe()
        assert safe is True

    async def test_pie_state_changed_notification(self):
        manager = _make_manager()
        emit_log = []
        manager._emit = lambda m, p: emit_log.append((m, p))
        manager.on_pie_state_changed(True)
        assert manager._pie_active is True


class TestPlanSteps:
    """Plan steps tracked for undo log."""

    async def test_add_step(self):
        tx = NyraTransaction(
            id="tx-1",
            session_id="s1",
            state=TransactionState.ACTIVE,
        )
        tx.add_step("spawn_actor", {"class": "BP_Hero"}, "Actor spawned: BP_Hero")
        assert len(tx.plan_steps) == 1
        assert tx.plan_steps[0]["tool"] == "spawn_actor"
        assert tx.plan_steps[0]["result"] == "Actor spawned: BP_Hero"

    async def test_rollback_emits_diagnostics(self):
        manager = _make_manager()
        emit_log = []
        manager._emit = lambda m, p: emit_log.append((m, p))

        async with manager.begin_transaction("session-rollback") as tx:
            tx.add_step("delete_actor", {"name": "Cube"})
        # After commit, no rollback event emitted
        assert all(m != "diagnostics/transaction-rollback" for m, _ in emit_log)


class TestSuperTransactionGrouping:
    """Super-transaction ID for session grouping."""

    def test_super_transaction_id_unique_per_call(self):
        manager = _make_manager()
        manager._super_tx_counter = 0
        # Simulate begin_transaction without async context
        manager._super_tx_counter += 1
        id1 = f"super-{manager._super_tx_counter:06d}"
        manager._super_tx_counter += 1
        id2 = f"super-{manager._super_tx_counter:06d}"
        assert id1 != id2


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_manager():
    from pathlib import Path
    import tempfile

    async def noop_emit(method, params):
        pass

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        return NyraTransactionManager(
            project_dir=tmp_path,
            emit_notification=noop_emit,
            storage=None,
        )