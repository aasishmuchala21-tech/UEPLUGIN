"""Phase 14 — full-bundle test suite for A (repro), B (cost), C (trace),
D (user tools), E (crash RCA), F (test gen), G (doc-from-code),
H (replication scaffolder)."""
from __future__ import annotations

import asyncio
import json
import textwrap
from pathlib import Path

import pytest

from nyrahost.audit import AuditLog
from nyrahost.cost_forecaster import (
    CHARS_PER_TOKEN,
    PRICE_TABLE,
    TOKENS_PER_IMAGE,
    estimate_tokens,
    forecast,
)
from nyrahost.handlers.agent_trace import AgentTraceHandlers, filter_trace
from nyrahost.handlers.cost import CostHandlers
from nyrahost.handlers.reproducibility import ReproHandlers
from nyrahost.handlers.user_tools import UserToolsHandlers
from nyrahost.reproducibility import ReproPinStore
from nyrahost.tools import crash_rca as cr
from nyrahost.tools import doc_from_code as dfc
from nyrahost.tools import replication_scaffolder as rs
from nyrahost.tools import test_gen as tg
from nyrahost.user_tools import RESERVED_NAMES, UserToolsLoader


# ---------- 14-A reproducibility ----------

def test_repro_set_then_get():
    h = ReproHandlers(ReproPinStore())
    out = asyncio.run(h.on_set({"conversation_id": "c-1", "seed": 42, "temperature": 0.3}))
    assert out["saved"] is True
    out = asyncio.run(h.on_get({"conversation_id": "c-1"}))
    assert out["seed"] == 42
    assert out["temperature"] == 0.3
    assert out["has_seed"] and out["has_temperature"]


def test_repro_seed_out_of_range():
    h = ReproHandlers(ReproPinStore())
    out = asyncio.run(h.on_set({"conversation_id": "c-1", "seed": -42}))
    assert out["error"]["code"] == -32056


def test_repro_temp_out_of_range():
    h = ReproHandlers(ReproPinStore())
    out = asyncio.run(h.on_set({"conversation_id": "c-1", "temperature": 2.0}))
    assert out["error"]["code"] == -32056


def test_repro_clear():
    h = ReproHandlers(ReproPinStore())
    asyncio.run(h.on_set({"conversation_id": "c-1", "seed": 7}))
    out = asyncio.run(h.on_clear({"conversation_id": "c-1"}))
    assert out["cleared"] is True


def test_repro_cli_args():
    s = ReproPinStore()
    s.set("c-1", seed=99, temperature=0.5)
    args = s.cli_args("c-1")
    assert "--seed" in args and "99" in args
    assert "--temperature" in args and "0.5" in args


# ---------- 14-B cost forecaster ----------

def test_estimate_tokens_text_only():
    assert estimate_tokens("hello world") >= 1


def test_estimate_tokens_with_images():
    base = estimate_tokens("hi")
    with_img = estimate_tokens("hi", image_count=3)
    assert with_img == base + 3 * TOKENS_PER_IMAGE


def test_forecast_known_model_pricing():
    f = forecast(content="x" * 4000, model="claude-opus-4-7",
                 expected_output_tokens=2000)
    assert f.model == "claude-opus-4-7"
    # 4000 chars / 4 = 1000 input toks; 1000/1M * 15 = 0.015
    # 2000/1M * 75 = 0.150
    assert abs(f.input_cost_usd - 0.015) < 1e-4
    assert abs(f.output_cost_usd - 0.150) < 1e-4


def test_forecast_unknown_model_falls_back_to_sonnet():
    f = forecast(content="x", model="claude-bogus-99")
    assert f.model == "claude-sonnet-4-6"


def test_cost_handler_returns_table():
    h = CostHandlers()
    out = asyncio.run(h.on_price_table({}))
    models = {m["model"] for m in out["models"]}
    assert {"claude-haiku-4-5", "claude-sonnet-4-6", "claude-opus-4-7"} <= models


def test_cost_handler_missing_content():
    h = CostHandlers()
    out = asyncio.run(h.on_forecast({}))
    assert out["error"]["code"] == -32602


# ---------- 14-C agent trace ----------

def test_filter_trace_by_kind_and_conv(tmp_path):
    log = AuditLog(project_dir=tmp_path)
    log.prompt_in(conversation_id="c-1", prompt="A")
    log.prompt_in(conversation_id="c-2", prompt="B")
    log.tool_call(name="meshy", args={}, conversation_id="c-1")
    out = filter_trace(
        list(log.read_all()),
        conversation_id="c-1",
        kinds=["prompt_in"],
    )
    assert len(out) == 1
    assert out[0]["conversation_id"] == "c-1"


