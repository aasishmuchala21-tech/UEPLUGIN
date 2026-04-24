---
phase: 00-legal-brand-gate
plan: 04
slug: gemma-license-and-eula-draft
type: execute
tdd: false
wave: 1
depends_on: []
autonomous: true
requirements: [PLUG-05]
task_count: 2
files_modified:
  - .planning/phases/00-legal-brand-gate/external-snapshots/gemma-terms-of-use-SNAPSHOT.md
  - .planning/phases/00-legal-brand-gate/legal/00-04-gemma-license-reverify-note.md
  - .planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-draft.md
  - .planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-gemma-notice-appendix.md
objective: >
  Close ROADMAP Phase 0 SC#4 in two parts. (A) Re-verify the current Gemma
  3 4B IT QAT Q4_0 GGUF license text at ai.google.dev/gemma/terms per D-05:
  confirm the Use Restrictions list hasn't changed since STACK.md captured
  it, date-stamp a snapshot, and author a "Gemma Notice" appendix clause
  for the NYRA EULA. (B) Author NYRA's v1 EULA first draft per D-06
  covering exactly two novel areas: generated-content liability passthrough
  (Meshy / ComfyUI / Substance output belongs to the user, NYRA warranties
  nothing about third-party output) and reference-video ephemeral
  processing (yt-dlp + keyframe + Claude vision; full video deleted from
  /tmp after run, user affirms copyright-clean use). Everything else uses
  a standard UE-plugin EULA template. Counsel review is deferred per D-06.
must_haves:
  truths:
    - "A date-stamped markdown snapshot of the current ai.google.dev/gemma/terms page exists under external-snapshots/ — this is the ground-truth Gemma license text NYRA's redistribution relies on"
    - "A Gemma license re-verification note exists under legal/ comparing the April 2026 STACK.md captured license ('Gemma license allows commercial redistribution with terms-notice') against the fresh snapshot — any delta flagged with impact assessment on NYRA redistribution"
    - "A NYRA v1 EULA first draft exists under legal/ with all standard sections (definitions, license grant, permitted uses, prohibited uses, warranty disclaimer, limitation of liability, indemnification, termination, governing law, venue, general) + the two D-06 novel sections (generated-content liability passthrough + reference-video ephemeral processing)"
    - "A Gemma-notice appendix exists either as a separate file or a clearly-delineated appendix section within the EULA draft — it passes through the Gemma license's prohibited-use restrictions to NYRA users and fulfils the 'terms-notice' redistribution requirement"
    - "The EULA draft explicitly marks itself as founder-authored first draft + counsel review deferred per D-06: frontmatter `status: founder-first-draft`, `counsel_reviewed: false`, `counsel_review_scheduled: post-v1 or at-founder-discretion`"
    - "The EULA draft includes a §'Data We Do Not Collect' sub-section covering the built-in minimal-privacy-policy per CONTEXT.md §deferred — avoids spawning a separate standalone privacy policy doc in Phase 0"
    - "The reference-video ephemeral-processing clause matches ROADMAP Phase 7 SC#4 exactly: yt-dlp + ≤16 keyframes sent to Claude + full video deleted from /tmp after run + user affirms copyright-clean use + no redistribution by NYRA"
    - "The generated-content liability passthrough clause covers Meshy, ComfyUI, Substance Sampler outputs (the three API-first / computer-use external tools in STACK.md) and explicitly states NYRA does NOT warranty these outputs — responsibility + ownership + licensing flow from the external tool's own terms to the user"
  artifacts:
    - path: .planning/phases/00-legal-brand-gate/external-snapshots/gemma-terms-of-use-SNAPSHOT.md
      provides: "Date-stamped snapshot of https://ai.google.dev/gemma/terms"
      contains: "Snapshot-date:"
    - path: .planning/phases/00-legal-brand-gate/legal/00-04-gemma-license-reverify-note.md
      provides: "Re-verification note comparing STACK.md's April 2026 capture vs today's snapshot; delta assessment; impact on NYRA redistribution"
      contains: "re_verify_verdict:"
    - path: .planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-draft.md
      provides: "NYRA v1 EULA first draft — standard UE-plugin template with two D-06 novel sections + built-in minimal privacy clause"
      contains: "status: founder-first-draft"
    - path: .planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-gemma-notice-appendix.md
      provides: "Gemma-notice appendix — passes through Gemma's use-restrictions list to NYRA users; fulfils the terms-notice redistribution requirement"
      contains: "Gemma Terms"
  key_links:
    - from: legal/00-04-nyra-eula-draft.md
      to: legal/00-04-nyra-eula-gemma-notice-appendix.md
      via: "EULA main doc references the Gemma Notice appendix as incorporated-by-reference in §Third-Party Components"
      pattern: "Gemma Notice"
    - from: legal/00-04-gemma-license-reverify-note.md
      to: external-snapshots/gemma-terms-of-use-SNAPSHOT.md
      via: "Re-verify note quotes specific clauses from the dated snapshot as the comparison baseline"
      pattern: "Snapshot-date"
    - from: legal/00-04-nyra-eula-draft.md
      to: ROADMAP Phase 7 SC#4
      via: "Ephemeral-processing clause mirrors the Phase 7 cold-start release gate language so user-facing policy matches implementation behaviour"
      pattern: "ephemeral"
    - from: legal/00-04-nyra-eula-draft.md
      to: STACK.md External Tools
      via: "Generated-content liability passthrough clause enumerates the exact external tools Meshy + ComfyUI + Substance Sampler per STACK.md API-First constraint"
      pattern: "Meshy"
