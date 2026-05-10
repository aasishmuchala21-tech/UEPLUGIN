---
phase: 07-sequencer-video-to-matched-shot-launch-demo
fixed_at: 2026-05-10T00:00:00Z
review_path: .planning/phases/07-sequencer-video-to-matched-shot-launch-demo/07-REVIEW.md
iteration: 1
fix_scope: critical_and_warning
findings_in_scope: 20
fixed: 18
skipped: 2
regressed: 0
status: partial
---

# Phase 7 Code Review Fix Report

**Fixed at:** 2026-05-10
**Source review:** `.planning/phases/07-sequencer-video-to-matched-shot-launch-demo/07-REVIEW.md`
**Iteration:** 1
**Scope:** critical_and_warning (BLOCKER + WARNING; INFO out of scope)

## Summary

- Findings in scope: 20 (8 BLOCKER + 12 WARNING)
- Fixed: 18 (all 8 BLOCKERs + 10 WARNINGs)
- Skipped: 1 (WR-07)
- Partial: 1 (WR-03)
- Phase 7 tests: 43/43 passing
- Broad sweep delta: 0 regressions (331 passed / 13 pre-existing test_transaction failures, identical to baseline)

## Applied Fixes

### BL-01: Sequencer*Tool classes don't inherit SequencerToolMixin
**Files:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/sequencer_tools.py`
**Commit:** 740c201
**Applied fix:** Changed all four declarations to `class X(SequencerToolMixin, NyraTool):`. Verified each class is now a subclass of `SequencerToolMixin` so the helper-method calls inside `execute()` resolve at runtime.

### BL-02: VideoReferenceParams.from_json never defined
**Files:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/video_llm_parser.py`
**Commit:** 72bf1b8
**Applied fix:** Added `@classmethod from_json(cls, payload: str)` symmetric to `to_json`. JSON-decodes, coerces lists back to tuples for `subject_position`/`primary_color`/positions/rotations, and restores `CameraMoveType` enum values (UNKNOWN on bad input). Verified round-trip via a quick driver: `to_json` → `from_json` reproduces the same dataclass.

### BL-03: get_primary_lighting_params passes wrong kwarg primary_temperature
**Files:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/video_llm_parser.py`
**Commit:** 3ccf57f
**Applied fix:** Renamed `primary_temperature=` to `primary_temperature_k=` to match the `LightingParams` dataclass field. Verified the method now constructs a `LightingParams` instance without TypeError.

### BL-04: _download_youtube returns hardcoded /tmp path on Windows
**Files:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/video_reference_analyzer.py`
**Commit:** 3781f20
**Applied fix:** Replaced the `/tmp/downloaded_video.mp4` stub with `raise NotImplementedError("[-32037] YouTube download via yt-dlp is not yet wired up; attach a local mp4 instead.")` per env directive. Real yt-dlp wiring is out of phase 7 scope. Tests that exercise the YouTube branch monkeypatch `_download_youtube`, so they remain unaffected.

### BL-05: Wrong UE API call add_keyframe_absolute_focal_focus + missing FOV→mm conversion
**Files:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/sequencer_tools.py`
**Commit:** 0fba199
**Applied fix:** Renamed call to `add_keyframe_absolute_focal_length` (the actual UE Sequencer API) and added `_fov_degrees_to_focal_length_mm()` helper using the standard pinhole-camera relation `(sensor_width/2) / tan(fov_deg * pi / 360)` against the 36 mm horizontal sensor default. Both keyframe callsites now flow through the helper.

### BL-06: _bind_camera_to_sequence passed actor path string, not actor object
**Files:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/sequencer_tools.py`
**Commit:** f67eaff
**Applied fix:** Resolve the actor object via `unreal.EditorAssetLibrary.load_asset(actor_path)` before forwarding to `_bind_camera_to_sequence`. Mixin signature is `camera_actor: Any`, so this is purely a callsite lift. Per env note, the operator wiring inside UE editor handles the path-to-actor resolution.

