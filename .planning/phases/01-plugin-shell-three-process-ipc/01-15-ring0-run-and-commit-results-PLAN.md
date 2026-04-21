---
phase: 01-plugin-shell-three-process-ipc
plan: 15
type: execute
wave: 5
depends_on: [14]
autonomous: false
requirements: [PLUG-02, PLUG-03, CHAT-01]
files_modified:
  - .planning/phases/01-plugin-shell-three-process-ipc/ring0-bench-results.md
  - .planning/phases/01-plugin-shell-three-process-ipc/ring0-run-instructions.md
objective: >
  Phase 1 architectural gate: run `Nyra.Dev.RoundTripBench 100` end-to-end
  against the fully built plugin (Gemma downloaded, NyraHost authenticated,
  editor at normal focus), capture the full LogNyra output, decide PASS
  vs FAIL on the documented thresholds, and commit the results +
  dev-machine spec to
  `.planning/phases/01-plugin-shell-three-process-ipc/ring0-bench-results.md`.
  This plan is a CHECKPOINT plan (autonomous=false) — after Claude prepares
  run instructions + result capture template, the USER runs the bench on
  their dev machine and pastes the report. Claude then commits the
  formatted results. Closes VALIDATION row 1-ring0 and ROADMAP Phase 1
  Success Criterion 3.
must_haves:
  truths:
    - ".planning/phases/01-plugin-shell-three-process-ipc/ring0-run-instructions.md exists with step-by-step prerequisites (Gemma downloaded, supervisor Ready, editor window focused, all 4 checkboxes before run)"
    - "ring0-run-instructions.md specifies the exact command Nyra.Dev.RoundTripBench 100 \"Reply with the single word OK only.\""
    - "ring0-bench-results.md is created with a template: dev machine spec (GPU, CPU, RAM, Gemma model path), raw LogNyra block, pass/fail verdict per criterion, date"
    - "After the user pastes the bench output, ring0-bench-results.md is updated with actual results and the PASS/FAIL verdict is finalised"
    - "If any criterion fails, ring0-bench-results.md lists remediation action and explicitly flags Phase 2 as blocked until a re-run passes"
  artifacts:
    - path: .planning/phases/01-plugin-shell-three-process-ipc/ring0-run-instructions.md
      provides: "Step-by-step Ring 0 run instructions for the dev machine"
      contains: "Nyra.Dev.RoundTripBench 100"
    - path: .planning/phases/01-plugin-shell-three-process-ipc/ring0-bench-results.md
      provides: "Canonical record of the Ring 0 run: dev spec, raw output, verdict"
      contains: "ring0 Verdict"
  key_links:
    - from: ring0-bench-results.md
      to: VALIDATION.md row 1-ring0
      via: "The results doc is the authoritative evidence for the 1-ring0 test ID"
      pattern: "1-ring0"
    - from: ring0-bench-results.md
      to: ROADMAP.md Phase 1 Success Criterion 3
      via: "Records the 100-round-trip gate outcome that unblocks Phase 2"
      pattern: "100 consecutive"
---

<objective>
Plan 14 built the harness; Plan 15 executes it and commits the canonical
outcome. This is a deliberate CHECKPOINT plan — the user runs the bench
because:

1. Fully-assembled NyraHost requires python-build-standalone + wheels +
   Gemma GGUF (3.16 GB) + llama-server binaries actually present on the dev
   machine. Executor agent in this environment cannot satisfy that.
2. The "editor responsive during streaming" assertion is only meaningful on
   real hardware with a real GPU/CPU — there is no headless equivalent.

Claude's job in this plan:
A. Write the run-instructions markdown so the user has a precise procedure.
B. Pre-create the results markdown with slots to fill in.
C. When the user pastes back the LogNyra output, parse verdicts and commit
   the finalised results.

