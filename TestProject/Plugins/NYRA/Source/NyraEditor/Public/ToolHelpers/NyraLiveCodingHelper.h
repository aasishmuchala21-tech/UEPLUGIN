// Copyright NYRA. All rights reserved.
// SPDX-License-Identifier: MIT
//
// Plan 08-02 / PARITY-02 — C++ helper UCLASS that exposes UE's Live Coding +
// Hot Reload subsystems to the NyraHost Python sidecar through the standard
// `unreal.NyraLiveCodingHelper.*` Python reflection surface.
//
// UE Python does not directly expose ILiveCodingModule or IHotReloadInterface
// in 5.4-5.7. NyraHost cannot trigger a recompile without a thin native
// helper. This UCLASS is that helper. NyraHost calls it as:
//
//     unreal.NyraLiveCodingHelper.trigger_live_coding_compile()
//     unreal.NyraLiveCodingHelper.trigger_hot_reload("NyraEditor")
//     unreal.NyraLiveCodingHelper.get_last_compile_output()
//
// Per PLAN.md §"C++ Helper Surface" + RESEARCH.md §A6.
//
// Per CONTEXT.md LOCKED-10 the orchestrator (NOT this commit) is responsible
// for adding "LiveCoding" + "HotReload" to NyraEditor.Build.cs's
// PrivateDependencyModuleNames in a single batched commit at end-of-wave.

#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "NyraLiveCodingHelper.generated.h"

/**
 * Editor-only helper that NyraHost (Python) calls via UCLASS reflection to
 * trigger UE Live Coding compiles and Hot Reload fallbacks. All methods are
 * static and BlueprintCallable so the Python binding generator produces
 * `unreal.NyraLiveCodingHelper.<method>()` callsites without an instance.
 *
 * MinimalAPI is intentional — only the reflection-visible surface needs to
 * be exported. The implementation lives entirely in the .cpp.
 */
UCLASS(MinimalAPI)
class UNyraLiveCodingHelper : public UObject
{
	GENERATED_BODY()

public:
	/**
	 * Trigger an asynchronous Live Coding compile of the patchable modules.
	 * Returns true if the compile was successfully *started* (not necessarily
	 * succeeded — Live Coding compiles are asynchronous and the result is
	 * surfaced through the Live Coding output log; NyraHost reads that log
	 * via GetLastCompileOutput()). Returns false if the LiveCoding module
	 * is not loaded / the API is unavailable on this UE version (in which
	 * case the Python tool falls back to TriggerHotReload).
	 */
	UFUNCTION(BlueprintCallable, Category = "Nyra|LiveCoding", meta = (ScriptMethod))
	static bool TriggerLiveCodingCompile();

	/**
	 * Trigger a synchronous Hot Reload for the given module. Returns true if
	 * the reload completed without exception (Hot Reload is the fallback path
	 * for UE versions where Live Coding is unreliable per T-08-03).
	 *
	 * @param ModuleName  Module to reload, e.g. "NyraEditor". Empty FName
	 *                    triggers a full editor Hot Reload.
	 */
	UFUNCTION(BlueprintCallable, Category = "Nyra|LiveCoding", meta = (ScriptMethod))
	static bool TriggerHotReload(FName ModuleName);

	/**
	 * Best-effort string of the last compile log captured by this helper.
	 * NyraHost passes the returned string through `_parse_compile_errors`
	 * (which delegates to `blueprint_debug._explain_error_pattern`) to
	 * surface MSVC/clang/LNK/UHT errors back to the LLM.
	 *
	 * On UE versions where the Live Coding output device cannot be tapped,
	 * returns an empty string — the Python tool degrades gracefully to
	 * `compile_errors=[]` rather than asserting on the buffer shape.
	 */
	UFUNCTION(BlueprintCallable, Category = "Nyra|LiveCoding", meta = (ScriptMethod))
	static FString GetLastCompileOutput();
};
