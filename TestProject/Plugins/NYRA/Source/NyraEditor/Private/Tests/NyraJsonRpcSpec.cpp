// =============================================================================
// NyraJsonRpcSpec.cpp  (Phase 1 Plan 01 — Wave 0 test scaffold)
// =============================================================================
//
// JSON-RPC 2.0 unit test shell. Test path: Nyra.Jsonrpc.*
//
// Populated by Plan 10 (FNyraJsonRpc envelope implementation). VALIDATION
// row 1-02-02 references the `Nyra.Jsonrpc.EnvelopeRoundtrip` test ID which
// will live in this file.
//
// The helpers MakeJsonRpcRequest() from Nyra::Tests (NyraTestFixtures.h) are
// intended to be called from the Define() body once Plan 10 adds the
// production FNyraJsonRpc code.
// =============================================================================

#include "Misc/AutomationTest.h"
#include "NyraTestFixtures.h"

#if WITH_AUTOMATION_TESTS

BEGIN_DEFINE_SPEC(FNyraJsonRpcSpec,
                   "Nyra.Jsonrpc",
                   EAutomationTestFlags::EditorContext |
                   EAutomationTestFlags::EngineFilter)
END_DEFINE_SPEC(FNyraJsonRpcSpec)

void FNyraJsonRpcSpec::Define()
{
    // Plan 10 (FNyraJsonRpc) fills this with:
    //   Describe("EnvelopeRoundtrip", [this]() {
    //       It("encodes request correctly", [this]() { ... });
    //       It("decodes response correctly", [this]() { ... });
    //       It("surfaces error.data.remediation", [this]() { ... });
    //   });
    // Test ID: Nyra.Jsonrpc.EnvelopeRoundtrip (VALIDATION row 1-02-02)
    //
    // Fixtures available: Nyra::Tests::MakeJsonRpcRequest(Id, Method, Params).
}

#endif // WITH_AUTOMATION_TESTS
