# Requirements: NYRA

**Defined:** 2026-04-21
**Core Value:** Turn a reference (image, video, prompt) into a finished Unreal Engine scene — without the user paying a new AI bill or leaving the editor.
**Quality Bar:** Every requirement must, at minimum, match the best competitor on its dimension, and the aggregate v1 must beat every competitor on the economic wedge (Claude subscription driving) + capability wedge (image/video → UE-native scene via API-first orchestration + Claude computer-use).

## v1 Requirements

### Plugin Foundation

- [ ] **PLUG-01**: Plugin ships as a native UE5 C++ plugin with two modules (`NyraEditor`, `NyraRuntime`), installable on Windows for UE 5.4, 5.5, 5.6, and 5.7
- [ ] **PLUG-02**: Plugin hosts a Python MCP sidecar process (`NyraHost`) communicating with the editor over a loopback WebSocket; NyraHost hosts the MCP server, agent router, RAG, and session state
- [x] **PLUG-03**: Plugin launches a llama.cpp inference process (`NyraInfer`) for Gemma 3 4B IT QAT Q4_0 GGUF (3.16 GB, 128K context, multimodal) exposed over localhost HTTP
- [ ] **PLUG-04**: Four-version CI matrix (UE 5.4 / 5.5 / 5.6 / 5.7) running from day one of the build-matrix phase; no version-specific code merges without all four passing
- [ ] **PLUG-05**: Pre-code legal gate passed — written ToS clearance from Anthropic (CLI subprocess driving) and Epic (Fab AI-plugin policy) before any subscription-driving code ships

### Chat UI & Session

- [x] **CHAT-01**: Dockable in-editor Slate chat panel with streaming tokens, markdown rendering, code blocks, image/video/file attachments, and per-conversation history persisted under project `Saved/NYRA/`
- [ ] **CHAT-02**: Subscription connection status UI surfacing which backends are active (Claude Code, Gemma local, computer-use) and which features each unlocks
- [ ] **CHAT-03**: Every agent mutation wrapped in `FScopedTransaction` so Ctrl+Z works; in-flight task cancellable and computer-use subprocesses cleanly unwound
- [ ] **CHAT-04**: Safe-mode / dry-run — agent outputs its planned tool-call sequence before execution; user can approve, edit, or reject

### Subscription Driving (Claude Only in v1)

- [ ] **SUBS-01**: Claude Code CLI subprocess driver using `claude -p --output-format stream-json`, injecting NYRA's MCP server via `--mcp-config`, with OAuth via `claude setup-token` (1-year scoped to user's Pro/Max sub)
- [ ] **SUBS-02**: Rate-limit and auth-drift detection; graceful fallback to Gemma on 429 / expired token, with clear user-facing status
- [ ] **SUBS-03**: Agent router designed multi-backend (Claude-only in v1) so Codex drop-in for v1.1 requires no refactor

### UE5 Knowledge

- [ ] **KNOW-01**: Bundled LanceDB RAG index with BGE-small-en-v1.5 embeddings covering UE5 official docs (5.4–5.7), Blueprint node reference, C++ API headers, Epic forum posts, and license-safe community transcripts with attribution
- [ ] **KNOW-02**: Agent answers cite sources with UE-version tags; before any action that touches a UE API, agent validates cited symbols exist in the user's UE version
- [ ] **KNOW-03**: RAG index refreshable via GitHub releases when Epic ships a new UE version; same-day or next-day updates after each UE release
- [ ] **KNOW-04**: Gemma 3 4B multimodal fallback handles offline docs Q&A and baseline asset search when Claude is unavailable (offline / rate-limited / privacy mode)

### In-Editor Agent Actions

- [ ] **ACT-01**: Agent can read a Blueprint graph, expose nodes/wires/variables/events as structured JSON, and write back edits (add/remove/reconnect nodes, set defaults, compile)
- [ ] **ACT-02**: Blueprint debug loop — intercept compile/runtime errors, explain in plain English, propose a diff, one-click apply, re-compile, iterate until clean
- [ ] **ACT-03**: Asset search over `FAssetRegistryModule` — baseline name/tag/class fuzzy search, structured queries. No thumbnail embeddings in v1.
- [ ] **ACT-04**: Actor CRUD via `UEditorActorSubsystem` / `UEditorLevelLibrary` — spawn by class or asset path, set transform, duplicate, delete, select, group, snap-to-ground, align-to-surface
- [ ] **ACT-05**: Material Instance operations — read/write scalar/vector/texture params, create MIC from parent, swap base textures, apply to actors
- [ ] **ACT-06**: Console command execution via `GEngine->Exec` — cvars, `stat`, `showflag`, custom exec commands
- [ ] **ACT-07**: Output Log / Message Log streaming to agent context with category filtering

### Scene & Cinematic

