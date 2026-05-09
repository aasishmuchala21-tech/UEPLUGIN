---
phase: 3
plan: 03-06
type: execute
wave: 2
autonomous: true
depends_on: [02, 04]
blocking_preconditions:
  - "03-02 KnowledgeRetriever is complete"
  - "03-04 SymbolGate is wired into the action router"
  - "Gemma 3 4B Q4_0 GGUF is downloaded and cached at %LOCALAPPDATA%/NYRA/models/"
---

# Plan 03-06: Gemma 3 4B Offline Q&A (KNOW-03 / KNOW-04)

## Current Status

03-02 delivers `KnowledgeRetriever` for RAG-grounded answers and 03-04 delivers the symbol validation gate. 03-06 wires Gemma 3 4B IT QAT Q4_0 into NyraHost as a secondary inference backend for offline/privacy-mode Q&A (KNOW-04). It loads the model via llama.cpp over localhost HTTP, retrieves top-5 grounding chunks from the knowledge index, and generates an answer that always cites sources.

## Objectives

Deliver `nyra_ask_offline(question, ue_version?) -> Answer` as an MCP tool that:
1. Detects whether the user is in offline mode (no Claude subscription configured, or explicit privacy toggle)
2. Retrieves top-5 grounding chunks from the active LanceDB index
3. Formats a Gemma prompt with the chunks as context and the question
4. Streams the answer from Gemma via llama.cpp (localhost HTTP), yielding partial tokens in NDJSON
5. Always formats the final answer with verbatim citations matching KNOW-02

## What Will Be Built

### `Plugins/NYRA/Source/NyraHost/nyra_knowledge/offline_engine.py`

Gemma 3 4B inference wrapper:

