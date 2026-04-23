// =============================================================================
// SNyraAttachmentChip.h  (Phase 1 Plan 12 -- chat panel streaming integration)
// =============================================================================
//
// Renders one attachment row above the composer. Displays filename + a small
// [x] remove button that fires the OnRemoved delegate with the FNyraAttachmentRef
// so the parent SNyraComposer can remove the chip from its internal array.
//
// VALIDATION row 1-04-04 (Nyra.Panel.AttachmentChip) targets this widget.
// CD-04 (attachments drop zone + [+] picker) sources the attachment; Phase 1
// forwards paths only -- no upload.
// =============================================================================

#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Panel/NyraMessageModel.h"

/** Fires when the user clicks the [x] remove button. */
DECLARE_DELEGATE_OneParam(FOnAttachmentRemoved, const FNyraAttachmentRef& /*Ref*/);

/**
 * One attachment row above the composer (filename + [x] button).
 * Constructed by SNyraComposer::AddAttachment.
 */
class NYRAEDITOR_API SNyraAttachmentChip : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SNyraAttachmentChip) {}
        SLATE_ATTRIBUTE(FNyraAttachmentRef, Attachment)
        SLATE_EVENT(FOnAttachmentRemoved, OnRemoved)
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);

private:
    FReply HandleRemoveClicked();

    FNyraAttachmentRef CurrentRef;
    FOnAttachmentRemoved OnRemovedDelegate;
};
