---
phase: 00-legal-brand-gate
plan: 02
slug: epic-fab-policy-email
type: execute
tdd: false
wave: 1
depends_on: []
autonomous: false
requirements: [PLUG-05]
task_count: 3
files_modified:
  - .planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-draft.md
  - .planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-sent.md
  - .planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-response.md
  - .planning/phases/00-legal-brand-gate/external-snapshots/fab-content-guidelines-SNAPSHOT.md
  - .planning/phases/00-legal-brand-gate/external-snapshots/fab-ai-disclosure-policy-SNAPSHOT.md
  - .planning/phases/00-legal-brand-gate/external-snapshots/fab-code-plugin-checklist-SNAPSHOT.md
  - .planning/phases/00-legal-brand-gate/legal/00-02-direct-download-fallback-plan.md
objective: >
  Close ROADMAP Phase 0 SC#2 — get a written AI-plugin policy pre-clearance
  from Epic/Fab on record before Phase 2 subscription code ships, AND
  document the direct-download fallback plan so a Fab rejection stops being
  product-fatal. Per D-07, the fallback is a PLAN not an implementation —
  Phase 8 builds it. Per D-03, email response must be written.
must_haves:
  truths:
    - "Sent-record of the Epic/Fab pre-clearance email exists under correspondence/ with subject, recipient chain (Fab seller support + dev-rel fallback), sent-timestamp, message-id; raw sender redacted in committed copy per D-03"
    - "Written response from Epic/Fab (Fab support or dev-rel) is filed under correspondence/ with verbatim language, received-timestamp, and founder verdict"
    - "Snapshots of the three Fab policy surfaces (Content Guidelines, AI-disclosure policy, Code Plugin submission checklist) exist under external-snapshots/, date-stamped to email-send date"
    - "A direct-download fallback plan doc exists under legal/ covering: signed Windows installer toolchain choice, update manifest format, SmartScreen mitigation strategy, hosting location, and the handoff-to-Phase-8 implementation pointer per D-07"
    - "The email draft explicitly enumerates NYRA's AI-plugin disclosure surface (Claude subprocess, Meshy REST, ComfyUI HTTP, Substance Sampler via computer-use, local Gemma fallback), the network-call surface (localhost-only + user-initiated external API calls + no NYRA-owned backend), and asks the three specific questions: (a) disclosure pattern acceptable? (b) expected review turnaround? (c) pre-submission policy-clarification channel?"
    - "Founder sign-off at the bottom of the response file with verdict: PERMITTED | CONDITIONAL | BLOCKED; PERMITTED or CONDITIONAL closes SC#2; BLOCKED shifts launch to the direct-download fallback primary per D-07"
  artifacts:
    - path: .planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-draft.md
      provides: "The email body, pre-send — subject, recipients, AI-disclosure list, network-call list, 3 questions, signature"
      contains: "AI-plugin disclosure"
    - path: .planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-sent.md
      provides: "Sent-record with recipient, Date-sent, Message-Id, thread URL"
      contains: "Date-sent:"
    - path: .planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-response.md
      provides: "Epic/Fab verbatim reply + founder interpretation + verdict"
      contains: "Verdict:"
    - path: .planning/phases/00-legal-brand-gate/external-snapshots/fab-content-guidelines-SNAPSHOT.md
      provides: "Fab Content Guidelines page snapshot — the general submission policies baseline"
      contains: "Snapshot-date:"
    - path: .planning/phases/00-legal-brand-gate/external-snapshots/fab-ai-disclosure-policy-SNAPSHOT.md
      provides: "Fab AI-disclosure policy snapshot (2026 current) — the specific policy NYRA must comply with"
      contains: "Snapshot-date:"
    - path: .planning/phases/00-legal-brand-gate/external-snapshots/fab-code-plugin-checklist-SNAPSHOT.md
      provides: "Fab Code Plugin submission checklist snapshot — per-engine binaries, network-call rules, AI disclosure flag"
      contains: "Snapshot-date:"
    - path: .planning/phases/00-legal-brand-gate/legal/00-02-direct-download-fallback-plan.md
      provides: "Direct-download fallback PLAN (not implementation) — installer toolchain + update manifest + SmartScreen + hosting + Phase 8 handoff"
      contains: "Phase 8"
  key_links:
    - from: correspondence/00-02-epic-fab-policy-email-draft.md
      to: external-snapshots/fab-ai-disclosure-policy-SNAPSHOT.md
      via: "Draft cites specific sections of the snapshotted AI-disclosure policy so reviewer answers against a known version"
      pattern: "AI-disclosure"
    - from: legal/00-02-direct-download-fallback-plan.md
      to: ROADMAP.md Phase 8
      via: "Fallback plan explicitly points at Phase 8 (Fab Launch Prep) as the implementing phase per D-07; DIST-02 requirement is the handoff hook"
      pattern: "Phase 8"
    - from: correspondence/00-02-epic-fab-policy-email-response.md
      to: .planning/ROADMAP.md Phase 0 SC#2
      via: "Response verdict + fallback-plan existence together close SC#2; ledger (00-06) reads both to flip the SC#2 status bit"
      pattern: "Verdict:"