- [ ] **SCENE-01**: Lighting authoring — directional / point / spot / rect / sky lights, `SkyAtmosphere`, `VolumetricCloud`, `ExponentialHeightFog`, `PostProcessVolume`, exposure curves. Natural-language prompts ("golden hour", "match this reference image's mood")
- [ ] **SCENE-02**: Sequencer automation — create `ULevelSequence`, add CineCameras, set keyframes on actor/camera/light/PPV params, author shot blocking from natural language ("slow push-in on the hero, then cut wide")

### External Tool Integrations (API-First)

- [ ] **GEN-01**: Meshy REST API integration — image → 3D model, job polling, download, auto-import as UE `UStaticMesh` with LODs and collision
- [ ] **GEN-02**: ComfyUI local HTTP API integration — image-to-image workflows (textures, variations, references), auto-import results as `UTexture2D` or Material inputs
- [ ] **GEN-03**: Claude computer-use (`computer_20251124` tool with Opus 4.7) reserved for Substance 3D Sampler (image → PBR material, no public API) and UE editor modal dialogs the Unreal API doesn't expose

### Differentiator Demos

- [ ] **DEMO-01**: Image → full UE-native scene — indoor static scene, 5–20 actors, one light setup, hero materials. Agent prefers the user's asset library first; generates missing hero assets via Meshy and missing textures via Substance Sampler or ComfyUI
- [ ] **DEMO-02**: **LAUNCH DEMO** — Reference video → matched UE shot. User pastes a YouTube link or attaches an ≤10s mp4; NYRA extracts keyframes, infers shot composition + lighting + approximate geometry, assembles a single-shot single-location matching scene with one CineCamera, 1 key + 1 fill light, sky + fog, Sequencer-driven camera

### Distribution & Onboarding

- [ ] **DIST-01**: Fab listing ready — AI-disclosure copy compliant with Fab policy, launch demo trailer, per-UE-version plugin binaries, screenshots/marketing assets
- [ ] **DIST-02**: Direct-download fallback live *before* Fab submission — signed installer on `nyra.ai` (or temporary host) so a Fab rejection doesn't block launch
- [ ] **DIST-03**: EV code-signing certificate acquired and build pipeline signs all binaries (plugin DLL, NyraHost executable, NyraInfer executable)
- [ ] **DIST-04**: Zero-config install — user enables the plugin in UE, runs `claude setup-token` once, and is operational. First-run wizard verifies Claude Code CLI, downloads Gemma on demand, and confirms computer-use readiness

## v2 Requirements

Deferred to v1.1+. Tracked but not in current roadmap.

### Expanded AI Backends

- **SUBS-10**: Codex CLI subprocess driving (OpenAI ChatGPT Plus/Pro/Business subs) as a second reasoning backend — dropped from v1 to halve integration, legal, and auth surface
- **SUBS-11**: Anthropic direct API support for users without a Claude subscription (bring-your-own-API-key mode)

### Expanded Agent Capabilities

- **KNOW-10**: Local project RAG — indexing the user's own Blueprint comments, function names, struct fields, C++ header comments, level notes
- **ACT-10**: Thumbnail-embedding asset search (CLIP-like local model) — semantic queries over asset imagery, not just names
- **ACT-11**: Blueprint auto-fix for animation Blueprints and widget Blueprints (v1 scopes K2 event graphs / function libraries / construction scripts only)

### Expanded External Tools

- **GEN-10**: Substance 3D Sampler via a future public API (replace computer-use path if Adobe ships one)
- **GEN-11**: Blender via Python scripting API + headless CLI for mesh cleanup / retopology before UE import
- **GEN-12**: Tripo REST API as a Meshy alternative / redundancy

### Expanded Demos

- **DEMO-10**: YouTube tutorial → executable plan — NYRA ingests a UE tutorial, produces a step-by-step plan of tool calls, user approves, NYRA executes with pause-per-step
- **DEMO-11**: Multi-shot reference video — multi-shot sequences with camera-movement curve-fitting from optical flow
- **DEMO-12**: Outdoor scenes with Landscape / foliage for DEMO-01
- **DEMO-13**: Dynamic scenes — Niagara VFX, character blocking/animation for DEMO-01/02

### Expanded Authoring

- **SCENE-10**: Niagara VFX authoring
- **SCENE-11**: PCG graph authoring for procedural scatter
- **SCENE-12**: MetaSound graph authoring (v1 limits to SFX placement via actor events)
- **SCENE-13**: Animation Blueprint / State Tree / Control Rig authoring
- **SCENE-14**: Landscape sculpting, material-layer painting, foliage painting
- **SCENE-15**: World Partition cell management for open-world projects
- **SCENE-16**: Multiplayer / networking Blueprint setup (replicated vars, RPCs, role checks) with verification loop
- **SCENE-17**: Packaging / build automation (UAT / UBT cook + package commands)

### Platform & Distribution

