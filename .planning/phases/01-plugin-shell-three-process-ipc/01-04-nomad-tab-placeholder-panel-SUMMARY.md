---
phase: 01-plugin-shell-three-process-ipc
plan: 04
subsystem: ui
tags: [ue5, unreal-plugin, cpp, slate, tab-spawner, tool-menus, wave-1, automation-spec]

requires:
  - phase: 01-plugin-shell-three-process-ipc
    plan: 03
    provides: FNyraEditorModule + NyraEditor.Build.cs (ToolMenus/WorkspaceMenuStructure/Slate deps) + empty StartupModule/ShutdownModule skeleton (commits 2dd106c · 978075d)
  - phase: 01-plugin-shell-three-process-ipc
    plan: 01
    provides: NyraPanelSpec.cpp placeholder Define() with inline Plan 04 + Plan 12 pointers (commit ca182ba)
provides:
  - Nyra::NyraChatTabId canonical FName ("NyraChatTab") + Nyra::NyraToolsMenuExtensionPoint ("LevelEditor.MainMenu.Tools") + Nyra::NyraMenuSectionName ("NYRA")
  - SNyraChatPanel SCompoundWidget (NYRAEDITOR_API) — Phase 1 placeholder rendering "NYRA — not yet connected"
  - FNyraEditorModule::StartupModule wired to FGlobalTabManager::RegisterNomadTabSpawner + UToolMenus Tools->NYRA->Chat extension
  - FNyraEditorModule::ShutdownModule clean-teardown of tab spawner + UToolMenus owner
  - Nyra.Panel.TabSpawner automation It block (VALIDATION row 1-04-01, CHAT-01)
affects: [01-12-chat-panel-streaming-integration, 01-12b-history-drawer, 01-13-first-run-ux-banners-diagnostics]

tech-stack:
  added:
    - FGlobalTabManager + RegisterNomadTabSpawner nomad-tab lifecycle pattern
    - WorkspaceMenu::GetMenuStructure().GetToolsCategory() workspace category wiring
    - UToolMenus::RegisterStartupCallback + ExtendMenu("LevelEditor.MainMenu.Tools") + FToolMenuSection::AddMenuEntry pattern for Tools -> NYRA -> Chat
    - FUIAction lambda wiring TryInvokeTab to a menu entry
    - SCompoundWidget + SLATE_BEGIN_ARGS/END_ARGS placeholder widget pattern
    - SBox/SVerticalBox/STextBlock centre-aligned placeholder layout primitives
  patterns:
    - Additive module-lifecycle superset: Plan 04 preserves Plan 03's IMPLEMENT_MODULE + log line and ONLY appends tab/menu registration + teardown
    - LOCTEXT namespacing per file: "NyraEditor" for module, "NyraChatPanel" for widget — Plan 12 appends keys inside "NyraChatPanel" without touching Plan 04's defines
    - Canonical-FName header (NyraChatTabNames.h) shared by module + test + Plan 12 widget — prevents string drift and makes grep-trivial
    - Test-first symbol availability: NyraPanelSpec.cpp includes the same NyraChatTabNames.h the module registers against, so Nyra.Panel.TabSpawner asserts the exact FName contract

key-files:
  created:
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraChatTabNames.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraChatPanel.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp
  modified:
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp

