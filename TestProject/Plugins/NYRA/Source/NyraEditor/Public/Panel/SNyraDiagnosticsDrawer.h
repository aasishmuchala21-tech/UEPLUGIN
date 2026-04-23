// =============================================================================
// SNyraDiagnosticsDrawer.h  (Phase 1 Plan 13)
// =============================================================================
//
// Collapsed-by-default drawer widget mounted BELOW the composer in
// SNyraChatPanel. Shows the tail of the current-day NyraHost log file on
// demand.
//
// Per RESEARCH Open Q 6 (resolved): the `diagnostics/tail` JSON-RPC method
// is SKIPPED in Phase 1. The drawer reads the log file directly from disk
// via FFileHelper::LoadFileToStringArray. This keeps the Python wire
// surface minimal for Phase 1 and matches D-16 (log location under
// <ProjectSaved>/NYRA/logs/).
//
// Log path convention:
//   <ProjectDir>/Saved/NYRA/logs/nyrahost-YYYY-MM-DD.log
//
// LogFilePath() is exposed as a static so SNyraChatPanel can reuse it for
// the banner's [Open log] button without duplicating path construction.
// =============================================================================

#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/DeclarativeSyntaxSupport.h"

class NYRAEDITOR_API SNyraDiagnosticsDrawer : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SNyraDiagnosticsDrawer) {}
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);

    /** Refresh the tail from disk (last 100 lines). No-op if the log file
     *  does not yet exist -- shows a placeholder string in that case. */
    void RefreshFromDisk();

    /** Returns <ProjectDir>/Saved/NYRA/logs/nyrahost-<today-UTC>.log. Used
     *  by SNyraChatPanel to point [Open log] at the logs directory. */
    static FString LogFilePath();

private:
    FReply HandleToggle();
    FReply HandleRefresh();

    TSharedPtr<class SMultiLineEditableTextBox> TailBox;
    TSharedPtr<class SBox> ContentContainer;
    bool bExpanded = false;
};
