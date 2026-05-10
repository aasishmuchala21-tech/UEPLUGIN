---
phase: 8
plan: 08-01
requirement: PARITY-01
type: execute
wave: 1
tier: 1
autonomous: false
depends_on: []
blocking_preconditions: []
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/attachments.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/extractors/__init__.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/extractors/pdf.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/extractors/docx.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/extractors/pptx.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/extractors/xlsx.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/extractors/html.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/extractors/md.py
  - TestProject/Plugins/NYRA/Source/NyraHost/pyproject.toml
  - TestProject/Plugins/NYRA/Source/NyraHost/requirements.lock
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_extractors_pdf.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_extractors_docx.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_extractors_others.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_wheel_cache_budget.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/fixtures/sample.pdf
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/fixtures/sample.docx
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/fixtures/sample.pptx
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/fixtures/sample.xlsx
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/fixtures/sample.html
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/fixtures/sample.md
---

# Plan 08-01: Document Attachments (PARITY-01)

## Goal

Extend NyraHost's chat-attachment pipeline to accept **PDF, DOCX, PPTX, XLSX, HTML, Markdown** and emit (a) extracted plain text + (b) re-ingested embedded images that automatically flow into the existing image-attachment vision-routing path. Pure-Python parsers only; wheel-cache impact bounded under 75 MB.

## Why this beats Aura

Per CONTEXT.md SC#1 (verbatim):

> **Beats Aura on document inputs**: PARITY-01 attachment pipeline accepts PDF + DOCX + PPTX + XLSX + HTML + Markdown (matches Aura's surface) and additionally extracts inline images for vision-routing through the existing image-attachment path (Aura accepts docs but NYRA's attachment flow already routes images to Claude vision — the combination is a clean win). Text extraction uses pure-Python parsers (`pypdf`, `python-docx`, `python-pptx`, `openpyxl`, `markdown`) so the offline wheel cache stays bounded under 50 MB.

The "beats" lever is that NYRA re-ingests embedded images through `attachments.ingest_attachment` — which already content-addresses, dedups, and routes images to Claude vision. Aura accepts docs as text-only.

## Pattern Compliance (PARITY-01 — non-mutator pattern alignment)

PARITY-01 is **not** a Phase 4 mutator. It extends the `attachments.py` pipeline. Pattern alignment per PATTERNS.md §"PARITY-01":

| Concern | Existing primitive (reused) | Where it lives |
|---|---|---|
| File hash + dedup | `_sha256_of_file()` (attachments.py:81-97) | reused as-is for documents |
| Path validation + symlink rejection + sensitive-prefix blocklist | `ingest_attachment()` (attachments.py:100-182) | reused as-is |
| Kind classification | `_classify(ext_lower)` (attachments.py:63-78) iterates `ALLOWED_EXTENSIONS.items()` | extended via `ALLOWED_EXTENSIONS["document"]` |
| Embedded image vision routing | `attachments.ingest_attachment(...)` recursive call from extractors | reused as-is — the existing `image` kind → Claude vision pipeline runs unchanged |
| SQL link | `Storage.link_attachment` (storage.py:247-264) — `kind TEXT NOT NULL` already accepts new values | no DDL change; no `user_version` bump |

**No new helpers. No new abstractions.** The new `extractors/` package is pure compute that returns `(text, list[AttachmentRef])` and pushes embedded images through the existing `ingest_attachment` call.

## MCP Registration

**No MCP tool registered.** PARITY-01 plugs into the WS attachment ingestion path (chat handler), not the `_tools` dict. Concretely:

- `nyrahost/attachments.py` is extended (new `"document"` kind in `AttachmentKind` Literal at line 34, new entry in `ALLOWED_EXTENSIONS` at lines 38-42).
- The chat-handler dispatch in `nyrahost/mcp_server/handlers/` (or whichever module currently calls `ingest_attachment`) gains a `if ext in DOCUMENT_EXTS: text, image_refs = extractors.dispatch(...)` branch. Text attachment is written under `<ProjectSaved>/NYRA/attachments/<sha[:2]>/<sha>.txt`; image refs are emitted into the same submission's attachment list.

No edits to `mcp_server/__init__.py:_tools` dict, `list_tools()` schemas, or imports. PARITY-01 is silent at the MCP-tool layer.

## Locked-decision compliance

