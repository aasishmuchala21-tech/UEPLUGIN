# Domain Pitfalls

**Project:** NYRA — UE5 in-editor AI assistant plugin driven by user's Claude + Codex subscriptions, with Claude computer-use orchestrating external tools (Meshy, Substance, ComfyUI, Blender)
**Researched:** 2026-04-21
**Confidence:** MEDIUM overall. Legal/ToS items are MEDIUM-HIGH (Anthropic/OpenAI usage policies are well-documented). Fab-specific policies on AI plugins are LOW-MEDIUM (policies evolve; verify current Fab TOS before submission). UE plugin ABI and AssetRegistry pitfalls are HIGH (well-documented Epic patterns).

**Note on tooling:** Bash, WebSearch, Grep, and template Read were denied in this research session. Content below is drawn from training data, the prompt's pitfall enumeration, and the PROJECT.md context. The recommended verification phase (Phase 1) should re-confirm the LEGAL and FAB items against live docs before code starts.

---

## Severity Scale

- **BLOCKING** — Would kill the product or cause delisting/legal action. Must have a mitigation *before* the affected phase starts.
- **HIGH** — Will cause major rework, bad reviews, or demo failure at launch. Mitigation required in-phase.
- **MEDIUM** — Will cause user friction or phase slippage. Mitigation should be tracked; graceful-degrade acceptable.
- **LOW** — Annoying, fixable post-launch. Track in backlog.

## Phase Map (referenced below)

Roadmap will be authored in a later phase; this document pre-tags pitfalls with the *logical* phase in which they should be neutralized:

- **P0 Legal/ToS gate** — must precede any code
- **P1 Subscription bridge** — Claude Code + Codex CLI subprocess, auth, rate limits
- **P2 UE5 plugin shell + Fab packaging** — C++ plugin, per-UE-version builds, module boundaries
- **P3 Knowledge / RAG** — corpus ingestion, index, citation, version tagging
- **P4 UE-native actions** — Blueprints, actors, materials, lighting, Sequencer
- **P5 Computer-use orchestration** — Claude computer-use driving Meshy/Substance/ComfyUI/Blender
- **P6 Reference-driven workflows** — image/video → scene, launch demo
- **P7 Distribution** — Fab listing, onboarding, signing
- **Cross-cutting** — spans multiple phases

---

## 1. Claude + Codex Subscription Driving

### 1.1 Anthropic Claude Code ToS on third-party subprocess driving — **BLOCKING**

**What goes wrong:** NYRA shells out to `claude` (Claude Code CLI) inside a third-party commercial UE plugin. Anthropic's consumer subscription terms (Claude Pro/Max) and the Claude Code acceptable use policy restrict automated/programmatic use of consumer subs; Claude Code is explicitly designed to be *interactively* driven by a developer at their own terminal. Shipping a product that marches users' subscription minutes through subprocess automation can be read as (a) sharing access to a consumer sub with a third-party product, (b) circumventing API billing, (c) operating an unauthorized "wrapper" around the subscription.

**Warning signs:**
- ToS language containing "sole benefit of the subscriber," "no resale," "no automated scripts," "no sharing credentials with third parties."
- Anthropic product changes that move Claude Code auth to per-IDE scopes (e.g., "Claude Code for VS Code" style sandboxes).
- Community/X posts of Anthropic rate-limiting or banning accounts that ran Claude Code under automation harnesses.
- Lack of an Anthropic-published "build commercial products on top of Claude Code" pathway.

**Prevention:**
1. **P0:** Read and summarize (as of build-start date) Anthropic's: Usage Policy, Consumer Terms, Claude Code Terms, Commercial Terms. Archive PDFs in `.planning/legal/`.
2. **P0:** Open a ticket with Anthropic asking a direct question: "Is it permissible for a third-party commercial plugin to drive the Claude Code CLI as a subprocess on the end user's own machine, using the end user's own subscription and OAuth token, with the end user's explicit consent?" Keep the written answer.
3. **P1:** Design the bridge so the *user* is always the principal: plugin never stores/reads their OAuth token; plugin spawns `claude` as a child process under the user's own login session; user sees full prompts and tool-use requests.
4. **P1:** Add explicit first-run disclosure: "This plugin drives *your* Claude Code session on *your* machine. It will count toward *your* Anthropic rate limits and is subject to Anthropic's Terms." User must check a box.
5. **P1:** Support an API-key mode (user-supplied Anthropic API key billed to them) as an escape hatch if subscription driving is ever prohibited. Keeps the product alive even if wedge #1 collapses.
6. **Cross-cutting:** Never, ever market NYRA as "unlimited Claude for $0" — market it as "bring your own subscription."

**Phase:** P0 (gate) + P1 (implementation)
**Severity:** BLOCKING (if Anthropic says no, the economic wedge collapses; need API-key fallback planned from day one)

---

### 1.2 OpenAI Codex CLI ToS on subscription driving — **BLOCKING**

**What goes wrong:** Same shape as 1.1, applied to Codex CLI driven by a user's ChatGPT Plus/Pro/Business subscription. OpenAI's consumer terms historically forbid using ChatGPT access to build competing products or to resell capacity. Codex CLI's TOS as of its 2025 GA explicitly ties seat usage to "your own development." A plugin that spawns Codex CLI on behalf of any user who happens to have the sub is a grey area at best.

**Warning signs:**
- OpenAI Usage Policies sections on "automated access," "resale," or "scraping."
- Codex CLI auth flow requiring interactive OAuth in a browser, with a session cookie that breaks when the browser closes.
- Posts showing Codex CLI refusing to run when stdin/stdout is not a TTY.

