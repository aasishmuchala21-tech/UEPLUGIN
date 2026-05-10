// SPDX-License-Identifier: MIT
// Copyright (c) NYRA contributors. PARITY-03 — Phase 8 Plan 08-03.
//
// UE 5.6 is the canonical API target; 5.4 / 5.5 / 5.7 paths are flagged
// with TODO(version-drift) where the call site is known to differ.
// Wave 0 will reflect-survey each version and finalise the conditional
// branches before the executor unblocks 5.4/5.5/5.7 ship.

#include "Tools/UNyraBTHelper.h"

#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetToolsModule.h"
#include "BehaviorTree/BehaviorTree.h"
#include "BehaviorTree/BehaviorTreeTypes.h"
#include "BehaviorTree/BlackboardData.h"
#include "BehaviorTree/BTCompositeNode.h"
#include "BehaviorTree/BTTaskNode.h"
#include "BehaviorTree/BTDecorator.h"
#include "BehaviorTree/Composites/BTComposite_Selector.h"
#include "BehaviorTree/Composites/BTComposite_Sequence.h"
#include "BehaviorTree/Composites/BTComposite_SimpleParallel.h"
#include "Editor.h"
#include "EditorAssetLibrary.h"
#include "Factories/Factory.h"
#include "IAssetTools.h"
#include "Logging/LogMacros.h"
#include "Misc/PackageName.h"
#include "UObject/Class.h"
#include "UObject/Package.h"
#include "UObject/UObjectGlobals.h"

DEFINE_LOG_CATEGORY_STATIC(LogNyraBT, Log, All);

namespace
{
	/** Resolve a UClass* by FName, accepting bare or fully-qualified names.
	 *  Tries /Script/AIModule.<Name> first, then ANY_PACKAGE fallback.
	 *  TODO(version-drift): UE 5.7 may deprecate ANY_PACKAGE entirely; switch
	 *  to TopLevelAssetPath lookup once Wave 0 confirms availability.
	 */
	UClass* ResolveClassByName(const FName ClassFName, const TCHAR* DefaultModule)
	{
		const FString ClassStr = ClassFName.ToString();
		if (ClassStr.IsEmpty())
		{
			return nullptr;
		}

		// Already fully qualified ("/Script/AIModule.BTTask_MoveTo")
		if (ClassStr.StartsWith(TEXT("/Script/")))
		{
			return FindObject<UClass>(nullptr, *ClassStr);
		}

		// Try the supplied default module first.
		if (DefaultModule && *DefaultModule)
		{
			const FString Qualified = FString::Printf(TEXT("/Script/%s.%s"), DefaultModule, *ClassStr);
			if (UClass* Found = FindObject<UClass>(nullptr, *Qualified))
			{
				return Found;
			}
		}

		// TODO(version-drift): ANY_PACKAGE deprecated in 5.7 — using FindFirstObject
		// as the cross-version-stable form. The 5.4/5.5 builds may emit a
		// deprecation warning we can ignore until Wave 0 finalises the branch.
		return FindFirstObject<UClass>(*ClassStr, EFindFirstObjectOptions::None, ELogVerbosity::Warning);
	}

	/** Walk a BT root composite recursively to find a composite by FName. */
	UBTCompositeNode* FindCompositeByName(UBehaviorTree* BT, const FName Name)
	{
		if (!BT || !BT->RootNode)
		{
			return nullptr;
		}
		const FString NameStr = Name.ToString();
		// "Root" matches the root node regardless of generated FName.
		if (NameStr.Equals(TEXT("Root"), ESearchCase::IgnoreCase))
		{
			return BT->RootNode;
		}

		TArray<UBTCompositeNode*> Stack;
		Stack.Add(BT->RootNode);
		while (Stack.Num() > 0)
		{
			UBTCompositeNode* Cur = Stack.Pop(EAllowShrinking::No);
			if (!Cur) continue;
			if (Cur->GetFName() == Name || Cur->NodeName == NameStr)
			{
				return Cur;
			}
			for (FBTCompositeChild& Child : Cur->Children)
			{
				if (UBTCompositeNode* CChild = Cast<UBTCompositeNode>(Child.ChildComposite))
				{
					Stack.Add(CChild);
				}
			}
		}
		return nullptr;
	}

