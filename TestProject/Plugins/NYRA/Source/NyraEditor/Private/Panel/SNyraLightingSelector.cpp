// SNyraLightingSelector.cpp - SCENE-01 horizontal preset card row.
// Build status: pending_manual_verification. See header.

#include "Panel/SNyraLightingSelector.h"

#include "Widgets/Text/STextBlock.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/SBoxPanel.h"
#include "EditorStyleSet.h"

namespace NyraLightingTokens
{
	// 06-UI-SPEC.md design tokens.
	static const FLinearColor Dominant(0.02f, 0.02f, 0.03f, 1.0f);     // #050507
	static const FLinearColor Secondary(0.05f, 0.05f, 0.08f, 1.0f);    // #0D0D14
	static const FLinearColor Accent(0.776f, 0.749f, 1.0f, 1.0f);      // #C6BFFF
	static const FLinearColor AccentHover(0.549f, 0.502f, 1.0f, 1.0f); // #8C80FF
	static const FLinearColor TextPrimary(0.95f, 0.95f, 0.97f, 1.0f);
	static const FLinearColor Transparent(0, 0, 0, 0);

	static const float CardWidth = 80.0f;
	static const float CardHeight = 60.0f;
	static const FMargin CardMargin(4.0f, 0.0f);
	static const FMargin ContentPadding(16.0f, 8.0f);
}

void SNyraLightingSelector::Construct(const FArguments& InArgs)
{
	OnPresetSelectedDelegate = InArgs._OnPresetSelected;
	OnDryRunHoverDelegate = InArgs._OnDryRunHover;
	OnDryRunUnhoverDelegate = InArgs._OnDryRunUnhover;

	BuildPresetCards();

	TSharedRef<SHorizontalBox> CardRow = SNew(SHorizontalBox);
	for (const FNyraLightingPresetCard& Card : Presets)
	{
		CardRow->AddSlot()
			.AutoWidth()
			.Padding(NyraLightingTokens::CardMargin)
			[
				MakeCardWidget(Card)
			];
	}

	ChildSlot
	[
		SNew(SVerticalBox)
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(NyraLightingTokens::ContentPadding)
		[
			SAssignNew(SelectedLabel, STextBlock)
			.Text(FText::FromString(TEXT("Lighting Setup")))
			.ColorAndOpacity(NyraLightingTokens::TextPrimary)
		]
		+ SVerticalBox::Slot()
		.AutoHeight()
		[
			SAssignNew(ScrollBox, SScrollBox)
			.Orientation(Orient_Horizontal)
			+ SScrollBox::Slot()
			[
				CardRow
			]
		]
	];
}

void SNyraLightingSelector::BuildPresetCards()
{
	Presets.Empty();
	Presets.Add({TEXT("Golden Hour"), TEXT("golden_hour"), NyraLightingTokens::Accent, false});
	Presets.Add({TEXT("Harsh Overhead"), TEXT("harsh_overhead"), NyraLightingTokens::Accent, false});
	Presets.Add({TEXT("Moody Blue"), TEXT("moody_blue"), NyraLightingTokens::Accent, false});
	Presets.Add({TEXT("Studio Fill"), TEXT("studio_fill"), NyraLightingTokens::Accent, false});
	Presets.Add({TEXT("Dawn"), TEXT("dawn"), NyraLightingTokens::Accent, false});
	Presets.Add({TEXT("Matched from Image"), TEXT("matched_from_image"), NyraLightingTokens::Accent, true});
}

TSharedRef<SWidget> SNyraLightingSelector::MakeCardWidget(const FNyraLightingPresetCard& Card)
{
	const FString PresetKey = Card.PresetKey;

	return SNew(SBox)
		.WidthOverride(NyraLightingTokens::CardWidth)
		.HeightOverride(NyraLightingTokens::CardHeight)
		[
			SNew(SButton)
			.ButtonColorAndOpacity(NyraLightingTokens::Secondary)
			.OnClicked(FOnClicked::CreateSP(this, &SNyraLightingSelector::HandleCardClicked, PresetKey))
			.OnHovered(FSimpleDelegate::CreateLambda([this, PresetKey]()
			{
				const_cast<SNyraLightingSelector*>(this)->HandleCardHovered(PresetKey);
			}))
			.OnUnhovered(FSimpleDelegate::CreateLambda([this]()
			{
				const_cast<SNyraLightingSelector*>(this)->HandleCardUnhovered();
			}))
			[
				SNew(SBorder)
				.BorderBackgroundColor_Lambda([this, PresetKey]()
				{
					return GetCardBorderColor(PresetKey);
				})
				[
					SNew(STextBlock)
					.Text(FText::FromString(Card.Name))
					.ColorAndOpacity(NyraLightingTokens::TextPrimary)
				]
			]
		];
}

FReply SNyraLightingSelector::HandleCardClicked(FString PresetKey)
{
	SelectedPreset = PresetKey;
	if (OnPresetSelectedDelegate.IsBound())
	{
		OnPresetSelectedDelegate.Execute(PresetKey);
	}
	return FReply::Handled();
}

void SNyraLightingSelector::HandleCardHovered(FString PresetKey)
{
	if (OnDryRunHoverDelegate.IsBound())
	{
		OnDryRunHoverDelegate.Execute(PresetKey);
	}
}

void SNyraLightingSelector::HandleCardUnhovered()
{
	if (OnDryRunUnhoverDelegate.IsBound())
	{
		OnDryRunUnhoverDelegate.Execute();
	}
}

FLinearColor SNyraLightingSelector::GetCardBorderColor(FString PresetKey) const
{
	return PresetKey == SelectedPreset ? NyraLightingTokens::Accent : NyraLightingTokens::Transparent;
}

void SNyraLightingSelector::SelectPreset(const FString& PresetKey)
{
	SelectedPreset = PresetKey;
}
