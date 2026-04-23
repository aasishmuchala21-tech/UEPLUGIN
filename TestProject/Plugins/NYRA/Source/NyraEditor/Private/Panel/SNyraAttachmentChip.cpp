// =============================================================================
// SNyraAttachmentChip.cpp  (Phase 1 Plan 12 -- chat panel streaming integration)
// =============================================================================
//
// Chip layout: SBorder (ToolPanel.GroupBorder brush, 6x3 padding) wrapping
// a SHorizontalBox with:
//   - AutoWidth STextBlock(DisplayName) with absolute-path tooltip
//   - AutoWidth SButton([ x ]) firing OnRemoved delegate via FReply
//
// The remove button invokes the OnRemoved delegate with the CurrentRef
// captured at Construct time. The parent SNyraComposer rebuilds its chip
// row from the remaining attachments.
// =============================================================================

#include "Panel/SNyraAttachmentChip.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Styling/AppStyle.h"

#define LOCTEXT_NAMESPACE "NyraAttachmentChip"

void SNyraAttachmentChip::Construct(const FArguments& InArgs)
{
    CurrentRef = InArgs._Attachment.Get();
    OnRemovedDelegate = InArgs._OnRemoved;
    ChildSlot
    [
        SNew(SBorder)
        .BorderImage(FAppStyle::GetBrush("ToolPanel.GroupBorder"))
        .Padding(FMargin(6, 3))
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
            [
                SNew(STextBlock)
                .Text(FText::FromString(CurrentRef.DisplayName))
                .ToolTipText(FText::FromString(CurrentRef.AbsolutePath))
            ]
            + SHorizontalBox::Slot().AutoWidth().Padding(6, 0, 0, 0).VAlign(VAlign_Center)
            [
                SNew(SButton)
                .Text(LOCTEXT("X", "x"))
                .ToolTipText(LOCTEXT("Remove", "Remove attachment"))
                .OnClicked(this, &SNyraAttachmentChip::HandleRemoveClicked)
            ]
        ]
    ];
}

FReply SNyraAttachmentChip::HandleRemoveClicked()
{
    OnRemovedDelegate.ExecuteIfBound(CurrentRef);
    return FReply::Handled();
}

#undef LOCTEXT_NAMESPACE
