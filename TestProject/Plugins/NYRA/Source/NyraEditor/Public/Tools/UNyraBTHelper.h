// SPDX-License-Identifier: MIT
// Copyright (c) NYRA contributors. PARITY-03 — Phase 8 Plan 08-03.
//
// UCLASS bridge from Python (`unreal.NyraBTHelper.*`) to the UE
// BehaviorTreeEditor module. EdGraph node spawn classes
// (UEdGraphNode_BehaviorTreeComposite/Task/Decorator) are not reflected
// to Python directly — this helper wraps the canonical 5.6 API surface
// so the Python mutator tools in nyrahost.tools.bt_tools can call:
//
//   unreal.NyraBTHelper.create_behavior_tree(asset_path, parent_class)
//   unreal.NyraBTHelper.add_composite_node(bt, "BTComposite_Sequence",
//                                          "Root", unreal.Vector2D(0,0))
//   unreal.NyraBTHelper.add_task_node(bt, "BTTask_MoveTo", parent, pos)
//   unreal.NyraBTHelper.add_decorator_node(bt, "BTDecorator_Blackboard",
//                                          target_name)
//   unreal.NyraBTHelper.set_blackboard_key(bb, "TargetActor", "Object")
//
// Each function logs via UE_LOG(LogNyra, ...) and returns failure as
// empty FString / false — never throws across the C++/Python boundary.
//
// NOTE: this header lives in NyraEditor/Public/Tools/ per orchestrator
// path direction (the plan's narrative referenced ToolHelpers/; the
// orchestrator authoritatively routed to Tools/ for filesystem
// consistency with the broader NyraEditor module layout).
#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "UObject/NoExportTypes.h"
#include "UNyraBTHelper.generated.h"

class UBehaviorTree;
class UBlackboardData;

/**
 * Result struct returned to Python from the BT mutator helpers.
 * Plain UStruct — UFUNCTION(BlueprintCallable) reflects this to the
 * `unreal.NyraBTAuthorResult` Python class automatically.
 *
 * Status values:
 *   "ok"                       — operation completed
 *   "parent_not_found"         — named parent node missing
 *   "class_not_found"          — UClass lookup failed for the supplied FName
 *   "graph_unavailable"        — BehaviorTreeGraph could not be created/edited
 *   "unsupported_on_version"   — UE 5.x API surface didn't match expectations
 *   "internal_error"           — caught exception or unexpected null
 */
USTRUCT(BlueprintType)
struct FNyraBTAuthorResult
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category="Nyra|BT")
	FString Status;

	UPROPERTY(BlueprintReadOnly, Category="Nyra|BT")
	FString NodeName;

	UPROPERTY(BlueprintReadOnly, Category="Nyra|BT")
	FString Detail;

	FNyraBTAuthorResult()
		: Status(TEXT("internal_error"))
		, NodeName(TEXT(""))
		, Detail(TEXT(""))
	{
	}
};

/**
 * UNyraBTHelper — UCLASS bridge for Python → BehaviorTree authoring.
 *
 * MinimalAPI: header is consumed by other modules only via reflection.
 * No DLL exports needed — all entry points are UFUNCTION.
 */
UCLASS(MinimalAPI, BlueprintType)
class UNyraBTHelper : public UObject
{
	GENERATED_BODY()

public:
	/**
	 * Create a new UBehaviorTree asset at the given content path.
	 *
	 * @param AssetPath        /Game/... target path (without extension)
	 * @param BlackboardPath   Optional /Game/... path to an existing
	 *                         UBlackboardData asset; empty FName for none.
	 * @return                 Result with Status="ok" + NodeName=AssetPath
	 *                         on success.
	 *
	 * Python: `unreal.NyraBTHelper.create_behavior_tree("/Game/AI/BT_X", "")`
	 */
	UFUNCTION(BlueprintCallable, Category="Nyra|BT", meta=(ScriptMethod, DisplayName="Create Behavior Tree"))
	static FNyraBTAuthorResult CreateBehaviorTree(const FString& AssetPath, const FString& BlackboardPath);

	/**
	 * Add a composite node (BTComposite_Selector / Sequence / SimpleParallel)
	 * to the BT root or under a named parent composite.
	 *
	 * @param BT               Target BT asset (loaded via EditorAssetLibrary).
	 * @param CompositeClass   FName of the composite class. Two formats accepted:
	 *                         - bare ("BTComposite_Sequence")
	 *                         - fully-qualified ("/Script/AIModule.BTComposite_Sequence")
	 * @param ParentName       "Root" (case-insensitive) or FName of an existing composite.
	 * @param NodePos          Editor-graph position (Vector2D).
	 * @return                 The created node's FName, or empty on failure.
	 *
	 * Python: `unreal.NyraBTHelper.add_composite_node(bt, "BTComposite_Sequence", "Root", unreal.Vector2D(0,0))`
	 */
	UFUNCTION(BlueprintCallable, Category="Nyra|BT", meta=(ScriptMethod, DisplayName="Add Composite Node"))
	static FString AddCompositeNode(
		UBehaviorTree* BT,
		FName CompositeClass,
		FName ParentName,
		FVector2D NodePos);

	/**
	 * Add a task node (BTTask_*) under a composite.
	 *
	 * @param BT          Target BT asset.
	 * @param TaskClass   FName like "BTTask_MoveTo" or fully-qualified path.
	 * @param ParentName  FName of the parent composite.
	 * @param NodePos     Editor-graph position.
	 * @return            Created node FName as FString, or empty on failure.
	 *
	 * Python: `unreal.NyraBTHelper.add_task_node(bt, "BTTask_MoveTo", "Sequence_0", unreal.Vector2D(0, 200))`
	 */
	UFUNCTION(BlueprintCallable, Category="Nyra|BT", meta=(ScriptMethod, DisplayName="Add Task Node"))
	static FString AddTaskNode(
		UBehaviorTree* BT,
		FName TaskClass,
		FName ParentName,
		FVector2D NodePos);

	/**
	 * Add a decorator (BTDecorator_*) onto an existing task or composite.
	 *
	 * @param BT               Target BT asset.
	 * @param DecoratorClass   FName like "BTDecorator_Blackboard".
	 * @param TargetNodeName   FName of the node to decorate.
	 * @return                 true on success.
	 *
	 * Python: `unreal.NyraBTHelper.add_decorator_node(bt, "BTDecorator_Blackboard", "MoveTo_0")`
	 */
	UFUNCTION(BlueprintCallable, Category="Nyra|BT", meta=(ScriptMethod, DisplayName="Add Decorator Node"))
	static bool AddDecoratorNode(
		UBehaviorTree* BT,
		FName DecoratorClass,
		FName TargetNodeName);

	/**
	 * Add or overwrite a key on a UBlackboardData asset.
	 *
	 * @param BB        Target BlackboardData asset.
	 * @param KeyName   Logical key name.
	 * @param KeyType   One of: Bool, Int, Float, String, Vector, Object.
	 * @return          true on success.
	 *
	 * Python: `unreal.NyraBTHelper.set_blackboard_key(bb, "TargetActor", "Object")`
	 */
	UFUNCTION(BlueprintCallable, Category="Nyra|BT", meta=(ScriptMethod, DisplayName="Set Blackboard Key"))
	static bool SetBlackboardKey(
		UBlackboardData* BB,
		FName KeyName,
		FName KeyType);
};
