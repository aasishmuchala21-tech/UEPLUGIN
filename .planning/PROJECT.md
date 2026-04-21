# NYRA

## What This Is

NYRA is a free Unreal Engine 5 plugin, distributed on Fab, that gives UE developers an in-editor AI agent powered by their existing Claude subscription (no new API bills in v1). It combines deep, continuously-updated knowledge of UE5 with a three-process architecture — UE plugin + Python MCP sidecar + local Gemma 3 4B inference — that uses API-first integrations for Meshy, ComfyUI, and Blender, with Claude computer-use reserved for apps without APIs (Substance 3D Sampler, UE editor modals). Built for solo devs, indies, and studios who want a single agent that can go from a reference image or YouTube clip to a lit, dressed, playable Unreal scene.

## Core Value

**Turn a reference (image, video, prompt) into a finished Unreal Engine scene — without the user paying a new AI bill or leaving the editor.**

If everything else fails, this must work: the user hands NYRA a reference, NYRA uses the user's own Claude/Codex subscription to plan and execute, drives the tools needed via computer-use, and delivers a UE-native result (imported meshes, authored materials, spawned actors, configured lighting).

## Quality Bar

**NYRA must be materially better than every competitor on every dimension it competes on.** Parity with Nwiro, Aura (Telos), Ultimate Engine CoPilot, Ludus AI, or the OSS MCP servers is a failure state. Every phase goal, requirement, and success criterion in this project carries the same bar: *beats competitor X on dimension Y*, not *matches X*.

Concrete implications that downstream plans must respect:
- Tool / action count ≥ Ultimate Engine CoPilot's 1,050+ actions, OR an explicit depth-over-breadth argument with measurable proof
- Blueprint reasoning accuracy / speed ≥ Aura Telos 2.0's published baselines (25× error reduction)
- UE version update latency < any competitor (day-of support for new UE releases, not day-one)
- Reference-video → matched scene: no competitor ships this; NYRA must set the benchmark
- Subscription-driven (Claude + Codex) economics: no competitor ships this; defend the wedge relentlessly
- If a plan reads like "reach parity with X", it gets rejected and re-scoped before execution

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- v1 scope. All items are hypotheses until shipped. -->

**Plugin foundation**
- [ ] Ship a native UE5 plugin that installs from Fab on Windows for UE 5.4, 5.5, 5.6, and 5.7
- [ ] Plugin opens an in-editor chat panel with conversation history, attachments, and task status
- [ ] Plugin works with no API keys — agent subprocess-drives the user's Claude Code CLI (`claude -p --output-format stream-json`) on their machine
- [ ] Plugin falls back to a local Gemma 3 4B multimodal GGUF model (via llama.cpp / Ollama) for offline, low-cost, and privacy-mode operation
- [ ] v1 does NOT ship Codex integration — deferred to v1.1 to halve integration, legal, and auth surface

**UE5 knowledge**
- [ ] Ship a bundled, refreshable RAG index covering UE5 official docs (5.4–5.7), Blueprint node reference, C++ API, and community-safe corpus (Epic forums, Unreal slackers-style public transcripts, YouTube tutorial transcripts with attribution)
- [ ] Agent can answer any "how do I do X in UE5" question from the indexed corpus and cite its sources
- [ ] Knowledge index updates automatically when Epic ships a new UE version

**In-editor agent actions (UE-native)**
- [ ] Agent can read and modify Blueprints (graph edits, variable changes, node wiring)
- [ ] Agent can debug a Blueprint, explain the bug, propose the fix, and apply it
- [ ] Agent can spawn actors, place meshes, and author levels programmatically
- [ ] Agent can create/edit materials, set material parameters, and apply them to actors
- [ ] Agent can configure lighting (directional/point/spot/rect/sky), fog, post-process volumes, and exposure
- [ ] Agent can drive Sequencer (cameras, keyframes, shot composition)

