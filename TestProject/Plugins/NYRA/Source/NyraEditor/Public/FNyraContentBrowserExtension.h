// FNyraContentBrowserExtension.h - Phase 19-C right-click "Add to Context".
// Build status: pending_manual_verification (no UE toolchain).
//
// Adds a NYRA section + "Add to Context" entry to the Content Browser's
// asset right-click menu. Click captures the selected FAssetData(s) and
// fires the existing composer/asset_search → composer/add-context flow
// (or directly emits chat/attach-context) via GNyraSupervisor.

#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"

struct FAssetData;
class FExtender;

class NYRAEDITOR_API FNyraContentBrowserExtension
{
public:
    /** Called once from NyraEditor's StartupModule. Idempotent. */
    static void Register();

    /** Called from ShutdownModule. */
    static void Unregister();

private:
    static TSharedRef<FExtender> ExtendAssetMenu(
        const TArray<FAssetData>& SelectedAssets);

    static void AddNyraSection(class FMenuBuilder& Builder,
                                TArray<FAssetData> SelectedAssets);

    static void HandleAddToContext(TArray<FAssetData> SelectedAssets);
    static void HandleReviewBlueprint(TArray<FAssetData> SelectedAssets);
    static void HandleRunHygiene(TArray<FAssetData> SelectedAssets);

    static FDelegateHandle MenuExtenderHandle;
};
