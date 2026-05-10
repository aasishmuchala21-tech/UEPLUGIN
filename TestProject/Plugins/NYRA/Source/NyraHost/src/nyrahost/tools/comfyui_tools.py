"""nyrahost.tools.comfyui_tools — GEN-02 ComfyUI HTTP API MCP tools.

Per Plan 05-02:
  - nyra_comfyui_run_workflow: submit ComfyUI workflow, write pending manifest entry, return job_id
  - nyra_comfyui_get_node_info: probe available node types from GET /object_info

Threat mitigations: T-05-02 (workflow JSON validated against object_info before submit),
  T-05-03 (path traversal blocked in staging.py), T-05-04 (error messages include setup instructions).
"""
from __future__ import annotations

import asyncio
import json as _json
import uuid
from pathlib import Path
from typing import Optional

import structlog

from nyrahost.tools.base import NyraTool, NyraToolResult, run_async_safely
from nyrahost.external.comfyui_client import (
    ComfyUIClient,
    ComfyUIConnectionError,
    ComfyUIAPIError,
    ComfyUIWorkflowValidationError,
)
from nyrahost.tools.staging import StagingManifest

log = structlog.get_logger("nyrahost.tools.comfyui_tools")

__all__ = ["ComfyUIRunWorkflowTool", "ComfyUIGetNodeInfoTool"]


