# Roadmap: NYRA

**Defined:** 2026-04-21
**Core Value:** Turn a reference (image, video, prompt) into a finished Unreal Engine scene — without the user paying a new AI bill or leaving the editor.
**Quality Bar:** Every phase's success criteria are framed as "beats competitor X on dimension Y" (not parity) or are an architectural gate that unblocks a future competitor-beating feature. Parity is failure.
**Granularity:** standard (config), 9 phases justified — Phase 0 is a deliberately short non-code legal gate that runs in parallel with Phase 1, so effective code phases = 8, within the standard band.
**Timeline target:** Solo full-time builder, 6-9 months to Fab v1 launch.

---

## Phases

- [ ] **Phase 0: Legal & Brand Gate** - Clear Anthropic/Epic/Fab ToS and trademark before any subscription-driving code ships (runs in parallel with Phase 1 plugin-shell work)
- [ ] **Phase 1: Plugin Shell + Three-Process IPC** - UE C++ plugin + NyraHost Python sidecar + NyraInfer llama.cpp + Slate chat panel skeleton; Ring 0 "it can talk" (2/15 plans complete — 01-03 shipped 2026-04-21; 01-01 shipped 2026-04-21)
- [ ] **Phase 2: Subscription Bridge + Four-Version CI Matrix** - Claude CLI subprocess driving with Gemma fallback, transactional safety, safe-mode, console/log tools, EV code-signing, and UE 5.4/5.5/5.6/5.7 CI from day one
- [ ] **Phase 3: UE5 Knowledge RAG** - Bundled LanceDB index with version-tagged citations, symbol validation, Epic-release auto-updater, and Gemma multimodal offline fallback
- [ ] **Phase 4: Blueprint + Asset + Material + Actor Tool Catalog** - Deep UE-native Tool Catalog targeting Aura's Blueprint error-reduction benchmark; every tool transactional, every action post-condition-verified
- [ ] **Phase 5: External Tool Integrations (API-First)** - Meshy REST, ComfyUI HTTP, computer-use reserved for Substance Sampler + UE modal dialogs, with the computer-use reliability spike gating scope
- [ ] **Phase 6: Scene Assembly + Image-to-Scene (Fallback Launch Demo)** - Lighting authoring from NL/reference images, end-to-end DEMO-01 that beats Nwiro's fixed-library approach
- [ ] **Phase 7: Sequencer + Video-to-Matched-Shot (LAUNCH DEMO)** - Video reference analyzer + Sequencer automation delivering DEMO-02, the capability no competitor ships
- [ ] **Phase 8: Fab Launch Prep** - EV-signed installer, direct-download fallback, zero-config onboarding, Fab listing and AI-disclosure compliance

---

## Phase Details

