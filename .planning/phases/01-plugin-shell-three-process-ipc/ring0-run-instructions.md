# Ring 0 Stability Gate — Run Instructions

**Plan:** 01-15 (Phase 1 architectural gate)
**Requirement closed:** ROADMAP Phase 1 Success Criterion 3 + VALIDATION row `1-ring0`
**Who runs this:** Dev-machine operator (Windows 11 + UE 5.6 + Gemma downloaded, or Ollama `gemma3:4b-it-qat`)
**Expected duration:** ~5-10 minutes wall-clock (100 rounds × 2-3 s/round plus warm-up + cold-start)
**Platform:** Windows 11 x64 ONLY. macOS / Linux dev hosts CANNOT run this gate (bundled `llama-server.exe` is Windows-only; UE 5.6 editor + `Nyra.Dev.RoundTripBench` is the only execution surface).

---

## Why this exists

Phase 1 is mostly done at the source level — 15 of 16 plans have shipped with green
SUMMARY.md files. The final architectural gate before Phase 2 unblocks is a live,
empirical measurement: **100 consecutive WebSocket round-trips on UE 5.6 with the
editor remaining responsive during streaming.** That measurement can only happen on
a real Windows dev machine with the Phase-1 plugin fully assembled:

- python-build-standalone CPython 3.12 Win64 extracted under `Plugins/NYRA/Binaries/Win64/NyraHost/cpython/`
- Pre-resolved wheel cache populated at `Plugins/NYRA/Binaries/Win64/NyraHost/wheels/`
- Bundled `llama-server.exe` populated at `Plugins/NYRA/Binaries/Win64/NyraInfer/{cuda,vulkan,cpu}/`
- Gemma 3 4B IT QAT Q4_0 GGUF (3.16 GB) present at `TestProject/Saved/NYRA/models/gemma-3-4b-it-qat-q4_0.gguf`, **OR** Ollama running with `gemma3:4b-it-qat` available

This runbook walks the operator through preparing the environment, warming the
model, running `Nyra.Dev.RoundTripBench 100`, and capturing the output for commit
back to `ring0-bench-results.md`.

---

## Pass criteria (RESEARCH §3.6 / ROADMAP Phase 1 SC#3)

The run is **green** only if all three verdicts are `PASS`:

| Criterion | Threshold | Output Log line |
|-----------|-----------|-----------------|
| First-token latency (p95) | `< 500 ms` | `PASS first-token p95 < 500 ms` |
| Editor tick max (p95) | `< 33 ms` (= 30 FPS floor) | `PASS editor_tick p95 < 33 ms` |
| Round-trip errors | `errors=0` | `PASS zero errors` |

A single `FAIL` on any line → Phase 2 is blocked until a re-run passes.
The `[NyraDevTools]` report also honours a **compliance gate**: if `N < 100` in the
command invocation, the report prepends `[NON-COMPLIANT: requires N>=100 per
ROADMAP Phase 1 SC#3]` AND forces all three verdicts to `FAIL` even if the
thresholds would otherwise pass. This is intentional — short runs are allowed
for dev iteration, but they cannot be committed as the Plan 15 deliverable.

---

## Preconditions Checklist

Run each step in order. **Do not proceed to the bench command until all 4 checkboxes
are confirmed green.**

### [ ] 1. TestProject opens cleanly in UE 5.6

1. Launch `UnrealEditor.exe` via the Epic Games Launcher or a shell invocation:
   ```
   "C:\Program Files\Epic Games\UE_5.6\Engine\Binaries\Win64\UnrealEditor.exe" "<repo-root>\TestProject\TestProject.uproject"
   ```
2. If this is the first launch after a `git pull`, UE will rebuild the NYRA plugin —
   watch the "Compiling" progress and wait for completion.
3. Confirm no compilation errors in the Output Log. Errors here indicate a Plan 10/11/12/13/14
   file did not survive the UE 5.6 UBT/MSVC toolchain — fix before proceeding.
4. Confirm the editor fully loads to the main viewport / Content Browser.

### [ ] 2. NyraHost reached `Ready` state

