---
phase: 02-subscription-bridge-ci-matrix
plan: 12
slug: status-pill-ui
type: execute
wave: 3
depends_on: [02, 06]
autonomous: true
tdd: false
requirements: [CHAT-02]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraBackendStatusStrip.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraBackendStatusStrip.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraStatusPillSpec.cpp
research_refs: [§9.1, §9.2, §9.3, §9.4, §9.5]
context_refs: [D-03, D-05, D-23, D-24]
phase0_clearance_required: false
must_haves:
  truths:
    - "SNyraBackendStatusStrip Slate widget renders 3 pills horizontally: Claude | Gemma | Privacy"
    - "Pill colours map router states (RESEARCH §9.3): Green=ready, Yellow=rate-limited, Red=auth-drift, Purple=privacy-mode active, Grey=not-installed/not-configured, Blue spinner=streaming"
    - "SetState(FNyraBackendState) updates pill appearance + tooltip text (hover shows verbose state e.g. 'Claude Max connected. Rate limit resets at 3:00 PM PT.')"
    - "Click opens a small popover: [Sign in] / [Sign out] / [Test connection] / [Switch to Gemma] buttons context-sensitive to current state"
    - "Mounted in SNyraChatPanel in a new strip row BETWEEN existing banner (Plan 13) and message list (Plan 12) — vertical layout preserved; module-superset on SNyraChatPanel"
    - "Panel subscribes to diagnostics/backend-state notifications (from Plan 02-06 router); HandleNotification dispatches shape-validated params to the strip's SetState"
    - "First-run wizard integration: if Claude pill is grey, banner surfaces 'Sign into Claude' button linking to a terminal invocation of `claude auth login` (RESEARCH §9.4); after 5-min TTL refresh OR [Test connection] click, pill transitions green"
    - "NyraStatusPillSpec.cpp: Nyra.Panel.StatusPill.Ready (green + 'Claude Pro connected' tooltip), Nyra.Panel.StatusPill.RateLimited (yellow + remaining-time tooltip), Nyra.Panel.StatusPill.AuthDrift (red + 'claude auth login' instruction), Nyra.Panel.StatusPill.PrivacyMode (purple + all three pills show privacy overlay), Nyra.Panel.StatusPill.SwitchToGemmaButton (click → emits session/set-mode? no — emits user_approved_fallback on next chat/send; test covers the state wiring)"
  artifacts:
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraBackendStatusStrip.h
      provides: "Three-pill status strip Slate widget"
      exports: ["SNyraBackendStatusStrip", "FNyraBackendState (mirrors diagnostics/backend-state params)"]
  key_links:
    - from: SNyraChatPanel HandleNotification(diagnostics/backend-state)
      to: SNyraBackendStatusStrip.SetState
      via: "JSON parse → FNyraBackendState POD"
      pattern: "diagnostics/backend-state.*SetState"
    - from: SNyraBackendStatusStrip click → [Switch to Gemma]
      to: Router user_approved_fallback flag (Plan 02-06)
      via: "Panel sets bUserApprovedFallback=true for next chat/send; on next turn the router reads and transitions"
      pattern: "bUserApprovedFallback"
---

<objective>
Surface the router state to the user via a three-pill status strip in the chat panel (CHAT-02). This is the **visible manifestation of the economic wedge** — users see "Claude Pro connected" right in the editor, making the "no new AI bill" promise concrete.

Per CONTEXT.md:
- D-03: state enum maps 1:1 to pill color
- D-05: Privacy Mode has distinctive purple overlay across all three pills
- D-23: diagnostics/backend-state notification already documented
- D-24: module-superset on SNyraChatPanel

Per RESEARCH §9 layout (between banner and message list).

**NOT TDD** — this is Slate widget rendering + click-callback wiring; visual verification dominates. Uses UE Automation Spec to structure-test the widget tree.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/02-subscription-bridge-ci-matrix/02-CONTEXT.md
@.planning/phases/02-subscription-bridge-ci-matrix/02-RESEARCH.md
@docs/JSONRPC.md

