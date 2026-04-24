---
phase: 02-subscription-bridge-ci-matrix
plan: 01
slug: four-version-ci-matrix-bootstrap
type: execute
wave: 0
depends_on: []
autonomous: false
tdd: false
requirements: [PLUG-04]
files_modified:
  - .github/workflows/plugin-matrix.yml
  - .github/workflows/pytest-host.yml
  - .github/workflows/README-CI.md
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraCompatSpec.cpp
research_refs: [§5.1, §5.2, §5.3, §5.5, §10.2, §11 Wave 0]
context_refs: [D-12, D-13, D-14, D-15]
phase0_clearance_required: false
user_setup:
  - service: github-actions-self-hosted-runner
    why: "UE plugin builds cannot run on GitHub-hosted runners; four-version matrix is PLUG-04 non-negotiable"
    env_vars: []
    dashboard_config:
      - task: "Provision self-hosted Windows 11 runner with UE 5.4.4 / 5.5.4 / 5.6.1 / 5.7.X installed under C:\\EpicGames\\UE_5.X\\"
        location: "Windows workstation (founder's dev machine or cloud Windows VM)"
      - task: "Register runner to repo with labels self-hosted,Windows,unreal"
        location: "GitHub → repo Settings → Actions → Runners → New self-hosted runner"
      - task: "Install Visual Studio 2022 Community with C++ Game Dev workload + Python 3.12 + pip install -r requirements-dev.lock"
        location: "Runner host"
must_haves:
  truths:
    - "Self-hosted Windows runner registered to repo with label 'self-hosted,Windows,unreal'"
    - "plugin-matrix.yml workflow triggers on push-to-main and on pull_request; matrix = ['5.4','5.5','5.6','5.7']"
    - "fail-fast: false — one UE version red does not cancel other three"
    - "BuildPlugin target invoked via RunUAT.bat (NOT BuildCookRun) — we ship a plugin binary, not a project cook"
    - "UnrealEditor-Cmd.exe runs Automation RunTests Nyra headless with -nullrhi"
    - "Artifacts uploaded per UE version: Artifacts/UE_{version}/ + NyraAutomation-UE{version}.log"
    - "pytest-host.yml runs python -m pytest -v on the NyraHost package once per PR (version-agnostic)"
    - "NYRACompat.h exports NYRA_UE_AT_LEAST(Major, Minor) macro wrapping ENGINE_MAJOR_VERSION / ENGINE_MINOR_VERSION comparison"
    - "NyraCompatSpec.cpp has at least one smoke-test It block asserting NYRA_UE_AT_LEAST(5, 6) is true on the dev host"
  artifacts:
    - path: .github/workflows/plugin-matrix.yml
      provides: "Four-version UE BuildPlugin + Automation matrix"
      exports: ["compile-and-test job", "matrix.ue-version", "artifact upload"]
    - path: .github/workflows/pytest-host.yml
      provides: "Single-run pytest on NyraHost (version-agnostic)"
      exports: ["pytest-single job"]
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h
      provides: "Version-guard macro + empty NYRA::Compat namespace (populated empirically in Plan 02-06)"
      exports: ["NYRA_UE_AT_LEAST", "namespace NYRA::Compat"]
    - path: .github/workflows/README-CI.md
      provides: "Runner provisioning + local-reproduce instructions"
  key_links:
    - from: .github/workflows/plugin-matrix.yml
      to: RunUAT.bat BuildPlugin on C:\EpicGames\UE_${{ matrix.ue-version }}\
      via: "shell: cmd step invoking Engine\\Build\\BatchFiles\\RunUAT.bat"
      pattern: "BuildPlugin.*UE_\\${{ matrix\\.ue-version }}"
    - from: .github/workflows/plugin-matrix.yml
      to: UE Automation Spec headless run
      via: "UnrealEditor-Cmd.exe TestProject.uproject -ExecCmds=Automation RunTests Nyra;Quit -unattended -nullrhi"
      pattern: "Automation RunTests Nyra"
