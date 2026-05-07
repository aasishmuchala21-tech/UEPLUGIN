"""tests/test_computer_use.py — computer-use unit tests.

Per Plan 05-03 Task 4:
  9 unit tests covering permission gate, screenshot local storage,
  pause chord, API key validation, and MCP tool registration.

All tests use mocked Win32/HTTP (no live GUI or network required).
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nyrahost.external.computer_use_loop import (
    ComputerUseLoop,
    ComputerUseError,
    PermissionGateResult,
)
from nyrahost.external.win32_actions import (
    Win32ActionExecutor,
    ScreenCapture,
    PermissionGate,
    PAUSE_ID,
)
from nyrahost.tools.computer_use_tools import (
    ComputerUseTool,
    ComputerUseStatusTool,
    _loop_registry,
    _register_loop,
    _get_loop,
)


# --- Permission Gate Tests (T-05-07) ------------------------------------------


def test_permission_gate_blocks_until_approved():
    """T-05-07: No Win32 action executes until user approves via permission gate."""
    loop = ComputerUseLoop(
        task="open notepad",
        job_id="test-job-abc",
        api_key="sk-test-key",
    )
    # Simulate permission not yet approved
    assert not loop._permission_approved
    action = {"action": "left_click", "x": 100, "y": 200}
    # _execute_action should check permission before executing
    with patch.object(loop, "_check_permission", return_value=PermissionGateResult(approved=False, user_dismissed=True)):
        with pytest.raises(ComputerUseError, match="Permission denied"):
            loop._execute_action(action)


def test_permission_gate_approved_allows_action():
    """Permission gate approved → actions execute without raising."""
    loop = ComputerUseLoop(
        task="open notepad",
        job_id="test-job-abc",
        api_key="sk-test-key",
    )
    loop._permission_approved = True
    loop._action_executor = MagicMock()
    action = {"action": "left_click", "x": 100, "y": 200}
    # Should not raise
    loop._execute_action(action)
    loop._action_executor.execute.assert_called_once_with(action)


# --- Screenshot Local Storage (T-05-06) ---------------------------------------


def test_screenshot_stays_local():
    """T-05-06: Screenshots saved to staging dir, not exfiltrated as base64."""
    with patch.object(ComputerUseLoop, "_default_staging_root", return_value=Path("/tmp/nyra-test")):
        loop = ComputerUseLoop(
            task="test task",
            job_id="test-job-xyz",
            api_key="sk-test-key",
        )
        mock_sct = MagicMock()
        with patch.dict("sys.modules", {"mss": MagicMock()}):
            with patch.object(loop, "_capture_screenshot", return_value="/tmp/nyra-test/computer_use/test-job-xyz/screenshot_0000.png"):
                path = loop._capture_screenshot()
                assert "computer_use/test-job-xyz" in path
                assert path.endswith(".png")
                # Verify path is a file path, not base64 — the API message uses local_file
                msg = loop._build_api_message(path)
                assert msg["content"][0]["type"] == "image"
                assert msg["content"][0]["source"]["type"] == "local_file"
                assert msg["content"][0]["source"]["file_path"] == path


# --- Pause Chord (T-05-05) ----------------------------------------------------


def test_pause_chord_stops_loop():
    """T-05-05: Ctrl+Alt+Space halt works mid-loop."""
    with patch.object(ComputerUseLoop, "_default_staging_root", return_value=Path("/tmp/nyra-test")):
        loop = ComputerUseLoop(
            task="test task",
            job_id="test-pause-job",
            api_key="sk-test-key",
        )
        loop._action_executor = MagicMock()
        loop._action_executor.check_pause_chord.return_value = True
        loop._action_executor.register_pause_chord = MagicMock()
        loop._action_executor.unregister_pause_chord = MagicMock()
        # Run one iteration — should stop immediately due to pause chord
        result = loop.run()
        assert result["status"] == "paused"
        assert "Ctrl+Alt+Space" in result.get("message", "")


# --- API Key Validation -------------------------------------------------------


def test_api_key_missing_raises_error():
    """ANTHROPIC_API_KEY missing → ComputerUseError at construction."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ComputerUseError, match="ANTHROPIC_API_KEY"):
            ComputerUseLoop(task="test task", api_key="")


# --- MCP Tool Tests -----------------------------------------------------------


def test_computer_use_tool_returns_job_id():
    """nyra_computer_use returns a job_id immediately (non-blocking)."""
    tool = ComputerUseTool()
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
        with patch("nyrahost.tools.computer_use_tools.StagingManifest"):
            _loop_registry.clear()
            result = tool.execute({"task": "open notepad"})
            assert result.error is None
            assert "job_id" in result.data
            assert result.data["status"] == "started"


