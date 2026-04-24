---
plan: 00-02-epic-fab-policy-email
document_type: fallback-distribution-plan
status: plan-only
implements_at: Phase 8 DIST-02
author: NYRA Plan 00-02 executor
date: 2026-04-24
closes: "Phase 0 SC#2 half-two — direct-download fallback documented so Fab rejection stops being product-fatal (per CONTEXT.md D-07)"
supersedes: none
superseded_by: "(Phase 8 DIST-02 PLAN.md will implement this spec; DIST-02's SUMMARY.md will supersede this doc's implementation sections)"
handoff:
  owner_phase: 8
  owner_requirement: DIST-02
  contract: >
    Phase 8 DIST-02 plan author MUST read this doc end-to-end and either
    implement as written or explicitly document any deviations with
    rationale in the DIST-02 PLAN.md <context> section. DIST-02 is the
    IMPLEMENTATION plan; this file is the SPEC.
sections_required_by_PLAN_00_02:
  - "1. Trigger conditions"
  - "2. Installer toolchain choice"
  - "3. Update manifest format"
  - "4. SmartScreen mitigation strategy"
  - "5. Hosting location & CDN"
  - "6. Zero-config onboarding parity"
  - "7. Handoff to Phase 8"
  - "8. Open questions deferred to Phase 8"
---

# NYRA Direct-Download Fallback Plan (SPEC, not implementation)

> **Purpose.** Fab rejection stops being product-fatal. If Epic/Fab's
> verdict on the Plan 00-02 pre-clearance email is BLOCKED, or if the
> review turnaround exceeds NYRA's launch window by >4 weeks, or if a
> post-launch takedown happens, NYRA ships anyway via a signed Windows
> installer + update manifest delivered over two independent hosts. This
> document is the SPEC for that fallback; Phase 8 DIST-02 is the
> implementation plan that consumes it.
>
> **Status.** `plan-only`. No code lands from this file. Phase 8 writes
> the installer, the manifest publisher, and the auto-update client. This
> plan's job is to de-risk Phase 0 SC#2 by proving the fallback is
> buildable on demand — not to build it today.
>
> **Per CONTEXT.md D-07.** "Phase 0 ships the **plan** for direct-download
> distribution (signed Windows installer + update manifest + SmartScreen
> mitigation). **Implementing** the fallback lives in Phase 8 (Fab Launch
> Prep). Phase 0 only de-risks a Fab rejection by documenting the
> workaround." This file is that plan.

---

## 1. Trigger conditions

The direct-download fallback activates under exactly three trigger cases.
Each trigger is tied to a specific observable input; no trigger is left
to founder discretion without an explicit signal.

### Trigger (a) — Fab verdict is BLOCKED

**Input:** `correspondence/00-02-epic-fab-policy-email-response.md`
frontmatter `verdict: BLOCKED` + Sign-off triplet set to `Phase 8 primary
distribution: direct-download fallback`.

**Effect:** Fab submission is abandoned for v1. Direct-download fallback
becomes the **primary** distribution channel. Phase 8 DIST-02 plan is
promoted ahead of Phase 8 DIST-01 (Fab listing assembly) in the Phase 8
sequence. The EV cert (DIST-03) is still acquired — it's needed for the
installer regardless.

### Trigger (b) — Fab review turnaround exceeds launch window by >4 weeks

**Input:** Fab's response to Q2 (`expected_review_turnaround` in the
response file) + the founder's target launch date + the current date.
Formally: if `Fab-review-SLA-weeks > (target-launch-date – current-date) –
4-weeks-safety-buffer`, this trigger fires.

**Effect:** Direct-download fallback launches **first**, Fab listing
follows when it clears review. The founder gets real users (and their
feedback + public devlog fodder per PITFALLS §7.4) on schedule, without
letting Fab's queue block traction. The Fab listing becomes a credibility
signal ("now also on Fab") once it clears.

### Trigger (c) — Post-launch Fab takedown

