---
source_url: https://www.fab.com/seller-policy (probed 2026-04-29; WebFetch blocked by Cloudflare; no dedicated seller-branding sub-page URL found)
snapshot_date: 2026-04-29
snapshot_method: cloudflare-blocked
snapshot_by: NYRA Plan 00-05 executor
plan: 00-05-brand-guideline-archive-and-copy
rationale: >
  Fab (operated by Epic Games) has seller-facing policies that govern how
  sellers name and describe their products on the Fab marketplace. This
  snapshot captures the Fab-specific brand/naming rules that apply to
  NYRA's listing, distinct from the Fab Content Guidelines already
  snapshotted in Plan 00-02 (external-snapshots/fab-content-guidelines-
  SNAPSHOT.md) and the Fab AI Disclosure Policy snapshotted in Plan
  00-02 (external-snapshots/fab-ai-disclosure-policy-SNAPSHOT.md).
  This doc focuses specifically on the seller-branding / product-naming /
  prohibited-phrasing surface — the cross-section of Fab's Content
  Guidelines and Fab's seller-onboarding requirements that affects
  listing copy directly.
publisher: "Epic Games, Inc. (Fab, the unified 3D-content marketplace)"
canonical_title: "Fab Seller Branding / Naming Policy (inferred)"
license_notice: >
  Inferred here for fair-use research archival (NYRA legal gate). Full
  policy lives at the source_url above. Epic Games owns the policy.
---

# Fab Seller Branding Policy — Snapshot 2026-04-29

> **Snapshot method note.** WebFetch against fab.com/seller-policy returned
> 403 Cloudflare challenge (2026-04-29). Fab's help center also returns a
> Cloudflare challenge to automated clients. This snapshot is therefore
> based on: (a) the Fab Content Guidelines structural headings from the
> Plan 00-02 snapshot, (b) Fab's publicly-documented seller onboarding
> surface from Fab's late-2024 launch and 2025 updates, and (c) the known
> Fab marketplace norms from Fab's published seller documentation and
> forum posts. All rules below are marked `[inferred from public Fab surface]`
> or `[paraphrased from Fab seller documentation]` where derived from
> publicly-known Fab norms rather than a live-fetched page.
>
> **Upgrade trigger (founder-action).** When the founder logs into Fab as a
> seller (seller-dashboard is authenticated and bypasses Cloudflare):
>   1. Navigate to Fab seller policies / branding guidelines
>   2. Capture verbatim policy text into this file
>   3. Update `snapshot_method` to `authenticated-seller-dashboard-copy`
>   4. Commit as `docs(00-05): upgrade fab-seller-branding to authenticated copy`

## Relationship to other Fab snapshots in this archive

| Fab policy surface | Snapshot file | Plan |
|--------------------|---------------|------|
| Content Guidelines | fab-content-guidelines-SNAPSHOT.md | 00-02 |
| AI Disclosure Policy | fab-ai-disclosure-policy-SNAPSHOT.md | 00-02 |
| Code Plugin Submission Checklist | fab-code-plugin-checklist-SNAPSHOT.md | 00-02 |
| Seller Branding / Naming Policy | THIS FILE | 00-05 |

The Content Guidelines snapshot (00-02) covers what content Fab accepts.
This snapshot covers the SPECIFIC BRAND AND NAMING rules that apply to
NYRA's listing copy beyond the general content rules.

## Known Fab Seller Branding / Naming Rules (inferred)

### 1. Product Name Rules

[inferred from public Fab surface + marketplace norms]

- Product names on Fab must be the actual product name (NYRA)
- Seller may NOT prefix the product name with a platform's brand
  (e.g., not "Epic NYRA" or "Unreal NYRA")
- Seller may NOT use "Official", "Verified", or "Staff Pick" badges
  without Epic explicitly granting those designations
- Product name must match the downloadable asset's `.uplugin` descriptor
  `FriendlyName` field

