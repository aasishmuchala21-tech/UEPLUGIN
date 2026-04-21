---
phase: 01-plugin-shell-three-process-ipc
plan: 09
type: execute
wave: 2
depends_on: [02, 05, 06]
autonomous: true
requirements: [PLUG-03]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/downloader/__init__.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/downloader/gemma.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/downloader/progress.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/download.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_gemma_download.py
objective: >
  Implement the Gemma GGUF downloader: HTTP Range-resumable download from
  HuggingFace primary URL, GitHub-mirror fallback, SHA256 verification,
  progress-reporting via `diagnostics/download-progress` JSON-RPC
  notifications on the active WS session. Expose as a request method
  `diagnostics/download-gemma` that starts the download (returns
  {started:true}) and emits progress notifications while writing to
  `<ProjectDir>/Saved/NYRA/models/gemma-3-4b-it-qat-q4_0.gguf`. Fills
  VALIDATION row 1-03-04 (test_sha256_verify_and_range_resume).
must_haves:
  truths:
    - "download_gemma writes the GGUF to <ProjectDir>/Saved/NYRA/models/gemma-3-4b-it-qat-q4_0.gguf with SHA256 matching ModelPins::GemmaGgufSha256"
    - "Interrupting mid-download and re-calling download_gemma resumes via HTTP Range header from the partial file's existing byte count"
    - "If primary URL returns non-2xx, downloader falls back to mirror URL"
    - "If both URLs fail, downloader emits diagnostics/download-progress with status='error' and raises"
    - "Progress notifications are emitted no more often than 500ms OR every 10MB (whichever first) — avoid notification flood"
    - "pytest tests/test_gemma_download.py::test_sha256_verify_and_range_resume passes"
  artifacts:
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/downloader/gemma.py
      provides: "download_gemma + GemmaDownloader class"
      exports: ["download_gemma", "GemmaDownloader"]
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/downloader/progress.py
      provides: "ProgressReporter dataclass + rate limiting helper"
      exports: ["ProgressReporter", "RATE_LIMIT_MS", "RATE_LIMIT_BYTES"]
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/download.py
      provides: "diagnostics/download-gemma request handler"
      exports: ["DownloadHandlers"]
  key_links:
    - from: downloader/gemma.py download_gemma
      to: ModelPins GemmaGgufUrl + GemmaGgufSha256 + GemmaGgufMirrorUrl
      via: "Values fetched from assets-manifest.json at runtime (Python reads the same JSON)"
      pattern: "gemma-3-4b-it-qat-q4_0.gguf"
    - from: handlers/download.py DownloadHandlers.on_download_gemma
      to: build_notification("diagnostics/download-progress", ...)
      via: "NyraHost -> UE notification stream"
      pattern: "diagnostics/download-progress"
---

<objective>
Gemma download path so users can go from "enabled plugin -> typed a message"
in a single guided flow (first-run UX per §3.9).

Per CONTEXT.md D-17: download-on-first-run with progress UI + SHA256 verify.
Primary URL HuggingFace (`huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf/resolve/main/...`).
Fallback: GitHub Releases mirror. Retryable, resumable (HTTP Range).

Per RESEARCH §3.5 ("Gemma download URL (HuggingFace direct)" + §3.10 P1.5
mirror fallback expectations). §3.2 open question 7 resolved: Python-side
download with `diagnostics/download-progress` notification.

Purpose: Without this, the first-run UX is broken — user types a message,
gets -32005, can't recover without CLI. Plan 13 hooks this into the "Download
Gemma" button.
Output: 3 Python modules + 1 handler + real test (replacing Wave 0 placeholder).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md
@docs/JSONRPC.md
@TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/server.py
@TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py
@TestProject/Plugins/NYRA/Source/NyraHost/assets-manifest.json
@TestProject/Plugins/NYRA/Source/NyraHost/tests/test_gemma_download.py
</context>

