---
phase: 8
plan: 08-04
requirement: PARITY-04
type: execute
wave: 1
tier: 1
autonomous: false
depends_on: []
blocking_preconditions: []
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraImageDropZone.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraImageDropZone.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraComposer.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraComposer.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/NyraMessageModel.h
---

# Plan 08-04: Drag-from-Content-Browser into Chat (PARITY-04)

## Goal

Extend `SNyraImageDropZone` to recognize `FAssetDragDropOp` payloads from the UE Content Browser and forward the structured `FAssetData` (asset path + asset class) into the chat composer as a new `Asset`-kind attachment chip. Per LOCKED-07: **no new widget; extend the existing one.**

## Why this matches Aura

Per CONTEXT.md SC#4 (verbatim):

> **Matches Aura on drag-from-Content-Browser UX**: PARITY-04 wires Slate drag-target on `SNyraComposer` to receive `FAssetData` payloads from the Content Browser; converts to a structured attachment chip referencing the asset path. The existing image-drop-zone pattern extends cleanly. Architectural gate: this unblocks Phase 8 plans that need asset-targeted prompts ("apply this material to the dragged asset").

This is a **matches**, not a beats. The deliverable is feature-surface parity.

## Pattern Compliance (PARITY-04 — non-mutator pattern alignment)

PARITY-04 is **not** a Phase 4 mutator — it's a Slate widget extension. Pattern alignment per PATTERNS.md §"PARITY-04":

| Concern | Existing primitive (extended) | Where it lives |
|---|---|---|
| Drag enter/over/leave visual feedback | `SNyraImageDropZone::OnDragOver/OnDragLeave` (already returns `FReply::Handled()`) | reused as-is |
| Asset drag detection | `SNyraImageDropZone::OnDrop` already inspects `FAssetDragDropOp` (cpp lines 92-103) | **extended** with `OnAssetDropped` delegate emission |
| Chip rendering | `SNyraComposer::AddAttachment` (cpp lines 92-105) | extended with new `Asset` kind in `FNyraAttachmentRef` |
| WS payload shape | `FNyraAttachmentRef` (NyraMessageModel.h) | extended with `asset_path` + `asset_class` fields |

**Three deltas, no rewrite** (per PATTERNS.md §"Plan 08-04 work = three deltas"):
1. Add second delegate type `FOnNyraAssetDropped` next to existing `FOnNyraImageDropped`.
2. In `OnDrop` (cpp 92-103), capture full `FAssetData` and route to `OnAssetDropped` when operation is `FAssetDragDropOp`. Keep image-path branch for external-file (Explorer) drops.
3. Per T-08-06: per-UE-version verify `FAssetDragDropOp` payload shape on 5.4/5.5/5.6/5.7.

**No new widget. No header rename.** LOCKED-07 enforced.

## MCP Registration

**No MCP tool registered.** PARITY-04 is Slate-side only. The asset path + class arrive in the JSONRPC payload as fields on the existing attachment shape; NyraHost decides how to interpret them per-tool.

Per RESEARCH.md §Shared Pattern 5: "No NyraHost-side change for PARITY-04."

## Tasks

### Task 1: Extend `SNyraImageDropZone.h` with `FOnNyraAssetDropped` delegate

**Files:** `NyraEditor/Public/Panel/SNyraImageDropZone.h`

**Action:** Per RESEARCH.md §Code Examples §"PARITY-04 Slate drop extension":

```cpp
// Add near existing FOnNyraImageDropped declaration (line ~10)
DECLARE_DELEGATE_OneParam(FOnNyraAssetDropped, const FAssetData& /*Asset*/);

// In SLATE_BEGIN_ARGS block (lines 15-17):
SLATE_EVENT(FOnNyraImageDropped, OnImageDropped)
SLATE_EVENT(FOnNyraAssetDropped, OnAssetDropped)   // NEW

// In private section (line ~28):
FOnNyraImageDropped OnImageDroppedDelegate;
FOnNyraAssetDropped OnAssetDroppedDelegate;        // NEW
```

`#include "AssetRegistry/AssetData.h"` for `FAssetData` (Slate already pulls AssetRegistry transitively but the include is needed for the function arg).

**Verify:** `NyraEditor` compiles clean on UE 5.6.

**Done:** Header extended with new delegate type + slate arg + member.

