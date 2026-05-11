"""nyra_inpaint_submit MCP tool — Phase 9 INPAINT-01.

Aura-parity: in-painting modal with mask + prompt + (deferred) reference
panel. v0 ships SDXL inpaint via the local ComfyUI server; ControlNet
inpaint and IPAdapter reference-guided edits land in v1.1 (see
.planning/phases/09-aura-killers/09-CONTEXT.md).

Threat mitigations:
  T-09-01: All disk writes go through StagingManifest._validate_path so a
           caller-supplied prompt cannot path-traverse out of
           <ProjectDir>/Saved/NYRA/inpaint/.
  T-09-02: Source/mask PNGs are uploaded via ComfyUI /upload/image
           (the /upload/mask route does NOT exist; verified).
  T-09-03: Workflow JSON is validated against /object_info before
           submission via ComfyUIClient.run_workflow's existing
           validate_workflow gate (T-05-02 reuse).
"""
from __future__ import annotations

import base64
import binascii
import json
import os
import string
import uuid
from pathlib import Path
from typing import Final, Optional

import structlog

from nyrahost.external.comfyui_client import (
    ComfyUIAPIError,
    ComfyUIClient,
    ComfyUIWorkflowValidationError,
)
from nyrahost.tools.staging import PathTraversalError, StagingManifest

log = structlog.get_logger("nyrahost.tools.inpaint")

DEFAULT_CKPT: Final[str] = "juggernautXL_inpaint.safetensors"
WORKFLOW_TEMPLATE_PATH: Final[Path] = (
    Path(__file__).resolve().parent.parent
    / "external"
    / "comfyui_workflows"
    / "inpaint_sdxl.json"
)
CONTROLNET_TEMPLATE_PATH: Final[Path] = (
    Path(__file__).resolve().parent.parent
    / "external"
    / "comfyui_workflows"
    / "inpaint_sdxl_controlnet.json"
)

DEFAULT_CONTROLNET_NAME: Final[str] = "control_v11p_sd15_inpaint.pth"
DEFAULT_CONTROLNET_STRENGTH: Final[float] = 0.7

# JSON-RPC error codes (mirror docs/ERROR_CODES.md)
ERR_BAD_INPUT: Final[int] = -32602
ERR_INPAINT_FAILED: Final[int] = -32034


def _load_workflow_template() -> str:
    """Read the SDXL inpaint workflow template from disk."""
    return WORKFLOW_TEMPLATE_PATH.read_text(encoding="utf-8")


def _render_workflow(
    template_str: str,
    *,
    source_filename: str,
    mask_filename: str,
    positive_prompt: str,
    negative_prompt: str,
    seed: int,
    steps: int,
    cfg: float,
    denoise: float,
    sdxl_inpaint_ckpt: str = DEFAULT_CKPT,
    reference_filename: str | None = None,
    controlnet_name: str = DEFAULT_CONTROLNET_NAME,
    controlnet_strength: float = DEFAULT_CONTROLNET_STRENGTH,
) -> dict:
    """Substitute ${PLACEHOLDER}s and parse to dict.

    Uses string.Template so a stray ``$`` in a user prompt does not break
    parsing; substitute on a JSON-encoded version of the prompt strings
    so quotes inside them don't corrupt the surrounding JSON.
    """
    placeholders = {
        "SDXL_INPAINT_CKPT":   sdxl_inpaint_ckpt,
        "SOURCE_FILENAME":     source_filename,
        "MASK_FILENAME":       mask_filename,
        "POSITIVE_PROMPT":     _json_escape(positive_prompt),
        "NEGATIVE_PROMPT":     _json_escape(negative_prompt),
        "SEED":                str(seed),
        "STEPS":               str(steps),
        "CFG":                 str(cfg),
        "DENOISE":             str(denoise),
    }
    if reference_filename is not None:
        placeholders["REFERENCE_FILENAME"] = reference_filename
        placeholders["CONTROLNET_NAME"]    = controlnet_name
        placeholders["CONTROLNET_STRENGTH"] = str(controlnet_strength)
    sub = string.Template(template_str).substitute(**placeholders)
    return json.loads(sub)


def _json_escape(s: str) -> str:
    """Strip the surrounding quotes from json.dumps for inline substitution."""
    return json.dumps(s)[1:-1]


def _decode_b64(b64: str) -> bytes:
    try:
        return base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"invalid base64 payload: {exc}") from exc


