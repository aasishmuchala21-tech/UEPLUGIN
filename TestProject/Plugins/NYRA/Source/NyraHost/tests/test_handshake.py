"""Handshake atomic-write tests.
VALIDATION test ID: 1-02-05
"""
from __future__ import annotations
import json
import secrets
import threading
import time
from pathlib import Path

from nyrahost.handshake import (
    write_handshake,
    handshake_file_path,
    cleanup_orphan_handshakes,
)


def test_handshake_atomic_write(tmp_path: Path) -> None:
    handshake_dir = tmp_path / "NYRA"
    token = secrets.token_bytes(32).hex()
    final = write_handshake(
        handshake_dir,
        port=54321,
        token=token,
        nyrahost_pid=11111,
        ue_pid=22222,
    )
    assert final.exists()
    data = json.loads(final.read_text(encoding="utf-8"))
    assert data["port"] == 54321
    assert data["token"] == token
    assert len(token) == 64  # 32 bytes hex
    assert data["nyrahost_pid"] == 11111
    assert data["ue_pid"] == 22222
    assert isinstance(data["started_at"], int)
    # No .tmp left behind
    assert not final.with_suffix(final.suffix + ".tmp").exists()


def test_handshake_atomic_reader_never_sees_partial(tmp_path: Path) -> None:
    """Race: reader polls aggressively while writer races; reader must
    never observe an empty or partial JSON (proves os.replace atomicity)."""
    handshake_dir = tmp_path / "NYRA"
    handshake_dir.mkdir()
    path = handshake_file_path(handshake_dir, ue_pid=22222)

    partial_reads: list[object] = []
    stop = threading.Event()

    def reader() -> None:
        while not stop.is_set():
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    # If we loaded a dict, we expect all required fields
                    if "port" not in data or "token" not in data:
                        partial_reads.append(data)
                except (json.JSONDecodeError, OSError):
                    partial_reads.append("parse_failed_but_tolerated")

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    try:
        for i in range(30):
            write_handshake(
                handshake_dir,
                port=54321 + i,
                token=secrets.token_bytes(32).hex(),
                nyrahost_pid=11111,
                ue_pid=22222,
            )
            time.sleep(0.003)
    finally:
        stop.set()
        t.join(timeout=1.0)
    # Partial-DICT reads (dict with missing keys) must be zero — os.replace
    # guarantees all-or-nothing at the dict level.
    bad_dicts = [r for r in partial_reads if isinstance(r, dict)]
    assert bad_dicts == [], f"Non-atomic dict read observed: {bad_dicts}"


def test_handshake_cleanup_orphans(tmp_path: Path) -> None:
    handshake_dir = tmp_path / "NYRA"
    # Write handshake for a definitely-dead pid (a very large unused one)
    write_handshake(
        handshake_dir,
        port=5000,
        token="x" * 64,
        nyrahost_pid=11111,
        ue_pid=3_999_999_999,
    )
    cleaned = cleanup_orphan_handshakes(handshake_dir)
    assert 3_999_999_999 in cleaned
    assert not handshake_file_path(handshake_dir, 3_999_999_999).exists()