**Input:** Fab issues a takedown notice (email, dashboard flag, or
listing removal). Recorded in a new file
`correspondence/post-launch-fab-takedown-YYYY-MM-DD.md` with the verbatim
notice + date.

**Effect:** Direct-download fallback remains available as a continuity
path. Existing users are not cut off; new users can still install. The
founder has time to address the takedown reason or switch permanently to
direct-download distribution, without a discontinuity for users.

### Trigger precedence

If multiple triggers fire, (a) > (b) > (c). Example: if Trigger (a) and
(b) both could fire, the BLOCKED verdict is decisive — direct-download is
primary permanently, not temporarily.

---

## 2. Installer toolchain choice

**Choice:** **Inno Setup** (https://jrsoftware.org/isinfo.php).

**Rationale:**

- **Free + permissively licensed.** Inno Setup is distributed under a
  modified BSD-like license that allows free use for any purpose including
  commercial distribution. No licensing budget line.
- **Widely-used for UE plugin installers.** Established pattern in the UE
  community; Fab reviewers have seen Inno-Setup-packaged plugins before,
  and a reasonable fraction of direct-download UE plugins in the wider
  ecosystem already use it.
- **Code-signing hooks first-class.** The `SignTool` directive
  integrates with Windows SDK `signtool.exe` so the EV cert signs the
  installer itself plus any bundled binaries in one pass at build-time.
- **Per-engine-version subdirectories supported.** Inno's `[Files]`
  section + `Components:` pattern handles the four engine-version
  subdirectories (`5.4/`, `5.5/`, `5.6/`, `5.7/`) matching the Fab
  per-engine layout. The user picks their engine version at install-time
  (or the installer auto-detects installed UE versions via registry).
- **Scriptable + repeatable.** `.iss` (Inno Setup Script) file checks
  into the repo alongside the source; build is `iscc installer.iss`. No
  GUI-click-through packaging step — fully CI-friendly.
- **Uninstaller included.** Windows Add/Remove Programs entry is
  auto-generated; uninstall cleans the plugin files + optionally the
  Gemma model cache at `%LOCALAPPDATA%/NYRA/models/` (user prompted
  per-run).
- **Windows 10 22H2 + Windows 11 compatible.** Matches NYRA's target
  platform (PROJECT.md + STACK.md §"Windows Platform Specifics").

**Candidates considered and rejected:**

| Candidate | Why rejected |
|-----------|--------------|
| NSIS | Legacy, less active maintenance, weaker signing integration |
| WiX Toolset (MSI) | Enterprise-flavored; MSI is more rigid for a user-land plugin install; steeper learning curve for solo dev |
| Portable zip + PowerShell setup script | No SmartScreen signing path for `.ps1`; reliability across AV vendors is worse than a signed `.exe`; no Add/Remove Programs entry |
| Chocolatey / winget package | Distribution channel, not installer toolchain; orthogonal (could add later as alternative install flavor) |
| Per-engine-version zip (user drops into `Engine/Plugins/`) | No signing story; no auto-update hook; manual install is a friction point; not acceptable for v1 UX |

**Decision rationale (D-09 discretion):** Inno Setup is the default
recommendation in STACK.md §"Windows Platform Specifics" and aligns with
the solo-dev / low-complexity / maximum-reliability posture NYRA's v1
demands. DIST-02 plan author may revisit if Phase 2 discovers a concrete
blocker, but the default stands.

---

## 3. Update manifest format

Direct-download users need a way to be notified when NYRA ships a new
version — Fab's update mechanism is unavailable to them. The manifest is
the contract between NYRA's release process (Phase 8 DIST-02) and the
plugin's in-editor update-check logic (Phase 2 subscription-bridge plans
wire the client-side polling; this plan only specs the contract).

### Manifest schema (JSON, authoritative)

