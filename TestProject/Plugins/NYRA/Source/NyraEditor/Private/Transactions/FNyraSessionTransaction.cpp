// FNyraSessionTransaction.cpp — Phase 2 session super-transaction (Plan 02-08).
#include "Transactions/FNyraSessionTransaction.h"
#include "Editor.h"

void FNyraSessionTransaction::Begin(const FString& SessionSummary)
{
    if (!GEditor || !GEditor->Trans)
    {
        return;  // Graceful no-op outside editor context (commandlet / game)
    }

    if (IsActive())
    {
        return;  // Already open — idempotent guard
    }

    const FText Desc = FText::Format(
        NSLOCTEXT("NyraSessionFmt", "Fmt", "NYRA: {0}"),
        FText::FromString(SessionSummary)
    );

    TransactionIndex = GEditor->BeginTransaction(Desc);
}

void FNyraSessionTransaction::End()
{
    if (!GEditor || !GEditor->Trans || !IsActive())
    {
        return;  // Graceful no-op
    }

    GEditor->EndTransaction();
    TransactionIndex = INDEX_NONE;
}

void FNyraSessionTransaction::Cancel()
{
    if (!GEditor || !GEditor->Trans || !IsActive())
    {
        return;  // Graceful no-op; safe to call multiple times
    }

    GEditor->CancelTransaction(TransactionIndex);
    TransactionIndex = INDEX_NONE;
}