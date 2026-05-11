"""Content-addressed attachment ingestion (CD-08).

Hashes source file, then hard-links (or copies as a fallback) it into

    <ProjectSaved>/NYRA/attachments/<sha256[:2]>/<sha256>.<ext>

Content-addressing gives us free dedup: two different filenames holding
the same bytes converge to the same on-disk path. The SHA256 prefix
shard keeps per-directory file counts bounded so `ls` / filesystem
scans stay fast as the corpus grows.

Hard-link is preferred over copy: on NTFS / APFS / ext4 a hard-link is
O(1) metadata only, and the DB stores the `path` — so reading the
attachment back is a single syscall regardless of how many messages
reference it. `shutil.copy2` fallback handles the cross-device /
filesystem-without-hardlink-support case (FAT32 USB drops,
network-mounted Saved/, macOS case-folding boundaries, CI runners).

CD-04 scope: only image / video / text kinds are accepted in Phase 1.
The UI enforces the same list at drag-and-drop time; this module is
the backstop. Extensions outside the allow-list raise ValueError with
the full allow-list in the message so the UE-side error remediation
can surface it verbatim.
"""
from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

AttachmentKind = Literal["image", "video", "text", "document"]

# Allow-list matches CD-04 (image/video/text input types accepted by
# the Phase 1 chat panel drop zone + [+] picker).
#
# Phase 8 PARITY-01 adds the `document` kind (PDF/DOCX/PPTX/XLSX/HTML).
# `.md` stays under `text` — markdown lives natively as plain text and
# the document extractor only invokes the markdown library for the
# embedded-image edge case (handled at the chat-handler layer, not here).
ALLOWED_EXTENSIONS: dict[AttachmentKind, frozenset[str]] = {
    "image": frozenset({".png", ".jpg", ".jpeg", ".webp"}),
    "video": frozenset({".mp4", ".mov"}),
    "text": frozenset({".md", ".txt"}),
    "document": frozenset({".pdf", ".docx", ".pptx", ".xlsx", ".html", ".htm"}),
}


@dataclass(frozen=True)
class AttachmentRef:
    """Persisted attachment handle.

    `path` is absolute and points into
    ``<project_saved>/NYRA/attachments/<sha[:2]>/<sha>.<ext>``.
    The UE side receives this Path via the attachments table and can
    open it directly. `original_filename` is retained for display only
    (the content-addressed path uses the sha as the file name).
    """

    sha256: str
    path: str
    size_bytes: int
    kind: AttachmentKind
    original_filename: str


def _classify(ext_lower: str) -> AttachmentKind:
    """Map a lower-cased extension (e.g. ``.png``) to its AttachmentKind.

    Raises ValueError with a readable message listing every allow-listed
    extension. The UE side surfaces the message as-is to the user.
    """
    for k, exts in ALLOWED_EXTENSIONS.items():
        if ext_lower in exts:
            return k
    all_allowed = sorted(
        e for exts in ALLOWED_EXTENSIONS.values() for e in exts
    )
    raise ValueError(
        f"Unsupported attachment extension {ext_lower!r}. "
        "Allowed: " + ", ".join(all_allowed)
    )


def _sha256_of_file(path: Path, chunk: int = 1024 * 1024) -> str:
    """Stream the file through SHA256 in 1 MB chunks.

    Chunking matters: the Gemma test fixtures can reach hundreds of MB
    for video clips; reading them whole would blow out a 64-bit Python
    process's transient memory. 1 MB is a sweet spot where the
    per-chunk Python overhead is amortised but the working-set stays
    out of L2-cache territory.
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            buf = f.read(chunk)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()


def ingest_attachment(
    src_path: Path,
    *,
    project_saved: Path,
) -> AttachmentRef:
    """Ingest `src_path` into the project's content-addressed attachment store.

    Hashes src, then hard-links (os.link) or copies (shutil.copy2 on
    OSError) into ``<project_saved>/NYRA/attachments/<sha[:2]>/<sha>.<ext>``.

    `project_saved` is the project's ``Saved/`` directory (the caller
    composes ``<ProjectDir>/Saved``); the ``NYRA/attachments/...``
    sub-tree is created on demand. Returned ``AttachmentRef.path`` is
    absolute so downstream consumers don't have to resolve relative to
    cwd.

    Idempotent: calling ingest_attachment twice on the same bytes
    returns identical {sha256, path} and only one physical file exists
    on disk (content-addressed dedup).
    """
    # BL-03: agent-controlled `attachments` field can hand-pick paths via
    # the WS request. Reject symlinks at the leaf and blocklist sensitive
    # prefixes on the FULLY-RESOLVED real path so a chain like
    # `~/sneaky -> /etc/passwd` is caught by the blocklist below regardless
    # of which intermediate parent symlinks were traversed.
    try:
        src_resolved = src_path.resolve(strict=True)
    except FileNotFoundError:
        raise FileNotFoundError(src_path)
    if src_path.is_symlink():
        raise ValueError(
            f"Symlinked attachment paths are not permitted: {src_path}"
        )
    # Note: the previous version of this guard also walked every parent
    # of the *unresolved* src_path and refused if any was a symlink.
    # That was redundant — `resolve(strict=True)` already follows the
    # entire chain and the prefix blocklist runs against the resolved
    # path, so a sneaky symlink chain into /etc/ or ~/.ssh/ is caught.
    # The unresolved-parent check falsely rejected legitimate macOS
    # paths because /tmp itself is a symlink to /private/tmp; users
    # writing tempfiles under /tmp could not attach them.
    abs_lower = str(src_resolved).lower().replace("\\", "/")
    _PATH_BLOCKLIST = (
        "/etc/",
        "/root/",
        # R2.I3 fix from the full-codebase review: macOS's /etc and /var
        # are symlinks to /private/etc and /private/var. After
        # resolve(strict=True), an attachment path like /etc/passwd
        # becomes /private/etc/passwd, bypassing the /etc/ entry.
        "/private/etc/",
        "/private/var/db/",
        "/private/var/root/",
        "c:/windows/",
        "c:/users/default/",
        # User SSH/AWS/credentials directories on POSIX and Windows.
        "/.ssh/",
        "/.aws/",
        "/appdata/roaming/microsoft/credentials",
    )
    for prefix in _PATH_BLOCKLIST:
        if prefix in abs_lower:
            raise ValueError(
                f"Attachment source under sensitive prefix '{prefix}' rejected: {src_resolved}"
            )

    if not src_resolved.is_file():
        raise FileNotFoundError(src_path)
    ext = src_resolved.suffix.lower()
    kind = _classify(ext)
    sha = _sha256_of_file(src_resolved)
    prefix = sha[:2]
    dest_dir = project_saved / "NYRA" / "attachments" / prefix
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{sha}{ext}"
    if not dest.exists():
        try:
            os.link(src_path, dest)
        except OSError:
            # Cross-device, FAT32, network mount, or host FS doesn't
            # support hardlinks — fall back to a full copy. copy2
            # preserves mtime so the file's timestamp reflects the
            # source, not the moment of ingest.
            shutil.copy2(src_path, dest)
    size = dest.stat().st_size
    return AttachmentRef(
        sha256=sha,
        path=str(dest.resolve()),
        size_bytes=size,
        kind=kind,
        original_filename=src_path.name,
    )
