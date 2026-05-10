"""Plan 05-03 computer-use loop tests — exercises the orchestrator with
fake backends/actions so the contract holds without needing a live
Substance/UE host.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock

import pytest


# Skip the whole module on non-Windows: Win32Actions imports ctypes.windll
# at construction. The orchestrator (loop.py) is platform-agnostic;
# tests that exercise the loop with a fake actions object will still
# import fine on POSIX but the high-fidelity click/type tests below
# need the Windows path.
pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Computer-use is Windows-only per CLAUDE.md platform constraint.",
)

from nyrahost.external.computer_use import (  # noqa: E402
    BoundedWindow,
    ComputerUseLoop,
    ComputerUsePaused,
    ComputerUseSessionLimitExceeded,
    LoopResult,
    Win32Actions,
)


def _window() -> BoundedWindow:
    return BoundedWindow(
        hwnd=12345,
        process_name="Sampler.exe",
        rect_left=100,
        rect_top=200,
        rect_right=900,
        rect_bottom=800,
    )


class TestBoundedWindowClamp:
    def test_in_bounds_translates(self):
        w = _window()
        assert w.clamp(50, 50) == (150, 250)

    def test_out_of_bounds_clamps(self):
        w = _window()
        # Far past right edge
        sx, sy = w.clamp(99999, 99999)
        assert sx < w.rect_right and sy < w.rect_bottom

    def test_negative_clamps_to_zero(self):
        w = _window()
        assert w.clamp(-10, -10) == (100, 200)


class TestWin32ActionsAllowedProcesses:
    def test_refuses_unknown_process(self):
        bad = BoundedWindow(
            hwnd=1, process_name="evil.exe",
            rect_left=0, rect_top=0, rect_right=100, rect_bottom=100,
        )
        with pytest.raises(RuntimeError, match="refuses"):
            Win32Actions(bad)


class FakeBackend:
    """Test fixture: returns a script of pre-set actions in order."""
    def __init__(self, script: list[dict]):
        self.script = list(script)
        self.calls: list[dict] = []

    async def step(self, screenshot_path, history, goal):
        self.calls.append({"goal": goal, "n_history": len(history)})
        if not self.script:
            return {"action": "done", "summary": "ran out of script"}
        return self.script.pop(0)


class FakeCapture:
    def __init__(self):
        self.shots: list[Path] = []

    def grab(self, out_path: Path) -> Path:
        out_path.write_bytes(b"fake-png")
        self.shots.append(out_path)
        return out_path


class FakeActions:
    """Records dispatched actions instead of touching Win32."""
    def __init__(self, window: BoundedWindow):
        self.window = window
        self.dispatched: list[str] = []

    def click(self, x, y, *, button="left"):
        from nyrahost.external.computer_use.actions import ActionResult
        self.dispatched.append(f"click_{button}@({x},{y})")
        return ActionResult(ok=True, detail=self.dispatched[-1])

    def double_click(self, x, y):
        from nyrahost.external.computer_use.actions import ActionResult
        self.dispatched.append(f"dclick@({x},{y})")
        return ActionResult(ok=True, detail=self.dispatched[-1])

    def move(self, x, y):
        from nyrahost.external.computer_use.actions import ActionResult
        self.dispatched.append(f"move@({x},{y})")
        return ActionResult(ok=True, detail=self.dispatched[-1])

    def scroll(self, x, y, *, delta):
        from nyrahost.external.computer_use.actions import ActionResult
        self.dispatched.append(f"scroll{delta}@({x},{y})")
        return ActionResult(ok=True, detail=self.dispatched[-1])

    def type_text(self, text):
        from nyrahost.external.computer_use.actions import ActionResult
        self.dispatched.append(f"type({len(text)})")
        return ActionResult(ok=True, detail=self.dispatched[-1])

    def key(self, vk_code):
        from nyrahost.external.computer_use.actions import ActionResult
        self.dispatched.append(f"key{vk_code}")
        return ActionResult(ok=True, detail=self.dispatched[-1])


def _make_loop(
    *,
    backend: FakeBackend,
    actions: FakeActions,
    capture: FakeCapture,
    approve: bool = True,
    pause: bool = False,
    workspace: Path,
    max_iterations: int = 5,
) -> ComputerUseLoop:
    async def gate(step):
        return approve

    return ComputerUseLoop(
        window=actions.window,
        backend=backend,
        actions=actions,  # type: ignore[arg-type]
        capture=capture,  # type: ignore[arg-type]
        permission_gate=gate,
        check_pause=lambda: pause,
        workspace=workspace,
        max_iterations=max_iterations,
    )


class TestLoopOrchestration:
    @pytest.mark.asyncio
    async def test_done_action_returns_success(self, tmp_path: Path):
        backend = FakeBackend([{"action": "done", "summary": "task complete"}])
        loop = _make_loop(
            backend=backend, actions=FakeActions(_window()),
            capture=FakeCapture(), workspace=tmp_path,
        )
        result = await loop.run("test goal")
        assert result.success is True
        assert result.iterations == 1
        assert result.last_message == "task complete"

    @pytest.mark.asyncio
    async def test_click_then_done_dispatches_and_completes(
        self, tmp_path: Path
    ):
        actions = FakeActions(_window())
        backend = FakeBackend([
            {"action": "click", "x": 50, "y": 50},
            {"action": "done", "summary": "done"},
        ])
        loop = _make_loop(
            backend=backend, actions=actions,
            capture=FakeCapture(), workspace=tmp_path,
        )
        result = await loop.run("click and finish")
        assert result.success is True
        assert any("click_left" in s for s in actions.dispatched)

    @pytest.mark.asyncio
    async def test_permission_rejection_aborts(self, tmp_path: Path):
        actions = FakeActions(_window())
        backend = FakeBackend([
            {"action": "click", "x": 10, "y": 10},
            {"action": "done", "summary": "should never reach"},
        ])
        loop = _make_loop(
            backend=backend, actions=actions, capture=FakeCapture(),
            workspace=tmp_path, approve=False,
        )
        result = await loop.run("denied")
        assert result.success is False
        assert "action_rejected" in result.last_message
        assert actions.dispatched == [], "no Win32 calls before rejection"

    @pytest.mark.asyncio
    async def test_iteration_cap_raises(self, tmp_path: Path):
        # 100 read-only actions, never `done` — the cap should fire.
        backend = FakeBackend(
            [{"action": "screenshot"}] * 100
        )
        loop = _make_loop(
            backend=backend, actions=FakeActions(_window()),
            capture=FakeCapture(), workspace=tmp_path,
            max_iterations=3,
        )
        with pytest.raises(ComputerUseSessionLimitExceeded):
            await loop.run("never finish")

    @pytest.mark.asyncio
    async def test_pause_hotkey_raises(self, tmp_path: Path):
        backend = FakeBackend([{"action": "click", "x": 1, "y": 1}])
        loop = _make_loop(
            backend=backend, actions=FakeActions(_window()),
            capture=FakeCapture(), workspace=tmp_path,
            pause=True,
        )
        with pytest.raises(ComputerUsePaused):
            await loop.run("paused")

    @pytest.mark.asyncio
    async def test_readonly_action_skips_permission_gate(
        self, tmp_path: Path
    ):
        # Even with approve=False, a `wait` should not be gated.
        backend = FakeBackend([
            {"action": "wait", "seconds": 0.0},
            {"action": "done", "summary": "ok"},
        ])
        loop = _make_loop(
            backend=backend, actions=FakeActions(_window()),
            capture=FakeCapture(), workspace=tmp_path,
            approve=False,
        )
        result = await loop.run("read-only path")
        assert result.success is True
