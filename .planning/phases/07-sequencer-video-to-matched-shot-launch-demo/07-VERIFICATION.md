# Phase 7 Verification — 07-VERIFICATION.md

**Phase:** 07-sequencer-video-to-matched-shot-launch-demo
**LAUNCH DEMO verification gate**

---

## Phase 7 Success Criteria

| # | Criterion | Evidence Required | Status |
|---|----------|-----------------|--------|
| SC#1 | DEMO-02 ships end-to-end — no competitor has video→matched-shot as of April 2026 | Full pipeline runs on a real YouTube URL or mp4 | TBD |
| SC#2 | SCENE-02: ULevelSequence + CineCamera + keyframes + NL shot blocking | UE editor integration test with sequencer | TBD |
| SC#3 | Video Reference Analyzer: ffmpeg scene-cut + semantic lighting + camera taxonomy | Wave 1 tests pass, manual keyframe test | TBD |
| SC#4 | Ephemeral video processing: yt-dlp → keyframes → cleanup | Video file deleted from /tmp within 5 min | TBD |
| SC#5 | Cold-start test: 3 consecutive random clips pass | Operator-run test on 3 clips | TBD |

---

## Verification Procedures

### SC#1 — DEMO-02 End-to-End

```bash
# In UE editor chat panel:
# Paste: https://www.youtube.com/watch?v=<royalty-free-5s-clip>
# Type: "run demo02 on this video"
# Expected:
#   1. Ephemeral disclaimer appears
#   2. Keyframes extracted (8-16)
#   3. Claude vision analysis returns JSON
#   4. Sequencer sequence created
#   5. CineCamera placed
#   6. Lighting applied
#   7. Sequencer keyframes set
# Verify in UE:
#   - Open Sequencer, verify Shot_001 sequence exists
#   - Verify CineCamera in sequence
#   - Verify keyframes on camera transform
#   - Verify lighting actors in level
```

### SC#2 — SCENE-02 Sequencer Tools

```bash
# In UE editor chat panel:
# "create a level sequence called TestSeq"
# Expected: Level sequence appears in Content Browser

# "add a CineCamera to TestSeq at position (0, 0, 100)"
# Expected: CineCamera actor in level, bound to sequence in Sequencer

# "set a keyframe on the camera at time 2s at (100, 0, 100)"
# Expected: Keyframe appears in Sequencer timeline

# "slow dolly in, then cut wide"
# Expected: Camera moves forward then back in sequencer
```

### SC#3 — Video Reference Analyzer

```bash
# Unit test:
cd NyraHost && python -m pytest tests/test_video_reference_analyzer.py -x -q

# Manual test:
# Provide a 5s mp4 with known content
# Verify ffmpeg extracts correct number of keyframes
# Verify Claude response is valid JSON
# Verify VideoReferenceParams fields are populated
```

### SC#4 — Ephemeral Processing

```bash
# Monitor /tmp during DEMO-02 run:
# Before analysis: video file exists
# After analysis (<5 min): video file is deleted
# Keyframes directory remains (for audit)

ls -la /tmp/nyra_video_*  # Before run: exists
ls -la /tmp/nyra_video_*  # After run: should NOT exist
ls -la /tmp/nyra_keyframes_*  # After run: should exist (for audit)
```

### SC#5 — Cold-Start Test (Operator Run)

```bash
# Use 3 royalty-free or self-created 5s clips:
# Clip 1: Outdoor, golden hour, static camera
# Clip 2: Indoor, studio, dolly movement
# Clip 3: Outdoor, overcast, truck movement

# For each clip:
# 1. Uninstall NYRA plugin
# 2. Clear UE project Saved/NYRA/
# 3. Reinstall plugin
# 4. Open UE
# 5. Run: /demo02 <clip-url-or-path>
# Expected: All 3 clips complete without Meshy/ComfyUI/Claude API key

# Record results in 07-EXIT-GATE.md
```

---

## Source Audit

### ROADMAP Requirements Coverage

| Requirement | Plan(s) | Coverage |
|-------------|---------|----------|
| SCENE-02: ULevelSequence + CineCamera + keyframes | 07-00 | 4 tools: create, add_camera, set_keyframe, author_shot |
| SCENE-02: NL shot blocking | 07-00, 07-02 | SequencerAuthorShotTool + ShotBlockConfirmationUI |
| DEMO-02: YouTube/mp4 -> keyframes -> UE scene + Sequencer | 07-01, 07-02, 07-03 | VideoReferenceAnalyzer + Demo02Orchestrator + CLI tool |
| DEMO-02: Camera taxonomy (user-confirmable) | 07-02 | ShotBlockConfirmationUI with override mechanism |
| DEMO-02: Ephemeral processing | 07-01 | _schedule_cleanup() + _cleanup() |
| DEMO-02: ≤10s clip limit | 07-01, 07-03 | MAX_CLIP_DURATION + CLI validation |

### Feature Coverage (from FEATURES.md)

| Feature | Plan(s) | Coverage |
|---------|---------|----------|
| D1 Reference video → matched UE shot (LAUNCH DEMO) | 07-00, 07-01, 07-02, 07-03, 07-04 | Full pipeline |
| D7 Sequencer automation | 07-00 | 4 sequencer MCP tools |
| D8 Lighting authoring (SCENE-01 from Phase 6) | 07-02 | Integration via Demo02Orchestrator |
| TS6 Scene ops | 07-00 | ActorSpawnTool reused for CineCamera |

### Research Coverage (from RESEARCH.md)

| Item | Plan(s) | Coverage |
|------|---------|----------|
| Claude Opus 4.7 vision | 07-01 | VideoReferenceAnalyzer._analyze_with_claude() |
| FFmpeg scene-cut detection (gt(scene,0.3)) | 07-01 | FFmpegKeyframeExtractor._run_ffmpeg_scene_detect() |
| yt-dlp YouTube download | 07-01 | VideoReferenceAnalyzer._download_youtube() |
| Keyframe sampling strategy (≤16 frames) | 07-01 | FFmpegKeyframeExtractor.extract_keyframes() |
| Ephemeral processing | 07-01 | _schedule_cleanup() + _cleanup() |

---

## Phase 7 Plans Reference

| Plan | Wave | Type | TDD | Dependencies |
|------|------|------|-----|--------------|
| 07-00 | 0 | execute | no | — |
| 07-01 | 1 | tdd | yes | 07-00 |
| 07-02 | 2 | tdd | yes | 07-01 |
| 07-03 | 3 | tdd | yes | 07-00, 07-02 |
| 07-04 | 4 | execute | no | 07-00, 07-01, 07-02, 07-03 |

---

*Verification complete when: all 5 SC are PASS, exit gate verdict is PASS*