**External tool orchestration (API-first, computer-use only where APIs don't exist)**
- [ ] Agent drives Meshy via REST API (image → 3D model), auto-importing the result as a UE StaticMesh
- [ ] Agent drives a locally-installed ComfyUI via its HTTP API for image-to-image workflows (textures, references, variations)
- [ ] Agent drives Blender via Python scripting API for mesh cleanup / retopology before importing into UE
- [ ] Agent drives Substance 3D Sampler via Claude computer-use (`computer_20251124`, Opus 4.7) — no public API exists
- [ ] Claude computer-use can click inside the UE editor for modal dialogs and operations the Unreal API does not expose

**Reference-driven workflows**
- [ ] User can attach an image to the chat — NYRA creates a scene (models + materials + lighting) that matches it
- [ ] User can paste a YouTube link or attach a video file — NYRA analyzes lighting, composition, and camera direction, then replicates it in UE via Sequencer (**launch demo**)
- [ ] User can attach a UE tutorial video — NYRA turns it into an executable plan and runs it

**Distribution & onboarding**
- [ ] Listed on Fab as a free plugin with demo video
- [ ] Zero-config install: open UE, enable plugin, sign into Claude Code once (`claude setup-token`), go
- [ ] Clear in-plugin status for which subscriptions are connected and what capabilities are active

### Out of Scope

<!-- Explicit boundaries with reasoning. -->

- **macOS / Linux support (v1)** — Windows-only to halve the QA surface and because Claude computer-use is most reliable on Windows. Revisit post-launch.
- **UE 5.3 and earlier** — Epic's own deprecation cadence; supporting them doubles the native C++ compatibility work for a shrinking audience.
- **Paid Pro tier / subscription billing (v1)** — v1 is a free Fab plugin. Pro tier deferred until we have validated usage + churn signal. Backend may be scaffolded in Supabase/Railway *only if* research shows hosted RAG is materially better than bundled.
- **Ingesting paid courses (Udemy, Unreal Fellowship, etc.)** — Copyrighted, ToS-locked. Legal landmine. Users may index their *own* purchased courses locally, but NYRA does not redistribute.
- **Training or fine-tuning a UE-specialist model (v1)** — Incompatible with "use your own Claude/Codex subs" wedge. If hosted inference enters the picture later, reconsider.
- **Cross-engine (Unity, Godot)** — Ramen VR's Coplay acquisition already owns this. Focus wins.
- **NPC / conversational-AI runtime (Convai/Inworld territory)** — Different product, different buyer.
- **Full-featured image generation UI inside UE** — NYRA drives existing tools (ComfyUI, Meshy) rather than re-implementing their UX.
- **Codex / ChatGPT subscription driving (v1)** — Deferred to v1.1. Research flagged Codex CLI surface as LOW-confidence and keeping both CLIs doubles integration, auth-drift, and ToS-clearance work. Router is designed multi-backend so Codex drops in cleanly post-v1.
- **Computer-use as primary integration path for Meshy / ComfyUI / Blender** — These have APIs; using computer-use for them trades reliability for demo flash. API-first only; computer-use stays for Substance Sampler and UE modal dialogs.
- **Hosted backend for v1** — No Supabase/Railway in v1. RAG index ships bundled + updated via GitHub releases. Re-evaluate only if usage signal proves hosted is materially better.

## Context

**Market state (April 2026):** Generative-AI-in-gaming is a $2–5B segment growing ~23% CAGR. Unreal's share of Steam revenue rose from ~19% in 2023 to ~31% in 2024. The in-editor UE AI assistant category is no longer empty — Nwiro (Leartes), Aura (Ramen VR, Telos framework, 25× Blueprint error-reduction claim), Ultimate Engine CoPilot (BlueprintsLab, $220 perpetual, 1,050+ tool actions), and Ludus AI all compete. A long tail of free OSS MCP servers (chongdashu, flopperam, kvick-games, remiphilippe, others) sets the price floor at $0 for technical users.

**Competitive wedge:** The *combination* of three angles is the moat, not any single one:
1. **Economic** — uses the user's existing Claude + Codex subscriptions; no new bill.
2. **Capability** — image/video reference → full UE-native scene via Claude computer-use orchestrating external tools.
3. **Workflow** — the agent reaches outside UE to complete the loop (Meshy, Substance, ComfyUI, Blender) but delivers everything back as native UE assets.

**Technical environment:** Target users run Windows, pay for at least one of Claude (Pro/Max) or Codex (ChatGPT Plus/Pro/Business), have a mid-to-high-end GPU, and ship on UE 5.4–5.7. Competitors prove the category buys editor-native AI tooling.

**Resolved by research (April 2026):**

- Claude subscription driving: `claude -p --output-format stream-json` + `claude setup-token` (1-year OAuth), with `--mcp-config` injecting NYRA's MCP server. Verified ToS-safe (Anthropic prohibits embedding SDK; subprocessing user's CLI is the supported pattern).
- Sidecar language: Python — MCP Python SDK is mature and can also drive UE's built-in `unreal` Python module. No C++ MCP SDK exists.
- RAG backend: bundled LanceDB + BGE-small-en-v1.5 embeddings. No hosted backend in v1.
- Computer-use: `computer_20251124` with Opus 4.7 works, BUT recommended only for Substance Sampler + UE modal dialogs. Everything else uses APIs.

**Still-open research questions** (Phase 0/1 spike targets):

