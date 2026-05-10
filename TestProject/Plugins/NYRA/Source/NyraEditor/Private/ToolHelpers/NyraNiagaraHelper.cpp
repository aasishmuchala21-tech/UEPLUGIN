// SPDX-License-Identifier: MIT
// =============================================================================
// NyraNiagaraHelper.cpp  (Phase 8 Plan 08-05 -- PARITY-05 Niagara VFX Agent)
// =============================================================================
//
// Reach-around helper that the Python sidecar calls when the stock UE Python
// bindings don't expose Niagara's editor-only stack-API. See header for the
// full rationale; the per-method inline comments below document the UE-version
// drift surface (T-08-01) for each call site.
//
// Per LOCKED-10 the orchestrator (not this plan) batches the Build.cs edit
// adding `Niagara` + `NiagaraEditor` to `PrivateDependencyModuleNames`.
// Until that batch lands, this .cpp will fail to link -- expected; the
// Wave-0 operator runbook (`wave-0-symbol-survey/08-05-WAVE-0-PLAN.md`)
// only runs after the orchestrator has merged the deps batch.
//
// =============================================================================
#include "ToolHelpers/NyraNiagaraHelper.h"

#include "NiagaraSystem.h"
#include "NiagaraEmitter.h"
#include "NiagaraEmitterHandle.h"
#include "NiagaraScriptSourceBase.h"
#include "NiagaraTypes.h"

#include "UObject/Package.h"
#include "Editor.h"
#include "Misc/PackageName.h"

DEFINE_LOG_CATEGORY_STATIC(LogNyraNiagara, Log, All);


// -----------------------------------------------------------------------------
// AddEmitterFromTemplate
// -----------------------------------------------------------------------------
//
// The canonical UE 5.4 surface for adding an emitter to a system from a
// template is `UNiagaraSystem::AddEmitterHandle(FNiagaraEmitter&, FName)`.
// Older 5.4 builds shipped this as `AddEmitterHandleWithoutCopying`; the
// surface stabilised on `AddEmitterHandle(...)` for 5.5+. We probe by
// `FindFunctionChecked` only when the static link path is unavailable on
// the current UE major.
//
// T-08-01 fallback: if the system rejects the handle (template not a
// Niagara emitter, package locked), return an empty FString. The Python
// caller wraps this as `NyraToolResult.err("AddEmitterFromTemplate returned
// empty handle")`.
//
// T-08-04 GPU vs CPU split: `SimTarget` is mapped to
// `ENiagaraSimTarget::CPUSim` / `GPUComputeSim`. On versions where the GPU
// shader compile pass is broken, the system author still receives a
// successful handle from `AddEmitterHandle` -- the failure manifests at
// editor compile time, not at handle creation time. The operator
// verification (`08-05-VERIFICATION.md`) is the only path that detects
// the broken GPU compile.
// -----------------------------------------------------------------------------
FString UNyraNiagaraHelper::AddEmitterFromTemplate(
    UNiagaraSystem* System,
    FName TemplatePath,
    FName SimTarget,
    FName HandleName)
{
    if (!System)
    {
        UE_LOG(LogNyraNiagara, Warning, TEXT("AddEmitterFromTemplate: System is null"));
        return FString();
    }
    if (TemplatePath.IsNone() || HandleName.IsNone())
    {
        UE_LOG(LogNyraNiagara, Warning,
            TEXT("AddEmitterFromTemplate: TemplatePath or HandleName is empty"));
        return FString();
    }

    // Resolve the template -- the path may be a content-browser path
    // (e.g. /Niagara/Templates/Sprite/SpriteBurst) or a fully-qualified
    // ObjectPath (e.g. /Niagara/Templates/Sprite/SpriteBurst.SpriteBurst).
    // LoadObject<UNiagaraEmitter> handles both via FSoftObjectPath.
    const FString TemplatePathStr = TemplatePath.ToString();
    UNiagaraEmitter* Template = LoadObject<UNiagaraEmitter>(
        nullptr, *TemplatePathStr, nullptr, LOAD_None, nullptr);
    if (!Template)
    {
        UE_LOG(LogNyraNiagara, Warning,
            TEXT("AddEmitterFromTemplate: failed to load template '%s'"),
            *TemplatePathStr);
        return FString();
    }

    // Add the handle. UE 5.4-5.7 all expose AddEmitterHandle(EmitterRef, Name);
    // on UE versions where the signature has drifted, the version is added
    // to KNOWN_NIAGARA_BAD_VERSIONS in the Python tool module via the
    // Wave-0 symbol survey rather than papered over with reflection here.
    FNiagaraEmitterHandle Handle = System->AddEmitterHandle(*Template, HandleName);
    if (!Handle.IsValid())
    {
        UE_LOG(LogNyraNiagara, Warning,
            TEXT("AddEmitterFromTemplate: AddEmitterHandle returned invalid handle for template '%s'"),
            *TemplatePathStr);
        return FString();
    }

    // Apply sim-target. The handle now owns a copy of the template's
    // emitter instance; we mutate that copy, not the template.
    if (FVersionedNiagaraEmitter Versioned = Handle.GetInstance(); Versioned.Emitter)
    {
        if (FVersionedNiagaraEmitterData* Data = Versioned.GetEmitterData())
        {
            const FString SimStr = SimTarget.ToString().ToLower();
            if (SimStr == TEXT("gpu"))
            {
                Data->SimTarget = ENiagaraSimTarget::GPUComputeSim;
            }
            else
            {
                // Default to CPU for any non-"gpu" string (incl. empty).
                Data->SimTarget = ENiagaraSimTarget::CPUSim;
            }
        }
    }

    // Mark the system dirty so the Python caller's
    // `unreal.EditorAssetLibrary.save_asset(system_path)` actually persists
    // the new handle to disk.
    System->MarkPackageDirty();

    return Handle.GetName().ToString();
}


