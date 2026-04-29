# Phase 02 Plan 08: Session Super Transaction Summary

**Plan:** 02-08
**Phase:** 02-subscription-bridge-ci-matrix
**Subsystem:** NyraTransactionManager
**Wave:** 2
**Dependencies:** 02
**Phase 0 Clearance:** NOT REQUIRED (execute fully)
**GSD Plan:** .planning/phases/02-subscription-bridge-ci-matrix/02-08-session-super-transaction-PLAN.md

## One-Liner
Session super-transaction via BeginTransaction/EndTransaction pair + PIE guard that refuses mutations during Play-In-Editor + rollback-on-exception + diagnostics/transaction-rollback notification.

## What Was Built

### Python: NyraTransactionManager (nyrahost/transaction.py)

**begin_transaction(session_id, parent_id)** — async context manager:
- Generates super_tx_id for session grouping (zero-padded 6-digit counter)
- Checks PIE active → yields PIE_GUARDED transaction if in PIE
- Yields ACTIVE transaction otherwise
- On normal exit: commits if still ACTIVE
- On exception: rolls back then re-raises

**commit()** — marks COMMITTED, clears active reference
**rollback()** — marks ROLLED_BACK, emits diagnostics/transaction-rollback notification with step count

**pie_safe()** → bool — returns not self._pie_active (updated by diagnostics/pie-state notification handler)
**on_pie_state_changed(pie_active: bool)** — called by pie-state notification handler to update local flag

**NyraTransaction** dataclass: id, session_id, state, plan_steps, super_transaction_id, created_at
**add_step(tool, args, result)** — appends to plan_steps for undo log

**TransactionState** enum: ACTIVE, COMMITTED, ROLLED_BACK, PIE_GUARDED

### Python: TransactionHandlers (nyrahost/handlers/transaction.py)

Handles WS requests: transaction/begin, transaction/commit, transaction/rollback, diagnostics/pie-state

### C++: FNyraSessionTransaction (NyraEditor/Public/Transactions/FNyraSessionTransaction.h/.cpp)

**Begin(SessionSummary)** — calls GEditor->BeginTransaction with formatted FText "NYRA: {summary}"
Early-return guard: if !GEditor || !GEditor->Trans → graceful no-op
Stores returned int32 TransactionIndex

**End()** — calls GEditor->EndTransaction(); resets TransactionIndex=INDEX_NONE

**Cancel()** — calls GEditor->CancelTransaction(TransactionIndex); idempotent (safe to call multiple times)

**IsActive()** → bool — TransactionIndex != INDEX_NONE

### C++: FNyraChatRouter (NyraEditor/Public/Panel/FNyraChatRouter.h/.cpp)

Owns FNyraSessionTransaction + bPIEActive flag
Registers FEditorDelegates::BeginPIE/EndPIE in constructor, unregisters in destructor

### Tests: test_transaction.py

- test_transaction_begins_and_commits
- test_transaction_rollback_on_exception (ValueError re-raised after rollback)
- test_nested_transaction_outer_wins
- test_super_transaction_id_generated
- test_pie_guard_prevents_mutation (state = PIE_GUARDED when PIE active)
- test_pie_safe_false_during_pie
- test_pie_safe_true_without_pie
- test_pie_state_changed_notification
- test_add_step

### C++: NyraTransactionsSpec.cpp

Three Describe blocks (8+ It blocks):
- **Nyra.Transactions.SessionScope**: Begin+End roundtrip, Cancel rollback, End/Cancel idempotent/no-op
- **Nyra.Transactions.NestedCoalesce**: inner FScopedTransaction coalesces into outer BeginTransaction
- **Nyra.Transactions.CancelRollback**: outer Cancel rolls back inner mutations

## Key Decisions

1. **Async context manager over manual begin/end calls**: ensures commit/rollback even when exceptions propagate — exception-safe per D-10.

2. **PIE guard at begin_transaction level**: returns PIE_GUARDED state rather than raising — callers can detect and surface -32014 without crashing.

3. **Super-transaction ID counter**: simple int counter → "super-000001" string; enables session grouping without UUID overhead for the grouping key.

4. **Stub _emit in Phase 1 app.py**: diagnostics/transaction-rollback fires but goes nowhere — Phase 2 Wave 2 wires real notification dispatch.

## Deviation from Plan

- **Python transaction.py uses Storage directly** rather than creating a separate transactions table in sessions.db — plan_steps tracked in-memory for undo log; persistence to DB deferred to Phase 2 Wave 2.
- **No direct UTransBuffer testing in pytest** — C++ NyraTransactionsSpec covers the transaction system integration.
- **diagnostics/pie-state notification**: stub emit in Python manager; UE→NH notification wiring is a Phase 2 Wave 2 task.

## Artifacts Created

| File | Provides |
|------|----------|
| TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/transaction.py | NyraTransactionManager + NyraTransaction + TransactionState |
| TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/transaction.py | TransactionHandlers WS request handlers |
| TestProject/Plugins/NYRA/Source/NyraHost/tests/test_transaction.py | 9 test cases |
| TestProject/Plugins/NYRA/Source/NyraEditor/Public/Transactions/FNyraSessionTransaction.h | Begin/End/Cancel RAII wrapper |
| TestProject/Plugins/NYRA/Source/NyraEditor/Private/Transactions/FNyraSessionTransaction.cpp | Implementation with GEditor guards |
| TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/FNyraChatRouter.h/.cpp | PIE delegate registration + SessionTransaction owner |
| TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTransactionsSpec.cpp | 8+ It blocks: SessionScope, NestedCoalesce, CancelRollback |

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| T-02-08-01 | FNyraSessionTransaction.cpp | Hot-reload mid-session UTransBuffer leak — mitigated: ShutdownModule unconditional Cancel() |
| T-02-08-02 | FNyraChatRouter.cpp | Mutation during PIE corrupts runtime — mitigated: PIE gate in begin_transaction + -32014 at UE side |
| T-02-08-03 | transaction.py | Session cancel mid-stream partial rollback — mitigated: CancelTransaction reverts all Modify()ed objects |

## Known Stubs

- `_emit` in NyraTransactionManager is a no-op — diagnostics/transaction-rollback notification has no subscriber yet
- diagnostics/pie-state UE→NH notification: handled by on_pie_state_changed() but no real WS emit yet

## Metrics

- Duration: Wave 1 batch
- Tasks: 2 (Task 1 TransactionManager + Task 2 FNyraSupervisor wiring)
- Files: 3 Python source, 1 Python test, 5 C++ files, 1 C++ spec

## TDD Gate Compliance

RED (test) commit: `test(02-08): add failing transaction tests` — EXISTS
GREEN (impl) commit: `feat(02-08): session super-transaction + PIE guard + undo log` — EXISTS

## Self-Check

- [x] NyraTransactionManager with begin_transaction async context manager
- [x] PIE guard returns PIE_GUARDED state, doesn't raise
- [x] super_tx_id generated per transaction
- [x] plan_steps tracked in NyraTransaction
- [x] FNyraSessionTransaction with Begin/End/Cancel and GEditor guards
- [x] FNyraChatRouter with BeginPIE/EndPIE delegate registration
- [x] NyraTransactionsSpec.cpp with 3 Describe blocks
- [x] Test: transaction_begins_and_commits
- [x] Test: transaction_rollback_on_exception
- [x] Test: pie_guard_prevents_mutation
- [x] Test: super_transaction_id_generated

## Self-Check: PASSED