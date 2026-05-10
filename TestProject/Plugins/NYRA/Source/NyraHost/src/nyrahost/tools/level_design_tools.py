"""nyrahost.tools.level_design_tools — Phase 9 LDA-01 single MCP tool.

Aura-parity: ``nyra_blockout_room`` generates a 3D blockout actor in the
active level using GeometryScript primitives. v0 ships single-floor
rooms + linear staircases; PCG, structural validation, spiral
staircases and arches at diagonals are deferred to v1.1 — see
.planning/phases/09-aura-killers/09-CONTEXT.md.

This module renders a UE-side Python script from blockout.py.j2 and
returns it; the chat handler then forwards the script to the editor
through the existing console/exec WS pipeline (Phase 1 supervisor).
"""
from __future__ import annotations

import json
import string
from pathlib import Path
from typing import Final, Optional

import structlog

from nyrahost.tools.blockout_primitives import (
    BlockoutSpec,
    BlockoutValidationError,
)

log = structlog.get_logger("nyrahost.tools.level_design")

ERR_BAD_INPUT: Final[int] = -32602
ERR_BLOCKOUT_EMPTY: Final[int] = -32036
ERR_BLOCKOUT_TOO_LARGE: Final[int] = -32037
ERR_RENDER_FAILED: Final[int] = -32040

TEMPLATE_PATH: Final[Path] = (
    Path(__file__).resolve().parent / "templates" / "blockout.py.j2"
)


def render_blockout_script(spec: BlockoutSpec) -> str:
    """Render blockout.py.j2 with the given BlockoutSpec.

    The template embeds the spec as a JSON literal between triple
    single-quotes; we json.dumps + escape the literal so a stray
    backslash or single-quote in user-supplied data cannot break out.
    """
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    spec_json = json.dumps(spec.to_dict(), separators=(",", ":"))
    # The template uses ''' ... ''' to wrap the JSON; ensure no literal
    # ''' inside the JSON can break out. JSON.dumps never produces three
    # consecutive single-quotes (no quotes at all in numbers/strings of
    # the BlockoutSpec shape) but defend with a sanity check anyway.
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


async def on_blockout(params: dict, session=None, ws=None) -> dict:
    """Handle ``level_design/blockout`` JSON-RPC requests.

    params:
      rooms       (list[RoomSpec], required, 1..MAX_ROOMS_PER_BLOCKOUT)
      staircases  (list[StaircaseSpec], optional)
      spawn_at    ({x,y,z}, optional, default {0,0,0})

    Returns the rendered Python script string. The chat handler is
    responsible for forwarding it to the editor via console/exec.
    """
    try:
        spec = BlockoutSpec.from_dict(params)
    except BlockoutValidationError as exc:
        msg = str(exc)
        if msg.startswith("blockout_empty"):
            return _err(ERR_BLOCKOUT_EMPTY, "blockout_empty", msg)
        if msg.startswith("blockout_too_large"):
            return _err(ERR_BLOCKOUT_TOO_LARGE, "blockout_too_large", msg)
        return _err(ERR_BAD_INPUT, "blockout_invalid_spec", msg)

    try:
        script = render_blockout_script(spec)
    except (KeyError, OSError, ValueError) as exc:
        return _err(ERR_RENDER_FAILED, "blockout_render_failed", str(exc))

    log.info(
        "blockout_script_rendered",
        rooms=len(spec.rooms),
        staircases=len(spec.staircases),
        chars=len(script),
    )
    return {
        "script": script,
        "language": "python",
        "rooms_count": len(spec.rooms),
        "staircases_count": len(spec.staircases),
    }


__all__ = [
    "on_blockout",
    "render_blockout_script",
    "TEMPLATE_PATH",
    "ERR_BAD_INPUT",
    "ERR_BLOCKOUT_EMPTY",
    "ERR_BLOCKOUT_TOO_LARGE",
    "ERR_RENDER_FAILED",
]
