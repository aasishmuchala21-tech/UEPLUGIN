---
phase: 01-plugin-shell-three-process-ipc
plan: 13
subsystem: first-run-ux-banners-diagnostics
tags: [ue-cpp, slate, first-run-ux, banners, diagnostics, download-progress, chat-01, plug-02, plug-03, research-3-9]
requirements_progressed: [CHAT-01, PLUG-02, PLUG-03]
dependency_graph:
  requires:
    - 01-05-specs-handshake-jsonrpc-pins (docs/ERROR_CODES.md D-11 error.data.remediation wire shape consumed verbatim by the banner and download-modal error branches)
    - 01-09-gemma-downloader (nyrahost.handlers.download.DownloadHandlers emits diagnostics/download-progress notifications with status downloading/verifying/done/error; the modal consumes these)
    - 01-10-cpp-supervisor-ws-jsonrpc (FNyraSupervisor ENyraSupervisorState enum + OnStateChanged + OnUnstable + OnNotification + RequestShutdown + SpawnAndConnect consumed by the banner bindings + Restart callback)
    - 01-12-chat-panel-streaming-integration (SNyraChatPanel.h/.cpp structure + extern GNyraSupervisor pattern + Plan 12 chat/send + chat/stream + chat/cancel wiring preserved verbatim while being additively extended)
    - 01-12b-history-drawer (SNyraHistoryDrawer left column + SHorizontalBox two-column layout + OnOpenConversation/OnNewConversation bridge lambdas + HistoryDrawer->Refresh() call all preserved verbatim)
  provides:
    - SNyraBanner Slate widget (SCompoundWidget) with ENyraBannerKind {Hidden, Info, Warning, Error} + SetState overloads (message-only + message+buttons) + Hide + GetCurrentKind + indeterminate SProgressBar for Info kind + blue/yellow/red BorderBackgroundColor_Lambda + FOnBannerRestartClicked/FOnBannerOpenLogClicked delegates
    - SNyraDownloadModal Slate widget (SCompoundWidget) with OnProgress(TSharedPtr<FJsonObject>) + Show/Hide/IsShown + FOnDownloadCancelled delegate; SProgressBar Percent_Lambda on BytesDone/BytesTotal; status field dispatch for downloading/verifying/done/error; D-11 error.data.remediation extraction
    - SNyraDiagnosticsDrawer Slate widget (SCompoundWidget) with RefreshFromDisk() + static LogFilePath() helper; SExpandableArea InitiallyCollapsed(true); FFileHelper::LoadFileToStringArray reads last 100 lines into read-only monospace SMultiLineEditableTextBox; graceful fallback string "(log file not yet written)" when log file absent
    - SNyraChatPanel superset: 3 new TSharedPtr members (Banner, DownloadModal, Diagnostics); 4-slot right-column VBox layout [Banner | SOverlay(MessageList + DownloadModal) | Composer | Diagnostics]; GNyraSupervisor->OnStateChanged + OnUnstable + OnNotification bindings; diagnostics/download-progress dispatch BEFORE chat/stream branch; destructor unbinds all three delegates
  affects:
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraChatPanel.h (added 3 forward decls + 3 private TSharedPtr members; Plan 12 + 12b declarations preserved verbatim)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp (additively extended: new 4-slot VBox layout in right HBox column, OnStateChanged + OnUnstable lambdas, diagnostics/download-progress dispatch in HandleNotification, destructor extended to unbind the two new delegates)
tech-stack:
  added:
    - "SBorder + BorderBackgroundColor_Lambda color-swap pattern: kind-driven linear colour read via lambda so ENyraBannerKind transitions repaint without widget-tree rebuild"
    - "Indeterminate SProgressBar (no Percent binding) for Info-kind banner: communicates progress without a meaningful percentage"
    - "SProgressBar Percent_Lambda returning TOptional<float>: returns empty TOptional when BytesTotal <= 0 so the bar renders indeterminate until the first downloading frame arrives"
    - "SExpandableArea InitiallyCollapsed(true) + HeaderContent + BodyContent for the diagnostics drawer"
    - "FFileHelper::LoadFileToStringArray + FMath::Max(0, Lines.Num() - 100) tail-of-file pattern: full-file read then last-100-lines slice"
    - "FAppStyle::GetFontStyle(TEXT(\"MonospacedText\")) for the log-tail text box"
    - "FPlatformProcess::ExploreFolder for [Open log] -- opens logs directory in Windows Explorer / host platform file browser"
    - "IPluginManager::FindPlugin + GetBaseDir for the restart-supervisor callback so the respawn uses the same paths as the initial StartupModule spawn"
    - "SOverlay + HAlign(HAlign_Center) + VAlign(VAlign_Center) for the download-modal centred overlay on top of MessageList"
  patterns:
    - "Additive module-superset: Plan 12 + 12b SNyraChatPanel.cpp content preserved verbatim; Plan 13 adds three Slate members, one OnStateChanged lambda, one OnUnstable lambda, one diagnostics/download-progress branch in HandleNotification, and one destructor-unbind pair. No existing behaviour changed; no existing tests invalidated."
    - "Banner state machine driven by FNyraSupervisor lifecycle: the state-to-banner-kind mapping lives inside the panel's OnStateChanged lambda, so supervisor state changes (ENyraSupervisorState::{Spawning,WaitingForHandshake,Connecting,Authenticating}) cause Banner->SetState(Info,...) automatically; Ready -> Banner->Hide(); Crashed -> Banner->SetState(Warning,...). Matches RESEARCH §3.9 table."
    - "OnUnstable -> Error banner with [Restart] + [Open log]: the 3-in-60s restart policy trip point from Plan 10 is the ONLY way Error kind appears in Phase 1. Restart callback tears down + respawns the supervisor; Open log callback calls SNyraDiagnosticsDrawer::LogFilePath() (shared helper) then FPlatformProcess::ExploreFolder on the parent directory."
    - "RESEARCH Open Q 6 resolved: diagnostics/tail JSON-RPC method is SKIPPED in Phase 1. SNyraDiagnosticsDrawer reads the log file DIRECTLY from disk via FFileHelper::LoadFileToStringArray. Wire surface stays minimal; when/if the log grows unwieldy a Phase 2 plan can add the WS method."
    - "diagnostics/download-progress dispatch BEFORE chat/stream branch in HandleNotification: ensures the download modal can update even if MessageList is not yet valid (e.g. bootstrap-time progress before first chat). Early return after modal update keeps the branch independent of the chat dispatch fallthrough."
    - "Shared LogFilePath() static: SNyraDiagnosticsDrawer::LogFilePath() is callable from both the drawer body (to load the log) and the [Open log] callback (to derive the parent directory). Single source of truth for the <ProjectSaved>/NYRA/logs/nyrahost-<YYYY-MM-DD>.log path convention."
    - "Graceful fallback in RefreshFromDisk: if LoadFileToStringArray returns false (file missing -- most first-launch scenarios) the drawer shows \"(log file not yet written)\" instead of leaving the text box empty. Matches RESEARCH §3.9's \"panel is ALWAYS usable\" invariant."
