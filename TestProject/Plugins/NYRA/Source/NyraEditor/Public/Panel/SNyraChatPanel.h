// =============================================================================
// SNyraChatPanel.h  (Phase 1 Plan 12 -- chat panel streaming integration)
// =============================================================================
//
// Top-level chat panel hosted inside the NyraChatTab nomad tab (registered
// by FNyraEditorModule::StartupModule per Plan 04).
//
// Composition:
//   SVerticalBox
//     Slot[FillHeight=1.0]  SNyraMessageList   (message rows, streaming swap)
//     Slot[AutoHeight]      SNyraComposer      (textbox + chips + [+] + [Send])
//
// Wiring:
//   - OnComposerSubmit -> GNyraSupervisor->SendRequest("chat/send", { ... })
//   - GNyraSupervisor->OnNotification -> HandleNotification -> dispatch
//     chat/stream to SNyraMessageList::UpdateMessageStreaming / FinalizeMessage
//   - OnMessageCancel -> GNyraSupervisor->SendNotification("chat/cancel", { ... })
//
// Conversation id management (Phase 1):
//   - CurrentConversationId seeded on Construct with a fresh FGuid (sensible
//     default for first-ever open).
//   - SNyraHistoryDrawer (Plan 12b) overrides this via OpenConversation()
//     when the user picks a saved conversation OR creates a fresh one.
//   - Plan 12 alone does NOT persist conversation_id across editor restarts;
//     that is Plan 12b's SQLite sessions-table responsibility.
//
// Streaming strategy: plain STextBlock during stream, swap to SRichTextBlock
// on chat/stream done:true. SNyraMessageList::GenerateRow handles the swap;
// this panel just wires the notification pump.
//
// Thread safety: GameThread-only. GNyraSupervisor->OnNotification fires on
// the WS thread and Plan 10 marshals back to GameThread before invoking
// delegates, so HandleNotification is safe to mutate Slate directly.
// =============================================================================

#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Panel/NyraMessageModel.h"
#include "WS/FNyraJsonRpc.h"

class SNyraMessageList;
class SNyraComposer;

/** Fired after SNyraChatPanel::OpenConversation completes so the history
 *  drawer (Plan 12b) can sync its selection highlight. */
DECLARE_DELEGATE_OneParam(FOnConversationSelected, const FGuid& /*ConversationId*/);

class NYRAEDITOR_API SNyraChatPanel : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SNyraChatPanel) {}
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);
    virtual ~SNyraChatPanel() override;

    /** Handler bound to FNyraSupervisor::OnNotification. Dispatches
     *  chat/stream frames to the message list (delta + done + cancelled
     *  + error.data.remediation). */
    void HandleNotification(const FNyraJsonRpcEnvelope& Env);

    /**
     * Entry point driven by SNyraHistoryDrawer (Plan 12b) when the user
     * picks a conversation. Replaces CurrentConversationId and rebuilds
     * the message list from the supplied snapshot (from sessions/load).
     * Pass an empty Messages array to start a fresh conversation -- Plan
     * 12b's [+ New Conversation] button allocates a new FGuid and calls
     * this with empty.
     */
    void OpenConversation(const FGuid& ConversationId, const TArray<TSharedPtr<FNyraMessage>>& Messages);

    /** Accessor so the drawer (Plan 12b) can know which conversation is
     *  currently live (used to highlight the matching row). */
    FGuid GetCurrentConversationId() const { return CurrentConversationId; }

    /** Fired after OpenConversation completes. Plan 12b's history drawer
     *  binds this to update its selection highlight. */
    FOnConversationSelected OnConversationSelected;

private:
    void OnComposerSubmit(const FString& Text, const TArray<FNyraAttachmentRef>& Attachments);
    void OnMessageCancel(const TSharedPtr<FNyraMessage>& Msg);

    TSharedPtr<SNyraMessageList> MessageList;
    TSharedPtr<SNyraComposer> Composer;
    FGuid CurrentConversationId;  // default on first-ever editor launch; Plan 12b drawer overwrites via OpenConversation
    FDelegateHandle NotificationHandle;
};
