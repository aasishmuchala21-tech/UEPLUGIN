// =============================================================================
// SNyraChatPanel.cpp  (Phase 1 Plan 12 -- chat panel streaming integration)
// =============================================================================
//
// REPLACES Plan 04's placeholder "NYRA -- not yet connected" widget with the
// full chat UI. Plan 04's canonical tab wiring (NyraEditorModule.cpp +
// NyraChatTabNames.h) is left UNTOUCHED -- this file only replaces the widget
// body hosted inside the already-registered nomad tab.
//
// Composition + wiring pattern documented at the top of SNyraChatPanel.h.
//
// chat/send params shape (per docs/JSONRPC.md 3.3):
//     {
//       "conversation_id": <guid-lower-with-hyphens>,
//       "req_id":          <guid-lower-with-hyphens>,
//       "content":         <user markdown text>,
//       "backend":         "gemma-local"   // Phase 1 default; subscription backends in Phase 2
//     }
//
// chat/cancel params shape (per docs/JSONRPC.md 3.5):
//     {
//       "conversation_id": <guid>,
//       "req_id":          <guid>
//     }
//
// chat/stream notification params dispatched by HandleNotification
// (per docs/JSONRPC.md 3.4):
//     {
//       "req_id":    <guid>,
//       "delta":     "...",              // incremental text (may be empty on done)
//       "done":      true|false,
//       "cancelled": true|false,         // optional, true if chat/cancel delivered
//       "error":     { "data": { "remediation": "..." } }   // optional error frame (D-11)
//     }
// =============================================================================

#include "Panel/SNyraChatPanel.h"
#include "Panel/SNyraMessageList.h"
#include "Panel/SNyraComposer.h"
#include "Panel/SNyraHistoryDrawer.h"
#include "Process/FNyraSupervisor.h"
#include "NyraLog.h"

#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBox.h"
#include "Dom/JsonObject.h"
#include "Styling/AppStyle.h"

// Module-level supervisor singleton owned by FNyraEditorModule (Plan 10).
// Declared non-static in NyraEditorModule.cpp so this extern link succeeds.
extern TUniquePtr<class FNyraSupervisor> GNyraSupervisor;

#define LOCTEXT_NAMESPACE "NyraChatPanel"

