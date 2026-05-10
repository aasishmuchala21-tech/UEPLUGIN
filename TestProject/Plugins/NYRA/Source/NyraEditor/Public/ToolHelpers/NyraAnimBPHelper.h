// Copyright NYRA. All rights reserved.
// SPDX-License-Identifier: MIT
//
// Plan 08-07 / PARITY-07 — C++ helper UCLASS that exposes UE's AnimBlueprint
// AnimGraph authoring surface (state machines + states + transitions) to the
// NyraHost Python sidecar through the standard `unreal.NyraAnimBPHelper.*`
// Python reflection surface.
//
// UE Python does NOT directly reach AnimGraph node classes
// (UAnimGraphNode_StateMachineBase, UAnimGraphNode_StateResult,
// UAnimStateTransitionNode) in 5.4-5.7; those types live in editor-only
// AnimGraph + AnimGraphRuntime modules with no Python reflection. NyraHost
// cannot author AnimBP graphs without a thin native helper. This UCLASS is
// that helper. NyraHost calls it as:
//
//     unreal.NyraAnimBPHelper.add_state_machine(abp, "Locomotion", Vec(0,0))
//     unreal.NyraAnimBPHelper.add_state(abp, "Locomotion", "Idle", Vec(0,0))
//     unreal.NyraAnimBPHelper.add_transition(abp, "Locomotion", "Idle", "Walk")
//
// Per PLAN.md §"C++ Helper Surface" + RESEARCH.md §A3.
//
// Per CONTEXT.md LOCKED-10 the orchestrator (NOT this commit) is responsible
// for adding "AnimGraph" + "AnimGraphRuntime" + "BlueprintGraph" to
// NyraEditor.Build.cs's PrivateDependencyModuleNames in a single batched
// commit at end-of-wave.

#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "Animation/AnimBlueprint.h"
#include "NyraAnimBPHelper.generated.h"

/**
 * Editor-only helper that NyraHost (Python) calls via UCLASS reflection to
 * mutate AnimBlueprint AnimGraphs (state-machines, states, transitions).
 * All methods are static and BlueprintCallable so the Python binding
 * generator produces `unreal.NyraAnimBPHelper.<method>()` callsites without
 * an instance.
 *
 * MinimalAPI is intentional — only the reflection-visible surface needs to
 * be exported. The implementation lives entirely in the .cpp.
 *
 * Out-of-scope per CONTEXT.md: custom AnimNode generation. This helper only
 * mutates state-machine + state + transition graphs; it does NOT generate
 * new AnimNode C++ classes. That work goes through PARITY-02.
 */
UCLASS(MinimalAPI)
class UNyraAnimBPHelper : public UObject
{
	GENERATED_BODY()

public:
	/**
	 * Add a state machine node to the AnimBP's primary AnimGraph.
	 *
	 * @param AnimBP       The target UAnimBlueprint. Must be non-null and
	 *                     have a valid AnimGraph (created by AnimBlueprintFactory).
	 * @param MachineName  Desired display name for the state machine.
	 *                     If a state machine with this name already exists
	 *                     it is returned (idempotent, BL-05 alignment).
	 * @param NodePos      Graph-space position for the new node.
	 *
	 * @return The created (or existing) state machine's name as an FString.
	 *         Empty string on failure (e.g. AnimBP has no AnimGraph yet,
	 *         AnimGraph module unavailable on this UE version).
	 */
	UFUNCTION(BlueprintCallable, Category = "Nyra|AnimBP", meta = (ScriptMethod))
	static FString AddStateMachine(
		UAnimBlueprint* AnimBP,
		FName MachineName,
		FVector2D NodePos);

	/**
	 * Add a state to a state machine inside the AnimBP.
	 *
	 * @param AnimBP       The target UAnimBlueprint.
	 * @param MachineName  Name of an existing state machine (created via
	 *                     AddStateMachine).
	 * @param StateName    Desired display name for the new state. If a
	 *                     state with this name already exists in the
	 *                     machine it is returned (idempotent).
	 * @param NodePos      Graph-space position for the new node.
	 *
	 * @return The created (or existing) state's name as an FString.
	 *         Empty string on failure (machine not found, state-graph
	 *         unavailable, etc).
	 */
	UFUNCTION(BlueprintCallable, Category = "Nyra|AnimBP", meta = (ScriptMethod))
	static FString AddState(
		UAnimBlueprint* AnimBP,
		FName MachineName,
		FName StateName,
		FVector2D NodePos);

	/**
	 * Add a transition between two existing states inside a state machine.
	 *
	 * @param AnimBP       The target UAnimBlueprint.
	 * @param MachineName  Name of the parent state machine.
	 * @param FromState    Name of the source state.
	 * @param ToState      Name of the destination state.
	 *
	 * @return true if the transition node was created (or already existed
	 *         with the same source/destination — idempotent). false if the
	 *         machine or either state could not be located, or the AnimGraph
	 *         module is unavailable on this UE version.
	 */
	UFUNCTION(BlueprintCallable, Category = "Nyra|AnimBP", meta = (ScriptMethod))
	static bool AddTransition(
		UAnimBlueprint* AnimBP,
		FName MachineName,
		FName FromState,
		FName ToState);
};