```json
{
  "schema_version": 1,
  "version": "1.0.0",
  "ue_versions": ["5.4", "5.5", "5.6", "5.7"],
  "installer_url": "https://nyra.dev/releases/1.0.0/NYRA-1.0.0-Windows.exe",
  "installer_mirror_url": "https://github.com/<nyra-org>/nyra/releases/download/v1.0.0/NYRA-1.0.0-Windows.exe",
  "sha256": "<64-hex-char SHA256 of the installer binary>",
  "size_bytes": 123456789,
  "released_at": "2026-NN-NNTNN:NN:NNZ",
  "release_notes_url": "https://github.com/<nyra-org>/nyra/releases/tag/v1.0.0",
  "min_engine_version": "5.4",
  "max_engine_version": "5.7",
  "ai_content_flags": {
    "providers": ["anthropic-cli", "meshy", "comfyui", "computer-use", "gemma-local"],
    "no_seller_backend": true,
    "see": "https://nyra.dev/policy/ai-disclosure"
  },
  "signed_by": "<Subject CN of EV cert used to sign installer>",
  "signed_at": "<ISO-8601 UTC of signing time>"
}
```

**Schema versioning:** `schema_version: 1` is the initial contract. Any
breaking schema change (field rename, field removal) bumps
`schema_version` and publishes an alongside v2 manifest for a
two-release deprecation window.

### Hosting

- **Primary manifest URL:** `https://nyra.dev/updates/manifest.json`
  served over HTTPS, strong cache-bust (`Cache-Control: no-cache,
  no-store, max-age=0` + `ETag` per-release).
- **Mirror manifest URL:** `https://raw.githubusercontent.com/<nyra-org>/nyra/main/updates/manifest.json`
  (or the GitHub Pages equivalent), tracking the primary.

### Client polling cadence (Phase 2 implements; Phase 0 specs)

- Once per editor launch, background, failure-silent.
- Jittered by ±60 seconds to avoid manifest-host thundering herds on
  release day.
- On 4xx / 5xx / network error: silent. Never blocks editor operation.
- On new-version detected: a non-modal banner in the chat panel offers
  "Update available — download v1.0.1" with a link to the release notes.
  The user clicks to open the installer URL in their browser; the
  plugin does NOT auto-download or auto-install (permission posture:
  users stay in control).

### Signature verification (Phase 2 implements; Phase 0 specs)

- The plugin verifies the manifest's `sha256` against the downloaded
  installer before presenting the install prompt.
- The plugin verifies `signed_by` matches a pinned list of acceptable
  subject CNs so a manifest-compromise-without-cert-compromise is caught
  (belt-and-braces). Pinned list ships in the plugin binary; updating it
  requires a plugin release.

---

## 4. SmartScreen mitigation strategy

Windows SmartScreen assigns reputation based on the signing certificate.
Unsigned or OV-signed installers from a new publisher trigger the "Windows
protected your PC" warning dialog for ~30 days until reputation
accumulates. EV (Extended Validation) certificates establish reputation
immediately — no warmup.

### Primary strategy: EV code-signing cert

- **Cert type:** EV Code Signing Certificate, hardware-token-based (FIPS
  140-2 Level 2 requirement per CA/Browser Forum baseline).
- **Issuer candidates:** Sectigo, DigiCert, SSL.com, GlobalSign (all
  recognized by Microsoft Authenticode for SmartScreen reputation).
- **Budget:** $400–700/yr (PROJECT.md explicit budget line +
  STACK.md §"Windows Platform Specifics").
- **Acquisition phase:** **Phase 2 DIST-03** is the requirement that
  owns EV cert acquisition. Direct-download fallback piggybacks on the
  same cert — no separate budget line, no separate acquisition work.
- **Usage:** Sign the Inno-generated `.exe` installer + the bundled
  `NyraHost` Python launcher + bundled `llama-server.exe` + `ffmpeg.exe`
  + optional `yt-dlp.exe`. All binaries signed by the same cert.

### Contingency: EV cert delayed

If DIST-03 is delayed and the direct-download trigger fires before the
EV cert is in hand, the emergency path is a standard OV code-signing
cert with aggressive pre-warm:

- **Cert type:** OV (Organization Validation) Code Signing Certificate.
  Cheaper ($100–300/yr), faster to issue (1–3 days), but SmartScreen
  reputation requires ~30 days of installs at non-trivial volume.
