#pragma once

// =============================================================================
// FNyraJsonRpc.h  (Phase 1 Plan 10 — JSON-RPC 2.0 envelope encode/decode)
// =============================================================================
//
// Wire spec: docs/JSONRPC.md (D-09/D-10).
// Error shape: docs/ERROR_CODES.md (D-11 — error.data.remediation).
//
// Encode / Decode the four envelope kinds used on the loopback WS transport
// between UE (FNyraWsClient) and the NyraHost Python sidecar:
//   * Request        {jsonrpc, id, method, params}
//   * Response       {jsonrpc, id, result}
//   * Error          {jsonrpc, id, error{code,message,data.remediation}}
//   * Notification   {jsonrpc,      method, params}   (no id)
//
// Compact (no-whitespace) output via TCondensedJsonPrintPolicy so wire frames
// are minimal. Decode tolerates missing/extra fields per JSON-RPC 2.0:
//   * jsonrpc != "2.0"  -> Invalid
//   * malformed JSON    -> Invalid
//   * has method + id   -> Request
//   * has method only   -> Notification
//   * has result        -> Response
//   * has error         -> Error
// =============================================================================

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

/** Tag for FNyraJsonRpcEnvelope classification. */
enum class ENyraEnvelopeKind : uint8
{
    Request,
    Notification,
    Response,
    Error,
    Invalid,
};

/**
 * Parsed JSON-RPC 2.0 envelope. Fields are populated conditionally based
 * on Kind. Callers should branch on Kind and then consume the subset of
 * fields that apply.
 *
 *   Kind = Request       -> Id, bHasId, Method, Params
 *   Kind = Notification  -> Method, Params             (Id == 0, bHasId == false)
 *   Kind = Response      -> Id, bHasId, Result
 *   Kind = Error         -> Id, bHasId, ErrorCode, ErrorMessage, ErrorRemediation
 *   Kind = Invalid       -> (no fields valid)
 */
struct NYRAEDITOR_API FNyraJsonRpcEnvelope
{
    ENyraEnvelopeKind Kind = ENyraEnvelopeKind::Invalid;
    int64 Id = 0;                      // valid for Request / Response / Error
    bool bHasId = false;
    FString Method;                    // valid for Request / Notification
    TSharedPtr<FJsonObject> Params;    // valid for Request / Notification
    TSharedPtr<FJsonObject> Result;    // valid for Response
    int32 ErrorCode = 0;               // valid for Error
    FString ErrorMessage;              // valid for Error
    FString ErrorRemediation;          // valid for Error (from error.data.remediation)
};

class NYRAEDITOR_API FNyraJsonRpc
{
public:
    /** Encode a request: {"jsonrpc":"2.0","id":Id,"method":Method,"params":Params} */
    static FString EncodeRequest(int64 Id, const FString& Method, const TSharedRef<FJsonObject>& Params);

    /** Encode a notification: {"jsonrpc":"2.0","method":Method,"params":Params} -- no id */
    static FString EncodeNotification(const FString& Method, const TSharedRef<FJsonObject>& Params);

    /** Encode a response: {"jsonrpc":"2.0","id":Id,"result":Result} */
    static FString EncodeResponse(int64 Id, const TSharedRef<FJsonObject>& Result);

    /** Encode an error: {"jsonrpc":"2.0","id":Id,"error":{"code":Code,"message":Msg,"data":{"remediation":Rem}}} */
    static FString EncodeError(int64 Id, int32 Code, const FString& Message, const FString& Remediation);

    /** Parse an incoming text frame. Returns Envelope with Kind=Invalid on malformed/unknown. */
    static FNyraJsonRpcEnvelope Decode(const FString& Frame);
};