**Prevention:**
1. **P0:** Same legal audit as 1.1, for OpenAI.
2. **P0:** Send OpenAI a parallel clarification request.
3. **P1:** Support user-supplied OpenAI API key mode as escape hatch.
4. **P1:** If Codex CLI requires an interactive TTY, spawn it with a pseudo-TTY (pty) from C++/Node — but document this as a support gotcha.
5. **P1:** Do not bundle Codex CLI binary; require user to install it (keeps liability on the user's side: they agreed to OpenAI ToS when they installed Codex).
6. **Cross-cutting:** Treat Codex as Priority-2 relative to Claude (Claude is the wedge; Codex is nice-to-have). If only one survives the legal gate, ship with Claude.

**Phase:** P0 + P1
**Severity:** BLOCKING

---

### 1.3 Auth drift — tokens expire, user logs out, OAuth scope changes mid-release — **HIGH**

**What goes wrong:** Claude Code and Codex CLI store OAuth tokens locally (typically `~/.claude/` / `~/.codex/`). Tokens refresh silently most of the time but break when: the user logs out, the vendor rotates refresh-token format, the user switches accounts, or the vendor invalidates sessions en masse. NYRA sees an opaque failure mid-scene-build and the user has no idea why.

**Warning signs:**
- `claude` subprocess exits code non-zero with "Not authenticated" / "session expired."
- Silent truncation of responses.
- User reports "it worked yesterday."

**Prevention:**
1. **P1:** Implement a "health check" MCP-style ping to Claude Code / Codex at plugin boot and before each big action. If unauth, surface a modal: "Please run `claude login` / `codex login` in a terminal, then click Retry."
2. **P1:** Detect common error strings from each CLI and map them to human messages. Snapshot CLI versions tested against and add a version-pin check.
3. **P1:** Never swallow auth errors into generic "something went wrong." Distinct error class.
4. **P1:** Log (locally, opt-in) the CLI exit code + first-line stderr for support triage.

**Phase:** P1
**Severity:** HIGH

---

### 1.4 Rate-limit / quota exhaustion mid-action — **HIGH**

**What goes wrong:** Claude Pro/Max and ChatGPT Plus/Pro have rolling 5-hour windows. NYRA kicks off a scene-build that fans out into 40 tool calls; user hits their cap 20 calls in; computer-use automation is halfway through driving Meshy; Meshy now has a half-submitted job; UE has a half-imported asset. Everything is in a broken intermediate state.

**Warning signs:**
- HTTP 429 from the CLI; "rate limit reached" in stderr.
- Long pauses where the CLI blocks waiting for the window to reset.
- Claude Code's "quota bar" showing red.

**Prevention:**
1. **P1:** Pre-flight estimator — before starting a multi-step job, estimate tool-call budget and ask the CLI for remaining quota (Claude Code exposes this). Warn user "this job will likely use ~25% of your 5-hour window; continue?"
2. **P1:** **Checkpointing** — every durable side-effect (file written, UE asset imported, Meshy job started) is recorded to a transactional `.nyra/job.json`. Resume logic picks up after a quota reset.
3. **P1:** Backoff + graceful pause — if rate-limited mid-job, pause the job (not abort), show the user a timer, offer to switch to Gemma-4B-fallback for remaining *knowledge-only* steps (not for computer-use).
4. **P5:** Computer-use orchestration must be idempotent at the tool boundary — re-running the "upload to Meshy" step should detect an existing job, not start a second one.
5. **Cross-cutting:** Separate the "planning" LLM (cheap, local Gemma or the single large Claude call) from the "doing" LLM (costly computer-use calls) so the user doesn't burn premium quota on internal thinking loops.

**Phase:** P1 (quota introspection) + P5 (checkpointing across computer-use)
**Severity:** HIGH — mid-scene-build failure is the worst possible user experience.

---

### 1.5 CLI version drift — Claude Code / Codex CLI are moving targets — **HIGH**

**What goes wrong:** Claude Code ships weekly with behavioral changes (command flags renamed, output schema changed, auth flow tweaked). NYRA was tested against `claude-code@1.4.2`; user has `1.7.0`; the `--format json` flag now emits a different shape. Plugin breaks silently.

**Warning signs:**
- New fields in CLI stdout that don't parse.
- Release notes from Anthropic announcing breaking CLI changes.
- Users reporting "worked last week, broken today."

**Prevention:**
1. **P1:** Detect `claude --version` / `codex --version` at startup. Maintain a `supported-versions.json` with ranges. Warn clearly outside the range: "NYRA is tested with Claude Code 1.4.x–1.7.x. You have 1.9.0. Things may break — please report."
2. **P1:** Wrap CLI I/O in a thin adapter layer so swapping the transport (direct JSON, MCP, HTTP) is a one-file change.
3. **P1:** **Do not parse human-readable output.** Require JSON / MCP stream. If the CLI can't emit structured output, fall back to not integrating that feature.
4. **P1:** Nightly CI job (or a weekly local smoke test) that runs the top-10 NYRA commands against the latest CLI versions. Catch breakage before users do.
5. **Cross-cutting:** Bias toward MCP (protocol) over CLI (binary). MCP is versioned at the protocol level; CLIs change flags at any time.

**Phase:** P1
**Severity:** HIGH

---

### 1.6 "User without subscription" onboarding dead-end — **MEDIUM**

**What goes wrong:** A UE dev installs NYRA from Fab excited to try it. They don't have Claude or Codex. The plugin says "please sign into Claude or Codex to continue." They close the plugin, leave a 1-star review: "Doesn't work out of the box."

**Warning signs:**
- Low activation rate (installs ÷ first-successful-action).
- Fab reviews mentioning "need to pay for something else first."
- Support tickets asking "which subscription do I need?"

**Prevention:**
1. **P1:** Ship the **Gemma 4B local fallback** as truly first-class, not aspirational. On first-run, if no subscription is detected, NYRA should immediately demonstrate value with Gemma (e.g., "here's what I can do locally; here's what unlocks with a subscription").
2. **P7:** Fab listing must set expectations above the fold: screenshot of the "No subscription? Use local mode" banner. The product page must not bait-and-switch.
3. **P7:** A 60-second in-editor tour on first-run, explaining the three modes (Claude / Codex / local Gemma) with "Try with Gemma now" CTA.
4. **P7:** Offer a clear upgrade path — a "Connect Claude" button that links to Anthropic's signup with a UTM so we can measure conversion (not an affiliate, just attribution).

**Phase:** P1 (tech) + P7 (UX)
**Severity:** MEDIUM

---

## 2. Claude Computer-Use Reliability on Windows

### 2.1 Element-detection false positives — **HIGH**

**What goes wrong:** Computer-use identifies "the Generate button" by vision+coords; it clicks where the button *was* on the tested build; Meshy A/B-tests a redesign; the click hits the "Delete" button instead. Agent reports success. User's account loses work.

**Warning signs:**
- Pixel-level regressions in Meshy/Substance/ComfyUI UIs after a release.
- Computer-use action success rate dropping in the canary run.
- User screenshots showing clicks at unexpected coordinates.

**Prevention:**
1. **P5:** **Visual verification before every destructive click.** Take the screenshot → model must explicitly say "I see [Generate button] with text 'Generate' and it is enabled" before clicking. If the assertion fails, halt and ask user.
2. **P5:** Prefer keyboard shortcuts and URL parameters over clicks when the target app supports them (Meshy, ComfyUI expose URL-param-driven flows).
3. **P5:** **Canary suite** — maintain a scripted demo run against Meshy/Substance/ComfyUI that executes daily on a CI VM. If any step fails, flip a feature flag off so users don't hit it.
4. **P5:** Screen-recording of every computer-use session, retained locally (user-controlled), so a failed run can be post-mortemed.
5. **P5:** Hard timeout + max-retry (e.g., 3 attempts per step, 5-minute wall clock per tool) with clear failure UX: "Meshy's UI has changed. Please finish this step manually."
6. **Cross-cutting:** Prefer official API > MCP server > computer-use. Re-check every target tool quarterly for a real API (Meshy has one; ComfyUI has a workflow API; use them).

**Phase:** P5
**Severity:** HIGH — destructive false-positives are the single scariest failure mode.

---

### 2.2 Windows UAC / SmartScreen / modal-dialog nightmares — **HIGH**

**What goes wrong:** Claude computer-use is driving Meshy in Chrome; a Windows UAC prompt pops up from an unrelated process; the UAC dialog runs on the Secure Desktop — screenshots from the ordinary desktop can't see it; computer-use is now blind and clicking into the void. Worse: SmartScreen blocks a download the agent initiated.

**Warning signs:**
- Agent "stuck" with the same screenshot every step.
- Windows Event Log entries for UAC prompts during automation runs.
- SmartScreen toasts in screenshots.

**Prevention:**
1. **P5:** **Pre-flight system check** on first-run: detect if the user is on an admin account, whether UAC is at default level, whether SmartScreen for apps is enabled. Document a "Computer-Use Ready" profile and guide users to it.
2. **P5:** Never run computer-use on the Secure Desktop. Detect Secure Desktop active (via Win32 API `GetThreadDesktop`) and pause.
3. **P5:** Modal detection — after every click, verify the foreground window class. If a UAC/SmartScreen dialog is detected, halt and ask the user to resolve it.
4. **P5:** Pre-whitelist / pre-install target tools (Meshy is web; ComfyUI is local) *before* a demo run starts, so no installer/UAC prompt fires mid-run.
5. **P2:** Do not require the plugin itself to elevate. Never run UE editor as Admin — break features that need Admin rather than dragging the user into a bad security posture.

**Phase:** P5 (detection) + P2 (architecture: don't require elevation)
**Severity:** HIGH

---

### 2.3 DPI scaling + multi-monitor coordinate confusion — **HIGH**

**What goes wrong:** User has 4K primary at 150% DPI and a 1080p secondary at 100%. Computer-use reports "click at (1800, 900)" — which monitor? Which DPI space? Clicks land off-screen or on the wrong app. This is the single most common computer-use bug on Windows.

**Warning signs:**
- Clicks consistently N pixels off.
- Multi-monitor users reporting 100% failure rate.
- Screenshots that show different windows than the user sees.

**Prevention:**
1. **P5:** Normalize to the primary monitor at 100% DPI. Before automation, bring the target window to the primary monitor and note its HWND.
2. **P5:** Use Windows UIAutomation (UIA) for structural clicks where possible (Chrome, Electron, Substance all support UIA) — UIA works in logical coordinates and is DPI-safe.
3. **P5:** Document a "computer-use mode": single primary monitor, app maximized, DPI fixed. Enforce at runtime: "NYRA computer-use is about to take over. Please confirm the target app is on your primary monitor."
4. **P5:** Emit a pre-run screenshot and ask the user to confirm "Yes, that's what I see" — catches DPI/monitor mismatch before the agent does damage.

**Phase:** P5
**Severity:** HIGH

---

### 2.4 Target-app version drift — Meshy/Substance/ComfyUI UIs change — **HIGH**

**What goes wrong:** NYRA's computer-use prompts ("click the 'Generate 3D' button on the left panel") assume Meshy v4.2; Meshy ships v5 with a redesigned left panel; all NYRA tutorials break on day X+1.

**Warning signs:**
- Canary suite (see 2.1) fails after a Meshy/Substance/ComfyUI release.
- Twitter posts about a Meshy redesign.
- Support tickets spike in the 24 hours after a target-app release.

**Prevention:**
1. **P5:** Canary suite (shared with 2.1) is the primary detector.
2. **P5:** Version-detect target apps where possible (Meshy footer, Substance About dialog, ComfyUI version endpoint) and gate features per known-good version range.
3. **P5:** **Prefer the stable API** — Meshy has a REST API for the core generate flow. Use it. Reserve computer-use for tools that *don't* expose APIs (ComfyUI's custom UI states, Blender for interactive retopo).
4. **P5:** Feature flag each tool independently so a Meshy UI break doesn't kill Substance workflows.
5. **P5:** "Updated UI detected, computer-use disabled for this tool. Please use the manual workflow or wait for a NYRA update." — graceful degrade, not silent failure.

**Phase:** P5
**Severity:** HIGH

---

### 2.5 Race conditions — clicking before the page is ready — **HIGH**

**What goes wrong:** Agent clicks "Upload," the upload form is still hydrating, click is lost; agent assumes upload started; next step (click "Generate") finds no upload. Or: Meshy shows "processing… 0%," agent polls DOM and sees "Complete" because the text from a prior job is still in the buffer.

**Warning signs:**
- Intermittent failures with no clear reproducer.
- Success-rate differences between fast and slow networks.
- "Completed" status followed by empty output.

**Prevention:**
1. **P5:** Every action step has an **explicit post-condition** ("after clicking Upload, a file chooser must open OR an upload progress bar must appear within 5 seconds"). Verify post-condition before moving on.
2. **P5:** Use event-based waits, not `sleep(N)` — wait for element to be `interactive` via UIA or DOM ready state, not wall-clock.
3. **P5:** Hash the last-seen screenshot region; require it to *change* before accepting a click landed (otherwise you might be polling stale pixels).
4. **P5:** For long-running target actions (Meshy 3-minute generate), poll with an increasing interval (1s, 3s, 10s, 30s) and require a specific "Done" signal (filename in downloads, status API ok, screenshot OCR match).

**Phase:** P5
**Severity:** HIGH

---

### 2.6 Long-running job polling — "Meshy takes 3 minutes" — **MEDIUM**

**What goes wrong:** Agent kicks off Meshy, then falls into a polling loop that burns Claude calls every 5 seconds for 3 minutes → 36 unnecessary model invocations → quota exhaustion.

**Warning signs:**
- Sudden spike in Claude calls per "successful" job.
- User hits rate limit on a job that should be 4 calls total.
- CPU pegged from constant screenshotting.

**Prevention:**
1. **P5:** For every target tool, define the **cheapest possible poll**: filesystem watch > HTTP API poll > DOM check > OCR screenshot. In that order.
2. **P5:** Meshy specifically has a REST status endpoint — use it; do not screenshot-poll.
3. **P5:** Polling is done by *plugin code*, not by an LLM agent. The LLM gets invoked once at job start and once at job completion. Polling is dumb code.
4. **P5:** Cap poll wall-clock per job (e.g., 10 min default; user override). If exceeded, ask the user rather than quietly waiting.

**Phase:** P5
**Severity:** MEDIUM — quality issue; not a data-destruction issue like 2.1–2.5.

---

### 2.7 User-watching vs user-AFK UX — **MEDIUM**

**What goes wrong:** Computer-use hijacks the user's mouse and keyboard. If the user is watching, they see their cursor jerking around — unsettling. If the user is AFK and comes back mid-run, they interrupt the agent by moving the mouse, breaking the run.

**Warning signs:**
- Support tickets: "it clicked my email by accident."
- User reports of stopped runs with no error.

**Prevention:**
1. **P5:** **Run target apps in a separate user session where possible.** Windows "secondary session" (Shadow, or Remote Desktop into localhost) isolates cursor. Or use a headless browser (Playwright) for web targets (Meshy) so there's no cursor takeover at all — computer-use was a hammer; a headless browser is a scalpel.
2. **P5:** Clear "agent-active" HUD in UE — non-dismissible banner "NYRA is driving your computer. Click [PAUSE] to interrupt."
3. **P5:** Keyboard chord to instantly pause (e.g., Ctrl+Alt+Space). Publicized in onboarding.
4. **P5:** Detect human input during an agent run (mouse moved > N pixels in a non-agent frame) → auto-pause.
5. **P6:** Launch demo uses headless browser path for Meshy (no cursor takeover) — makes the demo reliable *and* the daily UX better.

**Phase:** P5 (detection) + P6 (launch demo architecture)
**Severity:** MEDIUM — impacts trust more than correctness.

---

## 3. UE Plugin Distribution (Fab)

### 3.1 Fab's AI-plugin policy — unknown and evolving — **BLOCKING**

**What goes wrong:** Fab (Epic's marketplace, post-2024 UE Marketplace replacement) has evolving policies on AI-generated content, AI tools that reach external services, and plugins that automate other software. A plugin that (a) drives third-party websites, (b) ingests user images to ship to external AI services, (c) depends on a non-Epic AI subscription, (d) ships an ML model, may be rejected at submission or delisted post-launch. *LOW-MEDIUM confidence — requires live verification.*

**Warning signs:**
- Fab submission review delayed beyond typical 2–4 weeks.
- Rejection citing "automation of external services," "AI training data provenance," or "subscription dependency."
- Public Fab policy updates about AI content.

**Prevention:**
1. **P0:** Read Fab's current Content Guidelines, Creator Terms, and Acceptable Use (as of build-start). Archive PDFs.
2. **P0:** Email Epic Fab creator support with a one-page product summary ("UE plugin that requires user's own Claude subscription; drives Meshy on the user's behalf; ships local ML model under Apache 2"). Get written pre-clearance.
3. **P2:** Architect the plugin so contentious features can be toggled off per-jurisdiction / per-distribution-channel without a fork. "Fab build" vs "Direct build" (GitHub releases).
4. **P7:** Plan for a **direct-distribution fallback** from day one (signed installer, GitHub releases, Itch.io mirror). If Fab rejects, we ship anyway. Listed vs. unlisted matters for discovery but not for existence.
5. **P7:** Fab listing copy avoids trigger words ("automates," "bot," "crawls"). Instead: "assists," "drives on your behalf," "orchestrates."

**Phase:** P0 (legal) + P7 (distribution)
**Severity:** BLOCKING if sole-distribution is Fab-only. With direct-distribution fallback: HIGH.

---

### 3.2 Binary size / per-UE-version builds — **HIGH**

**What goes wrong:** UE plugins must ship a separate binary per UE version (5.4, 5.5, 5.6, 5.7) × per platform; NYRA bundles a RAG index (potentially hundreds of MB), a Gemma 4B model (~4 GB), an ONNX model or two, and native .dll deps. Plugin balloons past Fab's size cap; or plugin takes 20 minutes to download.

**Warning signs:**
- Packaged `.uplugin` dir > 2 GB per UE-version.
- Fab upload timing out.
- First-install feedback: "too big to download."

**Prevention:**
1. **P2:** **Model and index hosted, not bundled.** Fab plugin ships a thin shell; RAG index + Gemma weights download on first-run from a CDN (Cloudflare R2 / GitHub releases). User sees a "Downloading knowledge base (800 MB)" progress bar.
2. **P2:** Per-UE-version binaries share all non-native assets (index, models) via a per-user cache directory (`%LocalAppData%/NYRA/`).
3. **P2:** Model quantization — Gemma 4B Q4_K_M is ~2.5 GB. Do not ship unquantized.
4. **P2:** The native C++ shell should be < 20 MB per UE version. All heavy lifting in the downloaded runtime.
5. **P3:** Index slicing — ship a tiny "bootstrap" index in the Fab package (50 MB — enough for offline first answer), full index downloaded lazily.

**Phase:** P2 + P3
**Severity:** HIGH

---

### 3.3 C++ ABI breakage UE 5.4 → 5.7 — **HIGH**

**What goes wrong:** UE's C++ ABI is not stable across minor versions. Headers move, UPROPERTY macros gain fields, Blueprint-facing APIs are deprecated. NYRA builds on 5.4; users on 5.6 crash because a vtable shifted. Support burns days.

**Warning signs:**
- Compile errors when bumping UE version in the build matrix.
- Runtime crashes in UE version N not seen in N-1.
- Epic release notes with "BREAKING" tags in the Editor module.

**Prevention:**
1. **P2:** **CI with all four UE versions** (5.4, 5.5, 5.6, 5.7) from Phase 2 day one. GitHub Actions with self-hosted Windows runners; do not defer this.
2. **P2:** Isolate version-specific code behind `#if ENGINE_MAJOR_VERSION == 5 && ENGINE_MINOR_VERSION >= X` blocks. Keep those blocks small and clearly tagged.
3. **P2:** Use MCP / IPC boundary aggressively — C++ shell is small; most logic lives in a child process (Node / Python) that is version-independent.
4. **P2:** Track Epic's UE public roadmap; if 5.8 is imminent, factor its breaking changes before release.
5. **P2:** Automated smoke test per UE version — launch editor, enable plugin, run 5 canned actions. If any fails, do not ship that version.

**Phase:** P2
**Severity:** HIGH

---

### 3.4 Anti-virus / SmartScreen blocking subprocess spawn — **HIGH**

**What goes wrong:** NYRA spawns `claude.exe`, `codex.exe`, `ollama.exe`, and drives Chrome via CDP. Windows Defender / AV flags the unsigned plugin DLL as "suspicious process spawning"; SmartScreen warns the user away; enterprise AV blocks the process entirely.

**Warning signs:**
- Enterprise users reporting "plugin won't load."
- SmartScreen popup on first run.
- VirusTotal flagging the plugin (false positive).

**Prevention:**
1. **P2:** **Code-sign the plugin's native DLLs with an EV cert.** EV certs ($400–700/year) instantly clear SmartScreen reputation. Non-EV certs still warn for ~30 days. Plan this cost in.
2. **P7:** Submit early builds to Microsoft Defender's "not malware" portal to pre-clear false positives.
3. **P2:** Use named-pipe IPC with well-known names (`\\.\pipe\nyra-*`), avoid raw socket listeners that look like trojans.
4. **P2:** Document AV allowlist instructions for enterprise users in docs/ENTERPRISE.md.
5. **P7:** Fab listing explicitly states system requirements and "may require antivirus exception on locked-down corporate machines."

**Phase:** P2 (signing) + P7 (comms)
**Severity:** HIGH

---

### 3.5 NNE / ONNX model licensing — **HIGH**

**What goes wrong:** NYRA bundles Gemma 4B. Gemma license (Google) has use restrictions; redistributing inside a commercial Fab plugin may or may not be permitted. Or: user-contributed ONNX models (e.g., community depth estimators) ship under "research only" licenses that forbid commercial use. Fab delists or Google sends a letter.

**Warning signs:**
- License text mentioning "research only," "non-commercial," "Google AI services only."
- Upstream model cards updated post-ship.

**Prevention:**
1. **P0:** Legal audit of every bundled model: Gemma, any ONNX, any tokenizer. Record SPDX license IDs.
2. **P0:** Gemma 4B specifically: Google's Gemma Terms allow commercial redistribution subject to the Prohibited Use Policy. Re-verify as of build date; archive PDF.
3. **P2:** **Download models on first-run from the original provider** (Kaggle/HuggingFace/ollama) rather than re-hosting. Places the EULA click in front of the user, not us.
4. **P3:** If shipping any model we didn't train: attribution file + license summary visible in the plugin's About dialog.
5. **Cross-cutting:** Prefer Apache-2/MIT-licensed models. Forbid GPL (copyleft infection).

**Phase:** P0 (audit) + P2 (delivery mechanism) + P3 (attribution)
**Severity:** HIGH

---

### 3.6 GPU compatibility — Gemma 4B won't run on low-VRAM machines — **MEDIUM**

**What goes wrong:** User has a GTX 1060 (6 GB VRAM). Gemma 4B loads, OOMs, crashes UE editor. User posts "NYRA crashed my Unreal" on Twitter.

**Warning signs:**
- Crash reports with `VkAllocateMemory` / `CUDA out of memory` / `DXGI_ERROR_DEVICE_HUNG`.
- Slow inference (< 2 tok/s) on lower-tier GPUs.

**Prevention:**
1. **P2:** **Never load Gemma in-process with UE.** Run Ollama (or llama.cpp server) as a separate child process with its own VRAM footprint. If it OOMs, UE survives.
2. **P2:** GPU probe at install: detect VRAM, compute capability, CUDA/DirectML availability. If below Gemma-4B threshold, default to CPU mode with a warning; if below CPU-RAM threshold (16 GB), disable local mode entirely and surface "subscription required."
3. **P2:** Multiple quantization options (Q4, Q5, Q8) selectable based on hardware probe.
4. **P7:** Fab listing states minimum and recommended specs clearly.
5. **P7:** Hardware tier is tracked in opt-in telemetry so we know the real distribution.

**Phase:** P2 + P7
**Severity:** MEDIUM (graceful degrade makes this not-blocking)

---

## 4. RAG / Knowledge Quality

### 4.1 UE version drift — docs/code/release-notes say different things — **HIGH**

**What goes wrong:** Index says "use `UGameplayStatics::SpawnObject`" (docs phrasing from 5.4); in 5.7 the signature changed; agent confidently tells user to use the old API; code doesn't compile; user loses trust.

**Warning signs:**
- RAG answers with no version tag.
- User reports "that function doesn't exist in my version."
- Divergence between official docs, header comments, and Unreal Slackers answers.

**Prevention:**
1. **P3:** **Every indexed chunk is version-tagged** at ingest time (source URL tells us UE 5.4 vs 5.5 vs 5.6 vs 5.7; header comments come with a commit hash). Metadata includes `ue_min_version`, `ue_max_version`.
2. **P3:** Retrieval is constrained to the user's active UE version. Project.uproject is read to determine version; RAG query filters.
3. **P3:** Answer formatter must cite the chunk's version tag: "Per UE 5.6 docs, ..."
4. **P3:** **Pre-execution validation** — before the agent runs code/spawns a Blueprint node, validate the symbol exists in the user's version (using Unreal Reflection, or a local symbol index generated from the user's install). If invalid, ask for confirmation rather than executing.
5. **P3:** When docs contradict code, code wins — record a divergence ticket for human triage.

**Phase:** P3 + P4 (pre-execution validation lives in the actions layer)
**Severity:** HIGH — hallucinated APIs destroy trust fast.

---

### 4.2 YouTube transcript noise — **MEDIUM**

**What goes wrong:** Auto-generated captions transcribe "Niagara" as "an agora" 40% of the time; "Cascade" as "casket"; timecodes are off by 2–5 seconds. RAG retrieves this garbage; agent answers with "to emit particles, use the Agora system."

**Warning signs:**
- RAG answers containing misspelled UE terms.
- Low retrieval precision on UE-specific vocabulary queries.
- Users reporting "that's not a real UE feature."

**Prevention:**
1. **P3:** **Whitelist-only channels** for the YouTube corpus: known quality creators (Epic official, Unreal Sensei, Unreal University, Prismatica Dev, Ben Cloward, Unreal Sensei, etc.). No generic firehose.
2. **P3:** Post-process transcripts through a domain-spellchecker: a dictionary of UE terms (Niagara, Lumen, Nanite, ControlRig, MetaSounds, etc.) with fuzzy correction.
3. **P3:** Tag transcript chunks at lower trust weight (e.g., `source_weight: 0.5`) vs official docs (`1.0`); retrieval re-ranker prefers higher-weight sources.
4. **P3:** Require at least one official-docs chunk in the top-3 retrieved for every answer; if none, answer "I don't know" or fall back to asking the subscription LLM without RAG grounding.
5. **P3:** Periodically re-ingest — YouTube captions improve over time as channels add manual captions.

**Phase:** P3
**Severity:** MEDIUM

---

### 4.3 Outdated tutorials poisoning the index — **HIGH**

**What goes wrong:** A 2021 tutorial teaching the UE 5.0 workflow for Chaos Destruction is in the corpus; it uses a GEV preset that was removed in 5.3; agent executes the steps; user's project breaks.

**Warning signs:**
- Tutorials from before the user's UE version dominating retrieval.
- Agent suggesting workflows with removed menu items.

**Prevention:**
1. **P3:** **Freshness filter** at ingest — tutorial metadata includes publication date; retrieval downranks anything > 2 major UE versions older than the user's active version.
2. **P3:** Explicit staleness flag surfaced in the UI: "This answer draws from a 2022 tutorial; portions may be outdated for 5.7."
3. **P3:** Human-curated "deprecated patterns" blocklist — if retrieval hits a known-deprecated chunk, show a warning banner.
4. **P3:** For workflow-style tutorials (multi-step), never auto-execute without user preview; "Here are 7 steps from this tutorial — want me to run them?" Always.

**Phase:** P3
**Severity:** HIGH

---

### 4.4 RAG citation hallucination — agent cites a node that doesn't exist — **HIGH**

**What goes wrong:** Agent says "add a SetComponentTickInterval node to your Niagara component." That node exists for ActorComponents but *not* on NiagaraComponent in 5.6. Agent confidently cites docs; docs don't actually say that.

**Warning signs:**
- Cited URL doesn't actually contain the claimed content.
- Node/API name not in the user's Reflection dump.
- "Source [1]" when there is no source.

**Prevention:**
1. **P3:** Citations are **verbatim quote + URL + version tag** from the retrieved chunk, not a paraphrase. If the quote doesn't support the claim, the answer is wrong — UI can show the quote next to the claim for user verification.
2. **P3:** **Symbol validation** before any action referring to a UE API — generate a symbol index from the user's installed UE headers at plugin install; agent's "use node X" / "call function Y" must pass through a symbol-exists check against that index.
3. **P3:** If retrieval confidence low (top-k scores below threshold), agent says "I don't have reliable docs on this in 5.7. Want me to try anyway based on general knowledge?" — explicit low-confidence mode.
4. **P3:** In-plugin "report a hallucination" button that captures conversation + retrieved chunks; feeds back into corpus curation.

**Phase:** P3 (retrieval) + P4 (symbol validation)
**Severity:** HIGH

---

### 4.5 Index size blowup vs Fab size cap — **MEDIUM**

**What goes wrong:** Corpus ingests UE docs × 4 versions × community × YouTube = 20 GB of chunks. Fab plugin size balloons. Or: index is pruned so aggressively that recall crashes.

**Warning signs:**
- Index grows super-linearly with corpus.
- Answer quality drops when corpus grows.

**Prevention:**
1. **P3:** **Tiered index:** small "always-on" index shipped with plugin (~50 MB, official docs only, top-ranked chunks); large "full" index downloaded on-demand per user; community corpus is server-side (if we ever do hosted RAG) or opt-in download.
2. **P3:** Deduplicate at ingest — near-duplicate tutorials share 80% content. Hash-and-cluster before indexing.
3. **P3:** Per-UE-version sub-indexes; user on 5.7 doesn't need the 5.4 subindex loaded.
4. **P3:** Compression: use quantized embeddings (int8), dense-only (skip BM25 shard or make it optional).
5. **P3:** Instrument index-size vs answer-quality and treat it as a tradeoff knob, not a fixed parameter.

**Phase:** P3
**Severity:** MEDIUM

---

## 5. Computer-Use → UE Asset Import Race Conditions

### 5.1 AssetRegistry hasn't seen the file yet — **HIGH**

**What goes wrong:** Meshy finishes, downloads `mesh.fbx` to `Content/NYRA/Imported/`; plugin calls `IAssetRegistry::GetAssetByObjectPath`; AssetRegistry hasn't rescanned that folder yet; returns null; plugin reports "import failed."

**Warning signs:**
- Intermittent "asset not found" after computer-use success.
- Works in editor after a manual Content Browser refresh.

**Prevention:**
1. **P4:** **Explicit rescan + wait** after any on-disk write: call `IAssetRegistry::ScanPathsSynchronous({path})` before lookup. Synchronous scan on a known small path is cheap.
2. **P4:** Prefer **in-memory import** via `UAssetImportTask` / `FReimportManager` — these register the asset into the AssetRegistry as part of import. Never "drop file + hope."
3. **P4:** Post-import verification: `GetAssetByObjectPath` + size sanity + material-count sanity before declaring success.
4. **P4:** Use a `FileSystemWatcher` + event-driven import pipeline, not polling.
5. **P5:** Computer-use "Meshy done" signal is the trigger; plugin owns the import (not computer-use).

**Phase:** P4 + P5 boundary
**Severity:** HIGH

---

### 5.2 Silent import failure — **HIGH**

**What goes wrong:** `UAssetImportTask` returns `bSuccess=false` but the agent's prompt says "Imported!" because it never checked. User sees an empty Content Browser folder.

**Warning signs:**
- "Done" messages with no visible asset.
- Import task warnings in Output Log that the plugin ignores.

**Prevention:**
1. **P4:** Import wrapper returns a typed result — `Success | PartialSuccess{warnings} | Failure{reason}`. Agent must handle each.
2. **P4:** Plug into UE's import callbacks (`OnAssetPostImport`) and aggregate warnings into user-visible status.
3. **P4:** Acceptance test after every import: spawn the imported mesh into the current level (or a hidden "preview" sublevel), ensure no crash, render a thumbnail. Only then "success."

**Phase:** P4
**Severity:** HIGH

---

### 5.3 UE crash on GPU-side processing during import — **HIGH**

**What goes wrong:** FBX imports fine; UE triggers material/mip/virtual-texture cooks; GPU driver crashes; UE hard-crashes; conversation state lost.

**Warning signs:**
- Editor crashes correlated with import of large / unusual meshes.
- Driver logs showing TDR (Timeout Detection & Recovery).

**Prevention:**
1. **P4:** **Import pipeline runs in a sub-editor process** where feasible (UE Commandlet or a detached Python editor process). If it crashes, main editor survives.
2. **P4:** Pre-flight checks on imported file — poly count, texture resolution, shader complexity. If above thresholds, ask user before full import: "This mesh has 2M triangles; UE may stall. Reduce via Blender first?"
3. **P4:** Set a wall-clock limit on import; if exceeded, cancel and surface error.
4. **P4:** Every NYRA session persists state to disk every N seconds → conversation and job log survives editor crash.
5. **P4:** On editor restart, detect an interrupted NYRA job and offer to resume.

**Phase:** P4
**Severity:** HIGH

---

### 5.4 Reimport loops and duplicate assets — **MEDIUM**

**What goes wrong:** Agent didn't see import completion; retried; now `NYRA_Tree.fbx` and `NYRA_Tree_1.fbx` exist. Next retry creates `_2`. User's Content Browser turns to garbage.

**Warning signs:**
- Multiple suffixed duplicates of the same logical asset.
- Storage growing fast.

**Prevention:**
1. **P4:** **Idempotent import keyed by a stable ID** — every agent-initiated import carries a UUID stored in the asset's `AssetUserData`. Re-import with same UUID updates, doesn't duplicate.
2. **P4:** Before creating a new asset, check if UUID exists; if so, update existing.
3. **P4:** Explicit "replace" vs "new version" user choice for conflicts; no silent overwrites.
4. **P4:** Lock file / semaphore per logical asset to prevent concurrent imports of the same thing.

**Phase:** P4
**Severity:** MEDIUM

---

## 6. Video Analysis for Reference-Video → Matched-Shot (Launch Demo)

### 6.1 Keyframe sampling misses key moments — **HIGH**

**What goes wrong:** Naive 1-fps uniform sample; key cinematic beat happens between frames; agent's understanding of the shot is based on boring in-between frames. Resulting UE shot is wrong.

**Warning signs:**
- Matched shot lighting/composition differs obviously from reference.
- Important props / characters absent from analysis.

**Prevention:**
1. **P6:** **Scene-cut detection first** (e.g., PySceneDetect) — sample at least 2 frames per detected shot, including the midpoint of each shot.
2. **P6:** Saliency-weighted extra samples — frames with peak motion / peak brightness change get extra coverage.
3. **P6:** User-confirmable timeline — "I extracted these 8 key frames; add or remove any before I analyze" — trust-through-transparency.
4. **P6:** For the launch demo specifically, accept a curated input (a 10–30 second clip, single shot) rather than "paste any YouTube link." Bound the problem.

**Phase:** P6
**Severity:** HIGH (for the launch demo; the demo is the marketing wedge)

---

### 6.2 Camera motion misinterpretation (dolly vs truck vs pan) — **HIGH**

**What goes wrong:** Reference is a camera truck-left; NYRA reads it as a pan-left; UE Sequencer camera rotates in place instead of translating; the match fails the "eye test."

**Warning signs:**
- Parallax wrong in output.
- Objects in foreground moving at same rate as background.

**Prevention:**
1. **P6:** Use **optical flow + monocular depth estimation** (MiDaS / Depth Anything), not raw pixel diff. Parallax between depth layers reveals translation vs rotation.
2. **P6:** Classify camera moves into a canonical taxonomy: static, pan, tilt, roll, dolly, truck, pedestal, zoom, handheld. Agent reasons over labels, not pixels.
3. **P6:** Surface the detected camera move to the user before executing: "I think this is a truck-left + slight tilt-up. Confirm?" Give an override dropdown.
4. **P6:** Fall back gracefully — if confidence low on move classification, default to "static frame, re-create composition" rather than guessing wrong.

**Phase:** P6
**Severity:** HIGH (launch demo quality)

---

### 6.3 Lighting / exposure / tonemapping mismatch — **HIGH**

**What goes wrong:** Reference is filmed with an ARRI + LUT applied; NYRA analyzes RGB directly and concludes "scene is lit with a warm 3200K key at 45 degrees." UE output looks nothing like reference because LUT was doing the work.

**Warning signs:**
- NYRA's lighting plan replicates the LUT's look, not the physical lighting.
- Exposure off by 2+ stops.

**Prevention:**
1. **P6:** Encode that lighting analysis is *approximate inverse*. Surface this uncertainty: "Reconstructed lighting (best-effort from tonemapped footage):"
2. **P6:** Extract lighting intent at **semantic level**, not physical: "key light from upper-left, cold fill from right, strong rim." Let UE artists refine.
3. **P6:** Provide a "match tonemapping" post-process step in UE — user can toggle between "physically plausible" and "looks like reference" outputs.
4. **P6:** Acknowledge in docs and demo: "NYRA matches *mood and composition*; color-grading pass is on you."

**Phase:** P6
**Severity:** HIGH (demo quality) / MEDIUM (day-to-day)

---

### 6.4 Copyright of reference videos — **HIGH**

**What goes wrong:** User pastes a YouTube link to a copyrighted film trailer. NYRA downloads the video, sends frames to Claude (Anthropic), stores locally. This is potentially infringing reproduction and distribution; Anthropic may refuse or flag; content rights-holders may complain.

**Warning signs:**
- YouTube API/yt-dlp blocked or rate-limited.
- Claude refusing to analyze content that looks copyrighted.
- DMCA notices.

**Prevention:**
1. **P0:** Legal review of "fair use for analysis" — US fair use has leeway for transformative analysis + educational use; other jurisdictions less so. Document our stance.
2. **P6:** **Disclaimer at paste time:** "By providing this video, you confirm you have the right to analyze it for your creative work. NYRA does not store or redistribute the video."
3. **P6:** **Ephemeral processing** — downloaded video deleted immediately after frame extraction; only low-res keyframes retained for the session. Nothing persisted by default.
4. **P6:** Do not upload full video to Anthropic; extract keyframes locally first; send only frames relevant to analysis.
5. **P6:** Log + surface to user which assets left their machine ("I sent 8 keyframes to Claude for analysis").
6. **P6:** Block known-copyrighted domains/patterns from being auto-ingested? (too aggressive — user responsibility).
7. **P0:** Terms of Service for NYRA must place responsibility for input content on the user.

**Phase:** P0 (legal + ToS) + P6 (technical)
**Severity:** HIGH

---

## 7. Project Management / Scope

### 7.1 Solo-builder scope creep — **BLOCKING (for shipping in 6–9 months)**

**What goes wrong:** PROJECT.md's Active list is ambitious (4 UE versions × Claude + Codex + Gemma × 5 external tools × launch demo × RAG × Fab + direct distribution). Solo, 6–9 months. Every feature attracts a "one more thing" instinct. Project never ships.

**Warning signs:**
- Phase durations slipping by > 30%.
- New items added to Active without removing old ones.
- "It's almost done" spanning multiple weeks.

**Prevention:**
1. **Cross-cutting:** **Pre-defined scope cut lines per phase.** Every phase entering planning has a "minimum shippable" tier and a "stretch" tier; if by day X of the phase the stretch isn't clearly reachable, it's cut *before* it's half-done. This is a planning discipline, not a reactive one.
2. **Cross-cutting:** **One launch demo** drives the roadmap (reference-video → matched UE shot — per PROJECT.md). Every feature is evaluated against "does this make the launch demo work?" Non-launch-demo features are P-lowered.
3. **P7:** **v1 is Claude-only, not Claude+Codex.** Codex is nice-to-have. Ship with one subscription, add the other post-launch. Halves integration and legal work.
4. **P7:** **v1 is Windows-only** (per PROJECT.md — keep this firm).
5. **Cross-cutting:** Weekly 1-hour retrospective with self: "What's in Active that's not on the critical path to launch demo + reviews?" Be ruthless.
6. **P3/P4:** **Feature count cap per phase** (e.g., "Phase 3: RAG ships with UE5.6 only, official docs only, one creator channel — not all four UE versions × five sources"). Expand post-launch.

**Phase:** Cross-cutting (scope is a discipline, not a feature)
**Severity:** BLOCKING — this is the #1 reason solo-built ambitious projects die.

---

### 7.2 Demo-driven development trap — **HIGH**

**What goes wrong:** NYRA optimizes for the 90-second Fab trailer: cherry-picked reference image, pre-warmed Meshy account, cached Claude responses, scripted camera moves. Trailer looks incredible. Real user tries the same thing on day one — 5-minute wait, Meshy quota hit, imports fail, shot looks nothing like reference. Reviews crater.

**Warning signs:**
- Demo path uses cached / pre-generated artifacts.
- First-install users fail on the exact demo workflow.
- Internal tests done on the demo reference, not random references.

**Prevention:**
1. **Cross-cutting:** **Random-reference daily test.** Every day of P5/P6, run the flagship demo on a *randomly chosen* reference image/video (not the demo reference). If it fails, that's the top-priority bug.
2. **P7:** **"First-install cold-start" test scripted as a release gate.** Uninstall plugin, uninstall Claude Code cache, uninstall browser profile, re-install everything, run demo. If it doesn't work clean, don't ship.
3. **Cross-cutting:** **No "demo mode"** feature flag. The exact code path the demo uses is the exact code path users use. If we can't make the real path demo-quality, we cut the demo.
4. **P7:** Trailer says "typical result" and shows a real, time-lapsed run (with the 5-minute Meshy wait visible), not a cherry-picked one.
5. **P7:** Provide a bundled "try this first" reference image/prompt in the plugin, pre-validated to work — so user's first experience is a win even if their own references are harder.

**Phase:** Cross-cutting + P7
**Severity:** HIGH — trust is hard to regain after a first-day disappointment.

---

### 7.3 "Wait for technology to mature" paralysis — **MEDIUM**

**What goes wrong:** Claude computer-use is flaky today; UE NNE is preview-state; Gemma 4B is good-not-great. Builder waits for each to hit "ready" — months slip, competitors ship, market closes.

**Warning signs:**
- Roadmap gates on upstream releases not in our control.
- "We'll start once X GAs" repeated in retro.

**Prevention:**
1. **Cross-cutting:** **Architecture for substitution, not commitment.** Computer-use is behind an interface; swap for Playwright/UIA/headless-browser when computer-use fails. NNE behind same interface as ONNX Runtime. Gemma behind same interface as any ollama-compatible model.
2. **P5:** Write and merge the fallback *before* shipping the primary. If Claude computer-use breaks for a tool, NYRA auto-falls-back to Playwright.
3. **Cross-cutting:** Ship the product **without** immature technology if it's not ready. Text-chat + RAG + UE-native actions alone is a product (matches Aura, Nwiro). Computer-use is the differentiator but not the minimum.
4. **Cross-cutting:** Every month, re-evaluate maturity of each dependency; lock a "tech cut date" (e.g., "if Claude computer-use isn't stable by month 5, P6 uses Playwright for Meshy").

**Phase:** Cross-cutting
**Severity:** MEDIUM

---

### 7.4 Competitor launches the same demo first — **MEDIUM**

**What goes wrong:** Aura (Ramen VR) or Nwiro ships a "reference-video → UE shot" demo three weeks before NYRA. NYRA's launch wedge dulls; traffic halves; Fab reviews compare unfavorably.

**Warning signs:**
- Competitor tweets/trailers teasing video-to-shot workflows.
- Slack/Discord community chatter about "they're doing X too."

**Prevention:**
1. **Cross-cutting:** **Public changelog + monthly devlog from month 1.** Builds a following *before* launch; even if pipped on the demo, NYRA's audience is already attached.
2. **Cross-cutting:** Wedge is the **combination** (per PROJECT.md), not just the video demo. Messaging pivots to "BYO subscription + UE-native + orchestrates external tools" if the demo alone is commoditized.
3. **Cross-cutting:** Multi-wedge readiness — have 2–3 launch demos in the back pocket (e.g., "UE tutorial video → executable plan," per PROJECT.md) so if one lands mid, another can lead.
4. **P7:** Don't over-reveal before launch; tease without spec. Competitors can't directly copy what they haven't seen.

**Phase:** Cross-cutting + P7
**Severity:** MEDIUM

---

## 8. Legal / IP

### 8.1 Paid-course ingestion temptation — **HIGH**

**What goes wrong:** Builder adds "Ingest Udemy transcripts" feature (PROJECT.md explicitly excludes this). Course platforms' ToS forbid scraping; authors sue; Epic delists.

**Warning signs:**
- Feature requests to index paid courses.
- Scope creep into "the user chose to upload it."

**Prevention:**
1. **P0/P3:** **Hard technical block**: NYRA's ingestion pipeline refuses URLs matching known paid-course domains (Udemy, Skillshare, Unreal Fellowship, Domestika, ArtStation Learning, etc.). Log attempts.
2. **P0/P3:** User's own local materials (PDFs, mp4 on their disk) *are* allowed — indexed **on their machine only**, never sent to any NYRA-controlled service. Documented clearly.
3. **P0:** ToS explicitly states NYRA does not encourage or enable ToS violations of third-party educational platforms.
4. **Cross-cutting:** Keep this in PROJECT.md Out of Scope permanently; review at every milestone boundary that it hasn't crept.

**Phase:** P0 + P3
**Severity:** HIGH

---

### 8.2 Trademark: is "NYRA" clear? — **HIGH**

**What goes wrong:** "NYRA" is a short name; likely collisions with existing trademarks in software / gaming / AI. Post-launch, a C&D arrives; rebrand costs Fab listing momentum + SEO.

**Warning signs:**
- USPTO / EUIPO / Madrid registrations for "NYRA" in Class 9 (software) or 42 (SaaS).
- Existing domain (nyra.ai, nyra.io, nyra.com) owned by a related business.
- Google search returning same-sector products.

**Prevention:**
1. **P0:** **Trademark screening search** before any public mention: USPTO TESS, EUIPO, UK IPO, WIPO Global Brand Database. Search Class 9 + 42 + 41 (entertainment software).
2. **P0:** Domain availability check (nyra.ai, nyra.dev, getnyra.com, trynyra.com, etc.). Acquire at least one.
3. **P0:** **GitHub org + Fab creator name + X handle** reserved same day as domain.
4. **P0:** If screening finds any close collision, pick a backup name *before* any public marketing.
5. **P0:** Budget for a TM registration post-launch (~$750 USPTO filing) to lock in.

**Phase:** P0
**Severity:** HIGH

---

### 8.3 Liability when NYRA generates commercially-published content — **HIGH**

**What goes wrong:** User ships a game with an asset NYRA generated via Meshy; that asset contains recognizable IP (training data leakage); rights-holder sues the user; user sues NYRA.

**Warning signs:**
- NYRA-generated assets that look like recognizable characters/logos.
- User asking "can I sell games made with NYRA?"

**Prevention:**
1. **P0:** **ToS + EULA** that: (a) transfers liability for generated content to the user, (b) disclaims warranty of non-infringement, (c) warns about third-party services' licensing (Meshy's ToS pass through to user).
2. **P0:** Surface in-editor at generation time: "Generated content via Meshy; review its license at meshy.ai/terms."
3. **P7:** FAQ section: "Can I sell work I made with NYRA? Yes — your creative work is yours, subject to the license of each underlying tool (Meshy, Substance, etc.)."
4. **Cross-cutting:** Never promise "safe for commercial use" without caveats. That promise is the one that lands a lawsuit on our desk.

