---
phase: 4
slug: blueprint-asset-material-actor-tool-catalog
status: draft
grey_areas: 7
consensus_threshold: founder-review
---

# Phase 4: Blueprint + Asset + Material + Actor Tool Catalog — Context

**Gathered:** 2026-05-07
**Status:** Ready for planning
**Source:** `REQUIREMENTS.md` §ACT-01..ACT-05 + `ROADMAP.md` §Phase 4 + inherited Phase 2 D-locks

---

<domain>
## Phase Boundary

Phase 4 delivers NYRA's in-editor tool catalog — the UE-native actions the agent drives via MCP tools: Blueprint graph read/write, Blueprint compile-error interception + fix loop, asset search over the UE asset registry, Actor spawn/duplicate/delete/transform via editor subsystems, and Material Instance parameter read/write.

**Requirements this phase satisfies:** ACT-01, ACT-02, ACT-03, ACT-04, ACT-05.

**Depends on:** Phase 3 (SymbolGate validates cited UE symbols before any action; RAG provides context for "how do I use this API").

**Out of scope for Phase 4:**
- Console command execution (ACT-06) → Phase 2 shipped
- Output/Message Log streaming (ACT-07) → Phase 2 shipped
- Meshy / ComfyUI / Substance (GEN-01/02/03) → Phase 5
- Lighting / Sequencer (SCENE-01/02) → Phase 6/7
- Fab launch prep → Phase 8
- Blueprint auto-fix for Animation/Widget Blueprints → v1.1 (ACT-11)
- CLIP thumbnail-embedding asset search → v1.1 (ACT-10)

</domain>

<grey_areas>
## Grey Areas

| # | Area | Pre-selected Position | Confidence | Kill Criteria |
|---|------|----------------------|------------|---------------|
| GA-1 | Blueprint read API surface | Kismet Python API (`unreal.Blueprint`) covers node/variable reading; node position + pin default reading may need C++ fallback | MEDIUM | If Python API is insufficient for node position, add C++ `FNyraBlueprintReader` using `FBlueprintEditorModule` |
| GA-2 | Blueprint write + recompile | `FKismetCompilerContext` for graph modification; `FBlueprintEditorUtils::RebuildBlueprint` for recompile | MEDIUM | If RebuildBlueprint has ABI issues across 5.4–5.7, wrap in NYRA_UE_AT_LEAST shim; defer recompile to user-click to avoid silent compile failures |
| GA-3 | Asset search fuzzy-match algorithm | Python `fuzzywuzzy` over `FAssetData` name/tag/class strings (no vector embeddings in v1) | HIGH | If fuzzywuzzy is too slow for 50K+ asset libraries, switch to RapidFuzz or pre-index with Levenshtein |
| GA-4 | Material param write visibility | `UKismetMaterialLibrary` exposes scalar/vector params; texture params need `UMaterialInstance` set texture overrides | MEDIUM | If set_texture fails in Python, use C++ `UMaterialEditingLibrary::SetTextureParameterValue` |
| GA-5 | Actor transform precision | `EditorActorSubsystem` uses `USceneComponent::SetWorldLocation/Rotation/Scale` which preserves rotation order | HIGH | Rotation-order edge cases are rare enough to defer to Phase 4.1 if users report them |
| GA-6 | Session transaction wrapping | All ACT-01..ACT-05 tools wrapped in Phase 2's `FNyraSessionTransaction` (CHAT-03 D-10 lock) | HIGH | No deviation — every mutation calls `Modify()` inside an active transaction |
| GA-7 | Wave structure for 5 plans | Wave 0 = shared schema/types; Wave 1 = read tools (ACT-03, ACT-04 partial, ACT-05 partial); Wave 2 = write tools (ACT-01, ACT-02, ACT-04 partial, ACT-05 partial) | HIGH | If any plan has hidden complexity, break it into sub-waves — no 5-plan wave is forced |

</grey_areas>

<decisions>
## Decisions

### D-1: Blueprint Read — Python-First, C++ Fallback

`unreal.Blueprint` (Python binding) exposes `get_functions()`, `get_variables()`, `get_event_graphs()`. Reading node/wire topology: `UK2Node` iterated via `UBlueprintGeneratedClass`. Node position from `UK2Node::NodePosX/Y`. If Python API returns incomplete data for a specific subgraph, add `NyraEditor::FNyraBlueprintReader` C++ helper using `FBlueprintEditorModule`.

### D-2: Blueprint Write — Compile Guard

All graph mutations go through `FKismetCompilerContext`. On mutation: mark dirty, call `FBlueprintEditorUtils::RebuildBlueprint`, catch `FKismetCompilerContext::Compile` errors, surface as `compile_error` struct with node GUID + message. **One-click apply = user approves diff → recompile**. If recompile fails, roll back to pre-mutation snapshot and surface the error.

### D-3: Asset Search — Fuzzy String Match

Use `FAssetRegistryModule` to get all `FAssetData` for the current project. Python `fuzzywuzzy.fuzz.partial_ratio` over (name + tags + class). Index refreshed on plugin load and on `AssetRegistryChanged` broadcast. Threshold configurable; default 70.

### D-4: Actor CRUD — EditorActorSubsystem

All actor operations call `unreal.EditorActorSubsystem` or `unreal.EditorLevelLibrary`. `spawn_actor_from_class` for class-path spawns; `duplicate_actors` for duplication; `delete_actors` for deletion. Transform via `actor.set_actor_location/rotation/scale`. Snap-to-ground via `line_trace_by_object` on actor bounding box bottom.

### D-5: Material Instance — UKismetMaterialLibrary + Python

Scalar/vector params: `unreal.KismetMaterialLibrary.set_scalar_parameter_value` / `set_vector_parameter_value`. Create MIC: `unreal.MaterialInstanceDynamic.create`. Texture params: `UMaterialInstance.set_texture_parameter_value_by_name` via Python `unreal` binding.

### D-6: Transaction Discipline

All 5 tool categories are **write operations** (ACT-01, ACT-02 are write; ACT-03 is read-only; ACT-04, ACT-05 are write). ACT-03 asset search has no transaction cost (read-only). All others: `FNyraSessionTransaction::Begin` + `UObject::Modify` before mutation. Phase 2's `chat/cancel` → `FNyraSessionTransaction::Cancel` rollback covers Phase 4 tools.

### D-7: MCP Tool Naming Convention

Tools follow `nyra_<category>_<verb>` pattern:
- `nyra_blueprint_read` — ACT-01 read
- `nyra_blueprint_write` — ACT-01 write
- `nyra_blueprint_debug` — ACT-02 debug loop
- `nyra_asset_search` — ACT-03
- `nyra_actor_spawn` / `nyra_actor_delete` / `nyra_actor_transform` — ACT-04
- `nyra_material_get_param` / `nyra_material_set_param` — ACT-05

### D-8: Module-Superset Discipline

Phase 1 (`Nyra.Dev.RoundTripBench`) and Phase 2 (`Nyra.Dev.SubscriptionBridgeCanary`) preserved verbatim. Phase 4 adds `Nyra.Dev.ToolCatalogCanary` console command to smoke-test all 12 MCP tools with mock data.

</decisions>