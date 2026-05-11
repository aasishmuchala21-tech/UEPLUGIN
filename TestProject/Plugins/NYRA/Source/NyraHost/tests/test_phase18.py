"""Phase 18 — Tier 3 polish tests.

A (warm pool), B (snapshot), C (recovery), D (settings aggregator),
E (i18n catalog)."""
from __future__ import annotations

import asyncio
import json
import time
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from nyrahost.handlers.settings_aggregator import SettingsAggregatorHandlers
from nyrahost.handlers.instructions import InstructionsHandlers
from nyrahost.handlers.model_settings import ModelSettingsHandlers
from nyrahost.handlers.reproducibility import ReproHandlers
from nyrahost.handlers.session_mode import SessionModeHandler
from nyrahost.handlers.user_tools import UserToolsHandlers
from nyrahost.handlers.mcp_install import McpInstallHandlers
from nyrahost.custom_instructions import CustomInstructions
from nyrahost.model_preference import ModelPreference
from nyrahost.reproducibility import ReproPinStore
from nyrahost.user_tools import UserToolsLoader
from nyrahost.recovery import RecoveryHandlers, RecoveryStore
from nyrahost.snapshot import (
    MAX_SNAPSHOT_BYTES,
    SnapshotHandlers,
    export_snapshot,
)
from nyrahost.i18n_catalog import CATALOG, CATALOG_NAMESPACE, lookup, on_catalog
from nyrahost.warm_pool import (
    IDLE_TIMEOUT_S,
    MAX_POOL_SIZE,
    WarmClaudePool,
)


# ---------- 18-A warm claude pool ----------

class _FakeProc:
    def __init__(self, pid):
        self.pid = pid
        self.returncode = None
    def terminate(self): self.returncode = 0
    async def wait(self): return 0


def _make_factory():
    counter = {"n": 0}
    async def factory():
        counter["n"] += 1
        return _FakeProc(pid=1000 + counter["n"])
    return factory, counter


def test_warm_pool_spawns_on_demand():
    factory, counter = _make_factory()
    pool = WarmClaudePool(spawn_factory=factory)
    p = asyncio.run(pool.acquire())
    assert p.pid == 1001
    assert counter["n"] == 1


def test_warm_pool_release_reuses():
    factory, counter = _make_factory()
    pool = WarmClaudePool(spawn_factory=factory)
    p1 = asyncio.run(pool.acquire())
    asyncio.run(pool.release(p1))
    p2 = asyncio.run(pool.acquire())
    assert p1.pid == p2.pid   # same proc reused
    assert counter["n"] == 1


def test_warm_pool_max_size_enforced():
    factory, _ = _make_factory()
    pool = WarmClaudePool(spawn_factory=factory, max_size=2)
    pa = asyncio.run(pool.acquire())
    pb = asyncio.run(pool.acquire())
    pc = asyncio.run(pool.acquire())
    asyncio.run(pool.release(pa))
    asyncio.run(pool.release(pb))
    asyncio.run(pool.release(pc))   # over cap; should be terminated
    assert pool.idle_count <= 2


def test_warm_pool_prewarm():
    factory, _ = _make_factory()
    pool = WarmClaudePool(spawn_factory=factory)
    n = asyncio.run(pool.prewarm())
    assert n == MAX_POOL_SIZE


def test_warm_pool_drain():
    factory, _ = _make_factory()
    pool = WarmClaudePool(spawn_factory=factory)
    asyncio.run(pool.prewarm())
    n = asyncio.run(pool.drain())
    assert n == MAX_POOL_SIZE
    assert pool.idle_count == 0


# ---------- 18-B snapshot export ----------

def test_snapshot_export_creates_zip(tmp_path):
    nyra = tmp_path / "Saved" / "NYRA"
    nyra.mkdir(parents=True)
    (nyra / "audit.jsonl").write_text('{"kind":"prompt_in","ts":1}\n')
    (nyra / "instructions.md").write_text("Use British spelling.")
    snap = export_snapshot(
        project_dir=tmp_path,
        settings={"model": "claude-opus-4-7", "privacy": False},
    )
    assert snap.path.exists()
    assert snap.bytes_written > 0
    with zipfile.ZipFile(snap.path) as zf:
        names = set(zf.namelist())
        assert "README.txt" in names
        assert "audit.jsonl" in names
        assert "instructions.md" in names
        assert "settings.json" in names


def test_snapshot_handler_list_empty(tmp_path):
    h = SnapshotHandlers(project_dir=tmp_path)
    out = asyncio.run(h.on_list({}))
    assert out["snapshots"] == []


def test_snapshot_handler_export_then_list(tmp_path):
    h = SnapshotHandlers(project_dir=tmp_path)
    asyncio.run(h.on_export({"settings": {}}))
    out = asyncio.run(h.on_list({}))
    assert len(out["snapshots"]) == 1


def test_snapshot_extras_name_with_parent_traversal_rejected(tmp_path):
    """L1 from PR #2 follow-up: extras name with '..' must not pop out of
    the extras/ prefix; the entry is silently skipped."""
    snap = export_snapshot(
        project_dir=tmp_path,
        settings={},
        extra_files={"../evil.txt": b"payload", "ok.txt": b"hi"},
    )
    with zipfile.ZipFile(snap.path) as zf:
        names = set(zf.namelist())
    assert "extras/ok.txt" in names
    assert "../evil.txt" not in names
    # No entry should reach outside extras/
    assert not any(n.startswith("..") for n in names)