key-decisions:
  - "Accepted UE 5.6 nomad-tab floating-default dock over explicit right-side 420px placement. Rationale: UE 5.6 FTabSpawnerEntry does not expose a stable 'default dock area' API; FGlobalTabManager-side DockOn(RelativeDocking::RightSide) requires a target AreaSpec that does not exist at StartupModule time (no level editor layout has loaded yet). Floating-by-default matches UE's stock nomad tab behaviour (Output Log, Developer Tools, etc.) and users can dock anywhere via drag. Plan 12 revisits this when the panel gains persistent layout config via FTabManager::FLayout."
  - "Named FName constants (Nyra::NyraChatTabId) instead of inline FName literals. Rationale: single-source-of-truth — the automation test, the module registrar, the ShutdownModule un-registrar, and Plan 12's future consumers all reference the same symbol. Also enables grep -n 'Nyra::NyraChatTabId' to surface every usage site, critical for Plan 12 and Plan 13 surgery."
  - "UToolMenus::RegisterStartupCallback (not direct UToolMenus::Get()->ExtendMenu call) during StartupModule. Rationale: LoadingPhase PostEngineInit fires before the level editor's menu tree is fully populated; RegisterStartupCallback queues the extension until UToolMenus is ready. This is the canonical UE 5.6 pattern (matches how FLevelEditorModule registers its own extensions)."
  - "LOCTEXT namespace per file. Rationale: NyraEditorModule.cpp uses 'NyraEditor' (tab/menu labels live with the registrar); SNyraChatPanel.cpp uses 'NyraChatPanel' (widget-copy ownership). Localizer can ship panel and module strings in separate .po units."

patterns-established:
  - "Canonical-FName header pattern: Public/Nyra<Subsystem>TabNames.h defines inline const FName constants in namespace Nyra. Plans 12b/13 will mirror this for history-drawer and diagnostics tabs."
  - "Module superset pattern for multi-plan evolution: each plan that modifies NyraEditorModule.cpp must preserve every symbol and log line from prior plans; new wiring only appends. Verified via explicit acceptance literal in Plan 04 ('UE_LOG(LogNyra, Log, TEXT(\"[NYRA] NyraEditor module starting (Phase 1 skeleton)\"))' required to remain verbatim)."
  - "Spec-superset pattern: plans that populate Define() bodies preserve existing placeholder comments for sibling specs owned by other plans (Plan 04's TabSpawner block sits alongside retained Plan 12 AttachmentChip + StreamingBuffer placeholders)."

requirements-completed: []

duration: 8min
completed: 2026-04-21
---

# Phase 1 Plan 04: Nomad Tab + Placeholder Panel Summary

**Wave 1 UI scaffold — dockable "NyraChatTab" nomad tab under Tools -> NYRA -> Chat (CD-02) hosting an SNyraChatPanel placeholder that renders "NYRA — not yet connected", plus Nyra.Panel.TabSpawner automation It block closing VALIDATION row 1-04-01.**

## Performance

- **Duration:** ~8 min (wall clock; small plan, pure source authorship, zero surprise)
- **Started:** 2026-04-21T17:49:40Z
- **Completed:** 2026-04-21T17:58:36Z
- **Tasks:** 3/3 completed
- **Files created:** 3 (NyraChatTabNames.h + SNyraChatPanel.h + SNyraChatPanel.cpp)
- **Files modified:** 2 (NyraEditorModule.cpp superset of Plan 03; NyraPanelSpec.cpp superset of Plan 01 scaffold)

## Accomplishments

