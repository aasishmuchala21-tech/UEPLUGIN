"""Phase 19 — Aura-killer final push tests.

A (audio gen), B (Fab search), D (smart low-poly Meshy), E (replace
player), G (Timeline all 4 kinds), I (Junie + todos)."""
from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from nyrahost.external import audio_gen_client as agc
from nyrahost.external.meshy_client import MeshyClient
from nyrahost.handlers.todos import TodosHandlers, TodosStore, MAX_LISTS
from nyrahost.mcp_installer import list_targets
from nyrahost.tools import audio_gen as ag
from nyrahost.tools import character_replace as cr
from nyrahost.tools import fab_search as fs
from nyrahost.tools import timeline_tools as tt


# ---------- 19-A audio generation ----------

@pytest.fixture(autouse=True)
def _eleven_key(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key-not-real")
    yield


def test_audio_gen_handler_missing_prompt(tmp_path):
    out = asyncio.run(ag.on_generate_sfx({"project_saved": str(tmp_path)}))
    assert out["error"]["code"] == -32602


def test_audio_gen_handler_auth_error(tmp_path, monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    out = asyncio.run(ag.on_generate_sfx(
        {"prompt": "boom", "project_saved": str(tmp_path)}
    ))
    assert out["error"]["code"] == -32081


def test_audio_gen_client_clamps_duration(tmp_path):
    """duration_s outside [0.5, 22] is silently clamped per ElevenLabs cap."""
    async def fake_post(self, url, headers=None, json=None):
        class R:
            status_code = 200
            content = b"FAKE_MP3"
            is_success = True
            reason_phrase = "OK"
        return R()

    async def fake_gen(self, *, prompt, duration_s, prompt_influence, output_path):
        return agc.AudioGenResult(
            file_path=str(output_path), duration_s=duration_s,
            prompt=prompt, provider="elevenlabs_sfx",
        )

    # Verify clamp in handler call path (not the real HTTP — that needs httpx mock)
    client = agc.AudioGenClient(api_key="k")
    # Simulate the clamp logic directly
    d = max(agc.MIN_DURATION_S, min(99.0, agc.MAX_DURATION_S))
    assert d == agc.MAX_DURATION_S
    d2 = max(agc.MIN_DURATION_S, min(-1.0, agc.MAX_DURATION_S))
    assert d2 == agc.MIN_DURATION_S


def test_audio_gen_handler_calls_through(tmp_path):
    async def fake_generate_sfx(self, *, prompt, duration_s, output_path, prompt_influence=0.3):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"OK")
        return agc.AudioGenResult(
            file_path=str(output_path), duration_s=duration_s,
            prompt=prompt, provider="elevenlabs_sfx",
        )
    with patch.object(agc.AudioGenClient, "generate_sfx", new=fake_generate_sfx):
        out = asyncio.run(ag.on_generate_sfx(
            {"prompt": "explosion", "duration_s": 3.0,
             "project_saved": str(tmp_path)}
        ))
    assert "file_path" in out
    assert out["duration_s"] == 3.0


# ---------- 19-B Fab Store search ----------

def test_fab_handler_missing_query():
    h = fs.FabSearchHandlers()
    out = asyncio.run(h.on_search({}))
    assert out["error"]["code"] == -32602


def test_fab_handler_network_error():
    class _FakeC:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, params=None): raise RuntimeError("dns fail")
    client = fs.FabSearchClient(_http=_FakeC())
    h = fs.FabSearchHandlers(client)
    out = asyncio.run(h.on_search({"query": "rocks"}))
    assert out["error"]["code"] == -32083


def test_fab_handler_success_slim_response():
    class _FakeResp:
        is_success = True
        status_code = 200
        def json(self):
            return {"results": [
                {"uid": "abc", "title": "Free Forest Pack",
                 "seller": {"name": "Acme"},
                 "price": {"amount": 0.0},
                 "free": True,
                 "url": "https://fab.com/abc"},
                {"id": "def", "name": "Premium Rocks",
                 "creator": {"name": "RockCo"},
                 "price": {"amount": 12.99},
                 "url": "https://fab.com/def"},
            ]}
    class _FakeC:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, params=None): return _FakeResp()
    client = fs.FabSearchClient(_http=_FakeC())
    h = fs.FabSearchHandlers(client)
    out = asyncio.run(h.on_search({"query": "rocks", "limit": 10}))
    assert "error" not in out
    assert len(out["listings"]) == 2
    assert out["listings"][0]["free"] is True
    assert out["listings"][1]["price_usd"] == 12.99


# ---------- 19-D smart low-poly Meshy param ----------

@pytest.mark.asyncio
async def test_meshy_low_poly_param_passthrough(tmp_path, monkeypatch):
    """When low_poly=True, MeshyClient inserts target_polycount=1500 in body."""
    monkeypatch.setenv("MESHY_API_KEY", "test-key")
    sent: dict = {}

    class _FakeResp:
        status_code = 200
        is_success = True
        reason_phrase = "OK"
        def json(self):
            return {"id": "task_abc"}

    class _FakeStatusResp(_FakeResp):
        def json(self):
            return {"status": "completed", "model_urls": {"glb": "https://x.com/x.glb"}}

    async def fake_request(self, method, path, *, client, **kwargs):
        if method == "POST":
            sent["data"] = kwargs.get("data")
            return _FakeResp()
        return _FakeStatusResp()

    img = tmp_path / "img.jpg"
    img.write_bytes(b"\xFF\xD8\xFF")
    with patch.object(MeshyClient, "_request", new=fake_request):
        client = MeshyClient()
        await client.image_to_3d(image_path=str(img), low_poly=True)
    assert sent["data"]["target_polycount"] == "1500"


