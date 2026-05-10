// Copyright NYRA. All rights reserved.
// SPDX-License-Identifier: MIT
//
// Plan 08-07 / PARITY-07 — Implementation of UNyraAnimBPHelper.
//
// AnimGraph node spawning lives in editor-only modules (AnimGraph,
// AnimGraphRuntime, BlueprintGraph). This .cpp is the only place Python
// touches those classes — every Python entrypoint goes through one of the
// three static methods declared in NyraAnimBPHelper.h.
//
// Defensive coding (PATTERNS.md S5): every AnimGraph type access is guarded.
// Missing graphs / null skeletons / unsupported UE versions return empty
// FString / false rather than crashing the editor. The Python tool
// (animbp_tools.py) inspects the return value and surfaces a clean
// NyraToolResult.err to the LLM.
//
// Per CONTEXT.md LOCKED-10 the orchestrator adds the matching Build.cs
// dependencies (AnimGraph, AnimGraphRuntime, BlueprintGraph) in a single
// batched commit at end-of-wave; this file SHOULD NOT modify Build.cs.

#include "ToolHelpers/NyraAnimBPHelper.h"

#include "Animation/AnimBlueprint.h"
#include "Animation/AnimBlueprintGeneratedClass.h"
#include "AnimGraphNode_StateMachineBase.h"
#include "AnimGraphNode_StateMachine.h"
#include "AnimGraphNode_StateResult.h"
#include "AnimStateNode.h"
#include "AnimStateTransitionNode.h"
#include "AnimationStateMachineGraph.h"
#include "AnimationStateMachineSchema.h"
#include "AnimationGraphSchema.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphPin.h"
#include "EdGraphSchema_K2.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"

DEFINE_LOG_CATEGORY_STATIC(LogNyraAnimBP, Log, All);

namespace NyraAnimBP_Detail
{
	/**
	 * Find the primary AnimGraph (the one named by UEdGraphSchema_K2::GN_AnimGraph)
	 * inside an AnimBlueprint. Returns nullptr if the AnimBP has no AnimGraph
	 * (which happens when the asset was created without AnimBlueprintFactory's
	 * default AnimGraph generation, or on UE versions where the schema constant
	 * is named differently).
	 */
	static UEdGraph* FindAnimGraph(UAnimBlueprint* AnimBP)
	{
		if (AnimBP == nullptr)
		{
			return nullptr;
		}

		// FunctionGraphs holds AnimGraphs alongside event graphs — we want the
		// graph whose schema is UAnimationGraphSchema. This survives schema
		// constant renames between 5.4 and 5.7.
		for (UEdGraph* Graph : AnimBP->FunctionGraphs)
		{
			if (Graph != nullptr && Graph->Schema != nullptr
				&& Graph->Schema->IsChildOf(UAnimationGraphSchema::StaticClass()))
			{
				return Graph;
			}
		}
		return nullptr;
	}

	/**
	 * Find a state-machine node by display name inside an AnimGraph. Returns
	 * nullptr if not found. Used by AddStateMachine for idempotency and by
	 * AddState / AddTransition to look up the parent machine.
	 */
	static UAnimGraphNode_StateMachineBase* FindStateMachineNode(
		UEdGraph* AnimGraph, FName MachineName)
	{
		if (AnimGraph == nullptr)
		{
			return nullptr;
		}
		for (UEdGraphNode* Node : AnimGraph->Nodes)
		{
			if (UAnimGraphNode_StateMachineBase* SMNode =
				Cast<UAnimGraphNode_StateMachineBase>(Node))
			{
				// State-machine nodes use the bound graph's name as the
				// display label — that's what users see in the editor.
				if (SMNode->EditorStateMachineGraph != nullptr
					&& SMNode->EditorStateMachineGraph->GetFName() == MachineName)
				{
					return SMNode;
				}
			}
		}
		return nullptr;
	}

