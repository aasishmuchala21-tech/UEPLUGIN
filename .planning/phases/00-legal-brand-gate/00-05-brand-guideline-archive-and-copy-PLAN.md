---
phase: 00-legal-brand-gate
plan: 05
slug: brand-guideline-archive-and-copy
type: execute
tdd: false
wave: 1
depends_on: []
autonomous: true
requirements: [PLUG-05]
task_count: 2
files_modified:
  - .planning/phases/00-legal-brand-gate/external-snapshots/anthropic-brand-guidelines-SNAPSHOT.md
  - .planning/phases/00-legal-brand-gate/external-snapshots/openai-brand-guidelines-SNAPSHOT.md
  - .planning/phases/00-legal-brand-gate/external-snapshots/epic-games-brand-guidelines-SNAPSHOT.md
  - .planning/phases/00-legal-brand-gate/external-snapshots/fab-seller-branding-policy-SNAPSHOT.md
  - .planning/phases/00-legal-brand-gate/brand/00-05-brand-compliance-summary.md
  - .planning/phases/00-legal-brand-gate/brand/00-05-fab-listing-copy-fragments.md
objective: >
  Close ROADMAP Phase 0 SC#5 — archive date-stamped snapshots of Anthropic,
  OpenAI, Epic Games, and Fab seller brand/trademark-use guidelines under
  external-snapshots/, synthesise a per-brand compliance summary covering
  what NYRA can/cannot say about each brand without explicit partner-program
  permission, then author neutral-phrasing Fab listing copy fragments for
  v1 submission that stay within every listed guideline (per D-08 archive
  first, ask permission second; no third-party logos on the Fab listing
  unless an explicit partner-program permission is on file). OpenAI is
  included pre-emptively even though Codex is deferred to v1.1 — so any
  future ChatGPT-branded copy lands in a re-verified context without
  re-archiving.
