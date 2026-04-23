// =============================================================================
// SNyraComposer.cpp  (Phase 1 Plan 12 -- chat panel streaming integration)
// =============================================================================
//
// Layout:
//   SVerticalBox
//     Slot[AutoHeight]  -- ChipsRow (SHorizontalBox; SNyraAttachmentChip[])
//     Slot[AutoHeight, Padding=4-top]  -- input row
//       SHorizontalBox
//         Slot[FillWidth]   SMultiLineEditableTextBox (hint: Message NYRA (Ctrl+Enter to send))
//         Slot[AutoWidth]   SButton [+] (FDesktopPlatformModule OpenFileDialog)
//         Slot[AutoWidth]   SButton [Send] (HandleSubmitClicked)
//
// Keyboard contract (CD-03):
//   - Ctrl+Enter / Cmd+Enter   -> submit
//   - Enter only               -> newline (default SMultiLineEditableTextBox behaviour)
//
// Attachment picker contract (CD-04):
//   - Filter: "Supported|*.png;*.jpg;*.jpeg;*.webp;*.mp4;*.mov;*.md;*.txt|All Files|*.*"
//   - EFileDialogFlags::Multiple
//   - DisplayName = FPaths::GetCleanFilename(AbsolutePath)
//   - SizeBytes  = IPlatformFile::GetPlatformPhysical().GetStatData(...).FileSize
//
// Submit semantics:
//   - If text trimmed empty AND no attachments -> no-op (prevents stray sends)
//   - Otherwise fire OnSubmit(Text, Attachments) then Clear() the composer
// =============================================================================

#include "Panel/SNyraComposer.h"
#include "Panel/SNyraAttachmentChip.h"

#include "DesktopPlatformModule.h"
#include "IDesktopPlatform.h"

#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SMultiLineEditableTextBox.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Framework/Application/SlateApplication.h"
#include "InputCoreTypes.h"
#include "HAL/PlatformFileManager.h"
#include "GenericPlatform/GenericPlatformFile.h"
#include "Misc/Paths.h"

#define LOCTEXT_NAMESPACE "NyraComposer"

void SNyraComposer::Construct(const FArguments& InArgs)
{
    OnSubmitDelegate = InArgs._OnSubmit;
    ChildSlot
    [
        SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight()
        [
            SAssignNew(ChipsRow, SHorizontalBox)
        ]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 4, 0, 0)
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().FillWidth(1.0f)
            [
                SAssignNew(TextBox, SMultiLineEditableTextBox)
                .HintText(LOCTEXT("Placeholder", "Message NYRA (Ctrl+Enter to send)"))
                .AutoWrapText(true)
                .OnKeyDownHandler(this, &SNyraComposer::HandleKeyDown)
            ]
            + SHorizontalBox::Slot().AutoWidth().Padding(4, 0, 0, 0).VAlign(VAlign_Bottom)
            [
                SNew(SButton)
                .Text(LOCTEXT("Attach", "+"))
                .ToolTipText(LOCTEXT("AttachTip", "Attach file"))
                .OnClicked(this, &SNyraComposer::HandleAttachClicked)
            ]
            + SHorizontalBox::Slot().AutoWidth().Padding(4, 0, 0, 0).VAlign(VAlign_Bottom)
            [
                SNew(SButton)
                .Text(LOCTEXT("Send", "Send"))
                .OnClicked(this, &SNyraComposer::HandleSubmitClicked)
            ]
        ]
    ];
}

void SNyraComposer::Clear()
{
    if (TextBox.IsValid()) TextBox->SetText(FText::GetEmpty());
    Attachments.Empty();
    if (ChipsRow.IsValid()) ChipsRow->ClearChildren();
}

void SNyraComposer::AddAttachment(const FNyraAttachmentRef& Ref)
{
    Attachments.Add(Ref);
    if (ChipsRow.IsValid())
    {
        ChipsRow->AddSlot().AutoWidth().Padding(4, 0)
        [
            SNew(SNyraAttachmentChip)
            .Attachment(Ref)
            .OnRemoved(FOnAttachmentRemoved::CreateRaw(this, &SNyraComposer::HandleRemoveAttachment))
        ];
    }
}

void SNyraComposer::HandleRemoveAttachment(const FNyraAttachmentRef& Ref)
{
    Attachments.RemoveAll([&](const FNyraAttachmentRef& R){ return R.AbsolutePath == Ref.AbsolutePath; });
    // Rebuild the chips row so the visible layout tracks the Attachments array.
    if (ChipsRow.IsValid())
    {
        ChipsRow->ClearChildren();
        const TArray<FNyraAttachmentRef> Snapshot = Attachments;
        Attachments.Empty();
        for (const FNyraAttachmentRef& R : Snapshot)
        {
            AddAttachment(R);
        }
    }
}

FReply SNyraComposer::HandleSubmitClicked()
{
    const FString Text = TextBox.IsValid() ? TextBox->GetText().ToString() : FString();
    if (Text.TrimStartAndEnd().IsEmpty() && Attachments.Num() == 0)
    {
        return FReply::Handled();
    }
    OnSubmitDelegate.ExecuteIfBound(Text, Attachments);
    Clear();
    return FReply::Handled();
}

FReply SNyraComposer::HandleAttachClicked()
{
    IDesktopPlatform* DesktopPlatform = FDesktopPlatformModule::Get();
    if (!DesktopPlatform) return FReply::Handled();
    TArray<FString> OutFilenames;
    const FString FileTypes = TEXT(
        "Supported|*.png;*.jpg;*.jpeg;*.webp;*.mp4;*.mov;*.md;*.txt|"
        "All Files|*.*");
    const bool bOpened = DesktopPlatform->OpenFileDialog(
        /*ParentWindow=*/nullptr,
        TEXT("Attach file"),
        /*DefaultPath=*/FString(),
        /*DefaultFile=*/FString(),
        FileTypes,
        EFileDialogFlags::Multiple,
        OutFilenames);
    if (bOpened)
    {
        for (const FString& Path : OutFilenames)
        {
            FNyraAttachmentRef Ref;
            Ref.AbsolutePath = Path;
            Ref.DisplayName = FPaths::GetCleanFilename(Path);
            const FFileStatData Stat = IPlatformFile::GetPlatformPhysical().GetStatData(*Path);
            Ref.SizeBytes = Stat.FileSize;
            AddAttachment(Ref);
        }
    }
    return FReply::Handled();
}

FReply SNyraComposer::HandleKeyDown(const FGeometry& Geom, const FKeyEvent& InKeyEvent)
{
    // Cmd/Ctrl + Enter submits; plain Enter inserts a newline (default
    // SMultiLineEditableTextBox behaviour when we return Unhandled).
    if (InKeyEvent.GetKey() == EKeys::Enter && (InKeyEvent.IsControlDown() || InKeyEvent.IsCommandDown()))
    {
        HandleSubmitClicked();
        return FReply::Handled();
    }
    return FReply::Unhandled();
}

#undef LOCTEXT_NAMESPACE
