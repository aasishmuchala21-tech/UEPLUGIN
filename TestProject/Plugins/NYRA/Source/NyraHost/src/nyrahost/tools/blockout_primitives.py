"""nyrahost.tools.blockout_primitives — Phase 9 LDA-01 schema.

Strongly-typed dataclasses for the Level Design Agent v0. The MCP tool
parses a natural-language request into one of these specs (or a list of
them) and ships the JSON to a UE-side Python script that materialises
the geometry via GeometryScript primitives.

Out of scope for v0 (deferred to v1.1):
  * PCG surface / volume / spline scatter
  * Structural validation (room overlap, door-blocked-by-wall, etc.)
  * Spiral staircases (need append_curved_stairs param verification)
  * Arches at diagonal wall angles
  * Multi-zone layouts >50 actors
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Final, Literal


DoorWall = Literal["north", "south", "east", "west", "none"]
ALLOWED_DOOR_WALLS: Final[set[str]] = {"north", "south", "east", "west", "none"}

# Hard caps lifted from PLAN_aura_killers_1wk.md §4.8 anti-patterns.
MAX_ROOMS_PER_BLOCKOUT: Final[int] = 12   # Aura's "blockout too large" threshold
MAX_DIM_CM: Final[float] = 50_000.0       # 500 m — anything larger is asking for trouble


class BlockoutValidationError(ValueError):
    """Raised when a BlockoutSpec violates a hard cap."""


@dataclass(frozen=True)
class RoomSpec:
    width_cm:    float = 800.0
    depth_cm:    float = 600.0
    height_cm:   float = 300.0
    wall_thick:  float = 20.0
    has_floor:   bool  = True
    has_ceiling: bool  = True
    door_wall:   str   = "north"
    door_w:      float = 100.0
    door_h:      float = 220.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class StaircaseSpec:
    steps:    int   = 12
    step_w:   float = 120.0
    step_h:   float = 18.0
    step_d:   float = 30.0
    floating: bool  = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SpawnPoint:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass(frozen=True)
class BlockoutSpec:
    rooms:      tuple[RoomSpec, ...] = field(default_factory=tuple)
    staircases: tuple[StaircaseSpec, ...] = field(default_factory=tuple)
    spawn_at:   SpawnPoint = field(default_factory=SpawnPoint)

    @classmethod
    def from_dict(cls, raw: dict) -> "BlockoutSpec":
        rooms_raw = raw.get("rooms")
        if not isinstance(rooms_raw, list) or len(rooms_raw) == 0:
            raise BlockoutValidationError(
                "blockout_empty: 'rooms' must be a non-empty list"
            )
        if len(rooms_raw) > MAX_ROOMS_PER_BLOCKOUT:
            raise BlockoutValidationError(
                f"blockout_too_large: {len(rooms_raw)} rooms exceeds cap "
                f"of {MAX_ROOMS_PER_BLOCKOUT}; chunk the request into "
                "smaller blockouts."
            )

        rooms = tuple(_parse_room(r) for r in rooms_raw)
        stairs_raw = raw.get("staircases", []) or []
        if not isinstance(stairs_raw, list):
            raise BlockoutValidationError("'staircases' must be a list")
        stairs = tuple(_parse_stair(s) for s in stairs_raw)

        spawn_raw = raw.get("spawn_at", {}) or {}
        spawn = SpawnPoint(
            float(spawn_raw.get("x", 0.0)),
            float(spawn_raw.get("y", 0.0)),
            float(spawn_raw.get("z", 0.0)),
        )
        return cls(rooms=rooms, staircases=stairs, spawn_at=spawn)

    def to_dict(self) -> dict:
        return {
            "rooms":      [r.to_dict() for r in self.rooms],
            "staircases": [s.to_dict() for s in self.staircases],
            "spawn_at":   asdict(self.spawn_at),
        }


def _parse_room(raw: dict) -> RoomSpec:
    if not isinstance(raw, dict):
        raise BlockoutValidationError(f"room must be an object, got {type(raw).__name__}")
    door_wall = str(raw.get("door_wall", "north")).lower()
    if door_wall not in ALLOWED_DOOR_WALLS:
        raise BlockoutValidationError(
            f"invalid door_wall {door_wall!r}; must be one of {sorted(ALLOWED_DOOR_WALLS)}"
        )
    out = RoomSpec(
        width_cm=float(raw.get("width_cm", 800.0)),
        depth_cm=float(raw.get("depth_cm", 600.0)),
        height_cm=float(raw.get("height_cm", 300.0)),
        wall_thick=float(raw.get("wall_thick", 20.0)),
        has_floor=bool(raw.get("has_floor", True)),
        has_ceiling=bool(raw.get("has_ceiling", True)),
        door_wall=door_wall,
        door_w=float(raw.get("door_w", 100.0)),
        door_h=float(raw.get("door_h", 220.0)),
    )
    for v in (out.width_cm, out.depth_cm, out.height_cm):
        if v <= 0 or v > MAX_DIM_CM:
            raise BlockoutValidationError(
                f"room dimension out of range (0, {MAX_DIM_CM}]: {v}"
            )
    return out


def _parse_stair(raw: dict) -> StaircaseSpec:
    if not isinstance(raw, dict):
        raise BlockoutValidationError(
            f"staircase must be an object, got {type(raw).__name__}"
        )
    return StaircaseSpec(
        steps=int(raw.get("steps", 12)),
        step_w=float(raw.get("step_w", 120.0)),
        step_h=float(raw.get("step_h", 18.0)),
        step_d=float(raw.get("step_d", 30.0)),
        floating=bool(raw.get("floating", False)),
    )


__all__ = [
    "BlockoutSpec",
    "BlockoutValidationError",
    "RoomSpec",
    "StaircaseSpec",
    "SpawnPoint",
    "ALLOWED_DOOR_WALLS",
    "MAX_ROOMS_PER_BLOCKOUT",
    "MAX_DIM_CM",
]