### 2. Description / Marketing Copy Rules

[inferred from public Fab surface]

- Descriptions may not misrepresent the product's capabilities
- Descriptions must disclose AI-powered features (mandatory per Fab AI
  disclosure policy — see fab-ai-disclosure-policy-SNAPSHOT.md)
- Third-party brand names may be used factually to describe integrations
  (e.g., "works with your Claude subscription" is acceptable)
- Third-party brand names may NOT be used in a way that implies endorsement
  or partnership (e.g., "Anthropic-endorsed", "Official Meshy integration")
- No comparative claims against named competitors (e.g., "better than X")
  without verifiable evidence — Fab's general moderation applies here

### 3. Logo / Visual Identity Rules

[inferred from public Fab surface]

- Sellers may NOT use Epic Games, Unreal Engine, or Fab logos in their
  listing assets without written permission from Epic
- Sellers may NOT use third-party logos (Anthropic, OpenAI, Google,
  Adobe, ComfyUI, Meshy) in listing graphics without permission from
  the respective brand owner
- Screenshots showing third-party UIs (e.g., ComfyUI, Meshy, Substance
  3D Sampler) are acceptable as functional screenshots of the workflow
  IF the third-party product is referenced factually in the description

### 4. Tag / Category Rules

[inferred from public Fab surface]

- Tags must be relevant to the actual product content
- Tags must not be misleading about product capabilities
- Category selection must match the product type (Code Plugin for NYRA)

### 5. Prohibited Phrasing (known from Fab Content Guidelines)

Fab's Content Guidelines (snapshotted Plan 00-02) prohibit:
- Content that infringes third-party IP
- Content that misrepresents functionality
- Content that uses brand names in ways that imply endorsement

The brand-implication rule is the most directly relevant to NYRA's copy:
**NYRA must not say "official", "partner", "endorsed by", or "approved by"
ANY of the four brands (Anthropic, OpenAI, Epic/Fab, Google) in v1 copy.**

### 6. Pricing / Offer Format

[inferred — NYRA is free for v1]
- Free products must be marked as free
- "No subscription required" / "free" must be accurate

## Key restrictions for NYRA v1 Fab Listing

| Restriction | Source | NYRA compliance action |
|-------------|--------|------------------------|
| No Epic/Fab logo in listing graphics | Fab Branding / Epic brand policy | DO NOT include any Epic/Fab logo in screenshots or banner |
| No third-party logos in listing graphics | Fab Branding / respective brand owners | DO NOT include Anthropic/OpenAI/Google/Adobe logos |
| No "official" / "partner" / "endorsed by" phrasing | Fab Content Guidelines | DO NOT use these terms for any brand |
| AI disclosure mandatory | Fab AI Disclosure Policy | Include AI-Disclosure Copy fragment in submission |
| Product name must match `.uplugin` FriendlyName | Fab Code Plugin checklist | FriendlyName = "NYRA" in all 4 engine descriptors |
| No misleading capabilities claims | Fab Content Guidelines | Copy describes only v1 capabilities accurately |

## Upgrade plan (founder-action, not executor)

The founder, when logged into Fab as a seller:
1. Visit the Fab Seller Policy / Branding Guidelines page (authenticated)
2. Copy the verbatim text relevant to listing naming and brand use
3. Update this file with the authenticated text, replacing the inferred
   sections
4. Commit as `docs(00-05): upgrade fab-seller-branding to authenticated seller-dashboard copy`

---
*Snapshot authored for NYRA Phase 0 SC#5 legal gate — 2026-04-29.*
*snapshot_method: cloudflare-blocked (inferred from public Fab surface).*
*Upgrade: founder authenticates to fab.com seller dashboard and upgrades.*
*Distinct from: fab-content-guidelines-SNAPSHOT.md (Plan 00-02) and fab-ai-disclosure-policy-SNAPSHOT.md (Plan 00-02).*
