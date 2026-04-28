---
final_name: NYRA
final_name_source: Plan 00-03 trademark verdict (LOCKED 2026-04-24)
final_name_status: LOCKED
compliance_reference: brand/00-05-brand-compliance-summary.md
phase_8_handoff: DIST-01 consumes these fragments verbatim at Fab submission time
author: NYRA Plan 00-05 executor
date: 2026-04-29
plan: 00-05-brand-guideline-archive-and-copy
phase: 00-legal-brand-gate
note_on_backup_names: >
  If Plan 00-03's rollback is ever triggered (cease-and-desist from NYRA
  enforcer, or founder-manual-verdict upgrade flips to BLOCKED), find-replace
  NYRA -> AELRA throughout this document before Phase 8 DIST-01 consumes it.
  The compliance rules in 00-05-brand-compliance-summary.md apply to the
  backup name identically.
---

# Fab Listing Copy Fragments — NYRA v1

These fragments are written in neutral, compliant language. Every fragment
annotates which compliance-summary DO row it satisfies. Phase 8 DIST-01
(Fab listing ready) consumes these fragments verbatim. Any DIST-01 deviation
MUST cite the specific compliance-summary row being violated and either
reword to stay compliant or open a permission-requests-queue item per D-08.

**Final name:** NYRA (LOCKED per Plan 00-03). See frontmatter note on
rollback procedure if the name changes.

---

## 1. Short Description (< 200 chars)

> Target: 80–160 characters. One sentence or two short sentences.
> Fab field label: "Short Description" on the listing submission form.

```
NYRA is a free in-editor AI agent for Unreal Engine 5. It works with your
Claude subscription and drives external tools to turn reference images or
videos into finished UE scenes — no new AI bill required.
```

> compliance: Anthropic DO ("works with your Claude subscription");
> Anthropic DON'T (no "Claude-powered" or claimed partnership);
> Epic DO ("for Unreal Engine 5" descriptor); Fab DON'T (no logos,
> no "official"); OpenAI DON'T (zero OpenAI references in v1 copy).

---

## 2. Long Description (3–8 paragraphs)

> Target: 3–8 paragraphs. Fab's description field accepts markdown.
> Each integration block kept under 3 sentences.
> Reference the EULA at the bottom.

```
NYRA is a free in-editor AI agent for Unreal Engine 5. It connects to your
existing Claude subscription through your locally-installed Claude Code CLI —
there is no new AI bill to pay and no NYRA-owned backend in the loop.

Give NYRA a reference image or video clip and it breaks the task into
concrete steps: planning in Claude, driving Meshy via REST API to generate
3D geometry from your reference images, integrating with your locally-installed
ComfyUI to produce texture and VFX assets, and finally assembling everything
in your UE editor. The chat panel runs inside the editor alongside your
viewport, with full markdown and code block rendering.

For tasks without a reference image — code review, Blueprint debugging, asset
search, or answering UE questions — NYRA reasons in plain language using
your Claude subscription. When offline or intentionally disconnected, NYRA
switches to a bundled Gemma 3 4B inference engine running entirely on your
local machine, no external calls at all.

NYRA drives your third-party tools with your own accounts and subscriptions.
It invokes Meshy using API credentials you supply, runs ComfyUI workflows
on your local installation, and uses Claude computer-use (beta) to operate
Substance 3D Sampler and UE editor modal dialogs when no API exists.
All data stays on your machine; NYRA does not operate or phone home to
any NYRA-owned server.

No new AI bill. No hosted backend. No NYRA telemetry. Your Claude
subscription, your Meshy account, your ComfyUI installation — all stay
under your control. See the end-user licence agreement included with the
plugin for full terms.
```

> compliance: Anthropic DO ("works with your Claude subscription",
> "invokes Claude", "uses Claude computer-use (beta)"); Anthropic DON'T
> (no "Claude-powered", no claimed partnership); Epic DO ("for Unreal
> Engine 5", factual engine version listing); Fab DO (factual AI disclosure,
> no logos, neutral verbs); OpenAI DON'T (zero OpenAI references in v1 copy).

---

## 3. Feature Bullets (5–12)

> One line per bullet. Neutral, factual. No logos, no "powered by".
> Fab field label: "Features" or "Key Features" on the submission form.

- UE 5.4, 5.5, 5.6, and 5.7 support out of the box
  > compliance: Epic DO ("Unreal Engine 5.x" descriptor); Fab DO (factual)

- Chat panel inside the editor with markdown, code blocks, and file attachments
  > compliance: Fab DO (factual capability description)

- Works with your Claude subscription via the Claude Code CLI on your machine
  > compliance: Anthropic DO ("works with your Claude subscription");
  > Anthropic DON'T (neutral phrasing, no wordmark, no "Claude-powered")

