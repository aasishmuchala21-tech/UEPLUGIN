# NYRA Automation Tests

C++ UE Automation Spec suite for the NyraEditor module. All tests run under
`EAutomationTestFlags::EditorContext` (editor builds only) and are guarded by
`#if WITH_AUTOMATION_TESTS` so shipping builds emit no test code.

## Test paths

- `Nyra.Jsonrpc.*` — unit tests for JSON-RPC 2.0 envelope encode/decode (Plan 10)
- `Nyra.Markdown.*` — unit tests for the Slate markdown parser (Plan 11)
- `Nyra.Supervisor.*` — supervisor 3-in-60s policy w/ `FNyraTestClock` injection (Plan 10)
- `Nyra.Panel.*` — Slate widget / tab spawner tests (Plans 04, 12)
- `Nyra.Integration.*` — E2E handshake + auth, guarded by `ENABLE_NYRA_INTEGRATION_TESTS` (Plan 10)
- `Nyra.Plugin.ModulesLoad` — both NyraEditor and NyraRuntime IsModuleLoaded (Plan 03, shipped)

## Run

From the `TestProject/` directory on Windows:

```
UnrealEditor-Cmd.exe TestProject/TestProject.uproject \
    -ExecCmds="Automation RunTests Nyra;Quit" -unattended -nopause \
    -testexit="Automation Test Queue Empty"
```

Filter to a single spec by replacing `Nyra` with the full path, e.g.
`Automation RunTests Nyra.Jsonrpc`.

## Integration-test opt-in

Integration specs require a live NyraHost subprocess. Enable them by adding
the following to `TestProject.Target.cs` (Editor target):

```
GlobalDefinitions.Add("ENABLE_NYRA_INTEGRATION_TESTS=1");
```

Default: **off**. CI only flips the flag on the integration-ring job, not
the default unit-test job, so dev-laptop runs stay fast.

## Shared fixtures

`NyraTestFixtures.h` exports `namespace Nyra::Tests` with:

- `FNyraTempDir` — RAII temp directory under `Intermediate/NyraTests/<guid>/`
- `FNyraTestClock` — injectable monotonic clock for deterministic supervisor tests
- `WriteHandshakeFile(...)` — writes D-06-schema handshake JSON
- `MakeJsonRpcRequest(...)` — builds D-09-shape JSON-RPC 2.0 request envelope

All Wave 1–5 plans `#include "NyraTestFixtures.h"` instead of rolling their own.

## File map

| Spec file                    | Path                  | Owning plan(s) |
| ---------------------------- | --------------------- | -------------- |
| `NyraJsonRpcSpec.cpp`        | `Nyra.Jsonrpc.*`      | 10             |
| `NyraMarkdownSpec.cpp`       | `Nyra.Markdown.*`     | 11             |
| `NyraSupervisorSpec.cpp`     | `Nyra.Supervisor.*`   | 10             |
| `NyraPanelSpec.cpp`          | `Nyra.Panel.*`        | 04, 12         |
| `NyraIntegrationSpec.cpp`    | `Nyra.Integration.*`  | 10 (guarded) + `Nyra.Plugin.ModulesLoad` (03, shipped) |
| `NyraTestFixtures.{h,cpp}`   | shared helpers        | 01 (this plan) |
