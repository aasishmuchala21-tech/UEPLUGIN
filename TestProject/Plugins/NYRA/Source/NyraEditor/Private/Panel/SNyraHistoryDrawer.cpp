// =============================================================================
// SNyraHistoryDrawer.cpp  (Phase 1 Plan 12b -- collapsed-left drawer)
// =============================================================================
//
// Implementation notes beyond the header:
//
// 1) RESPONSE CORRELATION. Plan 10's FOnSupervisorResponse is a single-bind
//    DECLARE_DELEGATE_OneParam. Converting to multicast would touch Plan 10's
//    FNyraSupervisor.h + FNyraSupervisor.cpp + ANY existing binders, none of
//    which currently use OnResponse in Phase 1. The drawer takes ownership
//    of OnResponse: it binds ONCE in Construct and routes per-rpc-id to
//    handlers stored in PendingResponses. If Phase 2 adds more OnResponse
//    consumers, the upgrade is `BindRaw` -> `Broadcast` on a multicast
//    delegate; no drawer code changes.
//
// 2) SAFE SELF-REFERENCE. Construct's lambda captures TWeakPtr<SNyraHistoryDrawer>
//    via SharedThis(this).ToWeakPtr() so a late response after destruction
//    cannot resurrect a dead widget. Every path pins the weak ptr before
//    touching member state.
//
// 3) COLLAPSED/EXPANDED WIDTHS. SBox::WidthOverride drives the layout; we
//    recycle the same SBox via RootBox and flip its override on toggle.
//    Collapsed = 24 px (just the toggle button + handle), expanded = 220 px.
// =============================================================================

#include "Panel/SNyraHistoryDrawer.h"
#include "Process/FNyraSupervisor.h"
#include "WS/FNyraJsonRpc.h"
#include "NyraLog.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Views/STableRow.h"
#include "Styling/AppStyle.h"

// Module-level supervisor singleton owned by FNyraEditorModule (Plan 10).
// Declared non-static in NyraEditorModule.cpp so this extern links.
extern TUniquePtr<class FNyraSupervisor> GNyraSupervisor;

#define LOCTEXT_NAMESPACE "NyraHistoryDrawer"

