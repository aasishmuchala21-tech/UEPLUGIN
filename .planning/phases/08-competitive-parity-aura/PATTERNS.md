# Phase 8: Competitive Parity vs Aura — Pattern Map

**Mapped:** 2026-05-10
**Files analyzed:** 8 plans (PARITY-01..08); 1 Slate widget extension; ~20 new MCP tools
**Analogs found:** 8 / 8 (every Phase 8 plan has a strong intra-repo analog)

## File Classification

| New / Modified File | Plan | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|---|
| `nyrahost/attachments.py` (extend) + `nyrahost/document_extractors.py` (NEW) | 08-01 | service/utility | file-I/O + transform | `nyrahost/attachments.py` (self) | exact (extension) |
| `nyrahost/tools/cpp_authoring_tools.py` (NEW) | 08-02 | MCP tool (mutator) | request-response + file-I/O | `nyrahost/tools/blueprint_tools.py` + `blueprint_debug.py` | exact |
| `nyrahost/tools/bt_tools.py` (NEW) | 08-03 | MCP tool (mutator) | CRUD | `nyrahost/tools/actor_tools.py` (ActorSpawnTool — canonical BL-04/05/06 shape) | exact |
| `NyraEditor/.../SNyraImageDropZone.{h,cpp}` (extend) | 08-04 | Slate widget | event-driven | self (LOCKED-07) | exact (extension) |
| `nyrahost/tools/niagara_tools.py` (NEW) | 08-05 | MCP tool (mutator) | CRUD + asset-create | `nyrahost/tools/material_tools.py` (MaterialCreateMICTool / MaterialSetParamTool) | exact |
| `nyrahost/tools/perf_tools.py` (NEW) | 08-06 | MCP tool (read-only) | request-response + RAG | `nyrahost/log_tail.py` + `nyrahost/tools/kb_search.py` | role-match (compose) |
| `nyrahost/tools/animbp_tools.py` (NEW) | 08-07 | MCP tool (mutator) | CRUD | `nyrahost/tools/actor_tools.py` (ActorSpawnTool) | exact |
| `nyrahost/tools/metasound_tools.py` (NEW) | 08-08 | MCP tool (mutator) | CRUD + asset-create | `nyrahost/tools/material_tools.py` | exact |

---

## Canonical Phase 4 Mutator Shape (MUST-USE per LOCKED-03)

**Source of truth:** `nyrahost/tools/actor_tools.py:78-170` (`ActorSpawnTool.execute`).
**All Phase 8 mutator tools (08-02, 08-03, 08-05, 08-07, 08-08) MUST be a copy-rename of this shape.**

Phase 4 helpers imported from `nyrahost.tools.base`:

| Helper | Defined at | What it does | When the new tool calls it |
|---|---|---|---|
| `NyraTool` | `base.py:63-80` | Base class — declares `name`, `description`, `parameters` (JSON Schema), `execute()` contract returning `NyraToolResult` | All new tool classes subclass this |
| `NyraToolResult.ok(data)` / `.err(msg)` / `.to_dict()` | `base.py:31-60` | BL-01: serialises to JSON-RPC envelope. `mcp_server` dispatches via `result.to_dict()` | Every `execute()` returns one of these |
| `idempotent_lookup(name, params)` | `base.py:127-131` | BL-05: returns cached result dict if (tool, params) hash matches a prior success | First line of `execute()` body |
| `idempotent_record(name, params, data)` | `base.py:134-138` | BL-05: stores success result for future dedup | Last line before `return ok(...)` |
| `session_transaction(label)` | `base.py:147-179` | BL-04: opens `unreal.ScopedEditorTransaction` (UE 5.4+) so user Ctrl+Z reverts the entire NYRA mutation. No-op if `unreal` not importable (pytest path) | `with session_transaction(f"NYRA: {self.name}"):` wraps every mutation block |
| `verify_post_condition(label, check)` | `base.py:182-206` | BL-06: re-fetches state via callable `check` after mutation; returns error string or `None` | After mutation, before `idempotent_record`/return |
| `run_async_safely(coro)` | `base.py:13-28` | Phase 6 helper — block-and-await a coroutine from sync `execute()`; detects running loop and uses worker thread | When the new tool needs an `async` HTTP client / WS call (Phase 8: cpp recompile may dispatch to UE via WS, perf tools likely too) |