---

<objective>
Phase 0 SC#4 has two mechanically-independent deliverables that share a
domain (product legal terms):

Part A (Gemma license re-verify): Phase 1's NyraInfer process + Phase 2's
Gemma fallback + Phase 3's Gemma offline Q&A + Phase 6/7's Gemma vision
all redistribute Gemma 3 4B IT QAT Q4_0 GGUF with NYRA. STACK.md captured
the license as "allows commercial redistribution with terms-notice" in
April 2026; Phase 0 re-verifies that this is still true as of Phase 2
execution start, because a license change between April 2026 and Phase 2
execution would destroy the Gemma-fallback architectural decision.

Part B (NYRA EULA first draft): NYRA is a free Fab plugin, but a plugin
that drives external tools generating content the user may commercialise
needs a clear liability story. D-06 scopes the novel content to exactly
two areas — everything else is boilerplate from a standard UE-plugin EULA
template. Counsel review is explicitly deferred (D-06, D-09): this is the
founder-authored draft that counsel can review post-v1, NOT a legally-
negotiated contract.

This plan is `autonomous: true` because everything is founder-executor
work — the snapshot is a public URL, the re-verify note is a mechanical
diff, the EULA draft is authoring from a standard template + two custom
sections. No external waits.

Purpose: Close SC#4 — Gemma redistribution is confirmed legal and NYRA's
v1 terms cover the two novel liability surfaces (generated content +
reference video) so counsel has a draft to review at v1.1.
Output: 1 external snapshot + 1 re-verify note + 1 EULA draft + 1 Gemma
Notice appendix.
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
  <name>Task 1: Snapshot Gemma terms + author re-verify note + Gemma Notice appendix</name>
  <files>
    .planning/phases/00-legal-brand-gate/external-snapshots/gemma-terms-of-use-SNAPSHOT.md,
    .planning/phases/00-legal-brand-gate/legal/00-04-gemma-license-reverify-note.md,
    .planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-gemma-notice-appendix.md
  </files>
  <action>
    Step A — Snapshot current Gemma terms. Fetch
    https://ai.google.dev/gemma/terms . Write
    `external-snapshots/gemma-terms-of-use-SNAPSHOT.md` with YAML
    frontmatter `source_url: https://ai.google.dev/gemma/terms`,
    `snapshot_date: <ISO-8601>`, `snapshot_method:`, and the full terms
    body below as normalised markdown. Also snapshot the Gemma Prohibited
    Use Policy page (typically linked from the terms doc — follow the
    "Gemma Prohibited Use Policy" link and capture in the same file as a
    second section or in a separate companion snapshot; executor picks
    based on how Google currently structures the pages).

    Step B — Re-verify note
    `legal/00-04-gemma-license-reverify-note.md`. Frontmatter:
    ```
    baseline_source: .planning/research/STACK.md (April 2026 capture — "Gemma license allows commercial redistribution with terms-notice")
    reverify_snapshot: .planning/phases/00-legal-brand-gate/external-snapshots/gemma-terms-of-use-SNAPSHOT.md
    reverify_date: <ISO-8601>
    re_verify_verdict: UNCHANGED | NON-MATERIAL-CHANGES | MATERIAL-CHANGES
    impact_on_nyra_redistribution: NONE | REVIEW-NEEDED | BLOCKS-REDISTRIBUTION
    ```

    Body sections:
    1. `## Baseline (April 2026)` — one paragraph: STACK.md captured
       "Gemma license allows commercial redistribution with terms-notice",
       Gemma 3 family launched 2025-03-12, model card at
       huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf links back to
       ai.google.dev/gemma/terms.
    2. `## Today's Snapshot Summary` — bullet list of the current license's
       key provisions: commercial-use permitted (yes/no), redistribution
       permitted (yes/no), notice-requirement text (verbatim excerpt from
       the snapshot), prohibited-uses list (link to Prohibited Use Policy
       + one-sentence summary).
    3. `## Delta Analysis` — side-by-side comparison of baseline vs
       current. If no material changes: state so explicitly. If there are
       changes, call each one out and classify as non-material (wording
       cleanups) or material (new use restrictions, changed attribution
       requirements, new territorial carve-outs).
    4. `## Impact on NYRA Redistribution` — one paragraph: given the
       delta (or lack thereof), does NYRA's Phase 1/2/3/6/7 Gemma usage
       still fit within the license? Specifically confirm:
       - Bundling the 3.16 GB GGUF file in the plugin download is
         permitted (or if delta requires download-on-demand instead, note
         that downstream plans must be updated).
       - Running Gemma inference locally on user hardware is permitted.
       - Exposing Gemma via the nyrahost/infer OpenAI-compatible HTTP
         endpoint is permitted (this is an NYRA-internal interface, not
         a third-party API exposure).
       - Users' Gemma-generated outputs belong to the user per Gemma's
         current terms (flows into EULA §Generated Content).
    5. `## Recommended Action` — one paragraph: if verdict is UNCHANGED
       or NON-MATERIAL-CHANGES, proceed. If MATERIAL-CHANGES, open a
       follow-up planning conversation; Phase 2 execution may be
       affected.

    Step C — Gemma Notice appendix
    `legal/00-04-nyra-eula-gemma-notice-appendix.md`. This is the
    redistribution notice NYRA is REQUIRED to include to satisfy the
    Gemma license's terms-notice clause. Frontmatter:
    ```
    incorporated_by: legal/00-04-nyra-eula-draft.md §Third-Party Components
    gemma_terms_source: https://ai.google.dev/gemma/terms (snapshotted <date>)
    ```

    Body (the actual appendix text a user reads):
    ```
    ## Appendix: Gemma 3 Model Notice

    NYRA includes and distributes the Gemma 3 4B Instruction-Tuned model
    (QAT Q4_0 GGUF format) developed by Google. Your use of the Gemma
    model through NYRA is governed by the Gemma Terms of Use (linked
    below) in addition to the NYRA End User License Agreement.

    **Gemma Terms of Use:** https://ai.google.dev/gemma/terms
    **Gemma Prohibited Use Policy:** <link from snapshot>

    By using NYRA's local-fallback / offline mode, you agree to comply
    with Google's Gemma Terms of Use and Prohibited Use Policy. The most
    notable restrictions (not an exhaustive list — full terms govern):
    - <enumerate 4–6 Prohibited Use Policy bullets verbatim from the
      snapshot, e.g. no use for illegal activity, no high-risk automated
      decision-making without human review, etc.>

    **Output Ownership:** Content generated via Gemma inference belongs
    to you per Gemma's current terms. NYRA makes no additional claim on
    your Gemma-generated outputs.

    **Redistribution:** NYRA redistributes Gemma under the Gemma license's
    terms-notice provision. You may not redistribute the Gemma model
    independently of NYRA; if you wish to redistribute, obtain the model
    directly from Google per the Gemma license terms.
    ```

    Commit all three files with
    `docs(00-04): snapshot Gemma terms + re-verify license + author Gemma Notice appendix`.
  </action>
  <verify>
    <automated>test -f .planning/phases/00-legal-brand-gate/external-snapshots/gemma-terms-of-use-SNAPSHOT.md && test -f .planning/phases/00-legal-brand-gate/legal/00-04-gemma-license-reverify-note.md && test -f .planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-gemma-notice-appendix.md && grep -q "re_verify_verdict:" .planning/phases/00-legal-brand-gate/legal/00-04-gemma-license-reverify-note.md && grep -q "Snapshot-date:" .planning/phases/00-legal-brand-gate/external-snapshots/gemma-terms-of-use-SNAPSHOT.md && grep -q "Gemma Terms" .planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-gemma-notice-appendix.md</automated>
  </verify>
  <done>Snapshot + re-verify note + Gemma Notice appendix all exist; re-verify verdict is UNCHANGED, NON-MATERIAL-CHANGES, or MATERIAL-CHANGES (latter requires follow-up per plan notes).</done>