	/**
	 * Find a state node by name inside a state-machine graph.
	 */
	static UAnimStateNode* FindStateNode(UEdGraph* StateMachineGraph, FName StateName)
	{
		if (StateMachineGraph == nullptr)
		{
			return nullptr;
		}
		for (UEdGraphNode* Node : StateMachineGraph->Nodes)
		{
			if (UAnimStateNode* StateNode = Cast<UAnimStateNode>(Node))
			{
				if (StateNode->GetStateName() == StateName.ToString()
					|| StateNode->GetFName() == StateName)
				{
					return StateNode;
				}
			}
		}
		return nullptr;
	}
}

// -----------------------------------------------------------------------------
// AddStateMachine
// -----------------------------------------------------------------------------

FString UNyraAnimBPHelper::AddStateMachine(
	UAnimBlueprint* AnimBP, FName MachineName, FVector2D NodePos)
{
	using namespace NyraAnimBP_Detail;

	if (AnimBP == nullptr)
	{
		UE_LOG(LogNyraAnimBP, Warning, TEXT("AddStateMachine: AnimBP is null"));
		return FString();
	}

	UEdGraph* AnimGraph = FindAnimGraph(AnimBP);
	if (AnimGraph == nullptr)
	{
		UE_LOG(LogNyraAnimBP, Warning,
			TEXT("AddStateMachine: AnimBP %s has no AnimGraph"),
			*AnimBP->GetName());
		return FString();
	}

	// BL-05 idempotency at the C++ layer: if a machine with this name
	// already exists, return its name rather than creating a duplicate.
	if (UAnimGraphNode_StateMachineBase* Existing =
		FindStateMachineNode(AnimGraph, MachineName))
	{
		return Existing->EditorStateMachineGraph != nullptr
			? Existing->EditorStateMachineGraph->GetName()
			: MachineName.ToString();
	}

	// Spawn the state-machine node via the K2 schema's templated helper —
	// this is the canonical path used by the AnimBP editor's "Add Node"
	// menu and survives the 5.4 → 5.7 schema refactors.
	UAnimGraphNode_StateMachine* SMNode =
		FEdGraphSchemaAction_K2NewNode::SpawnNode<UAnimGraphNode_StateMachine>(
			AnimGraph, /*FromPin=*/nullptr, NodePos, EK2NewNodeFlags::SelectNewNode);

	if (SMNode == nullptr)
	{
		UE_LOG(LogNyraAnimBP, Warning,
			TEXT("AddStateMachine: SpawnNode returned null"));
		return FString();
	}

	// Create + name the bound state-machine graph (this is what users see
	// in the AnimBP editor's "MyBlueprint" sidebar as the SM's label).
	if (SMNode->EditorStateMachineGraph == nullptr)
	{
		SMNode->EditorStateMachineGraph =
			FBlueprintEditorUtils::CreateNewGraph(
				SMNode,
				MachineName,
				UAnimationStateMachineGraph::StaticClass(),
				UAnimationStateMachineSchema::StaticClass());
	}
	else
	{
		// Rename the existing graph so the display name matches MachineName.
		SMNode->EditorStateMachineGraph->Rename(*MachineName.ToString(), SMNode);
	}

	// Persist the change so the next FindAnimGraph traversal sees it.
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(AnimBP);

	return SMNode->EditorStateMachineGraph != nullptr
		? SMNode->EditorStateMachineGraph->GetName()
		: MachineName.ToString();
}

// -----------------------------------------------------------------------------
// AddState
// -----------------------------------------------------------------------------