void SNyraChatPanel::Construct(const FArguments& InArgs)
{
    // CurrentConversationId is a sensible default only. SNyraHistoryDrawer
    // (Plan 12b) calls OpenConversation() after Construct finishes:
    //   - on FIRST-EVER editor launch (empty sessions table) -> drawer
    //     allocates a fresh GUID (matches this default)
    //   - on SUBSEQUENT launches -> drawer opens the most-recently-updated
    //     conversation and overwrites this value via OpenConversation.
    CurrentConversationId = FGuid::NewGuid();

    // Plan 12b layout: (drawer | existing VBox) in a SHorizontalBox. The
    // drawer owns its own width management via SBox::SetWidthOverride, so
    // the outer HBox just gives it AutoWidth and lets the message list +
    // composer fill the remaining width.
    ChildSlot
    [
        SNew(SHorizontalBox)
        + SHorizontalBox::Slot().AutoWidth()
        [
            SAssignNew(HistoryDrawer, SNyraHistoryDrawer)
            .bStartCollapsed(true)
            .OnOpenConversation(FOnHistoryOpenConversation::CreateLambda(
                [this](const FGuid& ConvId,
                       const TArray<TSharedPtr<FNyraMessage>>& Msgs)
                {
                    // Clear the current rows before repopulating so
                    // switching conversations does not bleed previous
                    // content into the new conversation. (Redundant with
                    // OpenConversation's own Clear, but explicit here for
                    // readability of the drawer-driven flow.)
                    if (MessageList.IsValid()) MessageList->ClearMessages();
                    this->OpenConversation(ConvId, Msgs);
                    if (HistoryDrawer.IsValid()) HistoryDrawer->SetSelected(ConvId);
                }))
            .OnNewConversation(FOnHistoryNewConversation::CreateLambda(
                [this]()
                {
                    if (MessageList.IsValid()) MessageList->ClearMessages();
                    const FGuid NewId = FGuid::NewGuid();
                    this->OpenConversation(NewId, TArray<TSharedPtr<FNyraMessage>>());
                    if (HistoryDrawer.IsValid()) HistoryDrawer->SetSelected(NewId);
                }))
        ]
        + SHorizontalBox::Slot().FillWidth(1.0f)
        [
            SNew(SVerticalBox)
            + SVerticalBox::Slot().FillHeight(1.0f)
            [
                SAssignNew(MessageList, SNyraMessageList)
                .OnCancel(FOnMessageCancel::CreateRaw(this, &SNyraChatPanel::OnMessageCancel))
            ]
            + SVerticalBox::Slot().AutoHeight().Padding(6)
            [
                SAssignNew(Composer, SNyraComposer)
                .OnSubmit(FOnComposerSubmit::CreateRaw(this, &SNyraChatPanel::OnComposerSubmit))
            ]
        ]
    ];

    // Bind to supervisor notifications if available. The supervisor lives
    // as a module-level TUniquePtr in FNyraEditorModule -- it's created
    // before any SNyraChatPanel Construct runs (StartupModule registers
    // the tab AFTER GNyraSupervisor is populated).
    if (GNyraSupervisor.IsValid())
    {
        GNyraSupervisor->OnNotification.BindRaw(this, &SNyraChatPanel::HandleNotification);
    }

    // Populate the history drawer from SQLite. On first-ever launch
    // (no rows persisted), the drawer ingests an empty list and our
    // default fresh-FGuid CurrentConversationId stays in place. On
    // subsequent launches the drawer's Refresh() auto-opens the
    // most-recently-updated conversation and overwrites
    // CurrentConversationId via the OnOpenConversation lambda above.
    // Safe to call unconditionally: Refresh no-ops if GNyraSupervisor
    // is not yet valid.
    if (HistoryDrawer.IsValid())
    {
        HistoryDrawer->Refresh();
    }
}

SNyraChatPanel::~SNyraChatPanel()
{
    // Break the notification binding on destruct so dangling TSharedRef to
    // this widget doesn't fire HandleNotification after the tab is closed.
    if (GNyraSupervisor.IsValid())
    {
        GNyraSupervisor->OnNotification.Unbind();
    }
}

void SNyraChatPanel::OnComposerSubmit(const FString& Text, const TArray<FNyraAttachmentRef>& Attachments)
{
    if (!GNyraSupervisor.IsValid() || !MessageList.IsValid()) return;

    // Append user message locally with terminal status so the list renders
    // it immediately without going through the streaming pipeline.
    TSharedPtr<FNyraMessage> UserMsg = MakeShared<FNyraMessage>();
    UserMsg->MessageId = FGuid::NewGuid();
    UserMsg->ConversationId = CurrentConversationId;
    UserMsg->ReqId = FGuid::NewGuid();
    UserMsg->Role = ENyraMessageRole::User;
    UserMsg->Status = ENyraMessageStatus::Done;
    UserMsg->FinalContent = Text;
    UserMsg->Attachments = Attachments;
    MessageList->AppendMessage(UserMsg);

    // Append assistant placeholder row; REUSE the user's ReqId so
    // HandleNotification's FindByReqId routes chat/stream deltas to this row.
    TSharedPtr<FNyraMessage> AssistantMsg = MakeShared<FNyraMessage>();
    AssistantMsg->MessageId = FGuid::NewGuid();
    AssistantMsg->ConversationId = CurrentConversationId;
    AssistantMsg->ReqId = UserMsg->ReqId;
    AssistantMsg->Role = ENyraMessageRole::Assistant;
    AssistantMsg->Status = ENyraMessageStatus::Streaming;
    MessageList->AppendMessage(AssistantMsg);

    // Fire chat/send request. See file header for params shape.
    TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
    Params->SetStringField(TEXT("conversation_id"), CurrentConversationId.ToString(EGuidFormats::DigitsWithHyphensLower));
    Params->SetStringField(TEXT("req_id"),          UserMsg->ReqId.ToString(EGuidFormats::DigitsWithHyphensLower));
    Params->SetStringField(TEXT("content"),         Text);
    Params->SetStringField(TEXT("backend"),         TEXT("gemma-local"));
    GNyraSupervisor->SendRequest(TEXT("chat/send"), Params);
}

