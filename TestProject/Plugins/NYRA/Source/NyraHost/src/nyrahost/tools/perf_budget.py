"""nyrahost.tools.perf_budget — Phase 13-E Performance Budget Agent.

Tier 2 moat. Persists per-level budgets to ``Saved/NYRA/perf_budgets.json``
and compares each new measurement against the saved baseline. Aura's
SaaS pricing makes per-build perf scrubs cost-prohibitive at studio
scale; NYRA's runs locally so cost is constant.

v0 measures actor / light / static-mesh-actor counts only — these are
strong proxies for draw call growth without needing a stat-dump RPC
into the renderer.
"""
from __future__ import annotations

import json
import os
import string
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Optional

import structlog

log = structlog.get_logger("nyrahost.tools.perf_budget")

ERR_BAD_INPUT: Final[int] = -32602
ERR_PERF_FAILED: Final[int] = -32055

TEMPLATE_PATH: Final[Path] = (
    Path(__file__).resolve().parent / "templates" / "perf_budget.py.j2"
)


@dataclass(frozen=True)
class LevelBudget:
    level_path: str
    actor_count: int = 1500
    light_count: int = 64
    static_mesh_actor_count: int = 1200


def _budgets_path(project_dir: Path) -> Path:
    return Path(project_dir) / "Saved" / "NYRA" / "perf_budgets.json"


def load_budgets(project_dir: Path) -> dict[str, LevelBudget]:
    p = _budgets_path(project_dir)
    if not p.exists():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, LevelBudget] = {}
    for entry in raw.get("budgets", []):
        if not isinstance(entry, dict):
            continue
        try:
            out[entry["level_path"]] = LevelBudget(
                level_path=entry["level_path"],
                actor_count=int(entry.get("actor_count", 1500)),
                light_count=int(entry.get("light_count", 64)),
                static_mesh_actor_count=int(entry.get("static_mesh_actor_count", 1200)),
            )
        except (KeyError, TypeError, ValueError):
            continue
    return out


def save_budgets(project_dir: Path, budgets: dict[str, LevelBudget]) -> Path:
    """Atomic write the budgets file via tempfile + os.replace."""
    target = _budgets_path(project_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "version": 1,
        "budgets": [
            {
                "level_path": b.level_path,
                "actor_count": b.actor_count,
                "light_count": b.light_count,
                "static_mesh_actor_count": b.static_mesh_actor_count,
            }
            for b in budgets.values()
        ],
    }
    tmp = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False,
        dir=str(target.parent),
        prefix=".perf_budgets.", suffix=".tmp",
    )
    try:
        json.dump(body, tmp, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, target)
    except Exception:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        raise
    return target


def diff_against_budget(measurement: dict, budget: LevelBudget) -> dict:
    """Return a structured diff of a measurement against its budget."""
    out: dict = {"level_path": budget.level_path, "violations": []}
    for field_name in ("actor_count", "light_count", "static_mesh_actor_count"):
        measured = int(measurement.get(field_name, 0))
        cap = int(getattr(budget, field_name))
        if measured > cap:
            out["violations"].append({
                "metric": field_name,
                "measured": measured,
                "budget": cap,
                "over_by": measured - cap,
                "ratio": measured / max(1, cap),
            })
    out["passed"] = len(out["violations"]) == 0
    return out


def render_perf_script(*, levels: list[str]) -> str:
    if not isinstance(levels, list) or not levels:
        raise ValueError("levels must be a non-empty list")
    spec = {"levels": levels}
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


class PerfBudgetHandlers:
    """WS handlers for ``perf_budget/*`` methods."""

    def __init__(self, *, project_dir: Path) -> None:
        self._project_dir = Path(project_dir)

    async def on_render_script(self, params: dict, session=None, ws=None) -> dict:
        try:
            script = render_perf_script(levels=params.get("levels", []))
        except ValueError as exc:
            return _err(ERR_BAD_INPUT, "bad_request", str(exc))
        except OSError as exc:
            return _err(ERR_PERF_FAILED, "render_failed", str(exc))
        return {"script": script, "language": "python"}

    async def on_get_budgets(self, params: dict, session=None, ws=None) -> dict:
        b = load_budgets(self._project_dir)
        return {
            "budgets": [
                {
                    "level_path": x.level_path,
                    "actor_count": x.actor_count,
                    "light_count": x.light_count,
                    "static_mesh_actor_count": x.static_mesh_actor_count,
                }
                for x in b.values()
            ],
        }

    async def on_set_budget(self, params: dict, session=None, ws=None) -> dict:
        path = params.get("level_path")
        if not isinstance(path, str) or not path:
            return _err(ERR_BAD_INPUT, "missing_field", "level_path")
        try:
            b = LevelBudget(
                level_path=path,
                actor_count=int(params.get("actor_count", 1500)),
                light_count=int(params.get("light_count", 64)),
                static_mesh_actor_count=int(params.get("static_mesh_actor_count", 1200)),
            )
        except (TypeError, ValueError) as exc:
            return _err(ERR_BAD_INPUT, "bad_value", str(exc))
        store = load_budgets(self._project_dir)
        store[path] = b
        try:
            save_budgets(self._project_dir, store)
        except OSError as exc:
            return _err(ERR_PERF_FAILED, "save_failed", str(exc))
        return {"saved": True, "level_path": path}

    async def on_check(self, params: dict, session=None, ws=None) -> dict:
        """Compare a caller-supplied measurement against the persisted budget."""
        m = params.get("measurement")
        if not isinstance(m, dict) or "level_path" not in m:
            return _err(ERR_BAD_INPUT, "missing_field", "measurement.level_path")
        store = load_budgets(self._project_dir)
        b = store.get(m["level_path"])
        if b is None:
            return _err(
                ERR_BAD_INPUT, "no_budget_for_level", m["level_path"],
                remediation="Call perf_budget/set first to record a baseline.",
            )
        return diff_against_budget(m, b)


__all__ = [
    "LevelBudget",
    "PerfBudgetHandlers",
    "load_budgets",
    "save_budgets",
    "diff_against_budget",
    "render_perf_script",
    "ERR_BAD_INPUT",
    "ERR_PERF_FAILED",
]
