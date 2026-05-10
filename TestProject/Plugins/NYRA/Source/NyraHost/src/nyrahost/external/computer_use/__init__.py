"""Plan 05-03 — Computer-use loop (Substance 3D Sampler + UE editor modals).

GEN-03 surface. Drives the user's Claude Pro subscription's
``computer_20251124`` tool (Opus 4.7) to operate Windows applications
that don't expose APIs (Substance 3D Sampler, UE editor modal dialogs).

Architecture:
  - ``ComputerUseLoop`` orchestrates: screenshot -> model -> action -> repeat
  - ``Win32Actions`` implements click / type / scroll / key via SendInput
  - ``ScreenCapture`` snapshots the bounded application window via Win32
  - Permission gate calls into ``nyrahost.console.NyraConsole.await_decision``
    so every destructive action surfaces to the UE chat panel before
    SendInput fires

Hard rules per Phase 5 review (T-05-05..T-05-08):
  1. ``max_iterations=20`` cap; ``max_wall_clock_seconds=300`` cap
  2. ``window_handle`` is REQUIRED — actions clamp coordinates to the
     bounded HWND's client rect; we never click on the wider desktop
  3. Scope confinement: only Substance 3D Sampler (process name
     ``Sampler.exe``) or the UE editor (``UnrealEditor.exe``) may host
     a computer-use session
  4. ``Ctrl+Alt+Space`` global hotkey raises ``ComputerUsePaused`` so
     the user can stop a stuck session at any time
  5. Permission gate fires BEFORE every Action that mutates state
     (click, type, key, drag) — read-only actions (screenshot, zoom,
     wait) skip the gate
  6. Screenshots are downscaled to <=2576 px on the long edge before
     leaving the machine (T-05-06: minimize exfiltration surface)

This package ships the structure + Win32 actions + screen capture +
loop scaffold. The Anthropic SDK call site is wired but kept behind a
``backend.send_screenshot_get_action`` dependency-injection point so
Phase 5.1 can swap between ``anthropic.Messages`` and the ``claude``
CLI subprocess driver as the auth-resolution decision shakes out (the
Phase 0 SC#1 verdict).

Operator-side prerequisites (NOT shipped here):
  - User has ``ANTHROPIC_API_KEY`` set OR a Claude Pro subscription
    routed through the Claude Desktop computer-use surface
  - Substance 3D Sampler v4.x or UE editor 5.4-5.7 must be running
    and visible at session start
"""
from __future__ import annotations

from .actions import (
    ActionResult,
    BoundedWindow,
    ScreenCapture,
    Win32Actions,
)
from .loop import (
    ComputerUseBackend,
    ComputerUseLoop,
    ComputerUsePaused,
    ComputerUseSessionLimitExceeded,
    LoopResult,
)

__all__ = [
    "ActionResult",
    "BoundedWindow",
    "ScreenCapture",
    "Win32Actions",
    "ComputerUseBackend",
    "ComputerUseLoop",
    "ComputerUsePaused",
    "ComputerUseSessionLimitExceeded",
    "LoopResult",
]