### Canonical example annotated (copy-paste skeleton for 08-02/03/05/07/08)

From `actor_tools.py:113-170`:

```python
def execute(self, params: dict) -> NyraToolResult:
    # BL-05 — short-circuit duplicate calls.
    cached = idempotent_lookup(self.name, params)
    if cached is not None:
        return NyraToolResult.ok({**cached, "deduped": True})

    # ... unpack params, validate symbol if needed ...

    # BL-04 — wrap mutation in editor transaction (Ctrl+Z reverts).
    with session_transaction(f"NYRA: {self.name}"):
        try:
            # ... call unreal.* APIs to perform the mutation ...
            actor = editor_level_lib.spawn_actor_from_class(...)
        except Exception as e:
            log.error(f"{self.name}_failed", error=str(e))
            return NyraToolResult.err(f"Failed: {e}")

        # BL-06 — re-fetch to confirm world reflects the change.
        post_err = verify_post_condition(
            f"{self.name}({actor_path})",
            lambda: _load_actor(actor_path) is not None,
        )
        if post_err:
            return NyraToolResult.err(post_err)

    # BL-05 — record for future dedup (after transaction closes successfully).
    result = {"actor_name": actor.get_name(), "actor_path": actor_path}
    idempotent_record(self.name, params, result)
    return NyraToolResult.ok(result)
```

---

## MCP Server Registration (where Phase 8 entries slot in)

**File:** `nyrahost/mcp_server/__init__.py`

### `_tools` dict (lines 77-101)

Phase 8 entries land **after line 100** (after `nyra_kb_search`). Group by plan with section comments matching the existing Phase 3/4/5 banners (lines 77-100):

```python
self._tools = {
    # Phase 4: ... (existing lines 79-91)
    # Phase 5: ... (existing lines 93-98)
    # Phase 3: ... (existing lines 99-100)

    # === Phase 8 BEGIN — slot after line 100 ===
    # PARITY-02: C++ authoring + Live Coding
    "nyra_cpp_module_create":  CppModuleCreateTool(),
    "nyra_cpp_class_add":      CppClassAddTool(),
    "nyra_cpp_function_add":   CppFunctionAddTool(),
    "nyra_cpp_recompile":      CppRecompileTool(),
    # PARITY-03: Behavior Tree
    "nyra_bt_create":              BTCreateTool(),
    "nyra_bt_add_composite":       BTAddCompositeTool(),
    "nyra_bt_add_task":            BTAddTaskTool(),
    "nyra_bt_add_decorator":       BTAddDecoratorTool(),
    "nyra_bt_set_blackboard_key":  BTSetBlackboardKeyTool(),
    # PARITY-05: Niagara
    "nyra_niagara_create_system":         NiagaraCreateSystemTool(),
    "nyra_niagara_add_emitter":           NiagaraAddEmitterTool(),
    "nyra_niagara_set_module_parameter":  NiagaraSetModuleParameterTool(),
    # PARITY-06: Performance Profiling
    "nyra_perf_stat_read":         PerfStatReadTool(),
    "nyra_perf_insights_query":    PerfInsightsQueryTool(),
    "nyra_perf_explain_hotspot":   PerfExplainHotspotTool(),
    # PARITY-07: AnimBP
    "nyra_animbp_create":             AnimBPCreateTool(),
    "nyra_animbp_add_state_machine":  AnimBPAddStateMachineTool(),
    "nyra_animbp_add_transition":     AnimBPAddTransitionTool(),
    # PARITY-08: Metasounds
    "nyra_metasound_create":   MetasoundCreateTool(),
    "nyra_metasound_add_node": MetasoundAddNodeTool(),
    "nyra_metasound_connect":  MetasoundConnectTool(),
    # === Phase 8 END ===
}
```