<interfaces>
<!-- diagnostics/backend-state params (docs/JSONRPC.md §4.8): -->
```json
{
  "claude": {
    "installed": true,
    "version": "2.1.118",
    "auth": "pro",
    "state": "ready",
    "rate_limit_resets_at": null
  },
  "gemma": {
    "model_present": true,
    "runtime": "ollama",
    "state": "ready"
  },
  "computer_use": {"state": "not-configured"},
  "mode": "normal",
  "updated_at": "2026-04-22T14:00:00Z"
}
```

<!-- FNyraBackendState C++ POD mirror: -->
```cpp
struct FNyraClaudeState { bool bInstalled; FString Version; FString Auth; FString State; TOptional<FDateTime> RateLimitResetsAt; };
struct FNyraGemmaState { bool bModelPresent; FString Runtime; FString State; };
struct FNyraComputerUseState { FString State; };
enum class ENyraPrivacyMode : uint8 { Normal, PrivacyMode };
struct FNyraBackendState {
    FNyraClaudeState Claude;
    FNyraGemmaState Gemma;
    FNyraComputerUseState ComputerUse;
    ENyraPrivacyMode Mode;
    FDateTime UpdatedAt;
    static FNyraBackendState ParseJson(const FString& Json);
};
```

<!-- Pill colour mapping (RESEARCH §9.3): -->
<!--   Claude.state=ready → Green            "Claude {Pro|Max|Teams|Enterprise} connected" -->
<!--   Claude.state=rate-limited → Yellow    "Rate-limited. Resume in <relative-time>" -->
<!--   Claude.state=auth-drift → Red         "Signed out — run `claude auth login`" -->
<!--   Claude.state=offline → Grey           "Offline" -->
<!--   Claude.installed=false → Grey         "Claude CLI not installed" -->
<!--   Gemma.state=ready → Green             "Gemma {ollama|llama-server} ready" -->
<!--   Gemma.state=downloading → Blue spinner"Downloading Gemma…" -->
<!--   Gemma.state=loading → Blue spinner    "Loading Gemma (~8s)…" -->
<!--   Gemma.state=not-installed → Grey      "Click to download (3.16 GB)" → opens diagnostics/download-gemma -->
<!--   Mode=privacy-mode → purple border around ALL pills overlay + Privacy pill goes solid purple -->

