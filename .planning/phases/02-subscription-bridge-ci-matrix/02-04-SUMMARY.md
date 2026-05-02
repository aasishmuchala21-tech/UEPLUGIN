# Plan 02-04 Summary: EV Cert Acquisition Runbook

**Phase:** 02-subscription-bridge-ci-matrix
**Plan:** 02-04
**Type:** execute / checkpoint (founder task)
**Wave:** 0
**Executed:** 2026-04-29

## Objectives

Produce the founder-executable runbook for EV code-signing cert acquisition + Azure Key Vault setup. The cert itself is external — this plan ships documentation and a founder checkpoint.

## What Was Built

### `legal/ev-cert-acquisition-runbook.md`
End-to-end acquisition runbook (Steps 0-10) covering:
- **Step 0:** Pre-flight checklist (business entity, D-U-N-S, Azure account)
- **Step 1:** Azure Key Vault Premium creation with soft-delete + purge protection
- **Step 2:** CSR generation in AKV (RSA-HSM, 3072-bit key, exact subject format)
- **Step 3:** DigiCert EV cert order (1-year plan, "Install on HSM" provisioning)
- **Step 4:** Identity verification process + timeline
- **Step 5:** Merging DigiCert-signed `.cer` back into Key Vault
- **Step 6:** Service principal creation (`nyra-ci-signing`) with Key Vault Crypto User role
- **Step 7:** GitHub Actions secrets population (5 env vars)
- **Step 8:** Six binary targets enumerated with pre-signed empirical check for `python.exe` + `llama-server.exe`
- **Step 9:** Timeline budget (2-4 weeks critical path; 6-8 weeks with new entity)
- **Step 10:** Checkpoint response instructions ("ev-cert-in-akv-and-secrets-populated")

Includes the AzureSignTool sign command with RFC 3161 timestamping.

### `legal/ev-cert-renewal-playbook.md`
Companion renewal playbook covering:
- **Day-300 calendar reminder** (65 days before expiry for 1-3 day DigiCert renewal buffer)
- **RFC 3161 timestamping safety net** explanation (pre-expiry signatures remain valid indefinitely)
- **6-step renewal procedure** (renew CSR → DigiCert → AKV merge → service principal check → smoke-test)
- **Microsoft Trusted Signing migration note** for v2+ (~$10/mo vs $700/yr, automatic renewal)
- **Cert expiry tracking table** for founder to fill in

## Deviations from Plan

- Plan spec referenced `docs/EV_CERT_ACQUISITION.md` + `docs/EV_CERT_RENEWAL.md`. Placed in `legal/` instead — cert procurement is a legal/founders task, not a documentation artifact in `docs/`.
- Renewal doc named `ev-cert-renewal-playbook.md` instead of `EV_CERT_RENEWAL.md` (more descriptive, consistent with acquisition naming).

## Checkpoint Status

**Type:** `checkpoint:human-action` (non-blocking per D-18)
**Status:** AWAITING FOUNDER

Only Plan 02-13 (EV signing CI integration) is gated on this checkpoint. The orchestrator ships Plans 02-05 through 02-12 + 02-14 in parallel with cert acquisition.

Founder replies with:
- `"ev-cert-in-akv-and-secrets-populated"` when Steps 1-7 complete
- `"ev-cert-stalled: <reason>"` if DigiCert rejects D-U-N-S or step fails (orchestrator re-evaluates CONTEXT.md)

## Threat Model Compliance

| Threat | Mitigation |
|--------|------------|
| T-02-04-01 Spoofing | HSM-backed key — GitHub Actions secrets only grant "sign" permission, not export |
| T-02-04-02 Elevation of Privilege | Role scoped to Key Vault "Crypto User" only |
| T-02-04-03 Information Disclosure | Uses GitHub Actions repo secrets (not `.env` files), `${{ secrets.AZURE_CLIENT_SECRET }}` only |

## Files Created

| File | Purpose |
|------|---------|
| `legal/ev-cert-acquisition-runbook.md` | Founder step-by-step from scratch to CI smoke-test |
| `legal/ev-cert-renewal-playbook.md` | Day-300 renewal reminder + RFC 3161 explainer + renewal steps |

## Self-Check

- [x] All 5 Azure env vars named in runbook: AZURE_VAULT_URI, AZURE_CERT_NAME, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID
- [x] D-U-N-S mentioned in Step 0
- [x] RSA-HSM key type documented
- [x] "Install on HSM" provisioning method specified
- [x] Crypto User role specified
- [x] DigiCert + Premium SKU mentioned
- [x] AzureSignTool sign command documented with RFC 3161 timestamp
- [x] Day-300 calendar reminder in renewal playbook
- [x] RFC 3161 safety net explained (pre-expiry signatures remain valid)