PARITY-01 (doc attachments) does NOT register an MCP tool — it extends the WS attachment ingestion path (`attachments.ingest_attachment` + `Storage.link_attachment`) and the chat handler. PARITY-04 is Slate-side only.

### `list_tools()` schemas (lines 162-517)

Phase 8 schemas slot **after line 516** (after `nyra_kb_search` schema, before the closing `]`). Mirror the per-tool schema shape used at lines 167-192 (`nyra_permission_gate` is the most thorough exemplar — required + properties + enum where applicable). Group with `# === Phase 8 PARITY-xx ===` banners matching lines 165, 234, 428, 494.

### Imports (lines 36-63)

Add these import lines after line 63 (`from nyrahost.tools.kb_search import KbSearchTool`):

```python
from nyrahost.tools.cpp_authoring_tools import (
    CppModuleCreateTool, CppClassAddTool, CppFunctionAddTool, CppRecompileTool,
)
from nyrahost.tools.bt_tools import (
    BTCreateTool, BTAddCompositeTool, BTAddTaskTool,
    BTAddDecoratorTool, BTSetBlackboardKeyTool,
)
from nyrahost.tools.niagara_tools import (
    NiagaraCreateSystemTool, NiagaraAddEmitterTool, NiagaraSetModuleParameterTool,
)
from nyrahost.tools.perf_tools import (
    PerfStatReadTool, PerfInsightsQueryTool, PerfExplainHotspotTool,
)
from nyrahost.tools.animbp_tools import (
    AnimBPCreateTool, AnimBPAddStateMachineTool, AnimBPAddTransitionTool,
)
from nyrahost.tools.metasound_tools import (
    MetasoundCreateTool, MetasoundAddNodeTool, MetasoundConnectTool,
)
```

---

## Per-Plan Pattern Assignments

### PARITY-01 — Document Attachments

**Closest analog:** `nyrahost/attachments.py` (self-extension)

**Key existing pieces:**
| Function | Lines | Status | Action |
|---|---|---|---|
| `AttachmentKind` (Literal type) | 34 | EXTEND | add `"document"` to the Literal |
| `ALLOWED_EXTENSIONS` | 38-42 | EXTEND | add `"document": frozenset({".pdf", ".docx", ".pptx", ".xlsx", ".html", ".md"})` (note: `.md` already in `text` — choose one home) |
| `_classify(ext_lower)` | 63-78 | REUSABLE AS-IS | already iterates `ALLOWED_EXTENSIONS.items()` — automatically covers any new kind added above |
| `_sha256_of_file()` | 81-97 | REUSABLE AS-IS | content-addressing works on any bytes |
| `ingest_attachment()` | 100-182 | REUSABLE AS-IS | path validation + symlink rejection + sensitive-prefix blocklist + hardlink/copy-fallback all extend cleanly |
| `AttachmentRef` dataclass | 45-61 | EXTEND | optional: add `extracted_text: str \| None` and `embedded_image_paths: list[str]` if downstream wants them inline (else carry on a sibling dataclass returned from the new extractor module) |

**New file: `nyrahost/document_extractors.py`** — pure-Python extractors only (LOCKED-06):

```python
# Skeleton signature
def extract_document(ref: AttachmentRef, *, project_saved: Path) -> ExtractedDocument:
    """Dispatch by ref.path suffix to pypdf / python-docx / python-pptx / openpyxl / markdown.
    Returns plain text + a list of AttachmentRef for any embedded images
    (re-ingested via attachments.ingest_attachment so they get the same
    content-addressed shard treatment images already get).
    """
```

Per LOCKED-06: only `pypdf`, `python-docx`, `python-pptx`, `openpyxl`, `markdown` — no native deps. Per T-08-02: measure wheel cache impact, fail-loud if total >75 MB.

