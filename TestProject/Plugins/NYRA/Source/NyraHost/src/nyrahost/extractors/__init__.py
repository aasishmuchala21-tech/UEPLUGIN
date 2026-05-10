"""Document extractors — PARITY-01 (Phase 8 plan 08-01).

Each extractor consumes a document file (PDF/DOCX/PPTX/XLSX/HTML/MD) and
returns ``(text, list[AttachmentRef])`` where the AttachmentRef list
holds embedded images that have already been re-ingested via
:func:`nyrahost.attachments.ingest_attachment`. That re-ingestion step is
why this module beats Aura's doc surface: the embedded images inherit
the existing image-attachment chat-handler vision-routing pipeline for
free, with content-addressing + symlink rejection + sensitive-prefix
blocklist enforced as a side effect.

Per CONTEXT.md LOCKED-06 (amended 2026-05-10): only the six approved
parsers (pypdf, python-docx, python-pptx, openpyxl, markdown,
beautifulsoup4). No pdfplumber, no pypdfium2, no mupdf — all three
ship platform-fragmented C++ binaries.

Per RESEARCH.md §Pitfalls and §Security Domain, every extractor MUST:
  - convert embedded images via Pillow's ``Image.convert("RGB")`` so
    the downstream image-attachment kind doesn't choke on CMYK / RGBA
    surprises (Pitfall 7 — colour-space confusion);
  - skip images smaller than 64x64 pixels (icon-noise filter);
  - pre-check zip total uncompressed size <100 MB for OOXML formats
    (DOCX/PPTX/XLSX) before parsing (zip-bomb mitigation).
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

from nyrahost.attachments import AttachmentRef


def dispatch(
    src: Path, *, project_saved: Path
) -> Tuple[str, list[AttachmentRef]]:
    """Pick extractor by suffix; return (text, embedded_image_refs).

    The image refs are produced via ``attachments.ingest_attachment`` so
    they inherit content-addressing + symlink-rejection + sensitive-
    prefix blocklist for free. Vision routing happens automatically via
    the existing image-attachment chat-handler path — there is no new
    plumbing on the prompt-construction side.
    """
    suffix = src.suffix.lower()
    if suffix == ".pdf":
        from nyrahost.extractors.pdf import extract_pdf
        return extract_pdf(src, project_saved=project_saved)
    if suffix == ".docx":
        from nyrahost.extractors.docx import extract_docx
        return extract_docx(src, project_saved=project_saved)
    if suffix == ".pptx":
        from nyrahost.extractors.pptx import extract_pptx
        return extract_pptx(src, project_saved=project_saved)
    if suffix == ".xlsx":
        from nyrahost.extractors.xlsx import extract_xlsx
        return extract_xlsx(src, project_saved=project_saved)
    if suffix in {".html", ".htm"}:
        from nyrahost.extractors.html import extract_html
        return extract_html(src, project_saved=project_saved)
    if suffix == ".md":
        from nyrahost.extractors.md import extract_md
        return extract_md(src, project_saved=project_saved)
    raise ValueError(f"no extractor for {src.suffix!r}")
