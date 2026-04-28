---
document_title: "NYRA End User License Agreement"
version: "0.1.0-draft"
status: "founder-first-draft"
counsel_reviewed: false
counsel_review_scheduled: "post-v1 or at-founder-discretion"
effective_date: TBD-v1-launch
author: founder
date: "2026-04-29"
jurisdictions: "United States (venue), Worldwide (distribution)"
incorporates:
  - "legal/00-04-nyra-eula-gemma-notice-appendix.md (Appendix: Gemma 3 Model Notice — incorporated by reference)"
plan: "00-04-gemma-license-and-eula-draft"
scope_note: >
  This is the NYRA v1 EULA first draft per D-06. It covers standard UE-plugin
  boilerplate sections plus exactly two D-06 novel areas: (1) generated-content
  liability passthrough covering Meshy / ComfyUI / Substance / Claude outputs,
  and (2) reference-video ephemeral processing (yt-dlp + keyframes + tmp delete).
  Counsel review is explicitly deferred to post-v1 or at founder discretion.
  This is NOT a legally-negotiated contract — it is a founder-authored working
  draft for counsel to review at v1.1.
---

# NYRA End User License Agreement

**Version:** 0.1.0-draft
**Date:** 2026-04-29
**Status:** Founder-first draft — not legally reviewed
**Effective Date:** TBD (to be set at v1 launch)

> **Note:** This is a founder-authored first draft. It has not been reviewed by
> legal counsel. Review is scheduled for post-v1 or at founder discretion per
> D-06. Sections marked **D-06 NOVEL CLAUSE** contain non-standard provisions
> that require careful counsel review. All other sections are standard UE-plugin
> boilerplate, minimally adapted for a free plugin.

---

## 1. Definitions

**"NYRA"** means the NYRA Unreal Engine plugin (the "Plugin"), consisting of the
UE5 C++ plugin shell, the Python MCP sidecar (`NyraHost`), and the local Gemma
3 4B inference process (`NyraInfer`), together the "NYRA software."

**"User"** or **"you"** means the individual or entity that installs and uses NYRA
on their own machines. Where "you" refers to a studio or organization, "you"
means the authorized individual user within that organization who accepted these
terms.

**"Plugin"** means the UE5 C++ plugin files, Python sidecar, llama.cpp runtime
binaries, bundled Gemma 3 4B model files, and any documentation shipped together
as NYRA.

**"Third-Party Components"** means the external services, tools, and models that
NYRA orchestrates or bundles: (a) the Claude Code CLI (Anthropic) — user-provided
via the user's own subscription; (b) Meshy (MeshyAI) — user-provided API key;
(c) ComfyUI — user-installed; (d) Substance 3D Sampler (Adobe) — user-provided
license, driven by NYRA via computer-use; (e) the Gemma 3 4B model (Google) —
bundled with NYRA per the Gemma license.

**"Generated Content"** means any meshes, textures, materials, scene
configurations, code, text, images, video segments, or other output produced by
any Third-Party Component or by NYRA's own processing in the course of a NYRA
session.

**"Reference Material"** means any image, video, URL, or other content you
provide to NYRA as a reference input for a session.

**"Local Fallback Model"** means the Gemma 3 4B IT QAT Q4_0 GGUF model that NYRA
bundles or downloads on demand for offline / privacy-mode operation.

**"Fab"** means the Epic Games Fab marketplace (fab.com) or any other official
NYRA distribution channel designated by NYRA's founder.

---

## 2. License Grant

Subject to the terms of this Agreement, NYRA grants you a **worldwide,
royalty-free, non-exclusive, non-transferable license** to install and use NYRA
on your own machines for any lawful purpose, including commercial Unreal Engine
development, without payment to NYRA.

This license does **NOT** permit you to:
- Redistribute NYRA independently of Fab or official distribution channels.
- Sublicense, rent, or lease NYRA.
- Reverse-engineer the Plugin to extract the bundled Gemma model or other
  components for use outside NYRA.
