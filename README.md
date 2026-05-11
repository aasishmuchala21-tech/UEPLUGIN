# NYRA — the AI agent for Unreal Engine, free for life

NYRA is a free Unreal Engine 5 plugin that gives UE developers an in-editor
AI agent powered by **their existing Claude subscription**. No new API bills,
no token metering, no separate account. Drop a reference image, paste a
YouTube URL, type a prompt — NYRA produces a lit, dressed, playable Unreal
scene.

> **Status: public beta.** Tested on UE 5.6 (Windows). UE 5.4 / 5.5 / 5.7 builds
> via the same source tree on the CI matrix. Mac + Linux land in v1.1.

## Why NYRA

| | NYRA | Aura | Ultimate Engine CoPilot |
|---|---|---|---|
| Free for life | ✅ | ❌ paid SaaS | ❌ paid |
| Use your own Claude / Codex sub | ✅ | ❌ | ❌ |
| Privacy Mode + offline Gemma fallback | ✅ | ❌ cloud-only | ❌ |
| Open source (auditable for studios under NDA) | ✅ | ❌ closed | ❌ |
| Runs on UE 5.4 – 5.7 | ✅ | ✅ | ✅ |
| Computer-use for non-API apps (Substance Sampler, UE modals) | ✅ | ❌ | ❌ |
| Behavior Trees, Niagara, Anim Blueprints, MetaSounds, C++ Live Coding | ✅ | ✅ | partial |
| In-painting modal w/ brush mask | ✅ | ✅ | ❌ |
| Auto-rig + animation retargeting | ✅ Pro tier | ✅ | ❌ |
| Level Design Agent (procedural blockouts) | v0 | ✅ | ❌ |

## Quickstart

```powershell
# 1. Clone
git clone https://github.com/aasishmuchala21-tech/UEPLUGIN.git
cd UEPLUGIN/TestProject/Plugins/NYRA

# 2. Fetch bundled binaries (CPython, llama.cpp builds; SHA-256 verified)
PowerShell -ExecutionPolicy Bypass -File prebuild.ps1

# 3. Open TestProject.uproject in Unreal Engine 5.6
# 4. Tools menu → NYRA → Chat
# 5. (One-time) install the Claude CLI on PATH and run `claude setup-token`
```

The chat panel turns green within 30 s of editor startup once NyraHost is
ready. Type *"Tell me about this project"* to confirm it sees your `Content/`.

## Architecture

NYRA is a three-process plugin:

```
   ┌──────────────┐   loopback WS    ┌────────────────┐   stdio NDJSON   ┌──────────────┐
   │ UE Editor    │ ws://127.0.0.1   │  NyraHost      │ claude -p        │  Claude CLI  │
   │  NyraEditor  │ ◄──────────────► │  (Python MCP   │ ◄──────────────► │   subprocess │
   │  (C++ Slate) │  JSON-RPC 2.0    │   sidecar)     │                  │              │
   └──────────────┘                  └────────────────┘                  └──────────────┘
                                            │ HTTP localhost
                                            ▼
                                    ┌────────────────┐
                                    │  llama.cpp     │
                                    │  (Gemma 3 4B   │
                                    │   local fbk)   │
                                    └────────────────┘
```

- **UE plugin shell** (`Source/NyraEditor` + `Source/NyraRuntime`) — Slate
  chat panel, supervisor that spawns + monitors the sidecar, JSON-RPC client.
- **NyraHost** (`Source/NyraHost`) — Python MCP sidecar with WebSocket
  server, 30+ MCP tools (BT, Niagara, AnimBP, MetaSound, blueprint, material,
  perf, asset search, computer-use, image gen, 3D model gen, in-painting,
  auto-rig, retargeting, level-design blockout), SQLite session store.
- **NyraInfer** — bundled `llama-server.exe` for offline Gemma 3 4B inference
  (CUDA / Vulkan / CPU variants auto-selected).

Wire spec: [`docs/JSONRPC.md`](docs/JSONRPC.md) · Handshake: [`docs/HANDSHAKE.md`](docs/HANDSHAKE.md) · Error codes: [`docs/ERROR_CODES.md`](docs/ERROR_CODES.md)

