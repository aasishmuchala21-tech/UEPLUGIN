---
phase: 8
plan: 08-06
requirement: PARITY-06
verification_type: operator-runbook-pending
pending_manual_verification: true
created: 2026-05-10
status: pending
---

# Plan 08-06 Verification — Performance Profiling Agent (PARITY-06)

**Status:** PLACEHOLDER — operator must run the steps below in a live
UE 5.6 editor session and replace this file with PASS / FAIL results.
Do NOT mark the plan COMPLETE on the strength of unit tests alone; the
unit tests cover (a) `stat unit` regex over a synthesised fixture,
(b) the LOCKED-05 + T-08-05 dual-path on the `PerfExplainHotspotTool`
class via mocked `KbSearchTool`, and (c) `nyra_perf_insights_query`
path validation. They do NOT exercise:

  - Live `stat unit / unitgraph / memory / gpu` capture from a running
    UE editor (requires the WS bridge endpoint `perf/stat-read` to be
    implemented on the UE side; the Python side is wired and forwards
    correctly).
  - `.utrace` ingestion via `UnrealInsights.exe -ExportCSV` — per
    RESEARCH.md A7 this is **scope-narrowed to v1.1** until the
    operator confirms whether `UnrealInsights.exe -?` exposes a
    headless export mode on UE 5.4 / 5.5 / 5.6 / 5.7. The Python
    handler is wired so the v1.1 enablement is a UE-side-only change.
  - The "beats Aura" demo: a real `stat unit` hotspot identified by
    Claude, fed back through `nyra_perf_explain_hotspot`, with the
    KB index actually loaded so the citations field returns Epic docs
    file paths.

## Pre-conditions

- UE 5.6 editor open with NYRA plugin enabled.
- NyraHost sidecar running (auto-starts via plugin lifecycle).
- A live Claude session (`CLAUDE_CODE_OAUTH_TOKEN` set, or
  `claude setup-token` has been run at least once on this machine).
- A test scene with measurable rendering work (the SCENE-01 test scene
  from Phase 6 works fine).
- For Step 5: a `.utrace` capture in
  `<ProjectDir>/Saved/Profiling/Test1.utrace`.
- For Step 6 (LOCKED-05 acceptance bar): the UE5 knowledge index either
  loaded at `%LOCALAPPDATA%/NYRA/knowledge/ue5-index.json` OR a fixture
  index at `<repo>/.nyra-index.json`. Operator runs Step 6 once with
  the file present and once with it removed/renamed.

## Operator runbook

### Step 1 — `nyra_perf_stat_read({stat: "unit"})`

1. Open the NYRA chat panel in UE 5.6 with the SCENE-01 scene loaded.
2. From the chat, ask: "Run nyra_perf_stat_read with stat=unit and
   duration_ms=1000."
3. Confirm the response contains a `raw_text` (or equivalent) field
   with a `stat unit` line block AND a `parsed` dict with at least
   `frame`, `game`, `draw`, `gpu` keys mapping to floats in plausible
   ranges (frame > 0, game/draw/gpu each <= frame).

**PASS criteria:** parsed dict has all four buckets within plausible
bounds.

### Step 2 — `nyra_perf_stat_read({stat: "memory"})`

1. From the chat, ask: "Run nyra_perf_stat_read with stat=memory."
2. Confirm the response contains memory categories (Physical, Virtual,
   GPU memory, etc.) with non-zero MB values.

**PASS criteria:** memory dict is non-empty and values are plausible.

### Step 3 — `nyra_perf_stat_read({stat: "gpu"})`

1. From the chat, ask: "Run nyra_perf_stat_read with stat=gpu."
2. Confirm GPU pass timings (BasePass, Lighting, PostProcessing, etc.)
   are returned with millisecond values.

**PASS criteria:** GPU pass dict has at least 3 named passes with
positive ms values.

### Step 4 — Bad input rejected

1. Ask: "Run nyra_perf_stat_read with stat=garbage."
2. Confirm the response is a JSON-RPC error envelope with
   `code: -32602` and message containing "stat must be one of".
3. Confirm the editor does NOT crash; subsequent valid stat reads
   still succeed.

**PASS criteria:** error envelope returned, editor stable.

### Step 5 — `nyra_perf_insights_query` (deferred to v1.1 per A7)

1. Capture a `.utrace` via UE editor `Trace > Recording`. Save to
   `<ProjectDir>/Saved/Profiling/Test1.utrace`.
2. Ask: "Run nyra_perf_insights_query with trace_path=Saved/Profiling/Test1.utrace."
3. **Expected v1 outcome:** response has `status: "unsupported"` with
   a remediation string pointing the operator at `nyra_perf_stat_read`
   plus `nyra_perf_explain_hotspot` as the working "beats Aura" path.
4. **Expected v1.1 outcome (after `UnrealInsights.exe -ExportCSV` is
   wired):** response has `status: "ok"` plus parsed CSV rows from the
   trace.
5. **Path-validation sub-check (works in v1):** ask the same with a
   non-existent `.utrace` path; confirm `status: "no_trace_loaded"`
   plus a `remediation` field.

