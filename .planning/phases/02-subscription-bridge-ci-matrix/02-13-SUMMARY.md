# Plan 02-13 Summary: EV Signing CI Integration

**Phase:** 02-subscription-bridge-ci-matrix
**Plan:** 02-13
**Type:** execute / checkpoint
**Wave:** 3
**Autonomous:** false | **TDD:** false
**Depends on:** [01, 04]
**Blocking precondition:** Plan 02-04 `ev-cert-in-akv-and-secrets-populated` checkpoint

## Objectives

Integrate EV code signing into `plugin-matrix.yml` so every released binary
carries a DigiCert EV signature with RFC 3161 timestamping. SmartScreen
reputation accrues from day one of CI, not from first user install.

## Current Status: CHECKPOINT — awaiting Plan 02-04 EV cert precondition

### Precondition

Plan 02-04 must emit `ev-cert-in-akv-and-secrets-populated` OR
`ev-cert-stalled` (in which case this plan defers to post-Phase-2 per the
cut-line contingency in Plan 02-04).

The orchestrator enforces this precondition at execute-time.

**If stalling:** AzureSignTool steps are NOT added to `plugin-matrix.yml`.
EV signing defers to a post-Phase-2 patch. `docs/SIGNING_VERIFICATION.md`
is still authored (without empirical pre-sign capture), documenting the
manual-signing escape hatch.

## What Will Be Built (after precondition clears)

### Task 1: Extend `plugin-matrix.yml` with AzureSignTool + signtool verify

Three new steps inserted between the Automation step and artifact upload step
(Phase 1 Plan 02-01 lines preserved verbatim — module-superset):

```yaml
# Step A: Install AzureSignTool
- name: Install AzureSignTool
  shell: pwsh
  run: dotnet tool install --global AzureSignTool

# Step B: Sign plugin + bundled binaries
- name: Sign plugin + bundled binaries
  shell: pwsh
  env:
    AZ_VAULT_URI:     ${{ secrets.AZURE_VAULT_URI }}
    AZ_CERT_NAME:     ${{ secrets.AZURE_CERT_NAME }}
    AZ_CLIENT_ID:     ${{ secrets.AZURE_CLIENT_ID }}
    AZ_CLIENT_SECRET:  ${{ secrets.AZURE_CLIENT_SECRET }}
    AZ_TENANT_ID:     ${{ secrets.AZURE_TENANT_ID }}
  run: |
    $binaries = Get-ChildItem -Recurse -Include @("*.dll","*.exe") `
                  -Path Artifacts/UE_${{ matrix.ue-version }}/
    foreach ($bin in $binaries) {
      $sig = Get-AuthenticodeSignature $bin.FullName
      if ($sig.Status -eq "Valid" -and
          $sig.SignerCertificate.Subject -match "Astral|ggml") {
        Write-Host "Skipping pre-signed $($bin.Name)"
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
      if ($LASTEXITCODE -ne 0) { throw "AzureSignTool failed" }
    }

# Step C: Verify signatures
- name: Verify signatures
  shell: pwsh
  run: |
    Get-ChildItem -Recurse -Include @("*.dll","*.exe") `
      -Path Artifacts/UE_${{ matrix.ue-version }}/ | ForEach-Object {
      & signtool verify /pa /v $_.FullName
      if ($LASTEXITCODE -ne 0) { throw "verify failed: $_" }
    }
```

### Task 2: Author `docs/SIGNING_VERIFICATION.md` + update `prebuild.ps1`

**`docs/SIGNING_VERIFICATION.md`** — post-CI-run operator runbook:

- Manual verification script using `Get-AuthenticodeSignature`
- Expected output: `Status=Valid; Signer=NYRA Pte Ltd` OR `Signer=Astral|ggml`
  (pre-signed binaries respected)
- Troubleshooting: `NotSigned` → re-run workflow; `HashMismatch` → investigate;
  `UnknownError` → check timestamp server reachability
- Empirical pre-sign capture table (PENDING cells for operator to fill after first run):
  - `python.exe` (bundled): [operator fills after first CI run]
  - `llama-server.exe`: [operator fills after first CI run]
- First release candidate checklist (4 UE cells green + signed, manual verify,
  no NotSigned/UnknownError, smoke-install SmartScreen check)

**`prebuild.ps1`** — at end of bundling, echo signing status per binary via
`Get-AuthenticodeSignature` so local developers see immediately whether re-sign is
needed (diagnostic only — CI does its own check).

### README-CI.md Updates

- Document the five GitHub Actions secrets consumed (`AZURE_VAULT_URI`,
  `AZURE_CERT_NAME`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`)
- Document the pre-sign-skip heuristic (Astral/ggml subject match)
- Document Azure region outage contingency: unsigned artifacts held;
  re-run signing step when region recovers; BuildPlugin results stay cached

## Threat Mitigations

| Threat | Mitigation |
|--------|-------------|
| T-02-13-01: `AZURE_CLIENT_SECRET` log disclosure | `$env:` vars not echoed; GitHub Actions auto-masks secrets |
| T-02-13-02: Pre-sign skip heuristic spoofing | Strict subject match on `Astral\|ggml`; Wave 0 empirical capture tightens pattern |
| T-02-13-03: Azure region outage | Artifacts cached; manual local-sign escape hatch in README-CI.md |
| T-02-13-04: Signature audit trail | RFC 3161 timestamp + signer subject give complete non-repudiation |

## Files Modified (planned)

| File | Change |
|------|---------|
| `.github/workflows/plugin-matrix.yml` | AzureSignTool install + sign + verify steps |
| `.github/workflows/README-CI.md` | Secrets documentation + outage contingency |
| `docs/SIGNING_VERIFICATION.md` | Manual runbook + pre-sign capture table |
| `TestProject/Plugins/NYRA/prebuild.ps1` | Signing-status diagnostic echo |

## Next Steps

After this plan completes, `plugin-matrix.yml` emits EV-signed artifacts per UE
version. `docs/SIGNING_VERIFICATION.md` gives the operator a verified-copy
runbook for first RC. Plan 02-14 (release canary) unblocks on this:
its `Nyra.Dev.SubscriptionBridgeCanary` runs against signed binaries.
