// SNyraLightingPanel.cpp - SCENE-01 chat-side container panel.
// Build status: pending_manual_verification. See header.

#include "Panel/SNyraLightingPanel.h"
#include "Panel/SNyraLightingSelector.h"
#include "WS/FNyraWsClient.h"

#include "Dom/JsonObject.h"
#include "Misc/Paths.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/SBoxPanel.h"

namespace NyraPanelTokens
{
	static const FLinearColor Dominant(0.02f, 0.02f, 0.03f, 1.0f);     // #050507
	static const FLinearColor Secondary(0.05f, 0.05f, 0.08f, 1.0f);    // #0D0D14
	static const FLinearColor Accent(0.776f, 0.749f, 1.0f, 1.0f);      // #C6BFFF
	static const FLinearColor AccentHover(0.549f, 0.502f, 1.0f, 1.0f); // #8C80FF
	static const FLinearColor TextPrimary(0.95f, 0.95f, 0.97f, 1.0f);
	static const FLinearColor TextDim(0.6f, 0.6f, 0.65f, 1.0f);
	static const FLinearColor StatusError(0.95f, 0.4f, 0.4f, 1.0f);
	static const FLinearColor StatusOk(0.5f, 0.85f, 0.55f, 1.0f);

	static const FMargin Md(16.0f, 8.0f);
	static const FMargin Lg(24.0f, 16.0f);
}

void SNyraLightingPanel::Construct(const FArguments& InArgs)
{
	WsClient = InArgs._WsClient;

	ChildSlot
	[
		SNew(SBorder)
		.BorderBackgroundColor(NyraPanelTokens::Dominant)
		.Padding(NyraPanelTokens::Lg)
		[
			SNew(SVerticalBox)
			// Heading
			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(NyraPanelTokens::Md)
			[
				SNew(STextBlock)
				.Text(FText::FromString(TEXT("Lighting Setup")))
				.ColorAndOpacity(NyraPanelTokens::TextPrimary)
			]
			// Selector
			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(NyraPanelTokens::Md)
			[
				SAssignNew(LightingSelector, SNyraLightingSelector)
				.OnPresetSelected(FOnNyraLightingPresetSelected::CreateSP(this, &SNyraLightingPanel::HandlePresetSelected))
				.OnDryRunHover(FOnNyraLightingDryRunHover::CreateSP(this, &SNyraLightingPanel::HandleDryRunHover))
				.OnDryRunUnhover(FOnNyraLightingDryRunUnhover::CreateSP(this, &SNyraLightingPanel::HandleDryRunUnhover))
			]
			// Action row: Apply Lighting button
			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(NyraPanelTokens::Md)
			[
				SNew(SBox)
				.HeightOverride(36.0f)
				[
					SAssignNew(ApplyButton, SButton)
					.ButtonColorAndOpacity(NyraPanelTokens::Accent)
					.OnClicked(this, &SNyraLightingPanel::HandleApplyClicked)
					[
						SNew(STextBlock)
						.Text(FText::FromString(TEXT("Apply Lighting")))
						.ColorAndOpacity(FLinearColor(0.05f, 0.05f, 0.08f, 1.0f))
					]
				]
			]
			// Status pill
			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(NyraPanelTokens::Md)
			[
				SAssignNew(StatusText, STextBlock)
				.Text_Lambda([this]() { return GetStatusText(); })
				.ColorAndOpacity_Lambda([this]() { return GetStatusColor(); })
			]
		]
	];

	SetState(ENyraLightingPanelState::Idle);
}

FReply SNyraLightingPanel::HandleApplyClicked()
{
	// CR-06 / WR-09: validate the path actually exists before treating it as
	// configured. After CR-05 the drop zone fails closed when no path is
	// extractable, but local clipboard / paste paths still need a positive
	// existence check before sending to NyraHost.
	const bool bHasPreset = !CurrentPreset.IsEmpty();
	const bool bHasImage = !CurrentImagePath.IsEmpty()
		&& FPaths::FileExists(CurrentImagePath);
	if (!bHasPreset && !bHasImage)
	{
		SetState(ENyraLightingPanelState::Error, TEXT("Select a preset or attach a reference image first."));
		return FReply::Handled();
	}

	SetState(ENyraLightingPanelState::Applying);

	// CR-06: actually dispatch the JSON-RPC call instead of an empty branch.
	// Method: nyra_lighting_authoring. Params are built from the panel's
	// current state -- preset_name and/or reference_image_path -- and apply
	// is true so NyraHost places real actors.
	if (TSharedPtr<FNyraWsClient> Pinned = WsClient.Pin())
	{
		TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
		if (bHasPreset)
		{
			Params->SetStringField(TEXT("preset_name"), CurrentPreset);
		}
		if (bHasImage)
		{
			Params->SetStringField(TEXT("reference_image_path"), CurrentImagePath);
		}
		Params->SetBoolField(TEXT("apply"), true);
		Pinned->SendRequest(TEXT("nyra_lighting_authoring"), Params);
	}
	else
	{
		SetState(ENyraLightingPanelState::Error, TEXT("WebSocket client unavailable."));
	}

	return FReply::Handled();
}

