# Feature Landscape: NYRA — UE5 AI Assistant Plugin

**Domain:** In-editor AI agent for Unreal Engine 5 (solo devs → studios), Windows, UE 5.4–5.7
**Researched:** 2026-04-21
**Confidence:** MEDIUM overall (HIGH on UE API surface and competitor category scope, MEDIUM on specific per-competitor tool inventories since those counts came from prior market research and were not re-verified here, MEDIUM on computer-use reliability which is a known open research question from `PROJECT.md`)

---

## How to Read This Document

Every feature is tagged with:

- **Category** — Table stakes (TS) / Differentiator (D) / Anti-feature (AF)
- **Complexity** — XS (hours) / S (days) / M (1–2 weeks) / L (3–6 weeks) / XL (> 6 weeks) for a solo full-time builder already past the plugin-scaffolding hump
- **UE subsystem** — which editor/runtime surface the feature touches (Blueprint / Material / Sequencer / Niagara / PCG / MetaSound / Landscape / World Partition / Asset Registry / Level / Lighting / Chaos / Audio / AnimationSystem / Build / Editor UI)
- **API stance** — `DOCUMENTED` (Epic-exposed Editor Scripting or C++ API), `PARTIAL` (some things work, others need editor subsystem poking), `FRICTION` (undocumented, requires reflection/Slate hacks, or needs computer-use), `COMPUTER-USE` (no reliable API path — drive the editor UI)
- **Backend** — Claude (reasoning/planning/tool-calls), Codex (code-gen / Blueprint-as-code translation), Computer-Use (Claude drives OS/GUI), Gemma (local fallback), RAG (indexed docs)
- **Depends on** — other features that must exist first

Complexity estimates assume the MCP bridge and native C++ tool-dispatch shell are already working (those are Phase 0 plumbing, not features).

---

## Competitor Baseline (April 2026)

From the prior competitive analysis referenced in `PROJECT.md`:

| Competitor | Count of exposed "tools/actions" | What that count actually implies |
|---|---|---|
| **Ultimate Engine CoPilot (BlueprintsLab)** | ~1,050 actions | Near-complete wrapper over `UnrealEditor-Python` + editor subsystems. Every asset CRUD op, every common node type, every project/package command is its own action. Exhaustive-by-breadth. |
| **Nwiro Pro (Leartes)** | ~209 native C++ tools | Curated, hand-written C++ tool set. Fewer, more opinionated — scene-centric (Leartes is an environment-art studio). Emphasis: asset search, one-prompt scene, cinematic camera, material authoring. |
| **Aura (Ramen VR)** | 43 tools + "Dragon Agent" | Small hand-curated toolset + a meta-agent layer. 25× Blueprint error-reduction claim implies heavy investment in Blueprint graph *validation* — compile loop, type-checking, node-wiring heuristics — not just generation. |
| **Ludus AI** | (not public) | Positioning: Blueprint & C++ code-gen assistant with scene generation; aimed at indies. |

**What this tells us about the table-stakes floor:**

Any plugin shipping fewer than ~40 primitives that cover {Blueprint CRUD, actor/level CRUD, material CRUD, asset search, docs Q&A, chat UI} will feel incomplete on arrival. CoPilot's 1,050 is the *ceiling* (mostly padding); Aura's 43 is the *floor*. NYRA needs to hit the floor for credibility and spend complexity budget on the differentiators, not on racing CoPilot to 1,050.

---

## Table Stakes

Ship these or users bounce within 10 minutes of install.

### 1. In-editor chat panel with history, attachments, status

**Category:** TS | **Complexity:** S | **UE subsystem:** Editor UI (Slate / UMG for editor) | **API stance:** DOCUMENTED | **Backend:** Claude | **Depends on:** nothing

Dockable editor tab, streaming tokens, markdown rendering, code blocks, file/image/video attachments, per-conversation history persisted to project `Saved/`, current-task status pill ("Planning / Calling Meshy / Importing…"), cancel button. This is the shell every competitor has — no innovation here, just don't ship a worse one.

**Competitor parity:** All four (Nwiro, Aura, CoPilot, Ludus) have a chat dock. Aura's is the most polished today.

**Watchouts:** Slate's styling API ages poorly across 5.4 → 5.7. Expect per-version tweaks.

### 2. UE5 Documentation & Blueprint Reference Q&A (RAG)

