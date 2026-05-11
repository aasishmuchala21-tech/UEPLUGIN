// SNyraToolsSidebar.cpp - Phase 14-I Aura-parity Tools & Agents sidebar.
// Build status: pending_manual_verification.

#include "Panel/SNyraToolsSidebar.h"

#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
    const FLinearColor Dominant(0.02f, 0.02f, 0.03f, 1.0f);
    const FLinearColor TextDim(0.6f, 0.6f, 0.65f, 1.0f);
}

void SNyraToolsSidebar::Construct(const FArguments& InArgs)
{
    OnPromptSelected = InArgs._OnPromptSelected;

    ChildSlot
    [
        SNew(SBorder)
        .BorderImage(FAppStyle::Get().GetBrush("ToolPanel.GroupBorder"))
        .BorderBackgroundColor(Dominant)
        [
            SNew(SScrollBox)
            // Authoring tools (Phase 8 PARITY)
            + SScrollBox::Slot().Padding(2)
            [
                SNew(STextBlock)
                .ColorAndOpacity(TextDim)
                .Text(FText::FromString(TEXT("Authoring agents")))
            ]
            + SScrollBox::Slot()
            [
                MakeRow(
                    TEXT("Behavior Tree"),
                    TEXT("Plan a Behavior Tree for the selected enemy actor."),
                    TEXT("Phase 8 PARITY-03 — uses tools/bt_tools.py"))
            ]
            + SScrollBox::Slot()
            [
                MakeRow(
                    TEXT("Niagara VFX"),
                    TEXT("Create a Niagara system for sparks coming off a hit impact."),
                    TEXT("Phase 8 PARITY-05 — uses tools/niagara_tools.py"))
            ]
            + SScrollBox::Slot()
            [
                MakeRow(
                    TEXT("Animation Blueprint"),
                    TEXT("Create an Animation Blueprint with idle/walk/run state machine."),
                    TEXT("Phase 8 PARITY-07 — uses tools/animbp_tools.py"))
            ]
            + SScrollBox::Slot()
            [
                MakeRow(
                    TEXT("MetaSound"),
                    TEXT("Wrap the selected sound in a MetaSound with volume + pitch controls."),
                    TEXT("Phase 8 PARITY-08 — uses tools/metasound_tools.py"))
            ]
            + SScrollBox::Slot()
            [
                MakeRow(
                    TEXT("C++ Live Coding"),
                    TEXT("Add a Velocity component to the selected actor and recompile via Live Coding."),
                    TEXT("Phase 8 PARITY-02 — uses tools/cpp_authoring_tools.py"))
            ]
            + SScrollBox::Slot()
            [
                MakeRow(
                    TEXT("Performance profiling"),
                    TEXT("Profile this level for 30 seconds and report the top 5 hot spots."),
                    TEXT("Phase 8 PARITY-06 — uses tools/perf_tools.py"))
            ]
            + SScrollBox::Slot()
            [
                MakeRow(
                    TEXT("Material"),
                    TEXT("Create a stone-wall material with three texture layers."),
                    TEXT("Phase 8 PARITY-04 — uses tools/material_tools.py"))
            ]
            // Whole-project agents (Phase 13–14 Tier 2 moats)
            + SScrollBox::Slot().Padding(2, 12, 2, 2)
            [
                SNew(STextBlock)
                .ColorAndOpacity(TextDim)
                .Text(FText::FromString(TEXT("Whole-project agents")))
            ]
            + SScrollBox::Slot()
            [
                MakeRow(
                    TEXT("Asset Hygiene"),
                    TEXT("Run Asset Hygiene under /Game and list unused assets + naming-convention violations."),
                    TEXT("Phase 13-C — uses tools/asset_hygiene.py"))
            ]
            + SScrollBox::Slot()
            [
                MakeRow(
                    TEXT("Perf Budget check"),
                    TEXT("Measure the current level and check it against the persisted perf budget."),
                    TEXT("Phase 13-E — uses tools/perf_budget.py"))
            ]
            + SScrollBox::Slot()
            [
                MakeRow(
                    TEXT("Crash RCA"),
                    TEXT("Walk Saved/Crashes/, dedupe by signature, and summarise."),
                    TEXT("Phase 14-E — uses tools/crash_rca.py"))
            ]
            + SScrollBox::Slot()
            [
                MakeRow(
                    TEXT("Test scaffolding"),
                    TEXT("Scan NyraEditor module headers and emit Spec.cpp scaffolds for any UCLASS without one."),
                    TEXT("Phase 14-F — uses tools/test_gen.py"))
            ]
            + SScrollBox::Slot()
            [
                MakeRow(
                    TEXT("Doc-from-code"),
                    TEXT("Generate Markdown docs for the NyraEditor module's public headers."),
                    TEXT("Phase 14-G — uses tools/doc_from_code.py"))
            ]
            + SScrollBox::Slot()
            [
                MakeRow(
                    TEXT("Replication scaffold"),
                    TEXT("Scaffold replication for the selected actor: list which UPROPERTY entries should replicate."),
                    TEXT("Phase 14-H — uses tools/replication_scaffolder.py"))
            ]
        ]
    ];
}

TSharedRef<SWidget> SNyraToolsSidebar::MakeRow(
    const FString& Label, const FString& PromptText, const FString& Tooltip)
{
    return SNew(SButton)
        .Text(FText::FromString(Label))
        .ToolTipText(FText::FromString(Tooltip))
        .OnClicked_Lambda([this, PromptText]() { return HandleClicked(PromptText); });
}

FReply SNyraToolsSidebar::HandleClicked(FString PromptText)
{
    OnPromptSelected.ExecuteIfBound(PromptText);
    Invalidate(EInvalidateWidget::Paint);   // WR-08
    return FReply::Handled();
}