## What the agent can do today

- **Plan & iterate** on Blueprints (Aura-parity surface — actor / component
  / interface / function / collision / replication / UI / AI nodes)
- **Author C++** with Live Coding compile + hot-reload
- **Edit Behavior Trees, Niagara systems, Animation Blueprints, MetaSound graphs**
- **Spawn assets and edit actors** in the level via UE Python
- **Generate images, 3D models, textures, audio** through API-first
  integrations (Meshy, ComfyUI) — your keys, your rate limits
- **In-paint** any image with a brush mask + prompt (SDXL via local ComfyUI)
- **Auto-rig** generated humanoid meshes (Meshy Pro tier)
- **Retarget** UE Mannequin animations onto your custom rigged mesh
- **Block out** procedural rooms + linear staircases via GeometryScript
- **Drive non-API apps** (Substance 3D Sampler, UE editor modals) via
  Anthropic computer-use with bounded windows + hard caps + permission gate
- **Search your Content/ + bundled UE5 knowledge corpus** with BM25 RAG
- **Stay private** — Privacy Mode hard-refuses Claude and routes 100 %
  through local Gemma; no telemetry, no outbound HTTP

## Plan-first by default

Every destructive action surfaces an editable Markdown plan in
`Saved/NYRA/plans/<plan_id>.md`. You can reorder steps, drop steps, tweak
args, then submit `plan/edit`. Plan-first cannot be silently disabled
(CHAT-04 invariant). Three operating modes:

- **Ask** — read-only. Knowledge tools work; mutations refuse.
- **Plan** — generates a plan preview; you Approve before each mutation.
- **Agent** — auto-executes pre-approved plans; previews still emitted
  for inspection. Safe-mode itself stays ON.

Plus an orthogonal **Privacy Mode** that pins everything to the local
Gemma fallback.

## Project layout

```
UEPLUGIN/
├── README.md                          this file
├── LICENSE                            MIT
├── CONTRIBUTING.md                    contributor guide
├── CLAUDE.md                          per-project memory (used by Claude Code agents)
├── docs/                              wire-protocol specs
│   ├── JSONRPC.md
│   ├── HANDSHAKE.md
│   └── ERROR_CODES.md
├── .planning/                         per-phase planning artefacts (PROJECT, ROADMAP, …)
└── TestProject/                       UE host project + the plugin
    └── Plugins/NYRA/
        ├── NYRA.uplugin
        ├── prebuild.ps1               SHA-256-verified binary downloader
        └── Source/
            ├── NyraEditor/            UE C++ editor module (~3k LOC)
            ├── NyraRuntime/           tiny runtime stub
            └── NyraHost/              Python MCP sidecar (~10k LOC, 600+ tests)
```

## Status of the wedge

- **No new AI bill** — gated on Anthropic SC#1 ToS clearance.
  Claude path is stubbed until it lands; offline Gemma path is fully live.
  Watch [`.planning/PROJECT.md`](.planning/PROJECT.md) for status.
- **Fab listing** — gated on Epic AI-plugin policy clearance.
  Direct-download channel is the live fallback.
- **EV code-signed binary** — runbook in `legal/ev-cert-acquisition-runbook.md`;
  cert acquisition in progress.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Short version: clone, run
`prebuild.ps1`, open TestProject, hack on `NyraEditor` for the C++/Slate side
or `NyraHost` for the Python sidecar. CI matrix builds against UE 5.4 / 5.5 /
5.6 / 5.7 on a self-hosted Windows runner; Python tests run on every push.

## License

MIT. See [LICENSE](LICENSE).

## Credits

NYRA stands on the shoulders of:

- [Anthropic Claude](https://docs.claude.com) — the agent backbone
- [Google Gemma 3](https://huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf) — the offline fallback
- [llama.cpp](https://github.com/ggml-org/llama.cpp) — local inference
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) — image gen
- [Meshy](https://meshy.ai) — 3D model gen + auto-rigging
- [Model Context Protocol](https://modelcontextprotocol.io) — tool surface
- The Unreal Engine Slate, GeometryScript, IK Rig, and AnimBP teams at Epic
