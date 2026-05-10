"""nyrahost.tools.cinematic — Phase 15-C Cinematic / DOP Agent."""
from __future__ import annotations

import json
import string
from pathlib import Path
from typing import Final, Optional

import structlog

log = structlog.get_logger("nyrahost.tools.cinematic")

ERR_BAD_INPUT: Final[int] = -32602
ERR_CINEMATIC_FAILED: Final[int] = -32066

TEMPLATE_PATH: Final[Path] = (
    Path(__file__).resolve().parent / "templates" / "cinematic.py.j2"
)

# Sane defaults — 35mm prime at f/2.8 is the "cinematic look" baseline.
DEFAULTS: Final[dict] = {
    "asset_path": "/Game/NYRA/Cinematics",
    "asset_name": "LS_NyraShot",
    "focal_length_mm": 35.0,
    "aperture_f": 2.8,
    "focus_distance_cm": 250.0,
    "duration_s": 5.0,
    "add_key_light": True,
    "add_fill_light": False,
}

ALLOWED_KEYS: Final[set[str]] = set(DEFAULTS.keys())


def render_cinematic_script(**overrides) -> str:
    bad = set(overrides) - ALLOWED_KEYS
    if bad:
        raise ValueError(f"unknown key(s): {sorted(bad)}")
    spec = {**DEFAULTS, **overrides}
    spec_json = json.dumps(spec, separators=(",", ":"))
    if "'''" in spec_json:
        raise ValueError("spec contains forbidden triple-quote sequence")
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
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


async def on_cinematic(params: dict, session=None, ws=None) -> dict:
    # Filter to ALLOWED_KEYS so a stray param can't slip into the template.
    filtered = {k: v for k, v in params.items() if k in ALLOWED_KEYS}
    try:
        script = render_cinematic_script(**filtered)
    except ValueError as exc:
        return _err(ERR_BAD_INPUT, "bad_request", str(exc))
    except (OSError, KeyError) as exc:
        return _err(ERR_CINEMATIC_FAILED, "cinematic_render_failed", str(exc))
    return {"script": script, "language": "python"}


__all__ = [
    "on_cinematic",
    "render_cinematic_script",
    "DEFAULTS",
    "ALLOWED_KEYS",
    "TEMPLATE_PATH",
    "ERR_BAD_INPUT",
    "ERR_CINEMATIC_FAILED",
]