key-files:
  created:
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraBanner.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraBanner.cpp
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraDownloadModal.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraDownloadModal.cpp
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraDiagnosticsDrawer.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraDiagnosticsDrawer.cpp
  modified:
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraChatPanel.h (added forward decls + 3 TSharedPtr members for Banner, DownloadModal, Diagnostics; Plan 12 + 12b declarations preserved verbatim)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp (additively extended per Plan 13 action block; Plan 12 + 12b wiring preserved verbatim)
decisions:
  - "Banner state-machine mapping lives in SNyraChatPanel's OnStateChanged lambda (not in SNyraBanner itself). Rationale: SNyraBanner is a generic three-kind widget -- making it aware of ENyraSupervisorState would couple it to Plan 10's supervisor types and make reuse in later phases (e.g. subscription-bridge banners in Phase 2) awkward. Keeping the mapping in the panel means Phase 2 can add new OnStateChanged branches (e.g. for Claude Code CLI auth state) without touching SNyraBanner. The panel is the right anchor because it already holds the extern GNyraSupervisor reference + the other wiring, and because the banner must inherit the panel's conversation context for future Phase 2 badges."
  - "Restart-callback does a full supervisor teardown + respawn rather than calling an idempotent 'restart' method on FNyraSupervisor. Rationale: Plan 10 does not provide a RestartFromScratch method -- FNyraSupervisor's respawn path is internal to its 3-in-60s policy (PerformSpawn is private). Calling RequestShutdown + .Reset() + MakeUnique + SpawnAndConnect mirrors NyraEditorModule::StartupModule's spawn sequence exactly and avoids adding new public API to FNyraSupervisor just for this callback. The full teardown also resets the CrashTimestamps window so the user can genuinely recover from an Unstable trip (otherwise the new supervisor would inherit the trip state and go Unstable again immediately)."
  - "Download modal does NOT auto-dismiss on status=done. Rationale: PLAN.md suggests 'Auto-hide after a short delay in a real app' but Phase 1 leaves the modal visible until the user clicks Cancel (which reads as 'Close' when status=done). Keeps the implementation deterministic (no timer handles to manage across panel teardown), lets the user verify the 'Done!' status text, and reuses the existing Cancel button for dismissal. A Phase 2 polish plan can add auto-dismiss with a 1.5s fade."
  - "Download-cancel path is local-only (no Python-side cancel endpoint). Rationale: Plan 09's DownloadHandlers explicitly does NOT expose a download-cancel method (it's a fire-and-forget asyncio.Task; killing it mid-flight leaves a .partial file that the next retry resumes from). The UE modal's Cancel button closes the modal locally and fires OnCancelled, which is bound to a no-op lambda in the panel. Documented as a known Phase 1 limitation; a Phase 2 plan can add a diagnostics/download-cancel notification if user research shows this is painful."
  - "Log-tail read uses FFileHelper::LoadFileToStringArray (full file into memory) instead of streaming the last N bytes. Rationale: Phase 1 log files are structlog JSON lines rotated daily at midnight (D-16) -- typical size <1 MB for a working editor session. Full read is both simpler and well within memory budget. If the file ever exceeds comfort bounds a Phase 2 plan can add a tail-via-seek helper without touching the drawer's public API (RefreshFromDisk is the single call site)."
  - "Graceful-fallback string for missing log file is literal \"(log file not yet written)\" instead of a LOCTEXT-keyed translation. Rationale: Plan 13 already uses LOCTEXT('DiagHeader', ...) and LOCTEXT('Refresh', ...) for the drawer's user-visible labels; the fallback string is a diagnostic placeholder that appears only during the narrow window before structlog's first write, and is not expected to need localisation for Phase 1. A Phase 2 i18n pass can promote it if needed."
  - "Banner is a direct SVerticalBox slot (AutoHeight) instead of wrapping inside a named container. Rationale: Hidden-kind banners use EVisibility::Collapsed on the SBorder which yields zero layout rows -- the SVerticalBox slot itself has no minimum height, so the banner costs nothing when hidden. Adding a named container (e.g. SBox with MinDesiredHeight(0)) would only be useful if we needed animated show/hide which is not a Phase 1 concern."
  - "DownloadModal lives inside an SOverlay WITH MessageList rather than as a modal window (SWindow / FMenuBuilder::AddMenuWidget). Rationale: the overlay approach keeps the modal inside the chat tab and therefore inside the same dock layout and mutation boundary as the rest of the panel. A real SWindow would float, could get lost behind other UE windows, and needs explicit teardown in the panel's destructor. HAlign/VAlign-Center plus the modal's own SBox visibility toggle give the same UX (centred blocking overlay) with less lifecycle surface."