void SNyraHistoryDrawer::Construct(const FArguments& InArgs)
{
    bCollapsed = InArgs._bStartCollapsed;
    OnOpenDelegate = InArgs._OnOpenConversation;
    OnNewDelegate = InArgs._OnNewConversation;

    ListView = SNew(SListView<TSharedPtr<FNyraConversationSummary>>)
        .ListItemsSource(&Rows)
        .OnGenerateRow(this, &SNyraHistoryDrawer::GenerateRow)
        .OnMouseButtonClick(this, &SNyraHistoryDrawer::HandleRowClicked)
        .SelectionMode(ESelectionMode::Single);

    ChildSlot
    [
        SAssignNew(RootBox, SBox)
        .WidthOverride(bCollapsed ? 24.f : 220.f)
        [
            SNew(SBorder)
            .BorderImage(FAppStyle::GetBrush("ToolPanel.GroupBorder"))
            [
                SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight().Padding(4)
                [
                    SNew(SHorizontalBox)
                    + SHorizontalBox::Slot().AutoWidth()
                    [
                        SNew(SButton)
                        .Text(LOCTEXT("Toggle", "<>"))
                        .ToolTipText(LOCTEXT("ToggleTip", "Toggle history drawer"))
                        .OnClicked(this, &SNyraHistoryDrawer::HandleToggleCollapsed)
                    ]
                    + SHorizontalBox::Slot().FillWidth(1.0f).Padding(6, 0, 0, 0)
                    [
                        SNew(STextBlock)
                        .Text(LOCTEXT("Title", "Conversations"))
                        .Visibility(bCollapsed ? EVisibility::Collapsed : EVisibility::Visible)
                    ]
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(4)
                [
                    SNew(SButton)
                    .Text(LOCTEXT("NewConversation", "+ New Conversation"))
                    .Visibility(bCollapsed ? EVisibility::Collapsed : EVisibility::Visible)
                    .OnClicked(this, &SNyraHistoryDrawer::HandleNewConversationClicked)
                ]
                + SVerticalBox::Slot().FillHeight(1.0f)
                [
                    ListView.ToSharedRef()
                ]
            ]
        ]
    ];

    // R4.I2: OnResponse is now a multicast delegate. Store our subscription
    // handle so the destructor removes only our own binding, not every
    // other panel's drawer. PendingResponses routes envelopes to per-rpc-id
    // lambdas.
    if (GNyraSupervisor.IsValid())
    {
        ResponseHandle = GNyraSupervisor->OnResponse.AddRaw(this, &SNyraHistoryDrawer::HandleResponse);
    }
}

SNyraHistoryDrawer::~SNyraHistoryDrawer()
{
    // Remove only our own OnResponse subscription (R4.I2 multicast change).
    // A late response after tab close cannot fire HandleResponse on a dead
    // widget because the handle is gone; other panels' drawers stay subscribed.
    if (GNyraSupervisor.IsValid() && ResponseHandle.IsValid())
    {
        GNyraSupervisor->OnResponse.Remove(ResponseHandle);
    }
    PendingResponses.Empty();
}

FReply SNyraHistoryDrawer::HandleToggleCollapsed()
{
    bCollapsed = !bCollapsed;
    if (RootBox.IsValid())
    {
        RootBox->SetWidthOverride(bCollapsed ? 24.f : 220.f);
    }
    // Force the drawer to recalc layout so the hidden children re-evaluate
    // their EVisibility attributes on next paint.
    Invalidate(EInvalidateWidgetReason::Layout);
    return FReply::Handled();
}

FReply SNyraHistoryDrawer::HandleNewConversationClicked()
{
    OnNewDelegate.ExecuteIfBound();
    return FReply::Handled();
}

void SNyraHistoryDrawer::HandleRowClicked(TSharedPtr<FNyraConversationSummary> Item)
{
    if (!Item.IsValid() || !GNyraSupervisor.IsValid()) return;
    SelectedId = Item->Id;

    TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
    Params->SetStringField(
        TEXT("conversation_id"),
        Item->Id.ToString(EGuidFormats::DigitsWithHyphensLower));
    Params->SetNumberField(TEXT("limit"), 200);

    const int64 RpcId = GNyraSupervisor->SendRequest(TEXT("sessions/load"), Params);
    TWeakPtr<SNyraHistoryDrawer> WeakSelf = SharedThis(this).ToWeakPtr();
    PendingResponses.Add(RpcId,
        [WeakSelf](const FNyraJsonRpcEnvelope& Env)
        {
            TSharedPtr<SNyraHistoryDrawer> Self = WeakSelf.Pin();
            if (!Self.IsValid()) return;
            if (Env.Kind != ENyraEnvelopeKind::Response || !Env.Result.IsValid()) return;
            FGuid ConvId;
            TArray<TSharedPtr<FNyraMessage>> Messages;
            Self->IngestSessionsLoadResult(Env.Result, ConvId, Messages);
            Self->OnOpenDelegate.ExecuteIfBound(ConvId, Messages);
        });
}

void SNyraHistoryDrawer::SetSelected(const FGuid& ConvId)
{
    SelectedId = ConvId;
    if (ListView.IsValid())
    {
        ListView->RequestListRefresh();
    }
}

TSharedRef<ITableRow> SNyraHistoryDrawer::GenerateRow(
    TSharedPtr<FNyraConversationSummary> Item,
    const TSharedRef<STableViewBase>& OwnerTable)
{
    const bool bIsSelected = Item.IsValid() && Item->Id == SelectedId;
    return SNew(STableRow<TSharedPtr<FNyraConversationSummary>>, OwnerTable)
    .Padding(FMargin(6, 3))
    [
        SNew(STextBlock)
        .Text(FText::FromString(Item.IsValid() ? Item->Title : FString()))
        .ColorAndOpacity(
            bIsSelected ? FLinearColor(1.f, 1.f, 0.4f) : FLinearColor::White)
        .AutoWrapText(true)
    ];
}

void SNyraHistoryDrawer::Refresh()
{
    if (!GNyraSupervisor.IsValid()) return;
    TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
    Params->SetNumberField(TEXT("limit"), 50);

    const int64 RpcId = GNyraSupervisor->SendRequest(TEXT("sessions/list"), Params);
    TWeakPtr<SNyraHistoryDrawer> WeakSelf = SharedThis(this).ToWeakPtr();
    PendingResponses.Add(RpcId,
        [WeakSelf](const FNyraJsonRpcEnvelope& Env)
        {
            TSharedPtr<SNyraHistoryDrawer> Self = WeakSelf.Pin();
            if (!Self.IsValid()) return;
            if (Env.Kind != ENyraEnvelopeKind::Response || !Env.Result.IsValid()) return;
            Self->IngestSessionsListResult(Env.Result);
            // Subsequent-launch behaviour (per must_haves): auto-open the
            // most-recently-updated conversation. Rows[0] is guaranteed to
            // be the DESC-by-updated_at top row per Plan 12b SQL contract.
            if (Self->Rows.Num() > 0 && Self->Rows[0].IsValid())
            {
                Self->HandleRowClicked(Self->Rows[0]);
            }
        });
}

void SNyraHistoryDrawer::HandleResponse(const FNyraJsonRpcEnvelope& Env)
{
    if (!Env.bHasId) return;
    TFunction<void(const FNyraJsonRpcEnvelope&)> Handler;
    if (PendingResponses.RemoveAndCopyValue(Env.Id, Handler))
    {
        Handler(Env);
    }
    // If the id is not in the map the envelope is ignored (stale response or
    // response intended for another widget once Phase 2 adds consumers).
}

void SNyraHistoryDrawer::IngestSessionsListResult(const TSharedPtr<FJsonObject>& Result)
{
    Rows.Empty();
    if (!Result.IsValid()) return;
    const TArray<TSharedPtr<FJsonValue>>* Convs = nullptr;
    if (!Result->TryGetArrayField(TEXT("conversations"), Convs) || !Convs) return;
    for (const TSharedPtr<FJsonValue>& V : *Convs)
    {
        const TSharedPtr<FJsonObject>* Obj = nullptr;
        if (!V.IsValid() || !V->TryGetObject(Obj) || !Obj || !Obj->IsValid()) continue;
        TSharedPtr<FNyraConversationSummary> Row = MakeShared<FNyraConversationSummary>();
        FString IdStr;
        (*Obj)->TryGetStringField(TEXT("id"), IdStr);
        FGuid::Parse(IdStr, Row->Id);
        (*Obj)->TryGetStringField(TEXT("title"), Row->Title);
        double UpdatedAt = 0.0;
        (*Obj)->TryGetNumberField(TEXT("updated_at"), UpdatedAt);
        Row->UpdatedAtMs = static_cast<int64>(UpdatedAt);
        double MessageCount = 0.0;
        (*Obj)->TryGetNumberField(TEXT("message_count"), MessageCount);
        Row->MessageCount = static_cast<int32>(MessageCount);
        Rows.Add(Row);
    }
    if (ListView.IsValid())
    {
        ListView->RequestListRefresh();
    }
}

void SNyraHistoryDrawer::IngestSessionsLoadResult(
    const TSharedPtr<FJsonObject>& Result,
    FGuid& OutConvId,
    TArray<TSharedPtr<FNyraMessage>>& OutMessages)
{
    OutMessages.Reset();
    if (!Result.IsValid()) return;
    FString ConvIdStr;
    Result->TryGetStringField(TEXT("conversation_id"), ConvIdStr);
    FGuid::Parse(ConvIdStr, OutConvId);

    const TArray<TSharedPtr<FJsonValue>>* Msgs = nullptr;
    if (!Result->TryGetArrayField(TEXT("messages"), Msgs) || !Msgs) return;
    for (const TSharedPtr<FJsonValue>& V : *Msgs)
    {
        const TSharedPtr<FJsonObject>* Obj = nullptr;
        if (!V.IsValid() || !V->TryGetObject(Obj) || !Obj || !Obj->IsValid()) continue;
        TSharedPtr<FNyraMessage> M = MakeShared<FNyraMessage>();
        FString MidStr, Role;
        (*Obj)->TryGetStringField(TEXT("id"), MidStr);
        FGuid::Parse(MidStr, M->MessageId);
        M->ConversationId = OutConvId;
        (*Obj)->TryGetStringField(TEXT("role"), Role);
        if (Role == TEXT("assistant"))       M->Role = ENyraMessageRole::Assistant;
        else if (Role == TEXT("system"))     M->Role = ENyraMessageRole::System;
        else if (Role == TEXT("error"))      M->Role = ENyraMessageRole::Error;
        else                                  M->Role = ENyraMessageRole::User;
        (*Obj)->TryGetStringField(TEXT("content"), M->FinalContent);
        // Loaded messages are already complete -- mark Done so the render
        // path picks the SRichTextBlock + markdown branch (SNyraMessageList
        // MakeBodyWidget dispatches on Status).
        M->Status = ENyraMessageStatus::Done;
        // ReqId is zeroed -- loaded messages don't correlate with any
        // in-flight chat/send. Plan 12's chat/stream dispatch will not
        // touch these rows because FindByReqId compares FGuids and only
        // new outgoing requests get a non-zero ReqId.
        OutMessages.Add(M);
    }
}

void SNyraHistoryDrawer::SetConversationsForTest(
    const TArray<FNyraConversationSummary>& InRows)
{
    Rows.Empty();
    for (const FNyraConversationSummary& R : InRows)
    {
        Rows.Add(MakeShared<FNyraConversationSummary>(R));
    }
    if (ListView.IsValid())
    {
        ListView->RequestListRefresh();
    }
}

#undef LOCTEXT_NAMESPACE