**Category:** TS | **Complexity:** M | **UE subsystem:** none (runs in agent, not UE) | **API stance:** n/a | **Backend:** RAG + Claude, Gemma for offline | **Depends on:** chat panel

Bundled vector index covering official UE5 docs (5.4–5.7), Blueprint node reference, C++ API, Epic forums, public community transcripts (license-safe), YouTube tutorial transcripts with attribution. Answers cite sources. Index refreshable on UE version bumps.

**Competitor parity:** CoPilot and Aura both do this. Nwiro less so (scene-first product). The bar is "citations + version-aware."

**Why table stakes:** Solo devs use this more than any other feature. Being wrong or un-cited here is a trust killer.

### 3. Blueprint read / write / rewire

**Category:** TS | **Complexity:** L | **UE subsystem:** Blueprint, Kismet | **API stance:** PARTIAL (EditorScripting + K2 nodes reachable via reflection; Blueprint *graph mutation* is partially undocumented — most competitors wrote custom C++ for this) | **Backend:** Claude + Codex | **Depends on:** chat panel

Reading a Blueprint graph, exposing its nodes + wires as structured JSON to the agent, having the agent add/remove/reconnect nodes, set variable defaults, add components, hook events, and compile. Must handle: function libraries, macros, event graphs, construction scripts, animation blueprints (limited), widget blueprints.

**Competitor parity:**
- Aura's "25× Blueprint error reduction" claim lives here — they invested hard in the compile/validate loop.
- CoPilot exposes this as dozens of granular actions ("add node", "connect pins", "set default value").
- Nwiro does less graph surgery; more "create new Blueprint from template."

**NYRA approach:** Codex is the right backend for this — it's literally code-gen. Treat the Blueprint graph as a serializable AST, let Codex produce diffs, compile, feed errors back.

**Watchouts:** K2 pin type system is byzantine. Expect bugs on wildcard pins, interface casts, and soft references.

### 4. Blueprint debug — explain + propose fix + apply

**Category:** TS | **Complexity:** L | **UE subsystem:** Blueprint compiler, Message Log, Output Log | **API stance:** PARTIAL | **Backend:** Claude + Codex | **Depends on:** Blueprint read/write

Intercept compile errors and runtime "Blueprint Runtime Error" messages, feed them + the surrounding graph to the agent, get a plain-English explanation and a proposed diff, one-click apply, re-compile, loop until clean or gave up.

**Competitor parity:** Aura leads here (Dragon Agent). CoPilot and Ludus have basic versions.

**Why table stakes:** This is the first thing users test. If the demo is "fix this broken Blueprint," and you fail, they uninstall.

### 5. Asset search & tagging

**Category:** TS | **Complexity:** M | **UE subsystem:** Asset Registry, Content Browser | **API stance:** DOCUMENTED (`FAssetRegistryModule`) | **Backend:** RAG (local embeddings over asset names + tags + thumbnails) | **Depends on:** nothing

Semantic search across the project's Content: "find me all hero weapon meshes," "show me the rusty metal materials." Needs local thumbnail embeddings (CLIP-like) for visual search. Agent can also auto-tag newly imported assets.

**Competitor parity:** Nwiro leans on this heavily (scene assembly needs asset discovery). CoPilot has a keyword-level version.

**NYRA approach:** Don't ship v1 with full thumbnail embeddings — defer to Phase 2. V1: structured Asset Registry queries + name/tag fuzzy search. That's enough to be useful and keeps the scope honest.

### 6. Basic scene operations (spawn / move / delete / select actors)

**Category:** TS | **Complexity:** S | **UE subsystem:** Level, Editor, EditorScripting | **API stance:** DOCUMENTED (`UEditorActorSubsystem`, `UEditorLevelLibrary`) | **Backend:** Claude | **Depends on:** asset search (to know *what* to spawn)

Spawn actor by class or asset path, set transform, duplicate, delete, select, group. Also: snap-to-ground, align-to-surface, random-in-radius. The primitives a scene-builder needs. Every competitor has this; ship the CRUD, don't innovate yet.

### 7. Material & texture operations

**Category:** TS | **Complexity:** M | **UE subsystem:** Material, Texture | **API stance:** PARTIAL (Material Instance params: DOCUMENTED; creating full Material graphs: FRICTION — most people create MICs, not MIs programmatically) | **Backend:** Claude + Codex | **Depends on:** asset search

