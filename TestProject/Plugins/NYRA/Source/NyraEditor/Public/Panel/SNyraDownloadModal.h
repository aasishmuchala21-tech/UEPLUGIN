// =============================================================================
// SNyraDownloadModal.h  (Phase 1 Plan 13 -- first-run Gemma download UX)
// =============================================================================
//
// Modal-style widget mounted as a centred overlay inside SNyraChatPanel's
// message-list SOverlay. Consumes `diagnostics/download-progress` WS
// notifications (docs/JSONRPC.md §3.7) emitted by Plan 09's Python
// DownloadHandlers and renders a progress bar + status text + cancel
// button.
//
// Progress-frame lifecycle (matches Plan 09 handler flow):
//   status="downloading" -> update progress bar + "Downloading N%"
//   status="verifying"   -> status text "Verifying SHA256..."
//   status="done"        -> status text "Done!" (user dismisses manually)
//   status="error"       -> render error.data.remediation from Plan 05
//
// The OnCancelled delegate fires when the user clicks Cancel. Phase 1's
// Python side has NO download-cancel endpoint -- the modal just closes
// locally; the background asyncio.Task in NyraHost runs to completion or
// error naturally. Documented limitation in SUMMARY.md.
// =============================================================================

#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "WS/FNyraJsonRpc.h"

DECLARE_DELEGATE(FOnDownloadCancelled);

class NYRAEDITOR_API SNyraDownloadModal : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SNyraDownloadModal) {}
        SLATE_EVENT(FOnDownloadCancelled, OnCancelled)
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);

    /** Feed a diagnostics/download-progress params object (Env.Params). */
    void OnProgress(const TSharedPtr<FJsonObject>& Params);

    void Show();
    void Hide();
    bool IsShown() const { return bVisible; }

private:
    FReply HandleCancel();

    TSharedPtr<class SProgressBar> ProgressBar;
    TSharedPtr<class STextBlock> StatusText;
    TSharedPtr<class STextBlock> BytesText;
    TSharedPtr<class SBox> RootContainer;
    int64 BytesDone = 0;
    int64 BytesTotal = 0;
    FString CurrentStatus;
    FOnDownloadCancelled OnCancelledDelegate;
    bool bVisible = false;
};
