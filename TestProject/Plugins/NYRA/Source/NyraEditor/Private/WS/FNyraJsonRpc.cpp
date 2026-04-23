// =============================================================================
// FNyraJsonRpc.cpp  (Phase 1 Plan 10)
// =============================================================================

#include "WS/FNyraJsonRpc.h"
#include "NyraLog.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include "Dom/JsonValue.h"

namespace
{
    /** Serialize a FJsonObject to compact (no-whitespace) JSON text. */
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
        return Env;  // Invalid -- missing or wrong protocol version
    }

    // Id is optional (Notifications omit it). When present, must be numeric.
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

    // Request or Notification (method present)
    FString Method;
    if (Root->TryGetStringField(TEXT("method"), Method))
    {
        Env.Method = Method;
        const TSharedPtr<FJsonObject>* ParamsObj = nullptr;
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

    // Response (result present)
    const TSharedPtr<FJsonObject>* ResultObj = nullptr;
    if (Root->TryGetObjectField(TEXT("result"), ResultObj) && ResultObj && ResultObj->IsValid())
    {
        Env.Result = *ResultObj;
        Env.Kind = ENyraEnvelopeKind::Response;
        return Env;
    }

    // Error (error object present)
    const TSharedPtr<FJsonObject>* ErrObj = nullptr;
    if (Root->TryGetObjectField(TEXT("error"), ErrObj) && ErrObj && ErrObj->IsValid())
    {
        double Code = 0.0;
        (*ErrObj)->TryGetNumberField(TEXT("code"), Code);
        Env.ErrorCode = static_cast<int32>(Code);
        (*ErrObj)->TryGetStringField(TEXT("message"), Env.ErrorMessage);

        const TSharedPtr<FJsonObject>* DataObj = nullptr;
        if ((*ErrObj)->TryGetObjectField(TEXT("data"), DataObj) && DataObj && DataObj->IsValid())
        {
            (*DataObj)->TryGetStringField(TEXT("remediation"), Env.ErrorRemediation);
        }
        Env.Kind = ENyraEnvelopeKind::Error;
        return Env;
    }

    // Fallthrough: had jsonrpc:"2.0" but no method/result/error
    return Env;  // Invalid
}
