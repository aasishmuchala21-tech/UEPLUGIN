// =============================================================================
// FNyraWsClient.cpp  (Phase 1 Plan 10)
// =============================================================================

#include "WS/FNyraWsClient.h"
#include "NyraLog.h"
#include "WebSocketsModule.h"
#include "Dom/JsonObject.h"

void FNyraWsClient::Connect(const FString& Host, int32 Port, const FString& AuthToken)
{
    const FString Url = FString::Printf(TEXT("ws://%s:%d/"), *Host, Port);
    PendingAuthToken = AuthToken;
    bAuthenticated = false;

    Socket = FWebSocketsModule::Get().CreateWebSocket(Url, TEXT(""));

    Socket->OnConnected().AddLambda([this]()
    {
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
    Socket->OnConnectionError().AddLambda([this](const FString& Err)
    {
        UE_LOG(LogNyra, Warning, TEXT("[NYRA] WS connection error: %s"), *Err);
    });

    Socket->Connect();
}

void FNyraWsClient::Disconnect()
{
    if (Socket.IsValid())
    {
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
