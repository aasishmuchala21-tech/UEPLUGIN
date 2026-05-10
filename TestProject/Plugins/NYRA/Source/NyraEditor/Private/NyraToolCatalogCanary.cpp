// NyraToolCatalogCanary.cpp — Phase 4 + Phase 5 + Phase 6 smoke test
// Phase 4 (Plan 04-05): Validates 13 Phase 4 MCP tool registrations
// Phase 5 (Plan 05-04): Validates 4 Phase 5 MCP tool registrations (Meshy, ComfyUI)
// Phase 6 (Plan 06-04): Validates 3 Phase 6 MCP tool registrations (SCENE-01 + DEMO-01)

#include "CoreMinimal.h"
#include "Logging/LogMacros.h"
#include "Containers/Array.h"
#include "Containers/UnrealString.h"
#include "Math/UnrealMathUtility.h"

// CR-07: DECLARE_STDOUT_CHANNEL is not a UE macro. Use the canonical
// DEFINE_LOG_CATEGORY_STATIC for a cpp-local log category. Dead includes
// (EditorScriptingUtilities/BlueprintEditorUtilityLibrary.h, AssetRegistry,
// BlueprintEditorSubsystem, Kismet*) are removed -- none of the symbols
// they expose are referenced in this file.
DEFINE_LOG_CATEGORY_STATIC(LogNyraToolCanary, Log, All);

// ---------------------------------------------------------------------------
// Phase 4 tool registry (13 tools across ACT-01..ACT-05)
// ---------------------------------------------------------------------------

struct FToolEntry
{
    FString Name;
    bool (*ValidateFn)();
};

static bool Validate_nyra_blueprint_read();
static bool Validate_nyra_blueprint_write();
static bool Validate_nyra_blueprint_debug();
static bool Validate_nyra_asset_search();
static bool Validate_nyra_actor_spawn();
static bool Validate_nyra_actor_duplicate();
static bool Validate_nyra_actor_delete();
static bool Validate_nyra_actor_select();
static bool Validate_nyra_actor_transform();
static bool Validate_nyra_actor_snap_ground();
static bool Validate_nyra_material_get_param();
static bool Validate_nyra_material_set_param();
static bool Validate_nyra_material_create_mic();

static TArray<FToolEntry> GPhase4Tools = {
    // ACT-01 Blueprint Read/Write
    { TEXT("nyra_blueprint_read"),      Validate_nyra_blueprint_read },
    { TEXT("nyra_blueprint_write"),     Validate_nyra_blueprint_write },
    // ACT-02 Blueprint Debug
    { TEXT("nyra_blueprint_debug"),     Validate_nyra_blueprint_debug },
    // ACT-03 Asset Search
    { TEXT("nyra_asset_search"),        Validate_nyra_asset_search },
    // ACT-04 Actor CRUD
    { TEXT("nyra_actor_spawn"),        Validate_nyra_actor_spawn },
    { TEXT("nyra_actor_duplicate"),     Validate_nyra_actor_duplicate },
    { TEXT("nyra_actor_delete"),        Validate_nyra_actor_delete },
    { TEXT("nyra_actor_select"),       Validate_nyra_actor_select },
    { TEXT("nyra_actor_transform"),     Validate_nyra_actor_transform },
    { TEXT("nyra_actor_snap_ground"),  Validate_nyra_actor_snap_ground },
    // ACT-05 Material Instance
    { TEXT("nyra_material_get_param"), Validate_nyra_material_get_param },
    { TEXT("nyra_material_set_param"), Validate_nyra_material_set_param },
    { TEXT("nyra_material_create_mic"),Validate_nyra_material_create_mic },
};

// ---------------------------------------------------------------------------
// Phase 5 tool registry (4 tools across GEN-01, GEN-02)
// ---------------------------------------------------------------------------

static bool Validate_nyra_meshy_image_to_3d();
static bool Validate_nyra_job_status();
static bool Validate_nyra_comfyui_run_workflow();
static bool Validate_nyra_comfyui_get_node_info();

