# Plan 03-06 Summary: Gemma 3 4B Offline Q&A (KNOW-03 / KNOW-04)

**Phase:** 03-ue5-knowledge-rag
**Plan:** 03-06
**Type:** execute / TDD
**Wave:** 2
**Autonomous:** true | **TDD:** true
**Depends on:** [02, 04]
**Blocking preconditions:** 03-02 KnowledgeRetriever complete, 03-04 SymbolGate wired, Gemma GGUF cached

## Objectives

Deliver `nyra_ask_offline(question, ue_version?) -> OfflineAnswer` as an MCP tool for users in offline mode, privacy mode, or whose Claude subscription is unavailable. The engine retrieves top-5 grounding chunks from LanceDB, pipes them into Gemma 3 4B IT QAT Q4_0 via llama-server (localhost HTTP), and always formats answers with KNOW-02 citations.

## What Was Built

### `OfflineEngine` class

```python
class OfflineEngine:
    def is_available() -> bool:
        """True if GGUF present AND llama-server reachable at port 18901."""

    def ensure_server() -> None:
        """Start llama-server if not already running. Waits 15s for health."""

    def ask(question, ue_version?, top_k=5) -> OfflineAnswer:
        # 1. Retrieve top-k chunks via self._retriever
        # 2. Build Gemma prompt with context block
        # 3. Stream tokens via localhost HTTP POST /completion
        # 4. Format citations (dedup by source_url)
        # Returns: OfflineAnswer(text, cited_sources, citations, model, inference_ms, chunks_used)

    def stream_ask(...) -> AsyncGenerator[str]:
        """Streaming variant — yields partial tokens as NDJSON."""
```

### Gemma prompt format

```
<start_of_turn>
You are NYRA, an Unreal Engine 5 expert assistant. Answer using ONLY the provided context.
If the answer is not in the context, say "I don't know based on my knowledge base."

Rules:
- Always cite using: [source](URL) — UE {version} — {chunk_type}: "...exact quote..."
- Use verbatim quotes from the context for each claim.
- Do not invent UE API calls not present in the context.

<context>
[Context 1]
Source: https://docs.unrealengine.com/...
Version: 5.4
Type: api_doc
Quote: "FVector defines a three-dimensional vector..."
Citation: [FVector](url) — UE 5.4 — api_doc: "FVector defines..."
</context>

<question>
{user question}
</question>

<answer>
```

### `nyra_ask_offline` MCP tool

```python
@_registry.tool(name="nyra_ask_offline")
def nyra_ask_offline(
    question: str,
    ue_version: str | None = None,
) -> dict:
    # Returns: {available, text, citations, cited_sources, model, inference_ms, chunks_used}
    # If model not present: {available: False, error: "Download from NYRA settings..."}
```

### `nyra_check_offline_mode` MCP tool

Returns `model_present`, `model_path`, `server_reachable`, `port` — used by the settings UI to show the offline status pill.

### Privacy mode toggle

`NyraSettings.privacy_mode: bool` controls routing: when `True`, NyraHost router redirects all inference to `OfflineEngine` instead of Claude. Bootstrap wizard prompts user to download Gemma if they enable offline mode.

## Tests

- `test_offline_engine.py` — availability checks, prompt format, citation deduplication, retriever integration
- `test_prompt_includes_citation_format` — verifies `[citation]` pattern present in prompt
- `Nyra.Offline.It cites` — dedup of cited_sources (two chunks with same URL → appears once)

## Files Created

| File | Purpose |
|------|---------|
| `NyraHost/nyra_host/offline/offline_engine.py` | OfflineEngine + OfflineAnswer dataclass |
| `NyraHost/nyra_host/offline/mcp_tools.py` | `nyra_ask_offline` + `nyra_check_offline_mode` |
| `NyraHost/nyra_host/offline/settings.py` | `NyraSettings.privacy_mode` toggle |
| `NyraHost/tests/test_offline_engine.py` | Full TDD suite |

## Module-Superset Discipline

No prior Phase 1-2 code modified. `NyraHost/nyra_host/offline/` package (sibling to `rag/`, `symbols/`, `knowledge/`). `llama-server` binary bundled in `Binaries/ThirdParty/llama.cpp/`.

## Next Steps

- Plan 03-07 builds the CI/CD pipeline that generates LanceDB index release assets
- Plan 03-08 runs `KnowledgeBench` and produces the phase-exit gate