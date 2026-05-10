"""nyrahost.warm_pool — Phase 18-A keep one idle claude subprocess hot.

Aura doesn't quote first-token latency; the perceived "fast" threshold
for chat is < 300 ms. NYRA's `ClaudeBackend.send` spawns
``claude -p ...`` per turn — the binary startup is the dominant cost.

This module maintains a small pool of pre-warmed Claude CLI
subprocesses idling on stdin. When ``chat/send`` fires, we grab the
warm process and feed it the prompt; first-token is bounded by the
WS round-trip + Anthropic's first-token latency, NOT by Claude CLI
startup.

Hard caps:
  * MAX_POOL_SIZE = 2 — one in-flight + one waiting; more than two
    would burn the user's Pro-tier session quota on idle processes.
  * IDLE_TIMEOUT_S = 600 — drain idle processes after 10 minutes of
    no chat activity so a forgotten editor doesn't leak CLI sessions.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Final, Optional

import structlog

log = structlog.get_logger("nyrahost.warm_pool")

MAX_POOL_SIZE: Final[int] = 2
IDLE_TIMEOUT_S: Final[float] = 600.0


@dataclass
class WarmProcess:
    proc: object   # asyncio.subprocess.Process — typed loose for ease of mocking
    spawned_at: float
    last_used_at: float
    pid: int


@dataclass
class WarmClaudePool:
    """Async, size-bounded pool of idling claude CLI subprocesses.

    The pool is intentionally tiny (MAX_POOL_SIZE=2). The goal isn't
    horizontal scale — it's eliminating the per-turn startup cost.
    """

    spawn_factory: object  # callable returning an awaitable of asyncio.subprocess.Process
    max_size: int = MAX_POOL_SIZE
    idle_timeout_s: float = IDLE_TIMEOUT_S
    _idle: list[WarmProcess] = field(default_factory=list)
    _lock: object = None

    def __post_init__(self) -> None:
        self._lock = asyncio.Lock()

    @property
    def idle_count(self) -> int:
        return len(self._idle)

    async def acquire(self) -> WarmProcess:
        """Return a warm process, spawning one if the pool is empty."""
        async with self._lock:
            while self._idle:
                cand = self._idle.pop(0)
                age = time.time() - cand.last_used_at
                if age > self.idle_timeout_s:
                    log.info("warm_pool_evict_stale", pid=cand.pid, age=age)
                    await self._terminate(cand)
                    continue
                cand.last_used_at = time.time()
                return cand
            return await self._spawn_one()

    async def release(self, proc: WarmProcess) -> None:
        """Return a process to the pool if it's still healthy + under cap."""
        async with self._lock:
            if not _is_alive(proc):
                log.info("warm_pool_dead_on_release", pid=proc.pid)
                return
            if len(self._idle) >= self.max_size:
                await self._terminate(proc)
                return
            proc.last_used_at = time.time()
            self._idle.append(proc)

    async def prewarm(self, count: int | None = None) -> int:
        """Spawn up to count (default max_size) processes if pool is below cap."""
        target = self.max_size if count is None else min(count, self.max_size)
        async with self._lock:
            while len(self._idle) < target:
                p = await self._spawn_one_locked()
                self._idle.append(p)
        return len(self._idle)

    async def drain(self) -> int:
        """Terminate all idle processes; return count drained."""
        async with self._lock:
            drained = list(self._idle)
            self._idle.clear()
        for p in drained:
            await self._terminate(p)
        return len(drained)

    async def _spawn_one(self) -> WarmProcess:
        return await self._spawn_one_locked()

    async def _spawn_one_locked(self) -> WarmProcess:
        spawn = self.spawn_factory
        proc = await spawn() if asyncio.iscoroutinefunction(spawn) else spawn()
        # Allow either an awaitable or a coroutine returning the proc
        if asyncio.iscoroutine(proc):
            proc = await proc
        wp = WarmProcess(
            proc=proc,
            spawned_at=time.time(),
            last_used_at=time.time(),
            pid=getattr(proc, "pid", -1),
        )
        log.info("warm_pool_spawn", pid=wp.pid)
        return wp

    async def _terminate(self, wp: WarmProcess) -> None:
        try:
            if hasattr(wp.proc, "terminate"):
                wp.proc.terminate()
            if hasattr(wp.proc, "wait"):
                w = wp.proc.wait()
                if asyncio.iscoroutine(w):
                    await asyncio.wait_for(w, timeout=2.0)
        except Exception:  # noqa: BLE001 — best-effort cleanup
            pass


def _is_alive(wp: WarmProcess) -> bool:
    rc = getattr(wp.proc, "returncode", None)
    return rc is None


__all__ = [
    "WarmClaudePool",
    "WarmProcess",
    "MAX_POOL_SIZE",
    "IDLE_TIMEOUT_S",
]
