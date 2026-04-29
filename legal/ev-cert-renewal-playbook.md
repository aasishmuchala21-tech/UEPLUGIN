# EV Code-Signing Certificate Renewal Playbook

**Status:** Phase 2 Wave 0 (Plan 02-04)
**Last updated:** 2026-04-29

---

## Why a Separate Document

The February 2026 regulation caps EV certificate lifespan at **1 year**. Renewal is annual. Forgetting means Fab re-submissions break — the cert expires and `signtool verify /pa` fails on all new builds until renewal completes.

This document is the annual calendar reminder.

---

## Day-300 Calendar Reminder

Set a calendar reminder **65 days before cert expiry**.

DigiCert renewal typically takes 1-3 business days. Leaving 60+ days of buffer handles identity verification delays, DigiCert phone callback scheduling, and AKV cert merge steps.

Example: if your cert expires March 15, set the reminder for **January 9**.

---

## RFC 3161 Timestamping Safety Net

Every CI signing step uses:

```
-tr http://timestamp.digicert.com -td SHA256 -fd SHA256
```

The RFC 3161 timestamp anchors the signature to a trusted time source at sign-time. This means:

- **Binaries signed before cert expiry remain valid indefinitely.**
- Users who installed NYRA before expiry are completely unaffected by renewal.
- Only **new builds signed after the old cert expires** are blocked — until renewal completes.

This is the key property that makes annual renewal low-risk: you never need to ask users to re-download old binaries.

---

## Renewal Steps

### Step 1: Log into DigiCert

Navigate to [digicert.com/account](https://www.digicert.com/account) → **Code Signing Certificates** → find your active cert → click **Renew**.

Usually a 1-click flow if your organization info hasn't changed.

### Step 2: New CSR in Azure Key Vault

Repeat the CSR generation from the acquisition runbook (Step 2):
- Key Vault → Certificates → Generate/Import
- Subject name: must match DigiCert's verified organization name exactly
- Key Type: RSA-HSM, Key Size: 3072
- Download the new CSR

### Step 3: Submit New CSR to DigiCert

Upload the new CSR through the DigiCert renewal flow. Identity verification may be faster (1-2 business days) since DigiCert already has your organization's verification on file.

### Step 4: Merge New Cert into Key Vault

DigiCert emails the new signed `.cer` → Key Vault → Certificates → the pending cert → **Merge Signed Request**.

The old cert is automatically superseded. AzureSignTool in CI will pick up the new cert automatically via `AZURE_CERT_NAME`.

### Step 5: Service Principal Credentials

Service principal credentials (client secret from Step 6 of the acquisition runbook) carry over — no action needed unless approaching the 2-year secret expiry.

**Day-600 hygiene pass:** Rotate the client secret on Day 600 (midpoint of the 2-year expiry) as a security hygiene measure. Add the new secret as a second GitHub Actions secret and update the workflow to use it.

### Step 6: Run CI Smoke-Test

Trigger a test workflow run to confirm the new cert works end-to-end:
- `AzureSignTool sign` on a placeholder file
- `signtool verify /pa /v <signed-file>` confirms valid signature

---

## When to Consider Microsoft Trusted Signing (v2+)

| Factor | DigiCert EV | Microsoft Trusted Signing |
|--------|-------------|--------------------------|
| Cost | ~$700/yr | ~$10/mo ($120/yr) |
| Renewal | Manual annual | Automatic |
| HSM | Bring-your-own (AKV) | Microsoft-managed |
| Publisher reputation | Deep history | Newer, building trust |
| CI integration | AzureSignTool | AzureSignTool |

Trusted Signing is attractive for v2+ once NYRA has ~6 months of signed-binary history. For v1, DigiCert EV's established SmartScreen reputation is worth the higher cost.

---

## Out of Scope for This Playbook

- **Multi-region AKV replication** — v2+
- **Migration off Azure** — no fallback plan in v1
- **Revocation** — not covered; DigiCert handles CRL distribution

---

## Key Contacts

| Service | Contact |
|---------|---------|
| DigiCert EV renewal | [digicert.com/account](https://www.digicert.com/account) → Support chat |
| Azure Key Vault | [portal.azure.com](https://portal.azure.com) → Key Vault → Support |

---

## Cert Expiry Tracking

| Cert Name | Key Vault | Expiry Date | Day-300 Reminder |
|-----------|-----------|-------------|-----------------|
| `nyra-code-signing` | `<vault>.vault.azure.net` | _FILL_IN_ | _FILL_IN_ |

Fill in the Expiry Date from Step 5 of the acquisition runbook once cert is in AKV. Calculate the Day-300 date and add to your calendar immediately.