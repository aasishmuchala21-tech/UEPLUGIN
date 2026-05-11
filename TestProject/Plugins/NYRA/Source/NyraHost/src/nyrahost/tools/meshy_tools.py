"""nyrahost.tools.meshy_tools — GEN-01 Meshy REST API MCP tools.

Per Plan 05-01:
  - nyra_meshy_image_to_3d: submit image-to-3D job, write pending manifest entry, return job_id
  - nyra_job_status: poll status of any pending job by job_id

Phase 0 gate: not phase0-gated — execute fully.
Threat mitigations: T-05-01 (key never logged), T-05-03 (path traversal blocked in staging.py)
"""
from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

import structlog

from nyrahost.tools.base import NyraTool, NyraToolResult
from nyrahost.external.meshy_client import (
    MeshyClient,
    MeshyAuthError,
    MeshyRateLimitError,
    MeshyAPIError,
    MeshyTimeoutError,
)
from nyrahost.tools.staging import StagingManifest

log = structlog.get_logger("nyrahost.tools.meshy_tools")

__all__ = ["MeshyImageTo3DTool", "JobStatusTool"]


class MeshyImageTo3DTool(NyraTool):
    """Submit a Meshy image-to-3D job and stage the result for UE import.

    Implements the staging manifest pattern: a pending entry is written to
    nyra_pending.json BEFORE the tool returns, so NyraHost crash mid-polling
    does not orphan a job (Pitfall 1 mitigation).

    The polling loop runs in a background task on NyraHost's event loop;
    this method returns immediately with the job_id so the MCP stdio loop
    stays responsive.
    """

    name = "nyra_meshy_image_to_3d"
    description = (
        "Generate a 3D mesh from a reference image using Meshy AI. "
        "Uploads the image, polls until the job completes, downloads the GLB, "
        "and stages it for UE import as UStaticMesh with LODs and collision. "
        "Submitting the same image twice returns the existing job_id "
        "(idempotent, no duplicate imports). "
        "Use nyra_job_status to poll for completion."
    )
    parameters = {
        "type": "object",
        "properties": {
            "image_path": {
                "type": "string",
                "description": (
                    "Absolute path to the reference image on disk (JPG, PNG, WebP). "
                    "Used to derive the input_hash for idempotency."
                ),
            },
            "prompt": {
                "type": "string",
                "description": (
                    "Optional natural-language guidance for mesh generation. "
                    'E.g. "low-poly stylized", "realistic stone texture", "cartoon style".'
                ),
            },
            "task_type": {
                "type": "string",
                "default": "meshy-image-to-3d-reMeshed",
                "description": "Meshy task type. Default: meshy-image-to-3d-reMeshed.",
            },
            "target_folder": {
                "type": "string",
                "default": "/Game/NYRA/Meshes",
                "description": "UE Content Browser destination folder for the imported mesh.",
            },
        },
        "required": ["image_path"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        image_path = params["image_path"]
        task_type = params.get("task_type", "meshy-image-to-3d-reMeshed")
        target_folder = params.get("target_folder", "/Game/NYRA/Meshes")
        prompt = params.get("prompt", "")

        # Validate image exists
        if not Path(image_path).exists():
            return NyraToolResult.err(
                f"[-32030] Image file not found: {image_path}"
            )

        # Check for MESHY_API_KEY
        api_key = os.environ.get("MESHY_API_KEY")
        if not api_key:
            return NyraToolResult.err(
                "[-32031] MESHY_API_KEY not configured. "
                "Set it via: Settings -> External Tools -> Meshy API Key. "
                "Get your key at: https://dashboard.meshy.ai/api"
            )

        manifest = StagingManifest()
        # BL-04: include task_type and prompt in the dedup key so a
        # re-submit with different generation parameters does NOT
        # silently return the prior job's GLB.
        # BL-05: compute_hash validates extension/size/file-type before
        # reading the bytes; the LLM cannot point us at a device path
        # or multi-GB file.
        try:
            input_hash = manifest.compute_hash(
                image_path,
                extra=f"task_type={task_type}|prompt={prompt}",
            )
        except ValueError as e:
            return NyraToolResult.err(f"[-32030] {e}")

        # Idempotency: check for existing job
        existing_id = manifest.find_by_hash(
            tool="meshy",
            operation="image-to-3d",
            input_hash=input_hash,
        )
        if existing_id:
            log.info("meshy_idempotent_dedup", job_id=existing_id, image_path=image_path)
            return NyraToolResult.ok({
                "job_id": existing_id,
                "status": "existing",
                "message": (
                    f"Meshy job already exists for this image. "
                    f"Use nyra_job_status('{existing_id}') to check status."
                ),
                "target_folder": target_folder,
            })

        # Fresh job
        job_id = str(uuid.uuid4())

        # Pitfall 1 mitigation: write pending entry BEFORE returning.
        # BL-04: pass the composed input_hash so dedup re-submits match.
        manifest.add_pending(
            job_id=job_id,
            tool="meshy",
            operation="image-to-3d",
            input_ref=image_path,
            api_response={"task_type": task_type, "prompt": prompt},
            input_hash=input_hash,
        )
        log.info("meshy_pending_job_written", job_id=job_id, image_path=image_path)

        # Start background polling task on NyraHost's event loop.
        # _poll_meshy_and_update_manifest is an async fn. When mocked (e.g. in tests)
        # it may be a regular function — detect and handle accordingly.
        _coro = _poll_meshy_and_update_manifest(
            job_id=job_id,
            image_path=image_path,
            task_type=task_type,
            target_folder=target_folder,
            api_key=api_key,
        )
        try:
            loop = asyncio.get_running_loop()
            if asyncio.iscoroutine(_coro):
                loop.create_task(_coro)
            # else: mock is a sync noop — nothing to schedule
        except RuntimeError:
            # No running event loop (test context) — run synchronously if it's a coroutine
            if asyncio.iscoroutine(_coro):
                asyncio.run(_coro)
            # else: mock is a sync noop — nothing to run

        return NyraToolResult.ok({
            "job_id": job_id,
            "status": "pending",
            "message": (
                f"Meshy job started. Use nyra_job_status('{job_id}') to poll. "
                "The mesh will be auto-imported into UE when complete."
            ),
            "target_folder": target_folder,
        })


async def _poll_meshy_and_update_manifest(
    job_id: str,
    image_path: str,
    task_type: str,
    target_folder: str,
    api_key: str,
) -> None:
    """Background task: poll Meshy and update the manifest entry on completion."""
    manifest = StagingManifest()
    try:
        client = MeshyClient(api_key=api_key)
        # Phase 19-D smart low-poly toggle.
        _low_poly = bool(params.get("low_poly", False))
        _target_polycount = params.get("target_polycount")
        result = await client.image_to_3d(image_path=image_path, low_poly=_low_poly, target_polycount=_target_polycount, task_type=task_type)

        if result.status == "completed" and result.glb_url:
            # Phase 5 WR-01: SSRF defence. The glb_url is supplied by
            # Meshy's API response; if that response is tampered with or
            # the API itself returns a malformed URL, an unchecked GET
            # would let an attacker pivot through NyraHost to localhost
            # or an internal network. Restrict to https + the Meshy CDN
            # domains before issuing the download. The allowlist is
            # narrow on purpose — Meshy moves files between
            # `assets.meshy.ai` and S3-fronted CDNs but always over
            # https on a *.meshy.ai or *.amazonaws.com host.
            from urllib.parse import urlparse
            parsed = urlparse(result.glb_url)
            host = (parsed.hostname or "").lower()
            scheme_ok = parsed.scheme == "https"
            host_ok = (
                host.endswith(".meshy.ai")
                or host == "meshy.ai"
                or host.endswith(".amazonaws.com")
            )
            if not (scheme_ok and host_ok):
                manifest.update_job(
                    job_id=job_id,
                    ue_import_status="failed",
                    error_message=(
                        "Refused to download GLB from untrusted host "
                        f"{host or '?'}; expected https://*.meshy.ai or "
                        "https://*.amazonaws.com."
                    ),
                )
                log.warning(
                    "meshy_glb_url_rejected_ssrf",
                    job_id=job_id,
                    host=host,
                    scheme=parsed.scheme,
                )
                return NyraToolResult.ok({
                    "job_id": job_id,
                    "task_id": result.task_id,
                    "status": "failed",
                    "error": "untrusted_glb_host",
                })

            # Download GLB to staging directory
            staging_root = manifest._root
            glb_path = staging_root / f"{job_id}.glb"

            import httpx
            async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as http_client:
                resp = await http_client.get(result.glb_url)
                resp.raise_for_status()
                glb_path.write_bytes(resp.read())

            manifest.update_job(
                job_id=job_id,
                api_response=result.raw_response,
                downloaded_path=str(glb_path),
                ue_import_status="pending",  # UE import bridge reads this
            )
            log.info("meshy_glb_downloaded", job_id=job_id, glb_path=str(glb_path))

        else:
            manifest.update_job(
                job_id=job_id,
                api_response=result.raw_response,
                ue_import_status="failed",
                error_message=result.error_message or f"Meshy task status: {result.status}",
            )
            log.warning("meshy_job_failed", job_id=job_id, status=result.status)

    except MeshyAuthError as e:
        manifest.update_job(job_id=job_id, ue_import_status="failed", error_message=str(e))
        log.error("meshy_auth_error", job_id=job_id)
    except MeshyRateLimitError as e:
        manifest.update_job(job_id=job_id, ue_import_status="failed", error_message=str(e))
        log.error("meshy_rate_limit", job_id=job_id, retry_after=e.retry_after)
    except MeshyAPIError as e:
        manifest.update_job(job_id=job_id, ue_import_status="failed", error_message=str(e))
        log.error("meshy_api_error", job_id=job_id)
    except MeshyTimeoutError as e:
        manifest.update_job(job_id=job_id, ue_import_status="timeout", error_message=str(e))
        log.warning("meshy_timeout", job_id=job_id)
    except Exception as e:
        manifest.update_job(job_id=job_id, ue_import_status="failed", error_message=str(e))
        log.exception("meshy_unexpected_error", job_id=job_id)


class JobStatusTool(NyraTool):
    """Poll the status of any NYRA staging job by job_id.

    Works for Meshy, ComfyUI, and computer-use jobs — all share the same
    staging manifest.
    """

    name = "nyra_job_status"
    description = (
        "Poll the status of a NYRA staging job by its job_id. "
        "Works for Meshy, ComfyUI, and computer-use jobs. "
        "Returns the current import status and downloaded asset path if available."
    )
    parameters = {
        "type": "object",
        "properties": {
            "job_id": {
                "type": "string",
                "description": (
                    "The job_id returned by nyra_meshy_image_to_3d or "
                    "nyra_comfyui_run_workflow"
                ),
            },
        },
        "required": ["job_id"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        job_id = params["job_id"]
        manifest = StagingManifest()
        job = manifest.get_job(job_id)

        if job is None:
            return NyraToolResult.err(f"[-32032] Job not found: {job_id}")

        return NyraToolResult.ok({
            "job_id": job.id,
            "tool": job.tool,
            "operation": job.operation,
            "input_ref": job.input_ref,
            "ue_import_status": job.ue_import_status,
            "downloaded_path": job.downloaded_path,
            "ue_asset_path": job.ue_asset_path,
            "error_message": job.error_message,
            "created_at": job.created_at,
        })