---

<objective>
Wave 0 CI infrastructure: the four-version UE build matrix that every
subsequent Phase 2 plan depends on, plus the empty `NYRA::Compat::`
shim header that Plans 02-05/02-06 will populate with empirical drift
entries once the matrix runs for real.

Per CONTEXT.md:
- D-12: self-hosted Windows runner is the ONLY viable option
- D-13: shim discipline — small `#if` blocks, tagged comments
- D-14: `fail-fast: false` so one bad cell doesn't block others
- D-15: UE 5.7 deferral rule (plan for 4 cells, operator may drop to 3)

This is a CHECKPOINT plan because runner provisioning requires the
founder to physically register the Windows machine; Claude produces
the workflow YAMLs + the compat header, then checkpoints for the
founder to run the `./config.cmd` runner-registration step.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/REQUIREMENTS.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/02-subscription-bridge-ci-matrix/02-CONTEXT.md
@.planning/phases/02-subscription-bridge-ci-matrix/02-RESEARCH.md

<interfaces>
<!-- From TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs — module structure already established in Phase 1 -->
<!-- From UE 5.6 source: Runtime/Launch/Resources/Version.h exports ENGINE_MAJOR_VERSION, ENGINE_MINOR_VERSION, ENGINE_PATCH_VERSION -->

The compat macro the header exports (for downstream Plans 02-05, 02-06, 02-11):

