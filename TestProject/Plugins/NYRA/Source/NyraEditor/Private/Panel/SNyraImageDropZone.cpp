// SNyraImageDropZone.cpp - DEMO-01 reference image drop / paste entry.
// Build status: pending_manual_verification.

#include "Panel/SNyraImageDropZone.h"

#include "Widgets/Layout/SBorder.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/SBoxPanel.h"
#include "HAL/PlatformApplicationMisc.h"
#include "DragAndDrop/AssetDragDropOp.h"
#include "Input/DragAndDrop.h"

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
	Invalidate(EInvalidateWidget::Paint);

	// CR-05: Fail closed when no usable path can be extracted. Firing the
	// delegate with FString() previously caused downstream consumers (e.g.
	// SNyraLightingPanel.CurrentImagePath, AssembleSceneTool) to receive an
	// empty path, breaking the headline DEMO-01 user gesture.
	FString ResolvedPath;

	// External file drop (Windows Explorer drag): UE exposes external file
	// drops through FExternalDragOperation in some UE versions and via the
	// engine-internal IDragDropOperation chain in others. Handle the most
	// common shape first; further drop sources are covered by the manual
	// verification step.
	if (TSharedPtr<FDragDropOperation> Operation = DragDropEvent.GetOperation())
	{
		// Asset Browser drop -- pick the first asset path.
		if (Operation->IsOfType<FAssetDragDropOp>())
		{
			TSharedPtr<FAssetDragDropOp> AssetOp = StaticCastSharedPtr<FAssetDragDropOp>(Operation);
			if (AssetOp.IsValid() && AssetOp->GetAssets().Num() > 0)
			{
				ResolvedPath = AssetOp->GetAssets()[0].GetObjectPathString();
			}
		}
	}

	if (ResolvedPath.IsEmpty())
	{
		// No path could be extracted -- propagate Unhandled so the parent
		// widget (or UE's default) can react, and DO NOT fire the delegate
		// with an empty string.
		return FReply::Unhandled();
	}

	if (OnImageDroppedDelegate.IsBound())
	{
		OnImageDroppedDelegate.Execute(ResolvedPath);
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