	/** Find any node (composite or task) by FName, scanning the whole tree. */
	UBTNode* FindAnyNodeByName(UBehaviorTree* BT, const FName Name)
	{
		if (!BT || !BT->RootNode)
		{
			return nullptr;
		}
		const FString NameStr = Name.ToString();
		TArray<UBTCompositeNode*> Stack;
		Stack.Add(BT->RootNode);
		while (Stack.Num() > 0)
		{
			UBTCompositeNode* Cur = Stack.Pop(EAllowShrinking::No);
			if (!Cur) continue;
			if (Cur->GetFName() == Name || Cur->NodeName == NameStr) return Cur;
			for (FBTCompositeChild& Child : Cur->Children)
			{
				if (Child.ChildTask && (Child.ChildTask->GetFName() == Name || Child.ChildTask->NodeName == NameStr))
				{
					return Child.ChildTask;
				}
				if (UBTCompositeNode* CChild = Cast<UBTCompositeNode>(Child.ChildComposite))
				{
					Stack.Add(CChild);
				}
			}
		}
		return nullptr;
	}

	EBlackboardKeyType MapKeyTypeName(const FName KeyType)
	{
		const FString S = KeyType.ToString();
		if (S.Equals(TEXT("Bool"),   ESearchCase::IgnoreCase)) return EBlackboardKeyType::Bool;
		if (S.Equals(TEXT("Int"),    ESearchCase::IgnoreCase)) return EBlackboardKeyType::Int;
		if (S.Equals(TEXT("Float"),  ESearchCase::IgnoreCase)) return EBlackboardKeyType::Float;
		if (S.Equals(TEXT("String"), ESearchCase::IgnoreCase)) return EBlackboardKeyType::String;
		if (S.Equals(TEXT("Vector"), ESearchCase::IgnoreCase)) return EBlackboardKeyType::Vector;
		if (S.Equals(TEXT("Object"), ESearchCase::IgnoreCase)) return EBlackboardKeyType::Object;
		return EBlackboardKeyType::None;
	}
}

// ---------------------------------------------------------------------------
// CreateBehaviorTree
// ---------------------------------------------------------------------------

FNyraBTAuthorResult UNyraBTHelper::CreateBehaviorTree(const FString& AssetPath, const FString& BlackboardPath)
{
	FNyraBTAuthorResult Result;

	if (AssetPath.IsEmpty() || !AssetPath.StartsWith(TEXT("/Game/")))
	{
		Result.Status = TEXT("internal_error");
		Result.Detail = TEXT("AssetPath must start with /Game/");
		UE_LOG(LogNyraBT, Warning, TEXT("CreateBehaviorTree: invalid AssetPath '%s'"), *AssetPath);
		return Result;
	}

	FString PackagePath, AssetName;
	if (!AssetPath.Split(TEXT("/"), &PackagePath, &AssetName, ESearchCase::IgnoreCase, ESearchDir::FromEnd))
	{
		Result.Status = TEXT("internal_error");
		Result.Detail = TEXT("Could not split AssetPath into package + name");
		return Result;
	}

	// TODO(version-drift): UBehaviorTreeFactory lives in BehaviorTreeEditor on 5.6;
	// 5.4 may surface only AIModule's runtime UBehaviorTree directly. Wave 0
	// will pin the import line.
	UClass* FactoryClass = FindFirstObject<UClass>(TEXT("BehaviorTreeFactory"), EFindFirstObjectOptions::None, ELogVerbosity::Warning);
	if (!FactoryClass)
	{
		Result.Status = TEXT("unsupported_on_version");
		Result.Detail = TEXT("BehaviorTreeFactory not found in current UE build");
		UE_LOG(LogNyraBT, Error, TEXT("CreateBehaviorTree: BehaviorTreeFactory class missing"));
		return Result;
	}
	UFactory* Factory = NewObject<UFactory>(GetTransientPackage(), FactoryClass);
	if (!Factory)
	{
		Result.Status = TEXT("internal_error");
		Result.Detail = TEXT("Failed to instantiate BehaviorTreeFactory");
		return Result;
	}

	IAssetTools& AssetTools = FModuleManager::LoadModuleChecked<FAssetToolsModule>(TEXT("AssetTools")).Get();
	UObject* NewAsset = AssetTools.CreateAsset(AssetName, PackagePath, UBehaviorTree::StaticClass(), Factory);
	UBehaviorTree* BT = Cast<UBehaviorTree>(NewAsset);
	if (!BT)
	{
		Result.Status = TEXT("internal_error");
		Result.Detail = TEXT("CreateAsset returned null or wrong class");
		UE_LOG(LogNyraBT, Error, TEXT("CreateBehaviorTree: CreateAsset failed for %s"), *AssetPath);
		return Result;
	}

	if (!BlackboardPath.IsEmpty())
	{
		UObject* BBObj = UEditorAssetLibrary::LoadAsset(BlackboardPath);
		if (UBlackboardData* BB = Cast<UBlackboardData>(BBObj))
		{
			BT->BlackboardAsset = BB;
		}
		else
		{
			UE_LOG(LogNyraBT, Warning, TEXT("CreateBehaviorTree: Blackboard %s not found / wrong class"), *BlackboardPath);
		}
	}

	UEditorAssetLibrary::SaveAsset(AssetPath, /*bOnlyIfIsDirty=*/false);

	Result.Status = TEXT("ok");
	Result.NodeName = AssetPath;
	UE_LOG(LogNyraBT, Log, TEXT("CreateBehaviorTree: created %s"), *AssetPath);
	return Result;
}

