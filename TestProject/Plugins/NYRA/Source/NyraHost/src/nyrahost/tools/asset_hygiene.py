"""nyrahost.tools.asset_hygiene — Phase 13-C whole-project Asset Hygiene Agent.

Tier 2 moat. Aura ships per-asset / per-domain agents; a whole-project
sweep at their per-event SaaS pricing would bankrupt either the user
(huge token spend on read-only walks) or Aura (eaten margin). NYRA
runs the walk locally via UE Python — zero token cost — and the user's
Claude pin only sees the SUMMARY, not every asset.

The handler renders a UE-side Python script that:
  * Walks /Game/ via AssetRegistry
  * Flags unused assets (no inbound hard refs)
  * Flags naming-convention violations per project rules
"""
from __future__ import annotations

import json
import string
from pathlib import Path
from typing import Final, Optional

import structlog

log = structlog.get_logger("nyrahost.tools.asset_hygiene")

ERR_BAD_INPUT: Final[int] = -32602
ERR_HYGIENE_FAILED: Final[int] = -32054

TEMPLATE_PATH: Final[Path] = (
    Path(__file__).resolve().parent / "templates" / "asset_hygiene.py.j2"
)

# Canonical UE5 naming-convention starter set per Epic's coding standard.
DEFAULT_NAMING_RULES: Final[dict[str, str]] = {
    "Blueprint":      "BP_*",
    "Texture2D":      "T_*",
    "Material":       "M_*",
    "MaterialInstanceConstant": "MI_*",
    "StaticMesh":     "SM_*",
    "SkeletalMesh":   "SK_*",
    "AnimSequence":   "A_*",
    "AnimBlueprint":  "ABP_*",
    "BehaviorTree":   "BT_*",
    "BlackboardData": "BB_*",
    "NiagaraSystem":  "NS_*",
    "Sound":          "S_*",
    "DataTable":      "DT_*",
    "DataAsset":      "DA_*",
    "Enum":           "E_*",
    "Struct":         "F_*",   # struct prefix in C++ is `F`; .uasset Struct mirrors
}


def render_hygiene_script(
    *,
    under: str = "/Game",
    naming_rules: dict[str, str] | None = None,
    find_unused: bool = True,
    find_naming_violations: bool = True,
) -> str:
    if not isinstance(under, str) or not under.startswith("/"):
        raise ValueError("under must be a UE asset path (start with /Game/)")
    rules = dict(DEFAULT_NAMING_RULES) if naming_rules is None else dict(naming_rules)
    spec = {
        "under": under,
        "naming_rules": rules,
        "find_unused": bool(find_unused),
        "find_naming_violations": bool(find_naming_violations),
    }
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


async def on_run_hygiene(params: dict, session=None, ws=None) -> dict:
    """Handle ``hygiene/run`` JSON-RPC requests."""
    try:
        script = render_hygiene_script(
            under=params.get("under", "/Game"),
            naming_rules=params.get("naming_rules"),
            find_unused=bool(params.get("find_unused", True)),
            find_naming_violations=bool(params.get("find_naming_violations", True)),
        )
    except ValueError as exc:
        return _err(ERR_BAD_INPUT, "bad_request", str(exc))
    except (OSError, KeyError) as exc:
        return _err(ERR_HYGIENE_FAILED, "hygiene_render_failed", str(exc))
    return {"script": script, "language": "python"}


__all__ = [
    "on_run_hygiene",
    "render_hygiene_script",
    "DEFAULT_NAMING_RULES",
    "TEMPLATE_PATH",
    "ERR_BAD_INPUT",
    "ERR_HYGIENE_FAILED",
]