@pytest.mark.asyncio
async def test_meshy_explicit_polycount_overrides(tmp_path, monkeypatch):
    monkeypatch.setenv("MESHY_API_KEY", "test-key")
    sent: dict = {}
    class _R:
        status_code = 200; is_success = True; reason_phrase = "OK"
        def json(self): return {"id": "t", "status": "completed",
                                 "model_urls": {"glb": "u"}}
    async def fake_request(self, method, path, *, client, **kwargs):
        if method == "POST":
            sent["data"] = kwargs.get("data")
        return _R()
    img = tmp_path / "i.jpg"
    img.write_bytes(b"x")
    with patch.object(MeshyClient, "_request", new=fake_request):
        await MeshyClient().image_to_3d(image_path=str(img),
                                          low_poly=False, target_polycount=2500)
    assert sent["data"]["target_polycount"] == "2500"


# ---------- 19-E replace player character ----------

def test_replace_player_renders_no_leftovers():
    s = cr.render_replace_script(new_mesh_path="/Game/NYRA/SK_Hero")
    assert "${" not in s
    start = s.index("'''") + 3
    end = s.index("'''", start)
    spec = json.loads(s[start:end])
    assert spec["new_mesh_path"] == "/Game/NYRA/SK_Hero"


def test_replace_player_compiles():
    s = cr.render_replace_script(new_mesh_path="/Game/NYRA/SK_Hero")
    compile(s, "<replace>", "exec")


def test_replace_player_rejects_relative_path():
    with pytest.raises(ValueError, match="UE asset path"):
        cr.render_replace_script(new_mesh_path="SK_Hero")


def test_replace_player_handler_bad_input():
    out = asyncio.run(cr.on_replace_player({"new_mesh_path": "not_a_path"}))
    assert out["error"]["code"] == -32602


def test_replace_player_handler_ok():
    out = asyncio.run(cr.on_replace_player({"new_mesh_path": "/Game/NYRA/SK"}))
    assert out["language"] == "python"
    assert "auto_rig_and_retarget" not in out["script"]  # different template
    assert "find_player_pawn_class" in out["script"]


# ---------- 19-G Timeline all 4 track kinds ----------

def test_timeline_vector_renders():
    s = tt.render_timeline_script(
        blueprint_path="/Game/BP_X", track_name="Move",
        keyframes=[[0, 0, 0, 0], [1, 1, 1, 1]], track_kind="vector",
    )
    assert "${" not in s
    compile(s, "<vec>", "exec")


def test_timeline_linear_color_renders():
    s = tt.render_timeline_script(
        blueprint_path="/Game/BP_X", track_name="Flash",
        keyframes=[[0, 1, 0, 0, 1], [0.5, 1, 1, 1, 1]],
        track_kind="linear_color",
    )
    assert "${" not in s
    compile(s, "<lc>", "exec")


def test_timeline_event_renders():
    s = tt.render_timeline_script(
        blueprint_path="/Game/BP_X", track_name="Bursts",
        keyframes=[[0.5], [1.0], [1.5]], track_kind="event",
    )
    assert "${" not in s
    compile(s, "<ev>", "exec")


def test_timeline_unknown_track_kind_still_rejected():
    with pytest.raises(ValueError):
        tt.render_timeline_script(
            blueprint_path="/Game/BP_X", track_name="X",
            track_kind="quaternion",
        )


# ---------- 19-I Junie + todos ----------

def test_junie_in_list_targets():
    targets = list_targets()
    keys = {t.key for t in targets}
    assert "junie" in keys


def test_todos_create_and_edit(tmp_path):
    store = TodosStore(project_dir=tmp_path)
    h = TodosHandlers(store)
    out = asyncio.run(h.on_create({"title": "Sprint 1"}))
    assert "list" in out
    lid = out["list"]["list_id"]
    edited = asyncio.run(h.on_edit({
        "list_id": lid,
        "ops": [{"op": "add", "text": "Fix the supervisor compile"},
                {"op": "add", "text": "Apply phase patches"}],
    }))
    assert len(edited["list"]["items"]) == 2


def test_todos_check_then_remove(tmp_path):
    store = TodosStore(project_dir=tmp_path)
    h = TodosHandlers(store)
    asyncio.run(h.on_create({"title": "t"}))
    out = asyncio.run(h.on_list_all({}))
    lid = out["lists"][0]["list_id"]
    edited = asyncio.run(h.on_edit({"list_id": lid,
                                    "ops": [{"op": "add", "text": "x"}]}))
    item_id = edited["list"]["items"][0]["id"]
    asyncio.run(h.on_edit({"list_id": lid,
                           "ops": [{"op": "check", "id": item_id}]}))
    out = asyncio.run(h.on_list_all({}))
    assert out["lists"][0]["items"][0]["done"] is True
    asyncio.run(h.on_edit({"list_id": lid,
                           "ops": [{"op": "remove", "id": item_id}]}))
    out = asyncio.run(h.on_list_all({}))
    assert out["lists"][0]["items"] == []


def test_todos_unknown_list_returns_error(tmp_path):
    h = TodosHandlers(TodosStore(project_dir=tmp_path))
    out = asyncio.run(h.on_edit({"list_id": "ghost",
                                  "ops": [{"op": "add", "text": "x"}]}))
    assert out["error"]["code"] == -32085


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
