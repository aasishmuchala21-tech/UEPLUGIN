// SNyraInstructionsTab.h - Phase 11-E Aura-parity Custom Instructions editor.
// Build status: pending_manual_verification.
//
// Multiline text box bound to the per-project Saved/NYRA/instructions.md
// via settings/get-instructions / settings/set-instructions.

#pragma once

#include "CoreMinimal.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SCompoundWidget.h"

class SMultiLineEditableTextBox;

class NYRAEDITOR_API SNyraInstructionsTab : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SNyraInstructionsTab) {}
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);

    void LoadFromHost();   // fire settings/get-instructions
    void SaveToHost();     // fire settings/set-instructions with the buffer

private:
    FReply HandleSave();
    FReply HandleReload();
    void OnTextChanged(const FText& NewText);

    TSharedPtr<SMultiLineEditableTextBox> TextBox;
    FText Buffer;
    bool bDirty = false;
};
