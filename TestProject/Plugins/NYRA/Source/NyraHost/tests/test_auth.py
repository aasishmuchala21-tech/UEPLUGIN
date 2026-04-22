"""Auth + first-frame gate tests.
VALIDATION test ID: 1-02-04
"""
from __future__ import annotations
import asyncio
import json
import secrets
from pathlib import Path

import pytest
import websockets

from nyrahost.config import NyraConfig
from nyrahost.server import run_server


async def _start_server(tmp_path: Path, *, token: str) -> tuple[int, asyncio.Task]:
    """Start NyraServer on an ephemeral port and return (port, task).

    Monkey-patches nyrahost.server.secrets.token_bytes to inject a known
    token so the test can predict what UE's session/authenticate frame
    must carry.
    """
    config = NyraConfig(
        editor_pid=99999,
        log_dir=tmp_path / "logs",
        handshake_dir=tmp_path / "NYRA",
    )
    import nyrahost.server as server_mod

    original = server_mod.secrets.token_bytes
    server_mod.secrets.token_bytes = lambda n: bytes.fromhex(token)  # type: ignore[attr-defined]
    try:
        task = asyncio.create_task(run_server(config, nyrahost_pid=12345))
        # Wait for handshake file
        handshake = config.handshake_dir / f"handshake-{config.editor_pid}.json"
        for _ in range(50):
            if handshake.exists():
                break
            await asyncio.sleep(0.05)
        else:
            raise RuntimeError("handshake file never appeared")
        data = json.loads(handshake.read_text())
        return data["port"], task
    finally:
        server_mod.secrets.token_bytes = original


@pytest.mark.asyncio
async def test_auth_rejects_bad_token(tmp_path: Path) -> None:
    good_token_bytes = secrets.token_bytes(32)
    good_token_hex = good_token_bytes.hex()
    port, task = await _start_server(tmp_path, token=good_token_hex)
    try:
        uri = f"ws://127.0.0.1:{port}/"
        async with websockets.connect(uri) as ws:
            bad_frame = json.dumps({
                "jsonrpc": "2.0", "id": 1,
                "method": "session/authenticate",
                "params": {"token": "00" * 32},
            })
            await ws.send(bad_frame)
            # Expect close with code 4401
            try:
                await asyncio.wait_for(ws.recv(), timeout=2.0)
                pytest.fail("Server should have closed the connection")
            except websockets.exceptions.ConnectionClosed as e:
                assert e.code == 4401
                assert e.reason == "unauthenticated"
    finally:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


@pytest.mark.asyncio
async def test_auth_rejects_first_method_not_authenticate(tmp_path: Path) -> None:
    good_token_hex = secrets.token_bytes(32).hex()
    port, task = await _start_server(tmp_path, token=good_token_hex)
    try:
        async with websockets.connect(f"ws://127.0.0.1:{port}/") as ws:
            # Send session/hello as FIRST frame — must be rejected
            await ws.send(json.dumps({
                "jsonrpc": "2.0", "id": 1,
                "method": "session/hello", "params": {},
            }))
            try:
                await asyncio.wait_for(ws.recv(), timeout=2.0)
                pytest.fail("Server should have closed")
            except websockets.exceptions.ConnectionClosed as e:
                assert e.code == 4401
    finally:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


@pytest.mark.asyncio
async def test_auth_accepts_valid_token_and_session_hello(tmp_path: Path) -> None:
    good_token_hex = secrets.token_bytes(32).hex()
    port, task = await _start_server(tmp_path, token=good_token_hex)
    try:
        async with websockets.connect(f"ws://127.0.0.1:{port}/") as ws:
            await ws.send(json.dumps({
                "jsonrpc": "2.0", "id": 1,
                "method": "session/authenticate",
                "params": {"token": good_token_hex},
            }))
            reply = json.loads(await ws.recv())
            assert reply["id"] == 1
            assert reply["result"]["authenticated"] is True
            assert isinstance(reply["result"]["session_id"], str)

            await ws.send(json.dumps({
                "jsonrpc": "2.0", "id": 2,
                "method": "session/hello", "params": {},
            }))
            hello = json.loads(await ws.recv())
            assert hello["id"] == 2
            assert hello["result"]["backends"] == ["gemma-local"]
            assert hello["result"]["phase"] == 1
            assert isinstance(hello["result"]["session_id"], str)
    finally:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
