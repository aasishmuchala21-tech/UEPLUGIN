// =============================================================================
// SNyraChatPanel.h  (Phase 1 Plan 04 — Wave 1 nomad tab placeholder)
// =============================================================================
//
// Phase 1 placeholder widget hosted inside the NyraChatTab nomad tab.
// Renders "NYRA — not yet connected" centred in the panel so the user sees
// a real NYRA artifact immediately on opening the project, even without a
// working backend (RESEARCH §3.9 ENABLED_PLUGIN state machine: the panel is
// ALWAYS usable; there is no blank screen).
//
// Plan 12 (chat-panel-streaming-integration) replaces the Construct body
// with the full chat UI (message list, composer, attachment chips,
// streaming tokens, markdown) in place — no rename, no new class — so
// every NyraChatTab consumer locks to this symbol today.
// =============================================================================

#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/DeclarativeSyntaxSupport.h"

/**
 * Phase 1 placeholder for the NYRA chat panel. Renders
 * "NYRA — not yet connected" centred in the tab. Plan 12 replaces
 * the Construct body with the full chat UI (message list, composer,
 * attachment chips, streaming, markdown).
 */
class NYRAEDITOR_API SNyraChatPanel : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SNyraChatPanel) {}
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);
};
