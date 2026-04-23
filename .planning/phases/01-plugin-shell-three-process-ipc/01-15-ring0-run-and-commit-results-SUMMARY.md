---
phase: 01-plugin-shell-three-process-ipc
plan: 15
subsystem: ring0-run-and-commit-results
tags: [phase-1-architectural-gate, docs-only, operator-runbook, placeholder-deliverable, roadmap-phase-1-sc3, validation-1-ring0, plug-02, plug-03, chat-01, windows-operator-pending]
requirements_progressed: [PLUG-02, PLUG-03, CHAT-01]
pending_manual_verification: true
empirical_gate_status: deferred_to_windows_operator
dependency_graph:
  requires:
    - 01-14-ring0-bench-harness (provides FNyraDevTools + Nyra.Dev.RoundTripBench console command with NON-COMPLIANT gate when N<100; compiled at source level on macOS host, real execution requires Windows + UE 5.6 + Gemma 3 4B)
    - 01-13-first-run-ux-banners-diagnostics (operator sees bootstrap Info banner + download modal before invoking bench per ring0-run-instructions.md precondition #2 + #3)
    - 01-09-gemma-downloader (3.16 GB Gemma GGUF download surface + diagnostics/download-gemma JSON-RPC method; runbook Step 3 Path A depends on this surface)
    - 01-10-cpp-supervisor-ws-jsonrpc (FNyraSupervisor Ready-state gate + handshake + auth + WS round-trip path; runbook precondition #2 reads Output Log lines emitted by this plan's module startup)
  provides:
    - ring0-run-instructions.md (step-by-step Windows operator runbook -- preconditions, warm-up, real 100-round invocation, output capture, dev-spec capture, paste-back instructions, troubleshooting)
    - ring0-bench-results.md (structured placeholder committed during Plan 15; table schema locked, numeric cells PENDING until operator runs the bench)
  affects:
    - .planning/STATE.md (plan counter advanced to 15, completed_plans=16, Phase 01 100% at documentation level with pending_manual_verification:true flag)
    - .planning/ROADMAP.md (Phase 1 row updated to 16/16; footnote documents the Windows-only empirical bench deferral)
tech-stack:
  added:
    - "Placeholder-deliverable pattern: structured markdown file with every numeric cell reading 'PENDING (awaiting first Windows run)' + prominent multi-line PLACEHOLDER banner + frontmatter flags (status: placeholder, pending_manual_verification: true) so readers cannot mistake it for real measurement data"
    - "Operator-runbook pattern: dedicated ring0-run-instructions.md doc with 4-item Preconditions Checklist, warm-up vs real run separation, per-failure-mode Troubleshooting section, Appendix distinguishing canonical Plan-15 invocation from dev-convenience variants"
  patterns:
    - "Platform-gap posture extended to empirical architectural gates, not just toolchain verifications. Plans 01/03/04/05/10/11/12/12b/13/14 deferred UBT/MSVC compile + Automation test runs to Windows CI -- Plan 15 additionally defers the Nyra.Dev.RoundTripBench 100 live measurement itself. Phase 1 is complete at the documentation + source level; the architectural gate's empirical closure is owed by a Windows operator."
    - "Quality-bar guard against premature closure: the SUMMARY explicitly marks plan 15 COMPLETE at documentation level while flagging pending_manual_verification:true + setting empirical_gate_status:deferred_to_windows_operator in frontmatter. ROADMAP.md Phase 1 row adds a footnote; STATE.md Session Continuity records the TODO. No reader can interpret Phase 1 as fully closed without noticing the deferral."
key-files:
  created:
    - .planning/phases/01-plugin-shell-three-process-ipc/ring0-run-instructions.md
    - .planning/phases/01-plugin-shell-three-process-ipc/ring0-bench-results.md
  modified:
    - .planning/STATE.md (plan advance + decisions block + session continuity + Phase 1 completion note + pending_manual_verification flag)
    - .planning/ROADMAP.md (Phase 1 row 16/16 + footnote documenting Windows-only empirical deferral)
decisions:
  - "Partial-completion policy for plan 15 given host is macOS: author ring0-run-instructions.md FULLY (real deliverable the Windows operator needs) + author ring0-bench-results.md as STRUCTURED PLACEHOLDER with schema locked and all numeric cells PENDING. Rationale: this preserves Phase 1 completeness at the documentation level while being honest about the empirical measurement owed by the Windows operator. The alternative (leave Plan 15 incomplete + block Phase 1 advancement until Windows access) would block the entire critical path on a manual operator step that can happen in parallel with Phase 2 planning work."
  - "Prominent multi-line PLACEHOLDER banner at top of ring0-bench-results.md (ASCII box art with ⚠ warning symbols). Rationale: this file WILL be read out of context by future planners + PR reviewers + potentially Epic Fab reviewers. A frontmatter flag alone (status: placeholder) is invisible in most rendering paths. The banner makes it impossible to mistake the templated cells for real measurements at a glance."
  - "ring0-bench-results.md frontmatter includes status: placeholder + pending_manual_verification: true + platform_host_at_authoring: macOS + platform_target: Windows 11. Rationale: frontmatter is machine-readable for tooling (e.g., a future GSD dashboard checking 'are there open placeholder deliverables?') and human-readable at the top of the rendered file. When operator replaces PENDING cells, they flip status to 'measured' + pending_manual_verification to false + add measured_date_utc + measured_commit_hash fields."
  - "Runbook warm-up step (Nyra.Dev.RoundTripBench 3) is explicit + mandatory, not a hidden implementation detail. Rationale: Gemma 3 4B cold-load on llama-server.exe takes ~6-12s per RESEARCH §3.5. Without warm-up, Round 1 of the real 100-round bench bears this cost and spuriously inflates p99 (potentially p95 on fast machines). The runbook instructs the operator to discard warm-up output explicitly so they cannot accidentally report the cold-start number as the gate measurement."
  - "Canonical prompt locked to 'Reply with the single word OK only.' across all dev-machine runs. Rationale: results must be comparable across operators + across dev machines. If each operator chose a different prompt, total_ms and tokens/sec would diverge (different generation lengths) even when first_token_ms is stable. Runbook Appendix A lists other prompts as dev-iteration options that MUST NOT be committed to ring0-bench-results.md as the Phase 1 gate measurement."
  - "Troubleshooting section covers exactly the 5 failure modes the harness surfaces: command-not-found (plugin didn't compile), all-rounds-error (supervisor not Ready or NyraHost crashed), editor_tick p95 > 33 ms (known Phase 1 limit per RESEARCH §3.10 P1.6), first_token p95 >> 500 ms (cold-start or CPU-only backend), editor freezes (async task stuck). Each has action items keyed to specific log lines + specific source files. Rationale: operator may not have UE expertise; runbook must be self-contained for a Phase 2 engineer or a Fab pre-review contractor to follow without asking questions."
  - "ring0-bench-results.md includes a Re-run history table so multiple bench invocations on the same machine (e.g., before and after a fix, warm vs cold variance testing, Phase 2 regression checks) can be appended without rewriting prior rows. Rationale: VALIDATION row 1-ring0 closes on the last PASS row; earlier attempts remain as audit trail. This pattern generalises to Phase 2's CI matrix results (per UE version) and Phase 5's computer-use reliability spike."
metrics:
  duration: ~10min (agent wall time)
  completed: 2026-04-23
  tasks: 3 (Task 1: runbook, Task 2: results placeholder, Task 3: metadata + SUMMARY)
  commits: 3 (docs per task, commit hashes recorded below)
  files_created: 3 (ring0-run-instructions.md + ring0-bench-results.md + this SUMMARY.md)
  files_modified: 2 (STATE.md + ROADMAP.md, in the final metadata commit)
---

# Phase 1 Plan 15: Ring 0 Run and Commit Results Summary

**One-liner:** Authored the Windows-operator runbook (`ring0-run-instructions.md`)
and a structured placeholder (`ring0-bench-results.md`) that closes Phase 1 at
the documentation layer while honestly flagging the empirical
`Nyra.Dev.RoundTripBench 100` measurement as owed by a Windows operator --
cannot be executed from a macOS dev host where the bundled `llama-server.exe`,
UE 5.6 editor, and `Nyra.Dev.*` console surface are all unavailable.

## Context

Plan 14 shipped the bench harness as source (`FNyraDevTools` +
`Nyra.Dev.RoundTripBench` console command with `NON-COMPLIANT` compliance
gate forcing FAIL when N<100). Plan 15 is the architectural gate: run the
harness against the fully-assembled Phase 1 stack on a Windows dev machine
with:
- python-build-standalone CPython 3.12 Win64 extracted
- Wheel cache populated (from Plan 06 `prebuild.ps1`)
- Bundled `llama-server.exe` present (CUDA / Vulkan / CPU backends) OR Ollama running
- Gemma 3 4B IT QAT Q4_0 GGUF (3.16 GB) downloaded and SHA256-verified OR Ollama gemma3:4b-it-qat

None of the above is available on a macOS host. Per PLAN.md frontmatter
(`autonomous: false`), this plan is explicitly a CHECKPOINT plan: Claude
authors the runbook + placeholder; the USER runs the bench and pastes
the results; Claude then replaces the PENDING cells and commits.

Runtime constraints for this execution (set by the caller of the sequential
execute-plan command) instructed a partial-completion path: commit the two
docs (runbook in full + placeholder with schema locked) and the metadata
commit marking Plan 15 COMPLETE at the documentation layer, while
`pending_manual_verification: true` flags the outstanding empirical step.

## What Shipped

### Task 1 -- `ring0-run-instructions.md` (commit `d3731f2`)

Operator runbook for the Windows dev machine. Sections:

- **Why this exists** -- explains the platform gap + what Plan 14 shipped vs
  what Plan 15 still needs.
- **Pass criteria** -- 3-row threshold table (first_token p95 < 500 ms,
  editor_tick p95 < 33 ms, errors == 0) sourced from ROADMAP Phase 1 SC#3 /
  RESEARCH §3.6.
- **Preconditions Checklist** -- 4 checkbox steps that MUST be green before
  running the bench:
  1. TestProject opens cleanly in UE 5.6 (plugin compiles).
  2. NyraHost reached `Ready` state (banner hides, `LogNyra` supervisor log
     lines confirm handshake + auth + Ready transition).
  3. Gemma 3.16 GB GGUF downloaded + SHA256-verified, OR Ollama
     `gemma3:4b-it-qat` installed + reachable at 127.0.0.1:11434.
  4. Editor window focused + system idle (editor throttles `FApp::GetDeltaTime()`
     when unfocused; measurement would be meaningless).
- **Warm-up run** -- `Nyra.Dev.RoundTripBench 3` (compliance-FAIL by design,
  output discarded) warms Gemma + llama-server caches before the real
  measurement so Round 1 doesn't pay cold-start cost.
- **Run the bench** -- canonical invocation
  `Nyra.Dev.RoundTripBench 100 "Reply with the single word OK only."` with
  an explanation of the prompt choice (uniform short responses let
  first_token_ms dominate, not generation length).
- **Capture the Output** -- exact block to copy from Output Log (LogNyra
  filter, from `[NyraDevTools] RoundTripBench results (N=100):` header
  through the third `PASS`/`FAIL` verdict line).
- **Capture the Dev Machine Spec** -- OS / CPU / RAM / GPU / UE version /
  Gemma backend / Gemma source / InferRouter log line. Commands listed
  for each (winver, dxdiag, nvidia-smi, Help→About).
- **Paste both blocks back** -- clear hand-off instructions for Plan 15 Task 3.
- **Troubleshooting** -- 5 named failure modes with specific log-line triggers
  and action items:
  - command-not-found (`FAutoConsoleCommand` didn't register -- plugin didn't compile)
  - all rounds error (supervisor not Ready -- check NyraHost crash log)
  - editor_tick p95 FAIL (known Phase 1 limit from RESEARCH §3.10 P1.6; Phase 2 fix)
  - first_token p95 >> 500 ms (cold-start or CPU-only backend despite GPU present)
  - editor freezes (async task stuck; ABORT + investigate)
- **Appendix A** -- alternate dev-iteration invocations (`Nyra.Dev.RoundTripBench 3`,
  `1000`, different prompts) marked clearly as NOT valid Plan 15 deliverables.
- **Appendix B** -- explains the NON-COMPLIANT compliance gate and why an
  operator cannot accidentally commit an N<100 run.

Document is self-contained: a Phase 2 engineer or a Fab pre-review contractor
should be able to follow it without asking questions.

**Grep literals verified:**
```
Nyra.Dev.RoundTripBench 100           -> 7 (>=1)
first-token p95 < 500 ms              -> 4 (>=1)
editor_tick p95 < 33 ms               -> 4 (>=1)
zero errors                            -> 3 (>=1)
Preconditions Checklist                -> 1 (>=1)
Troubleshooting                        -> 1 (>=1)
Reply with the single word OK only     -> 6 (canonical prompt locked)
```

### Task 2 -- `ring0-bench-results.md` (placeholder, commit `6a50059`)

Structured markdown file with locked schema + all numeric cells reading
`PENDING (awaiting first Windows run)`.

Top of file carries a prominent ASCII-banner box (multi-line ⚠ PLACEHOLDER
warning) so no reader can confuse the templated cells with real measurement
data. Frontmatter additionally flags:
```yaml
status: placeholder
pending_manual_verification: true
platform_host_at_authoring: macOS Darwin (cannot run UE 5.6 + llama-server.exe)
platform_target: Windows 11 x64 + UE 5.6
```

Locked sections:
- **Verdict** -- 3-row table (first_token p95, editor_tick_max_ms p95, errors)
  with threshold column + PENDING verdicts. Phase 2 gate status is
  PENDING with the PASS/FAIL/PARTIAL branching logic explicitly documented.
- **Raw Output** -- fenced block with `PENDING (awaiting first Windows run)`
  + an "Expected shape" subsection showing the RESEARCH §3.6 output format
  + the NON-COMPLIANT variant for N<100.
- **Full Percentile Table** -- 4-row metric table (first_token_ms, total_ms,
  tokens_per_sec, editor_tick_max_ms) × 3 percentile columns (p50/p95/p99)
  + unit column + metric-definition notes. Summary counters (N, errors,
  frames_per_round) below.
- **Dev Machine Spec** -- 11-row table (OS, Windows build, CPU, cores/threads,
  RAM, GPU, GPU driver, UE version, Gemma backend, Gemma source, InferRouter log)
  with expected values listed for the backend + source fields.
- **Remediation** -- per-failure-mode templates:
  - first_token FAIL: cold-start, CPU-only backend, low-spec machine
  - editor_tick FAIL: RESEARCH §3.10 P1.6 Phase 2 refactor + marginal-vs-severe
    branching for PARTIAL vs BLOCKED verdicts
  - errors FAIL: handshake flake, NyraHost crash, Ollama service died; always BLOCKS Phase 2
- **Re-run history** -- 1-row table with all PENDING cells; operator appends
  rows for multiple bench attempts.
- **Links** -- cross-references to runbook, Plan 14 source file + commit,
  Plan 14 SUMMARY, RESEARCH §3.6, VALIDATION row 1-ring0, ROADMAP SC#3.
- **Integrity notes** -- 8-step checklist for the operator populating real
  values (flip frontmatter flags, add measured-* fields, remove banner,
  remove "Expected shape" template, update commit message, update STATE.md
  + ROADMAP.md).

**Grep literals verified:**
```
ring0 Verdict                          -> 2 (>=1)
first_token p95                         -> 2 (>=1)
editor_tick_max_ms p95                  -> 1 (>=1)
Dev Machine Spec                        -> 1 (>=1)
PASS|FAIL|PARTIAL|PENDING               -> 51 (>=3)
PLACEHOLDER                             -> 3 (banner visible)
< 500 ms                                -> 4 (threshold cited)
< 33 ms                                 -> 4 (threshold cited)
```

### Task 3 -- Metadata (this SUMMARY.md + STATE.md + ROADMAP.md updates, metadata commit follows)

This summary plus STATE.md plan-advance / Phase 1 completion note / decisions
block + ROADMAP.md Phase 1 row update with footnote are committed in a single
final docs commit (per execute-plan.md final_commit contract).

## Partial-completion policy (explicit)

This plan is marked **COMPLETE at the documentation layer** with
`pending_manual_verification: true` flagged in three places:

1. `ring0-bench-results.md` frontmatter (`status: placeholder`, explicit
   PLACEHOLDER banner).
2. This SUMMARY.md frontmatter (`pending_manual_verification: true`,
   `empirical_gate_status: deferred_to_windows_operator`).
3. STATE.md Plan 15 decisions block (Task 3 writes explicit
   "Phase 1 COMPLETE at source level; architectural Gate 3 empirical
   verification pending Windows bench run" session handoff note).

ROADMAP.md Phase 1 row advances to 16/16 with a footnote citing
`ring0-run-instructions.md` as the Windows-operator runbook and
`ring0-bench-results.md` as the placeholder that gets populated when
the empirical gate closes.

This is the ONLY way Phase 1 can progress on a macOS host. Alternatives
rejected:
- **Leave Plan 15 at 0/16 tasks until Windows access:** blocks entire
  critical path on a manual operator step that can happen in parallel
  with Phase 2 planning work. Wrong trade for a solo-builder timeline.
- **Fake numeric data to make verdicts green:** violates PROJECT.md Quality
  Bar + constitutes fraud against the architectural gate it purports to
  close. Never acceptable.
- **Run the bench under a mock harness with synthetic data:** Plan 14 source
  is already tested at the compliance-gate level (NON-COMPLIANT
  header + forced-FAIL when N<100). What remains is REAL first_token /
  editor_tick measurement under real Gemma load -- that is by definition
  not mockable.

The partial-completion path chosen preserves honesty (placeholder is
obviously a placeholder) + forward progress (Plan 15 counter advances,
ROADMAP reflects Phase 1 close at documentation level) + clear ownership
(Windows operator has a self-contained runbook).

## Metric definitions (referenced from runbook + results doc)

| Metric | Captured how | Unit | Gate? | Threshold |
|--------|--------------|------|-------|-----------|
| `first_token_ms` | `(FPlatformTime::Seconds() - T0Seconds) * 1000.0` on first chat/stream frame with non-empty delta | ms | YES | p95 < 500 |
| `editor_tick_max_ms` | `max(FApp::GetDeltaTime() * 1000)` observed by FTSTicker sampler during streaming | ms | YES | p95 < 33 |
| `errors` | Round-level: timeout OR chat/stream{done:true, error:{...}} OR supervisor not-Ready | count | YES | 0 |
| `total_ms` | Same expression as first_token_ms but on chat/stream{done:true} frame | ms | no | (informational) |
| `tokens_per_sec` | `completion_tokens / ((total_ms - first_token_ms) / 1000.0)` | tokens/s | no | (informational) |

All definitions are verbatim from `FNyraDevTools.cpp` (Plan 14 commit `7f479b2`)
and Plan 14 SUMMARY "Metric definitions (RESEARCH §3.6 fidelity)" table.

## Commits

| # | Task | Type | Commit | Message |
|---|------|------|--------|---------|
| 1 | Task 1 (runbook) | docs | `d3731f2` | docs(01-15): add ring0-run-instructions runbook for Windows operator |
| 2 | Task 2 (placeholder) | docs | `6a50059` | docs(01-15): add ring0-bench-results placeholder with PENDING cells |
| 3 | Task 3 (metadata) | docs | (final commit adds this SUMMARY.md + STATE.md + ROADMAP.md) | docs(01-15): complete ring0-run-and-commit-results plan |

## Deviations from Plan

### [Rule 2 - Missing critical functionality] Extended PLACEHOLDER banner beyond PLAN.md sketch

- **Found during:** Task 2 authoring.
- **Context:** PLAN.md's `<action>` block for Task 3 (which in our partial-completion
  path is fused with Task 2 since the user cannot paste real results) specified the
  file structure and sections. But the PLAN.md block assumed the user would paste
  real data immediately after the checkpoint; it did not specify what the file
  should look like when authored with ALL PENDING cells on a macOS host with no
  operator bench paste forthcoming.
- **Fix:** Added a prominent multi-line ASCII-banner box at the top of
  `ring0-bench-results.md` with ⚠ warning symbols + 15-line explanation of what
  PENDING means + explicit instructions for the future operator on how to
  populate the file. Also added `status: placeholder` +
  `pending_manual_verification: true` + `platform_host_at_authoring: macOS Darwin`
  fields to the frontmatter, plus an "Integrity notes" section at the bottom of
  the file listing the 8-step checklist for replacing PENDING cells with
  real values.
- **Rationale:** Without these additions a future reader (Phase 2 planner, Fab
  reviewer, external contributor) could glance at the file's table structure and
  mistake the templated cells for measured data, or miss that Phase 1's
  architectural gate is actually still owed. The Quality Bar (PROJECT.md +
  ROADMAP.md) forbids hidden caveats; banners + frontmatter flags are the
  right mitigation.
- **Files modified:** `.planning/phases/01-plugin-shell-three-process-ipc/ring0-bench-results.md`
- **Commit:** Included in Task 2 (`6a50059`).

### [Rule 2 - Missing critical functionality] Added Appendix A + Appendix B to runbook

- **Found during:** Task 1 authoring.
- **Context:** PLAN.md specified Preconditions Checklist, Run, Capture, Pass
  Criteria, Dev Machine Spec, Troubleshooting sections. It did NOT specify
  guidance for distinguishing the canonical Plan-15 invocation from
  dev-convenience variants (N=3 for smoke, N=1000 for stress, different
  prompts), nor did it specify an explanation of the NON-COMPLIANT compliance
  gate for operators unfamiliar with Plan 14's internal design.
- **Fix:** Added `Appendix A: Alternate invocations (dev iteration only)` listing
  the other valid harness calls with an explicit note that NONE of them is
  committable as the Plan 15 deliverable, and `Appendix B: What the compliance
  gate prevents` explaining the `[NON-COMPLIANT: requires N>=100 per ROADMAP
  Phase 1 SC#3]` header + forced-FAIL behaviour from `FormatReport()`.
- **Rationale:** An operator who isn't an NYRA core dev could easily type
  `Nyra.Dev.RoundTripBench 3` (because 100 takes 5 minutes and they're
  iterating) and copy-paste the output without noticing the NON-COMPLIANT
  header. Appendix A preempts that class of error; Appendix B explains WHY
  the gate exists so the operator respects it rather than working around it.
- **Files modified:** `.planning/phases/01-plugin-shell-three-process-ipc/ring0-run-instructions.md`
- **Commit:** Included in Task 1 (`d3731f2`).

### [Deferral - Platform gap, host:macOS target:Windows] Task 3 paste-back + Verdict finalisation deferred

- **Found during:** Plan start (runtime constraints explicitly note this).
- **Context:** PLAN.md Task 3 specifies parsing a user-pasted LogNyra block +
  dev machine spec, extracting p50/p95/p99 from each metric, deciding
  PASS/FAIL/PARTIAL, populating the Remediation section accordingly, and
  committing the finalised `ring0-bench-results.md`. The ONLY way this can
  happen is after the user has actually run `Nyra.Dev.RoundTripBench 100`
  on their Windows dev machine. The current macOS host cannot run that
  command (no UE 5.6, no bundled llama-server.exe, no Gemma GGUF, no
  editor console).
- **Fix:** Bifurcated the original PLAN.md Task 3 into:
  1. **This plan's Task 3 (docs-layer close):** author SUMMARY.md + update
     STATE.md + ROADMAP.md + final metadata commit. Mark Plan 15 COMPLETE
     at the documentation layer with `pending_manual_verification: true`.
  2. **Operator's manual Task 3 (empirical close, deferred):** Windows
     operator follows `ring0-run-instructions.md`, runs the bench, pastes
     output. A future Claude session then edits `ring0-bench-results.md`
     in-place, flips the frontmatter flags, updates STATE.md to clear
     `pending_manual_verification`, updates ROADMAP.md to remove the footnote,
     commits with message `feat(01-15): record ring0 bench results from
     Windows dev machine`.
- **Rationale:** Executing the PLAN.md Task 3 as literally written is impossible
  on this host. The alternatives (see "Partial-completion policy" section above)
  all have worse trade-offs than the bifurcation chosen.
- **Files affected:** N/A (this is a structural deviation, not a file change).
- **Tracking:** STATE.md Plan 15 decisions block carries the
  `pending_manual_verification: true` flag + Session Continuity TODO. ROADMAP.md
  Phase 1 row carries a footnote. `ring0-bench-results.md` frontmatter +
  PLACEHOLDER banner + "Integrity notes" section give the future operator a
  complete checklist. This deferral is maximally visible, not hidden.

## Deferred Issues

None introduced by Plan 15 (all platform-gap deferrals are properly documented above).

## Known Stubs

1. **`ring0-bench-results.md` numeric cells all read `PENDING (awaiting first Windows run)`.**
   This is the intentional deliverable state for Plan 15 on a macOS host per
   the partial-completion policy. Resolution: Windows operator follows
   `ring0-run-instructions.md`, populates the cells, commits.
   - **Affected file:** `.planning/phases/01-plugin-shell-three-process-ipc/ring0-bench-results.md`
   - **Affected cells:** all rows in the Verdict table, all cells in the Full
     Percentile Table, all cells in the Dev Machine Spec table, the Raw Output
     fenced block, Re-run history row 1.
   - **Reason intentional:** empirical measurement impossible on macOS host;
     Phase 1 advancement at documentation layer requires a placeholder.
   - **Which plan will resolve:** not a new plan -- a manual operator edit +
     commit `feat(01-15): record ring0 bench results from Windows dev machine`
     that flips the frontmatter flags and replaces PENDING cells with real
     values. This does not require a new PLAN.md -- it's a continuation of
     Plan 15's manual-verification tail.

## Threat Flags

No new network-exposed surface in Plan 15:
- Both files are markdown documentation + placeholder data only. No code changes.
- No new JSON-RPC methods, no new file-system paths, no new subprocess invocations.
- The runbook references existing Phase 1 surfaces (`Nyra.Dev.RoundTripBench`
  console command from Plan 14, `diagnostics/download-gemma` from Plan 09,
  WS + handshake from Plan 10) but does not introduce any new ones.
- Plan 14 SUMMARY already documented the Plan 14 threat surface
  (editor-local console command, loopback WS, Gemma-local generation -- all
  three-process-perimeter confined).

No `threat_flag:` markers emitted.

## Self-Check: PASSED

All claimed files exist on disk:

```
.planning/phases/01-plugin-shell-three-process-ipc/ring0-run-instructions.md           FOUND (new, 419 lines)
.planning/phases/01-plugin-shell-three-process-ipc/ring0-bench-results.md              FOUND (new, 273 lines, PLACEHOLDER)
.planning/phases/01-plugin-shell-three-process-ipc/01-15-ring0-run-and-commit-results-SUMMARY.md  FOUND (this file)
```

All claimed commits present in `git log --oneline`:

```
d3731f2 FOUND -- Task 1 (ring0-run-instructions.md)
6a50059 FOUND -- Task 2 (ring0-bench-results.md placeholder)
```

All Task 1 + Task 2 grep acceptance literals pass at source level (see tables
above). Prominent PLACEHOLDER banner verified in ring0-bench-results.md at line
count >= 3 grep matches for "PLACEHOLDER" literal.

`git diff --diff-filter=D --name-only HEAD~2 HEAD` expected to be empty (no
unintended deletions, only additions; STATE/ROADMAP modifications land in the
final metadata commit).

## Phase 1 completion posture

Phase 1 (Plugin Shell + Three-Process IPC) is now **16/16 plans complete at
the documentation + source layer**:

| Plan | Name                             | Status                |
|------|----------------------------------|-----------------------|
| 01   | cpp-automation-scaffold          | COMPLETE              |
| 02   | python-pytest-scaffold           | COMPLETE              |
| 03   | uplugin-two-module-scaffold      | COMPLETE              |
| 04   | nomad-tab-placeholder-panel      | COMPLETE              |
| 05   | specs-handshake-jsonrpc-pins     | COMPLETE              |
| 06   | nyrahost-core-ws-auth-handshake  | COMPLETE              |
| 07   | nyrahost-storage-attachments     | COMPLETE              |
| 08   | nyrahost-infer-spawn-ollama-sse  | COMPLETE              |
| 09   | gemma-downloader                 | COMPLETE              |
| 10   | cpp-supervisor-ws-jsonrpc        | COMPLETE              |
| 11   | cpp-markdown-parser              | COMPLETE              |
| 12   | chat-panel-streaming-integration | COMPLETE              |
| 12b  | history-drawer                   | COMPLETE              |
| 13   | first-run-ux-banners-diagnostics | COMPLETE              |
| 14   | ring0-bench-harness              | COMPLETE              |
| 15   | ring0-run-and-commit-results     | COMPLETE (docs layer; pending_manual_verification=true) |

Phase 1 architectural success criteria status:
- **SC#1** (out-of-process crash isolation): source-level COMPLETE (Plan 10
  FNyraSupervisor spawns NyraHost; Plan 14's bench will exercise this on Windows).
- **SC#2** (chat panel foundation depth): source-level COMPLETE (Plans 04/11/12/12b/13).
- **SC#3** (100-round stability gate): source-level COMPLETE (Plan 14 harness);
  empirical measurement PENDING Windows operator run of Plan 15's runbook.
- **SC#4** (NyraInfer spawn + OpenAI-compatible surface): source-level COMPLETE
  (Plan 08 handlers + router + llama-server spawn); empirical end-to-end
  exercised by SC#3's bench run.
- **SC#5** (two-module uplugin layout, Fab-ready): source-level COMPLETE
  (Plan 03 scaffold).

**Phase 2 gate:** Phase 2 (Subscription Bridge + Four-Version CI Matrix) may
proceed with PLANNING work in parallel; actual EXECUTION of Phase 2 code should
wait on two things:
1. Phase 0 legal clearance (runs in parallel; founder decision locked).
2. Empirical closure of SC#3 via the Windows operator's bench run +
   `ring0-bench-results.md` update.

If SC#3 returns PASS on first real run: no further Phase 1 rework needed.
If SC#3 returns FAIL: a remediation plan (e.g., "Plan 01-16 move WS I/O to
dedicated thread") may be needed before Phase 2 can commit. That contingency
is explicitly documented in `ring0-bench-results.md` Remediation section +
Phase 2 status branching.
