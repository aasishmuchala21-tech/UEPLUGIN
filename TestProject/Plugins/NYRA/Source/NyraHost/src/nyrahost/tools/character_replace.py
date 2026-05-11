"""nyrahost.tools.character_replace — Phase 19-E replace player character.

Aura ships "Replace the player character with my custom skeletal mesh"
as one-shot. NYRA composes the same flow over the existing Phase 9
RIG-02 retarget pipeline + a UE Python script that updates the
GameMode's DefaultPawnClass + retargets the Mannequin anims.

Returns a UE-Python script that the chat handler forwards via the
existing console/exec channel. Tests stay hermetic — they only
verify the script renders cleanly + compiles.
"""
from __future__ import annotations

import json
import string
from pathlib import Path
from typing import Final, Optional

import structlog

log = structlog.get_logger("nyrahost.tools.character_replace")

ERR_BAD_INPUT: Final[int] = -32602
ERR_REPLACE_FAILED: Final[int] = -32084

TEMPLATE_PATH: Final[Path] = (
    Path(__file__).resolve().parent / "templates" / "character_replace.py.j2"
)


def render_replace_script(
    *,
    new_mesh_path: str,
    rig_path: str = "/Game/NYRA/Rigs/IK_NYRA_Auto",
    retargeter_path: str = "/Game/NYRA/Rigs/RTG_Mannequin_to_NYRA",
    out_path: str = "/Game/NYRA/Retargeted",
) -> str:
    if not isinstance(new_mesh_path, str) or not new_mesh_path.startswith("/"):
        raise ValueError(
            "new_mesh_path must be a UE asset path (e.g. /Game/NYRA/SK_Hero)"
        )
    spec = {
        "new_mesh_path": new_mesh_path,
        "rig_path": rig_path,
        "retargeter_path": retargeter_path,
        "out_path": out_path,
    }
    spec_json = json.dumps(spec, separators=(",", ":"))
    if "'''" in spec_json:
        raise ValueError("spec contains forbidden triple-quote sequence")
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return string.Template(template).substitute(SPEC_JSON=spec_json)


def _err(code: int, message: str, detail: str = "",
         remediation: Optional[str] = None) -> dict:
    data: dict = {}
    if detail:
        data["detail"] = detail
    if remediation:
        data["remediation"] = remediation
    out: dict = {"error": {"code": code, "message": message}}
    if data:
        out["error"]["data"] = data
    return out


async def on_replace_player(params: dict, session=None, ws=None) -> dict:
    try:
        script = render_replace_script(
            new_mesh_path=params.get("new_mesh_path", ""),
            rig_path=params.get("rig_path", "/Game/NYRA/Rigs/IK_NYRA_Auto"),
            retargeter_path=params.get("retargeter_path",
                                        "/Game/NYRA/Rigs/RTG_Mannequin_to_NYRA"),
            out_path=params.get("out_path", "/Game/NYRA/Retargeted"),
        )
    except ValueError as exc:
        return _err(ERR_BAD_INPUT, "bad_request", str(exc))
    except (OSError, KeyError) as exc:
        return _err(ERR_REPLACE_FAILED, "render_failed", str(exc))
    return {"script": script, "language": "python"}


__all__ = [
    "on_replace_player",
    "render_replace_script",
    "TEMPLATE_PATH",
    "ERR_BAD_INPUT",
    "ERR_REPLACE_FAILED",
]
