"""llama-server spawn + port capture tests.
VALIDATION test ID: 1-03-01
"""
from __future__ import annotations
import stat
import sys
from pathlib import Path
import pytest
from nyrahost.infer.gpu_probe import GpuBackend
from nyrahost.infer.llama_server import spawn_llama_server, PORT_RE


def _write_mock_llama(tmp_path: Path, *, port: int, delay_s: float, exit_code: int = 0) -> Path:
    """Write a Python script that mimics llama-server's startup line + blocks."""
    script = tmp_path / "mock_llama.py"
    script.write_text(
        "import sys, time\n"
        f"time.sleep({delay_s})\n"
        f"print('server listening at http://127.0.0.1:{port}')\n"
        "sys.stdout.flush()\n"
        f"if {exit_code} != 0:\n"
        f"    sys.exit({exit_code})\n"
        # Block indefinitely so the test controls lifetime
        "try:\n"
        "    while True:\n"
        "        time.sleep(10)\n"
        "except KeyboardInterrupt:\n"
        "    sys.exit(0)\n",
        encoding="utf-8",
    )
    return script


def _wrapper_bat(tmp_path: Path, script_py: Path) -> Path:
    """Create a shim so spawn_llama_server (which expects llama-server.exe) runs our python."""
    if sys.platform == "win32":
        bat = tmp_path / "llama-server.bat"
        bat.write_text(
            f'@echo off\r\n"{sys.executable}" "{script_py}" %*\r\n',
            encoding="utf-8",
        )
        return bat
    # POSIX: shebang wrapper
    wrapper = tmp_path / "llama-server"
    wrapper.write_text(
        f"#!/usr/bin/env bash\n{sys.executable} {script_py} \"$@\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return wrapper


@pytest.mark.asyncio
async def test_llama_server_port_capture(tmp_path: Path) -> None:
    script = _write_mock_llama(tmp_path, port=54321, delay_s=0.1)
    exe = _wrapper_bat(tmp_path, script)
    gguf = tmp_path / "fake.gguf"
    gguf.write_bytes(b"fake gguf contents")
    handle = await spawn_llama_server(
        exe_path=exe,
        gguf_path=gguf,
        backend=GpuBackend.CPU,
        startup_timeout_s=5.0,
    )
    try:
        assert handle.port == 54321
        assert handle.backend == GpuBackend.CPU
        assert handle.base_url == "http://127.0.0.1:54321"
    finally:
        await handle.terminate()


@pytest.mark.asyncio
async def test_llama_server_dies_before_port_raises(tmp_path: Path) -> None:
    # Mock that exits immediately with code 1 and NO port line
    script = tmp_path / "mock.py"
    script.write_text("import sys; sys.exit(1)\n", encoding="utf-8")
    exe = _wrapper_bat(tmp_path, script)
    gguf = tmp_path / "fake.gguf"
    gguf.write_bytes(b"x")
    with pytest.raises(RuntimeError):
        await spawn_llama_server(
            exe_path=exe,
            gguf_path=gguf,
            backend=GpuBackend.CPU,
            startup_timeout_s=2.0,
        )


def test_port_regex_matches_expected_llama_line() -> None:
    line = "server listening at http://127.0.0.1:41273 for embeddings"
    m = PORT_RE.search(line)
    assert m is not None
    assert int(m.group(1)) == 41273