void SNyraLightingPanel::HandlePresetSelected(const FString& PresetKey)
{
	CurrentPreset = PresetKey;
	SetState(ENyraLightingPanelState::Idle, FString::Printf(TEXT("Preset: %s"), *PresetKey));
}

void SNyraLightingPanel::HandleDryRunHover(const FString& PresetKey)
{
	// CR-06: actually dispatch the dry-run preview request.
	if (TSharedPtr<FNyraWsClient> Pinned = WsClient.Pin())
	{
		TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
		Params->SetStringField(TEXT("preset_name"), PresetKey);
		Pinned->SendRequest(TEXT("nyra_lighting_dry_run_preview"), Params);
	}
	SetState(ENyraLightingPanelState::PreviewingDryRun, PresetKey);
}

void SNyraLightingPanel::HandleDryRunUnhover()
{
	if (State == ENyraLightingPanelState::PreviewingDryRun)
	{
		SetState(ENyraLightingPanelState::Idle, CurrentPreset);
	}
}

void SNyraLightingPanel::OnDryRunPreviewMessage(const TSharedPtr<FJsonObject>& Payload)
{
	if (!Payload.IsValid())
	{
		return;
	}
	const FString PrimaryLightType = Payload->GetStringField(TEXT("primary_light_type"));
	SetState(ENyraLightingPanelState::PreviewingDryRun, PrimaryLightType);
}

void SNyraLightingPanel::OnLightingAppliedMessage(const TSharedPtr<FJsonObject>& Payload)
{
	if (!Payload.IsValid())
	{
		SetState(ENyraLightingPanelState::Error, TEXT("Empty payload"));
		return;
	}
	int32 ActorCount = 0;
	Payload->TryGetNumberField(TEXT("actor_count"), ActorCount);
	const FString Message = Payload->GetStringField(TEXT("message"));
	SetState(ENyraLightingPanelState::Applied,
		FString::Printf(TEXT("%d actors placed - %s"), ActorCount, *Message));
}

void SNyraLightingPanel::SetState(ENyraLightingPanelState NewState, const FString& Detail)
{
	State = NewState;
	StatusDetail = Detail;
}

FText SNyraLightingPanel::GetStatusText() const
{
	switch (State)
	{
	case ENyraLightingPanelState::Idle:
		return StatusDetail.IsEmpty()
			? FText::FromString(TEXT("Select a preset or attach a reference image."))
			: FText::FromString(StatusDetail);
	case ENyraLightingPanelState::PreviewingDryRun:
		return FText::Format(
			FText::FromString(TEXT("Previewing: {0}")),
			FText::FromString(StatusDetail));
	case ENyraLightingPanelState::Applying:
		return FText::FromString(TEXT("Applying lighting..."));
	case ENyraLightingPanelState::Applied:
		return FText::Format(
			FText::FromString(TEXT("Applied: {0}")),
			FText::FromString(StatusDetail));
	case ENyraLightingPanelState::Error:
		return FText::Format(
			FText::FromString(TEXT("Error: {0}")),
			FText::FromString(StatusDetail));
	}
	return FText::FromString(TEXT(""));
}

FLinearColor SNyraLightingPanel::GetStatusColor() const
{
	switch (State)
	{
	case ENyraLightingPanelState::Applied:
		return NyraPanelTokens::StatusOk;
	case ENyraLightingPanelState::Error:
		return NyraPanelTokens::StatusError;
	case ENyraLightingPanelState::PreviewingDryRun:
		return NyraPanelTokens::Accent;
	default:
		return NyraPanelTokens::TextDim;
	}
}
