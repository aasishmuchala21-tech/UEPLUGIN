"""Gemma GGUF downloader subpackage (Plan 01-09).

Owns the download-on-first-run surface per CONTEXT.md D-17:
  - HTTP Range-resumable stream from HuggingFace CDN primary URL
  - GitHub Releases mirror fallback
  - SHA256 verification against ModelPins-pinned hash
  - Rate-limited ``diagnostics/download-progress`` notification emission

Public surface:
  :class:`GemmaSpec` — (primary_url, mirror_url, expected_sha256, total_bytes_hint)
  :class:`GemmaDownloader` — orchestrates resume + verify + atomic rename
  :func:`download_gemma` — one-shot async helper used by handlers/download.py
  :class:`ProgressReporter` — rate-limited status frame emitter
  ``RATE_LIMIT_MS`` / ``RATE_LIMIT_BYTES`` — module-level constants.
"""
