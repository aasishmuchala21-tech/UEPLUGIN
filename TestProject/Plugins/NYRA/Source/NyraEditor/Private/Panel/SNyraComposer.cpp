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
#include "Panel/SNyraImageDropZone.h"  // Plan 08-04: drag entry point.

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
#include "AssetRegistry/AssetData.h"   // Plan 08-04: FAssetData fields.

#define LOCTEXT_NAMESPACE "NyraComposer"

void SNyraComposer::Construct(const FArguments& InArgs)
{
    OnSubmitDelegate = InArgs._OnSubmit;
    ChildSlot
    [
        SNew(SVerticalBox)
        // Plan 08-04 (PARITY-04): drop zone above the chips row. Receives
        // both Content-Browser asset drops (-> HandleAssetDropped) and
        // Windows Explorer external-file drops (-> HandleImageDropped via
        // the legacy SNyraImageDropZone OnImageDropped path).
        + SVerticalBox::Slot().AutoHeight()
        [
            SNew(SNyraImageDropZone)
            .OnImageDropped(this, &SNyraComposer::HandleImageDropped)
            .OnAssetDropped(this, &SNyraComposer::HandleAssetDropped)
        ]
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
    // Plan 08-04: removal-key strategy. AbsolutePath is empty for Asset
    // kind, so we tie-break on AssetPath when both are empty equally
    // (i.e. two asset chips are distinguished by /Game/... path).
    Attachments.RemoveAll([&](const FNyraAttachmentRef& R)
    {
        if (R.Kind == ENyraAttachmentKind::Asset && Ref.Kind == ENyraAttachmentKind::Asset)
        {
            return R.AssetPath == Ref.AssetPath;
        }
        return R.AbsolutePath == Ref.AbsolutePath;
    });
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

void SNyraComposer::HandleImageDropped(const FString& ImagePath)
{
    // Plan 08-04: external-file (Windows Explorer) drop -> Image chip.
    // Mirrors HandleAttachClicked's per-file ref construction so the
    // rendered chip is indistinguishable from a [+] picker attachment.
    if (ImagePath.IsEmpty()) return;
    FNyraAttachmentRef Ref;
    Ref.Kind = ENyraAttachmentKind::Image;
    Ref.AbsolutePath = ImagePath;
    Ref.DisplayName = FPaths::GetCleanFilename(ImagePath);
    const FFileStatData Stat = IPlatformFile::GetPlatformPhysical().GetStatData(*ImagePath);
    Ref.SizeBytes = Stat.bIsValid ? Stat.FileSize : 0;
    AddAttachment(Ref);
}

void SNyraComposer::HandleAssetDropped(const FAssetData& Asset)
{
    // Plan 08-04 (PARITY-04): Content-Browser drop -> Asset chip.
    // FAssetData::AssetClassPath is the FTopLevelAssetPath introduced in
    // UE 5.1+ (replaces the older AssetClass FName). Its short name is
    // what NyraHost expects for asset_class (e.g. "StaticMesh"). The
    // object path returned by GetObjectPathString() is the canonical
    // /Game/... form (e.g. "/Game/Meshes/SM_Crate.SM_Crate").
    FNyraAttachmentRef Ref;
    Ref.Kind        = ENyraAttachmentKind::Asset;
    Ref.AssetPath   = Asset.GetObjectPathString();
    Ref.AssetClass  = Asset.AssetClassPath.GetAssetName().ToString();
    // DisplayName uses "[<Class>] <Name>" so the existing SNyraAttachmentChip
    // (which renders DisplayName as the chip label and AbsolutePath as the
    // tooltip) shows enough disambiguation at a glance. Asset thumbnails
    // via FAssetThumbnailPool are deferred -- per plan, label-only fallback
    // is acceptable when richer Slate plumbing isn't already in place.
    const FString AssetName = Asset.AssetName.ToString();
    Ref.DisplayName = FString::Printf(TEXT("[%s] %s"),
        Ref.AssetClass.IsEmpty() ? TEXT("Asset") : *Ref.AssetClass,
        *AssetName);
    // AbsolutePath stays empty for Asset kind -- /Game/... isn't a fs path.
    // We mirror AssetPath into AbsolutePath so the chip tooltip (which
    // reads CurrentRef.AbsolutePath verbatim) still surfaces useful info
    // without needing a chip-widget rewrite.
    Ref.AbsolutePath = Ref.AssetPath;
    Ref.SizeBytes = 0;
    AddAttachment(Ref);
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