**Phase:** P0
**Severity:** HIGH

---

### 8.4 Studio / NDA data handling — on-device story — **HIGH**

**What goes wrong:** Studio installs NYRA; an employee uploads an unreleased character concept; NYRA sends it to Claude for analysis; it leaks (via Anthropic training, or via NYRA telemetry). Studio fires the user; NYRA banned from enterprise.

**Warning signs:**
- Enterprise inquiries asking "where does my data go?"
- Lack of a clear data-flow diagram.

**Prevention:**
1. **P2:** **Privacy Mode** first-class: toggle in plugin that forces Gemma-4B-local for all steps; blocks any network egress (except to user's subscription CLIs, which flow to the user's account). No NYRA telemetry in privacy mode.
2. **P2:** **Data-flow diagram** published: where every byte goes, for every mode. "Your image → Claude" / "Your image → local Gemma" / "Your image → Meshy" — each with arrows.
3. **P2:** Opt-in telemetry only. Default OFF.
4. **P2:** No NYRA-operated server for Core flows. Everything is user-local or user-owned account.
5. **P7:** Enterprise docs / FAQ aimed at studio IT departments (ISO 27001-style questions).

**Phase:** P2 (architecture) + P7 (docs)
**Severity:** HIGH

---

### 8.5 Anthropic / OpenAI brand usage in Fab listing and UI — **MEDIUM**

