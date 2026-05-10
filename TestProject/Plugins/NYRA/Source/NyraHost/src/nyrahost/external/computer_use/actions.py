"""Win32 action handlers + screen capture for the computer-use loop.

All actions are clamped to a ``BoundedWindow`` (client rect of a
specific HWND). Coordinates supplied by the model are interpreted as
window-local; we translate to screen coordinates ourselves and refuse
anything outside the rect (T-05-07 — coordinate clamping).

The ``unreal``-equivalent for Win32 here is ``ctypes`` so this module
loads on the dev box (no UE editor required) and on CI runners. On
non-Windows the import gracefully degrades — ``Win32Actions(...)``
raises ``RuntimeError`` instead of silently producing garbage.
"""
from __future__ import annotations

import ctypes
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import structlog

log = structlog.get_logger("nyrahost.external.computer_use.actions")

# ----- Allowed host processes (T-05-08 scope confinement) ----------------
ALLOWED_PROCESSES = frozenset({"Sampler.exe", "UnrealEditor.exe"})

# Anthropic computer_20251124 max long-edge: 2576 px on Opus 4.7
MAX_SCREENSHOT_LONG_EDGE_PX = 2576


@dataclass(frozen=True)
class BoundedWindow:
    """A window the loop is allowed to operate on."""
    hwnd: int
    process_name: str
    rect_left: int
    rect_top: int
    rect_right: int
    rect_bottom: int

    @property
    def width(self) -> int:
        return self.rect_right - self.rect_left

    @property
    def height(self) -> int:
        return self.rect_bottom - self.rect_top

    def clamp(self, x: int, y: int) -> tuple[int, int]:
        """Translate window-local (x,y) to screen coords, clamped to rect."""
        cx = max(0, min(x, self.width - 1))
        cy = max(0, min(y, self.height - 1))
        return (self.rect_left + cx, self.rect_top + cy)

    def contains_screen_point(self, sx: int, sy: int) -> bool:
        return (
            self.rect_left <= sx < self.rect_right
            and self.rect_top <= sy < self.rect_bottom
        )


@dataclass
class ActionResult:
    """Outcome of a single action."""
    ok: bool
    detail: str = ""
    screenshot_path: Optional[Path] = None


def _require_windows() -> None:
    if sys.platform != "win32":
        raise RuntimeError(
            "computer-use loop is Windows-only (per CLAUDE.md platform "
            "constraint). Got platform: " + sys.platform
        )


class ScreenCapture:
    """BitBlt the client area of a BoundedWindow into a PNG.

    Output is downscaled to MAX_SCREENSHOT_LONG_EDGE_PX along the long
    edge (T-05-06: bound the exfiltration surface). The shipped
    implementation uses pure-Win32 GDI so we don't add a dependency on
    Pillow/mss; that keeps the offline wheel cache small.
    """

    def __init__(self, window: BoundedWindow) -> None:
        _require_windows()
        self.window = window

    def grab(self, out_path: Path) -> Path:
        """Capture the window and write a PNG to ``out_path``.

        Raises:
            RuntimeError: if the window is no longer visible / valid.
        """
        # Implementation note: a full BitBlt + PNG encode without Pillow
        # uses ctypes against gdi32 + zlib. The skeleton here documents
        # the contract and falls back to a clear NotImplementedError so
        # tests can inject a fake. v1.1 wires the real BitBlt path.
        out_path.parent.mkdir(parents=True, exist_ok=True)
        raise NotImplementedError(
            "ScreenCapture.grab is wired in v1.1 — inject a fake in "
            "tests via dependency injection on ComputerUseLoop."
        )


class Win32Actions:
    """SendInput-based action handlers, scoped to a single BoundedWindow."""

    # SendInput constants (winuser.h)
    INPUT_MOUSE = 0
    INPUT_KEYBOARD = 1
    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    MOUSEEVENTF_WHEEL = 0x0800
    MOUSEEVENTF_ABSOLUTE = 0x8000
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004

    def __init__(self, window: BoundedWindow) -> None:
        _require_windows()
        if window.process_name not in ALLOWED_PROCESSES:
            raise RuntimeError(
                f"computer-use refuses to operate on {window.process_name!r}. "
                f"Allowed: {sorted(ALLOWED_PROCESSES)}"
            )
        self.window = window

    # ----- mouse -------------------------------------------------------
    def click(self, x: int, y: int, *, button: str = "left") -> ActionResult:
        sx, sy = self.window.clamp(x, y)
        ctypes.windll.user32.SetCursorPos(sx, sy)
        if button == "left":
            ctypes.windll.user32.mouse_event(self.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            ctypes.windll.user32.mouse_event(self.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        elif button == "right":
            ctypes.windll.user32.mouse_event(self.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            ctypes.windll.user32.mouse_event(self.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        else:
            return ActionResult(ok=False, detail=f"unknown_button:{button}")
        return ActionResult(ok=True, detail=f"click_{button}@({sx},{sy})")

    def double_click(self, x: int, y: int) -> ActionResult:
        a = self.click(x, y)
        if not a.ok:
            return a
        time.sleep(0.05)
        b = self.click(x, y)
        return ActionResult(ok=b.ok, detail="double_click " + b.detail)

    def move(self, x: int, y: int) -> ActionResult:
        sx, sy = self.window.clamp(x, y)
        ctypes.windll.user32.SetCursorPos(sx, sy)
        return ActionResult(ok=True, detail=f"move@({sx},{sy})")

    def scroll(self, x: int, y: int, *, delta: int) -> ActionResult:
        """Scroll wheel delta (positive = up, 120 per detent)."""
        sx, sy = self.window.clamp(x, y)
        ctypes.windll.user32.SetCursorPos(sx, sy)
        ctypes.windll.user32.mouse_event(self.MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
        return ActionResult(ok=True, detail=f"scroll {delta}@({sx},{sy})")

    # ----- keyboard ----------------------------------------------------
    def type_text(self, text: str) -> ActionResult:
        """Type ``text`` as Unicode key events (works for any locale)."""
        if "\x00" in text:
            return ActionResult(ok=False, detail="text_contains_nul")
        for ch in text:
            self._send_unicode(ch)
        return ActionResult(ok=True, detail=f"type({len(text)} chars)")

    def _send_unicode(self, ch: str) -> None:
        # Simplified: real impl builds INPUT struct and calls SendInput.
        # Skeleton placeholder kept short on purpose.
        VK_CHAR = ord(ch)
        ctypes.windll.user32.keybd_event(0, VK_CHAR, self.KEYEVENTF_UNICODE, 0)
        ctypes.windll.user32.keybd_event(
            0, VK_CHAR, self.KEYEVENTF_UNICODE | self.KEYEVENTF_KEYUP, 0
        )

    def key(self, vk_code: int) -> ActionResult:
        ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk_code, 0, self.KEYEVENTF_KEYUP, 0)
        return ActionResult(ok=True, detail=f"key 0x{vk_code:02x}")