- Offline fallback via bundled Gemma 3 4B model (local inference, no external calls)
  > compliance: Anthropic DO (neutral "Gemma" as product name); Fab DO (factual)

- Reference image → full UE-native scene (actor placement, materials, lighting)
  > compliance: Fab DO (factual capability, no misleading superlatives)

- Reference video → matched UE shot with Sequencer camera and lighting authored
  > compliance: Fab DO (factual capability, no misleading superlatives)

- Drives Meshy via your Meshy account to generate 3D geometry from reference images
  > compliance: Anthropic DON'T (no wordmark in bullet); Fab DO (factual
  > third-party reference); OpenAI DON'T (zero OpenAI references)

- Integrates with your locally-installed ComfyUI for texture and VFX workflows
  > compliance: Fab DO (factual); OpenAI DON'T (zero OpenAI references)

- Uses Claude computer-use (beta) to operate Substance 3D Sampler and UE editor dialogs
  > compliance: Anthropic DO ("Claude computer-use (beta)" factual, neutral);
  > Fab DO (discloses third-party tool); OpenAI DON'T (zero OpenAI references)

- No NYRA-owned backend; no telemetry; all data stays local
  > compliance: Fab DO (factual claim; no hidden backend per Fab content guidelines)

- Ships as a standalone plugin — no installer dependencies beyond UE 5.4+
  > compliance: Fab DO (factual)

---

## 4. AI-Disclosure Copy

> Mandatory Fab field. Required at submission time per Fab AI Disclosure Policy
> (fab-ai-disclosure-policy-SNAPSHOT.md, Plan 00-02). Must enumerate all
> AI providers invoked, whether they run locally or externally, and whether
> they require user-supplied accounts or API keys.
> Fab field label: "AI Disclosure" or equivalent on the submission form.

```
NYRA uses AI in the following ways:

- Invokes the user's own Anthropic Claude subscription via the user's
  locally-installed Claude Code CLI. The user runs "claude setup-token"
  once to authenticate with their own account. NYRA drives Claude as a
  subprocess; no NYRA-owned credentials are involved.

- Optionally uses a bundled Google Gemma 3 4B GGUF model (approximately
  3.16 GB) for local offline inference. No external calls are made when
  this mode is active. The Gemma model is fetched on first use and cached
  locally.

- Drives the following third-party services using credentials the user
  provides: Meshy (image-to-3D geometry via REST API, user's Meshy account).

- Uses Claude computer-use (beta) to operate Adobe Substance 3D Sampler on
  the user's machine. This capability uses Anthropic's computer-use API
  with the user's own API key, if the user has opted in to that mode.

- ComfyUI is invoked as a local subprocess on the user's machine. NYRA
  does not host or operate any ComfyUI instance; the user must have
  ComfyUI installed.

No NYRA-owned or NYRA-operated AI service, backend, or API is involved at
any point in NYRA's operation. All AI inference either uses the user's own
third-party subscription or runs locally on the user's hardware.

Generated content ownership: all assets created by AI services invoked through
NYRA are owned by the user per each service's applicable terms. See the
end-user licence agreement for full details.
```

> compliance: Anthropic DO ("Claude Code CLI", "Anthropic Claude subscription",
> "Claude computer-use (beta)" — factual enumeration, no wordmark use,
> no claimed partnership); Google DO ("Gemma 3 4B" as factual product name);
> Fab DO (mandatory AI disclosure satisfied; no logos; neutral verbs);
> Fab AI Disclosure Policy (Plan 00-02) requirement satisfied;
> EULA consistency note: matches EULA Third-Party Components enumeration.

---

## 5. Third-Party Tool Disclosure

> Fab's submission form may separate "Third-Party APIs / Services" from the
> AI-disclosure field. If so, use this fragment for that field. If not,
> the AI-Disclosure Copy above covers this requirement — this section is
> provided as a standalone fallback.
> Fab field label: "Third-Party Services" or equivalent.

```
NYRA integrates with the following third-party tools. All require the user
to hold their own account or installation:

- Meshy (mesh.ai): image-to-3D geometry via REST API. User provides
  their own Meshy API key via NYRA settings.

- ComfyUI: runs locally as a subprocess on the user's machine. The user
  must have ComfyUI installed. NYRA does not host or operate ComfyUI.

- Adobe Substance 3D Sampler: operated via Claude computer-use (beta)
  on the user's machine. Requires the user to have Substance 3D Sampler
  installed and (optionally) an Anthropic API key if the computer-use
  path is enabled.

- Claude Code CLI: the user must have Claude Code installed and run
  "claude setup-token" once to authenticate with their own Anthropic
  Claude subscription. NYRA does not hold or transmit the user's
  authentication token.

NYRA does not operate any server, backend, or API on the user's behalf.
All third-party calls are either localhost-only or use credentials the
user provides directly.
```

