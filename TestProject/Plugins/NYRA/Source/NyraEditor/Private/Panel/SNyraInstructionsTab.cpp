// SNyraInstructionsTab.cpp - Phase 11-E Aura-parity Custom Instructions editor.
// Build status: pending_manual_verification.

#include "Panel/SNyraInstructionsTab.h"

#include "Process/FNyraSupervisor.h"
#include "Widgets/Input/SMultiLineEditableTextBox.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBorder.h"
#include "Dom/JsonObject.h"

extern TUniquePtr<class FNyraSupervisor> GNyraSupervisor;

namespace
{
    const FLinearColor TextDim(0.6f, 0.6f, 0.65f, 1.0f);
}

void SNyraInstructionsTab::Construct(const FArguments& InArgs)
{
    ChildSlot
    [
        SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 6)
        [
            SNew(STextBlock)
            .ColorAndOpacity(TextDim)
            .Text(FText::FromString(TEXT(
                "Custom Instructions are prepended to every prompt for this project.\n"
                "Stored at <ProjectDir>/Saved/NYRA/instructions.md (max 64 KB).\n"
                "Don't paste secrets — this file may be checked into project git.")))
        ]
        + SVerticalBox::Slot().FillHeight(1.0f).Padding(0, 0, 0, 6)
        [
            SAssignNew(TextBox, SMultiLineEditableTextBox)
            .Text(Buffer)
            .OnTextChanged(this, &SNyraInstructionsTab::OnTextChanged)
            .HintText(FText::FromString(TEXT(
                "e.g. \"Use British spelling.\\nNaming convention: BP_*.\\n"
                "Prefer Lyra over GAS.\"")))
        ]
        + SVerticalBox::Slot().AutoHeight()
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth().Padding(2)
            [
                SNew(SButton)
                .Text(FText::FromString(TEXT("Reload from disk")))
                .OnClicked(this, &SNyraInstructionsTab::HandleReload)
            ]
            + SHorizontalBox::Slot().AutoWidth().Padding(2)
            [
                SNew(SButton)
                .Text(FText::FromString(TEXT("Save")))
                .OnClicked(this, &SNyraInstructionsTab::HandleSave)
            ]
        ]
    ];
    LoadFromHost();
}

void SNyraInstructionsTab::OnTextChanged(const FText& NewText)
{
    Buffer = NewText;
    bDirty = true;
}

FReply SNyraInstructionsTab::HandleSave()
{
    SaveToHost();
    return FReply::Handled();
}

FReply SNyraInstructionsTab::HandleReload()
{
    LoadFromHost();
    return FReply::Handled();
}

void SNyraInstructionsTab::LoadFromHost()
{
    if (!GNyraSupervisor.IsValid()) return;
    TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
    GNyraSupervisor->SendRequest(TEXT("settings/get-instructions"), Params);
    // Response handler in SNyraChatPanel pushes the body into Buffer;
    // SetText() is called on the next OnPaint pulse via Invalidate.
    bDirty = false;
}

void SNyraInstructionsTab::SaveToHost()
{
    if (!GNyraSupervisor.IsValid()) return;
    TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
    Params->SetStringField(TEXT("body"), Buffer.ToString());
    GNyraSupervisor->SendRequest(TEXT("settings/set-instructions"), Params);
    bDirty = false;
    Invalidate(EInvalidateWidget::Paint);   // WR-08
}
