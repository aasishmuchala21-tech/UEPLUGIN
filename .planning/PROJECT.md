# NYRA

## What This Is

NYRA is a free Unreal Engine 5 plugin, distributed on Fab, that gives UE developers an in-editor AI agent powered by their existing Claude and Codex subscriptions (no new API bills). It combines a deep, continuously-updated knowledge of UE5 with Claude computer-use to take real action — driving external tools like Meshy, Substance, ComfyUI, and Blender — and route the results back into the editor as native UE assets, scenes, and blueprints. Built for solo devs, indies, and studios who want a single agent that can go from a reference image or YouTube clip to a lit, dressed, playable Unreal scene.

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
- [ ] Plugin works with no API keys — agent uses the user's Claude subscription (via Claude Code) and Codex subscription (via Codex CLI) on their machine
- [ ] Plugin falls back to a local Gemma 4B model for offline, low-cost, and privacy-mode operation

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

**Computer-use for asset generation and tool orchestration**
- [ ] Agent can drive Meshy (image → 3D model) end-to-end from inside UE, auto-importing the result as a UE StaticMesh
- [ ] Agent can drive Substance 3D Sampler (image → PBR material) and auto-import as a UE Material
- [ ] Agent can drive a locally-installed ComfyUI for image-to-image workflows (textures, references, variations)
- [ ] Agent can drive Blender for mesh cleanup / retopology before importing into UE
- [ ] Computer-use can click inside the UE editor for operations the Unreal API does not expose

**Reference-driven workflows**
- [ ] User can attach an image to the chat — NYRA creates a scene (models + materials + lighting) that matches it
- [ ] User can paste a YouTube link or attach a video file — NYRA analyzes lighting, composition, and camera direction, then replicates it in UE via Sequencer (**launch demo**)
- [ ] User can attach a UE tutorial video — NYRA turns it into an executable plan and runs it

**Distribution & onboarding**
- [ ] Listed on Fab as a free plugin with demo video
- [ ] Zero-config install: open UE, enable plugin, sign into Claude Code + Codex CLI once, go
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

## Context

**Market state (April 2026):** Generative-AI-in-gaming is a $2–5B segment growing ~23% CAGR. Unreal's share of Steam revenue rose from ~19% in 2023 to ~31% in 2024. The in-editor UE AI assistant category is no longer empty — Nwiro (Leartes), Aura (Ramen VR, Telos framework, 25× Blueprint error-reduction claim), Ultimate Engine CoPilot (BlueprintsLab, $220 perpetual, 1,050+ tool actions), and Ludus AI all compete. A long tail of free OSS MCP servers (chongdashu, flopperam, kvick-games, remiphilippe, others) sets the price floor at $0 for technical users.

**Competitive wedge:** The *combination* of three angles is the moat, not any single one:
1. **Economic** — uses the user's existing Claude + Codex subscriptions; no new bill.
2. **Capability** — image/video reference → full UE-native scene via Claude computer-use orchestrating external tools.
3. **Workflow** — the agent reaches outside UE to complete the loop (Meshy, Substance, ComfyUI, Blender) but delivers everything back as native UE assets.

**Technical environment:** Target users run Windows, pay for at least one of Claude (Pro/Max) or Codex (ChatGPT Plus/Pro/Business), have a mid-to-high-end GPU, and ship on UE 5.4–5.7. Competitors prove the category buys editor-native AI tooling.

**Open research questions** (to be resolved in the research phase):
- How exactly does a third-party plugin invoke the user's Claude subscription? Claude Code CLI subprocess vs. MCP-to-Claude-Desktop vs. both. Same question for Codex.
- Does UE's Neural Network Engine (NNE) with bundled ONNX models beat a local ComfyUI subprocess for image→mesh / image→texture, on quality, latency, and plugin size?
- Is hosted RAG (Supabase pgvector, Railway Weaviate) materially better than a bundled LanceDB/Qdrant-lite index updated via GitHub releases, for a free plugin?
- What's the legal-safe corpus for the UE5 knowledge index, and how is attribution handled for YouTube transcripts?
- How reliable is Claude computer-use on Windows for automating Meshy web UI, Substance 3D Sampler, and ComfyUI, as of April 2026?

## Constraints

- **Tech stack**: UE5 C++ plugin (hybrid architecture — thin C++ shell hosting an MCP client/server) — required for native editor integration and Fab distribution
- **Platform**: Windows-only for v1 — keeps QA matrix small and aligns with Claude computer-use reliability
- **UE versions**: 5.4, 5.5, 5.6, 5.7 — matches the widest-supported competitor (Ultimate Engine CoPilot) to capture studios that can't jump versions immediately
- **Cost model**: Free on Fab — no backend billing; user provides their own Claude/Codex subs
- **AI backend**: Primary = user's Claude + Codex subscriptions via CLI/MCP; Fallback = Gemma 4B local model (offline, cheap, privacy)
- **Distribution**: Fab-only for v1 — Epic's unified marketplace, credibility signal, built-in billing if Pro tier arrives
- **Legal**: Only index public and license-compatible content; user's own paid materials stay on their machine
- **Team**: Solo, full-time — roadmap must sequence for one person with clear "kill the scope" cut lines per phase
- **Timeline**: 6–9 months to v1 Fab launch

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hybrid C++ shell + MCP bridge architecture | Native editor integration + fast agent iteration; avoids pure-Python runtime dependency | — Pending |
| Use user's Claude + Codex subscriptions instead of API keys | Core economic wedge vs. competitors; removes a second AI bill for the buyer | — Pending |
| Gemma 4B local fallback model | Covers offline, low-cost, and NDA/privacy scenarios without hitting subs | — Pending |
| Claude computer-use as the action layer | User-stated "most important piece"; lets NYRA reach tools UE doesn't expose | — Pending |
| Free Fab plugin for v1, Dual SKU deferred | Maximize adoption; validate usage before building paid backend | — Pending |
| UE 5.4–5.7 support | Widest competitor-matching matrix; captures studios stuck on older versions | — Pending |
| Windows-only for v1 | Smaller QA matrix; computer-use is most reliable on Windows | — Pending |
| Launch demo = reference video → matched UE shot | Best wedge demo; showcases video understanding + scene assembly + computer-use in one take | — Pending |

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
*Last updated: 2026-04-21 after initialization*