metrics:
  duration: ~6min (agent wall time)
  completed: 2026-04-23
  tasks: 2
  commits: 2
  files_created: 6
  files_modified: 2
---

# Phase 1 Plan 13: First-Run UX Banners + Diagnostics Summary

**One-liner:** Closed the CHAT-01 "panel depth" gap by wiring `FNyraSupervisor` state transitions into an `SNyraBanner` (4 kinds: Hidden / Info / Warning / Error), mounting an `SNyraDownloadModal` that consumes `diagnostics/download-progress` notifications from Plan 09's Python side, and adding a collapsed-by-default `SNyraDiagnosticsDrawer` that tails `<ProjectSaved>/NYRA/logs/nyrahost-YYYY-MM-DD.log` directly from disk (RESEARCH Open Q 6 resolved: no `diagnostics/tail` WS method in Phase 1). Plan 12 + 12b `SNyraChatPanel.cpp` content preserved verbatim; all new wiring is additive inside a new 4-slot VBox in the existing right-column of the Plan 12b SHorizontalBox two-column layout.

## What Shipped

### Task 1 — `SNyraBanner` + `SNyraDiagnosticsDrawer` (commit `1995eea`)

- **`Public/Panel/SNyraBanner.h`** (74 lines). `enum class ENyraBannerKind : uint8 { Hidden, Info, Warning, Error }` + `FOnBannerRestartClicked` / `FOnBannerOpenLogClicked` delegates + `SNyraBanner : SCompoundWidget` with `SetState(Kind, Message, RestartCb, OpenLogCb)` + `SetState(Kind, Message)` (no-button overload) + `Hide()` + `GetCurrentKind()` accessor. Private members: `CurrentKind`, `RootBorder`, `Row`, the two delegate storage slots.

- **`Private/Panel/SNyraBanner.cpp`** (134 lines). `ColorForKind` maps `Info` -> blue (0.25, 0.40, 0.75, 0.95), `Warning` -> yellow (0.75, 0.55, 0.15, 0.95), `Error` -> red (0.80, 0.25, 0.25, 0.95), `Hidden` -> transparent. Construct wires an `SBorder` (initially Collapsed) with `BorderBackgroundColor_Lambda([this]() { return ColorForKind(CurrentKind); })` so kind swaps repaint in place. `SetState`:
  - Sets `CurrentKind` and stores the two delegates.
  - Sets SBorder visibility (Collapsed if Hidden else Visible).
  - Clears the row and rebuilds: if Info, prepends an indeterminate `SProgressBar` (no Percent binding) inside an `SBox(80x6)`; always adds the message `STextBlock` with `AutoWrapText(true)`; appends `[Restart]` button only if `RestartDelegate.IsBound()`; appends `[Open log]` button only if `OpenLogDelegate.IsBound()`.
  - `HandleRestart` / `HandleOpenLog` call `ExecuteIfBound` + return `FReply::Handled()`.

- **`Public/Panel/SNyraDiagnosticsDrawer.h`** (51 lines). `SNyraDiagnosticsDrawer : SCompoundWidget` with public `RefreshFromDisk()` + static `LogFilePath()` + private `HandleToggle` / `HandleRefresh` + `TailBox` (`SMultiLineEditableTextBox`) + `ContentContainer` (`SBox`) + `bExpanded`.

