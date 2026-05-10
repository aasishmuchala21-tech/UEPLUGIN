---
phase: 07-sequencer-video-to-matched-shot-launch-demo
plan: "07-01"
subsystem: video-reference-analyzer
tags: [demo-02, ffmpeg, keyframe-extraction, claude-vision, ephemeral-processing]

requires:
  - phase: "07-00"
    provides: VideoReferenceParams + ShotBlock + CameraMoveType
provides:
  - FFmpegKeyframeExtractor (extract_keyframes with FileNotFoundError; scene-cut at threshold 0.3)
  - VideoReferenceAnalyzer (analyze entry; 10s clip cap; ephemeral cleanup; YouTube URL routing)
affects: [07-02, 07-04]

requirements-completed: [SCENE-02, DEMO-02]

duration: ~8min
completed: 2026-05-10
---

# Phase 07 Plan 01: Video Reference Analyzer - Summary

**DEMO-02 entry pipeline source-layer complete: FFmpegKeyframeExtractor + VideoReferenceAnalyzer replacing the pre-existing files that contained YAML plan-frontmatter as their body (SyntaxError on every import). 10/10 video reference analyzer tests now green.**

## Note

The pre-existing `ffmpeg_extractor.py` and `video_reference_analyzer.py` files were corrupted with literal plan-frontmatter content as their Python source. This plan executes a full replacement with minimal-viable implementations matching the existing test contract: extract_keyframes / _run_ffmpeg_scene_detect / analyze / _download_youtube / _get_video_duration / _extract_keyframes / _analyze_with_claude / _cleanup / _raw_to_params. Ephemeral processing per ROADMAP DEMO-02 is enforced: source video and keyframe JPEGs are unlinked from /tmp after analyze completes (or on the failure path).

## Verification

```text
python -m pytest tests/test_video_reference_analyzer.py -q
=========================== 10 passed in 0.06s ===========================
```

## Status

✅ **Plan 07-01 SOURCE COMPLETE.**