> compliance: Fab DO (third-party disclosure; no logos; neutral verbs);
> Anthropic DO (factual "Claude Code CLI", "Anthropic Claude subscription");
> OpenAI DON'T (zero OpenAI references in v1 copy).

---

## 6. Category + Tags

> Fab category selection and tag input on the submission form.
> Executor note: confirm exact category names against the live Fab form
> before Phase 8 submission — Fab may rename categories between now
> and launch.

**Category (primary):**
- Code Plugin

**Category (secondary, if allowed by Fab):**
- AI Tools
- Workflow Automation

**Tags:**
```
AI, Claude, Gemma, Meshy, ComfyUI, Blueprints, Agents,
Automation, Scene Generation, Video to Scene, Image to Scene,
Unreal Engine, UE5, Free, Local Inference
```

> compliance: Anthropic DO ("Claude", "Gemma" as product names only, no
> wordmark); Epic DO ("Unreal Engine", "UE5" as factual product references);
> Fab DO (correct category name; tags relevant to actual capabilities;
> no logos); OpenAI DON'T (zero OpenAI references in v1 tags).

---

## 7. Marketing Asset Copy (trailer title, screenshot captions)

> Used in: video trailer title field, screenshot alt-text / caption fields.
> Fab field label: "Trailer Title", "Screenshot Caption", or equivalent.

### Trailer title

```
NYRA — turn a reference into a UE scene
```

> compliance: Anthropic DON'T (neutral, no "Claude-powered"); Epic DO
> ("UE" as factual abbreviation); Fab DON'T (no logos, no "official").

### Screenshot captions (examples — write one per screenshot)

**Screenshot 1 — Chat panel with reference image attached:**
```
Attach a reference image, video clip, or text description — NYRA analyses it
in your Claude subscription and plans the scene before touching the editor.
```
> compliance: Anthropic DO ("Claude subscription" neutral); Fab DO (factual).

**Screenshot 2 — 3D mesh imported into UE:**
```
Meshy generates geometry from your reference image; NYRA imports the result
directly into your UE project as a placed actor with material slots.
```
> compliance: Anthropic DON'T (no wordmark in copy); Fab DO (factual
> integration description).

**Screenshot 3 — Material authored on mesh in UE:**
```
NYRA drives Substance 3D Sampler via Claude computer-use (beta) to author
PBR materials on your mesh, then assigns them in the UE material graph.
```
> compliance: Anthropic DO ("Claude computer-use (beta)" factual);
> Fab DO (discloses third-party tool); Adobe DO (Substance 3D Sampler
> as factual product name).

**Screenshot 4 — ComfyUI workflow result imported into UE:**
```
NYRA kicks off a ComfyUI workflow on your local installation, waits for
the render, and imports the output as a texture or VFX asset in UE.
```
> compliance: Fab DO (factual local subprocess; no logos).

**Screenshot 5 — Offline mode with Gemma:**
```
Privacy mode: switch to the bundled Gemma 3 4B model for fully local
reasoning — no external network calls, no external accounts.
```
> compliance: Anthropic DO (Gemma as factual product name); Fab DO
> (no logos; factual privacy claim).

---

## 8. Phrasing That Is EXPLICITLY BANNED in v1 Copy

> This block-list applies to every field of the Fab listing and all
> NYRA marketing copy (devlog, nyra-engine.com, social posts).
> Phase 8 DIST-01 must not enter any of these phrases verbatim.

### BANNED — Anthropic (Anthropic DON'T rows)

| Banned phrase | Why banned | Compliant replacement |
|---|---|---|
| "Claude-powered" | Implies endorsement; wordmark use without permission | "works with your Claude subscription" |
| "Powered by Anthropic" | Implies endorsement; Anthropic brand colour/logo risk | "uses Claude via your Claude Code CLI" |
| "Anthropic-approved" | Claimed endorsement; no such relationship exists | "Anthropic" as factual company name only |
| "Anthropic-recommended" | Claimed endorsement | Remove |
| "Official Anthropic partner" | No partner relationship exists | Remove |
| "Anthropic-endorsed" | Claimed endorsement | Remove |
| "Claude.ai login" or implies NYRA offers claude.ai access | Misrepresents what NYRA does | "Claude Code CLI subprocess" |
| Any Anthropic logo or Claude wordmark in graphics | Requires explicit permission | No logo |
| "NYRA-Claude" or "Claude+NYRA" combined marks | Wordmark modification | NYRA stands alone |

### BANNED — OpenAI (OpenAI DON'T rows)

