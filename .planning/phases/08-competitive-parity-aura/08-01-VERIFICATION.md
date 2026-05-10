---
phase: 8
plan: 08-01
requirement: PARITY-01
verification_type: operator-runbook-pending
pending_manual_verification: true
created: 2026-05-10
status: pending
---

# Plan 08-01 Verification — Document Attachments (PARITY-01)

**Status:** PLACEHOLDER — operator must run the steps below in a live
UE 5.6 editor session and replace this file with PASS / FAIL results
per format. Do NOT mark the plan COMPLETE on the strength of unit
tests alone; the unit tests cover extraction correctness but cannot
exercise the Slate composer drag-drop path or the Claude-vision
round-trip on the embedded images.

## Pre-conditions

- UE 5.6 editor open with NYRA plugin enabled
- NyraHost sidecar running (auto-starts via plugin lifecycle)
- A live Claude session (CLAUDE_CODE_OAUTH_TOKEN set, or `claude setup-token`
  has been run at least once on this machine)
- Sample documents available (build them via the test fixtures or grab
  any small PDF/DOCX/PPTX/XLSX/HTML/MD from disk)

## Operator runbook

### Step 1 — PDF with embedded images

1. Open the NYRA chat panel in UE 5.6.
2. Drag a PDF that contains at least one embedded image onto the chat drop zone.
3. Confirm: a chip appears showing the PDF filename plus N image chips
   (one per embedded image extracted by `extractors/pdf.py`).
4. Type "describe the images in this document" and submit.
5. Wait for the streaming response to complete.
6. Confirm: Claude's response references the embedded image content
   (not just the surrounding PDF text). This proves the image-attachment
   vision-routing pipeline received the extracted images.

**PASS criteria:** chip count matches expected images + Claude
response demonstrably uses image content (not just text).

### Step 2 — DOCX with inline pictures

1. Drag a DOCX (with `Document().add_picture(...)` or any Word doc
   containing at least one inline image) onto the drop zone.
2. Confirm: chip for the DOCX + chip(s) for each embedded picture.
3. Submit a prompt that requires understanding both text and image
   content (e.g. "what does the diagram on page 1 show, in the context
   of the surrounding paragraphs?").
4. Confirm Claude correlates text and image.

### Step 3 — PPTX deck

1. Drag a PPTX deck (any deck with at least 2-3 slides containing
   pictures) onto the drop zone.
2. Confirm: chip for the PPTX + N image chips (one per embedded
   picture across all slides).
3. Submit a prompt: "summarise each slide and describe the
   accompanying visual."
4. Confirm Claude addresses each slide's text + visual.

### Step 4 — XLSX (text-only baseline)

1. Drag an XLSX with multi-sheet text data onto the drop zone.
2. Confirm: chip for the XLSX + 0 image chips (XLSX rarely has
   meaningful images; the openpyxl 3.1.5 image extractor is
   best-effort).
3. Submit a prompt: "summarise the data in each sheet."
4. Confirm Claude reads sheet names and cell contents.

### Step 5 — HTML with data-URI image

1. Drag an HTML file containing at least one `<img src="data:image/png;base64,...">`
   tag onto the drop zone.
2. Confirm: chip for the HTML + 1 image chip per data-URI image.
3. Submit a prompt: "describe the embedded image."
4. Confirm Claude addresses the embedded image.

### Step 6 — Markdown with image

1. Drag a `.md` file containing `![alt](data:image/png;base64,...)`.
2. Confirm: chip for the MD + 1 image chip.
3. Submit a prompt: "describe the embedded image and the surrounding text."
4. Confirm Claude addresses both.

### Step 7 — Negative path (malformed PDF)

1. Save a non-PDF text file with a `.pdf` extension.
2. Drag onto the drop zone.
3. Confirm: an error chip or remediation message appears, and the
   chat does NOT crash. The handler logs `doc_extract_failed` to
   `Saved/NYRA/logs/`.
4. Confirm subsequent valid drops still work (no sticky error state).

## Result template — fill in below after operator run

| Step | Format | Chips rendered | Claude used image content | PASS / FAIL | Notes |
|------|--------|----------------|---------------------------|-------------|-------|
| 1    | PDF    | TBD            | TBD                       | TBD         |       |
| 2    | DOCX   | TBD            | TBD                       | TBD         |       |
| 3    | PPTX   | TBD            | TBD                       | TBD         |       |
| 4    | XLSX   | TBD            | n/a (text-only)           | TBD         |       |
| 5    | HTML   | TBD            | TBD                       | TBD         |       |
| 6    | MD     | TBD            | TBD                       | TBD         |       |
| 7    | bad PDF | error chip    | n/a                       | TBD         |       |

**Operator:** Replace TBDs with results. Set `pending_manual_verification: false`
in the frontmatter and update `status: passed` or `status: failed`. Commit
this file as part of the EXIT-GATE evidence chain.

## What this verification cannot prove

- Wheel-cache size on the operator's machine (covered by
  `tests/test_wheel_cache_budget.py` once the wheel cache is materialised
  via `pip download -r requirements.lock -d Binaries/Win64/NyraHost/wheels/`).
- Cross-version compatibility (UE 5.4 / 5.5 / 5.7) — that's a separate
  matrix run as part of Phase 8 EXIT-GATE.
- Performance under heavy docs (a 200-page PDF with 50 images) — out
  of scope for the parity bar; document and revisit if user reports lag.