FString UNyraAnimBPHelper::AddState(
	UAnimBlueprint* AnimBP, FName MachineName, FName StateName, FVector2D NodePos)
{
	using namespace NyraAnimBP_Detail;

	if (AnimBP == nullptr)
	{
		return FString();
	}

	UEdGraph* AnimGraph = FindAnimGraph(AnimBP);
	UAnimGraphNode_StateMachineBase* SMNode = FindStateMachineNode(AnimGraph, MachineName);
	if (SMNode == nullptr || SMNode->EditorStateMachineGraph == nullptr)
	{
		UE_LOG(LogNyraAnimBP, Warning,
			TEXT("AddState: state machine %s not found in %s"),
			*MachineName.ToString(),
			AnimBP ? *AnimBP->GetName() : TEXT("<null>"));
		return FString();
	}

	UEdGraph* SMGraph = SMNode->EditorStateMachineGraph;

	// BL-05 idempotency: a state with this name in this machine wins.
	if (UAnimStateNode* Existing = FindStateNode(SMGraph, StateName))
	{
		return Existing->GetStateName();
	}

	UAnimStateNode* NewStateNode =
		FEdGraphSchemaAction_K2NewNode::SpawnNode<UAnimStateNode>(
			SMGraph, /*FromPin=*/nullptr, NodePos, EK2NewNodeFlags::SelectNewNode);

	if (NewStateNode == nullptr)
	{
		UE_LOG(LogNyraAnimBP, Warning, TEXT("AddState: SpawnNode returned null"));
		return FString();
	}

	// Set the state's display name. Different UE versions expose the setter
	// through different surfaces — we set the FName outright (which is the
	// underlying storage) and let the editor reconcile its label.
	NewStateNode->Rename(*StateName.ToString(), SMGraph);

	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(AnimBP);
	return NewStateNode->GetStateName();
}

// -----------------------------------------------------------------------------
// AddTransition
// -----------------------------------------------------------------------------

bool UNyraAnimBPHelper::AddTransition(
	UAnimBlueprint* AnimBP, FName MachineName, FName FromState, FName ToState)
{
	using namespace NyraAnimBP_Detail;

	if (AnimBP == nullptr)
	{
		return false;
	}

	UEdGraph* AnimGraph = FindAnimGraph(AnimBP);
	UAnimGraphNode_StateMachineBase* SMNode = FindStateMachineNode(AnimGraph, MachineName);
	if (SMNode == nullptr || SMNode->EditorStateMachineGraph == nullptr)
	{
		UE_LOG(LogNyraAnimBP, Warning,
			TEXT("AddTransition: state machine %s not found"),
			*MachineName.ToString());
		return false;
	}
	UEdGraph* SMGraph = SMNode->EditorStateMachineGraph;

	UAnimStateNode* SourceState = FindStateNode(SMGraph, FromState);
	UAnimStateNode* TargetState = FindStateNode(SMGraph, ToState);
	if (SourceState == nullptr || TargetState == nullptr)
	{
		UE_LOG(LogNyraAnimBP, Warning,
			TEXT("AddTransition: from=%s (%p) to=%s (%p) — one or both missing"),
			*FromState.ToString(), SourceState,
			*ToState.ToString(),   TargetState);
		return false;
	}

	// BL-05 idempotency: if the source already has a transition node into
	// the target, treat the call as success without spawning a duplicate.
	for (UEdGraphNode* Node : SMGraph->Nodes)
	{
		if (UAnimStateTransitionNode* Existing = Cast<UAnimStateTransitionNode>(Node))
		{
			if (Existing->GetPreviousState() == SourceState
				&& Existing->GetNextState() == TargetState)
			{
				return true;
			}
		}
	}

	// The state-machine schema knows how to wire a transition between two
	// states (and inserts the UAnimStateTransitionNode automatically). Using
	// TryCreateConnection instead of manually spawning + connecting keeps
	// us aligned with the AnimBP editor's drag-from-pin behaviour.
	const UAnimationStateMachineSchema* Schema =
		Cast<UAnimationStateMachineSchema>(SMGraph->GetSchema());
	if (Schema == nullptr)
	{
		UE_LOG(LogNyraAnimBP, Warning,
			TEXT("AddTransition: state-machine graph schema unavailable"));
		return false;
	}

	UEdGraphPin* OutPin = SourceState->GetOutputPin();
	UEdGraphPin* InPin  = TargetState->GetInputPin();
	if (OutPin == nullptr || InPin == nullptr)
	{
		UE_LOG(LogNyraAnimBP, Warning,
			TEXT("AddTransition: source/target pin missing"));
		return false;
	}

	const bool bConnected = Schema->TryCreateConnection(OutPin, InPin);
	if (!bConnected)
	{
		UE_LOG(LogNyraAnimBP, Warning,
			TEXT("AddTransition: TryCreateConnection refused %s -> %s"),
			*FromState.ToString(), *ToState.ToString());
		return false;
	}

	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(AnimBP);
	return true;
}
