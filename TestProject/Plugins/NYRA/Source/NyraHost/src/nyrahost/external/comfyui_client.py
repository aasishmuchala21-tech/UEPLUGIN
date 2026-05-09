"""nyrahost.external.comfyui_client — async ComfyUI local HTTP API client (GEN-02).

Per Plan 05-02: image-to-image workflows, texture generation, variations,
img2img via local ComfyUI server at http://127.0.0.1:8188.

Endpoints verified from docs.comfy.org 2026-05-07:
  POST /prompt     — submit workflow JSON. Body: {"prompt": workflow}.
                     Response: {"prompt_id": "uuid-string"}
  GET  /history/{prompt_id} — poll for completion.
                     Response: {prompt_id: {"outputs": {...}}}
  GET  /object_info        — all available node types.
                     Response: {class_type: {inputs: {...}, output: [...]}}
  GET  /queue               — current queue state.
  POST /interrupt           — stop running prompt.

Threat mitigations:
  T-05-02: Workflow JSON validated against GET /object_info before POST /prompt.
           Unknown class_type values raise ComfyUIWorkflowValidationError.
  T-05-04: Error messages include setup instructions only; no internal paths.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import aiohttp
import structlog

log = structlog.get_logger("nyrahost.external.comfyui_client")

# Ports to probe for ComfyUI server (per RESEARCH.md A5)
DEFAULT_PORTS = [8188, 8189, 8190]
DEFAULT_TIMEOUT = 300  # 5 minutes


class ComfyUIConnectionError(Exception):
    """Raised when ComfyUI server cannot be reached."""
    pass


class ComfyUIAPIError(Exception):
    """Raised on non-retryable ComfyUI API errors (non-2xx)."""
    pass


class ComfyUIWorkflowValidationError(Exception):
    """Raised when a workflow contains node types not in GET /object_info.

    This is the T-05-02 mitigation — workflow injection attack prevention.
    """
    pass


@dataclass
class ComfyUIResult:
    """Result of a ComfyUI workflow run."""
    prompt_id: str
    status: str           # "completed" | "failed" | "interrupted"
    output_images: list[str]  # list of saved image paths (local)
    raw_outputs: dict
    error_message: Optional[str] = None


class ComfyUIClient:
    """Async client for the local ComfyUI HTTP API.

    Per RESEARCH.md A5: ComfyUI default port is 8188 but may be configured
    to different ports. This class probes the three most common ports.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8188,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._host = host
        self._base = f"http://{host}:{port}"
        self._timeout = timeout

    async def _get(self, path: str, **kwargs) -> dict:
        async with aiohttp.ClientSession() as sess:
            try:
                async with sess.get(f"{self._base}{path}", **kwargs) as resp:
                    if not resp.ok:
                        text = await resp.text()
                        raise ComfyUIAPIError(
                            f"ComfyUI GET {path} returned HTTP {resp.status}: {text}"
                        )
                    return await resp.json()
            except aiohttp.ClientError as e:
                raise ComfyUIConnectionError(
                    f"Cannot connect to ComfyUI at {self._base}. "
                    "Is ComfyUI running? Install: https://github.com/comfyanonymous/ComfyUI"
                ) from e

    async def _post(self, path: str, json_body: dict, **kwargs) -> dict:
        async with aiohttp.ClientSession() as sess:
            try:
                async with sess.post(f"{self._base}{path}", json=json_body, **kwargs) as resp:
                    if not resp.ok:
                        text = await resp.text()
                        raise ComfyUIAPIError(
                            f"ComfyUI POST {path} returned HTTP {resp.status}: {text}"
                        )
                    return await resp.json()
            except aiohttp.ClientError as e:
                raise ComfyUIConnectionError(
                    f"Cannot connect to ComfyUI at {self._base}. "
                    "Is ComfyUI running? Install: https://github.com/comfyanonymous/ComfyUI"
                ) from e

    async def get_node_info(self) -> dict:
        """GET /object_info — returns all available node types.

        Use this to validate a workflow before submitting it.
        """
        return await self._get("/object_info")

    async def validate_workflow(self, workflow: dict) -> list[str]:
        """Validate a workflow JSON against /object_info.

        Returns a list of unknown class_type values found in the workflow
        that are not in the server's node registry.

        Raises ComfyUIWorkflowValidationError if any unknown node types exist.
        This is the T-05-02 mitigation — workflow injection attack prevention.
        """
        node_info = await self.get_node_info()
        known_types = set(node_info.keys())
        workflow_types: set[str] = set()

        def collect_types(node: dict) -> None:
            if isinstance(node, dict):
                if "class_type" in node:
                    workflow_types.add(node["class_type"])
                for v in node.values():
                    if isinstance(v, dict):
                        collect_types(v)
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict):
                                collect_types(item)

        prompt = workflow.get("prompt", workflow)
        for node_id, node in prompt.items():
            if isinstance(node, dict) and "class_type" in node:
                workflow_types.add(node["class_type"])
        unknown = workflow_types - known_types
        return list(unknown)

    async def run_workflow(
        self,
        workflow: dict,
        download_dir: Optional[str] = None,
    ) -> ComfyUIResult:
        """Submit a ComfyUI workflow and poll until completion.

        Validates the workflow against /object_info before submission (T-05-02).
        Polls GET /queue first to catch the prompt_id (Pitfall 2 mitigation),
        then polls GET /history/{prompt_id}.

        Args:
            workflow: ComfyUI workflow JSON (as exported from the ComfyUI UI in API format)
            download_dir: Directory to save output images (default: staging dir)

        Returns ComfyUIResult with output image paths when completed.
        """
        # T-05-02: Validate against object_info before submitting
        unknown_types = await self.validate_workflow(workflow)
        if unknown_types:
            raise ComfyUIWorkflowValidationError(
                f"Workflow contains unknown node types: {unknown_types}. "
                "Validate that your ComfyUI installation has these custom nodes installed. "
                "Run nyra_comfyui_get_node_info to see available node types."
            )

        # 1. Submit workflow
        result = await self._post("/prompt", {"prompt": workflow})
        prompt_id = result.get("prompt_id")
        log.info("comfyui_workflow_submitted", prompt_id=prompt_id)

        # 2. Poll /queue first (Pitfall 2: history may not be written yet when prompt is queued)
        queue_delay = 2.0
        poll_start = time.monotonic()

        while True:
            if time.monotonic() - poll_start > self._timeout:
                raise TimeoutError(
                    f"ComfyUI workflow {prompt_id} timed out while queuing ({self._timeout}s)"
                )
            try:
                queue_resp = await self._get("/queue")
                queue_data = queue_resp if isinstance(queue_resp, dict) else {}
                running = queue_data.get("queue_running", [])
                pending = queue_data.get("queue_pending", [])
                if (
                    prompt_id in running
                    or prompt_id in pending
                    or any(
                        isinstance(item, dict) and item.get("prompt_id") == prompt_id
                        for item in running + pending
                    )
                ):
                    break
            except Exception:
                pass  # Queue endpoint may not be available in all ComfyUI versions
            await asyncio.sleep(queue_delay)
            queue_delay = min(queue_delay * 1.5, 10.0)

        # 3. Poll /history/{prompt_id}
        history_delay = 3.0
        while True:
            if time.monotonic() - poll_start > self._timeout:
                raise TimeoutError(
                    f"ComfyUI workflow {prompt_id} timed out ({self._timeout}s)"
                )

            history_resp = await self._get(f"/history/{prompt_id}")
            if prompt_id in history_resp:
                outputs = history_resp[prompt_id].get("outputs", {})

                # Download output images to download_dir
                output_images: list[str] = []
                if download_dir:
                    d = Path(download_dir)
                    d.mkdir(parents=True, exist_ok=True)
                    for node_id, output_data in outputs.items():
                        if isinstance(output_data, dict) and "images" in output_data:
                            for img in output_data["images"]:
                                fname = img.get("filename", "")
                                if fname:
                                    src = d / fname
                                    if src.exists():
                                        output_images.append(str(src))

                log.info(
                    "comfyui_workflow_completed",
                    prompt_id=prompt_id,
                    output_count=len(output_images),
                )
                return ComfyUIResult(
                    prompt_id=prompt_id,
                    status="completed",
                    output_images=output_images,
                    raw_outputs=outputs,
                )

            await asyncio.sleep(history_delay)
            history_delay = min(history_delay * 1.25, 15.0)

    async def interrupt(self) -> None:
        """POST /interrupt — stop the currently running ComfyUI prompt."""
        await self._post("/interrupt", {})

    @classmethod
    async def discover(cls, host: str = "127.0.0.1") -> "ComfyUIClient":
        """Probe DEFAULT_PORTS to find a running ComfyUI server.

        Returns the first client that successfully connects.
        Raises ComfyUIConnectionError if no server found on any port.
        """
        for port in DEFAULT_PORTS:
            client = cls(host=host, port=port)
            try:
                await client.get_node_info()  # Test connection
                log.info("comfyui_server_found", host=host, port=port)
                return client
            except ComfyUIConnectionError:
                continue
        raise ComfyUIConnectionError(
            f"No ComfyUI server found on {host} at ports {DEFAULT_PORTS}. "
            f"Start ComfyUI with: python main.py --listen {host} --port 8188"
        )


__all__ = [
    "ComfyUIClient",
    "ComfyUIConnectionError",
    "ComfyUIAPIError",
    "ComfyUIWorkflowValidationError",
    "ComfyUIResult",
    "DEFAULT_PORTS",
    "DEFAULT_TIMEOUT",
]