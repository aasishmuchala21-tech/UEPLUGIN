<#
.SYNOPSIS
  Fetches NYRA plugin binary artefacts per assets-manifest.json.
  Idempotent: skips entries whose dest file already exists with matching SHA256.

.DESCRIPTION
  Reads assets-manifest.json (authored in Plan 05), downloads each of:
    - python_build_standalone (CPython 3.12 Windows x64, D-13)
    - llama_server_cuda       (llama.cpp CUDA 12.4 build, D-18)
    - llama_server_vulkan     (llama.cpp Vulkan build, D-18)
    - llama_server_cpu        (llama.cpp CPU build, D-18)
  Verifies each archive against the pinned SHA256, then extracts to
  the dest folder relative to the plugin root.

  Gemma GGUF is NOT a prebuild artefact — it downloads at runtime via
  Plan 09 (see assets-manifest.json::gemma_model_note).

.USAGE
  PowerShell -ExecutionPolicy Bypass -File prebuild.ps1

.NOTES
  This script is Windows-only (PowerShell + Invoke-WebRequest). It is
  NOT executed as part of pytest verification on dev machines; it runs
  once on a dev's Windows box (or on Windows CI) before packaging the
  plugin for Fab submission.
#>
param(
    [string]$ManifestPath = "$PSScriptRoot\Source\NyraHost\assets-manifest.json",
    [string]$PluginRoot = "$PSScriptRoot"
)

$ErrorActionPreference = "Stop"
$manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json

function Test-Sha256($Path, $ExpectedHex) {
    if (-not (Test-Path $Path)) { return $false }
    $actual = (Get-FileHash $Path -Algorithm SHA256).Hash.ToLower()
    return $actual -eq $ExpectedHex.ToLower()
}

function Fetch-Asset($Name, $Entry, $PluginRoot) {
    $destDir = Join-Path $PluginRoot $Entry.dest
    if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Force -Path $destDir | Out-Null }

    $url = $Entry.url
    if ($url -like "*TODO_RESOLVE_AT_BUILD*") {
        Write-Warning "[$Name] manifest has unresolved URL placeholder; skipping"
        return
    }

    $filename = [System.IO.Path]::GetFileName($url)
    $tmpPath = Join-Path $env:TEMP "nyra-prebuild-$Name-$filename"

    if (-not (Test-Sha256 $tmpPath $Entry.sha256)) {
        Write-Host "[$Name] Downloading $url"
        Invoke-WebRequest -Uri $url -OutFile $tmpPath -UseBasicParsing
    } else {
        Write-Host "[$Name] Cached in $tmpPath"
    }
    if (-not (Test-Sha256 $tmpPath $Entry.sha256)) {
        throw "[$Name] SHA256 mismatch after download"
    }

    Write-Host "[$Name] Extracting to $destDir"
    if ($filename -like "*.tar.zst") {
        # Requires zstd in PATH on the dev machine
        & zstd -d -o (Join-Path $env:TEMP "nyra-prebuild-$Name.tar") $tmpPath
        tar -xf (Join-Path $env:TEMP "nyra-prebuild-$Name.tar") -C $destDir
    } elseif ($filename -like "*.zip") {
        Expand-Archive -Path $tmpPath -DestinationPath $destDir -Force
    } elseif ($filename -like "*.tar.gz" -or $filename -like "*.tgz") {
        tar -xzf $tmpPath -C $destDir
    } else {
        Copy-Item $tmpPath -Destination (Join-Path $destDir $filename) -Force
    }
}

Fetch-Asset "python_build_standalone" $manifest.python_build_standalone $PluginRoot
Fetch-Asset "llama_server_cuda" $manifest.llama_server_cuda $PluginRoot
Fetch-Asset "llama_server_vulkan" $manifest.llama_server_vulkan $PluginRoot
Fetch-Asset "llama_server_cpu" $manifest.llama_server_cpu $PluginRoot

Write-Host "[NYRA prebuild] done."