async def on_inpaint_submit(
    params: dict,
    session,  # SessionState — typed via duck typing to avoid circular import
    ws=None,  # unused for Phase 9 v0; reserved for streaming progress
) -> dict:
    """Handle ``inpaint/submit`` JSON-RPC requests.

    params:
      source_image_b64 (str, required)
      mask_b64         (str, required)
      prompt           (str, required)
      negative_prompt  (str, optional, default "")
      denoise          (float, default 0.85)
      steps            (int, default 30)
      cfg              (float, default 7.0)
      seed             (int, default -1; -1 means CryptoRandom)
      project_saved    (str, optional; falls back to env NYRA_PROJECT_SAVED)
      comfy_host       (str, optional, default 127.0.0.1)
      comfy_port       (int, optional, default 8188)
    """
    try:
        source_b64 = _require_str(params, "source_image_b64")
        mask_b64 = _require_str(params, "mask_b64")
        prompt = _require_str(params, "prompt")
    except KeyError as exc:
        return _err(ERR_BAD_INPUT, "missing_field", str(exc))
    negative = params.get("negative_prompt", "") or ""
    denoise = float(params.get("denoise", 0.85))
    steps = int(params.get("steps", 30))
    cfg = float(params.get("cfg", 7.0))
    seed = int(params.get("seed", -1))
    if seed < 0:
        seed = int.from_bytes(os.urandom(4), "big") & 0x7FFFFFFF

    project_saved = (
        params.get("project_saved")
        or os.environ.get("NYRA_PROJECT_SAVED")
        or "."
    )
    staging_root = Path(project_saved) / "NYRA" / "inpaint"
    try:
        manifest = StagingManifest(staging_root=staging_root)
    except OSError as exc:
        return _err(ERR_INPAINT_FAILED, "staging_init_failed", str(exc))

    job_id = str(uuid.uuid4())
    job_dir = staging_root / job_id
    try:
        job_dir.mkdir(parents=True, exist_ok=True)
        # T-09-01: any caller-supplied path component cannot escape job_dir
        # because we never join the user's prompt or filenames into the path;
        # we only use job_id (UUID) as the dir component.
        manifest._validate_path(str(job_dir))  # noqa: SLF001 - intentional reuse
    except (OSError, PathTraversalError) as exc:
        return _err(ERR_INPAINT_FAILED, "staging_path_invalid", str(exc))

    reference_b64 = params.get("reference_image_b64")
    reference_bytes: bytes | None = None
    try:
        source_bytes = _decode_b64(source_b64)
        mask_bytes = _decode_b64(mask_b64)
        if isinstance(reference_b64, str) and reference_b64:
            reference_bytes = _decode_b64(reference_b64)
    except ValueError as exc:
        return _err(ERR_BAD_INPUT, "bad_base64", str(exc))

    source_path = job_dir / "source.png"
    mask_path = job_dir / "mask.png"
    source_path.write_bytes(source_bytes)
    mask_path.write_bytes(mask_bytes)

    host = params.get("comfy_host", "127.0.0.1")
    port = int(params.get("comfy_port", 8188))
    client = ComfyUIClient(host=host, port=port)

    reference_remote: str | None = None
    try:
        source_remote = await client.upload_image(
            source_bytes, f"{job_id}_source.png", subfolder="nyra_inpaint",
        )
        mask_remote = await client.upload_image(
            mask_bytes, f"{job_id}_mask.png", subfolder="nyra_inpaint",
        )
        if reference_bytes is not None:
            reference_remote = await client.upload_image(
                reference_bytes, f"{job_id}_ref.png", subfolder="nyra_inpaint",
            )
    except (ComfyUIAPIError, OSError) as exc:
        return _err(ERR_INPAINT_FAILED, "comfyui_upload_failed", str(exc))

    use_controlnet = reference_remote is not None
    try:
        template_path = CONTROLNET_TEMPLATE_PATH if use_controlnet else WORKFLOW_TEMPLATE_PATH
        template = template_path.read_text(encoding="utf-8")
    except OSError as exc:
        return _err(ERR_INPAINT_FAILED, "template_missing", str(exc))

    try:
        workflow = _render_workflow(
            template,
            source_filename=source_remote,
            mask_filename=mask_remote,
            positive_prompt=prompt,
            negative_prompt=negative,
            seed=seed,
            steps=steps,
            cfg=cfg,
            denoise=denoise,
            reference_filename=reference_remote,
            controlnet_name=str(params.get("controlnet_name", DEFAULT_CONTROLNET_NAME)),
            controlnet_strength=float(params.get("controlnet_strength", DEFAULT_CONTROLNET_STRENGTH)),
        )
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        return _err(ERR_INPAINT_FAILED, "workflow_render_failed", str(exc))

    try:
        result = await client.run_workflow(
            workflow, download_dir=str(job_dir),
        )
    except ComfyUIWorkflowValidationError as exc:
        return _err(
            ERR_INPAINT_FAILED, "workflow_validation_failed", str(exc),
            remediation=(
                "ComfyUI rejected the workflow. Confirm the SDXL inpaint "
                "checkpoint is installed under "
                "ComfyUI/models/checkpoints/, then retry."
            ),
        )
    except (ComfyUIAPIError, TimeoutError) as exc:
        return _err(ERR_INPAINT_FAILED, "comfyui_run_failed", str(exc))

    if not result.output_images:
        return _err(
            ERR_INPAINT_FAILED, "no_output",
            "ComfyUI returned a result with no output images.",
        )

    log.info("inpaint_done", job_id=job_id, output=result.output_images[0])
    return {
        "job_id": job_id,
        "image_path": result.output_images[0],
        "all_images": result.output_images,
    }


def _require_str(params: dict, key: str) -> str:
    if key not in params or not isinstance(params[key], str) or not params[key]:
        raise KeyError(key)
    return params[key]


def _err(
    code: int,
    message: str,
    detail: str = "",
    *,
    remediation: Optional[str] = None,
) -> dict:
    data: dict = {}
    if detail:
        data["detail"] = detail
    if remediation:
        data["remediation"] = remediation
    out: dict = {"error": {"code": code, "message": message}}
    if data:
        out["error"]["data"] = data
    return out


__all__ = [
    "on_inpaint_submit",
    "_render_workflow",
    "_load_workflow_template",
    "_decode_b64",
    "WORKFLOW_TEMPLATE_PATH",
    "DEFAULT_CKPT",
    "ERR_BAD_INPUT",
    "ERR_INPAINT_FAILED",
]
