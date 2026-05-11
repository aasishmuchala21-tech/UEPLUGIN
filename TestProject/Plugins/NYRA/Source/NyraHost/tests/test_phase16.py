"""Phase 16 — Tier 1.B finish-line tests.

A (PCG scatter), B (structural validation), C (spiral + arches),
D (BP review LLM), E (ControlNet inpaint), F (engine source RAG)."""
from __future__ import annotations

import asyncio
import json
import textwrap
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from nyrahost.external.comfyui_client import ComfyUIResult
from nyrahost.knowledge import source_ingest as si
from nyrahost.tools import blockout_primitives as bp
from nyrahost.tools import blockout_validation as bv
from nyrahost.tools import blueprint_review_llm as bplr
from nyrahost.tools import inpaint_tools as it
from nyrahost.tools import pcg_scatter as ps


# ---------- 16-A PCG scatter ----------

def test_pcg_surface_renders():
    s = ps.render_scatter_script(
        mode="surface", mesh_path="/Game/SM_Rock", density=0.3,
    )
    assert "${" not in s
    start = s.index("'''") + 3
    end = s.index("'''", start)
    spec = json.loads(s[start:end])
    assert spec["mode"] == "surface"
    assert spec["density"] == 0.3


def test_pcg_volume_with_anchor_floor():
    s = ps.render_scatter_script(
        mode="volume", mesh_path="/Game/SM_Crate", count=42, anchor="floor",
    )
    assert '"count":42' in s.replace(" ", "")
    assert "floor" in s


def test_pcg_spline_renders():
    s = ps.render_scatter_script(
        mode="spline", mesh_path="/Game/SM_Tree", spacing_cm=150.0,
    )
    assert '"mode":"spline"' in s.replace(" ", "")


def test_pcg_rejects_bad_mesh_path():
    with pytest.raises(ValueError, match="UE asset path"):
        ps.render_scatter_script(mode="surface", mesh_path="not_an_asset")


def test_pcg_rejects_huge_density():
    with pytest.raises(ValueError, match="density"):
        ps.render_scatter_script(
            mode="surface", mesh_path="/Game/X", density=ps.MAX_DENSITY + 1,
        )


def test_pcg_rejects_unknown_anchor():
    with pytest.raises(ValueError, match="anchor"):
        ps.render_scatter_script(
            mode="volume", mesh_path="/Game/X", count=10, anchor="moon",
        )


def test_pcg_compiles():
    s = ps.render_scatter_script(mode="surface", mesh_path="/Game/X")
    compile(s, "<pcg_test>", "exec")


def test_pcg_handler_unsupported_mode():
    out = asyncio.run(ps.on_pcg_scatter({"mode": "underwater", "mesh_path": "/Game/X"}))
    assert out["error"]["code"] == -32602


# ---------- 16-B structural validation ----------

def test_validation_passes_simple_room():
    spec = bp.BlockoutSpec.from_dict({"rooms": [
        {"width_cm": 600, "depth_cm": 400, "height_cm": 300,
         "door_wall": "north", "door_w": 100, "door_h": 220},
    ]})
    findings = bv.validate_blockout(spec)
    assert bv.passes(findings) is True


def test_validation_flags_door_too_tall():
    spec = bp.BlockoutSpec.from_dict({"rooms": [
        {"width_cm": 600, "depth_cm": 400, "height_cm": 200,
         "door_wall": "north", "door_w": 100, "door_h": 300},
    ]})
    findings = bv.validate_blockout(spec)
    rules = {f.rule for f in findings}
    assert "door_too_tall" in rules
    assert bv.passes(findings) is False


def test_validation_flags_door_too_wide_on_north_wall():
    spec = bp.BlockoutSpec.from_dict({"rooms": [
        {"width_cm": 200, "depth_cm": 600, "height_cm": 300,
         "door_wall": "north", "door_w": 250, "door_h": 220},
    ]})
    findings = bv.validate_blockout(spec)
    rules = {f.rule for f in findings}
    assert "door_too_wide" in rules