**SQL link via `Storage.link_attachment` (storage.py:247-264):**
| Existing param | Extension needed |
|---|---|
| `kind: AttachmentKind` | NONE — already a Literal; widening at line 31 propagates automatically |
| `path / size_bytes / sha256` | NONE — content-addressing identical for documents |
| schema DDL `attachments` table (storage.py:62-69) | NONE — `kind TEXT NOT NULL` accepts new values; PRAGMA `user_version=1` does NOT need a bump (no column add) |

**Embedded image vision routing:** the SC#1 "beats Aura" claim comes from re-ingesting embedded images. Pattern: `extract_document` calls `ingest_attachment(embedded_img_temp, project_saved=project_saved)` for each image — the existing image-attachment path already routes images to Claude vision via the chat handler. Zero new vision plumbing.

---

### PARITY-02 — C++ Authoring + Live Coding

**Closest analog:** `nyrahost/tools/blueprint_tools.py` (BlueprintReadTool/WriteTool — class shape and recompile flag) + `nyrahost/tools/blueprint_debug.py` (compile-error pattern matching).

**Reusable as-is:**
- `NyraTool` subclass shape: `blueprint_tools.py:20` — `name / description / parameters / execute()` four-attribute class.
- Compile-error regex catalog: `blueprint_debug.py:33-91` (`_ERROR_PATTERNS`). The C++ Live Coding compile log uses MSVC/clang error syntax (`error C2065`, `undeclared identifier`, etc.) — extend the same `list[tuple[re.Pattern, str, str | None]]` catalog with C++-shaped entries; the dispatch helper `_explain_error_pattern` (lines 99-130) is regex-shape-agnostic and reusable as-is.
- `_DefaultDict` placeholder safety (lines 107-110) — copy verbatim into perf_tools / cpp tools wherever templated explanations land.

**New tools (each follows the canonical Phase 4 shape):**

| Tool | Signature (params) | Maps to analog |
|---|---|---|
| `nyra_cpp_module_create` | `{ module_name: str, parent_dir: str, type: "Editor" \| "Runtime" }` | analog: BlueprintWriteTool's `asset_path` + `mutation` shape — but here `mutation` is "scaffold module folder + .Build.cs" |
| `nyra_cpp_class_add` | `{ module_name: str, class_name: str, parent_class: str, header_only: bool }` | analog: BlueprintWriteTool — files are the asset; `recompile=False` by default (caller batches) |
| `nyra_cpp_function_add` | `{ class_path: str, signature: str, body: str }` | analog: blueprint_tools `_blueprint_ubergraph` graph metadata read — but writes a method into a .h/.cpp pair |
| `nyra_cpp_recompile` | `{ scope: "module" \| "all", use_live_coding: bool }` | analog: BlueprintDebugTool.execute (`blueprint_debug.py:193-326`) — same try/except + parse + structured-error envelope; `compile_attempted / compile_success / compile_errors` flow lines 219-242 copies cleanly |

**Pre-condition gate (LOCKED — Out-of-Scope §"Live Coding for non-NYRA-authored code"):** before any write, the tool must verify the target file is in the session's "NYRA-authored" set. Maintain a session-scoped allowlist in NyraTool subclass state (or a tiny `nyrahost.cpp_authoring_state` module — pattern: see `safe_mode.NyraPermissionGate` for session-scoped state).

**Live Coding dispatch:** UE Live Coding has no Python entry point in 5.4. Per T-08-03 + the WR-03/WR-05 lesson in `blueprint_debug.py:208-218`, prefer dispatching via WS to a UE C++ helper (mirror `log_tail.handle_nyra_output_log_tail` lines 21-46 — `await ws_emit_request("livecoding/recompile", {...})`). Use `run_async_safely` from `base.py:13-28` to bridge sync `execute()` → async WS call.

---

### PARITY-03 — Behavior Tree Agent