- **Pre-warm via Microsoft Authenticode submission portal:** Microsoft
  accepts direct binary submissions for a-priori reputation review at
  the Microsoft Defender Security Intelligence portal. This is an
  emergency path only — Microsoft's turnaround is days to weeks and
  reputation is not guaranteed.
- **User messaging:** The NYRA website + GitHub README document the
  expected SmartScreen warning during the OV warmup window, with a
  screenshot of the "More info → Run anyway" click path. Transparency
  over reputation-engineering tricks.
- **Migration:** Once the EV cert lands (DIST-03), the next point
  release re-signs with EV and ships a manifest update forcing
  reinstall-on-next-launch (`force_resign: true` flag in a v2 manifest
  schema). OV-signed installers continue to verify but new downloads
  route to EV.

### SmartScreen-adjacent concerns

- **Windows Defender heuristics** sometimes flag subprocess-spawning
  plugins even with EV signatures. Mitigation: all bundled binaries
  live under the plugin's `Binaries/ThirdParty/` directory (not
  `%APPDATA%` which triggers more AV heuristics per STACK.md). The
  Gemma model lives in `%LOCALAPPDATA%/NYRA/models/` because it is
  user-consented + genuinely data, not code.
- **Corporate AV products** (CrowdStrike, SentinelOne, etc.) have
  per-vendor heuristics NYRA cannot influence. Mitigation: the
  installer + all bundled binaries include VERSIONINFO + ProductName +
  CompanyName metadata tied to the EV cert CN, giving enterprise AV
  the context needed to allowlist NYRA via policy.

---

## 5. Hosting location & CDN

### Primary host: `https://nyra.dev/releases/`

- **Custom domain:** `nyra.dev` acquired as part of Plan 00-03
  (trademark + domain + handles). If the trademark screening blocks
  NYRA as a name, the backup domain from Plan 00-03's 5 pre-screened
  candidates takes its place — the manifest URL updates accordingly in
  a v2-manifest release.
- **Backing static host:** Cloudflare Pages or Vercel (zero-cost
  tier). Serves `/releases/<version>/NYRA-<version>-Windows.exe` +
  `/updates/manifest.json` + `/policy/ai-disclosure` (NYRA policy
  landing, Plan 00-05 owns copy). No server-side code; purely static.
- **TLS:** Managed automatically by the static host.
- **Rationale:** Zero-cost hosting fits the free-plugin budget; custom
  domain is a trust signal vs. a raw github.io URL.

### Mirror host: GitHub Releases

- **Mirror URL:** `https://github.com/<nyra-org>/nyra/releases/download/v<version>/NYRA-<version>-Windows.exe`.
- **Why GitHub:** Already free, already versioned, already CDN-fronted
  (Fastly-backed). Standard distribution channel for OSS-adjacent
  tooling. Listed in the update manifest as `installer_mirror_url`.
- **Promoted use:** If the primary host is temporarily unreachable,
  the in-editor update prompt + the website README both link to the
  GitHub Releases page as an obvious alternative.

### Rationale for two independent hosts

A single-provider outage (Cloudflare incident, DNS misconfiguration on
`nyra.dev`, GitHub outage) cannot block all users from installing. The
plugin's update-check logic tries primary, falls back to mirror, and
reports manifest-fetch failure only if both fail. Installing users are
handed both URLs up-front so they can choose.

### What is NOT hosted

- **No NYRA-owned backend.** `nyra.dev` serves static assets only; no
  API endpoints, no auth flows, no analytics endpoints, no telemetry
  ingestion. This is load-bearing for the PROJECT.md constraint
  "Cost model: Free on Fab — no backend billing; user provides their
  own Claude subscription" and the Plan 00-02 email's Fact 3 ("NYRA
  does NOT operate or call any NYRA-owned backend").

---

## 6. Zero-config onboarding parity

Per **DIST-04** (zero-config install), the direct-download install path
must deliver the same first-run experience as the Fab install path —
the user opens UE, enables the plugin, runs `claude setup-token` once,
and is operational. Two explicit divergences from the Fab flow, both
minor:

