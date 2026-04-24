---
phase: 02-subscription-bridge-ci-matrix
plan: 07
slug: compat-shim-empirical-fill
type: execute
wave: 1
depends_on: [01]
autonomous: false
tdd: false
requirements: [PLUG-04]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraCompatSpec.cpp
  - .planning/phases/02-subscription-bridge-ci-matrix/compat-matrix-first-run.md
research_refs: [§5.4, §5.5, §10.2]
context_refs: [D-13, D-14, D-15]
phase0_clearance_required: false
must_haves:
  truths:
    - "plugin-matrix.yml has been executed at least once (may include UE 5.7 as a manual local build if GA is imminent but CI runner cell still red) and the compile errors / deprecation warnings from each cell captured"
    - ".planning/phases/02-subscription-bridge-ci-matrix/compat-matrix-first-run.md archives the empirical findings: per-UE-version compile log excerpts, list of drift points encountered, deprecation warning summary"
    - "NYRACompat.h populated with SHIM ENTRIES ONLY for the drift points ACTUALLY surfaced by the matrix run — no speculative entries. Each entry has a // NYRA_COMPAT: <reason> tag and an #if NYRA_UE_AT_LEAST(X,Y) ... #else ... #endif block <20 lines"
    - "NyraCompatSpec.cpp extended with one It block per shim entry — each It asserts the compat helper returns a non-null / valid result on the current engine version"
    - "Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs module dependencies validated against all four UE versions' API surface (any dependency that drifted is noted in compat-matrix-first-run.md)"
    - "If UE 5.7 is unavailable at execute time per D-15, the matrix deferral is documented with a target date for the follow-up MR and the NYRACompat.h entries are still valid for 5.4/5.5/5.6"
  artifacts:
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h
      provides: "Populated NYRA::Compat namespace with empirically-verified drift entries"
      exports: ["NYRA_UE_AT_LEAST macro", "namespace NYRA::Compat with N drift helpers"]
    - path: .planning/phases/02-subscription-bridge-ci-matrix/compat-matrix-first-run.md
      provides: "Authoritative record of the first four-version matrix run — for future compat audits"
  key_links:
    - from: compat-matrix-first-run.md
      to: Plans 02-08, 02-09, 02-10 (Wave 2 C++ plans)
      via: "Wave 2 C++ plans MUST consult this doc before using drifted APIs (Slate text style, Material params, message log, etc.)"
      pattern: "Plan 02-0[89]|Plan 02-10"
---

<objective>
Populate `NYRA::Compat::` with **empirically-verified** drift entries after running Plan 02-01's four-version matrix for the first time. **Zero speculation** — every `#if` block is justified by a compile error / warning captured in `compat-matrix-first-run.md`.

Per CONTEXT.md:
- D-13: shim blocks <20 lines, tagged with `// NYRA_COMPAT: <reason>`
- D-14: `fail-fast: false` so all four cells run to completion — we get a full drift picture in one pass
- D-15: if 5.7 not GA, downgrade matrix + note deferral; 5.4/5.5/5.6 entries still valid

**This is a human-in-the-loop plan** (checkpoint inside Task 2) because the drift list is not known at plan-write time. Claude authors the archival doc structure + the NYRACompat.h skeleton additions; the operator pastes the real compile output and Claude populates the shim entries based on what actually surfaced.

Anticipated hotspots from RESEARCH §5.4 (candidates only — NOT pre-committed):
- `FSlateFontInfo` / `FTextBlockStyle` between 5.5 and 5.6
- `UMaterialInstanceConstant::SetScalarParameterValueEditorOnly` deprecation chain
- `UUMGSequencePlayer` deprecation in 5.6
- `ToolMenus` identifier drift (Phase 1 Plan 04 used `Tools > NYRA > Chat`)
- `FWebSocketsModule` edge cases (Phase 1 Plan 10 validated on 5.6; now tests all four)
- NNE header drift (deferred implementation — Plan 07 only verifies headers include cleanly)
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/02-subscription-bridge-ci-matrix/02-CONTEXT.md
@.planning/phases/02-subscription-bridge-ci-matrix/02-RESEARCH.md
@TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h
@TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs

