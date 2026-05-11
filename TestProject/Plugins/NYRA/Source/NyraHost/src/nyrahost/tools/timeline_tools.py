"""nyrahost.tools.timeline_tools — Phase 13-B Timeline node authoring.

Aura's Blueprint docs callout: "Aura supports all four Timeline track
types: float, vector, linear color, and event." NYRA v0 ships float
tracks only; vector / linear-color / event are explicit v1.1 backlog
items in 09-CONTEXT.md.

Float tracks cover ~80% of common Timeline needs (door opens, fans
spin, platforms move, lights pulse). The remaining 20% require curve
asset types this v0 doesn't materialise.
"""
from __future__ import annotations

import json
import string
from pathlib import Path
from typing import Final, Optional

import structlog

log = structlog.get_logger("nyrahost.tools.timeline")

ERR_BAD_INPUT: Final[int] = -32602
ERR_TIMELINE_FAILED: Final[int] = -32053

ALLOWED_TRACK_KINDS: Final[frozenset[str]] = frozenset(
    {"float", "vector", "linear_color", "event"}  # all 4 — Phase 19-G
)

# Fix #4 from PR #1 code review: when Phase 19-G opened ALLOWED_TRACK_KINDS
# to all four kinds, the only validation at the render boundary remained
# the membership check. The template helpers blindly unpack tuples
# (`(t, vx, vy, vz)`, `(t, r, g, b, a)`), so a `vector` track that
# accidentally received float-shaped keyframes raised ValueError deep
# inside UE's Python interpreter, never seen by the WS caller. Pin per-kind
# arity at the host boundary so the JSON-RPC client gets a -32602 instead.
TRACK_KIND_ARITY: Final[dict[str, int]] = {
    "float":        2,   # [t, value]
    "vector":       4,   # [t, vx, vy, vz]
    "linear_color": 5,   # [t, r, g, b, a]
    "event":        1,   # [t]
}

TEMPLATE_PATH: Final[Path] = (
    Path(__file__).resolve().parent / "templates" / "timeline.py.j2"
)


def render_timeline_script(
    *,
    blueprint_path: str,
    track_name: str,
    keyframes: list[list[float]] | None = None,
    track_kind: str = "float",
    autoplay: bool = False,
    loop: bool = False,
    duration: float | None = None,
) -> str:
    """Render timeline.py.j2 with a JSON-encoded spec for the UE-side
    interpreter. Caller-supplied strings are JSON-escaped before
    embedding so backslashes / quotes can't break out of the template's
    triple-quoted JSON literal.
    """
    if track_kind not in ALLOWED_TRACK_KINDS:
        raise ValueError(
            f"track_kind={track_kind!r} not allowed in v0; "
            f"must be one of {sorted(ALLOWED_TRACK_KINDS)}"
        )
    if not isinstance(blueprint_path, str) or not blueprint_path:
        raise ValueError("blueprint_path must be a non-empty string")
    if not isinstance(track_name, str) or not track_name:
        raise ValueError("track_name must be a non-empty string")

    # Resolve keyframes: explicit caller-supplied list, or kind-appropriate
    # default. Float defaults remain backward-compatible.
    if keyframes is None:
        defaults = {
            "float":        [[0.0, 0.0], [1.0, 1.0]],
            "vector":       [[0.0, 0.0, 0.0, 0.0], [1.0, 1.0, 1.0, 1.0]],
            "linear_color": [[0.0, 0.0, 0.0, 0.0, 1.0], [1.0, 1.0, 1.0, 1.0, 1.0]],
            "event":        [[0.0]],
        }
        kf_list = defaults[track_kind]
    else:
        kf_list = keyframes

    # Fix #4: per-kind shape validation — refuse mismatched keyframes
    # at the host boundary so the UE template's tuple-unpack helpers
    # cannot blow up deep inside the editor's Python interpreter.
    expected_arity = TRACK_KIND_ARITY[track_kind]
    if not isinstance(kf_list, list) or not kf_list:
        raise ValueError("keyframes must be a non-empty list")
    for i, kf in enumerate(kf_list):
        if not isinstance(kf, (list, tuple)):
            raise ValueError(
                f"keyframes[{i}] must be a list, got {type(kf).__name__}"
            )
        if len(kf) != expected_arity:
            raise ValueError(
                f"keyframes[{i}] for track_kind={track_kind!r} must have "
                f"exactly {expected_arity} numeric elements "
                f"(got {len(kf)})"
            )
        for j, v in enumerate(kf):
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                raise ValueError(
                    f"keyframes[{i}][{j}] must be a number, "
                    f"got {type(v).__name__}"
                )

    spec = {
        "blueprint_path": blueprint_path,
        "track_name": track_name,
        "track_kind": track_kind,
        "keyframes": kf_list,
        "autoplay": bool(autoplay),
        "loop": bool(loop),
    }
    if duration is not None:
        spec["duration"] = float(duration)
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


async def on_add_timeline(params: dict, session=None, ws=None) -> dict:
    """Handle ``timeline/add`` JSON-RPC requests."""
    try:
        script = render_timeline_script(
            blueprint_path=params.get("blueprint_path", ""),
            track_name=params.get("track_name", ""),
            keyframes=params.get("keyframes"),
            track_kind=params.get("track_kind", "float"),
            autoplay=bool(params.get("autoplay", False)),
            loop=bool(params.get("loop", False)),
            duration=params.get("duration"),
        )
    except ValueError as exc:
        return _err(ERR_BAD_INPUT, "bad_request", str(exc))
    except (OSError, KeyError) as exc:
        return _err(ERR_TIMELINE_FAILED, "timeline_render_failed", str(exc))
    return {"script": script, "language": "python"}


__all__ = [
    "on_add_timeline",
    "render_timeline_script",
    "ALLOWED_TRACK_KINDS",
    "TRACK_KIND_ARITY",
    "TEMPLATE_PATH",
    "ERR_BAD_INPUT",
    "ERR_TIMELINE_FAILED",
]