- **LOCKED-06 (pure-Python only):** `requirements.lock` adds **only** `pypdf 6.11.0`, `python-docx 1.2.0`, `python-pptx 1.0.2`, `openpyxl 3.1.5`, `markdown 3.10.2`, `beautifulsoup4 4.x` (latest minor). Transitive C-extension wheels (`Pillow`, `lxml`) are accepted under the LOCKED-06 reading "no platform-fragmented native deps" — Pillow + lxml ship Windows-x64 precompiled wheels with no platform fragmentation on our only target. Per RESEARCH.md Assumption A8, this reading is the planner's clarification of LOCKED-06; if the user reads LOCKED-06 strictly as "zero compiled code anywhere", drop python-docx/pptx and reduce scope at plan-check.
- **NO `pdfplumber`** (would pull `pypdfium2` which ships PDFium C++ binaries — RESEARCH.md §Anti-Patterns).
- **T-08-02 wheel-cache fail-loud at 75 MB:** dedicated test (`test_wheel_cache_budget.py`) measures `du -sh Binaries/Win64/NyraHost/wheels/` post-add and asserts < 75 MB. Estimated ~9.1 MB total (well under ceiling).

## Tasks

### Task 1: Add doc-parser deps to requirements.lock and rebuild wheel cache

**Files:**
- `TestProject/Plugins/NYRA/Source/NyraHost/pyproject.toml` (add to `[project.dependencies]`)
- `TestProject/Plugins/NYRA/Source/NyraHost/requirements.lock` (regenerated)

**Action:**
Pin exactly these versions per LOCKED-06 + RESEARCH.md §Standard Stack PARITY-01:

```
pypdf==6.11.0
python-docx==1.2.0
python-pptx==1.0.2
openpyxl==3.1.5
markdown==3.10.2
beautifulsoup4>=4.12,<5
```

Run pip-compile (or the existing `NyraHost/scripts/compile-requirements.{ps1,sh}` if present) to regenerate `requirements.lock` with full transitive closure. Materialize wheels under `Binaries/Win64/NyraHost/wheels/` per the existing D-14 wheel-cache contract.

**Verify:**
- `pip-compile --no-emit-options pyproject.toml -o requirements.lock` succeeds
- All six top-level packages appear in lock file at exactly the pinned versions

**Done:** Lock file regenerated; wheel cache rebuilt.

### Task 2: Build wheel-cache budget test (T-08-02 fail-loud)

**Files:** `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_wheel_cache_budget.py`

**Action:** pytest that walks `Binaries/Win64/NyraHost/wheels/` and asserts total size < 75 MB. Skip with explicit `pytest.skip("wheel cache not materialized — run pip download first")` when the directory is empty. This is the T-08-02 fail-loud bar.

```python
def test_wheel_cache_under_75mb():
    wheels_dir = Path(__file__).parent.parent.parent.parent / "Binaries/Win64/NyraHost/wheels"
    if not wheels_dir.exists() or not any(wheels_dir.iterdir()):
        pytest.skip("wheel cache not materialized")
    total = sum(p.stat().st_size for p in wheels_dir.rglob("*.whl"))
    assert total < 75 * 1024 * 1024, f"wheel cache {total/1024/1024:.1f} MB exceeds 75 MB ceiling"
```

**Verify:** `pytest tests/test_wheel_cache_budget.py -x -q` passes (or skips cleanly).

**Done:** Test exists and gates wheel-cache size on every CI run.

### Task 3: Extend `AttachmentKind` Literal + `ALLOWED_EXTENSIONS` in attachments.py

**Files:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/attachments.py`

**Action:**
- Line 34 (`AttachmentKind`): widen Literal to add `"document"`. Existing values stay verbatim.
- Lines 38-42 (`ALLOWED_EXTENSIONS`): add `"document": frozenset({".pdf", ".docx", ".pptx", ".xlsx", ".html", ".htm"})`. **Do not** add `.md` here — `.md` already lives under `text` per current code; document extractor handles `.md` via the markdown library to produce structured text but the attachment kind stays `text`.
- `_classify(ext_lower)` (lines 63-78): no change — iterates `ALLOWED_EXTENSIONS.items()` and automatically picks up the new kind.
- `AttachmentRef` dataclass (lines 45-61): no change. Extracted text + embedded image refs flow as separate `AttachmentRef` siblings produced by the new extractor module.

**Verify:** `pytest tests/test_attachments.py -x -q` (existing tests for image/text/video kinds still pass).

**Done:** `attachments.classify(Path("foo.pdf"))` returns kind `"document"`; existing image/text tests untouched.

### Task 4: Build `extractors/` package — six dispatchers + `dispatch()` entrypoint

**Files:**
- `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/extractors/__init__.py`
- `extractors/pdf.py`, `docx.py`, `pptx.py`, `xlsx.py`, `html.py`, `md.py`

**Action — top-level `dispatch()` signature (in `__init__.py`):**

```python
from pathlib import Path
from typing import Tuple
from nyrahost.attachments import AttachmentRef