static TArray<FToolEntry> GPhase5Tools = {
    // GEN-01: Meshy REST
    { TEXT("nyra_meshy_image_to_3d"), Validate_nyra_meshy_image_to_3d },
    { TEXT("nyra_job_status"),       Validate_nyra_job_status },
    // GEN-02: ComfyUI HTTP
    { TEXT("nyra_comfyui_run_workflow"),    Validate_nyra_comfyui_run_workflow },
    { TEXT("nyra_comfyui_get_node_info"), Validate_nyra_comfyui_get_node_info },
};

// ---------------------------------------------------------------------------
// Phase 6 tool registry (3 tools across SCENE-01 + DEMO-01)
// Plan 06-04 — DEMO-01 launch-demo canary.
// ---------------------------------------------------------------------------

static bool Validate_nyra_lighting_authoring();
static bool Validate_nyra_lighting_dry_run_preview();
static bool Validate_nyra_assemble_scene();

static TArray<FToolEntry> GPhase6Tools = {
    // SCENE-01: Lighting authoring (Plan 06-01)
    { TEXT("nyra_lighting_authoring"),         Validate_nyra_lighting_authoring },
    { TEXT("nyra_lighting_dry_run_preview"),   Validate_nyra_lighting_dry_run_preview },
    // DEMO-01: Scene assembly (Plan 06-02)
    { TEXT("nyra_assemble_scene"),             Validate_nyra_assemble_scene },
};

static bool Validate_nyra_lighting_authoring()
{
    // Check: LightingAuthoringTool registered with nl_prompt + reference_image_path +
    // preset_name + apply params. Verify SCENE-01 spec fields present.
    return false; // BL-03 PENDING: real validation requires IPC to NyraHost tools/list endpoint; returning false so canary truthfully reports "no validation performed" rather than fraudulent PASS
}

static bool Validate_nyra_lighting_dry_run_preview()
{
    // Check: LightingDryRunTool registered with preset_name + lighting_params_json.
    return false; // BL-03 PENDING: real validation requires IPC to NyraHost tools/list
}

static bool Validate_nyra_assemble_scene()
{
    // Check: AssembleSceneTool registered with reference_image_path required +
    // optional lighting_preset.
    return false; // BL-03 PENDING: real validation requires IPC to NyraHost tools/list
}

// ---------------------------------------------------------------------------
// Phase 4 validation stubs
// Each stub checks the Python NyraHost sidecar registers the named tool
// by reading its JSON-RPC tool-list response via the stdio MCP interface.
// ---------------------------------------------------------------------------

static bool Validate_nyra_blueprint_read()
{
    // Check: BlueprintReadTool is registered in mcp_server/__init__.py
    // Verify: tool name, description non-empty, asset_path param present
    return false; // BL-03 PENDING: real validation requires IPC to NyraHost tools/list endpoint; returning false so canary truthfully reports "no validation performed" rather than fraudulent PASS
}

static bool Validate_nyra_blueprint_write()
{
    // Check: BlueprintWriteTool is registered
    // Verify: mutation + asset_path params, dry_run + recompile flags
    return false; // BL-03 PENDING: real validation requires IPC to NyraHost tools/list
}

static bool Validate_nyra_blueprint_debug()
{
    // Check: BlueprintDebugTool is registered
    // Verify: include_warnings + include_suggestions optional params
    return false; // BL-03 PENDING: real validation requires IPC to NyraHost tools/list
}

static bool Validate_nyra_asset_search()
{
    // Check: AssetSearchTool is registered
    // Verify: query param, class_filter/limit/threshold optional params
    return false; // BL-03 PENDING: real validation requires IPC to NyraHost tools/list
}

static bool Validate_nyra_actor_spawn()
{
    // Check: ActorSpawnTool is registered
    // Verify: actor_class + spawn_transform params
    return false; // BL-03 PENDING: real validation requires IPC to NyraHost tools/list
}

static bool Validate_nyra_actor_duplicate()
{
    // Check: ActorDuplicateTool is registered
    // Verify: source_actor param
    return false; // BL-03 PENDING: real validation requires IPC to NyraHost tools/list
}

static bool Validate_nyra_actor_delete()
{
    // Check: ActorDeleteTool is registered
    // Verify: actor_path param
    return false; // BL-03 PENDING: real validation requires IPC to NyraHost tools/list
}

static bool Validate_nyra_actor_select()
{
    // Check: ActorSelectTool is registered
    // Verify: actor_path + mode params
    return false; // BL-03 PENDING: real validation requires IPC to NyraHost tools/list
}

