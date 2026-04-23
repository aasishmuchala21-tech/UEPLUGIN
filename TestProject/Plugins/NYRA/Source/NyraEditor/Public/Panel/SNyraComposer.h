// =============================================================================
// SNyraComposer.h  (Phase 1 Plan 12 -- chat panel streaming integration)
// =============================================================================
//
// Multiline composer + attachment-chip row + [+] attach button + [Send]
// submit button.
//
// Contracts (per CONTEXT CD-03 / CD-04):
//   - SMultiLineEditableTextBox with min 3 / max 12 visible rows (via Slate
//     auto-wrap + natural growing behaviour).
//   - Cmd/Ctrl+Enter submits; plain Enter inserts a newline.
//   - Attachment picker filter: *.png;*.jpg;*.jpeg;*.webp;*.mp4;*.mov;*.md;*.txt
//   - OnSubmit delegate carries (Text, Attachments[]) to the parent panel.
//
// Phase 1 scope:
//   - No drag-and-drop yet (Plan 12b or Phase 2 -- FDesktopPlatform picker
//     is the only attachment path in this plan).
//   - No char-count / token-count meter (Phase 2 polish).
//
// Threading: GameThread-only. The picker opens a native Windows file dialog
// via FDesktopPlatformModule -- that call blocks the GameThread until the
// user picks/cancels, which is standard UE editor UX and matches stock
// "Import..." menu behaviour.
// =============================================================================

#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Panel/NyraMessageModel.h"

class SMultiLineEditableTextBox;
class SHorizontalBox;

/** Fired when the user hits Ctrl/Cmd+Enter OR clicks the Send button. */
DECLARE_DELEGATE_TwoParams(FOnComposerSubmit,
    const FString& /*Text*/,
    const TArray<FNyraAttachmentRef>& /*Attachments*/);

/**
 * Composer row sitting below the SNyraMessageList. Hosts an auto-growing
 * multiline text box + attachment chips + [+] picker + [Send] button.
 */
class NYRAEDITOR_API SNyraComposer : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SNyraComposer) {}
        SLATE_EVENT(FOnComposerSubmit, OnSubmit)
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);

    /** Clear text box + attachments (called after successful submit). */
    void Clear();

    /** Add an attachment to the chip row. Instantiates SNyraAttachmentChip
     *  inside ChipsRow + wires its OnRemoved back to HandleRemoveAttachment. */
    void AddAttachment(const FNyraAttachmentRef& Ref);

private:
    FReply HandleSubmitClicked();
    FReply HandleAttachClicked();
    FReply HandleKeyDown(const FGeometry& Geom, const FKeyEvent& InKeyEvent);
    void HandleRemoveAttachment(const FNyraAttachmentRef& Ref);

    TSharedPtr<SMultiLineEditableTextBox> TextBox;
    TSharedPtr<SHorizontalBox> ChipsRow;
    TArray<FNyraAttachmentRef> Attachments;
    FOnComposerSubmit OnSubmitDelegate;
};
