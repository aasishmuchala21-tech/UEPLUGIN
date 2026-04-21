#pragma once

// =============================================================================
// NyraTestFixtures.h  (Phase 1 Plan 01 — Wave 0 test scaffold)
// =============================================================================
//
// Shared automation-test fixtures for the Nyra.* UE Automation Spec suite.
//
// This file is a PURE SUPERSET of the minimal Rule-3 stub authored by
// Plan 03 Task 5 (commit 2dc2d32). The stub only contained:
//     #pragma once
//     #include "CoreMinimal.h"
// and was placed to keep Plan 03's NyraIntegrationSpec.cpp compiling before
// Plan 01 (this file) landed. Plan 01 replaces the stub with the full
// Nyra::Tests fixture namespace declared below. No Plan 03 symbol is removed;
// the stub's single include is preserved.
//
// Scope — Phase 1 Wave 0 only:
//   * RAII temp-dir helper for file-system-touching tests (D-06 handshake,
//     CD-07 SQLite, CD-08 attachments).
//   * Injectable monotonic clock for supervisor restart-policy tests
//     (D-08: "3 restarts in 60 seconds"). Kept header-only because it has
//     no external deps.
//   * Handshake-file writer matching the exact D-06 schema (UE side polls
//     this file, NyraHost side writes it; the test-harness side is this
//     helper so both transports can be exercised in isolation).
//   * JSON-RPC 2.0 request-envelope builder for Nyra.Jsonrpc.EnvelopeRoundtrip
//     tests (D-09 envelope shape).
//
// Zero dependencies on not-yet-existing Nyra production headers. Everything
// here resolves against UE Core: CoreMinimal + HAL/PlatformFileManager +
// Misc/Paths + Misc/Guid + Misc/FileHelper + Misc/DateTime.
//
// Guard: the full body is inside `#if WITH_AUTOMATION_TESTS` so shipping
// builds never see it. The unguarded portion is only `#pragma once` plus
// the CoreMinimal include that the Plan 03 stub already exposed.
// =============================================================================

#include "CoreMinimal.h"
#include "HAL/PlatformFileManager.h"
#include "Misc/Paths.h"
#include "Misc/Guid.h"

#if WITH_AUTOMATION_TESTS

namespace Nyra::Tests
{
    /**
     * RAII temp directory under
     *   FPaths::ProjectIntermediateDir() / "NyraTests" / <guid>/
     *
     * On construction: creates the directory tree.
     * On destruction: recursively deletes the directory tree.
     *
     * Safe to use across spec It() blocks — a fresh instance yields a fresh
     * guid-scoped directory. Never touches the user's home dir or the plugin
     * Binaries tree.
     */
    class FNyraTempDir
    {
    public:
        FNyraTempDir();
        ~FNyraTempDir();

        /** Absolute path to the temp directory (no trailing slash). */
        const FString& Path() const { return DirPath; }

        /** Absolute path to a file inside the temp directory. */
        FString File(const FString& Name) const { return DirPath / Name; }

    private:
        FString DirPath;

        // Non-copyable; non-movable. RAII ownership must be unique.
        FNyraTempDir(const FNyraTempDir&) = delete;
        FNyraTempDir& operator=(const FNyraTempDir&) = delete;
    };

    /**
     * Injectable monotonic clock for supervisor 3-in-60s tests (D-08).
     *
     * The supervisor under test (Plan 10) accepts a function object
     * returning `double` seconds; in production it is wired to
     * `FPlatformTime::Seconds()`, in tests we wire it to
     * `FNyraTestClock::Now()` and advance the clock deterministically.
     *
     * Header-only: implementation is trivial, no .cpp needed.
     */
    class FNyraTestClock
    {
    public:
        FNyraTestClock() : NowSeconds(0.0) {}

        /** Advance the clock by the given delta. */
        void Advance(double Seconds) { NowSeconds += Seconds; }

        /** Jump the clock to an absolute value (for replay scenarios). */
        void Set(double Seconds) { NowSeconds = Seconds; }

        /** Current simulated time, in seconds since the fixture was created. */
        double Now() const { return NowSeconds; }

    private:
        double NowSeconds;
    };

    /**
     * Write a valid handshake JSON file matching the D-06 schema:
     *   { "port": <port>,
     *     "token": "<token>",
     *     "nyrahost_pid": <nyrahost_pid>,
     *     "ue_pid": <editor_pid>,
     *     "started_at": <unix_millis> }
     *
     * `Dir` must already exist (typical caller: `FNyraTempDir::Path()`).
     * Returns the absolute path of the written file; on IO failure returns
     * an empty string and the caller's automation test will fail via
     * `TestFalse("empty path", Path.IsEmpty())`.
     *
     * `started_at` is populated from `FDateTime::UtcNow()` so the envelope is
     * realistic; tests that need a pinned value can truncate/replace the
     * file after the call.
     */
    FString WriteHandshakeFile(
        const FString& Dir,
        int32 EditorPid,
        int32 NyraHostPid,
        int32 Port,
        const FString& Token);

    /**
     * Build a sample JSON-RPC 2.0 request envelope (D-09):
     *   {"jsonrpc":"2.0","id":<Id>,"method":"<Method>","params":<ParamsJson>}
     *
     * `ParamsJson` must already be a valid JSON value serialised as a string
     * (e.g., `TEXT("{\"token\":\"abc\"}")`). This helper does NO escaping;
     * callers are expected to pass pre-formed JSON. That keeps the fixture
     * deterministic and mirrors how production-code JSON-RPC framers in
     * Plan 10 will build the envelope.
     */
    FString MakeJsonRpcRequest(int64 Id, const FString& Method, const FString& ParamsJson);

} // namespace Nyra::Tests

#endif // WITH_AUTOMATION_TESTS