<interfaces>
<!-- Shim entry template (per RESEARCH §5.5) - this is the AUTHORIZED form: -->

```cpp
// NYRA_COMPAT: 5.6 deprecated UUMGSequencePlayer in favor of runner structs
#if NYRA_UE_AT_LEAST(5, 6)
    inline FTextBlockStyle MakeChatHeaderStyle()
    {
        // 5.6+ shape — uses FTextBlockStyle::SetFontSize over deprecated SetFont
        return FTextBlockStyle()
            .SetFontSize(14.f)
            .SetColorAndOpacity(FSlateColor(FLinearColor::White));
    }
#else
    inline FTextBlockStyle MakeChatHeaderStyle()
    {
        // 5.4, 5.5 shape — uses legacy SetFont
        FSlateFontInfo Font = FCoreStyle::GetDefaultFontStyle("Regular", 14);
        return FTextBlockStyle()
            .SetFont(Font)
            .SetColorAndOpacity(FSlateColor(FLinearColor::White));
    }
#endif
```

<!-- compat-matrix-first-run.md template: -->

```markdown
# Phase 2 compat matrix — first-run empirical drift capture

**Captured:** <date>
**Runner:** <self-hosted hostname>
**UE versions tested:** 5.4.4, 5.5.4, 5.6.1, [5.7.X or "DEFERRED per D-15 — follow-up MR YYYY-MM-DD"]

## Per-version build status

| UE | BuildPlugin | Automation | Artifact size | Notes |
|----|-------------|------------|---------------|-------|
| 5.4.4 | ✅ green | ✅ green | X MB | — |
| 5.5.4 | ❌ compile error `FOO_API` | — | — | Drift #1 (Slate text style) |
| 5.6.1 | ✅ green | ✅ green | X MB | Phase 1 baseline (unchanged) |
| 5.7.X | ⚠ deprecated `UUMGSequencePlayer` | ✅ green | X MB | Drift #2 |

## Drift #1 — Slate text style (5.4, 5.5)
- Error: <verbatim compile error>
- Root cause: <inferred>
- Shim entry: `NYRA::Compat::MakeChatHeaderStyle()` in NYRACompat.h
- It block: `Nyra.Compat.TextStyleMake`

## Drift #2 — ...
...
```
</interfaces>
</context>

<tasks>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task 1: OPERATOR — Trigger plugin-matrix.yml first full run + capture logs</name>
  <what-built>
    Plan 02-01 landed plugin-matrix.yml + NYRACompat.h skeleton. This task needs the operator to physically trigger the CI matrix and capture the output.
  </what-built>
  <how-to-verify>
    1. On GitHub, navigate to Actions → Plugin Multi-Version CI → Run workflow → branch main. (Alternatively, open a PR touching any plugin source file to auto-trigger.)
    2. Wait for all four matrix cells to complete. `fail-fast: false` means all four run to completion.
    3. Download artifacts for each UE version (Artifacts/UE_X.Y/ + NyraAutomation-UEX.Y.log).
    4. For each cell, capture:
       - BuildPlugin exit status
       - First 50 lines of any compile error
       - Full deprecation-warning list
       - Automation test summary (pass/fail count)
    5. Save all logs locally (do not commit raw logs — they may be large). Provide Claude with summaries sufficient to populate compat-matrix-first-run.md.
    6. If UE 5.7 cell is red due to GA unavailability (not drift), note the planned follow-up MR date and plan to skip the 5.7 shim entries in Task 2; this is D-15 deferral.
  </how-to-verify>
  <resume-signal>
    Reply "matrix-run-complete" with a summary block like:
      - 5.4.4: green / red — [details]
      - 5.5.4: green / red — [details]
      - 5.6.1: green — (expected, Phase 1 baseline)
      - 5.7.X: green / red / deferred — [details]
    Paste compile error excerpts or "no drift" for each red cell.
  </resume-signal>
</task>