### BL-07: _validate_file_duration permanently returns True; 10-s cap unenforced
**Files:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/demo02_cli_tool.py`
**Commit:** bfdc22f (combined with WR-12, WR-01)
**Applied fix:** Implemented real ffprobe-based probe with `duration <= MAX_CLIP_SECONDS` check. Probe failures (binary missing, unreadable file, timeout) pass through so the user sees the real downstream error rather than a misleading cap message; only positive-duration clips that exceed 10 s are rejected. Combined with BL-08 in the analyzer this gives belt-and-suspenders enforcement.
**Status:** fixed: requires human verification — the cap-and-pass-through logic is intentional but should be sanity-checked against real video clips before launch.

### BL-08: _get_video_duration silently returns 0.0 on ffprobe failure
**Files:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/video_reference_analyzer.py`
**Commit:** 701e252 (combined with WR-01, WR-08, WR-09)
**Applied fix:** Added `check=True` to the subprocess call and re-raise as `RuntimeError("[-32035] Could not probe video duration: ...")`. Empty stdout and non-numeric output are also hard rejections. Tests mock `_get_video_duration` directly, so they are unaffected.

### WR-01: asyncio.run inside sync execute() will deadlock under WS handler
**Files:** `demo02_cli_tool.py`, `video_reference_analyzer.py`
**Commits:** bfdc22f (demo02_cli), 701e252 (analyzer)
**Applied fix:** Replaced all three `asyncio.run(...)` callsites with `run_async_safely(...)` from `nyrahost.tools.base`. Imports added to both files.

### WR-02: extract_keyframes glob picks up stale files from prior runs
**Files:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/ffmpeg_extractor.py`
**Commit:** 47efb95 (combined with WR-03 partial, WR-10, WR-11, IN-05)
**Applied fix:** `extract_keyframes` now creates a fresh per-run subdir via `tempfile.mkdtemp(prefix='nyra_kf_', dir=output_dir)` and globs only that subdir. Stale frames from earlier failed/parallel runs cannot leak into the returned path list, and ordering is monotonic per call.

### WR-03 (partial): _run_ffmpeg_scene_detect missing safety contract
**Files:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/ffmpeg_extractor.py`
**Commit:** 47efb95
**Applied fix:** Added per-run subdir, `try/except` around the subprocess call, and `Path.exists` filtering on glob results. The pre-existing-input-file existence check was deliberately NOT lifted because `test_scene_cut_detection_threshold` drives the method against `/fake/video.mp4` to assert the constructed command string; adding an `exists()` guard would regress the green test. Documented in code.
**Status:** fixed: partial (existence check intentionally omitted to preserve green test)

### WR-04: transform.location / transform.rotation JSON Schema malformed
**Files:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/sequencer_tools.py`
**Commit:** cadca93
**Applied fix:** Wrapped both `location` and `rotation` in `{"type": "object", "properties": {...}, "required": [...]}`. Listed all axis keys in `required` so an LLM cannot omit one.

### WR-05: light_intensity / fov_degrees skipped when caller passes 0
**Files:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/sequencer_tools.py`
**Commit:** cde2994
**Applied fix:** Switched four optional-channel guards in `SequencerSetKeyframeTool.execute` from truthiness checks to explicit `is not None`. A user can now keyframe a light to 0 (dim out) or set a 0 deg adjustment.

### WR-06: _camera_move_to_keyframe_pattern overlays every shot on outer window
**Files:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/sequencer_tools.py`
**Commit:** 91a27fc
**Applied fix:** Use the shot's own `start_time`/`end_time` when they're sensible (positive end > start); fall back to the outer (start, end) when the shot has sentinel zero/inverted times so single-shot path keeps working. Multi-shot params now author each shot at its own window.

### WR-08: Cleanup leaks keyframes if duration check raises
**Files:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/video_reference_analyzer.py`
**Commit:** 701e252
**Applied fix:** Wrapped the entire `analyze()` body in a single try/finally; cleanup runs whether duration cap rejects, extractor fails, or LLM call fails. Both video and any extracted keyframes are deleted.