- **`Private/Panel/SNyraDiagnosticsDrawer.cpp`** (113 lines). `LogFilePath()` returns `<ProjectSavedDir>/NYRA/logs/nyrahost-<today-UTC>.log` via `FPaths::Combine` + `FDateTime::UtcNow().ToString("%Y-%m-%d")` + `FString::Printf("nyrahost-%s.log", ...)`. `Construct` wires an `SExpandableArea(InitiallyCollapsed(true))` with header `"Diagnostics"` and body = `[Refresh button + LogPath label (grey)] / [read-only monospace SMultiLineEditableTextBox, MaxHeight 300]`. `RefreshFromDisk` calls `FFileHelper::LoadFileToStringArray`; on failure shows `"(log file not yet written)"`; on success slices `FMath::Max(0, Lines.Num() - 100)` and concatenates with `"\n"` into the text box. `HandleToggle` flips `bExpanded` + calls `RefreshFromDisk` if expanding (unused in the current layout because `SExpandableArea` owns the toggle state — kept for future use); `HandleRefresh` always calls `RefreshFromDisk`.

### Task 2 — `SNyraDownloadModal` + banner/modal/drawer wiring into `SNyraChatPanel` (commit `b0ef8d1`)

- **`Public/Panel/SNyraDownloadModal.h`** (60 lines). `FOnDownloadCancelled` delegate + `SNyraDownloadModal : SCompoundWidget` with `SLATE_EVENT(OnCancelled)` + `OnProgress(TSharedPtr<FJsonObject>)` + `Show/Hide/IsShown()` + private `HandleCancel` + cached `BytesDone/BytesTotal/CurrentStatus` + `ProgressBar`, `StatusText`, `BytesText`, `RootContainer` widget pointers + `bVisible`.

- **`Private/Panel/SNyraDownloadModal.cpp`** (167 lines). Construct wires an `SBox` (initially Collapsed) wrapping an `SBorder(ToolPanel.GroupBorder, Padding=16)` containing an `SVerticalBox`:
  1. Bold "Downloading Gemma 3 4B (3.16 GB)" title
  2. `StatusText` — "Starting..." default
  3. `SProgressBar` with `Percent_Lambda([this]() -> TOptional<float> { if (BytesTotal <= 0) return {}; return float(BytesDone)/float(BytesTotal); })` — renders indeterminate until the first downloading frame lands
  4. `BytesText` grey label (0.6, 0.6, 0.6)
  5. `[Cancel]` `SButton`

  `OnProgress(Params)` calls `Show()`, extracts `status` + `bytes_done` + `bytes_total`, and dispatches on status:
  - `"downloading"` -> `StatusText = "Downloading... N%"` where `N = 100 * BytesDone/BytesTotal` (guarded against zero)
  - `"verifying"` -> `StatusText = "Verifying SHA256..."`
  - `"done"` -> `StatusText = "Done!"` (modal stays visible until user dismisses)
  - `"error"` -> extracts `error.data.remediation` per D-11 and sets `StatusText = "Error: " + Remediation`

  BytesText always formats to `"%.1f MB / %.1f MB"` when BytesTotal > 0.

  `HandleCancel` fires `OnCancelledDelegate` + `Hide()` + returns `FReply::Handled()`.

- **`Public/Panel/SNyraChatPanel.h`** — added three forward declarations (`SNyraBanner`, `SNyraDownloadModal`, `SNyraDiagnosticsDrawer`) and three private `TSharedPtr` members. Plan 12 + 12b declarations preserved verbatim.

