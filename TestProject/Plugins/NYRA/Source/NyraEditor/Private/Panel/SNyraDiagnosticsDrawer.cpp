// =============================================================================
// SNyraDiagnosticsDrawer.cpp  (Phase 1 Plan 13)
// =============================================================================
//
// Implementation notes:
//   - SExpandableArea with InitiallyCollapsed(true) satisfies "collapsed by
//     default" per CONTEXT.md <specifics> + RESEARCH §3.9 table.
//   - RefreshFromDisk reads the log via FFileHelper (see .cpp body) -- full
//     read into memory. For a Phase 1 debug drawer the log
//     is small (structlog JSON lines, rotated daily at midnight) so full
//     read is acceptable. If the file grows beyond comfort bounds a
//     Phase 2 plan can add streaming or a WS `diagnostics/tail` method.
//   - Fallback string "(log file not yet written)" is shown when
//     LoadFileToStringArray returns false (missing file / permissions).
//     This matches the "panel is ALWAYS usable" invariant.
//   - Monospace font: FAppStyle::GetFontStyle("MonospacedText"). Read-only
//     text box so the user can select+copy lines but cannot edit them.
// =============================================================================

#include "Panel/SNyraDiagnosticsDrawer.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SExpandableArea.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SMultiLineEditableTextBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Misc/DateTime.h"
#include "Styling/AppStyle.h"

#define LOCTEXT_NAMESPACE "NyraDiagnosticsDrawer"

FString SNyraDiagnosticsDrawer::LogFilePath()
{
    const FString DateStr = FDateTime::UtcNow().ToString(TEXT("%Y-%m-%d"));
    return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("NYRA"), TEXT("logs"),
                            FString::Printf(TEXT("nyrahost-%s.log"), *DateStr));
}

void SNyraDiagnosticsDrawer::Construct(const FArguments& InArgs)
{
    ChildSlot
    [
        SNew(SExpandableArea)
        .InitiallyCollapsed(true)
        .HeaderContent()
        [
            SNew(STextBlock).Text(LOCTEXT("DiagHeader", "Diagnostics"))
        ]
        .BodyContent()
        [
            SNew(SVerticalBox)
            + SVerticalBox::Slot().AutoHeight()
            [
                SNew(SHorizontalBox)
                + SHorizontalBox::Slot().AutoWidth()
                [
                    SNew(SButton).Text(LOCTEXT("Refresh", "Refresh"))
                        .OnClicked(this, &SNyraDiagnosticsDrawer::HandleRefresh)
                ]
                + SHorizontalBox::Slot().FillWidth(1.0f).VAlign(VAlign_Center).Padding(8, 0)
                [
                    SNew(STextBlock).Text_Lambda([]() { return FText::FromString(LogFilePath()); })
                        .ColorAndOpacity(FLinearColor(0.6f, 0.6f, 0.6f))
                ]
            ]
            + SVerticalBox::Slot().FillHeight(1.0f).MaxHeight(300).Padding(0, 6, 0, 0)
            [
                SAssignNew(TailBox, SMultiLineEditableTextBox)
                .IsReadOnly(true)
                .AutoWrapText(false)
                .Font(FAppStyle::GetFontStyle(TEXT("MonospacedText")))
            ]
        ]
    ];
}

void SNyraDiagnosticsDrawer::RefreshFromDisk()
{
    if (!TailBox.IsValid()) return;
    TArray<FString> Lines;
    if (!FFileHelper::LoadFileToStringArray(Lines, *LogFilePath()))
    {
        // Graceful fallback: log file does not yet exist (fresh install,
        // first editor launch before any structlog output).
        TailBox->SetText(FText::FromString(TEXT("(log file not yet written)")));
        return;
    }
    const int32 Start = FMath::Max(0, Lines.Num() - 100);
    FString Out;
    for (int32 I = Start; I < Lines.Num(); ++I)
    {
        Out += Lines[I] + TEXT("\n");
    }
    TailBox->SetText(FText::FromString(Out));
}

FReply SNyraDiagnosticsDrawer::HandleToggle()
{
    bExpanded = !bExpanded;
    if (bExpanded) RefreshFromDisk();
    return FReply::Handled();
}

FReply SNyraDiagnosticsDrawer::HandleRefresh()
{
    RefreshFromDisk();
    return FReply::Handled();
}

#undef LOCTEXT_NAMESPACE
