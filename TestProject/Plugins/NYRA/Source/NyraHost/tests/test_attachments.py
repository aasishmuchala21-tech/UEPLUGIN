"""Content-addressed attachment tests.
VALIDATION test ID: 1-04-07
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest

from nyrahost.attachments import ALLOWED_EXTENSIONS, AttachmentRef, ingest_attachment


def _write_fixture(tmp: Path, name: str, payload: bytes) -> Path:
    p = tmp / name
    p.write_bytes(payload)
    return p


def test_ingest_hardlink_and_sha256(tmp_project_dir: Path, tmp_path: Path) -> None:
    payload = b"hello world" * 1024  # 11 KB
    src = _write_fixture(tmp_path, "note.txt", payload)
    expected_sha = hashlib.sha256(payload).hexdigest()
    ref = ingest_attachment(src, project_saved=tmp_project_dir / "Saved")
    assert isinstance(ref, AttachmentRef)
    assert ref.sha256 == expected_sha
    assert ref.kind == "text"
    assert ref.size_bytes == len(payload)
    assert ref.original_filename == "note.txt"
    # dest path under attachments/<prefix>/<sha>.txt
    dest = Path(ref.path)
    assert dest.exists()
    assert dest.parent.name == expected_sha[:2]
    assert dest.name == f"{expected_sha}.txt"


def test_ingest_dedup(tmp_project_dir: Path, tmp_path: Path) -> None:
    payload = b"\x00\x01\x02\x03" * 100
    src1 = _write_fixture(tmp_path, "a.png", payload)
    src2 = _write_fixture(tmp_path, "b.png", payload)  # same bytes, different filename
    r1 = ingest_attachment(src1, project_saved=tmp_project_dir / "Saved")
    r2 = ingest_attachment(src2, project_saved=tmp_project_dir / "Saved")
    assert r1.sha256 == r2.sha256
    assert r1.path == r2.path
    # Only one physical file in the sharded directory.
    att_dir = (
        tmp_project_dir
        / "Saved"
        / "NYRA"
        / "attachments"
        / r1.sha256[:2]
    )
    assert len(list(att_dir.iterdir())) == 1


def test_ingest_unsupported_kind(tmp_project_dir: Path, tmp_path: Path) -> None:
    src = _write_fixture(tmp_path, "bad.exe", b"MZ\x00\x00")
    with pytest.raises(ValueError) as exc:
        ingest_attachment(src, project_saved=tmp_project_dir / "Saved")
    assert ".exe" in str(exc.value) or "Unsupported" in str(exc.value)


def test_ingest_hardlink_falls_back_to_copy(
    tmp_project_dir: Path, tmp_path: Path
) -> None:
    payload = b"pixeldata" * 500
    src = _write_fixture(tmp_path, "frame.jpg", payload)
    with patch("nyrahost.attachments.os.link", side_effect=OSError("cross-device")):
        ref = ingest_attachment(src, project_saved=tmp_project_dir / "Saved")
    # Even with link failing, copy succeeds and sha256 matches
    assert ref.sha256 == hashlib.sha256(payload).hexdigest()
    assert Path(ref.path).exists()
    assert ref.kind == "image"


def test_accepted_extensions_coverage() -> None:
    # Sanity: each kind has at least one ext and they don't collide.
    all_exts: set[str] = set()
    for k, exts in ALLOWED_EXTENSIONS.items():
        assert exts, f"Kind {k!r} has no allowed extensions"
        assert all_exts.isdisjoint(exts), f"Overlapping extensions for {k!r}"
        all_exts |= exts