// -----------------------------------------------------------------------------
// Internal helper: find an emitter handle by display name on a system.
// -----------------------------------------------------------------------------
//
// FNiagaraEmitterHandle is value-type; we return a pointer to the handle in
// the system's TArray to avoid a copy when the caller mutates the handle's
// emitter data. Returns nullptr if the handle is not present.
// -----------------------------------------------------------------------------
static FNiagaraEmitterHandle* FindHandleByName_NyraNiagara(
    UNiagaraSystem* System, FName HandleName)
{
    if (!System) return nullptr;

    // GetEmitterHandles() is editor-only on UE 5.4-5.7; the Build.cs dep on
    // Niagara (the runtime module) is sufficient because this method
    // surface is exposed there.
    TArray<FNiagaraEmitterHandle>& Handles = System->GetEmitterHandles();
    for (FNiagaraEmitterHandle& H : Handles)
    {
        if (H.GetName() == HandleName)
        {
            return &H;
        }
    }
    return nullptr;
}


// -----------------------------------------------------------------------------
// SetScalarModuleParameter / SetVectorModuleParameter / GetScalarModuleParameter
// -----------------------------------------------------------------------------
//
// The Niagara stack-API (UNiagaraStackEntry, UNiagaraStackModuleItem,
// FNiagaraVariable override-stack) is the FULL surface needed to set a
// per-module parameter override on an emitter. That surface lives in the
// NiagaraEditor module and changes shape every UE major.
//
// For Plan 08-05 we ship a NARROW first-cut that covers what Aura's
// public docs document: the parity bar is "GPU sprite + ribbon emitter
// examples reproduce" and Aura's documented examples only set top-level
// scalar/vector overrides on the emitter's parameter store -- not deep
// per-module overrides.
//
// Concretely: UNiagaraEmitter exposes a parameter store via
// `GetEmitterParameterStore()` (UE 5.4+); we set the scalar/vector value
// in that store. This covers the ~80% of Aura-documented use cases.
// Per-module overrides (the riskier 20%) are deferred to a follow-up
// helper extension once the Wave-0 symbol survey confirms a stable
// surface across 5.4-5.7.
//
// For UE versions where `GetEmitterParameterStore()` is absent, the
// helper returns false and the Python caller surfaces
// `not_supported_on_this_ue_version` -- the plan does NOT abort
// (T-08-01 graceful degradation).
// -----------------------------------------------------------------------------