- **`Private/Panel/SNyraChatPanel.cpp`** — additively extended:
  1. New includes: `Panel/SNyraBanner.h` + `Panel/SNyraDownloadModal.h` + `Panel/SNyraDiagnosticsDrawer.h` + `Process/FNyraSupervisor.h` + `Widgets/SOverlay.h` + `Interfaces/IPluginManager.h` + `Misc/Paths.h` + `HAL/PlatformProcess.h` + `HAL/PlatformApplicationMisc.h`.
  2. Right-column `SVerticalBox` was previously 2 slots `[FillHeight MessageList | AutoHeight Composer]`; it now has 4 slots `[AutoHeight Banner | FillHeight SOverlay(MessageList + DownloadModal) | AutoHeight Composer | AutoHeight Diagnostics]`. The outer SHorizontalBox two-column layout (drawer | right-column) from Plan 12b is preserved verbatim.
  3. Plan 12b's `OnOpenConversation` + `OnNewConversation` lambda bridges are preserved verbatim.
  4. Inside the existing `if (GNyraSupervisor.IsValid())` block:
     - `OnNotification` binding preserved verbatim.
     - NEW: `OnStateChanged.BindLambda` — switch on `ENyraSupervisorState` per RESEARCH §3.9 table. `Spawning/WaitingForHandshake/Connecting/Authenticating` -> `Banner->SetState(Info, "Setting up NYRA (~30s)")`. `Ready` -> `Banner->Hide()`. `Crashed` -> `Banner->SetState(Warning, "NyraHost crashed -- restarting")`.
     - NEW: `OnUnstable.BindLambda` — build `FOnBannerRestartClicked` (calls `RequestShutdown` + `.Reset()` + freshly-constructed `FNyraSupervisor` via `IPluginManager::FindPlugin("NYRA")->GetBaseDir()` + `FPaths::ProjectDir()` + `FPaths::Combine(..., "Saved", "NYRA", "logs")` — mirrors `NyraEditorModule::StartupModule`'s spawn sequence) and `FOnBannerOpenLogClicked` (calls `SNyraDiagnosticsDrawer::LogFilePath()` + `FPlatformProcess::ExploreFolder` on the parent directory). Then `Banner->SetState(Error, "NyraHost is unstable -- see Saved/NYRA/logs/", RestartCb, OpenLogCb)`.
  5. `HandleNotification` early-returns on `diagnostics/download-progress` -> `DownloadModal->OnProgress(Env.Params)` BEFORE the chat/stream branch. chat/stream branch preserved verbatim.
  6. `HistoryDrawer->Refresh()` call at end of Construct preserved verbatim.
  7. Destructor extended to unbind `OnStateChanged` + `OnUnstable` in addition to the preserved `OnNotification.Unbind()`.

## Banner state-machine (RESEARCH §3.9 table)

| FNyraSupervisor state | Banner kind | Banner message | Buttons |
| --- | --- | --- | --- |
| `Spawning` | `Info` (blue-accent) | "Setting up NYRA (~30s)" | none |
| `WaitingForHandshake` | `Info` (blue-accent) | "Setting up NYRA (~30s)" | none |
| `Connecting` | `Info` (blue-accent) | "Setting up NYRA (~30s)" | none |
| `Authenticating` | `Info` (blue-accent) | "Setting up NYRA (~30s)" | none |
| `Ready` | `Hidden` (collapsed) | — | — |
| `Crashed` | `Warning` (yellow-accent) | "NyraHost crashed -- restarting" | none |
| `Unstable` (OnUnstable trip) | `Error` (red-accent) | "NyraHost is unstable -- see Saved/NYRA/logs/" | `[Restart]` + `[Open log]` |

`ShuttingDown` and `Idle` are intentionally unhandled (default branch) — the tab closing sequence in `NyraEditorModule::ShutdownModule` tears the panel down before these states are observed.

## Download modal status flow

| `status` field | Modal behaviour |
| --- | --- |
| `"downloading"` | Progress bar updates from `bytes_done/bytes_total`; status text `"Downloading... N%"`; bytes label `"X MB / Y MB"` |
| `"verifying"` | Progress bar frozen at 100%; status text `"Verifying SHA256..."` |
| `"done"` | Progress bar at 100%; status text `"Done!"`; modal stays visible until user clicks Cancel (reads as "Close") |
| `"error"` | Status text `"Error: <remediation>"` where remediation is `error.data.remediation` per D-11; modal stays visible |

Phase 1 known limit: user-clicked Cancel is LOCAL-ONLY. Python's `DownloadHandlers` exposes no cancel endpoint (Plan 09); the background `asyncio.Task` runs to completion or error regardless. The modal's `OnCancelled` delegate is bound to a no-op lambda in the panel. A Phase 2 plan can add a `diagnostics/download-cancel` notification if user research shows this is painful.

## Log path convention

```
<ProjectDir>/Saved/NYRA/logs/nyrahost-YYYY-MM-DD.log
```

- `FPaths::ProjectSavedDir()` resolves to `<ProjectDir>/Saved`.
- Date segment uses `FDateTime::UtcNow().ToString("%Y-%m-%d")` (matches Python `structlog`'s `TimedRotatingFileHandler(when="midnight")` rotation from D-16).
- `SNyraDiagnosticsDrawer::LogFilePath()` is a static helper callable from both the drawer body (load for tail) and the banner's `[Open log]` callback (derive parent dir for `FPlatformProcess::ExploreFolder`) — single source of truth.
- Fallback when log file is absent: drawer shows `"(log file not yet written)"`; the banner's `[Open log]` still navigates to the logs directory (Explorer handles the empty dir gracefully).

## Widget hierarchy (post-Plan-13)

```
SNyraChatPanel (SCompoundWidget, NomadTab host)
  +-- SHorizontalBox  (Plan 12b two-column layout)
       |
       +-- Slot[AutoWidth]   SNyraHistoryDrawer  (Plan 12b, collapsed 24 px / expanded 220 px)
       |
       +-- Slot[FillWidth=1.0]
             +-- SVerticalBox  (Plan 13 extends to 4 slots)
                   |
                   +-- Slot[AutoHeight]       SNyraBanner  (Plan 13, Hidden by default)
                   |
                   +-- Slot[FillHeight=1.0]
                   |     +-- SOverlay  (Plan 13: message list + centred modal)
                   |           +-- Slot       SNyraMessageList  (Plan 12)
                   |           +-- Slot[HAlign=Center, VAlign=Center]
                   |                 +-- SNyraDownloadModal  (Plan 13, Collapsed by default)
                   |
                   +-- Slot[AutoHeight, Padding=6]  SNyraComposer  (Plan 12)
                   |
                   +-- Slot[AutoHeight]       SNyraDiagnosticsDrawer  (Plan 13, SExpandableArea collapsed)
```

Pre-Plan-13 2-slot right-column `[FillHeight MessageList | AutoHeight Composer]` is preserved inside slots 2 + 3 of the new 4-slot layout.

## JSON-RPC wire shapes consumed

Plan 13 consumes (does not emit) two new wire shapes:

**diagnostics/download-progress** (Plan 09 emits; docs/JSONRPC.md §3.7):
```json
{
  "jsonrpc": "2.0",
  "method": "diagnostics/download-progress",
  "params": {
    "status": "downloading",
    "bytes_done": 1572864,
    "bytes_total": 3391733760
  }
}
```

`status` field values: `"downloading"`, `"verifying"`, `"done"`, `"error"`. On `"error"`, `params.error.data.remediation` contains the D-11 remediation string rendered verbatim.

**FNyraSupervisor::OnStateChanged** (Plan 10 emits; C++ delegate, not WS):
```cpp
DECLARE_DELEGATE_OneParam(FOnSupervisorStateChanged, ENyraSupervisorState NewState);
```

Dispatched by `FNyraSupervisor::SetState` on state transition. Plan 13 binds the single-consumer lambda in `SNyraChatPanel::Construct`.

**FNyraSupervisor::OnUnstable** (Plan 10 emits; C++ delegate, not WS):
```cpp
DECLARE_DELEGATE(FOnSupervisorUnstable);
```

Dispatched by `FNyraSupervisor::RecordCrashAndMaybeRestart` when 3 crashes fall within a 60-second window. Plan 13 binds the single-consumer lambda in `SNyraChatPanel::Construct`.

## Restart callback sequence (Unstable banner -> `[Restart]` button)

```cpp
FOnBannerRestartClicked RestartCb = FOnBannerRestartClicked::CreateLambda([]()
{
    if (!GNyraSupervisor.IsValid()) return;
    GNyraSupervisor->RequestShutdown();       // sends "shutdown" notif, 2s grace, KillTree
    GNyraSupervisor.Reset();                  // free the unique_ptr

    TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(TEXT("NYRA"));
    if (!Plugin.IsValid()) return;
    const FString PluginDir  = Plugin->GetBaseDir();
    const FString ProjectDir = FPaths::ProjectDir();
    const FString LogDir     = FPaths::Combine(ProjectDir, TEXT("Saved"), TEXT("NYRA"), TEXT("logs"));

    GNyraSupervisor = MakeUnique<FNyraSupervisor>();
    GNyraSupervisor->SpawnAndConnect(ProjectDir, PluginDir, LogDir);
});
```

Mirrors `NyraEditorModule::StartupModule`'s spawn sequence exactly. Full-reset rationale: the new supervisor starts with empty `CrashTimestamps`, so the user can actually recover from the Unstable trip. An in-place "restart without reset" would inherit the 3-in-60s window and likely re-trigger OnUnstable immediately.

## Commits

| # | Task | Type | Commit | Message |
|---|------|------|--------|---------|
| 1 | Task 1 | feat | `1995eea` | add SNyraBanner + SNyraDiagnosticsDrawer widgets |
| 2 | Task 2 | feat | `b0ef8d1` | wire SNyraDownloadModal + banner + diagnostics into SNyraChatPanel |

_Plan metadata commit (SUMMARY + STATE + ROADMAP) follows this summary._

## Deviations from Plan

### Non-breaking adaptation

**1. [Adaptation] `SNyraDownloadModal::Construct` uses `SLATE_EVENT + InArgs._OnCancelled` instead of `OnCancelled_Lambda`**

- **Context:** PLAN.md Task 2 Action step 3 shows `DownloadModal::OnCancelled_Lambda([]() { ... })` inside the `SAssignNew` SOverlay slot. Slate macro expansion for `SLATE_EVENT(FOnDownloadCancelled, OnCancelled)` generates a setter method `.OnCancelled(FOnDownloadCancelled)` not `.OnCancelled_Lambda`. The `_Lambda` suffix is generated only by `SLATE_ATTRIBUTE` (TAttribute<T>).
- **Fix:** The SOverlay slot uses `.OnCancelled(FOnDownloadCancelled::CreateLambda([]() { /* no-op */ }))` which is the correct Slate-macro invocation for `SLATE_EVENT`. Modal's `Construct` reads `InArgs._OnCancelled` into `OnCancelledDelegate` as shown in PLAN.md.
- **Impact:** Zero semantic difference — lambda is still captured, delegate still executed on cancel. Matches the canonical Slate macro behaviour.
- **Files modified:** `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp`
- **Commit:** Included in Task 2 (`b0ef8d1`)

**2. [Adaptation] `TSharedPtr<IPlugin>::FindPlugin` + `IsValid()` guard in Restart callback**

- **Context:** PLAN.md shows `IPluginManager::Get().FindPlugin(TEXT("NYRA"))->GetBaseDir()` as a single chained expression. `FindPlugin` returns a `TSharedPtr<IPlugin>` which could be null if the plugin descriptor cannot be located (mostly theoretical -- this lambda fires from inside the plugin's own code, so the plugin is definitionally loaded).
- **Fix:** Store the `TSharedPtr<IPlugin>` in a local and guard with `if (!Plugin.IsValid()) return;` before calling `GetBaseDir()`. Prevents a null-deref crash in the pathological case where `FindPlugin` returns null (e.g. during tab teardown race). Rule 2 (missing critical defensive guard) — a crash here would be terminal because it fires on the user clicking [Restart] during an already-unstable state.
- **Impact:** Zero semantic difference in the happy path; one extra null-safety branch in the edge case. Matches the defensive posture already in place in `NyraEditorModule::StartupModule` (which also checks `Plugin.IsValid()` before calling `GetBaseDir()`).
- **Files modified:** `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp`
- **Commit:** Included in Task 2 (`b0ef8d1`)

### Platform-gap deferrals (host: macOS, target: Windows + UE 5.6)

Consistent with Plans 03/04/05/10/11/12/12b as documented in STATE.md. Plan 13 source is authored + grep-verified at the literal level, but the UE-toolchain verifications below require Windows + UE 5.6 UBT/MSVC which the macOS dev host cannot run:

1. **UE 5.6 compile** of 6 new files + 2 modified files through UBT's auto-include-generator. All referenced UE headers exist in UE 5.6 per Plans 10/11/12's confirmed header list plus Plan 13's additions (`Widgets/Layout/SExpandableArea.h`, `Widgets/Input/SMultiLineEditableTextBox.h`, `Widgets/Notifications/SProgressBar.h`, `Misc/FileHelper.h`, `HAL/PlatformProcess.h::ExploreFolder`, `Interfaces/IPluginManager.h` already verified in Plan 10 module wiring). Deferred to Windows CI.

2. **Manual verification** per PLAN.md `<verification>` block: delete `%LOCALAPPDATA%/NYRA/venv/` + `<ProjectDir>/Saved/NYRA/`, open UE 5.6, open NYRA Chat tab. Observe Info banner during bootstrap; after Ready, banner hides; on first chat send observe gemma_not_installed error frame with D-11 remediation; click Diagnostics expander, observe last 100 log lines. Kill NyraHost 3 times via Task Manager within 60s, observe Error banner with [Restart] + [Open log]; click [Restart] and verify respawn succeeds. Deferred to first Windows dev-machine open of TestProject.uproject after Plan 06's prebuild.ps1 has populated the NyraHost binaries.

3. **Manual download-modal verification**: trigger `diagnostics/download-gemma` (either from a future settings panel or by invoking the handler directly via a Ring 0 bench), observe the modal transitions through `downloading` (with progress bar + bytes label) -> `verifying` -> `done` states. Deferred to Plan 14's Ring 0 bench harness or a manual Windows smoke test.

4. **Banner state-machine verification**: exercise each `ENyraSupervisorState` value via the `FNyraSupervisor` policy test hooks (`SimulateCrashForTest` + the INyraClock injection path) and assert the banner's `GetCurrentKind()` matches the expected kind for each state. Deferred to a future automation spec (a `Describe("BannerStateMachine")` block in `NyraPanelSpec.cpp`) — Plan 13 focuses on wiring + manual verification per PLAN.md `<verification>` block.

These deferrals are consistent with the Phase-1 platform-gap posture established by all prior plans and do not block Plan 14 / 15 execution.

## Grep acceptance literals (all pass source-level)

Task 1 (8 literals):

```
grep -c "class NYRAEDITOR_API SNyraBanner"                            SNyraBanner.h              -> 1   PASS
grep -c "enum class ENyraBannerKind"                                  SNyraBanner.h              -> 1   PASS
grep -c "SetState"                                                    SNyraBanner.h              -> 3   PASS (>= 2; 2 overloads + 1 doc ref)
grep -c "SProgressBar"                                                SNyraBanner.cpp            -> 4   PASS (>= 1; include + 1 call + 2 comment refs)
grep -c "FFileHelper::LoadFileToStringArray"                          SNyraDiagnosticsDrawer.cpp -> 1   PASS (comment rewrite avoided the literal duplication)
grep -c 'TEXT("nyrahost-%s.log")'                                     SNyraDiagnosticsDrawer.cpp -> 1   PASS
grep -c "FMath::Max(0, Lines.Num() - 100)"                            SNyraDiagnosticsDrawer.cpp -> 1   PASS
grep -c "SExpandableArea"                                             SNyraDiagnosticsDrawer.cpp -> 3   PASS (>= 1; include + call + doc)
```

Task 2 (10 literals):

```
grep -c "class NYRAEDITOR_API SNyraDownloadModal"                     SNyraDownloadModal.h       -> 1   PASS
grep -c "OnProgress"                                                  SNyraDownloadModal.h       -> 1   PASS (>= 1)
grep -c "SProgressBar"                                                SNyraDownloadModal.cpp     -> 3   PASS (>= 1; include + call + doc)
grep -c "diagnostics/download-progress"                               SNyraChatPanel.cpp         -> 4   PASS (>= 1; real branch + 3 doc refs)
grep -c "GNyraSupervisor->OnStateChanged.BindLambda"                  SNyraChatPanel.cpp         -> 1   PASS
grep -c "GNyraSupervisor->OnUnstable.BindLambda"                      SNyraChatPanel.cpp         -> 1   PASS
grep -c "FPlatformProcess::ExploreFolder"                             SNyraChatPanel.cpp         -> 1   PASS (>= 1)
grep -c "Setting up NYRA"                                             SNyraChatPanel.cpp         -> 1   PASS (>= 1)
grep -c "NyraHost is unstable"                                        SNyraChatPanel.cpp         -> 1   PASS (>= 1)
TestProject builds cleanly                                            -- DEFERRED to Windows CI (see platform-gap §)
```

Plan 12 / 12b preservation invariants (all source-level):

```
grep -c "extern TUniquePtr<class FNyraSupervisor> GNyraSupervisor"    SNyraChatPanel.cpp         -> 1   PASS
grep -c 'GNyraSupervisor->SendRequest(TEXT("chat/send")'              SNyraChatPanel.cpp         -> 1   PASS
grep -c 'GNyraSupervisor->SendNotification(TEXT("chat/cancel")'       SNyraChatPanel.cpp         -> 1   PASS
grep -c "MessageList->UpdateMessageStreaming"                         SNyraChatPanel.cpp         -> 1   PASS
grep -c "MessageList->FinalizeMessage"                                SNyraChatPanel.cpp         -> 1   PASS
grep -c "SAssignNew(HistoryDrawer, SNyraHistoryDrawer)"               SNyraChatPanel.cpp         -> 1   PASS
grep -c "HistoryDrawer->Refresh()"                                    SNyraChatPanel.cpp         -> 2   PASS (call site + doc)
grep -c "OnOpenConversation"                                          SNyraChatPanel.cpp         -> 3   PASS (bind + doc refs)
grep -c "OnNewConversation"                                           SNyraChatPanel.cpp         -> 2   PASS (bind + doc ref)
```

Plan 13 new wiring:

```
grep -c "SAssignNew(Banner, SNyraBanner)"                             SNyraChatPanel.cpp         -> 1   PASS
grep -c "SAssignNew(DownloadModal, SNyraDownloadModal)"               SNyraChatPanel.cpp         -> 1   PASS
grep -c "SAssignNew(Diagnostics, SNyraDiagnosticsDrawer)"             SNyraChatPanel.cpp         -> 1   PASS
```

## Known Stubs

None introduced by Plan 13 itself. The Plan 12 "backend hard-coded to `gemma-local`" stub is orthogonal and remains (Phase 2 adds subscription backends per PROJECT.md). Plan 13 does not touch the chat/send path.

The one explicit Phase 1 limitation documented in PLAN.md and this summary:

- **Download-cancel is local-only** (no Python-side endpoint). The modal's Cancel button closes locally; background `asyncio.Task` continues to completion/error. This is an intentional Phase 1 scope decision (Plan 09 Decision #6), not a stub. The download eventually terminates naturally; on re-invocation `on_download_gemma` returns `{already_present:true}` once the GGUF lands.

## Threat Flags

No new network-exposed surface in Plan 13:

- **Banner Restart callback** tears down + respawns the in-process supervisor (IPC over loopback only). No new outbound network surface. The respawn re-uses Plan 10's `SpawnAndConnect` which still goes through the session/authenticate first-frame auth gate (D-07) with a freshly-generated token in the handshake file — the old token is invalidated by the handshake-file overwrite.
- **Banner Open-log callback** opens the logs directory via `FPlatformProcess::ExploreFolder`. Path is derived from `SNyraDiagnosticsDrawer::LogFilePath()` which constructs from `FPaths::ProjectSavedDir()` + static segments. No path-traversal surface.
- **DiagnosticsDrawer log read** reads from `<ProjectSavedDir>/NYRA/logs/nyrahost-<YYYY-MM-DD>.log`. Path is fully static (no user-controlled segments). `FFileHelper::LoadFileToStringArray` reads the whole file into a `TArray<FString>` then slices the last 100 — no integer-overflow surface, no buffer-overflow surface (UE's FString handles allocation internally).
- **DownloadModal D-11 remediation rendering**: `error.data.remediation` is rendered as plain text via `FText::FromString` in `StatusText->SetText`. No HTML/markdown interpretation — the remediation string cannot inject rich-text tags or Slate markup. D-11 remediation is a programmatic constant from `docs/ERROR_CODES.md` populated by the Python side, not user-controlled.

No threat_flag markers emitted.

## Self-Check: PASSED

All claimed files exist on disk:

```
TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraBanner.h                FOUND (new)
TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraBanner.cpp             FOUND (new)
TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraDownloadModal.h         FOUND (new)
TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraDownloadModal.cpp      FOUND (new)
TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraDiagnosticsDrawer.h     FOUND (new)
TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraDiagnosticsDrawer.cpp  FOUND (new)
TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraChatPanel.h             FOUND (modified -- Plan 12+12b content preserved verbatim, 3 new members added)
TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp          FOUND (modified -- Plan 12+12b content preserved verbatim, 4-slot VBox + state-machine lambdas + diagnostics/download-progress branch added)
```

All claimed commits present in `git log --oneline`:

```
1995eea FOUND -- Task 1 (SNyraBanner + SNyraDiagnosticsDrawer)
b0ef8d1 FOUND -- Task 2 (SNyraDownloadModal + banner/modal/drawer wiring)
```

All 8 Task 1 + 10 Task 2 = 18 grep acceptance literals verified green at source level. Plan 12 preservation invariants (9 literals) + Plan 12b preservation invariants (4 literals) all green. Plan 13 new wiring literals (3) all green. `git diff --diff-filter=D --name-only HEAD~2 HEAD` is empty (no unintended deletions).

Plan 14 / Plan 15 ready to consume: `SNyraBanner::SetState` + `SNyraDownloadModal::OnProgress` + `SNyraDiagnosticsDrawer::LogFilePath` are all public-API stable so Ring 0 bench harness (Plan 14) can exercise the first-run flow end-to-end on Windows without further widget changes.
