---
phase: 3
slug: ue5-knowledge-rag
status: draft
discussed_at: 2026-05-07
grey_areas: 6
consensus_threshold: founder-review
---

# Phase 3: UE5 Knowledge RAG - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning
**Source:** /gsd:discuss-phase (6 grey areas, 6 decisions locked with provisional positions)

## Phase Boundary

Phase 3 delivers the UE5 Knowledge RAG system: NYRA answers "how do I do X in UE5" questions with verbatim-quote citations tagged to the user's UE version, validates cited symbols against the user's installed UE headers before any action, and refreshes its index same-day or next-day after Epic ships a new UE version.

**Requirements this phase satisfies:** KNOW-01, KNOW-02, KNOW-03, KNOW-04.

**Depends on:** Phase 2 (agent router + Gemma fallback + CI matrix).

**Out of scope for Phase 3:**
- Claude Code CLI subprocess driving → Phase 2 (SUBS-01)
- MCP server hosting + tool catalog → Phase 4+ (already deferred from Phase 1)
- API-first tool integrations (Meshy, ComfyUI, Blender) → Phase 5
- Fab launch prep → Phase 8

</domain>

<grey_areas>
## Grey Areas

| # | Area | Pre-selected Position | Confidence | Kill Criteria |
|---|------|----------------------|------------|---------------|
| GA-1 | Index tiering strategy | Bootstrap 50 MB bundled + full index download on first run | MEDIUM-HIGH | If Fab hard-limits listing artifact to <80 MB, tier down to pure-on-demand streaming |
| GA-2 | Corpus coverage scope | Conservative: UE official docs + C++ headers + Blueprint node reference only | HIGH | If Epic releases a "community docs" license in future that explicitly covers forum content |
| GA-3 | Embedding model choice | BGE-small-en-v1.5 (133 MB) over all-MiniLM-L6-v2 (90 MB) | MEDIUM-HIGH | If BGE-small ONNX fails to compile in UE NNE / DirectML at acceptable speed |
| GA-4 | Symbol validation timing | Pre-execution gate (before any UE API action) over query-time or UHT intercept | HIGH | If pre-execution gate latency is >500 ms per action in a real chat scenario, move to background validation with a warning |
| GA-5 | Gemma 3 4B offline Q&A mode | Text-only MVP; Gemma vision (multimodal) as Phase 3.5 extension | MEDIUM | If Phase 2 Gemma integration already ships with multimodal working and Phase 3 extends it for free |
| GA-6 | Index refresh trigger | GitHub Release on Epic tag (automatic) + user "Update Knowledge" button (manual) | HIGH | If Epic does not publish a standard release tag format; fallback to community-maintained changelog scraper |

</grey_areas>

<decisions>
## Decisions

### D-1: Index Tiering Strategy

**Decision text:**
NYRA ships a two-tier index: a 50 MB bootstrap bundle in the plugin listing, and a full index downloaded on first run with user consent. The bootstrap covers UE 5.4–5.6 core documentation; the full index adds UE 5.7, Blueprint node reference, and C++ API header chunks. This is not pure-on-demand streaming — the index must be local for KNOW-04 offline Q&A to work.

**Selected position:** Two-tier (bootstrap + download-on-first-run)

**Rationale:**
Pure-on-demand streaming fails the KNOW-04 requirement: Gemma offline Q&A needs a local index, not a network-dependent one. Pure-on-demand also makes the hallucination-squashing benchmark (<2%) harder to measure — symbol validation requires a deterministic local corpus. The 50 MB bootstrap gives immediate utility on first install (even before download completes, users can ask questions about 5.4–5.6 docs). First-run download with consent is standard practice (Gemma model download already follows this pattern in Phase 1). The Fab listing artifact size budget is not yet confirmed as a hard limit; if it is <80 MB, the tiering collapses to pure-on-demand streaming with a warning that KNOW-04 becomes "text-only offline mode" until the index downloads.

**Trade-offs considered:**
- Bootstrap 50 MB + download: gives immediate value, supports offline, but increases Fab artifact size
- Pure-on-demand streaming: smallest artifact, but KNOW-04 offline mode is degraded to text-only with no RAG grounding
- Pure-on-demand with background prefetch: intermediate, but prefetch logic adds complexity for marginal gain

