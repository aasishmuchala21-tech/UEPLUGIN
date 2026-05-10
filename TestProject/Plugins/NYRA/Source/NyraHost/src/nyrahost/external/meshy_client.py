"""nyrahost.external.meshy_client — Async Meshy REST API client (GEN-01).

Per Plan 05-01:
  - image_to_3d: submit task + exponential-backoff polling
  - Auth via Bearer token; key never logged (T-05-01)
  - Raises MeshyAuthError / MeshyRateLimitError / MeshyAPIError / MeshyTimeoutError

Threat mitigations:
  T-05-01: API key in Authorization header only; error messages never include key value
  T-05-03: Path validation done in StagingManifest._validate_path (not here)
"""
from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx
import structlog

log = structlog.get_logger("nyrahost.external.meshy_client")

MESHY_BASE_URL = "https://meshy.ai/api/v1"
MESHY_RIGGING_URL = "https://api.meshy.ai/openapi/v1/rigging"   # Phase 9 RIG-01
DEFAULT_TIMEOUT = 600  # 10 minutes


class MeshyAuthError(Exception):
    """Raised when the Meshy API key is invalid or missing."""
    pass


class MeshyRateLimitError(Exception):
    """Raised when Meshy rate limit is hit (HTTP 429)."""
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class MeshyAPIError(Exception):
    """Raised on non-retryable Meshy API errors (non-401, non-429)."""
    pass


class MeshyTimeoutError(Exception):
    """Raised when a Meshy job exceeds the configured timeout."""
    pass


@dataclass
class MeshyTaskResult:
    """Result of a Meshy task poll."""
    task_id: str
    status: str           # "pending" | "in_progress" | "completed" | "failed" | "cancelled"
    glb_url: Optional[str] = None
    error_message: Optional[str] = None
    raw_response: Optional[dict] = None


