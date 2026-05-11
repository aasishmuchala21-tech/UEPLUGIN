// =============================================================================
// FNyraWsClient.cpp  (Phase 1 Plan 10)
// =============================================================================

#include "WS/FNyraWsClient.h"
#include "NyraLog.h"
#include "WebSocketsModule.h"
#include "Dom/JsonObject.h"

FNyraWsClient::~FNyraWsClient()
{
    // R4.I1 fix from the full-codebase review: Disconnect() clears every
    // socket delegate before Socket.Reset(). If we don't call it here,
    // any IWebSocket callback the underlying module has already queued
    // dispatches into our freed lambdas.
    Disconnect();
}

void FNyraWsClient::Connect(const FString& Host, int32 Port, const FString& AuthToken)
{
    // BL-05: bump the connection generation BEFORE creating the new socket
    // so any in-flight callbacks fired by the previous socket (which may
    // still be enqueued on the WS worker thread) compare unequal and
    // bail out without touching `this`. Defends against rapid reconnect
    // race + use-after-free on supervisor destruction.
    const uint64 ThisGeneration = ++ConnectionGeneration;

    // BL-05: tear down the previous socket cleanly. Clearing the delegates
    // BEFORE Socket.Reset() prevents any callback the WS module has already
    // queued from dispatching into our (about-to-be-destructed) lambdas.
    if (Socket.IsValid())
    {
        Socket->OnConnected().Clear();
        Socket->OnMessage().Clear();
        Socket->OnClosed().Clear();
        Socket->OnConnectionError().Clear();
        Socket->Close();
        Socket.Reset();
    }

    const FString Url = FString::Printf(TEXT("ws://%s:%d/"), *Host, Port);
    PendingAuthToken = AuthToken;
    bAuthenticated = false;

    Socket = FWebSocketsModule::Get().CreateWebSocket(Url, TEXT(""));

    Socket->OnConnected().AddLambda([this, ThisGeneration]()
    {
        // BL-05: stale-generation guard. If Connect() was called again
        // between the WS upgrade and this callback firing, ConnectionGeneration
        // will have advanced past ThisGeneration; ignore this callback
        // entirely so we don't auth on a socket Disconnect() already torn down.
        if (ThisGeneration != ConnectionGeneration)
        {
            return;
        }
        // D-07: Send session/authenticate as the FIRST frame after the WS upgrade.
        TSharedRef<FJsonObject> Params = MakeShared<FJsonObject>();
        Params->SetStringField(TEXT("token"), PendingAuthToken);
        AuthRequestId = NextId++;
        const FString Frame = FNyraJsonRpc::EncodeRequest(AuthRequestId, TEXT("session/authenticate"), Params);
        if (Socket.IsValid() && Socket->IsConnected())
        {
            Socket->Send(Frame);
        }
    });

    Socket->OnMessage().AddRaw(this, &FNyraWsClient::HandleMessage);
    Socket->OnClosed().AddRaw(this, &FNyraWsClient::HandleClose);
    Socket->OnConnectionError().AddLambda([this, ThisGeneration](const FString& Err)
    {
        // BL-05: stale-generation guard.
        if (ThisGeneration != ConnectionGeneration)
        {
            return;
        }
        UE_LOG(LogNyra, Warning, TEXT("[NYRA] WS connection error: %s"), *Err);
    });

    Socket->Connect();
}

void FNyraWsClient::Disconnect()
{
    // BL-05: bump generation so any pending callbacks bail.
    ++ConnectionGeneration;
    if (Socket.IsValid())
    {
        // Clear delegates before Reset to avoid the in-flight-callback UAF
        // on the WS worker thread.
        Socket->OnConnected().Clear();
        Socket->OnMessage().Clear();
        Socket->OnClosed().Clear();
        Socket->OnConnectionError().Clear();
        Socket->Close();
        Socket.Reset();
    }
}

bool FNyraWsClient::IsConnected() const
{
    return Socket.IsValid() && Socket->IsConnected();
}

int64 FNyraWsClient::SendRequest(const FString& Method, const TSharedRef<FJsonObject>& Params)
{
    const int64 Id = NextId++;
    if (Socket.IsValid() && Socket->IsConnected())
    {
        Socket->Send(FNyraJsonRpc::EncodeRequest(Id, Method, Params));
    }
    return Id;
}

void FNyraWsClient::SendNotification(const FString& Method, const TSharedRef<FJsonObject>& Params)
{
    if (Socket.IsValid() && Socket->IsConnected())
    {
        Socket->Send(FNyraJsonRpc::EncodeNotification(Method, Params));
    }
}

void FNyraWsClient::HandleMessage(const FString& Frame)
{
    const FNyraJsonRpcEnvelope Env = FNyraJsonRpc::Decode(Frame);
    switch (Env.Kind)
    {
    case ENyraEnvelopeKind::Response:
        if (!bAuthenticated && Env.Id == AuthRequestId)
        {
            bAuthenticated = true;
            OnAuthenticated.ExecuteIfBound();
        }
        OnResponse.ExecuteIfBound(Env);
        break;

    case ENyraEnvelopeKind::Notification:
        OnNotification.ExecuteIfBound(Env);
        break;

    case ENyraEnvelopeKind::Error:
        if (!bAuthenticated && Env.Id == AuthRequestId)
        {
            OnAuthFailed.ExecuteIfBound(Env.ErrorCode, Env.ErrorMessage);
        }
        else
        {
            OnErrorResponse.ExecuteIfBound(Env);
        }
        break;

    case ENyraEnvelopeKind::Invalid:
        UE_LOG(LogNyra, Warning, TEXT("[NYRA] Invalid WS frame (first 120 chars): %s"),
               *Frame.Left(120));
        break;

    default:
        break;
    }
}

void FNyraWsClient::HandleClose(int32 Code, const FString& Reason, bool bWasClean)
{
    UE_LOG(LogNyra, Log, TEXT("[NYRA] WS closed code=%d reason='%s' clean=%d"),
           Code, *Reason, bWasClean ? 1 : 0);

    // D-07: WS close 4401 (unauthenticated) before auth success -> fire OnAuthFailed.
    if (Code == 4401 && !bAuthenticated)
    {
        OnAuthFailed.ExecuteIfBound(Code, Reason);
    }
    OnClosed.ExecuteIfBound(Code, Reason);
}
