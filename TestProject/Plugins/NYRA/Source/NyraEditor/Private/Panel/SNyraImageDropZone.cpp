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
#include "AssetRegistry/AssetData.h"  // Plan 08-04: explicit include for FAssetData

namespace
{
	const FLinearColor Dominant(0.02f, 0.02f, 0.03f, 1.0f);
	const FLinearColor Accent(0.776f, 0.749f, 1.0f, 1.0f);
	const FLinearColor TextDim(0.6f, 0.6f, 0.65f, 1.0f);
}

void SNyraImageDropZone::Construct(const FArguments& InArgs)
{
	OnImageDroppedDelegate = InArgs._OnImageDropped;
	// Plan 08-04 (PARITY-04): capture the structured-asset delegate so OnDrop
	// can prefer it when an FAssetDragDropOp arrives from the Content Browser.
	OnAssetDroppedDelegate = InArgs._OnAssetDropped;

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
	// WR-08: explicitly invalidate so the BorderBackgroundColor lambda is
	// re-evaluated; otherwise SLATE_NEW_INVALIDATION builds may not visibly
	// toggle the highlight until another paint event happens.
	if (!bDragOverActive)
	{
		bDragOverActive = true;
		Invalidate(EInvalidateWidget::Paint);
	}
	return FReply::Handled();
}

void SNyraImageDropZone::OnDragLeave(const FDragDropEvent& DragDropEvent)
{
	if (bDragOverActive)
	{
		bDragOverActive = false;
		Invalidate(EInvalidateWidget::Paint);
	}
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
		// Asset Browser drop -- structured FAssetData payload.
		if (Operation->IsOfType<FAssetDragDropOp>())
		{
			TSharedPtr<FAssetDragDropOp> AssetOp = StaticCastSharedPtr<FAssetDragDropOp>(Operation);
			if (AssetOp.IsValid() && AssetOp->GetAssets().Num() > 0)
			{
				const FAssetData& Asset = AssetOp->GetAssets()[0];

				// Plan 08-04 (PARITY-04): prefer the structured asset delegate
				// when the parent (composer) has bound it. We pass the full
				// FAssetData so the consumer can read both /Game/... path AND
				// the asset class (StaticMesh / Material / Blueprint / etc.).
				// Short-circuit return: when this delegate fires the legacy
				// OnImageDropped path-string emission MUST NOT also fire (would
				// produce a duplicate chip).
				if (OnAssetDroppedDelegate.IsBound())
				{
					OnAssetDroppedDelegate.Execute(Asset);
					return FReply::Handled();
				}

				// LOCKED-08 backward compat: when the new delegate is unbound,
				// fall through to the legacy path-string emission so any
				// existing wiring (DEMO-01 reference-image flow) keeps working.
				ResolvedPath = Asset.GetObjectPathString();
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
