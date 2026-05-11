// SNyraSettingsTab.cpp - Phase 18-F NYRA Settings tab.
// Build status: pending_manual_verification.

#include "Panel/SNyraSettingsTab.h"
#include "Panel/SNyraInstructionsTab.h"
#include "Panel/SNyraModelSelector.h"
#include "Panel/SNyraModeToggle.h"

#include "Process/FNyraSupervisor.h"
#include "Widgets/Input/SCheckBox.h"
#include "Widgets/Input/SSlider.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/SBoxPanel.h"
#include "Dom/JsonObject.h"

extern TUniquePtr<class FNyraSupervisor> GNyraSupervisor;

namespace
{
    // Phase 18-F: pull from FAppStyle so Light/Dark/UE themes match.
    // We define the named slots so a future Tier-3 colour pass can
    // override them without editing every widget.
    static FSlateColor NyraGetAccent()
    {
        return FAppStyle::Get().GetSlateColor("AccentBlue");
    }
    static FSlateColor NyraGetMutedText()
    {
        return FAppStyle::Get().GetSlateColor("Colors.Foreground");
    }
}

void SNyraSettingsTab::Construct(const FArguments& InArgs)
{
    ConversationId = InArgs._ConversationId.Get();
    OnFieldChanged = InArgs._OnFieldChanged;

    ChildSlot
    [
        SNew(SScrollBox)
        // Instructions
        + SScrollBox::Slot().Padding(8)
        [
            SNew(SBorder)
            .BorderImage(FAppStyle::Get().GetBrush("ToolPanel.GroupBorder"))
            [
                SAssignNew(Instructions, SNyraInstructionsTab)
            ]
        ]
        // Mode + Model row
        + SScrollBox::Slot().Padding(8)
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth().Padding(4)
            [
                SAssignNew(ModeToggle, SNyraModeToggle)
            ]
            + SHorizontalBox::Slot().FillWidth(1.0f)
            + SHorizontalBox::Slot().AutoWidth().Padding(4)
            [
                SAssignNew(ModelSelector, SNyraModelSelector)
                .ConversationId(ConversationId)
            ]
        ]
        // Privacy Mode + repro
        + SScrollBox::Slot().Padding(8)
        [
            SNew(SVerticalBox)
            + SVerticalBox::Slot().AutoHeight().Padding(0, 4)
            [
                SNew(SHorizontalBox)
                + SHorizontalBox::Slot().AutoWidth()
                [
                    SAssignNew(PrivacyToggle, SCheckBox)
                    .OnCheckStateChanged(this, &SNyraSettingsTab::HandlePrivacyChange)
                ]
                + SHorizontalBox::Slot().AutoWidth().Padding(6, 0)
                [
                    SNew(STextBlock)
                    .ColorAndOpacity(NyraGetMutedText())
                    .Text(FText::FromString(TEXT("Privacy Mode (refuses outbound HTTP)")))
                ]
            ]
            + SVerticalBox::Slot().AutoHeight().Padding(0, 4)
            [
                SNew(SHorizontalBox)
                + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 8, 0)
                [
                    SNew(STextBlock)
                    .ColorAndOpacity(NyraGetMutedText())
                    .Text(FText::FromString(TEXT("Seed")))
                ]
                + SHorizontalBox::Slot().FillWidth(1.0f)
                [
                    SAssignNew(SeedSlider, SSlider)
                    .MinValue(-1.0f).MaxValue(99999.0f)
                ]
            ]
            + SVerticalBox::Slot().AutoHeight().Padding(0, 4)
            [
                SNew(SHorizontalBox)
                + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 8, 0)
                [
                    SNew(STextBlock)
                    .ColorAndOpacity(NyraGetMutedText())
                    .Text(FText::FromString(TEXT("Temperature")))
                ]
                + SHorizontalBox::Slot().FillWidth(1.0f)
                [
                    SAssignNew(TempSlider, SSlider)
                    .MinValue(-1.0f).MaxValue(1.0f).Value(0.7f)
                ]
            ]
        ]
        // Buttons row
        + SScrollBox::Slot().Padding(8)
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth().Padding(4)
            [
                SNew(SButton)
                .ButtonColorAndOpacity(NyraGetAccent())
                .Text(FText::FromString(TEXT("Export Snapshot")))
                .OnClicked(this, &SNyraSettingsTab::HandleExportSnapshot)
            ]
            + SHorizontalBox::Slot().AutoWidth().Padding(4)
            [
                SNew(SButton)
                .Text(FText::FromString(TEXT("Open Marketplace")))
                .OnClicked(this, &SNyraSettingsTab::HandleOpenMarketplace)
            ]
        ]
    ];
    RefreshAll();
}

void SNyraSettingsTab::RefreshAll()
{
    if (!GNyraSupervisor.IsValid()) return;
    TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
    Params->SetStringField(TEXT("conversation_id"), ConversationId);
    GNyraSupervisor->SendRequest(TEXT("settings/all"), Params);
    // The response handler in SNyraChatPanel applies each section into
    // the corresponding sub-widget; this widget itself only fires the request.
}

FReply SNyraSettingsTab::HandleExportSnapshot()
{
    if (!GNyraSupervisor.IsValid()) return FReply::Handled();
    GNyraSupervisor->SendRequest(TEXT("snapshot/export"), MakeShared<FJsonObject>());
    return FReply::Handled();
}

FReply SNyraSettingsTab::HandleOpenMarketplace()
{
    if (!GNyraSupervisor.IsValid()) return FReply::Handled();
    GNyraSupervisor->SendRequest(TEXT("marketplace/list"), MakeShared<FJsonObject>());
    return FReply::Handled();
}

FReply SNyraSettingsTab::HandleClearAudit()
{
    return FReply::Handled();
}

void SNyraSettingsTab::HandlePrivacyChange(ECheckBoxState NewState)
{
    if (!GNyraSupervisor.IsValid()) return;
    TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
    const bool bEnable = (NewState == ECheckBoxState::Checked);
    Params->SetStringField(TEXT("mode"), bEnable ? TEXT("privacy") : TEXT("normal"));
    GNyraSupervisor->SendRequest(TEXT("session/set-mode"), Params);
    OnFieldChanged.ExecuteIfBound(TEXT("privacy"));
    Invalidate(EInvalidateWidget::Paint);   // WR-08
}
