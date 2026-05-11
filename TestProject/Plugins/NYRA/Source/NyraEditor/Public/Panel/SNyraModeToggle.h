// SNyraModeToggle.h - Phase 11-E Aura-parity Ask/Plan/Agent toggle.
// Build status: pending_manual_verification (no UE toolchain).
//
// Three pills; clicking one calls session/set-mode with
// {"operating_mode": "<ask|plan|agent>"}. Default selection is "plan"
// to mirror the CHAT-04 plan-first-by-default behaviour. The toggle is
// orthogonal to the Privacy / Backend mode (handled separately via
// SNyraBackendStatusStrip).

#pragma once

#include "CoreMinimal.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SCompoundWidget.h"

DECLARE_DELEGATE_OneParam(FOnNyraOperatingModeChanged, const FString& /*Mode*/);

class NYRAEDITOR_API SNyraModeToggle : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SNyraModeToggle)
        : _InitialMode(TEXT("plan")) {}
        SLATE_ATTRIBUTE(FString, InitialMode)
        SLATE_EVENT(FOnNyraOperatingModeChanged, OnModeChanged)
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);

    void SetMode(const FString& Mode);
    const FString& GetMode() const { return CurrentMode; }

private:
    FReply HandleAsk();
    FReply HandlePlan();
    FReply HandleAgent();

    FSlateColor PillTint(const FString& PillMode) const;

    FString CurrentMode;
    FOnNyraOperatingModeChanged OnModeChanged;
};