def test_validation_flags_stair_above_room():
    spec = bp.BlockoutSpec.from_dict({
        "rooms": [{"width_cm": 600, "depth_cm": 400, "height_cm": 100,
                   "door_wall": "none"}],
        "staircases": [{"steps": 20, "step_w": 120, "step_h": 18, "step_d": 30}],
    })
    findings = bv.validate_blockout(spec)
    rules = {f.rule for f in findings}
    assert "stair_climbs_above_room" in rules
    # warning, not error
    assert bv.passes(findings) is True


# ---------- 16-C spiral stairs + arches ----------

def test_blockout_spec_with_spiral():
    spec = bp.BlockoutSpec.from_dict({
        "rooms": [{"width_cm": 600, "depth_cm": 400, "height_cm": 300,
                   "door_wall": "none"}],
        "spiral_staircases": [
            {"inner_radius_cm": 60, "width_cm": 120, "angle_deg": 360,
             "height_cm": 400, "num_steps": 24},
        ],
    })
    assert len(spec.spiral_staircases) == 1
    assert spec.spiral_staircases[0].num_steps == 24


def test_blockout_spec_with_arch():
    spec = bp.BlockoutSpec.from_dict({
        "rooms": [{"width_cm": 600, "depth_cm": 400, "height_cm": 300,
                   "door_wall": "none"}],
        "arches": [
            {"width_cm": 200, "height_cm": 250, "thickness_cm": 30,
             "wall": "east"},
        ],
    })
    assert len(spec.arches) == 1
    assert spec.arches[0].wall == "east"


def test_blockout_spec_rejects_invalid_arch_wall():
    with pytest.raises(bp.BlockoutValidationError):
        bp.BlockoutSpec.from_dict({
            "rooms": [{"width_cm": 600, "depth_cm": 400, "height_cm": 300,
                       "door_wall": "none"}],
            "arches": [{"wall": "ceiling"}],
        })


def test_blockout_to_dict_includes_new_lists():
    spec = bp.BlockoutSpec.from_dict({
        "rooms": [{"width_cm": 600, "depth_cm": 400, "height_cm": 300,
                   "door_wall": "none"}],
        "spiral_staircases": [{"num_steps": 8}],
        "arches": [{"wall": "north"}],
    })
    d = spec.to_dict()
    assert "spiral_staircases" in d
    assert "arches" in d
    assert len(d["spiral_staircases"]) == 1
    assert len(d["arches"]) == 1


# ---------- 16-D BP review LLM ----------

SMALL_BP = {
    "blueprint_path": "/Game/BP_X",
    "nodes": [
        {"node_id": "n1", "pins": [
            {"name": "Out", "direction": "output", "pin_type": "exec", "links": []},
        ]},
    ],
    "variables": [],
}


def test_bp_review_llm_includes_static_findings():
    out = bplr.render_review_prompt(graph=SMALL_BP)
    assert "## Static analyser findings" in out["user_prompt"]
    assert out["static_findings"]["counts"]["total"] >= 1


def test_bp_review_llm_includes_diff_when_given():
    out = bplr.render_review_prompt(graph=SMALL_BP, diff="@@ -1,2 +1,3 @@\n+new line")
    assert "## Revision-control diff" in out["user_prompt"]
    assert "new line" in out["user_prompt"]


def test_bp_review_llm_rejects_oversized_graph():
    big = {"nodes": [{"node_id": f"n{i}", "pins": []} for i in range(10_000)]}
    with pytest.raises(ValueError, match="exceeds"):
        bplr.render_review_prompt(graph=big)


def test_bp_review_llm_handler_accepts_json_string():
    out = asyncio.run(bplr.on_compose_review({"graph": json.dumps(SMALL_BP)}))
    assert "error" not in out
    assert "system_prompt" in out
    assert "user_prompt" in out


def test_bp_review_llm_handler_bad_json():
    out = asyncio.run(bplr.on_compose_review({"graph": "{not json"}))
    assert out["error"]["code"] == -32602


# ---------- 16-E ControlNet inpaint ----------