def dispatch(
    src: Path, *, project_saved: Path
) -> Tuple[str, list[AttachmentRef]]:
    """Pick extractor by suffix; return (text, embedded_image_refs).

    The image refs are produced via attachments.ingest_attachment so they
    inherit content-addressing + symlink-rejection + sensitive-prefix
    blocklist for free. Vision routing happens automatically via the
    existing image-attachment chat-handler path.
    """
    suffix = src.suffix.lower()
    if suffix == ".pdf":
        from nyrahost.extractors.pdf import extract_pdf
        return extract_pdf(src, project_saved=project_saved)
    if suffix == ".docx":
        from nyrahost.extractors.docx import extract_docx
        return extract_docx(src, project_saved=project_saved)
    if suffix == ".pptx":
        from nyrahost.extractors.pptx import extract_pptx
        return extract_pptx(src, project_saved=project_saved)
    if suffix == ".xlsx":
        from nyrahost.extractors.xlsx import extract_xlsx
        return extract_xlsx(src, project_saved=project_saved)
    if suffix in {".html", ".htm"}:
        from nyrahost.extractors.html import extract_html
        return extract_html(src, project_saved=project_saved)
    if suffix == ".md":
        from nyrahost.extractors.md import extract_md
        return extract_md(src, project_saved=project_saved)
    raise ValueError(f"no extractor for {src.suffix!r}")