1. Open the NYRA chat panel: `Tools → NYRA → Chat` (from the level editor's main menu).
2. Watch the banner at the top of the panel:
   - Briefly shows **"Setting up NYRA (~30s)"** (Info banner, blue with spinner) during
     bootstrap (venv creation, wheel install, Python process spawn, WS handshake, auth).
   - Hides itself when supervisor state reaches `Ready`.
3. Open the Output Log and filter on `LogNyra`. You should see this sequence
   (from Plans 03/04/10/13/14):
   ```
   LogNyra: [NYRA] NyraEditor module starting (Phase 1 skeleton)
   LogNyra: [NYRA] Registered NyraChatTab spawner
   LogNyra: [NYRA] Spawning NyraHost: <path-to-cpython>\python.exe -m nyrahost --project-dir <...> --plugin-binaries-dir <...>
   LogNyra: [NYRA] Handshake polling started: %LOCALAPPDATA%/NYRA/handshake-<editor-pid>.json
   LogNyra: [NYRA] Handshake file resolved: port=<NNNN> token=<redacted-16-chars>
   LogNyra: [NYRA] WS connected, sending session/authenticate
   LogNyra: [NYRA] Auth OK (session_id=<uuid>)
   LogNyra: [NYRA] Supervisor state: Ready
   LogNyra: [NYRA] Nyra.Dev.RoundTripBench console command registered
   ```
4. **If the Info banner stays up >60s:** the supervisor is stuck before `Ready`. Most
   common causes:
   - `prebuild.ps1` hasn't been run → `cpython/` or `wheels/` or `NyraInfer/` dirs missing.
     Run from the repo root:
     ```
     powershell -ExecutionPolicy Bypass -File "<repo-root>\TestProject\Plugins\NYRA\prebuild.ps1"
     ```
   - Port collision on 127.0.0.1 — restart the editor to retry with a fresh ephemeral port.
   - Handshake-file DACL rejection under strict corporate policy — check `%LOCALAPPDATA%\NYRA\`
     exists and is writable by the current user.

### [ ] 3. Gemma GGUF downloaded + verified, OR Ollama path active

**Path A — bundled llama-server.exe with GGUF on disk:**

1. Check the file exists:
   ```
   dir "<repo-root>\TestProject\Saved\NYRA\models\gemma-3-4b-it-qat-q4_0.gguf"
   ```
   Expected size: **~3.16 GB** (3,164,574,720 bytes approximately).
2. If missing:
   - In the NYRA chat panel, type any short message and press Ctrl+Enter.
   - Chat will surface an error bubble with remediation `gemma_not_installed` + a `[Download Gemma]` button.
   - Click the button. A progress modal shows byte-level progress (~5-15 minutes on a typical
     residential connection, longer on slow links). Download is resumable — if you kill the
     editor mid-download, re-invoking the download resumes from the byte offset via HTTP Range.
   - After the `verifying` status clears to `done`, the SHA256 has matched the pinned value in
     `ModelPins.h`. The file is now ready.

**Path B — Ollama fast path (faster first-token; no 3.16 GB download required):**

1. Install Ollama for Windows from https://ollama.com/download/windows
2. Pull the Gemma 3 4B IT QAT model:
   ```
   ollama pull gemma3:4b-it-qat
   ```
3. Verify the model is listed:
   ```
   ollama list
   ```
   Should show `gemma3:4b-it-qat` with size ~3.2 GB.
4. Confirm Ollama's API is reachable at `http://127.0.0.1:11434/api/tags` — try:
   ```
   curl http://127.0.0.1:11434/api/tags
   ```
5. On next chat/send, NyraHost's `InferRouter` auto-detects Ollama at startup and uses it
   instead of spawning `llama-server.exe`. You'll see in the Output Log:
   ```
   LogNyra: [NYRA] InferRouter: Ollama detected with gemma3:4b-it-qat; using fast path
   ```
   If you see `llama-server` startup instead, Ollama wasn't reachable — go back to step 4.

### [ ] 4. Editor window focused + system idle during the run

The `editor_tick_max_ms` metric is read from `FApp::GetDeltaTime()` via an FTSTicker sampler
installed for each round. UE throttles `DeltaTime` when the editor window is unfocused, so
the measurement is only meaningful when the editor is the foreground app.

1. Keep the UE editor window **focused** during the full 5-10 minute bench window.
2. Do **not** interact with the editor (no mouse clicks, no keyboard input, no camera
   movement) — that skews the tick samples. The measurement we want is: "would the editor
   be responsive **if** the user were to interact?" — not the tick cost of actual input handling.
3. Close other heavy applications consuming GPU / CPU:
   - Other UE editor instances
   - Claude Desktop
   - Streaming apps (OBS, Discord screen-share)
   - Chrome with many tabs
4. Optional: maximise the editor window so the full viewport is rendering (this gives the
   most realistic measurement of tick cost under real working conditions).

---

## Warm-up run (discard output)

Cold Gemma first-token cost is ~6-12s per RESEARCH §3.5 (lazy spawn + cold model load).
Including this in the 100-round percentile will spuriously inflate p99 and may push p95
over 500 ms even on a healthy dev machine. So:

1. Open the editor **Console** (default backtick key `` ` ``).
2. Type and enter:
   ```
   Nyra.Dev.RoundTripBench 3 "Reply with the single word OK only."
   ```
3. Wait ~20-40 seconds. The Output Log will emit:
   ```
   [NON-COMPLIANT: requires N>=100 per ROADMAP Phase 1 SC#3]

   [NyraDevTools] RoundTripBench results (N=3):
     first_token  p50= XXXX.Xms  p95= XXXX.Xms  p99= XXXX.Xms
     total        p50= XXXX.Xms  p95= XXXX.Xms  p99= XXXX.Xms
     tokens/sec   p50=   XX.XX    p95=   XX.XX    p99=   XX.XX
     editor_tick_max_ms  p50=  XX.XX  p95=  XX.XX  p99=  XX.XX
     errors=0
     FAIL first-token p95 < 500 ms
     FAIL editor_tick p95 < 33 ms
     FAIL zero errors
   ```
   The `FAIL` verdicts on the warm-up are EXPECTED — the compliance gate forces
   `FAIL` when `N < 100`. Ignore them. We just want Gemma loaded into memory.

4. **Discard this output.** Do not copy it anywhere. Its only purpose was to warm
   Gemma so Round 1 of the real bench doesn't pay cold-load cost.

---

## Run the bench (real 100-round)

In the same console, type and enter:

```
Nyra.Dev.RoundTripBench 100 "Reply with the single word OK only."
```

- `100` is the Count argument (clamped to [1, 1000] per PLAN 14 decision; 100 is the
  minimum compliant value per ROADMAP Phase 1 SC#3).
- `"Reply with the single word OK only."` is chosen to produce tiny, uniform responses
  (~1-3 tokens) so `total_ms` isn't dominated by generation length. The interesting
  metric is `first_token_ms` — the round-trip cost + model-generation initiation.
  Prompt is deliberately the same across runs on different dev machines so results
  are comparable.

The bench will run for **~3-5 minutes** (warm Gemma at ~2-3 s/round including
round-trip + generation + tokens). The editor **will freeze visually** during this
window — the bench pumps `FTSTicker::Tick(0.016f) + Sleep(1ms)` on the GameThread
synchronously (intentional design per PLAN 14 decision #1 and RESEARCH §3.6: running
off-thread would invalidate the `editor_tick_max_ms` measurement). Do not click,
do not switch windows — just wait.

You'll see per-round `LogNyra: Verbose` lines in the Output Log (if Verbose filtering
is on):
```
LogNyra: [NyraDevTools] Round 1/100: first=243.1ms total=1844.3ms tick_max=17.22ms frames=18
LogNyra: [NyraDevTools] Round 2/100: first=241.9ms total=1830.5ms tick_max=16.90ms frames=17
...
```

---

## Capture the Output

After all 100 rounds complete, the Output Log (filter: `LogNyra`) will emit the
final report block:

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

*(Example numbers — your actual values will differ based on your GPU, CPU, model
backend, and system load.)*

**Copy the ENTIRE block** from the opening `[NyraDevTools] RoundTripBench results`
line through the third PASS/FAIL line (9 lines total, plus the blank line before it).

---

## Capture the Dev Machine Spec

Alongside the bench output, record the following so `ring0-bench-results.md` can
document reproducibility:

```
OS:              Windows 11 <build number, e.g. 26100.x>
CPU:             <model, e.g. Intel Core i9-13900K>, <cores>C / <threads>T, <base GHz> / <boost GHz>
RAM:             <GB> @ <speed MHz, e.g. 32 GB DDR5-5600>
GPU:             <model, e.g. NVIDIA GeForce RTX 4090 24GB> (driver <version>)
UE:              5.6.<patch>  (check Help → About Unreal Editor)
Gemma backend:   <bundled-cuda | bundled-vulkan | bundled-cpu | ollama>
Gemma path:      <one of:>
                   TestProject\Saved\NYRA\models\gemma-3-4b-it-qat-q4_0.gguf (SHA256 matches ModelPins)
                   OR  Ollama gemma3:4b-it-qat
LogNyra backend line: <from Output Log, e.g. "InferRouter: Ollama detected with gemma3:4b-it-qat; using fast path"
                                           OR "InferRouter: spawning bundled llama-server.exe backend=cuda">
```

Windows build number: `Start → Run → winver` or `cmd → ver`.
CPU model: `Start → System → About`.
GPU + driver: `nvidia-smi` (NVIDIA) or `dxdiag` (generic).
UE patch: Help → About Unreal Editor.

---

## Paste both blocks back

Paste the LogNyra `[NyraDevTools] RoundTripBench results (N=100):` block **AND** the
Dev Machine Spec block into the chat / PR / issue where you're coordinating with the
AI assistant on Plan 15.

Plan 15 Task 3 will then finalise `ring0-bench-results.md` with:
- A 3-row verdict table (first_token p95, editor_tick p95, errors)
- The raw Output Log block preserved verbatim
- A full percentile table (p50/p95/p99 for first_token, total, tokens/sec, editor_tick)
- Your dev machine spec
- A `Phase 2 status` line: **proceed** (PASS), **blocked** (any FAIL), or **conditional** (PARTIAL)

Commit hash + date will be recorded in the results doc frontmatter.

---

## Troubleshooting

### Command not found in console
**Symptom:** Console says `Nyra.Dev.RoundTripBench is not a command.`

**Cause:** The `FAutoConsoleCommand` registration in `FNyraDevTools.cpp` didn't run — the
plugin didn't compile, or the NyraEditor module didn't load.

**Fix:**
1. Confirm `LogNyra: [NYRA] Nyra.Dev.RoundTripBench console command registered` appears
   in the Output Log on editor start. If missing, the plugin didn't compile.
2. Check the Output Log for UBT compile errors. Most likely: a stale UBT cache →
   close editor, delete `TestProject/Binaries/` + `TestProject/Intermediate/`,
   right-click `TestProject.uproject` → Generate Visual Studio Files, then rebuild in VS.
3. If still missing: Confirm the plugin is enabled in `Edit → Plugins → NYRA`.

### All rounds error (errors=100)
**Symptom:** `errors=100` in the final report; every per-round log line says
`Round N/100 errored/timed out (bDone=0 bErrored=0)` or similar.

**Cause:** Supervisor state is not Ready at bench start, or NyraHost died mid-bench.

**Fix:**
1. Check the NYRA panel banner: if it shows Info (bootstrapping) or Error (crashed/unstable),
   wait for Ready or click Restart.
2. Check `TestProject/Saved/NYRA/logs/nyrahost-<YYYY-MM-DD>.log` for Python stack traces.
   Common causes: Gemma GGUF corrupted (SHA mismatch → re-download), llama-server.exe
   crashed on startup (check `NyraInfer/<backend>/llama-server.exe` is not quarantined by
   antivirus), Ollama API returned 500 (check `ollama logs`).
3. Re-run the bench after fix confirmed.

### `editor_tick_max_ms` p95 > 33 ms (PASS on first-token, FAIL on tick)
**Symptom:** `FAIL editor_tick p95 < 33 ms`, but the other two verdicts are PASS.

**Cause:** RESEARCH §3.10 P1.6 — Phase 1 uses GameThread WebSocket callbacks; under
heavy burst the WS frame delivery plus JSON parse work starts eating into the 16.67 ms
frame budget. This is a known Phase 1 limitation with a planned Phase 2 fix.

**Action:**
1. Record the exact `editor_tick_max_ms` p95 + p99 values in the results doc — they
   inform the Phase 2 plan for moving WS I/O to a dedicated thread with
   `AsyncTask(ENamedThreads::GameThread, ...)` marshalling.
2. Plan 15 Task 3 will write Verdict = FAIL (or PARTIAL if first-token PASSes) and
   set Phase 2 status = BLOCKED until the fix ships.
3. If the failure is marginal (e.g., p95 = 34-36 ms), Plan 15 may record Verdict =
   PARTIAL and allow Phase 2 Wave 0 to schedule the WS-thread refactor as its first
   deliverable. This is an operator + planner judgement call — include your own read
   on severity when you paste the report back.

### `first_token_ms` p95 >> 500 ms (e.g. 2000+ ms)
**Symptom:** `FAIL first-token p95 < 500 ms` with values orders of magnitude over threshold.

**Cause:** Almost certainly a cold Gemma load that the warm-up run above didn't fully
cover — or a CPU-only backend where a discrete GPU is present.

**Fix:**
1. Confirm the Output Log line at bench start:
   ```
   LogNyra: [NYRA] InferRouter: <backend>
   ```
   backend should be `cuda` (NVIDIA), `vulkan` (AMD / Intel Arc), or `ollama` — NOT `cpu`
   if you have a discrete GPU. If it's `cpu`:
   - Run `nvidia-smi` (NVIDIA) or `vulkaninfo --summary` (AMD) from cmd — confirm the GPU
     is visible to the system.
   - Check NyraHost's `Saved/NYRA/logs/nyrahost-<date>.log` for `gpu_probe` output. If it
     says "CUDA DLL not found", Plan 06's `prebuild.ps1` likely didn't populate
     `NyraInfer/cuda/` — re-run the prebuild script.
2. Re-run the warm-up bench (`Nyra.Dev.RoundTripBench 3`) TWICE — the first call warms
   Gemma on the selected backend, the second warms the server's internal caches.
3. Then re-run the real `Nyra.Dev.RoundTripBench 100`.
4. If still >500 ms: the measurement is honest and your machine is under the Phase 1
   performance target. Record it in the results doc; Phase 2 may need to revise the
   threshold or add a minimum-dev-machine spec to the Fab listing.

### Editor freezes completely / doesn't respond for > 10 minutes
**Symptom:** No per-round log lines; no progress; editor appears hung.

**Cause:** NyraHost likely crashed and the bench is waiting on each round's 60s timeout
× 100 rounds = 6000s worst case. Or Gemma went into a pathological slow path.

**Fix:**
1. Open Task Manager → check if `python.exe` (running `-m nyrahost`) is alive.
2. Check if `llama-server.exe` (or `ollama.exe serve`) is alive.
3. If either is dead: ABORT the editor (force quit), then investigate logs as above.
4. If both alive but the bench is stuck: attach a debugger or wait out the timeouts.
   Record the partial result — it's informative for Phase 2 debugging even if it's
   a FAIL.

---

## Appendix A: Alternate invocations (dev iteration only)

These are useful during development and do NOT satisfy Plan 15's gate:

```
# Quick sanity check (3 rounds, compliance gate FORCES fail)
Nyra.Dev.RoundTripBench 3 "Reply with the single word OK only."

# Default prompt variant (uses "Reply with OK.")
Nyra.Dev.RoundTripBench 100

# Different prompt — useful for comparing tokens/sec
Nyra.Dev.RoundTripBench 100 "List three short words."

# Stress test (upper clamp; much longer wall time)
Nyra.Dev.RoundTripBench 1000 "Reply with the single word OK only."
```

Only `Nyra.Dev.RoundTripBench 100 "Reply with the single word OK only."` is the
canonical Plan 15 invocation. Any other invocation is dev-convenience and must not
be committed to `ring0-bench-results.md` as the Phase 1 gate measurement.

## Appendix B: What the compliance gate prevents

Short `N < 100` runs get the following header prepended to their report:

```
[NON-COMPLIANT: requires N>=100 per ROADMAP Phase 1 SC#3]
```

AND all three verdict strings are forced from `PASS` to `FAIL`, even if the individual
thresholds would have passed. This is a deliberate quality-bar guard in `FormatReport()`
(see `FNyraDevTools.cpp` commit `7f479b2`).

Rationale: without this gate, an operator could accidentally commit a `N=5` green
result as the Plan 15 deliverable — bypassing the 100-round-stability requirement
from ROADMAP Phase 1 SC#3. The committed bench log MUST show `PASS` on all three
verdicts WITHOUT the NON-COMPLIANT header, which mechanically requires `N=100`.
