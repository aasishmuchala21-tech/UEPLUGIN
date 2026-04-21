# NYRA Project Research Summary

**Project:** NYRA — AI agent plugin for Unreal Engine 5, distributed on Fab
**Domain:** In-editor AI assistant / agentic tool orchestrator for game development (Windows, UE 5.4–5.7)
**Researched:** 2026-04-21
**Synthesized:** 2026-04-21
**Overall Confidence:** MEDIUM-HIGH (stack HIGH on verified items; architecture MEDIUM; pitfalls MEDIUM-HIGH on legal; features MEDIUM on competitor specifics)

---

## Quality Bar (Founder Directive — Non-Negotiable)

**NYRA must be materially better than every competitor on every dimension it competes on. Parity is failure.**

Every phase goal, success criterion, and feature scope in this document is framed as "beats competitor X on dimension Y." If any phase only reaches parity, it is called out explicitly for re-scoping before execution. This directive applies to every downstream planning document.

Competitors: Nwiro (Leartes Studios), Aura/Telos 2.0 (Ramen VR), Ultimate Engine CoPilot (BlueprintsLab), Ludus AI, and the free OSS MCP server long tail (chongdashu, flopperam, kvick-games, remiphilippe).

### Quality-Bar Scorecard

| Dimension | Best Competitor & Their Bar | NYRA Target | Status |
|-----------|---------------------------|-------------|--------|
| Tool / action count | CoPilot ~1,050 actions (breadth-first wrappers over Python scripting) | 60–80 *deep* tools with full transaction support, undo, pre-condition validation, and post-condition verification. Depth-over-breadth argument: each NYRA tool is tested for reliability, not just enumerated. Document the argument with measurable reliability per-tool. | Needs explicit reliability-per-tool metric at Phase 4 gate |
| Blueprint reasoning accuracy | Aura Telos 2.0 claims 25× error reduction vs baseline | Beat Aura's published baseline on error reduction rate. Measurement: compile-success rate on a canned suite of broken Blueprints. Target: >30× or document why 25× is the ceiling. | Phase 4 milestone gate; requires a canned benchmark |
| Subscription economics | All competitors bill for inference — Aura/Telos, CoPilot, Ludus all run hosted APIs | "Bring your own Claude/Codex subscription" — no new bill. No competitor ships this. Defend the wedge: any feature that requires a NYRA-hosted API key must be explicitly justified as a v2+ trade-off, not a v1 shortcut. | Architecture enforces this: BYO-CLI driver path only in v1 |
| Reference-video → matched shot | No competitor ships this as of April 2026 | NYRA sets the benchmark. There is no competitor bar to beat — NYRA must make the benchmark high enough that the next entrant cannot trivially match it. V1: single-shot ≤10s clips with correct composition + lighting intent. V2: multi-shot, camera motion curves. | Phase 6 is the launch demo gate |
| UE knowledge freshness | Nwiro (scene-first) and Aura (Blueprint-focused) index docs; CoPilot relies on Python scripting surface | Day-of support for new UE releases (index pipeline triggers on Epic release tag). All answers version-tagged. Symbol validation against user's installed UE headers prevents hallucinated APIs. No competitor has published day-of UE version support. | Phase 3 index pipeline must include auto-trigger on Epic release |
| Cross-tool orchestration | No competitor drives external tools (Meshy, Substance, ComfyUI, Blender) — all stay inside UE | NYRA orchestrates the full asset pipeline: UE editor + Meshy + Substance Sampler + ComfyUI + Blender, all via Claude computer-use or API. Result is delivered back as native UE assets. No competitor does this. NYRA sets the benchmark. | Phase 5 computer-use gate |

---

## Executive Summary

NYRA is a free UE5 editor plugin that turns a reference (image, video, or prompt) into a finished Unreal Engine scene by combining the user's own Claude and Codex subscriptions with Claude computer-use to drive external tools (Meshy, Substance, ComfyUI, Blender) and deliver results back as native UE assets. The research confirms this product is technically feasible on a 6–9 month solo timeline, with a clear three-process architecture that keeps UE editor stability intact, but it faces a mandatory pre-code legal gate that could delay the start by 1–2 weeks and two architectural risks (computer-use reliability on Windows and Codex CLI programmatic surface) that must be spiked in Phase 1 before locking scope.

The recommended build approach is three cooperating processes: the UE plugin shell (C++, Fab-distributable), NyraHost (Rust or TypeScript binary, the MCP host and agent router), and NyraInfer (llama.cpp serving Gemma 3 4B for offline fallback). Claude Code CLI v2.1.111+ drives the user's Claude Pro/Max subscription via subprocess with `--output-format stream-json`; this is the verified, ToS-supported path. Codex CLI integration is architecturally parallel but its programmatic surface is unverified and must be confirmed before Phase 2 — the fallback is shipping v1 as Claude-only. The launch demo (reference video to matched UE Sequencer shot) is the single feature that differentiates NYRA from every competitor and is architected as the final ring before Fab submission.

The top risks are: (1) legal ambiguity around driving user subscriptions via subprocess automation — requires written clarification from Anthropic and OpenAI before code ships; (2) computer-use reliability on Windows for web UIs like Meshy — requires a dedicated spike in Phase 5 before committing the D1 launch demo; (3) C++ ABI drift across UE 5.4–5.7 — mitigated by a compat shim and four-version CI from day one; (4) solo scope creep on a 6–9 month timeline — mitigated by pre-defined per-phase cut lines; and (5) Fab AI-plugin policy uncertainty — requires written pre-clearance from Epic before distribution commits. All five are manageable with the mitigations in this document.

---

## Scope Challenges to the Founder's Current Vision

These are issues surfaced by the researchers that require explicit founder decisions before Phase 1 planning locks scope. They are recorded here so the roadmapper can flag them in the requirements phase.

### FLAG 1: v1 Codex support — defer to v1.1?

FEATURES.md and PITFALLS.md both recommend shipping v1 as Claude-only and adding Codex in v1.1. The rationale: Codex CLI programmatic surface is unverified (STACK gives it LOW confidence), its ToS is a separate BLOCKING legal item, and it doubles the integration + auth + rate-limit handling work. The economic wedge works with Claude alone ("bring your own $20/mo subscription"). Codex is additive, not foundational.

