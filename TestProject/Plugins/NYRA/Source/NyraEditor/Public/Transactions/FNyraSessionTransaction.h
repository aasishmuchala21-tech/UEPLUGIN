// FNyraSessionTransaction.h — Phase 2 session super-transaction (Plan 02-08).
// Wraps every NYRA session turn in BeginTransaction/EndTransaction.
// Inner FScopedTransaction objects (Phase 4+ tools) coalesce into this outer pair.
// Ctrl+Z rolls back the entire session as one atomic unit.
#pragma once

#include "CoreMinimal.h"
#include "Containers/UnrealString.h"

class NYRAEDITOR_API FNyraSessionTransaction
{
public:
    /** Open a super-transaction with the given summary description. */
    void Begin(const FString& SessionSummary);

    /** Close the super-transaction gracefully (called on chat/stream done:true). */
    void End();

    /** Roll back all mutations in this transaction (called on cancel or error). */
    void Cancel();

    /** True if a transaction is currently open. */
    bool IsActive() const { return TransactionIndex != INDEX_NONE; }

    /** Get the current transaction index (for diagnostics). */
    int32 GetTransactionIndex() const { return TransactionIndex; }

private:
    /** INDEX_NONE when inactive; set by BeginTransaction. */
    int32 TransactionIndex = INDEX_NONE;
};