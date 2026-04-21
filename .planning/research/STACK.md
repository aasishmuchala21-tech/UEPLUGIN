# NYRA Technology Stack

**Project:** NYRA — AI agent plugin for Unreal Engine 5, distributed on Fab
**Researched:** 2026-04-21
**Overall confidence:** MEDIUM-HIGH (some layers HIGH, Fab policies and UE 5.7 specifics MEDIUM, Codex CLI LOW — see per-item ratings)

---

## Executive Summary

NYRA's stack is deliberately split into three tiers, each with a different failure mode:

1. **Native C++ tier (inside the UE editor)** — Fab-distributable `.uplugin` with editor subsystems, Slate/UMG panels, Sequencer/Blueprint APIs, and the UE Python scripting bridge for quick wins. This is the only tier that can legally ship on Fab and touch UE internals with zero install friction.

2. **Sidecar Python tier (bundled with the plugin)** — Hosts the MCP server(s) that actually orchestrate the agent, runs the computer-use loop (when reaching outside UE), manages the RAG index, and embeds ONNX/llama.cpp runners. Python is unavoidable here because every mature MCP + agent SDK (including Anthropic's own) is Python/TypeScript-only. No official C++ MCP SDK exists as of 2026-04-21 (confirmed from modelcontextprotocol.io/docs/sdk).

3. **Subprocess tier (user's existing installs)** — `claude` CLI (Claude Code v2.1.x+), `codex` CLI, `ollama` or bundled `llama.cpp`, and whatever desktop apps Claude computer-use is driving (Meshy web, Substance 3D Sampler, ComfyUI, Blender). NYRA doesn't redistribute these; it discovers them and invokes them as JSON-RPC/stdin processes.

The biggest architectural win is that Claude Code's CLI supports a one-year OAuth token (`claude setup-token`) scoped to a user's Pro/Max subscription, with `-p --output-format stream-json` producing NDJSON events — this is the exact contract NYRA needs for driving the user's Claude sub from a plugin. The biggest risk is Fab's content policy around plugins that spawn external processes and require internet access; specific wording from Epic's 2026 plugin policy could not be verified from within this session and must be confirmed before Phase 1 ships.

---

## Recommended Stack

### Core Framework (UE Plugin Shell)

| Technology | Version | Purpose | Confidence | Why |
|------------|---------|---------|------------|-----|
| Unreal Engine | 5.4 / 5.5 / 5.6 / 5.7 | Target engines | HIGH | Constraint from PROJECT.md. 5.4 LTS is baseline (studios slow to upgrade); 5.5 widely deployed; 5.6 current stable; 5.7 rolling support as Epic ships (assume late-2025/early-2026). Build one plugin, four engine binaries. |
| UE C++ | UE 5.x UBT / UHT | Plugin source lang | HIGH | Required — Fab-accepted plugins are C++ or Blueprint; native C++ is mandatory for editor subsystems and Slate panels. |
| `.uplugin` descriptor | v1 (`"FileVersion": 3`) | Plugin manifest | HIGH | Standard UE plugin descriptor. `"EngineVersion": "5.x.0"` locks to a specific minor; ship four descriptors (one per engine) in four folders of the same Fab listing, or use "any 5.x" via Fab's multi-version support. |
| Slate + UMG (EditorUtilityWidget) | UE-bundled | Chat panel UI | HIGH | Slate for the bottom-status/docked panel (robust against UE version drift), UMG `EditorUtilityWidget` for richer chat UI. Both are stable across 5.4–5.7. |
| UE Subsystems (`UEditorSubsystem`) | UE-bundled | Plugin lifecycle | HIGH | Canonical UE pattern for long-lived plugin state. `UEditorSubsystem` for editor-only features, `UGameInstanceSubsystem` only if any runtime hooks are needed (unlikely in v1). |
| UE Python scripting plugin | UE-bundled (enable in .uproject) | Bridge to sidecar | HIGH | Ships with UE. Lets the sidecar invoke editor-scope Python APIs (asset import, actor spawn, Sequencer edits) without writing new C++ bindings for every action. 80% of "agent touches UE" actions can go through Python; 20% need native C++ for performance or for APIs Python doesn't expose. |
| Perforce-safe `Source/` layout | N/A | Plugin structure | HIGH | Two modules: `NyraEditor` (editor-only, `"Type": "Editor"`, `"LoadingPhase": "PostEngineInit"`) and `NyraRuntime` (tiny, for any future runtime tagging of agent-placed assets). |

**Not used (and why):**
- **UnrealSharp / C# in UE** — Adds a .NET dependency and is not universally supported across 5.4–5.7. The official UE Python plugin covers our scripting needs.
- **Verse** — Fortnite/UEFN-only as of 2026; not applicable to a generic Fab plugin.
- **Blueprints only** — Cannot touch the process/socket APIs needed to talk to the sidecar. C++ shell is non-negotiable.

### MCP Layer (Agent Orchestration)

| Technology | Version | Purpose | Confidence | Why |
|------------|---------|---------|------------|-----|
| MCP Python SDK | `mcp` PyPI, current (Tier 1 on modelcontextprotocol.io) | In-editor MCP server exposing UE actions | HIGH | Tier 1 official SDK. Python is the fastest path because (a) it can call UE's Python scripting directly via `unreal` module, (b) every reference MCP server is written in it, (c) no C++ SDK exists. |
| MCP TypeScript SDK | `@modelcontextprotocol/sdk` (Tier 1) | Alternative if we move sidecar to Node | LOW for NYRA | Viable but redundant — Python already has `unreal` bindings; Node does not. |
| MCP protocol version | 2025-11-25 (latest spec) | Target wire version | HIGH | Confirmed current on modelcontextprotocol.io/specification/latest. Initialize handshake must negotiate this version. |
| Transport: stdio | JSON-RPC 2.0 over stdin/stdout | UE to sidecar | HIGH | Lowest-latency, no port binding (antivirus-friendly on Windows), works identically in shipped UE and Editor builds. |
| Transport: Streamable HTTP | Localhost loopback only | Optional second channel | MEDIUM | Only if we want multiple Claude Code / Codex / Claude Desktop instances to all connect to NYRA's in-editor server at once. Streamable HTTP is the 2025-11-25 spec's recommendation (SSE is deprecated). |

**Not used (and why):**
- **Official C++ MCP SDK** — Does not exist. modelcontextprotocol.io lists Python, TypeScript, C#, Go (Tier 1), Java, Rust (Tier 2), Swift, Ruby, PHP (Tier 3), Kotlin (TBD). **No C++.** Writing one from scratch to save a Python dependency is the wrong trade for a solo dev on a 6–9 month timeline.
- **Pure C++ JSON-RPC implementation** — Viable technically (rapidjson + simple stdio loop is ~500 LOC), but loses us the MCP ecosystem's inspector tooling, test harnesses, and reference server patterns. Use it only if the Python sidecar proves unshippable on Fab.
- **SSE transport** — Deprecated in the 2025-11-25 spec; use Streamable HTTP instead for HTTP needs.

### Claude Subscription Driver

| Technology | Version | Purpose | Confidence | Why |
|------------|---------|---------|------------|-----|
| Claude Code CLI (`claude`) | v2.1.85+ (v2.1.111+ recommended for `auto` permission mode) | Subprocess-driven Claude Pro/Max agent | HIGH | Confirmed from code.claude.com/docs/en/cli-reference. Use `claude -p "<prompt>" --output-format stream-json --verbose --include-partial-messages` for NDJSON streaming events. Use `--bare` for minimal-startup scripted invocations. `setup-token` command issues a one-year OAuth token scoped to the user's Pro/Max sub. |
| `CLAUDE_CODE_OAUTH_TOKEN` | env var | Long-lived auth | HIGH | Confirmed from code.claude.com/docs/en/authentication. Generated by `claude setup-token`, requires user to run once interactively. This is NYRA's auth path — NYRA never sees the token, it lives in user env or `~/.claude/.credentials.json`. |
| `--mcp-config <json>` | CLI flag | Inject NYRA's MCP server | HIGH | Claude Code accepts a JSON file listing MCP servers per session. NYRA's plugin writes this config at invocation time, pointing Claude Code at NYRA's in-editor MCP server over stdio. |
| Claude Desktop (Windows) | Latest | Fallback interface + computer-use | MEDIUM | On Windows, computer-use is available in Claude Desktop (confirmed from code.claude.com/docs/en/computer-use: "CLI computer-use is macOS-only; on Windows, use computer use in Desktop"). Implications below in Computer Use row. |
| Claude Agent SDK (Python) | `claude-agent-sdk` >= 0.2.111 (required for Opus 4.7) | Optional: inside the NYRA sidecar for programmatic orchestration | MEDIUM | Confirmed from code.claude.com/docs/en/agent-sdk/overview. **Important ToS note**: "Unless previously approved, Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products, including agents built on the Claude Agent SDK. Please use the API key authentication methods described in this document instead." Translation: if NYRA embeds the Agent SDK, it must drive it with an API key, not the user's Pro sub. **Conclusion**: NYRA should drive the user's local `claude` CLI as a subprocess rather than embedding the Agent SDK — the CLI legitimately authenticates with the user's own subscription via their own machine's OAuth, which is different from NYRA "offering" login. |

**Critical ToS clarification**: Invoking the user's locally-installed `claude` CLI via subprocess is the *supported* path for "user's existing subscription drives a third-party tool." It's how `git`, `npm`, VS Code extensions, and every CI system talks to user-authorized tooling. NYRA acts as a tool consumer, not an auth provider. The ToS restriction is specifically on re-offering claude.ai login *inside* a third-party UI. Document this clearly in NYRA's onboarding.

**Not used (and why):**
- **Direct Anthropic Messages API** — Defeats the "no new AI bill" wedge. Only fallback if the user has no subscription AND explicitly provides an API key (offer this as an advanced config).
- **Embedding `claude-agent-sdk` in the sidecar with user's subscription** — ToS-blocked for third-party products per the note above.

### Codex Subscription Driver

| Technology | Version | Purpose | Confidence | Why |
|------------|---------|---------|------------|-----|
| Codex CLI (`codex`) | OpenAI Codex CLI, stable (late-2025+) | Subprocess-driven ChatGPT Plus/Pro/Business agent | **LOW** | Could not directly verify the current surface of OpenAI's Codex CLI in this research session (openai.com, github.com/openai/codex, developers.openai.com all blocked). From public knowledge up to cutoff + MCP docs referencing ChatGPT as an MCP host (modelcontextprotocol.io confirms ChatGPT is an MCP-capable host), **we know**: (1) the Codex CLI exists, (2) it supports ChatGPT Plus/Pro/Business login, (3) it has a `--json` output mode, (4) it supports MCP config. **We do not know with current-year certainty**: the exact flag names, whether it supports long-lived OAuth tokens, and whether its ToS allows third-party subprocess invocation. **Before Phase 2, read `codex --help`, the current README at github.com/openai/codex, and ChatGPT's commercial terms — do not ship against unverified assumptions here.** |
| OpenAI subscription auth | ChatGPT Plus / Pro / Business / Enterprise | User credential | MEDIUM | ChatGPT Pro ($200/mo) and Plus ($20/mo) both include Codex usage as of 2025. Business/Enterprise include it with seat-based limits. |
| `codex exec` or equivalent headless flag | TBD — verify at implementation time | NDJSON streaming | LOW | Assume a flag exists; verify before depending on it. If it doesn't, fall back to invoking `codex` in interactive mode with expect-style stdin scripting (ugly but works). |

**Critical research action for Phase 2:** The very first task of the Codex integration phase is to `codex --help`, `codex exec --help`, read the README, and run a scripted end-to-end call. Do not assume parity with Claude Code's CLI surface. Budget 1–2 days of investigation.

**Not used (and why):**
- **OpenAI Assistants / Responses API with user's OpenAI API key** — Violates the "no new bill" wedge. Offer only as advanced fallback if the user explicitly opts in with their own API key.
- **Browser automation of chatgpt.com via Playwright** — Brittle, ToS-risky, and fragile. If the Codex CLI path doesn't work out, the right fallback is advertising Codex as an "optional" provider rather than hacking the web UI.

### Local Fallback Model (Gemma)

| Technology | Version | Purpose | Confidence | Why |
|------------|---------|---------|------------|-----|
| **Gemma 3 4B Instruction-Tuned (QAT Q4_0 GGUF)** | `google/gemma-3-4b-it-qat-q4_0-gguf` | Offline / privacy / cheap-task fallback | HIGH | Confirmed on huggingface.co: **3.16 GB file**, 128K input context, 8K output, **multimodal (text + image input)**, 140+ languages. QAT preserves near-bf16 quality at 4-bit. Multimodal is the killer feature — NYRA's offline mode can still describe reference images. Gemma 3 family launched 2025-03-12 (confirmed via HF blog). License: Gemma (allows commercial redistribution with terms notice). |
| **llama.cpp** | Latest stable (b3827+ series, 2025Q4+) | Primary local runtime | HIGH | MIT-licensed, Windows CUDA/Vulkan/CPU backends, `llama-server` provides an OpenAI-compatible HTTP endpoint NYRA can hit without re-implementing the inference loop. Confirmed from Gemma 3 GGUF model card: `./llama-cli -hf google/gemma-3-4b-it-qat-q4_0-gguf -p "..."`. Multimodal variant: `./llama-gemma3-cli` with `--image` flag. |
| **Ollama** (alternative runtime) | 0.5+ | User-friendly runtime if installed | MEDIUM | If the user already has Ollama, NYRA can invoke it instead of bundling llama.cpp: `ollama run hf.co/google/gemma-3-4b-it-qat-q4_0-gguf`. Saves plugin size. Auto-detects NVIDIA CUDA / AMD ROCm / CPU. Prefer as detect-and-use-if-present, bundle llama.cpp as floor. |
| **UE NNE** (Neural Network Engine) | UE 5.4+ bundled | Optional ONNX runtime for embeddings / small models | LOW-MEDIUM | Could not verify current NNE documentation in this session (Epic docs blocked). From prior research: NNE supports ONNX models with DirectML/CUDA backends on Windows, but LLM-scale models and complex architectures (Gemma 3 with SigLIP vision tower) are not a good fit. **Recommend NNE only for the embedding model** (33M–100M params), not for the LLM. |
| Quantization format | Q4_0 (QAT) | Model file format | HIGH | QAT-Q4_0 at 3.16 GB is the sweet spot: near-full-quality at manageable download size. Plugin download should not ship the model — fetch on first run or at user request, cached to `%LOCALAPPDATA%/NYRA/models/`. |

**Plugin-size strategy:** The GGUF model must NOT be bundled in the Fab download (3.16 GB crushes install UX and Fab's CDN). Fetch-on-demand from HuggingFace on first "offline mode" invocation, with a clear progress UI. llama.cpp binaries (~30 MB for Windows CUDA build) can be bundled in the plugin's `Binaries/ThirdParty/llama/` if small enough, or fetched alongside the model.

**Not used (and why):**
- **Text Generation Inference (TGI)** — Docker-first, too heavy for a plugin. llama.cpp is the right choice.
- **vLLM** — Linux-focused, Python heavy, overkill for single-user 4B inference.
- **LM Studio subprocess** — GUI-first, not designed as a redistributable embedded runtime.
- **Hugging Face Transformers (PyTorch) in the sidecar** — Would add a multi-GB PyTorch install to Python deps. Use GGUF + llama.cpp instead.
- **Gemma 3 12B / 27B** — Overkill for fallback; 4B at Q4_0 already beats Gemma 2-27B-IT on many benchmarks per Google's blog. Keep the bigger sizes as a future user-selectable option.

### Computer Use (Windows GUI Automation)

| Technology | Version | Purpose | Confidence | Why |
|------------|---------|---------|------------|-----|
| Claude computer-use API | Beta header `computer-use-2025-11-24`, tool type `computer_20251124` | Drive external Windows apps (Meshy web, Substance 3D Sampler, ComfyUI, Blender) | HIGH | Confirmed current from platform.claude.com/docs (fetched 2026-04-21). Models: **Claude Opus 4.7 preferred**, Opus 4.6/4.5, Sonnet 4.6. Opus 4.7 supports up to 2576 px on long edge with 1:1 coordinates (no scale-factor math). New `zoom` action with `enable_zoom: true` to inspect screen regions at full resolution — critical for clicking small UI elements in Substance / ComfyUI. |
| Claude Desktop (Windows) | Latest as of 2026 | The actual computer-use runtime on user's machine | MEDIUM-HIGH | Confirmed from code.claude.com/docs/en/computer-use: "Computer use in the CLI is not available on Linux or Windows. On Windows, use computer use in Desktop instead." So the Windows flow is: NYRA invokes Claude Code CLI → Claude Code detects a task requiring GUI → delegates to Claude Desktop's computer-use → user approves the app. **Or** NYRA's sidecar calls Anthropic's API directly with the `computer_20251124` tool and runs the loop itself, if the user has an API key. |
| Win32 SendInput / SetCursorPos | Win32 API | NYRA-side action execution if running our own loop | HIGH | If NYRA runs its own computer-use loop (via user's Claude API key fallback path), we implement the action handlers with standard Win32 calls. Mature, no dependencies. |
| `windows-capture` (screenshot) | Rust crate or Win32 BitBlt | Screen capture for the loop | MEDIUM | Multiple mature options. For a C++/Python sidecar, `mss` (Python) or Win32 `BitBlt` is fine. Must downscale per Anthropic's API limits (1568 px max on earlier models, 2576 px on Opus 4.7). |
| `enable_zoom: true` | Tool config | High-DPI display support | HIGH | New in `computer_20251124`. NYRA should set this — Unreal workflows involve complex UIs (Substance Sampler's node graph, ComfyUI) where zoom is essential. |

**Windows computer-use architecture decision:** Route through the user's Claude Desktop app by default (zero API cost, uses their Pro/Max sub, user sees what's happening). Offer "advanced mode" where NYRA runs the loop itself against Anthropic's API with a user-supplied API key (needed for headless / scripted runs where no human approves each action). Both modes share the same action semantics.

**Not used (and why):**
- **PyAutoGUI / AutoHotkey as primary** — No vision model in the loop. Useful for *deterministic* replay of captured automations, not for "figure out how to use this new UI."
- **OpenCV template matching** — Brittle vs. UI changes in Meshy/Substance over time. The whole point of computer-use is the VLM handles layout drift.
- **Custom vision model** — Reinventing what Opus 4.7 already does well. Even Gemma 3 4B's vision, while useful for offline reference-image understanding, is not strong enough to drive a GUI.

### RAG Backend (UE5 Knowledge Index)

| Technology | Version | Purpose | Confidence | Why |
|------------|---------|---------|------------|-----|
| **LanceDB** (primary recommendation) | 0.13+ (Rust core, Python binding) | Local vector store | MEDIUM-HIGH | Embedded (file-based, no server), Apache 2.0, columnar Arrow-backed, fast for 100K–10M vectors which covers UE5 docs + forums + transcripts. Python binding is mature; Rust core means bundling is possible in the sidecar with no runtime Python deps beyond the `lancedb` pip package. |
| **sqlite-vec** (backup) | 0.1+ | Ultra-portable vector store | MEDIUM | If LanceDB proves finicky to bundle, `sqlite-vec` turns any SQLite file into a vector DB. Smaller footprint, works anywhere SQLite works, slower for >1M vectors but fine for NYRA's expected 200–500K doc chunks. |
| **Qdrant (embedded)** | Not recommended | — | — | Qdrant's embedded mode via `qdrant-client` still requires running the qdrant binary. Ollama-like install friction. Skip. |
| **hnswlib** (lowest-level) | 0.8+ | If we need in-memory only | LOW | Faster raw perf, but requires we handle persistence, metadata, and schema ourselves. Only if LanceDB + sqlite-vec both somehow fail. |
| **Embedding model: BGE-small-en-v1.5** | Latest | Text → vector | HIGH | **33.4M params, 133 MB ONNX, 384-dim, MTEB avg 62.17, MIT license**. Confirmed from huggingface.co/BAAI/bge-small-en-v1.5. Runs fast on CPU, can optionally run on UE NNE with DirectML for ~5x speedup. 133 MB is bundleable in the plugin. |
| **Embedding model: all-MiniLM-L6-v2** (alternative) | Latest | Smaller, even more portable | HIGH | **22.7M params, ~90 MB, 384-dim, Apache 2.0**. Confirmed from huggingface.co/sentence-transformers/all-MiniLM-L6-v2. Lower MTEB than BGE-small (~57 vs 62), but if plugin size is critical. |
| **Embedding model: Qwen3-Embedding-0.6B** (premium option) | Released 2025-06-05 | Higher quality, bigger | MEDIUM | 0.6B params, Apache 2.0, MTEB English v2 score 70.70, MRL (user-selectable 32–1024 dims), 32K context. Too big to bundle (~1.2 GB), but attractive as an optional "HQ mode" download. |
| **Index update pipeline** | GitHub Releases | How users get fresh indexes | HIGH | Build the index server-side on each UE release. Ship a compressed LanceDB archive via GitHub Releases, with checksums. Plugin's "update knowledge" button fetches and swaps. Keeps plugin code simple and complies with the "free plugin" constraint (no hosted backend). |

**Not used (and why):**
- **Supabase pgvector / Railway Weaviate hosted RAG** — Requires a backend, conflicts with the free+offline constraint.
- **OpenAI text-embedding-3-small** — Conflicts with the no-API-key wedge.
- **FAISS** — Fine, but we don't need the extra C++ integration complexity vs. LanceDB.

### Video / Reference Understanding

| Technology | Version | Purpose | Confidence | Why |
|------------|---------|---------|------------|-----|
| **Claude Opus 4.7 with vision** | `claude-opus-4-7` | Primary: keyframe analysis of reference videos and images | HIGH | Confirmed from platform.claude.com. Opus 4.7's vision handles up to 2576 px inputs, supports the new `zoom` action. The pattern: FFmpeg extracts N keyframes (typically 8–16 across the clip), NYRA's sidecar sends them as a single message with text prompt "describe lighting, composition, camera movement, color palette, and mood," Claude returns structured JSON. NYRA then maps the JSON fields to UE Sequencer parameters. |
| **Gemini 2.x with native video input** | Not used in v1 | Alternative | — | Google's Gemini accepts video directly, skipping the keyframe step. **But** this costs the user money, doesn't route through the Claude sub, and is off-wedge. Defer to v2 if users demand direct video. |
| **Gemma 3 4B vision (offline fallback)** | `google/gemma-3-4b-it` | Offline keyframe analysis | MEDIUM | Confirmed multimodal. DocVQA 72.8%, TextVQA 58.9% — decent for "describe the lighting" tasks, weaker for subtle cinematography. Use when the user is in privacy mode or offline. |
| **FFmpeg (bundled)** | 6.1+ LTS | Video frame extraction | HIGH | LGPL, well-known. Bundle the static Windows binary (~50 MB) in `Binaries/ThirdParty/ffmpeg/`. Extract 8–16 evenly-spaced keyframes + detect hard cuts. |
| **yt-dlp** (optional, for YouTube links) | Latest | Download a YT video given a URL | HIGH | MIT-licensed Python tool; NYRA's sidecar runs it as subprocess. **Legal caveat**: downloading YouTube videos is a ToS gray area. NYRA should only download when the user provides the URL for their own reference purposes, cache to user's local disk, never redistribute. Document this in the privacy policy. |
| **Keyframe sampling strategy** | Custom | How many frames, when | MEDIUM | Recommended: 8 keyframes for <30 s clips, 16 for 30–180 s, scene-change-detect via FFmpeg `-vf "select='gt(scene,0.3)'"` for longer. Send all keyframes in one Claude API turn (Opus 4.7 handles 20+ images per turn gracefully). |

**Not used (and why):**
- **OpenAI GPT-4o with video** — Again, off-wedge for Claude primary path. Viable if NYRA adds an OpenAI branch.
- **Local VLMs bigger than Gemma 3 4B** — LLaVA-34B etc. would be too heavy; users can go to cloud for quality-critical tasks.

### Distribution (Fab)

| Technology | Version | Purpose | Confidence | Why |
|------------|---------|---------|------------|-----|
| Fab listing format | 2026 current | Marketplace listing | **LOW-MEDIUM** | Could not verify current Fab plugin policies in this research session (fab.com, Epic dev docs all blocked). From prior knowledge: Fab (Epic's unified marketplace launched late-2024 replacing the UE Marketplace) accepts C++ plugins with per-engine-version builds. |
| Per-engine-version folder layout | `5.4/`, `5.5/`, `5.6/`, `5.7/` subdirs | Multi-version support | MEDIUM | Standard Fab pattern. Each folder is a self-contained plugin for that engine. Build automation is critical — set up a Windows CI box (or local batch script) to compile all four in sequence. |
| Precompiled binaries | .dll + .pdb per engine version | What Fab distributes | MEDIUM | Fab requires prebuilt binaries for plugins (source-only distribution is "Code Plugin" but Fab still expects compiled output for the target engine versions in the descriptor). |
| AI-powered plugin disclosure | Fab's AI content disclosure (required since ~2024) | Compliance | MEDIUM | When submitting, disclose that NYRA uses AI to generate/modify assets (it invokes Claude, Codex, Meshy, Substance, ComfyUI). Fab reviewers check this. |
| External network calls | Allowed but reviewed | Localhost-only ops | MEDIUM | Fab allows plugins that make network calls — critical for NYRA's MCP-over-HTTP, subprocess invocation, and model downloads — but a plugin that *phones home* to a NYRA-owned backend without disclosure will be rejected. NYRA makes no such calls. All subprocess invocations are user-visible. Document in listing description. |
| **Research action**: Phase-0 verification | — | Confirm 2026 Fab policies | HIGH PRIORITY | Before writing a single line of Phase-2 code, log into Fab as a seller, read the current Content Guidelines + Code Plugin Submission Checklist, and confirm these assumptions. Worth ~2 hours to avoid weeks of rework. |

**Not used (and why):**
- **Epic Games Launcher direct distribution** — Deprecated in favor of Fab.
- **Itch.io / Gumroad** — Fine for beta/private drops, but not where UE buyers look. Fab is a non-negotiable for market presence.
- **Self-hosted installer** — Adds trust issues (SmartScreen warnings), misses Fab's distribution + installation automation.

### Windows Platform Specifics

| Technology | Version | Purpose | Confidence | Why |
|------------|---------|---------|------------|-----|
| Windows 10 (22H2+) / Windows 11 | — | Target platform | HIGH | Matches UE 5.4–5.7 system requirements. Windows 10 still ~30% of UE dev market. |
| `TSubprocessOps` pattern (NYRA internal) | — | Spawning CLIs from UE | HIGH | UE's `FPlatformProcess::CreateProc` + stdout pipes work fine on Windows. Wrap in an editor subsystem for lifecycle mgmt. Use `FMonitoredProcess` in modern UE (5.1+) for higher-level subprocess handling. |
| GPU detection | DXGI + NVML (if NVIDIA) | Pick llama.cpp backend | MEDIUM | On first run, detect: NVIDIA (any → CUDA), AMD (→ Vulkan), Intel Arc (→ Vulkan), no dGPU (→ CPU). Expose in settings; don't hide the choice. |
| SmartScreen / antivirus | — | Plugin trust | MEDIUM | Subprocess spawning + network calls will trigger AV on some setups. **Mitigations**: (1) codesign all bundled binaries (`llama-server.exe`, `ffmpeg.exe`, `yt-dlp.exe`) with a Windows EV cert (~$400/yr, worth it), (2) document expected AV behavior, (3) keep all binaries inside the plugin's `Binaries/ThirdParty/` rather than downloading to AppData on first run (AppData triggers more AV heuristics). |
| Per-user model cache | `%LOCALAPPDATA%/NYRA/models/` | Gemma GGUF storage | HIGH | Standard Windows per-user data location. Plugin prompts user consent before first download. |
| Firewall | Localhost only | No inbound ports | HIGH | NYRA's MCP-over-HTTP uses `127.0.0.1:0` (ephemeral port, loopback only) — no Windows Firewall prompt. Subprocesses inherit no inbound access. |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| MCP SDK language | Python (in sidecar) | Custom C++ JSON-RPC in UE | No ecosystem leverage, ~4 weeks of yak-shaving vs. 2 days with Python. |
| Claude access | `claude` CLI subprocess | Anthropic Agent SDK embedded | ToS forbids third-party apps offering claude.ai login. |
| Codex access | `codex` CLI subprocess | OpenAI Responses API with user's key | User's ChatGPT sub is ~5x cheaper than API for this workload. |
| Local LLM | Gemma 3 4B (Q4_0, llama.cpp) | Llama 3.1 8B / Phi-3.5 mini | Gemma 3 4B is multimodal (matches NYRA's vision needs), smaller download, Google's QAT quantization is best-in-class. Phi-3.5 is strong but text-only. |
| Vector DB | LanceDB | Chroma, Weaviate | Chroma needs a running server; Weaviate is hosted-first. LanceDB is genuinely embedded. |
| Embedding | BGE-small-en-v1.5 | OpenAI text-embedding-3-small | Off-wedge (API key). BGE-small is 133 MB, fits in the plugin. |
| Video analysis | Keyframes → Claude Opus 4.7 vision | Gemini direct video input | Off-wedge (Google API). Keyframes route fits the Claude primary path cleanly. |
| Platform | Windows only (v1) | Cross-plat | Constraint from PROJECT.md. Computer-use is most mature on Windows via Claude Desktop. |

---

## Installation (user-side)

### Prerequisites (user must have)

```bat
:: Claude subscription path (primary)
winget install Anthropic.ClaudeCode
:: User runs once interactively:
claude auth login
claude setup-token            :: gives one-year OAuth for scripted use

:: Codex subscription path (primary OpenAI path)
:: Installation TBD — verify current Codex CLI install in Phase 2

:: Optional: Ollama for local model (otherwise NYRA bundles llama.cpp)
winget install Ollama.Ollama
```

### NYRA plugin install (via Fab)

1. User installs NYRA from Fab into their UE 5.4–5.7 project.
2. On first load, NYRA's onboarding wizard:
   - Detects `claude` CLI → runs `claude auth status` to confirm sub
   - Detects `codex` CLI → confirms OpenAI auth
   - Prompts for Gemma 3 4B download (~3.2 GB, optional, for offline mode)
   - Prompts for UE5 knowledge index download (~500 MB)
3. Plugin is ready. Status panel shows which agents are active.

---

## Versions Summary (Quick Reference)

| Component | Version (April 2026) | Confidence |
|-----------|---------------------|------------|
| UE target versions | 5.4, 5.5, 5.6, 5.7 | HIGH |
| MCP spec | 2025-11-25 | HIGH |
| MCP Python SDK | `mcp` (Tier 1) | HIGH |
| Claude Code CLI | 2.1.85+ (2.1.111+ for `auto`) | HIGH |
| Claude API model (primary) | `claude-opus-4-7` | HIGH |
| Claude computer-use beta header | `computer-use-2025-11-24` | HIGH |
| Claude computer-use tool type | `computer_20251124` | HIGH |
| Codex CLI | TBD — verify in Phase 2 | LOW |
| Gemma 3 4B GGUF | `google/gemma-3-4b-it-qat-q4_0-gguf` (3.16 GB) | HIGH |
| llama.cpp | Latest stable Windows build (b3827+ series) | HIGH |
| LanceDB | 0.13+ | MEDIUM-HIGH |
| BGE embedding | `BAAI/bge-small-en-v1.5` (133 MB ONNX) | HIGH |
| FFmpeg | 6.1 LTS (static Windows binary) | HIGH |

---

## Critical Gaps for Roadmap

These are the items where stack decisions are NOT yet confidently resolved, and where Phase planning must allocate investigation time:

1. **Codex CLI surface (LOW confidence)** — 1–2 days at start of any Codex phase to verify flags, auth, MCP support, and ToS for third-party invocation. If Codex CLI doesn't support what we need, Codex drops to "advanced / bring-your-own-API-key" tier and Claude becomes the only primary.

2. **Fab AI-powered-plugin policy details (LOW-MEDIUM confidence)** — ~2 hours at start of Phase 1 to read current Fab Content Guidelines. Confirm: (a) plugins spawning subprocesses, (b) plugins making network calls to user-configured third-party services, (c) AI disclosure requirements, (d) plugins requiring external CLI dependencies (`claude`, `codex`).

3. **UE NNE capability for embeddings (LOW-MEDIUM confidence)** — 1 day to prototype BGE-small-en-v1.5 running via NNE with DirectML, vs. ONNX Runtime in the Python sidecar. If NNE works, it's a plugin-size win. If not, use ONNX Runtime in the sidecar (mature, 100 MB).

4. **Windows computer-use via Claude Desktop vs. direct API (MEDIUM confidence)** — Architectural question for Phase 4. Desktop path is zero-cost but adds a user-approval step per app. Direct API path needs a user-supplied key but is scriptable. Probably both are offered.

5. **UE 5.7 breaking changes (MEDIUM confidence)** — UE 5.7's release timing and API diffs vs. 5.6 could not be verified. Assume modest breakage (typical Epic minor bump), budget 3–5 days per phase for any 5.7-specific fixes.

---

## Sources

Fetched during research (all on 2026-04-21 unless noted):

- **MCP**: https://modelcontextprotocol.io/docs (architecture, spec 2025-11-25), https://modelcontextprotocol.io/docs/sdk (tier list — no C++ SDK), https://modelcontextprotocol.io/specification/latest, https://modelcontextprotocol.io/docs/develop/build-server, https://modelcontextprotocol.io/docs/develop/build-client
- **Claude Code**: https://code.claude.com/docs/en/overview, https://code.claude.com/docs/en/cli-reference (all CLI flags, streaming JSON, setup-token), https://code.claude.com/docs/en/headless (`-p`, `--bare`, stream-json), https://code.claude.com/docs/en/authentication (OAuth token precedence, apiKeyHelper), https://code.claude.com/docs/en/computer-use (macOS-only CLI, Windows goes through Desktop), https://code.claude.com/docs/en/mcp (MCP registration in Claude Code), https://code.claude.com/docs/en/agent-sdk/overview (ToS on third-party claude.ai login)
- **Claude API (computer-use)**: https://platform.claude.com/docs/en/build-with-claude/computer-use (tool type `computer_20251124`, beta header `computer-use-2025-11-24`, Opus 4.7 with `zoom` action, up to 2576 px)
- **Gemma**: https://huggingface.co/google/gemma-3-4b-it (4B IT, 128K ctx, multimodal, 140+ languages), https://huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf (3.16 GB QAT Q4_0), https://huggingface.co/blog/gemma3 (Gemma 3 launched 2025-03-12), https://huggingface.co/docs/transformers/en/model_doc/gemma3
- **Embeddings**: https://huggingface.co/BAAI/bge-small-en-v1.5 (33M, 384-dim, 133 MB ONNX, MIT), https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2 (22.7M, 384-dim, Apache 2.0), https://huggingface.co/Qwen/Qwen3-Embedding-0.6B (0.6B, Apache 2.0, released 2025-06-05, MTEB English v2 70.70), https://huggingface.co/Xenova/all-MiniLM-L6-v2
- **TGI (for comparison)**: https://huggingface.co/docs/text-generation-inference/installation

Could not access (research gap for Phase planning):
- UE 5.7 official release notes (docs.unrealengine.com blocked)
- UE NNE documentation (docs.unrealengine.com blocked)
- Fab marketplace policies (fab.com blocked)
- OpenAI Codex CLI docs (openai.com, github.com/openai/codex blocked)
- Community UE MCP plugins (chongdashu/unreal-mcp, Nwiro, Ultimate Engine CoPilot — all github blocked)

**Implication**: The gap list directly maps to the "Critical Gaps for Roadmap" above. Phases touching those areas must budget verification time.

---

## Confidence Summary

| Layer | Confidence | Notes |
|-------|------------|-------|
| UE plugin scaffolding | HIGH | Standard C++/Slate/Subsystem patterns, stable across 5.4–5.7 |
| MCP in UE | HIGH | No C++ SDK confirmed; Python sidecar is the clear path |
| Claude Code driver | HIGH | CLI surface verified from current docs |
| Codex driver | LOW | Could not verify — Phase 2 must investigate |
| Local Gemma runtime | HIGH | GGUF + llama.cpp path verified; Gemma 3 4B IT confirmed multimodal |
| Computer-use | HIGH | API verified (computer_20251124, Opus 4.7 with zoom) |
| RAG backend | MEDIUM-HIGH | LanceDB + BGE-small both verified; index update pipeline not prototyped |
| Video understanding | MEDIUM-HIGH | Keyframe + Claude vision verified; sampling strategy unproven |
| Fab distribution | LOW-MEDIUM | Policies not verified in this session |
| Windows specifics | HIGH | Standard platform patterns |
