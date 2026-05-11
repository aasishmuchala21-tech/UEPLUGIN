// SNyraModelSelector.h - Phase 11-E Aura-parity model selector pill.
// Build status: pending_manual_verification.
//
// Combo-box of the closed model set returned by settings/get-model;
// on selection, fires settings/set-model. Empty selection = "use CLI default"
// (preserves the "no new bill" semantics — we never force an upgrade).

#pragma once

#include "CoreMinimal.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SCompoundWidget.h"

DECLARE_DELEGATE_OneParam(FOnNyraModelChanged, const FString& /*Model*/);

class NYRAEDITOR_API SNyraModelSelector : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SNyraModelSelector) {}
        SLATE_ATTRIBUTE(FString, ConversationId)
        SLATE_EVENT(FOnNyraModelChanged, OnModelChanged)
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);

    void RefreshFromHost();   // fire settings/get-model and rebuild the combo
    void PinModel(const FString& Model);  // fire settings/set-model

private:
    FReply HandleClicked();
    void HandleSelection(TSharedPtr<FString> NewSelection);
    TSharedRef<class SWidget> MakeOption(TSharedPtr<FString> Option);
    FText CurrentLabel() const;

    FString ConversationId;
    FString CurrentModel;
    TArray<TSharedPtr<FString>> ModelOptions;
    FOnNyraModelChanged OnModelChanged;
};
