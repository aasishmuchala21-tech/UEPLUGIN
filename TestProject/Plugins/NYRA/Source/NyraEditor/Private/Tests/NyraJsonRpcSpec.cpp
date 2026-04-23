// =============================================================================
// NyraJsonRpcSpec.cpp  (Phase 1 Plan 10 — upgraded from Plan 01 Wave 0 stub)
// =============================================================================
//
// Nyra.Jsonrpc.EnvelopeRoundtrip — JSON-RPC 2.0 unit tests against FNyraJsonRpc
// (VALIDATION row 1-02-02).
//
// Covers:
//   * Encode: Request / Notification / Response / Error
//   * Decode: Request / Notification / Response / Error
//   * Invalid: malformed JSON / missing jsonrpc:"2.0"
// =============================================================================

#include "Misc/AutomationTest.h"
#include "NyraTestFixtures.h"
#include "WS/FNyraJsonRpc.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"

#if WITH_AUTOMATION_TESTS

BEGIN_DEFINE_SPEC(FNyraJsonRpcSpec,
                   "Nyra.Jsonrpc",
                   EAutomationTestFlags::EditorContext |
                   EAutomationTestFlags::EngineFilter)
END_DEFINE_SPEC(FNyraJsonRpcSpec)

void FNyraJsonRpcSpec::Define()
{
    Describe("EnvelopeRoundtrip", [this]()
    {
        It("encodes a request envelope with jsonrpc 2.0, id, method, params", [this]()
        {
            TSharedRef<FJsonObject> P = MakeShared<FJsonObject>();
            P->SetStringField(TEXT("token"), TEXT("abc123"));
            const FString Encoded = FNyraJsonRpc::EncodeRequest(1, TEXT("session/authenticate"), P);
            TestTrue(TEXT("jsonrpc field"),   Encoded.Contains(TEXT("\"jsonrpc\":\"2.0\"")));
            TestTrue(TEXT("id field"),        Encoded.Contains(TEXT("\"id\":1")));
            TestTrue(TEXT("method field"),    Encoded.Contains(TEXT("\"method\":\"session/authenticate\"")));
            TestTrue(TEXT("params field"),    Encoded.Contains(TEXT("\"params\":{\"token\":\"abc123\"}")));
        });

        It("encodes a notification without id", [this]()
        {
            TSharedRef<FJsonObject> P = MakeShared<FJsonObject>();
            P->SetStringField(TEXT("req_id"), TEXT("r1"));
            P->SetStringField(TEXT("conversation_id"), TEXT("c1"));
            const FString Encoded = FNyraJsonRpc::EncodeNotification(TEXT("chat/cancel"), P);
            TestTrue(TEXT("no id"),  !Encoded.Contains(TEXT("\"id\":")));
            TestTrue(TEXT("method"), Encoded.Contains(TEXT("\"method\":\"chat/cancel\"")));
        });

        It("encodes a response with id + result", [this]()
        {
            TSharedRef<FJsonObject> R = MakeShared<FJsonObject>();
            TArray<TSharedPtr<FJsonValue>> Backs;
            Backs.Add(MakeShared<FJsonValueString>(TEXT("gemma-local")));
            R->SetArrayField(TEXT("backends"), Backs);
            const FString Encoded = FNyraJsonRpc::EncodeResponse(2, R);
            TestTrue(TEXT("id 2"),  Encoded.Contains(TEXT("\"id\":2")));
            TestTrue(TEXT("result"), Encoded.Contains(TEXT("\"result\":{\"backends\":[\"gemma-local\"]}")));
        });

        It("encodes an error envelope with code + message + data.remediation", [this]()
        {
            const FString Encoded = FNyraJsonRpc::EncodeError(
                3, -32005, TEXT("gemma_not_installed"), TEXT("Click Download"));
            TestTrue(TEXT("error code"),    Encoded.Contains(TEXT("\"code\":-32005")));
            TestTrue(TEXT("error message"), Encoded.Contains(TEXT("\"message\":\"gemma_not_installed\"")));
            TestTrue(TEXT("remediation"),   Encoded.Contains(TEXT("\"remediation\":\"Click Download\"")));
        });

        It("decodes a request", [this]()
        {
            const FString Frame =
                TEXT("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"session/hello\",\"params\":{}}");
            const FNyraJsonRpcEnvelope Env = FNyraJsonRpc::Decode(Frame);
            TestEqual(TEXT("kind"),   (int32)Env.Kind, (int32)ENyraEnvelopeKind::Request);
            TestEqual(TEXT("id"),     Env.Id, (int64)1);
            TestEqual(TEXT("method"), Env.Method, FString(TEXT("session/hello")));
        });

        It("decodes a notification", [this]()
        {
            const FString Frame =
                TEXT("{\"jsonrpc\":\"2.0\",\"method\":\"chat/stream\",\"params\":{\"delta\":\"hi\",\"done\":false}}");
            const FNyraJsonRpcEnvelope Env = FNyraJsonRpc::Decode(Frame);
            TestEqual(TEXT("kind"),   (int32)Env.Kind, (int32)ENyraEnvelopeKind::Notification);
            TestEqual(TEXT("method"), Env.Method, FString(TEXT("chat/stream")));
            TestFalse(TEXT("no id"),  Env.bHasId);
        });

        It("decodes a response", [this]()
        {
            const FString Frame =
                TEXT("{\"jsonrpc\":\"2.0\",\"id\":2,\"result\":{\"backends\":[\"gemma-local\"],\"phase\":1}}");
            const FNyraJsonRpcEnvelope Env = FNyraJsonRpc::Decode(Frame);
            TestEqual(TEXT("kind"),       (int32)Env.Kind, (int32)ENyraEnvelopeKind::Response);
            TestEqual(TEXT("id"),         Env.Id, (int64)2);
            TestTrue(TEXT("result valid"), Env.Result.IsValid());
        });

        It("decodes an error", [this]()
        {
            const FString Frame =
                TEXT("{\"jsonrpc\":\"2.0\",\"id\":3,\"error\":{\"code\":-32005,\"message\":\"gemma_not_installed\",\"data\":{\"remediation\":\"Click Download\"}}}");
            const FNyraJsonRpcEnvelope Env = FNyraJsonRpc::Decode(Frame);
            TestEqual(TEXT("kind"),        (int32)Env.Kind, (int32)ENyraEnvelopeKind::Error);
            TestEqual(TEXT("code"),        Env.ErrorCode, -32005);
            TestEqual(TEXT("remediation"), Env.ErrorRemediation, FString(TEXT("Click Download")));
        });

        It("returns Invalid on malformed JSON", [this]()
        {
            const FNyraJsonRpcEnvelope Env = FNyraJsonRpc::Decode(TEXT("not json"));
            TestEqual(TEXT("invalid"), (int32)Env.Kind, (int32)ENyraEnvelopeKind::Invalid);
        });

        It("returns Invalid on missing jsonrpc:2.0", [this]()
        {
            const FNyraJsonRpcEnvelope Env = FNyraJsonRpc::Decode(
                TEXT("{\"id\":1,\"method\":\"x\",\"params\":{}}"));
            TestEqual(TEXT("invalid"), (int32)Env.Kind, (int32)ENyraEnvelopeKind::Invalid);
        });
    });
}

#endif // WITH_AUTOMATION_TESTS