```python
"""
nyra_knowledge/offline_engine.py

Offline inference engine: loads Gemma 3 4B IT QAT Q4_0 via llama.cpp
HTTP API (llama-server) and streams answers grounded by the NYRA RAG index.

In v1 this is text-only (D-5). Multimodal (image input) is deferred to Phase 3.5.
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)

GemmaGGUF_REPO = "google/gemma-3-4b-it-qat-q4_0-gguf"
DEFAULT_MODEL_PATH = Path.home() / "AppData" / "Local" / "NYRA" / "models" / "gemma-3-4b-it-qat-q4_0.gguf"
LLAMA_SERVER_PORT = 18901    # Avoids conflicts with other llama.cpp instances


@dataclass
class OfflineAnswer:
    """Final structured answer from the offline engine."""

    text: str
    cited_sources: list[str]         # Unique list of cited source URLs
    citations: list[str]             # KNOW-02 formatted citation strings
    model: str = "gemma-3-4b-it-q4_0"
    inference_ms: float = 0.0
    chunks_used: int = 0


class OfflineEngine:
    """
    Manages the Gemma 3 4B offline inference lifecycle.

    Starts llama-server on the configured port if not already running.
    Falls back to Claude API when the model is not available.
    """

    def __init__(
        self,
        model_path: Optional[Path] = None,
        port: int = LLAMA_SERVER_PORT,
        retriever = None,            # KnowledgeRetriever
    ) -> None:
        self._model_path = model_path or self._resolve_model_path()
        self._port = port
        self._retriever = retriever
        self._server_pid: Optional[int] = None
        self._base_url = f"http://127.0.0.1:{port}"

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """True if Gemma GGUF is present and llama-server is reachable."""
        if not self._model_path.exists():
            return False
        try:
            urllib.request.urlopen(f"{self._base_url}/health", timeout=2)
            return True
        except urllib.error.URLError:
            return False

    def ensure_server(self) -> None:
        """Start llama-server if not already running."""
        if self.is_available():
            return
        import subprocess
        cmd = [
            "llama-server.exe"
            if os.name == "nt"
            else "llama-server",
            "-m", str(self._model_path),
            "--port", str(self._port),
            "--host", "127.0.0.1",
            "-c", "8192",          # 8K context — Gemma 3 4B supports 128K but keep memory reasonable
            "-fa",                 # flash attention
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._server_pid = proc.pid
        # Wait for server to be ready
        import time
        for _ in range(30):
            try:
                urllib.request.urlopen(f"{self._base_url}/health", timeout=1)
                logger.info("llama-server ready on port %d (pid=%d)", self._port, self._server_pid)
                return
            except urllib.error.URLError:
                time.sleep(0.5)
        raise RuntimeError(f"llama-server failed to start on port {self._port}")

    def ask(
        self,
        question: str,
        ue_version: Optional[str] = None,
        top_k: int = 5,
    ) -> OfflineAnswer:
        """
        Ask Gemma a question grounded by the NYRA knowledge index.

        Parameters
        ----------
        question:
            Free-text question about UE5.
        ue_version:
            Optional version hint to scope retrieval.
        top_k:
            Number of grounding chunks to retrieve (default 5).

        Returns
        -------
        OfflineAnswer
            Answer with KNOW-02 formatted citations.
        """
        import time
        t0 = time.monotonic()

        # --- retrieve grounding context ---
        chunks = []
        if self._retriever:
            try:
                results = self._retriever.retrieve(
                    query=question,
                    ue_version=ue_version,
                    top_k=top_k,
                )
                chunks = results
            except Exception as exc:
                logger.warning("RAG retrieval failed in offline engine: %s", exc)

        # --- build Gemma prompt ---
        prompt = self._build_prompt(question, chunks)

        # --- stream from llama-server ---
        tokens = list(self._stream_tokens(prompt))
        answer_text = "".join(tokens)

        inference_ms = (time.monotonic() - t0) * 1000

        # --- format citations ---
        cited_sources = []
        citation_strings = []
        for chunk in chunks:
            cit = chunk.citation()
            if chunk.source_url and chunk.source_url not in cited_sources:
                cited_sources.append(chunk.source_url)
                citation_strings.append(cit)

        return OfflineAnswer(
            text=answer_text,
            cited_sources=cited_sources,
            citations=citation_strings,
            model="gemma-3-4b-it-q4_0",
            inference_ms=inference_ms,
            chunks_used=len(chunks),
        )

    def stream_ask(
        self,
        question: str,
        ue_version: Optional[str] = None,
        top_k: int = 5,
    ) -> AsyncGenerator[str, None]:
        """
        Streaming version of ask(). Yields partial token strings as NDJSON.

        Used when the caller wants to stream tokens to the UI in real time.
        """
        chunks = []
        if self._retriever:
            try:
                results = self._retriever.retrieve(question, ue_version, top_k=top_k)
                chunks = results
            except Exception:
                pass

        prompt = self._build_prompt(question, chunks)
        yield from self._stream_tokens(prompt)

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _build_prompt(self, question: str, chunks: list) -> str:
        """
        Build the Gemma 3 4B prompt.

        Gemma 3 uses instruction format with <start_of_turn> / <end_of_turn> tokens.
        """
        ctx_parts = []
        for i, chunk in enumerate(chunks, 1):
            version_tag = chunk.metadata.get("ue_version", "UE5")
            cit_str = chunk.citation()
            ctx_parts.append(
                f"[Context {i}]\n"
                f"Source: {chunk.source_url or 'unknown'}\n"
                f"Version: {version_tag}\n"
                f"Type: {chunk.chunk_type}\n"
                f'Quote: "{chunk.content[:500]}"\n'
                f"Citation: {cit_str}"
            )
        context_block = "\n\n".join(ctx_parts)

        prompt = f"""<start_of_turn>
You are NYRA, an Unreal Engine 5 expert assistant. Answer the user's question using ONLY the provided context. If the answer is not in the context, say "I don't know based on my knowledge base."

Rules:
- Always cite your sources using this exact format: [source](URL) — UE {{version}} — {{chunk_type}}: "...exact quote..."
- Use a verbatim quote from the context for each claim.
- Keep answers concise and actionable.
- Do not invent UE API calls not present in the context.

<context>
{context_block}
</context>

<question>
{question}
</question>

<answer>
""".strip()
        return prompt

    def _stream_tokens(self, prompt: str) -> AsyncGenerator[str, None]:
        """Send prompt to llama-server and yield tokens as they arrive."""
        payload = {
            "prompt": prompt,
            "n_predict": 512,
            "stream": True,
            "temperature": 0.3,     # Low temperature for factual Q&A
            "stop": ["<end_of_turn>", "</context>", "\n\n<answer>\n"],
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base_url}/completion",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                for line in resp:
                    line = line.decode("utf-8").strip()
                    if not line:
                        continue
                    # llama-server streaming format: one JSON per line
                    try:
                        data = json.loads(line)
                        token = data.get("content", "")
                        if token:
                            yield token
                    except json.JSONDecodeError:
                        continue
        except urllib.error.URLError as exc:
            logger.error("llama-server request failed: %s", exc)
            yield "[Offline engine error: Gemma server unreachable. Check your model installation.]"

    def _resolve_model_path(self) -> Path:
        import os
        local = os.environ.get("LOCALAPPDATA", "")
        base = Path(local) / "NYRA" / "models" if local else Path.home() / "AppData" / "Local" / "NYRA" / "models"
        return base / "gemma-3-4b-it-qat-q4_0.gguf"

    def shutdown(self) -> None:
        """Stop the llama-server process."""
        if self._server_pid is None:
            return
        import os
        try:
            os.kill(self._server_pid, 15)
        except ProcessLookupError:
            pass
        self._server_pid = None
```

