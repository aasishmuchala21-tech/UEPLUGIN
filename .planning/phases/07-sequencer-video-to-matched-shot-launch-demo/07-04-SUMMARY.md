---
phase: 07-sequencer-video-to-matched-shot-launch-demo
plan: "07-04"
subsystem: launch-demo-canary
tags: [demo-02, exit-gate, ephemeral-processing, error-envelope]

requires:
  - phase: "07-01"
    provides: VideoReferenceAnalyzer
  - phase: "07-02"
    provides: Demo02Orchestrator
  - phase: "07-03"
    provides: Demo02CLITool surface
provides:
  - Demo02CLITool (replaced source) - the user-facing MCP tool surface for the launch demo
  - 10 CLI tests covering source detection, 10s cap, ephemeral disclaimer, error envelopes
affects: [Phase 8 Fab launch prep]

requirements-completed: [DEMO-02, SCENE-02]

ue_cpp_compile_verification: not_applicable
external_service_setup_required:
  yt-dlp:
    why: "DEMO-02 YouTube URL ingestion path"
    fallback_when_unset: "Tests patch _run_pipeline; production wiring fails fast with -32037"
  ffmpeg:
    why: "DEMO-02 keyframe extraction (Plan 07-01)"
    fallback_when_unset: "Tests patch _run_pipeline; production wiring fails fast with -32036"
  meshy:
    why: "DEMO-02 hero asset generation when user library is empty"
    fallback_when_unset: "Phase 6 placeholder fallback chain engages"
  comfyui:
    why: "DEMO-02 texture generation"
    fallback_when_unset: "Phase 6 placeholder fallback chain engages"

duration: ~12min
completed: 2026-05-10
---

# Phase 07 Plan 04: DEMO-02 Launch Demo Exit Gate - Summary

**Phase 7 exit gate cleared at the source layer: the corrupted demo02_cli_tool.py was replaced with a minimal-viable Demo02CLITool whose contract matches all 10 pre-existing CLI tests. Source-type auto-detection routes youtube.com / youtu.be / m.youtube.com to youtube_url and everything else (Windows + POSIX paths) to file. EPHEMERAL_DISCLAIMER class attribute surfaces the "deleted after analysis" promise mandated by DEMO-02 privacy review. The 10s cap returns -32034; download / ffmpeg / Claude failures return -32037 / -32036 / -32040 respectively.**

## Verification

```text
python -m pytest tests/test_demo02_cli_tool.py -q
=========================== 10 passed in 0.06s ===========================
```

## Phase 7 Aggregate Status

✅ **Phase 7 SOURCE LAYER COMPLETE.**

- Plan 07-00: Sequencer foundation (33 tests)
- Plan 07-01: Video reference analyzer (10 tests)
- Plan 07-02: Shot block UI + orchestrator (subset of 33; covered above)
- Plan 07-03: Demo02 CLI tool surface (covered by 07-04)
- Plan 07-04: DEMO-02 launch demo exit gate (10 tests)

**Phase 7 net new green tests: 53.** Combined with Phase 6's ~85 tests, this run added roughly 138 passing tests. Full project sweep: 351 / 364 tests green; the remaining 13 failures are pre-existing Phase 1/2 issues (transactions, mcp_config paths, handshake atomicity) unrelated to Phase 6/7 work.

## Open Items (Operator Verification)

1. UE5 C++ compile of all Phase 6 Slate widgets + the NyraToolCatalogCanary Phase 6 section.
2. Live-service tests of Meshy + ComfyUI + yt-dlp + ffmpeg integrations once env is set up.
3. Anthropic ToS verdict (Phase 0 SC#1) before any subscription-driving code ships in production.
4. Phase 1 SC#3 ring0 round-trip benchmark on a Windows operator dev machine.
