"""nyrahost.tools.retarget_tools — Phase 9 RIG-02 retargeting MCP tool.

Aura-parity: replace UE Mannequin animations onto a custom rigged
skeletal mesh, preserving forward direction and bone mapping. v0
ships humanoid-only retargeting via IKRetargetBatchOperation; quadruped
and custom solvers land in v1.1.

This module's job is to *generate* the UE-Python script string from the
retarget.py.j2 template. The script is then executed inside the UE
editor via the existing console.py / unreal_python_exec channel — it
does NOT run inside the NyraHost asyncio process.
"""
from __future__ import annotations

import json
import string
from pathlib import Path
from typing import Final, Optional

import structlog

log = structlog.get_logger("nyrahost.tools.retarget")

ERR_BAD_INPUT: Final[int] = -32602
ERR_RETARGET_FAILED: Final[int] = -32039

TEMPLATE_PATH: Final[Path] = (
    Path(__file__).resolve().parent / "templates" / "retarget.py.j2"
)

# Sensible UE5 defaults the user can override.
DEFAULT_SOURCE_MESH: Final[str] = "/Game/Characters/Mannequins/Meshes/SKM_Manny"
DEFAULT_SOURCE_RIG: Final[str] = "/Game/Characters/Mannequins/Rigs/IK_Mannequin"
DEFAULT_OUT_PATH: Final[str] = "/Game/NYRA/Retargeted"


def render_retarget_script(
    *,
    rigged_mesh: str,
    source_mesh: str = DEFAULT_SOURCE_MESH,
    source_rig: str = DEFAULT_SOURCE_RIG,
    out_path: str = DEFAULT_OUT_PATH,
) -> str:
    """Render retarget.py.j2 with caller-supplied UE asset paths.

    Fix #2 from PR #1 code review: previously this used
    ``string.Template.substitute`` to inline each path raw into a Python
    string literal in the rendered script. A path containing a quote +
    newline could break out and execute arbitrary code in the UE editor's
    Python interpreter. Now mirrors the safe ``SPEC_JSON`` pattern used by
    blockout.py.j2: serialise a dict via ``json.dumps`` and embed it in the
    template between triple single-quotes, then parse with ``json.loads``
    on the UE side. Defensive guard rejects strings containing a literal
    ``'''`` so they cannot break out of the surrounding triple-quote.
    """
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    spec = {
        "rigged_mesh": rigged_mesh,
        "source_mesh": source_mesh,
        "source_rig": source_rig,
        "out_path": out_path,
    }
    spec_json = json.dumps(spec, separators=(",", ":"))
    if "'''" in spec_json:
        raise ValueError("spec contains forbidden triple-quote sequence")
    return string.Template(template).substitute(SPEC_JSON=spec_json)


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


async def on_retarget(params: dict, session=None, ws=None) -> dict:
    """Handle ``rigging/retarget`` JSON-RPC requests.

    params:
      rigged_mesh   (str, required)  — UE asset path of the rigged target mesh
      source_mesh   (str, optional)  — defaults to UE Mannequin
      source_rig    (str, optional)  — defaults to UE Mannequin IK rig
      out_path      (str, optional)  — defaults to /Game/NYRA/Retargeted

    Returns the rendered Python script string. The chat handler is
    responsible for forwarding the script to the UE editor via the
    existing console/exec WS request.
    """
    rigged = params.get("rigged_mesh")
    if not isinstance(rigged, str) or not rigged:
        return _err(ERR_BAD_INPUT, "missing_field", "rigged_mesh")

    try:
        script = render_retarget_script(
            rigged_mesh=rigged,
            source_mesh=params.get("source_mesh", DEFAULT_SOURCE_MESH),
            source_rig=params.get("source_rig", DEFAULT_SOURCE_RIG),
            out_path=params.get("out_path", DEFAULT_OUT_PATH),
        )
    except (KeyError, OSError, ValueError) as exc:
        return _err(ERR_RETARGET_FAILED, "render_failed", str(exc))

    log.info("retarget_script_rendered", chars=len(script))
    return {"script": script, "language": "python"}


__all__ = [
    "on_retarget",
    "render_retarget_script",
    "TEMPLATE_PATH",
    "DEFAULT_SOURCE_MESH",
    "DEFAULT_SOURCE_RIG",
    "DEFAULT_OUT_PATH",
    "ERR_BAD_INPUT",
    "ERR_RETARGET_FAILED",
]