**PASS criteria for v1:** the unsupported envelope is returned (never
silent no-op); the path-validation sub-check returns
`status: "no_trace_loaded"`. **Defer the parsed-CSV check to v1.1.**

### Step 6 — `nyra_perf_explain_hotspot` LOCKED-05 + T-08-05 dual-path

This is the headline "beats Aura" verification. Run it twice.

#### 6a — KB index LOADED

1. Confirm `%LOCALAPPDATA%/NYRA/knowledge/ue5-index.json` exists
   (either a real downloaded index or the test fixture symlinked /
   copied to that path).
2. From an earlier `stat unit` read, identify a non-trivial hotspot
   (e.g. "Draw" exceeds 5 ms, or "GPU" exceeds 12 ms).
3. Ask: "Run nyra_perf_explain_hotspot with hotspot_label='Draw'
   and hotspot_metric='5.2 ms'."
4. Confirm response has all SIX LOCKED-05 fields:
   - `hotspot_label: "Draw"`
   - `hotspot_metric: "5.2 ms"`
   - `explanation: <non-empty string referencing the hotspot>`
   - `citations: ["<docs path 1>", "<docs path 2>", ...]` —
     **MUST be non-empty** when the index is loaded.
   - `citations_status: "ok"`
   - `citations_remediation: null`

**PASS criteria for 6a:** `citations` is non-empty AND
`citations_status == "ok"`.

#### 6b — KB index UNLOADED

1. Move (or rename) `%LOCALAPPDATA%/NYRA/knowledge/ue5-index.json`
   so the resolution falls through.
2. Reload NYRA settings (or restart the sidecar — the cached index in
   `KbSearchTool` needs to be invalidated; the `nyra_kb_index_invalidate`
   diagnostic from Plan 03-x covers this).
3. Re-run the same `nyra_perf_explain_hotspot` call.
4. Confirm response STILL has all SIX fields:
   - `hotspot_label: "Draw"`
   - `hotspot_metric: "5.2 ms"`
   - `explanation: <non-empty heuristic-only string>`
   - `citations: []` — **MUST be empty list** (not absent)
   - `citations_status: "no_index_loaded"` — **MUST flip to this**
   - `citations_remediation: <non-null string mentioning Download
     or the LOCALAPPDATA path>`

**PASS criteria for 6b (the LOCKED-05 + T-08-05 acceptance bar):**
   - `citations == []`
   - `citations_status == "no_index_loaded"`
   - `citations_remediation` is non-null and starts with the verbatim
     `KbSearchTool` remediation string ("No UE5 knowledge index found...").
   - **The forbidden combination `citations: []` + `citations_status: "ok"`
     does NOT appear.** This is the silent-failure mode T-08-05 calls
     out by name.

5. Restore the index file. Re-run the call. Confirm 6a state returns
   (citations populated, status flips back to `"ok"`).

## Result template — fill in below after operator run

| Step | Tool                              | Input                                                  | PASS / FAIL | Notes |
|------|-----------------------------------|--------------------------------------------------------|-------------|-------|
| 1    | `nyra_perf_stat_read`             | `{stat: "unit"}`                                       | TBD         |       |
| 2    | `nyra_perf_stat_read`             | `{stat: "memory"}`                                     | TBD         |       |
| 3    | `nyra_perf_stat_read`             | `{stat: "gpu"}`                                        | TBD         |       |
| 4    | `nyra_perf_stat_read`             | `{stat: "garbage"}` (negative)                         | TBD         |       |
| 5a   | `nyra_perf_insights_query`        | valid `.utrace` (expect `unsupported` in v1)           | TBD         |       |
| 5b   | `nyra_perf_insights_query`        | nonexistent path (expect `no_trace_loaded`)            | TBD         |       |
| 6a   | `nyra_perf_explain_hotspot`       | KB index LOADED — citations populated                  | TBD         |       |
| 6b   | `nyra_perf_explain_hotspot`       | KB index UNLOADED — `citations_status` flips           | TBD         |       |

**Operator:** Replace TBDs with results. Set
`pending_manual_verification: false` in the frontmatter and update
`status: passed` or `status: failed`. Commit this file as part of the
EXIT-GATE evidence chain.

## What this verification cannot prove

- Cross-version compatibility (UE 5.4 / 5.5 / 5.7) — that's a separate
  matrix run as part of Phase 8 EXIT-GATE.
- `.utrace` parsing in v1 — deferred to v1.1 per RESEARCH.md A7.
- Index download flow (handled by Phase 3 plans).
- Performance under load (a multi-thousand-line `stat memory` capture);
  the duration cap of 5000 ms is the v1 ceiling.

## Honest acknowledgments preserved from PLAN

- A7 risk acknowledged — `UnrealInsights.exe` may lack headless
  `-ExportCSV`. The "beats Aura" claim still holds in v1 via
  `stat unit` + KB citations only.
- The KB index must be loaded for the headline demo. The unit tests
  cover the unloaded path (T-08-05); the loaded path is validated here
  by Step 6a on the operator's machine.
- Heuristic explanation composer — first-sentence concatenation. Real
  LLM-grade rewriting happens at the chat layer; this tool's job is
  citations + a baseline explanation.
