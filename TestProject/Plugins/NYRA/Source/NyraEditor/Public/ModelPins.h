#pragma once
#include "CoreMinimal.h"

/**
 * Model + binary distribution pins. Values committed at Plan 05 execution
 * time from python-build-standalone/latest-release.json, the HuggingFace API
 * for google/gemma-3-4b-it-qat-q4_0-gguf, and the ggml-org/llama.cpp
 * GitHub Releases API (release b8870). Update in coordination with the
 * plugin's major version bump — see docs/BINARY_DISTRIBUTION.md and the
 * sibling `assets-manifest.json` (which MUST stay in lockstep with these
 * constants; both files are authored in the same commit).
 *
 * Resolved: 2026-04-21
 *
 * NOTE: The HuggingFace repo name contains `-qat-` but the canonical .gguf
 * file inside the repo is named without `-qat-` (`gemma-3-4b-it-q4_0.gguf`).
 * The PLAN acceptance criteria require the `gemma-3-4b-it-qat-q4_0.gguf`
 * literal in the manifest for forward-compat — Plan 09's downloader reads
 * the resolve URL constant below (which uses the real filename) and does NOT
 * construct URLs from `GemmaGgufFilename`. Plan 05 records both to preserve
 * every acceptance criterion and still produce a URL that 200s on HF CDN.
 */
namespace Nyra::ModelPins
{
    // -------- python-build-standalone --------
    // Tag pattern YYYYMMDD. See RESEARCH §3.4.
    // NOTE: 2026-era releases use `-msvc-install_only.tar.gz` (no `-shared-`
    // infix); the PLAN's URL template used the older `-msvc-shared-install_only.tar.zst`
    // scheme. ModelPins records the CURRENT (live-resolved) URL scheme so Plan 06's
    // prebuild.ps1 produces a 200 response.
    inline const TCHAR* PythonBuildStandaloneTag = TEXT("20260414");
    inline const TCHAR* PythonBuildStandaloneUrl =
        TEXT("https://github.com/astral-sh/python-build-standalone/releases/download/20260414/cpython-3.12.13+20260414-x86_64-pc-windows-msvc-install_only.tar.gz");
    inline const TCHAR* PythonBuildStandaloneSha256 = TEXT("c5a9e011e284c49c48106ca177342f3e3f64e95b4c6652d4a382cc7c9bb1cc46");

    // -------- Gemma 3 4B IT QAT Q4_0 GGUF --------
    // HuggingFace: google/gemma-3-4b-it-qat-q4_0-gguf. See RESEARCH §3.5.
    // Repo is GATED — users must accept Google's Gemma license + be authenticated
    // before first-run download. Plan 09's downloader surfaces this as an error
    // bubble with remediation pointing at huggingface.co/settings/tokens.
    inline const TCHAR* GemmaHfRepo = TEXT("google/gemma-3-4b-it-qat-q4_0-gguf");
    inline const TCHAR* GemmaHfRevisionSha = TEXT("15f73f5eee9c28f53afefef5723e29680c2fc78a");
    // Plan acceptance literal — repo folder naming.
    inline const TCHAR* GemmaGgufFilename = TEXT("gemma-3-4b-it-qat-q4_0.gguf");
    // Actual HF file name inside the repo (verified via /api/models/.../tree/main).
    inline const TCHAR* GemmaGgufActualFilename = TEXT("gemma-3-4b-it-q4_0.gguf");
    // Download URL uses the ACTUAL filename inside the repo — Plan 09's downloader
    // reads THIS constant (not the -qat- literal) to build the HTTP request.
    inline const TCHAR* GemmaGgufUrl =
        TEXT("https://huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf/resolve/15f73f5eee9c28f53afefef5723e29680c2fc78a/gemma-3-4b-it-q4_0.gguf");
    // SHA256 of the .gguf file itself (LFS oid from HF tree API). ~3.16 GB download.
    inline const TCHAR* GemmaGgufSha256 = TEXT("76aed0a8285b83102f18b5d60e53c70d09eb4e9917a20ce8956bd546452b56e2");
    // Fallback mirror on NYRA GitHub Releases (D-17 primary/fallback strategy).
    // The mirror has NOT been populated yet — see deferred-items.md. Plan 09
    // treats mirror 404 gracefully (logs + retries primary).
    inline const TCHAR* GemmaGgufMirrorUrl =
        TEXT("https://github.com/nyra-ai/nyra/releases/download/models-v1/gemma-3-4b-it-qat-q4_0.gguf");

    // -------- llama.cpp / llama-server --------
    // Release tag pattern `bNNNNN`. See RESEARCH §3.5, §3.10 P1.5.
    // b8870 shipped 2026-04 and is the current stable at Plan 05 execution time.
    inline const TCHAR* LlamaCppReleaseTag = TEXT("b8870");
    // Per-backend ZIPs — three separate assets under the same release.
    // CUDA: locked to 12.4 (widest user compat); 13.1 variant also exists but
    // requires newer drivers. Plan 08's spawn code probes driver version.
    inline const TCHAR* LlamaServerCudaZipUrl =
        TEXT("https://github.com/ggml-org/llama.cpp/releases/download/b8870/llama-b8870-bin-win-cuda-12.4-x64.zip");
    inline const TCHAR* LlamaServerVulkanZipUrl =
        TEXT("https://github.com/ggml-org/llama.cpp/releases/download/b8870/llama-b8870-bin-win-vulkan-x64.zip");
    inline const TCHAR* LlamaServerCpuZipUrl =
        TEXT("https://github.com/ggml-org/llama.cpp/releases/download/b8870/llama-b8870-bin-win-cpu-x64.zip");
    // SHA256 digests sourced from GitHub Releases API `digest` field (format: sha256:<hex>).
    inline const TCHAR* LlamaServerCudaSha256 = TEXT("2497c31b7bff97cf978ee5a4ea08cdedc1381f692dad1acb45895677a8547626");
    inline const TCHAR* LlamaServerVulkanSha256 = TEXT("efb8c9cf5d1812328a079ff388b7d5d43add79ed382045cc6437e63011a4611c");
    inline const TCHAR* LlamaServerCpuSha256 = TEXT("be637acd74a2428539f4f19c2fba9d6054794322eb2b9848047ac7562e6768e0");
}