</task>

<task type="auto">
  <name>Task 2: Author NYRA v1 EULA first draft (D-06 scope)</name>
  <files>
    .planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-draft.md
  </files>
  <action>
    Author the NYRA v1 EULA first draft per D-06 scope.
    **Boilerplate = standard UE-plugin EULA template, minimally adapted
    for a FREE plugin (no license key, no commercial resale by user).**
    **Novel content = exactly two sections.** Counsel review is DEFERRED.

    Frontmatter:
    ```
    document_title: "NYRA End User License Agreement"
    version: 0.1.0-draft
    status: founder-first-draft
    counsel_reviewed: false
    counsel_review_scheduled: post-v1 or at-founder-discretion
    effective_date: <leave blank until v1 launch>
    author: <founder name>
    date: <ISO-8601>
    jurisdictions: "United States (venue), Worldwide (distribution)"
    incorporates: [legal/00-04-nyra-eula-gemma-notice-appendix.md]
    ```

    Body sections (order matters — follow a standard EULA structure):

    1. `## 1. Definitions` — "NYRA", "User", "Plugin", "Third-Party
       Components", "Generated Content", "Reference Material", "Local
       Fallback Model", etc. Short paragraph each.

    2. `## 2. License Grant` — a worldwide, royalty-free, non-exclusive,
       non-transferable license to install and use NYRA on the User's
       own machines for any purpose, including commercial UE
       development. NOT a license to redistribute, sublicense, or
       re-sell NYRA itself.

    3. `## 3. Permitted Uses` — short list; anchor on "install, use,
       run alongside your Unreal Engine projects (including commercial
       ones)".

    4. `## 4. Prohibited Uses` — redistribute NYRA independently of
       Fab/official channels; remove NYRA attribution; use NYRA to
       violate third-party ToS (explicit: Anthropic, Google/Gemma,
       Meshy, ComfyUI, Epic, Adobe); use NYRA for generation prohibited
       by any Third-Party Component's terms.

    5. `## 5. Third-Party Components` — NYRA orchestrates several
       third-party services and bundles one third-party model:
       - Claude Code CLI (Anthropic) — user-provided; user's own
         Anthropic terms apply; NYRA never stores Anthropic credentials.
       - Meshy (MeshyAI) — user-provided API key; Meshy's terms apply.
       - ComfyUI (open source) — user-installed; upstream license
         applies.
       - Substance 3D Sampler (Adobe) — user-provided license; Adobe's
         terms apply; NYRA drives via computer-use with user consent.
       - Gemma 3 4B Model (Google) — bundled with NYRA per Gemma's
         terms; see **Appendix: Gemma 3 Model Notice** (incorporated by
         reference from legal/00-04-nyra-eula-gemma-notice-appendix.md).

    6. `## 6. Generated Content — Liability Passthrough` (**D-06 NOVEL
       CLAUSE**): one clear paragraph stating:
       > "NYRA orchestrates third-party tools (including Meshy, ComfyUI,
       > Substance 3D Sampler, and Claude) to produce assets such as 3D
       > meshes, textures, materials, scene configurations, and code.
       > Ownership of, licensing of, and liability for any such
       > generated content flow from the originating third-party tool's
       > own terms directly to you. NYRA makes no representations or
       > warranties regarding the originality, copyright status,
       > fitness for any purpose, or commercial usability of generated
       > content. You are solely responsible for reviewing each
       > generated asset against the relevant third-party tool's
       > terms and any applicable laws before commercial use."
       Add sub-paragraphs explicitly flagging: (a) Meshy output is
       governed by Meshy's terms, (b) ComfyUI workflow output is the
       user's responsibility, (c) Substance Sampler output follows
       Adobe's terms per the user's Substance license, (d) Claude-
       generated code/text follows Anthropic's usage policies per the
       user's Claude subscription.

    7. `## 7. Reference Material — Ephemeral Processing` (**D-06 NOVEL
       CLAUSE**): one clear paragraph stating:
       > "NYRA supports reference-driven workflows where you may
       > provide images, video files, or URLs to videos (including
       > YouTube links) as references. When you provide a URL, NYRA
       > downloads the referenced content via `yt-dlp` to your local
       > temporary directory, extracts up to 16 keyframes, submits
       > those keyframes plus limited text context to Claude (via your
       > Claude subscription, through your local Claude Code CLI), and
       > deletes the full downloaded content from your temporary
       > directory after the analysis run completes. NYRA does not
       > transmit, host, or redistribute the full video or downloaded
       > content to any NYRA-owned server (no such server exists).
       > You represent and warrant that: (a) you have the right to
       > download and use the reference content for the purpose of
       > producing derivative Unreal Engine scenes in your own
       > projects, (b) you will not direct NYRA to copy the protected
       > expression of copyrighted works, only to infer structural,
       > lighting, and compositional properties, and (c) you assume
       > all responsibility for compliance with copyright and platform
       > terms of the source site (including YouTube's Terms of
       > Service)."
       Add a sub-paragraph noting that ephemeral processing is the
       DEFAULT and that a user can disable yt-dlp-based URL fetching
       entirely in settings if they prefer to only provide local files.

    8. `## 8. Data We Do Not Collect` (**Per CONTEXT.md §deferred,
       built-in privacy clause avoids a separate standalone policy**):
       - NYRA does not operate a backend server. No NYRA-owned
         telemetry, no NYRA-owned analytics, no NYRA-owned account
         system.
       - All chat history, attachments, and session state are stored
         locally under your project's `Saved/NYRA/` directory.
       - Crashes are NOT automatically reported; user may opt in to
         submit a diagnostics bundle via the in-plugin diagnostics
         drawer, which is a manual action.
       - Third-party services (Claude, Meshy, etc.) receive only the
         content you explicitly route to them through NYRA; each
         service's privacy policy governs its own data practices.

    9. `## 9. Warranty Disclaimer` — standard "AS IS" disclaimer
       adapted for a free plugin.

    10. `## 10. Limitation of Liability` — standard cap-to-zero-
        liability for a free plugin.

    11. `## 11. Indemnification` — user indemnifies NYRA for their
        own misuse, particularly around: content generated in
        violation of third-party terms, reference material used in
        violation of copyright, or regulatory misuse.

    12. `## 12. Termination` — on EULA breach; on user uninstall.

    13. `## 13. Governing Law & Venue` — founder chooses (default
        suggestion: jurisdiction of founder's residence; venue a
        county-level court in that jurisdiction; update at counsel
        review).

    14. `## 14. Changes to EULA` — NYRA may update the EULA with
        version-bump notice shipped in the plugin changelog.

    15. `## 15. General` — severability, entire-agreement, assignment.

    16. `## Appendix A: Gemma 3 Model Notice` — one line: "Incorporated
        by reference from [legal/00-04-nyra-eula-gemma-notice-appendix.md]
        (00-04-nyra-eula-gemma-notice-appendix.md)."

    17. `## Counsel Review Checklist (for post-v1)` — bulleted list of
        sections counsel should pay special attention to, flagging
        non-boilerplate areas: §6 (Generated Content), §7 (Reference
        Material), §8 (Data We Do Not Collect), §13 (Governing Law),
        Appendix A (Gemma Notice). One line each explaining the
        specific concern or ambiguity for counsel to resolve.

    Commit with `docs(00-04): author NYRA v1 EULA first draft (D-06 scope)`.
  </action>
  <verify>
    <automated>test -f .planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-draft.md && grep -q "status: founder-first-draft" .planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-draft.md && grep -q "counsel_reviewed: false" .planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-draft.md && grep -qi "generated content" .planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-draft.md && grep -qi "ephemeral" .planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-draft.md && grep -qi "yt-dlp" .planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-draft.md && grep -q "Meshy" .planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-draft.md && grep -q "ComfyUI" .planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-draft.md && grep -q "Gemma" .planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-draft.md && grep -qi "data we do not collect" .planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-draft.md && grep -qi "counsel review" .planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-draft.md</automated>
  </verify>
  <done>EULA draft exists with all 15 numbered sections + Appendix A + Counsel Review Checklist; both D-06 novel clauses (§6 Generated Content, §7 Ephemeral Processing) are present with the required specifics; frontmatter marks it as founder-first-draft with counsel review deferred.</done>
