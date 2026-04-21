// =============================================================================
// NyraChatTabNames.h  (Phase 1 Plan 04 — Wave 1 nomad tab scaffold)
// =============================================================================
//
// Canonical FName constants for the NYRA chat tab registration and the Tools
// menu extension (CD-02). Consumed by:
//   - FNyraEditorModule::StartupModule / ShutdownModule   (tab + menu wiring)
//   - Nyra.Panel.TabSpawner automation test               (VALIDATION 1-04-01)
//
// Owning plan: 01-04-nomad-tab-placeholder-panel
// Downstream consumers: Plan 12 (chat-panel-streaming-integration) reuses
// Nyra::NyraChatTabId when it replaces SNyraChatPanel's Construct body.
// =============================================================================

#pragma once

#include "CoreMinimal.h"

namespace Nyra
{
    /** Tab manager id for the NYRA chat panel (registered in FNyraEditorModule::StartupModule). */
    inline const FName NyraChatTabId(TEXT("NyraChatTab"));

    /** Main editor tools menu name used to register the NYRA submenu. */
    inline const FName NyraToolsMenuExtensionPoint(TEXT("LevelEditor.MainMenu.Tools"));

    /** Section name inside the Tools menu. */
    inline const FName NyraMenuSectionName(TEXT("NYRA"));
}