**Closest analog:** `nyrahost/tools/actor_tools.py` — **canonical Phase 4 mutator shape**. Every BT tool is a copy-rename of `ActorSpawnTool` (lines 78-170) with class/asset paths swapped for BT graph node paths.

**Reusable as-is:**
- The full `_load_actor` pattern (lines 43-64) translates directly to `_load_bt_asset(path: str)` — `unreal.EditorAssetLibrary.load_asset(path)` is identical; isinstance-check against `unreal.BehaviorTree`.
- BL-04 `session_transaction(f"NYRA: {self.name}")` wrapping (line 130).
- BL-05 `idempotent_lookup` / `idempotent_record` (lines 117-119, 169) — keys on (tool_name, sha256(params)); calling `nyra_bt_add_task` twice with the same `(bt_path, parent_node, task_class)` returns `deduped: True`.
- BL-06 `verify_post_condition(label, lambda: _load_bt_asset(path) is not None and ...)` (lines 155-160).

**New tools:** five — `nyra_bt_create / nyra_bt_add_composite / nyra_bt_add_task / nyra_bt_add_decorator / nyra_bt_set_blackboard_key`. Signatures mirror `ActorSpawnTool.parameters` (lines 84-111): `type:"object" / properties / required` JSON Schema. Param names: `bt_path`, `parent_node_id`, `node_class`, `position: {x, y}`, `name`.

**UE Python API surface to verify (per T-08-01):** `unreal.BehaviorTree`, `unreal.BTCompositeNode`, `unreal.BTTaskNode`, `unreal.BlackboardData`. Symbol-validate via Phase 3 `nyra_validate_symbol` before mutation (the pattern Plan 04-04 already follows — see `actor_tools.py` module docstring line 8 "Phase 3 SymbolGate integration via nyra_validate_symbol").

---

### PARITY-04 — Drag from Content Browser

**Closest analog (LOCKED-07):** `TestProject/Plugins/NYRA/Source/NyraEditor/{Public,Private}/Panel/SNyraImageDropZone.{h,cpp}` — **extend, do not replace**.

**Existing public surface (`SNyraImageDropZone.h` lines 12-29):**

| Member | Line | Status |
|---|---|---|
| `class NYRAEDITOR_API SNyraImageDropZone : public SCompoundWidget` | 12 | KEEP — rename to `SNyraComposerDropZone` is the next bigger change; per LOCKED-07 do NOT rename in this phase |
| `SLATE_BEGIN_ARGS / SLATE_EVENT(FOnNyraImageDropped, OnImageDropped) / SLATE_END_ARGS` | 15-17 | EXTEND — add `SLATE_EVENT(FOnNyraAssetDropped, OnAssetDropped)` |
| `void Construct(const FArguments& InArgs)` | 19 | REUSABLE AS-IS — bind both delegates if present |
| `virtual FReply OnDragOver(...)` | 21 | REUSABLE AS-IS — already returns `FReply::Handled()` for any operation |
| `virtual void OnDragLeave(...)` | 22 | REUSABLE AS-IS |
| `virtual FReply OnDrop(...)` | 23 | EXTEND — already handles `FAssetDragDropOp` (lines 92-103); split branch to fire `OnAssetDropped` vs `OnImageDropped` based on whether the resolved path looks like a `/Game/...` asset path or a filesystem path |
| `HandlePasteFromClipboard()` | 26 | REUSABLE AS-IS |
| `bool bDragOverActive` | 28 | REUSABLE AS-IS |

**The current `OnDrop` already inspects `FAssetDragDropOp`:**

```cpp
// SNyraImageDropZone.cpp lines 92-103 — ALREADY HANDLES Content Browser drag
if (TSharedPtr<FDragDropOperation> Operation = DragDropEvent.GetOperation())
{
    if (Operation->IsOfType<FAssetDragDropOp>())
    {
        TSharedPtr<FAssetDragDropOp> AssetOp = StaticCastSharedPtr<FAssetDragDropOp>(Operation);
        if (AssetOp.IsValid() && AssetOp->GetAssets().Num() > 0)
        {
            ResolvedPath = AssetOp->GetAssets()[0].GetObjectPathString();  // /Game/... path
        }
    }
}
```

