"""nyrahost.tools.pcg_scatter — Phase 16-A PCG scatter agent (Tier 1.B).

Aura ships three scatter workflows on top of UE PCG: surface, volume,
spline. NYRA mirrors the surface — same three modes, same parameters,
same template-the-UE-Python-script flow we used in Phase 9 LDA v0.

Parameter shape verified against:
  https://dev.epicgames.com/documentation/en-us/unreal-engine/procedural-content-generation-overview-in-unreal-engine
  https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/PCGGraph
"""
from __future__ import annotations

import json
import string
from pathlib import Path
from typing import Final, Optional

import structlog

log = structlog.get_logger("nyrahost.tools.pcg_scatter")

ERR_BAD_INPUT: Final[int] = -32602
ERR_PCG_FAILED: Final[int] = -32068

TEMPLATE_PATH: Final[Path] = (
    Path(__file__).resolve().parent / "templates" / "pcg_scatter.py.j2"
)

ALLOWED_MODES: Final[frozenset[str]] = frozenset({"surface", "volume", "spline"})
ALLOWED_ANCHORS: Final[frozenset[str]] = frozenset({"floor", "ceiling", "walls", "any"})

# Reasonable caps so a typo can't produce a 100k-point scatter on the
# user's machine.
MAX_DENSITY: Final[float] = 10.0   # points per m²
MAX_COUNT: Final[int] = 10_000
MAX_SPACING_CM: Final[float] = 100_000.0   # 1 km


def render_scatter_script(*, mode: str, mesh_path: str,
                          asset_path: str = "/Game/NYRA/PCG",
                          asset_name: str = "PCG_NyraScatter",
                          location: tuple[float, float, float] = (0.0, 0.0, 0.0),
                          **kwargs) -> str:
    if mode not in ALLOWED_MODES:
        raise ValueError(f"mode must be one of {sorted(ALLOWED_MODES)}; got {mode!r}")
    if not isinstance(mesh_path, str) or not mesh_path.startswith("/"):
        raise ValueError(f"mesh_path must be a UE asset path; got {mesh_path!r}")
    spec: dict = {
        "asset_path": asset_path,
        "asset_name": asset_name,
        "mode": mode,
        "mesh_path": mesh_path,
        "location": list(location),
    }
    if mode == "surface":
        density = float(kwargs.get("density", 0.5))
        if density <= 0 or density > MAX_DENSITY:
            raise ValueError(f"density {density} out of range (0, {MAX_DENSITY}]")
        spec["density"] = density
        spec["scale_min"] = float(kwargs.get("scale_min", 0.8))
        spec["scale_max"] = float(kwargs.get("scale_max", 1.2))
    elif mode == "volume":
        count = int(kwargs.get("count", 100))
        if count <= 0 or count > MAX_COUNT:
            raise ValueError(f"count {count} out of range (0, {MAX_COUNT}]")
        anchor = str(kwargs.get("anchor", "floor"))
        if anchor not in ALLOWED_ANCHORS:
            raise ValueError(f"anchor must be one of {sorted(ALLOWED_ANCHORS)}")
        spec["count"] = count
        spec["anchor"] = anchor
    elif mode == "spline":
        spacing = float(kwargs.get("spacing_cm", 200.0))
        if spacing <= 0 or spacing > MAX_SPACING_CM:
            raise ValueError(f"spacing_cm {spacing} out of range")
        spec["spacing_cm"] = spacing
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


async def on_pcg_scatter(params: dict, session=None, ws=None) -> dict:
    try:
        script = render_scatter_script(
            mode=params.get("mode", ""),
            mesh_path=params.get("mesh_path", ""),
            asset_path=params.get("asset_path", "/Game/NYRA/PCG"),
            asset_name=params.get("asset_name", "PCG_NyraScatter"),
            location=tuple(params.get("location", (0.0, 0.0, 0.0))),
            density=params.get("density"),
            count=params.get("count"),
            anchor=params.get("anchor"),
            scale_min=params.get("scale_min", 0.8),
            scale_max=params.get("scale_max", 1.2),
            spacing_cm=params.get("spacing_cm"),
        )
    except (TypeError, ValueError) as exc:
        return _err(ERR_BAD_INPUT, "bad_request", str(exc))
    except (OSError, KeyError) as exc:
        return _err(ERR_PCG_FAILED, "pcg_render_failed", str(exc))
    return {"script": script, "language": "python"}


__all__ = [
    "on_pcg_scatter",
    "render_scatter_script",
    "ALLOWED_MODES",
    "ALLOWED_ANCHORS",
    "MAX_DENSITY", "MAX_COUNT", "MAX_SPACING_CM",
    "TEMPLATE_PATH",
    "ERR_BAD_INPUT", "ERR_PCG_FAILED",
]
