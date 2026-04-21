#pragma once

// Phase 1 Plan 03 Task 5 creates a minimal Rule-3 stub so that
// NyraIntegrationSpec.cpp's #include "NyraTestFixtures.h" resolves before
// Plan 01 (Wave 0 test scaffold) lands. Plan 01 will replace this file with
// the full fixture set declaring:
//   namespace Nyra::Tests { class FNyraTempDir; class FNyraTestClock; ... }
//
// The Nyra.Plugin.ModulesLoad spec below does not use any fixture helpers —
// it only uses FModuleManager directly — so this empty stub is sufficient
// for Plan 03's compile gate.

#include "CoreMinimal.h"
