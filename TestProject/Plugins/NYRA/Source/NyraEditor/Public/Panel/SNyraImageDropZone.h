// SNyraImageDropZone.h - DEMO-01 reference image drop / paste entry.
// Plan 06-02. Build status: pending_manual_verification (no UE toolchain).

#pragma once

#include "CoreMinimal.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SCompoundWidget.h"

DECLARE_DELEGATE_OneParam(FOnNyraImageDropped, const FString& /*ImagePath*/);

class NYRAEDITOR_API SNyraImageDropZone : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SNyraImageDropZone) {}
		SLATE_EVENT(FOnNyraImageDropped, OnImageDropped)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	virtual FReply OnDragOver(const FGeometry& MyGeometry, const FDragDropEvent& DragDropEvent) override;
	virtual void OnDragLeave(const FDragDropEvent& DragDropEvent) override;
	virtual FReply OnDrop(const FGeometry& MyGeometry, const FDragDropEvent& DragDropEvent) override;

private:
	FReply HandlePasteFromClipboard();
	FOnNyraImageDropped OnImageDroppedDelegate;
	bool bDragOverActive = false;
};
