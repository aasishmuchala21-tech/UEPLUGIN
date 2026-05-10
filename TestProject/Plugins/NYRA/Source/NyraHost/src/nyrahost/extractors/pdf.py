"""PDF extractor — pypdf 6.11.0 (LOCKED-06 approved, pure-Python).

Returns ``(text, list[AttachmentRef])``. Text is extracted via
``page.extract_text()`` joined with newline separators; embedded images
are iterated via ``page.images`` (pypdf 6.x API), normalised through
Pillow, and fed back into the attachment store via
:func:`nyrahost.attachments.ingest_attachment` so they ride the
existing image-attachment vision-routing path.
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

from nyrahost.attachments import AttachmentRef
from nyrahost.extractors._common import ingest_image_bytes


def extract_pdf(
    src: Path, *, project_saved: Path
) -> Tuple[str, list[AttachmentRef]]:
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError as e:
        raise ValueError(
            "pypdf not installed — cannot extract PDF documents"
        ) from e

    text_chunks: list[str] = []
    image_refs: list[AttachmentRef] = []

    try:
        reader = PdfReader(str(src))
        for page in reader.pages:
            try:
                page_text = page.extract_text() or ""
            except Exception:
                # A single broken page shouldn't kill the whole document;
                # log silently and continue. Aura crashes here; we don't.
                page_text = ""
            if page_text:
                text_chunks.append(page_text)
            # Iterate embedded images. pypdf 6.x exposes them via
            # page.images (an iterable of ImageFile namedtuple-likes
            # carrying .data + .name). Older versions had no such
            # accessor — the AttributeError-guard keeps us safe.
            try:
                images = list(page.images)
            except (AttributeError, NotImplementedError):
                images = []
            for img in images:
                try:
                    blob = img.data
                except AttributeError:
                    continue
                if not blob:
                    continue
                ref = ingest_image_bytes(blob, project_saved=project_saved)
                if ref is not None:
                    image_refs.append(ref)
    except PdfReadError as e:
        raise ValueError(f"malformed PDF {src.name}: {e}") from e
    except (ValueError, KeyError, OSError) as e:
        # pypdf raises these on truncated / pickle-style malformed PDFs.
        raise ValueError(f"unreadable PDF {src.name}: {e}") from e

    text = "\n".join(text_chunks)
    return text, image_refs