Per ROADMAP Phase 1 Success Criterion 3: "loopback WebSocket + localhost
HTTP IPC is stable over 100 consecutive round-trips on UE 5.6 with editor
responsive during streaming; this gate unblocks Phase 2's subscription
driving." VALIDATION row 1-ring0: `Nyra.Dev.RoundTripBench 100` passes with
`p95 first-token < 500 ms; p95 editor tick < 33 ms; errors == 0`.

Purpose: close Phase 1 architectural gate with committed evidence.
Output: 2 markdown files.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-VALIDATION.md
@.planning/ROADMAP.md
@TestProject/Plugins/NYRA/Source/NyraEditor/Public/Dev/FNyraDevTools.h
</context>

<interfaces>
Expected LogNyra bench output shape (from Plan 14 FormatReport):
```
[NyraDevTools] RoundTripBench results (N=100):
  first_token  p50=  245.3ms  p95=  487.1ms  p99=  612.8ms
  total        p50= 1843.0ms  p95= 2341.5ms  p99= 2889.2ms
  tokens/sec   p50=  33.20    p95=  29.10    p99=  27.40
  editor_tick_max_ms  p50=  18.3  p95=  22.1  p99=  41.2
  errors=0
  PASS first-token p95 < 500 ms
  PASS editor_tick p95 < 33 ms
  PASS zero errors
```
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Create ring0-run-instructions.md (step-by-step pre-run checklist)</name>
  <files>
    .planning/phases/01-plugin-shell-three-process-ipc/ring0-run-instructions.md
  </files>
  <read_first>
    - .planning/phases/01-plugin-shell-three-process-ipc/01-VALIDATION.md row 1-ring0 + §"Manual-Only Verifications" row "Editor responsiveness during 100-RT burst"
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.6 (pass criteria)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Dev/FNyraDevTools.h (Plan 14 contract)
    - docs/JSONRPC.md §3.3 chat/send expected shape
  </read_first>
  <action>
    Create `.planning/phases/01-plugin-shell-three-process-ipc/ring0-run-instructions.md`:

    ```markdown
    # Ring 0 Stability Gate — Run Instructions

    **Plan:** 01-15
    **Requirement:** ROADMAP Phase 1 Success Criterion 3 + VALIDATION row 1-ring0
    **Who runs:** Dev machine operator (Windows 11 + UE 5.6 + Gemma downloaded)
    **Expected duration:** ~5-10 minutes wall-clock (100 rounds × 2-3 s/round plus warm-up)

    ## Preconditions Checklist

    Run each in order. DO NOT proceed to the bench command until all 4 are confirmed.

    - [ ] **1. TestProject opens cleanly in UE 5.6**
      - Launch `UnrealEditor.exe` with TestProject/TestProject.uproject.
      - Wait for editor fully loaded. No compilation errors in Output Log.
      - If first launch after a git pull, UE will rebuild the plugin — wait.

    - [ ] **2. NyraHost reached Ready state**
      - Open `Tools -> NYRA -> Chat` panel.
      - Banner should briefly show "Setting up NYRA (~30s)" then disappear.
      - Output Log filter `LogNyra` should show:
        - `[NYRA] NyraEditor module starting (Phase 1 skeleton)`
        - `[NYRA] Handshake polling started: <path>`
        - `[NYRA] auth_ok session_id=<uuid>` (from the Python side — forwarded if verbose enough)
      - If banner stays "Setting up NYRA" >60s, re-check that prebuild.ps1 ran
        (the cpython/ + wheels/ + llama-server.exe directories must exist).

    - [ ] **3. Gemma GGUF downloaded + verified**
      - File exists: `TestProject/Saved/NYRA/models/gemma-3-4b-it-qat-q4_0.gguf` (~3.16 GB)
      - If not present: type a chat message; error bubble shows `gemma_not_installed`;
        click the surfaced download button (or run `diagnostics/download-gemma` via a
        test harness) and wait for completion (~5-15 min depending on network).
      - Alternative fast path: if Ollama is installed AND `ollama list` shows
        `gemma3:4b-it-qat`, NyraHost auto-uses Ollama (no GGUF download needed).

    - [ ] **4. Editor window focused during the run**
      - The `editor_tick_max_ms` metric reads `FApp::GetDeltaTime()`; UE throttles
        deltaTime when the editor window is unfocused. For a meaningful measurement,
        keep the editor window focused (but do NOT interact — no mouse/keyboard input
        during the bench; that would skew the tick samples).
      - Close unrelated windows (no other UE editor instances open; no Claude Desktop
        or heavy apps consuming GPU).
      - Optional: maximise the editor for full-window focus guarantee.

    ## Run the Bench

    In the editor, open **Console** (default backtick `) and type:

    ```
    Nyra.Dev.RoundTripBench 100 "Reply with the single word OK only."
    ```

    The prompt is chosen to produce tiny, uniform responses (~1-3 tokens) so
    `total_ms` isn't dominated by generation length — the interesting metric
    is `first_token_ms` (the round-trip + model-warm-up cost).

    ## Capture the Output

    After the command completes, the **Output Log** filtered by `LogNyra`
    shows a block like:

    ```
    [NyraDevTools] RoundTripBench results (N=100):
      first_token  p50=  245.3ms  p95=  487.1ms  p99=  612.8ms
      total        p50= 1843.0ms  p95= 2341.5ms  p99= 2889.2ms
      tokens/sec   p50=  33.20    p95=  29.10    p99=  27.40
      editor_tick_max_ms  p50=  18.3  p95=  22.1  p99=  41.2
      errors=0
      PASS first-token p95 < 500 ms
      PASS editor_tick p95 < 33 ms
      PASS zero errors
    ```

    Copy the entire `[NyraDevTools] RoundTripBench results` block (from the
    opening bracket to the third PASS/FAIL line).

    ## Pass Criteria (RESEARCH §3.6)

    The run is **green** only if all three:

    1. `first-token p95 < 500 ms` → `PASS`
    2. `editor_tick p95 < 33 ms` → `PASS`
    3. `zero errors` → `errors=0` AND `PASS`

    If any is `FAIL`, capture the output anyway — Plan 15 Task 2 will record
    the failure and surface Phase 2 as blocked until a re-run passes.

    ## Dev Machine Spec to Record

    Alongside the bench output, capture:

    ```
    OS:         Windows 11 <build>
    CPU:        <model>, <cores>C/<threads>T
    RAM:        <GB> @ <speed>
    GPU:        <model> (driver <version>)
    UE:        5.6.<patch>
    Gemma path: <TestProject>/Saved/NYRA/models/gemma-3-4b-it-qat-q4_0.gguf (SHA256 <verify>) OR Ollama gemma3:4b-it-qat
    Backend:   <bundled-cuda | bundled-vulkan | bundled-cpu | ollama>
    ```

    Paste both the LogNyra block AND the dev machine spec to the AI
    assistant; Plan 15 Task 2 will finalise ring0-bench-results.md.

    ## Troubleshooting

    - **Command not found in console:** `FAutoConsoleCommand` registered at
      module load. Confirm `LogNyra: [NYRA] Nyra.Dev.RoundTripBench console
      command registered` appeared in the Output Log on editor start. If
      missing, the plugin likely didn't compile — check Output Log for
      compile errors.
    - **All rounds error:** Supervisor not Ready. Check banner state; see
      troubleshooting in `docs/HANDSHAKE.md`.
    - **editor_tick_max_ms p95 > 33 ms:** Phase 1 uses GameThread WS callbacks
      (RESEARCH §3.10 P1.6). If tick regressions are severe, Phase 2 re-plans
      to move WS I/O to a dedicated thread with `AsyncTask(ENamedThreads::GameThread)`
      marshalling. Record the p95 and flag the issue in ring0-bench-results.md.
    - **first_token_ms p95 >> 500 ms:** Almost certainly a cold Gemma load.
      Warm up by running `Nyra.Dev.RoundTripBench 3` first; discard that
      output; then run the real `Nyra.Dev.RoundTripBench 100`.
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "Nyra.Dev.RoundTripBench 100" .planning/phases/01-plugin-shell-three-process-ipc/ring0-run-instructions.md` >= 1
      - `grep -c "first-token p95 < 500 ms" .planning/phases/01-plugin-shell-three-process-ipc/ring0-run-instructions.md` >= 1
      - `grep -c "editor_tick p95 < 33 ms" .planning/phases/01-plugin-shell-three-process-ipc/ring0-run-instructions.md` >= 1
      - `grep -c "zero errors" .planning/phases/01-plugin-shell-three-process-ipc/ring0-run-instructions.md` >= 1
      - `grep -c "Preconditions Checklist" .planning/phases/01-plugin-shell-three-process-ipc/ring0-run-instructions.md` >= 1
      - `grep -c "Troubleshooting" .planning/phases/01-plugin-shell-three-process-ipc/ring0-run-instructions.md` >= 1
    </automated>
  </verify>
  <acceptance_criteria>
    - File ring0-run-instructions.md exists
    - File contains literal text `Nyra.Dev.RoundTripBench 100 "Reply with the single word OK only."`
    - File contains 4 Preconditions Checklist items covering TestProject compile, NyraHost Ready, Gemma present OR Ollama, editor focused
    - File contains Pass Criteria section naming all three: `first-token p95 < 500 ms`, `editor_tick p95 < 33 ms`, `zero errors`
    - File contains Dev Machine Spec section with OS, CPU, RAM, GPU, UE version, Gemma path or Ollama backend
    - File contains Troubleshooting section with at least: command-not-found, all-rounds-error, tick-regression, cold-Gemma-first-run
  </acceptance_criteria>
  <done>Run instructions on disk; user can follow to produce bench output.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
    FNyraDevTools (Plan 14) + end-to-end Phase 1 stack. All Python tests
    green; all UE automation tests green; TestProject builds under UE 5.6.
    Ring 0 bench harness available as console command.
  </what-built>
  <how-to-verify>
    Follow `.planning/phases/01-plugin-shell-three-process-ipc/ring0-run-instructions.md`
    step by step on your Windows 11 + UE 5.6 dev machine. The instructions cover:
    1. Pre-checks (plugin built, NyraHost Ready, Gemma present, window focused)
    2. Warm-up run: `Nyra.Dev.RoundTripBench 3` (discard output)
    3. Real run: `Nyra.Dev.RoundTripBench 100 "Reply with the single word OK only."`
    4. Capture:
       - The full `[NyraDevTools] RoundTripBench results (N=100):` block
         from the Output Log (LogNyra)
       - Dev machine spec (OS / CPU / RAM / GPU / UE patch / Gemma-path-or-Ollama / backend selected)

    Paste BOTH blocks into the chat — Task 3 uses them to finalise
    ring0-bench-results.md.

    If ANY pass criterion fails:
    - Still capture and paste the output + spec.
    - Task 3 will record the failure and mark Phase 2 blocked.
  </how-to-verify>
  <resume-signal>
    Reply with:
    - "passed" + pasted LogNyra block + dev spec, OR
    - "failed" + pasted LogNyra block + dev spec, OR
    - "partial" + describe which criterion failed + pasted output.
  </resume-signal>
</task>

<task type="auto">
  <name>Task 3: Finalise ring0-bench-results.md from pasted bench output</name>
  <files>
    .planning/phases/01-plugin-shell-three-process-ipc/ring0-bench-results.md
  </files>
  <read_first>
    - .planning/phases/01-plugin-shell-three-process-ipc/ring0-run-instructions.md (just created)
    - User's pasted LogNyra block + dev machine spec from the checkpoint
    - .planning/phases/01-plugin-shell-three-process-ipc/01-VALIDATION.md row 1-ring0
    - .planning/ROADMAP.md Phase 1 Success Criterion 3
  </read_first>
  <action>
    Parse the user-provided LogNyra block + dev machine spec from the
    checkpoint. Extract:
    - `first_token` p50, p95, p99
    - `total` p50, p95, p99
    - `tokens/sec` p50, p95, p99
    - `editor_tick_max_ms` p50, p95, p99
    - `errors=N`
    - Three PASS/FAIL verdicts
    - Dev machine spec fields

    Create `.planning/phases/01-plugin-shell-three-process-ipc/ring0-bench-results.md`
    with the following structure (fill in actual values from user input;
    if a field is missing from the user's paste, write `TODO: ask user`):

    ```markdown
    # Ring 0 Stability Gate — Results

    **Run date (UTC):** <YYYY-MM-DD HH:MM from git commit timestamp or "see commit"
    **Plan:** 01-15
    **Validates:** VALIDATION row `1-ring0` + ROADMAP Phase 1 Success Criterion 3

    ## Verdict

    **ring0 Verdict: <PASS | FAIL | PARTIAL>**

    | Criterion                          | Value       | Threshold | Verdict |
    |------------------------------------|-------------|-----------|---------|
    | first_token p95                    | <X> ms      | < 500 ms  | <PASS/FAIL> |
    | editor_tick_max_ms p95             | <Y> ms      | < 33 ms   | <PASS/FAIL> |
    | errors                             | <N>         | 0         | <PASS/FAIL> |

    ## Raw Output

    ```
    <paste user's [NyraDevTools] RoundTripBench results block verbatim>
    ```

    ## Full Percentile Table

    | Metric               | p50         | p95         | p99         |
    |----------------------|-------------|-------------|-------------|
    | first_token_ms       | <X>         | <X>         | <X>         |
    | total_ms             | <X>         | <X>         | <X>         |
    | tokens/sec           | <X>         | <X>         | <X>         |
    | editor_tick_max_ms   | <X>         | <X>         | <X>         |

    ## Dev Machine Spec

    | Field       | Value |
    |-------------|-------|
    | OS          | <pasted from user> |
    | CPU         | <pasted> |
    | RAM         | <pasted> |
    | GPU         | <pasted> |
    | UE version  | 5.6.<pasted> |
    | Gemma path  | <pasted OR "Ollama gemma3:4b-it-qat"> |
    | Backend     | <bundled-cuda | bundled-vulkan | bundled-cpu | ollama> |

    ## Remediation (if FAIL)

    <If any verdict is FAIL, Claude populates this block:>
    <For first_token_ms FAIL>:
      - Likely cause: Gemma cold-start or CPU-only backend.
      - Action: Retry with warm Gemma (run 3× bench first, discard; then 100×).
      - If still FAIL: backend inspection. Run `nvidia-smi` and compare to bench
        log `backend=<value>`. If CPU when a GPU is present, investigate
        `gpu_probe.py` on the Python side.
    <For editor_tick_max_ms FAIL>:
      - Likely cause: GameThread WS dispatch under heavy burst (RESEARCH §3.10 P1.6).
      - Action: Phase 2 plans a dedicated WS I/O thread with AsyncTask marshalling.
        Phase 1 documents the limit in devlog; Phase 2 refactor fixes.
    <For errors > 0>:
      - Likely cause: handshake flake, NyraHost crash mid-bench, or Gemma OOM.
      - Action: inspect `Saved/NYRA/logs/nyrahost-<date>.log` for stack traces.
      - Phase 2 is BLOCKED until a clean re-run (errors=0) is committed.

    **If Verdict = PASS:** Phase 1 architectural gate cleared. Phase 2 may proceed.
    **If Verdict = FAIL:** Phase 2 is BLOCKED. Re-plan the failing component.
    **If Verdict = PARTIAL:** Document which criteria passed, which failed, and
    whether Phase 2 can conditionally proceed (e.g., PASS on first_token but
    FAIL on tick can proceed to Phase 2 with the tick refactor scheduled as
    a Phase 2 Wave 0 item).
    ```

    **Heuristics for autonomous parsing:**
    - If the user pasted a block containing `PASS first-token p95 < 500 ms` + `PASS editor_tick p95 < 33 ms` + `errors=0` + `PASS zero errors` → Verdict = PASS; omit the Remediation section's first three bullets, keep the last three lines.
    - If at least one FAIL present → Verdict = FAIL OR PARTIAL (PARTIAL if some PASS, FAIL if all fail). Populate remediation for each failed criterion.
    - If user reply was `passed` verbatim without a LogNyra block → leave raw-output as `TODO: user did not paste full block` and commit with Verdict = "PASS (reported, raw output not captured)".
    - Always include the full percentile table — even on FAIL, the numbers are diagnostic.
  </action>
  <verify>
    <automated>
      - `test -f .planning/phases/01-plugin-shell-three-process-ipc/ring0-bench-results.md`
      - `grep -c "ring0 Verdict" .planning/phases/01-plugin-shell-three-process-ipc/ring0-bench-results.md` >= 1
      - `grep -c "first_token p95" .planning/phases/01-plugin-shell-three-process-ipc/ring0-bench-results.md` >= 1
      - `grep -c "editor_tick_max_ms p95" .planning/phases/01-plugin-shell-three-process-ipc/ring0-bench-results.md` >= 1
      - `grep -c "Dev Machine Spec" .planning/phases/01-plugin-shell-three-process-ipc/ring0-bench-results.md` >= 1
      - `grep -cE "PASS|FAIL|PARTIAL" .planning/phases/01-plugin-shell-three-process-ipc/ring0-bench-results.md` >= 3
    </automated>
  </verify>
  <acceptance_criteria>
    - ring0-bench-results.md contains literal text `ring0 Verdict`
    - ring0-bench-results.md contains a verdict table with 3 rows: `first_token p95`, `editor_tick_max_ms p95`, `errors`
    - ring0-bench-results.md contains a "Raw Output" block preserving (or clearly noting absence of) the user's pasted LogNyra output
    - ring0-bench-results.md contains a Full Percentile Table with 4 metric rows and p50/p95/p99 columns (values from user paste OR `TODO: ask user`)
    - ring0-bench-results.md contains a Dev Machine Spec table with fields OS/CPU/RAM/GPU/UE/Gemma/Backend
    - ring0-bench-results.md contains a "Remediation (if FAIL)" section — blocks that apply to the recorded failures are kept; blocks for passed criteria may be pruned for clarity
    - ring0-bench-results.md final line explicitly states Phase 2 status (proceed / blocked / conditional) based on verdict
  </acceptance_criteria>
  <done>Ring 0 gate result committed; Phase 1 architectural gate closed (PASS) or Phase 2 explicitly blocked (FAIL).</done>
</task>

</tasks>

<verification>
- ring0-run-instructions.md exists on disk with all required sections
- User runs bench; pastes output + dev spec
- ring0-bench-results.md committed with verdict + raw + percentile table + spec + remediation (if applicable)
- VALIDATION row 1-ring0 can be marked ✅ green (if PASS) or ❌ red (if FAIL) referencing this file
</verification>

<success_criteria>
- Instructions file unambiguous for a dev-machine run
- Results file captures: verdict, raw output, full percentiles, dev spec, remediation/next steps
- Phase 2 unblock / block state is explicit
</success_criteria>

<output>
After completion, create `.planning/phases/01-plugin-shell-three-process-ipc/01-15-SUMMARY.md`
documenting: run date, final verdict (PASS/FAIL/PARTIAL), path to
ring0-bench-results.md, Phase 2 unblock status, and — if PASS — a one-line
note that ROADMAP Phase 1 Success Criterion 3 is satisfied.
</output>
