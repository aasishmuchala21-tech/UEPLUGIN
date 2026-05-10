// SNyraImageDropZone.cpp - DEMO-01 reference image drop / paste entry.
// Build status: pending_manual_verification.

#include "Panel/SNyraImageDropZone.h"

#include "Widgets/Layout/SBorder.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/SBoxPanel.h"
#include "HAL/PlatformApplicationMisc.h"

namespace
{
	const FLinearColor Dominant(0.02f, 0.02f, 0.03f, 1.0f);
	const FLinearColor Accent(0.776f, 0.749f, 1.0f, 1.0f);
	const FLinearColor TextDim(0.6f, 0.6f, 0.65f, 1.0f);
}

void SNyraImageDropZone::Construct(const FArguments& InArgs)
{
	OnImageDroppedDelegate = InArgs._OnImageDropped;

	ChildSlot
	[
		SNew(SBorder)
		.BorderBackgroundColor_Lambda([this]()
		{
			return bDragOverActive ? Accent : Dominant;
		})
		.Padding(FMargin(24.0f, 16.0f))
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(STextBlock)
				.Text(NSLOCTEXT("Nyra", "DropHint", "Drop a reference image here, or paste from clipboard"))
				.ColorAndOpacity(TextDim)
			]
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(SButton)
				.OnClicked(this, &SNyraImageDropZone::HandlePasteFromClipboard)
				[
					SNew(STextBlock)
					.Text(NSLOCTEXT("Nyra", "PasteCta", "Paste"))
				]
			]
		]
	];
}

FReply SNyraImageDropZone::OnDragOver(const FGeometry& MyGeometry, const FDragDropEvent& DragDropEvent)
{
	bDragOverActive = true;
	return FReply::Handled();
}

void SNyraImageDropZone::OnDragLeave(const FDragDropEvent& DragDropEvent)
{
	bDragOverActive = false;
}

FReply SNyraImageDropZone::OnDrop(const FGeometry& MyGeometry, const FDragDropEvent& DragDropEvent)
{
	bDragOverActive = false;
	// External-file drop wiring (FExternalDragOperation) is finished in operator
	// verification step; placeholder fires the delegate with empty path so wiring
	// is reachable for compile-time linking checks.
	if (OnImageDroppedDelegate.IsBound())
	{
		OnImageDroppedDelegate.Execute(FString());
	}
	return FReply::Handled();
}

FReply SNyraImageDropZone::HandlePasteFromClipboard()
{
	FString Clipboard;
	FPlatformApplicationMisc::ClipboardPaste(Clipboard);
	if (OnImageDroppedDelegate.IsBound())
	{
		OnImageDroppedDelegate.Execute(Clipboard);
	}
	return FReply::Handled();
}