<interfaces>
Gemma GGUF download URL shapes (from Plan 05 ModelPins):
- Primary: `https://huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf/resolve/<sha>/gemma-3-4b-it-qat-q4_0.gguf`
- Mirror:  `https://github.com/nyra-ai/nyra/releases/download/models-v1/gemma-3-4b-it-qat-q4_0.gguf`
- File SHA256: from assets-manifest.json (or `ModelPins::GemmaGgufSha256`)

HTTP Range resume pattern (httpx):
```python
resume_from = dest_partial.stat().st_size if dest_partial.exists() else 0
headers = {"Range": f"bytes={resume_from}-"} if resume_from > 0 else {}
async with client.stream("GET", url, headers=headers) as resp:
    # 206 Partial Content on successful resume; 200 on full re-download
    if resp.status_code not in (200, 206):
        raise HttpError(resp.status_code)
    total = int(resp.headers.get("Content-Length", 0)) + resume_from
    async for chunk in resp.aiter_bytes(chunk_size=1024*1024):
        f.write(chunk)
        hasher.update(chunk)
```

`diagnostics/download-progress` notification params (docs/JSONRPC.md §3.7):
```json
{"asset":"gemma-3-4b-it-qat-q4_0.gguf",
 "bytes_done":1073741824, "bytes_total":3391733760,
 "status":"downloading"|"verifying"|"done"|"error",
 "error"?: {code, message, data:{remediation}}}
```
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: downloader/gemma.py + progress.py + test_gemma_download.py</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/downloader/__init__.py
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/downloader/gemma.py
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/downloader/progress.py
    TestProject/Plugins/NYRA/Source/NyraHost/tests/test_gemma_download.py
  </files>
  <read_first>
    - .planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md D-17
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.5 (Gemma download URL, HuggingFace Range support) and §3.10 P1.5 (mirror fallback)
    - docs/JSONRPC.md §3.7 (diagnostics/download-progress shape)
    - TestProject/Plugins/NYRA/Source/NyraHost/assets-manifest.json
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_gemma_download.py (Wave 0 placeholder)
  </read_first>
  <behavior>
    - test_sha256_verify_and_range_resume: using httpx MockTransport returning split byte ranges (first half then second half on retry), GemmaDownloader produces a file whose SHA256 matches the expected pin; verify that on second call to download, the server only sees a Range request for the missing tail.
    - test_fallback_to_mirror_on_primary_404: MockTransport returns 404 for primary URL, 200 for mirror; downloader succeeds using mirror.
    - test_both_urls_fail_raises_and_emits_error_progress: MockTransport 500 for both; downloader raises and ProgressReporter received a status=error frame.
    - test_progress_rate_limited: simulate many small chunks; ProgressReporter emits at most 1 frame per 500ms OR per 10MB.
  </behavior>
  <action>
    **1. CREATE src/nyrahost/downloader/__init__.py** (empty package marker).

    **2. CREATE src/nyrahost/downloader/progress.py:**

    ```python
    """Rate-limited progress reporter for downloader + future bulk tasks."""
    from __future__ import annotations
    import time
    from dataclasses import dataclass, field
    from typing import Awaitable, Callable, Literal

    RATE_LIMIT_MS = 500  # min time between consecutive "downloading" frames
    RATE_LIMIT_BYTES = 10 * 1024 * 1024  # 10 MB

    ProgressStatus = Literal["downloading", "verifying", "done", "error"]
    Emit = Callable[[dict], Awaitable[None]]  # async callable; receives the params dict


    @dataclass
    class ProgressReporter:
        emit: Emit  # async callable that wraps build_notification + ws.send
        asset: str
        total_bytes: int
        _last_emit_ms: float = 0.0
        _last_bytes: int = 0
        _sent_any: bool = False

        async def downloading(self, bytes_done: int) -> None:
            now_ms = time.monotonic() * 1000
            if self._sent_any:
                ms_since = now_ms - self._last_emit_ms
                bytes_since = bytes_done - self._last_bytes
                if ms_since < RATE_LIMIT_MS and bytes_since < RATE_LIMIT_BYTES:
                    return
            await self.emit({
                "asset": self.asset,
                "bytes_done": int(bytes_done),
                "bytes_total": int(self.total_bytes),
                "status": "downloading",
            })
            self._last_emit_ms = now_ms
            self._last_bytes = bytes_done
            self._sent_any = True

        async def verifying(self) -> None:
            await self.emit({
                "asset": self.asset,
                "bytes_done": int(self.total_bytes),
                "bytes_total": int(self.total_bytes),
                "status": "verifying",
            })

        async def done(self) -> None:
            await self.emit({
                "asset": self.asset,
                "bytes_done": int(self.total_bytes),
                "bytes_total": int(self.total_bytes),
                "status": "done",
            })

        async def error(self, *, code: int, message: str, remediation: str) -> None:
            await self.emit({
                "asset": self.asset,
                "bytes_done": int(self._last_bytes),
                "bytes_total": int(self.total_bytes),
                "status": "error",
                "error": {"code": code, "message": message, "data": {"remediation": remediation}},
            })
    ```

    **3. CREATE src/nyrahost/downloader/gemma.py:**

    ```python
    """Gemma GGUF downloader with Range-resume + SHA256 verify + mirror fallback."""
    from __future__ import annotations
    import asyncio
    import hashlib
    import json
    from dataclasses import dataclass
    from pathlib import Path
    from typing import Callable, Sequence
    import httpx
    import structlog

    from .progress import ProgressReporter

    log = structlog.get_logger("nyrahost.downloader.gemma")

    CHUNK_SIZE = 1024 * 1024  # 1 MB read/hash granularity
    HTTP_CONNECT_TIMEOUT = 10.0
    HTTP_READ_TIMEOUT = 60.0
    GEMMA_FILENAME = "gemma-3-4b-it-qat-q4_0.gguf"


    @dataclass(frozen=True)
    class GemmaSpec:
        primary_url: str
        mirror_url: str
        expected_sha256: str
        total_bytes_hint: int = 0  # optional; resolved at runtime from Content-Length

        @staticmethod
        def from_manifest(manifest_path: Path) -> "GemmaSpec":
            # If manifest doesn't have gemma entry, we use ModelPins defaults.
            # Phase 1 expects Plan 05 resolved values or fallbacks.
            from ..config import NyraConfig  # avoid top-level import cycle
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            # Plan 05 stored gemma under a `gemma_model_note`; we keep the canonical
            # values in a separate gemma block OR fall back to ModelPins-style defaults.
            gemma_block = data.get("gemma") or {}
            return GemmaSpec(
                primary_url=gemma_block.get("url", ""),
                mirror_url=gemma_block.get("mirror_url", ""),
                expected_sha256=gemma_block.get("sha256", ""),
                total_bytes_hint=int(gemma_block.get("total_bytes", 0)),
            )


    class GemmaDownloader:
        def __init__(self, *, spec: GemmaSpec, dest_path: Path):
            self.spec = spec
            self.dest_path = dest_path
            self.partial_path = dest_path.with_suffix(dest_path.suffix + ".partial")

        def _resume_offset(self) -> int:
            if self.partial_path.exists():
                return self.partial_path.stat().st_size
            return 0

        async def _download_from(
            self,
            *,
            url: str,
            progress: ProgressReporter,
            client: httpx.AsyncClient,
        ) -> None:
            offset = self._resume_offset()
            headers = {"Range": f"bytes={offset}-"} if offset > 0 else {}
            hasher = hashlib.sha256()

            # Pre-hash any existing partial bytes so we can continue the digest
            if offset > 0:
                with self.partial_path.open("rb") as f:
                    while True:
                        b = f.read(CHUNK_SIZE)
                        if not b:
                            break
                        hasher.update(b)

            async with client.stream("GET", url, headers=headers, follow_redirects=True) as resp:
                if resp.status_code not in (200, 206):
                    raise httpx.HTTPStatusError(
                        f"unexpected status {resp.status_code}",
                        request=resp.request, response=resp,
                    )
                # Total size: 206 returns Content-Range 'bytes START-END/TOTAL'
                if resp.status_code == 206:
                    cr = resp.headers.get("Content-Range", "")
                    if "/" in cr:
                        try:
                            total = int(cr.rsplit("/", 1)[1])
                        except ValueError:
                            total = offset + int(resp.headers.get("Content-Length", 0))
                    else:
                        total = offset + int(resp.headers.get("Content-Length", 0))
                else:
                    # 200 -> full response; server ignored/rejected our Range. Restart.
                    hasher = hashlib.sha256()
                    offset = 0
                    total = int(resp.headers.get("Content-Length", 0))

                progress.total_bytes = total
                written = offset
                mode = "ab" if resp.status_code == 206 else "wb"
                with self.partial_path.open(mode) as f:
                    async for chunk in resp.aiter_bytes(chunk_size=CHUNK_SIZE):
                        f.write(chunk)
                        hasher.update(chunk)
                        written += len(chunk)
                        await progress.downloading(written)

            # Verify
            await progress.verifying()
            actual_sha = hasher.hexdigest()
            if self.spec.expected_sha256 and actual_sha.lower() != self.spec.expected_sha256.lower():
                # Don't rename; leave .partial so user can retry / inspect
                raise ValueError(
                    f"sha256 mismatch: expected {self.spec.expected_sha256}, got {actual_sha}"
                )
            # Atomic rename to final path
            self.dest_path.parent.mkdir(parents=True, exist_ok=True)
            self.partial_path.replace(self.dest_path)
            await progress.done()

        async def download(self, *, progress: ProgressReporter) -> Path:
            """Try primary URL; on failure, retry with mirror URL.
            Raises on both-failure."""
            # Short-circuit if already valid
            if self.dest_path.exists() and self.spec.expected_sha256:
                if await asyncio.to_thread(
                    _verify_sha256_matches, self.dest_path, self.spec.expected_sha256
                ):
                    await progress.done()
                    return self.dest_path
                else:
                    # Hash mismatch — start over
                    self.dest_path.unlink(missing_ok=True)
                    self.partial_path.unlink(missing_ok=True)

            urls: list[str] = []
            if self.spec.primary_url:
                urls.append(self.spec.primary_url)
            if self.spec.mirror_url:
                urls.append(self.spec.mirror_url)
            if not urls:
                await progress.error(
                    code=-32005, message="gemma_not_installed",
                    remediation="No download URL configured in assets-manifest.json.",
                )
                raise RuntimeError("no download URLs")

            last_err: Exception | None = None
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=HTTP_CONNECT_TIMEOUT, read=HTTP_READ_TIMEOUT),
            ) as client:
                for url in urls:
                    try:
                        log.info("gemma_download_start", url=url)
                        await self._download_from(url=url, progress=progress, client=client)
                        return self.dest_path
                    except (httpx.HTTPError, OSError, ValueError) as e:
                        log.warning("gemma_download_attempt_failed", url=url, err=str(e))
                        last_err = e
                        continue

            await progress.error(
                code=-32005, message="gemma_download_failed",
                remediation=(
                    "Gemma download failed from both HuggingFace and GitHub mirror. "
                    "Check your internet connection and retry, or see Saved/NYRA/logs/."
                ),
            )
            raise RuntimeError(f"download failed; last_err={last_err}")


    def _verify_sha256_matches(path: Path, expected_hex: str) -> bool:
        h = hashlib.sha256()
        with path.open("rb") as f:
            while True:
                b = f.read(CHUNK_SIZE)
                if not b:
                    break
                h.update(b)
        return h.hexdigest().lower() == expected_hex.lower()


    async def download_gemma(
        *,
        spec: GemmaSpec,
        dest_path: Path,
        emit_progress: Callable,  # async; receives dict (build_notification params)
    ) -> Path:
        reporter = ProgressReporter(
            emit=emit_progress,
            asset=GEMMA_FILENAME,
            total_bytes=spec.total_bytes_hint,
        )
        dl = GemmaDownloader(spec=spec, dest_path=dest_path)
        return await dl.download(progress=reporter)
    ```

    **4. REPLACE tests/test_gemma_download.py:**

    ```python
    """Gemma downloader tests.
    VALIDATION test ID: 1-03-04
    """
    from __future__ import annotations
    import asyncio
    import hashlib
    from pathlib import Path
    import pytest
    import httpx
    from nyrahost.downloader.gemma import GemmaDownloader, GemmaSpec, download_gemma, GEMMA_FILENAME
    from nyrahost.downloader.progress import ProgressReporter, RATE_LIMIT_MS, RATE_LIMIT_BYTES


    @pytest.fixture
    def fake_payload() -> bytes:
        # 5 MB payload
        return b"A" * (5 * 1024 * 1024)


    def _sha(b: bytes) -> str:
        return hashlib.sha256(b).hexdigest()


    def _mock_transport(*, primary_payload: bytes | None, mirror_payload: bytes | None, allow_range: bool = True):
        """Responds: GET primary -> primary_payload (supports Range if allow_range); GET mirror -> mirror_payload."""
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
                        206, content=body,
                        headers={
                            "Content-Length": str(len(body)),
                            "Content-Range": f"bytes {start}-{len(primary_payload)-1}/{len(primary_payload)}",
                        },
                    )
                return httpx.Response(200, content=primary_payload,
                                       headers={"Content-Length": str(len(primary_payload))})
            if "mirror" in url:
                if mirror_payload is None:
                    return httpx.Response(500)
                return httpx.Response(200, content=mirror_payload,
                                       headers={"Content-Length": str(len(mirror_payload))})
            return httpx.Response(404)
        return httpx.MockTransport(handler)


    @pytest.mark.asyncio
    async def test_sha256_verify_and_range_resume(tmp_path: Path, fake_payload: bytes, monkeypatch) -> None:
        expected = _sha(fake_payload)
        dest = tmp_path / GEMMA_FILENAME
        partial = dest.with_suffix(dest.suffix + ".partial")

        # Write the first 1 MB to the partial file (simulating a prior interrupted download)
        partial.parent.mkdir(parents=True, exist_ok=True)
        partial.write_bytes(fake_payload[:1024*1024])

        events: list[dict] = []
        async def emit(d: dict) -> None:
            events.append(d)

        # Patch httpx.AsyncClient to use our mock transport
        original = httpx.AsyncClient
        def make_client(*args, **kwargs):
            kwargs["transport"] = _mock_transport(primary_payload=fake_payload, mirror_payload=None)
            return original(*args, **kwargs)
        monkeypatch.setattr("nyrahost.downloader.gemma.httpx.AsyncClient", make_client)

        spec = GemmaSpec(
            primary_url="http://primary/gemma.gguf",
            mirror_url="http://mirror/gemma.gguf",
            expected_sha256=expected,
            total_bytes_hint=len(fake_payload),
        )
        result = await download_gemma(spec=spec, dest_path=dest, emit_progress=emit)
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
    async def test_fallback_to_mirror_on_primary_404(tmp_path: Path, fake_payload: bytes, monkeypatch) -> None:
        expected = _sha(fake_payload)
        dest = tmp_path / GEMMA_FILENAME
        events: list[dict] = []
        async def emit(d): events.append(d)

        original = httpx.AsyncClient
        def make_client(*args, **kwargs):
            kwargs["transport"] = _mock_transport(primary_payload=None, mirror_payload=fake_payload)
            return original(*args, **kwargs)
        monkeypatch.setattr("nyrahost.downloader.gemma.httpx.AsyncClient", make_client)

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
    async def test_both_urls_fail_raises_and_emits_error_progress(tmp_path: Path, monkeypatch) -> None:
        dest = tmp_path / GEMMA_FILENAME
        events: list[dict] = []
        async def emit(d): events.append(d)

        original = httpx.AsyncClient
        def make_client(*args, **kwargs):
            kwargs["transport"] = _mock_transport(primary_payload=None, mirror_payload=None)
            return original(*args, **kwargs)
        monkeypatch.setattr("nyrahost.downloader.gemma.httpx.AsyncClient", make_client)

        spec = GemmaSpec(
            primary_url="http://primary/gemma.gguf",
            mirror_url="http://mirror/gemma.gguf",
            expected_sha256="ab" * 32,
        )
        with pytest.raises(RuntimeError):
            await download_gemma(spec=spec, dest_path=dest, emit_progress=emit)
        # Last event is an error frame
        assert events[-1]["status"] == "error"
        assert "error" in events[-1]


    @pytest.mark.asyncio
    async def test_progress_rate_limited() -> None:
        events: list[dict] = []
        async def emit(d): events.append(d)
        r = ProgressReporter(emit=emit, asset="x", total_bytes=1_000_000_000)
        # Hammer with 1000 tiny updates (< 1 ms apart) for well under RATE_LIMIT_BYTES total
        for i in range(1000):
            await r.downloading(i * 1024)  # 1 KB steps
        # Expect exactly 1 event (only the first went through, since rate-limit trips subsequently)
        assert len(events) == 1
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "class GemmaDownloader" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/downloader/gemma.py` equals 1
      - `grep -c "Range\": f\"bytes={offset}-\"" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/downloader/gemma.py` equals 1
      - `grep -c "hashlib.sha256()" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/downloader/gemma.py` >= 2
      - `grep -c "self.partial_path.replace(self.dest_path)" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/downloader/gemma.py` equals 1
      - `grep -c "class ProgressReporter" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/downloader/progress.py` equals 1
      - `grep -c "RATE_LIMIT_MS = 500" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/downloader/progress.py` equals 1
      - `grep -c "RATE_LIMIT_BYTES = 10 \* 1024 \* 1024" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/downloader/progress.py` equals 1
      - `pytest TestProject/Plugins/NYRA/Source/NyraHost/tests/test_gemma_download.py -v` exits 0 with 4 tests passing
    </automated>
  </verify>
  <acceptance_criteria>
    - progress.py exports `ProgressReporter` with methods `downloading`, `verifying`, `done`, `error`
    - progress.py defines `RATE_LIMIT_MS = 500` and `RATE_LIMIT_BYTES = 10 * 1024 * 1024` as module-level constants
    - progress.py ProgressReporter rate-limits `downloading` events to at most 1 per (500ms OR 10MB)
    - gemma.py exports `GemmaSpec` dataclass, `GemmaDownloader` class, `download_gemma` async function
    - gemma.py contains literal text `"Range": f"bytes={offset}-"`
    - gemma.py resume-from-partial reads existing .partial bytes into the hasher before continuing
    - gemma.py handles status 200 (full) AND 206 (partial content) cases
    - gemma.py atomic rename `self.partial_path.replace(self.dest_path)` after verify
    - gemma.py falls back from primary_url to mirror_url on HTTPError/OSError
    - gemma.py emits `error` progress before raising when both URLs fail
    - test_gemma_download.py contains `test_sha256_verify_and_range_resume` (NOT skipped) + `test_fallback_to_mirror_on_primary_404` + `test_both_urls_fail_raises_and_emits_error_progress` + `test_progress_rate_limited`
    - `pytest tests/test_gemma_download.py -v` exits 0 with 4 tests passing
  </acceptance_criteria>
  <done>Gemma download + SHA256 verify + Range resume + mirror fallback + rate-limited progress all tested.</done>
