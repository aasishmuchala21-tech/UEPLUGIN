// SNyraModeToggle.cpp - Phase 11-E Aura-parity Ask/Plan/Agent toggle.
// Build status: pending_manual_verification.

#include "Panel/SNyraModeToggle.h"

#include "Process/FNyraSupervisor.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Text/STextBlock.h"
#include "Dom/JsonObject.h"

extern TUniquePtr<class FNyraSupervisor> GNyraSupervisor;

namespace
{
    const FLinearColor Dominant(0.02f, 0.02f, 0.03f, 1.0f);
    const FLinearColor Accent(0.776f, 0.749f, 1.0f, 1.0f);
    const FLinearColor TextDim(0.6f, 0.6f, 0.65f, 1.0f);
}

void SNyraModeToggle::Construct(const FArguments& InArgs)
{
    CurrentMode = InArgs._InitialMode.Get();
    OnModeChanged = InArgs._OnModeChanged;

    ChildSlot
    [
        SNew(SHorizontalBox)
        + SHorizontalBox::Slot().AutoWidth().Padding(2)
        [
            SNew(SButton)
            .ButtonColorAndOpacity(this, &SNyraModeToggle::PillTint, FString(TEXT("ask")))
            .Text(FText::FromString(TEXT("Ask")))
            .ToolTipText(FText::FromString(TEXT("Read-only — knowledge tools only, mutations refuse")))
            .OnClicked(this, &SNyraModeToggle::HandleAsk)
        ]
        + SHorizontalBox::Slot().AutoWidth().Padding(2)
        [
            SNew(SButton)
            .ButtonColorAndOpacity(this, &SNyraModeToggle::PillTint, FString(TEXT("plan")))
            .Text(FText::FromString(TEXT("Plan")))
            .ToolTipText(FText::FromString(TEXT("Generate a preview; you Approve before each mutation")))
            .OnClicked(this, &SNyraModeToggle::HandlePlan)
        ]
        + SHorizontalBox::Slot().AutoWidth().Padding(2)
        [
            SNew(SButton)
            .ButtonColorAndOpacity(this, &SNyraModeToggle::PillTint, FString(TEXT("agent")))
            .Text(FText::FromString(TEXT("Agent")))
            .ToolTipText(FText::FromString(TEXT("Auto-execute pre-approved plans; safe-mode still ON")))
            .OnClicked(this, &SNyraModeToggle::HandleAgent)
        ]
    ];
}

FSlateColor SNyraModeToggle::PillTint(const FString& PillMode) const
{
    return PillMode == CurrentMode ? FSlateColor(Accent) : FSlateColor(TextDim);
}

void SNyraModeToggle::SetMode(const FString& Mode)
{
    if (Mode != CurrentMode && (Mode == TEXT("ask") || Mode == TEXT("plan") || Mode == TEXT("agent")))
    {
        CurrentMode = Mode;
        if (GNyraSupervisor.IsValid())
        {
            TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
            Params->SetStringField(TEXT("operating_mode"), CurrentMode);
            GNyraSupervisor->SendRequest(TEXT("session/set-mode"), Params);
        }
        OnModeChanged.ExecuteIfBound(CurrentMode);
        Invalidate(EInvalidateWidget::Paint);   // WR-08
    }
}

FReply SNyraModeToggle::HandleAsk()   { SetMode(TEXT("ask"));   return FReply::Handled(); }
FReply SNyraModeToggle::HandlePlan()  { SetMode(TEXT("plan"));  return FReply::Handled(); }
FReply SNyraModeToggle::HandleAgent() { SetMode(TEXT("agent")); return FReply::Handled(); }
