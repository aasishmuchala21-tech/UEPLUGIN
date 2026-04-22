"""GPU backend probe (D-18, RESEARCH §3.5). Order: nvidia-smi -> vulkaninfo -> CPU.

Used by router.py to pick which per-backend folder of llama-server.exe
to spawn. Plan 08 keeps the probe to a simple binary-present test; a
more thorough "does this GPU actually have enough VRAM for Gemma 4B Q4_0"
check (~3.2 GB) is a Phase 2 refinement (§3.10 P1.5 CUDA DLL fallback).
"""
from __future__ import annotations

import asyncio
from enum import Enum

import structlog

log = structlog.get_logger("nyrahost.gpu")


class GpuBackend(str, Enum):
    CUDA = "cuda"
    VULKAN = "vulkan"
    CPU = "cpu"


async def _binary_probe(*cmd: str, timeout_s: float = 3.0) -> bool:
    """Run ``cmd`` to probe for the existence of a GPU stack.

    Returns True iff the binary launched AND exited 0 within the timeout.
    FileNotFoundError / generic OSError both return False silently — the
    probe is a "does this stack exist" signal, not a diagnostic.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            await asyncio.wait_for(proc.wait(), timeout=timeout_s)
        except asyncio.TimeoutError:
            proc.terminate()
            return False
        return proc.returncode == 0
    except FileNotFoundError:
        return False
    except OSError:
        return False


async def probe_gpu_backend() -> GpuBackend:
    """Probe in canonical order CUDA -> Vulkan -> CPU; return first hit."""
    if await _binary_probe("nvidia-smi", "-L"):
        log.info("gpu_backend_selected", backend="cuda")
        return GpuBackend.CUDA
    if await _binary_probe("vulkaninfo", "--summary"):
        log.info("gpu_backend_selected", backend="vulkan")
        return GpuBackend.VULKAN
    log.info("gpu_backend_selected", backend="cpu")
    return GpuBackend.CPU
