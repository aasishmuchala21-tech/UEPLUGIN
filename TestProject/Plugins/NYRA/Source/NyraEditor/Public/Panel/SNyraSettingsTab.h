// SNyraSettingsTab.h - Phase 18-F NYRA Settings tab.
// Build status: pending_manual_verification (no UE toolchain).
//
// Single tab inside SNyraChatPanel that hosts:
//   * Custom Instructions multiline editor (Phase 11-A)
//   * Model selector pill (Phase 10-3)
//   * Operating-mode toggle (Phase 11-2 / 10-2)
//   * Privacy Mode switch (Phase 15-E)
//   * Reproducibility seed + temperature sliders (Phase 14-A)
//   * IDE-install buttons (Phase 12-A)
//   * Marketplace browse button (Phase 17-B)
//   * Multiplayer rooms list (Phase 17-C)
//
// Renders via a single settings/all WS call (Phase 18-D) so the tab
// opens without staggered flicker.

#pragma once

#include "CoreMinimal.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SCompoundWidget.h"

class SNyraInstructionsTab;
class SNyraModelSelector;
class SNyraModeToggle;
class SCheckBox;
class SSlider;

DECLARE_DELEGATE_OneParam(FOnNyraSettingsChange, const FString& /*Field*/);

class NYRAEDITOR_API SNyraSettingsTab : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SNyraSettingsTab) {}
        SLATE_ATTRIBUTE(FString, ConversationId)
        SLATE_EVENT(FOnNyraSettingsChange, OnFieldChanged)
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);

    void RefreshAll();   // fires settings/all

private:
    FReply HandleExportSnapshot();
    FReply HandleClearAudit();
    FReply HandleOpenMarketplace();
    void   HandlePrivacyChange(ECheckBoxState NewState);

    FString ConversationId;
    FOnNyraSettingsChange OnFieldChanged;

    TSharedPtr<SNyraInstructionsTab> Instructions;
    TSharedPtr<SNyraModelSelector>   ModelSelector;
    TSharedPtr<SNyraModeToggle>      ModeToggle;
    TSharedPtr<SCheckBox>            PrivacyToggle;
    TSharedPtr<SSlider>              SeedSlider;
    TSharedPtr<SSlider>              TempSlider;
};
