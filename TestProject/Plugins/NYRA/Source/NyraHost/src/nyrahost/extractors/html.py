"""HTML extractor — beautifulsoup4 (LOCKED-06 amended).

Uses bs4 with the stdlib ``html.parser`` backend (NOT lxml) per the
plan body — lxml is already a transitive of python-docx but we don't
want to make bs4 depend on it implicitly. ``.get_text(separator=" ")``
yields a flat human-readable string; embedded ``<img>`` tags whose
``src`` attribute is a ``data:image/...;base64,...`` URI are decoded
and re-ingested through the image-attachment store.
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Tuple

from nyrahost.attachments import AttachmentRef
from nyrahost.extractors._common import ingest_image_bytes


def _decode_data_uri(src: str) -> bytes | None:
    """Decode an ``<img src="data:image/...;base64,...">`` URI to bytes.

    Returns None for non-data URIs (http://, https://, file://, /Game/...) —
    those need network or filesystem fetches the security model
    forbids during sandboxed extraction.
    """
    if not src.startswith("data:"):
        return None
    try:
        head, payload = src.split(",", 1)
    except ValueError:
        return None
    if ";base64" not in head:
        # Plain URL-encoded data URI; rare for images. Skip.
        return None
    try:
        return base64.b64decode(payload, validate=False)
    except (ValueError, TypeError):
        return None


def extract_html(
    src: Path, *, project_saved: Path
) -> Tuple[str, list[AttachmentRef]]:
    try:
        from bs4 import BeautifulSoup
    except ImportError as e:
        raise ValueError(
            "beautifulsoup4 not installed — cannot extract HTML documents"
        ) from e

    try:
        raw = src.read_bytes()
    except OSError as e:
        raise ValueError(f"unreadable HTML {src.name}: {e}") from e

    if not raw:
        raise ValueError(f"empty HTML file: {src.name}")

    # Decode bytes to str — bs4's html.parser accepts either, but
    # explicit utf-8-with-fallback gives clearer error surfaces than
    # bs4's auto-detect heuristic.
    try:
        text_in = raw.decode("utf-8")
    except UnicodeDecodeError:
        text_in = raw.decode("latin-1", errors="replace")

    try:
        soup = BeautifulSoup(text_in, "html.parser")
    except Exception as e:  # bs4 wraps parser-internal errors
        raise ValueError(f"malformed HTML {src.name}: {e}") from e

    extracted = soup.get_text(separator=" ").strip()

    image_refs: list[AttachmentRef] = []
    for img in soup.find_all("img"):
        data_src = img.get("src", "")
        if not isinstance(data_src, str):
            continue
        blob = _decode_data_uri(data_src)
        if not blob:
            continue
        ref = ingest_image_bytes(blob, project_saved=project_saved)
        if ref is not None:
            image_refs.append(ref)

    return extracted, image_refs
