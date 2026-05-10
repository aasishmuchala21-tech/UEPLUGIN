"""Phase 15 — final bundle: encrypted memory, localization, cinematic,
health, privacy guard, blueprint static review."""
from __future__ import annotations

import asyncio
import json
import textwrap
from pathlib import Path

import pytest

from nyrahost.audit import AuditLog
from nyrahost.encrypted_memory import EncryptedMemory, MAX_MEMORY_BYTES
from nyrahost.handlers.encrypted_memory import EncryptedMemoryHandlers
from nyrahost.handlers.health import HealthHandlers
from nyrahost.handlers.threads import ThreadRegistry
from nyrahost.health import HealthDashboard
from nyrahost.privacy_guard import (
    ALWAYS_ALLOWED_HOSTS,
    OutboundRefused,
    PrivacyGuard,
)
from nyrahost.tools import blueprint_review as bpr
from nyrahost.tools import cinematic as cm
from nyrahost.tools import localization as loc


# ---------- 15-A encrypted memory ----------

def test_memory_save_load_roundtrip(tmp_path):
    m = EncryptedMemory(project_dir=tmp_path)
    m.save({"hello": "world", "n": 42})
    m2 = EncryptedMemory(project_dir=tmp_path)
    assert m2.load() == {"hello": "world", "n": 42}


def test_memory_set_get_delete(tmp_path):
    m = EncryptedMemory(project_dir=tmp_path)
    m.set_key("foo", [1, 2, 3])
    assert m.get_key("foo") == [1, 2, 3]
    assert m.delete_key("foo") is True
    assert m.get_key("foo") is None


def test_memory_oversized_raises(tmp_path):
    m = EncryptedMemory(project_dir=tmp_path)
    payload = {"k": "x" * (MAX_MEMORY_BYTES + 1)}
    with pytest.raises(ValueError):
        m.save(payload)


def test_memory_handler_set_then_get(tmp_path):
    m = EncryptedMemory(project_dir=tmp_path)
    h = EncryptedMemoryHandlers(m)
    out = asyncio.run(h.on_set({"key": "x", "value": "y"}))
    assert out["saved"] is True
    out = asyncio.run(h.on_get({"key": "x"}))
    assert out["value"] == "y"


def test_memory_handler_missing_value(tmp_path):
    m = EncryptedMemory(project_dir=tmp_path)
    h = EncryptedMemoryHandlers(m)
    out = asyncio.run(h.on_set({"key": "x"}))
    assert out["error"]["code"] == -32602


def test_memory_tamper_detection(tmp_path):
    """Manually corrupt the .enc file; load() returns {} not garbage."""
    m = EncryptedMemory(project_dir=tmp_path)
    m.save({"hello": "world"})
    enc_path = tmp_path / "Saved" / "NYRA" / "memory.enc"
    enc_path.write_bytes(b"definitely-not-fernet")
    assert EncryptedMemory(project_dir=tmp_path).load() == {}


# ---------- 15-B localization ----------

SAMPLE_CPP = textwrap.dedent('''
    #define LOCTEXT_NAMESPACE "Combat"
    void Foo()
    {
        FText Msg = LOCTEXT("HitPlayerKey", "You took {0} damage!");
    }
    #undef LOCTEXT_NAMESPACE

    void Bar()
    {
        FText X = NSLOCTEXT("UI", "OkButton", "OK");
    }
''')


def test_loctext_extracts_namespace_and_key():
    entries = loc.extract_from_text(SAMPLE_CPP)
    assert len(entries) == 2
    by_key = {e.key: e for e in entries}
    assert by_key["HitPlayerKey"].namespace == "Combat"
    assert by_key["OkButton"].namespace == "UI"


def test_loctext_csv_renders():
    entries = loc.extract_from_text(SAMPLE_CPP)
    csv = loc.to_csv(entries)
    assert "namespace,key,source" in csv
    assert "Combat,HitPlayerKey" in csv


def test_loctext_po_skeleton():
    entries = loc.extract_from_text(SAMPLE_CPP)
    po = loc.to_po_skeleton(entries, lang="ja")
    assert 'Language: ja' in po
    assert 'msgctxt "Combat/HitPlayerKey"' in po


def test_loctext_handler_emit_unsupported_format():
    h = loc.LocalizationHandlers(plugin_source_dir=Path("/nonexistent"))
    out = asyncio.run(h.on_emit({"format": "xml"}))
    assert out["error"]["code"] == -32602


# ---------- 15-C cinematic ----------

def test_cinematic_renders_no_leftovers():
    s = cm.render_cinematic_script(focal_length_mm=50.0, duration_s=8.0)
    assert "${" not in s
    start = s.index("'''") + 3
    end = s.index("'''", start)
    spec = json.loads(s[start:end])
    assert spec["focal_length_mm"] == 50.0
    assert spec["duration_s"] == 8.0


def test_cinematic_rejects_unknown_key():
    with pytest.raises(ValueError):
        cm.render_cinematic_script(rocket_engine=True)


def test_cinematic_compiles():
    s = cm.render_cinematic_script()
    compile(s, "<cm>", "exec")


def test_cinematic_handler_filters_unknown_keys():
    out = asyncio.run(cm.on_cinematic({
        "duration_s": 4.0,
        "junk_field": "ignored",   # silently filtered, not an error
    }))
    assert "error" not in out
    assert "main(" in out["script"]


