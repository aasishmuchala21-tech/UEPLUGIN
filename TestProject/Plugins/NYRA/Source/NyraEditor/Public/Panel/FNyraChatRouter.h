// FNyraChatRouter.h — Phase 2 router integration into FNyraSupervisor (Plan 02-06).
// Router-owned SessionTransaction + PIE tracking + chat/send forwarding.
// Module-superset discipline: all Phase 1 FNyraSupervisor content preserved verbatim.
#pragma once

#include "CoreMinimal.h"
#include "Transactions/FNyraSessionTransaction.h"
#include "NyraRouter.generated.h"

class FNyraRouter;  // Forward declare Python router

class NYRAEDITOR_API FNyraChatRouter
{
public:
    FNyraChatRouter();
    ~FNyraChatRouter();

    /** True if UE editor is in PIE mode — chat/send must be refused. */
    bool IsPIEActive() const { return bPIEActive; }

    /** Get the session transaction for shutdown safety. */
    FNyraSessionTransaction& GetSessionTransaction() { return SessionTransaction; }

    // PIE delegate handlers (register in constructor, unregister in destructor)
    void OnBeginPIE(bool bIsSimulating);
    void OnEndPIE(bool bIsSimulating);

private:
    FNyraSessionTransaction SessionTransaction;
    bool bPIEActive = false;
    FDelegateHandle BeginPIEHandle;
    FDelegateHandle EndPIEHandle;
};