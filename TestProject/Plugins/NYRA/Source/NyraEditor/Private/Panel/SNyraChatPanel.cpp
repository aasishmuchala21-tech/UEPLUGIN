// =============================================================================
// SNyraChatPanel.cpp  (Phase 1 Plans 12 + 12b + 13 -- superset)
// =============================================================================
//
// REPLACES Plan 04's placeholder "NYRA -- not yet connected" widget with the
// full chat UI. Plan 04's canonical tab wiring (NyraEditorModule.cpp +
// NyraChatTabNames.h) is left UNTOUCHED -- this file only replaces the widget
// body hosted inside the already-registered nomad tab.
//
// Composition + wiring pattern documented at the top of SNyraChatPanel.h.
//
// Plan layering (all preserved verbatim below):
//   - Plan 12  : SNyraMessageList + SNyraComposer + chat/send + chat/stream
//                + chat/cancel + OpenConversation + GetCurrentConversationId
//   - Plan 12b : SNyraHistoryDrawer left column via SHorizontalBox two-column
//                layout + OnOpenConversation / OnNewConversation bridge lambdas
//                + HistoryDrawer->Refresh() at end of Construct
//   - Plan 13  : SNyraBanner above MessageList + SNyraDownloadModal overlay on
//                MessageList + SNyraDiagnosticsDrawer below composer +
//                FNyraSupervisor OnStateChanged + OnUnstable bindings +
//                diagnostics/download-progress notification dispatch
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
//
// diagnostics/download-progress notification params (Plan 09, docs/JSONRPC.md 3.7):
//     {
//       "status":      "downloading"|"verifying"|"done"|"error",
//       "bytes_done":  <number>,
//       "bytes_total": <number>,
//       "error":       { "data": { "remediation": "..." } }  // only when status=="error"
//     }
// =============================================================================

#include "Panel/SNyraChatPanel.h"
#include "Panel/SNyraMessageList.h"
#include "Panel/SNyraComposer.h"
#include "Panel/SNyraHistoryDrawer.h"
#include "Panel/SNyraBanner.h"
#include "Panel/SNyraDownloadModal.h"
#include "Panel/SNyraDiagnosticsDrawer.h"
#include "Panel/SNyraBackendStatusStrip.h"
#include "Panel/SNyraModeToggle.h"
#include "Panel/SNyraModelSelector.h"
#include "Process/FNyraSupervisor.h"
#include "NyraLog.h"