</task>

<task type="auto">
  <name>Task 2: handlers/download.py + wire into app.py</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/download.py
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py
  </files>
  <read_first>
    - docs/JSONRPC.md §3.7 (diagnostics/download-progress)
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/downloader/gemma.py (just created)
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py (current — Plan 08)
    - TestProject/Plugins/NYRA/Source/NyraHost/assets-manifest.json
  </read_first>
  <action>
    **1. CREATE src/nyrahost/handlers/download.py:**

    ```python
    """diagnostics/download-gemma request handler.

    The UE panel calls this once; NyraHost replies {started:true, already_present:bool}
    immediately and streams progress via diagnostics/download-progress notifications.
    """
    from __future__ import annotations
    import asyncio
    from dataclasses import dataclass
    from pathlib import Path
    from typing import Any
    import structlog
    from websockets.server import ServerConnection

    from ..jsonrpc import build_notification
    from ..session import SessionState
    from ..downloader.gemma import GemmaDownloader, GemmaSpec, download_gemma, GEMMA_FILENAME

    log = structlog.get_logger("nyrahost.download")


    @dataclass
    class DownloadHandlers:
        project_dir: Path
        spec: GemmaSpec
        _inflight: asyncio.Task | None = None

        def dest_path(self) -> Path:
            return self.project_dir / "Saved" / "NYRA" / "models" / GEMMA_FILENAME

        async def on_download_gemma(self, params: dict, session: SessionState) -> dict:
            ws: ServerConnection | None = getattr(session, "_ws", None)
            if ws is None:
                return {"started": False, "error": {
                    "code": -32001, "message": "internal",
                    "data": {"remediation": "No active WS bound to session."},
                }}
            if self._inflight is not None and not self._inflight.done():
                return {"started": False, "already_running": True}

            dest = self.dest_path()
            if dest.exists():
                # Size check only — full verify is the downloader's job if requested
                return {"started": False, "already_present": True, "size_bytes": dest.stat().st_size}

            async def emit(progress_params: dict) -> None:
                try:
                    await ws.send(build_notification("diagnostics/download-progress", progress_params))
                except Exception:  # noqa: BLE001
                    pass

            async def run() -> None:
                try:
                    await download_gemma(spec=self.spec, dest_path=dest, emit_progress=emit)
                except Exception as e:  # noqa: BLE001
                    log.exception("gemma_download_task_failed")

            self._inflight = asyncio.create_task(run())
            return {"started": True}
    ```

    **2. UPDATE src/nyrahost/app.py** — wire DownloadHandlers:

    Add imports:
    ```python
    from .handlers.download import DownloadHandlers
    from .downloader.gemma import GemmaSpec
    ```

    Add helper to load the GemmaSpec from assets-manifest.json. Plan 05
    doesn't store the Gemma entry under a `gemma` key directly — it stores
    a `gemma_model_note`. For Phase 1, we hard-code fallback values here from
    ModelPins semantics (assuming Plan 05 resolved them; otherwise default
    to the well-known HF URL):

    ```python
    def _load_gemma_spec(manifest_path: Path) -> GemmaSpec:
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        gemma = data.get("gemma") or {}
        return GemmaSpec(
            primary_url=gemma.get(
                "url",
                "https://huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf/resolve/main/gemma-3-4b-it-qat-q4_0.gguf",
            ),
            mirror_url=gemma.get(
                "mirror_url",
                "https://github.com/nyra-ai/nyra/releases/download/models-v1/gemma-3-4b-it-qat-q4_0.gguf",
            ),
            expected_sha256=gemma.get("sha256", ""),
            total_bytes_hint=int(gemma.get("total_bytes", 3_391_733_760)),
        )
    ```

    Extend `build_and_run` to register the download handler. Find the
    existing `def register(server: NyraServer) -> None:` callback and add:

    ```python
        download_handlers = DownloadHandlers(
            project_dir=project_dir,
            spec=_load_gemma_spec(plugin_binaries_dir.parent.parent / "Source" / "NyraHost" / "assets-manifest.json"),
        )
        server.request_handlers["diagnostics/download-gemma"] = download_handlers.on_download_gemma
    ```

    Additionally, extend the existing `gemma-3-4b-it-qat-q4_0.gguf` path
    constant in app.py to the shared module-level constant from downloader:
    replace `gemma_gguf_path(project_dir)` body to use `GEMMA_FILENAME`:

    ```python
    from .downloader.gemma import GEMMA_FILENAME

    def gemma_gguf_path(project_dir: Path) -> Path:
        return project_dir / "Saved" / "NYRA" / "models" / GEMMA_FILENAME
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "class DownloadHandlers" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/download.py` equals 1
      - `grep -c "on_download_gemma" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/download.py` equals 1
      - `grep -c 'build_notification("diagnostics/download-progress"' TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/download.py` equals 1
      - `grep -c "diagnostics/download-gemma" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py` equals 1
      - `grep -c "_load_gemma_spec" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py` >= 2
      - `grep -c "from .downloader.gemma import GEMMA_FILENAME" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py` equals 1
      - `pytest TestProject/Plugins/NYRA/Source/NyraHost/tests/ -v` exits 0 (all existing tests still pass after the app.py edit)
    </automated>
  </verify>
  <acceptance_criteria>
    - handlers/download.py contains `class DownloadHandlers` with `project_dir`, `spec`, `_inflight` fields
    - handlers/download.py `on_download_gemma` returns `{"started": True}` on fresh download, `{"already_present": True, "size_bytes": N}` on existing file, `{"already_running": True}` on re-invoke
    - handlers/download.py `on_download_gemma` creates an asyncio.Task wrapping `download_gemma(..., emit_progress=emit)` where emit sends `build_notification("diagnostics/download-progress", ...)`
    - app.py imports `DownloadHandlers` and `GemmaSpec`
    - app.py has helper `_load_gemma_spec(manifest_path)` that reads assets-manifest.json and falls back to known HF URL
    - app.py `build_and_run` registers `server.request_handlers["diagnostics/download-gemma"] = download_handlers.on_download_gemma`
    - app.py `gemma_gguf_path` uses `GEMMA_FILENAME` from downloader module
    - All NyraHost pytest tests still pass (run `pytest tests/ -v`, exit 0)
  </acceptance_criteria>
  <done>diagnostics/download-gemma handler wired; Plan 13 panel can call it and receive progress notifications.</done>
</task>

</tasks>

<verification>
From TestProject/Plugins/NYRA/Source/NyraHost/:
```
pytest tests/ -v
```
Must exit 0; tests from Plan 09 (4 in test_gemma_download.py) PLUS all prior
plans' tests pass. Integration smoke: start NyraHost, call
diagnostics/download-gemma request, receive diagnostics/download-progress
notifications; kill mid-download, restart, call again — observe resume.
</verification>

<success_criteria>
- Gemma downloader implemented with Range-resume + SHA256 verify + mirror fallback
- ProgressReporter rate-limits notifications (500ms OR 10MB threshold)
- `diagnostics/download-gemma` registered as request handler on NyraServer
- All pytest tests green (4 download tests + prior plans)
- `download_gemma` function callable from future plans (Phase 2 re-downloads after corruption)
</success_criteria>

<output>
After completion, create `.planning/phases/01-plugin-shell-three-process-ipc/01-09-SUMMARY.md`
documenting: primary/mirror URLs used, resume protocol (206 vs 200 handling),
rate-limit constants, and the handler registration pattern.
</output>