**Recommendation:** Ship v1 as Claude-only. Codex becomes Ring 8 (post-launch). If the founder disagrees, Codex research and legal gate must happen in P0 alongside Claude, adding 1–2 weeks.

**Impact if deferred:** Removes one BLOCKING legal item from P0, halves the subscription bridge testing surface, and tightens the critical path.

### FLAG 2: Meshy integration path — headless browser vs cursor-takeover computer-use

PITFALLS.md (section 2.7) recommends using a headless browser (Playwright) for Meshy's web UI rather than cursor-takeover computer-use for the launch demo, specifically because it eliminates mouse-hijack UX issues and is more reliable on Windows. Meshy also has a REST API. ARCHITECTURE.md notes that Meshy has a documented image-to-3D API and recommends the API path over computer-use wherever available.

**Recommendation:** For Meshy specifically, use the REST API (not computer-use) in Phase 3/4; reserve computer-use for tools with no API (Substance 3D Sampler, Blender interactive retopo). PITFALLS also recommends Playwright for web targets in the launch demo.

**Impact on Phase 3/4 plans:** Meshy API path is implemented in Ring 3, not Ring 4. Computer-use Ring 4 focuses on Substance Sampler and ComfyUI. This simplifies the launch demo path significantly.

**Decision needed:** Does the founder want to lead with computer-use for all external tools (as stated in PROJECT.md), or adopt the API-first-then-computer-use fallback pattern that ARCHITECTURE and PITFALLS both recommend?

### FLAG 3: Pre-code legal gate (P0) — 1–2 weeks delay before any code

Both STACK.md and PITFALLS.md independently surface a mandatory P0 legal gate covering:
- Written clarification from Anthropic: is driving `claude` CLI via subprocess from a third-party commercial plugin within their Terms?
- Written clarification from OpenAI: same question for Codex CLI.
- Fab AI-plugin policy: does a plugin that spawns external CLIs, downloads ML models on first run, and drives external web tools pass Fab review?
- NYRA ToS + EULA draft: liability for generated content, data handling, subscription attribution.
- Trademark screening on "NYRA" (Class 9 + 42 + 41).
- Gemma license verification for commercial redistribution via Fab.

**Recommendation:** This gate is non-negotiable. Starting code before these are resolved risks building on a legally invalid foundation. Budget 1–2 weeks for P0. Founder may choose to start lower-risk technical work (plugin scaffolding) in parallel, but no subscription-driving or distribution code before written responses.

**Impact:** Delays effective Phase 1 start by ~1–2 weeks from project kick-off.

### FLAG 4: EV code-signing certificate — $400–700/yr budget item

PITFALLS.md (section 3.4) and STACK.md both flag that the plugin spawns multiple binaries (claude.exe, codex.exe, llama-server.exe, ffmpeg.exe, yt-dlp.exe) and this will trigger Windows SmartScreen and AV false positives on first install. An EV code-signing certificate (~$400–700/yr) immediately clears SmartScreen reputation and is the only reliable solution for enterprise users.

**Recommendation:** Budget this before Phase 2. Non-EV certs have a 30-day reputation-building window that creates a bad first-install experience at Fab launch.

### FLAG 5: UE-version CI matrix — must start in Phase 2, not post-launch

PITFALLS.md (section 3.3) is unambiguous: four-version CI (5.4, 5.5, 5.6, 5.7) must start at Phase 2 day one, not after the main feature work. Deferring this is the ABI-drift trap — a late retrofit of four-version support costs 3–5x more than building with it from the start. ARCHITECTURE.md's compat shim design assumes CI exists.

**Recommendation:** Phase 2 planning must include Windows CI runner setup for all four UE versions as a first-day deliverable, not a "nice to have" at the end of the phase.

### FLAG 6: Launch demo phase placement — reconcile Phase 6 vs Ring 6 discrepancy

FEATURES.md places the video-to-shot launch demo at Phase 6 (its "Ring 5" maps to image→scene, "Ring 6" to video→shot). ARCHITECTURE.md places it at Ring 6 of a 9-ring build order. Both converge on video→shot being the second-to-last milestone before polish and Fab submission, which maps to Phase 7 in the suggested phase structure below (Phases 0–9 spanning legal gate through Fab launch).

**Reconciliation:** Video-to-shot demo is Phase 7 of 9 in the roadmap below. This is a HIGH-convergence finding.

---

## Key Findings

### Stack (Verified — LOCKED)

These decisions are verified against live 2026 documentation by the STACK researcher (web access confirmed). They are locked.

| Component | Version | Confidence | What It Does |
|-----------|---------|------------|--------------|
| Claude Code CLI subprocess | v2.1.111+ (`claude -p --output-format stream-json --verbose`, `claude setup-token`) | HIGH | Drives user's Claude Pro/Max subscription from the plugin. One-year OAuth token via `CLAUDE_CODE_OAUTH_TOKEN`. `--mcp-config <json>` injects NYRA's MCP server per session. |
| Python MCP sidecar | `mcp` PyPI (Tier 1, current) | HIGH | No C++ MCP SDK exists (confirmed on modelcontextprotocol.io). Python sidecar is the only viable path for MCP orchestration with UE Python binding access. |
| MCP protocol | 2025-11-25 spec | HIGH | Current spec confirmed. Streamable HTTP (not deprecated SSE) for HTTP transport; stdio default. |
| Gemma 3 4B IT QAT Q4_0 GGUF | `google/gemma-3-4b-it-qat-q4_0-gguf`, 3.16 GB, 128K ctx | HIGH | Offline/privacy/fallback local model. Multimodal (text + image input). Confirmed on HuggingFace 2026-04-21. |
| llama.cpp / Ollama | b3827+ series; Ollama 0.5+ as detect-and-use | HIGH | Local inference runtime. `llama-server` provides OpenAI-compatible HTTP endpoint. |
| Computer-use tool type | `computer_20251124`, beta header `computer-use-2025-11-24`, Claude Opus 4.7 | HIGH | Confirmed current on platform.claude.com. Opus 4.7 supports 2576 px long edge, `zoom` action with `enable_zoom: true`. Windows: use Claude Desktop (not CLI — CLI computer-use is macOS-only). |
| BGE-small-en-v1.5 embedding | BAAI/bge-small-en-v1.5, 33M params, 133 MB ONNX, 384-dim, MIT | HIGH | Bundleable embedding model for RAG. Confirmed on HuggingFace. |
| LanceDB | 0.13+, embedded, Apache 2.0 | MEDIUM-HIGH | Local vector store. No server required. Rust core, Python binding. |
| FFmpeg | 6.1 LTS static Windows binary | HIGH | Keyframe extraction for video reference analysis. |