- Use NYRA in a manner that violates any applicable law or any Third-Party
  Component's terms of service.

NYRA is a free plugin. No license key, no payment, no commercial resale
arrangement is associated with this EULA in v1.

---

## 3. Permitted Uses

You may use NYRA to:
- Install the Plugin in your Unreal Engine 5.4/5.5/5.6/5.7 projects (including
  commercial projects).
- Run NYRA's agent alongside your UE development workflow.
- Use the Claude Code CLI, Meshy, ComfyUI, Substance 3D Sampler, and the Gemma
  Local Fallback Model in connection with NYRA as intended.
- Provide your own Reference Material for NYRA to process.
- Download and use the Gemma 3 4B model for offline / privacy-mode operation
  in connection with NYRA.

---

## 4. Prohibited Uses

You may NOT use NYRA (or direct NYRA to be used) for any of the following:

1. **Unauthorized redistribution:** Redistributing NYRA independently of Fab or
   official NYRA distribution channels; selling NYRA as a standalone product.

2. **Attribution removal:** Stripping NYRA's attribution from the plugin,
   documentation, or any bundled components.

3. **Anthropic ToS violations:** Using NYRA to violate Anthropic's Acceptable
   Use Policy or any terms applicable to your Claude subscription. In particular:
   NYRA does not permit third-party applications to offer Claude login or
   sub-accounting; NYRA drives your own local Claude Code CLI using your own
   subscription credentials.

4. **Google / Gemma license violations:** Using Gemma in a manner that violates
   the Gemma Terms of Use or Gemma Prohibited Use Policy. See **Appendix: Gemma
   3 Model Notice** (incorporated by reference).

5. **Meshy ToS violations:** Using Meshy-generated assets in ways that violate
   MeshyAI's terms of service.

6. **ComfyUI license violations:** Using ComfyUI in ways that violate its
   open-source license.

7. **Epic / Fab policy violations:** Using NYRA to violate Epic Games' Fab
   Content Guidelines, the Epic Games Terms of Service, or any other Epic
   platform terms.

8. **Adobe Substance 3D Sampler violations:** Using NYRA or computer-use to
   operate Adobe Substance 3D Sampler in ways that violate Adobe's license
   terms or terms of service.

9. **Generation of prohibited content:** Using NYRA or any Third-Party
   Component to generate content that any applicable law, policy, or
   Third-Party Component terms prohibit — including but not limited to
   content that violates the Gemma Prohibited Use Policy.

10. **Copyright infringement:** Providing Reference Material to NYRA in a
    manner that infringes the copyright of the Reference Material's rights
    holder, except where you have the right to create derivative works from
    that material for your own UE project purposes.

---

## 5. Third-Party Components

NYRA orchestrates several third-party services and bundles one third-party
model. Each Third-Party Component has its own governing terms:

### Claude Code CLI (Anthropic)
NYRA does not provide your Claude subscription. You provide your own
Claude Pro or Max subscription. Your use of the Claude Code CLI through NYRA
is governed by Anthropic's applicable terms of service and usage policies for
your subscription. **NYRA never stores your Anthropic credentials.** NYRA
drives your local `claude` CLI subprocess; authentication is handled by the
CLI itself using your machine's stored credentials.

### Meshy (MeshyAI)
Meshy is an opt-in, API-first integration. You provide your own Meshy API key
configured in NYRA's settings. Your use of Meshy is governed by MeshyAI's
terms of service. NYRA makes no representations about Meshy's output;
**Meshy output is governed by Meshy's terms**.

### ComfyUI (Open Source)
ComfyUI is an opt-in, user-installed tool. NYRA communicates with ComfyUI via
HTTP API. Your installation of ComfyUI and your use of ComfyUI workflows is
governed by ComfyUI's upstream open-source license. **ComfyUI workflow output
is your responsibility.**