must_haves:
  truths:
    - "Date-stamped markdown snapshots of Anthropic + OpenAI + Epic Games + Fab seller branding-use guidelines exist under external-snapshots/, each tagged with snapshot_date in frontmatter"
    - "A brand-compliance summary doc exists under brand/ enumerating, per brand, the concrete DO-and-DON'T list for NYRA's Fab listing + devlog + website copy: allowed references (what NYRA can say), prohibited references (what triggers takedown), logo-use policy (generally forbidden without partner-program permission), trademark-name capitalisation and phrasing rules"
    - "A Fab listing copy fragments doc exists under brand/ with pre-approved (by founder, vs. the compliance summary) copy fragments for every field of the Fab listing: short description, long description, feature bullets, AI-disclosure copy, third-party-tool disclosure copy, and the canonical no-third-party-logos phrasing per D-08"
    - "All Fab listing copy fragments use neutral phrasing — 'works with your Claude subscription', 'integrates with Meshy via your account', 'drives your locally-installed ComfyUI', 'uses Claude computer-use (beta) for Substance 3D Sampler' — with no third-party logos embedded, no claimed partnership, no 'official' implying endorsement"
    - "A permission-requests queue doc section exists at the bottom of the compliance summary listing any copy items that would be stronger with explicit partner-program permission (e.g. Epic verified plugin badge, Claude-powered with Anthropic wordmark). Each queue item records its current status: NOT-REQUESTED | REQUESTED | GRANTED | DENIED — for v1 all items default to NOT-REQUESTED per D-08 safer-default"
    - "Per CONTEXT.md Out-of-scope: OpenAI / Codex clearance is deferred to v1.1, but OpenAI brand guidelines ARE archived here pre-emptively so when Codex lands in v1.1 the researcher does not need to re-archive"
    - "The Fab listing copy references the final chosen name from Plan 00-03 (NYRA or selected backup) — if Plan 00-03 chose a backup, this plan uses the backup name throughout; executor checks Plan 00-03 verdict-and-reservations.md at execution time and propagates accordingly"
  artifacts:
    - path: .planning/phases/00-legal-brand-gate/external-snapshots/anthropic-brand-guidelines-SNAPSHOT.md
      provides: "Anthropic brand-use guidelines snapshot (anthropic.com/trademark, branding, or equivalent 2026 page)"
      contains: "Snapshot-date:"
    - path: .planning/phases/00-legal-brand-gate/external-snapshots/openai-brand-guidelines-SNAPSHOT.md
      provides: "OpenAI brand/trademark-use guidelines snapshot (openai.com/brand or equivalent 2026 page)"
      contains: "Snapshot-date:"
    - path: .planning/phases/00-legal-brand-gate/external-snapshots/epic-games-brand-guidelines-SNAPSHOT.md
      provides: "Epic Games + Unreal Engine brand-use guidelines snapshot (epicgames.com/site/en-US/tos or /branding or unrealengine.com equivalent)"
      contains: "Snapshot-date:"
    - path: .planning/phases/00-legal-brand-gate/external-snapshots/fab-seller-branding-policy-SNAPSHOT.md
      provides: "Fab marketplace seller / branding / naming policy snapshot — the Fab-specific rules on listing copy, product naming, prohibited phrasing"
      contains: "Snapshot-date:"
    - path: .planning/phases/00-legal-brand-gate/brand/00-05-brand-compliance-summary.md
      provides: "Per-brand DO/DON'T compliance matrix + permission-requests queue"
      contains: "permission-requests queue"
    - path: .planning/phases/00-legal-brand-gate/brand/00-05-fab-listing-copy-fragments.md
      provides: "Neutral-phrasing copy fragments for every Fab listing field, vetted against the compliance summary"
      contains: "works with your"
  key_links:
    - from: brand/00-05-fab-listing-copy-fragments.md
      to: brand/00-05-brand-compliance-summary.md
      via: "Every copy fragment annotates which compliance-summary DO row it complies with (traceability)"
      pattern: "compliance-summary"
    - from: brand/00-05-brand-compliance-summary.md
      to: external-snapshots/anthropic-brand-guidelines-SNAPSHOT.md
      via: "Anthropic DO/DON'T section cites specific snapshotted clauses as authority"
      pattern: "anthropic-brand"
    - from: brand/00-05-fab-listing-copy-fragments.md
      to: trademark/00-03-verdict-and-reservations.md (Plan 00-03)
      via: "Fab listing copy uses the final name from 00-03 — executor reads the verdict doc at execution and substitutes if backup was selected"
      pattern: "final_name"
    - from: brand/00-05-fab-listing-copy-fragments.md
      to: legal/00-04-nyra-eula-draft.md (Plan 00-04)
      via: "AI-disclosure copy matches EULA Third-Party Components enumeration so listing and terms are consistent"
      pattern: "Third-Party Components"
---

<objective>
Phase 0 SC#5 protects the Fab listing's legal-safety. Per PITFALLS §7.4-
adjacent risk: the public devlog + Fab listing go live before Phase 8; any
brand-guideline violation (unauthorised logo, claimed endorsement, wrong
trademark phrasing) could produce a Fab takedown, a cease-and-desist from
Anthropic/OpenAI/Epic, OR both. Phase 8 (Fab Launch Prep) inherits the
pre-approved copy from this plan — Phase 8 does not re-do the brand work,
it consumes it.

Per D-08 archive first, ask permission second: Phase 0 archives (snapshots)
and writes SAFE copy; any stronger copy that wants to use a partner-
program-permitted wordmark/logo goes in a permission-requests queue, NOT
in the Phase 0 output. For v1, all queue items default to NOT-REQUESTED —
the founder can open permission threads post-v1 if usage signal justifies.

Per D-09 Claude's Discretion: the exact phrasing ("works with your Claude
subscription" vs "Claude-powered" vs "AI-powered") is the planner's /
executor's call within the bounds of the compliance summary — the rule
is neutral-language + no logos.

Per CONTEXT.md Out of Scope: OpenAI / Codex clearance is deferred to v1.1.
Including OpenAI guidelines in Phase 0 is a low-cost pre-emptive archive —
when Codex lands in v1.1 the researcher does not need to re-archive.

