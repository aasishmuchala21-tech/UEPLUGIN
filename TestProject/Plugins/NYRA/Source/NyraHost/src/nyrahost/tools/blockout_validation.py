"""nyrahost.tools.blockout_validation — Phase 16-B LDA v1 structural checks.

Aura's docs call out specific Level Design Agent limitations:
  * Spiral staircases on non-standard floor heights
  * Arches at diagonal angles
  * Large blockouts and performance
  * Rooms with door cutouts where the door is blocked by another wall

NYRA v1 validates BlockoutSpec up front so the LLM never wastes
output on a structurally-bad request. Pure-Python — runs locally in
the sidecar; no UE editor needed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Iterable

from nyrahost.tools.blockout_primitives import (
    BlockoutSpec,
    RoomSpec,
    StaircaseSpec,
    MAX_DIM_CM,
    MAX_ROOMS_PER_BLOCKOUT,
)


SEVERITY_INFO: Final[str] = "info"
SEVERITY_WARN: Final[str] = "warning"
SEVERITY_ERROR: Final[str] = "error"


@dataclass(frozen=True)
class ValidationFinding:
    rule: str
    severity: str
    message: str
    room_index: int | None = None

    def to_dict(self) -> dict:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "message": self.message,
            "room_index": self.room_index,
        }


def _room_bbox(idx: int, room: RoomSpec, x_cursor: float) -> tuple[float, float, float, float]:
    """Return (min_x, min_y, max_x, max_y) for the room's footprint."""
    return (
        x_cursor - room.width_cm / 2,
        -room.depth_cm / 2,
        x_cursor + room.width_cm / 2,
        room.depth_cm / 2,
    )


def _bboxes_overlap(a: tuple[float, float, float, float],
                    b: tuple[float, float, float, float]) -> bool:
    return not (
        a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]
    )


def validate_blockout(spec: BlockoutSpec) -> list[ValidationFinding]:
    """Pure-function validation pass. Returns a list of findings."""
    findings: list[ValidationFinding] = []

    # Use the same cursor math the template uses (250 cm between items)
    # so overlap detection matches the actual placed footprints.
    GAP = 200.0
    cursor = 0.0
    bboxes: list[tuple[int, tuple[float, float, float, float]]] = []
    for i, r in enumerate(spec.rooms):
        bbox = _room_bbox(i, r, cursor)
        # Pairwise overlap check — O(N²) but N <= MAX_ROOMS_PER_BLOCKOUT.
        for j, prev in bboxes:
            if _bboxes_overlap(bbox, prev):
                findings.append(ValidationFinding(
                    rule="room_overlap",
                    severity=SEVERITY_ERROR,
                    message=f"Room {i} overlaps room {j} (likely cursor / GAP misconfig)",
                    room_index=i,
                ))
        bboxes.append((i, bbox))
        cursor += r.width_cm + GAP

        # Door cutout sanity: door_h must fit in wall height
        if r.door_wall != "none":
            if r.door_h >= r.height_cm:
                findings.append(ValidationFinding(
                    rule="door_too_tall",
                    severity=SEVERITY_ERROR,
                    message=f"Room {i}: door_h={r.door_h} >= height_cm={r.height_cm}",
                    room_index=i,
                ))
            if r.door_w >= r.width_cm and r.door_wall in ("north", "south"):
                findings.append(ValidationFinding(
                    rule="door_too_wide",
                    severity=SEVERITY_ERROR,
                    message=f"Room {i}: door_w={r.door_w} >= width_cm={r.width_cm}",
                    room_index=i,
                ))
            if r.door_w >= r.depth_cm and r.door_wall in ("east", "west"):
                findings.append(ValidationFinding(
                    rule="door_too_wide",
                    severity=SEVERITY_ERROR,
                    message=f"Room {i}: door_w={r.door_w} >= depth_cm={r.depth_cm}",
                    room_index=i,
                ))

        # Floor / ceiling missing
        if not r.has_floor:
            findings.append(ValidationFinding(
                rule="missing_floor",
                severity=SEVERITY_WARN,
                message=f"Room {i} has no floor — agent placement on this room will fall",
                room_index=i,
            ))

    # Staircase landing height vs room height (best-effort heuristic)
    for k, s in enumerate(spec.staircases):
        total_h = s.step_h * s.steps
        # Find an adjacent room (the room before the staircase in cursor order)
        if spec.rooms:
            last = spec.rooms[-1]
            if total_h > last.height_cm * 0.95:
                findings.append(ValidationFinding(
                    rule="stair_climbs_above_room",
                    severity=SEVERITY_WARN,
                    message=f"Staircase {k} rises {total_h}cm — taller than the "
                            f"adjacent room ({last.height_cm}cm). Did you mean a "
                            f"multi-floor blockout?",
                ))

    # Empty / too-large checks (already enforced in BlockoutSpec.from_dict
    # but re-asserted here so a programmatically-built spec gets caught too)
    if not spec.rooms:
        findings.append(ValidationFinding(
            rule="blockout_empty", severity=SEVERITY_ERROR,
            message="blockout_empty: no rooms",
        ))
    if len(spec.rooms) > MAX_ROOMS_PER_BLOCKOUT:
        findings.append(ValidationFinding(
            rule="blockout_too_large", severity=SEVERITY_ERROR,
            message=f"more than {MAX_ROOMS_PER_BLOCKOUT} rooms",
        ))

    return findings


def passes(findings: Iterable[ValidationFinding]) -> bool:
    """True iff there are zero error-level findings (warnings tolerated)."""
    return not any(f.severity == SEVERITY_ERROR for f in findings)


__all__ = [
    "ValidationFinding",
    "validate_blockout",
    "passes",
    "SEVERITY_INFO", "SEVERITY_WARN", "SEVERITY_ERROR",
]
