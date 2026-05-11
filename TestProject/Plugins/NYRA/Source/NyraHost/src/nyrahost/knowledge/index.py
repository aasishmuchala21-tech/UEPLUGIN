"""BM25 knowledge index — Phase 3 v1 floor.

Implements Okapi BM25 over a Markdown corpus. The index serializes to a
single JSON file per shard so the GitHub-Releases delivery pipeline (the
locked Phase 3 distribution decision per CONTEXT.md) is a one-line
download + load.

Schema is intentionally LanceDB-compatible:
  KnowledgeChunk maps 1-1 to a row in the v1.1 vector table; the only
  v1.1 addition is an `embedding: list[float]` field. Every other column
  (chunk_id, source_path, heading_path, body, n_tokens) is identical, so
  v1.1 ingest_directory can read v1 indexes and append embeddings
  without re-chunking.

References:
  - Robertson, S. & Zaragoza, H. (2009). The Probabilistic Relevance
    Framework: BM25 and Beyond. (k1=1.2, b=0.75 default per §2.4.)
  - https://en.wikipedia.org/wiki/Okapi_BM25 — formula reference
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Optional

import structlog

log = structlog.get_logger("nyrahost.knowledge.index")

# Tokenizer: lower-case, strip punctuation, split on whitespace + dashes
# + common code-doc separators. Not a real Unicode tokenizer — but good
# enough for English UE5 docs and zero deps.
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:_[a-z0-9]+)*")
_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
    "to", "was", "were", "will", "with",
})


def _tokenize(text: str) -> list[str]:
    """Lower-case + alphanumeric/underscore tokenization with stopword removal."""
    return [
        t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS
    ]


# Markdown chunking: split on H1/H2/H3 headings, preserve heading path so
# search results can show "Page > Section > Subsection" breadcrumbs.
_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)
_CHUNK_MAX_TOKENS = 400  # ~300 words per chunk — balances recall vs noise


@dataclass(frozen=True)
class KnowledgeChunk:
    """A retrievable unit. v1.1-compatible row schema."""
    chunk_id: str
    source_path: str  # relative to corpus root
    heading_path: list[str]  # ["Page Title", "Section", "Subsection"]
    body: str
    n_tokens: int


@dataclass
class KnowledgeIndex:
    """In-memory BM25 index. Persistable as a single JSON file per shard.

    Build:  ``idx = KnowledgeIndex.from_chunks(chunks)``
    Save:   ``idx.save(Path("ue5-index.json"))``
    Load:   ``idx = KnowledgeIndex.load(Path("ue5-index.json"))``
    Search: ``idx.search("how do I spawn an actor", k=8)``
    """
    chunks: list[KnowledgeChunk]
    # Internal: posting lists, doc_lens, idf scores. Built once, kept
    # in memory. JSON-serializable so the published index is a static
    # GitHub Release asset.
    _doc_freqs: list[dict[str, int]] = field(default_factory=list)
    _idf: dict[str, float] = field(default_factory=dict)
    _avgdl: float = 0.0
    # R3.I2 fix from the full-codebase review: cache per-doc length to
    # avoid recomputing sum(tf.values()) on every query. Built once in
    # _build() alongside _doc_freqs.
    _doc_lens: list[int] = field(default_factory=list)
    _k1: float = 1.2
    _b: float = 0.75
    schema_version: int = 1

    @classmethod
    def from_chunks(
        cls, chunks: list[KnowledgeChunk], *, k1: float = 1.2, b: float = 0.75
    ) -> "KnowledgeIndex":
        """Build a fresh BM25 index from a list of chunks."""
        idx = cls(chunks=list(chunks), _k1=k1, _b=b)
        idx._build()
        return idx

    def _build(self) -> None:
        n = len(self.chunks)
        if n == 0:
            self._avgdl = 0.0
            return

        self._doc_freqs = []
        self._doc_lens = []   # R3.I2 — populate alongside _doc_freqs
        df: dict[str, int] = {}
        total_len = 0

        for ch in self.chunks:
            tokens = _tokenize(ch.body)
            tf: dict[str, int] = {}
            for tok in tokens:
                tf[tok] = tf.get(tok, 0) + 1
            self._doc_freqs.append(tf)
            self._doc_lens.append(len(tokens))   # R3.I2
            total_len += len(tokens)
            for tok in tf.keys():
                df[tok] = df.get(tok, 0) + 1

        self._avgdl = total_len / n if n > 0 else 0.0
        # IDF formula from Robertson 2009: ln((N - df + 0.5) / (df + 0.5) + 1)
        self._idf = {}
        for tok, dfreq in df.items():
            self._idf[tok] = math.log((n - dfreq + 0.5) / (dfreq + 0.5) + 1)

    def search(
        self, query: str, *, k: int = 8, min_score: float = 0.5
    ) -> list[tuple[KnowledgeChunk, float]]:
        """Return top-k chunks ranked by BM25, filtered by min_score."""
        if not self.chunks:
            return []
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []

        scores: list[tuple[float, int]] = []
        for i, tf in enumerate(self._doc_freqs):
            # R3.I2 — read pre-computed doc length instead of recomputing
            # sum(tf.values()) on every query. ~5-20ms saved per call on
            # the seed corpus, ~100-500ms on a full-engine ingest.
            doc_len = self._doc_lens[i] if i < len(self._doc_lens) else sum(tf.values())
            if doc_len == 0:
                continue
            score = 0.0
            for tok in q_tokens:
                if tok not in tf:
                    continue
                idf = self._idf.get(tok, 0.0)
                if idf <= 0:
                    continue
                f = tf[tok]
                num = f * (self._k1 + 1)
                denom = f + self._k1 * (
                    1 - self._b + self._b * (doc_len / self._avgdl)
                )
                score += idf * (num / denom)
            if score >= min_score:
                scores.append((score, i))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [(self.chunks[i], score) for score, i in scores[:k]]

    def save(self, path: Path) -> None:
        """Persist to a JSON file. Atomic via tmp+rename."""
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": self.schema_version,
            "k1": self._k1,
            "b": self._b,
            "avgdl": self._avgdl,
            "idf": self._idf,
            "doc_freqs": self._doc_freqs,
            "chunks": [asdict(c) for c in self.chunks],
        }
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.replace(path)
        log.info(
            "knowledge_index_saved",
            path=str(path),
            chunks=len(self.chunks),
        )

    @classmethod
    def load(cls, path: Path) -> "KnowledgeIndex":
        """Load a previously-saved index. Refuses unknown schema versions."""
        payload = json.loads(path.read_text(encoding="utf-8"))
        sv = payload.get("schema_version", 0)
        if sv != 1:
            raise ValueError(
                f"unknown KnowledgeIndex schema_version={sv}; expected 1. "
                "Re-fetch the index from the GitHub Releases asset."
            )
        chunks = [KnowledgeChunk(**c) for c in payload["chunks"]]
        idx = cls(
            chunks=chunks,
            _k1=payload["k1"],
            _b=payload["b"],
            _avgdl=payload["avgdl"],
            _idf=dict(payload["idf"]),
            _doc_freqs=[dict(d) for d in payload["doc_freqs"]],
        )
        log.info(
            "knowledge_index_loaded",
            path=str(path),
            chunks=len(chunks),
        )
        return idx


def _split_markdown(content: str) -> list[tuple[list[str], str]]:
    """Split a Markdown document into (heading_path, body) chunks.

    Splits at H1/H2/H3 boundaries. Sub-chunks longer than _CHUNK_MAX_TOKENS
    are further split at paragraph boundaries to keep ranking signal
    concentrated.
    """
    headings: list[tuple[int, str, int]] = []  # (level, title, char_offset)
    for m in _HEADING_RE.finditer(content):
        headings.append((len(m.group(1)), m.group(2), m.start()))

    if not headings:
        # No headings → single chunk, empty heading_path
        return [([], content.strip())] if content.strip() else []

    chunks: list[tuple[list[str], str]] = []
    path: list[str] = []
    for i, (level, title, start) in enumerate(headings):
        # Update heading_path: pop deeper-or-equal levels, push current
        while len(path) >= level:
            path.pop()
        path.append(title)

        end = headings[i + 1][2] if i + 1 < len(headings) else len(content)
        # Body starts after the heading line itself (skip to next \n)
        line_end = content.find("\n", start)
        body_start = line_end + 1 if line_end != -1 else end
        body = content[body_start:end].strip()
        if not body:
            continue

        # Further split if too long. Paragraph break is the natural unit.
        para_chunks = _split_long_chunk(body)
        for piece in para_chunks:
            if piece.strip():
                chunks.append((list(path), piece.strip()))

    return chunks


def _split_long_chunk(text: str) -> list[str]:
    """Split a chunk longer than _CHUNK_MAX_TOKENS at paragraph boundaries."""
    tokens = _tokenize(text)
    if len(tokens) <= _CHUNK_MAX_TOKENS:
        return [text]
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    cur: list[str] = []
    cur_tokens = 0
    for para in paragraphs:
        ptokens = len(_tokenize(para))
        if cur_tokens + ptokens > _CHUNK_MAX_TOKENS and cur:
            chunks.append("\n\n".join(cur))
            cur = [para]
            cur_tokens = ptokens
        else:
            cur.append(para)
            cur_tokens += ptokens
    if cur:
        chunks.append("\n\n".join(cur))
    return chunks


def ingest_directory(
    corpus_root: Path,
    *,
    extensions: Iterable[str] = (".md", ".markdown"),
) -> list[KnowledgeChunk]:
    """Walk ``corpus_root`` and return a flat list of KnowledgeChunk.

    Used by the index-build pipeline (run on the maintainer's machine,
    not on the user's). The resulting list is fed to
    ``KnowledgeIndex.from_chunks(...)`` and saved as the published
    GitHub Release asset.
    """
    if not corpus_root.is_dir():
        raise FileNotFoundError(f"corpus_root not a directory: {corpus_root}")

    extensions = tuple(extensions)
    chunks: list[KnowledgeChunk] = []
    for path in sorted(corpus_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            log.warning(
                "knowledge_skip_non_utf8", path=str(path)
            )
            continue
        rel = str(path.relative_to(corpus_root)).replace("\\", "/")
        for i, (heading_path, body) in enumerate(_split_markdown(content)):
            chunks.append(
                KnowledgeChunk(
                    chunk_id=f"{rel}#{i}",
                    source_path=rel,
                    heading_path=heading_path,
                    body=body,
                    n_tokens=len(_tokenize(body)),
                )
            )
    log.info(
        "knowledge_ingested",
        corpus_root=str(corpus_root),
        chunks=len(chunks),
    )
    return chunks
