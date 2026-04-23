// =============================================================================
// SNyraHistoryDrawer.h  (Phase 1 Plan 12b -- collapsed-left conversation drawer)
// =============================================================================
//
// CD-05 history navigator. Collapsed by default (~24 px handle) and expandable
// to ~220 px; lists conversations fetched via the `sessions/list` JSON-RPC
// request (Plan 12b Python handler; docs/JSONRPC.md 3.8). Selecting a row
// issues `sessions/load` (3.9), parses the response into FNyraMessage rows,
// and fires OnOpenConversation so SNyraChatPanel::OpenConversation can swap
// the message list. A [+ New Conversation] button fires OnNewConversation so
// the panel can allocate a fresh client-side FGuid and clear the list.
//
// Mounted by SNyraChatPanel::Construct inside a SHorizontalBox alongside the
// existing VBox (message list + composer). The drawer + panel live in the
// same widget tree so delegate bindings are lifetime-safe via SharedThis.
//
// Correlation approach (Plan 12b <action> block):
//   The supervisor's OnResponse is a single-binding FOnSupervisorResponse
//   (DECLARE_DELEGATE_OneParam, Plan 10). Rather than converting that to a
//   multicast delegate (touches Plan 10 files) or routing through a central
//   pump in SNyraChatPanel (extra indirection), this widget binds OnResponse
//   ONCE in Construct and dispatches incoming envelopes via an internal
//   TMap<int64, TFunction<>> keyed by rpc id. Each SendRequest records the
//   id and its matching handler; the bound lambda dispatches + erases on
//   match. Plan 13+ can replace this with a multicast upgrade if additional
//   widgets need OnResponse -- for Phase 1 the drawer is the sole consumer.
//
// Thread safety: GameThread-only. GNyraSupervisor marshals responses back
// to GameThread before firing OnResponse (Plan 10 contract).
// =============================================================================

#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/Views/SListView.h"
#include "Panel/NyraMessageModel.h"

class FJsonObject;
struct FNyraJsonRpcEnvelope;

/** Conversation metadata row populated from sessions/list responses. */
struct NYRAEDITOR_API FNyraConversationSummary
{
    FGuid Id;
    FString Title;
    int64 UpdatedAtMs = 0;
    int32 MessageCount = 0;
};

/** Fired when the user picks a conversation row in the drawer. Delivers the
 *  conversation id + parsed message snapshot so SNyraChatPanel::OpenConversation
 *  can rebuild the message list. Pass an empty Messages array to start fresh. */
DECLARE_DELEGATE_TwoParams(FOnHistoryOpenConversation,
    const FGuid& /*ConvId*/,
    const TArray<TSharedPtr<FNyraMessage>>& /*Messages*/);

/** Fired when the user clicks [+ New Conversation]. The panel allocates a
 *  fresh client-side FGuid and calls OpenConversation(NewGuid, {}) to reset. */
DECLARE_DELEGATE(FOnHistoryNewConversation);

class NYRAEDITOR_API SNyraHistoryDrawer : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SNyraHistoryDrawer)
        : _bStartCollapsed(true)
    {}
        SLATE_ARGUMENT(bool, bStartCollapsed)
        SLATE_EVENT(FOnHistoryOpenConversation, OnOpenConversation)
        SLATE_EVENT(FOnHistoryNewConversation, OnNewConversation)
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);
    virtual ~SNyraHistoryDrawer() override;

    /** Issue a sessions/list request. On matching response, populate Rows
     *  and auto-open the most-recently-updated conversation (per CD-05
     *  "subsequent launches auto-open most-recent"). Safe to call again to
     *  refresh after a new conversation is persisted. No-op if the supervisor
     *  singleton is not yet initialised. */
    void Refresh();

    /** Test hook: populate Rows directly without going through the WS. */
    void SetConversationsForTest(const TArray<FNyraConversationSummary>& Rows);

    int32 NumConversations() const { return Rows.Num(); }
    void SetSelected(const FGuid& ConvId);

private:
    TSharedRef<ITableRow> GenerateRow(
        TSharedPtr<FNyraConversationSummary> Item,
        const TSharedRef<STableViewBase>& OwnerTable);
    FReply HandleNewConversationClicked();
    FReply HandleToggleCollapsed();
    void HandleRowClicked(TSharedPtr<FNyraConversationSummary> Item);

    /** Central response pump -- bound ONCE in Construct. Dispatches to the
     *  per-request handler stored in PendingResponses via rpc id. */
    void HandleResponse(const FNyraJsonRpcEnvelope& Env);

    /** Parse sessions/list response result into Rows. */
    void IngestSessionsListResult(const TSharedPtr<FJsonObject>& Result);

    /** Parse sessions/load response result into a message array for
     *  OpenConversation. Non-const because it uses the drawer's logging
     *  context; otherwise purely functional. */
    void IngestSessionsLoadResult(
        const TSharedPtr<FJsonObject>& Result,
        FGuid& OutConvId,
        TArray<TSharedPtr<FNyraMessage>>& OutMessages);

    TArray<TSharedPtr<FNyraConversationSummary>> Rows;
    TSharedPtr<SListView<TSharedPtr<FNyraConversationSummary>>> ListView;
    FGuid SelectedId;
    bool bCollapsed = true;
    FOnHistoryOpenConversation OnOpenDelegate;
    FOnHistoryNewConversation OnNewDelegate;

    /** Per-rpc-id response handlers -- keyed by the id returned from
     *  GNyraSupervisor->SendRequest. The bound OnResponse lambda dispatches
     *  + erases on match. Envelopes whose id is not in the map are ignored
     *  (some other widget or a stale response). */
    TMap<int64, TFunction<void(const FNyraJsonRpcEnvelope&)>> PendingResponses;

    /** Holds the Construct-time SCompoundWidget root so toggling collapsed
     *  can invalidate layout without a full widget tree rebuild. */
    TSharedPtr<class SBox> RootBox;
};
