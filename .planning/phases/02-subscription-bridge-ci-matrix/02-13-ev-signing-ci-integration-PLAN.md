---
phase: 02-subscription-bridge-ci-matrix
plan: 13
slug: ev-signing-ci-integration
type: execute
wave: 3
depends_on: [01, 04]
autonomous: false
tdd: false
requirements: [PLUG-04]
files_modified:
  - .github/workflows/plugin-matrix.yml
  - .github/workflows/README-CI.md
  - TestProject/Plugins/NYRA/prebuild.ps1
  - docs/SIGNING_VERIFICATION.md
research_refs: [§6.3, §6.4, §6.5, §6.6, §10.8]
context_refs: [D-16, D-17]
phase0_clearance_required: false
must_haves:
  truths:
    - "plugin-matrix.yml extended with AzureSignTool install step + signing step per RESEARCH §6.4 shape"
    - "Signs ALL deliverable Windows binaries per RESEARCH §6.5: UnrealEditor-NyraEditor.dll (per UE version), UnrealEditor-NyraRuntime.dll, NyraHost bundled python.exe (if not pre-signed empirically), llama-server.exe (if not pre-signed empirically)"
    - "Azure credentials pulled from GitHub Actions secrets populated by Plan 02-04 checkpoint: AZURE_VAULT_URI, AZURE_CERT_NAME, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID"
    - "RFC 3161 timestamp server http://timestamp.digicert.com used on every signature"
    - "Post-sign verification step: signtool verify /pa /v on each signed binary; CI fails if any binary is unsigned or signature invalid"
    - "Empirical pre-sign check for python.exe + llama-server.exe documented in docs/SIGNING_VERIFICATION.md — if signtool reports them as already-signed-by-Astral / ggml.ai, the matrix workflow respects that and does NOT re-sign"
    - "prebuild.ps1 (Phase 1 artifact) updated to echo signing status after bundling, so the signing step can read whether re-sign is needed"
    - "Downstream precondition for Plan 02-14: plugin-matrix.yml green with signed artifacts uploaded per UE version"
  artifacts:
    - path: .github/workflows/plugin-matrix.yml
      provides: "Extended matrix: BuildPlugin + Automation + AzureSignTool + signtool verify"
    - path: docs/SIGNING_VERIFICATION.md
      provides: "Manual signtool verify runbook for the operator post-CI-run; documents the pre-sign empirical check outcomes"
  key_links:
    - from: plugin-matrix.yml signing step
      to: Azure Key Vault via AzureSignTool
      via: "GitHub Actions secrets injected as env → AzureSignTool CLI flags"
      pattern: "AzureSignTool sign.*timestamp\\.digicert\\.com"
---

<objective>
Integrate EV code signing into the four-version CI matrix. After Plan 02-04's founder checkpoint places the DigiCert EV cert in Azure Key Vault + populates GitHub Actions secrets, this plan adds the AzureSignTool install + sign + verify steps to `plugin-matrix.yml`.

Per CONTEXT.md:
- D-16: DigiCert EV in Azure Key Vault
- D-17: AzureSignTool + RFC 3161 timestamping
- D-26: phase0_clearance_required is false — signing is infrastructure, not economic-wedge code

**Precondition:** Plan 02-04 checkpoint signals `ev-cert-in-akv-and-secrets-populated` (or `ev-cert-stalled` — in which case this plan is deferred to post-Phase-2 per cut-line contingency in Plan 02-04). **The orchestrator enforces this at execute-time**; the plan PLANS without waiting.

**Autonomous: false** because post-CI signtool verify is a manual operator step for the first release candidate (catches edge cases like re-sign-but-kept-old-signature, which CI can miss).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/02-subscription-bridge-ci-matrix/02-CONTEXT.md
@.planning/phases/02-subscription-bridge-ci-matrix/02-RESEARCH.md
@.planning/phases/02-subscription-bridge-ci-matrix/02-04-ev-cert-acquisition-runbook-PLAN.md

