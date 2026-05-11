#pragma once

// =============================================================================
// FNyraWsClient.h  (Phase 1 Plan 10 -- loopback WS client + auth-first-frame)
// =============================================================================
//
// Wire spec: docs/JSONRPC.md §3.1 (session/authenticate first-frame gate,
// close code 4401 on failure).
// CONTEXT: D-07.
//
// Wraps FWebSocketsModule against ws://127.0.0.1:<port>/ with:
//   * FIRST FRAME = session/authenticate {"token":<from-handshake>} (D-07).
//   * On response matching AuthRequestId -> OnAuthenticated fires.
//   * On close code 4401 before authenticated -> OnAuthFailed fires.
//   * Inbound Notifications / Responses / Errors route to their delegates.
//
// Id policy (docs/JSONRPC.md §2, RESEARCH §3.10 P1.7):
//   NextId starts at 1 and is monotonic for the lifetime of the object.
//   It is NEVER reset on reconnect -- reconnects are handled one layer up
//   by FNyraSupervisor which constructs a fresh FNyraWsClient only after
//   a respawn, by which time the supervisor has already bumped its own id
//   counter and the in-flight replay re-sends under a new id.
// =============================================================================

#include "CoreMinimal.h"
#include "IWebSocket.h"
#include "WS/FNyraJsonRpc.h"

DECLARE_DELEGATE(FOnNyraAuthenticated);
DECLARE_DELEGATE_TwoParams(FOnNyraAuthFailed, int32 /*CloseCode*/, const FString& /*Reason*/);
DECLARE_DELEGATE_OneParam(FOnNyraNotification,  const FNyraJsonRpcEnvelope& /*Env*/);
DECLARE_DELEGATE_OneParam(FOnNyraResponse,      const FNyraJsonRpcEnvelope& /*Env*/);
DECLARE_DELEGATE_OneParam(FOnNyraErrorResponse, const FNyraJsonRpcEnvelope& /*Env*/);
DECLARE_DELEGATE_TwoParams(FOnNyraClosed, int32 /*CloseCode*/, const FString& /*Reason*/);

class NYRAEDITOR_API FNyraWsClient
{
public:
    /** R4.I1 fix from the full-codebase review: Disconnect() is the only
     *  thing that clears socket delegate bindings. If a caller destroys
     *  this client without first calling Disconnect(), the IWebSocket
     *  still holds a raw `this` pointer in its OnMessage/OnClosed
     *  delegates, and a libwebsockets game-thread tick after destruction
     *  triggers a UAF. */
    ~FNyraWsClient();

    void Connect(const FString& Host, int32 Port, const FString& AuthToken);
    void Disconnect();
    bool IsConnected() const;

    /** Send a request envelope; returns the id used so caller can correlate responses. */
    int64 SendRequest(const FString& Method, const TSharedRef<FJsonObject>& Params);

    /** Fire-and-forget notification. */
    void SendNotification(const FString& Method, const TSharedRef<FJsonObject>& Params);

    FOnNyraAuthenticated  OnAuthenticated;
    FOnNyraAuthFailed     OnAuthFailed;
    FOnNyraNotification   OnNotification;
    FOnNyraResponse       OnResponse;
    FOnNyraErrorResponse  OnErrorResponse;
    FOnNyraClosed         OnClosed;

private:
    void HandleMessage(const FString& Frame);
    void HandleClose(int32 Code, const FString& Reason, bool bWasClean);

    TSharedPtr<IWebSocket> Socket;
    FString PendingAuthToken;
    int64 NextId = 1;
    int64 AuthRequestId = 0;   // id used for the session/authenticate first frame
    bool bAuthenticated = false;
    // BL-05: monotonic counter bumped on every Connect()/Disconnect(). Lambdas
    // capture the generation by value; if the captured generation differs
    // from the current value when the callback fires, we know Connect was
    // called again (or Disconnect ran) and the callback bails out cleanly,
    // avoiding use-after-free on the WS worker thread during rapid reconnect.
    uint64 ConnectionGeneration = 0;
};
