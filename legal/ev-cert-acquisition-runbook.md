# EV Code-Signing Certificate Acquisition Runbook

**Status:** Phase 2 Wave 0 (Plan 02-04)
**Last updated:** 2026-04-29
**Owner:** Founder (non-engineer executable)

---

## 0. Pre-flight Checklist

Before you start, confirm all three:

- **Business entity?** EV certs are only issued to registered business entities (LLC, C-Corp, etc.), not individuals. If you don't have one, pause here and form an LLC first (state-specific; typically 1-2 weeks).
- **D-U-N-S number?** Free at [dnb.com](https://www.dnb.com). Takes 3-5 business days. DigiCert requires it.
- **Azure account with billing?** Create at [portal.azure.com](https://portal.azure.com) (includes $200 free credit).

---

## 1. Azure Subscription + Key Vault Premium

1. Log into [portal.azure.com](https://portal.azure.com)
2. Create a Resource Group (or use an existing one)
3. Create a Key Vault:
   - **SKU:** Premium (required for RSA-HSM key support — Standard cannot hold EV certs)
   - **Region:** Choose your primary region (99.9% SLA)
   - **Recovery options:** Enable soft-delete + purge protection
4. Cost: ~$5/mo for Premium operations + ~$1/mo per HSM-protected key

---

## 2. Generate a Certificate Signing Request (CSR) in Key Vault

1. Open your Key Vault → **Certificates** → **Generate/Import**
2. Fill in:
   - **Certificate Name:** `nyra-code-signing` (or your choice)
   - **Type of Certificate Authority:** `Non-integrated CA`
   - **Subject:** Must exactly match your DigiCert-verified organization name:
     ```
     CN=Your Company Name, O=Your Company Name, L=City, S=State, C=US
     ```
     (Copy the format from your D-U-N-S / business registration exactly)
   - **Key Type:** RSA-HSM (Azure Dedicated HSM — not RSA, not managed HSM)
   - **Key Size:** 3072 (EV minimum)
3. Click **Create** — the CSR is generated in the vault
4. Download the CSR (base64-encoded blob)

---

## 3. Order DigiCert EV Code-Signing Certificate

1. Go to [digicert.com/tls-ssl/ev-code-signing](https://www.digicert.com/tls-ssl/ev-code-signing)
2. Choose **1-year plan** (February 2026 regulation caps EV cert lifespan at 1 year)
3. **Provisioning method:** Choose **"Install on HSM"** — paste the CSR from Step 2
   - Do NOT choose USB token or PFX — those are CI-unfriendly
4. Enter your D-U-N-S number, business registration info, and contact details
5. **Pricing:** ~$559–$699/yr. Budget $700 to include taxes/add-ons
6. Submit the order

---

## 4. DigiCert Identity Verification

DigiCert will:
1. Email a verification form to your registered contact email
2. Phone-call the founder contact for callback verification

**Timeline:** 1-3 business days (normal), 1-2 weeks (if delays)

**Tips:**
- Answer unknown numbers during the verification window
- Confirm your phone listing in Google My Business / D-U-N-S directory
- Respond to DigiCert emails within 24 hours to avoid timer reset
- If DigiCert can't reach you on the listed phone, the process restarts

---

## 5. Merge Signed Certificate Back into Key Vault

Once DigiCert verifies your identity:
1. DigiCert emails a signed certificate file (`.cer`)
2. Go to: Azure Portal → Your Key Vault → **Certificates**
3. Find the pending certificate → **Merge Signed Request**
4. Upload the `.cer` file DigiCert sent
5. The vault now holds your complete EV certificate + private key in HSM

---

## 6. Create Service Principal for CI Signing

GitHub Actions needs a way to sign binaries using your AKV cert — without reading the private key out of the vault.

1. **Microsoft Entra ID** → **App registrations** → **New registration**
   - Name: `nyra-ci-signing`
   - Account type: "Accounts in this organizational directory only"
2. Click **Certificates & secrets** → **New client secret**
   - Description: `nyra-ci-signing`
   - Expires: 2 years
   - **Copy the secret VALUE immediately** — it's never shown again after this
3. **Key Vault** → **Access control (IAM)** → **Add role assignment**
   - Role: **Key Vault Crypto User**
   - Assign to: your `nyra-ci-signing` service principal
   - Scope: your Key Vault

---

## 7. Populate GitHub Actions Secrets

In your GitHub repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**, add exactly:

| Secret name | Value |
|-------------|-------|
| `AZURE_VAULT_URI` | `https://<vault-name>.vault.azure.net/` |
| `AZURE_CERT_NAME` | The certificate name from Step 2 (e.g., `nyra-code-signing`) |
| `AZURE_CLIENT_ID` | Application (client) ID from Step 6 |
| `AZURE_CLIENT_SECRET` | The secret VALUE you copied in Step 6 |
| `AZURE_TENANT_ID` | Microsoft Entra ID → Overview → Tenant ID |

**Smoke-test:** In a feature branch, add a test workflow step using [AzureSignTool](https://learn.microsoft.com/en-us/azure/container-apps/azure-arc-code-signing-tutorial) to sign a placeholder `.exe`. Green = Plan 02-13 will work on first try.

---

## 8. Binary Targets to Sign (Six Binaries)

The EV cert identity signs all of these — do NOT request per-binary certs:

| Binary | Source | Pre-signed check |
|--------|--------|-----------------|
| `UnrealEditor-NyraEditor.dll` | BuildPlugin output (per UE version) | No — NYRA-specific |
| `UnrealEditor-NyraRuntime.dll` | BuildPlugin output (per UE version) | No — NYRA-specific |
| `python.exe` | python-build-standalone bundled in `Binaries/Win64/` | **Empirical check required** — if Astral pre-signs the binary, skip re-signing |
| `llama-server.exe` | Bundled in `Binaries/Win64/NyraInfer/` | **Empirical check required** — some ggml.ai releases are pre-signed |
| `ffmpeg.exe` | `Binaries/Win64/` (Phase 3+) | No — NYRA-specific |
| `yt-dlp.exe` | `Binaries/Win64/` (Phase 3+) | No — NYRA-specific |

For `python.exe` and `llama-server.exe`: run `signtool verify /pa /v <file>` on each. If `verify` returns "No signature found" or "Failed to verify", add the file to the CI signing step. If `verify` passes, skip to reduce CI time.

---

## 9. Timeline Budget

| Step | Duration |
|------|----------|
| Business entity (if new) | 1-2 weeks |
| D-U-N-S (if new) | 3-5 business days, free |
| Azure Key Vault + CSR | 30 minutes |
| DigiCert order | 30 minutes to submit |
| Identity verification | 1-3 business days (normal), 1-2 weeks (delays) |
| Merge + service principal | 30 minutes |
| GitHub Actions secrets | 10 minutes |
| **Total critical path** | **2-4 weeks** (everything in place) / **6-8 weeks** (new business entity) |

---

## 10. When This Runbook Is Complete

Reply to the Plan 02-04 checkpoint with:
- **"ev-cert-in-akv-and-secrets-populated"** — when all Steps 1-7 are done and the smoke-test from Step 7 passes
- **"ev-cert-stalled: <reason>"** — if DigiCert rejects your D-U-N-S or any step fails; orchestrator will re-evaluate

**Plan 02-13 (EV signing CI integration)** is the only Phase 2 plan gated on this checkpoint. The orchestrator can ship Plans 02-05 through 02-12 + 02-14 in parallel with cert acquisition.

---

## Quick Reference: AzureSignTool Sign Command

```powershell
AzureSignTool sign -kvu $env:AZURE_VAULT_URI `
  -kvi $env:AZURE_CLIENT_ID `
  -kvs $env:AZURE_CLIENT_SECRET `
  -kvt $env:AZURE_TENANT_ID `
  -kvc $env:AZURE_CERT_NAME `
  -tr http://timestamp.digicert.com `
  -td SHA256 `
  -fd SHA256 `
  <path-to-file-to-sign>
```

The `-tr http://timestamp.digicert.com` RFC 3161 timestamp means signatures remain valid indefinitely after cert expiry — already-signed binaries are unaffected by annual renewals.

---

## Out of Scope

- Multi-region Key Vault replication — v2+
- USB token workflow (not CI-friendly)
- Sectigo / other CAs — not AKV-compatible per CONTEXT.md D-16