- **Canonical-FName header** `Public/NyraChatTabNames.h` exposing `Nyra::NyraChatTabId("NyraChatTab")`, `Nyra::NyraToolsMenuExtensionPoint("LevelEditor.MainMenu.Tools")`, and `Nyra::NyraMenuSectionName("NYRA")` — single source of truth referenced by the module, the menu callback, the unregister path, and the automation test.
- **SNyraChatPanel placeholder widget** (`Public/Panel/SNyraChatPanel.h` + `Private/Panel/SNyraChatPanel.cpp`) — NYRAEDITOR_API SCompoundWidget with `SLATE_BEGIN_ARGS(SNyraChatPanel) {}` and a `Construct` that renders "NYRA — not yet connected" header + "Plan 12 replaces this panel with the full chat UI." sub-line inside a centred SBox (HAlign_Center, VAlign_Center, Padding 32). Slate + AppStyle primitives only — zero backend deps, compiles in isolation.
- **Module wiring (additive superset of Plan 03's NyraEditorModule.cpp)** — `StartupModule` now registers the nomad tab spawner with `FGlobalTabManager::Get()->RegisterNomadTabSpawner(Nyra::NyraChatTabId, FOnSpawnTab::CreateStatic(&SpawnNyraChatTab))` under `WorkspaceMenu::GetMenuStructure().GetToolsCategory()`, and queues a `UToolMenus::RegisterStartupCallback` that extends `"LevelEditor.MainMenu.Tools"` with a NYRA section containing a Chat entry whose `FUIAction` calls `FGlobalTabManager::Get()->TryInvokeTab(Nyra::NyraChatTabId)`. `ShutdownModule` calls `UnregisterNomadTabSpawner(Nyra::NyraChatTabId)` and `UToolMenus::UnregisterOwner(this)` (guarded by `UObjectInitialized()`).
- **Plan 03 symbols preserved verbatim:** `IMPLEMENT_MODULE(FNyraEditorModule, NyraEditor)` at the canonical location; the `UE_LOG(LogNyra, Log, TEXT("[NYRA] NyraEditor module starting (Phase 1 skeleton)"))` log line still fires first in `StartupModule`; the Plan 10 TODO pointer (`// Plan 10: FNyraSupervisor::Get().SpawnNyraHost()`) relocated below the new wiring; `FNyraEditorModule::Get()` and `FNyraEditorModule::IsAvailable()` kept at the bottom.
- **Nyra.Panel.TabSpawner test (superset of Plan 01 scaffold)** — `Describe("TabSpawner") { It("registers NyraChatTab so TryInvokeTab returns a valid SDockTab", ...) }` asserts `FGlobalTabManager::Get()->TryInvokeTab(Nyra::NyraChatTabId)` returns a valid `TSharedPtr<SDockTab>` and that its `GetTabRole()` equals `ETabRole::NomadTab`. RequestCloseTab() on teardown for re-runnability. Plan 01 placeholders for `Nyra.Panel.AttachmentChip` (1-04-04) and `Nyra.Panel.StreamingBuffer` (1-04-05) retained verbatim with their Plan 12 pointers.

## Task Commits

1. **Task 1: NyraChatTabNames.h + SNyraChatPanel placeholder** — `224ffa7` (feat)
2. **Task 2: NyraEditorModule.cpp tab spawner + Tools -> NYRA -> Chat menu** — `628de82` (feat)
3. **Task 3: Nyra.Panel.TabSpawner automation It block** — `cf3ab9c` (test)

_Plan metadata commit (SUMMARY + STATE + ROADMAP) follows this summary._

## Files Created/Modified

**Created (3 files, ~92 LOC excluding doc headers):**

- `TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraChatTabNames.h` — 28 lines: three inline const FName constants in namespace Nyra with a 15-line doc header documenting owning plan + downstream consumers.
- `TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraChatPanel.h` — 36 lines: NYRAEDITOR_API SCompoundWidget declaration with doc header covering Phase 1 scope and Plan 12 replacement contract.
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp` — 56 lines: Construct body with SBox + SVerticalBox + two STextBlock slots, LOCTEXT namespace "NyraChatPanel", doc header locking the LOCTEXT key schema (NotConnectedHeader / NotConnectedSub) for Plan 12 to extend without rename.

**Modified (2 files):**

- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp` — superset of Plan 03's 31-line skeleton; grew to 95 lines. Preserves every Plan 03 symbol and log line verbatim (IMPLEMENT_MODULE line, StartupModule log, Plan 10 TODO marker, Get/IsAvailable accessors). Adds: 5 new includes (NyraChatTabNames, Panel/SNyraChatPanel, TabManager, SDockTab, WorkspaceMenuStructure + WorkspaceMenuStructureModule, ToolMenus, AppStyle), `LOCTEXT_NAMESPACE "NyraEditor"` scope, static `SpawnNyraChatTab(const FSpawnTabArgs&)`, StartupModule tab+menu wiring, ShutdownModule tab+menu teardown.
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp` — superset of Plan 01's 48-line scaffold; grew to 62 lines. Preserves `BEGIN_DEFINE_SPEC(FNyraPanelSpec, "Nyra.Panel", ...)`, `#if WITH_AUTOMATION_TESTS` guard, and inline placeholder comments for Plan 12's AttachmentChip (1-04-04) + StreamingBuffer (1-04-05) tests. Adds: 3 new includes (NyraChatTabNames.h, TabManager.h, SDockTab.h), one populated `Describe("TabSpawner") { It(...) }` block implementing VALIDATION row 1-04-01.

## Decisions Made

Followed PLAN.md exactly on all three tasks. Four implementation-nuance decisions worth recording for Plan 12:

1. **Floating-default dock accepted over right-side 420px default.** PLAN.md's `<interfaces>` section flags the dock-area trade-off explicitly ("precise docking area ... is usually user-overrideable. The DEFAULT is a floating tab; achieve 'right side panel' via the tab manager's DockOn ..."). UE 5.6's stable nomad-tab API does not expose a `FTabSpawnerEntry::SetDefaultDockArea` — the only path to enforce right-side placement is to edit `FTabManager::FLayout` (which requires a saved layout to already exist, chicken-and-egg). Plan 12 will revisit this when the panel gains persistent layout state via `FLayoutExtender`.

2. **Nyra::NyraChatTabId as inline const FName (not `static` or `extern`).** Inline const variables at namespace scope have guaranteed one-definition ODR in C++17+ (Cpp20 is the module baseline). This lets every .cpp that includes `NyraChatTabNames.h` reference the same symbol without a separate .cpp definition file — matches UE's own pattern for `LevelEditorTabIds::LevelEditorViewport` etc.

3. **UToolMenus::RegisterStartupCallback over direct ExtendMenu.** At StartupModule time (LoadingPhase = PostEngineInit per Plan 03 .uplugin), `UToolMenus::Get()->ExtendMenu("LevelEditor.MainMenu.Tools")` may return null because the level editor's menu tree is still being populated. `RegisterStartupCallback` queues the extension until UToolMenus signals ready — this is the pattern FLevelEditorModule itself uses. Without this indirection the menu entry would silently fail to appear on cold editor starts.

4. **LOCTEXT namespace split: NyraEditor for module-owned strings, NyraChatPanel for widget-owned strings.** Module labels (tab display name, menu section header, menu entry labels) stay in `NyraEditor` — localizer treats them as module-UI strings. Panel copy (NotConnectedHeader, NotConnectedSub) lives in `NyraChatPanel` — this namespace is the one Plan 12 extends with chat-UI strings (composer placeholder, attachment-chip labels, error toasts, etc.). Separation prevents Plan 12's chat-UI churn from flagging module-label .po files dirty.

## Deviations from Plan

### Non-breaking supersets of prior-plan artifacts

**1. [Rule 1 / non-breaking superset] `NyraEditorModule.cpp` grown from Plan 03's 31-line skeleton to 95-line tab-spawner + menu-extension module**

- **Found during:** Task 2 setup — Plan 03 authored a minimal StartupModule/ShutdownModule with only the log lines and two TODO markers (Plan 04 and Plan 10). PLAN.md's `<files_modified>` lists this file, and the `<action>` instructs "REPLACE `NyraEditorModule.cpp` with this content — preserving the Plan 03 StartupModule log line".
- **Action taken:** Replaced the file body but preserved every Plan 03 symbol verbatim per the Task 2 acceptance criteria ("File NyraEditorModule.cpp still contains literal text `UE_LOG(LogNyra, Log, TEXT("[NYRA] NyraEditor module starting (Phase 1 skeleton)"))` (preserved from Plan 03)" and "contains literal text `IMPLEMENT_MODULE(FNyraEditorModule, NyraEditor)` (preserved from Plan 03)"). Preserved Plan 03's Plan-10 TODO marker by relocating it after the new tab/menu wiring so Plan 10's supervisor spawn lands at the same logical injection point.
- **Impact:** Zero — acceptance criteria 13 and 14 explicitly require these preservations. This is the PLAN.md-mandated behaviour, not a deviation in the sense of scope creep.

**2. [Rule 1 / non-breaking superset] `NyraPanelSpec.cpp` Describe("TabSpawner") block added to Plan 01's placeholder Define()**

- **Found during:** Task 3 setup — Plan 01 (commit `ca182ba`) shipped NyraPanelSpec.cpp with an empty Define() containing only inline Plan 04 + Plan 12 placeholder comments, exactly as Plan 04 expected.
- **Action taken:** Added the TabSpawner Describe/It block, preserved Plan 01's BEGIN_DEFINE_SPEC signature (`"Nyra.Panel"` path, `EditorContext|EngineFilter` flags), preserved the `#if WITH_AUTOMATION_TESTS` guard, preserved the Plan 12 AttachmentChip + StreamingBuffer placeholder comments, preserved the `#include "NyraTestFixtures.h"` per Plan 01's fixture-first scaffold pattern (even though the TabSpawner test doesn't use any fixture helpers — Plan 01 locked "all five spec shells include NyraTestFixtures.h even when unused so future It() blocks drop in without touching includes").
- **Impact:** Zero. Plan 01's README file-map row for `Nyra.Panel.*` already declared Plan 04 as the co-owner of this file; this is the declared handoff.

### Platform-gap deferrals (host is macOS, target is Windows)

Per `<runtime_constraints>` in the execution prompt, every UE-compile-gated and UE-automation-execution-gated verify step is deferred to Windows CI:

- **Task 1 verify (UE 5.6 compile of SNyraChatPanel in isolation):** Deferred — macOS host lacks UE 5.6 UBT/MSVC. All grep-level acceptance criteria pass (8/8 literals).
- **Task 2 verify (UE 5.6 compile of NyraEditorModule.cpp with new includes; visual confirmation of Tools -> NYRA -> Chat menu; nomad tab spawn on click):** Deferred — same toolchain constraint. All grep-level acceptance criteria pass (14/14 literals). IDE clangd diagnostics on macOS report every UE type (`SDockTab`, `FSpawnTabArgs`, `ETabRole`, `LOCTEXT`, `FNyraEditorModule`, `NYRAEDITOR_API`, etc.) as undeclared — this is the documented macOS-LSP-lacks-UE-SDK-include-paths pattern carried over from Plans 01/03/05 and NOT a real compile failure.
- **Task 3 verify (running `UnrealEditor-Cmd.exe TestProject.uproject -ExecCmds="Automation RunTests Nyra.Panel.TabSpawner;Quit" -unattended -nopause -testexit="Automation Test Queue Empty"` exits 0):** Deferred — UnrealEditor-Cmd.exe is Windows-only. All grep-level acceptance criteria pass (7/7 literals).
- **Overall manual verification (open TestProject.uproject → Tools → NYRA → Chat menu → click → nomad tab with "NYRA — not yet connected" appears):** Deferred to the first Windows dev-machine open of TestProject.uproject.

**Total deviations:** 0 Rule 1-4 auto-fixes (plan content was followed exactly) + 2 non-breaking supersets of Plans 01/03 (both PLAN.md-mandated) + 4 platform-gap deferrals (mandated by runtime constraints, not scope creep).

**Impact on plan:** Zero scope creep. The plan specified an additive layer on top of two prior plans' scaffolds and each superset remains strictly additive (every old symbol preserved, new wiring appended). The `CHAT-01` requirement remains `pending` in REQUIREMENTS.md because CHAT-01's full surface — streaming tokens, markdown rendering, attachments, persisted per-conversation history — is scoped to Plan 12 and Plan 12b; Plan 04 lands only the tab-spawner scaffold (`requirements: [CHAT-01]` in plan frontmatter is the wave-1 contribution, not the closure).

## Issues Encountered

- **No blockers.** The two files-already-existed situations (NyraEditorModule.cpp from Plan 03 and NyraPanelSpec.cpp from Plan 01) were both PLAN.md-declared handoffs, handled as documented above.

## TDD Gate Compliance

Plan 04 is `type: execute` (Wave 1 UI scaffold), not `type: tdd`. No RED/GREEN/REFACTOR gate applies. The three commits follow conventional-commit types: `feat(...)` for the new widget + module wiring, `test(...)` for the automation It block. This matches the Plan 01/02/03 pattern (feat/test split with no TDD gate).

## Known Stubs

**SNyraChatPanel's Construct body is an intentional placeholder, not a stub.** The widget renders a declared "NYRA — not yet connected" copy plus a "Plan 12 replaces this panel with the full chat UI" sub-line — this is the Phase-1-locked visible artifact per RESEARCH §3.9 "ENABLED_PLUGIN state machine: panel is ALWAYS usable — no blank screen". Plan 12 (chat-panel-streaming-integration) replaces the Construct body in-place; Plan 12b (history-drawer) extends the layout; Plan 13 (first-run-ux-banners-diagnostics) overlays banner/diagnostics UI. The plan's `must_haves.truths` locks this as the expected Phase 1 rendering — not a stub preventing plan goal achievement.

No data-source stubs (no hardcoded empty arrays/objects/nulls flowing to UI), no TODO/FIXME markers beyond the Plan 10 supervisor hook preserved from Plan 03, no components receiving mock data.

## Threat Flags

No new security-relevant surface introduced. Plan 04 is pure editor-scope UI scaffolding:

- No network endpoints (tab-spawner + menu extension are editor-process-local)
- No auth paths (the SDockTab spawn is gated only by UE's own tab manager)
- No file access (the widget reads no config, writes no state)
- No schema change (no SQLite, no JSON persistence)

The future tab will host WebSocket traffic (Plan 10) and render streamed tokens (Plan 12) — both introduce threat surface that Plans 05/10/12's `<threat_model>` blocks will cover. Plan 04 adds zero such surface.

## Self-Check: PASSED

All claimed files exist on disk:

- `TestProject/Plugins/NYRA/Source/NyraEditor/Public/NyraChatTabNames.h` FOUND
- `TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraChatPanel.h` FOUND
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp` FOUND
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp` FOUND (modified)
- `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp` FOUND (modified)

All claimed commits exist in `git log --oneline`:

- `224ffa7` FOUND — Task 1 (NyraChatTabNames.h + SNyraChatPanel placeholder)
- `628de82` FOUND — Task 2 (NyraEditorModule.cpp tab spawner + Tools menu)
- `cf3ab9c` FOUND — Task 3 (Nyra.Panel.TabSpawner automation It block)

## User Setup Required

None — the placeholder panel is self-contained. First Windows dev-machine open of `TestProject.uproject` will compile the plugin (UBT picks up the 5 new includes automatically via `PublicDependencyModuleNames` declared in Plan 03's NyraEditor.Build.cs), and `Tools -> NYRA -> Chat` will appear in the menu bar on first launch.

## Next Phase Readiness

- **01-05 (specs-handshake-jsonrpc-pins):** Ready. Plan 05 is pure spec + fixture work; does not touch NyraEditorModule.cpp or the chat panel.
- **01-06 (nyrahost-core-ws-auth-handshake):** Ready. NyraHost side is independent of Plan 04.
- **01-10 (cpp-supervisor-ws-jsonrpc):** Ready. The StartupModule injection point marked `// Plan 10: FNyraSupervisor::Get().SpawnNyraHost()` is now positioned directly after the tab/menu wiring — supervisor lifecycle attaches cleanly.
- **01-12 (chat-panel-streaming-integration):** Ready. `SNyraChatPanel::Construct` is the single injection point. LOCTEXT_NAMESPACE "NyraChatPanel" locked for extension. The tab manager contract (`Nyra::NyraChatTabId`) is permanent — Plan 12 does NOT re-register the spawner, only replaces the widget body.
- **01-12b (history-drawer):** Ready. The SBox-centred ChildSlot is trivially replaceable with a split-pane layout; Plan 12b can depend on Plan 12 or drop in as a sibling slot.
- **01-13 (first-run-ux-banners-diagnostics):** Ready. Banners overlay onto SNyraChatPanel's layout; diagnostics drawer will hang off the same tab.

---

*Phase: 01-plugin-shell-three-process-ipc*
*Plan: 04-nomad-tab-placeholder-panel*
*Completed: 2026-04-21*