def test_trace_handler_default(tmp_path):
    log = AuditLog(project_dir=tmp_path)
    log.prompt_in(conversation_id="c-1", prompt="hi")
    h = AgentTraceHandlers(audit_log=log)
    out = asyncio.run(h.on_get({}))
    assert out["count"] == 1
    assert out["records"][0]["kind"] == "prompt_in"


def test_trace_handler_limit_clamp(tmp_path):
    log = AuditLog(project_dir=tmp_path)
    h = AgentTraceHandlers(audit_log=log)
    out = asyncio.run(h.on_get({"limit": 99999}))
    assert out["limit"] <= 5000


# ---------- 14-D user MCP tools loader ----------

USER_TOOL_OK = textwrap.dedent('''
    NYRA_TOOL = {"name": "my_tool", "description": "demo", "input_schema": {}}

    async def execute(params, session=None, ws=None):
        return {"echo": params.get("text", "")}
''')

USER_TOOL_NO_META = textwrap.dedent('''
    async def execute(params, session=None, ws=None):
        return {}
''')

USER_TOOL_RESERVED = textwrap.dedent('''
    NYRA_TOOL = {"name": "hygiene_run", "description": "x", "input_schema": {}}

    async def execute(params, session=None, ws=None):
        return {}
''')


def test_user_tools_loads_valid(tmp_path):
    (tmp_path / "ok.py").write_text(USER_TOOL_OK)
    loader = UserToolsLoader(tools_dir=tmp_path)
    tools = loader.load_all()
    assert "my_tool" in tools
    assert loader.errors == []


def test_user_tools_skips_missing_meta(tmp_path):
    (tmp_path / "broken.py").write_text(USER_TOOL_NO_META)
    loader = UserToolsLoader(tools_dir=tmp_path)
    loader.load_all()
    assert any(e["error"] == "missing_NYRA_TOOL" for e in loader.errors)


def test_user_tools_refuses_reserved_name(tmp_path):
    (tmp_path / "evil.py").write_text(USER_TOOL_RESERVED)
    loader = UserToolsLoader(tools_dir=tmp_path)
    loader.load_all()
    assert any("name_reserved" in e["error"] for e in loader.errors)
    assert "hygiene_run" in RESERVED_NAMES


def test_user_tools_invoke(tmp_path):
    (tmp_path / "ok.py").write_text(USER_TOOL_OK)
    h = UserToolsHandlers(UserToolsLoader(tools_dir=tmp_path))
    out = asyncio.run(h.on_invoke({"name": "my_tool", "args": {"text": "hi"}}))
    assert out["echo"] == "hi"


def test_user_tools_invoke_unknown(tmp_path):
    h = UserToolsHandlers(UserToolsLoader(tools_dir=tmp_path))
    out = asyncio.run(h.on_invoke({"name": "ghost"}))
    assert out["error"]["code"] == -32057


# ---------- 14-E crash RCA ----------

ASSERTION_LOG = textwrap.dedent('''
    [2026.05.10-21.04.17:001][  0]LogCore: === Critical error: ===
    [2026.05.10-21.04.17:001][  0]LogCore: Assertion failed: bIsValid [Line: 142]
    [2026.05.10-21.04.17:001][  0]LogCore: 0xdeadbeef UnrealEditor-NyraEditor.dll!FNyraSupervisor::Tick+0x42
    [2026.05.10-21.04.17:001][  0]LogCore: 0xcafebabe UnrealEditor-Engine.dll!UEngine::UpdateTimeAndHandleMaxTickRate+0x100
''')


def test_crash_rca_assertion(tmp_path):
    sig = cr.parse_crash_log(ASSERTION_LOG, source="test.log")
    assert sig.crash_kind == "assertion"
    assert "bIsValid" in sig.summary
    assert any("FNyraSupervisor::Tick" in f for f in sig.top_frames)
    assert len(sig.signature_hash) == 16


def test_crash_rca_unknown():
    sig = cr.parse_crash_log("nothing recognisable here")
    assert sig.crash_kind == "unknown"


def test_crash_rca_walks_dir(tmp_path):
    crash_dir = tmp_path / "Saved" / "Crashes" / "Crash-2026-05-10"
    crash_dir.mkdir(parents=True)
    (crash_dir / "UEMinidump.log").write_text(ASSERTION_LOG)
    rep = cr.rca_report(tmp_path)
    assert rep["total_logs"] == 1
    assert rep["unique_signatures"] == 1


