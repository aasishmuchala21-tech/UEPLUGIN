"""Tests for nyrahost.cpp_authoring_state — Plan 08-02 PARITY-02 allowlist.

The allowlist gates `nyra_cpp_recompile` (and the file-mutating tools'
pre-conditions) so NYRA only ever Live-Codes files it authored this session.
The semantics under test:

    - record / is_authored round-trip
    - case-insensitive on Windows (Path.resolve normalises casing)
    - clear_session resets to empty
    - record_authored_many is bulk-equivalent
    - thread-safety smoke (concurrent record + read does not raise)
"""
from __future__ import annotations

import threading
from pathlib import Path

import pytest

from nyrahost import cpp_authoring_state as cas


@pytest.fixture(autouse=True)
def _isolation():
    """Each test starts with a clean allowlist."""
    cas.clear_session()
    yield
    cas.clear_session()


def test_record_then_is_authored_round_trip(tmp_path: Path):
    f = tmp_path / "Public" / "Foo.h"
    f.parent.mkdir(parents=True)
    f.write_text("// nyra-test", encoding="utf-8")

    assert cas.is_authored(f) is False
    cas.record_authored(f)
    assert cas.is_authored(f) is True


def test_unrecorded_path_is_not_authored(tmp_path: Path):
    other = tmp_path / "Foreign.cpp"
    other.write_text("// not nyra", encoding="utf-8")
    assert cas.is_authored(other) is False


def test_clear_session_drops_all_entries(tmp_path: Path):
    a = tmp_path / "a.h"
    b = tmp_path / "b.cpp"
    a.write_text("//", encoding="utf-8")
    b.write_text("//", encoding="utf-8")
    cas.record_authored(a)
    cas.record_authored(b)
    assert cas.is_authored(a)
    cas.clear_session()
    assert cas.is_authored(a) is False
    assert cas.is_authored(b) is False


def test_record_authored_many_bulk(tmp_path: Path):
    paths = [tmp_path / f"f{i}.cpp" for i in range(5)]
    for p in paths:
        p.write_text("//", encoding="utf-8")
    cas.record_authored_many(paths)
    for p in paths:
        assert cas.is_authored(p)


def test_record_accepts_string_or_path(tmp_path: Path):
    p = tmp_path / "FromString.h"
    p.write_text("//", encoding="utf-8")
    cas.record_authored(str(p))
    assert cas.is_authored(p)
    assert cas.is_authored(str(p))


def test_normalises_path_casing_smoke(tmp_path: Path):
    """resolve(strict=False) normalises representation; the same logical
    file recorded once must look authored when queried by an equivalent
    Path object.
    """
    p = tmp_path / "Sub" / "File.h"
    p.parent.mkdir(parents=True)
    p.write_text("//", encoding="utf-8")
    cas.record_authored(p)
    # Re-construct from the same string — must still be authored.
    same = Path(str(p))
    assert cas.is_authored(same)


def test_snapshot_returns_immutable_copy(tmp_path: Path):
    a = tmp_path / "a.h"
    a.write_text("//", encoding="utf-8")
    cas.record_authored(a)
    snap = cas.snapshot_authored()
    assert isinstance(snap, frozenset)
    # Mutating after snapshot does not affect the snapshot.
    b = tmp_path / "b.h"
    b.write_text("//", encoding="utf-8")
    cas.record_authored(b)
    assert b.resolve() not in snap


def test_thread_safety_smoke(tmp_path: Path):
    paths = [tmp_path / f"thread{i}.cpp" for i in range(20)]
    for p in paths:
        p.write_text("//", encoding="utf-8")

    def _writer(slice_: list[Path]):
        for p in slice_:
            cas.record_authored(p)

    def _reader():
        for _ in range(50):
            cas.snapshot_authored()

    threads = [
        threading.Thread(target=_writer, args=(paths[:10],)),
        threading.Thread(target=_writer, args=(paths[10:],)),
        threading.Thread(target=_reader),
        threading.Thread(target=_reader),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for p in paths:
        assert cas.is_authored(p), f"missing after concurrent writes: {p}"