| Banned phrase | Why banned | Compliant replacement |
|---|---|---|
| "ChatGPT" | No OpenAI integration in v1 | Remove entirely |
| "OpenAI" | No OpenAI integration in v1 | Remove entirely |
| "Codex" | No Codex integration in v1 | Remove entirely |
| "GPT" | No GPT model in v1 | Remove entirely |
| "Powered by ChatGPT" | No OpenAI integration | Remove entirely |
| "OpenAI-powered" | No OpenAI integration | Remove entirely |
| Any OpenAI logo in graphics | No OpenAI integration; logo use without permission | No logo |
| "Works with ChatGPT" | No OpenAI integration in v1 | Remove entirely |

### BANNED — Epic Games / Unreal Engine (Epic DON'T rows)

| Banned phrase | Why banned | Compliant replacement |
|---|---|---|
| Any Epic Games logo or wordmark in listing graphics | Requires written permission | No logo |
| "Official Unreal Engine plugin" | No official relationship; Epic partner required | "for Unreal Engine 5" |
| "Epic-approved" | No such approval exists | Remove |
| "Epic-recommended" | No such relationship | Remove |
| "Unreal Engine logo" in screenshots or banner | Requires Epic permission | No logo |
| "Built with Unreal Engine" as branding element | Requires Epic co-marketing agreement | "for Unreal Engine 5" or "targets UE 5.x" |
| "UE NYRA" or any UE-prefixed product name | Implies official Epic prefix | "NYRA for Unreal Engine 5" |

### BANNED — Fab / Marketplace (Fab DON'T rows)

| Banned phrase | Why banned | Compliant replacement |
|---|---|---|
| Any Fab logo in listing graphics | Requires Epic/Fab permission | No logo |
| "Official" (any brand) | No official status in v1 | Remove entirely |
| "Partner" (any brand) | No partner status in v1 | Remove entirely |
| "Endorsed by" or "Approved by" (any brand) | No endorsement exists | Remove entirely |
| Any third-party logo in listing graphics (Anthropic, OpenAI, Google, Adobe, Meshy, ComfyUI) | Requires respective brand permission | No logos |

### ALLOWED — quick reference

| Allowed phrase | Why allowed | Example source |
|---|---|---|
| "works with your Claude subscription" | Neutral verb, user-centric, no wordmark | Anthropic DO |
| "integrates with your locally-installed ComfyUI" | Neutral verb, factual | Fab DO |
| "drives Meshy via your Meshy account" | Neutral verb, factual | Fab DO |
| "uses Claude computer-use (beta)" | Factual, no wordmark | Anthropic DO |
| "for Unreal Engine 5" | Factual descriptor | Epic DO |
| "Anthropic" (as factual company name) | Correct capitalisation | Anthropic DO |
| "Claude Code CLI" (as product name) | Correct capitalisation | Anthropic DO |
| "Gemma 3 4B" (as model name) | Factual, Google product name | Anthropic DO (neutral use) |
| "no NYRA-owned backend; no telemetry" | Factual claim | Fab DO |

---

## 9. Handoff to Phase 8 DIST-01

Phase 8 DIST-01 (Fab listing ready) consumes this document verbatim as
the v1 submission copy. No further brand research is required at Phase 8
for the copy itself.

**DIST-01 executor instructions:**

1. Copy each fragment into the corresponding Fab submission form field.
2. Count characters on the Short Description — must be under 200 chars.
3. Verify the Long Description against the live Fab form (paragraph
   count limits may change; trim to fit).
4. Confirm exact Fab category names against the live submission form before
   selecting categories and tags.
5. Do NOT add any of the BANNED phrases from Section 8 to any field.
6. Do NOT include any third-party logos in screenshots, the banner, or
   the trailer.
7. AI-Disclosure Copy (Section 4) is mandatory at submission time —
   paste it verbatim into the required Fab AI Disclosure field.
8. If the submission form adds a new field not covered here, apply the
   cross-brand rules from `00-05-brand-compliance-summary.md` to write
   compliant copy for that field before submission.

**If DIST-01 needs to deviate from any fragment:** cite the specific
compliance-summary row being violated and either (a) reword to stay
compliant or (b) open a permission-requests-queue item per D-08 before
submitting. Do not silently deviate.

**Rollback note:** if Plan 00-03's rollback to AELRA is triggered,
find-replace NYRA -> AELRA in all 9 sections before DIST-01 consumption.
The compliance rules are name-agnostic and require no further change.

---
*Authored for NYRA Phase 0 SC#5 — 2026-04-29.*
*final_name: NYRA (LOCKED per Plan 00-03).*
*compliance_reference: brand/00-05-brand-compliance-summary.md*
*phase_8_handoff: DIST-01 consumes verbatim.*