def test_inpaint_with_reference_uses_controlnet_template(tmp_path, monkeypatch):
    captured: dict = {}

    async def fake_upload(self, png_bytes, filename, *, subfolder="", overwrite=True):
        return f"remote_{filename}"

    async def fake_run_workflow(self, workflow, download_dir=None):
        captured["workflow"] = workflow
        out = Path(download_dir) / "result.png"
        out.write_bytes(b"out")
        return ComfyUIResult(prompt_id="p", status="completed",
                             output_images=[str(out)], raw_outputs={})

    import base64
    params = {
        "source_image_b64": base64.b64encode(b"src").decode(),
        "mask_b64": base64.b64encode(b"mask").decode(),
        "reference_image_b64": base64.b64encode(b"ref").decode(),
        "prompt": "in the style of the reference",
        "negative_prompt": "",
        "project_saved": str(tmp_path),
    }

    with patch.object(it.ComfyUIClient, "upload_image", new=fake_upload), \
         patch.object(it.ComfyUIClient, "run_workflow", new=fake_run_workflow):
        result = asyncio.run(it.on_inpaint_submit(params, session=None))

    assert "error" not in result, result
    # ControlNet workflow uses node 8 = ControlNetApplyAdvanced
    wf = captured["workflow"]
    class_types = {n["class_type"] for n in wf.values()}
    assert "ControlNetApplyAdvanced" in class_types
    assert "ControlNetLoader" in class_types


def test_inpaint_without_reference_uses_plain_template(tmp_path):
    captured: dict = {}

    async def fake_upload(self, *a, **k): return "x.png"

    async def fake_run_workflow(self, workflow, download_dir=None):
        captured["workflow"] = workflow
        out = Path(download_dir) / "r.png"
        out.write_bytes(b"")
        return ComfyUIResult(prompt_id="p", status="completed",
                             output_images=[str(out)], raw_outputs={})

    import base64
    params = {
        "source_image_b64": base64.b64encode(b"s").decode(),
        "mask_b64": base64.b64encode(b"m").decode(),
        "prompt": "no reference",
        "project_saved": str(tmp_path),
    }
    with patch.object(it.ComfyUIClient, "upload_image", new=fake_upload), \
         patch.object(it.ComfyUIClient, "run_workflow", new=fake_run_workflow):
        asyncio.run(it.on_inpaint_submit(params, session=None))
    class_types = {n["class_type"] for n in captured["workflow"].values()}
    assert "ControlNetApplyAdvanced" not in class_types


# ---------- 16-F engine source RAG ingest ----------

SAMPLE_H = textwrap.dedent('''
    /** Manages timers across the world. */
    UCLASS()
    class CORE_API UFTimerManager : public UObject
    {
        GENERATED_BODY()
    public:
        /** Set a timer that fires after the given delay. */
        UFUNCTION(BlueprintCallable)
        void SetTimer(FTimerHandle& Handle, float DelaySeconds);
    };
''')


def test_chunk_header_extracts_uclass_and_ufunc():
    chunks = si.chunk_header(Path("/fake/Timer.h"), SAMPLE_H)
    kinds = {c.chunk_id.split("::")[1] for c in chunks}
    assert {"uclass", "ufunction"} <= kinds
    bodies = " ".join(c.body for c in chunks)
    assert "SetTimer" in bodies


def test_source_chunk_to_dict_has_n_tokens():
    chunks = si.chunk_header(Path("/x.h"), SAMPLE_H)
    for c in chunks:
        d = c.to_dict()
        assert d["n_tokens"] >= 1


def test_walk_ue_root_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        list(si.walk_ue_root(tmp_path / "no_such_dir"))


def test_ingest_to_jsonl_roundtrip(tmp_path):
    ue_root = tmp_path / "UE_5.6"
    runtime = ue_root / "Engine" / "Source" / "Runtime"
    runtime.mkdir(parents=True)
    (runtime / "Timer.h").write_text(SAMPLE_H)
    out_path = tmp_path / "out.jsonl"
    summary = si.ingest_to_jsonl(
        ue_root=ue_root,
        out_path=out_path,
        subpaths=["Engine/Source/Runtime"],
    )
    assert summary["files_seen"] == 1
    assert summary["chunks_written"] >= 1
    # Each line parses as JSON
    for line in out_path.read_text().splitlines():
        rec = json.loads(line)
        assert "chunk_id" in rec
        assert "body" in rec


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