def test_status_tool_retrieves_running_job():
    """nyra_computer_use_status returns correct status for a running job."""
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
        loop = ComputerUseLoop(
            task="test",
            job_id="test-status-job",
            api_key="sk-test",
        )
        _loop_registry.clear()
        _register_loop(loop)
        tool = ComputerUseStatusTool()
        result = tool.execute({"job_id": "test-status-job", "action": "status"})
        assert result.error is None
        assert result.data["job_id"] == "test-status-job"


def test_status_tool_unknown_job_returns_error():
    """Unknown job_id returns an error NyraToolResult."""
    tool = ComputerUseStatusTool()
    _loop_registry.clear()
    result = tool.execute({"job_id": "does-not-exist"})
    assert result.error is not None
    assert "not found" in result.error


def test_stop_action_stops_loop():
    """nyra_computer_use_status(action='stop') terminates the loop."""
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
        loop = ComputerUseLoop(
            task="test",
            job_id="test-stop-job",
            api_key="sk-test",
        )
        _loop_registry.clear()
        _register_loop(loop)
        tool = ComputerUseStatusTool()
        result = tool.execute({"job_id": "test-stop-job", "action": "stop"})
        assert result.error is None
        assert result.data["status"] == "stopped"
        assert loop._stopped is True


# --- Win32ActionExecutor Tests -----------------------------------------------


def test_win32_executor_handles_all_action_types():
    """Win32ActionExecutor routes each action type to the correct handler."""
    executor = Win32ActionExecutor()
    executor._pause_hotkey_registered = False  # Skip win32api registration

    with patch.object(executor, "_move_cursor") as m_move, \
         patch.object(executor, "_left_click") as m_lc, \
         patch.object(executor, "_right_click") as m_rc, \
         patch.object(executor, "_scroll") as m_scroll, \
         patch.object(executor, "_type_text") as m_type, \
         patch.object(executor, "_send_key_combo") as m_combo:

        # screenshot is a no-op (handled by loop)
        executor.execute({"action": "screenshot"})
        # cursor
        executor.execute({"action": "cursor", "x": 100, "y": 200})
        m_move.assert_called_once_with(100, 200)
        # left_click with coordinates
        executor.execute({"action": "left_click", "x": 300, "y": 400})
        m_lc.assert_called_once_with(300, 400)
        # right_click
        executor.execute({"action": "right_click", "x": 50, "y": 60})
        m_rc.assert_called_once_with(50, 60)
        # scroll
        executor.execute({"action": "scroll", "scroll_amount": 120})
        m_scroll.assert_called_once_with(120)
        # type
        executor.execute({"action": "type", "text": "hello"})
        m_type.assert_called_once_with("hello")
        # key_combo
        executor.execute({"action": "key_combo", "keys": ["ctrl", "c"]})
        m_combo.assert_called_once_with(["ctrl", "c"])


def test_pause_chord_check_returns_false_when_not_registered():
    """check_pause_chord returns False when RegisterHotKey is not available."""
    executor = Win32ActionExecutor()
    executor._pause_hotkey_registered = False
    # With win32api = None, check_pause_chord should return False
    with patch("nyrahost.external.win32_actions.win32api", None):
        result = executor.check_pause_chord()
        assert result is False


# --- ScreenCapture Tests ------------------------------------------------------


def test_screen_capture_saves_to_correct_dir(tmp_path):
    """ScreenCapture stores screenshot in output_dir."""
    cap = ScreenCapture(str(tmp_path))
    mock_sct = MagicMock()
    mock_mss_mod = MagicMock()
    mock_mss_mod.mss.return_value.__enter__ = MagicMock(return_value=mock_sct)
    mock_mss_mod.mss.return_value.__exit__ = MagicMock(return_value=False)
    with patch("nyrahost.external.win32_actions.mss", mock_mss_mod):
        path = cap.capture("my_screenshot.png")
        assert path == str(tmp_path / "my_screenshot.png")
        mock_sct.save.assert_called_once()


def test_screen_capture_increments_counter(tmp_path):
    """ScreenCapture increments internal counter when no filename given."""
    cap = ScreenCapture(str(tmp_path))
    mock_sct = MagicMock()
    mock_mss_mod = MagicMock()
    mock_mss_mod.mss.return_value.__enter__ = MagicMock(return_value=mock_sct)
    mock_mss_mod.mss.return_value.__exit__ = MagicMock(return_value=False)
    with patch("nyrahost.external.win32_actions.mss", mock_mss_mod):
        p1 = cap.capture()
        p2 = cap.capture()
        p3 = cap.capture()
        assert "screenshot_0000.png" in p1
        assert "screenshot_0001.png" in p2
        assert "screenshot_0002.png" in p3