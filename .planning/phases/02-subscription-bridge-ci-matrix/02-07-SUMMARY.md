# Plan 02-07 Summary: Compat Shim Empirical Fill

**Phase:** 02-subscription-bridge-ci-matrix
**Plan:** 02-07
**Type:** execute / checkpoint
**Wave:** 1
**Autonomous:** false | **TDD:** false
**Depends on:** [01]
**Blocking precondition:** `matrix-run-complete` resume signal from operator

## Objectives

Populate `NYRA::Compat::` with empirically-verified drift entries based on the
first full four-version CI matrix run. Zero speculation — every `#if` block
justified by a compile error or warning captured in `compat-matrix-first-run.md`.

## Current Status: CHECKPOINT — awaiting operator action

### Task 1 (blocking): OPERATOR — trigger plugin-matrix.yml first full run

Task 1 is a **human-action checkpoint**. Claude cannot execute this because:
- The self-hosted Windows runner is on the operator's hardware
- Downloading artifacts and capturing compile errors requires runner access
- The drift list is genuinely unknown until the matrix runs

**Precondition:** Plan 02-01 runner provisioning complete (self-hosted runner
Online with label `self-hosted,Windows,unreal`).

**Resume signal required:** `matrix-run-complete` with per-cell status:
- 5.4.4: green / red — [details]
- 5.5.4: green / red — [details]
- 5.6.1: green — (Phase 1 baseline)
- 5.7.X: green / red / deferred — [details]

## Anticipated Drift Hotspots (from RESEARCH §5.4 — NOT pre-committed)

These are candidates only, verified or invalidated by the matrix run:

| Candidate | Affects | Notes |
|----------|---------|-------|
| `FSlateFontInfo` / `FTextBlockStyle` | 5.4, 5.5 vs 5.6 | `SetFont` deprecated in 5.6 in favor of `SetFontSize` |
| `UMaterialInstanceConstant::SetScalarParameterValueEditorOnly` | 5.4, 5.5 vs 5.6 | Deprecation chain |
| `UUMGSequencePlayer` | 5.7 only | Deprecated in 5.6+ |
| `ToolMenus` identifier drift | Unknown | Phase 1 Plan 04 used `Tools > NYRA > Chat` |
| `FWebSocketsModule` edge cases | Unknown | Phase 1 Plan 10 validated on 5.6 only |
| NNE header drift | All versions | Headers include cleanly — verified in Plan 02-01 |

## What Will Be Built (Task 2 — auto, after Task 1 resumes)

Once `matrix-run-complete` is received:

1. **`compat-matrix-first-run.md`** — archival doc with:
   - Per-version build status table (BuildPlugin + Automation exit status)
   - One Drift section per observed drift: verbatim error excerpt, inferred root cause,
     shim-entry name, NyraCompatSpec.cpp It-block name
   - D-15 deferral note if UE 5.7 is unavailable

2. **`NYRACompat.h`** — updated `namespace NYRA::Compat` with one shim entry per drift:
   - Each entry <20 lines, `// NYRA_COMPAT: <reason>` tagged
   - `NYRA_UE_AT_LEAST(X, Y)` guards only (never raw `ENGINE_MINOR_VERSION`)
   - Example entry (only populated after drift is confirmed):
     ```cpp
     // NYRA_COMPAT: 5.6 deprecated SetFont in favor of SetFontSize
     #if NYRA_UE_AT_LEAST(5, 6)
         inline FTextBlockStyle MakeChatHeaderStyle() {
             return FTextBlockStyle()
                 .SetFontSize(14.f)
                 .SetColorAndOpacity(FSlateColor(FLinearColor::White));
         }
     #else
         inline FTextBlockStyle MakeChatHeaderStyle() {
             FSlateFontInfo Font = FCoreStyle::GetDefaultFontStyle("Regular", 14);
             return FTextBlockStyle()
                 .SetFont(Font)
                 .SetColorAndOpacity(FSlateColor(FLinearColor::White));
         }
     #endif
     ```

3. **`NyraCompatSpec.cpp`** — one `It` block per shim entry asserting the
   helper returns valid results on the current engine version

4. **Zero-drift path:** if all four cells compile + test green with no changes,
   the archival doc notes "none observed; Phase 1 codebase is API-stable across
   5.4–5.7 within tested surface" and `NYRACompat.h` gets a comment to that
   effect. The macro infrastructure remains armed for future drift.

## D-15 Deferral Rule

If UE 5.7 is not GA at execute time:
- Document deferral in `compat-matrix-first-run.md` with target follow-up MR date
- `NYRACompat.h` shim entries valid for 5.4/5.5/5.6
- 5.7 entries added when runner is upgraded

## Files Modified (planned)

| File | Change |
|------|---------|
| `NYRACompat.h` | Populated `NYRA::Compat` namespace with empirical shims |
| `NyraCompatSpec.cpp` | One `It` block per shim entry |
| `compat-matrix-first-run.md` | First-run archival doc with drift capture |

## Module-Superset Discipline

`NyraEditor.Build.cs` module dependencies verified against all four UE versions.
Any dependency that drifted is noted in `compat-matrix-first-run.md` but **Build.cs
is NOT edited in this plan** — changes move to a follow-up plan with their own
justification.

## Next Steps

After this plan completes, Wave 2 C++ plans (02-08, 02-09, 02-10) consult
`compat-matrix-first-run.md` before using drifted APIs. Plans 02-08/02-09/02-10
are unblocked by this document's existence.