**Kill criteria:** Fab hard-limits listing artifact to <80 MB → fall back to pure-on-demand streaming with degraded KNOW-04.

---

### D-2: Corpus Coverage Scope

**Decision text:**
NYRA's Phase 3 index contains only: UE5 official docs (5.4–5.7), Blueprint node reference, C++ API headers (UCLASS, UFUNCTION, UPROPERTY, etc.), Epic forum posts with explicit license/attribution, and community transcripts (Discord, Reddit) only if they are explicitly CC-licensed or public domain. BlueprintCompendium and open UE courses are included only if they carry an explicit license permitting redistribution and indexing. Hard block: paid-course domains (Udemy, Skillshare, Unreal Fellowship, Domestika, ArtStation Learning) and any content behind a paywall or ToS that prohibits scraping.

**Selected position:** Conservative whitelist

**Rationale:**
The architectural gate says "Corpus is license-clean only." Epic forum posts are a grey area — Epic's forum ToS as of 2026 does not explicitly grant redistribution rights, but Epic also publishes official docs under a permissive license. Until Epic clarifies, forum posts are excluded from Phase 3. Community Discord/Reddit transcripts carry user-generated content ToS that is at best ambiguous for indexing; CC-licensed posts are included only if the scraper can verify the license field programmatically. BlueprintCompendium (if it ships under MIT/CC-BY) is a strong candidate to include — planner must verify its license in Phase 3 research. Paid courses are a hard no: the "no new AI bill" wedge extends to "no scraped paid content" in the corpus.

**Trade-offs considered:**
- Conservative whitelist (chosen): low risk, defensible, but corpus is smaller than competitors — Aura/CoPilot may have broader coverage
- Aggressive inclusion with legal review: more coverage but legal exposure on Epic forum ToS interpretation
- Community-only with AI-generated filter: technically complex to implement reliably

**Kill criteria:** Epic releases explicit community docs license covering forum content → add Epic forum posts immediately.

---

### D-3: Embedding Model Choice

**Decision text:**
NYRA uses BGE-small-en-v1.5 (133 MB ONNX, 384-dim, MTEB 62.17, MIT license) for all indexing and retrieval. all-MiniLM-L6-v2 (~90 MB, MTEB ~57) is retained as a fallback if BGE-small fails to compile in UE NNE / DirectML at acceptable latency, or if Fab's artifact size budget proves to be a hard constraint below 150 MB.

**Selected position:** BGE-small-en-v1.5

**Rationale:**
The MTEB gap (62.17 vs ~57) translates directly to retrieval quality for technical UE queries. On a "how do I use UPROPERTY MetaData?" query, the extra 5 MTEB points matter — the top retrieved chunk is the difference between a verbatim answer and a near-miss. The 43 MB delta (133 vs 90) is immaterial given that the bootstrap index itself is 50 MB and the bundled ONNX model is a separate artifact. If the 133 MB ONNX compiles in NNE/DirectML at acceptable speed (<100 ms per embedding batch of 512 tokens), there is no downside. The MIT license is clean for Fab distribution.

**Trade-offs considered:**
- BGE-small (chosen): higher quality, 133 MB, acceptable bundle cost
- all-MiniLM-L6-v2: smaller (90 MB), lower quality, fallback only
- Qwen3-Embedding-0.6B: highest quality (MTEB 70.70) but 1.2 GB — too large to bundle, optional download is a Phase 4+ nicety

**Kill criteria:** BGE-small ONNX fails NNE/DirectML compilation or runs >500 ms per batch → switch to all-MiniLM-L6-v2 as emergency fallback.

---

### D-4: Symbol Validation Timing

**Decision text:**
NYRA validates symbols at a pre-execution gate — immediately before any action that calls a UE API. This means: RAG retrieves chunks (including potentially hallucinated API symbols), the answer is generated with verbatim citations, and then before the agent executes the first UE API call in its plan, NyraHost runs a symbol-existence check against the user's installed UE headers (located via the .uproject or registry on Windows). If the symbol is not found, NYRA surfaces a warning to the user: "The cited symbol `UMyClass::DoThing` was not found in your UE 5.6 headers. This may be a hallucination. Do you want to proceed anyway?" — and blocks the action by default, requiring explicit user override.

**Selected position:** Pre-execution gate