```

Each extractor returns `Tuple[str, list[AttachmentRef]]`. The PDF skeleton from RESEARCH.md §Code Examples is the canonical shape; replicate that contract in the other five.

**Per-extractor invariants (per RESEARCH.md §Pitfalls):**
- **Pillow `convert("RGB")` for every embedded image** before `ingest_attachment` (T-08-07 colour-space safety).
- **Skip images < 64×64 px** (icon-noise filter).
- **Pre-check zip total uncompressed size < 100 MB** for DOCX/PPTX/XLSX (zip-bomb mitigation per RESEARCH.md §Security Domain).
- **`html.parser` (stdlib) default; lxml only if input has decode failures** (avoids pulling lxml into the hot path twice when bs4 already has it transitively).

**Verify:** `pytest tests/test_extractors_pdf.py tests/test_extractors_docx.py tests/test_extractors_others.py -x -q` (Task 5 below).

**Done:** All six extractors return non-empty text + correctly-routed image refs on the fixture set.

### Task 5: Build extractor unit tests + fixtures

**Files:**
- `tests/test_extractors_pdf.py`, `tests/test_extractors_docx.py`, `tests/test_extractors_others.py`
- `tests/fixtures/sample.{pdf,docx,pptx,xlsx,html,md}` — each with at least one embedded image > 64×64

**Action — minimum coverage per format:**
- text non-empty + monotonically grows with input size (sanity)
- embedded image count matches fixture (PDF fixture has 2 images, DOCX has 1, PPTX has 3, XLSX has 0, HTML has 1, MD has 0 — adjust counts to actual fixtures at construction time)
- every emitted `AttachmentRef.kind == "image"` and resolves to an existing file under `<project_saved>/NYRA/attachments/`
- malformed file (truncated PDF) raises `ValueError` with informative message — does NOT crash the chat-handler
- a DOCX symlinked to `~/.ssh/id_rsa` is rejected by the existing `ingest_attachment` symlink-rejection path (regression test for security domain)

Mark fixtures `pending_manual_verification: false` — these are deterministic file-IO tests, no UE editor required.

**Verify:** `pytest tests/test_extractors_*.py -x -q` passes.

**Done:** All extractor tests green on the dev box.

### Task 6: Wire `extractors.dispatch()` into the chat-handler attachment path

**Files:** Whichever module in `nyrahost/mcp_server/handlers/` (or `nyrahost/chat/`) currently iterates over the chat submission's `attachments[]` and calls `ingest_attachment`. Wave 0 grep step in Task 7 confirms the exact file before this task starts.

**Action:** Insert a branch after the existing `ingest_attachment` call: when the resulting `AttachmentRef.kind == "document"`, call `extractors.dispatch(src, project_saved=...)` to get `(text, image_refs)`. Write `text` to a sibling `AttachmentRef` of kind `"text"` (file lands under `<sha[:2]>/<sha>.txt`). Append `image_refs` directly to the submission's attachment list — they're already content-addressed and stored.

**Verify:** end-to-end — submit a PDF chat message; assert (a) prompt context contains extracted text, (b) embedded images appear as separate vision-routed attachments. Test path is integration-style (`tests/test_chat_attachments_documents.py`), marked `@pytest.mark.integration` so the fast suite skips it but CI runs it.

**Done:** A submitted PDF results in text + N image attachments, all visible to Claude.

### Task 7: Operator-run verification (live UE editor) — `pending_manual_verification: true`

**What this task does:** drag a real PDF (with embedded images) onto the chat composer in a live UE 5.6 editor session and confirm the chips render, the LLM receives the extracted text, and the embedded images are vision-routed.

**Files:** `TestProject/Plugins/NYRA/Source/NyraHost/.planning/phases/08-competitive-parity-aura/08-01-VERIFICATION.md` (PLACEHOLDER until operator runs)

**Operator runbook:**
1. UE 5.6 editor open with NYRA plugin enabled
2. Open NYRA chat panel
3. Drag `tests/fixtures/sample.pdf` onto the drop zone
4. Type "describe the images in this document" and submit
5. Assert: chip renders showing the PDF + N image chips
6. Assert: Claude response references the embedded image content (not just the text)
7. Repeat for `.docx`, `.pptx` (image-bearing formats only)

`pending_manual_verification: true` (operator runs). Plans 02..05/07/08 share this property — see RESEARCH.md §Validation Architecture.

**Done:** VERIFICATION.md filled with operator-run results (PASS / FAIL per format).

## Tests

| Test file | What it verifies | Pending manual? |
|---|---|---|
| `tests/test_wheel_cache_budget.py` | Wheel-cache total < 75 MB (T-08-02 fail-loud) | No |
| `tests/test_extractors_pdf.py` | PDF text + embedded images extract; truncated PDF raises | No |
| `tests/test_extractors_docx.py` | DOCX text + images; symlink-to-secret rejected | No |
| `tests/test_extractors_others.py` | PPTX/XLSX/HTML/MD round-trip on fixtures | No |
| `tests/test_chat_attachments_documents.py` | Integration — submit PDF, get text + image attachments back | No (mocked WS) |
| `08-01-VERIFICATION.md` | Live UE editor drop a real PDF, assert vision routing | **Yes** |

## Threats addressed

- **T-08-02** (wheel-cache bloat from PDF parsers): Task 2 enforces fail-loud at 75 MB. LOCKED-06 prevents pdfplumber/pypdfium2/qpdf from sneaking in.
- **Pitfall 7 / RESEARCH.md §Pitfalls** (CMYK colour space confusion): every extractor passes images through `Image.convert("RGB")` before `ingest_attachment`.
- **Security: zip-bomb / billion-laughs** (RESEARCH.md §Security Domain): each DOCX/PPTX/XLSX extractor pre-checks total uncompressed size < 100 MB.
- **Security: symlink trick** (T-08-X — pre-existing): existing `attachments.ingest_attachment:131-140` symlink rejection covers documents identically.

## Acceptance criteria

- [ ] `pip install -r requirements.lock` succeeds and produces a wheel cache < 75 MB on Windows x64 (`tests/test_wheel_cache_budget.py` passes).
- [ ] `pytest tests/test_extractors_*.py -x -q` is green — every format produces non-empty text and ≥0 image refs matching fixture counts.
- [ ] `attachments.classify(Path("foo.pdf"))` returns kind `"document"`; existing image/text/video tests still pass with zero regressions.
- [ ] Submitted PDF in chat (integration test) results in (a) extracted text in prompt context, (b) embedded image attachments visible to Claude vision (verified via JSON-RPC payload inspection).
- [ ] `08-01-VERIFICATION.md` operator-run confirms a real PDF + DOCX + PPTX drop produces the expected text + image chips in a live UE 5.6 editor.

## Honest acknowledgments

- **Plan does not affect the MCP `_tools` dict.** PARITY-01 is silent at the MCP-tool layer; the surface change lives in `attachments.py` + `extractors/` + the chat handler.
- **LOCKED-06 reading is the planner's clarification** (RESEARCH.md A8). Pillow/lxml precompiled Windows-x64 wheels are accepted as "no platform fragmentation on our only target." If the user reads LOCKED-06 stricter at plan-check, drop python-docx/pptx and reduce scope.
- **Wheel-cache estimate is ~9.1 MB**, 8x headroom under the 75 MB ceiling. The fail-loud test exists for the future, not for today's risk.