**On Windows computer-use path:** The CLI computer-use is macOS-only. On Windows, the flow is NYRA invokes Claude Code CLI, Claude Code detects GUI tasks, and delegates to Claude Desktop's computer-use. Alternatively, NYRA's sidecar calls the Anthropic API directly with `computer_20251124` if the user supplies an API key (advanced mode). Both paths should ship; the Desktop-routing path is the zero-API-cost default.

### Stack (Unverified — Phase 1 Spike Targets)

These must be empirically validated before v1 commits depend on them.

| Item | Risk Level | What to Verify | Who Verifies |
|------|-----------|----------------|--------------|
| Codex CLI programmatic surface | BLOCKING (if v1 includes Codex) | `codex --help`, `codex exec --help`, README at github.com/openai/codex — exact flags, JSON output mode, MCP support, TTY requirements, ToS for subprocess invocation | Phase 1 Day 1 if Codex in v1; else defer to Ring 8 spike |
| Fab AI-plugin policy 2026 | BLOCKING | Log into Fab seller portal, read Content Guidelines + Code Plugin Checklist — subprocess spawning, external CLI deps, AI disclosure, ML model bundling rules | P0 legal gate |
| UE NNE ONNX embedding feasibility | LOW (affects optimization path only) | Prototype BGE-small-en-v1.5 via NNE DirectML vs ONNX Runtime in Python sidecar. If NNE works: plugin-size win. If not: ONNX Runtime in sidecar (fallback is already known-good) | Phase 2 spike |
| UE 5.4 → 5.7 API drift matrix | HIGH (affects all four-version shipping) | Compile-test the compat shim for NNE, Material Editor, Blueprint graph editing, Sequencer APIs against all four UE versions. Empirical, not doc-based. | Phase 2 CI matrix setup |
| Meshy public API availability + pricing (April 2026) | MEDIUM | Confirm Meshy REST API is accessible to free accounts or define minimum tier; confirm pricing model has not changed | Phase 3 Day 1 |
| Claude computer-use reliability percentiles on Windows | HIGH (gates launch demo) | Run 20 scripted computer-use sessions against Meshy web, Substance Sampler, ComfyUI on a representative Windows 11 machine. Measure: success rate, click accuracy on dynamic UI elements, DPI-100% vs DPI-150% | Phase 5 spike — gate to committing video-to-shot demo |

### Architecture Spine

**Three-process model** (HIGH convergence across all four research files):

```
Process 1: UnrealEditor.exe + NYRA C++ plugin
  - Components: UE Plugin Shell, Tool Catalog, Asset Import Bridge, UE Compat Shim
  - IPC to Process 2: loopback WebSocket on 127.0.0.1 (ephemeral port)

Process 2: NyraHost (Rust or TypeScript binary)
  - Components: MCP Host + Agent Router, Backend Drivers, RAG/Knowledge Layer, Session State (SQLite), Computer-Use Orchestrator, External Tool Adapters, Video Reference Analyzer
  - IPC to Claude CLI: stream-JSON stdio
  - IPC to Codex CLI: stream-JSON stdio (Phase 2 / v1.1)
  - IPC to NyraInfer: localhost HTTP (OpenAI-compatible)
  - IPC to MCP tool servers: MCP over stdio

Process 3: NyraInfer (llama.cpp server)
  - Serves Gemma 3 4B on localhost HTTP (OpenAI-compatible endpoint)
  - Spawned on demand; stopped when not needed
```

**12 components across 3 processes:**

| # | Component | Process | Core Responsibility |
|---|-----------|---------|---------------------|
| 1 | UE Plugin Shell | UE Editor | Slate chat panel, subsystems, command queue, user-facing UI |
| 2 | Tool Catalog | UE Editor | UE-native tools (Blueprint, actor, material, lighting, Sequencer) as JSON-schema MCP tools |
| 3 | Asset Import Bridge | UE Editor | .fbx/.glb/.sbsar/.png → UE assets via `FAssetImportTask` |
| 4 | MCP Host + Agent Router | NyraHost | Routes turns to Claude/Codex/Gemma; hosts MCP; owns session context |
| 5 | Backend Drivers | NyraHost | Subprocess lifecycle for Claude CLI, Codex CLI, NyraInfer; stream-JSON I/O |
| 6 | RAG / Knowledge Layer | NyraHost | Bundled vector index, embedding pipeline, incremental GitHub-releases updater |
| 7 | Session State | NyraHost | SQLite: chat history, tool-call log, attachments, computer-use screenshots |
| 8 | UE Compat Shim | UE Editor | `NYRA::Compat::` wrappers for NNE, Material, Sequencer, Slate API drift across 5.4–5.7 |
| 9 | Computer-Use Orchestrator | NyraHost | DXGI screenshot, SendInput, UIA window targeting, confirmation gate, action log |
| 10 | External Tool Adapters | NyraHost | Per-tool recipes: Meshy API, ComfyUI local HTTP, Substance Sampler CU, Blender headless |
| 11 | Asset Staging Manifest | Disk | `nyra_pending.json` handoff between NyraHost writes and UE import watch |
| 12 | Video Reference Analyzer | NyraHost | yt-dlp + ffmpeg keyframe extraction, multimodal analysis (Claude or Gemma-vision), SHOT_PLAN.json |

