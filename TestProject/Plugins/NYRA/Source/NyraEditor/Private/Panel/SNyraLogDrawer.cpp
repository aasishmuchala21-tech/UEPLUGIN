// SNyraLogDrawer.cpp - collapsible bottom drawer with log entries.
// Build status: pending_manual_verification.

#include "Panel/SNyraLogDrawer.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SExpandableArea.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/SBoxPanel.h"

void SNyraLogDrawer::Construct(const FArguments& InArgs)
{
	ChildSlot
	[
		SNew(SExpandableArea)
		.InitiallyCollapsed(true)
		.HeaderContent()
		[
			SNew(STextBlock).Text(NSLOCTEXT("Nyra", "AssemblyLog", "Assembly Log"))
		]
		.BodyContent()
		[
			SNew(SBorder)
			[
				SNew(STextBlock)
				.Text_Lambda([this]()
				{
					return FText::FromString(FString::Join(Entries, TEXT("\n")));
				})
			]
		]
	];
}

void SNyraLogDrawer::AppendLogEntry(const FString& Entry)
{
	Entries.Add(Entry);
}

void SNyraLogDrawer::ClearEntries()
{
	Entries.Reset();
}

void SNyraLogDrawer::SetExpanded(bool bExpanded)
{
	bIsExpanded = bExpanded;
}

FReply SNyraLogDrawer::HandleToggleClicked()
{
	bIsExpanded = !bIsExpanded;
	return FReply::Handled();
}
