# NYRA Binary Distribution Strategy

**Locked in Phase 1 Plan 03.** Revisit in Phase 8 before Fab submission.

## The Problem

NYRA ships ~200 MB of non-UE binary artefacts:

- `Plugins/NYRA/Binaries/Win64/NyraHost/cpython/` — python-build-standalone CPython 3.12 Windows x64 (~120 MB installed)
- `Plugins/NYRA/Binaries/Win64/NyraHost/wheels/` — pre-resolved wheel cache for Phase 1 deps (~10 MB)
- `Plugins/NYRA/Binaries/Win64/NyraInfer/cuda/llama-server.exe` (~25 MB)
- `Plugins/NYRA/Binaries/Win64/NyraInfer/vulkan/llama-server.exe` (~20 MB)
- `Plugins/NYRA/Binaries/Win64/NyraInfer/cpu/llama-server.exe` (~15 MB)

Three options considered:

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| Commit via Git LFS | Reproducible; Fab-CI friendly | Requires LFS pointer config; free LFS quotas small | Phase 2 migration target (escape hatch) |
| Bootstrap-downloaded on first launch | Small repo; user-visible progress | Offline-hostile; first-launch 200 MB hit; trust issue on enterprise | Rejected |
| **Build-time downloaded by prebuild.ps1** | Small repo; dev machine fetches once; developer-facing | Requires PowerShell on Windows build hosts | **CHOSEN for Phase 1** |

**Chosen approach:** Build-time download via prebuild.ps1.

## Phase 1 Implementation

1. `TestProject/Plugins/NYRA/prebuild.ps1` (created in Plan 06) reads a manifest:

   ```
   TestProject/Plugins/NYRA/Source/NyraHost/assets-manifest.json
   ```

   which lists `{url, sha256, dest}` triples for each artefact.

2. `NyraEditor.Build.cs` invokes `prebuild.ps1` via an `ExternalDependencies`
   entry OR a conditional-on-missing-files pre-build step in a custom
   `NyraEditor.Target.cs` override.

3. After prebuild, `RuntimeDependencies.Add(...)` includes every file under
   `Binaries/Win64/NyraHost/` and `Binaries/Win64/NyraInfer/` for packaging.

The `assets-manifest.json` is the single source of truth for artefact URLs + SHA256
verification. Plan 06 authors `prebuild.ps1` and the first version of the manifest;
Plan 08 extends the manifest with `llama-server.exe` entries.

## Phase 8 Migration (Fab Prep — Git LFS escape hatch)

Switch to Git LFS with tracked `.gitattributes`:

```
Plugins/NYRA/Binaries/Win64/NyraHost/cpython/** filter=lfs diff=lfs merge=lfs -text
Plugins/NYRA/Binaries/Win64/NyraInfer/** filter=lfs diff=lfs merge=lfs -text
```

Rationale: Fab packaging pipeline must reproduce builds without external
network fetches; Git LFS gives us this. The `prebuild.ps1` path remains
functional (dev convenience) but CI switches to LFS-checkout.

## Security notes

- Every asset entry in `assets-manifest.json` MUST carry a SHA256 pinned at
  planning time; `prebuild.ps1` refuses to stage a mismatched file.
- Primary URLs point to upstream hosts (HuggingFace CDN for Gemma/CPython,
  GitHub Releases for llama.cpp). `prebuild.ps1` supports a `fallback_url`
  per entry pointing at a NYRA-hosted mirror.
- Artefacts are never executed during prebuild — they are unpacked to
  `Binaries/Win64/` only. First execution happens at UE editor runtime when
  the supervisor spawns NyraHost / NyraInfer.

## Sizes (for README + Fab disclosure)

| Artefact | Compressed download | Installed |
| --- | --- | --- |
| python-build-standalone CPython 3.12 | ~35 MB | ~120 MB |
| Wheel cache (Phase 1 deps) | ~10 MB | ~10 MB |
| llama-server.exe (CUDA) | ~25 MB | ~25 MB |
| llama-server.exe (Vulkan) | ~20 MB | ~20 MB |
| llama-server.exe (CPU) | ~15 MB | ~15 MB |
| **Total plugin install size** | — | **~190 MB** |

Gemma 3 4B QAT Q4_0 GGUF (3.16 GB) is downloaded on-demand at runtime, NOT via
prebuild.ps1 — see Plan 09.
