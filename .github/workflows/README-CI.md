# NYRA Plugin Multi-Version CI

GitHub Actions workflow for building the NYRA plugin across Unreal Engine
5.4, 5.5, 5.6, and 5.7 on a self-hosted Windows runner.

## Trigger

- `push` to `main` branch
- `pull_request` (runs on contributor forks with read-only token — no secrets)

## Matrix

| UE version | VS toolchain | Notes |
|-----------|-------------|-------|
| 5.4 | VS2022 17.8 | LTS baseline |
| 5.5 | VS2022 17.8 | Wide deploy |
| 5.6 | VS2022 17.10 | Current stable |
| 5.7 | VS2022 17.11 | Rolling; comment out if < 4 weeks post-GA |

`fail-fast: false` — one cell failure does not cancel others.

## Prerequisites (Runner)

See `.github/workflows/README-CI.md` for full provisioning runbook.
Briefly:

- Windows 11, UE 5.4.4 / 5.5.4 / 5.6.1 / 5.7.X installed under `C:\EpicGames\UE_5.X\`
- Visual Studio 2022 Community with "Game development with C++" workload
- Python 3.12 (64-bit) matching the python-build-standalone version
- GitHub Actions runner registered with labels: `self-hosted,Windows,unreal`
- Runner runs as a Windows service (`svc.cmd install/start`)

## Build steps

1. `actions/checkout@v4` with `lfs: true`
2. `RunUAT.bat BuildPlugin -Plugin=<repo>/TestProject/Plugins/NYRA/NYRA.uplugin -Package=<repo>/Artifacts/UE_<ver> -TargetPlatforms=Win64 -Unattended -NoP4`
3. `UnrealEditor-Cmd.exe TestProject.uproject -ExecCmds="Automation RunTests Nyra;Quit" -unattended -nopause -nullrhi -testexit="Automation Test Queue Empty" -log=NyraAutomation-UE<ver>.log`

## Artifacts

Each matrix cell uploads:

- `Artifacts/UE_<ver>/` — compiled plugin binaries (per engine version)
- `NyraAutomation-UE<ver>.log` — Automation runner output

## Local reproduce

```powershell
# From the runner host, run one UE version manually:
C:\EpicGames\UE_5.6\Engine\Build\BatchFiles\RunUAT.bat BuildPlugin `
  -Plugin=$env:GITHUB_WORKSPACE\TestProject\Plugins\NYRA\NYRA.uplugin `
  -Package=$env:GITHUB_WORKSPACE\Artifacts\UE_5.6 `
  -TargetPlatforms=Win64 -Unattended -NoP4
```

## UE 5.7 deferral rule (D-15)

If UE 5.7 has not reached General Availability or is < 4 weeks post-release
at plan-execution time, comment out the `'5.7'` line in
`strategy.matrix.ue-version` and open a follow-up MR to re-enable it once
Epic publishes the stable release.