### Task 2: Extend `SNyraImageDropZone::OnDrop` cpp to dispatch by drag-op kind

**Files:** `NyraEditor/Private/Panel/SNyraImageDropZone.cpp`

**Action:** Per RESEARCH.md §Code Examples §"PARITY-04" — existing lines 92-103 already handle `FAssetDragDropOp`. Replace the current single-branch with the dual-emission logic:

```cpp
FReply SNyraImageDropZone::OnDrop(const FGeometry& Geom, const FDragDropEvent& Evt)
{
    bDragOverActive = false;
    Invalidate(EInvalidateWidget::Paint);

    if (TSharedPtr<FDragDropOperation> Op = Evt.GetOperation())
    {
        if (Op->IsOfType<FAssetDragDropOp>())
        {
            TSharedPtr<FAssetDragDropOp> AssetOp = StaticCastSharedPtr<FAssetDragDropOp>(Op);
            if (AssetOp.IsValid() && AssetOp->GetAssets().Num() > 0)
            {
                const FAssetData& Asset = AssetOp->GetAssets()[0];

                // PARITY-04 NEW — prefer structured FAssetData if delegate is bound.
                if (OnAssetDroppedDelegate.IsBound())
                {
                    OnAssetDroppedDelegate.Execute(Asset);
                    return FReply::Handled();
                }
                // Fallback to legacy path-string emission for backward compat.
                if (OnImageDroppedDelegate.IsBound())
                {
                    OnImageDroppedDelegate.Execute(Asset.GetObjectPathString());
                    return FReply::Handled();
                }
            }
        }
        // External-file drag path — preserve existing logic.
        // ... (existing path-string emission unchanged) ...
    }
    return FReply::Unhandled();
}
```

**Per LOCKED-08 backward-compat:** chips that today render image attachments from external Explorer drops MUST continue to work unchanged. The dual-delegate emission only activates `OnAssetDroppedDelegate` when the parent (composer) explicitly binds it.

**Verify:** Manual smoke — drag a `.png` from Windows Explorer onto the existing drop zone (should still render an image chip via `OnImageDropped` legacy path); drag a UE asset from Content Browser onto the same drop zone (should render an asset chip via new path).

**Done:** Drop zone routes drag-op type correctly without breaking existing image-drop behavior.

### Task 3: Extend `FNyraAttachmentRef` with `Asset` kind + asset_path / asset_class fields

**Files:** `NyraEditor/Public/Panel/NyraMessageModel.h`

**Action:** Find the existing `FNyraAttachmentRef` struct (referenced by RESEARCH.md as the existing payload shape). Add an `Asset` value to the kind enum and two new fields:

```cpp
UENUM()
enum class ENyraAttachmentKind : uint8
{
    Image,
    Text,
    Video,
    Document,   // PARITY-01 — kept aligned across plans
    Asset       // PARITY-04 NEW
};

USTRUCT()
struct FNyraAttachmentRef
{
    GENERATED_BODY()
    UPROPERTY() ENyraAttachmentKind Kind;
    UPROPERTY() FString Path;          // existing
    UPROPERTY() FString DisplayName;   // existing
    // PARITY-04 NEW
    UPROPERTY() FString AssetPath;     // /Game/Foo/Bar
    UPROPERTY() FString AssetClass;    // StaticMesh / Material / Blueprint
};
```

JSONRPC serialization (existing `ToJson()` / `FromJson()` on the struct) extends to include the two new fields when `Kind == ENyraAttachmentKind::Asset`. The chat-handler on NyraHost side picks them up; no new helper.

**Verify:** `NyraEditor` compiles clean.

**Done:** Payload shape extended; serialization round-trips.

### Task 4: Wire `OnAssetDropped` in `SNyraComposer` to call `AddAttachment` with Asset kind

**Files:** `NyraEditor/Public/Panel/SNyraComposer.h`, `NyraEditor/Private/Panel/SNyraComposer.cpp`

**Action:** Wherever `SNyraComposer::Construct` (or its panel parent) instantiates the drop zone, bind the new delegate:

