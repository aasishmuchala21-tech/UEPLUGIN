"""Entry point for `python -m nyrahost`.

Parses CLI args, configures structlog JSON logging (D-16), cleans up
orphan handshake files left by a dead previous editor (P1.2), then
awaits the asyncio WS server forever (until SIGINT or shutdown
notification from UE).
"""
from __future__ import annotations
import argparse
import asyncio
import os
import sys
from pathlib import Path

from .config import NyraConfig
from .handshake import cleanup_orphan_handshakes
from .logging_setup import configure_logging
from .server import run_server


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="nyrahost")
    p.add_argument("--editor-pid", type=int, required=True)
    p.add_argument("--log-dir", type=Path, required=True)
    p.add_argument("--handshake-dir", type=Path, default=None)
    return p.parse_args()


async def main_async(args: argparse.Namespace) -> int:
    handshake_dir = args.handshake_dir or NyraConfig.default_handshake_dir()
    config = NyraConfig(
        editor_pid=args.editor_pid,
        log_dir=args.log_dir,
        handshake_dir=handshake_dir,
    )
    configure_logging(config.log_dir)

    # Clean up dead-editor handshakes before claiming our own slot (P1.2)
    cleanup_orphan_handshakes(handshake_dir)

    await run_server(config, nyrahost_pid=os.getpid())
    return 0


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(main_async(args))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
