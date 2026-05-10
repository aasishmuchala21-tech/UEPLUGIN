// SNyraRefImageTile.cpp - reference image thumbnail tile.
// Build status: pending_manual_verification.

#include "Panel/SNyraRefImageTile.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"

void SNyraRefImageTile::Construct(const FArguments& InArgs)
{
	ImagePath = InArgs._ImagePath;
	ChildSlot
	[
		SNew(SBox).WidthOverride(96.0f).HeightOverride(72.0f)
		[
			SNew(SBorder)
			[
				SNew(STextBlock)
				.Text_Lambda([this]() { return FText::FromString(ImagePath); })
			]
		]
	];
}

void SNyraRefImageTile::SetImagePath(const FString& InPath)
{
	ImagePath = InPath;
}