- **PLUG-10**: macOS support (Apple Silicon)
- **PLUG-11**: Linux support
- **PLUG-12**: UE 5.8+ support as Epic ships
- **DIST-10**: Paid Pro tier (Dual SKU) with hosted RAG updates, team features, studio licensing
- **DIST-11**: Hosted backend (Supabase or Railway) only if usage signal proves materially better than bundled

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| macOS / Linux support in v1 | Halves the QA matrix; Claude computer-use is most reliable on Windows. Revisit after launch. |
| UE 5.3 and earlier | Epic deprecation cadence; doubles C++ compatibility work for a shrinking audience. |
| Cross-engine (Unity, Godot) | Ramen VR's Coplay acquisition owns this. Focus wins. |
| NPC conversation runtime | Convai / Inworld own this; runtime/gameplay product, different buyer, different integration surface. |
| Fine-tuned UE-specialist model | Breaks the "use your Claude subscription" economic wedge. Hosting cost, second product surface. |
| Ingesting paid courses (Udemy, Unreal Fellowship, etc.) as RAG corpus | Copyright + ToS landmine. Users may index their own purchased materials locally; NYRA does not redistribute. |
| Hosted backend in v1 | Ship free, validate usage, then consider. Avoids building infra that nobody needs. |
| Full image generation UI inside UE | Would become a second product; we drive ComfyUI / Meshy instead. |
| AI-authored Material graphs from scratch | Unreliable across the industry; too many subtle graph rules. Limit v1 to Material Instance param editing. |
| AI-authored Animation / State Tree / Control Rig graphs | Same reasoning as Material graphs; failure cost is high (broken rigs). |
| Pro tier billing / auth / per-seat features in v1 | Free plugin first; paid tier considered only after usage validates demand. |

## Traceability

Phase mapping populated by the roadmapper — see `.planning/ROADMAP.md` for phase definitions, success criteria, and dependency graph.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PLUG-01 | Phase 1 | Pending |
| PLUG-02 | Phase 1 | Pending |
| PLUG-03 | Phase 1 | Complete |
| PLUG-04 | Phase 2 | Pending |
| PLUG-05 | Phase 0 | Pending |
| CHAT-01 | Phase 1 | Complete |
| CHAT-02 | Phase 2 | Pending |
| CHAT-03 | Phase 2 | Pending |
| CHAT-04 | Phase 2 | Pending |
| SUBS-01 | Phase 2 | Pending |
| SUBS-02 | Phase 2 | Pending |
| SUBS-03 | Phase 2 | Pending |
| KNOW-01 | Phase 3 | Pending |
| KNOW-02 | Phase 3 | Pending |
| KNOW-03 | Phase 3 | Pending |
| KNOW-04 | Phase 3 | Pending |
| ACT-01 | Phase 4 | Pending |
| ACT-02 | Phase 4 | Pending |
| ACT-03 | Phase 4 | Pending |
| ACT-04 | Phase 4 | Pending |
| ACT-05 | Phase 4 | Pending |
| ACT-06 | Phase 2 | Pending |
| ACT-07 | Phase 2 | Pending |
| SCENE-01 | Phase 6 | Pending |
| SCENE-02 | Phase 7 | Pending |
| GEN-01 | Phase 5 | Pending |
| GEN-02 | Phase 5 | Pending |
| GEN-03 | Phase 5 | Pending |
| DEMO-01 | Phase 6 | Pending |
| DEMO-02 | Phase 7 | Pending |
| DIST-01 | Phase 8 | Pending |
| DIST-02 | Phase 8 | Pending |
| DIST-03 | Phase 8 | Pending |
| DIST-04 | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 34 total
- Mapped to phases: 34 ✓
- Unmapped: 0 ✓

**Distribution by phase:**
- Phase 0 (Legal & Brand Gate): 1 (PLUG-05)
- Phase 1 (Plugin Shell + Three-Process IPC): 4 (PLUG-01, PLUG-02, PLUG-03, CHAT-01)
- Phase 2 (Subscription Bridge + Four-Version CI Matrix): 9 (PLUG-04, SUBS-01, SUBS-02, SUBS-03, CHAT-02, CHAT-03, CHAT-04, ACT-06, ACT-07)
- Phase 3 (UE5 Knowledge RAG): 4 (KNOW-01, KNOW-02, KNOW-03, KNOW-04)
- Phase 4 (Blueprint + Asset + Material + Actor Tool Catalog): 5 (ACT-01, ACT-02, ACT-03, ACT-04, ACT-05)
- Phase 5 (External Tool Integrations): 3 (GEN-01, GEN-02, GEN-03)
- Phase 6 (Image-to-Scene, Fallback Demo): 2 (SCENE-01, DEMO-01)
- Phase 7 (Video-to-Matched-Shot, LAUNCH DEMO): 2 (SCENE-02, DEMO-02)
- Phase 8 (Fab Launch Prep): 4 (DIST-01, DIST-02, DIST-03, DIST-04)

---
*Requirements defined: 2026-04-21*
*Last updated: 2026-04-21 after roadmapper mapped all 34 v1 requirements to 9 phases*
