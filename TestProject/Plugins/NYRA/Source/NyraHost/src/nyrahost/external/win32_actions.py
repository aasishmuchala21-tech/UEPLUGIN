"""nyrahost.external.win32_actions — Win32 action executor for computer-use.

Handles:
  - Mouse movement and clicks via SendInput
  - Keyboard input via SendInput
  - Global pause hotkey (Ctrl+Alt+Space) via RegisterHotKey
  - Screen capture via mss
"""
from __future__ import annotations

import ctypes
import time
from ctypes import wintypes
from typing import Optional

import structlog

try:
    import mss
except ImportError:
    mss = None

try:
    import win32api
    import win32con
except ImportError:
    win32api = None
    win32con = None

try:
    import win32input
except ImportError:
    win32input = None

log = structlog.get_logger("nyrahost.external.win32_actions")

# Win32 input types
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000

VK_C = 0x43
VK_ALT = 0x12
VK_SPACE = 0x20
VK_CONTROL = 0x11

PAUSE_CHORD = (VK_CONTROL, VK_ALT, VK_SPACE)
PAUSE_ID = 0x0001  # Arbitrary hotkey ID

# --- PermissionGate -----------------------------------------------------------


class PermissionGate:
    """Permission gate stub that shows a Win32 MessageBox before first action.

    In production this will be replaced by a UE modal via the Python bridge.
    This stub uses ctypes.windll.user32.MessageBoxW so it works without pywin32.
    """

    def check(self, task: str) -> bool:
        """Show a blocking dialog; return True if user clicks OK."""
        MB_OK = 0x0
        MB_ICONINFORMATION = 0x40

        title = "NYRA — Computer Use Permission"
        msg = (
            f"NYRA is about to control your mouse and keyboard.\n\n"
            f"Task: {task[:200]}\n\n"
            f"Press Ctrl+Alt+Space at any time to PAUSE.\n\n"
            f"Click OK to allow, Cancel to abort."
        )

        try:
            import ctypes as _ctypes

            result = _ctypes.windll.user32.MessageBoxW(
                None,
                msg,
                title,
                MB_OK | MB_ICONINFORMATION,
            )
            return result == 1  # IDOK
        except Exception:
            log.exception("permission_gate_messagebox_failed")
            return False


# --- ScreenCapture ------------------------------------------------------------


class ScreenCapture:
    """Screenshot capture using mss, saved to staging directory."""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self._counter = 0

    def capture(self, filename: Optional[str] = None) -> str:
        """Capture full screen, save to output_dir, return path."""
        if mss is None:
            raise RuntimeError("mss not available on this platform")

        import os

        os.makedirs(self.output_dir, exist_ok=True)

        name = filename or f"screenshot_{self._counter:04d}.png"
        path = os.path.join(self.output_dir, name)
        self._counter += 1

        with mss.mss() as sct:
            sct.save(path, region={})  # full screen
        log.info("screenshot_captured", path=path)
        return path


# --- Win32ActionExecutor ------------------------------------------------------


