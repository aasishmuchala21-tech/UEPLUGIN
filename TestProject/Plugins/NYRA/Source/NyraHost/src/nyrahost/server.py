"""asyncio WebSocket server with first-frame auth gate.

See docs/JSONRPC.md §3.1 + docs/HANDSHAKE.md. Implements:
  - D-04: eager bind on module-load (caller invokes run_server from __main__)
  - D-06: write handshake file AFTER port is assigned (via handshake.write_handshake)
  - D-07: 32-byte token + first-frame gate; reject with WS close code 4401
  - D-10: session/authenticate + session/hello on the default request surface
  - Extension points register_request / register_notification for Plans 07/08/09

Ring 0 gate: this module is the authentication boundary — NyraHost rejects
anything that is not a well-formed session/authenticate frame carrying the
correct token on the first WS message. Subsequent frames are dispatched
through request_handlers / notification_handlers after session.authenticated
flips True.
"""
from __future__ import annotations
import asyncio
import secrets
from typing import Awaitable, Callable

import structlog
import websockets
from websockets.exceptions import ConnectionClosed
from websockets.server import ServerConnection

from .config import NyraConfig
from .handshake import handshake_file_path, write_handshake
from .jsonrpc import (
    NotificationEnvelope,
    ProtocolError,
    RequestEnvelope,
    build_error,
    build_response,
    parse_envelope,
)
from .session import SessionState

log = structlog.get_logger("nyrahost.server")

AUTH_CLOSE_CODE = 4401
AUTH_CLOSE_REASON = "unauthenticated"

# Handler hooks — extension points Plans 07/08/09 bind to.
# Each takes (params, session) and returns result dict or raises.
RequestHandler = Callable[[dict, SessionState], Awaitable[dict]]
NotificationHandler = Callable[[dict, SessionState], Awaitable[None]]


class NyraServer:
    def __init__(self, config: NyraConfig, auth_token: str):
        self.config = config
        self.auth_token = auth_token
        self.request_handlers: dict[str, RequestHandler] = {
            "session/hello": self._on_session_hello,
        }
        self.notification_handlers: dict[str, NotificationHandler] = {}

    def register_request(self, method: str, handler: RequestHandler) -> None:
        self.request_handlers[method] = handler

    def register_notification(
        self, method: str, handler: NotificationHandler
    ) -> None:
        self.notification_handlers[method] = handler

    async def _on_session_hello(
        self, params: dict, session: SessionState
    ) -> dict:
        return {
            "backends": ["gemma-local"],
            "phase": 1,
            "session_id": session.session_id,
        }

    async def _handle_connection(self, ws: ServerConnection) -> None:
        session = SessionState()
        # --- First frame gate: MUST be session/authenticate with correct token ---
        try:
            first_frame = await asyncio.wait_for(ws.recv(), timeout=10.0)
        except (asyncio.TimeoutError, ConnectionClosed):
            log.warning("auth_no_first_frame")
            return
        try:
            env = parse_envelope(
                first_frame
                if isinstance(first_frame, str)
                else first_frame.decode("utf-8")
            )
        except ProtocolError as e:
            await ws.close(AUTH_CLOSE_CODE, AUTH_CLOSE_REASON)
            log.warning("auth_bad_envelope", err=str(e))
            return
        if (
            not isinstance(env, RequestEnvelope)
            or env.method != "session/authenticate"
        ):
            await ws.close(AUTH_CLOSE_CODE, AUTH_CLOSE_REASON)
            log.warning(
                "auth_first_method_not_authenticate",
                got=getattr(env, "method", None),
            )
            return
        client_token = env.params.get("token", "")
        if not isinstance(client_token, str) or not secrets.compare_digest(
            client_token, self.auth_token
        ):
            await ws.close(AUTH_CLOSE_CODE, AUTH_CLOSE_REASON)
            log.warning("auth_token_mismatch")
            return
        session.authenticated = True
        # Attach the websocket to the session so request handlers (e.g.
        # Plan 08's chat/send) can emit chat/stream notifications on the
        # same connection without re-plumbing the dispatch signature.
        # See app.py::_wrap_send for the reader side. Plan 06's tests
        # don't exercise this field, so the wire behaviour is unchanged
        # for session/hello callers.
        session._ws = ws  # type: ignore[attr-defined]
        await ws.send(
            build_response(
                env.id,
                {
                    "authenticated": True,
                    "session_id": session.session_id,
                },
            )
        )
        log.info("auth_ok", session_id=session.session_id)

        # --- Main dispatch loop ---
        try:
            async for raw in ws:
                await self._dispatch(ws, raw, session)
        except ConnectionClosed:
            log.info("ws_closed", session_id=session.session_id)

    async def _dispatch(
        self, ws: ServerConnection, raw, session: SessionState
    ) -> None:
        frame = raw if isinstance(raw, str) else raw.decode("utf-8")
        try:
            env = parse_envelope(frame)
        except ProtocolError as e:
            log.warning("dispatch_bad_envelope", err=str(e))
            return
        if isinstance(env, RequestEnvelope):
            handler = self.request_handlers.get(env.method)
            if handler is None:
                await ws.send(
                    build_error(
                        env.id,
                        code=-32601,
                        message="method_not_found",
                        remediation=f"Unknown method: {env.method}",
                    )
                )
                return
            try:
                result = await handler(env.params, session)
                await ws.send(build_response(env.id, result))
            except Exception:  # noqa: BLE001
                log.exception("handler_exception", method=env.method)
                await ws.send(
                    build_error(
                        env.id,
                        code=-32001,
                        message="subprocess_failed",
                        remediation=(
                            "A background NYRA process stopped unexpectedly. "
                            "Click [Restart] or see Saved/NYRA/logs/."
                        ),
                    )
                )
        elif isinstance(env, NotificationEnvelope):
            handler = self.notification_handlers.get(env.method)
            if handler is not None:
                try:
                    await handler(env.params, session)
                except Exception:  # noqa: BLE001
                    log.exception(
                        "notification_handler_exception", method=env.method
                    )


async def run_server(
    config: NyraConfig,
    *,
    nyrahost_pid: int,
    register_handlers: Callable[[NyraServer], None] | None = None,
) -> None:
    """Bind WS server on 127.0.0.1:<ephemeral>, write handshake, serve forever."""
    token = secrets.token_bytes(config.auth_token_bytes).hex()
    server_obj = NyraServer(config, auth_token=token)
    if register_handlers:
        register_handlers(server_obj)

    ws_server = await websockets.serve(
        server_obj._handle_connection,
        config.bind_host,
        config.bind_port,
        ping_interval=config.ws_ping_interval_s,
        ping_timeout=config.ws_ping_timeout_s,
        max_size=config.ws_max_frame_bytes,
    )
    assigned_port = ws_server.sockets[0].getsockname()[1]
    log.info("ws_bound", host=config.bind_host, port=assigned_port)

    write_handshake(
        config.handshake_dir,
        port=assigned_port,
        token=token,
        nyrahost_pid=nyrahost_pid,
        ue_pid=config.editor_pid,
    )
    log.info(
        "handshake_written",
        path=str(
            handshake_file_path(config.handshake_dir, config.editor_pid)
        ),
    )

    await ws_server.serve_forever()