Read a material or material instance, list parameters, change scalar/vector/texture params, create a Material Instance from a parent, swap base color textures, generate PBR channel-packed textures (via Substance / ComfyUI — see differentiators). Creating material *graphs* from scratch is hard and not v1 — stick to MIC param editing + template instantiation.

**Competitor parity:** Nwiro and CoPilot do MIC param editing. Nobody reliably authors material graphs via AI yet (this is a known open area).

### 8. Project/console command execution

**Category:** TS | **Complexity:** XS | **UE subsystem:** Engine console, CVars | **API stance:** DOCUMENTED | **Backend:** Claude | **Depends on:** nothing

`GEngine->Exec` wrapper exposed as a tool. Agent can run `stat unit`, `r.ScreenPercentage 75`, `showflag.lighting 0`. Tiny feature, enormous leverage — the agent uses this constantly for introspection.

### 9. Output Log / Message Log streaming

**Category:** TS | **Complexity:** XS | **UE subsystem:** Logging | **API stance:** DOCUMENTED (`FOutputDevice`) | **Backend:** Claude | **Depends on:** nothing

Agent can read the last N lines of the Output Log and filter by category. Feeds the debug loop (feature 4) but also general troubleshooting. Trivial to build; disproportionately useful.

### 10. Subscription connection status

**Category:** TS | **Complexity:** S | **UE subsystem:** Editor UI | **API stance:** n/a | **Backend:** Claude Code CLI / Codex CLI health checks | **Depends on:** chat panel

Surface which of {Claude Code, Codex CLI, Gemma local, computer-use} are connected, which features each unlocks, and what to do when one is missing. Non-negotiable given the "use your own subs" wedge — if a user doesn't know *why* a command failed (no Codex CLI installed), they'll churn.

### 11. Cancel / interrupt / rollback

**Category:** TS | **Complexity:** M | **UE subsystem:** Transactions (`FScopedTransaction`) | **API stance:** DOCUMENTED | **Backend:** n/a | **Depends on:** all mutation features

Every agent action that mutates the project must be wrapped in a UE transaction so Ctrl+Z works. The agent also needs an explicit "cancel current task" that unwinds any in-flight computer-use subprocess. Users will trust the agent roughly zero percent the first time they try it; undo must be bulletproof.

**Competitor parity:** CoPilot and Aura both support undo on most actions. This is a *must*, not a nice-to-have.

### 12. Safe-mode / dry-run

**Category:** TS | **Complexity:** S | **UE subsystem:** n/a | **API stance:** n/a | **Backend:** Claude | **Depends on:** chat panel

"Show me what you'd do before you do it." Agent outputs a plan (list of tool calls with args), user approves or edits, then it runs. Toggleable. Critical for studio adoption — no lead designer green-lights an agent that ships actions silently.

**Competitor parity:** CoPilot has preview mode. Aura's Dragon Agent does plan-then-execute. This is becoming a standard.

---

## Differentiators

These are where NYRA earns its position. Ordered by wedge weight, not complexity.

### D1. Reference video → matched UE shot (LAUNCH DEMO)

**Category:** D | **Complexity:** XL | **UE subsystem:** Sequencer, CineCamera, Lighting, Level | **API stance:** PARTIAL (Sequencer has a scripting API; camera/shot assembly is documented; *visual analysis* of the reference is all on the agent side) | **Backend:** Claude (video/vision) + Computer-Use (drive ComfyUI for still extraction) + Codex (Sequencer code-gen) | **Depends on:** scene building, lighting authoring, Sequencer automation, asset search, Meshy/ComfyUI bridges

The headline. User attaches a YouTube link or mp4; NYRA extracts keyframes, infers shot composition (framing, focal length, camera movement), lighting (key/fill/rim, color temperature, sky state), approximate geometry/asset categories ("a lone figure on a wet street at dusk"), then assembles a matching UE scene with Sequencer-driven camera.

**Why it's a moat:** Nwiro does one-prompt scenes from *text/image*. None of Nwiro/Aura/CoPilot/Ludus ships video→shot as of April 2026. The demo value is enormous — virtual production studios, pre-viz teams, and indie cinematics are all buyers.