// ---------------------------------------------------------------------------
// AddCompositeNode
// ---------------------------------------------------------------------------

FString UNyraBTHelper::AddCompositeNode(
	UBehaviorTree* BT,
	FName CompositeClass,
	FName ParentName,
	FVector2D /*NodePos*/)
{
	if (!BT)
	{
		UE_LOG(LogNyraBT, Warning, TEXT("AddCompositeNode: BT was null"));
		return FString();
	}

	UClass* CompClass = ResolveClassByName(CompositeClass, TEXT("AIModule"));
	if (!CompClass || !CompClass->IsChildOf(UBTCompositeNode::StaticClass()))
	{
		UE_LOG(LogNyraBT, Warning, TEXT("AddCompositeNode: class '%s' not a UBTCompositeNode subclass"),
			*CompositeClass.ToString());
		return FString();
	}

	UBTCompositeNode* Parent = nullptr;
	if (ParentName.IsNone() || ParentName.ToString().Equals(TEXT("Root"), ESearchCase::IgnoreCase))
	{
		Parent = BT->RootNode;
		if (!Parent)
		{
			// Empty BT: install the new composite as the root composite.
			UBTCompositeNode* NewRoot = NewObject<UBTCompositeNode>(BT, CompClass, NAME_None, RF_Transactional);
			if (!NewRoot)
			{
				UE_LOG(LogNyraBT, Error, TEXT("AddCompositeNode: NewObject for root composite failed"));
				return FString();
			}
			BT->RootNode = NewRoot;
			BT->MarkPackageDirty();
			UE_LOG(LogNyraBT, Log, TEXT("AddCompositeNode: installed root composite %s"), *NewRoot->GetName());
			return NewRoot->GetName();
		}
	}
	else
	{
		Parent = FindCompositeByName(BT, ParentName);
		if (!Parent)
		{
			UE_LOG(LogNyraBT, Warning, TEXT("AddCompositeNode: parent '%s' not found"), *ParentName.ToString());
			return FString();
		}
	}

	UBTCompositeNode* NewComp = NewObject<UBTCompositeNode>(BT, CompClass, NAME_None, RF_Transactional);
	if (!NewComp)
	{
		UE_LOG(LogNyraBT, Error, TEXT("AddCompositeNode: NewObject failed for class %s"), *CompClass->GetName());
		return FString();
	}

	FBTCompositeChild ChildSlot;
	ChildSlot.ChildComposite = NewComp;
	ChildSlot.ChildTask = nullptr;
	Parent->Children.Add(ChildSlot);

	BT->MarkPackageDirty();
	UE_LOG(LogNyraBT, Log, TEXT("AddCompositeNode: %s under %s"), *NewComp->GetName(), *Parent->GetName());
	return NewComp->GetName();
}