void SNyraChatPanel::OnMessageCancel(const TSharedPtr<FNyraMessage>& Msg)
{
    if (!GNyraSupervisor.IsValid() || !Msg.IsValid()) return;
    TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
    Params->SetStringField(TEXT("conversation_id"), Msg->ConversationId.ToString(EGuidFormats::DigitsWithHyphensLower));
    Params->SetStringField(TEXT("req_id"),          Msg->ReqId.ToString(EGuidFormats::DigitsWithHyphensLower));
    GNyraSupervisor->SendNotification(TEXT("chat/cancel"), Params);
}

void SNyraChatPanel::HandleNotification(const FNyraJsonRpcEnvelope& Env)
{
    if (Env.Method != TEXT("chat/stream") || !Env.Params.IsValid() || !MessageList.IsValid()) return;

    FString ReqIdStr;
    if (!Env.Params->TryGetStringField(TEXT("req_id"), ReqIdStr)) return;
    FGuid ReqId;
    FGuid::Parse(ReqIdStr, ReqId);

    FString Delta;
    Env.Params->TryGetStringField(TEXT("delta"), Delta);
    bool bDone = false;
    Env.Params->TryGetBoolField(TEXT("done"), bDone);
    bool bCancelled = false;
    Env.Params->TryGetBoolField(TEXT("cancelled"), bCancelled);

    // Error frame extraction (D-11): error.data.remediation rendered verbatim.
    FString Remediation;
    const TSharedPtr<FJsonObject>* ErrObj = nullptr;
    if (Env.Params->TryGetObjectField(TEXT("error"), ErrObj) && ErrObj && ErrObj->IsValid())
    {
        const TSharedPtr<FJsonObject>* DataObj = nullptr;
        if ((*ErrObj)->TryGetObjectField(TEXT("data"), DataObj) && DataObj && DataObj->IsValid())
        {
            (*DataObj)->TryGetStringField(TEXT("remediation"), Remediation);
        }
    }

    if (!Delta.IsEmpty())
    {
        MessageList->UpdateMessageStreaming(ReqId, Delta);
    }
    if (bDone)
    {
        if (TSharedPtr<FNyraMessage> M = MessageList->FindByReqId(ReqId))
        {
            const FString Buf = M->StreamingBuffer;
            MessageList->FinalizeMessage(ReqId, Buf, bCancelled, Remediation);
        }
    }
}

void SNyraChatPanel::OpenConversation(const FGuid& ConversationId, const TArray<TSharedPtr<FNyraMessage>>& Messages)
{
    // Called from SNyraHistoryDrawer (Plan 12b). Replaces the current
    // conversation id and rebuilds the message list from a sessions/load
    // snapshot. Pass an empty Messages array to start a fresh conversation.
    CurrentConversationId = ConversationId.IsValid() ? ConversationId : FGuid::NewGuid();

    if (MessageList.IsValid())
    {
        // Clear existing rows before repopulating so switching conversations
        // doesn't append to the previous conversation's rows.
        MessageList->ClearMessages();
        for (const TSharedPtr<FNyraMessage>& M : Messages)
        {
            MessageList->AppendMessage(M);
        }
    }

    OnConversationSelected.ExecuteIfBound(CurrentConversationId);
}

#undef LOCTEXT_NAMESPACE
