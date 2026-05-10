// SNyraProgressBar.cpp - 4-step segmented progress bar.
// Build status: pending_manual_verification.

#include "Panel/SNyraProgressBar.h"
#include "Widgets/Notifications/SProgressBar.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/SBoxPanel.h"

namespace
{
	const FLinearColor Accent(0.776f, 0.749f, 1.0f, 1.0f);
}

void SNyraProgressBar::Construct(const FArguments& InArgs)
{
	ChildSlot
	[
		SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()
		[
			SNew(STextBlock)
			.Text_Lambda([this]() {
				return FText::FromString(FString::Printf(
					TEXT("%s (%d/%d) %s"),
					*CurrentStep, CurrentN, CurrentTotal, *LastMessage));
			})
		]
		+ SVerticalBox::Slot().AutoHeight()
		[
			SNew(SProgressBar)
			.Percent_Lambda([this]() { return ProgressFor(CurrentStep); })
			.FillColorAndOpacity(Accent)
		]
	];
}

void SNyraProgressBar::SetProgress(const FString& Step, int32 Current, int32 Total, const FString& Message)
{
	CurrentStep = Step;
	CurrentN = Current;
	CurrentTotal = FMath::Max(1, Total);
	LastMessage = Message;
}

void SNyraProgressBar::Reset()
{
	CurrentStep.Reset();
	CurrentN = 0;
	CurrentTotal = 0;
	LastMessage.Reset();
}

float SNyraProgressBar::ProgressFor(const FString& Step) const
{
	// WR-06: WIRE CONSTANTS. The labels below MUST match
	// nyrahost.tools.scene_types.ASSEMBLY_PROGRESS_STEPS (in
	// NYRA/Source/NyraHost/src/nyrahost/tools/scene_types.py). Adding or
	// renaming a step requires updating BOTH that Python list AND this
	// switch -- the assembler emits these strings verbatim over WS.
	// 4 segments: Placing Actors / Applying Materials / Setting Up Lighting / Finalizing
	float SegmentBase = 0.0f;
	if (Step == TEXT("Applying Materials"))    SegmentBase = 0.25f;
	else if (Step == TEXT("Setting Up Lighting")) SegmentBase = 0.50f;
	else if (Step == TEXT("Finalizing"))       SegmentBase = 0.75f;

	const float SegmentSize = 0.25f;
	const float Within = CurrentTotal > 0 ? float(CurrentN) / float(CurrentTotal) : 0.0f;
	return FMath::Clamp(SegmentBase + Within * SegmentSize, 0.0f, 1.0f);
}