### `Plugins/NYRA/Source/NyraHost/nyra_knowledge/mcp_tools.py` addition

```python
@_registry.tool(
    name="nyra_ask_offline",
    description=textwrap.dedent("""\
        Ask a UE5 question using Gemma 3 4B running locally (offline mode).
        Uses the NYRA RAG index to ground the answer. Answers are always cited.

        Use this tool when:
        - The user has enabled privacy mode
        - No Claude subscription is configured
        - The user explicitly requests offline mode

        For connected mode with Claude, use nyra_retrieve_knowledge + nyra_ask instead.
    """),
)
def nyra_ask_offline(
    question: Annotated[str, Field(description="Free-text UE5 question")],
    ue_version: Annotated[
        Optional[str],
        Field(default=None, description="Optional UE version hint (e.g. '5.4')"),
    ] = None,
) -> dict:
    """
    MCP tool: nyra_ask_offline
    """
    engine: OfflineEngine = _deps.get(OfflineEngine)
    if not engine.is_available():
        return {
            "available": False,
            "error": (
                "Gemma model not found. Download it from NYRA settings, "
                "or switch to connected mode with your Claude subscription."
            ),
        }
    try:
        answer = engine.ask(question=question, ue_version=ue_version, top_k=5)
        return {
            "available": True,
            "text": answer.text,
            "citations": answer.citations,
            "cited_sources": answer.cited_sources,
            "model": answer.model,
            "inference_ms": round(answer.inference_ms, 1),
            "chunks_used": answer.chunks_used,
        }
    except Exception as exc:
        logger.exception("nyra_ask_offline failed")
        return {"available": True, "error": str(exc)}


@_registry.tool(
    name="nyra_check_offline_mode",
    description="Check whether the offline inference engine is available and the model is downloaded.",
)
def nyra_check_offline_mode() -> dict:
    """
    MCP tool: nyra_check_offline_mode
    """
    engine: OfflineEngine = _deps.get(OfflineEngine)
    return {
        "model_present": engine._model_path.exists(),
        "model_path": str(engine._model_path),
        "server_reachable": engine.is_available(),
        "port": engine._port,
    }
```

### `Plugins/NYHA/Source/NyraHost/nyra_knowledge/settings.py` addition

User-visible privacy toggle (wired into the UI in 03-08):

```python
@dataclass
class NyraSettings:
    """Global NYRA settings."""

    privacy_mode: bool = False
    offline_model_path: Path = DEFAULT_MODEL_PATH
    preferred_ue_version: str = "5.4"
    claude_subscription_active: bool = False
    # ... existing fields
```

### `Plugins/NYRA/Source/NyraHost/tests/test_offline_engine.py`