</task>

</tasks>

<verification>
Phase 0 SC#4 closure verification:
- [ ] Gemma terms snapshot exists with snapshot_date
- [ ] Gemma re-verify note exists with re_verify_verdict
- [ ] Gemma Notice appendix exists with prohibited-use enumeration
- [ ] NYRA EULA first draft exists with all 15 sections + Appendix A
- [ ] §6 Generated Content covers Meshy + ComfyUI + Substance + Claude
- [ ] §7 Reference Material covers yt-dlp + ≤16 keyframes + tmp delete + user affirms
- [ ] §8 Data We Do Not Collect is present (absorbs standalone privacy policy)
- [ ] Counsel Review Checklist is present (post-v1 deferral)
- [ ] All files committed to git
</verification>

<success_criteria>
Phase 0 SC#4 is CLOSED when:
1. Gemma license re-verify verdict is UNCHANGED or NON-MATERIAL-CHANGES
   (MATERIAL-CHANGES triggers a follow-up planning conversation before
   Phase 2 execution).
2. NYRA v1 EULA draft exists in `legal/00-04-nyra-eula-draft.md` with
   both D-06 novel clauses present and the standard boilerplate sections
   complete.
3. Gemma Notice appendix exists and is referenced from the EULA main doc.
4. The closure ledger (Plan 06) flips SC#4 from PENDING to CLOSED.
</success_criteria>

<output>
After completion, create `.planning/phases/00-legal-brand-gate/00-04-SUMMARY.md`
following the GSD summary template. Record: Gemma re-verify verdict,
EULA draft version, sections completed, counsel-review-deferred rationale.
</output>
