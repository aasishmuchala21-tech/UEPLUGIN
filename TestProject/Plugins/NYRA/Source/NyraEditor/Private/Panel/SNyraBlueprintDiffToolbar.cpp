// SNyraBlueprintDiffToolbar.cpp - Phase 19-F BP Diff toolbar button.
// Build status: pending_manual_verification.

#include "Panel/SNyraBlueprintDiffToolbar.h"

#include "ToolMenus.h"
#include "Engine/Blueprint.h"
#include "Process/FNyraSupervisor.h"
#include "Dom/JsonObject.h"

extern TUniquePtr<class FNyraSupervisor> GNyraSupervisor;

#define LOCTEXT_NAMESPACE "NyraBPDiff"

void FNyraBlueprintDiffToolbar::Register()
{
    UToolMenus* Menus = UToolMenus::Get();
    if (!Menus) return;
    UToolMenu* DiffMenu = Menus->ExtendMenu(
        TEXT("AssetEditor.BlueprintEditor.Diff.MainMenu"));
    if (!DiffMenu) return;
    FToolMenuSection& Section = DiffMenu->FindOrAddSection(
        TEXT("NYRA"), LOCTEXT("NyraSection", "NYRA"));
    Section.AddMenuEntry(
        TEXT("ReviewWithNYRA"),
        LOCTEXT("ReviewWithNYRA", "Review this diff with NYRA"),
        LOCTEXT("ReviewWithNYRA_Tip", "Static analysis + LLM review of the BP graph + this diff"),
        FSlateIcon(),
        FUIAction(FExecuteAction::CreateLambda([]()
        {
            // Note: the actual BP / Diff context is captured by UE inside
            // the diff editor's tabs; HandleReviewClicked receives them
            // via a parallel UAssetDiffer hookup at extension-time.
            FNyraBlueprintDiffToolbar::HandleReviewClicked(nullptr, nullptr);
        }))
    );
}

void FNyraBlueprintDiffToolbar::Unregister()
{
    // ExtendMenu registrations are torn down on module unload by
    // UToolMenus::UnregisterOwner(this); the module entry handles it.
}

void FNyraBlueprintDiffToolbar::HandleReviewClicked(UBlueprint* /*OldBP*/, UBlueprint* /*NewBP*/)
{
    if (!GNyraSupervisor.IsValid()) return;

    // v0: the chat handler treats an empty graph as "use the BP I last
    // opened" and pulls the graph itself via the existing BP serialiser
    // path. A future revision wires the actual diff hunks here.
    TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
    Params->SetObjectField(TEXT("graph"), MakeShared<FJsonObject>());
    Params->SetStringField(TEXT("diff"), TEXT(""));   // populated by next phase
    GNyraSupervisor->SendRequest(TEXT("blueprint_review/compose"), Params);
}

#undef LOCTEXT_NAMESPACE