<task type="auto">
  <name>Task 2: Populate NYRACompat.h + authoring compat-matrix-first-run.md</name>
  <files>TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraCompatSpec.cpp, .planning/phases/02-subscription-bridge-ci-matrix/compat-matrix-first-run.md</files>
  <action>
    Based on the operator's matrix-run-complete summary from Task 1:

    1. Author `.planning/phases/02-subscription-bridge-ci-matrix/compat-matrix-first-run.md` per the template in interfaces block. Include the per-version build status table, one Drift section per observed drift point with error excerpt + inferred root cause + shim-entry name + It-block name. If a cell was deferred per D-15, document the deferral reason + target follow-up MR date.

    2. Update `NYRACompat.h`: for each drift, add a shim entry inside `namespace NYRA::Compat` following the template in the interfaces block. Every entry:
       - Is <20 lines total (including comments)
       - Starts with `// NYRA_COMPAT: <reason>` comment
       - Uses `NYRA_UE_AT_LEAST(X, Y)` guards (never raw `ENGINE_MINOR_VERSION`)
       - Returns a value (no side-effectful init); compat helpers are pure.

    3. Update `NyraCompatSpec.cpp`: for each shim entry, add one It block asserting the helper returns a valid result on the CURRENT dev-host engine version (Phase 1 Plan 01 patterns apply — see NyraJsonRpcSpec.cpp for the Describe/It style). Example: `It("returns valid FTextBlockStyle on current UE version", [] { auto S = NYRA::Compat::MakeChatHeaderStyle(); TestNotEqual(TEXT("FontSize"), S.GetFont().Size, 0); });`

    4. If ZERO drift was observed (all four cells compile + test green without changes), still do all three substeps above but the "Drift Sections" of the archival doc list "none observed; Phase 1 codebase is API-stable across 5.4-5.7 within tested surface" and NYRACompat.h / NyraCompatSpec.cpp get a comment noting this — the macro infrastructure is kept armed for Phase 4+ deepening.

    5. Confirm module dependencies in `NyraEditor.Build.cs` — if any dependency (WebSockets, UMG, ToolMenus, MessageLog, etc.) drifted between versions, document it in compat-matrix-first-run.md but do NOT edit Build.cs in this plan. Changes to Build.cs move to a follow-up plan with its own justification.

    Commit: feat(02-07): populate NYRA::Compat with empirical drift entries from first matrix run
  </action>
  <verify>
    <automated>test -f .planning/phases/02-subscription-bridge-ci-matrix/compat-matrix-first-run.md && grep -q "NYRA_COMPAT:" TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h || grep -q "none observed" TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h</automated>
  </verify>
  <done>
    - compat-matrix-first-run.md archives the matrix output
    - NYRACompat.h has shim entries (or a clear "none observed" note) — no speculative entries
    - NyraCompatSpec.cpp extended with one It block per shim
    - D-15 5.7 deferral documented if applicable
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

No new boundaries. This plan is compile-time C++ discipline only.

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-07-01 | Tampering | Speculative `#if` blocks obscure which entries are empirical | mitigate | Hard rule: no speculative entries. Every entry references a compat-matrix-first-run.md Drift section by number. Plan checker scans for entries lacking `// NYRA_COMPAT:` tag. |
| T-02-07-02 | Information Disclosure | Raw compile logs in git | accept | compat-matrix-first-run.md paraphrases errors; raw logs stay on operator's runner (artifact retention is 90 days GitHub default) |
</threat_model>

<verification>
- `grep -c "^#if NYRA_UE_AT_LEAST" TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h` matches Drift count in compat-matrix-first-run.md (or both are 0)
- `grep -c "It(" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraCompatSpec.cpp` ≥ 1 + Drift count
- `test -f .planning/phases/02-subscription-bridge-ci-matrix/compat-matrix-first-run.md` — archival doc present
</verification>

<success_criteria>
- First matrix run completed with explicit pass/fail for all four UE cells (or documented D-15 deferral)
- Every shim entry is justified by an empirical drift observation
- Archival doc allows Wave 2 C++ plans (02-08/09/10) to reason about UE-version-safe APIs
- Anticipated-hotspots list from RESEARCH §5.4 validated or invalidated against reality
</success_criteria>

<output>
After completion, create `.planning/phases/02-subscription-bridge-ci-matrix/02-07-SUMMARY.md`
</output>