### Substance 3D Sampler (Adobe)
Substance 3D Sampler is driven via computer-use (Claude Opus 4.7 acting on
your screen) with your explicit consent for each session. You must hold a
valid Substance 3D Sampler license from Adobe. Your use of Substance 3D Sampler
is governed by Adobe's terms of service and your Substance license agreement.
NYRA invokes Substance 3D Sampler only when you explicitly direct it;
**Substance Sampler output is governed by Adobe's terms per your Substance
license**.

### Gemma 3 4B Model (Google)
NYRA bundles the Gemma 3 4B model subject to Google's Gemma Terms of Use.
This is not a Meshy / ComfyUI / Anthropic commercial product relationship — it
is a redistribution of Google's open-weight model under Google's license.
**See Appendix: Gemma 3 Model Notice** (incorporated by reference from
`legal/00-04-nyra-eula-gemma-notice-appendix.md`).

---

## 6. Generated Content — Liability Passthrough

> **D-06 NOVEL CLAUSE — requires counsel review before v1.1**

NYRA orchestrates third-party tools (including Meshy, ComfyUI, Substance 3D
Sampler, and Claude) to produce assets such as 3D meshes, textures, materials,
scene configurations, and code. **Ownership of, licensing of, and liability
for any such Generated Content flow from the originating third-party tool's
own terms directly to you.** NYRA makes no representations or warranties
regarding the originality, copyright status, fitness for any purpose, or
commercial usability of Generated Content. You are solely responsible for
reviewing each generated asset against the relevant Third-Party Component's
terms and any applicable laws before commercial use.

### Sub-provisions:

**Meshy output:** Meshy-generated 3D assets are governed by MeshyAI's terms of
service. You are responsible for reviewing those terms before incorporating
Meshy output into a commercial UE project.

**ComfyUI workflow output:** The output of any ComfyUI workflow invoked through
NYRA is generated by your ComfyUI installation using upstream models and
workflows. You bear sole responsibility for ComfyUI output, including ensuring
that your workflow's upstream model licenses permit your intended commercial
use.

**Substance 3D Sampler output:** Substance Sampler output is generated by
Adobe's software under your Adobe Substance license. You are responsible for
ensuring your Adobe Substance license permits the commercial use you intend.

**Claude-generated code and text:** Claude-generated code and text is produced
by Claude under your own Claude subscription, governed by Anthropic's usage
policies. You are responsible for reviewing Claude output, particularly for
copyright issues in generated code, before incorporating it into commercial
projects.

---

## 7. Reference Material — Ephemeral Processing

> **D-06 NOVEL CLAUSE — requires counsel review before v1.1**

NYRA supports reference-driven workflows where you may provide images, video
files, or URLs to videos (including YouTube links) as references for analysis.

**What NYRA does with reference material:**

When you provide a **URL** to NYRA:
1. NYRA downloads the referenced content to your local temporary directory
   via `yt-dlp`.
2. NYRA extracts **up to 16 keyframes** from the downloaded video using FFmpeg.
3. NYRA submits those keyframes plus limited text context to Claude (via your
   local Claude Code CLI, through your own subscription).
4. NYRA **deletes the full downloaded content** from your temporary directory
   after the analysis run completes.

When you provide a **local file** (image or video):
- The file is processed locally and is not transmitted to any remote server.

**NYRA does not transmit, host, or redistribute the full video or other
downloaded Reference Material to any NYRA-owned server.** No such server exists.
NYRA processes Reference Material ephemerally.

**Your representations and warranties:** By providing Reference Material to NYRA,
you represent and warrant that:

1. You have the right to download and use the Reference Material for the purpose
   of producing derivative Unreal Engine scenes in your own projects.
2. You will not direct NYRA to copy the protected expression of copyrighted
   works — only to infer structural, lighting, and compositional properties
   from Reference Material.
3. You assume all responsibility for compliance with the copyright and platform
   terms of the source site, including YouTube's Terms of Service.

**yt-dlp fetching:** You may disable yt-dlp-based URL fetching entirely in
NYRA settings if you prefer to only provide local files. Ephemeral processing
is the default; it is not a user-configurable opt-out from the delete behavior
above — it is the implementation behavior.

