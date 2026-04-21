---
phase: 01-plugin-shell-three-process-ipc
plan: 10
type: execute
wave: 2
depends_on: [01, 03, 05, 06]
autonomous: true
requirements: [PLUG-02]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/WS/FNyraJsonRpc.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/WS/FNyraJsonRpc.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/WS/FNyraWsClient.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/WS/FNyraWsClient.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraHandshake.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraHandshake.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraSupervisor.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraSupervisor.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraJsonRpcSpec.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraSupervisorSpec.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraIntegrationSpec.cpp
objective: >
  Implement the UE C++ half of the three-process handshake: FNyraJsonRpc
  (encode/decode envelopes per D-09), FNyraWsClient (wraps FWebSocketsModule
  with auth-first-frame protocol per D-07), FNyraHandshake (file polling with
  exponential backoff per D-06), FNyraSupervisor (FMonitoredProcess-based
  NyraHost spawn with 3-in-60s restart policy per D-08, in-flight request
  replay, orphan cleanup per P1.2). Fill automation tests:
  Nyra.Jsonrpc.EnvelopeRoundtrip (1-02-02), Nyra.Supervisor.RestartPolicy
  (1-02-03), Nyra.Integration.HandshakeAuth (1-02-01, guarded). Wire into
  FNyraEditorModule::StartupModule.
must_haves:
  truths:
    - "FNyraJsonRpc::EncodeRequest/EncodeResponse/EncodeNotification produce wire-format text frames matching docs/JSONRPC.md"
    - "FNyraJsonRpc::Decode parses all 4 envelope kinds and returns a tagged FNyraJsonRpcEnvelope"
    - "FNyraWsClient sends session/authenticate as first frame on OnConnected; on auth success emits OnAuthenticated; on close 4401 emits OnAuthFailed"
    - "FNyraHandshake::Poll runs a ticker with 50ms * 1.5 exp backoff capped at 2s, 30s total; on valid handshake calls OnReady with port+token"
    - "FNyraSupervisor spawns NyraHost via FMonitoredProcess with correct CLI args (--editor-pid, --log-dir, --project-dir, --plugin-binaries-dir, --handshake-dir), watches handshake file, connects FNyraWsClient, authenticates"
    - "FNyraSupervisor restart policy: after 3 crashes in 60s (using injected FNyraClock), stops restarting and emits OnUnstable banner signal"
    - "FNyraSupervisor replays in-flight request on respawn with new req_id; original marked cancelled in the panel layer"
    - "FNyraEditorModule::StartupModule integrates: SpawnNyraHost called AFTER tab registration; ShutdownModule sends shutdown notification, 2s grace, TerminateProc(KillTree=true) fallback"
    - "Nyra.Jsonrpc.EnvelopeRoundtrip and Nyra.Supervisor.RestartPolicy automation tests pass"
  artifacts:
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/WS/FNyraJsonRpc.h
      provides: "JSON-RPC 2.0 envelope encode/decode"
      exports: ["FNyraJsonRpcEnvelope", "FNyraJsonRpc::EncodeRequest", "FNyraJsonRpc::EncodeNotification", "FNyraJsonRpc::EncodeResponse", "FNyraJsonRpc::Decode"]
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/WS/FNyraWsClient.h
      provides: "WebSocket client + auth-first-frame gate + routing"
      exports: ["FNyraWsClient", "FOnNyraAuthenticated", "FOnNyraAuthFailed", "FOnNyraNotification", "FOnNyraResponse"]
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraHandshake.h
      provides: "Handshake file polling + JSON parse + orphan scan"
      exports: ["FNyraHandshake", "FNyraHandshakeData", "FOnHandshakeReady", "FOnHandshakeTimeout"]
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraSupervisor.h
      provides: "FNyraSupervisor singleton composing process + handshake + WS + restart policy"
      exports: ["FNyraSupervisor", "INyraClock", "FNyraSystemClock", "FNyraSupervisorState"]
  key_links:
    - from: FNyraSupervisor::SpawnNyraHost
      to: NyraHost `python -m nyrahost` CLI (Plan 06, 08)
      via: "FMonitoredProcess with exact args matching __main__.py parse_args()"
      pattern: "--editor-pid.*--log-dir.*--project-dir.*--plugin-binaries-dir"
    - from: FNyraWsClient OnConnected
      to: session/authenticate JSON-RPC request (docs/JSONRPC.md §3.1)
      via: "First frame after Connection: Upgrade; token from handshake"
      pattern: "session/authenticate"
    - from: FNyraSupervisor restart-history check
      to: INyraClock abstraction (FNyraTestClock in NyraTestFixtures.h)
      via: "Injected via constructor for Nyra.Supervisor.RestartPolicy test"
      pattern: "INyraClock"
---

<objective>
UE C++ half of the 3-process IPC — the biggest C++ plan in Phase 1 because
JSON-RPC + WS + handshake + supervisor are all tightly entangled and must
land together to reach "Ring 0 it can talk" end-to-end.

Per CONTEXT.md:
- D-04: eager spawn in StartupModule
- D-05: graceful shutdown (notification + 2s + TerminateProc KillTree)
- D-06: handshake file polling (50ms × 1.5 exp backoff, capped 2s, 30s total)
- D-07: first-frame auth + close 4401 handling
- D-08: 3-in-60s supervisor + in-flight replay
- D-09/D-10: JSON-RPC 2.0 encode/decode
- D-11: error.data.remediation rendering

Per RESEARCH §3.2 (FWebSocketsModule usage), §3.3 (FMonitoredProcess +
KillTree + pipe-drain-deadlock avoidance), §3.10 P1.2 (orphan cleanup), P1.7
(id persistence + session_id envelope check).

Purpose: After Plan 10, the UE editor CAN spawn NyraHost, authenticate, and
round-trip a basic `session/hello`. Plan 12 adds chat/send. Plan 14 adds Ring
0 bench.
Output: 4 C++ modules (JsonRpc / WsClient / Handshake / Supervisor), integration
wiring in NyraEditorModule, and 3 green automation specs.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md
@docs/HANDSHAKE.md
@docs/JSONRPC.md
@docs/ERROR_CODES.md
@TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp
@TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraEditorModule.h
@TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraLog.h
@TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraChatTabNames.h
@TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTestFixtures.h
@TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraJsonRpcSpec.cpp
@TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraSupervisorSpec.cpp
@TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraIntegrationSpec.cpp
</context>

<interfaces>
UE 5.6 FWebSocketsModule usage (from RESEARCH §3.2):
```cpp
#include "WebSocketsModule.h"
#include "IWebSocket.h"

TSharedRef<IWebSocket> Socket = FWebSocketsModule::Get().CreateWebSocket(
    FString::Printf(TEXT("ws://127.0.0.1:%d/"), Port),
    TEXT("")  // no sub-protocol
);
Socket->OnConnected().AddLambda([&]() { /* send auth */ });
Socket->OnMessage().AddLambda([&](const FString& Msg) { /* dispatch */ });
Socket->OnClosed().AddLambda([&](int32 Code, const FString& Reason, bool bWasClean) { /* reconnect */ });
Socket->Connect();
```

FMonitoredProcess usage (RESEARCH §3.3):
```cpp
#include "Misc/MonitoredProcess.h"

TSharedPtr<FMonitoredProcess> Proc = MakeShared<FMonitoredProcess>(
    PythonExe, ParamsString, /*bHidden=*/true, /*bCreatePipes=*/true);
Proc->OnOutput().BindLambda([](const FString& Line) { /* log */ });
Proc->OnCompleted().BindLambda([](int32 ExitCode) { /* restart policy */ });
Proc->Launch();
```

FTSTicker in UE 5.6 (for handshake polling):
```cpp
#include "Containers/Ticker.h"

FTSTicker::FDelegateHandle Handle =
    FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda(
        [this](float DeltaTime) -> bool {
            // return true to continue, false to auto-remove
            return ShouldContinuePolling();
        }), 0.05f);  // 50ms initial interval
FTSTicker::GetCoreTicker().RemoveTicker(Handle);
```

