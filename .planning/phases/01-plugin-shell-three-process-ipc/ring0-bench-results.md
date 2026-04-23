---
status: placeholder
pending_manual_verification: true
authored_date_utc: 2026-04-23
platform_host_at_authoring: macOS Darwin (cannot run UE 5.6 + llama-server.exe)
platform_target: Windows 11 x64 + UE 5.6
requires_operator: Windows dev-machine operator follows ring0-run-instructions.md
plan: 01-15
phase: 01-plugin-shell-three-process-ipc
validates: VALIDATION row 1-ring0 + ROADMAP Phase 1 Success Criterion 3
---

# ⚠️ PLACEHOLDER — this file is populated by running the Plan 14 harness on Windows. Results table is templated, not measured. ⚠️

```
===============================================================================
⚠  PLACEHOLDER — NO MEASUREMENT HAS BEEN RECORDED YET.                        ⚠
⚠                                                                              ⚠
⚠  This file is a STRUCTURED TEMPLATE committed during Plan 15 on a            ⚠
⚠  macOS dev host. Every numeric cell below reads PENDING — no real            ⚠
⚠  Nyra.Dev.RoundTripBench 100 run has been performed against the              ⚠
⚠  fully-assembled UE 5.6 + Windows 11 + Gemma 3 4B plugin build.              ⚠
⚠                                                                              ⚠
⚠  The Plan 14 bench harness (FNyraDevTools + Nyra.Dev.RoundTripBench)         ⚠
⚠  ships as source; Plan 15 authors this placeholder + the operator            ⚠
⚠  runbook (ring0-run-instructions.md). The empirical measurement              ⚠
⚠  that closes ROADMAP Phase 1 Success Criterion 3 + VALIDATION row            ⚠
⚠  1-ring0 is OWED by a Windows operator following ring0-run-instructions.md.  ⚠
⚠                                                                              ⚠
⚠  When populated: replace every `PENDING (awaiting first Windows run)`        ⚠
⚠  cell with the actual measured value, replace the frontmatter               ⚠
⚠  `status: placeholder` with `status: measured`, and set the                 ⚠
⚠  `pending_manual_verification` flag to `false`. Commit with message         ⚠
⚠  `feat(01-15): record ring0 bench results from Windows dev machine`.        ⚠
===============================================================================
```

---

# Ring 0 Stability Gate — Results

**Run date (UTC):** PENDING (awaiting first Windows run)
**Run commit hash:** PENDING (awaiting first Windows run)
**Plan:** 01-15
**Validates:** VALIDATION row `1-ring0` + ROADMAP Phase 1 Success Criterion 3
**Runbook:** [ring0-run-instructions.md](ring0-run-instructions.md)
**Operator:** PENDING (awaiting first Windows run — fill in operator handle / machine label)

---

## Verdict

**ring0 Verdict: PENDING (awaiting first Windows run)**

| Criterion                          | Measured Value                          | Threshold   | Verdict |
|------------------------------------|-----------------------------------------|-------------|---------|
| first_token p95 (ms)               | PENDING (awaiting first Windows run)    | < 500 ms    | PENDING |
| editor_tick_max_ms p95 (ms)        | PENDING (awaiting first Windows run)    | < 33 ms     | PENDING |
| errors                             | PENDING (awaiting first Windows run)    | 0           | PENDING |

Threshold source: ROADMAP Phase 1 Success Criterion 3 — "loopback WebSocket +
localhost HTTP IPC is stable over 100 consecutive round-trips on UE 5.6 with
editor responsive during streaming; this gate unblocks Phase 2's subscription
driving." Targets match RESEARCH §3.6 ("Pass criteria, explicit") verbatim.

### Phase 2 gate status: PENDING

- **If Verdict = PASS:** Phase 1 architectural gate cleared. Phase 2 (Subscription
  Bridge + Four-Version CI Matrix) may proceed from its first wave.
- **If Verdict = FAIL:** Phase 2 is BLOCKED. Re-plan the failing component, ship the
  fix, re-run the bench, commit a new results section (or replace this file).
