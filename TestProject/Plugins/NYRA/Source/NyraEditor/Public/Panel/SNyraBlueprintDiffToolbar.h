// SNyraBlueprintDiffToolbar.h - Phase 19-F BP Diff toolbar button.
// Build status: pending_manual_verification (no UE toolchain).
//
// Adds a "Review with NYRA" button to the Blueprint Editor's diff
// toolbar (the same one that hosts UE's Apply/Revert buttons). Click
// composes the BP graph + diff into blueprint_review/compose payload
// and ships it over the WS — the chat panel renders the resulting
// review.
//
// Hooked in NyraEditor's StartupModule by extending the toolbar via
// UToolMenus::ExtendMenu("AssetEditor.BlueprintEditor.Diff.MainMenu").

#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"

class NYRAEDITOR_API FNyraBlueprintDiffToolbar
{
public:
    static void Register();
    static void Unregister();

private:
    static void HandleReviewClicked(class UBlueprint* OldBP, class UBlueprint* NewBP);
};