- Fab AI-plugin policy (2026) for plugins that drive external websites, subprocess user subs, bundle ML models — requires written clarification from Epic.
- UE 5.4 → 5.7 API drift matrix for Blueprint graph authoring, Material editing, NNE — requires empirical matrix test across all four versions.
- Meshy REST API pricing and rate limits (April 2026) — may impact v1 UX if limits are tight.
- Claude computer-use reliability percentiles on Substance 3D Sampler specifically, Windows 11 — hands-on canary.
- Legal-safe YouTube transcript ingestion scope + attribution model for the RAG corpus.

## Constraints

- **Tech stack**: Three-process model — UE5 C++ plugin shell (two modules: `NyraEditor`, `NyraRuntime`) + Python MCP sidecar (`NyraHost`) + llama.cpp inference process (`NyraInfer`). IPC via loopback WebSocket (UE↔Host), stdio JSON-RPC (MCP tool servers), stream-JSON stdio (Claude CLI), localhost HTTP (llama.cpp).
- **Platform**: Windows-only for v1 — keeps QA matrix small and aligns with Claude computer-use reliability
- **UE versions**: 5.4, 5.5, 5.6, 5.7 — matches the widest-supported competitor (Ultimate Engine CoPilot) to capture studios that can't jump versions immediately. Four-version CI matrix on day one of Phase 2 (avoids the ABI-drift trap).
- **Cost model**: Free on Fab — no backend billing; user provides their own Claude subscription. EV code-signing cert ($400–700/yr) is an explicit budget line.
- **AI backend (v1)**: Primary = user's Claude subscription via Claude Code CLI subprocess (`claude -p --output-format stream-json`, `claude setup-token` for OAuth). Fallback = Gemma 3 4B IT QAT Q4_0 GGUF (multimodal, 128K context) via llama.cpp / Ollama for offline, cheap, privacy-mode work. **Codex integration deferred to v1.1.**
- **External tools**: API-first (Meshy REST, ComfyUI HTTP, Blender Python). Computer-use (`computer_20251124`, Opus 4.7) only for Substance 3D Sampler and UE editor modal dialogs.
- **Distribution**: Fab-only for v1 — Epic's unified marketplace, credibility signal, built-in billing if Pro tier arrives. Direct-download fallback live *before* Fab submission (in case of rejection).
- **Legal**: Phase 0 pre-code legal gate — written ToS clarification from Anthropic (subscription-subprocess driving) and Epic (Fab AI-plugin policy) runs in parallel with Phase 1 plugin shell work. Only index public and license-compatible content; user's own paid materials stay on their machine.
- **Team**: Solo, full-time — roadmap must sequence for one person with clear "kill the scope" cut lines per phase.
- **Timeline**: 6–9 months to v1 Fab launch.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Three-process architecture (UE plugin + Python NyraHost + llama.cpp NyraInfer) | Converged recommendation from Stack + Architecture research; crash isolation; plugin never sees Claude auth tokens | — Pending |
| Python sidecar (not Rust / TypeScript) | MCP Python SDK is most mature; can also drive UE's built-in `unreal` Python module; fastest solo path to v1 | — Pending |
| Subprocess-drive Claude Code CLI (not embed Agent SDK) | Anthropic ToS prohibits third-party claude.ai login embedding; subprocessing user's own CLI is the supported pattern | — Pending |
| Drop Codex from v1 — defer to v1.1 | Halves CLI integration + legal + auth surface; Codex CLI surface is LOW-confidence in current research; router designed multi-backend so drop-in post-v1 | — Pending |
| Gemma 3 4B IT QAT Q4_0 GGUF (multimodal) as local fallback | Verified current: 3.16 GB, 128K context, text+image. Covers offline, low-cost, NDA/privacy | — Pending |
| API-first external integrations; computer-use as last resort | Reliability-over-flash for launch demo. Meshy REST / ComfyUI HTTP / Blender Python are primary; Substance Sampler + UE modals via computer-use | — Pending |
| Pre-code legal gate runs in parallel with Phase 1 shell work | Founder decision: don't block plugin-shell work on legal emails, but don't write subscription-driving code until legal clears | — Pending |
| Free Fab plugin for v1, Dual SKU deferred | Maximize adoption; validate usage before building paid backend | — Pending |
| UE 5.4–5.7 support, four-version CI on day one of Phase 2 | Widest competitor-matching matrix; deferring CI is the ABI-drift trap | — Pending |
| Windows-only for v1 | Smaller QA matrix; computer-use is most reliable on Windows | — Pending |
| Launch demo = reference video → matched UE shot | No competitor ships this; sets the benchmark. Image → scene is the Phase-6 fallback demo if time is tight | — Pending |
| Claude-only for v1 reasoning (Codex deferred) | Simpler launch story, simpler ToS posture; v1.1 adds Codex for expanded economic wedge | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-21 after research synthesis — Codex deferred to v1.1, Python sidecar locked, API-first external tools, Phase 0 legal gate in parallel with Phase 1*