**Rationale:**
Query-time validation (during RAG retrieval) is too late to matter: if RAG has already returned a hallucinated symbol in a chunk, the validation would either reject the chunk (reducing recall) or need to re-run the query with a different retrieval strategy. That adds complexity and latency without meaningfully improving the user's experience. UHT intercept (at compile time) is architecturally complex — NYRA would need to either hook into UBT's pipeline or ship a UHT plugin — and it only catches compile-time symbols, not runtime API calls. Pre-execution gate is the minimal viable approach: it catches hallucinations at the point where they matter (before the UE engine mutates state), it gives the user agency to override with full information, and it is measurable against the <2% hallucination target (count false-positive symbol warnings vs. true hallucinations in the golden-set Q&A suite).

**Trade-offs considered:**
- Query-time (RAG retrieval): too late; rejects good chunks, adds latency, doesn't help the user
- Pre-execution gate (chosen): minimal viable, measurable, user agency preserved
- UHT intercept: too complex, only catches compile-time symbols, out of scope for Phase 3

**Kill criteria:** Pre-execution gate latency is >500 ms per action in real chat scenarios → move validation to background with a "validation in progress" indicator and proceed with a warning badge on the action.

---

### D-5: Gemma 3 4B Offline Q&A Mode

**Decision text:**
NYRA's minimum viable offline mode for KNOW-04 is text-only Q&A with RAG grounding. Gemma 3 4B (multimodal, Q4_0) handles text-based documentation Q&A by retrieving from the local LanceDB index and generating answers. The multimodal vision capability (Gemma can process reference images) ships as a Phase 3.5 extension — NOT in Phase 3 MVP. Phase 3 offline mode explicitly does not attempt to run Gemma vision on attached screenshots in the chat panel.

**Selected position:** Text-only MVP

**Rationale:**
Gemma 3 4B's vision scores (DocVQA 72.8%, TextVQA 58.9%) are sufficient for lighting-description tasks but not strong enough to reliably interpret complex UE editor screenshots (which are visually dense and domain-specific). Implementing multimodal image handling in the offline path requires: (1) encoding images in Gemma-compatible format, (2) managing the multimodal model's higher memory footprint, (3) handling image+text interleaving in the chat pipeline. All three are non-trivial and would push Phase 3 scope beyond a single sprint. Text-only Q&A against the local RAG index still delivers genuine offline value — users can ask "how do I set up a physics constraint?" or "what does UPROPERTY EditInline do?" without an internet connection. The multimodal extension is a natural Phase 3.5 candidate: it requires the same NyraHost infrastructure, the same Gemma runtime, and only adds image encoding.

**Trade-offs considered:**
- Text-only MVP (chosen): minimal scope, reliable quality, clear Phase 3.5 extension point
- Multimodal from day one: higher capability but complex scope creep; Gemma vision quality on UE screenshots is unverified
- No offline mode at all: fails KNOW-04; "first-class enterprise differentiator" claim from ROADMAP cannot be made

**Kill criteria:** Phase 2 Gemma integration already ships with multimodal working → evaluate whether Phase 3 multimodal is a free extension; if so, include it in Phase 3 scope.

---

### D-6: Index Refresh Trigger

**Decision text:**
NYRA's index refresh is triggered by two mechanisms working in parallel: (1) A GitHub Actions workflow that triggers on Epic's official GitHub release tags (unreal-engine repository uses semantic tags like `5.7.0-release`), builds a new LanceDB index for that UE version, and publishes it as a GitHub Release asset. (2) A user-facing "Update Knowledge" button in the plugin settings panel that checks for a new release and downloads it on demand. Scheduled weekly background check is NOT implemented in Phase 3 MVP — the GitHub Release trigger is the primary refresh mechanism, with manual button as user agency fallback.

**Selected position:** GitHub Release on Epic tag (automatic) + user button (manual)

**Rationale:**
The ROADMAP's success criterion #1 explicitly requires "day-of support for new UE releases via a GitHub-Releases index-build pipeline triggered on Epic release tags." This is the primary differentiator claim — no competitor publishes day-of UE version support. The GitHub Actions pipeline watches the `unreal-engine` repository for semantic-version tags matching `X.Y.0-release` (or `X.Y.Z-release` for patch releases), and on trigger: clones the new UE version's documentation snapshot, re-runs the ingestion pipeline, and publishes a new `nyra-index-ue-X.Y.Z.lance` artifact. The user button handles the "I'm on an older version and want to force-refresh" case. Weekly scheduled checks are deferred because: (a) Epic does not ship new UE versions on a weekly cadence, so the check would mostly be wasted, (b) a background network call every week is a privacy concern that may concern enterprise users, (c) the automatic GitHub Release trigger handles the only scenario that matters — new UE release.