### Divergence 1: Installer prompts for UE install location

- **Fab path:** Fab installs the plugin into Epic-managed UE locations
  automatically; no user input.
- **Direct-download path:** The Inno Setup installer reads the
  Windows registry for installed UE versions (`HKLM:\SOFTWARE\EpicGames\Unreal Engine\<version>`
  typically carries `InstalledDirectory`), auto-selects the default
  plugin destination (e.g. `<UE>/Engine/Plugins/Marketplace/NYRA/` or
  user-chosen `<Project>/Plugins/NYRA/`), and lets the user confirm or
  override. If no UE install is detected, the installer asks the user
  to select one manually.

### Divergence 2: Uninstall via Windows Add/Remove Programs

- **Fab path:** Uninstall via Fab's library UI (manages Fab-installed
  content).
- **Direct-download path:** Uninstall via Windows Settings → Apps →
  Installed apps → NYRA → Uninstall. The Inno-generated uninstaller
  removes plugin files; the user is prompted whether to also remove
  the Gemma model cache at `%LOCALAPPDATA%/NYRA/models/` (default:
  keep — the download is expensive and many users reinstall).

### Otherwise identical

- `claude setup-token` runs once; the token lives in
  `~/.claude/.credentials.json` regardless of install path.
- Meshy / ComfyUI API keys live in UE editor preferences regardless
  of install path.
- First-run Gemma download prompt + consent dialog is identical.
- Plugin UI, keybindings, editor-subsystem lifecycle are identical.

### DIST-04 acceptance implication

Phase 8 DIST-04's acceptance bar covers both paths: "zero-config
first-run works whether installed via Fab or direct-download".

---

## 7. Handoff to Phase 8

**Phase 8 (Fab Launch Prep) DIST-02 implements this plan.** The DIST-02
plan author MUST:

1. **Read this doc end-to-end** before writing the DIST-02 PLAN.md.
2. **Either implement each Section (1–6) as written, or explicitly
   document any deviations with rationale** in the DIST-02 PLAN.md
   `<context>` section. Deviations are allowed; unexplained deviations
   are not.
3. **Consume the triggers (Section 1) as inputs** to the DIST-02
   execution-order decision — if Trigger (a) is active at the time
   DIST-02 runs, direct-download becomes primary (re-order Phase 8
   plans accordingly).
4. **Confirm the EV cert status via DIST-03** before relying on the
   Section 4 primary strategy. If DIST-03 is delayed, activate the
   Section 4 contingency path (OV cert + Microsoft Authenticode
   pre-warm).
5. **Write the Inno Setup `.iss` file**, the manifest publisher
   (probably a short Python or Node script invoked in the release-tag
   CI job), and the plugin-side update-check client (C++ in
   `NyraEditor`, using `FHttpModule`).
6. **Update this file's `superseded_by:` frontmatter field** to point
   at `DIST-02-SUMMARY.md` once DIST-02 lands.

**DIST-02 is the IMPLEMENTATION plan; this file is the SPEC.**

### Cross-plan links

- **DIST-01:** Fab listing assembly — the primary distribution channel
  when Trigger (a) does NOT fire. DIST-02 and DIST-01 ship in the same
  Phase 8; only their relative ordering is controlled by the triggers.
- **DIST-03:** EV code-signing cert acquisition — required for both
  DIST-01 (Fab also benefits from EV-signed binaries) and DIST-02
  (SmartScreen primary strategy). Phase 2 if budget permits, else
  Phase 8.
- **DIST-04:** Zero-config onboarding — binds both install paths to the
  same first-run UX. Depends on both DIST-01 and DIST-02.

---

## 8. Open questions deferred to Phase 8

This plan does NOT resolve the following; DIST-02 answers them when it
gets there. Listed honestly so the founder knows what was parked.

### Q8.1. Do we mirror installer artifacts via IPFS?

