"""T-08-02 fail-loud — wheel cache size budget.

Walks ``TestProject/Plugins/NYRA/Binaries/Win64/NyraHost/wheels/`` and
asserts the total ``.whl`` size stays under 75 MB. Skips cleanly when
the wheel cache hasn't been materialised (dev-box pre-`pip download`
state, CI runners that don't ship the cache).

The 75 MB ceiling is per CONTEXT.md T-08-02 — pure-Python doesn't mean
small (openpyxl alone ships ~10 MB). PARITY-01's six parsers
(pypdf + python-docx + python-pptx + openpyxl + markdown +
beautifulsoup4) plus their transitive lxml + Pillow wheels come in
around ~9 MB total per RESEARCH.md, so the test exists for the
future-bloat case (someone adds pdfplumber → pulls pypdfium2's PDFium
binaries → cache jumps to ~80 MB) rather than for today's risk.
"""
from __future__ import annotations

from pathlib import Path

import pytest

# Plugin layout: NyraHost/tests/test_wheel_cache_budget.py is 4 levels above
# Binaries/Win64/NyraHost/wheels/. Keep the relative ascent explicit so a
# repo move surfaces immediately rather than silently skipping.
_NYRAHOST_ROOT = Path(__file__).resolve().parent.parent  # .../NyraHost/
_PLUGIN_ROOT = _NYRAHOST_ROOT.parent.parent  # .../NYRA/ (Source -> NYRA)
_WHEELS_DIR = _PLUGIN_ROOT / "Binaries" / "Win64" / "NyraHost" / "wheels"

_BUDGET_BYTES = 75 * 1024 * 1024  # 75 MB hard ceiling per T-08-02


def test_wheel_cache_under_75mb() -> None:
    """Asserts wheel cache total < 75 MB or skips if cache not materialised."""
    if not _WHEELS_DIR.exists():
        pytest.skip(
            f"wheel cache not materialised at {_WHEELS_DIR} — run "
            "`pip download -r requirements.lock -d <wheels-dir>` first"
        )
    wheels = list(_WHEELS_DIR.rglob("*.whl"))
    if not wheels:
        pytest.skip(
            f"wheel cache directory exists but is empty: {_WHEELS_DIR}"
        )
    total = sum(p.stat().st_size for p in wheels)
    total_mb = total / (1024 * 1024)
    assert total < _BUDGET_BYTES, (
        f"wheel cache {total_mb:.1f} MB exceeds 75 MB ceiling "
        f"(T-08-02). Wheels counted: {len(wheels)}. "
        "Likely culprit: a new dependency pulled a C-extension parser "
        "(pdfplumber → pypdfium2, mupdf, qpdf). Drop it per LOCKED-06."
    )
