// NYRACompat.h
// Phase 2 Wave 0 compatibility shim.
// Entries land as the four-version CI matrix surfaces drift (Plan 02-06).
// Every #if block MUST be <20 lines and tagged:
//   // NYRA_COMPAT: <reason>

#pragma once

#include "Runtime/Launch/Resources/Version.h"

// NYRA_UE_AT_LEAST(Major, Minor)
// True when compiled against ENGINE_VERSION >= specified (Major, Minor).
// Used to guard version-specific API calls across Plans 02-05, 02-06, 02-11.
#define NYRA_UE_AT_LEAST(Major, Minor) \
    (ENGINE_MAJOR_VERSION > (Major) || \
     (ENGINE_MAJOR_VERSION == (Major) && ENGINE_MINOR_VERSION >= (Minor)))

namespace NYRA::Compat
{
    // Phase 2 Wave 0: intentionally empty.
    // Entries land empirically after first four-version matrix run.
} // namespace NYRA::Compat