**Trade-offs considered:**
- GitHub Release + user button (chosen): meets day-of support requirement, respects user agency, minimal background network
- Scheduled weekly check: unnecessary for Epic's release cadence, adds background network for privacy-sensitive users
- User-button only: no day-of support claim; misses the primary differentiator
- Pure automatic: no user agency, no way for users on airgapped networks to refresh

**Kill criteria:** Epic does not publish standard release tag format in the `unreal-engine` GitHub repo → fallback to a community-maintained changelog scraper that monitors Epic's official UE5 release notes page; update trigger becomes manual check + weekly background polling of the release notes URL.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-level (mandatory)
- `.planning/PROJECT.md` — Vision, constraints, NYRA's core value ("turn a reference into a finished UE scene"), no-new-bill wedge, solo-dev timeline
- `.planning/REQUIREMENTS.md` — KNOW-01 through KNOW-04 requirement IDs; Phase 3 must address all four
- `.planning/ROADMAP.md` §"Phase 3: UE5 Knowledge RAG" — success criteria, depends-on, requirements map
- `.planning/STATE.md` — current project state
- `CLAUDE.md` §"RAG Backend (UE5 Knowledge Index)" — LanceDB, BGE-small, GitHub Releases for index distribution, embedding model rationale

### Research synthesis (mandatory)
- `.planning/research/SUMMARY.md` — cross-researcher synthesis; §"Stack (Verified — LOCKED)" includes LanceDB 0.13+ and BGE-small-en-v1.5
- `.planning/research/STACK.md` — verified versions for LanceDB, BGE-small (133 MB ONNX, 384-dim, MTEB 62.17, MIT), all-MiniLM-L6-v2
- `.planning/research/FEATURES.md` — TS5 (RAG knowledge) differentiator details; TS10 (offline Gemma fallback)
- `.planning/research/PITFALLS.md` — §8.1 hard block on paid-course domains; §5 (RAG corpus quality)

### Phase context (related phases)
- `.planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md` — Phase 1 process model, NyraHost lifecycle, D-17/D-18 (Gemma download + llama-server patterns), establishes the download-on-first-run precedent for D-1
- `.planning/phases/02-subscription-bridge-ci-matrix/PLAN.md` (when available) — Phase 2 CI matrix for multi-version compilation, relevant for KN-01 symbol validation against installed headers

### External specs
- LanceDB docs — `https://lancedb.io/docs/` — Python binding, file-based, no server; 0.13+ for Python binding
- BGE-small-en-v1.5 — `https://huggingface.co/BAAI/bge-small-en-v1.5` — 133 MB ONNX, 384-dim, MTEB 62.17, MIT license
- all-MiniLM-L6-v2 — `https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2` — 90 MB, MTEB ~57, fallback
- Unreal Engine GitHub — `https://github.com/EpicGames/UnrealEngine` — release tag format for GitHub Actions trigger
- Gemma 3 4B IT — `https://huggingface.co/google/gemma-3-4b-it` — multimodal confirmed; DocVQA 72.8%, TextVQA 58.9%

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Phase 1's download-on-first-run pattern** — D-17/D-18 in Phase 1 CONTEXT.md establish the user-consent download pattern, SHA256 verification, progress modal, and `%LOCALAPPDATA%/NYRA/models/` cache directory. Phase 3's index download reuses the same infrastructure: progress UI, retry/resume via HTTP Range, SHA256 verification.
- **NyraHost Python package** — `Plugins/NYRA/Source/NyraHost/` is already scaffolded in Phase 1. The RAG ingestion pipeline and LanceDB access live here in Phase 3. The same MCP server infrastructure serves both Phase 1 chat and Phase 3 RAG retrieval.
- **llama.cpp bundled binary pattern** — Phase 1 ships `llama-server.exe` in `Binaries/Win64/NyraInfer/`. Phase 3's BGE-small ONNX can be optionally run via the same NNE/DirectML backend; falls back to Python `onnxruntime` with CPU if NNE is unavailable.
- **Error remediation framing** — D-11 in Phase 1 sets the pattern: `error.data.remediation` is a human-copy string the panel renders as-is. D-4's symbol validation warning reuses this pattern: "The cited symbol `X` was not found. Do you want to proceed anyway?" is the remediation string.