**Scope cut lines for v1:**
- V1: short clips (≤ 10s), single shot, single location. One camera, one key + one fill light, one placed hero asset, sky + fog.
- V2: multi-shot sequences, camera movement curve-fitting from optical flow.
- V3: character blocking / animation matching.

**Known risks:** Video understanding quality from Claude's vision; keyframe→3D-pose is an unsolved problem (we sidestep by going 2.5D and relying on the user's asset library + Meshy for hero mesh). Flag as needing a spike in the research phase before committing.

### D2. Image → full UE-native scene (parity + one level up from Nwiro)

**Category:** D | **Complexity:** L | **UE subsystem:** Level, Lighting, Material, Asset Registry | **API stance:** DOCUMENTED for the UE side, COMPUTER-USE for external tool orchestration | **Backend:** Claude (vision + planning) + Computer-Use (Meshy, Substance, ComfyUI) + Codex (glue code) | **Depends on:** scene building, asset search, material ops, Meshy/Substance/ComfyUI bridges, lighting

User drops an image into chat. NYRA identifies objects, materials, lighting, mood; checks the project's asset library for matches; generates missing hero assets via Meshy; generates missing textures via Substance Sampler or ComfyUI; assembles actors at inferred positions; authors lighting to match; optionally adds fog / post-process.

**Why it's a differentiator vs Nwiro:**
- Nwiro's one-prompt scene uses *their* asset pool (Leartes Studios assets). Great quality, narrow style.
- NYRA uses the *user's* asset library first, then generates anything missing. The result is style-consistent with what the user already has — which is what indies and studios actually want.
- Computer-use orchestration across Meshy + Substance + ComfyUI means the missing-asset pipeline is broader than any one closed library.

**Scope cut lines for v1:**
- V1: indoor static scenes, 5–20 actors, one light setup, hero materials only.
- V2: outdoor scenes with landscape/foliage.
- V3: dynamic scenes (Niagara, characters).

### D3. Claude + Codex subscription driving (economic wedge)

**Category:** D | **Complexity:** M (invocation mechanics) + S (connection UX) + M (reliability retry/fallback) | **UE subsystem:** n/a (plugin IPC) | **API stance:** FRICTION (no official "plug into someone else's Claude sub" API — the route is Claude Code CLI subprocess and/or MCP client to Claude Desktop) | **Backend:** Claude Code CLI + Codex CLI + MCP | **Depends on:** nothing, but gates *everything*

This is the core economic wedge and the trickiest piece architecturally. Two viable paths, probably both:

1. **Subprocess path** — spawn `claude` / `codex` CLIs, pipe prompts and tool defs via stdin, stream results. Works today on Windows; users must have the CLIs installed and logged in.
2. **MCP-to-Desktop path** — plugin exposes an MCP server that Claude Desktop / Claude Code connects to; the user initiates tasks from Claude side with UE as a tool surface.

**Why it's a differentiator:** Every competitor bills for inference — Aura's Telos, Ludus, CoPilot all wrap a hosted API, either passed through or branded. NYRA's "bring your own $20/mo sub, no extra bill" wedge is unique and is the #1 reason indies will choose NYRA.

**Open research (flagged in `PROJECT.md`):** exact CLI surface for programmatic streaming + tool-use on each provider, rate-limit handling, session re-use, multi-turn context.

**Anti-feature link:** This is *why* we don't fine-tune our own UE-specialist model (AF4) — it invalidates the wedge.

### D4. Computer-use orchestration of Meshy / Substance / ComfyUI / Blender

**Category:** D | **Complexity:** XL (end-to-end reliable across 4 tools) | **UE subsystem:** Import pipeline (FBX/GLTF/PNG/EXR import factories) | **API stance:** COMPUTER-USE for external tools, DOCUMENTED for import | **Backend:** Computer-Use (primary) + Claude (planning) | **Depends on:** import handlers per tool

The action layer. NYRA's agent doesn't call Meshy's API directly — it *drives the Meshy web UI* via Claude computer-use (per locked decision in `PROJECT.md`). Same for Substance 3D Sampler, a locally-installed ComfyUI, and Blender for mesh cleanup / retop. Outputs are watched for, auto-imported, and placed.

**Why computer-use over direct APIs:**
- Meshy/Substance APIs exist but cost money or need paid tiers; computer-use rides the user's existing tool sub.
- ComfyUI is inherently graph/UI-based — much of what advanced users do is node-graph tweaking that's faster to drive visually than to re-implement.
- Blender has a Python API, but users have their own scripts and add-ons; driving the UI is more general.

