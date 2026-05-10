"""Shared helpers for the six PARITY-01 extractors.

Centralises:
  - zip-bomb pre-check for OOXML containers (DOCX/PPTX/XLSX);
  - PIL image normalisation (RGB convert + size threshold);
  - temp-file ingest into the content-addressed attachment store via
    :func:`nyrahost.attachments.ingest_attachment`.

Keeping these in one place means a future security tweak (e.g. lower
the zip-uncompressed cap, raise the icon-noise floor, add EXIF strip)
lands in exactly one file rather than six.
"""
from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from nyrahost.attachments import AttachmentRef, ingest_attachment

# RESEARCH.md §Security Domain — OOXML containers are zip files; an
# adversary can ship a 1 KB DOCX whose unzipped payload is multiple GB.
# 100 MB is generous (legitimate game-design docs with embedded 4K
# screenshots can hit ~30 MB) but bounds the worst case so a single
# malicious upload can't OOM the sidecar.
_OOXML_MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024  # 100 MB

# RESEARCH.md §Pitfalls — Pitfall 1 (icon-noise filter): documents
# routinely embed 16x16 / 32x32 bullet/footer icons whose vision-routing
# adds noise without value. 64x64 is the smallest size where a thumb-
# nail meaningfully describes content.
_MIN_IMAGE_DIM = 64

# Common image extensions when re-ingesting via ingest_attachment.
# We always write PNG so the content-addressed store doesn't have to
# round-trip JPEG quality; PNG also normalises away CMYK weirdness
# that Pitfall 7 warns about.
_IMG_EXT = ".png"


def assert_ooxml_within_zip_budget(src: Path) -> None:
    """Raise ValueError if the zip's total uncompressed size exceeds the cap.

    Run BEFORE python-docx / python-pptx / openpyxl open the file so an
    attacker can't get the parser to start materialising entries before
    we've seen the full content size.
    """
    try:
        with zipfile.ZipFile(src) as zf:
            total = sum(info.file_size for info in zf.infolist())
    except zipfile.BadZipFile as e:
        raise ValueError(f"file is not a valid OOXML/zip container: {src}") from e
    if total > _OOXML_MAX_UNCOMPRESSED_BYTES:
        raise ValueError(
            f"OOXML uncompressed size {total} bytes exceeds "
            f"{_OOXML_MAX_UNCOMPRESSED_BYTES}-byte cap (zip-bomb mitigation)"
        )


def ingest_image_bytes(
    blob: bytes, *, project_saved: Path
) -> AttachmentRef | None:
    """Decode image bytes via Pillow, drop tiny ones, ingest as PNG.

    Returns None when the image is below ``_MIN_IMAGE_DIM`` on either
    axis (icon noise) or undecodable (corrupt embedded asset). The
    ingested AttachmentRef has ``kind="image"`` and is content-addressed
    via the existing pipeline, which means later passes that ingest the
    same byte payload (e.g. the same logo embedded across pages of a
    single PDF) dedup automatically.
    """
    try:
        img = Image.open(io.BytesIO(blob))
        img.load()  # force decode so size + mode are populated
    except (UnidentifiedImageError, OSError):
        return None
    w, h = img.size
    if w < _MIN_IMAGE_DIM or h < _MIN_IMAGE_DIM:
        return None
    # Pitfall 7: convert to RGB BEFORE re-ingest so downstream image-
    # attachment vision routing doesn't get a CMYK or palette-mode PNG
    # that some tools then fail to decode.
    if img.mode != "RGB":
        img = img.convert("RGB")
    # Write to a NamedTemporaryFile then ingest. We can't write+ingest
    # in a single open() because ingest_attachment opens the file by
    # path with strict resolve(). delete=False + finally-unlink is the
    # Windows-safe pattern (NamedTemporaryFile delete=True breaks on
    # Win because two processes can't open the same handle).
    tmp = tempfile.NamedTemporaryFile(
        suffix=_IMG_EXT, delete=False, prefix="nyra_extracted_"
    )
    tmp_path = Path(tmp.name)
    try:
        try:
            img.save(tmp, format="PNG")
        finally:
            tmp.close()
        return ingest_attachment(tmp_path, project_saved=project_saved)
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            # Best-effort cleanup; the OS-level temp-clean job will
            # handle leftovers in the worst case.
            pass
