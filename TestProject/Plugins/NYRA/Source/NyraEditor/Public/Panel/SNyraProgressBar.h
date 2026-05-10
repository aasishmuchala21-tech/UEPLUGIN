// SNyraProgressBar.h - DEMO-01 4-step segmented progress bar.
// Plan 06-02. Build status: pending_manual_verification.

#pragma once

#include "CoreMinimal.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SCompoundWidget.h"

class NYRAEDITOR_API SNyraProgressBar : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SNyraProgressBar) {}
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	/** Update the bar from a parsed assembly_progress WS message. */
	void SetProgress(const FString& Step, int32 Current, int32 Total, const FString& Message = FString());

	/** Reset to idle state. */
	void Reset();

private:
	float ProgressFor(const FString& Step) const;

	FString CurrentStep;
	int32 CurrentN = 0;
	int32 CurrentTotal = 0;
	FString LastMessage;
};