**Key patterns to follow:**
- Tool-as-Contract: every UE capability is a JSON-schema MCP tool, never a raw API call from the agent
- Out-of-Process for Anything That Can Fail: all 3rd-party binaries run as supervised child processes
- File-Manifest Handoff: external tools write to staging dir, never touch UE Content directly
- Confirmation Gate on Computer-Use: first action per session requires explicit user approval
- Versioned Compat Shim: all 5.4/5.5/5.6/5.7 API differences isolated behind `NYRA::Compat::`
- RAG-First, Then Agent: knowledge queries retrieve before calling any backend

**NyraHost language decision gate (Phase 1):** Rust is the primary recommendation (memory safety, small binary, llama-cpp-2 crate). TypeScript/Node is the fallback if MCP Rust SDK maturity is insufficient at Phase 1 evaluation. This decision must be made empirically, not assumed. Both options accommodate the architecture.

### Feature Surface

**Table stakes (TS1–TS12) — ship these or users bounce in 10 minutes:**

| ID | Feature | Complexity | UE Subsystem | Competitor Parity |
|----|---------|-----------|--------------|-------------------|
| TS1 | In-editor chat panel (history, attachments, status, cancel) | S | Slate/UMG Editor | All four competitors have this; Aura's is most polished |
| TS2 | UE5 docs RAG (5.4–5.7, BP node ref, C++ API, forum, YT transcripts) | M | Agent/RAG | CoPilot and Aura both do this; NYRA must add version-tags + citations |
| TS3 | Blueprint read/write/rewire (K2 graph surgery) | L | Blueprint/Kismet | Aura leads (Dragon Agent); CoPilot has granular action set |
| TS4 | Blueprint debug loop (explain + fix + apply + recompile) | L | BP compiler, Output Log | Aura leads; CoPilot and Ludus have basic versions |
| TS5 | Asset search (semantic queries over project Content) | M | Asset Registry | Nwiro leans hard on this; CoPilot has keyword-level |
| TS6 | Basic scene operations (spawn/move/delete/select actors) | S | Level/EditorScripting | All competitors have this |
| TS7 | Material ops (MIC param editing, template instantiation) | M | Material, Texture | Nwiro and CoPilot do MIC param editing |
| TS8 | Console command execution (GEngine->Exec wrapper) | XS | Engine console/CVars | Baseline utility; most competitors include |
| TS9 | Output Log / Message Log streaming | XS | Logging | Baseline utility |
| TS10 | Subscription connection status UI | S | Editor UI | Unique to NYRA's BYO-subscription model |
| TS11 | Cancel / interrupt / undo (FScopedTransaction) | M | Transactions | CoPilot and Aura both support undo |
| TS12 | Safe-mode / dry-run (plan before execute) | S | N/A | CoPilot has preview; Aura's Dragon Agent does plan-then-execute |

**Differentiators (D1–D10) — where NYRA beats the field:**