static bool Validate_nyra_actor_transform()
{
    // Check: ActorTransformTool is registered
    // Verify: actor_path + location/rotation/scale optional params
    return false; // BL-03 PENDING: real validation requires IPC to NyraHost tools/list
}

static bool Validate_nyra_actor_snap_ground()
{
    // Check: ActorSnapGroundTool is registered
    // Verify: actor_path param
    return false; // BL-03 PENDING: real validation requires IPC to NyraHost tools/list
}

static bool Validate_nyra_material_get_param()
{
    // Check: MaterialGetParamTool is registered
    // Verify: material_path + param_name + param_type params
    return false; // BL-03 PENDING: real validation requires IPC to NyraHost tools/list
}

static bool Validate_nyra_material_set_param()
{
    // Check: MaterialSetParamTool is registered
    // Verify: material_path + param_name + param_type params
    return false; // BL-03 PENDING: real validation requires IPC to NyraHost tools/list
}

static bool Validate_nyra_material_create_mic()
{
    // Check: MaterialCreateMICTool is registered
    // Verify: parent_material param + optional mic_name
    return false; // BL-03 PENDING: real validation requires IPC to NyraHost tools/list
}

// ---------------------------------------------------------------------------
// Phase 5 validation stubs
// GEN-01: Meshy REST — validates tool registration + parameter schema
// GEN-02: ComfyUI HTTP — validates tool registration + parameter schema
// ---------------------------------------------------------------------------

// GEN-01: nyra_meshy_image_to_3d
// Check: MeshyImageTo3DTool registered in mcp_server/__init__.py or tools/meshy_tools.py
// Verify: name="nyra_meshy_image_to_3d", image_path required param, job_id in output schema
static bool Validate_nyra_meshy_image_to_3d()
{
    // Phase 5 GEN-01: Meshy image-to-3D tool registration
    // Validation checks:
    //   1. Tool name: "nyra_meshy_image_to_3d" in MCP tool list
    //   2. Required param: image_path (string)
    //   3. Optional params: prompt, task_type, target_folder
    //   4. Output schema includes job_id (string) and status (string)
    // Full validation requires Python sidecar running; stubs return true
    return false; // BL-03 PENDING: real validation requires IPC to NyraHost tools/list
}

// GEN-01: nyra_job_status
// Check: JobStatusTool registered in mcp_server/__init__.py or tools/meshy_tools.py
// Verify: name="nyra_job_status", job_id required, pending/completed/failed status returned
static bool Validate_nyra_job_status()
{
    // Phase 5 GEN-01: Job status polling tool registration
    // Validation checks:
    //   1. Tool name: "nyra_job_status" in MCP tool list
    //   2. Required param: job_id (string)
    //   3. Output schema includes status (string), progress (number, optional), error (string, optional)
    return false; // BL-03 PENDING: real validation requires IPC to NyraHost tools/list
}

// GEN-02: nyra_comfyui_run_workflow
// Check: ComfyUIRunWorkflowTool registered in mcp_server/__init__.py or tools/comfyui_tools.py
// Verify: name="nyra_comfyui_run_workflow", workflow_json required, idempotent via input_hash
static bool Validate_nyra_comfyui_run_workflow()
{
    // Phase 5 GEN-02: ComfyUI workflow execution tool registration
    // Validation checks:
    //   1. Tool name: "nyra_comfyui_run_workflow" in MCP tool list
    //   2. Required param: workflow_json (object — ComfyUI API JSON format)
    //   3. Optional params: input_image_asset_path, target_folder
    //   4. Idempotency: dedup by input_hash before new API call
    //   5. Output schema includes job_id (string) and status (string)
    return false; // BL-03 PENDING: real validation requires IPC to NyraHost tools/list
}

// GEN-02: nyra_comfyui_get_node_info
// Check: ComfyUIGetNodeInfoTool registered in mcp_server/__init__.py or tools/comfyui_tools.py
// Verify: name="nyra_comfyui_get_node_info", no required params, returns node type map
static bool Validate_nyra_comfyui_get_node_info()
{
    // Phase 5 GEN-02: ComfyUI node info tool registration
    // Validation checks:
    //   1. Tool name: "nyra_comfyui_get_node_info" in MCP tool list
    //   2. No required params
    //   3. Output: dict of node_type -> {inputs, required, properties}
    //   4. Security: only validated node types returned (no raw API dump — T-05-04)
    return false; // BL-03 PENDING: real validation requires IPC to NyraHost tools/list
}

