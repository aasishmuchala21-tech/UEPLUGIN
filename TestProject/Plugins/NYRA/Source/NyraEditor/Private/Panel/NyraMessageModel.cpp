// =============================================================================
// NyraMessageModel.cpp  (Phase 1 Plan 12 -- chat panel streaming integration)
// =============================================================================
//
// The model is header-only (inline AppendDelta + Finalize). This .cpp exists
// solely to give UBT a translation unit anchored to the header so the module
// compile graph explicitly references NyraMessageModel.h. Do not add logic
// here -- if FNyraMessage grows helpers, prefer inline in the header so
// Slate widget row generation (hot path) stays inlineable.
// =============================================================================

#include "Panel/NyraMessageModel.h"