def test_snapshot_extras_absolute_name_rejected(tmp_path):
    """L1: extras name starting with '/' is skipped (would otherwise
    create an entry at the zip root with an empty extras/ prefix on
    extraction)."""
    snap = export_snapshot(
        project_dir=tmp_path,
        settings={},
        extra_files={"/etc/passwd": b"payload"},
    )
    with zipfile.ZipFile(snap.path) as zf:
        names = set(zf.namelist())
    assert "/etc/passwd" not in names
    assert "extras/etc/passwd" not in names


# ---------- 18-C recovery ----------

def test_recovery_save_load_clear(tmp_path):
    store = RecoveryStore(project_dir=tmp_path)
    rec = store.save(
        session_id="s-1", conversation_id="c-1",
        last_tool="meshy.image_to_3d", last_prompt="make a hero",
        stage="running", ts=time.time(),
    )
    loaded = store.load()
    assert loaded is not None
    assert loaded.session_id == "s-1"
    assert loaded.last_tool == "meshy.image_to_3d"
    assert store.clear() is True
    assert store.load() is None


def test_recovery_handler_resume_then_clear(tmp_path):
    store = RecoveryStore(project_dir=tmp_path)
    store.save(session_id="s", conversation_id="c",
               last_tool="x", last_prompt="y", stage="z", ts=0.0)
    h = RecoveryHandlers(store)
    out = asyncio.run(h.on_check({}))
    assert out["has_resume"] is True
    r = asyncio.run(h.on_resume({}))
    assert r["resumed"] is True
    # Resume clears the record so next check is empty
    assert asyncio.run(h.on_check({}))["has_resume"] is False


def test_recovery_resume_when_absent(tmp_path):
    h = RecoveryHandlers(RecoveryStore(project_dir=tmp_path))
    out = asyncio.run(h.on_resume({}))
    assert out["error"]["code"] == -32079


def test_recovery_truncates_long_prompt(tmp_path):
    store = RecoveryStore(project_dir=tmp_path)
    rec = store.save(session_id="s", conversation_id="c",
                     last_tool="x", last_prompt="z" * 100_000,
                     stage="r", ts=0.0)
    assert len(rec.last_prompt) <= 4096


# ---------- 18-D settings aggregator ----------

def test_settings_all_aggregates(tmp_path):
    # Build the dependency graph the aggregator needs.
    ci = CustomInstructions(project_dir=tmp_path)
    pref = ModelPreference()
    repro = ReproPinStore()
    user_tools = UserToolsLoader(tools_dir=tmp_path / "tools_empty")
    instr_h = InstructionsHandlers(ci)
    model_h = ModelSettingsHandlers(pref)
    repro_h = ReproHandlers(repro)

    # SessionModeHandler needs a router + permission gate; the aggregator
    # only reads .operating_mode so a MagicMock is sufficient.
    sm = MagicMock()
    sm.operating_mode = "plan"
    ut_h = UserToolsHandlers(user_tools)
    mcp_h = McpInstallHandlers(
        python_exe=Path("/p"), mcp_script=Path("/s"),
    )

    agg = SettingsAggregatorHandlers(
        instructions=instr_h, model=model_h, repro=repro_h,
        session_mode=sm, user_tools=ut_h, mcp_install=mcp_h,
    )
    out = asyncio.run(agg.on_all({"conversation_id": "c-1"}))
    assert out["operating_mode"] == "plan"
    assert "instructions" in out
    assert "model" in out
    assert "repro" in out
    assert "privacy" in out
    assert "user_tools" in out
    assert "mcp_install_targets" in out


def test_settings_all_missing_conversation_id():
    sm = MagicMock(); sm.operating_mode = "plan"
    agg = SettingsAggregatorHandlers(
        instructions=MagicMock(),
        model=MagicMock(),
        repro=MagicMock(),
        session_mode=sm,
        user_tools=MagicMock(),
        mcp_install=MagicMock(),
    )
    out = asyncio.run(agg.on_all({}))
    assert out["error"]["code"] == -32602


# ---------- 18-E i18n catalog ----------

def test_i18n_catalog_has_panel_strings():
    assert "panel.send" in CATALOG
    assert "mode.ask" in CATALOG
    assert "model.default" in CATALOG
    assert "sidebar.hygiene" in CATALOG


def test_i18n_lookup_returns_key_when_missing():
    # Fallback contract — never raise, never return empty
    assert lookup("nonexistent.key") == "nonexistent.key"


def test_i18n_handler():
    out = asyncio.run(on_catalog({}))
    assert out["namespace"] == CATALOG_NAMESPACE
    assert out["locale"] == "en"
    assert len(out["strings"]) >= 30


def test_i18n_export_locale_shape():
    from nyrahost.i18n_catalog import export_locale
    body = export_locale({"panel.send": "Envoyer"}, locale="fr")
    parsed = json.loads(body)
    assert parsed["locale"] == "fr"
    assert parsed["strings"]["panel.send"] == "Envoyer"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