# ---------- 15-D live health ----------

def test_health_snapshot_no_threads(tmp_path):
    log = AuditLog(project_dir=tmp_path)
    log.prompt_in(conversation_id="c-1", prompt="hi")
    dash = HealthDashboard(
        project_dir=tmp_path,
        audit_log=log,
        thread_registry=ThreadRegistry(),
    )
    snap = dash.snapshot(recent_window_s=60.0)
    assert snap.audit_events_total == 1
    assert snap.thread_count == 0
    assert snap.thread_capacity == 4
    assert snap.crash_signature_count == 0


def test_health_capacity_full_note(tmp_path):
    reg = ThreadRegistry()
    for _ in range(reg.max_threads):
        reg.create()
    dash = HealthDashboard(
        project_dir=tmp_path,
        audit_log=AuditLog(project_dir=tmp_path),
        thread_registry=reg,
    )
    snap = dash.snapshot()
    assert "thread_capacity_full" in snap.notes


def test_health_handler(tmp_path):
    reg = ThreadRegistry()
    log = AuditLog(project_dir=tmp_path)
    h = HealthHandlers(HealthDashboard(
        project_dir=tmp_path, audit_log=log, thread_registry=reg,
    ))
    out = asyncio.run(h.on_snapshot({
        "last_crash_count": 2,
        "last_perf_violations": 5,
    }))
    assert out["crash_signature_count"] == 2
    assert out["perf_violations"] == 5
    assert "recent_crashes:2" in out["notes"]


# ---------- 15-E privacy guard ----------

def test_guard_idle_allows_anything():
    g = PrivacyGuard()
    g.assert_allowed("https://meshy.ai/api/v1/anything")   # no exception


def test_guard_enabled_blocks_external():
    g = PrivacyGuard()
    g.enable()
    with pytest.raises(OutboundRefused):
        g.assert_allowed("https://meshy.ai/api/v1/whatever")


def test_guard_enabled_allows_loopback():
    g = PrivacyGuard()
    g.enable()
    for host in ALWAYS_ALLOWED_HOSTS:
        # IPv6 hostnames in URLs require bracket form; everything else
        # is a bare authority. urllib.parse handles both shapes correctly.
        host_part = f"[{host}]" if ":" in host else host
        g.assert_allowed(f"http://{host_part}:8188/prompt")


def test_guard_refusal_count_increments():
    g = PrivacyGuard()
    g.enable()
    for _ in range(3):
        try:
            g.assert_allowed("https://api.openai.com/v1/x")
        except OutboundRefused:
            pass
    assert g.stats()["refusal_count"] == 3


def test_guard_disable_restores():
    g = PrivacyGuard()
    g.enable()
    g.disable()
    g.assert_allowed("https://meshy.ai/x")   # no exception


# ---------- 15-F blueprint static review ----------

BAD_BP = {
    "blueprint_path": "/Game/BP_Bad",
    "nodes": [
        {
            "node_id": "n_emit_exec",
            "pins": [
                {"name": "Then", "direction": "output", "pin_type": "exec", "links": []},
            ],
        },
        {
            "node_id": "n_wildcard",
            "pins": [
                {"name": "Value", "direction": "input", "pin_type": "wildcard"},
            ],
        },
        {
            "node_id": "n_cast",
            "class_type": "DynamicCast",
            "pins": [
                {"name": "CastFailed", "direction": "output", "pin_type": "exec", "links": []},
            ],
        },
        {
            "node_id": "n_funccall",
            "is_function_call": True,
            "pins": [
                {"name": "Target", "direction": "input", "links": []},
            ],
        },
    ],
    "variables": [
        {"name": "Health", "replication": "ReplicatedUsing"},
    ],
}


def test_bp_review_flags_hanging_exec():
    rep = bpr.review(BAD_BP)
    rules = {f["rule"] for f in rep["findings"]}
    assert "hanging_exec" in rules


def test_bp_review_flags_wildcard():
    rep = bpr.review(BAD_BP)
    rules = {f["rule"] for f in rep["findings"]}
    assert "wildcard_pin" in rules


def test_bp_review_flags_unsafe_cast():
    rep = bpr.review(BAD_BP)
    rules = {f["rule"] for f in rep["findings"]}
    assert "unsafe_cast" in rules


def test_bp_review_flags_unwired_target():
    rep = bpr.review(BAD_BP)
    rules = {f["rule"] for f in rep["findings"]}
    assert "unwired_target" in rules


def test_bp_review_flags_missing_on_rep():
    rep = bpr.review(BAD_BP)
    rules = {f["rule"] for f in rep["findings"]}
    assert "missing_on_rep" in rules


def test_bp_review_counts_match():
    rep = bpr.review(BAD_BP)
    assert rep["counts"]["total"] == len(rep["findings"])


def test_bp_review_handler_accepts_json_string():
    out = asyncio.run(bpr.on_review_graph({"graph": json.dumps(BAD_BP)}))
    assert "error" not in out
    assert out["counts"]["total"] > 0


def test_bp_review_handler_bad_json():
    out = asyncio.run(bpr.on_review_graph({"graph": "{not json"}))
    assert out["error"]["code"] == -32602


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