```cpp
// In SNyraComposer::Construct or wherever the drop zone is built:
ChildSlot
[
    SNew(SNyraImageDropZone)
    .OnImageDropped(this, &SNyraComposer::HandleImageDropped)
    .OnAssetDropped(this, &SNyraComposer::HandleAssetDropped)   // PARITY-04 NEW
];

// New handler:
void SNyraComposer::HandleAssetDropped(const FAssetData& Asset)
{
    FNyraAttachmentRef Ref;
    Ref.Kind         = ENyraAttachmentKind::Asset;
    Ref.AssetPath    = Asset.GetObjectPathString();
    Ref.AssetClass   = Asset.AssetClassPath.GetAssetName().ToString();
    Ref.DisplayName  = Asset.AssetName.ToString();
    AddAttachment(Ref);
}
```

`AddAttachment` (cpp lines 92-105) already pushes onto the chip row; the row renderer needs a tiny branch to render Asset chips with class+name (e.g. "[StaticMesh] SM_Crate") rather than a thumbnail. Use Asset thumbnail via `FAssetThumbnailPool` if straightforward; fall back to a label-only chip if not.

**Verify:** Manual — drag a StaticMesh from Content Browser; chip renders showing "[StaticMesh] SM_Crate" with the asset path tooltip.

**Done:** Composer renders asset chips alongside the existing image/text chips.

### Task 5: Operator-run four-version verification (T-08-06) — `pending_manual_verification: true`

**Files:** `08-04-VERIFICATION.md`

**Operator runbook (per UE version 5.4/5.5/5.6/5.7):**
1. Open NYRA chat panel
2. Drag a StaticMesh from Content Browser onto composer drop zone — assert chip renders with class+name
3. Drag a Material — assert chip
4. Drag a Blueprint — assert chip
5. Drag a `.png` from Windows Explorer onto the same drop zone — assert image chip still renders (regression for legacy path)
6. Submit chat: assert JSONRPC payload to NyraHost contains `attachments[i] = {kind: "asset", asset_path: "/Game/...", asset_class: "StaticMesh", display_name: "SM_Crate"}`

T-08-06 mitigation: per-version smoke. If `FAssetDragDropOp::GetAssets()` returns empty on some version, document the divergence and add a `NYRA::Compat::ReadAssetData(Op)` shim.

**Done:** VERIFICATION.md filled with PASS/FAIL per UE version.

## Tests

| Test file | What it verifies | Pending manual? |
|---|---|---|
| (no Python tests — Slate-only) | n/a | n/a |
| `08-04-VERIFICATION.md` | Four-version Slate drop-routing smoke | **Yes** (operator) |

Per RESEARCH.md §Validation Architecture: PARITY-04 has no automated test path — the surface is UE-side Slate; the only meaningful test is operator-run on each UE version.

## Threats addressed

- **T-08-06** (drag-from-Content-Browser payload format drift across UE 5.4-5.6): Task 5 four-version operator runbook explicitly covers this. If `GetAssets()` returns empty on a version, the per-version shim path is the documented response.
- **LOCKED-07 enforcement**: only `SNyraImageDropZone` modified; no new widget. Three-delta pattern from PATTERNS.md preserved.
- **LOCKED-08 backward compat**: existing `OnImageDropped` external-file path preserved; new `OnAssetDropped` only fires when bound by parent.

## Acceptance criteria

- [ ] `NyraEditor` compiles clean on UE 5.6 with no new warnings.
- [ ] Existing image-from-Explorer drop continues to work unchanged (regression-free) — verified manually.
- [ ] Dragging a UE asset from Content Browser onto the composer drop zone renders an asset chip showing `[<Class>] <Name>`.
- [ ] JSONRPC payload to NyraHost on submit contains `attachments[i] = {kind: "asset", asset_path: ..., asset_class: ...}` for asset chips.
- [ ] `08-04-VERIFICATION.md` operator-run: dragged-asset round-trip succeeds on at least UE 5.6 + one of {5.4, 5.5, 5.7}; T-08-06 divergence (if any) is documented with a shim plan.

## Honest acknowledgments

- **Slate-only plan with no Python tests.** The only meaningful verification is operator-run live drag-and-drop. RESEARCH.md §Validation Architecture explicitly classifies PARITY-04 as `manual-only`.
- **Per LOCKED-07, no `SNyraAssetDropZone` even though it might "feel cleaner."** Two parallel drop-target codepaths is the anti-pattern.
- **`FAssetThumbnailPool` for chip thumbnails is a nice-to-have**; if Slate plumbing is finicky on some UE version, fall back to label-only chip — visual polish is not the parity bar.