---

## 8. Data We Do Not Collect

> This section is the **built-in minimal privacy policy** for v1. It is
> incorporated here to avoid spawning a separate standalone privacy policy
> document in Phase 0. A full standalone privacy policy may be authored at
> v1.1 if NYRA later adds any telemetry, account system, or hosted services.

NYRA operates **no backend server.** No NYRA-owned telemetry, no NYRA-owned
analytics, no NYRA-owned account system is associated with NYRA v1.

1. **Local storage only:** All chat history, attachments, session state, and
   settings are stored locally under your Unreal Engine project's `Saved/NYRA/`
   directory. NYRA does not read, transmit, or back up this data to any remote
   service.

2. **No automatic crash reporting:** NYRA does not automatically report
   crashes or diagnostics to any server. You may manually submit a diagnostics
   bundle via the in-plugin diagnostics drawer — this is a deliberate,
   user-initiated action only.

3. **Third-party service data:** Third-party services you connect to NYRA
   (Claude, Meshy, ComfyUI, Adobe Substance, Google Gemma) receive only the
   content you explicitly route to them through NYRA. Each service's own
   privacy policy governs its data handling. NYRA does not add tracking
   pixels, analytics beacons, or any additional data collection to content
   routed through those services.

4. **Gemma model download:** When NYRA downloads the Gemma 3 4B GGUF model
   on demand, it fetches the file from HuggingFace directly to your local
   cache (`%LOCALAPPDATA%/NYRA/models/`). NYRA does not log or transmit the
   download event.

---

## 9. Warranty Disclaimer

**NYRA IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND.**

NYRA is a free plugin. TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, NYRA
AND ITS FOUNDER DISCLAIM ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT NOT
LIMITED TO THE IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE, AND NON-INFRINGEMENT.

NYRA does not warrant that:
- NYRA will be error-free, uninterrupted, or meet your specific requirements.
- The Plugin will produce accurate, reliable, or legally compliant Generated
  Content.
- Any Third-Party Component will function without interruption or error.
- NYRA is free from viruses or other harmful components (you are responsible
  for maintaining your own security and antivirus measures).

Because NYRA is free, some jurisdictions do not allow the exclusion of implied
warranties; to the extent those apply, this disclaimer applies to the maximum
extent permitted.

---

## 10. Limitation of Liability

**TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, IN NO EVENT SHALL NYRA
OR ITS FOUNDER BE LIABLE FOR ANY SPECIAL, INCIDENTAL, CONSEQUENTIAL, EXEMPLARY,
OR PUNITIVE DAMAGES ARISING OUT OF OR IN CONNECTION WITH THIS AGREEMENT OR
YOUR USE OF NYRA — INCLUDING BUT NOT LIMITED TO LOSS OF PROFITS, LOSS OF DATA,
BUSINESS INTERRUPTION, OR REPUTATIONAL HARM — REGARDLESS OF WHETHER SUCH
DAMAGES WERE FORESEEABLE OR WHETHER NYRA WAS ADVISED OF THE POSSIBILITY OF
SUCH DAMAGES.**

Because NYRA is provided free of charge, NYRA's total cumulative liability under
this Agreement is limited to $0.00 USD. Some jurisdictions do not allow the
limitation of liability for free products; to the extent those apply, this
limitation applies to the maximum extent permitted.

---

## 11. Indemnification

