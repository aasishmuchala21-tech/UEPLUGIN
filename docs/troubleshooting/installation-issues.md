# Installation issues

## The installer won't run / SmartScreen flags it

NYRA is signed with an EV code-signing certificate (acquisition runbook in `legal/ev-cert-acquisition-runbook.md`). If you see an "Unrecognised app" SmartScreen warning, you almost certainly downloaded a pre-1.0 unsigned beta — pull the latest release from `nyra.ai/download` which is signed.

## "Plugin failed to load" on editor startup

1. Confirm your UE version is **5.4, 5.5, 5.6, or 5.7**. UE 5.3 is not supported.
2. Open `<Project>/Saved/Logs/NyraHost.log` — the first ERROR line tells you what failed.
3. Most common: `python.exe not found at Binaries/Win64/NyraHost/cpython/`. Run `prebuild.ps1` from the plugin folder once; it fetches CPython + llama.cpp builds.

## "Aura is installed but Aura.uplugin not found" / opposite-plugin loading

NYRA and Aura have separate `.uplugin` descriptors. They can coexist in the same project. If both panel tabs open they'll compete for the active conversation; close one at a time.

## Compiling from source

You don't need to compile NYRA — the installer bundles a packaged plugin. But if you want to: `RunUAT.bat BuildPlugin -Plugin=NYRA.uplugin -TargetPlatforms=Win64 -Unattended -NoP4` from a UE 5.6 source build.

## The plugin loads but no chat tab appears

`FNyraEditorModule::StartupModule` registers the **NYRA Chat** tab under **Tools menu → NYRA → Chat**. If it's missing:
- Verify the plugin is enabled in Edit → Plugins (search "NYRA").
- Restart the editor.
- If still missing, look for `[NYRA] NyraEditor module starting` in Output Log — absence means the module didn't even load.
