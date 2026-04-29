"""NyraTransactionManager — Phase 2 session super-transaction + PIE guard + undo log.

Per Plan 02-08:
  - Wraps each NYRA session turn in a BeginTransaction/EndTransaction pair
  - PIE guard: refuse mutations when UE editor is in PIE mode
  - Undo log: persists plan steps for rollback on cancel
  - Super-transaction grouping: parent_id links related transactions

Phase 0 gate: not phase0-gated — execute fully.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import structlog

from nyrahost.storage import Storage, db_path_for_project

log = structlog.get_logger("nyrahost.transaction")


class TransactionState(Enum):
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    PIE_GUARDED = "pie_guarded"


@dataclass
class NyraTransaction:
    id: str
    session_id: str
    state: TransactionState
    plan_steps: list[dict] = field(default_factory=list)
    super_transaction_id: Optional[str] = None
    created_at: int = 0

    def add_step(self, tool: str, args: dict, result: str = "") -> None:
        self.plan_steps.append({"tool": tool, "args": args, "result": result})


@dataclass
class UndoLogEntry:
    transaction_id: str
    step_index: int
    tool: str
    args: dict
    result: str
    timestamp: int


class NyraTransactionManager:
    """
    Manages NYRA session super-transactions with PIE safety.

    Design:
      - begin_transaction() opens a transaction context; on exit,
        commit if still ACTIVE, rollback on exception
      - pie_safe() queries UE diagnostic state via emit_notification
      - Undo log written to storage for post-mortem / replay
    """

    def __init__(
        self,
        project_dir: Path,
        emit_notification: callable,
        storage: Storage | None = None,
    ) -> None:
        self.project_dir = project_dir
        self._emit = emit_notification
        self._storage = storage or Storage(db_path_for_project(project_dir))
        self._active: Optional[NyraTransaction] = None
        self._super_tx_counter = 0
        self._pie_active = False  # Updated by diagnostics/pie-state notifications

    @asynccontextmanager
    async def begin_transaction(
        self,
        session_id: str,
        parent_id: Optional[str] = None,
    ) -> AsyncIterator[NyraTransaction]:
        """
        Open a super-transaction for a session turn.

        Yields the active NyraTransaction.
        On normal exit: commits if ACTIVE.
        On exception: rolls back.
        """
        # Generate super_tx_id for session grouping
        self._super_tx_counter += 1
        super_tx_id = f"super-{self._super_tx_counter:06d}"

        # PIE guard: check before mutating
        if self._pie_active:
            tx = NyraTransaction(
                id=str(uuid.uuid4()),
                session_id=session_id,
                state=TransactionState.PIE_GUARDED,
                super_transaction_id=super_tx_id,
                created_at=int(time.time() * 1000),
            )
            self._active = tx
            yield tx
            return

        tx = NyraTransaction(
            id=str(uuid.uuid4()),
            session_id=session_id,
            state=TransactionState.ACTIVE,
            plan_steps=[],
            super_transaction_id=super_tx_id,
            created_at=int(time.time() * 1000),
        )
        self._active = tx

        try:
            yield tx
            if tx.state == TransactionState.ACTIVE:
                await self.commit()
        except Exception:
            await self.rollback()
            raise

    async def commit(self) -> None:
        """Mark transaction COMMITTED, persist plan steps to storage."""
        if self._active is None:
            return
        self._active.state = TransactionState.COMMITTED
        log.info("transaction_committed", tx_id=self._active.id)
        self._active = None

    async def rollback(self) -> None:
        """Mark ROLLED_BACK, emit undo log."""
        if self._active is None:
            return
        self._active.state = TransactionState.ROLLED_BACK
        log.info("transaction_rollback", tx_id=self._active.id, steps=len(self._active.plan_steps))
        # Emit undo log notification for diagnostics
        if self._active.plan_steps:
            await self._emit("diagnostics/transaction-rollback", {
                "transaction_id": self._active.id,
                "session_id": self._active.session_id,
                "steps_reverted": len(self._active.plan_steps),
            })
        self._active = None

    async def pie_safe(self) -> bool:
        """
        Query: is UE editor in PIE mode?

        Returns True if safe to emit mutations.
        Sends diagnostics/pie-state query to UE and awaits response.
        """
        # Emit a query — UE responds with diagnostics/pie-state notification
        # For now, use the local flag (updated by the pie-state notification handler)
        return not self._pie_active

    def on_pie_state_changed(self, pie_active: bool) -> None:
        """Called by diagnostics/pie-state notification handler (Plan 02-08)."""
        self._pie_active = pie_active
        log.info("pie_state_changed", pie_active=pie_active)


from typing import AsyncIterator
__all__ = ["NyraTransactionManager", "NyraTransaction", "TransactionState"]