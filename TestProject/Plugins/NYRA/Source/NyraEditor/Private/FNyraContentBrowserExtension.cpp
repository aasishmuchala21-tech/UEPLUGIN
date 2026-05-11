// FNyraContentBrowserExtension.cpp - Phase 19-C right-click extension.
// Build status: pending_manual_verification.

#include "FNyraContentBrowserExtension.h"

#include "ContentBrowserModule.h"
#include "ContentBrowserDelegates.h"
#include "AssetRegistry/AssetData.h"
#include "Framework/MultiBox/MultiBoxExtender.h"
#include "Framework/MultiBox/MultiBoxBuilder.h"
#include "Process/FNyraSupervisor.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"

extern TUniquePtr<class FNyraSupervisor> GNyraSupervisor;

FDelegateHandle FNyraContentBrowserExtension::MenuExtenderHandle;

#define LOCTEXT_NAMESPACE "NyraContentBrowser"

void FNyraContentBrowserExtension::Register()
{
    FContentBrowserModule& CB = FModuleManager::LoadModuleChecked<FContentBrowserModule>(
        TEXT("ContentBrowser"));
    auto& MenuExtenders = CB.GetAllAssetViewContextMenuExtenders();
    FContentBrowserMenuExtender_SelectedAssets Ext =
        FContentBrowserMenuExtender_SelectedAssets::CreateStatic(
            &FNyraContentBrowserExtension::ExtendAssetMenu);
    MenuExtenders.Add(Ext);
    MenuExtenderHandle = MenuExtenders.Last().GetHandle();
}

void FNyraContentBrowserExtension::Unregister()
{
    if (!FModuleManager::Get().IsModuleLoaded("ContentBrowser")) return;
    FContentBrowserModule& CB = FModuleManager::GetModuleChecked<FContentBrowserModule>(
        TEXT("ContentBrowser"));
    CB.GetAllAssetViewContextMenuExtenders().RemoveAll(
        [](const FContentBrowserMenuExtender_SelectedAssets& E) {
            return E.GetHandle() == MenuExtenderHandle;
        });
}

TSharedRef<FExtender> FNyraContentBrowserExtension::ExtendAssetMenu(
    const TArray<FAssetData>& SelectedAssets)
{
    TSharedRef<FExtender> Extender(new FExtender());
    Extender->AddMenuExtension(
        TEXT("AssetContextAdvancedActions"),
        EExtensionHook::After,
        nullptr,
        FMenuExtensionDelegate::CreateStatic(
            &FNyraContentBrowserExtension::AddNyraSection, SelectedAssets));
    return Extender;
}

void FNyraContentBrowserExtension::AddNyraSection(
    FMenuBuilder& Builder, TArray<FAssetData> SelectedAssets)
{
    Builder.BeginSection(TEXT("NYRA"), LOCTEXT("NyraSection", "NYRA"));

    Builder.AddMenuEntry(
        LOCTEXT("AddToContext", "Add to NYRA Chat context"),
        LOCTEXT("AddToContext_Tip", "Drop the selected asset(s) into the NYRA chat composer as @-referenced context"),
        FSlateIcon(),
        FUIAction(FExecuteAction::CreateStatic(
            &FNyraContentBrowserExtension::HandleAddToContext, SelectedAssets))
    );

    // Blueprint-only entries — guard at click time so we don't lie about
    // applicability on a Texture2D selection.
    Builder.AddMenuEntry(
        LOCTEXT("ReviewBP", "Review Blueprint with NYRA"),
        LOCTEXT("ReviewBP_Tip", "Run NYRA's static + LLM blueprint code review on the selected Blueprint"),
        FSlateIcon(),
        FUIAction(FExecuteAction::CreateStatic(
            &FNyraContentBrowserExtension::HandleReviewBlueprint, SelectedAssets))
    );

    Builder.AddMenuEntry(
        LOCTEXT("RunHygiene", "Run NYRA Asset Hygiene on this folder"),
        LOCTEXT("RunHygiene_Tip", "Sweep the parent folder for unused assets + naming-convention violations"),
        FSlateIcon(),
        FUIAction(FExecuteAction::CreateStatic(
            &FNyraContentBrowserExtension::HandleRunHygiene, SelectedAssets))
    );

    Builder.EndSection();
}

void FNyraContentBrowserExtension::HandleAddToContext(TArray<FAssetData> SelectedAssets)
{
    if (!GNyraSupervisor.IsValid()) return;
    TArray<TSharedPtr<FJsonValue>> AssetArr;
    for (const FAssetData& A : SelectedAssets)
    {
        TSharedRef<FJsonObject> O = MakeShared<FJsonObject>();
        O->SetStringField(TEXT("name"), A.AssetName.ToString());
        O->SetStringField(TEXT("class"), A.AssetClassPath.GetAssetName().ToString());
        O->SetStringField(TEXT("path"), A.GetObjectPathString());
        AssetArr.Add(MakeShared<FJsonValueObject>(O));
    }
    TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
    Params->SetArrayField(TEXT("assets"), AssetArr);
    GNyraSupervisor->SendRequest(TEXT("composer/add_context"), Params);
}

void FNyraContentBrowserExtension::HandleReviewBlueprint(TArray<FAssetData> SelectedAssets)
{
    if (!GNyraSupervisor.IsValid() || SelectedAssets.Num() == 0) return;
    // Pass the first selected Blueprint's path; the Python handler
    // ignores non-Blueprint selections with a structured error.
    TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
    Params->SetStringField(TEXT("blueprint_path"),
                            SelectedAssets[0].GetObjectPathString());
    GNyraSupervisor->SendRequest(TEXT("blueprint_review/compose"), Params);
}

void FNyraContentBrowserExtension::HandleRunHygiene(TArray<FAssetData> SelectedAssets)
{
    if (!GNyraSupervisor.IsValid() || SelectedAssets.Num() == 0) return;
    const FString ParentFolder = FPaths::GetPath(
        SelectedAssets[0].GetObjectPathString());
    TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
    Params->SetStringField(TEXT("under"), ParentFolder);
    GNyraSupervisor->SendRequest(TEXT("hygiene/run"), Params);
}

#undef LOCTEXT_NAMESPACE