// ---------------------------------------------------------------------------
// RunToolCatalogCanary — entry point from FNyraDevTools console command
// ---------------------------------------------------------------------------

void RunToolCatalogCanary(int32 Iterations)
{
    UE_LOG(LogNyraToolCanary, Display, TEXT(""));
    UE_LOG(LogNyraToolCanary, Display, TEXT("========================================"));
    UE_LOG(LogNyraToolCanary, Display, TEXT("  ToolCatalogCanary — Phase 4 + Phase 5 + Phase 6"));
    UE_LOG(LogNyraToolCanary, Display, TEXT("========================================"));

    // ---- Phase 4 ----
    UE_LOG(LogNyraToolCanary, Display, TEXT(""));
    UE_LOG(LogNyraToolCanary, Display, TEXT("=== Phase 4: UE Asset & Blueprint Tools (%d tools) ==="), GPhase4Tools.Num());

    int32 Phase4Passed = 0;
    int32 Phase4Failed = 0;
    TArray<FString> Phase4FailedTools;

    for (int32 i = 0; i < GPhase4Tools.Num(); ++i)
    {
        const FToolEntry& Tool = GPhase4Tools[i];
        bool Result = false;
        for (int32 Attempt = 0; Attempt < FMath::Max(Iterations, 1); ++Attempt)
        {
            Result = Tool.ValidateFn();
            if (Result)
                break;
        }
        if (Result)
        {
            UE_LOG(LogNyraToolCanary, Display, TEXT("  [PASS] %s"), *Tool.Name);
            Phase4Passed++;
        }
        else
        {
            UE_LOG(LogNyraToolCanary, Error, TEXT("  [FAIL] %s"), *Tool.Name);
            Phase4FailedTools.Add(Tool.Name);
            Phase4Failed++;
        }
    }

    UE_LOG(LogNyraToolCanary, Display, TEXT("  Phase 4: %d/%d passed"), Phase4Passed, GPhase4Tools.Num());

    // ---- Phase 5 ----
    UE_LOG(LogNyraToolCanary, Display, TEXT(""));
    UE_LOG(LogNyraToolCanary, Display, TEXT("=== Phase 5: External Tool Integrations (%d tools) ==="), GPhase5Tools.Num());

    int32 Phase5Passed = 0;
    int32 Phase5Failed = 0;
    TArray<FString> Phase5FailedTools;
    TArray<FString> Phase5PassedTools;

    for (int32 i = 0; i < GPhase5Tools.Num(); ++i)
    {
        const FToolEntry& Tool = GPhase5Tools[i];
        bool Result = false;
        for (int32 Attempt = 0; Attempt < FMath::Max(Iterations, 1); ++Attempt)
        {
            Result = Tool.ValidateFn();
            if (Result)
                break;
        }
        if (Result)
        {
            UE_LOG(LogNyraToolCanary, Display, TEXT("  [PASS] %s"), *Tool.Name);
            Phase5PassedTools.Add(Tool.Name);
            Phase5Passed++;
        }
        else
        {
            UE_LOG(LogNyraToolCanary, Error, TEXT("  [FAIL] %s"), *Tool.Name);
            Phase5FailedTools.Add(Tool.Name);
            Phase5Failed++;
        }
    }

    UE_LOG(LogNyraToolCanary, Display, TEXT("  Phase 5: %d/%d passed"), Phase5Passed, GPhase5Tools.Num());

    // ---- Phase 6 ----
    UE_LOG(LogNyraToolCanary, Display, TEXT(""));
    UE_LOG(LogNyraToolCanary, Display, TEXT("=== Phase 6: Scene Assembly + DEMO-01 (%d tools) ==="), GPhase6Tools.Num());

    int32 Phase6Passed = 0;
    int32 Phase6Failed = 0;
    TArray<FString> Phase6FailedTools;
    TArray<FString> Phase6PassedTools;

    for (int32 i = 0; i < GPhase6Tools.Num(); ++i)
    {
        const FToolEntry& Tool = GPhase6Tools[i];
        bool Result = false;
        for (int32 Attempt = 0; Attempt < FMath::Max(Iterations, 1); ++Attempt)
        {
            Result = Tool.ValidateFn();
            if (Result)
                break;
        }
        if (Result)
        {
            UE_LOG(LogNyraToolCanary, Display, TEXT("  [PASS] %s"), *Tool.Name);
            Phase6PassedTools.Add(Tool.Name);
            Phase6Passed++;
        }
        else
        {
            UE_LOG(LogNyraToolCanary, Error, TEXT("  [FAIL] %s"), *Tool.Name);
            Phase6FailedTools.Add(Tool.Name);
            Phase6Failed++;
        }
    }

    UE_LOG(LogNyraToolCanary, Display, TEXT("  Phase 6: %d/%d passed"), Phase6Passed, GPhase6Tools.Num());

    // ---- Combined Summary ----
    const int32 TotalTools = GPhase4Tools.Num() + GPhase5Tools.Num() + GPhase6Tools.Num();
    const int32 TotalPassed = Phase4Passed + Phase5Passed + Phase6Passed;
    const int32 TotalFailed = Phase4Failed + Phase5Failed + Phase6Failed;

    UE_LOG(LogNyraToolCanary, Display, TEXT(""));
    UE_LOG(LogNyraToolCanary, Display, TEXT("========================================"));
    UE_LOG(LogNyraToolCanary, Display, TEXT("  ToolCatalogCanary Summary"));
    UE_LOG(LogNyraToolCanary, Display, TEXT("========================================"));
    UE_LOG(LogNyraToolCanary, Display, TEXT("  Phase 4 (ACT-01..ACT-05): %d/%d passed"), Phase4Passed, GPhase4Tools.Num());
    UE_LOG(LogNyraToolCanary, Display, TEXT("  Phase 5 (GEN-01..GEN-02): %d/%d passed"), Phase5Passed, GPhase5Tools.Num());
    UE_LOG(LogNyraToolCanary, Display, TEXT("  Phase 6 (SCENE-01 + DEMO-01): %d/%d passed"), Phase6Passed, GPhase6Tools.Num());
    UE_LOG(LogNyraToolCanary, Display, TEXT("  Total: %d/%d tools passed"), TotalPassed, TotalTools);
    UE_LOG(LogNyraToolCanary, Display, TEXT("========================================"));

    if (!Phase5PassedTools.IsEmpty())
    {
        FString PassedStr = FString::Join(Phase5PassedTools, TEXT(", "));
        UE_LOG(LogNyraToolCanary, Display, TEXT("  Phase 5 PASSED: %s"), *PassedStr);
    }

    if (Phase4Failed > 0)
    {
        FString FailedStr = FString::Join(Phase4FailedTools, TEXT(", "));
        UE_LOG(LogNyraToolCanary, Error, TEXT("  Phase 4 FAILED: %s"), *FailedStr);
    }

    if (Phase5Failed > 0)
    {
        FString FailedStr = FString::Join(Phase5FailedTools, TEXT(", "));
        UE_LOG(LogNyraToolCanary, Error, TEXT("  Phase 5 FAILED: %s"), *FailedStr);
    }

    if (!Phase6PassedTools.IsEmpty())
    {
        FString PassedStr = FString::Join(Phase6PassedTools, TEXT(", "));
        UE_LOG(LogNyraToolCanary, Display, TEXT("  Phase 6 PASSED: %s"), *PassedStr);
    }

    if (Phase6Failed > 0)
    {
        FString FailedStr = FString::Join(Phase6FailedTools, TEXT(", "));
        UE_LOG(LogNyraToolCanary, Error, TEXT("  Phase 6 FAILED: %s"), *FailedStr);
    }

    UE_LOG(LogNyraToolCanary, Display, TEXT("========================================"));

    if (TotalFailed > 0)
    {
        UE_LOG(LogNyraToolCanary, Error,
            TEXT("[VERDICT] FAIL — %d tool(s) did not register correctly. "
                 "Check mcp_server/__init__.py tool dict and schemas."), TotalFailed);
    }
    else
    {
        UE_LOG(LogNyraToolCanary, Display,
            TEXT("[VERDICT] PASS — all %d tools registered (Phase 4 + Phase 5 + Phase 6)."), TotalPassed);
    }
}