JSON parse with UE's Json module:
```cpp
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Dom/JsonObject.h"

TSharedRef<TJsonReader<TCHAR>> Reader = TJsonReaderFactory<TCHAR>::Create(JsonString);
TSharedPtr<FJsonObject> Root;
if (FJsonSerializer::Deserialize(Reader, Root) && Root.IsValid()) {
    FString Method;
    if (Root->TryGetStringField(TEXT("method"), Method)) { ... }
}
```
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: FNyraJsonRpc (encode/decode) + fill Nyra.Jsonrpc.EnvelopeRoundtrip spec</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraEditor/Public/WS/FNyraJsonRpc.h
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/WS/FNyraJsonRpc.cpp
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraJsonRpcSpec.cpp
  </files>
  <read_first>
    - docs/JSONRPC.md (all 4 envelope shapes + method surface)
    - docs/ERROR_CODES.md (error payload shape)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraJsonRpcSpec.cpp (placeholder from Plan 01)
    - TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs (Json + JsonUtilities deps)
  </read_first>
  <behavior>
    - EncodeRequest(id=1, method="session/authenticate", params={"token":"abc"}) returns a string containing "jsonrpc":"2.0","id":1,"method":"session/authenticate","params":{"token":"abc"}.
    - EncodeNotification("chat/cancel", {"conversation_id":"...","req_id":"..."}) omits "id".
    - EncodeResponse(2, {"backends":["gemma-local"]}) contains "id":2 and "result":{"backends":["gemma-local"]}.
    - EncodeError(1, -32005, "gemma_not_installed", "...remediation") contains "error":{"code":-32005,"message":"gemma_not_installed","data":{"remediation":"..."}}.
    - Decode classifies 4 envelope kinds correctly; returns Invalid on malformed JSON or missing jsonrpc:"2.0".
    - Roundtrip: for each of the 6 Phase 1 methods listed in docs/JSONRPC.md, Encode then Decode produces matching fields.
  </behavior>
  <action>
    **1. CREATE Public/WS/FNyraJsonRpc.h:**

    ```cpp
    #pragma once
    #include "CoreMinimal.h"
    #include "Dom/JsonObject.h"

    enum class ENyraEnvelopeKind : uint8
    {
        Request,
        Notification,
        Response,
        Error,
        Invalid,
    };

    struct NYRAEDITOR_API FNyraJsonRpcEnvelope
    {
        ENyraEnvelopeKind Kind = ENyraEnvelopeKind::Invalid;
        int64 Id = 0;              // valid for Request / Response / Error (nullable id captured as 0)
        bool bHasId = false;
        FString Method;            // valid for Request / Notification
        TSharedPtr<FJsonObject> Params;   // valid for Request / Notification
        TSharedPtr<FJsonObject> Result;   // valid for Response
        int32 ErrorCode = 0;       // valid for Error
        FString ErrorMessage;      // valid for Error
        FString ErrorRemediation;  // valid for Error (from data.remediation)
    };

    class NYRAEDITOR_API FNyraJsonRpc
    {
    public:
        /** Encode a request: {"jsonrpc":"2.0","id":Id,"method":Method,"params":Params} */
        static FString EncodeRequest(int64 Id, const FString& Method, const TSharedRef<FJsonObject>& Params);

        /** Encode a notification: {"jsonrpc":"2.0","method":Method,"params":Params} — no id */
        static FString EncodeNotification(const FString& Method, const TSharedRef<FJsonObject>& Params);

        /** Encode a response: {"jsonrpc":"2.0","id":Id,"result":Result} */
        static FString EncodeResponse(int64 Id, const TSharedRef<FJsonObject>& Result);

        /** Encode an error: {"jsonrpc":"2.0","id":Id,"error":{"code":Code,"message":Msg,"data":{"remediation":Rem}}} */
        static FString EncodeError(int64 Id, int32 Code, const FString& Message, const FString& Remediation);

        /** Parse an incoming text frame. Returns Envelope with Kind=Invalid on malformed/unknown. */
        static FNyraJsonRpcEnvelope Decode(const FString& Frame);
    };
    ```

    **2. CREATE Private/WS/FNyraJsonRpc.cpp:**

    ```cpp
    #include "WS/FNyraJsonRpc.h"
    #include "NyraLog.h"
    #include "Serialization/JsonReader.h"
    #include "Serialization/JsonSerializer.h"
    #include "Serialization/JsonWriter.h"
    #include "Policies/CondensedJsonPrintPolicy.h"
    #include "Dom/JsonValue.h"

    namespace
    {
        FString WriteJsonObject(const TSharedRef<FJsonObject>& Root)
        {
            FString Out;
            TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer =
                TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Out);
            FJsonSerializer::Serialize(Root, Writer);
            Writer->Close();
            return Out;
        }
    }

    FString FNyraJsonRpc::EncodeRequest(int64 Id, const FString& Method, const TSharedRef<FJsonObject>& Params)
    {
        TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
        Root->SetStringField(TEXT("jsonrpc"), TEXT("2.0"));
        Root->SetNumberField(TEXT("id"), static_cast<double>(Id));
        Root->SetStringField(TEXT("method"), Method);
        Root->SetObjectField(TEXT("params"), Params);
        return WriteJsonObject(Root);
    }

    FString FNyraJsonRpc::EncodeNotification(const FString& Method, const TSharedRef<FJsonObject>& Params)
    {
        TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
        Root->SetStringField(TEXT("jsonrpc"), TEXT("2.0"));
        Root->SetStringField(TEXT("method"), Method);
        Root->SetObjectField(TEXT("params"), Params);
        return WriteJsonObject(Root);
    }

    FString FNyraJsonRpc::EncodeResponse(int64 Id, const TSharedRef<FJsonObject>& Result)
    {
        TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
        Root->SetStringField(TEXT("jsonrpc"), TEXT("2.0"));
        Root->SetNumberField(TEXT("id"), static_cast<double>(Id));
        Root->SetObjectField(TEXT("result"), Result);
        return WriteJsonObject(Root);
    }

    FString FNyraJsonRpc::EncodeError(int64 Id, int32 Code, const FString& Message, const FString& Remediation)
    {
        TSharedRef<FJsonObject> Data = MakeShared<FJsonObject>();
        Data->SetStringField(TEXT("remediation"), Remediation);
        TSharedRef<FJsonObject> Err = MakeShared<FJsonObject>();
        Err->SetNumberField(TEXT("code"), Code);
        Err->SetStringField(TEXT("message"), Message);
        Err->SetObjectField(TEXT("data"), Data);
        TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
        Root->SetStringField(TEXT("jsonrpc"), TEXT("2.0"));
        Root->SetNumberField(TEXT("id"), static_cast<double>(Id));
        Root->SetObjectField(TEXT("error"), Err);
        return WriteJsonObject(Root);
    }

    FNyraJsonRpcEnvelope FNyraJsonRpc::Decode(const FString& Frame)
    {
        FNyraJsonRpcEnvelope Env;
        TSharedRef<TJsonReader<TCHAR>> Reader = TJsonReaderFactory<TCHAR>::Create(Frame);
        TSharedPtr<FJsonObject> Root;
        if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
        {
            return Env;  // Invalid
        }
        FString JsonRpcVer;
        if (!Root->TryGetStringField(TEXT("jsonrpc"), JsonRpcVer) || JsonRpcVer != TEXT("2.0"))
        {
            return Env;
        }
        int64 IdVal = 0;
        bool bHasId = false;
        if (Root->HasField(TEXT("id")))
        {
            double D = 0.0;
            if (Root->TryGetNumberField(TEXT("id"), D))
            {
                IdVal = static_cast<int64>(D);
                bHasId = true;
            }
        }
        Env.Id = IdVal;
        Env.bHasId = bHasId;

        FString Method;
        if (Root->TryGetStringField(TEXT("method"), Method))
        {
            Env.Method = Method;
            const TSharedPtr<FJsonObject>* ParamsObj;
            if (Root->TryGetObjectField(TEXT("params"), ParamsObj) && ParamsObj && ParamsObj->IsValid())
            {
                Env.Params = *ParamsObj;
            }
            else
            {
                Env.Params = MakeShared<FJsonObject>();
            }
            Env.Kind = bHasId ? ENyraEnvelopeKind::Request : ENyraEnvelopeKind::Notification;
            return Env;
        }

        const TSharedPtr<FJsonObject>* ResultObj;
        if (Root->TryGetObjectField(TEXT("result"), ResultObj) && ResultObj && ResultObj->IsValid())
        {
            Env.Result = *ResultObj;
            Env.Kind = ENyraEnvelopeKind::Response;
            return Env;
        }

        const TSharedPtr<FJsonObject>* ErrObj;
        if (Root->TryGetObjectField(TEXT("error"), ErrObj) && ErrObj && ErrObj->IsValid())
        {
            double Code = 0.0;
            (*ErrObj)->TryGetNumberField(TEXT("code"), Code);
            Env.ErrorCode = static_cast<int32>(Code);
            (*ErrObj)->TryGetStringField(TEXT("message"), Env.ErrorMessage);
            const TSharedPtr<FJsonObject>* DataObj;
            if ((*ErrObj)->TryGetObjectField(TEXT("data"), DataObj) && DataObj && DataObj->IsValid())
            {
                (*DataObj)->TryGetStringField(TEXT("remediation"), Env.ErrorRemediation);
            }
            Env.Kind = ENyraEnvelopeKind::Error;
            return Env;
        }
        return Env;  // Invalid
    }
    ```

    **3. REPLACE NyraJsonRpcSpec.cpp Define() with real tests:**

    ```cpp
    #include "Misc/AutomationTest.h"
    #include "NyraTestFixtures.h"
    #include "WS/FNyraJsonRpc.h"
    #include "Dom/JsonObject.h"

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
                TestTrue(TEXT("jsonrpc field"), Encoded.Contains(TEXT("\"jsonrpc\":\"2.0\"")));
                TestTrue(TEXT("id field"), Encoded.Contains(TEXT("\"id\":1")));
                TestTrue(TEXT("method field"), Encoded.Contains(TEXT("\"method\":\"session/authenticate\"")));
                TestTrue(TEXT("params field"), Encoded.Contains(TEXT("\"params\":{\"token\":\"abc123\"}")));
            });

            It("encodes a notification without id", [this]()
            {
                TSharedRef<FJsonObject> P = MakeShared<FJsonObject>();
                P->SetStringField(TEXT("req_id"), TEXT("r1"));
                P->SetStringField(TEXT("conversation_id"), TEXT("c1"));
                const FString Encoded = FNyraJsonRpc::EncodeNotification(TEXT("chat/cancel"), P);
                TestTrue(TEXT("no id"), !Encoded.Contains(TEXT("\"id\":")));
                TestTrue(TEXT("method"), Encoded.Contains(TEXT("\"method\":\"chat/cancel\"")));
            });

            It("encodes a response with id + result", [this]()
            {
                TSharedRef<FJsonObject> R = MakeShared<FJsonObject>();
                TArray<TSharedPtr<FJsonValue>> Backs;
                Backs.Add(MakeShared<FJsonValueString>(TEXT("gemma-local")));
                R->SetArrayField(TEXT("backends"), Backs);
                const FString Encoded = FNyraJsonRpc::EncodeResponse(2, R);
                TestTrue(TEXT("id 2"), Encoded.Contains(TEXT("\"id\":2")));
                TestTrue(TEXT("result"), Encoded.Contains(TEXT("\"result\":{\"backends\":[\"gemma-local\"]}")));
            });

            It("encodes an error envelope with code + message + data.remediation", [this]()
            {
                const FString Encoded = FNyraJsonRpc::EncodeError(3, -32005, TEXT("gemma_not_installed"), TEXT("Click Download"));
                TestTrue(TEXT("error code"), Encoded.Contains(TEXT("\"code\":-32005")));
                TestTrue(TEXT("error message"), Encoded.Contains(TEXT("\"message\":\"gemma_not_installed\"")));
                TestTrue(TEXT("remediation"), Encoded.Contains(TEXT("\"remediation\":\"Click Download\"")));
            });

            It("decodes a request", [this]()
            {
                const FString Frame =
                    TEXT("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"session/hello\",\"params\":{}}");
                const FNyraJsonRpcEnvelope Env = FNyraJsonRpc::Decode(Frame);
                TestEqual(TEXT("kind"), (int32)Env.Kind, (int32)ENyraEnvelopeKind::Request);
                TestEqual(TEXT("id"), Env.Id, (int64)1);
                TestEqual(TEXT("method"), Env.Method, FString(TEXT("session/hello")));
            });

            It("decodes a notification", [this]()
            {
                const FString Frame =
                    TEXT("{\"jsonrpc\":\"2.0\",\"method\":\"chat/stream\",\"params\":{\"delta\":\"hi\",\"done\":false}}");
                const FNyraJsonRpcEnvelope Env = FNyraJsonRpc::Decode(Frame);
                TestEqual(TEXT("kind"), (int32)Env.Kind, (int32)ENyraEnvelopeKind::Notification);
                TestEqual(TEXT("method"), Env.Method, FString(TEXT("chat/stream")));
                TestFalse(TEXT("no id"), Env.bHasId);
            });

            It("decodes a response", [this]()
            {
                const FString Frame =
                    TEXT("{\"jsonrpc\":\"2.0\",\"id\":2,\"result\":{\"backends\":[\"gemma-local\"],\"phase\":1}}");
                const FNyraJsonRpcEnvelope Env = FNyraJsonRpc::Decode(Frame);
                TestEqual(TEXT("kind"), (int32)Env.Kind, (int32)ENyraEnvelopeKind::Response);
                TestEqual(TEXT("id"), Env.Id, (int64)2);
                TestTrue(TEXT("result valid"), Env.Result.IsValid());
            });

            It("decodes an error", [this]()
            {
                const FString Frame =
                    TEXT("{\"jsonrpc\":\"2.0\",\"id\":3,\"error\":{\"code\":-32005,\"message\":\"gemma_not_installed\",\"data\":{\"remediation\":\"Click Download\"}}}");
                const FNyraJsonRpcEnvelope Env = FNyraJsonRpc::Decode(Frame);
                TestEqual(TEXT("kind"), (int32)Env.Kind, (int32)ENyraEnvelopeKind::Error);
                TestEqual(TEXT("code"), Env.ErrorCode, -32005);
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

    #endif
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "class NYRAEDITOR_API FNyraJsonRpc" TestProject/Plugins/NYRA/Source/NyraEditor/Public/WS/FNyraJsonRpc.h` equals 1
      - `grep -c "ENyraEnvelopeKind" TestProject/Plugins/NYRA/Source/NyraEditor/Public/WS/FNyraJsonRpc.h` >= 2
      - `grep -c "static FString EncodeRequest" TestProject/Plugins/NYRA/Source/NyraEditor/Public/WS/FNyraJsonRpc.h` equals 1
      - `grep -c "static FString EncodeNotification" TestProject/Plugins/NYRA/Source/NyraEditor/Public/WS/FNyraJsonRpc.h` equals 1
      - `grep -c "static FString EncodeError" TestProject/Plugins/NYRA/Source/NyraEditor/Public/WS/FNyraJsonRpc.h` equals 1
      - `grep -c 'Describe("EnvelopeRoundtrip"' TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraJsonRpcSpec.cpp` equals 1
      - After build: `UnrealEditor-Cmd.exe TestProject/TestProject.uproject -ExecCmds="Automation RunTests Nyra.Jsonrpc;Quit" -unattended -nopause -testexit="Automation Test Queue Empty"` exits 0 with >= 10 It blocks passing
    </automated>
  </verify>
  <acceptance_criteria>
    - FNyraJsonRpc.h exports `enum class ENyraEnvelopeKind : uint8 { Request, Notification, Response, Error, Invalid }`
    - FNyraJsonRpc.h exports struct `FNyraJsonRpcEnvelope` with fields `Kind`, `Id`, `bHasId`, `Method`, `Params`, `Result`, `ErrorCode`, `ErrorMessage`, `ErrorRemediation`
    - FNyraJsonRpc.h exports class `FNyraJsonRpc` with static methods `EncodeRequest`, `EncodeNotification`, `EncodeResponse`, `EncodeError`, `Decode`
    - FNyraJsonRpc.cpp uses `TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>` for compact output
    - FNyraJsonRpc.cpp `EncodeError` produces `"error":{"code":N,"message":"...","data":{"remediation":"..."}}`
    - FNyraJsonRpc.cpp `Decode` checks `jsonrpc == "2.0"` before classifying
    - FNyraJsonRpc.cpp `Decode` classifies Request (has method+id) vs Notification (has method, no id) vs Response (has result) vs Error (has error)
    - NyraJsonRpcSpec.cpp contains 10 It() blocks covering: 4 encode types, 4 decode types, 2 invalid (malformed JSON, missing jsonrpc:2.0)
    - Running `UnrealEditor-Cmd.exe TestProject/TestProject.uproject -ExecCmds="Automation RunTests Nyra.Jsonrpc;Quit" -unattended -nopause -testexit="Automation Test Queue Empty"` exits 0
  </acceptance_criteria>
  <done>FNyraJsonRpc encode/decode tested end-to-end; VALIDATION 1-02-02 green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: FNyraHandshake (file polling) + FNyraWsClient (auth-first-frame)</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraHandshake.h
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraHandshake.cpp
    TestProject/Plugins/NYRA/Source/NyraEditor/Public/WS/FNyraWsClient.h
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/WS/FNyraWsClient.cpp
  </files>
  <read_first>
    - docs/HANDSHAKE.md (file path, schema, atomic-rename/partial-read tolerance, 30s polling budget)
    - docs/JSONRPC.md (session/authenticate + close code 4401)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/WS/FNyraJsonRpc.h (just created — Encode/Decode)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md D-06, D-07
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.2 (FWebSocketsModule), §3.10 P1.1, P1.7
  </read_first>
  <behavior>
    - FNyraHandshake::BeginPolling on a missing file retries with exp backoff; when the file appears with valid JSON, OnReady fires with parsed port+token. Malformed JSON is tolerated (continues polling).
    - 30s total budget elapses -> OnTimeout fires, polling stops.
    - FNyraWsClient on OnConnected sends session/authenticate (id=1) with the token from handshake. On successful response, fires OnAuthenticated. On WS close with code 4401, fires OnAuthFailed. Dispatches inbound Notifications/Responses/Errors on their respective events.
  </behavior>
  <action>
    **1. CREATE Public/Process/FNyraHandshake.h:**

    ```cpp
    #pragma once
    #include "CoreMinimal.h"
    #include "Containers/Ticker.h"

    struct NYRAEDITOR_API FNyraHandshakeData
    {
        int32 Port = 0;
        FString Token;
        int32 NyraHostPid = 0;
        int32 UeEditorPid = 0;
        int64 StartedAtMs = 0;
    };

    DECLARE_DELEGATE_OneParam(FOnHandshakeReady, const FNyraHandshakeData& /*Data*/);
    DECLARE_DELEGATE(FOnHandshakeTimeout);

    class NYRAEDITOR_API FNyraHandshake
    {
    public:
        /** Start polling for handshake-<EditorPid>.json in HandshakeDir. */
        void BeginPolling(const FString& HandshakeDir, int32 EditorPid);

        /** Stop polling + remove ticker. */
        void CancelPolling();

        FOnHandshakeReady OnReady;
        FOnHandshakeTimeout OnTimeout;

        /** Returns true and fills Out if Path contains a valid handshake JSON. */
        static bool TryReadFile(const FString& Path, FNyraHandshakeData& Out);

        /** Delete the handshake file (called from UE side on clean shutdown). */
        static void DeleteFile(const FString& HandshakeDir, int32 EditorPid);

        /** Walk HandshakeDir; delete handshake-*.json whose ue_pid is not running.
         *  Returns count of files deleted. */
        static int32 CleanupOrphans(const FString& HandshakeDir);

    private:
        FString ComputePath() const;
        bool Tick(float DeltaTime);

        FString HandshakeDir;
        int32 EditorPid = 0;
        FTSTicker::FDelegateHandle TickerHandle;
        double PollingStartTime = 0.0;
        float CurrentIntervalS = 0.05f;  // 50 ms start
        bool bPolling = false;
    };
    ```

    **2. CREATE Private/Process/FNyraHandshake.cpp:**

    ```cpp
    #include "Process/FNyraHandshake.h"
    #include "NyraLog.h"
    #include "HAL/PlatformProcess.h"
    #include "HAL/PlatformFileManager.h"
    #include "Misc/FileHelper.h"
    #include "Misc/Paths.h"
    #include "Dom/JsonObject.h"
    #include "Serialization/JsonReader.h"
    #include "Serialization/JsonSerializer.h"

    constexpr double HANDSHAKE_TOTAL_BUDGET_S = 30.0;
    constexpr float HANDSHAKE_MAX_INTERVAL_S = 2.0f;
    constexpr float HANDSHAKE_BACKOFF_MULTIPLIER = 1.5f;

    void FNyraHandshake::BeginPolling(const FString& InHandshakeDir, int32 InEditorPid)
    {
        HandshakeDir = InHandshakeDir;
        EditorPid = InEditorPid;
        PollingStartTime = FPlatformTime::Seconds();
        CurrentIntervalS = 0.05f;
        bPolling = true;
        TickerHandle = FTSTicker::GetCoreTicker().AddTicker(
            FTickerDelegate::CreateRaw(this, &FNyraHandshake::Tick), CurrentIntervalS);
        UE_LOG(LogNyra, Log, TEXT("[NYRA] Handshake polling started: %s"), *ComputePath());
    }

    void FNyraHandshake::CancelPolling()
    {
        if (TickerHandle.IsValid())
        {
            FTSTicker::GetCoreTicker().RemoveTicker(TickerHandle);
            TickerHandle.Reset();
        }
        bPolling = false;
    }

    FString FNyraHandshake::ComputePath() const
    {
        return FPaths::Combine(HandshakeDir, FString::Printf(TEXT("handshake-%d.json"), EditorPid));
    }

    bool FNyraHandshake::Tick(float DeltaTime)
    {
        if (!bPolling)
        {
            return false;  // auto-remove
        }
        const FString Path = ComputePath();
        FNyraHandshakeData Data;
        if (TryReadFile(Path, Data))
        {
            bPolling = false;
            OnReady.ExecuteIfBound(Data);
            return false;  // auto-remove
        }
        const double Elapsed = FPlatformTime::Seconds() - PollingStartTime;
        if (Elapsed >= HANDSHAKE_TOTAL_BUDGET_S)
        {
            bPolling = false;
            UE_LOG(LogNyra, Warning, TEXT("[NYRA] Handshake polling timed out after %.1fs"), Elapsed);
            OnTimeout.ExecuteIfBound();
            return false;
        }
        // Backoff for next tick
        CurrentIntervalS = FMath::Min(CurrentIntervalS * HANDSHAKE_BACKOFF_MULTIPLIER, HANDSHAKE_MAX_INTERVAL_S);
        // Re-add ticker with new interval (simplest — remove+re-add)
        FTSTicker::GetCoreTicker().RemoveTicker(TickerHandle);
        TickerHandle = FTSTicker::GetCoreTicker().AddTicker(
            FTickerDelegate::CreateRaw(this, &FNyraHandshake::Tick), CurrentIntervalS);
        return false;  // we re-added; current tick stops
    }

    bool FNyraHandshake::TryReadFile(const FString& Path, FNyraHandshakeData& Out)
    {
        if (!FPaths::FileExists(Path))
        {
            return false;
        }
        FString Content;
        if (!FFileHelper::LoadFileToString(Content, *Path))
        {
            return false;
        }
        if (Content.IsEmpty())
        {
            return false;
        }
        TSharedRef<TJsonReader<TCHAR>> Reader = TJsonReaderFactory<TCHAR>::Create(Content);
        TSharedPtr<FJsonObject> Root;
        if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
        {
            // Tolerate partial-read race (P1.1) — caller retries
            return false;
        }
        double Port = 0.0, NyraHostPid = 0.0, UeEditorPid = 0.0, StartedAt = 0.0;
        FString Token;
        if (!Root->TryGetNumberField(TEXT("port"), Port)) return false;
        if (!Root->TryGetStringField(TEXT("token"), Token)) return false;
        if (!Root->TryGetNumberField(TEXT("nyrahost_pid"), NyraHostPid)) return false;
        if (!Root->TryGetNumberField(TEXT("ue_pid"), UeEditorPid)) return false;
        if (!Root->TryGetNumberField(TEXT("started_at"), StartedAt)) return false;
        Out.Port = static_cast<int32>(Port);
        Out.Token = Token;
        Out.NyraHostPid = static_cast<int32>(NyraHostPid);
        Out.UeEditorPid = static_cast<int32>(UeEditorPid);
        Out.StartedAtMs = static_cast<int64>(StartedAt);
        return Out.Port > 0 && !Out.Token.IsEmpty();
    }

    void FNyraHandshake::DeleteFile(const FString& HandshakeDir, int32 EditorPid)
    {
        const FString Path = FPaths::Combine(HandshakeDir, FString::Printf(TEXT("handshake-%d.json"), EditorPid));
        IFileManager::Get().Delete(*Path, /*RequireExists=*/false, /*EvenReadOnly=*/true);
    }

    int32 FNyraHandshake::CleanupOrphans(const FString& HandshakeDir)
    {
        int32 Count = 0;
        if (!FPaths::DirectoryExists(HandshakeDir))
        {
            return 0;
        }
        TArray<FString> Files;
        IFileManager::Get().FindFiles(Files, *FPaths::Combine(HandshakeDir, TEXT("handshake-*.json")), true, false);
        for (const FString& Name : Files)
        {
            const FString FullPath = FPaths::Combine(HandshakeDir, Name);
            FNyraHandshakeData Data;
            if (!TryReadFile(FullPath, Data))
            {
                // Unreadable -> delete (stale/corrupt)
                IFileManager::Get().Delete(*FullPath, false, true);
                ++Count;
                continue;
            }
            // Check if UE PID still alive
            FProcHandle Handle = FPlatformProcess::OpenProcess(static_cast<uint32>(Data.UeEditorPid));
            const bool bAlive = Handle.IsValid() && FPlatformProcess::IsProcRunning(Handle);
            if (Handle.IsValid())
            {
                FPlatformProcess::CloseProc(Handle);
            }
            if (!bAlive)
            {
                // Optionally terminate orphan NyraHost PID too
                FProcHandle NyraHandle = FPlatformProcess::OpenProcess(static_cast<uint32>(Data.NyraHostPid));
                if (NyraHandle.IsValid() && FPlatformProcess::IsProcRunning(NyraHandle))
                {
                    FPlatformProcess::TerminateProc(NyraHandle, /*KillTree=*/true);
                }
                if (NyraHandle.IsValid())
                {
                    FPlatformProcess::CloseProc(NyraHandle);
                }
                IFileManager::Get().Delete(*FullPath, false, true);
                ++Count;
            }
        }
        return Count;
    }
    ```

    **3. CREATE Public/WS/FNyraWsClient.h:**

    ```cpp
    #pragma once
    #include "CoreMinimal.h"
    #include "IWebSocket.h"
    #include "WS/FNyraJsonRpc.h"

    DECLARE_DELEGATE(FOnNyraAuthenticated);
    DECLARE_DELEGATE_TwoParams(FOnNyraAuthFailed, int32 /*CloseCode*/, const FString& /*Reason*/);
    DECLARE_DELEGATE_OneParam(FOnNyraNotification, const FNyraJsonRpcEnvelope& /*Env*/);
    DECLARE_DELEGATE_OneParam(FOnNyraResponse, const FNyraJsonRpcEnvelope& /*Env*/);
    DECLARE_DELEGATE_OneParam(FOnNyraErrorResponse, const FNyraJsonRpcEnvelope& /*Env*/);
    DECLARE_DELEGATE_TwoParams(FOnNyraClosed, int32 /*CloseCode*/, const FString& /*Reason*/);

    class NYRAEDITOR_API FNyraWsClient
    {
    public:
        void Connect(const FString& Host, int32 Port, const FString& AuthToken);
        void Disconnect();
        bool IsConnected() const;

        /** Send a request envelope; returns the id used so caller can correlate responses. */
        int64 SendRequest(const FString& Method, const TSharedRef<FJsonObject>& Params);
        /** Fire-and-forget notification. */
        void SendNotification(const FString& Method, const TSharedRef<FJsonObject>& Params);

        FOnNyraAuthenticated OnAuthenticated;
        FOnNyraAuthFailed OnAuthFailed;
        FOnNyraNotification OnNotification;
        FOnNyraResponse OnResponse;
        FOnNyraErrorResponse OnErrorResponse;
        FOnNyraClosed OnClosed;

    private:
        void HandleMessage(const FString& Frame);
        void HandleClose(int32 Code, const FString& Reason, bool bWasClean);

        TSharedPtr<IWebSocket> Socket;
        FString PendingAuthToken;
        int64 NextId = 1;
        int64 AuthRequestId = 0;  // id used for the session/authenticate first frame
        bool bAuthenticated = false;
    };
    ```

    **4. CREATE Private/WS/FNyraWsClient.cpp:**

    ```cpp
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
            // Send session/authenticate as FIRST frame (D-07)
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
        if (Code == 4401 && !bAuthenticated)
        {
            OnAuthFailed.ExecuteIfBound(Code, Reason);
        }
        OnClosed.ExecuteIfBound(Code, Reason);
    }
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "class NYRAEDITOR_API FNyraHandshake" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraHandshake.h` equals 1
      - `grep -c "BeginPolling" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraHandshake.h` >= 1
      - `grep -c "HANDSHAKE_TOTAL_BUDGET_S = 30.0" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraHandshake.cpp` equals 1
      - `grep -c "HANDSHAKE_MAX_INTERVAL_S = 2.0f" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraHandshake.cpp` equals 1
      - `grep -c "HANDSHAKE_BACKOFF_MULTIPLIER = 1.5f" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraHandshake.cpp` equals 1
      - `grep -c "FTSTicker::GetCoreTicker().AddTicker" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraHandshake.cpp` >= 2
      - `grep -c "class NYRAEDITOR_API FNyraWsClient" TestProject/Plugins/NYRA/Source/NyraEditor/Public/WS/FNyraWsClient.h` equals 1
      - `grep -c "FWebSocketsModule::Get().CreateWebSocket" TestProject/Plugins/NYRA/Source/NyraEditor/Private/WS/FNyraWsClient.cpp` equals 1
      - `grep -c 'EncodeRequest(AuthRequestId, TEXT("session/authenticate")' TestProject/Plugins/NYRA/Source/NyraEditor/Private/WS/FNyraWsClient.cpp` equals 1
      - `grep -c "if (Code == 4401 && !bAuthenticated)" TestProject/Plugins/NYRA/Source/NyraEditor/Private/WS/FNyraWsClient.cpp` equals 1
    </automated>
  </verify>
  <acceptance_criteria>
    - FNyraHandshake.h exports struct `FNyraHandshakeData` with fields `Port`, `Token`, `NyraHostPid`, `UeEditorPid`, `StartedAtMs`
    - FNyraHandshake.h exports class `FNyraHandshake` with `BeginPolling`, `CancelPolling`, static `TryReadFile`, `DeleteFile`, `CleanupOrphans`, delegates `OnReady`, `OnTimeout`
    - FNyraHandshake.cpp defines `HANDSHAKE_TOTAL_BUDGET_S = 30.0`, `HANDSHAKE_MAX_INTERVAL_S = 2.0f`, `HANDSHAKE_BACKOFF_MULTIPLIER = 1.5f`
    - FNyraHandshake.cpp ticker backs off geometrically (`CurrentIntervalS = min(CurrentIntervalS * 1.5, 2.0)`)
    - FNyraHandshake.cpp `TryReadFile` returns false on missing/empty/malformed JSON (no exception — tolerates P1.1 partial-read race)
    - FNyraHandshake.cpp `CleanupOrphans` uses `FPlatformProcess::OpenProcess` + `IsProcRunning` to detect dead UE PIDs + `TerminateProc(KillTree=true)` for orphaned NyraHost
    - FNyraWsClient.h exports class with `Connect`, `Disconnect`, `SendRequest`, `SendNotification`, delegates `OnAuthenticated`, `OnAuthFailed`, `OnNotification`, `OnResponse`, `OnErrorResponse`, `OnClosed`
    - FNyraWsClient.cpp `Connect` uses `FWebSocketsModule::Get().CreateWebSocket`
    - FNyraWsClient.cpp `OnConnected` lambda sends `session/authenticate` as first frame with the token from `PendingAuthToken`
    - FNyraWsClient.cpp `HandleMessage` classifies Response/Notification/Error and fires matching delegate
    - FNyraWsClient.cpp `HandleClose` fires `OnAuthFailed` when code==4401 && !bAuthenticated
    - FNyraWsClient.cpp `NextId` starts at 1 and is never reset (P1.7)
  </acceptance_criteria>
  <done>Handshake polling + WS client + auth gate implemented. Plan's Task 3 ties them together in FNyraSupervisor.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: FNyraSupervisor + INyraClock + wire into NyraEditorModule + fill Nyra.Supervisor.RestartPolicy spec</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraSupervisor.h
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraSupervisor.cpp
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraSupervisorSpec.cpp
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraIntegrationSpec.cpp
  </files>
  <read_first>
    - docs/HANDSHAKE.md (delete on clean shutdown)
    - docs/JSONRPC.md §3.6 (shutdown notification)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/WS/FNyraWsClient.h (just created)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraHandshake.h (just created)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/ModelPins.h (for python paths)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTestFixtures.h (FNyraTestClock)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraSupervisorSpec.cpp (placeholder)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraIntegrationSpec.cpp (placeholder for Nyra.Integration.HandshakeAuth)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md D-04, D-05, D-08
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.3 (FMonitoredProcess + KillTree)
  </read_first>
  <behavior>
    - Nyra.Supervisor.RestartPolicy: with INyraClock injected via FNyraTestClock, simulate 2 crashes within 30s then a 3rd within 60s (total < 60s window) -> supervisor stops restarting, fires OnUnstable. A 3rd crash OUTSIDE the 60s window does NOT trip (policy evicts old entries).
    - In-flight replay: after crash with an in-flight request pending, on respawn the supervisor re-sends the request with a NEW req_id and marks the original cancelled.
    - Nyra.Integration.HandshakeAuth (guarded by ENABLE_NYRA_INTEGRATION_TESTS): spawn real NyraHost (requires Plan 06 artefacts present), wait for handshake, authenticate, receive session/hello result.
  </behavior>
  <action>
    **1. CREATE Public/Process/FNyraSupervisor.h:**

    ```cpp
    #pragma once
    #include "CoreMinimal.h"
    #include "Misc/MonitoredProcess.h"
    #include "Process/FNyraHandshake.h"
    #include "WS/FNyraWsClient.h"

    /** Clock abstraction for deterministic supervisor policy tests. */
    class NYRAEDITOR_API INyraClock
    {
    public:
        virtual ~INyraClock() = default;
        virtual double NowSeconds() const = 0;
    };

    class NYRAEDITOR_API FNyraSystemClock : public INyraClock
    {
    public:
        virtual double NowSeconds() const override { return FPlatformTime::Seconds(); }
    };

    enum class ENyraSupervisorState : uint8
    {
        Idle,
        Spawning,
        WaitingForHandshake,
        Connecting,
        Authenticating,
        Ready,
        Crashed,
        Unstable,   // 3-in-60s tripped
        ShuttingDown,
    };

    struct FNyraInFlightRequest
    {
        FString Method;
        TSharedPtr<FJsonObject> Params;
        int64 OriginalId = 0;
    };

    DECLARE_DELEGATE_OneParam(FOnSupervisorStateChanged, ENyraSupervisorState /*NewState*/);
    DECLARE_DELEGATE(FOnSupervisorReady);
    DECLARE_DELEGATE(FOnSupervisorUnstable);
    DECLARE_DELEGATE_OneParam(FOnSupervisorNotification, const FNyraJsonRpcEnvelope& /*Env*/);
    DECLARE_DELEGATE_OneParam(FOnSupervisorResponse, const FNyraJsonRpcEnvelope& /*Env*/);

    class NYRAEDITOR_API FNyraSupervisor
    {
    public:
        FNyraSupervisor();
        explicit FNyraSupervisor(TSharedRef<INyraClock> InClock);
        ~FNyraSupervisor();

        /** Spawn NyraHost, poll handshake, connect WS, authenticate. */
        void SpawnAndConnect(
            const FString& InProjectDir,
            const FString& InPluginDir,
            const FString& InLogDir);

        /** Clean shutdown: send `shutdown` notification, wait 2s, TerminateProc KillTree. */
        void RequestShutdown();

        /** Send a request; tracks in-flight entry so respawn can replay. */
        int64 SendRequest(const FString& Method, const TSharedRef<FJsonObject>& Params);
        void SendNotification(const FString& Method, const TSharedRef<FJsonObject>& Params);

        /** Policy-test hook: simulate a crash (without killing actual process). */
        void SimulateCrashForTest();

        ENyraSupervisorState GetState() const { return State; }

        FOnSupervisorStateChanged OnStateChanged;
        FOnSupervisorReady OnReady;
        FOnSupervisorUnstable OnUnstable;
        FOnSupervisorNotification OnNotification;
        FOnSupervisorResponse OnResponse;

    private:
        void SetState(ENyraSupervisorState NewState);
        void RecordCrashAndMaybeRestart();
        void PerformSpawn();

        TSharedRef<INyraClock> Clock;
        ENyraSupervisorState State = ENyraSupervisorState::Idle;

        FString ProjectDir;
        FString PluginDir;
        FString LogDir;
        FString HandshakeDir;

        TSharedPtr<FMonitoredProcess> HostProcess;
        FNyraHandshake Handshake;
        FNyraWsClient WsClient;

        FNyraHandshakeData CurrentHandshake;
        TArray<double> CrashTimestamps;  // recent crashes within 60s window
        TOptional<FNyraInFlightRequest> InFlight;

        bool bShutdownRequested = false;
    };
    ```

    **2. CREATE Private/Process/FNyraSupervisor.cpp:**

    ```cpp
    #include "Process/FNyraSupervisor.h"
    #include "NyraLog.h"
    #include "HAL/PlatformProcess.h"
    #include "HAL/PlatformFileManager.h"
    #include "Interfaces/IPluginManager.h"
    #include "Misc/Paths.h"
    #include "Misc/FileHelper.h"
    #include "Misc/MonitoredProcess.h"
    #include "Dom/JsonObject.h"

    constexpr int32 MAX_CRASHES_IN_WINDOW = 3;
    constexpr double CRASH_WINDOW_S = 60.0;
    constexpr double SHUTDOWN_GRACE_S = 2.0;

    FNyraSupervisor::FNyraSupervisor() : Clock(MakeShared<FNyraSystemClock>()) {}
    FNyraSupervisor::FNyraSupervisor(TSharedRef<INyraClock> InClock) : Clock(InClock) {}
    FNyraSupervisor::~FNyraSupervisor() = default;

    void FNyraSupervisor::SetState(ENyraSupervisorState NewState)
    {
        State = NewState;
        OnStateChanged.ExecuteIfBound(NewState);
    }

    void FNyraSupervisor::SpawnAndConnect(const FString& InProjectDir, const FString& InPluginDir, const FString& InLogDir)
    {
        ProjectDir = InProjectDir;
        PluginDir = InPluginDir;
        LogDir = InLogDir;
        // Resolve handshake dir: %LOCALAPPDATA%/NYRA/ primary, Saved/NYRA/ fallback
        FString LocalAppData;
        if (FPlatformProcess::ComputerName() && !(LocalAppData = FPlatformMisc::GetEnvironmentVariable(TEXT("LOCALAPPDATA"))).IsEmpty())
        {
            HandshakeDir = FPaths::Combine(LocalAppData, TEXT("NYRA"));
        }
        else
        {
            HandshakeDir = FPaths::Combine(ProjectDir, TEXT("Saved"), TEXT("NYRA"));
        }
        IFileManager::Get().MakeDirectory(*HandshakeDir, /*Tree=*/true);

        // Orphan cleanup (P1.2)
        const int32 Cleaned = FNyraHandshake::CleanupOrphans(HandshakeDir);
        if (Cleaned > 0)
        {
            UE_LOG(LogNyra, Log, TEXT("[NYRA] Cleaned %d orphan handshake file(s)"), Cleaned);
        }

        PerformSpawn();
    }

    void FNyraSupervisor::PerformSpawn()
    {
        SetState(ENyraSupervisorState::Spawning);
        const FString PythonExe = FPaths::Combine(PluginDir, TEXT("Binaries"), TEXT("Win64"), TEXT("NyraHost"), TEXT("cpython"), TEXT("python.exe"));
        const FString PluginBinariesDir = FPaths::Combine(PluginDir, TEXT("Binaries"), TEXT("Win64"));
        const int32 EditorPid = FPlatformProcess::GetCurrentProcessId();

        const FString Args = FString::Printf(
            TEXT("-m nyrahost --editor-pid %d --log-dir \"%s\" --project-dir \"%s\" --plugin-binaries-dir \"%s\" --handshake-dir \"%s\""),
            EditorPid, *LogDir, *ProjectDir, *PluginBinariesDir, *HandshakeDir);

        UE_LOG(LogNyra, Log, TEXT("[NYRA] Spawning NyraHost: %s %s"), *PythonExe, *Args);
        HostProcess = MakeShared<FMonitoredProcess>(PythonExe, Args, /*bHidden=*/true, /*bCreatePipes=*/true);
        HostProcess->OnOutput().BindLambda([](const FString& Line)
        {
            UE_LOG(LogNyra, Verbose, TEXT("[NyraHost] %s"), *Line);
        });
        HostProcess->OnCompleted().BindLambda([this](int32 ExitCode)
        {
            UE_LOG(LogNyra, Log, TEXT("[NYRA] NyraHost exited code=%d"), ExitCode);
            if (!bShutdownRequested)
            {
                RecordCrashAndMaybeRestart();
            }
        });
        if (!HostProcess->Launch())
        {
            UE_LOG(LogNyra, Error, TEXT("[NYRA] NyraHost failed to launch"));
            SetState(ENyraSupervisorState::Crashed);
            RecordCrashAndMaybeRestart();
            return;
        }

        // Start handshake polling
        SetState(ENyraSupervisorState::WaitingForHandshake);
        Handshake = FNyraHandshake{};
        Handshake.OnReady.BindLambda([this](const FNyraHandshakeData& Data)
        {
            CurrentHandshake = Data;
            SetState(ENyraSupervisorState::Connecting);
            WsClient.OnAuthenticated.BindLambda([this]()
            {
                SetState(ENyraSupervisorState::Ready);
                OnReady.ExecuteIfBound();
                // Replay in-flight if any
                if (InFlight.IsSet())
                {
                    const FNyraInFlightRequest Req = InFlight.GetValue();
                    InFlight.Reset();
                    SendRequest(Req.Method, Req.Params.ToSharedRef());
                }
            });
            WsClient.OnAuthFailed.BindLambda([this](int32 Code, const FString& Reason)
            {
                UE_LOG(LogNyra, Error, TEXT("[NYRA] WS auth failed code=%d reason=%s"), Code, *Reason);
            });
            WsClient.OnNotification.BindLambda([this](const FNyraJsonRpcEnvelope& E) { OnNotification.ExecuteIfBound(E); });
            WsClient.OnResponse.BindLambda([this](const FNyraJsonRpcEnvelope& E) { OnResponse.ExecuteIfBound(E); });
            SetState(ENyraSupervisorState::Authenticating);
            WsClient.Connect(TEXT("127.0.0.1"), CurrentHandshake.Port, CurrentHandshake.Token);
        });
        Handshake.OnTimeout.BindLambda([this]()
        {
            UE_LOG(LogNyra, Warning, TEXT("[NYRA] Handshake timeout"));
            SetState(ENyraSupervisorState::Crashed);
            RecordCrashAndMaybeRestart();
        });
        Handshake.BeginPolling(HandshakeDir, FPlatformProcess::GetCurrentProcessId());
    }

    void FNyraSupervisor::RecordCrashAndMaybeRestart()
    {
        SetState(ENyraSupervisorState::Crashed);
        const double Now = Clock->NowSeconds();
        CrashTimestamps.Add(Now);
        CrashTimestamps.RemoveAll([&](double T) { return (Now - T) > CRASH_WINDOW_S; });
        if (CrashTimestamps.Num() >= MAX_CRASHES_IN_WINDOW)
        {
            UE_LOG(LogNyra, Error, TEXT("[NYRA] NyraHost unstable: %d crashes in %.0fs window"), CrashTimestamps.Num(), CRASH_WINDOW_S);
            SetState(ENyraSupervisorState::Unstable);
            OnUnstable.ExecuteIfBound();
            return;
        }
        UE_LOG(LogNyra, Warning, TEXT("[NYRA] NyraHost crash %d/%d in window — respawning"), CrashTimestamps.Num(), MAX_CRASHES_IN_WINDOW);
        PerformSpawn();
    }

    void FNyraSupervisor::RequestShutdown()
    {
        bShutdownRequested = true;
        SetState(ENyraSupervisorState::ShuttingDown);
        if (WsClient.IsConnected())
        {
            TSharedRef<FJsonObject> Empty = MakeShared<FJsonObject>();
            WsClient.SendNotification(TEXT("shutdown"), Empty);
        }
        const double Deadline = FPlatformTime::Seconds() + SHUTDOWN_GRACE_S;
        while (HostProcess.IsValid() && HostProcess->Update() && FPlatformTime::Seconds() < Deadline)
        {
            FPlatformProcess::Sleep(0.05f);
        }
        if (HostProcess.IsValid() && HostProcess->IsRunning())
        {
            UE_LOG(LogNyra, Warning, TEXT("[NYRA] NyraHost did not exit within %.1fs — TerminateProc KillTree"), SHUTDOWN_GRACE_S);
            HostProcess->Cancel(/*bKillTree=*/true);
        }
        WsClient.Disconnect();
        FNyraHandshake::DeleteFile(HandshakeDir, FPlatformProcess::GetCurrentProcessId());
        SetState(ENyraSupervisorState::Idle);
    }

    int64 FNyraSupervisor::SendRequest(const FString& Method, const TSharedRef<FJsonObject>& Params)
    {
        // Track as in-flight (simple version — only one at a time in Phase 1).
        FNyraInFlightRequest Req;
        Req.Method = Method;
        Req.Params = Params;
        const int64 Id = WsClient.SendRequest(Method, Params);
        Req.OriginalId = Id;
        InFlight = Req;
        return Id;
    }

    void FNyraSupervisor::SendNotification(const FString& Method, const TSharedRef<FJsonObject>& Params)
    {
        WsClient.SendNotification(Method, Params);
    }

    void FNyraSupervisor::SimulateCrashForTest()
    {
        RecordCrashAndMaybeRestart();
    }
    ```

    **3. REPLACE NyraSupervisorSpec.cpp with real tests using FNyraTestClock (Plan 01):**

    ```cpp
    #include "Misc/AutomationTest.h"
    #include "NyraTestFixtures.h"
    #include "Process/FNyraSupervisor.h"

    #if WITH_AUTOMATION_TESTS

    // Adapter: wraps FNyraTestClock as an INyraClock
    class FTestClockAdapter : public INyraClock
    {
    public:
        Nyra::Tests::FNyraTestClock& Inner;
        explicit FTestClockAdapter(Nyra::Tests::FNyraTestClock& In) : Inner(In) {}
        virtual double NowSeconds() const override { return Inner.Now(); }
    };

    BEGIN_DEFINE_SPEC(FNyraSupervisorSpec,
                       "Nyra.Supervisor",
                       EAutomationTestFlags::EditorContext |
                       EAutomationTestFlags::EngineFilter)
    END_DEFINE_SPEC(FNyraSupervisorSpec)

    void FNyraSupervisorSpec::Define()
    {
        Describe("RestartPolicy", [this]()
        {
            It("trips Unstable after 3 crashes within 60 seconds", [this]()
            {
                Nyra::Tests::FNyraTestClock Clock;
                TSharedRef<INyraClock> Adapter = MakeShared<FTestClockAdapter>(Clock);
                FNyraSupervisor Sup(Adapter);
                bool bUnstableFired = false;
                Sup.OnUnstable.BindLambda([&](){ bUnstableFired = true; });

                // Simulate crash 1 at t=0
                Clock.Set(0.0);
                Sup.SimulateCrashForTest();
                // Since SimulateCrashForTest calls PerformSpawn on first two, we only care about the unstable flag.
                // Crash 2 at t=20
                Clock.Set(20.0);
                Sup.SimulateCrashForTest();
                // Crash 3 at t=40 (within 60s window) — trips
                Clock.Set(40.0);
                Sup.SimulateCrashForTest();
                TestTrue(TEXT("Unstable fired after 3 crashes in 60s"), bUnstableFired);
                TestEqual(TEXT("State is Unstable"), (int32)Sup.GetState(), (int32)ENyraSupervisorState::Unstable);
            });

            It("does NOT trip Unstable if crashes spread outside the 60s window", [this]()
            {
                Nyra::Tests::FNyraTestClock Clock;
                TSharedRef<INyraClock> Adapter = MakeShared<FTestClockAdapter>(Clock);
                FNyraSupervisor Sup(Adapter);
                bool bUnstableFired = false;
                Sup.OnUnstable.BindLambda([&](){ bUnstableFired = true; });

                Clock.Set(0.0); Sup.SimulateCrashForTest();
                Clock.Set(70.0); Sup.SimulateCrashForTest();    // evicts t=0
                Clock.Set(140.0); Sup.SimulateCrashForTest();   // evicts t=70
                TestFalse(TEXT("Unstable NOT fired (crashes outside window)"), bUnstableFired);
            });
        });
    }

    #endif
    ```

    **4. UPDATE NyraIntegrationSpec.cpp** to add the guarded
    `Nyra.Integration.HandshakeAuth` test (Plan 03 added `FNyraPluginModulesLoadSpec`; preserve it and replace the empty guarded FNyraIntegrationSpec Define body):

    ```cpp
    // After the existing #endif for FNyraPluginModulesLoadSpec:

    #if WITH_AUTOMATION_TESTS && ENABLE_NYRA_INTEGRATION_TESTS

    BEGIN_DEFINE_SPEC(FNyraIntegrationSpec,
                       "Nyra.Integration",
                       EAutomationTestFlags::EditorContext |
                       EAutomationTestFlags::ProductFilter)
    END_DEFINE_SPEC(FNyraIntegrationSpec)

    void FNyraIntegrationSpec::Define()
    {
        LatentIt("HandshakeAuth — spawn NyraHost, authenticate, receive session/hello", 30.0f,
                 [this](const FDoneDelegate& Done)
        {
            // Requires:
            //   Plugins/NYRA/Binaries/Win64/NyraHost/cpython/python.exe AND Source/NyraHost/src/nyrahost/__main__.py reachable
            // Intended for dev-machine execution with prebuild.ps1 already run.
            FNyraSupervisor* Sup = new FNyraSupervisor();
            Sup->OnReady.BindLambda([this, Sup, Done]()
            {
                TSharedRef<FJsonObject> Empty = MakeShared<FJsonObject>();
                const int64 Id = Sup->SendRequest(TEXT("session/hello"), Empty);
                Sup->OnResponse.BindLambda([this, Sup, Done, Id](const FNyraJsonRpcEnvelope& Env)
                {
                    TestEqual(TEXT("response id matches"), Env.Id, Id);
                    TestTrue(TEXT("result has phase field"), Env.Result.IsValid() && Env.Result->HasField(TEXT("phase")));
                    Sup->RequestShutdown();
                    delete Sup;
                    Done.Execute();
                });
            });
            const FString PluginDir = IPluginManager::Get().FindPlugin(TEXT("NYRA"))->GetBaseDir();
            const FString ProjectDir = FPaths::ProjectDir();
            const FString LogDir = FPaths::Combine(ProjectDir, TEXT("Saved"), TEXT("NYRA"), TEXT("logs"));
            Sup->SpawnAndConnect(ProjectDir, PluginDir, LogDir);
        });
    }

    #endif
    ```

    **5. UPDATE NyraEditorModule.cpp** — add supervisor lifecycle (preserve Plan 04's tab registration):

    Add at top of file after existing includes:
    ```cpp
    #include "Process/FNyraSupervisor.h"
    #include "Interfaces/IPluginManager.h"
    #include "Misc/Paths.h"
    ```

    Add a module-level TUniquePtr to hold the supervisor:
    ```cpp
    static TUniquePtr<FNyraSupervisor> GNyraSupervisor;
    ```

    At end of `FNyraEditorModule::StartupModule` (after existing tab +
    ToolMenus registration), add:
    ```cpp
        // D-04: Eager spawn NyraHost on editor start.
        GNyraSupervisor = MakeUnique<FNyraSupervisor>();
        const FString PluginDir = IPluginManager::Get().FindPlugin(TEXT("NYRA"))->GetBaseDir();
        const FString ProjectDir = FPaths::ProjectDir();
        const FString LogDir = FPaths::Combine(ProjectDir, TEXT("Saved"), TEXT("NYRA"), TEXT("logs"));
        GNyraSupervisor->SpawnAndConnect(ProjectDir, PluginDir, LogDir);
    ```

    At start of `FNyraEditorModule::ShutdownModule` (before existing
    Unregister calls), add:
    ```cpp
        // D-05: clean shutdown
        if (GNyraSupervisor.IsValid())
        {
            GNyraSupervisor->RequestShutdown();
            GNyraSupervisor.Reset();
        }
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "class NYRAEDITOR_API INyraClock" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraSupervisor.h` equals 1
      - `grep -c "class NYRAEDITOR_API FNyraSystemClock" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraSupervisor.h` equals 1
      - `grep -c "class NYRAEDITOR_API FNyraSupervisor" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraSupervisor.h` equals 1
      - `grep -c "MAX_CRASHES_IN_WINDOW = 3" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraSupervisor.cpp` equals 1
      - `grep -c "CRASH_WINDOW_S = 60.0" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraSupervisor.cpp` equals 1
      - `grep -c "--editor-pid" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraSupervisor.cpp` >= 1
      - `grep -c "--project-dir" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraSupervisor.cpp` >= 1
      - `grep -c "--plugin-binaries-dir" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraSupervisor.cpp` >= 1
      - `grep -c "Cancel(/\*bKillTree=\*/true)" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraSupervisor.cpp` equals 1
      - `grep -c 'WsClient.SendNotification(TEXT("shutdown")' TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraSupervisor.cpp` equals 1
      - `grep -c "GNyraSupervisor->SpawnAndConnect" TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp` equals 1
      - `grep -c "GNyraSupervisor->RequestShutdown" TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp` equals 1
      - `grep -c 'Describe("RestartPolicy"' TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraSupervisorSpec.cpp` equals 1
      - `grep -c "BEGIN_DEFINE_SPEC(FNyraIntegrationSpec" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraIntegrationSpec.cpp` equals 1
      - After build: `UnrealEditor-Cmd.exe TestProject/TestProject.uproject -ExecCmds="Automation RunTests Nyra.Supervisor.RestartPolicy;Quit" -unattended -nopause -testexit="Automation Test Queue Empty"` exits 0
    </automated>
  </verify>
  <acceptance_criteria>
    - FNyraSupervisor.h exports `INyraClock` abstract class with virtual `NowSeconds() const = 0`
    - FNyraSupervisor.h exports `FNyraSystemClock : public INyraClock` returning `FPlatformTime::Seconds()`
    - FNyraSupervisor.h exports `ENyraSupervisorState` with all states: Idle, Spawning, WaitingForHandshake, Connecting, Authenticating, Ready, Crashed, Unstable, ShuttingDown
    - FNyraSupervisor.h exports `struct FNyraInFlightRequest` with `Method`, `Params`, `OriginalId` fields
    - FNyraSupervisor.h exports class `FNyraSupervisor` with constructors `()` (default clock) and `(TSharedRef<INyraClock>)` (injected)
    - FNyraSupervisor.h exports methods `SpawnAndConnect`, `RequestShutdown`, `SendRequest`, `SendNotification`, `SimulateCrashForTest`, `GetState`
    - FNyraSupervisor.h delegates: `OnStateChanged`, `OnReady`, `OnUnstable`, `OnNotification`, `OnResponse`
    - FNyraSupervisor.cpp constants `MAX_CRASHES_IN_WINDOW = 3`, `CRASH_WINDOW_S = 60.0`, `SHUTDOWN_GRACE_S = 2.0`
    - FNyraSupervisor.cpp spawns with CLI args matching Plan 06/08 `__main__.py`: `-m nyrahost --editor-pid <N> --log-dir "<path>" --project-dir "<path>" --plugin-binaries-dir "<path>" --handshake-dir "<path>"`
    - FNyraSupervisor.cpp uses `FMonitoredProcess` with `bHidden=true, bCreatePipes=true`
    - FNyraSupervisor.cpp `RequestShutdown` sends `shutdown` notification, waits SHUTDOWN_GRACE_S seconds, then `Cancel(bKillTree=true)`
    - FNyraSupervisor.cpp `RecordCrashAndMaybeRestart` uses `Clock->NowSeconds()` (NOT FPlatformTime directly — for testability)
    - FNyraSupervisor.cpp `RecordCrashAndMaybeRestart` evicts crash timestamps older than CRASH_WINDOW_S before checking count
    - FNyraSupervisor.cpp in-flight replay: on respawn `OnAuthenticated`, if `InFlight.IsSet()`, re-send via SendRequest with new id
    - NyraEditorModule.cpp `StartupModule` creates `GNyraSupervisor = MakeUnique<FNyraSupervisor>()` and calls `SpawnAndConnect`
    - NyraEditorModule.cpp `ShutdownModule` calls `GNyraSupervisor->RequestShutdown()` and `GNyraSupervisor.Reset()` BEFORE tab unregister
    - NyraSupervisorSpec.cpp `Nyra.Supervisor.RestartPolicy` test with `FNyraTestClock` injected via `FTestClockAdapter` verifies 3-in-60s trips Unstable AND 3-outside-60s does NOT
    - NyraIntegrationSpec.cpp contains guarded `FNyraIntegrationSpec` with `Nyra.Integration.HandshakeAuth` LatentIt using real FNyraSupervisor
    - `UnrealEditor-Cmd.exe TestProject/TestProject.uproject -ExecCmds="Automation RunTests Nyra.Supervisor.RestartPolicy;Quit" -unattended -nopause -testexit="Automation Test Queue Empty"` exits 0 with 2 It blocks passing
  </acceptance_criteria>
  <done>FNyraSupervisor wires process + handshake + WS + restart policy. Editor launch spawns NyraHost and authenticates.</done>
</task>

</tasks>

<verification>
- Build TestProject in Development Editor config.
- Run `UnrealEditor-Cmd.exe TestProject/TestProject.uproject -ExecCmds="Automation RunTests Nyra.Jsonrpc+Nyra.Supervisor+Nyra.Plugin;Quit" -unattended -nopause -testexit="Automation Test Queue Empty"` — exits 0, all unit specs pass.
- Manual: open TestProject in UE 5.6 editor → confirm NyraHost process appears in Task Manager, authenticates within 5s, editor log shows `[NYRA] NyraEditor module starting` and `[NYRA] WS closed code=...` only on editor close.
- Integration test (opt-in with `ENABLE_NYRA_INTEGRATION_TESTS=1` in Target.cs): Nyra.Integration.HandshakeAuth passes.
</verification>

<success_criteria>
- FNyraJsonRpc encode/decode + Nyra.Jsonrpc.* tests green (VALIDATION 1-02-02)
- FNyraHandshake polling with exp backoff + orphan cleanup
- FNyraWsClient auth-first-frame + close-4401 handling
- FNyraSupervisor FMonitoredProcess + 3-in-60s policy + in-flight replay + injected INyraClock
- Nyra.Supervisor.RestartPolicy automation tests green (VALIDATION 1-02-03)
- Nyra.Integration.HandshakeAuth guarded test body filled (VALIDATION 1-02-01, opt-in)
- NyraEditorModule spawns NyraHost on StartupModule, shuts down cleanly on ShutdownModule
</success_criteria>

<output>
After completion, create `.planning/phases/01-plugin-shell-three-process-ipc/01-10-SUMMARY.md`
documenting: CLI args used, restart window constants, INyraClock abstraction,
handshake polling timing table, how Plan 12 (chat) consumes
FNyraSupervisor.OnNotification for chat/stream frames.
</output>
