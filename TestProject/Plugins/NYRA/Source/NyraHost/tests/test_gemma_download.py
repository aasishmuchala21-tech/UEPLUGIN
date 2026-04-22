"""Gemma downloader tests.
VALIDATION test ID: 1-03-04
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import pytest
import httpx
from nyrahost.downloader.gemma import (
    GemmaDownloader,
    GemmaSpec,
    download_gemma,
    GEMMA_FILENAME,
)
from nyrahost.downloader.progress import (
    ProgressReporter,
    RATE_LIMIT_MS,
    RATE_LIMIT_BYTES,
)


@pytest.fixture
def fake_payload() -> bytes:
    # 5 MB payload
    return b"A" * (5 * 1024 * 1024)


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _mock_transport(
    *,
    primary_payload: bytes | None,
    mirror_payload: bytes | None,
    allow_range: bool = True,
):
    """Responds: GET primary -> primary_payload (supports Range if allow_range);
    GET mirror -> mirror_payload.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "primary" in url:
            if primary_payload is None:
                return httpx.Response(404)
            if allow_range and request.headers.get("Range"):
                rng = request.headers["Range"]
                start = int(rng.removeprefix("bytes=").split("-")[0])
                body = primary_payload[start:]
                return httpx.Response(
                    206,
                    content=body,
                    headers={
                        "Content-Length": str(len(body)),
                        "Content-Range": (
                            f"bytes {start}-{len(primary_payload) - 1}/"
                            f"{len(primary_payload)}"
                        ),
                    },
                )
            return httpx.Response(
                200,
                content=primary_payload,
                headers={"Content-Length": str(len(primary_payload))},
            )
        if "mirror" in url:
            if mirror_payload is None:
                return httpx.Response(500)
            return httpx.Response(
                200,
                content=mirror_payload,
                headers={"Content-Length": str(len(mirror_payload))},
            )
        return httpx.Response(404)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_sha256_verify_and_range_resume(
    tmp_path: Path, fake_payload: bytes, monkeypatch
) -> None:
    expected = _sha(fake_payload)
    dest = tmp_path / GEMMA_FILENAME
    partial = dest.with_suffix(dest.suffix + ".partial")

    # Write the first 1 MB to the partial file (simulating a prior interrupted download)
    partial.parent.mkdir(parents=True, exist_ok=True)
    partial.write_bytes(fake_payload[: 1024 * 1024])

    events: list[dict] = []

    async def emit(d: dict) -> None:
        events.append(d)

    # Patch httpx.AsyncClient to use our mock transport
    original = httpx.AsyncClient

    def make_client(*args, **kwargs):
        kwargs["transport"] = _mock_transport(
            primary_payload=fake_payload, mirror_payload=None,
        )
        return original(*args, **kwargs)

    monkeypatch.setattr(
        "nyrahost.downloader.gemma.httpx.AsyncClient", make_client,
    )

    spec = GemmaSpec(
        primary_url="http://primary/gemma.gguf",
        mirror_url="http://mirror/gemma.gguf",
        expected_sha256=expected,
        total_bytes_hint=len(fake_payload),
    )
    result = await download_gemma(
        spec=spec, dest_path=dest, emit_progress=emit,
    )
    assert result == dest
    assert dest.exists()
    assert _sha(dest.read_bytes()) == expected
    # No .partial left over
    assert not partial.exists()
    # At least one "downloading" event and exactly one "done"
    statuses = [e["status"] for e in events]
    assert "downloading" in statuses
    assert "verifying" in statuses
    assert statuses[-1] == "done"


@pytest.mark.asyncio
async def test_fallback_to_mirror_on_primary_404(
    tmp_path: Path, fake_payload: bytes, monkeypatch
) -> None:
    expected = _sha(fake_payload)
    dest = tmp_path / GEMMA_FILENAME
    events: list[dict] = []

    async def emit(d):
        events.append(d)

    original = httpx.AsyncClient

    def make_client(*args, **kwargs):
        kwargs["transport"] = _mock_transport(
            primary_payload=None, mirror_payload=fake_payload,
        )
        return original(*args, **kwargs)

    monkeypatch.setattr(
        "nyrahost.downloader.gemma.httpx.AsyncClient", make_client,
    )

    spec = GemmaSpec(
        primary_url="http://primary/gemma.gguf",
        mirror_url="http://mirror/gemma.gguf",
        expected_sha256=expected,
        total_bytes_hint=len(fake_payload),
    )
    await download_gemma(spec=spec, dest_path=dest, emit_progress=emit)
    assert dest.exists()
    assert _sha(dest.read_bytes()) == expected


@pytest.mark.asyncio
async def test_both_urls_fail_raises_and_emits_error_progress(
    tmp_path: Path, monkeypatch
) -> None:
    dest = tmp_path / GEMMA_FILENAME
    events: list[dict] = []

    async def emit(d):
        events.append(d)

    original = httpx.AsyncClient

    def make_client(*args, **kwargs):
        kwargs["transport"] = _mock_transport(
            primary_payload=None, mirror_payload=None,
        )
        return original(*args, **kwargs)

    monkeypatch.setattr(
        "nyrahost.downloader.gemma.httpx.AsyncClient", make_client,
    )

    spec = GemmaSpec(
        primary_url="http://primary/gemma.gguf",
        mirror_url="http://mirror/gemma.gguf",
        expected_sha256="ab" * 32,
    )
    with pytest.raises(RuntimeError):
        await download_gemma(
            spec=spec, dest_path=dest, emit_progress=emit,
        )
    # Last event is an error frame
    assert events[-1]["status"] == "error"
    assert "error" in events[-1]


@pytest.mark.asyncio
async def test_progress_rate_limited() -> None:
    events: list[dict] = []

    async def emit(d):
        events.append(d)

    r = ProgressReporter(
        emit=emit, asset="x", total_bytes=1_000_000_000,
    )
    # Hammer with 1000 tiny updates (< 1 ms apart) for well under
    # RATE_LIMIT_BYTES total
    for i in range(1000):
        await r.downloading(i * 1024)  # 1 KB steps
    # Expect exactly 1 event (only the first went through, since
    # rate-limit trips subsequently)
    assert len(events) == 1
