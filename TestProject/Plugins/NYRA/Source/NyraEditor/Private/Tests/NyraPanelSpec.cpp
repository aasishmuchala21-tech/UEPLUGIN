// =============================================================================
// NyraPanelSpec.cpp  (Phase 1 Plan 04 — Wave 1 nomad tab scaffold)
// =============================================================================
//
// Slate chat-panel widget test shell. Test path: Nyra.Panel.*
//
// Populated across Plans 04 (tab spawner — THIS PLAN) and 12 (attachment
// chip + streaming buffer). VALIDATION rows reference:
//   - Nyra.Panel.TabSpawner       (1-04-01)  — Plan 04  (GREEN below)
//   - Nyra.Panel.AttachmentChip   (1-04-04)  — Plan 12  (placeholder)
//   - Nyra.Panel.StreamingBuffer  (1-04-05)  — Plan 12  (placeholder)
// =============================================================================

#include "Misc/AutomationTest.h"
#include "NyraTestFixtures.h"
#include "NyraChatTabNames.h"
#include "Framework/Docking/TabManager.h"
#include "Widgets/Docking/SDockTab.h"

#if WITH_AUTOMATION_TESTS

BEGIN_DEFINE_SPEC(FNyraPanelSpec,
                   "Nyra.Panel",
                   EAutomationTestFlags::EditorContext |
                   EAutomationTestFlags::EngineFilter)
END_DEFINE_SPEC(FNyraPanelSpec)

void FNyraPanelSpec::Define()
{
    // VALIDATION row 1-04-01 — Nyra.Panel.TabSpawner
    // Verifies FNyraEditorModule::StartupModule has registered a nomad tab
    // spawner under FName("NyraChatTab") and that invoking it returns a
    // valid SDockTab with ETabRole::NomadTab.
    Describe("TabSpawner", [this]()
    {
        It("registers NyraChatTab so TryInvokeTab returns a valid SDockTab", [this]()
        {
            TSharedPtr<SDockTab> Tab = FGlobalTabManager::Get()->TryInvokeTab(Nyra::NyraChatTabId);
            TestTrue(TEXT("TryInvokeTab returns valid ptr"), Tab.IsValid());
            if (Tab.IsValid())
            {
                TestEqual(TEXT("Tab role is NomadTab"), Tab->GetTabRole(), ETabRole::NomadTab);
                Tab->RequestCloseTab();
            }
        });
    });

    // Plan 12 (Chat panel) fills:
    //   Describe("AttachmentChip", [this]() {
    //       It("renders filename + size + MIME glyph", ...);
    //       It("dismisses on X-click", ...);
    //   });
    //   Describe("StreamingBuffer", [this]() {
    //       It("coalesces delta frames into an STextBlock during streaming", ...);
    //       It("swaps to SRichTextBlock on done:true", ...);
    //   });
    // Test IDs: Nyra.Panel.AttachmentChip (1-04-04),
    //           Nyra.Panel.StreamingBuffer (1-04-05)
}

#endif // WITH_AUTOMATION_TESTS
