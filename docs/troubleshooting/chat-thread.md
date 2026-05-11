# Chat thread issues

## "thread_limit_reached" (-32051)

Aura caps at ~4 concurrent threads; NYRA mirrors via Phase 13-A. Close an existing tab before opening another.

## A message is stuck "thinking…" forever

1. Click the per-message **Cancel** chip (Phase 18-F) — fires `chat/cancel` with the req_id.
2. If the chip doesn't appear, hit **Esc** (Phase 18-F keyboard shortcut bound to cancel).
3. Last resort: **Settings → Restart NYRA**. Phase 1 supervisor will kill the sidecar + respawn cleanly.

## "this person already said that" — duplicate messages

The supervisor's in-flight replay (Phase 1 P1.7) re-sends the last request after a respawn. If you see duplicate user turns, the previous turn finished AFTER the respawn started — harmless but noisy. We're tightening dedup in v1.1.

## Custom Instructions aren't being followed

Phase 11-B reads them from `<Project>/Saved/NYRA/instructions.md` on every WS round-trip via the chat handler's `_instructions_prefix()`. Verify:
1. The file exists (Settings → Custom Instructions shows the body).
2. You haven't exceeded the 64 KB cap (-32041).
3. The model is honouring them — Sonnet sometimes ignores subtle conventions; pin Opus to test.

## "no_resume_record" after a crash

Phase 18-C only writes resume.json on tool-call boundaries — if the agent crashed mid-text generation, there's nothing to resume. Open a new chat and re-paste the prompt.

## Threads don't sync across teammates

Phase 17-C ships `LocalRoomBackend` only. Real cross-machine sync needs the multiplayer server deployed by the founder.
