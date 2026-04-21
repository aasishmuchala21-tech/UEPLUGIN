// =============================================================================
// SNyraChatPanel.cpp  (Phase 1 Plan 04 — Wave 1 nomad tab placeholder)
// =============================================================================
//
// Construct renders the "NYRA — not yet connected" placeholder centred in
// the panel. Uses only Slate + AppStyle primitives (no backend deps) so the
// widget compiles in isolation and is safe to host inside the nomad tab on
// first editor launch.
//
// LOCTEXT key schema (locked — automation test asserts these):
//   - NotConnectedHeader : "NYRA — not yet connected"
//   - NotConnectedSub    : "Plan 12 replaces this panel with the full chat UI."
//
// Plan 12 swaps the ChildSlot body for the full chat UI (SScrollBox +
// SMultiLineEditableTextBox + streaming SRichTextBlock). The LOCTEXT
// namespace "NyraChatPanel" stays for Plan 12 to append new keys.
// =============================================================================

#include "Panel/SNyraChatPanel.h"

#include "Widgets/Layout/SBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"
#include "Styling/AppStyle.h"

#define LOCTEXT_NAMESPACE "NyraChatPanel"

void SNyraChatPanel::Construct(const FArguments& InArgs)
{
    ChildSlot
    [
        SNew(SBox)
        .HAlign(HAlign_Center)
        .VAlign(VAlign_Center)
        .Padding(32.f)
        [
            SNew(SVerticalBox)
            + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
            [
                SNew(STextBlock)
                .Text(LOCTEXT("NotConnectedHeader", "NYRA — not yet connected"))
                .Font(FAppStyle::GetFontStyle(TEXT("BoldFont")))
            ]
            + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 12, 0, 0)
            [
                SNew(STextBlock)
                .Text(LOCTEXT("NotConnectedSub",
                    "Plan 12 replaces this panel with the full chat UI."))
                .ColorAndOpacity(FLinearColor(0.7f, 0.7f, 0.7f))
            ]
        ]
    ];
}

#undef LOCTEXT_NAMESPACE
