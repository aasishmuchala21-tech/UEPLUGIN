# Plan 02-12 Summary: Status Pill UI

**Phase:** 02-subscription-bridge-ci-matrix
**Plan:** 12
**Type:** execute
**Wave:** 2
**Depends_on:** [02, 10]
**Autonomous:** true
**Requirements:** [SUBS-05]
**Executed:** 2026-05-02

## Objectives

Add a three-pill status strip to the NyraChatPanel — [Claude] [Gemma] [Privacy] —
that reflects real-time backend state via `diagnostics/backend-state`
notifications. Pill colours per RESEARCH §9.3; click opens a context-sensitive
popover.

## What Was Built

### `NyraEditor/Public/Panel/SNyraBackendStatusStrip.h` — `FNyraBackendState` + widget
- `FNyraBackendState::FClaudeState` (bInstalled, Version, Auth, State,
  RateLimitResetsAt)
- `FNyraBackendState::FGemmaState` (bModelPresent, Runtime, State)
- `FNyraBackendState::FComputerUseState` (State)
- `ENyraPrivacyMode` enum (Normal, PrivacyMode)
- `ParseJson()` — mirrors docs/JSONRPC.md §4.8 `diagnostics/backend-state` shape
- `SNyraBackendStatusStrip` widget: `SetState()`, `Construct()`,
  `_OnClaudeClick`, `_OnGemmaClick`, `_OnPrivacyClick` delegate slots
- Pill colour constants: Green / Yellow / Red / Grey / Purple / Blue
- Private `IsPrivacyMode()` helper

### `NyraEditor/Private/Panel/SNyraBackendStatusStrip.cpp`
- `ParseJson()` using `TJsonReaderFactory<TCHAR>` + `TJsonSerializer`
- `RelativeTimeFromDateTime()` — formats `rate_limit_resets_at` as "< 1 min",
  "X min", or "Xh Ym"
- Colour helpers: `ClaudeColour()`, `GemmaColour()`, `PrivacyColour()`
- Tooltip helpers: `ClaudeTooltip()` / `GemmaTooltip()` /
  `PrivacyTooltip()` — context-sensitive text per state string
- `Construct()` — three pills built with lambdas capturing `this` so
  colour/tooltip update on every paint pass (no stale captures)
- `SetState()` → `Invalidate(EInvalidationReason::Paint)` to refresh

### Pill colour mapping (RESEARCH §9.3)

| State | Colour |
|-------|--------|
| Claude: ready | Green |
| Claude: rate-limited | Yellow |
| Claude: auth-drift | Red |
| Claude: offline / not-installed | Grey |
| Gemma: ready | Green |
| Gemma: downloading / loading | Blue |
| Gemma: not-installed | Grey |
| PrivacyMode active | Purple (solid pill + overlay on all three) |

### Mount point in `SNyraChatPanel`
- Status strip inserted between banner (Plan 13) and message list
  (`SVerticalBox::Slot().AutoHeight().Padding(4, 2)`)
- `HandleNotification` dispatch for `diagnostics/backend-state` fires
  `StatusStrip->SetState()` with parsed `FNyraBackendState`
- Caches `CurrentBackendState` for popover rendering
- Three popover implementations: `OpenClaudePopover()`,
  `OpenGemmaPopover()`, `OpenPrivacyPopover()`
- Privacy popover emits `session/set-mode` notification (toggle Normal ↔ PrivacyMode)

### `SNyraBackendStatusStrip.h` forward-decl + `SNyraChatPanel.h` wiring
- `SNyraBackendStatusStrip` forward-decl added to `SNyraChatPanel.h`
- `StatusStrip` shared pointer + `CurrentBackendState` + `bUserApprovedFallback`
  members
- Popover method declarations: `OpenClaudePopover`, `OpenGemmaPopover`,
  `OpenPrivacyPopover`

### `NyraEditor/Private/Tests/NyraStatusPillSpec.cpp` — automation spec
Five validation rows (Nyra.StatusPill.*):
- **2-12-01 PillCount** — construct + `SetState` call without crash
- **2-12-02 ClickRouting** — delegate acceptance confirmed for all three
  pills
- **2-12-03 PrivacyOverlay** — `PrivacyMode` + `Normal` accepted without crash
- **2-12-04 ColourFromState** — parse round-trip for all 5 key JSON shapes
  (claude/ready, claude/rate-limited, claude/auth-drift, gemma/ready,
  gemma/not-installed) + malformed-JSON fallback
- **2-12-05 TooltipByState** — parse round-trip for all tooltip-relevant states
  including auth field, reset timestamp, PrivacyMode enum value

## Deviations from Plan

- Popovers implemented as `FSlateNotificationManager` toasts (minimal v1) rather
  than a full `SMenuAnchor`-based popover widget — popover widget deferred to
  future iteration
- No `PopoverAnchor` member actually used in `SNyraBackendStatusStrip` despite
  being declared in the header — declared for future popover expansion

## Phase 0 Clearance

- Not required — status strip UI is read-only diagnostics; no subprocess or
  network egress

## Threat Model Compliance

| Threat | Mitigation |
|--------|------------|
| T-02-12-01 Stale pill colour | Lambdas capture `this`; every paint pass recomputes colour from `CurrentState` |
| T-02-12-02 Missing notification | Guard: `if (StatusStrip.IsValid())` before calling `SetState` |
| T-02-12-03 Privacy toggle in wrong mode | `session/set-mode` emitted only from `OpenPrivacyPopover`; no toggle from other popovers |

## Files Created / Modified

| File | Change |
|------|--------|
| `NyraEditor/Public/Panel/SNyraBackendStatusStrip.h` | new |
| `NyraEditor/Private/Panel/SNyraBackendStatusStrip.cpp` | new |
| `NyraEditor/Public/Panel/SNyraChatPanel.h` | modified (forward-decl, members, method decls) |
| `NyraEditor/Private/Panel/SNyraChatPanel.cpp` | modified (strip mount, HandleNotification branch, popover impls) |
| `NyraEditor/Private/Tests/NyraStatusPillSpec.cpp` | new |

## Checkpoint

**Type:** none — purely local UI, no external dependency