**Plan 08-04 work = three deltas (not a rewrite):**
1. Add a second delegate type `DECLARE_DELEGATE_OneParam(FOnNyraAssetDropped, const FAssetData& /*Asset*/)` next to line 10.
2. In `OnDrop` (cpp line 92-103), capture the full `FAssetData` (not just `GetObjectPathString()`) and route to `OnAssetDropped` instead of `OnImageDropped` when the operation is `FAssetDragDropOp`. Keep the existing image-path branch for external-file (Explorer) drops.
3. Per T-08-06: per-UE-version verify `FAssetDragDropOp` payload shape on 5.4/5.5/5.6/5.7. Add a `#include` guard or a `NYRA::Compat::` shim if shape drifts.

**No new widget. No header rename. The composer-side wiring to forward the `FAssetData` over WS to NyraHost as a structured attachment chip is the one new behaviour.**

---

### PARITY-05 — Niagara VFX Agent

**Closest analog:** `nyrahost/tools/material_tools.py` — asset-create + parameter-set is the exact same shape Niagara needs.

**Pattern lift:**

| Niagara tool | Material analog | Shape |
|---|---|---|
| `nyra_niagara_create_system` | `MaterialCreateMICTool` (lines 283-325) | `_load_*` (line 26-30) → isinstance check (line 308-312) → `unreal.<Asset>.create(parent, world)` (line 317) → success log + `NyraToolResult.ok({path, parent})` |
| `nyra_niagara_add_emitter` | `MaterialSetParamTool` (lines 124-276) — particularly the optional `actor_path` apply branch (lines 239-261) | Load system, validate isinstance, mutate (`add_emitter`), BL-06 readback verify, return |
| `nyra_niagara_set_module_parameter` | `MaterialSetParamTool` set_*_parameter_value branches (lines 190-228) | Direct mirror — Niagara has scalar/vector/texture parameter setters with the same call shape. The BL-06 readback at lines 195-201 (`abs(readback - value) > 1e-4`) is the exact pattern to copy for scalar Niagara params |

**BL-12 lesson preserved (material_tools.py:65-72, 173-184):** when an LLM passes a path, validate the asset class via `isinstance` BEFORE mutating. For Niagara: `isinstance(asset, unreal.NiagaraSystem)` / `unreal.NiagaraEmitter`.

**T-08-04 (GPU vs CPU emitters):** same dispatch shape; the SC says "GPU sprite + ribbon emitter examples reproduce" — the parameter-set tool is identical in both; only `nyra_niagara_add_emitter` differentiates via a `sim_target: "cpu" | "gpu"` param.

---

### PARITY-06 — Performance Profiling