**What goes wrong:** NYRA's Fab listing says "Claude by Anthropic integrated" with the Claude logo. Anthropic's brand guidelines (which exist) are strict on "integrated with" vs "uses." Letter arrives; Fab listing pulled for edits; launch momentum lost.

**Warning signs:**
- Use of logos without license.
- "Powered by Claude / OpenAI" marketing claims.

**Prevention:**
1. **P0:** Read Anthropic brand guidelines + OpenAI brand guidelines + Epic/Fab brand guidelines. Archive current versions.
2. **P7:** **Neutral language in Fab listing:** "Works with your Claude Pro/Max subscription" / "Compatible with Codex CLI." No logos unless expressly permitted.
3. **P7:** In-UI: text-only references ("Connect your Claude subscription"), no brand assets.
4. **P7:** If a partner program exists (Anthropic Partner Program, OpenAI Partnerships), apply — gives us legal-safe logo usage.
5. **P7:** "Claude" / "Codex" / "GPT" are trademarks; NYRA itself is a *distinct* product, not an Anthropic/OpenAI product. Make the disclaimer explicit.

**Phase:** P0 (research) + P7 (execution)
**Severity:** MEDIUM

---

## 9. UX Traps Specific to AI-in-Editor

### 9.1 Silent failure — agent says "done" but editor unchanged — **HIGH**

