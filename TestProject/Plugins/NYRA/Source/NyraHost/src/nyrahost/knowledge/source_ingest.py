"""nyrahost.knowledge.source_ingest — Phase 16-F UE source-tree ingest.

Phase 1 shipped a tiny 8-doc seed corpus indexed via BM25
(``knowledge/index.py``). Tier 1.B asks for "engine source-code
example RAG" so the agent can answer 'show me FTimerManager::SetTimer
usage' from a real corpus, not 8 markdown stubs.

This module is the **ingest pipeline**:

  * Walks ``<UE root>/Engine/Source/Runtime/`` and
    ``<UE root>/Engine/Documentation/Source/`` (and optionally
    ``Engine/Source/Editor/`` for editor-API queries)
  * Per-file, extracts:
      - top-level UCLASS / USTRUCT / UFUNCTION declarations
      - Doxygen-style ``/** ... */`` blocks immediately above
      - the source file path + line for grounding
  * Emits per-chunk JSON records suitable for the existing
    BM25 index (chunk_id, source_path, heading_path, body, n_tokens)

The actual index population is deliberately offline — we ship the
walker + the chunker, and the user runs it once per UE install:

    python -m nyrahost.knowledge.source_ingest \
        --ue-root "C:\\Program Files\\Epic Games\\UE_5.6" \
        --out <ProjectDir>/Saved/NYRA/ue_source_corpus.jsonl

The chat handler's RAG step then consumes the .jsonl alongside the
existing seed corpus.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Iterable, Optional

import structlog

log = structlog.get_logger("nyrahost.knowledge.source_ingest")

UCLASS_DECL_RE: Final[re.Pattern[str]] = re.compile(
    r"(?P<doc>/\*\*[\s\S]*?\*/\s*)?"
    r"UCLASS\([^)]*\)\s*class\s+\w+_API\s+(?P<class_name>\w+)",
    re.MULTILINE,
)
USTRUCT_DECL_RE: Final[re.Pattern[str]] = re.compile(
    r"(?P<doc>/\*\*[\s\S]*?\*/\s*)?"
    r"USTRUCT\([^)]*\)\s*struct\s+\w+_API\s+(?P<struct_name>\w+)",
    re.MULTILINE,
)
UFUNC_DECL_RE: Final[re.Pattern[str]] = re.compile(
    r"(?P<doc>/\*\*[\s\S]*?\*/\s*)?"
    r"UFUNCTION\([^)]*\)\s*(?P<sig>[^;{]+)[;{]",
    re.MULTILINE,
)

# Caps so a single bad header can't blow the chunk size.
MAX_CHUNK_BYTES: Final[int] = 8 * 1024
MIN_CHUNK_BYTES: Final[int] = 32

# Default subtree roots inside a UE install we ingest from.
DEFAULT_SUBPATHS: Final[tuple[str, ...]] = (
    "Engine/Source/Runtime",
    "Engine/Source/Editor",
    "Engine/Documentation/Source",
)


@dataclass(frozen=True)
class SourceChunk:
    chunk_id: str
    source_path: str
    heading_path: str
    body: str

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "source_path": self.source_path,
            "heading_path": self.heading_path,
            "body": self.body,
            "n_tokens": _approx_tokens(self.body),
        }


def _approx_tokens(s: str) -> int:
    # Same heuristic as cost_forecaster (4 chars/token).
    return max(1, len(s) // 4)


def _clean_doc(raw: str | None) -> str:
    if not raw:
        return ""
    body = raw.strip().lstrip("/*").rstrip("*/").strip()
    out_lines = []
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("*"):
            s = s[1:].strip()
        out_lines.append(s)
    return "\n".join(out_lines).strip()


def chunk_header(path: Path, text: str, *, max_bytes: int = MAX_CHUNK_BYTES) -> list[SourceChunk]:
    """Split one .h file into per-declaration SourceChunk records.

    Each UCLASS / USTRUCT / UFUNCTION becomes one chunk; the chunk's
    body is the declaration source + its Doxygen doc block.
    """
    out: list[SourceChunk] = []
    source_path = str(path)

    def _emit(kind: str, name: str, decl: str, doc: str) -> None:
        body_lines = []
        if doc:
            body_lines.append(doc)
        body_lines.append(f"```cpp\n{decl}\n```")
        body = "\n\n".join(body_lines)
        if len(body) < MIN_CHUNK_BYTES:
            return
        if len(body.encode("utf-8")) > max_bytes:
            body = body.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
            body += "\n...<truncated>"
        out.append(SourceChunk(
            chunk_id=f"{path.stem}::{kind}::{name}",
            source_path=source_path,
            heading_path=f"{kind} {name}",
            body=body,
        ))

    for m in UCLASS_DECL_RE.finditer(text):
        _emit("uclass", m.group("class_name"),
              m.group(0).strip(), _clean_doc(m.group("doc")))
    for m in USTRUCT_DECL_RE.finditer(text):
        _emit("ustruct", m.group("struct_name"),
              m.group(0).strip(), _clean_doc(m.group("doc")))
    for m in UFUNC_DECL_RE.finditer(text):
        sig = m.group("sig").strip()
        if "(" in sig:
            name = sig.split("(", 1)[0].split()[-1]
        else:
            name = sig.split()[-1]
        _emit("ufunction", name, sig, _clean_doc(m.group("doc")))
    return out


def walk_ue_root(ue_root: Path, *, subpaths: Iterable[str] = DEFAULT_SUBPATHS) -> Iterable[Path]:
    """Yield every .h file under each requested subpath of the UE root."""
    ue_root = Path(ue_root)
    if not ue_root.exists():
        raise FileNotFoundError(f"UE root not found: {ue_root}")
    for sp in subpaths:
        root = ue_root / sp
        if not root.exists():
            log.warning("source_ingest_subpath_missing", subpath=sp)
            continue
        yield from sorted(root.rglob("*.h"))


def ingest_to_jsonl(
    *,
    ue_root: Path,
    out_path: Path,
    subpaths: Iterable[str] = DEFAULT_SUBPATHS,
    max_files: int | None = None,
) -> dict:
    """Walk ue_root, chunk every header, write JSONL to out_path.

    Returns a summary {files_seen, chunks_written, out_path}.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    files_seen = 0
    chunks_written = 0
    with out_path.open("w", encoding="utf-8") as f:
        for hdr in walk_ue_root(ue_root, subpaths=subpaths):
            files_seen += 1
            if max_files is not None and files_seen > max_files:
                break
            try:
                text = hdr.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for c in chunk_header(hdr, text):
                f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
                chunks_written += 1
    return {
        "files_seen": files_seen,
        "chunks_written": chunks_written,
        "out_path": str(out_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nyrahost.knowledge.source_ingest")
    parser.add_argument("--ue-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--subpath", action="append", default=None)
    parser.add_argument("--max-files", type=int, default=None)
    args = parser.parse_args(argv)
    subpaths = args.subpath or list(DEFAULT_SUBPATHS)
    summary = ingest_to_jsonl(
        ue_root=args.ue_root,
        out_path=args.out,
        subpaths=subpaths,
        max_files=args.max_files,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "SourceChunk",
    "chunk_header",
    "walk_ue_root",
    "ingest_to_jsonl",
    "DEFAULT_SUBPATHS",
    "MAX_CHUNK_BYTES",
]