**Closest analogs (compose two):**
1. `nyrahost/log_tail.py` (lines 21-46) — for `nyra_perf_stat_read` (read-only UE surface forwarded over WS).
2. `nyrahost/tools/kb_search.py` — for `nyra_perf_explain_hotspot` (the **mandatory** citations integration per LOCKED-05 + SC#6).

**Pattern lift for stat reads (`log_tail.py` style):**

```python
# Mirror handle_nyra_output_log_tail exactly — log_tail.py:21-46
async def handle_nyra_perf_stat_read(args, ws_emit_request):
    stat_name = args.get("stat", "unit")  # unit | unitgraph | memory | gpu
    duration_ms = min(args.get("duration_ms", 1000), 5000)  # cap like MAX_ENTRIES_CAP
    result = await ws_emit_request("perf/stat-read", {
        "stat": stat_name, "duration_ms": duration_ms,
    })
    return result
```

The MCP server registers it via the `_handle_*` pattern at `mcp_server/__init__.py:144-146` (parallel to `_handle_log_tail`). This is a **read-only WS forwarder**, not a `_tools` dict entry — match the `log_tail` integration shape (lines 38-41 imports, lines 144-150 dispatch).

**Insights `.utrace` query (`nyra_perf_insights_query`):** read-only file parser. Pattern lift from `kb_search._resolve_index_path` (lines 91-98): file-resolution-with-fallback returning `status: "no_trace_loaded"` when missing. Per T-08-05, never silently emit empty results.

**Citations integration (`nyra_perf_explain_hotspot`) — LOCKED-05 mandatory:**

```python
# Mirror KbSearchTool composition — kb_search.py:108-159
class PerfExplainHotspotTool(NyraTool):
    def __init__(self):
        super().__init__()
        self._kb = KbSearchTool()  # delegate, don't subclass

    def execute(self, params):
        hotspot = params["hotspot_name"]  # e.g. "DrawIndexedPrimitive"
        # ... build LLM-grade explanation ...
        # LOCKED-05: cross-reference Phase 3 RAG
        kb_result = self._kb.execute({"query": hotspot, "limit": 4})
        citations = []
        if kb_result.is_ok and kb_result.data.get("status") == "ok":
            citations = [r["source_path"] for r in kb_result.data["results"]]
        return NyraToolResult.ok({
            "hotspot": hotspot,
            "explanation": ...,
            "citations": citations,  # SC#6: schema MUST include this field
            "kb_status": kb_result.data.get("status", "unknown") if kb_result.is_ok else "error",
        })
```

**T-08-05 graceful degradation:** the `kb_status` field surfaces `"no_index_loaded"` honestly so callers can show remediation. Mirror `kb_search.py:121-132` exactly.

---

### PARITY-07 — Animation Blueprint

**Closest analog:** PARITY-03 (BT) — **same Phase 4 mutator shape** (`actor_tools.py` ActorSpawnTool body), different UE asset class.

**Tools:** `nyra_animbp_create / nyra_animbp_add_state_machine / nyra_animbp_add_transition`.

**Per-tool delta from BT:** swap `unreal.BehaviorTree` → `unreal.AnimBlueprint`; swap composite/task/decorator nomenclature → state-machine/state/transition. All BL-04/05/06 wrapping identical.

**Out-of-scope reminder (CONTEXT.md §Out of Scope):** no AnimNode generation. Authoring is graph-level only — `add_state`, `add_transition`, set blend params. If a tool's success criterion would need new AnimNode C++ code, it belongs in PARITY-02 (cpp-authoring), not here.

---

### PARITY-08 — Metasounds Audio

**Closest analog:** PARITY-05 (Niagara) — same asset+nodes+connect pattern, smaller surface.

**Tools:** `nyra_metasound_create / nyra_metasound_add_node / nyra_metasound_connect`.

**Pattern lift identical to PARITY-05:** `MaterialCreateMICTool` shape for `_create`, `MaterialSetParamTool` shape for `_add_node` + `_connect` (the latter sets `from_node_id`/`from_pin`/`to_node_id`/`to_pin` instead of `param_name`/`value`, but the BL-04/05/06 envelope is the same).

UE 5.4 Python entry point: `unreal.MetasoundDocument`, `unreal.MetasoundEditorSubsystem`. Per T-08-01: verify each across 5.4–5.7; document fallback (likely no-op + remediation) on versions where the Python binding is absent — the pattern is `blueprint_debug.py:244-257` (`status: "unsupported"` with remediation).

---

## Shared Patterns (cross-cutting; apply to every applicable Phase 8 plan)

### S1. Phase 4 mutator envelope (BL-04/05/06)

**Source:** `nyrahost/tools/base.py:127-206` + `actor_tools.py:113-170`.
**Apply to:** every plan that mutates UE state — 08-02, 08-03, 08-05, 08-07, 08-08.
**LOCKED-03 enforcement:** each plan's PLAN.md must include a "Pattern Compliance" subsection naming which call site uses each of `session_transaction`, `idempotent_lookup`/`idempotent_record`, `verify_post_condition`.

### S2. NyraToolResult envelope (BL-01)

**Source:** `nyrahost/tools/base.py:31-60`.
**Apply to:** every new tool. **Never** return raw dicts. `mcp_server/__init__.py:120-121` dispatches via `result.to_dict()` — bypassing this raises AttributeError → -32000 internal_error.

### S3. async-from-sync MCP dispatch (Phase 6 helper)

**Source:** `nyrahost/tools/base.py:13-28` (`run_async_safely`).
**Apply to:** any Phase 8 tool whose `execute()` needs to await a coroutine (e.g., 08-02 cpp recompile dispatching to UE via WS, 08-06 perf reads via WS forwarder, 08-05 if Niagara compile/bake is async). Detects running loop and trampolines through a worker thread to avoid `asyncio.run` RuntimeError.

### S4. WS forwarder pattern for read-only UE surfaces

**Source:** `nyrahost/log_tail.py:21-46` + `mcp_server/__init__.py:144-150`.
**Apply to:** 08-06 (perf stat reads, message log), any 08-02 step that reads UE Live Coding state, any tool that surfaces UE editor state without Python API coverage.

### S5. UE Python API version-drift defensive coding

**Source:** `nyrahost/tools/blueprint_debug.py:208-257` (status="unsupported" + remediation), `actor_tools.py:51-64` (multiple-fallback subsystem lookup), `material_tools.py:65-72` (BL-12 isinstance-check pattern), `actor_tools.py:294-306` (WR-08 multi-method fallback).
**Apply to:** all of 08-02/03/05/07/08 per T-08-01. Pattern: `try unreal.NewSubsystem; if not present, try legacy; if neither, return status="unsupported" with remediation`. Never silently no-op; never claim success when the API didn't exist.

### S6. JSON-Schema parameters block

**Source:** `actor_tools.py:84-111` (richest exemplar — required, properties, type, default, description, nested objects).
**Apply to:** every new tool's `parameters` class attribute. The `mcp_server.list_tools()` schemas at lines 252-516 must mirror the same shape. Keep the two in sync; consider extracting a small helper that reads `tool.parameters` directly to avoid drift (Phase 8 candidate refactor — out of scope here).

### S7. structlog logger naming

**Source:** every Phase 4 tool — e.g. `actor_tools.py:27`, `material_tools.py:17`, `blueprint_debug.py:18`.
**Pattern:** `log = structlog.get_logger("nyrahost.tools.<module_name>")` at module top; events named with snake_case tool action (`actor_spawn_failed`, `material_set_param_failed`). Apply to every new tool module.

### S8. Per-tool `__all__` export list

**Source:** `actor_tools.py:29-36`, `material_tools.py:19`, `blueprint_debug.py:20`.
**Apply to:** every new tool module. Lists the tool classes only (helpers stay private with `_` prefix).

---

## No Analog Found

None. Every Phase 8 plan has at least one strong intra-repo analog. The two cases that compose multiple analogs (08-02 Live Coding via WS forwarder + cpp-error parsing; 08-06 perf with kb_search citations) are explicitly called out above.

---

## Metadata

- **Analog search scope:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/**/*.py` (Python tools, 60 files), `TestProject/Plugins/NYRA/Source/NyraEditor/**/*.{h,cpp}` (Slate UI for PARITY-04), `nyrahost/storage.py` (SQL link extension for PARITY-01).
- **Files read for excerpt extraction:** `tools/base.py`, `tools/actor_tools.py`, `tools/material_tools.py`, `tools/blueprint_tools.py` (head), `tools/blueprint_debug.py`, `tools/kb_search.py`, `log_tail.py`, `attachments.py`, `storage.py` (relevant ranges), `mcp_server/__init__.py`, `Panel/SNyraImageDropZone.{h,cpp}`.
- **Pattern extraction date:** 2026-05-10.
