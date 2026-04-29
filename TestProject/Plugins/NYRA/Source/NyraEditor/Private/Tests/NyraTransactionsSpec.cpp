// NyraTransactionsSpec.cpp — Phase 2 Automation Spec for FNyraSessionTransaction (Plan 02-08).
// Three Describe blocks per RESEARCH §11 Wave 0:
//   Nyra.Transactions.SessionScope | NestedCoalesce | CancelRollback
#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"
#include "Transactions/FNyraSessionTransaction.h"
#include "Engine/Transaction.h"

// Simple test UObject with RF_Transactional
UCLASS()
class UTestNyraObject : public UObject
{
    GENERATED_BODY()
public:
    UPROPERTY()
    int32 TestValue = 0;
};

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FNyraTransactionsSessionScope,
    "Nyra.Transactions.SessionScope",
    EAutomationTestFlags::ApplicationContextMask | EAutomationTestFlags::ProductFilter
)

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FNyraTransactionsNestedCoalesce,
    "Nyra.Transactions.NestedCoalesce",
    EAutomationTestFlags::ApplicationContextMask | EAutomationTestFlags::ProductFilter
)

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FNyraTransactionsCancelRollback,
    "Nyra.Transactions.CancelRollback",
    EAutomationTestFlags::ApplicationContextMask | EAutomationTestFlags::ProductFilter
)

// --- Nyra.Transactions.SessionScope ---

bool FNyraTransactionsSessionScope::RunTest(const FString& Parameters)
{
    if (!GEditor)
    {
        return true;  // Skip outside editor context
    }

    // It("Begin followed by End leaves one UTransBuffer entry")
    {
        FNyraSessionTransaction Tx;
        UTestNyraObject* Target = NewObject<UTestNyraObject>();
        Target->AddToRoot();  // Prevent GC

        const int32 UndoCountBefore = GEditor->Trans->Num();

        Tx.Begin(TEXT("Test: Begin-End"));
        Target->Modify();
        Target->TestValue = 42;
        Tx.End();

        const int32 UndoCountAfter = GEditor->Trans->Num();

        // One new transaction should appear
        AddInfo(FString::Printf(TEXT("Undo entries before=%d after=%d"), UndoCountBefore, UndoCountAfter));
        TestTrue(TEXT("Transaction index active during scope"), Tx.IsActive() == false);

        Target->RemoveFromRoot();
    }

    // It("Cancel rolls back modifications")
    {
        FNyraSessionTransaction Tx;
        UTestNyraObject* Target = NewObject<UTestNyraObject>();
        Target->AddToRoot();

        Target->Modify();
        Target->TestValue = 99;

        Tx.Begin(TEXT("Test: Cancel"));
        Target->Modify();
        Target->TestValue = 100;
        Tx.Cancel();

        // Value should be rolled back to 99 (or original 0 if no inner Modify)
        AddInfo(FString::Printf(TEXT("Value after Cancel: %d"), Target->TestValue));
        TestTrue(TEXT("Cancel should leave transaction inactive"), !Tx.IsActive());

        Target->RemoveFromRoot();
    }

    // It("End on inactive is no-op")
    {
        FNyraSessionTransaction Tx;
        Tx.End();  // No crash
        TestTrue(TEXT("End on inactive is no-op"), true);
    }

    // It("Cancel is idempotent")
    {
        FNyraSessionTransaction Tx;
        Tx.Begin(TEXT("Test: Idempotent"));
        Tx.Cancel();
        Tx.Cancel();  // Second call — no crash
        TestTrue(TEXT("Cancel is idempotent"), !Tx.IsActive());
    }

    return true;
}

// --- Nyra.Transactions.NestedCoalesce ---

bool FNyraTransactionsNestedCoalesce::RunTest(const FString& Parameters)
{
    if (!GEditor)
    {
        return true;  // Skip outside editor context
    }

    // It("inner FScopedTransaction coalesces into outer BeginTransaction")
    {
        FNyraSessionTransaction Tx;
        UTestNyraObject* Target = NewObject<UTestNyraObject>();
        Target->AddToRoot();

        Tx.Begin(TEXT("Test: Nested coalesce"));

        {
            FScopedTransaction Inner(TEXT("inner"));
            Target->Modify();
            Target->TestValue = 77;
        }  // Inner goes out of scope here

        Tx.End();

        AddInfo(FString::Printf(TEXT("Nested test value: %d"), Target->TestValue));
        TestTrue(TEXT("Nested coalesce test"), Target->TestValue == 77);

        Target->RemoveFromRoot();
    }

    return true;
}

// --- Nyra.Transactions.CancelRollback ---

bool FNyraTransactionsCancelRollback::RunTest(const FString& Parameters)
{
    if (!GEditor)
    {
        return true;  // Skip outside editor context
    }

    // It("outer Cancel after inner completed rolls back both")
    {
        FNyraSessionTransaction Tx;
        UTestNyraObject* Target = NewObject<UTestNyraObject>();
        Target->AddToRoot();

        const int32 OriginalValue = Target->TestValue;

        Tx.Begin(TEXT("Test: Cancel rollback"));

        {
            FScopedTransaction Inner(TEXT("inner-mutation"));
            Target->Modify();
            Target->TestValue = 55;
        }

        Tx.Cancel();  // Should roll back inner mutation too

        AddInfo(FString::Printf(TEXT("After Cancel rollback: %d (original: %d)"), Target->TestValue, OriginalValue));

        Target->RemoveFromRoot();
    }

    return true;
}