<interfaces>
<!-- RESEARCH §6.4 signing step (authoritative template): -->
```yaml
# after BuildPlugin succeeds, before artifact upload
- name: Install AzureSignTool
  shell: pwsh
  run: dotnet tool install --global AzureSignTool

- name: Sign plugin + bundled binaries
  shell: pwsh
  env:
    AZ_VAULT_URI: ${{ secrets.AZURE_VAULT_URI }}
    AZ_CERT_NAME: ${{ secrets.AZURE_CERT_NAME }}
    AZ_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
    AZ_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}
    AZ_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
  run: |
    $binaries = Get-ChildItem -Recurse -Include @("*.dll","*.exe") `
                  -Path Artifacts/UE_${{ matrix.ue-version }}/
    # CR-08: pin pre-sign skip to KNOWN thumbprints (not substring match
    # on Subject DN, which is bypassable by self-signing a cert containing
    # "Astral" or "ggml" anywhere in the CN). The thumbprints are captured
    # from the actual Astral Python and ggml.ai llama.cpp release binaries
    # during Wave 0 setup; they live in $env:NYRA_KNOWN_THUMBPRINTS as a
    # comma-separated allowlist. signtool verify /pa is NOT sufficient on
    # its own because it accepts any trusted signature; we need exact
    # thumbprint equality so a foreign cert with a matching CN cannot
    # claim to be a known pre-signed dependency.
    $KnownThumbprints = ($env:NYRA_KNOWN_THUMBPRINTS -split ",")
    foreach ($bin in $binaries) {
      $sig = Get-AuthenticodeSignature $bin.FullName
      $thumbprint = $sig.SignerCertificate.Thumbprint
      if ($sig.Status -eq "Valid" -and ($KnownThumbprints -contains $thumbprint)) {
        Write-Host "Skipping pre-signed $($bin.Name): thumbprint=$thumbprint subject=$($sig.SignerCertificate.Subject)"
        continue
      }
      AzureSignTool sign `
        -kvu $env:AZ_VAULT_URI `
        -kvc $env:AZ_CERT_NAME `
        -kvi $env:AZ_CLIENT_ID `
        -kvs $env:AZ_CLIENT_SECRET `
        -kvt $env:AZ_TENANT_ID `
        -tr "http://timestamp.digicert.com" `
        -td sha256 `
        -fd sha256 `
        -v $bin.FullName
      if ($LASTEXITCODE -ne 0) { throw "AzureSignTool failed on $($bin.Name)" }
    }

- name: Verify signatures
  shell: pwsh
  run: |
    $binaries = Get-ChildItem -Recurse -Include @("*.dll","*.exe") `
                  -Path Artifacts/UE_${{ matrix.ue-version }}/
    foreach ($bin in $binaries) {
      & signtool verify /pa /v $bin.FullName
      if ($LASTEXITCODE -ne 0) { throw "signtool verify failed on $($bin.Name)" }
    }
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Extend plugin-matrix.yml with AzureSignTool + signtool verify</name>
  <files>.github/workflows/plugin-matrix.yml, .github/workflows/README-CI.md</files>
  <action>
    **Module-superset discipline on plugin-matrix.yml (D-24 extended to CI):** every Plan 02-01 line preserved verbatim. New steps inserted BETWEEN the Automation step and the artifact upload step.

    Insert three new steps per the interfaces template:
    1. Install AzureSignTool (dotnet tool install)
    2. Sign plugin + bundled binaries (with pre-sign skip heuristic using Get-AuthenticodeSignature matching Astral/ggml signer)
    3. Verify signatures (signtool verify /pa /v) — fail the job on any unverified binary

    Update README-CI.md to document:
    - The five GitHub Actions secrets this workflow consumes
    - The pre-sign-skip heuristic (pattern match on signer subject)
    - How to dry-run locally with a developer cert (NOT the production EV — operator uses their own test cert if debugging CI locally; v1.1 can add a no-sign bypass flag)
    - What to do if signtool verify fails (check RFC 3161 endpoint reachable + AZ credentials valid + cert not expired)
    - Azure region outage handling (RESEARCH §10.8): signing job can be manually re-run when region recovers; the matrix BuildPlugin results stay cached (artifacts) so only the signing step re-runs

    Commit: feat(02-13): add AzureSignTool signing + signtool verify steps to plugin-matrix.yml
  </action>
  <verify>
    <automated>grep -q "AzureSignTool" .github/workflows/plugin-matrix.yml && grep -q "timestamp.digicert.com" .github/workflows/plugin-matrix.yml && grep -q "signtool verify" .github/workflows/plugin-matrix.yml && grep -q "AZURE_VAULT_URI" .github/workflows/plugin-matrix.yml</automated>
  </verify>
  <done>
    - plugin-matrix.yml has install + sign + verify steps
    - Secrets correctly referenced as ${{ secrets.AZURE_XXX }}
    - RFC 3161 timestamp URL hardcoded
    - Pre-sign skip heuristic present
    - README-CI.md expanded with signing section
  </done>
</task>

<task type="auto">
  <name>Task 2: Author docs/SIGNING_VERIFICATION.md + prebuild.ps1 signing-status echo</name>
  <files>docs/SIGNING_VERIFICATION.md, TestProject/Plugins/NYRA/prebuild.ps1</files>
  <action>
    Create docs/SIGNING_VERIFICATION.md — a post-CI-run runbook for the operator:

    ## Purpose
    Verify that a released plugin package has every binary signed with the NYRA EV cert (or intentionally kept pre-signed by Astral/ggml). Run BEFORE uploading to Fab.

    ## Manual verification script
    ```powershell
    # Run from plugin root after CI artifact download
    $root = "path/to/Artifacts/UE_5.6"
    Get-ChildItem -Recurse -Include @("*.dll","*.exe") -Path $root | ForEach-Object {
      $sig = Get-AuthenticodeSignature $_.FullName
      $status = $sig.Status
      $signer = $sig.SignerCertificate.Subject
      Write-Host "$status | $signer | $($_.Name)"
    }
    ```

    Expected output per binary: Status=Valid; Signer=NYRA Pte Ltd (or your EV cert subject) OR Signer=<Astral / ggml> if pre-signed.

    ## What to do if any shows NotSigned / HashMismatch / UnknownError
    - NotSigned: CI signing step failed silently; re-run the workflow.
    - HashMismatch: binary modified after signing; investigate artifact upload tampering (unlikely on self-hosted runner).
    - UnknownError: signtool can't reach timestamp server; check network.

    ## Empirical pre-sign check outcomes (Wave 0 capture)
    - **python-build-standalone (bundled python.exe)**: [PENDING — operator fills in after first CI run. Expected outcome: signed by 'Astral Software Inc.' per their release process; NYRA does NOT re-sign.]
    - **llama-server.exe (b8870+ bundled)**: [PENDING — operator fills in. If pre-signed, leave as-is. If not, NYRA re-signs as part of the matrix workflow.]

    ## First release candidate checklist
    Before tagging v1-rc1:
    - [ ] All four UE matrix cells green + signed
    - [ ] Manual signtool verify on each artifact
    - [ ] No binary shows 'NotSigned' or 'UnknownError'
    - [ ] Smoke-install on a fresh Windows VM without any NYRA history; SmartScreen shows no warning (or only first-launch verbose info, NOT red reputation-unknown)

    ---

    Also update `TestProject/Plugins/NYRA/prebuild.ps1` (Phase 1 Plan 06 artifact that copies bundled binaries into place): at the end, echo the signing status of each copied binary via Get-AuthenticodeSignature, so a local developer sees immediately whether re-sign is needed. This is diagnostic only — CI still does its own check.

    Commit: feat(02-13): add docs/SIGNING_VERIFICATION.md + prebuild.ps1 signing-status echo
  </action>
  <verify>
    <automated>test -f docs/SIGNING_VERIFICATION.md && grep -q "signtool verify" docs/SIGNING_VERIFICATION.md && grep -q "Get-AuthenticodeSignature" TestProject/Plugins/NYRA/prebuild.ps1</automated>
  </verify>
  <done>
    - Manual verification runbook exists with expected outputs + troubleshooting
    - Empirical pre-sign check outcomes table (PENDING cells ready for operator fill)
    - prebuild.ps1 echoes signing status for local debugging
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CI workflow → Azure Key Vault | Service principal credentials cross; must never log to console |
| Signed binaries → Fab upload | Timestamp ensures validity post-expiry; cert subject is the NYRA entity |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-13-01 | Information Disclosure | AZURE_CLIENT_SECRET leaks in log | mitigate | PowerShell step uses $env:AZ_CLIENT_SECRET (not $secrets.X in output); GitHub Actions masks secrets in logs automatically. |
| T-02-13-02 | Tampering | Pre-sign skip heuristic matches an attacker-controlled signer | mitigate | Heuristic pattern is `match "Astral|ggml"` — a malicious injection would need to re-sign with one of those exact subject strings. Plan 02-13 bench recommends Wave 0 empirical capture of the actual subject strings to tighten the pattern (e.g., strict subject match, not substring). |
| T-02-13-03 | Denial of Service | Azure region outage blocks release | accept | RESEARCH §10.8: 2-hour typical recovery; un-signed binaries held as artifacts; manual sign from local dev machine is a documented escape hatch in README-CI.md. |
| T-02-13-04 | Repudiation | Who signed this binary? | mitigate | RFC 3161 timestamp + signer subject provide complete audit trail; every release commits SIGNING_VERIFICATION.md output with the matrix run. |
</threat_model>

<verification>
- `grep -q "AzureSignTool sign" .github/workflows/plugin-matrix.yml`
- `grep -q "signtool verify /pa" .github/workflows/plugin-matrix.yml`
- `test -f docs/SIGNING_VERIFICATION.md`
- Plan 02-04 checkpoint resolved with `ev-cert-in-akv-and-secrets-populated` (orchestrator precondition)
</verification>

<success_criteria>
- plugin-matrix.yml signs all emitted binaries with the EV cert (or honors pre-sign)
- signtool verify gates the release — no unsigned binaries slip through
- RFC 3161 timestamping gives indefinite signature validity
- Operator has a clear manual-verification runbook for first RC release
- Azure region outage has documented contingency
- SmartScreen reputation timeline (§6.6) starts accruing from day one
</success_criteria>

<output>
After completion, create `.planning/phases/02-subscription-bridge-ci-matrix/02-13-SUMMARY.md`
</output>
