"""Markdown extractor — markdown 3.10.2 + bs4 (LOCKED-06 approved).

Markdown is converted to HTML via the ``markdown`` library, then the
HTML extractor logic runs over the result. This routes through one
canonical text+image pipeline rather than re-implementing image-tag
scraping for two formats. Inline ``![alt](data:image/...;base64,...)``
links round-trip through the bs4 stage as ``<img src="data:...">``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

from nyrahost.attachments import AttachmentRef
from nyrahost.extractors._common import ingest_image_bytes
from nyrahost.extractors.html import _decode_data_uri


def extract_md(
    src: Path, *, project_saved: Path
) -> Tuple[str, list[AttachmentRef]]:
    try:
        import markdown as md_lib
    except ImportError as e:
        raise ValueError(
            "markdown not installed — cannot extract Markdown documents"
        ) from e
    try:
        from bs4 import BeautifulSoup
    except ImportError as e:
        raise ValueError(
            "beautifulsoup4 not installed — cannot extract Markdown documents"
        ) from e

    try:
        raw = src.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw = src.read_text(encoding="latin-1", errors="replace")
    except OSError as e:
        raise ValueError(f"unreadable Markdown {src.name}: {e}") from e

    if not raw:
        raise ValueError(f"empty Markdown file: {src.name}")

    try:
        # `extra` enables tables / fenced-code; `attr_list` keeps
        # attributes (e.g. {.foo}) when present. No HTML escape pass —
        # we run the output through bs4 immediately.
        html_str = md_lib.markdown(raw, extensions=["extra"])
    except Exception as e:
        raise ValueError(f"malformed Markdown {src.name}: {e}") from e

    soup = BeautifulSoup(html_str, "html.parser")
    text = soup.get_text(separator=" ").strip()
    # Append the original markdown source — extractors that produce a
    # rendered version of the input destroy the prose structure (lists,
    # headings) the LLM relies on. Concat is safe: the LLM treats
    # repetition as a soft hint.
    if raw not in text:
        text = raw + "\n\n" + text

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

    return text, image_refs