#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Notifications/SNotificationList.h"
#include "Dom/JsonObject.h"
#include "Styling/AppStyle.h"
#include "Interfaces/IPluginManager.h"
#include "Misc/Paths.h"
#include "HAL/PlatformProcess.h"
#include "HAL/PlatformApplicationMisc.h"

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

    // Plan 12b layout: (drawer | right-column VBox) in a SHorizontalBox.
    // Plan 13 extends the right-column VBox to:
    //   [Banner][SOverlay(MessageList + DownloadModal)][Composer][Diagnostics]
    // so the banner is ABOVE the message list, the download modal floats
    // centred over the list, and the diagnostics drawer is BELOW the composer.
    // The drawer owns its own width management via SBox::SetWidthOverride, so
    // the outer HBox just gives it AutoWidth and lets the right VBox fill the
    // remaining width.
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
            // Plan 13: banner above the message list. Hidden by default
            // (Construct of SNyraBanner starts in Hidden state).
            + SVerticalBox::Slot().AutoHeight()
            [
                SAssignNew(Banner, SNyraBanner)
            ]
            // Plan 02-12: status strip between banner and message list
            + SVerticalBox::Slot().AutoHeight().Padding(4, 2)
            [
                SAssignNew(StatusStrip, SNyraBackendStatusStrip)
                    .OnClaudeClick_Lambda([this]() { OpenClaudePopover(); })
                    .OnGemmaClick_Lambda([this]() { OpenGemmaPopover(); })
                    .OnPrivacyClick_Lambda([this]() { OpenPrivacyPopover(); })
            ]
            // Phase 12-D: Aura-parity Ask/Plan/Agent toggle + per-conversation
            // model selector pill, sitting just under the backend status strip.
            // Both widgets fire JSON-RPC over GNyraSupervisor and are otherwise
            // self-contained — no per-message wiring needed in this panel.
            + SVerticalBox::Slot().AutoHeight().Padding(4, 2)
            [
                SNew(SHorizontalBox)
                + SHorizontalBox::Slot().AutoWidth().Padding(2)
                [
                    SAssignNew(ModeToggle, SNyraModeToggle)
                ]
                + SHorizontalBox::Slot().FillWidth(1.0f).Padding(2)
                + SHorizontalBox::Slot().AutoWidth().Padding(2)
                [
                    SAssignNew(ModelSelector, SNyraModelSelector)
                    .ConversationId_Lambda([this]() { return CurrentConversationId; })
                ]
            ]
            // Message list + download-modal overlay occupy the main fill area.
            + SVerticalBox::Slot().FillHeight(1.0f)
            [
                SNew(SOverlay)
                + SOverlay::Slot()
                [
                    SAssignNew(MessageList, SNyraMessageList)
                    .OnCancel(FOnMessageCancel::CreateRaw(this, &SNyraChatPanel::OnMessageCancel))
                ]
                + SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
                [
                    SAssignNew(DownloadModal, SNyraDownloadModal)
                    .OnCancelled(FOnDownloadCancelled::CreateLambda([]()
                    {
                        // Phase 1: Python side has no cancel endpoint for the
                        // downloader; the modal simply closes. The background
                        // asyncio.Task in NyraHost finishes or errors naturally.
                        // Documented limitation in SUMMARY.md.
                    }))
                ]
            ]
            + SVerticalBox::Slot().AutoHeight().Padding(6)
            [
                SAssignNew(Composer, SNyraComposer)
                .OnSubmit(FOnComposerSubmit::CreateRaw(this, &SNyraChatPanel::OnComposerSubmit))
            ]
            // Plan 13: diagnostics drawer below composer. Collapsed by default.
            + SVerticalBox::Slot().AutoHeight()
            [
                SAssignNew(Diagnostics, SNyraDiagnosticsDrawer)
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

        // Plan 13: state-machine banner wiring per RESEARCH §3.9 table.
        // Spawning/WaitingForHandshake/Connecting/Authenticating -> Info
        // Ready                                                   -> Hidden
        // Crashed (under 3-in-60s restart policy)                 -> Warning
        // (Unstable/OnUnstable handled separately below.)
        GNyraSupervisor->OnStateChanged.BindLambda([this](ENyraSupervisorState NewState)
        {
            if (!Banner.IsValid()) return;
            switch (NewState)
            {
            case ENyraSupervisorState::Spawning:
            case ENyraSupervisorState::WaitingForHandshake:
            case ENyraSupervisorState::Connecting:
            case ENyraSupervisorState::Authenticating:
                Banner->SetState(ENyraBannerKind::Info,
                    FText::FromString(TEXT("Setting up NYRA (~30s)")));
                break;
            case ENyraSupervisorState::Ready:
                Banner->Hide();
                break;
            case ENyraSupervisorState::Crashed:
                Banner->SetState(ENyraBannerKind::Warning,
                    FText::FromString(TEXT("NyraHost crashed -- restarting")));
                break;
            default:
                break;
            }
        });

        // Plan 13: unstable-banner wiring. OnUnstable fires after the 3-in-60s
        // restart policy trips in FNyraSupervisor (Plan 10). Error kind banner
        // with [Restart] + [Open log] buttons wired to module-level actions.
        GNyraSupervisor->OnUnstable.BindLambda([this]()
        {
            if (!Banner.IsValid()) return;

            FOnBannerRestartClicked RestartCb = FOnBannerRestartClicked::CreateLambda([]()
            {
                // Full restart: shut down + respawn via a freshly-constructed
                // supervisor. Mirrors NyraEditorModule::StartupModule's spawn
                // sequence so the new instance picks up the same paths.
                if (!GNyraSupervisor.IsValid()) return;

                GNyraSupervisor->RequestShutdown();
                GNyraSupervisor.Reset();

                TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(TEXT("NYRA"));
                if (!Plugin.IsValid()) return;
                const FString PluginDir  = Plugin->GetBaseDir();
                const FString ProjectDir = FPaths::ProjectDir();
                const FString LogDir     = FPaths::Combine(ProjectDir, TEXT("Saved"), TEXT("NYRA"), TEXT("logs"));

                GNyraSupervisor = MakeUnique<FNyraSupervisor>();
                GNyraSupervisor->SpawnAndConnect(ProjectDir, PluginDir, LogDir);
            });

            FOnBannerOpenLogClicked OpenLogCb = FOnBannerOpenLogClicked::CreateLambda([]()
            {
                // Open the logs directory in Windows Explorer (or the host
                // platform's file browser) so the user can inspect rotated
                // nyrahost-YYYY-MM-DD.log files. Uses SNyraDiagnosticsDrawer's
                // static LogFilePath() helper so path construction matches.
                const FString LogPath = SNyraDiagnosticsDrawer::LogFilePath();
                FPlatformProcess::ExploreFolder(*FPaths::GetPath(LogPath));
            });

            Banner->SetState(ENyraBannerKind::Error,
                FText::FromString(TEXT("NyraHost is unstable -- see Saved/NYRA/logs/")),
                RestartCb, OpenLogCb);
        });
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
    // Also unbind the Plan 13 OnStateChanged + OnUnstable delegates so they
    // don't fire into a dead Banner pointer during teardown.
    if (GNyraSupervisor.IsValid())
    {
        GNyraSupervisor->OnNotification.Unbind();
        GNyraSupervisor->OnStateChanged.Unbind();
        GNyraSupervisor->OnUnstable.Unbind();
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
    if (!Env.Params.IsValid()) return;

    // Plan 13: route diagnostics/download-progress frames to the download
    // modal BEFORE the chat/stream branch so the modal can update progress
    // without any dependency on MessageList being valid.
    if (Env.Method == TEXT("diagnostics/download-progress"))
    {
        if (DownloadModal.IsValid())
        {
            DownloadModal->OnProgress(Env.Params);
        }
        return;
    }

    // Plan 02-12: diagnostics/backend-state updates the status strip in real time.
    // Must be BEFORE chat/stream so the strip refreshes before tokens arrive.
    if (Env.Method == TEXT("diagnostics/backend-state") && StatusStrip.IsValid())
    {
        FString ParamsJson;
        if (TSharedPtr<FJsonObject> Obj = Env.Params)
        {
            auto JsonWriter = TJsonWriterFactory<>::Create(&ParamsJson);
            FJsonSerializer::Serialize(Obj.ToSharedRef(), TEXT(""), JsonWriter);
            JsonWriter->Close();
            if (!ParamsJson.IsEmpty())
            {
                FNyraBackendState NewState = FNyraBackendState::ParseJson(ParamsJson);
                StatusStrip->SetState(NewState);
                CurrentBackendState = NewState;  // cached for popover rendering
            }
        }
        return;
    }

    // Plan 12: chat-stream dispatch. Preserved verbatim apart from the early
    // return for the diagnostics branch above.
    if (Env.Method != TEXT("chat/stream") || !MessageList.IsValid()) return;

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

void SNyraChatPanel::OpenClaudePopover()
{
    if (!StatusStrip.IsValid()) return;
    // Context-sensitive actions per current state:
    //   auth-drift / offline → [Sign in] instructions + [Test connection]
    //   ready             → [Sign out] + [Test connection]
    //   rate-limited     → [Switch to Gemma] button
    // Minimal v1 implementation: open a notification with instructions.
    const FString& State = CurrentBackendState.Claude.State;
    if (State == TEXT("auth-drift") || State == TEXT("offline") || !CurrentBackendState.Claude.bInstalled)
    {
        FNotificationInfo Info(FText::FromString(
            TEXT("Run 'claude auth login' in a terminal, then restart NYRA.")));
        Info.ExpireDuration = 10.0f;
        FSlateNotificationManager::Get().AddNotification(Info);
    }
}

void SNyraChatPanel::OpenGemmaPopover()
{
    if (!StatusStrip.IsValid()) return;
    // Gemma not-installed → offer download via existing Phase 1 diagnostics path.
    if (CurrentBackendState.Gemma.State == TEXT("not-installed"))
    {
        if (GNyraSupervisor.IsValid())
        {
            TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
            Params->SetStringField(TEXT("model"), TEXT("gemma-3-4b-it-qat-q4_0-gguf"));
            GNyraSupervisor->SendRequest(TEXT("diagnostics/download-gemma"), Params);
        }
    }
}

void SNyraChatPanel::OpenPrivacyPopover()
{
    // Privacy pill click: toggle Privacy Mode via session/set-mode notification.
    if (GNyraSupervisor.IsValid())
    {
        TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
        const bool bCurrentlyInPrivacy = CurrentBackendState.Mode == FNyraBackendState::ENyraPrivacyMode::PrivacyMode;
        Params->SetStringField(TEXT("mode"), bCurrentlyInPrivacy ? TEXT("normal") : TEXT("privacy-mode"));
        GNyraSupervisor->SendNotification(TEXT("session/set-mode"), Params);
    }
}

#undef LOCTEXT_NAMESPACE
