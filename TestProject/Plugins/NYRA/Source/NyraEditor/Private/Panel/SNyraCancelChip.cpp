// SNyraCancelChip.cpp - Phase 18-F per-message Cancel chip.
// Build status: pending_manual_verification.

#include "Panel/SNyraCancelChip.h"
#include "NyraTheme.h"

#include "Process/FNyraSupervisor.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Text/STextBlock.h"
#include "Dom/JsonObject.h"

extern TUniquePtr<class FNyraSupervisor> GNyraSupervisor;

void SNyraCancelChip::Construct(const FArguments& InArgs)
{
    ReqId = InArgs._ReqId.Get();
    OnClickDelegate = InArgs._OnClick;
    ChildSlot
    [
        SNew(SButton)
        .ButtonColorAndOpacity(FNyraTheme::GetDanger())
        .Text(FText::FromString(TEXT("Cancel")))
        .ToolTipText(FText::FromString(TEXT("Stop this in-flight response")))
        .OnClicked(this, &SNyraCancelChip::HandleClick)
    ];
}

FReply SNyraCancelChip::HandleClick()
{
    if (GNyraSupervisor.IsValid() && !ReqId.IsEmpty())
    {
        TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
        Params->SetStringField(TEXT("req_id"), ReqId);
        GNyraSupervisor->SendNotification(TEXT("chat/cancel"), Params);
    }
    OnClickDelegate.ExecuteIfBound(ReqId);
    Invalidate(EInvalidateWidget::Paint);   // WR-08
    return FReply::Handled();
}