**What goes wrong:** Agent declares "I've added a point light at 300,0,200." User looks at viewport — nothing changed. Either the action never ran, or it ran in a different level, or a selection filter hid it.

**Warning signs:**
- Support tickets: "it says done but nothing happened."
- Agent completion logs with no corresponding UE transactions.

**Prevention:**
1. **P4:** **Every state-changing action is wrapped in a UE transaction** (`FScopedTransaction`), logged to NYRA's job log with before/after snapshots (actor count, asset count, Blueprint graph hash).
2. **P4:** "Done" message includes the **evidence**: "Spawned PointLight_NYRA_07 at (300,0,200); confirmed visible in viewport. [View in outliner]." With a button that focuses the actor.
3. **P4:** If the post-condition check fails, action is reported as failed, not succeeded.
4. **P4:** Never report "done" on pure planning steps; distinguish "plan" vs "executed."

**Phase:** P4
**Severity:** HIGH

---

### 9.2 Undo / reversibility — agent spawned 200 actors — **HIGH**

**What goes wrong:** Agent executes a 40-step scene-build. User doesn't like the result. Hits Ctrl+Z. Undoes only the last transaction. Now level has 180 unwanted actors; cleanup is manual.

**Warning signs:**
- Large number of NYRA-tagged actors after a session.
- Users asking "how do I undo NYRA?"

