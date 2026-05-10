# Phase 8: Competitive Parity vs Aura — Research

**Researched:** 2026-05-10
**Domain:** UE5 Python authoring agents + document parsing + Slate drag/drop + UE Insights `.utrace`
**Confidence:** MEDIUM-HIGH overall (HIGH on doc parsers, drop zone, blueprint_debug pattern; MEDIUM on UE Python API symbols across 5.4–5.7; LOW on `.utrace` binary format)

## Summary

Phase 8 ships eight discrete plans (PARITY-01..08) that match Aura's documented public-beta surface as of 2026-05-10. Six of the eight (`PARITY-02/03/05/06/07/08`) are UE-side mutator/reader tools that plug into the Phase 4 NyraTool / NyraToolResult / `session_transaction` / `idempotent_lookup` / `verify_post_condition` pattern. PARITY-01 is a Python-only attachment-pipeline extension (no UE-side code). PARITY-04 is a Slate-only widget extension (no Python-side code). The bar is "Aura's documented capability is matched or exceeded on the same input shape."

**Primary recommendation:** Treat each plan as a thin wrapper around an already-paid-for primitive. PARITY-02..08 (UE Python authoring) reuse the canonical mutator shape from `actor_tools.py` / `material_tools.py` — one file per plan, one tool per name, every mutator wrapped by `with session_transaction(...)` and post-verified via `verify_post_condition`. PARITY-01 reuses `nyrahost.attachments.ingest_attachment` for the dedup/sharding boilerplate and adds a per-extension extractor pass that emits text + a list of embedded image refs. PARITY-04 extends `SNyraImageDropZone::OnDrop` (which already inspects `FAssetDragDropOp`) to forward the `FAssetData` payload into a new asset-chip variant of `SNyraAttachmentChip`.

Two findings drive the architecture more than expected: (a) Aura's own VFX/AnimBP/Metasounds agents are documented as "alpha" with explicit known-issue lists — the parity bar is therefore lower than feared and NYRA's transactional + idempotent + post-verified mutator shape is already a "beats" claim on those Aura docs; (b) UE's BehaviorTree Python API surface is **not** reflected through `unreal.BehaviorTree` directly — authoring requires `unreal.BehaviorTreeFactory` for asset creation plus `EditorGraphLibrary` + a per-node-class `UEdGraphNode_BehaviorTree*` instantiation pass that **may need a small C++ helper exposed via `UCLASS(MinimalAPI)` + `UFUNCTION(BlueprintCallable, meta=(ScriptMethod))`** for the composite/decorator/task node types that are not fully Python-reflected. Same risk applies to AnimBP transition graphs and Metasounds graph nodes. The planner must reserve a "uHelper.cpp" surface in PARITY-02/03/05/07/08 plans for the cases where Python alone can't reach a node class.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **LOCKED-01**: Phase 8 displaces Fab Launch Prep to Phase 9. ROADMAP.md updated 2026-05-10.
- **LOCKED-02**: Eight feature areas, one plan each. Plans 08-01..08-08 map 1:1 to PARITY-01..PARITY-08 for grep clarity.
- **LOCKED-03**: Reuse Phase 4 Tool Catalog patterns. Plans 08-02, 08-03, 08-05, 08-07, 08-08 are mutator tools and MUST follow `session_transaction` (BL-04) + `idempotent_lookup/record` (BL-05) + `verify_post_condition` (BL-06) + `NyraToolResult.to_dict()` (BL-01). No new mutator shape.
- **LOCKED-04**: Reuse Phase 5 `StagingManifest` for any artefact-producing tools that persist outside the UE project (Niagara templates, BT templates).
- **LOCKED-05**: Plan 08-06's `nyra_perf_explain_hotspot` output schema MUST include `citations: list[str]` populated from `KbSearchTool.execute(...)` results.
- **LOCKED-06**: Document-attachment text extraction is pure-Python only. Wheel-cache impact under 50 MB. No native PDF tooling (poppler/mupdf).
- **LOCKED-07**: PARITY-04 EXTENDS `SNyraImageDropZone`. Does NOT add a new widget. Avoids parallel drop-target codepaths.
- **LOCKED-08**: Each plan is independently shippable. No plan's success criteria reference another Phase 8 plan.
- **LOCKED-09**: Phase 8 EXIT bar is `{PARITY-01, PARITY-02, PARITY-03, PARITY-04}` all shipped + at least 2 of `{05, 06, 07, 08}`.

### Claude's Discretion

The CONTEXT.md does not list a separate "Claude's Discretion" section. The planner's freedom areas are constrained by LOCKED decisions; everything else (task wave structure, per-plan internal naming, helper-module organisation, test-fixture strategy) is at planner discretion.

### Deferred Ideas (OUT OF SCOPE)