- **If Verdict = PARTIAL:** Document which criteria passed, which failed, and
  whether Phase 2 can conditionally proceed (e.g., PASS on first_token +
  errors but marginal-FAIL on editor_tick → Phase 2 Wave 0 schedules the WS-thread
  refactor from RESEARCH §3.10 P1.6 as its first deliverable, and SC#3 is
  re-evaluated after the refactor).

---

## Raw Output

The following is the literal Output Log block produced by
`Nyra.Dev.RoundTripBench 100 "Reply with the single word OK only."` on the
Windows operator's dev machine. Until populated, the block shape below shows
the expected schema (from RESEARCH §3.6 / Plan 14 SUMMARY).

```
PENDING (awaiting first Windows run)

Expected shape on a green run:

[NyraDevTools] RoundTripBench results (N=100):
  first_token  p50=  245.3ms  p95=  487.1ms  p99=  612.8ms
  total        p50= 1843.0ms  p95= 2341.5ms  p99= 2889.2ms
  tokens/sec   p50=  33.20    p95=  29.10    p99=  27.40
  editor_tick_max_ms  p50=  18.3  p95=  22.1  p99=  41.2
  errors=0
  PASS first-token p95 < 500 ms
  PASS editor_tick p95 < 33 ms
  PASS zero errors

Expected shape on a red (non-compliant) run (N<100 would-be deliverable):

[NON-COMPLIANT: requires N>=100 per ROADMAP Phase 1 SC#3]

[NyraDevTools] RoundTripBench results (N=3):
  first_token  p50= ...ms  p95= ...ms  p99= ...ms
  ...
  FAIL first-token p95 < 500 ms
  FAIL editor_tick p95 < 33 ms
  FAIL zero errors
```

Operator: replace this entire fenced block with the literal verbatim copy from the
Output Log (keep the `[NyraDevTools] RoundTripBench results (N=100):` header through
the third `PASS` or `FAIL` verdict line).

---

## Full Percentile Table

All metrics per RESEARCH §3.6 definitions. p50 = median, p95 = 95th percentile
(primary gate metric), p99 = 99th percentile (tail-risk indicator).

| Metric               | Unit       | p50                                    | p95                                    | p99                                    | Notes |
|----------------------|------------|----------------------------------------|----------------------------------------|----------------------------------------|-------|
| first_token_ms       | ms         | PENDING (awaiting first Windows run)   | PENDING (awaiting first Windows run)   | PENDING (awaiting first Windows run)   | Time from `chat/send` emission to first non-empty `delta` in `chat/stream`. Gate metric: p95 < 500 ms. |
| total_ms             | ms         | PENDING (awaiting first Windows run)   | PENDING (awaiting first Windows run)   | PENDING (awaiting first Windows run)   | Time from `chat/send` emission to `chat/stream {done:true}`. Informational (not gated). |
| tokens_per_sec       | tokens/s   | PENDING (awaiting first Windows run)   | PENDING (awaiting first Windows run)   | PENDING (awaiting first Windows run)   | `completion_tokens / (total_ms - first_token_ms)`. Informational (not gated). |
| editor_tick_max_ms   | ms         | PENDING (awaiting first Windows run)   | PENDING (awaiting first Windows run)   | PENDING (awaiting first Windows run)   | `max(FApp::GetDeltaTime() * 1000)` observed during streaming via FTSTicker sampler. Gate metric: p95 < 33 ms (= 30 FPS floor). |

Summary counters:

| Counter              | Value                                     | Notes |
|----------------------|-------------------------------------------|-------|
| N (rounds)           | PENDING (awaiting first Windows run)      | Must be 100 for compliance (non-compliant headers force FAIL when N < 100). |
| errors               | PENDING (awaiting first Windows run)      | Round-level errors (timeout, `done:true` with `error` field, supervisor not-Ready). Gate metric: must be 0. |
| frames_per_round     | PENDING (awaiting first Windows run)      | Informational, average across rounds. Tracks chat/stream notification count per round. |

---

## Dev Machine Spec