**Per-tool complexity:**

| Tool | Complexity | Notes |
|---|---|---|
| Meshy (image→3D) | L | Web UI, login state, job queue, download handoff — brittle to UI changes. |
| Substance 3D Sampler (image→PBR) | L | Desktop app, file-based I/O makes the import side easy; driving the UI is the risk. |
| ComfyUI | M | Local, scriptable via JSON workflow API — can mix computer-use with API calls, easier than Meshy. |
| Blender | M | Headless CLI mode + Python scripts is the reliable path; computer-use only for interactive mesh cleanup. |

**Scope cut lines:** V1 = Meshy (highest ROI) + ComfyUI (most flexible). Substance + Blender move to V2.

**Launch risk:** Computer-use reliability on Windows for web-UI apps is a known open research question in `PROJECT.md`. This is the single biggest delivery risk in the whole product. A Phase-specific spike belongs before committing to the v1 scope.

### D5. Gemma 4B local fallback

**Category:** D | **Complexity:** M | **UE subsystem:** NNE (Neural Network Engine) or an external `llama.cpp` process | **API stance:** PARTIAL (NNE ships with UE 5.5+; loading GGUF via NNE isn't a first-class path — `llama.cpp` subprocess is simpler) | **Backend:** Gemma 4B, local | **Depends on:** chat panel, subscription status

Covers: offline use, NDA/privacy mode, users without a Claude/Codex sub, CI/batch jobs. Good enough for: docs Q&A, asset search, small Blueprint tweaks, console-command automation. Not good enough for: scene synthesis, video analysis, complex Blueprint graph surgery.

**Why differentiator:** None of the four main competitors ship an offline fallback. For enterprise / NDA / regulated customers this is table stakes *for them* — which makes it a differentiator for NYRA vs. the current field.

### D6. YouTube-tutorial-to-executable-plan

**Category:** D | **Complexity:** L | **UE subsystem:** depends on tutorial contents (often Blueprint + Level) | **API stance:** PARTIAL | **Backend:** Claude (video understanding) + Codex (translation to tool calls) + tools from TS and other D features | **Depends on:** Blueprint read/write, scene building, asset search, docs Q&A

User pastes a YouTube tutorial URL or drops an .mp4. NYRA transcribes + visually parses, produces an executable step-list ("create Blueprint X, add these nodes, set these defaults, compile"), user approves plan, NYRA executes with pause-per-step.

**Why differentiator:** The "I learned UE from YouTube" persona is huge. Nobody ships "turn this tutorial into applied code" today. This is a retention hook — a user who gets one tutorial auto-applied will never uninstall.

**Scope cut lines for v1:** Short (<15 min) Blueprint-only tutorials. Defer level-design tutorials, character animation tutorials, multiplayer tutorials.

### D7. Sequencer automation for virtual production

**Category:** D | **Complexity:** L | **UE subsystem:** Sequencer (`ULevelSequence`, `UMovieScene`), CineCamera | **API stance:** DOCUMENTED (`LevelSequenceEditor`, `SequencerScripting` module) | **Backend:** Claude + Codex | **Depends on:** scene building, lighting

Create level sequences, add camera cuts, set keyframes on actor/camera/light/post-process params, author shot blocking from natural language ("slow push-in on the hero, then cut wide"). Feeds D1 (video→shot).

**Competitor parity:** Nwiro has *some* cinematic composition; Aura and CoPilot have Sequencer touch-ups. None have strong natural-language shot blocking.

### D8. Lighting authoring (sky, sun, fog, post-process, exposure)

**Category:** D | **Complexity:** M | **UE subsystem:** Lighting (`ULightComponent`, SkyAtmosphere, VolumetricCloud, ExponentialHeightFog, PostProcessVolume) | **API stance:** DOCUMENTED | **Backend:** Claude | **Depends on:** scene building

"Make it golden hour." "Harsh overhead with strong volumetrics." "Match this reference image's mood." The agent sets directional light angle/color/intensity, sky/cloud params, fog density/color, PPV color grading, exposure. Enables D1 and D2.

**Competitor parity:** Nwiro has cinematic presets. CoPilot has granular light-property actions. "Match this image's lighting" is not well-covered today — that's the differentiator angle.

### D9. Natural-language asset tagging + thumbnail embeddings

**Category:** D | **Complexity:** L | **UE subsystem:** Asset Registry + local embedding DB | **API stance:** DOCUMENTED for tags, in-plugin for embeddings | **Backend:** local CLIP-like model | **Depends on:** asset search (baseline)

Upgrade to feature 5 (asset search). Every mesh/material/texture gets a local CLIP embedding at import; semantic queries become "find me weather-worn barn wood," not "find anything named barn." This is what makes D2 (image→scene) actually re-use the user's library.

**Scope:** V2, not V1. Ship the baseline first.

### D10. Local project-knowledge RAG

**Category:** D | **Complexity:** M | **UE subsystem:** Asset Registry | **API stance:** DOCUMENTED | **Backend:** local embeddings + Claude | **Depends on:** asset search

Index the user's own project: Blueprint comments, function names, struct fields, C++ header comments, level notes. Agent answers "where do we spawn the boss?" by citing *their* code. Massive productivity win; no competitor does this well today.

---

## Adjacent / Defer-to-later Features (not v1, but map them)

These are real features in competitor products. We're deliberately *not* shipping them in v1, but they're not anti-features — they may land in v2+. Listed here so roadmap phasing is explicit.

### Character / animation pipeline automation (IK Rig, Motion Matching, State Tree)

**Category:** defer-v2 | **Complexity:** XL | **UE subsystem:** AnimationSystem, ControlRig | **API stance:** FRICTION (Animation Blueprint graphs are quirky; Control Rig is code-heavy) | **Backend:** Claude + Codex | **Depends on:** Blueprint read/write

Authoring AnimBPs, setting up IK Rig retargets, configuring Motion Matching databases, editing State Trees. Huge scope, niche-specialist audience. Revisit after launch traction.

### Niagara VFX authoring

**Category:** defer-v2 | **Complexity:** XL | **UE subsystem:** Niagara | **API stance:** FRICTION (Niagara graphs have limited scripting support) | **Backend:** Claude + Codex | **Depends on:** Blueprint read/write

Niagara is notoriously hard to automate — the graph editing API is thin. Competitors don't do this well either. Not a v1 differentiator because it's so hard to land reliably.

### Procedural content generation (PCG)

**Category:** defer-v2 | **Complexity:** L | **UE subsystem:** PCG | **API stance:** PARTIAL (PCG graphs are scriptable but the node surface is huge) | **Backend:** Claude + Codex | **Depends on:** Blueprint read/write

Generate a PCG graph from "scatter these rocks naturally, avoiding water, denser near cliffs." Strong differentiator potential for open-world devs. Defer because it's deep and its audience is narrow.

### MetaSounds / audio authoring

**Category:** defer-v2 | **Complexity:** L | **UE subsystem:** MetaSounds | **API stance:** PARTIAL | **Backend:** Claude + Codex | **Depends on:** Blueprint read/write (MetaSounds uses the same graph infra)

SFX placement (triggering sound attached to actors or events) is S-complexity — easy. Authoring *MetaSound graphs* is L. Defer the graph authoring; maybe include trivial SFX placement in v1 as a bonus.

### Landscape / World Partition operations

**Category:** defer-v2 | **Complexity:** XL | **UE subsystem:** Landscape, World Partition, Foliage | **API stance:** PARTIAL | **Backend:** Claude | **Depends on:** scene building

Sculpt terrain, paint landscape material layers, paint foliage, manage World Partition cells. Narrow audience (open-world devs). Defer.

### Multiplayer / networking Blueprint work

**Category:** defer-v2 | **Complexity:** L | **UE subsystem:** Blueprint + Replication | **API stance:** PARTIAL | **Backend:** Claude + Codex | **Depends on:** Blueprint read/write

Setting up replicated variables, RPCs, client/server role checks. This is where bugs live — and where an AI agent with a *verify loop* could shine. Worth v2; too risky for v1 (one wrong `NetMulticast` and you break a game).

### Packaging / build automation

**Category:** defer-v2 | **Complexity:** M | **UE subsystem:** Project, UBT | **API stance:** DOCUMENTED (UAT, UBT command line) | **Backend:** Claude | **Depends on:** nothing

"Cook and package a Windows Shipping build." Useful, but a shell script does this today. Low differentiator value. Defer.

---

## Anti-features

Deliberately **not** building in v1. Reasoning attached.

### AF1. NPC conversation runtime

**What:** In-game NPC dialogue driven by live LLM inference.
**Why not:** Convai and Inworld own this category; it's a runtime/gameplay product, not an editor tool. Different buyer, different integration surface (runtime networking, latency, moderation). Building it would dilute NYRA's editor-agent positioning.
**Instead:** If a user wants NPC conversation, NYRA can help them *integrate Convai or Inworld* — that's an editor task, not a runtime one.

### AF2. Cross-engine support (Unity, Godot)

**What:** Same product for Unity/Godot.
**Why not:** Ramen VR's Coplay acquisition and others already cover this seam. Multi-engine means half the API investment per engine — the moat is depth, not breadth. `PROJECT.md` locks this.
**Instead:** Go deep on UE 5.4–5.7.

### AF3. Full image generation UI inside UE

**What:** Re-implementing a ComfyUI-like or Stable-Diffusion UI inside the UE editor.
**Why not:** It's a whole product; we'd end up maintaining a second app. Computer-use lets us drive ComfyUI (the user's preferred tool) cleanly.
**Instead:** Ship a "generate texture" command that drives ComfyUI in the background and imports the result. No in-editor image UI.

### AF4. Fine-tuned UE-specialist model

**What:** Training or fine-tuning our own model on UE content.
**Why not:** Breaks the "use your Claude/Codex sub" economic wedge. Also: compute-expensive, requires hosting, opens a second product surface. `PROJECT.md` locks this.
**Instead:** Lean on Claude + Codex + RAG. If hosted inference ever makes sense, it's a v3 conversation, not a v1.

### AF5. Ingesting paid courses as RAG corpus

**What:** Indexing Udemy, Unreal Fellowship, paid YouTube memberships, etc.
**Why not:** Copyright + ToS minefield. Legal risk dwarfs the value.
**Instead:** Users may point NYRA at their *own* purchased materials locally — NYRA indexes, but never redistributes. Bundled corpus is license-safe only.

### AF6. Hosted backend / SaaS features in v1

**What:** Auth servers, hosted RAG, team features, per-seat billing.
**Why not:** Free Fab plugin first, validate usage, *then* consider. Locked in `PROJECT.md`.
**Instead:** Everything runs locally in v1. Maybe scaffold Supabase/Railway *only if* research proves hosted RAG beats bundled.

### AF7. Creating full Material graphs from scratch via AI

**What:** Generating new Material assets with custom graphs.
**Why not:** Material graph authoring via AI is unreliable across the industry today — too many node types, too many subtle rules (sampler counts, texture coordinate semantics, shader compile limits). Low success rate → trust-destroying feature.
**Instead:** Material *Instance* editing (MIC param changes) is TS and ships in v1. For net-new materials, drive Substance Sampler (D4) for the hard authoring and import as a UE Material.

### AF8. Animation graph authoring

**What:** AI-authored AnimBPs, State Trees, Control Rigs.
**Why not:** Complexity like Material graphs — many subtle rules, high failure cost (broken rig → broken character). Not a v1 win.
**Instead:** Defer to v2 (see adjacent features). V1 can *read* AnimBPs for context but won't rewrite them.

---

## Feature Dependency Graph

```
Chat panel (TS1)
  ├── Subscription status (TS10)
  ├── Safe-mode/dry-run (TS12)
  ├── Cancel/rollback (TS11)
  ├── Output Log tool (TS9)
  ├── Console command tool (TS8)
  ├── Docs RAG (TS2)
  │   └── Local project RAG (D10)
  └── Asset search baseline (TS5)
      ├── NL asset tagging + embeddings (D9)
      ├── Scene ops: spawn/move/delete (TS6)
      │   ├── Material ops (TS7)
      │   │   └── Substance bridge (D4 partial)
      │   ├── Lighting authoring (D8)
      │   ├── Image → scene (D2)
      │   │   ├── Meshy bridge (D4)
      │   │   ├── ComfyUI bridge (D4)
      │   │   └── Substance bridge (D4)
      │   └── Sequencer automation (D7)
      │       └── Video → matched shot (D1)  ← LAUNCH DEMO
      └── Blueprint read/write (TS3)
          ├── Blueprint debug loop (TS4)
          ├── YouTube tutorial → plan (D6)
          └── (defer) AnimBP, Niagara, PCG, MetaSound, Multiplayer

Subscription driving (D3) gates ALL Claude/Codex-backed features.
Gemma fallback (D5) is the backup path when D3 is unavailable.
Computer-use (D4) gates all external tool bridges.
```

**Critical path to launch demo (D1):**
TS1 → TS5 → TS6 → D8 → D7 → D1 (with D4 + D2 running parallel for asset generation).

---

## MVP Recommendation

A ruthless MVP ordered by "what does the launch demo need + what do users bounce on if missing":

**Must-ship v1:**

1. TS1 Chat panel with history + attachments
2. TS10 Subscription status UI
3. D3 Claude + Codex subscription driving
4. TS11 Cancel / transaction-wrapped rollback
5. TS12 Safe-mode / dry-run
6. TS2 Docs RAG (bundled, UE 5.4–5.7)
7. TS5 Asset search (baseline, no thumbnails)
8. TS6 Scene ops (spawn / move / delete)
9. TS7 Material ops (MIC params)
10. TS8 Console command tool
11. TS9 Output Log tool
12. TS3 Blueprint read/write (core K2 surgery)
13. TS4 Blueprint debug loop
14. D8 Lighting authoring
15. D7 Sequencer automation (enough for D1)
16. D4 Computer-use: Meshy + ComfyUI (defer Substance + Blender)
17. D2 Image → scene
18. D1 Video → matched shot (short, single-scene variant — the demo)
19. D5 Gemma local fallback (docs Q&A + asset search at minimum)

**Defer explicitly:**

- D6 YouTube tutorial → plan (huge retention win, but the launch demo is D1; ship D6 in v1.1)
- D9 NL asset tagging with thumbnail embeddings
- D10 Local project RAG
- All v2-tagged features above (AnimBP, Niagara, PCG, MetaSound graphs, Landscape, Multiplayer, Packaging)
- Substance + Blender computer-use bridges

**Kill cut-lines if the solo timeline slips (6–9 months):**

- First cut: D6, D9, D10 (already deferred)
- Second cut: D1 multi-shot → D1 single-shot only
- Third cut: Blueprint *debug* down to "explain error" (drop auto-fix-and-apply)
- Fourth cut (nuclear): ship as a **UE5 chat + docs RAG + scene builder** without D1 video demo; re-position the launch around D2 image→scene (still better than Nwiro thanks to D4 computer-use). Painful but shippable.

---

## Sources & Confidence Notes

- **UE API surface claims** — based on Unreal Engine 5.x documentation knowledge (training cutoff Jan 2026). HIGH confidence for stable subsystems (Asset Registry, EditorScripting, Sequencer Scripting, Material Instance params, SkyAtmosphere/VolumetricCloud, PostProcessVolume, ULevelSequence, UEditorActorSubsystem, console/CVars, FOutputDevice, FScopedTransaction, NNE). MEDIUM for Blueprint graph mutation surface (known to be partially undocumented / reflection-heavy).
- **Competitor tool counts** (CoPilot ~1,050 / Nwiro ~209 / Aura 43) — taken from the April 2026 competitive analysis referenced in `PROJECT.md`. Not independently re-verified in this pass. Qualitative positioning (Aura's Blueprint-error focus, Nwiro's scene-centric product, CoPilot's breadth) is MEDIUM confidence from training data + the context provided.
- **Computer-use reliability on Windows for Meshy / Substance / ComfyUI / Blender (April 2026)** — flagged as open research in `PROJECT.md`. MEDIUM-to-LOW confidence pending a hands-on spike. Recommend this be the first deep-research task before committing v1 scope that depends on D4.
- **Convai / Inworld category boundary (AF1)** — HIGH confidence; well-established positioning.
- **Coplay / Ramen VR / Nwiro cross-engine coverage (AF2)** — MEDIUM confidence; relies on the competitive analysis from `PROJECT.md`.

**Web research attempted but denied in this session:** independent verification of current (April 2026) competitor feature pages and UE 5.7 release notes. Findings here rely on training data (through Jan 2026) + project-supplied context. Any claim whose accuracy is load-bearing for roadmap decisions — especially D4 computer-use reliability, exact Claude Code CLI / Codex CLI programmatic interfaces, and UE 5.7-specific API changes — should be verified with a targeted Context7 / official-docs pass before the requirements phase locks scope.