| ID | Feature | Complexity | Competitor Claim | NYRA Must Beat It By |
|----|---------|-----------|-----------------|---------------------|
| D1 | Reference video → matched UE shot (LAUNCH DEMO) | XL | No competitor ships this | NYRA sets the benchmark; V1: single-shot ≤10s, correct composition + lighting intent |
| D2 | Image → full UE-native scene | L | Nwiro's one-prompt scene uses their asset library (Leartes assets) | NYRA uses user's own library first, generates missing assets via Meshy/Substance/ComfyUI — style-consistent output vs. Nwiro's fixed library |
| D3 | Claude + Codex subscription driving (no new AI bill) | M+S+M | Every competitor charges for inference | "Bring your own $20/mo sub" — unique economic wedge; defend relentlessly |
| D4 | Computer-use orchestration of Meshy / Substance / ComfyUI / Blender | XL | No competitor reaches outside UE to drive external tools | NYRA sets the benchmark for cross-tool orchestration |
| D5 | Gemma 4B local fallback (offline/privacy/NDA mode) | M | No competitor ships offline fallback | First-class feature: enterprise differentiator even though the consumer-facing wedge is Claude/Codex |
| D6 | YouTube-tutorial-to-executable-plan | L | No competitor ships "turn this tutorial into applied code" | Defer to v1.1; include in multi-wedge launch backup |
| D7 | Sequencer automation for virtual production | L | Nwiro has some cinematic composition; no strong NL shot-blocking | "Slow push-in on the hero, then cut wide" beats any competitor's Sequencer support |
| D8 | Lighting authoring from natural language / reference image | M | Nwiro has cinematic presets; CoPilot has granular light actions | "Match this image's mood" is unique — no competitor does reference-driven lighting |
| D9 | Natural-language asset tagging + thumbnail embeddings | L | CoPilot has keyword-level; Nwiro uses their own catalog | CLIP-like semantic search beats keyword matching — deferred to v2 after baseline asset search |
| D10 | Local project-knowledge RAG (user's own code/comments/levels) | M | No competitor indexes the user's own project | Answers "where do we spawn the boss?" from user's own Blueprint comments |

**Anti-features (deliberately not shipping in v1):**
- AF1: NPC conversation runtime (Convai/Inworld territory — different buyer)
- AF2: Cross-engine support (Ramen VR's Coplay; depth over breadth)
- AF3: Full image-generation UI inside UE (re-implementing ComfyUI)
- AF4: Fine-tuned UE-specialist model (breaks the BYO-subscription wedge)
- AF5: Ingesting paid courses as RAG corpus (copyright + ToS minefield)
- AF6: Hosted backend / SaaS features in v1 (validate adoption first)
- AF7: Creating full Material graphs from scratch via AI (too brittle; trust-destroying failure rate)
- AF8: Animation graph authoring in v1 (AnimBP + Control Rig; deferred to v2)

**v1 cut-line priority (in order if timeline slips):**
1. D6 YouTube-tutorial-to-plan (already deferred to v1.1)
2. D9 NL asset tagging + thumbnail embeddings (already v2)
3. D1 multi-shot → D1 single-shot only
4. Blueprint *debug* auto-fix → "explain error only" (drop apply-and-recompile)
5. Nuclear cut: ship as UE5 chat + docs RAG + scene builder without D1 video demo; reposition launch around D2 image→scene (still beats Nwiro's fixed-library approach via D4 computer-use)

### Critical Pitfalls (Top 5 Severity-Ordered)

**1. Legal ambiguity on driving user subscriptions via subprocess — BLOCKING**
All four research files converge on this. Anthropic's ToS around "automated use" of consumer subscriptions is unresolved. Driving `claude` CLI from a third-party commercial plugin may be interpreted as sharing access or circumventing API billing.
Prevention: P0 legal gate — written clarification from Anthropic before any code ships. API-key fallback mode built in from Phase 1 so the product survives even if Anthropic says "no" to the BYO-subscription path. Design principle: NYRA is always the tool consumer, never the auth provider; user's token never touches NYRA's code.

**2. Computer-use reliability on Windows — HIGH (gates launch demo)**
PITFALLS identifies five distinct HIGH-severity computer-use failure modes: element-detection false positives, UAC/SmartScreen modal blindness, DPI scaling + multi-monitor coordinate confusion, target-app UI version drift, and race conditions on slow page loads.
Prevention: Phase 5 spike — 20 scripted sessions against Meshy/Substance/ComfyUI before committing D1 launch demo. Prefer API over computer-use wherever available (Meshy REST API, ComfyUI HTTP). Use UIA for structural clicks (DPI-safe). Canary suite runs daily on CI. Headless browser (Playwright) for Meshy as fallback.

**3. C++ ABI drift across UE 5.4–5.7 — HIGH**
UE's C++ ABI is not stable across minor versions. NYRA targets four versions; without CI, one version ships broken.
Prevention: Four-version CI from Phase 2 Day 1 (non-negotiable per PITFALLS). All drift-prone code behind `NYRA::Compat::` shim. Empirical matrix test of NNE, Material, Blueprint graph, Sequencer APIs in Phase 2.

**4. Solo scope creep on a 6–9 month timeline — BLOCKING for shipping**
PROJECT.md's active list spans: four UE versions × Claude + Codex + Gemma × five external tools × launch demo × RAG × Fab + direct distribution. This is the #1 reason ambitious solo projects die.
Prevention: Per-phase cut lines defined before each phase starts (minimum-shippable tier + stretch tier). v1 is Claude-only, Windows-only. Launch demo (D1) drives every scope decision. Weekly self-retrospective: "what in Active is not on the critical path to D1?"

**5. Fab AI-plugin policy uncertainty — BLOCKING if sole distribution channel**
Fab policies on AI plugins (subprocess spawning, external CLI deps, ML model bundling) are evolving and were unverifiable by both STACK and PITFALLS researchers (fab.com blocked in both sessions).
Prevention: P0 legal gate — read Fab Content Guidelines + Code Plugin Checklist as a seller; email Epic creator support with a one-page product summary; get written pre-clearance. Plan direct-distribution fallback from day one (GitHub releases, signed installer) so Fab rejection is a distribution setback, not a product death.

---

## Implications for Roadmap

### Suggested Phase Structure

The four research files converge on a 10-phase structure (P0 through P9). Phase numbers below correspond to logical milestones; the roadmapper should map these to calendar weeks based on complexity estimates.

---

**Phase 0: Legal + Brand Gate (P0)**
**Rationale:** Must precede any code. PITFALLS rates 10 distinct items as BLOCKING or HIGH-severity at this stage. Building without these gates is building on a legally uncertain foundation.
**Delivers:** Written legal clearance from Anthropic + OpenAI on subscription driving; Fab pre-clearance on AI plugin submission; NYRA ToS + EULA draft; trademark screening on "NYRA"; Gemma license verification; brand guidelines research (Anthropic, OpenAI, Epic); domain + GitHub org + social handle reservation.
**Features addressed:** Gates D3 (subscription driving), D4 (computer-use ToS), D5 (Gemma redistribution), all Fab distribution.
**Pitfalls addressed:** 1.1, 1.2, 3.1, 3.5, 6.4, 7.1, 8.1, 8.2, 8.3, 8.4, 8.5
**Duration estimate:** 1–2 weeks
**Research flag:** Needs live Fab seller portal access + direct email to Anthropic and OpenAI. Cannot be done from training data alone.

---

**Phase 1: Plugin Shell + Subscription Bridge (Ring 0 "It Can Talk")**
**Rationale:** Validates the entire process model, IPC, and CLI subprocess driving. Everything downstream depends on this. Ring 0 passes criteria are the gate.
**Delivers:** UE 5.6 Slate chat panel docked as editor tab; NyraHost (Ring 0 skeleton: WS server, message loop); Claude Code CLI driver (stream-JSON stdio); Session State (SQLite, one table); streaming reply in panel. No RAG, no tools, no Codex, no Gemma yet.
**Ring 0 pass criteria:** Plugin loads in UE 5.6 without errors; NyraHost spawns reliably; round-trip to Claude < 2s to first token; 100 consecutive turns without plugin-side error; editor remains responsive during streaming; auth failure gives clear in-panel message.
**Stack elements:** Claude Code CLI v2.1.111+, NyraHost (Rust or TypeScript — decision gate here), UE 5.6, loopback WebSocket IPC, SQLite.
**Pitfalls addressed:** 1.3 (auth drift), 1.4 (rate limiting — build checkpointing), 1.5 (CLI version drift — version-pin), 1.6 (no-subscription dead-end — design Gemma path now), 3.4 (SmartScreen — EV cert budgeted)
**Spike:** Codex CLI programmatic surface (1–2 days) — if v1 includes Codex; else defer spike to Ring 8.
**Research flag:** Standard patterns for UE plugin + subprocess IPC. New: NyraHost language spike (Rust MCP SDK vs TypeScript MCP SDK maturity), CLI flag verification.

---

**Phase 2: Four-Version Build Matrix + Plugin Foundation (Ring 0 → Ring 7 infrastructure)**
**Rationale:** Four-version CI must start here, not at the end. The compat shim is easier to build from the start than to retrofit. Anti-virus/SmartScreen mitigation (EV cert) must also happen before users touch the plugin.
**Delivers:** CI pipeline building all four UE version binaries (5.4, 5.5, 5.6, 5.7); UE Compat Shim (`NYRA::Compat::`) covering drift-prone APIs; empirical API drift matrix (NNE, Material, Blueprint graph, Sequencer); EV code-signing cert acquired and applied; Privacy Mode first-class (Gemma-only toggle blocks all egress except to user's own CLI).
**Pitfalls addressed:** 3.2 (binary size — models hosted not bundled), 3.3 (ABI breakage — four-version CI day one), 3.4 (SmartScreen — EV cert), 3.6 (GPU OOM — GPU probe at install), 8.4 (studio data handling — privacy mode architecture)
**Spike:** UE NNE ONNX feasibility (1 day — does BGE-small run via NNE DirectML?); UE 5.4→5.7 API drift empirical matrix (3–5 days).
**Research flag:** Needs empirical testing on UE 5.4 and 5.7 (the corners). Cannot be answered from docs.

---

**Phase 3: UE5 Knowledge RAG (Ring 1 "It Knows UE")**
**Rationale:** Knowledge is the second-most-used feature after chat. It enables TS2 and unblocks all downstream "agent answers before it acts" patterns. Legal-clean corpus is critical before indexing starts.
**Delivers:** Bundled LanceDB vector index covering UE5 official docs (5.4–5.7) + Blueprint node reference + C++ API; BGE-small-en-v1.5 ONNX embedding model (bundled, 133 MB); GitHub Releases updater pipeline triggered on Epic release tags; version-tagged chunks; symbol validation index from user's installed UE headers; citation rendering in chat panel. Demo: "How do I do soft shadows on a directional light in 5.6?" with verbatim-quote citation.
**Features addressed:** TS2, D10 (project RAG deferred to v1.1 unless timeline allows)
**Stack elements:** LanceDB 0.13+, BGE-small-en-v1.5, BGE-small ONNX via ONNX Runtime in Python sidecar (or NNE if Phase 2 spike succeeded), GitHub Releases CDN
**Pitfalls addressed:** 4.1 (UE version drift in answers), 4.2 (YouTube transcript noise — whitelist channels only), 4.3 (outdated tutorials — freshness filter), 4.4 (citation hallucination — verbatim quote + symbol validation), 4.5 (index size — tiered: 50 MB bootstrap bundled, full index downloaded), 8.1 (paid-course ingestion — hard technical block)
**Research flag:** RAG quality is testable with a golden-set Q&A suite. YouTube corpus requires manual creator allowlist curation. Standard patterns otherwise.

---

**Phase 4: UE-Native Tool Catalog + Actions (Rings 2 → Blueprint)**
**Rationale:** First phase where the agent changes UE state. The Tool Catalog and transaction safety patterns established here are the foundation every later phase builds on.
**Delivers:** Tool Catalog: first 20–30 tools covering spawn_actor, place_mesh, set_material_parameter, add_light, set_post_process, create_level_sequence, Blueprint read/write/rewire, Blueprint debug loop (explain + fix + apply + recompile), console command, Output Log access. Every tool wrapped in FScopedTransaction. Session-level super-transaction for undo. Plan-before-execute default. Demo: "Spawn 20 cubes in a spiral and make the middle one red." Demo: "Fix this Blueprint compilation error."
**Features addressed:** TS3, TS4, TS6, TS7, TS8, TS9, TS11, TS12, D8 (basic lighting)
**Pitfalls addressed:** 5.1 (AssetRegistry scan), 5.2 (silent import failure), 5.3 (GPU crash on import), 5.4 (duplicate assets — UUID idempotency), 9.1 (silent failure — post-condition verification), 9.2 (undo — super-transaction + session cleanup), 9.4 (trust-through-transparency — plan preview mandatory)
**Blueprint quality gate:** Must demonstrate beat on Aura Telos 2.0's Blueprint error reduction benchmark before Phase 5 starts. Measure with canned broken-Blueprint suite.
**Research flag:** Blueprint graph editing API stability across UE 5.4–5.7 is flagged LOW confidence. Needs empirical testing specifically on `UEdGraph` authoring APIs across all four versions.

---

**Phase 5: Computer-Use Orchestration (Ring 4 "It Drives Other Apps")**
**Rationale:** Highest-risk phase. The launch demo depends on computer-use working reliably on Windows. Must be validated thoroughly before committing Phase 6 scope.
**Delivers:** Computer-Use Orchestrator (DXGI screenshot, SendInput, UIA window targeting); user confirmation gate + "agent active" HUD + keyboard chord pause; Meshy integration (REST API primary, computer-use fallback for workflows the API doesn't cover); ComfyUI integration (local HTTP API primary, computer-use for custom node states); action log with screenshot thumbnails; phase-specific spike results. Demo: "Make me a tileable mossy stone material" (ComfyUI or Meshy).
**Features addressed:** D4 (Meshy + ComfyUI; Substance Sampler + Blender deferred to v1.1 unless timeline allows)
**Pitfalls addressed:** 2.1 (element-detection false positives — post-condition verification, visual confirmation before destructive clicks), 2.2 (UAC/SmartScreen — pre-flight system check, Secure Desktop detection), 2.3 (DPI scaling — UIA structural clicks, primary monitor normalization), 2.4 (target-app version drift — canary suite, API-first preference), 2.5 (race conditions — event-based waits, post-condition hashing), 2.6 (long-running polling — filesystem/API poll, not screenshot poll), 2.7 (cursor takeover — headless browser for Meshy web, agent-active HUD)
**Phase gate:** 20 scripted computer-use sessions on a representative Windows 11 machine with Meshy web (if CU path chosen), Substance Sampler, ComfyUI. Pass/fail threshold: >85% success rate on a canned task suite. If <85%, expand API path coverage and reduce CU scope before proceeding to Phase 6.
**Research flag:** Computer-use reliability on Windows is a primary open research question from PROJECT.md. This phase is the empirical answer.

---

**Phase 6: Asset Pipeline + Image-to-Scene (Ring 3 + Ring 5 merged)**
**Rationale:** Builds on Phases 4 + 5 to deliver the first publicly demo-able end-to-end scene-from-reference workflow. This is the v1-launchable state (video-to-shot is the stretch demo, image-to-scene is the fallback launch demo).
**Delivers:** Asset Import Bridge (FBX/GLB/PNG/EXR → UE assets with post-import verification); staging manifest pattern; scene-assembly recipe prompt in Agent Router; lighting authoring (sky, sun, fog, PPV, exposure from natural language + reference image); Sequencer automation (camera tracks, keyframes, shot blocking from NL). Demo: reference image → matching UE scene with correct lighting and materials. This demo alone beats Nwiro (uses user's library + generates missing assets vs. Nwiro's fixed Leartes catalog).
**Features addressed:** D2 (image → scene), D7 (Sequencer), D8 (lighting from reference), D3 (subscription economics validated end-to-end)
**Pitfalls addressed:** 5.1–5.4 (import pipeline), 9.1–9.2 (undo + transparency for multi-step scene builds)
**Research flag:** Scene assembly recipe prompt quality is testable. Standard patterns otherwise.

---

**Phase 7: Reference Video → Matched Shot (Ring 6 "Launch Demo")**
**Rationale:** The feature that no competitor ships. This is the Fab launch demo. Must be as reliable on arbitrary inputs as on the demo reference before Fab submission.
**Delivers:** Video Reference Analyzer (yt-dlp + ffmpeg scene-cut detection + multimodal keyframe analysis → SHOT_PLAN.json); canonical camera-move taxonomy (static/pan/tilt/dolly/truck — user-confirmable); semantic lighting extraction (not RGB analysis); Sequencer tools for camera cuts + transform keyframes + post-process; "side-by-side with reference" playback view in panel. Demo: YouTube link → matched Sequencer shot. This is the Fab launch demo.
**Features addressed:** D1 (video → matched shot — LAUNCH DEMO), D6 (YouTube tutorial → plan — ship here or defer to v1.1 depending on timeline)
**Pitfalls addressed:** 6.1 (keyframe sampling — scene-cut detection first), 6.2 (camera motion misinterpretation — optical flow + monocular depth), 6.3 (lighting/LUT mismatch — semantic extraction, not RGB), 6.4 (copyright of reference videos — ephemeral processing, user disclaimer, no full-video upload to Anthropic)
**Quality gate:** Random-reference daily test from Phase 7 Day 1. Every day, run the flagship demo on a randomly chosen reference clip (not the demo reference). "First-install cold-start" test is a release gate: uninstall everything, reinstall, run demo. If it fails clean, do not proceed to Phase 8.
**Research flag:** Video reference understanding quality with Claude Opus 4.7 vision needs empirical testing on a diverse clip set. Optical flow depth estimation (MiDaS / Depth Anything) integration needs a spike. Both can be spiked in Phase 7 Day 1–2.

---

**Phase 8: Second Backend + Offline Mode (Ring 8)**
**Rationale:** Codex CLI broadens the economic wedge; Gemma 4B makes NYRA usable by users without any subscription. Both are additive to an already-launchable product. Can slip post-launch if timeline is tight.
**Delivers:** Codex CLI driver (parallel to Claude driver — same stream-JSON IPC pattern if CLI surface is verified); NyraInfer.exe + Gemma 3 4B GGUF; backend router policy + user preference UI; Gemma handles offline: docs Q&A, asset search, basic Blueprint tweaks. Gemma multimodal handles offline reference-image description.
**Features addressed:** D3 (Codex half of the economic wedge), D5 (Gemma local fallback — promoted from aspirational to first-class)
**Pitfalls addressed:** 1.2 (Codex ToS — must be resolved in P0 if Codex v1; else here), 1.6 (no-subscription dead-end — Gemma makes the first-run experience complete)
**Cut line:** If 6–9 month timeline runs tight, defer Ring 8 to v1.1 post-launch. v1 ships as Claude-only. Gemma basic functionality (docs Q&A) can be included without full Ring 8 if the download-on-demand path is built in Phase 1–2.
**Research flag:** Codex CLI programmatic surface must be verified before this phase starts (spike carried forward from Phase 1 if deferred). Standard patterns for Gemma + llama.cpp (HIGH confidence from STACK research).

---

**Phase 9: Polish + Fab Submission (Ring 9)**
**Rationale:** The final integration, quality bar, and distribution phase. "First-install cold-start" test is the release gate, not a checkbox.
**Delivers:** Onboarding wizard (detect CLIs, prompt Gemma download, download knowledge index); error message polish (every auth failure, rate limit, import failure has a clear human message and a remediation path); telemetry opt-in (anonymous, default off); Fab listing materials (video, screenshots, descriptions); documentation site; launch video; EV-signed installer. Direct-distribution fallback (GitHub releases) live before Fab submission.
**Pitfalls addressed:** 3.1 (Fab AI-plugin policy — pre-clearance from Phase 0 applied here), 7.1 (scope creep — cut lines enforced), 7.2 (demo-driven trap — random-reference daily test is the release gate, not the scripted demo), 7.4 (competitor launches same demo first — devlog started Month 1), 8.5 (brand usage — neutral language in listing, no logos)
**Research flag:** Standard patterns. Fab listing format and requirements should be verified against the seller portal (part of P0 but revisited here for current guidelines).

---

### Phase Ordering Rationale

1. Legal gate first: without P0 clearance, the BYO-subscription economic wedge may be legally invalid.
2. Process model before features: Ring 0 (Phase 1) validates the entire three-process IPC architecture before any features are built on it.
3. Build matrix before features: Phase 2 CI prevents ABI-drift accumulation that becomes exponentially more expensive to fix later.
4. Knowledge before actions: RAG (Phase 3) gives the agent the context it needs to execute correctly; building actions (Phase 4) without knowledge context produces an agent that acts confidently and incorrectly.
5. In-editor tools before external tools: Phase 4 tool catalog before Phase 5 computer-use. External tool outputs need the import pipeline that Phase 4 establishes.
6. Computer-use gated by spike: Phase 5 cannot commit to D1 launch demo scope until computer-use reliability is measured empirically.
7. Image-to-scene before video-to-scene: Phase 6 delivers the fallback launch demo (D2) before Phase 7 delivers the primary launch demo (D1). If Phase 7 is cut, Phase 6 is the launch.
8. Economic wedge breadth (Codex + Gemma) after core demo: Phase 8 is additive. The wedge works with Claude alone; Codex + Gemma make it wider.

### Research Flags

Phases requiring deeper research / empirical validation during planning:

- **Phase 0:** Needs live Fab seller portal access + email correspondence with Anthropic, OpenAI, Epic. Cannot be done from training data.
- **Phase 1:** NyraHost language spike (Rust MCP SDK vs TypeScript MCP SDK as of April 2026). Codex CLI flag verification if v1 includes Codex.
- **Phase 2:** Empirical UE 5.4/5.5/5.6/5.7 API drift matrix. Cannot be answered from documentation alone.
- **Phase 4:** Blueprint graph authoring API stability across all four UE versions. Flagged LOW confidence in ARCHITECTURE.md.
- **Phase 5:** Computer-use reliability percentiles on Windows. Flagged as primary open research question in PROJECT.md.
- **Phase 7:** Video reference quality with Claude vision on diverse clip set. Camera motion classification accuracy.

Phases with well-documented patterns (standard engineering, reduce research scope):

- **Phase 3:** RAG architecture with LanceDB + BGE-small is well-established. Main work is corpus curation and freshness pipeline design.
- **Phase 6:** Asset import bridge and scene assembly patterns are well-documented UE APIs.
- **Phase 8:** Gemma + llama.cpp path is HIGH confidence from STACK research.
- **Phase 9:** Fab listing and distribution are procedural; research focus is verifying current 2026 seller guidelines.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack (verified items) | HIGH | Claude Code CLI, MCP protocol, Gemma 3 4B GGUF, llama.cpp, BGE-small, computer-use API all verified against live 2026 docs by STACK researcher with web access |
| Stack (unverified items) | LOW (Codex CLI) / LOW-MEDIUM (Fab policies, UE NNE, UE 5.7 drift) | Explicitly cannot be resolved from training data; require Phase 1/2 empirical spikes |
| Features | MEDIUM | Table stakes and differentiators categorized confidently; competitor-specific tool counts (CoPilot ~1,050, Nwiro ~209, Aura 43) not independently re-verified in this pass |
| Architecture | MEDIUM | Three-process model and 12 components are strong from first principles; 9 LOW-confidence items require Phase 1/2 empirical validation; NyraHost language is a Phase 1 decision gate |
| Pitfalls | MEDIUM-HIGH | Legal and UE plugin ABI patterns are well-documented; computer-use Windows failure modes are well-established general patterns; Fab-specific policy pitfalls are LOW-MEDIUM (evolving marketplace) |

**Overall confidence: MEDIUM-HIGH**

The verified stack decisions provide a HIGH-confidence foundation. The primary uncertainties are all in the "unverified" column: Codex CLI surface, Fab policy, UE 5.7 drift, and computer-use reliability on Windows. These are manageable uncertainties with clear Phase 0–2 spike plans, not fundamental feasibility questions.

### Gaps to Address

1. **Codex CLI programmatic surface** — verify before Phase 1 if Codex is in v1; verify before Phase 8 if deferred. Cannot assume flag parity with Claude Code CLI.
2. **Fab AI-plugin policy 2026** — must be verified in P0 via Fab seller portal + Epic email. Current policy is unverifiable from training data.
3. **Computer-use reliability on Windows for web UIs** — Phase 5 empirical spike is the only way to know. All architecture decisions about fallback paths should be designed before the spike so the spike results directly inform scope decisions.
4. **UE 5.4 → 5.7 API drift empirical matrix** — particularly Blueprint graph authoring APIs and NNE. Document these as compat shim entries during Phase 2 testing, not from docs.
5. **Meshy API availability and pricing April 2026** — confirm the API is accessible and affordable before Phase 3/4 architecture commits to it as the primary path.
6. **NyraHost language decision** — Rust vs TypeScript/Node. Must be resolved at Phase 1 with an empirical SDK maturity + binary size spike. Do not architect around an assumption; measure it.
7. **Anthropic written ToS clarification** — the entire economic wedge (D3) depends on this. It must be the first item in P0.

---

## Sources

### Primary (HIGH confidence — verified against live 2026 docs by STACK researcher)

- https://modelcontextprotocol.io/docs — MCP architecture, spec 2025-11-25, SDK tier list (no C++ SDK confirmed)
- https://code.claude.com/docs/en/cli-reference — Claude Code CLI flags, stream-json, setup-token, authentication, computer-use (CLI macOS-only on Windows use Desktop)
- https://platform.claude.com/docs/en/build-with-claude/computer-use — tool type `computer_20251124`, beta header, Opus 4.7 with zoom action
- https://huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf — 3.16 GB, 128K ctx, multimodal, confirmed 2026-04-21
- https://huggingface.co/BAAI/bge-small-en-v1.5 — 33M params, 133 MB ONNX, MIT license, 384-dim
- https://huggingface.co/Qwen/Qwen3-Embedding-0.6B — premium embedding option, Apache 2.0, MTEB 70.70

### Secondary (MEDIUM confidence — training data + project-supplied context)

- PROJECT.md — constraints, key decisions, quality bar, out-of-scope, competitor context (April 2026)
- STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md — this document synthesizes all four
- UE plugin architecture patterns (stable since UE 4.x — MEDIUM-HIGH)
- Competitor feature counts (CoPilot ~1,050 / Nwiro ~209 / Aura 43) — from PROJECT.md competitive analysis, not independently re-verified

### Tertiary (LOW confidence — require Phase 0/1 verification)

- Codex CLI programmatic interface — training data only; flagged LOW in STACK.md
- Fab AI-plugin policy 2026 — training data only; fab.com blocked in both STACK and PITFALLS research sessions
- UE 5.7 specific API changes — docs.unrealengine.com blocked; assumed modest breakage consistent with prior minor version pattern
- Computer-use reliability on Windows for web UI apps (April 2026) — flagged as open research in PROJECT.md

---

*Research completed: 2026-04-21*
*Synthesized: 2026-04-21*
*Ready for roadmap: yes — with the 7 gaps above flagged for Phase 0/1 resolution*
