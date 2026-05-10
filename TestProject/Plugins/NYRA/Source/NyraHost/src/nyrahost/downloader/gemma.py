"""Gemma GGUF downloader with Range-resume + SHA256 verify + mirror fallback.

Implements CONTEXT.md D-17 (download-on-first-run) and VALIDATION row
1-03-04 (test_sha256_verify_and_range_resume).

Flow:
  1. If dest_path already exists with matching SHA256, emit ``done`` and return.
  2. Try primary URL; on HTTP/OS/SHA error, try mirror URL.
  3. Each attempt honours an existing ``.partial`` file: hash its bytes
     into the rolling digest then issue ``Range: bytes=<offset>-``.
  4. Server responses:
     - 206 Partial Content → append to .partial; size derived from Content-Range.
     - 200 OK → server ignored Range; restart hasher at 0, truncate .partial.
     - Other → raise HTTPStatusError, outer loop tries next URL.
  5. After stream completes, verify SHA256. Mismatch raises; leaves .partial
     on disk so the user can retry or inspect.
  6. On success: atomic ``replace`` of .partial → dest_path; emit ``done``.
  7. If both URLs fail, emit ``status=error`` with -32005 code and raise RuntimeError.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

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
        """Construct a GemmaSpec from the assets-manifest.json's ``gemma`` block.

        Plan 05's manifest stores a ``gemma_model_note`` (free-form string)
        rather than a structured entry; if the block is missing the caller
        must pass defaults explicitly (see ``app._load_gemma_spec``).
        """
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
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
        self.partial_path = dest_path.with_suffix(
            dest_path.suffix + ".partial"
        )

    def _resume_offset(self) -> int:
        if self.partial_path.exists():
            size = self.partial_path.stat().st_size
            # WR-04: refuse to "resume" from a .partial that is already
            # at-or-past the expected total size. That state means a
            # prior download corrupted the file (or the manifest's
            # total_bytes shrank); a Range request from this offset
            # would 416 and the user would see an opaque HTTP error.
            # Clear the corrupt .partial and start over.
            hint = self.spec.total_bytes_hint
            if hint > 0 and size >= hint:
                log.warning(
                    "gemma_partial_oversize_reset",
                    partial_size=size,
                    expected=hint,
                )
                self.partial_path.unlink(missing_ok=True)
                return 0
            return size
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

        async with client.stream(
            "GET", url, headers=headers, follow_redirects=True,
        ) as resp:
            if resp.status_code not in (200, 206):
                raise httpx.HTTPStatusError(
                    f"unexpected status {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
            # Total size: 206 returns Content-Range 'bytes START-END/TOTAL'
            if resp.status_code == 206:
                cr = resp.headers.get("Content-Range", "")
                if "/" in cr:
                    try:
                        total = int(cr.rsplit("/", 1)[1])
                    except ValueError:
                        total = offset + int(
                            resp.headers.get("Content-Length", 0)
                        )
                else:
                    total = offset + int(
                        resp.headers.get("Content-Length", 0)
                    )
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
        if (
            self.spec.expected_sha256
            and actual_sha.lower() != self.spec.expected_sha256.lower()
        ):
            # Don't rename; leave .partial so user can retry / inspect
            raise ValueError(
                f"sha256 mismatch: expected {self.spec.expected_sha256}, "
                f"got {actual_sha}"
            )
        # Atomic rename to final path
        self.dest_path.parent.mkdir(parents=True, exist_ok=True)
        self.partial_path.replace(self.dest_path)
        await progress.done()

    async def download(self, *, progress: ProgressReporter) -> Path:
        """Try primary URL; on failure, retry with mirror URL.
        Raises on both-failure.
        """
        # Short-circuit if already valid
        if self.dest_path.exists() and self.spec.expected_sha256:
            if await asyncio.to_thread(
                _verify_sha256_matches,
                self.dest_path,
                self.spec.expected_sha256,
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
                code=-32005,
                message="gemma_not_installed",
                remediation=(
                    "No download URL configured in assets-manifest.json."
                ),
            )
            raise RuntimeError("no download URLs")

        last_err: Exception | None = None
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                HTTP_READ_TIMEOUT,
                connect=HTTP_CONNECT_TIMEOUT,
                read=HTTP_READ_TIMEOUT,
                write=HTTP_READ_TIMEOUT,
                pool=HTTP_READ_TIMEOUT,
            ),
        ) as client:
            for url in urls:
                try:
                    log.info("gemma_download_start", url=url)
                    await self._download_from(
                        url=url, progress=progress, client=client,
                    )
                    return self.dest_path
                except (httpx.HTTPError, OSError, ValueError) as e:
                    log.warning(
                        "gemma_download_attempt_failed",
                        url=url,
                        err=str(e),
                    )
                    last_err = e
                    continue

        # WR-10: both URLs exhausted. If the last failure was a SHA
        # mismatch the .partial is corrupt — clean it up rather than
        # leaving a stale, never-resumable file. HTTP/network failures
        # are kept on disk so the next attempt can continue from the
        # last good byte.
        if isinstance(last_err, ValueError) and "sha256 mismatch" in str(
            last_err
        ):
            self.partial_path.unlink(missing_ok=True)
            log.info(
                "gemma_partial_cleanup_after_sha_mismatch",
                path=str(self.partial_path),
            )

        await progress.error(
            code=-32005,
            message="gemma_download_failed",
            remediation=(
                "Gemma download failed from both HuggingFace and GitHub "
                "mirror. Check your internet connection and retry, or "
                "see Saved/NYRA/logs/."
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
    """One-shot helper. Constructs the reporter + downloader, runs end-to-end."""
    reporter = ProgressReporter(
        emit=emit_progress,
        asset=GEMMA_FILENAME,
        total_bytes=spec.total_bytes_hint,
    )
    dl = GemmaDownloader(spec=spec, dest_path=dest_path)
    return await dl.download(progress=reporter)