### Phase 0: Legal & Brand Gate
**Goal**: Every legal and brand constraint that gates NYRA's economic wedge (subscription-driving) and Fab distribution is resolved in writing before subscription-driving code ships.
**Depends on**: Nothing (runs in parallel with Phase 1's legal-safe plugin-shell work per founder decision)
**Requirements**: PLUG-05
**Success Criteria** (what must be TRUE):
  1. Beats every competitor on defensible-wedge legitimacy: written clarification from Anthropic on record that driving the user's local `claude` CLI via subprocess is ToS-permitted — no competitor has this written answer because no competitor attempts subscription driving
  2. Beats every competitor on Fab-readiness risk: written Fab AI-plugin policy pre-clearance from Epic on record before Phase 2 subscription code ships, plus a direct-download fallback plan documented (Fab rejection stops being product-fatal)
  3. Architectural gate: NYRA trademark screening (USPTO/EUIPO/WIPO Class 9 + 42 + 41) is clean or a backup name is selected; domain + GitHub org + social handle reserved before any public devlog post
  4. Architectural gate: Gemma 3 4B license re-verified for commercial Fab redistribution, NYRA ToS+EULA draft covers generated-content liability (Meshy/ComfyUI passthrough) and reference-video copyright (ephemeral processing clause)
  5. Architectural gate: Brand guideline research for Anthropic, OpenAI, Epic/Fab archived — Fab listing uses neutral "works with your Claude subscription" language, no third-party logos without explicit partner-program permission
**Plans**: TBD

### Phase 1: Plugin Shell + Three-Process IPC
**Goal**: The three-process architecture is proven end-to-end on UE 5.6 — UE editor hosts a Slate chat panel that round-trips to NyraHost over loopback WebSocket, NyraHost spawns NyraInfer (llama.cpp/Gemma) on demand, and nothing Phase 1 builds depends on Phase 0 legal clearance (plugin shell is legal-safe scaffolding).
**Depends on**: Nothing (runs in parallel with Phase 0)
**Requirements**: PLUG-01, PLUG-02, PLUG-03, CHAT-01
**Success Criteria** (what must be TRUE):
  1. Beats every OSS MCP plugin (chongdashu, flopperam, kvick-games, remiphilippe) on editor stability: NyraHost runs out-of-process; a NyraHost crash or Gemma OOM never takes UnrealEditor.exe down. OSS plugins that ran MCP in-process report exactly this instability — NYRA does not.
  2. Beats every competitor on chat-panel foundation depth: dockable Slate panel supports streaming tokens, markdown, code blocks, image/video/file attachments, per-conversation history persisted under project `Saved/NYRA/` — Aura's polished panel is the bar, NYRA meets it and adds multi-modal attachments from day one
  3. Architectural gate: loopback WebSocket (UE↔NyraHost) + localhost HTTP (NyraHost↔NyraInfer OpenAI-compatible) IPC is stable over 100 consecutive round-trips on UE 5.6 with editor responsive during streaming; this gate unblocks Phase 2's subscription driving
  4. Architectural gate: NyraInfer spawns on demand with Gemma 3 4B IT QAT Q4_0 GGUF loaded over llama.cpp (or auto-detected Ollama), exposed as OpenAI-compatible endpoint on localhost — proves the offline fallback binary path before Phase 2 wires the router to it
  5. Architectural gate: plugin builds as two modules (`NyraEditor` editor-only, `NyraRuntime` minimal runtime stub) with `.uplugin` descriptor valid on UE 5.6; no Fab packaging yet but the layout is Fab-ready
**Plans**: TBD
**UI hint**: yes

### Phase 2: Subscription Bridge + Four-Version CI Matrix
**Goal**: NYRA's economic wedge — subprocess-driving the user's Claude Code CLI — is live end-to-end with graceful Gemma fallback on rate-limit or auth failure, the four-version CI matrix (UE 5.4/5.5/5.6/5.7) is enforcing compat from day one, and every agent mutation is transactional with safe-mode plan-preview as default.
**Depends on**: Phase 0 (legal clearance required before any subscription-driving code ships), Phase 1 (three-process IPC working)
**Requirements**: PLUG-04, SUBS-01, SUBS-02, SUBS-03, CHAT-02, CHAT-03, CHAT-04, ACT-06, ACT-07
**Success Criteria** (what must be TRUE):
  1. Beats every competitor on economics (Aura/Telos, CoPilot, Ludus all bill for inference): Claude Code CLI subscription driving verified end-to-end on Windows via `claude -p --output-format stream-json --verbose` with `--mcp-config` injecting NYRA's MCP server — subscription connection status UI (CHAT-02) makes the no-new-bill wedge visible to users on first run
  2. Beats every competitor on enterprise-readiness: graceful fallback to Gemma on 429/auth-drift with clear user-facing status, AND Privacy Mode toggle (Gemma-only, all egress blocked except user's own CLI) — no competitor ships offline fallback, this converts NDA/studio prospects that bounce off cloud-only tools
  3. Beats Aura/CoPilot on trust-through-transparency: CHAT-04 safe-mode/dry-run is the DEFAULT — every agent mutation outputs its tool-call sequence before execution; CoPilot has preview mode and Aura's Dragon Agent does plan-then-execute, NYRA ships plan-first by default on day one of actions
  4. Beats CoPilot/Aura on undo safety: every agent mutation wrapped in `FScopedTransaction` under a per-session super-transaction — Ctrl+Z rolls back an entire NYRA session as one unit, not step-by-step. Cancel-button cleanly unwinds in-flight subprocesses.
  5. Architectural gate (non-negotiable per PITFALLS §3.3): four-version CI (UE 5.4/5.5/5.6/5.7) green on day one of this phase — no version-specific code merges without all four passing. `NYRA::Compat::` shim covers Slate/Material/Sequencer/Blueprint drift hotspots with empirical matrix test. This prevents the ABI-drift retrofit trap (3-5x cost late).
  6. Architectural gate: EV code-signing cert acquired and applied to plugin DLL, NyraHost.exe, NyraInfer.exe — SmartScreen clears on first install (non-EV has a 30-day reputation window that poisons launch). Router is designed multi-backend (SUBS-03) so Codex drops in for v1.1 without refactor. Console-command (ACT-06) and Output/Message Log tools (ACT-07) ship here as universal introspection primitives every later phase uses.
**Plans**: TBD
**UI hint**: yes

### Phase 3: UE5 Knowledge RAG
**Goal**: NYRA answers any "how do I do X in UE5" question with verbatim-quote citations tagged to the user's UE version, validates cited symbols against the user's installed UE headers before any action, and refreshes its index same-day or next-day after Epic ships a new UE version.
**Depends on**: Phase 2 (agent router + Gemma fallback + CI matrix)
**Requirements**: KNOW-01, KNOW-02, KNOW-03, KNOW-04
**Success Criteria** (what must be TRUE):
  1. Beats Nwiro and CoPilot on knowledge freshness: day-of support for new UE releases via a GitHub-Releases index-build pipeline triggered on Epic release tags — no competitor publishes day-of UE version support. Tested with simulated UE release (5.7 → 5.8 stub).
  2. Beats Aura/CoPilot on answer trustworthiness: every answer cites its source with a version tag AND a verbatim quote from the retrieved chunk (not a paraphrase) — and before any action touching a UE API, a symbol-validation step confirms the referenced symbol exists in the user's installed UE version. Hallucinated-API rate measured against a golden-set Q&A suite with target <2% (competitor baseline: agent-on-vanilla-LLM hallucination is ~15-30% on UE-specific APIs per FEATURES).
  3. Beats CoPilot/Ludus on offline/privacy use: KNOW-04 Gemma 3 4B multimodal answers docs Q&A and baseline asset search when Claude is unavailable (offline, rate-limited, privacy mode) — no competitor ships offline Q&A, so this is a first-class enterprise differentiator.
  4. Architectural gate: bundled LanceDB index ships <200 MB tiered (50 MB bootstrap bundled in plugin + full index downloaded on first run), with BGE-small-en-v1.5 ONNX embeddings (133 MB, MIT license). Corpus is license-clean only: UE5 official docs (5.4-5.7), Blueprint node reference, C++ API headers, Epic forum posts, community transcripts with attribution — hard block on paid-course domains (Udemy, Skillshare, Unreal Fellowship, Domestika, ArtStation Learning).
**Plans**: TBD

### Phase 4: Blueprint + Asset + Material + Actor Tool Catalog
**Goal**: NYRA ships a deep, reliable UE-native Tool Catalog — Blueprint graph read/write/rewire, Blueprint debug-and-fix loop, asset search, actor CRUD, material-instance operations — where every tool is transactional, idempotent, and verified post-condition. This is the phase that beats Aura/Telos on Blueprint reasoning.
**Depends on**: Phase 3 (symbol validation from RAG is the pre-execution gate)
**Requirements**: ACT-01, ACT-02, ACT-03, ACT-04, ACT-05
**Success Criteria** (what must be TRUE):
  1. Beats Aura/Telos 2.0 on Blueprint reasoning accuracy: compile-success rate on a canned suite of broken Blueprints exceeds Aura's published 25× error-reduction baseline (target >30× or documented ceiling). ACT-01 reads K2 graphs as structured JSON and writes back diffs; ACT-02 closes the debug loop (intercept error → plain-English explanation → diff → one-click apply → recompile → iterate until clean).
  2. Beats Ultimate Engine CoPilot on tool depth (not breadth): 20-30 deep tools with transaction support, undo, pre-condition validation (symbol validation from KNOW-02), and post-condition verification — each measured for per-tool reliability. CoPilot's ~1,050 actions are breadth-first Python wrappers; NYRA's depth-per-tool reliability metric is documented and measurably higher on the canned suite.
  3. Beats Nwiro on asset reuse workflow: ACT-03 fuzzy asset search over `FAssetRegistryModule` (name/tag/class, structured queries) means scene assembly prefers the user's own library before generating new assets — Nwiro's one-prompt scene uses their fixed Leartes catalog; NYRA uses the user's own assets first, generating only what's missing.
  4. Beats every competitor on silent-failure avoidance: ACT-04 actor CRUD and ACT-05 material-instance ops both emit evidence with every "done" message (actor name + world location + viewport-visible confirmation; parameter name + before/after value + applied-to-actor list). Every state change wrapped in `FScopedTransaction` under the session super-transaction from Phase 2.
**Plans**: TBD

### Phase 5: External Tool Integrations (API-First)
**Goal**: NYRA reaches outside UE to drive Meshy (REST), ComfyUI (local HTTP), and — where no API exists — Substance 3D Sampler and UE modal dialogs via Claude computer-use (`computer_20251124`, Opus 4.7). API-first per founder directive: computer-use is a scalpel, not a hammer. Computer-use reliability spike gates final phase scope.
**Depends on**: Phase 4 (Asset Import Bridge + staging-manifest pattern is built on the Tool Catalog foundation)
**Requirements**: GEN-01, GEN-02, GEN-03
**Success Criteria** (what must be TRUE):
  1. Beats every competitor on cross-tool orchestration (no competitor reaches outside UE): GEN-01 Meshy REST API integration (image → 3D, job polling, download, auto-import as `UStaticMesh` with LODs and collision) and GEN-02 ComfyUI local HTTP (image-to-image workflows → auto-import as `UTexture2D` or Material inputs) both pass a random-reference canary daily on a representative Windows 11 machine — >85% success rate on the canned task suite.
  2. Beats every competitor on trust during external-tool work: GEN-03 Claude computer-use is confined to Substance 3D Sampler (no public API exists) and UE editor modal dialogs the Unreal API doesn't expose; always-visible agent-active HUD, confirmation gate on first action per session, Ctrl+Alt+Space keyboard-chord pause, DPI-safe UIA structural clicks. User never sees their cursor hijacked for a tool that has an API.
  3. Beats every competitor on reliability-per-failure: staging-manifest pattern (NyraHost writes `nyra_pending.json`, UE Asset Import Bridge reads it) means external tools never touch UE Content directly — every import is undoable and auditable. Idempotent tool-calls (UUID-keyed imports) prevent duplicate-asset accumulation that PITFALLS §5.4 flags as a common cross-tool failure.
  4. Architectural gate: computer-use reliability spike (20 scripted sessions against Substance Sampler + ComfyUI UI states) completes with >85% success rate on the canned task suite. If <85%, computer-use scope contracts to UE modal dialogs only and Substance Sampler is flagged for v1.1. This gate is mandatory before Phase 7 commits to DEMO-02.
**Plans**: TBD

### Phase 6: Scene Assembly + Image-to-Scene (Fallback Launch Demo)
**Goal**: NYRA delivers DEMO-01 end-to-end — user drops a reference image, NYRA assembles a matching UE scene (5-20 actors, one light setup, hero materials) preferring the user's own asset library first and generating missing hero assets via Meshy or missing textures via Substance/ComfyUI. This is the fallback launch demo if DEMO-02 slips.
**Depends on**: Phase 4 (Tool Catalog), Phase 5 (external tool integrations and staging manifest)
**Requirements**: SCENE-01, DEMO-01
**Success Criteria** (what must be TRUE):
  1. Beats Nwiro on scene-assembly style consistency: DEMO-01 reference-image-to-UE-scene prefers the user's own asset library first, generates missing hero assets via Meshy and missing textures via Substance/ComfyUI — Nwiro's one-prompt scene uses their fixed Leartes catalog (great quality, narrow style); NYRA's output is style-consistent with what the user already has, which is what indies and studios actually want.
  2. Beats Nwiro/CoPilot on lighting authoring: SCENE-01 handles directional/point/spot/rect/sky lights + SkyAtmosphere + VolumetricCloud + ExponentialHeightFog + PostProcessVolume + exposure curves from natural-language prompts ("golden hour", "harsh overhead volumetrics") AND from reference images ("match this image's mood") — Nwiro has cinematic presets, CoPilot has granular light actions, but "match this reference image's lighting mood" is unique to NYRA.
  3. Beats every competitor on first-install cold-start reliability: DEMO-01 passes the random-reference daily test from Phase 6 Day 1 — the exact code path the demo uses is the exact code path users run (no "demo mode" feature flag). A full uninstall + reinstall + run-demo pass is a release gate, not a checkbox.
  4. Architectural gate: DEMO-01 is the v1-launchable state — if DEMO-02 (Phase 7) slips past the 6-9 month budget, the launch reposts around DEMO-01 and still beats Nwiro via GEN-01+GEN-02+GEN-03 orchestration. This is the nuclear cut-line from FEATURES §v1-cut-line.
**Plans**: TBD
**UI hint**: yes

### Phase 7: Sequencer + Video-to-Matched-Shot (LAUNCH DEMO)
**Goal**: NYRA delivers DEMO-02 — user pastes a YouTube link or attaches a ≤10s mp4, NYRA extracts keyframes, infers composition + lighting + approximate geometry, and assembles a matching single-shot single-location UE scene with one CineCamera, key+fill lighting, sky+fog, and Sequencer-driven camera. This is the launch demo that no competitor ships.
**Depends on**: Phase 6 (scene assembly + lighting), Phase 5 (external tool orchestration for per-shot asset generation)
**Requirements**: SCENE-02, DEMO-02
**Success Criteria** (what must be TRUE):
  1. Beats every competitor by setting a new benchmark: DEMO-02 reference-video-to-matched-shot ships end-to-end — no competitor (Nwiro, Aura, CoPilot, Ludus, OSS MCP long tail) has this as of April 2026. NYRA's v1 benchmark (single-shot ≤10s clips with correct composition + lighting intent + camera motion taxonomy) is high enough that the next entrant cannot trivially match it.
  2. Beats Nwiro on Sequencer authoring: SCENE-02 creates `ULevelSequence`, adds CineCamera actors, sets keyframes on actor/camera/light/PPV parameters, and authors shot blocking from natural language ("slow push-in on the hero, then cut wide"). Nwiro has some cinematic composition but no strong NL shot-blocking.
  3. Beats every competitor on video-reference correctness: the Video Reference Analyzer uses scene-cut detection (ffmpeg `-vf "select='gt(scene,0.3)'"`) + semantic lighting extraction (not RGB analysis that misreads LUTs) + a canonical camera-move taxonomy (static/pan/tilt/dolly/truck — user-confirmable). PITFALLS §6.1-6.3 risks (keyframe miss, dolly-vs-truck confusion, LUT/RGB mismatch) are measurably below 15% failure rate on a diverse clip set.
  4. Beats every competitor on copyright safety during demo use: reference-video processing is ephemeral (yt-dlp download + extract keyframes + send ≤16 keyframes to Claude; delete full video from `/tmp` after run by default). Surfaced paste-time disclaimer; no full-video upload to Anthropic. PITFALLS §6.4 mitigations are visible in the log.
  5. Architectural gate (release gate): the "first-install cold-start" test passes — uninstall plugin + claude-code cache + browser profile, reinstall everything, run the launch demo on a random-reference clip (not the demo reference). If it fails clean on three consecutive random clips, Phase 8 does not start.
**Plans**: TBD
**UI hint**: yes

### Phase 8: Fab Launch Prep
**Goal**: NYRA ships to Fab with zero-config install, per-UE-version EV-signed binaries, AI-disclosure-compliant listing, and a direct-download fallback already live on nyra.ai (or temporary host) so a Fab rejection doesn't block launch. Every onboarding path ends in first-successful-action within 10 minutes of install.
**Depends on**: Phase 7 (launch demo), Phase 2 (EV cert + CI matrix), Phase 0 (Fab pre-clearance + brand guideline compliance)
**Requirements**: DIST-01, DIST-02, DIST-03, DIST-04
**Success Criteria** (what must be TRUE):
  1. Beats every competitor on first-install experience: DIST-04 zero-config install — user enables plugin in UE, runs `claude setup-token` once, and is operational. First-run wizard verifies Claude Code CLI, downloads Gemma on demand (user-consented progress UI), confirms computer-use readiness. Time-to-first-successful-action target <10 minutes from Fab download click; no competitor has been measured under 15 minutes on Windows.
  2. Beats every competitor on distribution resilience: DIST-02 direct-download fallback live on nyra.ai BEFORE Fab submission — signed installer is the escape hatch if Fab rejects. Competitors distributing Fab-only (most of them) are exposed to a single point of failure; NYRA is not.
  3. Beats every competitor on AI-plugin compliance: DIST-01 Fab listing passes on first submission — AI-disclosure copy compliant with Fab's 2026 AI-plugin policy (pre-cleared in Phase 0), per-UE-version binaries (5.4/5.5/5.6/5.7), launch demo trailer shot as a real time-lapsed run (no cherry-picking, no demo-mode flag — per PITFALLS §7.2 demo-driven-development trap prevention), screenshots, marketing assets.
  4. Beats every competitor on install trust: DIST-03 EV code-signing cert signs all binaries (plugin DLL per UE version, NyraHost.exe, NyraInfer.exe) — SmartScreen clears instantly on first install. Competitors without EV certs have a 30-day reputation window that poisons early reviews; NYRA's first-install experience does not warn users away.
  5. Architectural gate: public devlog has been shipping from Month 1 (cross-cutting PITFALLS §7.4 mitigation) so NYRA has a following before Fab submission — if a competitor pips the DEMO-02 reveal, NYRA's audience is already attached.
**Plans**: TBD
**UI hint**: yes

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 0. Legal & Brand Gate | 0/? | Not started | - |
| 1. Plugin Shell + Three-Process IPC | 2/15 | In progress | 01-03 (2026-04-21), 01-01 (2026-04-21) |
| 2. Subscription Bridge + Four-Version CI Matrix | 0/? | Not started | - |
| 3. UE5 Knowledge RAG | 0/? | Not started | - |
| 4. Blueprint + Asset + Material + Actor Tool Catalog | 0/? | Not started | - |
| 5. External Tool Integrations (API-First) | 0/? | Not started | - |
| 6. Scene Assembly + Image-to-Scene (Fallback Launch Demo) | 0/? | Not started | - |
| 7. Sequencer + Video-to-Matched-Shot (LAUNCH DEMO) | 0/? | Not started | - |
| 8. Fab Launch Prep | 0/? | Not started | - |

---

## Dependency Graph

Derived from FEATURES.md feature-dependency graph + ARCHITECTURE.md ring order. Each arrow means "downstream phase requires upstream phase complete."

```
Phase 0 (Legal)               Phase 1 (Plugin Shell + IPC)
     \                             /
      \                           /
       \                         v
        +------> Phase 2 (Subscription Bridge + CI Matrix) <--+
                       |                                       |
                       v                                       |
                Phase 3 (RAG / Knowledge)                      |
                       |                                       |
                       v                                       |
                Phase 4 (Tool Catalog: BP + Asset + Mat + Act) |
                       |                                       |
                       v                                       |
                Phase 5 (External Tools: API-first + CU spike) |
                       |                                       |
                       +------------+                          |
                                    v                          |
                             Phase 6 (Image -> Scene / DEMO-01) (fallback launch)
                                    |
                                    v
                             Phase 7 (Video -> Shot / DEMO-02) (LAUNCH DEMO)
                                    |
                                    v
                             Phase 8 (Fab Launch Prep) <-------+
                                                     (needs P0 pre-clearance + P2 CI/EV cert)
```

Critical path to LAUNCH DEMO (DEMO-02): Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7.

Parallel-safe:
- Phase 0 runs in parallel with Phase 1 (legal emails in flight while plugin scaffold is built).
- Phase 3 (RAG) and Phase 4 (Tool Catalog) share a boundary: symbol validation (KNOW-02) is a pre-execution gate for Phase 4 actions, so Phase 3 must land before Phase 4 completes. A solo dev can start Phase 4 tooling stubs during Phase 3 corpus work.

Nuclear fallback: if Phase 7 exceeds the 6-9 month budget, the launch repositions around Phase 6 (DEMO-01, image → scene). This is the documented fourth cut-line (see Kill Cut-Lines below).

---

## Kill Cut-Lines

Explicit drop order if the solo 6-9 month timeline runs tight. Codex (originally FEATURES's first cut) is already deferred to v1.1 by founder decision, so the cut-lines adjust one slot down.

**First cut (already made — founder decision):**
- SUBS-10 Codex CLI subprocess driving → deferred to v1.1. Router designed multi-backend so drop-in post-v1 requires no refactor. Rationale: halves integration + legal + auth surface; Codex CLI programmatic surface is LOW-confidence in STACK research.

**Second cut (if Phase 5-6 slips by >4 weeks):**
- Drop DEMO-02 multi-shot ambitions → v1 is single-shot ≤10s only (already the v1 scope, so this cut is about *not* attempting multi-shot ambition in Phase 7).
- Defer GEN-03 Substance 3D Sampler computer-use → v1.1. Computer-use scope contracts to UE editor modal dialogs only. Phase 6/7 demos substitute ComfyUI for PBR material generation.

**Third cut (if Phase 4-5 slips by >6 weeks):**
- Drop ACT-02 Blueprint debug auto-fix-and-apply → downgrade to "explain error only" (remove the one-click apply + re-compile loop). This is the PITFALLS §7.1-aligned scope-cut from FEATURES cut-line 3. ACT-01 (read/write/rewire) still ships.
- Defer D10 local project RAG (not in v1 scope) and D9 thumbnail-embedding asset search (not in v1 scope) — already out of scope, listed here for clarity.

**Fourth cut (nuclear — if Phase 7 is not clearly reachable by Month 7):**
- Drop DEMO-02 (reference video → matched shot) → defer to v1.1 post-launch.
- Reposition launch around DEMO-01 (image → scene) as the primary demo. Still beats Nwiro via GEN-01+GEN-02+GEN-03 orchestration (user's own library first + generate missing) — painful because DEMO-02 is the explicit wedge and the reason no competitor can trivially match NYRA, but shippable.
- This cut triggers a repositioning of the launch messaging and Fab listing copy; the devlog-from-Month-1 discipline (PITFALLS §7.4) keeps audience engaged for a v1.1 DEMO-02 reveal.

**Discipline:** every phase entering planning has a "minimum shippable" tier and a "stretch" tier; if by day X of the phase the stretch isn't clearly reachable, it's cut *before* it's half-done (PITFALLS §7.1). Cut-lines are enforced at weekly self-retrospectives: "what's in Active that's not on the critical path to DEMO-02 + Fab-launch-readiness?"

---

*Roadmap defined: 2026-04-21 after research synthesis + founder directives*
*Coverage: 34/34 v1 requirements mapped to phases (see REQUIREMENTS.md traceability)*
