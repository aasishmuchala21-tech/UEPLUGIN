"""Ollama auto-detect tests.
VALIDATION test ID: 1-03-02
"""
from __future__ import annotations
import pytest
import httpx
from nyrahost.infer.ollama_probe import detect_ollama, OLLAMA_BASE_URL, GEMMA_TAG_PREFIX


def _transport_returning(payload: dict, status: int = 200) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(status, json=payload)
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_ollama_detect_gemma3_present() -> None:
    transport = _transport_returning({
        "models": [
            {"name": "llama3:8b", "details": {}},
            {"name": "gemma3:4b-it-qat", "details": {"family": "gemma"}},
        ]
    })
    async with httpx.AsyncClient(transport=transport) as c:
        url = await detect_ollama(client=c)
    assert url == OLLAMA_BASE_URL


@pytest.mark.asyncio
async def test_ollama_detect_absent_returns_none() -> None:
    transport = _transport_returning({
        "models": [{"name": "llama3:8b", "details": {}}]
    })
    async with httpx.AsyncClient(transport=transport) as c:
        url = await detect_ollama(client=c)
    assert url is None


@pytest.mark.asyncio
async def test_ollama_detect_connection_refused_returns_none() -> None:
    def raise_connect(_req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")
    transport = httpx.MockTransport(raise_connect)
    async with httpx.AsyncClient(transport=transport) as c:
        url = await detect_ollama(client=c)
    assert url is None


@pytest.mark.asyncio
async def test_ollama_detect_non_200_returns_none() -> None:
    transport = _transport_returning({}, status=503)
    async with httpx.AsyncClient(transport=transport) as c:
        url = await detect_ollama(client=c)
    assert url is None


def test_tag_prefix_constant() -> None:
    assert GEMMA_TAG_PREFIX == "gemma3:4b-it-qat"
