// =============================================================================
// SNyraDownloadModal.cpp  (Phase 1 Plan 13)
// =============================================================================
//
// Implementation notes:
//   - RootContainer is an SBox wrapping an SBorder so the modal can be
//     show/hidden via EVisibility without rebuilding the widget tree.
//   - Percent_Lambda on the SProgressBar reads BytesDone/BytesTotal on
//     every tick; returning an empty TOptional<float> renders as
//     indeterminate, which is the state before the first "downloading"
//     frame lands (BytesTotal == 0).
//   - Status -> StatusText mapping lives in OnProgress. On "error" the
//     remediation string from error.data.remediation (D-11 wire shape) is
//     rendered verbatim. NOTE: Plan 05's D-11 spec says remediation is
//     rendered as Markdown in a red-accent bubble for chat messages; the
//     modal just shows it as plain text -- sufficient for a download
//     failure where the remediation is a single-line "retry" hint.
//   - HandleCancel hides the modal and fires OnCancelled. Python side has
//     no cancel endpoint in Phase 1 -- documented limitation.
//   - BytesText displays "X MB / Y MB" formatted human-readable size.
// =============================================================================

#include "Panel/SNyraDownloadModal.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Notifications/SProgressBar.h"
#include "Styling/AppStyle.h"
#include "Dom/JsonObject.h"

#define LOCTEXT_NAMESPACE "NyraDownloadModal"

void SNyraDownloadModal::Construct(const FArguments& InArgs)
{
    OnCancelledDelegate = InArgs._OnCancelled;
    ChildSlot
    [
        SAssignNew(RootContainer, SBox)
        .Visibility(EVisibility::Collapsed)
        [
            SNew(SBorder)
            .BorderImage(FAppStyle::GetBrush("ToolPanel.GroupBorder"))
            .Padding(FMargin(16))
            [
                SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight()
                [
                    SNew(STextBlock).Text(LOCTEXT("Title", "Downloading Gemma 3 4B (3.16 GB)"))
                        .Font(FAppStyle::GetFontStyle(TEXT("BoldFont")))
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 8, 0, 0)
                [
                    SAssignNew(StatusText, STextBlock).Text(LOCTEXT("Starting", "Starting..."))
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 6, 0, 0)
                [
                    SAssignNew(ProgressBar, SProgressBar).Percent_Lambda([this]() -> TOptional<float>
                    {
                        if (BytesTotal <= 0) return TOptional<float>();
                        return float(BytesDone) / float(BytesTotal);
                    })
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 6, 0, 0)
                [
                    SAssignNew(BytesText, STextBlock).Text(FText::GetEmpty())
                        .ColorAndOpacity(FLinearColor(0.6f, 0.6f, 0.6f))
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 12, 0, 0)
                [
                    SNew(SButton).Text(LOCTEXT("Cancel", "Cancel"))
                        .OnClicked(this, &SNyraDownloadModal::HandleCancel)
                ]
            ]
        ]
    ];
}

void SNyraDownloadModal::Show()
{
    bVisible = true;
    if (RootContainer.IsValid()) RootContainer->SetVisibility(EVisibility::Visible);
}

void SNyraDownloadModal::Hide()
{
    bVisible = false;
    if (RootContainer.IsValid()) RootContainer->SetVisibility(EVisibility::Collapsed);
}

void SNyraDownloadModal::OnProgress(const TSharedPtr<FJsonObject>& Params)
{
    if (!Params.IsValid()) return;
    Show();

    FString Status;
    Params->TryGetStringField(TEXT("status"), Status);
    CurrentStatus = Status;

    double BytesDoneD = 0.0;
    double BytesTotalD = 0.0;
    Params->TryGetNumberField(TEXT("bytes_done"), BytesDoneD);
    Params->TryGetNumberField(TEXT("bytes_total"), BytesTotalD);
    BytesDone = static_cast<int64>(BytesDoneD);
    BytesTotal = static_cast<int64>(BytesTotalD);

    if (Status == TEXT("downloading"))
    {
        const int32 Pct = BytesTotal > 0 ? int32(100.0 * double(BytesDone) / double(BytesTotal)) : 0;
        if (StatusText.IsValid())
        {
            StatusText->SetText(FText::Format(LOCTEXT("Downloading", "Downloading... {0}%"), FText::AsNumber(Pct)));
        }
    }
    else if (Status == TEXT("verifying"))
    {
        if (StatusText.IsValid())
        {
            StatusText->SetText(LOCTEXT("Verifying", "Verifying SHA256..."));
        }
    }
    else if (Status == TEXT("done"))
    {
        if (StatusText.IsValid())
        {
            StatusText->SetText(LOCTEXT("Done", "Done!"));
        }
        // Auto-hide after a short delay in a real app; Phase 1 leaves the
        // modal shown until the user clicks Cancel (which now reads as
        // "Close" since the download completed -- acceptable first-run UX).
    }
    else if (Status == TEXT("error"))
    {
        FString Remediation;
        const TSharedPtr<FJsonObject>* Err = nullptr;
        if (Params->TryGetObjectField(TEXT("error"), Err) && Err && Err->IsValid())
        {
            const TSharedPtr<FJsonObject>* Data = nullptr;
            if ((*Err)->TryGetObjectField(TEXT("data"), Data) && Data && Data->IsValid())
            {
                (*Data)->TryGetStringField(TEXT("remediation"), Remediation);
            }
        }
        if (StatusText.IsValid())
        {
            StatusText->SetText(FText::FromString(TEXT("Error: ") + Remediation));
        }
    }

    if (BytesTotal > 0 && BytesText.IsValid())
    {
        BytesText->SetText(FText::FromString(FString::Printf(
            TEXT("%.1f MB / %.1f MB"),
            double(BytesDone) / (1024.0 * 1024.0),
            double(BytesTotal) / (1024.0 * 1024.0))));
    }
}

FReply SNyraDownloadModal::HandleCancel()
{
    OnCancelledDelegate.ExecuteIfBound();
    Hide();
    return FReply::Handled();
}

#undef LOCTEXT_NAMESPACE