class ComfyUIRunWorkflowTool(NyraTool):
    """Run a ComfyUI image generation workflow and stage results for UE import.

    Implements the staging manifest pattern: a pending entry is written to
    nyra_pending.json BEFORE the tool returns (Pitfall 1 mitigation).

    The workflow JSON is validated against GET /object_info before submission
    (T-05-02 mitigation).

    The polling loop runs in a background task on NyraHost's event loop;
    this method returns immediately with the job_id so the MCP stdio loop
    stays responsive.
    """

    name = "nyra_comfyui_run_workflow"
    description = (
        "Run a ComfyUI image generation workflow and stage results for UE import. "
        "Pass a workflow exported from ComfyUI in API format (JSON). "
        "The workflow is validated against the server's node registry before submission. "
        "Results are auto-imported as UTexture2D when complete. "
        "Use nyra_job_status to poll for completion."
    )
    parameters = {
        "type": "object",
        "properties": {
            "workflow_json": {
                "type": "object",
                "description": (
                    "ComfyUI workflow in API JSON format (export from ComfyUI UI "
                    "using the 'API' button). Must only contain node types that "
                    "are installed in the ComfyUI instance."
                ),
            },
            "input_image_asset_path": {
                "type": "string",
                "description": (
                    "Optional UE asset path of a UTexture2D to inject as input "
                    "to the workflow."
                ),
            },
            "target_folder": {
                "type": "string",
                "default": "/Game/NYRA/Textures",
                "description": "UE Content Browser destination folder for generated textures.",
            },
        },
        "required": ["workflow_json"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        workflow_json = params.get("workflow_json", {})
        target_folder = params.get("target_folder", "/Game/NYRA/Textures")
        input_image_asset_path = params.get("input_image_asset_path")

        # Discover ComfyUI server (probe 8188, 8189, 8190)
        try:
            # BL-06: route through run_async_safely so this works whether
            # invoked from a sync test or from NyraHost's async dispatcher.
            client = run_async_safely(ComfyUIClient.discover())
        except ComfyUIConnectionError as e:
            return NyraToolResult.err(
                f"[-32040] ComfyUI server not found. {str(e)}\n"
                "Start ComfyUI with API enabled: python main.py --listen 127.0.0.1 --port 8188"
            )

        manifest = StagingManifest()

        # BL-07: ComfyUI was minting a fresh UUID per call with no dedup,
        # so an agent retry on transient error burned the user's GPU on
        # duplicate workflows. Compose the idempotency key from the
        # canonical workflow string + target_folder + input_image so
        # distinct generations are not falsely deduped, identical re-
        # submits return the prior job_id.
        workflow_str = _json.dumps(workflow_json, sort_keys=True)
        try:
            input_hash = manifest.compute_hash(
                workflow_str,
                extra=f"target_folder={target_folder}|input_image={input_image_asset_path or ''}",
            )
        except ValueError as e:
            return NyraToolResult.err(f"[-32030] {e}")

        existing_id = manifest.find_by_hash(
            tool="comfyui",
            operation="run_workflow",
            input_hash=input_hash,
        )
        if existing_id:
            log.info("comfyui_idempotent_dedup", job_id=existing_id)
            return NyraToolResult.ok({
                "job_id": existing_id,
                "status": "existing",
                "message": (
                    f"ComfyUI job already exists for this workflow. "
                    f"Use nyra_job_status('{existing_id}') to check status."
                ),
                "target_folder": target_folder,
            })

        job_id = str(uuid.uuid4())

        # Pitfall 1 mitigation: write pending entry BEFORE returning.
        # BL-07: pass the composed input_hash so dedup re-submits match.
        manifest.add_pending(
            job_id=job_id,
            tool="comfyui",
            operation="run_workflow",
            input_ref=workflow_str,
            api_response={
                "target_folder": target_folder,
                "has_input_image": bool(input_image_asset_path),
            },
            input_hash=input_hash,
        )
        log.info("comfyui_pending_job_written", job_id=job_id)

        # Start background polling task
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                _poll_comfyui_and_update_manifest(
                    job_id=job_id,
                    workflow_json=workflow_json,
                    input_image_asset_path=input_image_asset_path,
                    target_folder=target_folder,
                    client=client,
                )
            )
        except RuntimeError:
            # No running event loop in test context — run synchronously via
            # the safe helper (BL-06).
            run_async_safely(
                _poll_comfyui_and_update_manifest(
                    job_id=job_id,
                    workflow_json=workflow_json,
                    input_image_asset_path=input_image_asset_path,
                    target_folder=target_folder,
                    client=client,
                )
            )

        return NyraToolResult.ok({
            "job_id": job_id,
            "status": "pending",
            "message": (
                f"ComfyUI workflow queued. Use nyra_job_status('{job_id}') to poll. "
                f"Results auto-imported to {target_folder} when complete."
            ),
            "target_folder": target_folder,
        })


async def _poll_comfyui_and_update_manifest(
    job_id: str,
    workflow_json: dict,
    input_image_asset_path: Optional[str],
    target_folder: str,
    client: ComfyUIClient,
) -> None:
    """Background task: run ComfyUI workflow and update manifest on completion."""
    manifest = StagingManifest()
    staging_root = Path(manifest._root)
    staging_root.mkdir(parents=True, exist_ok=True)

    try:
        result = await client.run_workflow(
            workflow=workflow_json,
            download_dir=str(staging_root),
        )

        manifest.update_job(
            job_id=job_id,
            api_response={"prompt_id": result.prompt_id, "outputs": result.raw_outputs},
            downloaded_path=_json.dumps(result.output_images),
            ue_import_status="pending",
        )
        log.info(
            "comfyui_workflow_completed",
            job_id=job_id,
            output_count=len(result.output_images),
        )

    except ComfyUIWorkflowValidationError as e:
        manifest.update_job(job_id=job_id, ue_import_status="failed", error_message=str(e))
        log.error("comfyui_workflow_validation_failed", job_id=job_id)
    except ComfyUIAPIError as e:
        manifest.update_job(job_id=job_id, ue_import_status="failed", error_message=str(e))
        log.error("comfyui_api_error", job_id=job_id)
    except TimeoutError as e:
        manifest.update_job(job_id=job_id, ue_import_status="timeout", error_message=str(e))
        log.warning("comfyui_timeout", job_id=job_id)
    except Exception as e:
        manifest.update_job(job_id=job_id, ue_import_status="failed", error_message=str(e))
        log.exception("comfyui_unexpected_error", job_id=job_id)


class ComfyUIGetNodeInfoTool(NyraTool):
    """Probe the ComfyUI server's available node types.

    Use this to discover what custom nodes are installed and validate
    workflows before submission.
    """

    name = "nyra_comfyui_get_node_info"
    description = (
        "Probe the ComfyUI server's available node types and their input/output schemas. "
        "Use this to validate a workflow before calling nyra_comfyui_run_workflow, "
        "or to discover what custom nodes are installed on the ComfyUI instance."
    )
    parameters = {
        "type": "object",
        "properties": {
            "class_type": {
                "type": "string",
                "description": (
                    "Optional: filter to a specific node type. "
                    "If omitted, returns all node types."
                ),
            },
        },
        "required": [],
    }

    def execute(self, params: dict) -> NyraToolResult:
        try:
            # BL-06: route through run_async_safely so this works whether
            # invoked from a sync test or from NyraHost's async dispatcher.
            client = run_async_safely(ComfyUIClient.discover())
        except ComfyUIConnectionError as e:
            return NyraToolResult.err(
                f"[-32040] ComfyUI server not found. {str(e)}\n"
                "Start ComfyUI with API enabled: python main.py --listen 127.0.0.1 --port 8188"
            )

        try:
            # BL-06
            node_info = run_async_safely(client.get_node_info())
        except ComfyUIAPIError as e:
            return NyraToolResult.err(f"[-32041] ComfyUI API error: {str(e)}")

        class_type_filter = params.get("class_type")
        if class_type_filter:
            if class_type_filter in node_info:
                return NyraToolResult.ok({
                    "class_type": class_type_filter,
                    **node_info[class_type_filter],
                })
            else:
                available = list(node_info.keys())[:10]
                return NyraToolResult.err(
                    f"[-32042] Node type '{class_type_filter}' not found. "
                    f"Available: {available}... (total: {len(node_info)})"
                )

        return NyraToolResult.ok({
            "node_count": len(node_info),
            "node_types": list(node_info.keys()),
            "note": (
                "Full schema available per node type via "
                "nyra_comfyui_get_node_info(class_type='...')"
            ),
        })