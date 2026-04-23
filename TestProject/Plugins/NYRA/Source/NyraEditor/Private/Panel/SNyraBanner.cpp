// =============================================================================
// SNyraBanner.cpp  (Phase 1 Plan 13)
// =============================================================================
//
// Implementation notes:
//   - CurrentKind == Hidden -> SBorder collapsed via EVisibility::Collapsed,
//     so an unused banner costs zero layout rows.
//   - ColorForKind maps ENyraBannerKind to a semi-opaque linear colour bound
//     through BorderBackgroundColor_Lambda so kind-swaps repaint without
//     rebuilding the widget tree.
//   - Indeterminate SProgressBar (no Percent binding) is inserted ONLY for
//     the Info kind -- it communicates "something is happening" during
//     bootstrap without a meaningful percentage to display.
//   - Buttons are appended to the row ONLY when their delegate is bound,
//     so Info/Warning banners render message-only while Error banners get
//     the [Restart] + [Open log] pair (wired via the parent panel).
// =============================================================================

#include "Panel/SNyraBanner.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Notifications/SProgressBar.h"
#include "Styling/AppStyle.h"
#include "Styling/CoreStyle.h"

#define LOCTEXT_NAMESPACE "NyraBanner"

static FLinearColor ColorForKind(ENyraBannerKind K)
{
    switch (K)
    {
    case ENyraBannerKind::Info:    return FLinearColor(0.25f, 0.40f, 0.75f, 0.95f);   // blue-accent
    case ENyraBannerKind::Warning: return FLinearColor(0.75f, 0.55f, 0.15f, 0.95f);   // yellow-accent
    case ENyraBannerKind::Error:   return FLinearColor(0.80f, 0.25f, 0.25f, 0.95f);   // red-accent
    default:                       return FLinearColor::Transparent;
    }
}

void SNyraBanner::Construct(const FArguments& InArgs)
{
    ChildSlot
    [
        SAssignNew(RootBorder, SBorder)
        .Visibility(EVisibility::Collapsed)
        .BorderImage(FAppStyle::GetBrush("ToolPanel.GroupBorder"))
        .BorderBackgroundColor_Lambda([this]() { return ColorForKind(CurrentKind); })
        .Padding(FMargin(8))
        [
            SAssignNew(Row, SHorizontalBox)
        ]
    ];
}

void SNyraBanner::SetState(ENyraBannerKind Kind, const FText& Message)
{
    SetState(Kind, Message, FOnBannerRestartClicked(), FOnBannerOpenLogClicked());
}

void SNyraBanner::SetState(ENyraBannerKind Kind, const FText& Message,
                            const FOnBannerRestartClicked& RestartHandler,
                            const FOnBannerOpenLogClicked& OpenLogHandler)
{
    CurrentKind = Kind;
    RestartDelegate = RestartHandler;
    OpenLogDelegate = OpenLogHandler;

    if (RootBorder.IsValid())
    {
        RootBorder->SetVisibility(Kind == ENyraBannerKind::Hidden ? EVisibility::Collapsed : EVisibility::Visible);
    }

    if (!Row.IsValid()) return;
    Row->ClearChildren();

    // Indeterminate SProgressBar (no Percent binding) for the Info kind only.
    if (Kind == ENyraBannerKind::Info)
    {
        Row->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 8, 0)
        [
            SNew(SBox).WidthOverride(80).HeightOverride(6)
            [
                SNew(SProgressBar)   // indeterminate: no Percent binding
            ]
        ];
    }

    Row->AddSlot().FillWidth(1.0f).VAlign(VAlign_Center)
    [
        SNew(STextBlock).Text(Message).ColorAndOpacity(FLinearColor::White).AutoWrapText(true)
    ];

    if (RestartDelegate.IsBound())
    {
        Row->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(8, 0, 0, 0)
        [
            SNew(SButton).Text(LOCTEXT("Restart", "Restart"))
                .OnClicked(this, &SNyraBanner::HandleRestart)
        ];
    }
    if (OpenLogDelegate.IsBound())
    {
        Row->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(8, 0, 0, 0)
        [
            SNew(SButton).Text(LOCTEXT("OpenLog", "Open log"))
                .OnClicked(this, &SNyraBanner::HandleOpenLog)
        ];
    }
}

void SNyraBanner::Hide()
{
    CurrentKind = ENyraBannerKind::Hidden;
    if (RootBorder.IsValid())
    {
        RootBorder->SetVisibility(EVisibility::Collapsed);
    }
}

FReply SNyraBanner::HandleRestart()
{
    RestartDelegate.ExecuteIfBound();
    return FReply::Handled();
}

FReply SNyraBanner::HandleOpenLog()
{
    OpenLogDelegate.ExecuteIfBound();
    return FReply::Handled();
}

#undef LOCTEXT_NAMESPACE
