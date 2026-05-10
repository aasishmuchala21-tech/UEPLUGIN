"""Phase 9 INPAINT-01 — tests for nyrahost.tools.inpaint_tools.

The handler is exercised end-to-end with a fake ComfyUIClient so the
suite stays hermetic — no real HTTP, no temp ComfyUI server. Five
required cases per PLAN_aura_killers_1wk.md §2.5.
"""
from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from nyrahost.tools import inpaint_tools as it
from nyrahost.external.comfyui_client import (
    ComfyUIAPIError,
    ComfyUIResult,
    ComfyUIWorkflowValidationError,
)


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _params(tmp_path: Path) -> dict:
    return {
        "source_image_b64": _b64(b"\x89PNG\r\n\x1a\n_fake_source"),
        "mask_b64": _b64(b"\x89PNG\r\n\x1a\n_fake_mask"),
        "prompt": "make this person wear sunglasses",
        "negative_prompt": "ugly, low quality",
        "denoise": 0.85,
        "steps": 25,
        "cfg": 7.5,
        "seed": 42,
        "project_saved": str(tmp_path),
    }


# (1) workflow template loads and renders all ${...} placeholders
def test_workflow_renders_all_placeholders():
    template = it._load_workflow_template()
    rendered = it._render_workflow(
        template,
        source_filename="src.png",
        mask_filename="mask.png",
        positive_prompt="hello",
        negative_prompt="bye",
        seed=7,
        steps=20,
        cfg=7.0,
        denoise=0.9,
    )
    # No leftover ${...}
    assert "${" not in json.dumps(rendered), "unrendered placeholder present"
    # Confirm the SDXL inpaint workflow shape
    class_types = {n["class_type"] for n in rendered.values()}
    assert {
        "CheckpointLoaderSimple",
        "LoadImage",
        "LoadImageMask",
        "VAEEncodeForInpaint",
        "KSampler",
        "VAEDecode",
        "SaveImage",
    }.issubset(class_types)


# (2) upload_image is invoked twice (source + mask) with the right shape
def test_upload_image_called_twice_with_correct_shape(tmp_path):
    captured: list[tuple[str, dict]] = []

    async def fake_upload(self, png_bytes, filename, *, subfolder="", overwrite=True):
        captured.append((filename, {"subfolder": subfolder, "overwrite": overwrite}))
        return f"remote_{filename}"

    async def fake_run_workflow(self, workflow, download_dir=None):
        Path(download_dir, "result.png").write_bytes(b"out")
        return ComfyUIResult(
            prompt_id="p", status="completed",
            output_images=[str(Path(download_dir) / "result.png")],
            raw_outputs={},
        )

    with patch.object(it.ComfyUIClient, "upload_image", new=fake_upload), \
         patch.object(it.ComfyUIClient, "run_workflow", new=fake_run_workflow):
        result = asyncio.run(it.on_inpaint_submit(_params(tmp_path), session=None))

    assert "image_path" in result, result
    # Source first, mask second
    assert len(captured) == 2
    assert captured[0][0].endswith("_source.png")
    assert captured[1][0].endswith("_mask.png")
    assert captured[0][1]["subfolder"] == "nyra_inpaint"


# (3) success returns the right JSON-RPC response shape
def test_success_response_shape(tmp_path):
    async def fake_upload(self, *a, **k):
        return "remote_ok.png"

    async def fake_run_workflow(self, workflow, download_dir=None):
        out = Path(download_dir) / "result.png"
        out.write_bytes(b"out")
        return ComfyUIResult(prompt_id="p1", status="completed",
                             output_images=[str(out)], raw_outputs={})

    with patch.object(it.ComfyUIClient, "upload_image", new=fake_upload), \
         patch.object(it.ComfyUIClient, "run_workflow", new=fake_run_workflow):
        result = asyncio.run(it.on_inpaint_submit(_params(tmp_path), session=None))

    assert "job_id" in result
    assert result["image_path"].endswith("result.png")
    assert isinstance(result["all_images"], list)
    assert "error" not in result


# (4) ComfyUI failure maps to -32034 inpaint_failed envelope
def test_comfyui_failure_maps_to_minus32034(tmp_path):
    async def fake_upload(self, *a, **k):
        return "ok.png"

    async def fake_run_workflow(self, workflow, download_dir=None):
        raise ComfyUIAPIError("HTTP 500 from ComfyUI")

    with patch.object(it.ComfyUIClient, "upload_image", new=fake_upload), \
         patch.object(it.ComfyUIClient, "run_workflow", new=fake_run_workflow):
        result = asyncio.run(it.on_inpaint_submit(_params(tmp_path), session=None))

    assert "error" in result
    assert result["error"]["code"] == -32034
    assert result["error"]["message"] == "comfyui_run_failed"


# (5) Invalid base64 is rejected before any disk write or HTTP call
def test_invalid_base64_rejected(tmp_path):
    bad = _params(tmp_path)
    bad["source_image_b64"] = "!!!not-base64!!!"
    # Should NOT call upload_image or run_workflow
    with patch.object(it.ComfyUIClient, "upload_image", new=AsyncMock(side_effect=AssertionError)), \
         patch.object(it.ComfyUIClient, "run_workflow", new=AsyncMock(side_effect=AssertionError)):
        result = asyncio.run(it.on_inpaint_submit(bad, session=None))
    assert "error" in result
    assert result["error"]["code"] == -32602
    assert result["error"]["message"] == "bad_base64"


# Bonus: missing required field returns -32602 missing_field
def test_missing_prompt_rejected(tmp_path):
    bad = _params(tmp_path)
    del bad["prompt"]
    result = asyncio.run(it.on_inpaint_submit(bad, session=None))
    assert result["error"]["code"] == -32602
    assert result["error"]["message"] == "missing_field"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
