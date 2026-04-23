// =============================================================================
// NyraSupervisorSpec.cpp  (Phase 1 Plan 10 -- upgraded from Plan 01 Wave 0 stub)
// =============================================================================
//
// Nyra.Supervisor.RestartPolicy (VALIDATION row 1-02-03) drives the 3-in-60s
// supervisor crash-rate policy via FNyraTestClock (NyraTestFixtures.h) wrapped
// in FTestClockAdapter (below) so tests advance simulated time without
// waiting on wall-clock.
//
// Two It() blocks:
//   1. 3 crashes at t=0,20,40 (within the 60s window) -> Unstable fires.
//   2. 3 crashes at t=0,70,140 (each outside the 60s window) -> NOT unstable.
// =============================================================================

#include "Misc/AutomationTest.h"
#include "NyraTestFixtures.h"
#include "Process/FNyraSupervisor.h"

#if WITH_AUTOMATION_TESTS

/** Adapter: wraps Nyra::Tests::FNyraTestClock as an INyraClock. */
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
            Sup.OnUnstable.BindLambda([&]() { bUnstableFired = true; });

            // Crash 1 at t=0, Crash 2 at t=20, Crash 3 at t=40 -- all within 60s window.
            Clock.Set(0.0);
            Sup.SimulateCrashForTest();
            Clock.Set(20.0);
            Sup.SimulateCrashForTest();
            Clock.Set(40.0);
            Sup.SimulateCrashForTest();

            TestTrue(TEXT("Unstable fired after 3 crashes in 60s"), bUnstableFired);
            TestEqual(TEXT("State is Unstable"),
                      (int32)Sup.GetState(), (int32)ENyraSupervisorState::Unstable);
        });

        It("does NOT trip Unstable if crashes spread outside the 60s window", [this]()
        {
            Nyra::Tests::FNyraTestClock Clock;
            TSharedRef<INyraClock> Adapter = MakeShared<FTestClockAdapter>(Clock);
            FNyraSupervisor Sup(Adapter);
            bool bUnstableFired = false;
            Sup.OnUnstable.BindLambda([&]() { bUnstableFired = true; });

            Clock.Set(0.0);   Sup.SimulateCrashForTest();   // entry [0]
            Clock.Set(70.0);  Sup.SimulateCrashForTest();   // evicts t=0 -> count=1
            Clock.Set(140.0); Sup.SimulateCrashForTest();   // evicts t=70 -> count=1

            TestFalse(TEXT("Unstable NOT fired (crashes outside window)"), bUnstableFired);
        });
    });
}

#endif // WITH_AUTOMATION_TESTS