class MeshyClient:
    """Async Meshy REST client — image-to-3D with exponential-backoff polling."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._api_key = api_key or os.environ.get("MESHY_API_KEY")
        if not self._api_key:
            raise ValueError(
                "MESHY_API_KEY not set. Set the environment variable or pass api_key."
            )
        self._base_url = base_url or os.environ.get("MESHY_API_BASE_URL", MESHY_BASE_URL)
        self._timeout = timeout

    def _headers(self) -> dict:
        """T-05-01: Bearer token in header, not query param; never log the key."""
        return {"Authorization": f"Bearer {self._api_key}"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        client: httpx.AsyncClient,
        **kwargs,
    ) -> httpx.Response:
        url = f"{self._base_url}{path}"
        resp = await client.request(method, url, headers=self._headers(), **kwargs)
        if resp.status_code == 401:
            # T-05-01: Do NOT include key in error message
            raise MeshyAuthError(
                "Meshy API key is invalid or expired. Check MESHY_API_KEY in settings."
            )
        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", "60"))
            raise MeshyRateLimitError(
                f"Meshy rate limit hit (HTTP 429). Retry after {retry_after}s.",
                retry_after=retry_after,
            )
        if not resp.is_success:
            raise MeshyAPIError(
                f"Meshy API error {resp.status_code}: {resp.reason_phrase}"
            )
        return resp

    async def image_to_3d(
        self,
        image_path: str,
        task_type: str = "meshy-image-to-3d-reMeshed",
        prompt: str = "",
    ) -> MeshyTaskResult:
        """Submit an image-to-3D task and poll until completion.

        Raises:
            MeshyAuthError: invalid/missing API key
            MeshyRateLimitError: HTTP 429 response
            MeshyAPIError: non-retryable API error
            MeshyTimeoutError: job exceeded self._timeout seconds
        """
        image_bytes = Path(image_path).read_bytes()

        async with httpx.AsyncClient(timeout=httpx.Timeout(self._timeout)) as client:
            # 1. Submit task (multipart form)
            files = {
                "model_file": (Path(image_path).name, image_bytes, "image/jpeg"),
            }
            data = {"task_type": task_type}
            if prompt:
                data["prompt"] = prompt

            resp = await self._request(
                "POST",
                "/meshes",
                client=client,
                files=files,
                data=data,
            )
            submit_result = resp.json()
            task_id = submit_result.get("id") or submit_result.get("task_id", "")
            log.info("meshy_task_submitted", task_id=task_id, task_type=task_type)

            # 2. Poll with exponential backoff
            delay = 2.0
            start = time.monotonic()
            while True:
                elapsed = time.monotonic() - start
                if elapsed > self._timeout:
                    raise MeshyTimeoutError(
                        f"Meshy job {task_id} timed out after {self._timeout}s. "
                        "Check Meshy dashboard for stuck jobs."
                    )

                resp = await self._request(
                    "GET",
                    f"/meshes/{task_id}",
                    client=client,
                )
                status_resp = resp.json()
                task_status = status_resp.get("status", "")

                if task_status == "completed":
                    model_urls = status_resp.get("model_urls", {})
                    glb_url = model_urls.get("glb") or model_urls.get("model_url")
                    log.info("meshy_task_completed", task_id=task_id, glb_url=glb_url)
                    return MeshyTaskResult(
                        task_id=task_id,
                        status="completed",
                        glb_url=glb_url,
                        raw_response=status_resp,
                    )

                if task_status in ("failed", "cancelled"):
                    error_msg = status_resp.get("error", "Unknown error")
                    log.warning(
                        "meshy_task_failed",
                        task_id=task_id,
                        status=task_status,
                        error=error_msg,
                    )
                    return MeshyTaskResult(
                        task_id=task_id,
                        status=task_status,
                        error_message=error_msg,
                        raw_response=status_resp,
                    )

                # in_progress or pending — backoff and retry
                await asyncio.sleep(delay)
                delay = min(delay * 1.5, 30.0)


    async def auto_rig(
        self,
        *,
        model_url: str,
        height_meters: float = 1.7,
        poll_interval_s: float = 5.0,
    ) -> str:
        """POST /openapi/v1/rigging then poll; return rigged GLB URL on success.

        Phase 9 RIG-01 (PLAN_aura_killers_1wk.md §3.1). Pro tier required.

        Verified fields (per docs.meshy.ai/en/api/rigging): model_url,
        height_meters. Other body fields (pose, quadruped) are NOT
        documented and are explicitly omitted to avoid inventing API
        surface.

        Confidence note: the response field name for the rigged GLB URL
        was not directly verified against a live response; this
        implementation reads ``raw["model_urls"]["glb"]`` first and
        falls back to ``raw["result"]`` and ``raw["model_url"]`` with a
        warning log so a future fix can be targeted.
        """
        body = {"model_url": model_url, "height_meters": float(height_meters)}
        async with httpx.AsyncClient(timeout=httpx.Timeout(self._timeout)) as client:
            # 1. Submit
            resp = await client.post(
                MESHY_RIGGING_URL,
                headers={**self._headers(), "Content-Type": "application/json"},
                json=body,
            )
            if resp.status_code == 401:
                raise MeshyAuthError(
                    "Meshy API key invalid or not Pro-tier. "
                    "Auto-rigging requires Meshy Pro ($20/mo) or higher."
                )
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", "60"))
                raise MeshyRateLimitError(
                    f"Meshy rigging rate limit hit. Retry after {retry_after}s.",
                    retry_after=retry_after,
                )
            if not resp.is_success:
                raise MeshyAPIError(
                    f"Meshy rigging submit failed (HTTP {resp.status_code})."
                )
            sub = resp.json()
            task_id = sub.get("result") or sub.get("id") or ""
            if not task_id:
                raise MeshyAPIError(
                    "Meshy rigging response missing task id. "
                    "Verify your account has Pro-tier API access."
                )
            log.info("meshy_rigging_submitted", task_id=task_id)

            # 2. Poll
            poll_url = f"{MESHY_RIGGING_URL}/{task_id}"
            start = time.monotonic()
            while True:
                if time.monotonic() - start > self._timeout:
                    raise MeshyTimeoutError(
                        f"Meshy rigging task {task_id} timed out after {self._timeout}s."
                    )
                pr = await client.get(poll_url, headers=self._headers())
                if not pr.is_success:
                    raise MeshyAPIError(
                        f"Meshy rigging poll failed (HTTP {pr.status_code})."
                    )
                payload = pr.json()
                status = (payload.get("status") or "").upper()
                if status in ("SUCCEEDED", "COMPLETED"):
                    glb_url = (
                        (payload.get("model_urls") or {}).get("glb")
                        or payload.get("result_url")
                        or payload.get("model_url")
                    )
                    if not glb_url:
                        log.warning(
                            "meshy_rigging_url_field_unknown",
                            keys=list(payload.keys()),
                        )
                        # Fall back to a guess so callers see something rather
                        # than silently dropping the response.
                        glb_url = payload.get("result", "")
                    return glb_url
                if status in ("FAILED", "CANCELED", "CANCELLED"):
                    raise MeshyAPIError(
                        f"Meshy rigging task {task_id} status={status}: "
                        f"{payload.get('error', '')}"
                    )
                await asyncio.sleep(poll_interval_s)

__all__ = [
    "MeshyClient",
    "MeshyAuthError",
    "MeshyRateLimitError",
    "MeshyAPIError",
    "MeshyTimeoutError",
    "MeshyTaskResult",
    "MESHY_BASE_URL",
    "DEFAULT_TIMEOUT",
]