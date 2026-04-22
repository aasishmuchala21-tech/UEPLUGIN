"""Ollama auto-detect (D-18). Probes http://127.0.0.1:11434/api/tags.

Fast path: if Ollama is running AND has a gemma3:4b-it-qat-tagged model,
NyraHost sends chat requests there instead of spawning the bundled
llama-server. Saves 6-12s of cold start on every first request of a
session because the model is already resident in the user's GPU VRAM.

Never raises on connection failure — a missing Ollama is the normal case
for users who never installed it. Graceful-degrade to None triggers the
bundled-llama-server branch in router.py.
"""
from __future__ import annotations

from typing import Optional

import httpx
import structlog

log = structlog.get_logger("nyrahost.ollama")

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
# Match any Ollama tag that starts with gemma3:4b-it-qat — model names
# include ":" suffix for variants (e.g. gemma3:4b-it-qat:q4_0).
GEMMA_TAG_PREFIX = "gemma3:4b-it-qat"


async def detect_ollama(
    *,
    client: httpx.AsyncClient | None = None,
    timeout: float = 1.0,
) -> Optional[str]:
    """Return base URL if Ollama is reachable AND has a matching Gemma 3 tag.

    Never raises on connection failure — returns None and logs instead,
    so callers (router.py) can fall through to the bundled-llama-server
    branch without a try/except.
    """
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=timeout)
    try:
        r = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
        if r.status_code != 200:
            log.info("ollama_probe_non_200", status=r.status_code)
            return None
        data = r.json()
        for m in data.get("models", []) or []:
            name = m.get("name", "") or ""
            if name.startswith(GEMMA_TAG_PREFIX):
                log.info("ollama_detected", model=name)
                return OLLAMA_BASE_URL
        log.info("ollama_running_but_no_gemma")
        return None
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError) as e:
        log.info("ollama_probe_failed", err=type(e).__name__)
        return None
    finally:
        if owns_client:
            await client.aclose()