```cpp
// TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h
#pragma once
#include "Runtime/Launch/Resources/Version.h"

#define NYRA_UE_AT_LEAST(Major, Minor) \
    (ENGINE_MAJOR_VERSION > (Major) || \
     (ENGINE_MAJOR_VERSION == (Major) && ENGINE_MINOR_VERSION >= (Minor)))

namespace NYRA::Compat
{
    // Phase 2 Wave 0: intentionally empty.
    // Entries land as the CI matrix surfaces drift (Plan 02-06).
    // Every #if block MUST be <20 lines and tagged:
    //   // NYRA_COMPAT: <reason>
}
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Author plugin-matrix.yml + pytest-host.yml CI workflows</name>
  <files>.github/workflows/plugin-matrix.yml, .github/workflows/pytest-host.yml, .github/workflows/README-CI.md</files>
  <action>
    Write .github/workflows/plugin-matrix.yml exactly per RESEARCH §5.3 shape:
    - name: Plugin Multi-Version CI
    - triggers: push (branches main) + pull_request
    - single job "compile-and-test" with runs-on: [self-hosted, Windows, unreal]
    - strategy: fail-fast: false, matrix: ue-version: ['5.4','5.5','5.6','5.7']
    - steps: actions/checkout@v4 with lfs:true; then two shell:cmd steps —
      (a) "C:\\EpicGames\\UE_${{ matrix.ue-version }}\\Engine\\Build\\BatchFiles\\RunUAT.bat" BuildPlugin with -Plugin=%GITHUB_WORKSPACE%\\TestProject\\Plugins\\NYRA\\NYRA.uplugin -Package=%GITHUB_WORKSPACE%\\Artifacts\\UE_${{ matrix.ue-version }} -TargetPlatforms=Win64 -Unattended -NoP4;
      (b) "C:\\EpicGames\\UE_${{ matrix.ue-version }}\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe" %GITHUB_WORKSPACE%\\TestProject\\TestProject.uproject -ExecCmds="Automation RunTests Nyra;Quit" -unattended -nopause -nullrhi -testexit="Automation Test Queue Empty" -log=NyraAutomation-UE${{ matrix.ue-version }}.log
    - final step: actions/upload-artifact@v4 with if:always() uploading Artifacts/UE_${{ matrix.ue-version }}/ + NyraAutomation-UE${{ matrix.ue-version }}.log

    Write pytest-host.yml with a single pytest-single job on [self-hosted,Windows,unreal] running: cd TestProject\\Plugins\\NYRA\\Source\\NyraHost && python -m pytest -v. This job is version-agnostic (not matrixed).

    Write .github/workflows/README-CI.md documenting:
    - Self-hosted runner requirements (Windows 11, UE 5.4.4/5.5.4/5.6.1/5.7.X installed under C:\\EpicGames\\UE_5.X\\, VS 2022 C++ Game Dev workload, Python 3.12)
    - Label registration command: ./config.cmd --url https://github.com/&lt;org&gt;/&lt;repo&gt; --token &lt;token&gt; --labels self-hosted,Windows,unreal
    - Local-reproduce recipe (run the RunUAT command manually for one UE version)
    - UE 5.7 deferral rule (D-15): if 5.7 not GA at phase-execution time, comment the '5.7' line of the matrix and open follow-up MR when available
    - Critical settings rationale: fail-fast:false, -nullrhi, BuildPlugin (not BuildCookRun)
    Do NOT use long repo paths — the runner's C:\\A\\_work\\ prefix forces short names (RESEARCH §5.1).
  </action>
  <verify>
    <automated>node -e "const y=require('fs').readFileSync('.github/workflows/plugin-matrix.yml','utf8'); const c=['5.4','5.5','5.6','5.7'].every(v=>y.includes(v)); const f=y.includes('fail-fast: false'); const b=y.includes('BuildPlugin'); const n=y.includes('-nullrhi'); if(!c||!f||!b||!n){console.error('Missing:',{c,f,b,n}); process.exit(1)} console.log('OK')"</automated>
  </verify>
  <done>
    - .github/workflows/plugin-matrix.yml exists with all four UE versions in matrix, fail-fast:false, BuildPlugin invocation, UnrealEditor-Cmd Automation step, artifact upload
    - .github/workflows/pytest-host.yml exists with single pytest-single job
    - .github/workflows/README-CI.md documents runner provisioning
  </done>
</task>

<task type="auto">
  <name>Task 2: Create NYRACompat.h + smoke-test spec</name>
  <files>TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraCompatSpec.cpp</files>
  <action>
    Create NYRACompat.h exactly per the interfaces block above: the NYRA_UE_AT_LEAST(Major,Minor) macro and an EMPTY namespace NYRA::Compat with two comment lines (Wave 0 intentionally empty, reason tag format). No #if blocks yet — those emerge from the empirical first-matrix run in Plan 02-06.

    Create NyraCompatSpec.cpp following Phase 1's spec style (see NyraJsonRpcSpec.cpp for the canonical BEGIN_DEFINE_SPEC / IMPLEMENT macro layout): single Describe block "Nyra.Compat.Macro" with one It block "recognises 5.6+ on dev host" that asserts NYRA_UE_AT_LEAST(5, 6) is true. This spec has zero functional value YET — its role is to guarantee the header compiles cleanly on every matrix cell. When CI lights up on 5.4/5.5/5.7, compile failures surface here first. Plan 02-06 extends this spec with one It block per drift entry populated.
  </action>
  <verify>
    <automated>test -f TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h && grep -q "NYRA_UE_AT_LEAST" TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h && grep -q "namespace NYRA::Compat" TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h && grep -q "Nyra.Compat.Macro" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraCompatSpec.cpp</automated>
  </verify>
  <done>
    - NYRACompat.h exports NYRA_UE_AT_LEAST macro + empty NYRA::Compat namespace with format-tag comment
    - NyraCompatSpec.cpp has Nyra.Compat.Macro Describe with at least one It block
    - Both files compile cleanly on UE 5.6 dev host (confirmed at plan-execute time by Phase 1 Automation runner)
  </done>
</task>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task 3: FOUNDER — Provision + register self-hosted Windows runner</name>
  <what-built>
    Claude has authored plugin-matrix.yml + pytest-host.yml + README-CI.md + NYRACompat.h + NyraCompatSpec.cpp. Before these workflows execute, the repo needs a self-hosted runner.
  </what-built>
  <how-to-verify>
    On the Windows 11 dev workstation (or provisioned cloud Windows VM):

    1. Install UE 5.4.4, 5.5.4, 5.6.1, and 5.7.X via Epic Games Launcher under C:\\EpicGames\\UE_5.X\\ (one folder per minor). If UE 5.7 is &lt;4 weeks post-release or not GA, comment out the '5.7' line in plugin-matrix.yml.strategy.matrix.ue-version and open a follow-up MR per CONTEXT.md D-15.
    2. Install Visual Studio 2022 Community with "Game development with C++" workload.
    3. Install Python 3.12.X (64-bit) matching the python-build-standalone version Phase 1 D-13 pins.
    4. GitHub → repo Settings → Actions → Runners → New self-hosted runner → Windows → x64. Download the runner tarball.
    5. Unpack to C:\\actions-runner\\ and run: .\\config.cmd --url https://github.com/&lt;org&gt;/&lt;repo&gt; --token &lt;GIVEN_TOKEN&gt; --labels self-hosted,Windows,unreal --unattended --replace
    6. Install as a service: .\\svc.cmd install, then .\\svc.cmd start
    7. Smoke-test: make a trivial commit on a feature branch that does NOT touch NYRA source; confirm plugin-matrix.yml triggers and reaches the "BuildPlugin" step for at least one UE version (OK if it fails with "plugin X not found" errors — we only need the job to pick up the label).
  </how-to-verify>
  <resume-signal>
    Reply with "runner-provisioned" once the runner appears Online in GitHub Actions Runners settings AND plugin-matrix.yml has triggered at least one matrix cell in a feature-branch push. If UE 5.7 was deferred, reply "runner-provisioned-5.7-deferred" and note the planned follow-up MR date.
  </resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| GitHub ↔ self-hosted runner | CI workflow YAML runs arbitrary code on the founder's dev workstation; pull_request from forks must NOT trigger it |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-01-01 | Tampering / Elevation of Privilege | plugin-matrix.yml `pull_request` trigger on external forks | mitigate | Use `pull_request` (not `pull_request_target`) so fork PRs run only with read-only token + do NOT access secrets. Founder reviews PR diff before approving first CI run from any new contributor. Document in README-CI.md. |
| T-02-01-02 | Information Disclosure | Artifacts upload may expose `Saved/NYRA/logs/` | mitigate | Artifact upload path is explicitly `Artifacts/UE_{ver}/` + `NyraAutomation-UE{ver}.log` — does NOT include Saved/NYRA/. README-CI.md pins this. |
| T-02-01-03 | Denial of Service | One runner, four matrix cells serialize (no parallelism) | accept | Solo dev, single runner is v1 budget; cloud Windows VM backup is v1.1. Monthly refresh MR bounds UE point-version churn. |
</threat_model>

<verification>
- `grep -q "fail-fast: false" .github/workflows/plugin-matrix.yml` — PRESENT
- `grep -c "5\\.[4-7]" .github/workflows/plugin-matrix.yml` returns ≥ 4 (all four versions referenced)
- `grep -q "NYRA_UE_AT_LEAST" TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h` — PRESENT
- `grep -q "// NYRA_COMPAT:" TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h || true` — format comment documented
- Founder checkpoint completed with resume-signal `runner-provisioned` or `runner-provisioned-5.7-deferred`
</verification>

<success_criteria>
- Four-version matrix workflow triggers on PR and targets all four UE versions with fail-fast:false
- Self-hosted Windows runner is Online with label `self-hosted,Windows,unreal`
- `NYRACompat.h` ships empty-but-macro-armed, ready for Plan 02-06 empirical population
- `NyraCompatSpec.cpp` Nyra.Compat.Macro smoke-test is discoverable by Automation runner
- README-CI.md provides a complete runbook a second engineer could follow
</success_criteria>

<output>
After completion, create `.planning/phases/02-subscription-bridge-ci-matrix/02-01-SUMMARY.md`
</output>