**Prevention:**
1. **P4:** **Every NYRA agent session is wrapped in a single "super-transaction."** Multiple `FScopedTransaction` entries coalesced under a parent "NYRA: [session summary]" that Ctrl+Z undoes as one unit.
2. **P4:** NYRA-created assets are **tagged** (component tag or AssetUserData) — "Clean up NYRA session" menu option removes all tagged items.
3. **P4:** Pre-action "preview mode" — agent describes what it's about to do, shows a diff; user confirms before actions execute. Mandatory for destructive ops (delete, overwrite).
4. **P4:** Before-state snapshot — for big scene changes, snapshot the level to a temp file; offer "Revert NYRA changes" even across restarts.
5. **P4:** Session log persisted: user can replay or undo the last N NYRA sessions.

**Phase:** P4
**Severity:** HIGH

---

### 9.3 Streaming status UX — 90-second spinner — **MEDIUM**

**What goes wrong:** Meshy takes 3 minutes, Claude is planning, RAG is searching. User stares at a spinner. Assumes the plugin is frozen. Kills UE. Loses state.

**Warning signs:**
- Users reporting "it froze."
- Force-kills during NYRA activity.

**Prevention:**
1. **P4/P5:** **Multi-stage progress UI** — every step emits a live status ("Querying Meshy... 00:42 elapsed, estimated 2m 18s remaining"). Never generic "Working…"
2. **P4/P5:** Stream partial results — LLM token stream visible; tool-use decisions shown as they're made; RAG citations appearing as they're retrieved.
3. **P4/P5:** Timer-based nudges — if a step exceeds expected duration, show "Still working — Meshy queue is longer than usual. [Cancel]" at 2× expected.
4. **P4/P5:** "Keep me posted" option — user can Alt-Tab out; NYRA toast / system notification when done.
5. **P5:** For computer-use specifically, show a thumbnail of the current screenshot so user sees "oh, the agent is on Meshy's login page."

