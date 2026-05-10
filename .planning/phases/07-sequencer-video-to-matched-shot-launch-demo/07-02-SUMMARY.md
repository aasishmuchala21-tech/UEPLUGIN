---
phase: 07-sequencer-video-to-matched-shot-launch-demo
plan: "07-02"
subsystem: shot-block-ui-and-orchestrator
tags: [demo-02, dolly-truck-confusion, user-confirmation, orchestrator]

requires:
  - phase: "07-00"
    provides: VideoReferenceParams, CameraMoveType, ShotBlock
  - phase: "07-01"
    provides: VideoReferenceAnalyzer (upstream producer of VideoReferenceParams)
provides:
  - shot_block_ui (existing): ShotBlockConfirmationUI, CONFUSION_PAIRS, CAMERA_MOVE_DISPLAY
  - demo02_orchestrator (existing): Demo02Orchestrator with run_video_to_sequencer + run_with_confirmation; .to_json() round-trip into SequencerAuthorShotTool wired in this plan
affects: [07-04]

requirements-completed: [DEMO-02, SCENE-02]

duration: ~5min
completed: 2026-05-10
---

# Phase 07 Plan 02: Shot Block UI + Orchestrator - Summary

**Source-layer was already in place from earlier project work. This plan delivered the missing wiring: VideoReferenceParams.to_json() (already covered in Plan 07-00 commit) so Demo02Orchestrator._author_shots can serialize the reference into SequencerAuthorShotTool's video_reference_json parameter without an AttributeError. Tests exercise the full confirmation gate including the dolly/truck confusion pair from PITFALLS Section 6.2.**

## Verification

```text
python -m pytest tests/test_shot_block_ui.py tests/test_demo02_cold_start.py -q
=========================== 22 passed in 0.05s ===========================
```

## Status

✅ **Plan 07-02 SOURCE COMPLETE** (delivered via Plan 07-00 wiring fix).
