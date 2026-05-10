"""nyrahost.tools.rigging_tools — Phase 9 RIG-01 auto-rig MCP tool.

Aura-parity: skeletal-mesh auto-rigging via Meshy /openapi/v1/rigging.
v0 ships humanoid-only rigging; quadruped + custom-skeleton support
land in v1.1 (see .planning/phases/09-aura-killers/09-CONTEXT.md).

Tier requirement: Meshy Pro ($20/mo) or higher — free tier cannot call
the rigging endpoint. Auth header is Bearer-token.

Threat mitigations:
  T-09-04: API key in Authorization header only; never logged.
  T-09-05: Local-path inputs are rejected with -32035 input_must_be_url
           because the rigging endpoint requires a publicly fetchable
           URL. Phase 10 will wrap the staging manifest in a localhost
           HTTPS proxy to allow generated meshes to flow through.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Final, Optional

import httpx
import structlog

from nyrahost.external.meshy_client import (
    MeshyAPIError,
    MeshyAuthError,
    MeshyClient,
    MeshyRateLimitError,
    MeshyTimeoutError,
)
from nyrahost.tools.staging import (
    JobEntry,
    PathTraversalError,
    StagingManifest,
)

log = structlog.get_logger("nyrahost.tools.rigging")

ERR_BAD_INPUT: Final[int] = -32602
ERR_AUTH: Final[int] = -32030
ERR_INPUT_NOT_URL: Final[int] = -32035
ERR_RIG_FAILED: Final[int] = -32038


def _err(code: int, message: str, detail: str = "", remediation: Optional[str] = None) -> dict:
    data: dict = {}
    if detail:
        data["detail"] = detail
    if remediation:
        data["remediation"] = remediation
    out: dict = {"error": {"code": code, "message": message}}
    if data:
        out["error"]["data"] = data
    return out


def _is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


async def on_auto_rig(params: dict, session=None, ws=None) -> dict:
    """Handle ``rigging/auto_rig`` JSON-RPC requests.

    params:
      input_glb_url   (str, required)   — must be http(s); local paths reject
      height_meters   (float, default 1.7)
      project_saved   (str, optional; falls back to env NYRA_PROJECT_SAVED)
    """
    url = params.get("input_glb_url")
    if not isinstance(url, str) or not url:
        return _err(ERR_BAD_INPUT, "missing_field", "input_glb_url")
    if not _is_url(url):
        return _err(
            ERR_INPUT_NOT_URL, "input_must_be_url",
            f"got local path: {url}",
            remediation=(
                "Auto-rig requires a publicly fetchable URL. "
                "Upload the GLB to a temporary signed URL or use the "
                "v1.1 staging-proxy when it ships."
            ),
        )

    height = float(params.get("height_meters", 1.7))
    project_saved = (
        params.get("project_saved")
        or os.environ.get("NYRA_PROJECT_SAVED")
        or "."
    )
    rigged_root = Path(project_saved) / "NYRA" / "staging" / "rigged"

    try:
        manifest = StagingManifest(staging_root=rigged_root)
        client = MeshyClient()
    except ValueError as exc:
        # MESHY_API_KEY missing
        return _err(
            ERR_AUTH, "meshy_auth_failed", str(exc),
            remediation=(
                "Set MESHY_API_KEY in the editor settings. Meshy Pro tier "
                "or higher is required for the rigging endpoint."
            ),
        )

    job_id = str(uuid.uuid4())[:16]
    try:
        rigged_url = await client.auto_rig(
            model_url=url, height_meters=height,
        )
    except MeshyAuthError as exc:
        return _err(ERR_AUTH, "meshy_auth_failed", str(exc))
    except (MeshyRateLimitError, MeshyAPIError, MeshyTimeoutError) as exc:
        return _err(ERR_RIG_FAILED, "meshy_rig_failed", str(exc))

    if not rigged_url:
        return _err(ERR_RIG_FAILED, "no_rigged_url",
                    "Meshy returned success without a rigged GLB URL.")

    # Download the rigged GLB into the staging dir.
    out_path = rigged_root / f"{job_id}.glb"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as dl:
            r = await dl.get(rigged_url)
            r.raise_for_status()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(r.content)
    except (httpx.HTTPError, OSError) as exc:
        return _err(ERR_RIG_FAILED, "rigged_download_failed", str(exc))

    # Path-validate (T-09-05 reuse of T-05-03).
    try:
        manifest._validate_path(str(out_path))  # noqa: SLF001
    except PathTraversalError as exc:
        return _err(ERR_RIG_FAILED, "path_invalid", str(exc))

    log.info("auto_rig_done", job_id=job_id, path=str(out_path))
    return {
        "job_id": job_id,
        "rigged_glb_path": str(out_path),
        "rigged_glb_url": rigged_url,
    }


__all__ = [
    "on_auto_rig",
    "ERR_BAD_INPUT",
    "ERR_AUTH",
    "ERR_INPUT_NOT_URL",
    "ERR_RIG_FAILED",
]
