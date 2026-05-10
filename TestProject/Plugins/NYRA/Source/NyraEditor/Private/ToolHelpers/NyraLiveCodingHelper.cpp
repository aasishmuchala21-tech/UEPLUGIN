// Copyright NYRA. All rights reserved.
// SPDX-License-Identifier: MIT
//
// Implementation of UNyraLiveCodingHelper. See header for surface contract.
//
// Build dependencies (orchestrator-batched per LOCKED-10):
//   PrivateDependencyModuleNames += "LiveCoding"  // ILiveCodingModule
//   PrivateDependencyModuleNames += "HotReload"   // IHotReloadInterface

#include "ToolHelpers/NyraLiveCodingHelper.h"

#include "Modules/ModuleManager.h"
#include "Misc/OutputDeviceRedirector.h"
#include "Misc/ScopeLock.h"

// LiveCoding module — UE 5.4+ exposes ILiveCodingModule. The header lives in
// the LiveCoding module's Public/ tree.
#if __has_include("ILiveCodingModule.h")
#include "ILiveCodingModule.h"
#define NYRA_HAS_LIVE_CODING 1
#else
#define NYRA_HAS_LIVE_CODING 0
#endif

// HotReload — fallback path. The interface lives in the HotReload module on
// 5.4-5.6; Epic deprecated the umbrella header on some 5.7 previews, so we
// __has_include both paths.
#if __has_include("Misc/HotReloadInterface.h")
#include "Misc/HotReloadInterface.h"
#define NYRA_HAS_HOT_RELOAD 1
#elif __has_include("HotReloadInterface.h")
#include "HotReloadInterface.h"
#define NYRA_HAS_HOT_RELOAD 1
#else
#define NYRA_HAS_HOT_RELOAD 0
#endif

namespace
{
	/**
	 * FOutputDevice that captures Live Coding log lines into a 4 KB ring
	 * buffer so NyraHost can fetch the last compile output via Python.
	 *
	 * The capture is tap-once / read-many: GetLastCompileOutput() returns
	 * a snapshot copy without flushing the buffer. Buffered through a
	 * critical section so concurrent log emission + Python reads don't
	 * shred the FString.
	 */
	class FNyraLiveCodingTap : public FOutputDevice
	{
	public:
		static FNyraLiveCodingTap& Get()
		{
			static FNyraLiveCodingTap Instance;
			return Instance;
		}

		void EnsureRegistered()
		{
			if (bRegistered) { return; }
			if (GLog != nullptr)
			{
				GLog->AddOutputDevice(this);
				bRegistered = true;
			}
		}

		virtual void Serialize(const TCHAR* V, ELogVerbosity::Type Verbosity, const FName& Category) override
		{
			// Only retain Live Coding / HotReload-categorised lines and any
			// MSVC/clang error shapes so the buffer doesn't fill with
			// unrelated editor spam.
			const FString Line(V);
			if (Category == FName(TEXT("LogLiveCoding"))
				|| Category == FName(TEXT("LogHotReload"))
				|| Line.Contains(TEXT("error C"))
				|| Line.Contains(TEXT("error LNK"))
				|| Line.Contains(TEXT("UnrealHeaderTool")))
			{
				FScopeLock Lock(&BufferGuard);
				Buffer.Append(Line);
				Buffer.AppendChar(TEXT('\n'));
				// Cap at ~4 KB; lop off the oldest half when we cross.
				if (Buffer.Len() > 4096)
				{
					Buffer = Buffer.Right(2048);
				}
			}
		}

		FString Snapshot()
		{
			FScopeLock Lock(&BufferGuard);
			return Buffer;
		}

	private:
		FNyraLiveCodingTap() = default;
		bool bRegistered = false;
		FCriticalSection BufferGuard;
		FString Buffer;
	};
}

bool UNyraLiveCodingHelper::TriggerLiveCodingCompile()
{
	FNyraLiveCodingTap::Get().EnsureRegistered();

#if NYRA_HAS_LIVE_CODING
	if (ILiveCodingModule* LiveCoding = FModuleManager::GetModulePtr<ILiveCodingModule>(TEXT("LiveCoding")))
	{
		// LiveCoding->Compile() kicks off an async compile. The return value is
		// best-effort — false means "could not start the compile" (Live Coding
		// disabled in editor prefs, or no patchable modules). Errors flow
		// through GLog and are captured by FNyraLiveCodingTap above.
		return LiveCoding->Compile();
	}
#endif
	// LiveCoding not present on this UE version — caller should fall back.
	return false;
}

bool UNyraLiveCodingHelper::TriggerHotReload(FName ModuleName)
{
	FNyraLiveCodingTap::Get().EnsureRegistered();

#if NYRA_HAS_HOT_RELOAD
	if (IHotReloadInterface* HotReload = FModuleManager::GetModulePtr<IHotReloadInterface>(TEXT("HotReload")))
	{
		// DoHotReloadFromEditor is the canonical entry point; signature is
		// stable across 5.4-5.7 even though the umbrella include path
		// drifted. Pass EHotReloadFlags::None to mirror the editor-button
		// behaviour rather than forcing a rebuild.
		HotReload->DoHotReloadFromEditor(EHotReloadFlags::None);
		(void)ModuleName; // Reserved — current API is editor-wide.
		return true;
	}
#endif
	(void)ModuleName;
	return false;
}

FString UNyraLiveCodingHelper::GetLastCompileOutput()
{
	return FNyraLiveCodingTap::Get().Snapshot();
}
