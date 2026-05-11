# FAQ

## How is NYRA different from Aura?

NYRA is free, uses your own Claude/Codex subscription, supports a Privacy Mode that hard-refuses outbound HTTP, ships an audit log of every prompt + tool call, is open source, and runs whole-project agents (Asset Hygiene, Perf Budget, Crash RCA, Doc-from-code, Test Gen, Replication scaffolder, Cinematic / DOP, Localization) that Aura's per-event SaaS pricing makes cost-prohibitive at studio scale.

Aura ships UE 5.3 support and a few features NYRA doesn't (yet) — see `NYRA_vs_Aura_GAPS.md` for the punch list.

## Where does my data go?

Without Privacy Mode: prompts go to Anthropic (Claude) via the CLI subprocess. Image / 3D model calls go to ComfyUI (localhost) and Meshy (your own account). Nothing goes to NYRA-the-company.

With Privacy Mode on (Phase 15-E): every non-loopback HTTP refuses. Inference falls back to local Gemma 3 4B via llama.cpp.

## Where are my chats stored?

`<Project>/Saved/NYRA/sessions.db` (SQLite). Encrypted memory is at `<Project>/Saved/NYRA/memory.enc` (Phase 15-A, Fernet AES-128-CBC + HMAC). Audit log at `<Project>/Saved/NYRA/audit.jsonl` (Phase 13-D, append-only, secret-redacted).

## How do I export a chat for a support ticket?

Settings → Export Snapshot (Phase 18-B). Produces a self-contained `.zip` with chat history + audit log + Custom Instructions + crash logs. Secrets are already redacted by Phase 13-D's `SECRET_FIELDS` filter.

## How do I install NYRA tools in Claude Code / Cursor / VS Code / Rider?

Settings → MCP Configuration → Add to Editor → pick your IDE (Phase 12-A). Junie is in the closed-set list as well (Phase 19-I).

## Can I write my own tools?

Yes — Phase 14-D ships user-installable MCP tools. Drop a `.py` file into `Plugins/NYRA/UserTools/` with `NYRA_TOOL = {...}` metadata and an `async def execute(params, session, ws)`. Auto-discovered on next launch.

## Where do I get plugin extensions from other users?

Plugin marketplace (Phase 17-B) — Settings → Marketplace. Client is shipped; the marketplace server is gated on the founder deploying it.

## How do I run the on-device Stable Diffusion (no ComfyUI)?

Phase 17-A ships the lazy-loader. Install `diffusers` + `torch` into the bundled venv, then prompts with a reference image route through it instead of ComfyUI. See `inpaint/local_probe` to verify your install.

## What's the cost of a typical session?

Phase 14-B's cost forecaster reports USD per round trip before you click Send. For a typical 1500-token prompt + 1500-token response: Haiku ≈ $0.01, Sonnet ≈ $0.025, Opus ≈ $0.13 (Anthropic public pricing 2026-04-21).

## How do I pin a specific Claude model?

Settings → Model selector (Phase 10-3). The pin is per-conversation; closed sets prevent injection (Phase 10-3 closed-set rejects unknown models with -32043).

## How do I get reproducible output?

Phase 14-A: Settings → Reproducibility seed + temperature. Pin both and you'll get byte-identical output across runs.
