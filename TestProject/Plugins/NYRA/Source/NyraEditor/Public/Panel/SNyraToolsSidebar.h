// SNyraToolsSidebar.h - Phase 14-I Aura-parity Tools & Agents sidebar.
// Build status: pending_manual_verification (no UE toolchain).
//
// Surfaces the Phase 8 PARITY tools (BT, Niagara, AnimBP, MetaSound,
// C++ Live Coding, Performance Profiling, Material Agent) plus the
// Phase 13 whole-project agents (Asset Hygiene, Perf Budget) plus the
// Phase 14 user-installable tools as one click-discovery panel along
// the right edge of SNyraChatPanel.
//
// Each row is a button that fires a JSON-RPC method seeding the chat
// with a templated prompt — eg "Run Asset Hygiene under /Game" — so
// the user doesn't have to remember the method name. Click is
// shorthand for "compose this prompt for me + send it".

#pragma once

#include "CoreMinimal.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SCompoundWidget.h"

DECLARE_DELEGATE_OneParam(FOnNyraToolPromptSelected, const FString& /*PromptText*/);

class NYRAEDITOR_API SNyraToolsSidebar : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SNyraToolsSidebar) {}
        SLATE_EVENT(FOnNyraToolPromptSelected, OnPromptSelected)
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);

private:
    FReply HandleClicked(FString PromptText);
    TSharedRef<class SWidget> MakeRow(const FString& Label, const FString& PromptText, const FString& Tooltip);

    FOnNyraToolPromptSelected OnPromptSelected;
};
