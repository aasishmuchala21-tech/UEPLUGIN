"""nyrahost.health — Phase 15-D Live Project Health Dashboard backend.

Tier 2 moat. Aggregates a periodic snapshot of:

  * Asset hygiene findings (unused assets, naming violations)
  * Perf budget violations
  * Crash signatures
  * In-flight chat threads
  * Audit event rate

The agent runs entirely locally; the WS handler emits a single
``health/snapshot`` notification every N seconds the user has the
panel open. UE-side rendering is a separate Tier 1.A integration
that lives in the panel.

Design constraint: NO LLM calls in this module. Health is a
read-only summarisation pass over data the user already has, so it
has to be free.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Iterable, Optional

import structlog

from nyrahost.audit import AuditLog
from nyrahost.handlers.threads import ThreadRegistry

log = structlog.get_logger("nyrahost.health")

DEFAULT_POLL_INTERVAL_S: Final[float] = 60.0
MAX_RECENT_EVENTS: Final[int] = 1000


@dataclass(frozen=True)
class HealthSnapshot:
    ts: float
    thread_count: int
    thread_capacity: int
    audit_events_recent: int
    audit_events_total: int
    crash_signature_count: int
    perf_violations: int
    hygiene_findings: int
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "ts": self.ts,
            "thread_count": self.thread_count,
            "thread_capacity": self.thread_capacity,
            "audit_events_recent": self.audit_events_recent,
            "audit_events_total": self.audit_events_total,
            "crash_signature_count": self.crash_signature_count,
            "perf_violations": self.perf_violations,
            "hygiene_findings": self.hygiene_findings,
            "notes": list(self.notes),
        }


@dataclass
class HealthDashboard:
    """Pure-function snapshot builder. No state of its own — takes the
    components it summarises as constructor injection points."""

    project_dir: Path
    audit_log: AuditLog
    thread_registry: ThreadRegistry

    def snapshot(
        self,
        *,
        recent_window_s: float = 300.0,
        last_crash_count: int | None = None,
        last_perf_violations: int | None = None,
        last_hygiene_findings: int | None = None,
    ) -> HealthSnapshot:
        """Build a single HealthSnapshot.

        ``last_*`` params are injected by the caller because the
        underlying agents (RCA, perf, hygiene) execute UE-side and
        return their results over WS; the health module just plays
        scoreboard. Defaults to 0 when unknown — never silently invents
        a number.
        """
        records = list(self.audit_log.read_all())
        now = time.time()
        recent = sum(1 for r in records if now - float(r.get("ts", 0)) < recent_window_s)
        notes: list[str] = []
        if self.thread_registry.count == self.thread_registry.max_threads:
            notes.append("thread_capacity_full")
        if last_crash_count and last_crash_count > 0:
            notes.append(f"recent_crashes:{last_crash_count}")
        if last_perf_violations and last_perf_violations > 0:
            notes.append(f"perf_violations:{last_perf_violations}")
        return HealthSnapshot(
            ts=now,
            thread_count=self.thread_registry.count,
            thread_capacity=self.thread_registry.max_threads,
            audit_events_recent=recent,
            audit_events_total=len(records),
            crash_signature_count=int(last_crash_count or 0),
            perf_violations=int(last_perf_violations or 0),
            hygiene_findings=int(last_hygiene_findings or 0),
            notes=tuple(notes),
        )


__all__ = [
    "HealthSnapshot",
    "HealthDashboard",
    "DEFAULT_POLL_INTERVAL_S",
    "MAX_RECENT_EVENTS",
]
