// SNyraImageDropZone.h - DEMO-01 reference image drop / paste entry.
// Plan 06-02. Build status: pending_manual_verification (no UE toolchain).
//
// Plan 08-04 (PARITY-04) extension: in addition to the legacy image-path
// delegate this widget now exposes a structured FAssetData delegate so a
// drag from the UE Content Browser can flow into the chat composer as a
// proper asset attachment chip (carrying both /Game/... path and asset
// class). The legacy OnImageDropped path is preserved verbatim for
// external-file (Windows Explorer) drops -- LOCKED-08 backward compat.
// Per LOCKED-07: NO new widget. Extension only.

#pragma once

#include "CoreMinimal.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SCompoundWidget.h"
#include "AssetRegistry/AssetData.h"

DECLARE_DELEGATE_OneParam(FOnNyraImageDropped, const FString& /*ImagePath*/);
// Plan 08-04 (PARITY-04): structured Content-Browser asset drop. Carries
// the full FAssetData so the composer can render an asset chip with the
// asset class and forward asset_path / asset_class over JSONRPC.
DECLARE_DELEGATE_OneParam(FOnNyraAssetDropped, const FAssetData& /*Asset*/);

class NYRAEDITOR_API SNyraImageDropZone : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SNyraImageDropZone) {}
		SLATE_EVENT(FOnNyraImageDropped, OnImageDropped)
		// Plan 08-04 (PARITY-04): bind this to receive Content-Browser asset
		// drops as structured FAssetData. If unbound, OnDrop falls back to
		// the legacy OnImageDropped path-string emission so existing wiring
		// keeps working unchanged.
		SLATE_EVENT(FOnNyraAssetDropped, OnAssetDropped)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	virtual FReply OnDragOver(const FGeometry& MyGeometry, const FDragDropEvent& DragDropEvent) override;
	virtual void OnDragLeave(const FDragDropEvent& DragDropEvent) override;
	virtual FReply OnDrop(const FGeometry& MyGeometry, const FDragDropEvent& DragDropEvent) override;

private:
	FReply HandlePasteFromClipboard();
	FOnNyraImageDropped OnImageDroppedDelegate;
	// Plan 08-04 (PARITY-04): asset-drop delegate; bound by SNyraComposer.
	FOnNyraAssetDropped OnAssetDroppedDelegate;
	bool bDragOverActive = false;
};
