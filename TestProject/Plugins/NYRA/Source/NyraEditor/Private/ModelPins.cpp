#include "ModelPins.h"
// ModelPins exposes compile-time constants only; no runtime logic here yet.
// Plan 09 (Gemma downloader) wires these into FHttpModule requests on the
// Python side via the assets-manifest.json mirror (see
// TestProject/Plugins/NYRA/Source/NyraHost/assets-manifest.json).
//
// The .cpp exists so the module links cleanly when other translation units
// import ModelPins.h via `#include "ModelPins.h"`. Because every constant in
// the header is `inline const TCHAR*` (C++17 ODR-safe), this .cpp contains
// no definitions — it is a linker anchor that keeps Unreal's UBT from
// complaining about an unused header in isolation builds and provides a
// deliberate touch-point for future runtime helpers (e.g., a future
// `Nyra::ModelPins::ValidateAssetManifest()` that asserts the sibling JSON
// stays in lockstep with the header).
