// =============================================================================
// NyraSupervisorSpec.cpp  (Phase 1 Plan 01 — Wave 0 test scaffold)
// =============================================================================
//
// Supervisor policy test shell. Test path: Nyra.Supervisor.*
//
// Populated by Plan 10 (FNyraSupervisor — 3-restarts-in-60s policy, D-08).
// VALIDATION row 1-02-03 references the Nyra.Supervisor.RestartPolicy test ID
// which injects the Nyra::Tests::FNyraTestClock clock from
// NyraTestFixtures.h to deterministically exercise the crash-rate window
// without waiting 60 seconds of wall-clock time.
// =============================================================================

#include "Misc/AutomationTest.h"
#include "NyraTestFixtures.h"

#if WITH_AUTOMATION_TESTS

BEGIN_DEFINE_SPEC(FNyraSupervisorSpec,
                   "Nyra.Supervisor",
                   EAutomationTestFlags::EditorContext |
                   EAutomationTestFlags::EngineFilter)
END_DEFINE_SPEC(FNyraSupervisorSpec)

void FNyraSupervisorSpec::Define()
{
    // Plan 10 (FNyraSupervisor) fills this with:
    //   Describe("RestartPolicy", [this]() {
    //       It("auto-restarts on crash 1 (clock=0s)", [this]() { ... });
    //       It("auto-restarts on crash 2 (clock=20s)", [this]() { ... });
    //       It("auto-restarts on crash 3 (clock=40s)", [this]() { ... });
    //       It("banners on crash 4 (clock=55s)", [this]() { ... });
    //       It("clears window after 60s idle", [this]() { ... });
    //   });
    // Test ID: Nyra.Supervisor.RestartPolicy (VALIDATION row 1-02-03)
    //
    // Fixture: Nyra::Tests::FNyraTestClock injected into FNyraSupervisor ctor
    // via a `TFunction<double()>` clock parameter so the test drives
    // deterministic crash-rate-window transitions.
}

#endif // WITH_AUTOMATION_TESTS
