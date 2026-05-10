// SNyraAssetChip.h - resolved asset display chip (library/Meshy/ComfyUI/placeholder).
// Plan 06-02. Build status: pending_manual_verification.

#pragma once

#include "CoreMinimal.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SCompoundWidget.h"

class NYRAEDITOR_API SNyraAssetChip : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SNyraAssetChip) {}
		SLATE_ARGUMENT(FString, AssetPath)
		SLATE_ARGUMENT(FString, Source)        // "library"|"meshy"|"comfyui"|"placeholder"
		SLATE_ARGUMENT(FString, Role)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

private:
	FLinearColor SourceColor() const;
	FString AssetPath;
	FString Source;
	FString Role;
};