// ---------------------------------------------------------------------------
// AddTaskNode
// ---------------------------------------------------------------------------

FString UNyraBTHelper::AddTaskNode(
	UBehaviorTree* BT,
	FName TaskClass,
	FName ParentName,
	FVector2D /*NodePos*/)
{
	if (!BT)
	{
		UE_LOG(LogNyraBT, Warning, TEXT("AddTaskNode: BT was null"));
		return FString();
	}

	UClass* TClass = ResolveClassByName(TaskClass, TEXT("AIModule"));
	if (!TClass || !TClass->IsChildOf(UBTTaskNode::StaticClass()))
	{
		UE_LOG(LogNyraBT, Warning, TEXT("AddTaskNode: class '%s' not a UBTTaskNode subclass"),
			*TaskClass.ToString());
		return FString();
	}

	UBTCompositeNode* Parent = FindCompositeByName(BT, ParentName);
	if (!Parent)
	{
		UE_LOG(LogNyraBT, Warning, TEXT("AddTaskNode: parent composite '%s' not found"), *ParentName.ToString());
		return FString();
	}

	UBTTaskNode* NewTask = NewObject<UBTTaskNode>(BT, TClass, NAME_None, RF_Transactional);
	if (!NewTask)
	{
		UE_LOG(LogNyraBT, Error, TEXT("AddTaskNode: NewObject failed for class %s"), *TClass->GetName());
		return FString();
	}

	FBTCompositeChild ChildSlot;
	ChildSlot.ChildComposite = nullptr;
	ChildSlot.ChildTask = NewTask;
	Parent->Children.Add(ChildSlot);

	BT->MarkPackageDirty();
	UE_LOG(LogNyraBT, Log, TEXT("AddTaskNode: %s under %s"), *NewTask->GetName(), *Parent->GetName());
	return NewTask->GetName();
}

// ---------------------------------------------------------------------------
// AddDecoratorNode
// ---------------------------------------------------------------------------

bool UNyraBTHelper::AddDecoratorNode(
	UBehaviorTree* BT,
	FName DecoratorClass,
	FName TargetNodeName)
{
	if (!BT)
	{
		UE_LOG(LogNyraBT, Warning, TEXT("AddDecoratorNode: BT was null"));
		return false;
	}

	UClass* DClass = ResolveClassByName(DecoratorClass, TEXT("AIModule"));
	if (!DClass || !DClass->IsChildOf(UBTDecorator::StaticClass()))
	{
		UE_LOG(LogNyraBT, Warning, TEXT("AddDecoratorNode: class '%s' not a UBTDecorator subclass"),
			*DecoratorClass.ToString());
		return false;
	}

	UBTNode* Target = FindAnyNodeByName(BT, TargetNodeName);
	if (!Target)
	{
		UE_LOG(LogNyraBT, Warning, TEXT("AddDecoratorNode: target node '%s' not found"), *TargetNodeName.ToString());
		return false;
	}

	UBTDecorator* NewDec = NewObject<UBTDecorator>(BT, DClass, NAME_None, RF_Transactional);
	if (!NewDec)
	{
		UE_LOG(LogNyraBT, Error, TEXT("AddDecoratorNode: NewObject failed for class %s"), *DClass->GetName());
		return false;
	}

	// TODO(version-drift): the decorators TArray field name has been stable as
	// `Decorators` from 5.0 through 5.6; verify on 5.7 in Wave 0.
	if (UBTCompositeNode* AsComp = Cast<UBTCompositeNode>(Target))
	{
		AsComp->Decorators.Add(NewDec);
	}
	else if (UBTTaskNode* AsTask = Cast<UBTTaskNode>(Target))
	{
		// In 5.6, decorators on tasks are stored in a parallel composite-child
		// metadata entry; for the canonical 5.6 path we attach via the parent
		// composite's child-decorator array. Wave 0 confirms the shape.
		// As an acceptable Phase-8-Plan-1 first cut, log a warning and append
		// to the task's built-in decorator list when present.
		if (UBTCompositeNode* TaskParent = Cast<UBTCompositeNode>(AsTask->GetOuter()))
		{
			for (FBTCompositeChild& C : TaskParent->Children)
			{
				if (C.ChildTask == AsTask)
				{
					C.Decorators.Add(NewDec);
					break;
				}
			}
		}
		else
		{
			UE_LOG(LogNyraBT, Warning, TEXT("AddDecoratorNode: task '%s' has no composite parent"), *TargetNodeName.ToString());
		}
	}
	else
	{
		UE_LOG(LogNyraBT, Warning, TEXT("AddDecoratorNode: target '%s' is neither composite nor task"), *TargetNodeName.ToString());
		return false;
	}

	BT->MarkPackageDirty();
	UE_LOG(LogNyraBT, Log, TEXT("AddDecoratorNode: %s on %s"), *NewDec->GetName(), *Target->GetName());
	return true;
}