### Established Patterns
- GSD planning phases: CONTEXT.md → RESEARCH.md → PLAN.md → execution. Honour this in Phase 3.
- Requirement ID convention (KNOW-NN) from REQUIREMENTS.md.
- Phase 1 decisions are architectural constraints: three-process model, Python sidecar, embedded CPython, download-on-first-run with progress UI.

### Integration Points
- **NyraHost** gains: RAG retrieval endpoint (new MCP tool `rag/query`), LanceDB index, BGE-small ONNX embedding model, index download manager.
- **NyraEditor** gains: "Update Knowledge" button in Settings panel, symbol validation result display in chat (warning badge on hallucinated API calls).
- **Phase 2 subscription bridge** wires Claude's responses into the RAG retrieval layer (knowledge grounding before action).
- **Phase 3 index pipeline** GitHub Actions workflow must have a trigger on Epic's release tags — verify the exact tag format in Phase 3 research.

</code_context>

<specifics>
## Specific Ideas

- **Golden-set Q&A benchmark suite** — Phase 3 must ship a measurable hallucination rate. Planner should define the golden-set format (JSON with `question`, `expected_api_symbol`, `acceptable_alternatives` fields), the evaluation harness (run 200 questions, count symbol validation warnings), and the <2% target threshold. This is the primary success criterion for KNOW-02.
- **Index version manifest** — Every release ships a `versions.json` alongside the LanceDB artifact: `{index_version, ue_versions_covered, chunk_count, built_at, epic_release_tag}`. Plugin compares this against the user's installed UE version and prompts upgrade if mismatched.
- **Chunk-level verbatim citation** — RAG retrieval returns chunk ID + text. The answer generator must quote the exact chunk text (not paraphrase). Planner should specify how the verbatim quote is surfaced: `[source: ue5-docs::UCLASS::MetaData]` inline in markdown, with a hover tooltip showing the full chunk.
- **Symbol validation against UHT headers** — On Windows, UE installs headers to `%PROGRAMFILES%\Epic Games\UE_5.X\Engine\Source\`. The validation step scans for `#UCLASS`, `#UFUNCTION` etc. matching the cited symbol. Planner must decide: full UBT header scan (comprehensive but ~5-30s on cold) vs. pre-built symbol manifest (fast but must be updated per UE version).

</specifics>

<deferred>
## Deferred Ideas

Scope-creep temptations caught during discussion, noted for later phases:
- **Multimodal Gemma vision for offline mode** — Phase 3.5 extension. Requires image encoding pipeline, memory management for multimodal model, and visual quality validation on UE screenshots.
- **Weekly background refresh check** — Deferred. Epic's release cadence makes weekly checks mostly wasted; the GitHub Release trigger covers the scenario that matters.
- **Qwen3-Embedding-0.6B as optional HQ mode** — Phase 4+ nicety. 1.2 GB too large to bundle; offered as an optional download for users who want maximum RAG quality.
- **UHT intercept for compile-time symbol validation** — Deferred to Phase 4. Complex to implement and only catches compile-time symbols; pre-execution gate at query-time is sufficient for <2% hallucination target.
- **Epic forum posts inclusion** — Deferred pending Epic's clarification of community content redistribution rights. Revisit when Epic publishes a community docs license.
- **Community Discord/Reddit transcript scraping** — Deferred. User-generated content ToS is ambiguous; CC-licensed posts only after the scraper can verify the license field programmatically.
- **BlueprintCompendium inclusion** — Planner must verify its license in Phase 3 research. MIT/CC-BY = include; proprietary = exclude.

</deferred>

---

*Phase: 03-ue5-knowledge-rag*
*Context gathered: 2026-05-07 via /gsd:discuss-phase*
*Areas discussed: Index tiering (D-1), corpus scope (D-2), embedding model (D-3), symbol validation timing (D-4), Gemma offline mode (D-5), index refresh trigger (D-6)*
*Areas deferred to founder review: Fab artifact size budget (hard vs. soft limit), BlueprintCompendium license verification, Epic forum content clarification*