| Field                 | Value                                    |
|-----------------------|------------------------------------------|
| OS                    | PENDING (awaiting first Windows run)     |
| Windows build number  | PENDING (awaiting first Windows run)     |
| CPU                   | PENDING (awaiting first Windows run)     |
| CPU cores / threads   | PENDING (awaiting first Windows run)     |
| RAM                   | PENDING (awaiting first Windows run)     |
| GPU                   | PENDING (awaiting first Windows run)     |
| GPU driver version    | PENDING (awaiting first Windows run)     |
| UE version            | PENDING (awaiting first Windows run)     |
| Gemma backend         | PENDING (awaiting first Windows run)     |
| Gemma source          | PENDING (awaiting first Windows run)     |
| InferRouter log line  | PENDING (awaiting first Windows run)     |

Expected `Gemma backend` values: `bundled-cuda` | `bundled-vulkan` | `bundled-cpu` | `ollama`
Expected `Gemma source` values:
- `TestProject\Saved\NYRA\models\gemma-3-4b-it-qat-q4_0.gguf (SHA256 verified against ModelPins)`
- OR `Ollama gemma3:4b-it-qat (via http://127.0.0.1:11434)`

---

## Remediation (populated when Verdict ≠ PASS)

Template for each possible failure mode. When the operator commits real results,
delete all bullet blocks that do not apply; keep the ones corresponding to FAIL
verdicts only.

### If `first_token_ms` p95 FAIL (≥ 500 ms)

- **Likely cause #1:** Gemma cold-start (warm-up run from `ring0-run-instructions.md` step "Warm-up run"
  was insufficient on this machine).
- **Action #1:** Retry — run `Nyra.Dev.RoundTripBench 3` twice to warm Gemma, discard both, then run
  the real `Nyra.Dev.RoundTripBench 100` again. Record both attempts' p95 in the results so future
  runs know the warm-up overhead on this class of hardware.

- **Likely cause #2:** CPU-only backend selected when a GPU is present.
- **Action #2:** Check the Output Log for `InferRouter: <backend>` at bench start. If `cpu` despite
  a visible NVIDIA / AMD GPU: re-run `prebuild.ps1` (may not have populated `NyraInfer/cuda/` or
  `NyraInfer/vulkan/`), or check `gpu_probe.py` logs in `Saved/NYRA/logs/nyrahost-<date>.log` for
  the probe output. Submit a Phase 2 Wave 0 plan to fix the GPU-probe logic if gpu_probe is the root cause.

- **Likely cause #3:** Low-spec dev machine — first-token genuinely takes > 500 ms at this hardware tier.
- **Action #3:** Record the measurement honestly. Plan a Fab-listing "minimum dev machine spec" line
  in Phase 8 based on these numbers; optionally revise the SC#3 threshold for Phase 2 with a
  Phase-2-CI rationale doc.

### If `editor_tick_max_ms` p95 FAIL (≥ 33 ms)

- **Likely cause:** RESEARCH §3.10 P1.6 — Phase 1 ships WS I/O on the GameThread; bursty
  `chat/stream` delivery + JSON parse work eats the 16.67 ms frame budget.
- **Action:** Plan 2-01 (or similar Phase 2 Wave 0 plan) moves WS I/O to a dedicated thread with
  `AsyncTask(ENamedThreads::GameThread, ...)` marshalling to Slate. This is acknowledged
  in the Phase 1 Plan 14 SUMMARY "Known limitations" section (#1 Synchronous GameThread pump).
- **Phase 2 blocked?** If this is the ONLY failing criterion and the magnitude is marginal
  (e.g., p95 = 34-38 ms), Plan 15 may set Verdict = PARTIAL and allow Phase 2 Wave 0 to
  schedule the refactor before its critical-path work. If magnitude is severe (p95 > 50 ms)
  or combined with other FAILs, Phase 2 is BLOCKED.

### If `errors` FAIL (> 0)

- **Likely cause #1:** Handshake flake — WS connection dropped mid-bench (supervisor respawns,
  in-flight replays, but the bench's BindStatic handler only listens for the ORIGINAL req_id so
  the replay notifications drop and the round times out).