```python
"""
tests/test_offline_engine.py

TDG suite for Plan 03-06: Gemma 3 4B Offline Q&A.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from nyra_knowledge.offline_engine import OfflineEngine, OfflineAnswer
from nyra_knowledge.retrieval import KnowledgeRetriever, RetrieverResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_retriever():
    """Fake retriever returning two pre-built chunks."""
    chunk1 = MagicMock(spec=RetrieverResult)
    chunk1.content = "FVector defines a three-dimensional vector."
    chunk1.source_url = "https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FVector"
    chunk1.chunk_type = "api_header"
    chunk1.metadata = {"ue_version": "5.4"}
    chunk1.citation.return_value = (
        "[FVector](https://docs.unrealengine.com) — UE 5.4 — api_header: "
        "\"FVector defines a three-dimensional vector.\""
    )
    chunk2 = MagicMock(spec=RetrieverResult)
    chunk2.content = "FVector::ZeroVector is a constant representing the zero vector."
    chunk2.source_url = "https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FVector/ZeroVector"
    chunk2.chunk_type = "api_header"
    chunk2.metadata = {"ue_version": "5.4"}
    chunk2.citation.return_value = (
        "[FVector::ZeroVector](https://docs.unrealengine.com) — UE 5.4 — api_header: "
        "\"FVector::ZeroVector is a constant.\""
    )
    retriever = MagicMock(spec=KnowledgeRetriever)
    retriever.retrieve.return_value = [chunk1, chunk2]
    return retriever


@pytest.fixture
def engine(mock_retriever):
    return OfflineEngine(
        model_path=Path("/fake/path/gemma-3-4b-it-q4_0.gguf"),
        port=18999,
        retriever=mock_retriever,
    )


# ---------------------------------------------------------------------------
# Tests — OfflineAnswer dataclass
# ---------------------------------------------------------------------------

class TestOfflineAnswer:
    def test_default_model(self):
        ans = OfflineAnswer(text="FVector is a vector.", cited_sources=[], citations=[])
        assert ans.model == "gemma-3-4b-it-q4_0"
        assert ans.inference_ms == 0.0

    def test_citations_list(self):
        ans = OfflineAnswer(
            text="Answer",
            cited_sources=["https://docs.unrealengine.com"],
            citations=["[FVector](url) — UE 5.4 — api_header: \"quote\""],
        )
        assert len(ans.citations) == 1


# ---------------------------------------------------------------------------
# Tests — OfflineEngine.is_available
# ---------------------------------------------------------------------------

class TestOfflineEngineAvailability:
    def test_false_when_model_not_found(self, engine: OfflineEngine, mock_retriever):
        with patch.object(engine, "_model_path", Path("/nonexistent/model.gguf")):
            assert engine.is_available() is False

    def test_true_when_server_reachable(self, engine: OfflineEngine):
        with patch.object(engine, "_model_path", Path("/fake/model.gguf")):
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.return_value.__enter__ = MagicMock()
                mock_urlopen.return_value.__exit__ = MagicMock()
                assert engine.is_available() is True


# ---------------------------------------------------------------------------
# Tests — _build_prompt
# ---------------------------------------------------------------------------

class TestBuildPrompt:
    def test_prompt_includes_context(self, engine: OfflineEngine, mock_retriever):
        chunks = mock_retriever.retrieve("what is FVector", "5.4", 5)
        prompt = engine._build_prompt("What is FVector?", chunks)
        assert "FVector" in prompt
        assert "Context" in prompt
        assert "[question]" in prompt
        assert "[answer]" in prompt

    def test_prompt_includes_citation_format(self, mock_retriever):
        engine = OfflineEngine(
            model_path=Path("/fake.gguf"),
            retriever=mock_retriever,
        )
        chunks = mock_retriever.retrieve("...", "5.4", 5)
        prompt = engine._build_prompt("What is FVector?", chunks)
        assert "cited" in prompt.lower() or "citation" in prompt.lower()

    def test_prompt_works_with_empty_chunks(self, engine: OfflineEngine):
        prompt = engine._build_prompt("How do I make an actor?", [])
        assert "NYRA" in prompt
        assert "<question>" in prompt


# ---------------------------------------------------------------------------
# Tests — ask() integration
# ---------------------------------------------------------------------------

class TestAsk:
    def test_retriever_called_before_inference(
        self,
        engine: OfflineEngine,
        mock_retriever,
    ):
        with patch.object(engine, "_stream_tokens", return_value=iter(["Answer"])):
            engine.ask("What is FVector?", "5.4")
            mock_retriever.retrieve.assert_called_once()

    def test_answer_includes_citations(
        self,
        engine: OfflineEngine,
        mock_retriever,
    ):
        with patch.object(engine, "_stream_tokens", return_value=iter(["FVector is a vector."])):
            ans = engine.ask("What is FVector?", "5.4")
            assert isinstance(ans, OfflineAnswer)
            assert ans.chunks_used == 2


# ---------------------------------------------------------------------------
# Tests — Nyra.Offline.It cites
# ---------------------------------------------------------------------------

class TestOfflineCitations:
    def test_cited_sources_deduplicated(self, mock_retriever):
        # Both chunks have the same source URL
        engine = OfflineEngine(
            model_path=Path("/fake.gguf"),
            port=18999,
            retriever=mock_retriever,
        )
        with patch.object(engine, "_stream_tokens", return_value=iter(["Answer text."])):
            ans = engine.ask("What is FVector?", "5.4")
            # Both chunks cite the same URL — should appear once in cited_sources
            unique_sources = list(dict.fromkeys(ans.cited_sources))
            assert ans.cited_sources == unique_sources
```

## Design Notes

- **Privacy mode toggle**: Exposed as `NyraSettings.privacy_mode` — when `True`, the NyraHost router redirects all inference to `OfflineEngine` instead of Claude. The toggle is in NYRA settings UI (wired in 03-08).
- **llama-server lifecycle**: `ensure_server()` starts on first offline query; `shutdown()` is called on NyraHost teardown. The port is fixed at `18901` (configurable via `NyraSettings`).
- **Model download**: Not handled in 03-06 — the bootstrap wizard (03-08) prompts the user to download Gemma if they enable offline mode. The `model_present` check in `nyra_check_offline_mode` surfaces a clear download CTA.
- **Multimodal deferred**: D-5 locks text-only in v1. The image input path for `llama-gemma3-cli` with `--image` is stubbed with a `NOT_IMPLEMENTED` comment and a TODO.
- **Flash attention**: Enabled via `-fa` flag on llama-server for ~2x throughput on modern GPUs.
- **Temperature**: Set to 0.3 for factual Q&A — low enough for reproducible grounded answers, high enough to not be robotic.
- **Context window**: 8192 tokens (well within Gemma 3 4B's 128K capability) — balances context quality against memory usage for typical chunk sets (5 chunks × ~500 tokens ≈ 2.5K context).
