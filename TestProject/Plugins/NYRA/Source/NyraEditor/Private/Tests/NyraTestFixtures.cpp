// =============================================================================
// NyraTestFixtures.cpp  (Phase 1 Plan 01 — Wave 0 test scaffold)
// =============================================================================
//
// Implementation of the Nyra::Tests helpers declared in NyraTestFixtures.h.
// All symbols here live inside `#if WITH_AUTOMATION_TESTS` so shipping
// builds do not emit any of this code.
//
// Dependencies: UE Core only — no Nyra production headers included.
// =============================================================================

#include "NyraTestFixtures.h"

#if WITH_AUTOMATION_TESTS

#include "HAL/PlatformFileManager.h"
#include "GenericPlatform/GenericPlatformFile.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Guid.h"
#include "Misc/DateTime.h"

namespace Nyra::Tests
{
    // -------------------------------------------------------------------------
    // FNyraTempDir
    // -------------------------------------------------------------------------

    FNyraTempDir::FNyraTempDir()
    {
        // Root: Intermediate/NyraTests/<guid>
        // Intermediate/ is always writable during editor sessions and is
        // excluded from source control, making it the safest scratch area.
        const FString Root = FPaths::ProjectIntermediateDir() / TEXT("NyraTests");
        const FString Guid = FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphens);
        DirPath = Root / Guid;

        IPlatformFile& PlatformFile = FPlatformFileManager::Get().GetPlatformFile();

        // CreateDirectoryTree is recursive and idempotent.
        if (!PlatformFile.DirectoryExists(*DirPath))
        {
            PlatformFile.CreateDirectoryTree(*DirPath);
        }
    }

    FNyraTempDir::~FNyraTempDir()
    {
        if (DirPath.IsEmpty())
        {
            return;
        }

        IPlatformFile& PlatformFile = FPlatformFileManager::Get().GetPlatformFile();
        if (PlatformFile.DirectoryExists(*DirPath))
        {
            // DeleteDirectoryRecursively removes contents + the dir itself.
            PlatformFile.DeleteDirectoryRecursively(*DirPath);
        }
    }

    // -------------------------------------------------------------------------
    // WriteHandshakeFile — D-06 schema
    // -------------------------------------------------------------------------

    FString WriteHandshakeFile(
        const FString& Dir,
        int32 EditorPid,
        int32 NyraHostPid,
        int32 Port,
        const FString& Token)
    {
        IPlatformFile& PlatformFile = FPlatformFileManager::Get().GetPlatformFile();

        if (!PlatformFile.DirectoryExists(*Dir))
        {
            // Caller contract: Dir must exist. Fail closed.
            return FString();
        }

        // File name mirrors production NyraHost: handshake-<editor-pid>.json
        const FString FileName = FString::Printf(TEXT("handshake-%d.json"), EditorPid);
        const FString FullPath = Dir / FileName;

        // started_at = Unix epoch millis (matches D-06).
        const int64 StartedAtMillis = FDateTime::UtcNow().ToUnixTimestamp() * 1000LL;

        const FString Body = FString::Printf(
            TEXT("{\"port\":%d,\"token\":\"%s\",\"nyrahost_pid\":%d,\"ue_pid\":%d,\"started_at\":%lld}"),
            Port,
            *Token,
            NyraHostPid,
            EditorPid,
            StartedAtMillis);

        const bool bWrote = FFileHelper::SaveStringToFile(
            Body,
            *FullPath,
            FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);

        if (!bWrote)
        {
            return FString();
        }

        return FullPath;
    }

    // -------------------------------------------------------------------------
    // MakeJsonRpcRequest — D-09 envelope
    // -------------------------------------------------------------------------

    FString MakeJsonRpcRequest(int64 Id, const FString& Method, const FString& ParamsJson)
    {
        // Deliberately no escaping — ParamsJson is pre-formed JSON per the
        // header contract. Production framer in Plan 10 uses FJsonObject +
        // TJsonWriter; this fixture stays deterministic and byte-exact so
        // Nyra.Jsonrpc.EnvelopeRoundtrip can compare against a golden string.
        return FString::Printf(
            TEXT("{\"jsonrpc\":\"2.0\",\"id\":%lld,\"method\":\"%s\",\"params\":%s}"),
            Id,
            *Method,
            *ParamsJson);
    }

} // namespace Nyra::Tests

#endif // WITH_AUTOMATION_TESTS
