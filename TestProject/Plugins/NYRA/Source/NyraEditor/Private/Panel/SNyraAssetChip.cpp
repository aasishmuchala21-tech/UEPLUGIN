// SNyraAssetChip.cpp - resolved asset display chip.
// Build status: pending_manual_verification.

#include "Panel/SNyraAssetChip.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/SBoxPanel.h"

void SNyraAssetChip::Construct(const FArguments& InArgs)
{
	AssetPath = InArgs._AssetPath;
	Source = InArgs._Source;
	Role = InArgs._Role;

	ChildSlot
	[
		SNew(SBorder)
		.BorderBackgroundColor(SourceColor())
		.Padding(FMargin(8.0f, 4.0f))
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth()
			[
				SNew(STextBlock).Text(FText::FromString(Role))
			]
			+ SHorizontalBox::Slot().AutoWidth()
			[
				SNew(STextBlock).Text(FText::FromString(Source))
			]
			+ SHorizontalBox::Slot().AutoWidth()
			[
				SNew(STextBlock).Text(FText::FromString(AssetPath))
			]
		]
	];
}

FLinearColor SNyraAssetChip::SourceColor() const
{
	if (Source == TEXT("library"))     return FLinearColor(0.5f, 0.85f, 0.55f, 1.0f);
	if (Source == TEXT("meshy"))       return FLinearColor(0.776f, 0.749f, 1.0f, 1.0f); // accent
	if (Source == TEXT("comfyui"))     return FLinearColor(0.7f, 0.5f, 0.9f, 1.0f);
	return FLinearColor(0.6f, 0.6f, 0.65f, 1.0f); // placeholder / default
}