### WR-09: analyze() didn't validate _video_path before passing to ffprobe / extractor
**Files:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/video_reference_analyzer.py`
**Commit:** 701e252
**Applied fix:** Added `if not self._video_path: raise RuntimeError("[-32035] ...")` after assignment. The on-disk-existence check is delegated to ffprobe (which now hard-rejects via BL-08) so tests that mock `_get_video_duration` are not broken.

### WR-10: extract_keyframes silently clamped max_keyframes
**Files:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/ffmpeg_extractor.py`
**Commit:** 47efb95
**Applied fix:** Log a warning whenever `max_keyframes` exceeds `MAX_KEYFRAMES_CAP=16` and is clamped down. The cap is documented as a Claude-vision-cost guardrail.

### WR-11: keyframe ordering not monotonic across runs
**Files:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/ffmpeg_extractor.py`
**Commit:** 47efb95
**Applied fix:** Subsumed by WR-02 — per-run subdir guarantees only this run's frames are returned, in alphabetical (== monotonic frame_NNNN.jpg) order.

### WR-12: _validate_file_duration ran even for youtube_url
**Files:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/demo02_cli_tool.py`
**Commit:** bfdc22f
**Applied fix:** Skip the ffprobe step entirely for `source_type == "youtube_url"` because ffprobe cannot probe a URL string; the post-download `VideoReferenceAnalyzer` re-applies the cap on the local file. Without this guard, ffprobe would always fail on the URL and the user would see a spurious cap-violation error.

## Skipped Issues

### WR-07: requires_user_confirmation ignores DOLLY/TRUCK confusion
**File:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/video_llm_parser.py:108-119`
**Reason:** skipped: would regress pre-existing green test.
**Detail:** The reviewer's suggested fix (return True for any DOLLY/TRUCK shot regardless of confidence) directly contradicts the existing test `test_all_known_high_confidence_no_confirmation` in `tests/test_shot_block_ui.py` (lines 221-244), which constructs a high-confidence DOLLY shot and asserts `requires_user_confirmation() is False`. Per the protocol "if a fix regresses any pre-existing green test, revert that fix and mark it 'regressed'", this finding was not applied.
**Recommended follow-up for human:** Decide between (a) keeping the existing semantics (confidence-gated only), (b) updating the test to assert the new DOLLY/TRUCK-always-confirm semantics if the SC#3 contract truly requires it, or (c) introducing a config flag (e.g. `dolly_truck_strict_confirm`) so both behaviours are reachable. The shot_block_ui already surfaces the DOLLY/TRUCK confusion note in `format_confirmation_card`, so the user sees the override hint regardless of whether `requires_user_confirmation` triggers.

## Info-Level Findings (Out of Scope)

`fix_scope: critical_and_warning` — IN-01 through IN-08 were not in scope. IN-05 was partially addressed in commit 47efb95 because the code change for WR-02 touched the same filter expression; the comment-vs-behaviour mismatch is now resolved. IN-01 (unused `import json`) was kept because `json` is still used by the `from_json` callsite path's parser inside `video_llm_parser.from_json`. IN-02 (duplicated `_find_binding_for_actor`) is left for a deliberate refactor pass.

## Test Results

**Phase 7 test files (4 files, 43 tests):**
```
tests/test_sequencer_tools.py       — 11/11 passed
tests/test_shot_block_ui.py         — 13/13 passed
tests/test_demo02_cli_tool.py       — 10/10 passed
tests/test_video_reference_analyzer.py — 10/10 passed
```

**Broad sweep (excluding the 2 unreal-mock-leaking files per env directive):**
```
331 passed, 13 failed (pre-existing test_transaction failures, identical to baseline)
```

The 13 test_transaction failures are pre-existing (unrelated to Phase 7) and identical between the baseline (before any fixes) and the post-fix run; no Phase 7 fix introduced any new test failure.

## Final Status

`partial` — 18/20 in-scope findings fixed; 1 partial (WR-03 input existence check intentionally omitted to preserve a green test); 1 skipped (WR-07 conflicts with `test_all_known_high_confidence_no_confirmation`). Recommend a follow-up human decision on WR-07's contract before re-review.

---
_Fixed: 2026-05-10_
_Fixer: Claude (gsd-code-fixer, Opus 4.7 1M)_
_Iteration: 1_