**Phase:** P4 + P5
**Severity:** MEDIUM

---

### 9.4 Trust-through-transparency — show-before-do — **HIGH**

**What goes wrong:** Agent autonomously does 20 things. User doesn't understand how they happened. No way to audit or learn. Agent also did something wrong among the 20. User doesn't know which. Trust collapses.

**Warning signs:**
- Users asking "why did it do that?"
- Users disabling auto-run, forcing single-step mode.

**Prevention:**
1. **P4/P5:** **Plan preview before execution** — agent outputs the full step list *before* executing; user can approve, edit, or reject. This is the default.
2. **P4/P5:** "Trust levels" per tool — user sets each tool to Auto / Ask / Never. Destructive ops (delete, overwrite, upload) default to Ask.
3. **P4/P5:** Inline "why?" for each action — hover shows retrieval source + reasoning.
4. **P4/P5:** Post-session summary — "Here's what I did: [12-item list]. Review / undo any?"
5. **P4/P5:** Conservative defaults — ship with Ask-heavy settings; users opt into auto-run per tool as trust builds.

**Phase:** P4 + P5
**Severity:** HIGH — trust is the currency; losing it is worse than losing a feature.

---

## Phase-Specific Warnings Summary

| Phase Topic | Likely Pitfalls | Mitigation |
|-------------|-----------------|------------|
| **P0 Legal/ToS gate** | 1.1, 1.2, 3.1, 3.5, 6.4, 8.1, 8.2, 8.3, 8.4, 8.5 | Front-load all legal/ToS research; do not write code until gate clears. Get written clarifications from Anthropic + OpenAI + Epic. |
| **P1 Subscription bridge** | 1.3, 1.4, 1.5, 1.6 | Structured I/O only (MCP/JSON). Version-pin. Health check. Checkpointing. API-key fallback designed in, not bolted on. |
| **P2 Plugin shell + Fab packaging** | 3.2, 3.3, 3.4, 3.6, 8.4 | Four-version CI from day one. EV code-signing budgeted. Models hosted not bundled. Privacy mode first-class. |
| **P3 RAG / knowledge** | 4.1, 4.2, 4.3, 4.4, 4.5, 8.1 | Version-tagged chunks. Symbol-validation. Whitelist creators. Tiered index. Hard block on paid-course domains. |
| **P4 UE-native actions** | 4.4, 5.1, 5.2, 5.3, 5.4, 9.1, 9.2, 9.3, 9.4 | Transactional boundary per session. Idempotent imports. Plan-before-execute. AssetRegistry rescan on every write. |
| **P5 Computer-use orchestration** | 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 9.3, 9.4 | Canary suite. Post-condition verification. Headless browser for web targets. Idempotent tool-calls. Trust-level UI. |
| **P6 Reference-driven workflows** | 6.1, 6.2, 6.3, 6.4 | Scene-cut sampling. Canonical camera taxonomy. Ephemeral video processing. Curated demo inputs. |
| **P7 Distribution** | 1.6, 3.1, 3.4, 7.2, 7.4, 8.5 | Fallback direct-dist path. Cold-start release gate. Neutral brand language. Public devlog from month 1. |
| **Cross-cutting** | 1.1, 1.2, 3.1, 7.1, 7.2, 7.3, 7.4, 8.1, 8.3 | Scope cut-lines per phase. Architecture for substitution. Single launch demo drives roadmap. v1 is Claude-only, Windows-only. |

