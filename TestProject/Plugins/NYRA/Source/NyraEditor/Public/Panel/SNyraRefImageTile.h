// SNyraRefImageTile.h - DEMO-01 reference image thumbnail tile.
// Plan 06-02. Build status: pending_manual_verification.

#pragma once

#include "CoreMinimal.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SCompoundWidget.h"

class NYRAEDITOR_API SNyraRefImageTile : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SNyraRefImageTile) {}
		SLATE_ARGUMENT(FString, ImagePath)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	void SetImagePath(const FString& InPath);
	const FString& GetImagePath() const { return ImagePath; }

private:
	FString ImagePath;
};
