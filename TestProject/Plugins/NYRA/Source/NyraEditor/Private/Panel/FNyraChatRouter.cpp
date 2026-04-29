// FNyraChatRouter.cpp — Phase 2 router integration into FNyraSupervisor (Plan 02-06).
#include "Panel/FNyraChatRouter.h"
#include "Editor/EditorEngine.h"
#include "HAL/IPlatformFileModule.h"

// Stub implementation — Python NyraRouter is the primary implementation.
// This C++ class manages the UE-side transaction lifecycle and PIE tracking.
FNyraChatRouter::FNyraChatRouter()
{
    if (GEditor)
    {
        BeginPIEHandle = FEditorDelegates::BeginPIE.AddRaw(
            this, &FNyraChatRouter::OnBeginPIE
        );
        EndPIEHandle = FEditorDelegates::EndPIE.AddRaw(
            this, &FNyraChatRouter::OnEndPIE
        );
    }
}

FNyraChatRouter::~FNyraChatRouter()
{
    if (GEditor)
    {
        FEditorDelegates::BeginPIE.Remove(BeginPIEHandle);
        FEditorDelegates::EndPIE.Remove(EndPIEHandle);
    }
}

void FNyraChatRouter::OnBeginPIE(bool bIsSimulating)
{
    bPIEActive = true;
    // Notify NyraHost of PIE state change via diagnostics/pie-state notification
    // (wired in FNyraSupervisor::OnBeginPIE which calls WsClient->SendNotification)
}

void FNyraChatRouter::OnEndPIE(bool bIsSimulating)
{
    bPIEActive = false;
}