Tradeoff: additional resilience vs. additional complexity. IPFS pinning
is inexpensive but adds a dependency + a second URL format users must
understand. **Default recommendation:** defer to post-v1 unless GitHub
or the primary host experiences a meaningful outage during v1's
direct-download window.

### Q8.2. Do we ship Linux/macOS installers when v1.1 lands cross-platform?

NYRA v1 is Windows-only (PROJECT.md constraint). When v1.1 (or later)
adds cross-platform support, direct-download distribution needs a .dmg
(macOS) and .deb/.AppImage (Linux) story. **Default recommendation:**
DMG + AppImage mirroring the Inno pattern; defer detailed planning
until the cross-platform requirement is actually on the roadmap.

### Q8.3. Dedicated auto-updater or piggyback on UE's plugin-update mechanism?

UE's built-in plugin-update mechanism is Fab-tied; direct-download users
don't benefit. Options:
- **(a) NYRA's own in-editor update-check** (this doc's Section 3).
  Simple, user-consented, no auto-install.
- **(b) Bundled auto-updater** (e.g. Squirrel.Windows) that silently
  downloads and applies updates. Higher UX polish but more moving
  parts + elevated-permissions story.

**Default recommendation:** start with (a) for v1 direct-download; add
(b) in v1.1+ if user feedback demands silent updates.

### Q8.4. Crash-report opt-in for direct-download users?

Fab probably provides a seller-dashboard-crash-report feed (unverified
until Plan 00-02 Fab response lands — may be a Q4 follow-up). Direct-
download users have no equivalent. Options:
- **(a) No crash reporting v1.** Consistent with the "no backend, no
  telemetry" wedge. Users manually report via GitHub Issues + the chat
  panel's "Report an issue" link.
- **(b) Opt-in crash telemetry to a hosted Sentry / self-hosted
  equivalent.** Violates the "no NYRA-owned backend" posture unless
  self-hosted under user's control.

**Default recommendation:** (a) for v1. The PROJECT.md posture is strict
on the no-backend wedge; crash visibility comes from GitHub Issues +
the founder's direct support inbox + in-plugin diagnostics drawer
(Phase 1 Plan 13 landed).

### Q8.5. Uninstaller behavior for the Gemma model cache?

~3.16 GB of Gemma weights at `%LOCALAPPDATA%/NYRA/models/`. Uninstaller
prompt:
- **(a) Keep by default, offer checkbox to delete.** Preserves user's
  expensive download for reinstalls.
- **(b) Delete by default, offer checkbox to keep.** Tidier but burns
  user bandwidth on reinstall.

**Default recommendation:** (a) — the download is expensive, users
reinstall more often than permanently uninstall. DIST-02 wires this
into the Inno uninstaller dialog.

### Q8.6. Release cadence + version-numbering discipline?

Semantic versioning is the obvious pick; cadence is an open decision:
biweekly, monthly, or as-ready. Impacts manifest-polling cost + user
patience for update prompts. **Default recommendation:** monthly
release cadence during launch quarter + as-ready afterwards, unless
user feedback suggests otherwise. DIST-02 owns the detailed release
process doc.

---

## Summary for closure ledger (Plan 00-06)

This file's existence — with all 8 required sections present per the
PLAN.md `<done>` criterion — closes the SECOND half of Phase 0 SC#2.
The FIRST half (Epic/Fab written response with founder verdict) is the
external-wait piece captured by
`correspondence/00-02-epic-fab-policy-email-response.md`. Per
CONTEXT.md D-07, SC#2 is closed when BOTH artifacts exist — and BLOCKED
does not fail SC#2 because this fallback plan covers it.

**Plan 00-06 closure-ledger anchor:** `grep -l "status: plan-only" legal/00-02-direct-download-fallback-plan.md` returns the path iff this doc exists. Combined with a `verdict: PERMITTED | CONDITIONAL | BLOCKED` bit in the response file, SC#2 flips.

---

*Plan: 00-02-epic-fab-policy-email*
*Document: direct-download fallback SPEC*
*Status: plan-only — Phase 8 DIST-02 implements*
*Authored: 2026-04-24*
