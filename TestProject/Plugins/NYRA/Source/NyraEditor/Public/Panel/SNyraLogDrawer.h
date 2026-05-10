// SNyraLogDrawer.h - DEMO-01 collapsible bottom drawer with assembly log entries.
// Plan 06-02. Build status: pending_manual_verification.

#pragma once

#include "CoreMinimal.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SCompoundWidget.h"

class NYRAEDITOR_API SNyraLogDrawer : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SNyraLogDrawer) {}
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	void AppendLogEntry(const FString& Entry);
	void ClearEntries();
	void SetExpanded(bool bExpanded);
	bool IsExpanded() const { return bIsExpanded; }

private:
	FReply HandleToggleClicked();
	TArray<FString> Entries;
	bool bIsExpanded = false;
};