- Slate UI overlay generation (Aura's natural-language-to-Slate; defer to v1.2).
- IDE / Claude Code integration (Aura's IDE-side; non-goal — NYRA users already use Claude Code separately).
- Live Coding C++ for non-NYRA-authored code (Plan 08-02 ships authoring + recompile loops only for files NYRA created in the session).
- Niagara module authoring (Plan 08-05 ships system + emitter + module-parameter-set, NOT custom-module DSL authoring).
- Behavior Tree task implementation in C++ (Plan 08-03 authors graphs + calls existing tasks; new-task generation could later land via Plan 08-02's C++ surface).
- AnimBP custom AnimNode generation (Plan 08-07 ships state machines + transitions only).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PARITY-01 | Document attachments (PDF/DOCX/PPTX/XLSX/HTML/MD) + embedded-image extraction | §1 below — pypdf 6.11.0 + python-docx 1.2.0 + python-pptx 1.0.2 + openpyxl 3.1.5 + Markdown 3.10.2 + beautifulsoup4 confirmed pure-Python under 50 MB combined |
| PARITY-02 | C++ authoring + Live Coding (`nyra_cpp_module_create / class_add / function_add / recompile`) | §2 below — `ILiveCodingModule::Compile()` + `IHotReloadInterface::DoHotReloadFromEditor()` accessible from Python via thin C++ helper. `nyra_blueprint_debug` regex pattern surface extends to MSVC/Clang error lines |
| PARITY-03 | Behavior Tree agent (`nyra_bt_create / add_composite / add_task / add_decorator / set_blackboard_key`) | §3 below — `unreal.BehaviorTreeFactory` exists; node-class instantiation needs a `MinimalAPI` C++ helper for the EdGraph nodes |
| PARITY-04 | Drag-from-Content-Browser into chat | §4 below — `FAssetDragDropOp` already handled in current `SNyraImageDropZone::OnDrop`; needs payload-shape branch + new asset-chip kind |
| PARITY-05 | Niagara VFX agent (`nyra_niagara_create_system / add_emitter / set_module_parameter`) | §5 below — `unreal.NiagaraSystemFactoryNew` + `unreal.NiagaraEditorSubsystem` exist 5.4+; module-parameter-set surface is the riskiest API and may require a C++ helper |
| PARITY-06 | Performance profiling (`nyra_perf_stat_read / insights_query / explain_hotspot`) | §6 below — `stat unit` parses from console output (already wired via Plan 02-10/11); `.utrace` is a custom binary format, so we shell to UnrealInsights.exe `-OpenTraceFile` + parse its CSV/JSON export, not the binary directly |
| PARITY-07 | Animation Blueprint (`nyra_animbp_create / add_state_machine / add_transition`) | §7 below — `unreal.AnimBlueprintFactory` exists; state-machine + transition graph nodes need a C++ helper for the `UAnimStateNodeBase` family |
| PARITY-08 | Metasounds (`nyra_metasound_create / add_node / connect`) | §8 below — `unreal.MetaSoundFactory` (note the capitalisation) exists 5.4+; node graph mutation requires `UMetaSoundBuilderSubsystem` (5.3+) which IS Python-reflected and is the cleanest surface in the phase |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| PARITY-01 doc text + image extraction | NyraHost (Python sidecar) | UE side reads paths via existing attachment table | Pure-Python parsers. Embedded-image refs flow through existing `attachments.ingest_attachment` |
| PARITY-02 C++ module/class/function authoring | NyraHost (Python sidecar) | UE C++ helper for Live Coding RPC | File creation is filesystem; Live Coding trigger needs a C++ shim because Python can't reach `ILiveCodingModule` directly |
| PARITY-03 BT graph authoring | NyraHost (Python sidecar) | UE C++ helper for EdGraph node spawning | `unreal.BehaviorTreeFactory` is reflected; node-class spawn likely needs MinimalAPI helper |
| PARITY-04 drag-from-Content-Browser | NyraEditor (Slate C++) | NyraHost (only as recipient of asset path) | Pure Slate. No Python work — `SNyraImageDropZone::OnDrop` extension only |
| PARITY-05 Niagara system/emitter authoring | NyraHost (Python sidecar) | UE C++ helper for module-parameter set | System/emitter create is reflected; parameter set is the Python-API gap |
| PARITY-06 perf stat read + Insights query + explain | NyraHost (Python sidecar) | NyraEditor (to relay `stat unit` console output via existing nyra_console_exec / nyra_output_log_tail) | Reuses Phase 2 Plan 02-10/11 console + log surfaces. `.utrace` parsing is out-of-process via `UnrealInsights.exe` |
| PARITY-07 AnimBP state machine | NyraHost (Python sidecar) | UE C++ helper for AnimGraphNode spawn | Same pattern as PARITY-03 |
| PARITY-08 Metasounds graph | NyraHost (Python sidecar) | None — `UMetaSoundBuilderSubsystem` is fully reflected | Smallest helper surface in the phase |

## Standard Stack

### PARITY-01 Document Parsers (verified at PyPI 2026-05-10)

| Library | Version | Purpose | Confidence | Why Standard |
|---------|---------|---------|------------|--------------|
| `pypdf` | 6.11.0 (BSD-3) | PDF text + image extraction | HIGH | [VERIFIED: pypi.org/pypi/pypdf/json] Pure-Python, ~310 KB wheel, no C extension hard deps. `cryptography` is optional for AES-encrypted PDFs only — declare as `pypdf[crypto]` extra and lazy-handle the fallback for password-locked inputs |
| `pdfplumber` | 0.11.9 (MIT, 2026-01-05) | Layout-aware PDF text + tables | MEDIUM | [VERIFIED: pypi.org/pypi/pdfplumber/json] Wheel is only 60 KB but pulls `pdfminer.six==20251230`, `Pillow>=9.1`, `pypdfium2>=4.18.0`. **Caution:** `pypdfium2` ships precompiled binaries for the PDFium C++ library — that's a C extension dependency, even though it's wheels-only. **Recommendation: skip pdfplumber for the default extractor.** Use pypdf for text and images. Reserve pdfplumber for an optional "table-aware" extraction pass that the user enables via flag |
| `python-docx` | 1.2.0 (MIT, 2025-06-16) | DOCX text + embedded image extraction | HIGH | [VERIFIED: pypi.org/pypi/python-docx/json] Pure-Python, ~253 KB wheel. Depends on `lxml>=3.1.0` (lxml ships precompiled wheels but is a C extension) — accepted under LOCKED-06 because lxml has no platform-fragmentation problem on Windows x64 (the only target) |
| `python-pptx` | 1.0.2 (MIT, 2024-08-07) | PPTX text + embedded image extraction | HIGH | [VERIFIED: pypi.org/pypi/python-pptx/json] ~473 KB wheel. Depends on `Pillow`, `XlsxWriter`, `lxml`, `typing-extensions`. Pillow ships C extensions but is wheel-only on Windows x64 |
| `openpyxl` | 3.1.5 (MIT, 2024-06-28) | XLSX cell text + sheet metadata | HIGH | [VERIFIED: pypi.org/pypi/openpyxl/json] ~251 KB wheel, pure-Python. Single dep `et-xmlfile` |
| `markdown` | 3.10.2 (BSD-3, 2026-02-09) | Markdown → HTML normalization | HIGH | [VERIFIED: pypi.org/pypi/markdown/json] Pure-Python, no runtime deps. Used to normalize MD into a structured-text intermediate that the same extractor pipeline consumes |
| `beautifulsoup4` | latest 4.x | HTML text + image extraction | HIGH | [ASSUMED — current version not verified this session, but the library is stable with `lxml` or `html.parser` parsers]. Use `html.parser` (stdlib) for the default to avoid pulling lxml twice |

**Wheel-cache budget table** (T-08-02 mitigation):

| Package | Approximate wheel size on Windows x64 |
|---------|---------------------------------------|
| pypdf | 0.31 MB |
| python-docx | 0.25 MB |
| python-pptx | 0.47 MB |
| openpyxl | 0.25 MB |
| markdown | 0.15 MB |
| beautifulsoup4 | 0.20 MB |
| Pillow (transitive) | ~3.5 MB |
| lxml (transitive) | ~3.8 MB |
| XlsxWriter (transitive) | ~0.16 MB |
| **Total estimate** | **~9.1 MB** |

[ASSUMED: transitive package sizes — pip-compile run on the dev box is the verification step]. Well under the 50 MB ceiling. Plan 08-01's verification step MUST run a real pip-compile on the Windows runner and assert the materialised wheels under `Binaries/Win64/NyraHost/wheels/` total under 75 MB (T-08-02 fail-loud bar).

### PARITY-02 C++ Authoring Helpers

| Technology | Version | Purpose | Confidence |
|------------|---------|---------|------------|
| `ILiveCodingModule` | UE 5.4+ | Trigger Live Coding compile from Python via C++ helper | MEDIUM [ASSUMED: API name from prior UE knowledge; verify in code via UE engine search before Plan 08-02 wave 1] |
| `IHotReloadInterface` | UE 5.4+ | Fallback Hot Reload trigger when Live Coding off | MEDIUM [ASSUMED] |
| `FModuleManager::Get()` | UE 5.4+ | Module lookup for module-creation step | HIGH |
| MSBuild (UnrealBuildTool subprocess) | UE-bundled | Standalone module compile when Live Coding offline | HIGH |
| Pattern matching surface | Existing `nyra_blueprint_debug` regex list (`base.py` + `blueprint_debug.py`) | C++ compile error → plain-English explanation | HIGH — extend the existing `_ERROR_PATTERNS` table with MSVC + clang patterns |

### PARITY-03 / PARITY-05 / PARITY-07 / PARITY-08 UE Python Authoring (verification matrix)

| Subsystem | Suspected Python Symbol | Confidence | Cross-Version Risk |
|-----------|--------------------------|------------|---------------------|
| BehaviorTree create | `unreal.BehaviorTreeFactory` + `unreal.AssetTools.create_asset(...)` | MEDIUM [ASSUMED] | T-08-01 — verify each of 5.4/5.5/5.6/5.7 |
| BehaviorTree blackboard | `unreal.BlackboardData` + `unreal.BlackboardEntry` | MEDIUM [ASSUMED] | Likely stable |
| BT composite/decorator/task spawn | `unreal.BTCompositeNode` family — NOT typically Python-reflected for graph spawn | LOW [ASSUMED — needs C++ helper] | High |
| Niagara System create | `unreal.NiagaraSystemFactoryNew` | MEDIUM [ASSUMED] | T-08-04 (GPU vs CPU emitter) |
| Niagara emitter add | `unreal.NiagaraEditorSubsystem` or stack-API | LOW [ASSUMED — likely needs C++ helper for module-parameter set] | High |
| AnimBP create | `unreal.AnimBlueprintFactory` | MEDIUM [ASSUMED] | T-08-01 |
| AnimBP state machine | `unreal.AnimGraphNode_StateMachineBase` family — not typically Python-reflected | LOW [ASSUMED — needs C++ helper] | High |
| Metasound create | `unreal.MetaSoundFactory` (note caps) | MEDIUM [ASSUMED] | T-08-01 — Aura docs mention 5.3 incompatibility, 5.4–5.6 Wave Player issues |
| Metasound builder | `unreal.MetaSoundBuilderSubsystem` (5.3+) | MEDIUM [ASSUMED — but cited from Aura's "5.4–5.6 Wave Player issues" implying the subsystem exists from at least 5.3] | Medium |

**Validation discipline (per LOCKED-03 + T-08-01):** Each of PARITY-03/05/07/08 plans MUST include a Wave 0 spike task that runs:

```python
# in a one-shot pytest under tests/test_unreal_python_smoke.py
import unreal
print([s for s in dir(unreal) if 'BehaviorTree' in s])
print([s for s in dir(unreal) if 'Niagara' in s])
print([s for s in dir(unreal) if 'AnimBlueprint' in s])
print([s for s in dir(unreal) if 'MetaSound' in s])
print([s for s in dir(unreal) if 'Metasound' in s])
```

The output is committed to `.planning/phases/08-competitive-parity-aura/symbol-survey-{ue_version}.md` per UE version (the operator runs it on each of 5.4/5.5/5.6/5.7 boxes). This is the **only** way to verify symbol availability — UE Python docs are Cloudflare-gated and not WebFetch-accessible.

### Code Sources (Phase 4 already-paid-for primitives)

| Primitive | Path | Use For |
|-----------|------|---------|
| `NyraTool` base class | `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/base.py` | Subclass for every PARITY tool |
| `session_transaction` | same | Wrap mutators (PARITY-02/03/05/07/08) |
| `idempotent_lookup` / `idempotent_record` | same | First two lines of every PARITY mutator |
| `verify_post_condition` | same | Last line before `NyraToolResult.ok(...)` |
| `_ERROR_PATTERNS` regex list | `blueprint_debug.py` lines 33–91 | Extend with MSVC/Clang patterns for PARITY-02 |
| `KbSearchTool` | `kb_search.py` | Mandatory dependency for PARITY-06 (LOCKED-05) |
| `attachments.ingest_attachment` | `attachments.py` | PARITY-01 reuses for embedded-image dedup |
| `SNyraImageDropZone::OnDrop` | `Panel/SNyraImageDropZone.cpp:76-118` | PARITY-04 extends (LOCKED-07) |
| `SNyraComposer::AddAttachment` | `Panel/SNyraComposer.cpp:92-105` | PARITY-04 endpoint — chip row already wired |
| `FNyraAttachmentRef` | `Panel/NyraMessageModel.h` (referenced) | Existing payload shape; PARITY-04 adds an `asset_path` variant |

## Architecture Patterns

### System Architecture Diagram (Phase 8)

```
                 ┌──────────────────────────────────────────────────┐
                 │                   UE Editor                       │
                 │                                                   │
  user drops ──► │  SNyraImageDropZone (Slate)                       │
   asset / file  │      │ OnDrop inspects FDragDropOperation type    │
                 │      ├── FAssetDragDropOp ──► asset chip variant  │ ◄── PARITY-04
                 │      └── FExternalDragOperation ──► path string   │
                 │              │                                    │
                 │      SNyraComposer.AddAttachment(...) ────────────┐
                 │                                                   │
                 │  user types ──► WebSocket JSONRPC to NyraHost     │
                 └────────────────────────────────┬──────────────────┘
                                                  │
                                                  ▼
                 ┌──────────────────────────────────────────────────┐
                 │              NyraHost (Python sidecar)            │
                 │                                                   │
                 │  attachments.py / extractors/                     │ ◄── PARITY-01
                 │      ├── pdf_extractor.py (pypdf)                 │
                 │      ├── docx_extractor.py (python-docx)          │
                 │      ├── pptx_extractor.py (python-pptx)          │
                 │      ├── xlsx_extractor.py (openpyxl)             │
                 │      ├── html_extractor.py (bs4)                  │
                 │      └── md_extractor.py (markdown + bs4)         │
                 │           ↓ each emits (text, [image AttachmentRef])
                 │           ↓                                       │
                 │      ingest_attachment for each embedded image    │
                 │           ↓ flows into vision routing as before   │
                 │                                                   │
                 │  tools/cpp_authoring.py                           │ ◄── PARITY-02
                 │  tools/bt_authoring.py                            │ ◄── PARITY-03
                 │  tools/niagara_authoring.py                       │ ◄── PARITY-05
                 │  tools/perf_profiling.py ──┐                      │ ◄── PARITY-06
                 │  tools/animbp_authoring.py │                      │ ◄── PARITY-07
                 │  tools/metasound_authoring.py                     │ ◄── PARITY-08
                 │                              │                    │
                 │  KbSearchTool ◄──────────────┘ (LOCKED-05)        │
                 │     │ all UE-side calls go through               │
                 │     ▼                                              │
                 │  unreal.* Python API   (in-editor Python plugin)  │
                 │     │                                              │
                 │     ▼ where unreal.* is unreflected               │
                 │  C++ helper module: NyraToolHelpers (MinimalAPI)  │
                 │     │   exposes UFUNCTION(BlueprintCallable,      │
                 │     │     meta=(ScriptMethod)) wrappers for       │
                 │     │     EdGraph node spawn, Live Coding, etc.   │
                 │     ▼                                              │
                 │  UE editor mutation                                │
                 │                                                   │
                 │  All mutators wrapped: session_transaction(...)   │
                 │  All mutators dedup: idempotent_lookup/record(...)│
                 │  All mutators verify: verify_post_condition(...)  │
                 └──────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
TestProject/Plugins/NYRA/Source/
├── NyraEditor/                                     # UE C++
│   ├── Private/Panel/
│   │   └── SNyraImageDropZone.cpp                  # PARITY-04 EXTENDS this file
│   ├── Private/ToolHelpers/                        # NEW — Phase 8 C++ helper bucket
│   │   ├── NyraBTHelper.cpp                        # PARITY-03 EdGraph node spawner
│   │   ├── NyraNiagaraHelper.cpp                   # PARITY-05 module-parameter setter
│   │   ├── NyraAnimBPHelper.cpp                    # PARITY-07 state-machine spawner
│   │   ├── NyraLiveCodingHelper.cpp                # PARITY-02 Live Coding trigger
│   │   └── NyraInsightsHelper.cpp                  # PARITY-06 utrace-CSV-export shim
│   └── Public/ToolHelpers/                         # NEW — matching headers
└── NyraHost/src/nyrahost/
    ├── attachments.py                              # PARITY-01 EXTENDS this file
    ├── extractors/                                 # NEW — Phase 8 extractor bucket
    │   ├── __init__.py
    │   ├── pdf.py
    │   ├── docx.py
    │   ├── pptx.py
    │   ├── xlsx.py
    │   ├── html.py
    │   └── md.py
    └── tools/
        ├── cpp_authoring.py                        # PARITY-02 NEW
        ├── bt_authoring.py                         # PARITY-03 NEW
        ├── niagara_authoring.py                    # PARITY-05 NEW
        ├── perf_profiling.py                       # PARITY-06 NEW
        ├── animbp_authoring.py                     # PARITY-07 NEW
        └── metasound_authoring.py                  # PARITY-08 NEW
```

### Pattern 1: Phase 4 Mutator Shape (canonical)

**What:** Every UE-mutating tool follows the same five-line wrapper around its core mutation.
**When to use:** PARITY-02 (each of 4 sub-tools), PARITY-03 (each of 5), PARITY-05 (each of 3), PARITY-07 (each of 3), PARITY-08 (each of 3).

```python
# Source: nyrahost.tools.actor_tools.ActorSpawnTool.execute (existing)
def execute(self, params: dict) -> NyraToolResult:
    # Step 1 — BL-05 idempotency lookup (deduped:True if cached)
    cached = idempotent_lookup(self.name, params)
    if cached is not None:
        return NyraToolResult.ok({**cached, "deduped": True})

    # Step 2 — BL-04 session transaction (Ctrl+Z scope)
    with session_transaction(self.name):
        # ... actual unreal.* calls here ...
        result = do_the_thing(params)

    # Step 3 — BL-06 post-condition verification
    err = verify_post_condition(
        self.name,
        lambda: confirm_world_reflects_change(result),
    )
    if err:
        return NyraToolResult.err(err)

    # Step 4 — BL-05 record success for next dedup hit
    idempotent_record(self.name, params, result)
    return NyraToolResult.ok(result)
```

### Pattern 2: C++ Helper for Unreflected APIs

**What:** When `unreal.*` does not expose a needed symbol, write a minimal `UCLASS(MinimalAPI)` exposing `UFUNCTION(BlueprintCallable, meta=(ScriptMethod))` wrappers.
**When to use:** PARITY-02 Live Coding trigger, PARITY-03 BT EdGraph node spawn, PARITY-05 Niagara module-parameter set, PARITY-07 AnimBP state-machine node spawn.
**Example sketch:**

```cpp
// Source: pattern derived from how UE's own EditorAssetSubsystem reflects
//         to unreal.EditorAssetSubsystem
// File: NyraEditor/Public/ToolHelpers/NyraBTHelper.h
UCLASS(MinimalAPI)
class UNyraBTHelper : public UObject
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Nyra|BT", meta=(ScriptMethod))
    static bool AddCompositeNode(UBehaviorTree* BT, FName CompositeClass, FVector2D NodePos);

    UFUNCTION(BlueprintCallable, Category="Nyra|BT", meta=(ScriptMethod))
    static bool AddDecoratorNode(UBehaviorTree* BT, FName DecoratorClass, FName ParentNodeName);

    UFUNCTION(BlueprintCallable, Category="Nyra|BT", meta=(ScriptMethod))
    static bool SetBlackboardKey(UBlackboardData* BB, FName KeyName, FName KeyType);
};
```

```python
# Source: corresponding Python call site (after engine reflection runs at startup)
import unreal
ok = unreal.NyraBTHelper.add_composite_node(bt, "BTComposite_Sequence", unreal.Vector2D(0, 0))
```

### Pattern 3: Pure Slate Drop-Type Branching

**What:** `OnDrop` inspects the operation's `IsOfType<T>()` to dispatch to the right payload extractor.
**When to use:** PARITY-04 only.
**Example:**

```cpp
// Source: SNyraImageDropZone.cpp:92-104 (existing) + extension for PARITY-04
FReply SNyraImageDropZone::OnDrop(const FGeometry& Geom, const FDragDropEvent& Evt)
{
    bDragOverActive = false;
    Invalidate(EInvalidateWidget::Paint);

    if (TSharedPtr<FDragDropOperation> Op = Evt.GetOperation())
    {
        // Existing path — keep as-is
        if (Op->IsOfType<FAssetDragDropOp>())
        {
            TSharedPtr<FAssetDragDropOp> AssetOp = StaticCastSharedPtr<FAssetDragDropOp>(Op);
            if (AssetOp.IsValid() && AssetOp->GetAssets().Num() > 0)
            {
                // PARITY-04: emit BOTH the path string (for backward compat with
                // OnImageDropped) AND a structured asset chip via OnAssetDropped.
                const FAssetData& Asset = AssetOp->GetAssets()[0];
                if (OnAssetDroppedDelegate.IsBound())
                {
                    OnAssetDroppedDelegate.Execute(Asset);
                    return FReply::Handled();
                }
                // Fallback to legacy path if no asset-handler is wired.
                if (OnImageDroppedDelegate.IsBound())
                {
                    OnImageDroppedDelegate.Execute(Asset.GetObjectPathString());
                    return FReply::Handled();
                }
            }
        }
        // Future: FExternalDragOperation for OS-level files (Phase 8 stretch).
    }
    return FReply::Unhandled();
}
```

### Anti-Patterns to Avoid

- **Hand-rolling PDF parsing.** pypdf 6.11.0 is the standard. Hand-rolling = "deceptively simple" trap (PDF spec is 1000+ pages with edge cases per parser-decade).
- **Silent C extension introduction.** `pypdfium2` (transitive of `pdfplumber`) ships PDFium binaries. Per LOCKED-06, hard C extensions are out — but lxml/Pillow precompiled wheels are in (Windows x64 only is a small QA surface). Document each transitive C dep in Plan 08-01.
- **Re-implementing the mutator shape.** Phase 4 already paid for `session_transaction`/`idempotent_lookup`/`verify_post_condition`. Each PARITY mutator imports them; nothing else.
- **Adding a second drop-target widget.** LOCKED-07. Extend `SNyraImageDropZone`; do not branch into a new `SNyraAssetDropZone` even if it "feels cleaner."
- **Empty `citations` lists in PARITY-06.** T-08-05. If `KbSearchTool` returns `no_index_loaded`, surface the `remediation` string verbatim — never silently emit `citations: []`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF text extraction | Custom regex on PDF byte stream | `pypdf.PdfReader` | PDF spec edge cases (encrypted, malformed xref, image-only, multi-stream) |
| PDF embedded image extraction | Walk `/XObject` dict manually | `pypdf.PdfReader.pages[i].images` (yields `ImageFile`) | Format detection (JPEG/JP2/CCITT) + colour-space conversion |
| DOCX zip extraction | `zipfile` + walk word/document.xml | `python-docx.Document(path)` | Numbering, styles, embedded objects, footnotes |
| PPTX zip extraction | Same as above | `python-pptx.Presentation(path)` | Slide layouts, master slides, notes |
| HTML text extraction | Regex strip tags | `bs4.BeautifulSoup(html, "html.parser").get_text()` | Encoding detection, malformed HTML, script/style stripping |
| `.utrace` parsing | Decode binary frames | Spawn `UnrealInsights.exe -OpenTraceFile=...` headless and parse exported CSV/JSON | Format is engine-internal and changes per UE version (T-08-01 reincarnated for `.utrace`) |
| BT EdGraph node spawn | Ad-hoc `unreal.set_editor_property` calls | C++ helper exposing `MinimalAPI` UCLASS | Graph schema enforcement, dirty tracking, undo capture |
| C++ compile-error parsing | Treat output as opaque blob | Extend `blueprint_debug._ERROR_PATTERNS` with MSVC C\d{4}/clang error: lines | Pattern table is already audit-trailed and maintained |
| Live Coding trigger | Spawn UBT subprocess from Python | `ILiveCodingModule::Compile()` via C++ helper | UBT-from-Python re-builds the whole project; Live Coding is incremental |

**Key insight:** Six of eight Phase 8 plans are **wrappers, not implementations**. The work is plumbing — pick the right primitive, wrap it in the canonical mutator shape, return structured data. Where the primitive is missing (BT/Niagara/AnimBP node spawn), the cost is a 50-line C++ helper, not a re-implementation.

## Runtime State Inventory

> Phase 8 is overwhelmingly greenfield (new tool surfaces). The only "existing state" exposure is PARITY-04 modifying the live `SNyraImageDropZone` widget.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Phase 8 produces no new persistent records (template caches go through Phase 5 StagingManifest per LOCKED-04) | None |
| Live service config | None — no external services touched | None |
| OS-registered state | None — no Windows tasks, no installed services, no PATH entries added | None |
| Secrets/env vars | None — no new env vars introduced | None |
| Build artifacts / installed packages | **YES — Plan 08-01 adds 6 new wheels under `Binaries/Win64/NyraHost/wheels/`**. Plans 08-02/03/05/07/08 may add a `NyraToolHelpers.dll` C++ helper to plugin binaries, **rebuilt per UE version (5.4/5.5/5.6/5.7)** | Plan 08-01 must include "rebuild wheel cache" task; Plans with C++ helpers must rebuild via existing four-version CI matrix (Phase 2 Plan 02-01) |

**Nothing found in any other category — verified by grep over `nyrahost/` for `keyring|task|service|systemd|launchd|nyra_register` (zero matches), and review of `Binaries/Win64/` runtime layout in `NyraEditor.Build.cs:46-69`.**

## Common Pitfalls

### Pitfall 1: UE Python API drift across 5.4 → 5.7 (T-08-01)

**What goes wrong:** A symbol exists in 5.7 but not 5.4 (or vice versa). Tool fails silently with `AttributeError` at first invocation in production.
**Why it happens:** Epic adds and removes Python reflections without changelog entries. `BehaviorTreeFactory` may be `BehaviorTreeFactoryNew` in some versions. `MetaSoundFactory` capitalisation drifted (Aura's docs explicitly call out "5.3 incompatibility" — see PARITY-08 row above).
**How to avoid:** Wave 0 spike per PARITY-{03,05,07,08} runs the symbol-survey script on each UE version, commits results to `symbol-survey-{ue_version}.md`. Each tool's `__init__` does an early `hasattr(unreal, "BehaviorTreeFactory")` check and raises `not_supported_on_this_ue_version` (NyraToolResult.err) at register-time, never at execute-time.
**Warning signs:** Tool works in dev (one UE version) but errors on user's box. Mitigation: the four-version CI matrix from Phase 2 must run the smoke script in every PR that adds a new PARITY tool.

### Pitfall 2: Wheel cache bloat from PDF parsers (T-08-02)

**What goes wrong:** Plan 08-01 adds dependencies, transitive deps balloon, plugin install size grows past Fab limits.
**Why it happens:** `pdfplumber` looks small (60 KB) but pulls `pypdfium2` (multi-MB precompiled binaries). Or `pikepdf` looks compelling for advanced PDF work but pulls qpdf (C library, 30+ MB).
**How to avoid:** Plan 08-01 task list MUST include a measurement task that runs `du -sh Binaries/Win64/NyraHost/wheels/` post-add and asserts <75 MB. **Skip pdfplumber for v1**; pypdf alone covers text + images for the documented Aura parity surface.
**Warning signs:** Lock file grows by >20 MB. Single transitive package >5 MB.

### Pitfall 3: Live Coding reliability across UE versions (T-08-03)

**What goes wrong:** Plan 08-02's `nyra_cpp_recompile` works on UE 5.7 but hangs / corrupts UnrealEditor.exe on UE 5.4 because Live Coding had known-bad version on that release.
**Why it happens:** Live Coding has a multi-year history of patch-cycle regressions per Epic forum threads.
**How to avoid:** Plan 08-02 ships **two compile paths** — `LiveCoding` (preferred) and `HotReload` (fallback). Selection is per-UE-version via a `KNOWN_LIVE_CODING_BAD_VERSIONS` constant gated by the operator's verification step. **Default the unverified versions to HotReload**, not Live Coding (fail-safe). Aura itself acknowledges this in its docs ("C++ can cause compilation issues. If this happens you will need to close Unreal and rebuild in Visual Studio or Rider"). NYRA's "beats" claim is the regex-pattern explanation — not zero-failure compile.
**Warning signs:** Editor process becomes unresponsive after recompile call; `claude` CLI hangs waiting for `nyra_cpp_recompile` reply.

### Pitfall 4: Niagara emitter API GPU vs CPU split (T-08-04)

**What goes wrong:** PARITY-05 plan ships `nyra_niagara_add_emitter` that works on CPU emitters but errors on GPU (because GPU requires shader compile pass).
**Why it happens:** Niagara has parallel API surfaces for CPU and GPU emitters; module-parameter setters may differ.
**How to avoid:** Plan 08-05 success criteria explicitly call out **both paths reproduce**. Test fixtures include a CPU sprite emitter AND a GPU sprite emitter AND a ribbon emitter. Aura's docs already flag custom HLSL modules as the riskier 0.13.7 surface — reproducing the standard sprite + ribbon library is fine.
**Warning signs:** Tool succeeds on simulation-target=CPU but errors on simulation-target=GPU.

### Pitfall 5: Empty `citations` from PARITY-06 (T-08-05)

**What goes wrong:** `nyra_perf_explain_hotspot` calls `KbSearchTool.execute(...)`, gets `status: no_index_loaded` (because user never downloaded the UE5 corpus), and silently emits `citations: []`. Demo screen shows no citations and the "beats Aura" claim collapses.
**Why it happens:** `KbSearchTool` returns `ok` with `status: no_index_loaded` (not `err`) — a Phase 3 design choice for graceful degradation. PARITY-06 must explicitly handle the `no_index_loaded` branch.
**How to avoid:** Plan 08-06 task list includes a "treat no_index_loaded as actionable" sub-task. The tool's output schema includes `citations_status: ok | no_index_loaded` and surfaces the remediation string as `citations_remediation` when no index is loaded. The demo recording for Phase 8 verification includes a step that downloads the index *before* running the perf demo.
**Warning signs:** Demo run on a fresh-install machine produces empty citations.

### Pitfall 6: Drag-from-Content-Browser payload format drift (T-08-06)

**What goes wrong:** `FAssetDragDropOp` payload format changed between UE 5.4 and 5.6 (per CONTEXT.md); PARITY-04 implementation works on 5.6 but `AssetOp->GetAssets()` returns empty on 5.4.
**Why it happens:** Slate APIs have minor breakage per UE release; `FAssetData` shape itself has shifted (e.g., `ObjectPath` deprecated for `GetObjectPathString()` somewhere in the 5.x series).
**How to avoid:** Plan 08-04 includes a Wave 0 four-version-matrix smoke test (UE 5.4/5.5/5.6/5.7) that drops a known asset onto the chat composer and asserts the chip renders with the right path. Use the existing `Phase 2 Plan 02-01` four-version CI runner. Keep the existing `IsOfType<FAssetDragDropOp>()` check (already works in current `OnDrop`); add a per-version branch only if the survey shows divergence.
**Warning signs:** Chip renders empty on one UE version but not another.

### Pitfall 7: Embedded-image extraction colour-space confusion (PARITY-01)

**What goes wrong:** A PDF embeds a CMYK JPEG; pypdf yields the image but Pillow/Claude vision misinterprets the colour space; the user uploads a "game design doc" with cover art and the agent describes wrong colours.
**Why it happens:** PDF supports JPEG with non-RGB colour spaces (CMYK, Lab, indexed). pypdf returns the raw bytes; Pillow can decode but conversion to RGB is the caller's job.
**How to avoid:** Embedded-image extractor in `extractors/pdf.py` MUST round-trip every extracted image through `PIL.Image.convert("RGB")` before passing to `attachments.ingest_attachment`. Skip images smaller than 64x64 px (likely UI icons, not content).
**Warning signs:** "Describe this slide" returns hallucinated colour palette.

## Code Examples

Verified patterns from existing NYRA codebase:

### PARITY-01 PDF text + image extraction skeleton

```python
# Source: pattern from nyrahost.attachments.ingest_attachment (existing)
#         + pypdf 6.11.0 reader API [VERIFIED: pypi.org/pypi/pypdf 2026-05-10]
from pathlib import Path
from typing import Tuple
import io
from PIL import Image
from pypdf import PdfReader
from nyrahost.attachments import ingest_attachment, AttachmentRef

def extract_pdf(
    pdf_path: Path,
    *,
    project_saved: Path,
) -> Tuple[str, list[AttachmentRef]]:
    """Return (concatenated_text, [embedded_image_refs])."""
    reader = PdfReader(str(pdf_path))
    text_chunks: list[str] = []
    image_refs: list[AttachmentRef] = []

    for page_num, page in enumerate(reader.pages):
        text_chunks.append(page.extract_text() or "")
        # pypdf 6.x: each page has .images yielding ImageFile objects.
        for img in page.images:
            try:
                pil = Image.open(io.BytesIO(img.data)).convert("RGB")
                if pil.width < 64 or pil.height < 64:
                    continue  # skip icon-size noise
                tmp = project_saved / "NYRA" / "tmp" / f"pdf_p{page_num}_{img.name}.png"
                tmp.parent.mkdir(parents=True, exist_ok=True)
                pil.save(tmp, format="PNG")
                ref = ingest_attachment(tmp, project_saved=project_saved)
                image_refs.append(ref)
            finally:
                tmp.unlink(missing_ok=True)

    return "\n\n".join(text_chunks), image_refs
```

### PARITY-02 C++ compile-error pattern extension

```python
# Source: extends blueprint_debug._ERROR_PATTERNS (existing structure)
import re

_CPP_ERROR_PATTERNS: list[tuple[re.Pattern, str, str | None]] = [
    (
        re.compile(r"error C(?P<code>\d{4}):\s+(?P<msg>.+)$", re.IGNORECASE),
        "MSVC compile error C{code}: {msg}.",
        "Open the .cpp file at the indicated line; check missing #include or syntax.",
    ),
    (
        re.compile(r"error:\s+use of undeclared identifier '(?P<sym>[^']+)'", re.IGNORECASE),
        "Clang: '{sym}' is referenced but no declaration is in scope.",
        "Add the right #include or forward declaration; verify the class is exported with the *_API macro.",
    ),
    (
        re.compile(r"LINK\s*:\s*fatal error LNK(?P<code>\d{4}):\s+(?P<msg>.+)$", re.IGNORECASE),
        "Link error LNK{code}: {msg}. Likely a missing module dependency or unresolved symbol.",
        "Add the missing module to your .Build.cs PublicDependencyModuleNames or PrivateDependencyModuleNames.",
    ),
    (
        re.compile(r"UnrealHeaderTool failed", re.IGNORECASE),
        "UHT failed parsing your reflection macros.",
        "Check UCLASS/UFUNCTION/UPROPERTY macro syntax; UHT errors include line numbers in preceding output.",
    ),
]
# Plan 08-02 extends blueprint_debug._ERROR_PATTERNS list with these entries
# (or factors them into a shared list). The matching loop is identical.
```

### PARITY-04 Slate drop extension (header)

```cpp
// Source: extension of SNyraImageDropZone.h
DECLARE_DELEGATE_OneParam(FOnNyraAssetDropped, const FAssetData& /*Asset*/);

class NYRAEDITOR_API SNyraImageDropZone : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SNyraImageDropZone) {}
        SLATE_EVENT(FOnNyraImageDropped, OnImageDropped)
        SLATE_EVENT(FOnNyraAssetDropped, OnAssetDropped)   // PARITY-04 NEW
    SLATE_END_ARGS()
    // ... existing members ...
private:
    FOnNyraImageDropped OnImageDroppedDelegate;
    FOnNyraAssetDropped OnAssetDroppedDelegate;             // PARITY-04 NEW
};
```

### PARITY-06 stat read + KB cite

```python
# Source: composes Phase 2 Plan 02-10 nyra_console_exec
#         + Phase 2 Plan 02-11 nyra_output_log_tail
#         + Phase 3 KbSearchTool
from nyrahost.tools.kb_search import KbSearchTool
from nyrahost.tools.base import NyraTool, NyraToolResult

class PerfExplainHotspotTool(NyraTool):
    name = "nyra_perf_explain_hotspot"
    parameters = {
        "type": "object",
        "properties": {
            "hotspot_label": {"type": "string"},
            "hotspot_metric": {"type": "string"},
        },
        "required": ["hotspot_label"],
    }

    def __init__(self) -> None:
        super().__init__()
        self._kb = KbSearchTool()

    def execute(self, params: dict) -> NyraToolResult:
        label = params["hotspot_label"]
        # Build query — heuristic: "<label> performance optimization UE5"
        query = f"{label} performance optimization Unreal Engine 5"
        kb_result = self._kb.execute({"query": query, "limit": 3, "min_score": 0.3})
        if kb_result.error:
            return NyraToolResult.err(kb_result.error)
        kb = kb_result.data or {}
        # T-08-05 — graceful degrade for missing index
        if kb.get("status") == "no_index_loaded":
            return NyraToolResult.ok({
                "hotspot_label": label,
                "explanation": "Hotspot identified; UE5 docs index not loaded.",
                "citations": [],
                "citations_status": "no_index_loaded",
                "citations_remediation": kb.get("remediation"),
            })
        citations = [r["source_path"] for r in kb.get("results", [])]
        return NyraToolResult.ok({
            "hotspot_label": label,
            "explanation": _compose_explanation(label, kb["results"]),
            "citations": citations,
            "citations_status": "ok",
        })
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `PyPDF2` | `pypdf` (rebrand of same project) | 2022 (PyPDF2 unmaintained) | Use `pypdf` — `PyPDF2` is deprecated |
| pypdf `extract_text()` page-by-page | pypdf 5.x+ supports inline image walk via `page.images` | pypdf 5.0 (2024) | Single-pass extraction; do not iterate XObject manually |
| Hot Reload | Live Coding | UE 4.22+ Live Coding shipped, became default in 5.0 | Faster but less reliable than Hot Reload (T-08-03) |
| Insights via in-editor "Trace > Insights" menu | Insights via standalone `UnrealInsights.exe -OpenTraceFile=...` | UE 5.0 (Insights became standalone exe) | Out-of-process parsing path is the supported one |
| MetaSounds via Editor UI | `UMetaSoundBuilderSubsystem` (5.3+) Python-reflected | UE 5.3 | Plan 08-08 uses the builder subsystem, not the EdGraph |

**Deprecated/outdated:**
- `PyPDF2` package name → use `pypdf`
- `EditorLevelLibrary.get_actor_reference()` → already worked-around in `actor_tools.py:43-64` via `EditorActorSubsystem.get_actor_reference()` fallback. PARITY-* tools should follow the same defensive pattern when adopting `unreal.*` symbols.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `unreal.BehaviorTreeFactory` exists across UE 5.4–5.7 | Standard Stack PARITY-03 row | PARITY-03 spike fails; need to add a C++ helper for asset creation as well. Mitigation: Wave 0 symbol-survey spike |
| A2 | `unreal.NiagaraSystemFactoryNew` exists across UE 5.4–5.7 | Standard Stack PARITY-05 row | Same; same mitigation |
| A3 | `unreal.AnimBlueprintFactory` exists across UE 5.4–5.7 | Standard Stack PARITY-07 row | Same; same mitigation |
| A4 | `unreal.MetaSoundFactory` capitalisation across 5.4–5.7 | Standard Stack PARITY-08 row | If actual name is `unreal.MetasoundFactory` (no caps), the import fails at register-time; smoke test catches this. Aura's docs imply 5.4+ supports it |
| A5 | `unreal.MetaSoundBuilderSubsystem` is reflected and stable | Standard Stack PARITY-08 row | Plan 08-08 needs to fall back to a thicker C++ helper. Aura's docs mention the builder subsystem indirectly via "Wave Player node assignment issues" which implies the API is reachable |
| A6 | `ILiveCodingModule::Compile()` is callable from a thin C++ helper exposed to Python | Standard Stack PARITY-02 row | If not, fall back to UBT subprocess (slower, requires editor restart). Aura openly admits this fallback in its docs |
| A7 | `.utrace` files are best parsed by spawning `UnrealInsights.exe -OpenTraceFile=` and extracting CSV | Don't Hand-Roll table | If `UnrealInsights.exe` lacks a headless export mode, PARITY-06 must reduce scope to `stat unit` + log-tail parsing only and explicitly mark `.utrace` parsing as PENDING. The "Aura beats" claim shifts to "stat hotspot + docs citation" only |
| A8 | Pillow + lxml precompiled wheels on Windows x64 are accepted under LOCKED-06 | Standard Stack PARITY-01 row | If user reads LOCKED-06 strictly as "no compiled code at all", we must drop python-docx/pptx and build a custom XML walker. **Recommend planner explicitly clarifies LOCKED-06 in plan check** — current reading is "no platform-fragmented native deps", not "zero compiled code anywhere" |
| A9 | Wheel-cache total estimate ~9.1 MB | PARITY-01 wheel-cache budget table | If real total exceeds 25 MB, plan shape unchanged but Plan 08-01 verification step is more important. T-08-02 ceiling is 75 MB; we have 8x headroom |
| A10 | `FAssetDragDropOp::GetAssets()` returns `TArray<FAssetData>` across UE 5.4–5.7 | PARITY-04 Code Examples | If shape changed, four-version matrix smoke test catches it. CONTEXT.md T-08-06 already calls out this risk |
| A11 | Pure-Python `markdown` 3.10.2 + `bs4` covers HTML extraction needs | PARITY-01 Standard Stack | If user inputs heavily-styled HTML where bs4's `html.parser` mis-decodes, fallback to lxml parser (already a transitive dep) |
| A12 | Aura's documented capabilities in this research session match v0.13.7+ public docs | All §1–§8 parity bars | If Aura updates docs between 2026-05-10 and Phase 8 ship, parity bar shifts. Mitigation: re-fetch tryaura.dev/documentation at Phase 8 EXIT-GATE check |

**12 assumptions logged.** Per planner discipline, A1–A6 are blockers for their respective plans (Wave 0 spike resolves them); A7 is a scope-narrowing risk for PARITY-06; A8 is a planner-clarification ask; A9–A12 are low-risk confirmations.

## Open Questions (RESOLVED — 2026-05-10)

All four questions resolved per plan-checker B1 finding. Per-question disposition below; no question remains gating phase planning.

1. **(DEFERRED-TO-WAVE-0)** **Does `UMetaSoundBuilderSubsystem` Python reflection cover node-graph mutation operations needed for `nyra_metasound_add_node` + `nyra_metasound_connect`?**
   - **Disposition:** Resolved by Plan 08-08 Wave 0 symbol-survey task (per `08-08-metasounds-audio-PLAN.md` Task 0). The plan accepts that the answer is unknown until the spike runs; Plan 08-08 frontmatter `autonomous: false` reflects the dependency on Wave 0.
   - **Fallback if Wave 0 reveals no Python reflection:** Plan 08-08 reduces scope to `nyra_metasound_create` only (one tool, not three). Documented inline in 08-08 acceptance-criteria as a tier-1 fallback.

2. **(DEFERRED-TO-WAVE-0)** **Can `UnrealInsights.exe` produce CSV/JSON output non-interactively?**
   - **Disposition:** Resolved by Plan 08-06 Wave 0 task (`UnrealInsights.exe -?` per UE version). Plan 08-06 frontmatter `autonomous: false` for the executor-bench step.
   - **Fallback if headless mode unavailable:** Plan 08-06 reduces scope to `nyra_perf_stat_read` (log-tail-based) — drops `.utrace` file ingestion. Documented inline in 08-06 per A7. The LOCKED-05 KB-citation claim still holds for the reduced scope.

3. **(RESOLVED — extend `SNyraAttachmentChip`)** **For PARITY-04's drag from Content Browser: new `SNyraAssetChip` widget or variant of `SNyraAttachmentChip`?**
   - **Disposition:** Extend `SNyraAttachmentChip`. Plan 08-04 explicitly takes the LOCKED-07-aligned path (one chip codepath, like one drop-target codepath). The existing standalone `SNyraAssetChip.cpp` is verified by Grep to be UNUSED in the chat composer (it lives in the editor module but isn't bound to `SNyraComposer`); leaving it untouched.
   - **Implication:** No new widget files. `FNyraAttachmentRef` enum gains an `Asset` variant alongside the `Document` variant added by 08-01 — both committed in plan-number order per LOCKED-10 (added below).

4. **(RESOLVED — out of Phase 8 scope; tracked for Phase 9 marketing copy)** **Does Aura's "alpha" caveat on BT Agent + AnimBP + Metasounds give NYRA's mutator-shape "beats" claim more headroom than CONTEXT.md anticipated?**
   - **Disposition:** Yes, but the headroom belongs to Phase 9 (Fab Launch Prep) marketing copy, not Phase 8 implementation. Phase 8 plans ship the same shape regardless of how Aura is positioned at submission day.
   - **Action:** Phase 9 Fab listing copy task (TBD when Phase 9 plans land) re-reads `tryaura.dev/documentation` as of Fab-submission day and adjusts NYRA's "matches" → "beats" wording per latest Aura caveats. Tracked here as a Phase 9 dependency, not a Phase 8 blocker.

## Environment Availability

> Phase 8 has external-tool dependencies on the developer side (PyPI install of doc parsers, Visual Studio for Live Coding, UnrealInsights.exe runtime) and on the operator side (UE 5.4/5.5/5.6/5.7 installations).

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| PyPI (pypi.org) | Plan 08-01 wheel build | ✓ | live | Bundled wheels under `Binaries/Win64/NyraHost/wheels/` (D-14 contract) — no runtime PyPI fetch |
| `pypdf` 6.11.0 | PARITY-01 | ✓ on PyPI | 6.11.0 | None — REQUIRED |
| `python-docx` 1.2.0 | PARITY-01 | ✓ on PyPI | 1.2.0 | None — REQUIRED |
| `python-pptx` 1.0.2 | PARITY-01 | ✓ on PyPI | 1.0.2 | None — REQUIRED |
| `openpyxl` 3.1.5 | PARITY-01 | ✓ on PyPI | 3.1.5 | None — REQUIRED |
| `markdown` 3.10.2 | PARITY-01 | ✓ on PyPI | 3.10.2 | stdlib `html.parser` for naïve fallback (degraded markdown handling) |
| `beautifulsoup4` | PARITY-01 | ✓ on PyPI | latest 4.x | stdlib `html.parser` (degraded HTML handling) |
| Visual Studio 2022 + UE workload | PARITY-02 Live Coding | OPERATOR-DEP — not on dev box | — | UnrealBuildTool subprocess (slower, requires editor restart). Operator runs PARITY-02 verification on Windows box per existing pattern (Phase 1 Plan 01-15) |
| `UnrealInsights.exe` (UE-bundled) | PARITY-06 | OPERATOR-DEP | UE 5.4+ | Reduce PARITY-06 scope to `stat unit` + log-tail (skip `.utrace`) per A7 |
| UE 5.4 / 5.5 / 5.6 / 5.7 installs | PARITY-02..08 verification | OPERATOR-DEP — only one UE version locally | — | Four-version CI matrix from Phase 2 Plan 02-01 covers automated verification; manual verification per Phase 1 ring0-run-instructions.md pattern |

**Missing dependencies with no fallback:** None at planning time. All hard deps are PyPI-resolvable.

**Missing dependencies with fallback:** PARITY-06 `.utrace` parsing degrades to log-only if `UnrealInsights.exe` headless mode unavailable. PARITY-02 Live Coding degrades to UBT subprocess if `ILiveCodingModule::Compile()` not reachable.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio (asyncio_mode=auto) — confirmed `pyproject.toml:47-49` |
| Config file | `TestProject/Plugins/NYRA/Source/NyraHost/pyproject.toml` |
| Quick run command | `pytest tests/ -x -q -m "not integration"` (run from `NyraHost/`) |
| Full suite command | `pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PARITY-01 | PDF text + image extraction | unit | `pytest tests/test_extractors_pdf.py -x` | ❌ Wave 0 |
| PARITY-01 | DOCX text + image extraction | unit | `pytest tests/test_extractors_docx.py -x` | ❌ Wave 0 |
| PARITY-01 | PPTX / XLSX / HTML / MD extraction | unit | `pytest tests/test_extractors_others.py -x` | ❌ Wave 0 |
| PARITY-01 | Wheel-cache size assertion | smoke | `pytest tests/test_wheel_cache_budget.py -x` | ❌ Wave 0 |
| PARITY-02 | C++ module/class/function generation (file IO only) | unit | `pytest tests/test_cpp_authoring.py -x` | ❌ Wave 0 |
| PARITY-02 | Compile-error pattern matching (extends `_ERROR_PATTERNS`) | unit | `pytest tests/test_cpp_error_patterns.py -x` | ❌ Wave 0 |
| PARITY-02 | Live Coding trigger (with mocked `unreal.NyraLiveCodingHelper`) | unit | `pytest tests/test_cpp_recompile_mock.py -x` | ❌ Wave 0 |
| PARITY-02 | Live Coding integration | manual-only | operator-run on Windows + UE | n/a (operator-run) |
| PARITY-03 | BT JSON schema validation + parameter validation | unit | `pytest tests/test_bt_authoring.py -x` | ❌ Wave 0 |
| PARITY-03 | Symbol availability survey | smoke (operator-run) | `pytest tests/test_unreal_symbols_bt.py -x` (skip on no-unreal) | ❌ Wave 0 |
| PARITY-03 | BT EdGraph node spawn | manual-only | operator-run | n/a |
| PARITY-04 | Drop payload routing logic (mocked Slate) | manual-only | operator-run on each of UE 5.4/5.5/5.6/5.7 | n/a — UE-side Slate |
| PARITY-05 | Niagara JSON schema + parameter validation | unit | `pytest tests/test_niagara_authoring.py -x` | ❌ Wave 0 |
| PARITY-05 | GPU + CPU emitter creation | manual-only | operator-run | n/a |
| PARITY-06 | Stat-line parsing (regex over `stat unit` text) | unit | `pytest tests/test_perf_stat_parse.py -x` | ❌ Wave 0 |
| PARITY-06 | KbSearchTool citations populated, `no_index_loaded` graceful | unit | `pytest tests/test_perf_kb_cite.py -x` | ❌ Wave 0 |
| PARITY-06 | `.utrace` parsing | manual-only | operator-run | n/a |
| PARITY-07 | AnimBP JSON schema + parameter validation | unit | `pytest tests/test_animbp_authoring.py -x` | ❌ Wave 0 |
| PARITY-07 | State machine + transition node spawn | manual-only | operator-run | n/a |
| PARITY-08 | Metasound JSON schema + parameter validation | unit | `pytest tests/test_metasound_authoring.py -x` | ❌ Wave 0 |
| PARITY-08 | Builder subsystem mutation | manual-only | operator-run | n/a |

### Sampling Rate

- **Per task commit:** `pytest tests/test_<plan>_*.py -x -q` (specific plan's tests)
- **Per wave merge:** `pytest tests/ -x -q -m "not integration"` (full unit suite)
- **Phase gate:** Full suite green + operator-run manual-verification per plan (per Phase 1 Plan 01-15 / Phase 4 04-05 pattern: `*-VERIFICATION.md` per plan with PLACEHOLDER cells until operator runs)

### Wave 0 Gaps

- [ ] `tests/test_extractors_pdf.py` — covers PARITY-01 (PDF)
- [ ] `tests/test_extractors_docx.py` — covers PARITY-01 (DOCX)
- [ ] `tests/test_extractors_others.py` — covers PARITY-01 (PPTX/XLSX/HTML/MD)
- [ ] `tests/test_wheel_cache_budget.py` — covers PARITY-01 (T-08-02 fail-loud at 75 MB)
- [ ] `tests/test_cpp_authoring.py` — covers PARITY-02 (file IO only)
- [ ] `tests/test_cpp_error_patterns.py` — covers PARITY-02 (regex extension)
- [ ] `tests/test_cpp_recompile_mock.py` — covers PARITY-02 (mocked unreal module)
- [ ] `tests/test_bt_authoring.py` — covers PARITY-03 (mocked unreal)
- [ ] `tests/test_unreal_symbols_bt.py` — covers PARITY-03 (operator-run, skip on no-unreal)
- [ ] `tests/test_niagara_authoring.py` — covers PARITY-05 (mocked unreal)
- [ ] `tests/test_perf_stat_parse.py` — covers PARITY-06 (`stat unit` regex)
- [ ] `tests/test_perf_kb_cite.py` — covers PARITY-06 (LOCKED-05 + T-08-05)
- [ ] `tests/test_animbp_authoring.py` — covers PARITY-07 (mocked unreal)
- [ ] `tests/test_metasound_authoring.py` — covers PARITY-08 (mocked unreal)
- [ ] Test fixtures: `tests/fixtures/sample.pdf` (with embedded image), `sample.docx`, `sample.pptx`, `sample.xlsx`, `sample.html`, `sample.md`, `sample_stat_unit.txt`, `sample_compile_error.txt`

Mocked-`unreal` pattern: existing tests under `tests/test_attachments.py` and others demonstrate the import-guard pattern; reuse it here. Tests should never require an actual UE editor.

## Security Domain

> `security_enforcement` is not explicitly disabled in `.planning/config.json`, so per default the section is included. Phase 8 surfaces touch user input (chat attachments) and disk paths — security review applies.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase 8 surfaces are local-loopback only; no auth boundary |
| V3 Session Management | no | Same |
| V4 Access Control | partial | PARITY-02 file write surface MUST stay inside the UE project's `Source/<ModuleName>/` tree — prevent path traversal via `pathlib.Path.resolve()` + parent-prefix check (matches existing `attachments.py:127-155` pattern) |
| V5 Input Validation | yes | Every PARITY tool defines a JSON schema (`parameters` field on the `NyraTool` subclass); MCP server enforces. Validate `path` parameters with the same blocklist as `attachments._PATH_BLOCKLIST` |
| V6 Cryptography | no | No crypto in Phase 8 surface |

### Known Threat Patterns for {NyraHost Python sidecar / NyraEditor C++}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via tool params (e.g., `nyra_cpp_module_create` writes to `../../../etc/`) | Tampering | Apply `attachments._PATH_BLOCKLIST` + `Path.resolve(strict=True)` + parent-prefix check; reject if path doesn't start with the project's `Source/` dir |
| Symlink attachment trick (PDF that's a symlink to ~/.ssh/id_rsa) | Information Disclosure | Already mitigated in `attachments.ingest_attachment` lines 131-140; reuse helper for embedded image flow |
| Malicious PDF zip-bomb / billion-laughs (DOCX/PPTX are zip files) | Denial of Service | Pre-check archive total uncompressed size before extracting (cap at 100 MB per attachment); reject XML with `>1000` nested entities |
| C++ source file with `#include <Windows.h>` + linker side-effects | Tampering | PARITY-02 module-create template is fixed; user-prompted code generation goes through Claude Code's existing review-before-apply flow (no new threat surface) |
| Embedded JavaScript in PDF (yes — PDFs can contain JS) | Tampering | pypdf 6.x does NOT execute JS; surface only text + images. Document explicitly in PARITY-01 README |
| `.utrace` file from untrusted source crashes UnrealInsights.exe | Denial of Service | Reject `.utrace` paths outside project `Saved/Profiling/`; UnrealInsights is sandboxed by Windows process isolation already |

## Sources

### Primary (HIGH confidence)
- **Codebase grep (HIGH):**
  - `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/base.py` (Phase 4 mutator helpers)
  - `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/blueprint_debug.py` (`_ERROR_PATTERNS` regex list, lines 33-91)
  - `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/actor_tools.py` (canonical mutator example)
  - `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/material_tools.py` (canonical reader+mutator)
  - `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/kb_search.py` (LOCKED-05 dependency)
  - `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/attachments.py` (PARITY-01 base)
  - `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraImageDropZone.cpp` (PARITY-04 base, current state already inspects `FAssetDragDropOp`)
  - `TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraComposer.h` (PARITY-04 endpoint)
  - `TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs` (already declares Slate/SlateCore/UnrealEd dependencies — PARITY-04 needs no new module deps)
  - `TestProject/Plugins/NYRA/Source/NyraHost/pyproject.toml` (PyPI deps current)
- **PyPI metadata (HIGH):** [pypi.org/pypi/{pypdf,python-docx,python-pptx,openpyxl,pdfplumber,markdown}/json] — fetched 2026-05-10

### Secondary (MEDIUM confidence)
- **Aura docs (MEDIUM):** `tryaura.dev/documentation` — fetched 2026-05-10. Sub-pages confirmed accessible: `/documentation/coding-agent-cpp/`, `/documentation/vfx-agent/`, `/documentation/audio/`, `/documentation/performance-profiling`, `/documentation/behavior-trees/`. Used to set parity bar per feature.

### Tertiary (LOW confidence — flagged for validation)
- **UE Python API symbols (LOW):** UE official docs at `docs.unrealengine.com` and `dev.epicgames.com` are Cloudflare-gated; WebFetch returns HTTP 403/redirect. Symbol claims (BehaviorTreeFactory, NiagaraSystemFactoryNew, AnimBlueprintFactory, MetaSoundFactory, MetaSoundBuilderSubsystem, ILiveCodingModule) are **[ASSUMED]** from prior NYRA codebase patterns (`actor_tools.py` cites the `EditorActorSubsystem.get_actor_reference` workaround pattern as Phase 4 BL-07 — same approach applies here). Each plan's Wave 0 spike resolves the assumption per UE version.
- **`.utrace` headless export (LOW):** No source verified; A7 in Assumptions Log marks this as scope-narrowing risk for PARITY-06.

## Metadata

**Confidence breakdown:**
- Standard stack PARITY-01 (doc parsers): HIGH — versions verified from PyPI 2026-05-10
- Standard stack PARITY-02 (Live Coding): MEDIUM — pattern confirmed but specific symbols `[ASSUMED]`
- Standard stack PARITY-03/05/07/08 (UE Python authoring): MEDIUM-LOW — Wave 0 spike per plan resolves
- Architecture (Phase 4 reuse): HIGH — direct codebase confirmation
- Architecture (PARITY-04 Slate extension): HIGH — direct codebase confirmation; current `OnDrop` already 80% there
- Pitfalls: MEDIUM-HIGH — synthesized from CONTEXT.md threats T-08-01..06 + Aura's own documented limitations
- Aura parity bar: MEDIUM — Aura docs accessible 2026-05-10; bar may shift if Aura updates docs before Phase 8 ship

**Research date:** 2026-05-10
**Valid until:** 2026-06-10 (30 days for stable; re-fetch tryaura.dev/documentation at Phase 8 EXIT-GATE)

---

## SHARED PATTERNS — Cross-Plan Concerns

These cross-cutting concerns let the planner batch implementation across plans where appropriate.

### Shared Pattern 1: PARITY-01 feeds existing `attachments.py` ingest pipeline (no parallel codepaths)

The existing pipeline:
1. UE side: `SNyraComposer.HandleAttachClicked` → `FDesktopPlatform OpenFileDialog` → `[+]` adds `FNyraAttachmentRef` to `ChipsRow`
2. UE side: User submits → `OnSubmit(Text, Attachments[])` → JSONRPC to NyraHost
3. NyraHost: For each attachment, calls `attachments.ingest_attachment(src, project_saved=...)` → returns `AttachmentRef` with content-addressed dedup path under `<ProjectSaved>/NYRA/attachments/<sha[:2]>/<sha>.<ext>`
4. NyraHost routes `image` kind into Claude vision; `text` kind concatenates to prompt; `video` kind into video pipeline (Phase 7)

PARITY-01 inserts at step 3:

```python
# in NyraHost dispatch — pseudo-code
ext = src.suffix.lower()
if ext in {".pdf", ".docx", ".pptx", ".xlsx", ".html", ".htm", ".md"}:
    text, image_refs = extractors.dispatch(ext, src, project_saved=...)
    # text becomes a `text` AttachmentRef (write to .txt under attachments/)
    # image_refs are already AttachmentRef objects of `image` kind via embedded extraction
    # Both flow through normal pipeline — vision routing for images is automatic
```

**Net new code:** `extractors/` package + a single dispatch function. No changes to `attachments.ingest_attachment`. The vision routing pipeline is unchanged.

### Shared Pattern 2: PARITY-02 extends `nyra_blueprint_debug` regex surface (one shared list, not parallel)

`blueprint_debug.py:33-91` defines `_ERROR_PATTERNS` as `list[tuple[re.Pattern, str, str | None]]` — pattern, plain-English explanation template, suggested-fix template.

PARITY-02 extends in one of two shapes (planner picks):

**Option A (simpler — recommended):** Append C++ patterns directly to `_ERROR_PATTERNS`. The matcher loop (`_explain_error_pattern` lines 99-130) doesn't care about source language — it returns the first match. Risk: a Blueprint error log containing the literal string "error C2065" could spuriously match the MSVC pattern. Risk is theoretical (Blueprint logs don't emit MSVC error codes).

**Option B (cleaner — slight refactor):** Promote `_ERROR_PATTERNS` from module-private list to a registry: `_BP_PATTERNS`, `_CPP_PATTERNS`. The matcher takes a language hint. PARITY-02 ships `_CPP_PATTERNS`. Risk: refactor touches Phase 4 file ([read carefully under LOCKED-08 scope discipline]).

**Recommendation:** Option A in Plan 08-02. Cleaner semantically, but Option B refactor is out-of-scope under LOCKED-08 (don't break Phase 4 in Phase 8). If reviewers flag the false-match risk during Plan-Check, escalate to a follow-up cleanup plan in Phase 9 backlog.

### Shared Pattern 3: PARITY-03/05/07/08 reuse Phase 4 mutator shape verbatim

Each of these plans is a Python file under `nyrahost/tools/` with `class Foo(NyraTool): ...`. Each tool's `execute` method follows Pattern 1 above. **No new helpers; no new abstractions.** The `session_transaction` no-ops cleanly when `unreal` is unimported (i.e. in pytest), so test files can drive these tools without a UE editor — the same pattern `actor_tools.py` and `material_tools.py` already use.

C++ helpers (per Pattern 2) live under `NyraEditor/Public/ToolHelpers/` and reflect via `unreal.NyraBTHelper.add_composite_node(...)` etc. Engine startup picks them up automatically because they live in an editor-loading-phase module.

### Shared Pattern 4: PARITY-06 integrates `KbSearchTool` for citations (LOCKED-05) with graceful `no_index_loaded` fallback (T-08-05)

Skeleton in PARITY-06 Code Examples above. Key invariants:

1. `nyra_perf_explain_hotspot` instantiates `KbSearchTool` once per tool instance (not per call) and caches it (matches `kb_search.py` cache-on-instance pattern).
2. Output schema MUST include both `citations: list[str]` (LOCKED-05) AND `citations_status: "ok" | "no_index_loaded"` (T-08-05).
3. When `no_index_loaded`, the `citations` list is `[]` AND a sibling `citations_remediation` field surfaces the verbatim remediation string from KbSearchTool. Demo / verification path MUST run with the index loaded; absence is a flag, not a silent failure.
4. Same pattern reusable for any future "explain X" tool that wants to cite UE5 docs. No new helper required.

### Shared Pattern 5: PARITY-04 modifies the chat composer flow at exactly two surfaces

1. `SNyraImageDropZone` adds an `OnAssetDropped` slate event (header) + an `IsOfType<FAssetDragDropOp>()` branch in `OnDrop` (cpp). Existing image-path emission is preserved as fallback for backward compat.
2. `SNyraChatPanel` (or whichever parent currently holds the drop zone — the planner's Wave 0 grep step confirms) wires `OnAssetDropped` to `SNyraComposer.AddAttachment(...)` with a new `FNyraAttachmentRef` kind: `Asset` (asset path string + asset class name).

**No NyraHost-side change** for PARITY-04. The asset path + class arrive in the JSONRPC payload as fields on the existing attachment shape. NyraHost decides whether to read the asset's bytes or just emit the path string in prompt context — that decision is per-tool, not per-payload.

The chat composer flow is unchanged for non-asset attachments (LOCKED-08: backward compatibility maintained). Plan 08-04 four-version smoke test (T-08-06 mitigation) covers the actual breakage risk surface.

---

*End of RESEARCH.md*