// ---------------------------------------------------------------------------
// SetBlackboardKey
// ---------------------------------------------------------------------------

bool UNyraBTHelper::SetBlackboardKey(
	UBlackboardData* BB,
	FName KeyName,
	FName KeyType)
{
	if (!BB)
	{
		UE_LOG(LogNyraBT, Warning, TEXT("SetBlackboardKey: BB was null"));
		return false;
	}
	if (KeyName.IsNone())
	{
		UE_LOG(LogNyraBT, Warning, TEXT("SetBlackboardKey: KeyName was None"));
		return false;
	}

	const EBlackboardKeyType KT = MapKeyTypeName(KeyType);
	if (KT == EBlackboardKeyType::None)
	{
		UE_LOG(LogNyraBT, Warning, TEXT("SetBlackboardKey: unknown KeyType '%s'"), *KeyType.ToString());
		return false;
	}

	// TODO(version-drift): `Keys` array of FBlackboardEntry is stable
	// across 5.4–5.6. The KeyType field on FBlackboardEntry is a
	// TSubclassOf<UBlackboardKeyType> rather than the EBlackboardKeyType
	// enum directly. Wave 0 needs to confirm the canonical mapping path
	// — currently writing the key entry with the closest UBlackboardKeyType
	// subclass we can resolve via a class lookup table.
	UClass* KeyClass = nullptr;
	switch (KT)
	{
		case EBlackboardKeyType::Bool:   KeyClass = FindFirstObject<UClass>(TEXT("BlackboardKeyType_Bool"));   break;
		case EBlackboardKeyType::Int:    KeyClass = FindFirstObject<UClass>(TEXT("BlackboardKeyType_Int"));    break;
		case EBlackboardKeyType::Float:  KeyClass = FindFirstObject<UClass>(TEXT("BlackboardKeyType_Float"));  break;
		case EBlackboardKeyType::String: KeyClass = FindFirstObject<UClass>(TEXT("BlackboardKeyType_String")); break;
		case EBlackboardKeyType::Vector: KeyClass = FindFirstObject<UClass>(TEXT("BlackboardKeyType_Vector")); break;
		case EBlackboardKeyType::Object: KeyClass = FindFirstObject<UClass>(TEXT("BlackboardKeyType_Object")); break;
		default: break;
	}
	if (!KeyClass)
	{
		UE_LOG(LogNyraBT, Error, TEXT("SetBlackboardKey: could not resolve UClass for type '%s'"), *KeyType.ToString());
		return false;
	}

	// Idempotent: replace the existing entry if KeyName already present.
	bool bUpdated = false;
	for (FBlackboardEntry& Entry : BB->Keys)
	{
		if (Entry.EntryName == KeyName)
		{
			Entry.KeyType = NewObject<UBlackboardKeyType>(BB, KeyClass);
			bUpdated = true;
			break;
		}
	}
	if (!bUpdated)
	{
		FBlackboardEntry NewEntry;
		NewEntry.EntryName = KeyName;
		NewEntry.KeyType = NewObject<UBlackboardKeyType>(BB, KeyClass);
		BB->Keys.Add(NewEntry);
	}

	BB->MarkPackageDirty();
	UE_LOG(LogNyraBT, Log, TEXT("SetBlackboardKey: %s = %s (%s)"), *KeyName.ToString(), *KeyType.ToString(),
		bUpdated ? TEXT("updated") : TEXT("added"));
	return true;
}