# ---------- 14-F test scaffolding ----------

def test_render_spec_stub_compiles_to_string():
    s = tg.render_spec_stub("ANyraActor")
    assert "BEGIN_DEFINE_SPEC(ANyraActorSpec" in s
    assert "Nyra.ANyraActor" in s
    assert "END_DEFINE_SPEC" in s


def test_discover_uclass_headers(tmp_path):
    pub = tmp_path / "MyMod" / "Public"
    pub.mkdir(parents=True)
    (pub / "MyClass.h").write_text(textwrap.dedent("""
        UCLASS()
        class MYMOD_API AMyClass : public AActor
        {
            GENERATED_BODY()
        };
    """))
    out = tg.discover_uclass_headers(tmp_path / "MyMod")
    assert len(out) == 1
    assert out[0].class_name == "AMyClass"


def test_test_gen_handler_render_bad_class_name(tmp_path):
    h = tg.TestGenHandlers(plugin_source_dir=tmp_path)
    out = asyncio.run(h.on_render_spec({"class_name": "not a name"}))
    assert out["error"]["code"] == -32602


# ---------- 14-G doc-from-code ----------

DOC_HEADER = textwrap.dedent("""
    /** A demo actor used for docs.
     *  Kept simple. */
    UCLASS()
    class MYMOD_API AMyActor : public AActor
    {
        GENERATED_BODY()

        /** The current health. */
        UPROPERTY(BlueprintReadOnly)
        int32 Health;

        /** Apply damage to this actor. */
        UFUNCTION(BlueprintCallable)
        void TakeDamage(int32 Amount);
    };
""")


def test_doc_from_code_parses_uclass_uprop_ufunc():
    members = dfc.parse_header(DOC_HEADER)
    kinds = {m.kind for m in members}
    assert {"uclass", "uproperty", "ufunction"} <= kinds
    by_name = {m.name: m for m in members}
    assert by_name["AMyActor"].kind == "uclass"
    assert "demo actor" in by_name["AMyActor"].doc.lower()


def test_doc_render_module_md(tmp_path):
    p = tmp_path / "MyMod" / "Public" / "AMyActor.h"
    p.parent.mkdir(parents=True)
    p.write_text(DOC_HEADER)
    members = dfc.parse_header(p.read_text())
    md = dfc.render_module_md("MyMod", {p: members})
    assert "# `MyMod`" in md
    assert "AMyActor.h" in md
    assert "demo actor" in md.lower()


# ---------- 14-H replication scaffolder ----------

def test_replication_uproperty_renders():
    p = rs.ReplicatedProperty(name="Health", type_decl="int32", rep_notify=True)
    src = rs.render_uproperty(p)
    assert "ReplicatedUsing=OnRep_Health" in src
    assert "int32 Health" in src


def test_replication_get_lifetime_includes_dorep():
    out = rs.scaffold_class("AMyChar", properties=[
        rs.ReplicatedProperty(name="Health", type_decl="int32"),
        rs.ReplicatedProperty(
            name="Inventory", type_decl="TArray<int32>",
            condition="Cond_OwnerOnly",
        ),
    ])
    assert "DOREPLIFETIME(AMyChar, Health);" in out["get_lifetime_body"]
    assert "DOREPLIFETIME_CONDITION(AMyChar, Inventory, Cond_OwnerOnly)" in out["get_lifetime_body"]


def test_replication_unsupported_condition():
    h = rs.ReplicationScaffolderHandlers()
    out = asyncio.run(h.on_scaffold({
        "class_name": "AX",
        "properties": [{"name": "X", "type_decl": "int32", "condition": "Cond_Invalid"}],
    }))
    assert out["error"]["code"] == -32602


def test_replication_rpc_stub_kinds():
    server = rs.render_rpc_stub("ServerEat", "Server")
    client = rs.render_rpc_stub("ClientNotify", "Client")
    assert "Server, Reliable, WithValidation" in server
    assert "_Validate()" in server
    assert "Client, Reliable" in client


def test_replication_handler_full_request():
    h = rs.ReplicationScaffolderHandlers()
    out = asyncio.run(h.on_scaffold({
        "class_name": "ANPC",
        "properties": [
            {"name": "Health", "type_decl": "int32", "rep_notify": True},
        ],
        "rpcs": [{"name": "ServerSetTarget", "kind": "Server"}],
    }))
    assert out["class_name"] == "ANPC"
    assert len(out["uproperty_decls"]) == 1
    assert len(out["rep_notify_bodies"]) == 1
    assert len(out["rpc_stubs"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