<!-- SNyraChatPanel layout after this plan (module-superset on Plan 13 layout): -->
<!--   SVerticalBox { -->
<!--     Plan 13 SNyraBanner                  — preserved -->
<!--     NEW SNyraBackendStatusStrip          — Plan 02-12 mounts here -->
<!--     SOverlay(MessageList + DownloadModal + NEW SNyraPreviewCard from Plan 02-09)  — Plan 02-09 + 13 -->
<!--     Plan 12 SNyraComposer                — preserved -->
<!--     Plan 13 SNyraDiagnosticsDrawer       — preserved -->
<!--   } -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: SNyraBackendStatusStrip widget + FNyraBackendState POD + JSON parser</name>
  <files>TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraBackendStatusStrip.h, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraBackendStatusStrip.cpp, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraStatusPillSpec.cpp</files>
  <action>
    Create SNyraBackendStatusStrip per interfaces composition. Key specifics:
    - SConstructor Slate macros mirror Phase 1 Plan 12's SNyraComposer style
    - Three child SButton widgets each owning an SBorder with ColorAndOpacity lambda reading the current FNyraClaudeState/FNyraGemmaState/ENyraPrivacyMode
    - Inner STextBlock labels: "Claude" "Gemma" "Privacy"
    - Tooltip_Lambda returns per-state verbose text using FText::Format
    - SetState(FNyraBackendState) assigns + triggers Invalidate() + reads next tick
    - OnClicked on each pill raises a delegate; panel binds to pop up SMenuAnchor with 2-4 buttons (Sign in / Sign out / Test connection / Switch to Gemma) depending on state
    - ParseJson uses FJsonSerializer::Deserialize on the FJsonObject (Phase 1's FNyraJsonRpc already provides helpers; reuse)

    Pill rendering color constants (reused palette — add to NyraEditor namespace if not present):
    - FLinearColor Green(0.2f, 0.7f, 0.3f)
    - FLinearColor Yellow(0.85f, 0.7f, 0.15f)
    - FLinearColor Red(0.8f, 0.15f, 0.15f)
    - FLinearColor Grey(0.45f, 0.45f, 0.45f)
    - FLinearColor Purple(0.55f, 0.25f, 0.75f)
    - FLinearColor Blue(0.2f, 0.5f, 0.85f)  (for blue spinner)

    Privacy-mode overlay: when Mode == PrivacyMode, wrap the HBox in an SBorder whose BorderImage Colour_Lambda returns Purple with alpha 0.5; Privacy pill itself renders solid Purple.

    NyraStatusPillSpec.cpp:
    - Nyra.Panel.StatusPill.Ready — build strip with FNyraBackendState {Claude.state="ready", Gemma.state="ready", Mode=Normal}; assert Claude pill color-lambda resolves to Green; tooltip text contains 'connected'
    - Nyra.Panel.StatusPill.RateLimited — state="rate-limited" with rate_limit_resets_at=30-min-from-now; Yellow pill + tooltip contains 'Rate-limited' + relative time format
    - Nyra.Panel.StatusPill.AuthDrift — state="auth-drift"; Red pill + tooltip contains 'claude auth login'
    - Nyra.Panel.StatusPill.PrivacyMode — Mode=PrivacyMode; all three pills have purple overlay; Privacy pill solid purple
    - Nyra.Panel.StatusPill.ParseJson — given the exact params shape from docs/JSONRPC.md §4.8, ParseJson produces a valid FNyraBackendState with all fields populated

    Commit: feat(02-12): add SNyraBackendStatusStrip widget + state-to-color mapping + spec
  </action>
  <verify>
    <automated>test -f TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraBackendStatusStrip.h && grep -q "FNyraBackendState" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraBackendStatusStrip.h && grep -q "Nyra.Panel.StatusPill" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraStatusPillSpec.cpp</automated>
  </verify>
  <done>
    - SNyraBackendStatusStrip renders 3 pills with color + tooltip + click-popover
    - FNyraBackendState JSON parser round-trips a §4.8-shaped payload
    - Five NyraStatusPillSpec It blocks cover happy-path + each pill state
  </done>
</task>

<task type="auto">
  <name>Task 2: Mount strip in SNyraChatPanel + subscribe to diagnostics/backend-state + wire click actions</name>
  <files>TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp</files>
  <action>
    **Module-superset discipline (D-24):** every Phase 1 (Plans 12/12b/13) + Plan 02-09 line preserved verbatim.

    Inject a new SVerticalBox slot between the banner and the message list:
    ```cpp
    // existing Plan 13 banner slot...
    + SVerticalBox::Slot().AutoHeight().Padding(4, 2)[
        SAssignNew(StatusStrip, SNyraBackendStatusStrip)
            .OnClaudeClick_Lambda([this]() { OpenClaudePopover(); })
            .OnGemmaClick_Lambda([this]() { OpenGemmaPopover(); })
            .OnPrivacyClick_Lambda([this]() { OpenPrivacyPopover(); })
    ]
    // existing Plan 02-09 + 13 SOverlay(MessageList + DownloadModal + PreviewCard) slot follows...
    ```

    HandleNotification branch — in the existing dispatch block (Plan 13 established the pattern):
    ```cpp
    if (Method == TEXT("diagnostics/backend-state"))
    {
        FNyraBackendState NewState = FNyraBackendState::ParseJson(ParamsJson);
        StatusStrip->SetState(NewState);
        CurrentBackendState = NewState;  // cached for popover rendering
        return;
    }
    ```
    Dispatch happens AFTER Plan 13's diagnostics/download-progress branch but BEFORE Plan 12's chat/stream branch.

    Popover handlers (OpenClaudePopover etc.):
    - Build a small SMenuAnchor attached to the clicked pill
    - Inside: SVerticalBox with 2-4 SButtons contextual to CurrentBackendState:
      - Claude auth-drift → [Sign in] button (shows modal with instructions to run `claude auth login` in terminal + [Test connection] button that triggers ClaudeBackend.health_check via new diagnostics/refresh WS notification — OR simpler v1: just the instructions modal)
      - Claude ready → [Sign out] + [Test connection]
      - Claude rate-limited → [Switch to Gemma] button that sets a `bUserApprovedFallback` panel-level flag consumed by next OnComposerSubmit call
      - Gemma not-installed → [Download Gemma] button emitting existing Phase 1 diagnostics/download-gemma request
      - Privacy pill (always visible) → [Enable Privacy Mode] / [Exit Privacy Mode] toggles emitting session/set-mode

    First-run wizard integration: in existing Plan 13 OnStateChanged lambda, if supervisor Ready AND CurrentBackendState.Claude.state == "offline" AND NOT dismissed, show a one-time banner via Plan 13's SNyraBanner: "Connect your Claude subscription" + [Sign in] button → clicks Claude pill popover's sign-in flow.

    Commit: feat(02-12): mount SNyraBackendStatusStrip in SNyraChatPanel + diagnostics/backend-state subscription + click popovers
  </action>
  <verify>
    <automated>grep -q "SNyraBackendStatusStrip" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp && grep -q "diagnostics/backend-state" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp && grep -q "bUserApprovedFallback" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp</automated>
  </verify>
  <done>
    - Status strip mounted between banner and message list; other Plan 12/12b/13/02-09 widgets unchanged
    - diagnostics/backend-state notification updates strip in real time
    - Pill clicks open SMenuAnchor popovers with context-sensitive buttons
    - [Switch to Gemma] sets bUserApprovedFallback consumed by next chat/send (Plan 02-06 router accepts it)
    - session/set-mode toggle wired via Privacy pill click
    - First-run Claude sign-in banner surfaces when backend state indicates offline
    - Phase 1 + Plan 02-09 tests still green; module-superset preserved
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User click → router state mutation | User clicks translate to state changes (PrivacyMode toggle, fallback approval); must be audit-logged |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-12-01 | Spoofing | UI makes fallback approval look accidental / easy-to-miss | mitigate | [Switch to Gemma] is a single explicit click; UX distinguishes from auto-fallback per D-04. Tooltip shows "Switches this conversation to local Gemma. Claude re-available when rate-limit resets." |
| T-02-12-02 | Tampering | diagnostics/backend-state notification can be crafted by compromised NyraHost | accept | First-frame auth (Phase 1 D-07) gates WS; if NyraHost is compromised, the plugin has bigger problems. Privacy Mode is the user's own toggle, not inferred from state. |
</threat_model>

<verification>
- `grep -q "SNyraBackendStatusStrip" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp`
- Automation: `Automation RunTests Nyra.Panel.StatusPill` — 5 It blocks pass
- Automation: `Automation RunTests Nyra.Panel` (Phase 1 panel tests) still green
</verification>

<success_criteria>
- Three pills visible in chat panel with correct color + tooltip for every router state
- diagnostics/backend-state notification drives real-time updates
- Click popovers surface the two or three next-best actions per state
- Privacy Mode overlay clearly signals egress-blocked state
- First-run wizard leverages the pill state for Claude sign-in prompt
- CHAT-02 success criterion (status UI) landed with beat-every-competitor polish
</success_criteria>

<output>
After completion, create `.planning/phases/02-subscription-bridge-ci-matrix/02-12-SUMMARY.md`
</output>
