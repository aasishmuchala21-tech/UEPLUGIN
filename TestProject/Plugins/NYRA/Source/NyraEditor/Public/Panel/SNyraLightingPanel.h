// SNyraLightingPanel.h - SCENE-01 chat-side container panel.
// Plan 06-01 / Phase 6.
//
// Build status: pending_manual_verification. See 06-01-SUMMARY.md.

#pragma once

#include "CoreMinimal.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SCompoundWidget.h"

class FJsonObject;
class SNyraLightingSelector;
class STextBlock;
class SButton;

class FNyraWsClient;

/** Panel state used by the status pill and applied/idle/error transitions. */
enum class ENyraLightingPanelState : uint8
{
	Idle,
	PreviewingDryRun,
	Applying,
	Applied,
	Error,
};

class NYRAEDITOR_API SNyraLightingPanel : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SNyraLightingPanel) {}
		SLATE_ARGUMENT(TWeakPtr<FNyraWsClient>, WsClient)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	/** Externally-callable: NyraHost emits dry_run_preview; chat panel forwards here. */
	void OnDryRunPreviewMessage(const TSharedPtr<FJsonObject>& Payload);

	/** Externally-callable: NyraHost emits assembly_complete after Apply. */
	void OnLightingAppliedMessage(const TSharedPtr<FJsonObject>& Payload);

private:
	FReply HandleApplyClicked();
	void HandlePresetSelected(const FString& PresetKey);
	void HandleDryRunHover(const FString& PresetKey);
	void HandleDryRunUnhover();

	void SetState(ENyraLightingPanelState NewState, const FString& Detail = FString());
	FText GetStatusText() const;
	FLinearColor GetStatusColor() const;

	TWeakPtr<FNyraWsClient> WsClient;
	TSharedPtr<SNyraLightingSelector> LightingSelector;
	TSharedPtr<STextBlock> StatusText;
	TSharedPtr<SButton> ApplyButton;

	FString CurrentPreset;
	FString CurrentImagePath; // populated when user attaches a reference image
	ENyraLightingPanelState State = ENyraLightingPanelState::Idle;
	FString StatusDetail;
};
