---
phase: 02-subscription-bridge-ci-matrix
plan: 04
slug: ev-cert-acquisition-runbook
type: execute
wave: 0
depends_on: []
autonomous: false
tdd: false
requirements: [PLUG-04]
files_modified:
  - docs/EV_CERT_ACQUISITION.md
  - docs/EV_CERT_RENEWAL.md
research_refs: [§6.1, §6.2, §6.3, §6.5, §6.6, §10.3]
context_refs: [D-16, D-17, D-18]
phase0_clearance_required: false
user_setup:
  - service: azure-key-vault
    why: "Houses the HSM-backed EV signing key per D-16"
    env_vars: []
    dashboard_config:
      - task: "Create Azure subscription (or confirm existing one); verify billing method"
        location: "https://portal.azure.com"
      - task: "Provision Azure Key Vault with Premium SKU (RSA-HSM key support)"
        location: "Azure Portal → Key Vaults → Create"
      - task: "Create Azure AD app registration + service principal with 'Key Vault Crypto User' role over the vault"
        location: "Azure Portal → Microsoft Entra ID → App registrations"
  - service: digicert-ev-code-signing
    why: "EV cert eliminates SmartScreen 30-day reputation window (D-16 rationale)"
    env_vars:
      - name: AZURE_VAULT_URI
        source: "Azure Portal → Key Vault → Properties → Vault URI"
      - name: AZURE_CERT_NAME
        source: "Azure Portal → Key Vault → Certificates — the cert name chosen at provisioning"
      - name: AZURE_CLIENT_ID
        source: "Azure Portal → App registrations → Overview → Application (client) ID"
      - name: AZURE_CLIENT_SECRET
        source: "Azure Portal → App registrations → Certificates & secrets → New client secret"
      - name: AZURE_TENANT_ID
        source: "Azure Portal → Microsoft Entra ID → Overview → Tenant ID"
    dashboard_config:
      - task: "Order DigiCert EV cert, choose 'Install on HSM' provisioning; supply D-U-N-S number"
        location: "https://www.digicert.com/tls-ssl/ev-code-signing"
      - task: "Complete DigiCert identity verification (1-3 business days; up to 2 weeks if founder has no business entity)"
        location: "DigiCert email + phone callback"
      - task: "Merge DigiCert-signed certificate with CSR in Azure Key Vault"
        location: "Azure Portal → Key Vault → Certificates → Merge"
      - task: "Add all five env vars above to GitHub Actions repo secrets"
        location: "GitHub → repo Settings → Secrets and variables → Actions"
must_haves:
  truths:
    - "docs/EV_CERT_ACQUISITION.md provides a step-by-step runbook a non-engineer founder can follow end-to-end without asking questions"
    - "Runbook covers: business entity / D-U-N-S setup if needed, Azure subscription + Key Vault Premium creation, CSR generation, DigiCert ordering with 'Install on HSM', identity verification tips + timelines, merge-cert flow, service principal creation with Crypto User role, GitHub Actions secrets setup"
    - "Runbook documents the six binary targets that will be signed (RESEARCH §6.5) AND the empirical 'pre-signed?' check for python.exe + llama-server.exe"
    - "docs/EV_CERT_RENEWAL.md documents the day-300 renewal trigger + RFC 3161 timestamping semantics that let pre-expiry signatures remain valid indefinitely"
    - "Checkpoint awaits founder confirmation that cert is in Azure Key Vault AND GitHub Actions secrets are populated"
  artifacts:
    - path: docs/EV_CERT_ACQUISITION.md
      provides: "End-to-end runbook for EV cert acquisition + AKV provisioning"
    - path: docs/EV_CERT_RENEWAL.md
      provides: "Renewal playbook — day-300 calendar reminder, DigiCert reorder flow, AKV cert update"
  key_links:
    - from: docs/EV_CERT_ACQUISITION.md
      to: Plan 02-13 (EV signing CI integration)
      via: "Runbook ends with 'verify GitHub Actions secrets populated' which is Plan 02-13's execute-time precondition"
      pattern: "Plan 02-13"
---

<objective>
Produce the founder-executable runbook for EV code-signing cert acquisition + Azure Key Vault setup. **This plan does NOT ship code** — it ships documentation + a founder checkpoint. The cert acquisition itself takes 1-3 business days (up to 2 weeks if a business entity must be created); Plan 02-13 depends on this checkpoint passing before the CI signing step can go green.