Purpose: Close SC#5 — Fab listing copy is pre-vetted against every
relevant brand's guidelines so v1 submission clears review cleanly.
Output: 4 external-snapshot files + 1 compliance-summary doc + 1 copy-
fragments doc.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/00-legal-brand-gate/00-CONTEXT.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Snapshot 4 brand-guideline surfaces + author compliance summary</name>
  <files>
    .planning/phases/00-legal-brand-gate/external-snapshots/anthropic-brand-guidelines-SNAPSHOT.md,
    .planning/phases/00-legal-brand-gate/external-snapshots/openai-brand-guidelines-SNAPSHOT.md,
    .planning/phases/00-legal-brand-gate/external-snapshots/epic-games-brand-guidelines-SNAPSHOT.md,
    .planning/phases/00-legal-brand-gate/external-snapshots/fab-seller-branding-policy-SNAPSHOT.md,
    .planning/phases/00-legal-brand-gate/brand/00-05-brand-compliance-summary.md
  </files>
  <action>
    Step A — Snapshot 4 brand-guideline pages. URL paths drift; executor
    searches each brand's site for the current "Brand Guidelines" /
    "Trademark Use Policy" / "Seller Branding Policy" doc and captures
    the live 2026 version.

    1. Anthropic — search anthropic.com for "brand guidelines" or
       "trademark use policy". Typical URL candidates:
       anthropic.com/trademark, anthropic.com/brand, anthropic.com/legal.
       If no public page exists, snapshot the relevant wordmark-use
       guidance embedded in anthropic.com's legal ToS or Acceptable Use
       Policy, and explicitly note in the snapshot that "no dedicated
       public brand-guidelines page was found on <snapshot_date>;
       conservative wordmark-use inference applies."

    2. OpenAI — search openai.com for "brand guidelines". Typical URLs:
       openai.com/brand, openai.com/trademark, openai.com/policies. Same
       fallback pattern as Anthropic if no dedicated page exists.

    3. Epic Games — search for "Epic Games trademark guidelines" or
       "Unreal Engine brand guidelines". Typical URLs:
       epicgames.com/site/en-US/tos, unrealengine.com/en-US/branding,
       unrealengine.com/en-US/eula. The Unreal-Engine-specific branding
       guide is more actionable for a UE plugin than the generic Epic
       Games one — snapshot both if separate pages exist; consolidate
       into one file if they are on one page.

    4. Fab seller branding — search fab.com/help for "seller naming
       conventions", "product naming", or "prohibited phrasing". If this
       is part of the Content Guidelines already snapshotted in Plan
       00-02, copy the relevant subsections into this dedicated file
       (so Phase 0 brand-compliance work does not cross-reference Plan
       00-02's policy surface and cause drift).

    Each snapshot file uses the standard external-snapshot frontmatter
    (source_url, snapshot_date, snapshot_method) + full body.

    Step B — Synthesise brand/00-05-brand-compliance-summary.md.
    Frontmatter:
    ```
    brands_covered: [Anthropic, OpenAI, Epic Games/Unreal Engine, Fab]
    summary_date: <ISO-8601>
    default_stance: neutral-phrasing + no-logos-without-permission
    permission_requests_queue_status: ALL-NOT-REQUESTED (D-08 safer-default for v1)
    ```

    Body — for EACH of the 4 brands, one section with this structure:

    ```
    ## Anthropic

    **Authoritative source:** external-snapshots/anthropic-brand-guidelines-SNAPSHOT.md (snapshotted <date>)

    ### DO (safe references NYRA may use without permission)
    - "works with your Claude subscription" (neutral + user-centric)
    - "uses Claude (via your Claude Code CLI)" (factual + user-CLI-scoped)
    - "Claude" as a product name, correctly capitalised
    - "Anthropic" as a company name, correctly capitalised
    - Link to anthropic.com in reference contexts

    ### DON'T (triggers takedown / C&D without explicit partner-program permission)
    - Use Anthropic or Claude logos or wordmarks in any NYRA marketing asset
    - Claim partnership ("official Anthropic partner", "Claude-powered", "Anthropic-approved")
    - Use Anthropic's brand colors or visual identity
    - Imply endorsement ("as featured by Anthropic", "Anthropic-recommended plugin")
    - Modify or co-opt the Claude wordmark (no "NYRA-Claude", "Claude+NYRA" logos)
    - Use Claude in a way that could confuse users about who operates the service

    ### Capitalisation and phrasing rules
    - "Claude" (capital C, the rest lowercase)
    - "Anthropic" (capital A)
    - "Claude Code" (two capitalised words)
    - NEVER "claude.ai" in copy implying NYRA offers a claude.ai login

    ### Permission-requests queue items for Anthropic (all NOT-REQUESTED for v1)
    - [ ] Permission to use "Claude-powered" phrasing with Anthropic
          wordmark — deferred post-v1
    - [ ] Permission to include a "Compatible with Claude" badge on the
          Fab listing — deferred post-v1
    ```

    Repeat this 5-section structure (Authoritative Source / DO / DON'T /
    Capitalisation / Permission-Queue) for OpenAI, Epic Games/Unreal
    Engine, and Fab seller-branding. For OpenAI, include a note at the
    top: "OpenAI listed pre-emptively; Codex integration deferred to
    v1.1. For v1 do NOT reference OpenAI/ChatGPT/Codex in Fab listing
    copy."

    Step C — At the bottom of the compliance summary, a final
    consolidated section:

    ```
    ## Permission-Requests Queue (Consolidated)
    | Brand | Item | Status | Priority | Notes |
    | <brand> | <item> | NOT-REQUESTED | LOW | <rationale: defer post-v1 per D-08> |
    ...

    ## Cross-Brand Rules (apply everywhere)
    - NO third-party logos on the Fab listing, the devlog, or NYRA's
      website UNLESS the corresponding partner-program permission is
      on file (D-08).
    - When naming an integration, prefer the neutral verb "works with"
      or "integrates with" or "drives" over the claimed "powered by"
      or "official".
    - The AI-disclosure copy for the Fab listing (required by Fab AI
      policy per Plan 00-02) uses neutral phrasing and enumerates the
      external tools factually, not promotionally.
    ```

    Commit with
    `docs(00-05): snapshot brand guidelines + author compliance summary`.
  </action>
  <verify>
    <automated>test -f .planning/phases/00-legal-brand-gate/external-snapshots/anthropic-brand-guidelines-SNAPSHOT.md && test -f .planning/phases/00-legal-brand-gate/external-snapshots/openai-brand-guidelines-SNAPSHOT.md && test -f .planning/phases/00-legal-brand-gate/external-snapshots/epic-games-brand-guidelines-SNAPSHOT.md && test -f .planning/phases/00-legal-brand-gate/external-snapshots/fab-seller-branding-policy-SNAPSHOT.md && test -f .planning/phases/00-legal-brand-gate/brand/00-05-brand-compliance-summary.md && grep -qE "permission-requests queue|Permission-Requests Queue|permission_requests_queue" .planning/phases/00-legal-brand-gate/brand/00-05-brand-compliance-summary.md && grep -q "Anthropic" .planning/phases/00-legal-brand-gate/brand/00-05-brand-compliance-summary.md && grep -q "OpenAI" .planning/phases/00-legal-brand-gate/brand/00-05-brand-compliance-summary.md && grep -qi "epic" .planning/phases/00-legal-brand-gate/brand/00-05-brand-compliance-summary.md && grep -qi "fab" .planning/phases/00-legal-brand-gate/brand/00-05-brand-compliance-summary.md</automated>
  </verify>
  <done>4 brand snapshots exist with snapshot_date; compliance summary covers all 4 brands with DO/DON'T/capitalisation/permission-queue for each + consolidated permission queue + cross-brand rules.</done>
</task>

<task type="auto">
  <name>Task 2: Author neutral-phrasing Fab listing copy fragments (D-08 compliance)</name>
  <files>
    .planning/phases/00-legal-brand-gate/brand/00-05-fab-listing-copy-fragments.md
  </files>
  <action>
    Step A — Before writing copy, read the final name from Plan 00-03's
    verdict-and-reservations doc:
    ```
    FINAL_NAME=$(grep -E "^final_name:" .planning/phases/00-legal-brand-gate/trademark/00-03-verdict-and-reservations.md | head -1 | awk -F: '{print $2}' | tr -d ' ')
    ```
    If the doc does not exist yet (Plan 00-03 running concurrently),
    record in frontmatter `final_name_status: PROVISIONAL-NYRA` and use
    NYRA throughout; add a note in the doc header "if Plan 00-03 chose a
    backup name, find-replace NYRA -> <backup-name> before Fab submission."
    If Plan 00-03 has closed: use the actual final name throughout.

    Step B — Author brand/00-05-fab-listing-copy-fragments.md covering
    every Fab listing field. Frontmatter:
    ```
    final_name: <NYRA or backup, from Plan 00-03>
    final_name_status: LOCKED | PROVISIONAL-NYRA
    compliance_reference: brand/00-05-brand-compliance-summary.md
    phase_8_handoff: DIST-01 consumes these fragments verbatim
    author: <founder name>
    date: <ISO-8601>
    ```

    Body — copy fragments for each Fab listing field. Each fragment is
    followed by a one-line annotation `> compliance: <relevant-DO-row-
    from-summary>` so traceability is explicit.

    1. `## Short Description (< 200 chars)`
       Example fragment (executor finalises wording):
       ```
       <NAME> is a free in-editor AI agent for Unreal Engine 5. It works
       with your Claude subscription and drives external tools (Meshy,
       ComfyUI) to turn references into finished UE scenes.
       ```
       > compliance: Anthropic DO ("works with your Claude subscription");
       > Fab no-logos; no partnership claim.

    2. `## Long Description (3–8 paragraphs)`
       Write the full description. Enumerate capabilities factually.
       Call out economics: "no new AI bill — uses your existing Claude
       subscription on your own machine." Call out integrations with
       neutral verbs ("drives Meshy via REST API with your Meshy
       account", "integrates with your locally-installed ComfyUI",
       "uses Claude computer-use (beta) for Substance 3D Sampler and UE
       modal dialogs"). Keep each integration block under 3 sentences.
       Reference the EULA + privacy clause at the bottom.

    3. `## Feature Bullets (5–12)`
       Each a single line, neutral, factual. Examples (executor
       finalises):
       - "UE 5.4, 5.5, 5.6, and 5.7 support out of the box"
       - "Chat panel with markdown, code blocks, and file attachments"
       - "Works with your Claude subscription via the Claude Code CLI"
       - "Offline fallback via bundled Gemma 3 4B model (local inference)"
       - "Image → full UE-native scene (DEMO-01)"
       - "Reference video → matched UE shot (DEMO-02, launch demo)"
       - "Drives Meshy, ComfyUI, and (via Claude computer-use) Substance
         3D Sampler"
       - "No hosted backend; no NYRA-owned telemetry; all data stays
         local"
       Each bullet gets a compliance annotation.

    4. `## AI-Disclosure Copy (for the Fab AI-content field)`
       Mandatory Fab field per Plan 00-02's AI policy snapshot. Example:
       ```
       <NAME> uses AI in the following ways:
       - Invokes the user's own Anthropic Claude subscription via the
         user's locally-installed Claude Code CLI for reasoning and
         planning.
       - Optionally uses a bundled Google Gemma 3 4B model for local
         offline inference.
       - Orchestrates external AI services on the user's behalf using
         the user's own accounts/keys: Meshy (image → 3D), ComfyUI
         (image workflows), and Adobe Substance 3D Sampler (PBR
         material authoring via Claude computer-use).
       - All AI-generated content is owned by the user per each
         service's terms. See the end-user licence agreement included
         with the plugin for details.
       ```
       > compliance: enumerates per-service honestly; matches EULA
       > Third-Party Components + Generated Content sections.

    5. `## Third-Party Tool Disclosure (if Fab separates this from AI)`
       If Fab's listing form distinguishes "uses third-party
       APIs/services" from the AI-disclosure field, provide a separate
       fragment focused on: user-supplied API keys, user-installed
       dependencies, no NYRA-owned backend. Otherwise fold into the
       AI-Disclosure copy above.

    6. `## Category + Tags`
       Recommended Fab categories (executor picks from the live Fab
       category list — this is a placeholder): "Code Plugin", "AI Tools",
       "Workflow Automation". Tags: "AI", "Claude", "Gemma", "Meshy",
       "ComfyUI", "Blueprints", "Agents", "Automation", "Scene", "Video".
       > compliance: "Claude", "Gemma" used as product names only; no
       > logos; no "Claude-powered".

    7. `## Marketing Asset Copy (trailer title, screenshot captions)`
       - Trailer title: "<NAME> — turn a reference into a UE scene"
         (neutral, does not claim partnership)
       - Screenshot captions (3–5 examples): executor writes neutral
         factual captions. "Reference video → matched UE shot with
         Sequencer camera authored automatically." "Image attachment →
         scene with lighting, materials, and 5–20 placed actors."
         Each caption compliance-annotated.

    8. `## Phrasing That Is EXPLICITLY BANNED in v1 Copy`
       An allow-list / block-list:
       - BANNED: "Claude-powered", "Powered by Anthropic", "AI-powered"
         (Anthropic D-08 without permission)
       - BANNED: any claim of partnership / endorsement / official
         status with any of the 4 brands
       - BANNED: third-party logos (Anthropic, OpenAI, Epic, Google,
         Meshy, ComfyUI, Adobe) on listing graphics or trailer
       - BANNED: naming the plugin in a way that confuses users about
         NYRA vs. the underlying services (e.g. "<NAME> Claude Edition")
       - BANNED: Codex/ChatGPT/OpenAI references entirely in v1 copy
         (Codex deferred to v1.1)
       - ALLOWED: factual neutral "works with / integrates with / drives
         / uses" phrasing; third-party product NAMES with correct
         capitalisation.

    9. `## Handoff to Phase 8 DIST-01` — one paragraph: Phase 8 DIST-01
       (Fab listing ready) consumes this doc verbatim. If the DIST-01
       executor needs to deviate from any fragment, they MUST cite the
       specific compliance-summary row that would be violated and
       either (a) stay compliant by rewording or (b) open a
       permission-requests-queue item per D-08.

    Commit with
    `docs(00-05): author neutral-phrasing Fab listing copy fragments`.
  </action>
  <verify>
    <automated>test -f .planning/phases/00-legal-brand-gate/brand/00-05-fab-listing-copy-fragments.md && grep -q "works with your" .planning/phases/00-legal-brand-gate/brand/00-05-fab-listing-copy-fragments.md && grep -qi "AI-Disclosure" .planning/phases/00-legal-brand-gate/brand/00-05-fab-listing-copy-fragments.md && grep -qi "BANNED" .planning/phases/00-legal-brand-gate/brand/00-05-fab-listing-copy-fragments.md && grep -q "DIST-01" .planning/phases/00-legal-brand-gate/brand/00-05-fab-listing-copy-fragments.md && grep -q "compliance:" .planning/phases/00-legal-brand-gate/brand/00-05-fab-listing-copy-fragments.md && grep -qE "final_name_status: (LOCKED|PROVISIONAL-NYRA)" .planning/phases/00-legal-brand-gate/brand/00-05-fab-listing-copy-fragments.md</automated>
  </verify>
  <done>Copy-fragments doc exists with all 9 sections; every fragment carries a `compliance:` annotation; final_name_status frontmatter is set to LOCKED or PROVISIONAL-NYRA; Phase 8 DIST-01 handoff is explicit.</done>
</task>

</tasks>

<verification>
Phase 0 SC#5 closure verification:
- [ ] 4 brand-guideline snapshots exist with snapshot_date
- [ ] brand-compliance-summary.md covers all 4 brands with DO/DON'T/capitalisation/permission-queue
- [ ] Consolidated permission-requests queue is present and defaults to ALL-NOT-REQUESTED
- [ ] Cross-brand rules section exists
- [ ] fab-listing-copy-fragments.md has copy for all 9 Fab listing areas
- [ ] Every copy fragment has a compliance annotation
- [ ] Final name matches Plan 00-03's selected name (or PROVISIONAL-NYRA noted)
- [ ] All files committed to git
</verification>

<success_criteria>
Phase 0 SC#5 is CLOSED when:
1. All 4 brand-guideline snapshots exist under external-snapshots/.
2. brand/00-05-brand-compliance-summary.md exists with per-brand DO/DON'T
   matrices + consolidated permission queue + cross-brand rules.
3. brand/00-05-fab-listing-copy-fragments.md exists with neutral-phrasing
   copy for every Fab listing field, each fragment traceable to the
   compliance summary.
4. The closure ledger (Plan 06) flips SC#5 from PENDING to CLOSED.
5. Phase 8 DIST-01 (Fab listing ready) can consume the copy fragments
   without redoing the brand research.
</success_criteria>

<output>
After completion, create `.planning/phases/00-legal-brand-gate/00-05-SUMMARY.md`
following the GSD summary template. Record: snapshot dates, per-brand
DO/DON'T counts, final_name_status, permission-queue item counts, Phase 8
DIST-01 handoff confirmation.
</output>