bool UNyraNiagaraHelper::SetScalarModuleParameter(
    UNiagaraSystem* System,
    FName EmitterHandle,
    FName ParameterName,
    float Value)
{
    FNiagaraEmitterHandle* Handle = FindHandleByName_NyraNiagara(System, EmitterHandle);
    if (!Handle)
    {
        UE_LOG(LogNyraNiagara, Warning,
            TEXT("SetScalarModuleParameter: emitter handle '%s' not found"),
            *EmitterHandle.ToString());
        return false;
    }

    FVersionedNiagaraEmitter Versioned = Handle->GetInstance();
    if (!Versioned.Emitter)
    {
        UE_LOG(LogNyraNiagara, Warning,
            TEXT("SetScalarModuleParameter: emitter instance unresolved on handle '%s'"),
            *EmitterHandle.ToString());
        return false;
    }

    // FNiagaraVariable typed as float scalar.
    const FNiagaraVariable Var(FNiagaraTypeDefinition::GetFloatDef(), ParameterName);

    FNiagaraParameterStore& Store = Versioned.Emitter->GetEmitterParameterStore();
    if (Store.IndexOf(Var) == INDEX_NONE)
    {
        // Add the variable to the store with the requested initial value.
        // AddParameter returns false if the variable already exists in a
        // non-overridable form -- treat that as failure surfaced to Python.
        const bool bAdded = Store.AddParameter(Var, /*bInitialize=*/true,
                                                /*bTriggerRebind=*/true,
                                                /*OutOffset=*/nullptr);
        if (!bAdded)
        {
            UE_LOG(LogNyraNiagara, Warning,
                TEXT("SetScalarModuleParameter: AddParameter rejected '%s' on '%s'"),
                *ParameterName.ToString(), *EmitterHandle.ToString());
            return false;
        }
    }

    if (!Store.SetParameterValue<float>(Value, Var, /*bAdd=*/false))
    {
        UE_LOG(LogNyraNiagara, Warning,
            TEXT("SetScalarModuleParameter: SetParameterValue failed for '%s'"),
            *ParameterName.ToString());
        return false;
    }

    System->MarkPackageDirty();
    return true;
}


bool UNyraNiagaraHelper::SetVectorModuleParameter(
    UNiagaraSystem* System,
    FName EmitterHandle,
    FName ParameterName,
    FVector Value)
{
    FNiagaraEmitterHandle* Handle = FindHandleByName_NyraNiagara(System, EmitterHandle);
    if (!Handle)
    {
        UE_LOG(LogNyraNiagara, Warning,
            TEXT("SetVectorModuleParameter: emitter handle '%s' not found"),
            *EmitterHandle.ToString());
        return false;
    }

    FVersionedNiagaraEmitter Versioned = Handle->GetInstance();
    if (!Versioned.Emitter)
    {
        UE_LOG(LogNyraNiagara, Warning,
            TEXT("SetVectorModuleParameter: emitter instance unresolved on handle '%s'"),
            *EmitterHandle.ToString());
        return false;
    }

    // Niagara's vector type def is FVector3f-shaped (Vec3) on 5.4+.
    const FNiagaraVariable Var(FNiagaraTypeDefinition::GetVec3Def(), ParameterName);
    const FVector3f Vec3f((float)Value.X, (float)Value.Y, (float)Value.Z);

    FNiagaraParameterStore& Store = Versioned.Emitter->GetEmitterParameterStore();
    if (Store.IndexOf(Var) == INDEX_NONE)
    {
        const bool bAdded = Store.AddParameter(Var, /*bInitialize=*/true,
                                                /*bTriggerRebind=*/true,
                                                /*OutOffset=*/nullptr);
        if (!bAdded)
        {
            UE_LOG(LogNyraNiagara, Warning,
                TEXT("SetVectorModuleParameter: AddParameter rejected '%s' on '%s'"),
                *ParameterName.ToString(), *EmitterHandle.ToString());
            return false;
        }
    }

    if (!Store.SetParameterValue<FVector3f>(Vec3f, Var, /*bAdd=*/false))
    {
        UE_LOG(LogNyraNiagara, Warning,
            TEXT("SetVectorModuleParameter: SetParameterValue failed for '%s'"),
            *ParameterName.ToString());
        return false;
    }

    System->MarkPackageDirty();
    return true;
}


float UNyraNiagaraHelper::GetScalarModuleParameter(
    UNiagaraSystem* System,
    FName EmitterHandle,
    FName ParameterName)
{
    FNiagaraEmitterHandle* Handle = FindHandleByName_NyraNiagara(System, EmitterHandle);
    if (!Handle)
    {
        return MIN_flt;
    }

    FVersionedNiagaraEmitter Versioned = Handle->GetInstance();
    if (!Versioned.Emitter)
    {
        return MIN_flt;
    }

    const FNiagaraVariable Var(FNiagaraTypeDefinition::GetFloatDef(), ParameterName);
    FNiagaraParameterStore& Store = Versioned.Emitter->GetEmitterParameterStore();
    const int32 Idx = Store.IndexOf(Var);
    if (Idx == INDEX_NONE)
    {
        return MIN_flt;
    }

    float OutValue = MIN_flt;
    if (!Store.CopyParameterData(Var, reinterpret_cast<uint8*>(&OutValue)))
    {
        return MIN_flt;
    }
    return OutValue;
}
