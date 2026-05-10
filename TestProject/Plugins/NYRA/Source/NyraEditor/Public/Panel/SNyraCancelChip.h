// SNyraCancelChip.h - Phase 18-F per-message Cancel chip.
// Build status: pending_manual_verification.
//
// Rendered next to each in-flight assistant message. Click fires the
// existing chat/cancel WS notification with the req_id of that message.

#pragma once

#include "CoreMinimal.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SCompoundWidget.h"

DECLARE_DELEGATE_OneParam(FOnNyraCancelClick, const FString& /*ReqId*/);

class NYRAEDITOR_API SNyraCancelChip : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SNyraCancelChip) {}
        SLATE_ATTRIBUTE(FString, ReqId)
        SLATE_EVENT(FOnNyraCancelClick, OnClick)
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);

private:
    FReply HandleClick();
    FString ReqId;
    FOnNyraCancelClick OnClickDelegate;
};
