"""Entry point for `python -m nyrahost`.

Parses CLI args, configures structlog JSON logging (D-16), cleans up
orphan handshake files left by a dead previous editor (P1.2), then
awaits the asyncio WS server forever (until SIGINT or shutdown
notification from UE).

Plan 08 extends the CLI with --project-dir and --plugin-binaries-dir so
``app.build_and_run`` can wire Storage + InferRouter + ChatHandlers
around :func:`server.run_server`.
"""
from __future__ import annotations
import argparse
import asyncio
import os
import sys
from pathlib import Path

from .app import build_and_run
from .config import NyraConfig
from .handshake import cleanup_orphan_handshakes
from .logging_setup import configure_logging


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="nyrahost")
    p.add_argument("--editor-pid", type=int, required=True)
    p.add_argument("--log-dir", type=Path, required=True)
    p.add_argument(
        "--project-dir",
        type=Path,
        required=True,
        help=(
            "Path to <ProjectDir>; used for Saved/NYRA/sessions.db "
            "and Saved/NYRA/models/"
        ),
    )
    p.add_argument(
        "--plugin-binaries-dir",
        type=Path,
        required=True,
        help=(
            "Path to <Plugin>/Binaries/Win64; used for "
            "NyraInfer/<backend>/llama-server.exe lookup"
        ),
    )
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

    await build_and_run(
        config=config,
        nyrahost_pid=os.getpid(),
        project_dir=args.project_dir,
        plugin_binaries_dir=args.plugin_binaries_dir,
    )
    return 0


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(main_async(args))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
