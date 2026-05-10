---
phase: 8
plan: 08-04
requirement: PARITY-04
verification_type: operator-manual
pending_manual_verification: true
ue_versions: [5.4, 5.5, 5.6, 5.7]
threats_addressed: [T-08-06]
created: 2026-05-10
status: pending
---

# Plan 08-04 (PARITY-04) — Operator Verification Runbook

**Why this is operator-manual:** PARITY-04 is C++/Slate-only. The verification
surface is the live UE editor's drag-and-drop pipeline -- there is no
automated harness for `FAssetDragDropOp` ingestion. Per RESEARCH.md
§Validation Architecture this plan is classified `manual-only`.

**Threats covered:** T-08-06 (drag-from-Content-Browser payload format
drift across UE 5.4 -> 5.7). The runbook below explicitly exercises each
of the 4 supported UE versions.

## Pre-conditions

- [ ] NYRA plugin builds clean for the target UE version (operator
  verifies with `Build/<Version>/Win64/UE5Editor-NyraEditor.dll` present
  and timestamp newer than this commit).
- [ ] NYRA chat panel docks visibly (`Window -> NYRA`).
- [ ] At least one StaticMesh, one Material, and one Blueprint asset
  exist somewhere under `/Game/...` (default starter content satisfies
  this).
- [ ] One `.png` file exists somewhere on disk reachable by Windows
  Explorer (any file).

## Per-version runbook

For each UE version in {5.4, 5.5, 5.6, 5.7}: open the project in that
editor, then run the six steps below. Mark PASS / FAIL / SKIPPED per
version in the result table.

1. **Open NYRA chat panel.** Confirm the composer drop zone label
   "Drop a reference image here, or paste from clipboard" is visible
   above the chips row.

2. **Drag StaticMesh from Content Browser.** Pick any StaticMesh
   (e.g. `/Game/StarterContent/Props/SM_Chair`) and drag it onto the
   composer drop zone.
   - **Expect:** drop zone briefly highlights (Accent border) on hover,
     reverts on drop, and a chip appears in the chips row showing
     `[StaticMesh] SM_Chair`. Chip tooltip shows the `/Game/...` path.
   - **Fail signal:** no chip appears, OR chip shows the bare filename
     without `[StaticMesh]` prefix, OR app crashes.

3. **Drag a Material.** Repeat step 2 with a Material asset (e.g.
   `/Game/StarterContent/Materials/M_Wood_Floor_Walnut_Polished`).
   - **Expect:** chip showing `[Material] M_Wood_Floor_Walnut_Polished`.

4. **Drag a Blueprint.** Repeat step 2 with a Blueprint class.
   - **Expect:** chip showing `[Blueprint] BP_<Name>` (or `[BlueprintGeneratedClass]`
     -- the exact class-name string is what `FAssetData::AssetClassPath.GetAssetName()`
     returns; record it verbatim in the result row).

5. **Drag a `.png` from Windows Explorer onto the same drop zone.**
   - **Expect:** chip rendering the legacy image-attachment shape
     (filename + absolute-path tooltip; NO `[<Class>]` prefix).
   - **This is the LOCKED-08 backward-compat regression check.** If the
     legacy chip stops rendering, the new OnAssetDropped delegate's
     short-circuit return is consuming external-file drops it shouldn't
     -- HALT and file a bug, do not mark PASS.

6. **Submit chat with chips present.** Click `[Send]`. Inspect the
   `chat/send` JSONRPC params (NyraHost log or `nyrahost`-side debug
   tap). Plan 08-04's scope ends at constructing `FNyraAttachmentRef`
   with the new fields; the JSON emission path that forwards them over
   WS is co-owned with Plan 08-01 (PARITY-01) per LOCKED-10.
   - **Expect (when 08-01 has shipped):** params include
     `attachments[i] = {kind: "asset", asset_path: "/Game/...",
     asset_class: "StaticMesh", display_name: "SM_Chair"}` for each
     asset chip.
   - **Expect (before 08-01 ships):** chat/send params do NOT yet
     include attachments at all. This is documented in NyraMessageModel.h
     -- not a regression. Mark step 6 as SKIPPED with a note pointing
     at the 08-01 dependency.

## Result table

| UE version | Step 1 | Step 2 (StaticMesh) | Step 3 (Material) | Step 4 (Blueprint) | Step 5 (Explorer .png regression) | Step 6 (JSONRPC) | Notes |
|------------|--------|---------------------|-------------------|--------------------|-----------------------------------|------------------|-------|
| 5.4        | TBD    | TBD                 | TBD               | TBD                | TBD                               | TBD              |       |
| 5.5        | TBD    | TBD                 | TBD               | TBD                | TBD                               | TBD              |       |
| 5.6        | TBD    | TBD                 | TBD               | TBD                | TBD                               | TBD              |       |
| 5.7        | TBD    | TBD                 | TBD               | TBD                | TBD                               | TBD              |       |

## T-08-06 divergence playbook

If `FAssetDragDropOp::GetAssets()` returns empty on some UE version even
though the editor visibly initiated a drag, the payload shape has drifted.
Mitigation in source order:

1. Add a `NYRA::Compat::ReadAssetData(const TSharedRef<FDragDropOperation>&)`
   shim near `SNyraImageDropZone::OnDrop` that handles version-specific
   payload extraction.
2. Surface the divergence in this VERIFICATION.md result row's Notes column
   with the exact UE build number (`Help -> About Unreal Editor`).
3. If the divergence cannot be papered over, escalate to a CONTEXT.md
   amendment and consider dropping the affected UE version from the
   four-version matrix temporarily.

## Operator sign-off

- **Operator name:** _________________________
- **Date verified:** _________________________
- **Result:** PASS / PASS-WITH-NOTES / FAIL
- **`pending_manual_verification`:** flip to `false` only after at least
  UE 5.6 + one of {5.4, 5.5, 5.7} pass steps 1-5 cleanly.
