# NYRA — Unreal Engine 5 Plugin

Free UE5 plugin (Fab distribution) that drives the user's Claude subscription
via three-process architecture. See `.planning/PROJECT.md` for the full vision.

## Phase 1 Scope

Plugin shell + three-process IPC skeleton on UE 5.6. No subscription driving yet
(Phase 2). Modules:

- `NyraEditor` (Editor-only, PostEngineInit): Slate chat panel, WebSocket client,
  NyraHost supervisor, `Nyra.Dev.*` console commands.
- `NyraRuntime` (Runtime, Default): empty stub. Future home of runtime-world
  hooks.

## Build

1. Open `TestProject/TestProject.uproject` — UE prompts to rebuild the plugin
   the first time.
2. Compile succeeds → plugin appears under `Edit -> Plugins -> AI -> NYRA`.
3. Chat tab: `Tools -> NYRA -> Chat` (added in Plan 04).

## Dependencies

- UE 5.6 (Phase 1 locked; UE 5.4/5.5/5.7 CI in Phase 2 per D-03)
- MSVC v143 (Visual Studio 2022 17.8+)
- Windows 10 22H2+ / Windows 11

## Binary artefacts

See `docs/BINARY_DISTRIBUTION.md`. In short: CPython + llama-server.exe are
fetched by `prebuild.ps1` (Plan 06) into `Binaries/Win64/NyraHost/` and
`Binaries/Win64/NyraInfer/` — those directories are .gitignored but staged
by `NyraEditor.Build.cs` as `RuntimeDependencies`.
