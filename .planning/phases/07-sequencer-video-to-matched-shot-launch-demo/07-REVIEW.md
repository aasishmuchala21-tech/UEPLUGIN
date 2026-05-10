---
phase: 07-sequencer-video-to-matched-shot-launch-demo
reviewed: 2026-05-10T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/video_llm_parser.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/sequencer_tools.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/shot_block_ui.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/demo02_orchestrator.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/ffmpeg_extractor.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/video_reference_analyzer.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/demo02_cli_tool.py
findings:
  critical: 8
  warning: 12
  info: 8
  total: 28
status: issues_found
---

# Phase 7 Code Review Report

**Reviewed:** 2026-05-10
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

This code does not run end-to-end. There are at least three independent BLOCKERs that turn the LAUNCH-DEMO pipeline into AttributeError/TypeError as soon as the orchestrator path executes. The Phase 7 test suite still passes because the four `Sequencer*Tool` classes never have `execute()` invoked under test (only static property checks), the orchestrator is never round-tripped through real `from_json`, and `get_primary_lighting_params()` is never called.

Wave 0 contains the structural defects (mixin not inherited, missing `from_json` deserializer, wrong UE API name). Wave 1 contains the platform/cleanup defects (hardcoded POSIX path, ffprobe-failure silently passes the 10-s cap, mixed `asyncio.run` instead of `run_async_safely`). Wave 2 (`shot_block_ui`) and the `Demo02Orchestrator` are functionally OK on the test path but their happy-path target crashes through the issues in Waves 0/1.

## Critical Issues

### BL-01: `Sequencer*Tool` classes don't inherit `SequencerToolMixin`; every helper call AttributeErrors

**File:** `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/sequencer_tools.py:94, 130, 188, 259`

**Issue:** `SequencerCreateTool`, `SequencerAddCameraTool`, `SequencerSetKeyframeTool`, and `SequencerAuthorShotTool` all declare `class X(NyraTool):` — none of them include `SequencerToolMixin`. Yet their `execute()` methods call mixin methods (`self._create_level_sequence`, `self._bind_camera_to_sequence`, `self._set_transform_keyframe`, etc.). Existing tests pass because they only check static properties, never call `execute()`. At runtime every `execute()` call will raise AttributeError.

**Fix:** Change each class declaration to `class X(SequencerToolMixin, NyraTool):`.

### BL-02: `VideoReferenceParams.from_json` is never defined; orchestrator → sequencer path AttributeErrors

**File:** `sequencer_tools.py:293`

**Issue:** `Demo02Orchestrator._author_shots` calls `params.to_json()` and passes the JSON string into `SequencerAuthorShotTool` as `video_reference_json`. That tool then calls `VideoReferenceParams.from_json(...)`. But `video_llm_parser.py` only defines `to_json` — there is no `from_json`. Every successful Demo02Orchestrator run hits AttributeError.

**Fix:** Add a symmetric `@classmethod from_json(cls, payload: str) -> VideoReferenceParams` to `video_llm_parser.py` that JSON-decodes and rebuilds the dataclass with proper enum coercion and tuple casting for `subject_position`/`primary_color`/`fog_color`/positions/rotations.

### BL-03: `get_primary_lighting_params` passes wrong kwarg `primary_temperature` to `LightingParams`; raises TypeError

**File:** `video_llm_parser.py:97`

**Issue:** `LightingParams` (in `scene_types.py`) has the field `primary_temperature_k`. `video_llm_parser.py:97` calls `LightingParams(..., primary_temperature=self.primary_temperature_k, ...)` — wrong kwarg name. Raises `TypeError: __init__() got an unexpected keyword argument 'primary_temperature'`. No existing test exercises this method, so it slipped through.

**Fix:** Rename to `primary_temperature_k=self.primary_temperature_k`.

### BL-04: `_download_youtube` returns hardcoded `/tmp/downloaded_video.mp4`, breaks YouTube path on Windows

**File:** `video_reference_analyzer.py:77-79`

**Issue:** Three problems compound: (1) `/tmp` doesn't exist on Windows (PROJECT.md mandates Windows-only for v1), (2) no actual yt-dlp invocation, (3) the duration check fails on missing file → returns 0.0 → DEMO-02 proceeds → `_extract_keyframes` raises FileNotFoundError. SUMMARY notes the shortcut but the source ships unguarded.

**Fix:** Either raise `NotImplementedError("[-32037] YouTube download via yt-dlp is not yet wired up; attach a local mp4 instead.")` or implement real `yt-dlp` subprocess using `tempfile.mkdtemp()`.

### BL-05: Wrong UE API call: `add_keyframe_absolute_focal_focus` does not exist; FOV uses focal-length API with degree units

**File:** `sequencer_tools.py:69-71`

**Issue:** The Unreal Python API exposes `add_keyframe_absolute_focal_length` (mm) and `add_keyframe_absolute_focus_distance` (cm). There is no `add_keyframe_absolute_focal_focus`. Even if renamed, the input is `fov_degrees` but UE expects mm — needs conversion `focal_mm = (sensor_width / 2) / tan(fov_deg * pi / 360)`.

