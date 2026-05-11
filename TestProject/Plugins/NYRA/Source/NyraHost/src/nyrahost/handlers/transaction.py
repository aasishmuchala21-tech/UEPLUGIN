"""Transaction handlers for NyraHost WS server — Plan 02-08."""

from __future__ import annotations

import structlog

from nyrahost.transaction import NyraTransactionManager, PIEActiveError

log = structlog.get_logger("nyrahost.handlers.transaction")


class TransactionHandlers:
    """Handlers for transaction-related WS requests."""

    def __init__(self, tx_manager: NyraTransactionManager) -> None:
        self._tx = tx_manager

    async def on_transaction_begin(self, params: dict) -> dict:
        """Handle transaction/begin request — creates a super-transaction.

        R1.C2 fix from the full-codebase review: use the non-context-manager
        ``NyraTransactionManager.begin()`` entrypoint. The previous
        ``await self._tx.begin_transaction(...)`` would always raise
        TypeError because @asynccontextmanager returns a non-awaitable
        _AsyncGeneratorContextManager. The entire transaction subsystem
        was non-functional.
        """
        session_id = params.get("session_id", "")
        parent_id = params.get("parent_id")
        if not session_id:
            return {"error": {"code": -32602, "message": "missing session_id"}}

        try:
            tx = await self._tx.begin(session_id, parent_id)
        except PIEActiveError as exc:
            return {"error": {"code": -32014, "message": "pie_active", "data": {"detail": str(exc)}}}
        return {
            "transaction_id": tx.id,
            "super_transaction_id": tx.super_transaction_id,
            "state": tx.state.value,
        }

    async def on_transaction_commit(self, params: dict) -> dict:
        """Handle transaction/commit request."""
        await self._tx.commit()
        return {"committed": True}

    async def on_transaction_rollback(self, params: dict) -> dict:
        """Handle transaction/rollback request."""
        await self._tx.rollback()
        return {"rolled_back": True}

    async def on_diagnostics_pie_state(self, params: dict) -> dict:
        """
        Handle diagnostics/pie-state notification from UE.

        Updates the transaction manager's PIE state.
        """
        pie_active = params.get("active", False)
        self._tx.on_pie_state_changed(pie_active)
        return {"pie_active": pie_active}


__all__ = ["TransactionHandlers"]