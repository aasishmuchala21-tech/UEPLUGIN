"""Phase 13 — full-bundle test suite for A (threads), B (timeline),
C (hygiene), D (audit), E (perf budget)."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from nyrahost.handlers.threads import (
    ChatThread,
    MAX_THREADS,
    ThreadHandlers,
    ThreadRegistry,
)
from nyrahost.tools import asset_hygiene as ah
from nyrahost.tools import perf_budget as pb
from nyrahost.tools import timeline_tools as tt
from nyrahost.audit import AuditLog, MAX_LINE_BYTES, SECRET_FIELDS


# ---------- 13-A multi-thread chats ----------

def test_threads_create_up_to_max():
    h = ThreadHandlers()
    for i in range(MAX_THREADS):
        out = asyncio.run(h.on_create({"title": f"t{i}"}))
        assert out["thread"]["title"] == f"t{i}"
    # Limit reached
    out = asyncio.run(h.on_create({"title": "overflow"}))
    assert out["error"]["code"] == -32051
    assert out["error"]["message"] == "thread_limit_reached"


def test_threads_close_returns_unknown_thread():
    h = ThreadHandlers()
    out = asyncio.run(h.on_close({"thread_id": "deadbeef"}))
    assert out["error"]["code"] == -32052


def test_threads_list_orders_by_last_active():
    h = ThreadHandlers()
    a = asyncio.run(h.on_create({"title": "A"}))["thread"]
    b = asyncio.run(h.on_create({"title": "B"}))["thread"]
    asyncio.run(h.on_touch({"thread_id": a["thread_id"]}))   # bump A
    out = asyncio.run(h.on_list({}))
    # A is now most-recent
    assert out["threads"][0]["thread_id"] == a["thread_id"]
    assert out["count"] == 2


def test_threads_close_then_create_replaces_slot():
    h = ThreadHandlers()
    for _ in range(MAX_THREADS):
        asyncio.run(h.on_create({}))
    first = asyncio.run(h.on_list({}))["threads"][0]["thread_id"]
    asyncio.run(h.on_close({"thread_id": first}))
    out = asyncio.run(h.on_create({"title": "fresh"}))
    assert "thread" in out


# ---------- 13-B Timeline ----------

def test_timeline_renders_no_leftovers():
    script = tt.render_timeline_script(
        blueprint_path="/Game/BP_Door",
        track_name="DoorOpen",
        keyframes=[[0, 0], [2, 1]],
        autoplay=False,
        loop=False,
        duration=2.0,
    )
    assert "${" not in script
    # JSON literal embedded
    start = script.index("'''") + 3
    end = script.index("'''", start)
    spec = json.loads(script[start:end])
    assert spec["track_name"] == "DoorOpen"
    assert spec["track_kind"] == "float"


def test_timeline_compiles():
    script = tt.render_timeline_script(
        blueprint_path="/Game/BP_X",
        track_name="X",
    )
    compile(script, "<timeline_test>", "exec")


def test_timeline_handler_rejects_unknown_track_kind():
    # Phase 19-G opened ALLOWED_TRACK_KINDS to all 4 Aura kinds (float, vector,
    # linear_color, event). Use a kind that's still unsupported.
    out = asyncio.run(tt.on_add_timeline({
        "blueprint_path": "/Game/BP",
        "track_name": "X",
        "track_kind": "quaternion",  # still not allowed
    }))
    assert out["error"]["code"] == -32602


def test_timeline_handler_missing_blueprint_path():
    out = asyncio.run(tt.on_add_timeline({"track_name": "X"}))
    assert out["error"]["code"] == -32602


# Fix #4 from PR #1 code review: per-kind keyframe shape validation.
# Phase 19-G expanded ALLOWED_TRACK_KINDS without arity guards, so a
# vector track with float-shaped keyframes used to blow up the UE
# template's tuple-unpack helper. Now the host returns -32602 with a
# kind-specific message.
def test_timeline_vector_with_float_shaped_keyframes_rejected():
    out = asyncio.run(tt.on_add_timeline({
        "blueprint_path": "/Game/BP",
        "track_name": "Pos",
        "track_kind": "vector",
        "keyframes": [[0.0, 1.0]],  # float shape — wrong for vector (needs 4)
    }))
    assert out["error"]["code"] == -32602
    assert "vector" in out["error"]["data"]["detail"]


def test_timeline_linear_color_with_vector_keyframes_rejected():
    out = asyncio.run(tt.on_add_timeline({
        "blueprint_path": "/Game/BP",
        "track_name": "Col",
        "track_kind": "linear_color",
        "keyframes": [[0.0, 1.0, 0.0, 0.0]],  # vector shape — needs 5 for linear_color
    }))
    assert out["error"]["code"] == -32602


def test_timeline_event_with_extra_value_rejected():
    out = asyncio.run(tt.on_add_timeline({
        "blueprint_path": "/Game/BP",
        "track_name": "Evt",
        "track_kind": "event",
        "keyframes": [[0.5, 1.0]],  # event needs only [t]
    }))
    assert out["error"]["code"] == -32602


def test_timeline_keyframes_default_to_per_kind_shape():
    # Caller omits keyframes — host must pick a kind-appropriate default,
    # not the legacy [[0,0],[1,1]] float pair that would now blow shape
    # validation for vector / linear_color / event.
    for kind in ("float", "vector", "linear_color", "event"):
        out = asyncio.run(tt.on_add_timeline({
            "blueprint_path": "/Game/BP",
            "track_name": "T",
            "track_kind": kind,
        }))
        assert "error" not in out, f"{kind} default keyframes should be valid"


# ---------- 13-C Asset Hygiene ----------

def test_hygiene_renders_no_leftovers():
    script = ah.render_hygiene_script(under="/Game/Foo")
    assert "${" not in script
    start = script.index("'''") + 3
    end = script.index("'''", start)
    spec = json.loads(script[start:end])
    assert spec["under"] == "/Game/Foo"
    assert "Blueprint" in spec["naming_rules"]


def test_hygiene_compiles():
    script = ah.render_hygiene_script(under="/Game")
    compile(script, "<hygiene_test>", "exec")


def test_hygiene_rejects_relative_path():
    with pytest.raises(ValueError):
        ah.render_hygiene_script(under="Game")


def test_hygiene_handler_default():
    out = asyncio.run(ah.on_run_hygiene({}))
    assert out["language"] == "python"
    assert "main(" in out["script"]


# ---------- 13-D Audit log ----------

def test_audit_writes_jsonl(tmp_path):
    log = AuditLog(project_dir=tmp_path)
    log.prompt_in(conversation_id="c-1", prompt="Hello", model="claude-opus-4-7")
    log.tool_call(name="meshy.image_to_3d", args={"image_path": "/tmp/x.png"}, decided="approved")
    records = list(log.read_all())
    assert len(records) == 2
    assert records[0]["kind"] == "prompt_in"
    assert records[1]["kind"] == "tool_call"
    assert records[1]["tool"] == "meshy.image_to_3d"


def test_audit_redacts_secrets(tmp_path):
    log = AuditLog(project_dir=tmp_path)
    log.outbound(target="https://meshy.ai/api/v1/meshes", method="POST", status=200)
    log.tool_call(name="claude.send", args={
        "Authorization": "Bearer sk-secret",
        "api_key": "MESHY-SECRET",
        "prompt": "harmless",
    })
    records = list(log.read_all())
    tool = records[1]
    assert tool["args"]["Authorization"] == "<redacted>"
    assert tool["args"]["api_key"] == "<redacted>"
    assert tool["args"]["prompt"] == "harmless"
    assert "sk-secret" not in json.dumps(records)


def test_audit_truncates_oversize(tmp_path):
    log = AuditLog(project_dir=tmp_path)
    huge = "x" * (MAX_LINE_BYTES + 100)
    log.prompt_in(conversation_id="c", prompt=huge)
    rec = list(log.read_all())[0]
    assert rec.get("_truncated") is True
    assert rec["prompt"].endswith("...<truncated>")


def test_audit_secret_fields_set_includes_canonical_keys():
    assert "ANTHROPIC_API_KEY" in SECRET_FIELDS
    assert "MESHY_API_KEY" in SECRET_FIELDS
    assert "Authorization" in SECRET_FIELDS


# ---------- 13-E Performance Budget ----------

def test_perf_budget_save_load_roundtrip(tmp_path):
    h = pb.PerfBudgetHandlers(project_dir=tmp_path)
    asyncio.run(h.on_set_budget({
        "level_path": "/Game/Levels/L_City",
        "actor_count": 2000,
        "light_count": 80,
        "static_mesh_actor_count": 1500,
    }))
    out = asyncio.run(h.on_get_budgets({}))
    assert len(out["budgets"]) == 1
    b = out["budgets"][0]
    assert b["level_path"] == "/Game/Levels/L_City"
    assert b["actor_count"] == 2000


def test_perf_budget_check_under_budget(tmp_path):
    h = pb.PerfBudgetHandlers(project_dir=tmp_path)
    asyncio.run(h.on_set_budget({
        "level_path": "/Game/L_X",
        "actor_count": 100,
        "light_count": 10,
        "static_mesh_actor_count": 50,
    }))
    out = asyncio.run(h.on_check({"measurement": {
        "level_path": "/Game/L_X",
        "actor_count": 90,
        "light_count": 5,
        "static_mesh_actor_count": 40,
    }}))
    assert out["passed"] is True
    assert out["violations"] == []


def test_perf_budget_check_violation(tmp_path):
    h = pb.PerfBudgetHandlers(project_dir=tmp_path)
    asyncio.run(h.on_set_budget({
        "level_path": "/Game/L_X",
        "actor_count": 100, "light_count": 10, "static_mesh_actor_count": 50,
    }))
    out = asyncio.run(h.on_check({"measurement": {
        "level_path": "/Game/L_X",
        "actor_count": 200, "light_count": 5, "static_mesh_actor_count": 50,
    }}))
    assert out["passed"] is False
    violations = {v["metric"]: v for v in out["violations"]}
    assert "actor_count" in violations
    assert violations["actor_count"]["over_by"] == 100


def test_perf_budget_check_no_baseline(tmp_path):
    h = pb.PerfBudgetHandlers(project_dir=tmp_path)
    out = asyncio.run(h.on_check({"measurement": {
        "level_path": "/Game/Unmapped",
        "actor_count": 1,
    }}))
    assert out["error"]["code"] == -32602
    assert out["error"]["message"] == "no_budget_for_level"


def test_perf_budget_render_script(tmp_path):
    h = pb.PerfBudgetHandlers(project_dir=tmp_path)
    out = asyncio.run(h.on_render_script({"levels": ["/Game/A", "/Game/B"]}))
    assert out["language"] == "python"
    compile(out["script"], "<perf_test>", "exec")


def test_perf_budget_set_missing_level_path(tmp_path):
    h = pb.PerfBudgetHandlers(project_dir=tmp_path)
    out = asyncio.run(h.on_set_budget({}))
    assert out["error"]["code"] == -32602


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