You agree to indemnify, defend, and hold harmless NYRA and its founder from and
against any and all claims, damages, losses, costs, and expenses (including
reasonable attorneys' fees) arising out of or in connection with:

1. **Your Generated Content:** Any claim that your Generated Content —
   produced using any Third-Party Component through NYRA — infringes the
   intellectual property rights of a third party or violates any applicable
   law.

2. **Your Reference Material:** Any claim arising from your provision of
   Reference Material to NYRA in a manner that infringes the copyright or
   other rights of the Reference Material's rights holder.

3. **Your use of NYRA:** Your violation of this Agreement, including the
   Gemma license, Meshy's terms, ComfyUI's license, Adobe's Substance terms,
   Anthropic's usage policies, Epic's Fab guidelines, or any applicable law.

4. **Regulatory misuse:** Any regulatory enforcement action or third-party
   claim arising from your use of NYRA or any Third-Party Component in a
   regulated industry or in a manner that violates applicable law.

---

## 12. Termination

This Agreement is effective from the date you install NYRA and continues
until terminated.

**NYRA may terminate this Agreement** immediately, without notice, if you
materially breach any provision of this Agreement, including the Gemma license
terms, the prohibited uses in Section 4, or the indemnification obligations
in Section 11.

**You may terminate this Agreement** at any time by uninstalling NYRA and
deleting all NYRA files from your machines.

Upon termination, all licenses granted herein immediately cease. Sections 6
(Generated Content), 7 (Reference Material — Ephemeral Processing), 8 (Data
We Do Not Collect), 9 (Warranty Disclaimer), 10 (Limitation of Liability),
11 (Indemnification), and 13 (Governing Law and Venue) survive termination.

---

## 13. Governing Law and Venue

> **Founder-fill:** Update this section at counsel review. Jurisdiction and
> venue should reflect the founder's location and preference.

This Agreement shall be governed by and construed in accordance with the laws
of the **United States** and the state in which the NYRA founder resides at
the time of v1 launch, without regard to conflict-of-law principles.

> **[Founder-fill before v1 launch:]** Replace "the state in which the NYRA
> founder resides" with the specific state name.

Any dispute arising out of or in connection with this Agreement shall be
resolved in the **state or federal courts located in [FILL: county-level court
in the governing state]** to the exclusion of other venues. You hereby
irrevocably consent to the personal jurisdiction and venue of those courts.

> **[Founder-fill before v1 launch:]** Fill in the specific county and court
> level (e.g., "the state courts in King County, Washington" or "the federal
> courts in the Northern District of California").

NYRA and you agree that the United Nations Convention on Contracts for the
International Sale of Goods (CISG) does not apply to this Agreement.

---

## 14. Changes to EULA

NYRA may update this EULA from time to time. Updated versions will be included
in the plugin changelog with a version-number bump. Continued use of NYRA after
an EULA update constitutes acceptance of the updated terms.

If an update introduces a material change that affects your rights or
obligations, NYRA will make reasonable efforts to notify you through the
plugin's changelog before the updated EULA takes effect.

EULA version history will be maintained in the plugin's git repository and
in each Fab release note.

---

## 15. General

**Severability:** If any provision of this Agreement is held by a court of
competent jurisdiction to be invalid, illegal, or unenforceable, the remaining
provisions continue in full force and effect.

**Entire Agreement:** This Agreement, together with the Gemma 3 Model Notice
(Appendix A) incorporated by reference, constitutes the entire agreement
between you and NYRA with respect to NYRA and supersedes all prior agreements,
understandings, and communications, whether oral or written.

**Assignment:** You may not assign this Agreement or any rights or obligations
under it without NYRA's prior written consent. NYRA may assign this Agreement
to a successor in connection with a sale of the NYRA project or a change of
control.

**No waiver:** NYRA's failure to enforce any provision of this Agreement does
not constitute a waiver of the right to enforce that provision or any other
provision in the future.

**Third-party beneficiaries:** Third-Party Component providers (Anthropic,
Google, MeshyAI, Adobe, ComfyUI) are third-party beneficiaries of this
Agreement solely with respect to the provisions that relate to their
respective services and the Gemma model.

---

## Appendix A: Gemma 3 Model Notice

> **Incorporated by reference from:** `legal/00-04-nyra-eula-gemma-notice-appendix.md`
> (file: `00-04-nyra-eula-gemma-notice-appendix.md`)
>
> **Source:** Gemma Terms of Use at `https://ai.google.dev/gemma/terms`
> (snapshotted 2026-04-25)

NYRA distributes the Gemma 3 4B Instruction-Tuned model (QAT Q4_0 GGUF format)
developed by Google LLC. Your use of the Gemma model through NYRA is governed
by the Gemma Terms of Use and Gemma Prohibited Use Policy in addition to this
Agreement.

The Gemma 3 Model Notice (`legal/00-04-nyra-eula-gemma-notice-appendix.md`) is
incorporated herein by reference. That notice sets out:
- The Gemma Terms of Use URL and Gemma Prohibited Use Policy URL.
- Key prohibited uses (not an exhaustive list; the full Gemma terms govern).
- Output ownership (you own your Gemma-generated output).
- Redistribution rules.

By using NYRA's local-fallback / offline mode, you agree to comply with the
Gemma Terms of Use and Gemma Prohibited Use Policy.

---

## Counsel Review Checklist

> For post-v1 counsel review. Each entry flags the specific concern or
> ambiguity in the noted section.

**§6 — Generated Content — Liability Passthrough (D-06 NOVEL CLAUSE)**
- *Concern:* Does the "liability flows from third-party tool directly to user"
  language effectively disclaim NYRA warranty without creating an unintended
  assumption-of-risk argument under applicable consumer protection law?
- *Concern:* Does the sub-provision for ComfyUI adequately address the risk that
  a user's ComfyUI workflow uses a model with restrictive license — should
  NYRA add a specific warning or acknowledgment step?
- *Concern:* Should the Generated Content clause be accompanied by a specific
  indemnity back from the user against third-party IP claims, or is the
  current §11 general indemnity sufficient?

**§7 — Reference Material — Ephemeral Processing (D-06 NOVEL CLAUSE)**
- *Concern:* Does the "up to 16 keyframes" limit constitute a warranty that is
  technically breached if a future implementation changes the keyframe count?
- *Concern:* Is the user-representation ("you have the right to download and
  use the reference material") legally enforceable when NYRA does not
  validate rights before processing?
- *Concern:* Should there be a specific exclusion for providing a YouTube
  URL where the video is clearly a third-party copyrighted work, or is the
  "only infer structural properties" standard sufficient?

**§8 — Data We Do Not Collect**
- *Concern:* Does this section (built-in minimal privacy policy) satisfy the
  "privacy policy" requirement for Fab submission or for the GDPR / CCPA if
  a European or Californian user downloads NYRA from Fab worldwide?
- *Concern:* Should "no automatic crash reporting" be accompanied by a specific
  technical description of what IS collected (chat logs written to
  `Saved/NYRA/`, local model cache files)?
- *Counsel action:* Determine whether a standalone privacy policy doc is
  needed before v1 launch or whether this section is sufficient for a free,
  no-backend plugin.

**§13 — Governing Law and Venue**
- *Concern:* Venue selection is county-level in founder's state — counsel
  should confirm this is appropriate and not inadvertently overly favorable
  to one party.
- *Concern:* "State in which the NYRA founder resides" is not a valid choice
  of law; this needs to be a specific state before v1 launch.
- *Counsel action:* Confirm the governing law state and appropriate venue
  with counsel at post-v1 review.

**Appendix A — Gemma 3 Model Notice**
- *Concern:* Is the Gemma Notice's "incorporation by reference" mechanism
  (referencing a separate file in the repo) legally sufficient to bind
  the user, or should the full Gemma prohibited-use bullets be reproduced
  inline in the EULA itself?
- *Concern:* The Gemma license permits commercial redistribution with
  "terms-notice" — counsel should confirm the Gemma Notice appendix
  satisfies the letter of Google's redistribution requirement for NYRA's
  specific delivery model (Fab download + on-demand GGUF fetch).
- *Concern:* The Gemma license "Updates to the Terms" clause means Google's
  terms may change prospectively. Should the EULA include a mechanism to
  notify users if Gemma's prohibited-use list is updated and the update
  materially affects their use?

---

*NYRA EULA draft end. Version 0.1.0-draft, 2026-04-29. Founder-first draft — not legally reviewed.*