Per CONTEXT.md:
- D-16: DigiCert EV in Azure Key Vault Premium — no Sectigo (not AKV-compatible), no USB token (CI-unfriendly)
- D-17: AzureSignTool + RFC 3161 timestamping
- D-18: cert acquisition is a founder task, parallelizable with planner work; blocks only Plan 02-13

Runbook content from RESEARCH §6 verbatim where applicable; authored in a step-by-step tone that assumes the reader is NOT a security engineer.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/02-subscription-bridge-ci-matrix/02-CONTEXT.md
@.planning/phases/02-subscription-bridge-ci-matrix/02-RESEARCH.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Author docs/EV_CERT_ACQUISITION.md</name>
  <files>docs/EV_CERT_ACQUISITION.md</files>
  <action>
    Write the end-to-end runbook. Structure:

    ## 0. Pre-flight checklist
      - Do you have a business entity (LLC or sole proprietor trading name)? If no: pause the runbook, form the entity first (state-specific; typically 1-2 weeks). DigiCert WILL refuse an individual EV cert.
      - Do you have a D-U-N-S number for that entity? If no: free D-U-N-S at dnb.com (3-5 business days). Required by DigiCert.
      - Do you have an Azure account with billing? If no: create at portal.azure.com (includes $200 trial credit).

    ## 1. Azure subscription + Key Vault Premium
      - Step-by-step portal clicks to create a Key Vault with Premium SKU (Standard CANNOT hold RSA-HSM keys per RESEARCH §6.2).
      - Choose a resource group + region; region outage has 99.9% SLA (RESEARCH §10.8).
      - Cost: ~$5/mo for Premium SKU operations + ~$1/mo per HSM-protected key.

    ## 2. Generate a Certificate Signing Request (CSR) in Key Vault
      - Portal path: Key Vault → Certificates → Generate/Import → Certificate Authority = "Non-integrated CA" → Subject exactly matches the DigiCert-verified organization name (format: CN=<Entity>, O=<Entity>, L=<City>, S=<State>, C=<Country>).
      - Advanced Policy Configuration: Key Type = RSA-HSM, Key Size = 3072 (RESEARCH §6.2 mandates HSM-backed since June 2023).
      - Download the CSR blob.

    ## 3. Order DigiCert EV cert
      - Navigate to digicert.com/tls-ssl/ev-code-signing. Choose 1-year plan (February 2026 regulation caps at 1 year — RESEARCH §10.3).
      - Provisioning option: "Install on HSM" (not USB token, not PFX).
      - Paste the CSR from Step 2.
      - Pricing: $559-$699/yr. Budget $700 to include taxes/add-ons.
      - Submit D-U-N-S, business license, contact info.

    ## 4. DigiCert identity verification
      - DigiCert will email a verification form, then phone-call the listed founder contact (callback-verification).
      - Timeline: 1-3 business days when D-U-N-S is established; 1-2 weeks if they can't reach you on the listed phone.
      - Tips: answer unknown numbers during the window; confirm your phone listing (Google My Business / D-U-N-S directory); respond to DigiCert emails within 24h to avoid timer reset.

    ## 5. Merge signed cert back into Key Vault
      - DigiCert emails a signed cert file (.cer) once verified.
      - Portal path: Key Vault → Certificates → the pending certificate → Merge Signed Request → upload the .cer.
      - Vault now holds a complete EV cert + private key in HSM.

    ## 6. Create service principal for CI signing
      - Microsoft Entra ID → App registrations → New registration — name "nyra-ci-signing".
      - Certificates & secrets → New client secret → 2-year expiry → copy the secret VALUE (not the secret ID) immediately; it's never shown again.
      - Key Vault → Access control (IAM) → Add role assignment → Key Vault Crypto User → assign to the service principal.

    ## 7. Populate GitHub Actions secrets
      - GitHub → repo Settings → Secrets and variables → Actions → New repository secret. Add exactly:
        - AZURE_VAULT_URI (https://<vault>.vault.azure.net)
        - AZURE_CERT_NAME (the name you chose in Step 2)
        - AZURE_CLIENT_ID
        - AZURE_CLIENT_SECRET
        - AZURE_TENANT_ID
      - Smoke-test: in a feature branch, add a throwaway workflow step running `AzureSignTool sign -kvu $env:AZ_VAULT_URI ...` on a placeholder .exe. Green = Plan 02-13 will work on first try.

    ## 8. Binary targets to sign (RESEARCH §6.5 verbatim)
      - UnrealEditor-NyraEditor.dll (per UE version, from BuildPlugin output)
      - UnrealEditor-NyraRuntime.dll (per UE version)
      - NyraHost bundled python.exe (from python-build-standalone) — empirical check required: if Astral pre-signs the binary, skip; if not, NYRA re-signs.
      - llama-server.exe (bundled in Binaries/Win64/NyraInfer/) — empirical check: ggml.ai pre-signs some releases; not all.
      - One EV cert identity signs all binaries — do NOT request per-binary certs.

    ## 9. Timeline budget
      - Business entity (if new): 1-2 weeks
      - D-U-N-S (if new): 3-5 business days, free
      - Azure Key Vault + CSR: 30 minutes
      - DigiCert order: 30 minutes to submit
      - Identity verification: 1-3 business days (normal) or 1-2 weeks (delays)
      - Merge + service principal: 30 minutes
      - GitHub Actions secrets: 10 minutes
      - Total critical path: 2-4 weeks if everything already in place; 6-8 weeks worst case

    ## 10. When this runbook is complete
      - Reply to Plan 02-04 checkpoint with "ev-cert-in-akv-and-secrets-populated" so Phase 2 execution can proceed to Plan 02-13 (EV signing CI integration) when that wave arrives. If cert acquisition is still in-flight when Wave 3 starts, the orchestrator will hold Plan 02-13 (not Plan 02-12) and continue the rest of the phase.

    The runbook is written in tutorial voice. Screenshots NOT required for v1 of the doc — link directly to DigiCert + Microsoft Learn canonical pages at each step.
  </action>
  <verify>
    <automated>python3 -c "t=open('docs/EV_CERT_ACQUISITION.md').read(); markers=['D-U-N-S','Azure Key Vault','Premium SKU','DigiCert','RSA-HSM','Install on HSM','Crypto User','AZURE_VAULT_URI','AZURE_CERT_NAME','AZURE_CLIENT_ID','AZURE_CLIENT_SECRET','AZURE_TENANT_ID','AzureSignTool']; missing=[m for m in markers if m not in t]; print('MISSING:', missing) if missing else print('OK')"</automated>
  </verify>
  <done>
    - Runbook exists with sections 0-10 covering pre-flight through handoff-to-Plan-02-13
    - All six binary targets from RESEARCH §6.5 enumerated
    - All five GitHub Actions secret names documented exactly
    - Timeline budget with critical path
  </done>
</task>

<task type="auto">
  <name>Task 2: Author docs/EV_CERT_RENEWAL.md</name>
  <files>docs/EV_CERT_RENEWAL.md</files>
  <action>
    Short companion runbook. Structure:

    ## Why a separate doc
      - The February 2026 regulation caps cert lifespan at 1 year (RESEARCH §10.3). Renewal happens annually; forgetting breaks Fab re-submissions.

    ## Day-300 calendar reminder
      - Put a calendar reminder 65 days before cert expiry (DigiCert renewal takes 1-3 business days; leaving 60+ days of buffer handles delays).

    ## RFC 3161 timestamping safety net
      - Because every CI signing step uses `-tr http://timestamp.digicert.com` (RESEARCH §6.4), binaries signed BEFORE cert expiry remain valid indefinitely. Users already-installed are unaffected by cert expiry.
      - Only NEW builds after expiry are blocked until renewal completes.

    ## Renewal steps
      - Log into DigiCert account → renew the EV cert (usually 1-click if entity info unchanged).
      - New CSR in Azure Key Vault (repeat EV_CERT_ACQUISITION.md §2).
      - Merge new DigiCert-signed cert into Key Vault.
      - Service principal credentials carry over (no secret rotation unless approaching 2-year secret expiry; rotate on Day-600 as a hygiene pass).
      - Run the CI smoke-test workflow to confirm new cert works end-to-end.

    ## When to consider Microsoft Trusted Signing migration (v2+)
      - Microsoft Trusted Signing is $10/mo vs. $700/yr DigiCert. Handles issuance + renewal + HSM automatically. Not recommended for v1 (maturity curve + DigiCert has deeper publisher-reputation history), but a clear migration target once NYRA has ~6 months of signed-binary history.

    ## Out-of-scope for this runbook
      - Multi-region AKV replication — v2+.
      - Migration off Azure — no fallback plan in v1; AKV region outage is accepted risk per RESEARCH §10.8 (2-hour typical recovery).
  </action>
  <verify>
    <automated>python3 -c "t=open('docs/EV_CERT_RENEWAL.md').read(); markers=['Day-300','RFC 3161','Microsoft Trusted Signing','timestamp.digicert.com']; missing=[m for m in markers if m not in t]; print('MISSING:', missing) if missing else print('OK')"</automated>
  </verify>
  <done>
    - Renewal runbook exists with calendar reminder, RFC 3161 explainer, renewal steps, Microsoft Trusted Signing evaluation note
  </done>
</task>

<task type="checkpoint:human-action" gate="non-blocking">
  <name>Task 3: FOUNDER — Execute EV cert acquisition runbook</name>
  <what-built>
    Claude has authored docs/EV_CERT_ACQUISITION.md + docs/EV_CERT_RENEWAL.md. The cert itself requires 2-4 weeks of founder-driven external work (business entity / D-U-N-S / DigiCert identity verification / Azure setup).

    Per CONTEXT.md D-18, this checkpoint is NON-BLOCKING for the rest of Phase 2 planning and most of execution. Plan 02-13 (the only plan that calls AzureSignTool) is the ONLY downstream work gated by this checkpoint. The orchestrator can ship Plans 02-05 through 02-12 + 02-14 in parallel with cert acquisition.
  </what-built>
  <how-to-verify>
    Execute the steps in docs/EV_CERT_ACQUISITION.md §1 through §7 end-to-end. When complete:

    1. Confirm `az keyvault certificate show --vault-name <vault> --name <cert>` returns a cert with `issuer_provider = Unknown` (the merged DigiCert cert) and `key_type = RSA-HSM`.
    2. Confirm all five GitHub Actions secrets are present in repo Settings → Secrets and variables → Actions.
    3. Run the smoke-test workflow described in §7 on a feature branch; it should sign a placeholder .exe and the `signtool verify /pa /v <file>` subsequent step should pass.
  </how-to-verify>
  <resume-signal>
    Reply with "ev-cert-in-akv-and-secrets-populated" when §10 of the runbook is complete. Plan 02-13 will unblock at that point. If this comes back later than the rest of Phase 2, the orchestrator ships Plans 02-05..02-12 + 02-14 first and holds Plan 02-13.

    If cert acquisition stalls (e.g., DigiCert rejects the D-U-N-S), reply with "ev-cert-stalled: <reason>" — orchestrator escalates to CONTEXT.md re-visit (may need to downgrade Plan 02-13 to a v1.1 follow-up and launch Phase 2 with unsigned binaries + SmartScreen warnings documented to early beta users).
  </resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Founder ↔ DigiCert identity verification | Callback phone + email channel; founder's D-U-N-S + business entity are the identity root |
| GitHub Actions ↔ Azure Key Vault | Service principal's client secret is the crossing credential |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-04-01 | Spoofing | Attacker steals GitHub Actions secrets and signs malware as NYRA | mitigate | Azure Key Vault holds the private key in HSM — secrets only grant "use the key to sign" permission, not export. Rotating the service principal secret invalidates stolen access. Runbook §6 documents 2-year rotation cadence. |
| T-02-04-02 | Elevation of Privilege | Service principal has broader Azure rights than needed | mitigate | Role assignment scoped to Key Vault "Crypto User" only — cannot create/delete certs, only sign with existing one. Runbook enforces this in §6. |
| T-02-04-03 | Information Disclosure | AZURE_CLIENT_SECRET committed to repo by accident | mitigate | Runbook §7 uses GitHub Actions repository secrets (not .env files); Plan 02-13 CI snippet references `${{ secrets.AZURE_CLIENT_SECRET }}` only. `.gitignore` + pre-commit hook (Phase 2 polish) block accidental commits. |
</threat_model>

<verification>
- `grep -q "D-U-N-S" docs/EV_CERT_ACQUISITION.md` — PRESENT
- `grep -c "AZURE_" docs/EV_CERT_ACQUISITION.md` ≥ 5 — all five env vars named
- `grep -q "RFC 3161" docs/EV_CERT_RENEWAL.md` — PRESENT
- Checkpoint resume-signal received (ev-cert-in-akv-and-secrets-populated OR ev-cert-stalled)
</verification>

<success_criteria>
- Founder can follow docs/EV_CERT_ACQUISITION.md end-to-end without asking clarifying questions
- Renewal runbook provides day-300 reminder + RFC 3161 safety net explanation
- Checkpoint cleanly resolves to either "ev-cert-in-akv-and-secrets-populated" (unlocks Plan 02-13) or "ev-cert-stalled: ..." (triggers CONTEXT.md re-visit)
- Plan 02-13 has a clean precondition surface to check at its own execute time
</success_criteria>

<output>
After completion, create `.planning/phases/02-subscription-bridge-ci-matrix/02-04-SUMMARY.md`
</output>