---

## Top 5 "Must-Not-Skip" Pre-Code Actions (P0)

1. **Legal gate 1.1 + 1.2** — Anthropic + OpenAI ToS research and direct clarification emails. (Without this, the product's economic wedge may be illegal.)
2. **Legal gate 3.1** — Fab AI-plugin policy research + Epic creator support ticket.
3. **Legal gate 6.4 + 8.3** — NYRA ToS draft covering user-supplied content and liability for commercial output.
4. **Trademark gate 8.2** — Global TM screening on "NYRA" + acquire domains + reserve handles.
5. **Scope gate 7.1** — Lock the v1 cut-lines in writing before Phase 1 begins. Solo 6–9-month plans die from scope creep, not from technical hardship.

---

## Sources / Confidence

- PROJECT.md (read in full; HIGH confidence on stated scope and constraints).
- Training-data knowledge of UE5 plugin ABI behavior, AssetRegistry, FScopedTransaction patterns: HIGH confidence (well-documented Epic patterns).
- Training-data knowledge of Anthropic/OpenAI consumer terms & Claude Code / Codex CLI behavior: MEDIUM confidence — policies evolve; P0 legal gate must re-verify against live docs.
- Training-data knowledge of Fab AI-plugin policies (2024-present): LOW-MEDIUM confidence — Fab is a newer marketplace; policies less well-documented than old UE Marketplace. P0 gate must re-verify.
- Training-data knowledge of Claude computer-use Windows failure modes: MEDIUM confidence — UAC/SmartScreen/DPI patterns are well-documented Windows automation pitfalls; computer-use's specific failure modes less so.
- No live verification via WebSearch, Context7, or official docs was possible in this research session (tools denied). **P0 phase must re-verify every BLOCKING and HIGH item flagged here against live sources before committing to the roadmap.**