---

<objective>
Phase 0 SC#2 has two halves: (a) get Epic/Fab to confirm NYRA's AI-plugin
disclosure pattern is acceptable before we sink Phase 2–8 effort into a
plugin that gets rejected at submission, and (b) document a direct-download
fallback plan so if Fab's verdict is BLOCKED or arrives too late, the
launch isn't dead.

Per STACK.md: Fab (Epic's unified marketplace, launched late-2024) accepts
C++ plugins with per-engine-version builds, and "AI-powered plugin
disclosure" has been a required compliance field since ~2024. Current 2026
policies were NOT confirmed during research (fab.com was blocked for the
researcher), so Phase 0 verification from the horse's mouth is the
non-negotiable gate.

Per CONTEXT.md D-07: the fallback is a plan, not an implementation. Phase 0
authors the plan doc; Phase 8 implements it. This plan is `autonomous: false`
because Task 3 (file Epic's response) requires an external reply, but the
fallback-plan doc (Task 2) is fully authored in this plan without external
dependency — so even if Epic's reply is slow, the launch-safety-net exists.

Purpose: Close SC#2 with both a written Fab verdict AND a shelf-ready
fallback so Fab rejection is recoverable.
Output: 3 correspondence files (draft, sent, response) + 3 external-snapshot
files (Fab policies) + 1 direct-download fallback plan doc.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/00-legal-brand-gate/00-CONTEXT.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Snapshot Fab policy surface + draft/send pre-clearance email</name>
  <files>
    .planning/phases/00-legal-brand-gate/external-snapshots/fab-content-guidelines-SNAPSHOT.md,
    .planning/phases/00-legal-brand-gate/external-snapshots/fab-ai-disclosure-policy-SNAPSHOT.md,
    .planning/phases/00-legal-brand-gate/external-snapshots/fab-code-plugin-checklist-SNAPSHOT.md,
    .planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-draft.md,
    .planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-sent.md
  </files>
  <action>
    Step A — Snapshot Fab policy surface. Fetch from https://www.fab.com/help
    the three policy pages relevant to NYRA:
    1. Fab Content Guidelines (general submission policies)
    2. Fab AI-disclosure / AI-content policy (current 2026 version)
    3. Fab Code Plugin submission checklist (per-engine binaries, network-
       calls, AI flag)

    URL paths may have drifted from STACK.md's research — use the live Fab
    help-center table of contents to find each document. For each, write a
    markdown snapshot file with YAML frontmatter `source_url:`,
    `snapshot_date:`, `snapshot_method:`, full text body.

    If Fab gates any of these pages behind a seller-dashboard login: the
    founder logs into fab.com as a seller, opens the page, and the executor
    copies the full text into the snapshot file. Record
    `snapshot_method: authenticated-seller-dashboard-copy` in that case.

    Step B — Draft the pre-clearance email as
    `00-02-epic-fab-policy-email-draft.md` (YAML frontmatter + body). Per
    D-09 use a direct founder-to-partner tone. The draft MUST include:

    1. One-line intro: NYRA is a free Unreal Engine 5 plugin, solo dev,
       targeting UE 5.4/5.5/5.6/5.7, planning a Fab submission in ~6–9
       months.
    2. AI-plugin disclosure surface (one section, enumerate every external
       AI dependency so the reviewer can't say "but what about X later"):
       - "NYRA invokes the user's locally-installed Claude Code CLI as a
         subprocess (`claude -p --output-format stream-json`) using the
         user's own subscription credentials; NYRA never sees the OAuth
         token and never embeds the Claude Agent SDK."
       - "NYRA drives Meshy via their REST API (user provides their own
         Meshy account + API key) for image → 3D model generation."
       - "NYRA drives a user-installed ComfyUI via its localhost HTTP API
         for image-to-image workflows (textures, variations)."
       - "NYRA uses Claude computer-use (`computer_20251124`, Opus 4.7) for
         Substance 3D Sampler (no public API exists) and UE editor modal
         dialogs — this is scoped to only those apps per the plugin's
         documented policy."
       - "NYRA optionally runs a local Gemma 3 4B GGUF model via
         llama.cpp/Ollama for offline/rate-limited/privacy fallback;
         Gemma's license permits commercial redistribution with notice
         (re-verified separately in Phase 0 Plan 04)."
    3. Network-call surface (one section, precise so the reviewer can
       confirm we meet the "no hidden backend" bar):
       - "All inter-process NYRA traffic is localhost-only (loopback
         WebSocket UE↔NyraHost; localhost HTTP NyraHost↔NyraInfer)."
       - "All external API traffic (Meshy, ComfyUI if remote, Anthropic via
         the user's `claude` CLI subprocess) is user-initiated and visible
         in the plugin UI."
       - "NYRA does NOT operate or call any NYRA-owned backend. No
         telemetry, no hosted auth, no hosted RAG, no hosted billing."
    4. Three specific questions (ask them numbered so the reply can answer
       in-line):
       - Q1: "Is NYRA's AI-plugin disclosure pattern — as enumerated above —
         acceptable for a free plugin submission under Fab's current
         AI-content policy?"
       - Q2: "What is the current expected review turnaround for a free
         Code Plugin with AI-content disclosure? We'd like to align our
         launch window."
       - Q3: "Is there a pre-submission channel for policy clarifications
         beyond this email thread, e.g. a dev-rel contact or a partner-
         program rep for plugins that drive external tools?"
    5. Attachments (mention in draft, attach actually when sending): PDFs
       of the three Fab-policy snapshots from Step A so the reviewer sees
       the version we're asking against.
    6. Signature: founder name, NYRA placeholder URL (nyra.dev or backup
       from Plan 03), GitHub org placeholder.

    Recipient order (record in frontmatter): primary Fab seller-support
    email address surfaced from the fab.com help center (varies over time
    — executor looks it up from the snapshotted Content Guidelines footer
    or the fab.com /help page). Fallback: any Epic dev-rel contact the
    founder has or a general `devrel@epicgames.com`. Subject line: "Free
    UE plugin pre-clearance — AI-content disclosure + network-call pattern".

    Step C — Founder sends the email. Populates
    `00-02-epic-fab-policy-email-sent.md` with frontmatter (subject,
    recipient, Date-sent, Message-Id, thread URL, redacted sender) and the
    full body EXACTLY as sent.

    Commit with
    `docs(00-02): snapshot Fab policy + draft and send pre-clearance email`.
  </action>
  <verify>
    <automated>test -f .planning/phases/00-legal-brand-gate/external-snapshots/fab-content-guidelines-SNAPSHOT.md && test -f .planning/phases/00-legal-brand-gate/external-snapshots/fab-ai-disclosure-policy-SNAPSHOT.md && test -f .planning/phases/00-legal-brand-gate/external-snapshots/fab-code-plugin-checklist-SNAPSHOT.md && test -f .planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-draft.md && test -f .planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-sent.md && grep -q "AI-plugin disclosure" .planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-draft.md && grep -q "Meshy" .planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-draft.md && grep -q "ComfyUI" .planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-draft.md && grep -q "computer_20251124" .planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-draft.md && grep -q "localhost" .planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-draft.md && grep -q "Date-sent:" .planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-sent.md</automated>
  </verify>
  <done>3 Fab snapshots exist with `snapshot_date`; draft enumerates all 4 AI dependencies + all 3 network-call facts + 3 numbered questions; sent-record has Date-sent + thread-id.</done>
</task>

<task type="auto">
  <name>Task 2: Author direct-download fallback plan document</name>
  <files>
    .planning/phases/00-legal-brand-gate/legal/00-02-direct-download-fallback-plan.md
  </files>
  <action>
    Per D-07, this task writes THE PLAN for direct-download distribution —
    not the implementation. Phase 8 (DIST-02) implements it.

    Author `00-02-direct-download-fallback-plan.md` (YAML frontmatter
    `status: plan-only`, `implements_at: Phase 8 DIST-02`, `author:`,
    `date:`) with the following mandatory sections:

    1. **Trigger conditions** — when does the fallback go live? Enumerate
       three trigger cases:
       (a) Fab verdict (Plan 00-02 response) is BLOCKED → fallback becomes
           primary distribution.
       (b) Fab review turnaround exceeds our launch window by >4 weeks →
           fallback launches first, Fab listing follows when it clears.
       (c) Post-launch Fab takedown → fallback remains available as
           continuity path.

    2. **Installer toolchain choice** — pick one installer framework and
       justify:
       - Candidates: Inno Setup (free, well-supported on Windows), NSIS
         (free, legacy), WiX (MSI-based, enterprise-flavoured), or a
         portable-zip distribution with a PowerShell setup script.
       - Choice: executor picks ONE based on D-09 discretion. Default
         recommendation: Inno Setup — free, MIT-equivalent, widely-used
         for UE plugin installers, supports code-signing hooks, supports
         per-engine-version subdirectories matching the Fab layout.
       - Record the chosen tool + one-paragraph rationale.

    3. **Update manifest format** — users who installed via direct-
       download need a way to be notified when NYRA ships a new version.
       Spec the manifest:
       - JSON schema: `{"version": "x.y.z", "ue_versions": ["5.4", "5.5",
         "5.6", "5.7"], "installer_url": "https://nyra.dev/releases/x.y.z/
         NYRA-x.y.z-Windows.exe", "sha256": "...", "released_at":
         "ISO-8601", "release_notes_url": "..."}`.
       - Hosting: `https://nyra.dev/updates/manifest.json` served over
         HTTPS with strong cache-bust.
       - Client polling cadence: once per editor launch, background,
         failure-silent. (Phase 2 adds the client-side polling code; Phase
         0 only specs the contract.)

    4. **SmartScreen mitigation strategy**:
       - EV code-signing cert (already a PROJECT.md budget line, $400–
         700/yr) signs the installer + all bundled binaries.
       - EV cert provides immediate SmartScreen reputation (no 30-day
         warmup).
       - Cert acquisition: handled in Phase 2 (DIST-03 is the EV cert
         requirement); direct-download distribution piggybacks on that
         cert.
       - Fallback if EV cert is delayed: non-EV cert (standard OV) has
         a 30-day SmartScreen reputation window that can be partially
         pre-warmed by uploading the installer to Microsoft's Authenticode
         submission portal for a-priori reputation; document this as
         emergency path only.

    5. **Hosting location & CDN**:
       - Primary: `https://nyra.dev/releases/` (custom domain acquired
         in Plan 00-03, backed by Cloudflare Pages or similar static
         host — zero-cost tier fits the free-plugin budget).
       - Mirror: GitHub Releases under `github.com/<nyra-org>/nyra` —
         already free, already versioned, already CDN-fronted. Listed in
         update manifest as a fallback URL.
       - Rationale: two independent hosts means a single-provider outage
         doesn't block users from installing.

    6. **Zero-config onboarding parity** — the direct-download install
       path must deliver the same first-run experience as the Fab install
       path per DIST-04 (zero-config, user just runs `claude setup-token`
       once and is operational). Call out the two places where the direct-
       download path differs:
       - Installer prompts the user to pick their UE install location
         (Fab's installer knows this automatically).
       - Uninstall is via Windows Add/Remove Programs (not via Fab's
         library UI).
       Otherwise identical.

    7. **Handoff to Phase 8** — explicit pointer: "Phase 8 (Fab Launch
       Prep) DIST-02 implements this plan. The DIST-02 plan author MUST
       read this doc and either implement as written or explicitly
       document any deviations with rationale. DIST-02 is the IMPLEMENTATION
       plan; this file is the SPEC."

    8. **Open questions deferred to Phase 8** — honest list of things this
       plan doesn't resolve (e.g. "will we mirror via IPFS?", "do we need
       a Linux/macOS installer when v1.1 adds those platforms?", "do we
       ship a dedicated auto-updater or piggyback on UE's own plugin-
       update mechanism?"). Phase 8 answers these when it gets there.

    Commit with `docs(00-02): author direct-download fallback plan`.
  </action>
  <verify>
    <automated>test -f .planning/phases/00-legal-brand-gate/legal/00-02-direct-download-fallback-plan.md && grep -q "Phase 8" .planning/phases/00-legal-brand-gate/legal/00-02-direct-download-fallback-plan.md && grep -q "status: plan-only" .planning/phases/00-legal-brand-gate/legal/00-02-direct-download-fallback-plan.md && grep -qi "smartscreen" .planning/phases/00-legal-brand-gate/legal/00-02-direct-download-fallback-plan.md && grep -q "EV" .planning/phases/00-legal-brand-gate/legal/00-02-direct-download-fallback-plan.md && grep -qi "installer" .planning/phases/00-legal-brand-gate/legal/00-02-direct-download-fallback-plan.md && grep -q "manifest" .planning/phases/00-legal-brand-gate/legal/00-02-direct-download-fallback-plan.md</automated>
  </verify>
  <done>Fallback plan doc exists with all 8 required sections, frontmatter marks it as plan-only, Phase 8 handoff is explicit.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: File Epic/Fab written response + founder verdict</name>
  <files>
    .planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-response.md
  </files>
  <what-built>
    Tasks 1+2 produced: 3 Fab policy snapshots, the email draft + sent-
    record, and the direct-download fallback plan. Even if Epic's reply is
    slow or BLOCKED, the fallback-plan doc is already shelf-ready. Task 3
    closes the external-wait half of SC#2 when Epic replies.
  </what-built>
  <how-to-verify>
    Founder action when Epic/Fab replies:

    1. Note received-timestamp (ISO-8601 UTC), responder email, thread URL.

    2. Create `.planning/phases/00-legal-brand-gate/correspondence/00-02-epic-fab-policy-email-response.md`
       with frontmatter:
       ```
       received_date: <ISO-8601>
       responder_address: <their email, redacted if personal>
       thread_id: <Gmail thread-id or Message-Id>
       verdict: PERMITTED | CONDITIONAL | BLOCKED | UNCLEAR
       expected_review_turnaround: "<their answer to Q2, verbatim>"
       pre_submission_channel: "<their answer to Q3, verbatim>"
       ```

    3. Under `## Epic/Fab Verbatim Reply`, paste the FULL reply body.

    4. Under `## Founder Interpretation`, 3–6 sentences on how you read
       each of the 3 answers (Q1/Q2/Q3) and why you chose the verdict bit.

    5. Under `## Conditions to Comply With Pre-Launch` (if CONDITIONAL),
       enumerate each condition with an acceptance criterion that a
       downstream plan (Phase 8 or earlier) will hit.

    6. Under `## Sign-off`:
       ```
       Approved: <today ISO-8601>, <founder name>
       Interpretation: <PERMITTED | CONDITIONAL | BLOCKED>
       Phase 2 gate: <OPEN | OPEN-WITH-CONDITIONS | CLOSED>
       Phase 8 primary distribution: <Fab | direct-download fallback>
       ```

    7. Commit with `docs(00-02): file Epic/Fab response + founder verdict`.

    Verdict semantics:
    - PERMITTED → Phase 2 gate OPEN (relative to SC#2). Phase 8 primary
      distribution = Fab. Fallback remains as shelf-ready insurance.
    - CONDITIONAL → Phase 2 gate OPEN-WITH-CONDITIONS. Record conditions.
      Phase 8 primary distribution = Fab with conditions applied.
    - BLOCKED → Phase 2 gate OPEN (Phase 2 is independent of Fab approval;
      subscription driving is cleared by Plan 00-01). Phase 8 primary
      distribution = direct-download fallback per D-07. NYRA ships anyway.
    - UNCLEAR → Send clarifying follow-up; re-run Task 3 when clarified.

    If 6 weeks pass with no reply: send a polite follow-up citing sent-
    date + Q1/Q2 again. If another 4 weeks silent, the founder has a
    decision: either pause submission and escalate (LinkedIn to an Epic
    dev-rel person, or Epic community forum) or commit to the direct-
    download fallback as the primary launch path and file a "no response
    after 10 weeks" response file with verdict: BLOCKED-BY-SILENCE so
    Phase 8 plans flow accordingly.
  </how-to-verify>
  <resume-signal>Type "approved: permitted", "approved: conditional", "approved: blocked", or paste the response file path + verdict.</resume-signal>
</task>

</tasks>

<verification>
Phase 0 SC#2 closure verification:
- [ ] 3 Fab-policy snapshots exist with `snapshot_date` frontmatter
- [ ] Email draft enumerates all 4 AI dependencies + all 3 network-call facts + 3 numbered questions
- [ ] Sent-record has Date-sent + thread-id
- [ ] Direct-download fallback plan doc exists with all 8 required sections (D-07)
- [ ] Response file exists with Epic/Fab verbatim reply + founder verdict
- [ ] Verdict is PERMITTED, CONDITIONAL, or BLOCKED (documented)
- [ ] All files committed to git
</verification>

<success_criteria>
Phase 0 SC#2 is CLOSED when both halves land:
1. `correspondence/00-02-epic-fab-policy-email-response.md` exists with a
   verdict (any of PERMITTED / CONDITIONAL / BLOCKED — BLOCKED does not
   fail SC#2 because the fallback plan covers it per D-07).
2. `legal/00-02-direct-download-fallback-plan.md` exists as a complete
   spec ready for Phase 8 DIST-02 to implement.
3. The closure ledger (Plan 06) flips SC#2 from PENDING to CLOSED citing
   both files + the chosen primary-distribution path.

Unlike SC#1, SC#2 has a built-in safety net (the fallback). That is the
entire point of D-07: Fab rejection stops being product-fatal.
</success_criteria>

<output>
After completion, create `.planning/phases/00-legal-brand-gate/00-02-SUMMARY.md`
following the GSD summary template. Record: snapshot dates, email sent-date,
response received-date, verdict, chosen primary distribution path
(Fab | direct-download), and Phase 8 handoff notes.
</output>
