// SNyraLightingSelector.h - SCENE-01 horizontal preset card row.
// Plan 06-01 / Phase 6.
//
// Build status: pending_manual_verification (no UE 5.4-5.7 toolchain on the
// authoring host as of Plan 06-01 commit; structure mirrors SNyraChatPanel.h
// patterns and 06-UI-SPEC.md design tokens). See 06-01-SUMMARY.md.

#pragma once

#include "CoreMinimal.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SCompoundWidget.h"

class STextBlock;
class SScrollBox;

/** A single lighting preset card displayed in SNyraLightingSelector. */
struct FNyraLightingPresetCard
{
	FString Name;        // Display label, e.g. "Golden Hour"
	FString PresetKey;   // MCP-side preset key, e.g. "golden_hour"
	FLinearColor Accent; // Accent border color when selected (default #C6BFFF)
	bool bCustom = false; // True for the trailing "Matched from Image" card
};

DECLARE_DELEGATE_OneParam(FOnNyraLightingPresetSelected, const FString& /*PresetKey*/);
DECLARE_DELEGATE_OneParam(FOnNyraLightingDryRunHover, const FString& /*PresetKey*/);
DECLARE_DELEGATE(FOnNyraLightingDryRunUnhover);

class NYRAEDITOR_API SNyraLightingSelector : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SNyraLightingSelector) {}
		SLATE_EVENT(FOnNyraLightingPresetSelected, OnPresetSelected)
		SLATE_EVENT(FOnNyraLightingDryRunHover, OnDryRunHover)
		SLATE_EVENT(FOnNyraLightingDryRunUnhover, OnDryRunUnhover)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	/** Currently-selected preset key, or empty string if none. */
	const FString& GetSelectedPreset() const { return SelectedPreset; }

	/** Programmatically select a preset (used by SNyraLightingPanel after WS round-trip). */
	void SelectPreset(const FString& PresetKey);

private:
	void BuildPresetCards();
	TSharedRef<SWidget> MakeCardWidget(const FNyraLightingPresetCard& Card);

	FReply HandleCardClicked(FString PresetKey);
	void HandleCardHovered(FString PresetKey);
	void HandleCardUnhovered();

	FLinearColor GetCardBorderColor(FString PresetKey) const;

	TArray<FNyraLightingPresetCard> Presets;
	FString SelectedPreset;

	TSharedPtr<SScrollBox> ScrollBox;
	TSharedPtr<STextBlock> SelectedLabel;

	FOnNyraLightingPresetSelected OnPresetSelectedDelegate;
	FOnNyraLightingDryRunHover OnDryRunHoverDelegate;
	FOnNyraLightingDryRunUnhover OnDryRunUnhoverDelegate;
};
