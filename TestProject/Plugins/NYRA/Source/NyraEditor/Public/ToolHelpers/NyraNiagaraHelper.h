// SPDX-License-Identifier: MIT
// =============================================================================
// NyraNiagaraHelper.h  (Phase 8 Plan 08-05 -- PARITY-05 Niagara VFX Agent)
// =============================================================================
//
// UCLASS exposing the Niagara editor surface that the UE Python bindings do
// not reflect cleanly. Three operations are needed by Plan 08-05's Python
// mutator tools (`nyrahost/tools/niagara_tools.py`):
//
//   1. AddEmitterFromTemplate -- create an emitter handle on a system from
//      a known template path, with a sim-target (CPU vs GPU) selector.
//      Wraps `UNiagaraSystem::GetEmitterHandles()` and the editor-only
//      `FNiagaraEmitterHandle` surface (T-08-04 GPU+CPU dual coverage).
//
//   2. SetScalarModuleParameter / SetVectorModuleParameter -- walk the
//      emitter's authoring stack and set a module override for a named
//      scalar or vector parameter. The Python `unreal.*` bindings do not
//      reach into the Niagara stack-API surface in 5.4 (verified via the
//      Wave 0 symbol survey -- see `wave-0-symbol-survey/08-05-WAVE-0-PLAN.md`).
//
//   3. GetScalarModuleParameter -- the BL-06 readback used by
//      `nyra_niagara_set_module_parameter` to verify the requested value
//      landed within `1e-4` tolerance (mirrors `material_tools.py:195-201`).
//
// The functions are tagged `BlueprintCallable, meta=(ScriptMethod)` so
// `unreal.NyraNiagaraHelper.add_emitter_from_template(...)` is callable
// from the NyraHost Python sidecar without a custom binding.
//
// Each function returns a sentinel-failure value on error:
//   - AddEmitterFromTemplate -> empty FString
//   - SetScalarModuleParameter / SetVectorModuleParameter -> false
//   - GetScalarModuleParameter -> MIN_flt (caller must guard against this)
//
// Failure paths are SILENT at the C++ level (UE_LOG only); the Python
// caller is responsible for surfacing structured `NyraToolResult.err(...)`.
//
// Build.cs requirement (orchestrator-batched per LOCKED-10):
//   PrivateDependencyModuleNames += { "Niagara", "NiagaraEditor" }
// =============================================================================
#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "NyraNiagaraHelper.generated.h"

class UNiagaraSystem;

/**
 * Editor-side helper UCLASS used by the NyraHost Python sidecar to author
 * Niagara systems where the stock `unreal.*` bindings do not reach.
 *
 * Marked `MinimalAPI` because there are no C++ callers inside NyraEditor
 * itself -- every method is invoked from Python. `MinimalAPI` keeps the
 * UHT-generated reflection table small and avoids a public-symbol export
 * tax for callers that never link against the helper from native code.
 */
UCLASS(MinimalAPI)
class UNyraNiagaraHelper : public UObject
{
    GENERATED_BODY()

public:
    /**
     * Add an emitter from a template path to a Niagara system.
     *
     * @param System        Target NiagaraSystem (must be non-null and saveable).
     * @param TemplatePath  UE asset path of the emitter template, e.g.
     *                      `/Niagara/Templates/Sprite/SpriteBurst`.
     * @param SimTarget     `"cpu"` or `"gpu"` -- selects between
     *                      `ENiagaraSimTarget::CPUSim` and
     *                      `ENiagaraSimTarget::GPUComputeSim`. Per T-08-04
     *                      both paths are part of the parity bar; on
     *                      versions where the GPU path fails to compile,
     *                      callers fall back to CPU and surface the
     *                      divergence in 08-05-VERIFICATION.md.
     * @param HandleName    Display name for the new emitter handle in the
     *                      system's emitter list (also used as the Python
     *                      caller's idempotent_lookup key).
     *
     * @return The materialised emitter handle name on success, or an empty
     *         FString on failure (template missing, system invalid, sim
     *         target unsupported on this UE version).
     */
    UFUNCTION(BlueprintCallable, Category="Nyra|Niagara", meta=(ScriptMethod))
    static FString AddEmitterFromTemplate(
        UNiagaraSystem* System,
        FName TemplatePath,
        FName SimTarget,
        FName HandleName);

    /**
     * Set a scalar module parameter on a specific emitter handle.
     *
     * @return true if the override was applied (and the system marked
     *         dirty); false on any failure (system null, handle not
     *         found, parameter not found, stack API unavailable on this
     *         UE version).
     */
    UFUNCTION(BlueprintCallable, Category="Nyra|Niagara", meta=(ScriptMethod))
    static bool SetScalarModuleParameter(
        UNiagaraSystem* System,
        FName EmitterHandle,
        FName ParameterName,
        float Value);

    /**
     * Set a vector module parameter on a specific emitter handle.
     */
    UFUNCTION(BlueprintCallable, Category="Nyra|Niagara", meta=(ScriptMethod))
    static bool SetVectorModuleParameter(
        UNiagaraSystem* System,
        FName EmitterHandle,
        FName ParameterName,
        FVector Value);

    /**
     * Read back a scalar module parameter for BL-06 post-condition checks.
     *
     * @return The current scalar value on success, or `MIN_flt` on failure.
     *         The Python caller (`nyra_niagara_set_module_parameter`)
     *         compares `abs(readback - requested) < 1e-4` to confirm the
     *         override persisted (mirror of `material_tools.py:195-201`).
     */
    UFUNCTION(BlueprintCallable, Category="Nyra|Niagara", meta=(ScriptMethod))
    static float GetScalarModuleParameter(
        UNiagaraSystem* System,
        FName EmitterHandle,
        FName ParameterName);
};