class Win32ActionExecutor:
    """Executes computer-use actions via Win32 APIs."""

    def __init__(self) -> None:
        self._pause_flag = False
        self._pause_hotkey_registered = False

        if win32api:
            try:
                win32api.RegisterHotKey(
                    None,
                    PAUSE_ID,
                    win32con.MOD_CONTROL | win32con.MOD_ALT,
                    VK_SPACE,
                )
                self._pause_hotkey_registered = True
                log.info("pause_hotkey_registered")
            except Exception as e:
                log.warning("failed_to_register_pause_hotkey", error=str(e))

    def check_pause_chord(self) -> bool:
        """Return True if Ctrl+Alt+Space was pressed.

        Checks via win32api PeekMessage (only works on the registering thread).
        Also checks the cross-thread _pause_flag set by a message-pump thread.
        """
        if win32api and self._pause_hotkey_registered:
            try:
                msg = wintypes.MSG()
                if win32api.PeekMessage(msg, 0, 0x0100, 0x0100, 0x0001):  # WM_HOTKEY
                    if msg.wParam == PAUSE_ID:
                        log.info("pause_chord_detected")
                        self._pause_flag = True
                        return True
            except Exception:
                pass
        return self._pause_flag

    def execute(self, action: dict) -> None:
        """Execute a single computer-use action dict.

        Supported action types:
          cursor, left_click, right_click, double_click, middle_click,
          scroll, type, key_combo, screenshot (no-op — handled by loop).
        """
        action_type = action.get("action") or action.get("type")
        x = action.get("x")
        y = action.get("y")

        if action_type == "screenshot":
            # Screenshots are captured by the loop, not the action executor
            return
        elif action_type == "cursor" and x is not None and y is not None:
            self._move_cursor(int(x), int(y))
        elif action_type in ("left_click", "click"):
            self._left_click(int(x) if x is not None else None, int(y) if y is not None else None)
        elif action_type == "double_click":
            self._left_click(int(x) if x is not None else None, int(y) if y is not None else None)
            time.sleep(0.05)
            self._left_click(int(x) if x is not None else None, int(y) if y is not None else None)
        elif action_type == "right_click":
            self._right_click(int(x) if x is not None else None, int(y) if y is not None else None)
        elif action_type == "middle_click":
            self._middle_click(int(x) if x is not None else None, int(y) if y is not None else None)
        elif action_type == "scroll":
            delta = int(action.get("scroll_amount", 100))
            self._scroll(delta)
        elif action_type == "type":
            text = action.get("text", "")
            self._type_text(text)
        elif action_type == "key_combo":
            keys = action.get("keys", [])
            self._send_key_combo(keys)

    def _move_cursor(self, x: int, y: int) -> None:
        """Move cursor to absolute position using SendInput."""
        if win32input is None:
            return

        # Normalize to 0-65535 range
        dx = max(0, min(65535, x))
        dy = max(0, min(65535, y))

        mi = win32input.MOUSEINPUT()
        mi.dx = dx
        mi.dy = dy
        mi.mouseData = 0
        mi.time = 0
        mi.dwExtraInfo = 0
        mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE

        inp = win32input.INPUT()
        inp.type = INPUT_MOUSE
        inp.mi = mi
        win32input.SendInput(1, [inp], ctypes.sizeof(win32input.INPUT))

    def _send_mouse_event(self, flags: int) -> None:
        """Send a mouse button event (down or up)."""
        if win32input is None:
            return

        mi = win32input.MOUSEINPUT()
        mi.dx = 0
        mi.dy = 0
        mi.mouseData = 0
        mi.time = 0
        mi.dwExtraInfo = 0
        mi.dwFlags = flags

        inp = win32input.INPUT()
        inp.type = INPUT_MOUSE
        inp.mi = mi
        win32input.SendInput(1, [inp], ctypes.sizeof(win32input.INPUT))

    def _left_click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        if x is not None and y is not None:
            self._move_cursor(x, y)
            time.sleep(0.02)
        self._send_mouse_event(MOUSEEVENTF_LEFTDOWN)
        time.sleep(0.02)
        self._send_mouse_event(MOUSEEVENTF_LEFTUP)

    def _right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        if x is not None and y is not None:
            self._move_cursor(x, y)
            time.sleep(0.02)
        self._send_mouse_event(MOUSEEVENTF_RIGHTDOWN)
        time.sleep(0.02)
        self._send_mouse_event(MOUSEEVENTF_RIGHTUP)

    def _middle_click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        if x is not None and y is not None:
            self._move_cursor(x, y)
            time.sleep(0.02)
        self._send_mouse_event(MOUSEEVENTF_MIDDLEDOWN)
        time.sleep(0.02)
        self._send_mouse_event(MOUSEEVENTF_MIDDLEUP)

    def _scroll(self, delta: int) -> None:
        if win32input is None:
            return
        mi = win32input.MOUSEINPUT()
        mi.dx = 0
        mi.dy = 0
        mi.mouseData = delta
        mi.time = 0
        mi.dwExtraInfo = 0
        mi.dwFlags = 0x0800  # MOUSEEVENTF_WHEEL
        inp = win32input.INPUT()
        inp.type = INPUT_MOUSE
        inp.mi = mi
        win32input.SendInput(1, [inp], ctypes.sizeof(win32input.INPUT))

    def _type_text(self, text: str) -> None:
        """Send text via SendInput Unicode mode."""
        if win32input is None or not text:
            return

        inputs: list[win32input.INPUT] = []
        for ch in text:
            # Press
            ki_down = win32input.KEYBDINPUT()
            ki_down.wVk = 0
            ki_down.scan = 0
            ki_down.time = 0
            ki_down.dwExtraInfo = 0
            ki_down.dwFlags = 0x0004  # KEYEVENTF_UNICODE
            inp_down = win32input.INPUT()
            inp_down.type = INPUT_KEYBOARD
            inp_down.ki = ki_down
            inputs.append(inp_down)
            # Release
            ki_up = win32input.KEYBDINPUT()
            ki_up.wVk = 0
            ki_up.scan = 0
            ki_up.time = 0
            ki_up.dwExtraInfo = 0
            ki_up.dwFlags = 0x0004 | 0x0002  # KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
            inp_up = win32input.INPUT()
            inp_up.type = INPUT_KEYBOARD
            inp_up.ki = ki_up
            inputs.append(inp_up)

        win32input.SendInput(len(inputs), inputs, ctypes.sizeof(win32input.INPUT))

    def _send_key_combo(self, keys: list) -> None:
        """Send a key combination (e.g. ['ctrl', 'c'])."""
        key_codes = {
            "ctrl": VK_CONTROL,
            "alt": VK_ALT,
            "space": VK_SPACE,
            "enter": 0x0D,
            "tab": 0x09,
            "esc": 0x1B,
            "shift": 0x10,
            "win": 0x5B,
        }
        vk_codes = [key_codes.get(str(k).lower(), ord(k.upper())) for k in keys]
        if win32input is None:
            return

        inputs: list[win32input.INPUT] = []
        for vk in vk_codes:
            ki_down = win32input.KEYBDINPUT()
            ki_down.wVk = vk
            ki_down.scan = 0
            ki_down.time = 0
            ki_down.dwExtraInfo = 0
            ki_down.dwFlags = 0
            inp = win32input.INPUT()
            inp.type = INPUT_KEYBOARD
            inp.ki = ki_down
            inputs.append(inp)
        for vk in reversed(vk_codes):
            ki_up = win32input.KEYBDINPUT()
            ki_up.wVk = vk
            ki_up.scan = 0
            ki_up.time = 0
            ki_up.dwExtraInfo = 0
            ki_up.dwFlags = 0x0002  # KEYEVENTF_KEYUP
            inp = win32input.INPUT()
            inp.type = INPUT_KEYBOARD
            inp.ki = ki_up
            inputs.append(inp)

        win32input.SendInput(len(inputs), inputs, ctypes.sizeof(win32input.INPUT))

    def register_pause_chord(self) -> None:
        """Re-register the Ctrl+Alt+Space pause hotkey."""
        if win32api and not self._pause_hotkey_registered:
            try:
                win32api.RegisterHotKey(
                    None,
                    PAUSE_ID,
                    win32con.MOD_CONTROL | win32con.MOD_ALT,
                    VK_SPACE,
                )
                self._pause_hotkey_registered = True
            except Exception as e:
                log.warning("failed_to_register_pause_hotkey", error=str(e))

    def unregister_pause_chord(self) -> None:
        """Unregister the pause hotkey."""
        if win32api and self._pause_hotkey_registered:
            try:
                win32api.UnregisterHotKey(None, PAUSE_ID)
                self._pause_hotkey_registered = False
            except Exception:
                pass

    def set_pause_flag(self) -> None:
        """Cross-thread signal that the pause chord fired."""
        self._pause_flag = True


__all__ = [
    "Win32ActionExecutor",
    "ScreenCapture",
    "PermissionGate",
    "PAUSE_CHORD",
    "PAUSE_ID",
]