- **Action #1:** Check `Saved/NYRA/logs/nyrahost-<date>.log` for disconnect + reconnect events
  during the bench window. If present: Phase 1 Plan 10's restart policy is firing inside the
  bench window; root-cause the NyraHost crash (most common: Gemma OOM on constrained systems)
  and re-run after fix.

- **Likely cause #2:** NyraHost crashed mid-bench (Gemma OOM, llama-server.exe access violation,
  Python exception in an async task).
- **Action #2:** Inspect the log for Python stack traces. Common Phase 1 crashes: `MemoryError`
  on llama-server load (GPU VRAM insufficient → switch to Vulkan or CPU backend); `FileNotFoundError`
  on mid-run attachment ingest; `asyncio.TimeoutError` on Ollama API lag. Fix, re-run.

- **Likely cause #3:** Ollama fast path selected at startup, Ollama service died mid-bench.
- **Action #3:** Confirm Ollama is running (`ollama ps`). Restart Ollama. Re-run bench. If
  Ollama repeatedly dies, switch to bundled llama-server path by temporarily stopping Ollama
  before the bench.

**Phase 2 BLOCKED until `errors=0` is achieved.** Unlike the other two criteria, a non-zero
error count signals an architectural-stability regression that must be fixed — Phase 2's
subscription bridge cannot be layered on top of an unstable Phase 1 IPC foundation.

---

## Re-run history (if applicable)

Template for tracking multiple bench invocations on the same machine (e.g.,
before and after a fix, or to show warm-vs-cold variance).

| Attempt | UTC datetime | N    | first_token p95 | editor_tick p95 | errors | Notes                             | Commit hash |
|---------|--------------|------|-----------------|-----------------|--------|-----------------------------------|-------------|
| 1       | PENDING      | 100  | PENDING         | PENDING         | PENDING| PENDING (awaiting first Windows run) | PENDING     |

*Operator: add rows as needed; never delete rows. Final official result is the last row with
Verdict = PASS (or the agreed-upon conditional-PASS per the Phase 2 gate logic above).*

---

## Links

- **Runbook:** [ring0-run-instructions.md](ring0-run-instructions.md)
- **Bench harness source (Plan 14):** `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Dev/FNyraDevTools.cpp` (commit `7f479b2`)
- **Plan 14 SUMMARY:** [01-14-ring0-bench-harness-SUMMARY.md](01-14-ring0-bench-harness-SUMMARY.md)
- **Plan 15 SUMMARY:** [01-15-ring0-run-and-commit-results-SUMMARY.md](01-15-ring0-run-and-commit-results-SUMMARY.md) (written alongside this placeholder)
- **RESEARCH §3.6 (Pass criteria):** `01-RESEARCH.md` §3.6
- **VALIDATION row 1-ring0:** [01-VALIDATION.md](01-VALIDATION.md)
- **ROADMAP Phase 1 Success Criterion 3:** `.planning/ROADMAP.md` §"Phase 1: Plugin Shell + Three-Process IPC"

---

## Integrity notes (for future operators / auditors)

When you replace `PENDING` cells with real measurements:

1. Update the frontmatter: set `status: measured`, `pending_manual_verification: false`,
   and add `measured_date_utc: <YYYY-MM-DD HH:MM>`, `measured_commit_hash: <short-hash>`,
   `measured_operator: <handle>`, `measured_machine_label: <optional>`.
2. Remove this entire "Integrity notes" section — its purpose ended when the real
   measurement landed.
3. Remove the prominent PLACEHOLDER banner at the top of the file.
4. Remove the "Expected shape" template from the Raw Output section — keep only the
   real verbatim copy.
5. Update `ring0 Verdict` line and all three verdict cells in the table.
6. Commit message: `feat(01-15): record ring0 bench results from Windows dev machine`.
7. In the same commit, update the Plan 15 SUMMARY.md's "Metrics" section to reflect
   that empirical measurement is complete, and flip STATE.md's `pending_manual_verification`
   flag for Plan 15 to `false`.
8. Update ROADMAP.md's Phase 1 progress footnote: remove the "architectural gate empirical
   verification pending Windows run" note and mark SC#3 fully satisfied.