**Fix:** Rename + convert; apply at every call site (`:232`, `:314`).

### BL-06: `_bind_camera_to_sequence` is passed an actor *path string*, not an actor object

**File:** `sequencer_tools.py:172`

**Issue:** `SequencerAddCameraTool.execute` does `binding = self._bind_camera_to_sequence(seq, spawn_result.data["actor_path"])` — but `actor_path` is a string. `LevelSequenceEditorSubsystem.add_possible_binding_to_sequence` requires a UObject Actor. UE will reject the string at runtime. Mixin signature `camera_actor: Any` hides the type error.

**Fix:** Load the actor object first: `actor_obj = unreal.EditorAssetLibrary.load_asset(spawn_result.data["actor_path"])`, then bind.

### BL-07: DEMO-02 `_validate_file_duration` permanently returns `True`; the 10-s cap is not enforced in production

**File:** `demo02_cli_tool.py:101-103`

**Issue:** ROADMAP requires "≤10s mp4" enforced before any LLM dispatch. With this stub, a user can paste a 30-minute clip; pipeline pushes 30 minutes of keyframes and a 30-minute Claude call. Security-adjacent: defeats cost-bounding for the user's Claude subscription quota.

**Fix:** Implement via ffprobe (reuse `VideoReferenceAnalyzer._get_video_duration`); reject `0 < duration <= MAX_CLIP_SECONDS`.

### BL-08: `_get_video_duration` silently returns 0.0 on ffprobe failure, bypassing the 10-s cap

**File:** `video_reference_analyzer.py:81-92`

**Issue:** On any ffprobe failure (binary missing, video unreadable, timeout, format unsupported), this returns 0.0. The caller compares `if duration > MAX_CLIP_SECONDS` — `0.0 > 10` is False, so the analyzer proceeds with an unprobed file of arbitrary length and feeds it to Claude. Doesn't `check=True`. Combined with BL-04, YouTube path always lands here with 0.0.

**Fix:** Treat probe failure as a hard reject with `check=True`; raise `RuntimeError("[-32035] Could not probe video duration: ...")` and let it propagate from `analyze()`.

## Warnings

### WR-01: `asyncio.run` used inside sync `execute()` will deadlock when called from an async WS handler

**Files:** `demo02_cli_tool.py:73`, `video_reference_analyzer.py:52, 68`

**Issue:** Per Phase 6 review and `tools/base.py:13` (`run_async_safely`), tools must use `run_async_safely(coro)` in sync paths. Phase 7 reintroduced raw `asyncio.run` in three places. Tests pass because pytest doesn't run inside a NyraHost event loop.

**Fix:** Replace each `asyncio.run(coro)` with `run_async_safely(coro)`.

### WR-02: `extract_keyframes` glob picks up stale files from prior runs

**File:** `ffmpeg_extractor.py:64-66`

**Issue:** Writes `nyra_kf_*.jpg` into `output_dir` (default `tempfile.gettempdir()`) and globs the entire directory. Stale files from previous runs (failed cleanup, parallel runs) get returned to the caller — Claude then receives keyframes from a different video. Same issue in `_run_ffmpeg_scene_detect`.

**Fix:** Use `tempfile.mkdtemp(prefix="nyra_kf_", ...)` per run; cleanup removes the run_dir, not just individual files.

### WR-03: `_run_ffmpeg_scene_detect` skips existence check and exception handling that `extract_keyframes` enforces

**File:** `ffmpeg_extractor.py:68-84`

**Issue:** Inconsistent contracts between two public-ish methods of the same class. Missing FileNotFoundError + try/except around subprocess.

**Fix:** Mirror `extract_keyframes` structure.

### WR-04: `transform.location` / `transform.rotation` JSON Schema is malformed

**File:** `sequencer_tools.py:201-207`

