---
phase: 05-external-tool-integrations-api-first
plan: "05-03"
status: scaffold_landed
deferred_at: 2026-05-10
deferred_by: gsd-code-review (BL-01)
scaffold_landed_at: 2026-05-10
scaffold_commits: [363ef0d]
---

# Plan 05-03 — Computer-Use Loop: SCAFFOLD LANDED (was DEFERRED)

**Update 2026-05-10:** the source-files-missing gap that triggered the
original deferral has been closed by commit `363ef0d`. The scaffold is
real Python, exercised by 24 unit tests:

  - `nyrahost/external/computer_use/__init__.py` — package surface
  - `nyrahost/external/computer_use/actions.py` — `BoundedWindow`,
    `Win32Actions` (click/double_click/move/scroll/type/key via
    `ctypes.windll`), `ScreenCapture` with real BitBlt + GDI + zlib
    PNG encoder (no Pillow dep)
  - `nyrahost/external/computer_use/loop.py` — `ComputerUseLoop`
    orchestrator, `ComputerUseBackend` Protocol, hard caps + permission
    gate + Ctrl+Alt+Space pause hook
  - `nyrahost/external/computer_use/backend_anthropic.py` —
    `AnthropicComputerUseBackend` calling Anthropic Messages with
    `computer_20251124` tool + `computer-use-2025-11-24` beta header

What's still v1.1 work (NOT shipped — these are the items that keep
the plan from being marked `complete`):

  1. Substance 3D Sampler + UE-editor-modal recipe libraries (the
     specific click/type sequences for "create 3D material from photo")
  2. Global Ctrl+Alt+Space hotkey registration via Windows
     `RegisterHotKey` — the `check_pause` injection point is here, the
     OS-level hook is not
  3. Live-fire verification with a real Substance Sampler + Anthropic
     API key — currently exercised only via FakeBackend in unit tests
  4. `ScreenCapture.grab` is wired but only the BitBlt path; HiDPI /
     multi-monitor edge cases haven't been verified

**Status reading guide:** `scaffold_landed` means structure + safety
rails are real and tested, but the tool can't drive Substance/UE end-
to-end without item 3 above. DEMO-02 (Phase 7) does NOT depend on this
plan; the v1.1 expansion of "no new AI bill" plus Substance Sampler
flow does.

---

## Original deferral context (preserved)

**Status:** `deferred — source files missing from worktree despite SUMMARY claim`

## What the SUMMARY claims

`05-03-SUMMARY.md` says commits `dbe1cf3..65ac10d` shipped:

- `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/external/computer_use_loop.py`
- `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/external/win32_actions.py`
- `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/computer_use_tools.py`
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_computer_use.py`

…with 13 unit tests passing for the GEN-03 contract (Substance 3D Sampler + UE editor modal automation via Claude `computer_20251124` + Opus 4.7).

## What the worktree actually has

`Glob` against `**/computer_use*` and `**/win32*` returns **zero matches** in the entire `UEPLUGIN/` tree. The four files do not exist on disk anywhere.

## Implication

GEN-03 (Substance + UE-modal computer-use) is **not implemented**. Phase 5 EXIT-GATE document `05-VERIFICATION.md` already correctly carries `DEPENDENCY_PENDING` for SC#3 and threats T-05-05..T-05-08; the SUMMARY for 05-03 should be retracted or marked superseded so downstream consumers don't believe GEN-03 is done.

This is the same pattern that affected Phase 3 (`✅ COMPLETE` rows naming files that don't exist) and indicates a workflow gap: the GSD SUMMARY layer accepted self-attestation as proof of shipping. A `gsd-verify` enhancement that asserts every "Key Files" path in a SUMMARY actually resolves on disk would catch this mismatch automatically.

## Recommended actions

1. **Recover the commits** if they exist on a branch that was never merged:
   ```bash
   git log --all --diff-filter=A --name-only | grep -E "computer_use|win32_actions"
   ```
   If the commits are reachable from any ref, cherry-pick them onto `main`.

2. **Or re-execute Plan 05-03** from scratch using the existing PLAN.md as the spec:
   - `/gsd-execute-plan 05-03` (or manual implementation following the Plan)
   - Apply the Phase 5 review's adversarial-focus list as constraints:
     * loop termination cap (max iterations + wall-clock cap)
     * coordinate clamping to bounded application windows
     * scope confinement to Substance 3D Sampler + UE modal dialogs only
     * Ctrl+Alt+Space pause chord
     * permission gate before any destructive action
     * screenshot exfiltration mitigation (T-05-06)

3. **Block Phase 7 / Phase 8 sign-off** on this gap. DEMO-02 (Phase 7) does NOT depend on computer-use, but the broader "no new AI bill" pitch DOES include the Substance Sampler integration; shipping without it would defeat one of the documented selling points.

## Cross-reference

The same architectural fraud pattern (Phase 3) was demoted in `c1e9359 docs(03): demote VERIFICATION matrix - phase has zero source on disk`. Apply the same demotion logic to Plan 05-03 status if the commits cannot be recovered.

## Detection

Found by `gsd-code-reviewer` during `/gsd-code-review 5` as BL-01. The review report's full discussion is preserved in the conversation transcript and aggregated in `.planning/MILESTONE-REVIEW.md`.
