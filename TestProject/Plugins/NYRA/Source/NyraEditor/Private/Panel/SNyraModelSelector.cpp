// SNyraModelSelector.cpp - Phase 11-E Aura-parity model selector pill.
// Build status: pending_manual_verification.

#include "Panel/SNyraModelSelector.h"

#include "Process/FNyraSupervisor.h"
#include "Widgets/Input/SComboBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/SBoxPanel.h"
#include "Dom/JsonObject.h"

extern TUniquePtr<class FNyraSupervisor> GNyraSupervisor;

namespace
{
    const FString DefaultLabel(TEXT("(default)"));
    // Mirrors ALLOWED_MODELS in nyrahost.model_preference. Cheap → expensive.
    const TArray<FString>& AllowedModels()
    {
        static const TArray<FString> M = {
            DefaultLabel,
            TEXT("claude-haiku-4-5"),
            TEXT("claude-sonnet-4-6"),
            TEXT("claude-opus-4-7"),
        };
        return M;
    }
}

void SNyraModelSelector::Construct(const FArguments& InArgs)
{
    ConversationId = InArgs._ConversationId.Get();
    OnModelChanged = InArgs._OnModelChanged;
    CurrentModel = DefaultLabel;

    ModelOptions.Reset();
    for (const FString& M : AllowedModels())
    {
        ModelOptions.Add(MakeShared<FString>(M));
    }

    ChildSlot
    [
        SNew(SComboBox<TSharedPtr<FString>>)
        .OptionsSource(&ModelOptions)
        .OnGenerateWidget(this, &SNyraModelSelector::MakeOption)
        .OnSelectionChanged(this, &SNyraModelSelector::HandleSelection)
        [
            SNew(STextBlock).Text(this, &SNyraModelSelector::CurrentLabel)
        ]
    ];
}

TSharedRef<SWidget> SNyraModelSelector::MakeOption(TSharedPtr<FString> Option)
{
    return SNew(STextBlock).Text(FText::FromString(Option.IsValid() ? *Option : FString()));
}

FText SNyraModelSelector::CurrentLabel() const
{
    return FText::FromString(CurrentModel.IsEmpty() ? DefaultLabel : CurrentModel);
}

void SNyraModelSelector::HandleSelection(TSharedPtr<FString> NewSelection)
{
    if (!NewSelection.IsValid()) return;
    PinModel(*NewSelection);
}

void SNyraModelSelector::PinModel(const FString& Model)
{
    CurrentModel = Model;
    if (GNyraSupervisor.IsValid())
    {
        TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
        Params->SetStringField(TEXT("conversation_id"), ConversationId);
        if (Model == DefaultLabel || Model.IsEmpty())
        {
            // null model clears the pin per Phase 10-3 contract
            Params->SetField(TEXT("model"), MakeShared<FJsonValueNull>());
        }
        else
        {
            Params->SetStringField(TEXT("model"), Model);
        }
        GNyraSupervisor->SendRequest(TEXT("settings/set-model"), Params);
    }
    OnModelChanged.ExecuteIfBound(Model);
    Invalidate(EInvalidateWidget::Paint);   // WR-08
}

void SNyraModelSelector::RefreshFromHost()
{
    if (!GNyraSupervisor.IsValid()) return;
    TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
    Params->SetStringField(TEXT("conversation_id"), ConversationId);
    GNyraSupervisor->SendRequest(TEXT("settings/get-model"), Params);
    // Response handling lives in the panel's response router — this widget
    // is fire-and-forget; the panel updates CurrentModel via PinModel when
    // the response lands.
}

FReply SNyraModelSelector::HandleClicked() { return FReply::Handled(); }