**Issue:** `location` and `rotation` are missing `"type": "object"` and inner `properties` wrapper. Strict validators (and Claude's tool-call validator) treat `x/y/z` as keyword schema entries, not properties.

**Fix:** Wrap in `{"type": "object", "properties": {...}, "required": [...]}`.

### WR-05: `params.get("light_intensity")` (and friends) treat `0` as "skip", silently swallowing legitimate values

**File:** `sequencer_tools.py:231-236`

**Issue:** `if params.get("fov_degrees"):` treats 0 as falsy → skipped. A user wanting to keyframe a light intensity to 0 (dim out) cannot do it.

**Fix:** Use explicit `is not None` checks.

### WR-06: `_camera_move_to_keyframe_pattern` discards `shot.start_time`/`shot.end_time` and overlays every shot on the outer window

**File:** `sequencer_tools.py:388-406`

**Issue:** Uses outer `start`/`end` for every shot, ignoring per-shot times. Multi-shot params collapse onto the same window, each successive shot overwriting previous keyframes.

**Fix:** Use the shot's own time bounds with fallback to outer window when shot times are sentinel.

### WR-07: `requires_user_confirmation()` ignores DOLLY/TRUCK confusion, silently auto-authoring high-confidence DOLLY shots

**File:** `video_llm_parser.py:108-119`

**Issue:** `shot_block_ui.py` exists specifically because dolly/truck confusion needs human confirmation (PITFALLS §6.2). But `requires_user_confirmation` only triggers on `confidence < 0.7` or UNKNOWN. A high-confidence DOLLY (0.95) bypasses the confirmation flow entirely. Contradicts SC#3 ("camera-move taxonomy is user-confirmable").

**Fix:** Add `if self.camera_move_type in (CameraMoveType.DOLLY, CameraMoveType.TRUCK): return True` to the predicate.

### WR-08: Cleanup runs only on the happy path; if duration check raises, only video is unlinked but keyframes leak

**File:** `video_reference_analyzer.py:46-73`

**Issue:** `analyze()` extracts keyframes only after the duration check passes. SC#4 requires keyframes deleted as well as the video; current `try/finally` only wraps the LLM call.

**Fix:** Wrap from `_video_path` assignment through return in a single `try/finally` that always calls `_cleanup`.

### WR-09: `analyze()` doesn't validate `_video_path is not None` before passing to ffprobe / extractor

**File:** `video_reference_analyzer.py:51-64`

**Issue:** If `_download_youtube` is wired up correctly later and ever returns None (download failure swallows its exception), `_get_video_duration(None)` and `extract_keyframes(None)` raise opaque errors.

**Fix:** Defensive check after assignment: `if not self._video_path or not Path(self._video_path).exists(): raise RuntimeError(...)`.

### WR-10: `extract_keyframes` `max_keyframes` upper-bound clamp ignores the parameter contract

**File:** `ffmpeg_extractor.py:46`

**Issue:** Silently rewrites a caller's request of `max_keyframes=32` to `16`. Defensible but should log a warning when clamping.

**Fix:** Log when clamping. Or document the cap explicitly.

### WR-11: `extract_keyframes` returns paths sorted alphabetically; combined with WR-02 stale-files bug they may be out-of-order across runs

**File:** `ffmpeg_extractor.py:64`

**Issue:** Mixed with stale files from other prefixes/runs, ordering is no longer monotonic. The fix in WR-02 (per-run subdir) also fixes this.

**Fix:** Subsumed by WR-02 fix.

### WR-12: `_validate_file_duration` is invoked even for `source_type == "youtube_url"` before the file exists

**File:** `demo02_cli_tool.py:66`

**Issue:** Cap check runs before download, can't probe a YouTube URL string. Once BL-07 is fixed with ffprobe, calling ffprobe on a URL fails. Must guard YouTube branch.

**Fix:** Skip cap check for `source_type == "youtube_url"` (cap re-checked post-download in pipeline).

## Info

### IN-01: Unused `import json` in `SequencerAuthorShotTool.execute`

**File:** `sequencer_tools.py:282`

**Fix:** Remove after BL-02 lands (JSON parsing delegated to `from_json`).

### IN-02: `_find_binding_for_actor` duplicated verbatim across two tool classes

**Files:** `sequencer_tools.py:247-256` and `:408-416`

**Fix:** Move to `SequencerToolMixin` once BL-01 is fixed.

### IN-03: Dead `keyframe.get("fov")` branch in `_author_from_video_reference`

**File:** `sequencer_tools.py:313-314`

**Fix:** Either populate fov in the pattern (preferred — current code drops shot.fov entirely) or remove the dead branch.

### IN-04: `_keyframes` instance attribute is set but never read

**File:** `video_reference_analyzer.py:44, 65`

**Fix:** Either drop or use for SC#4 audit logging.

### IN-05: Comment "Evenly-spaced keyframes via select... brittle" then proceeds to use `thumbnail` filter, which does not produce evenly-spaced frames

**File:** `ffmpeg_extractor.py:48-57`

**Fix:** Use `select='not(mod(n\\,N))'` with `N = total_frames / max_keyframes` or `fps=max_keyframes/duration`.

### IN-06: `CameraMoveType.TILT` enum has only one space alignment, breaking the visual column

**File:** `video_llm_parser.py:23`

**Fix:** Cosmetic alignment.

### IN-07: `confusion_note` chained-conditional expression is clever but hard to read

**File:** `shot_block_ui.py:114-122`

**Fix:** Replace with a small helper function.

### IN-08: `_format_confirmation_message` formats `{shot.fov:.0f}mm equivalent` but `fov` is degrees per dataclass docstring

**File:** `shot_block_ui.py:53`

**Fix:** Display as `{shot.fov:.0f}°` or rename `fov` to `focal_length_mm` and store millimetres. Touches the same FOV-vs-mm confusion as BL-05.

---

## Recommendation

Do not ship. The four MCP tools that own SC#2 (Sequencer create / add-camera / set-keyframe / author-shot) all crash on the first non-static call. The orchestrator's `to_json -> from_json` round-trip is broken. The DEMO-02 CLI's 10-second cap is unenforced. The YouTube path is a literal `/tmp` string. Together these defeat the LAUNCH-DEMO contract end-to-end.

Fix BL-01 through BL-08, run the existing test suite plus a manual orchestrator → sequencer integration, then re-review.

_Reviewed: 2026-05-10_
_Reviewer: Claude (gsd-code-reviewer, standard depth)_
