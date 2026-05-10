---
phase: 8
plan: 08-05
requirement: PARITY-05
verification_type: operator-manual
pending_manual_verification: true
ue_versions: [5.4, 5.5, 5.6, 5.7]
threats_addressed: [T-08-01, T-08-04]
created: 2026-05-10
status: pending
---

# Plan 08-05 (PARITY-05) — Operator Verification Runbook

**Why this is operator-manual:** PARITY-05 is gated on live emitter
rendering inside the UE editor. The Python sidecar's mocked tests
(`tests/test_niagara_authoring.py`) cover schema, parameter validation,
BL-06 readback within `1e-4` tolerance, and T-08-01 graceful degradation
— but they cannot exercise the Niagara shader compile pass that
`sim_target="gpu"` triggers. Per RESEARCH.md §Validation Architecture
this plan is classified `manual-only` for the live render leg.

**Threats covered:**
- **T-08-04** — GPU vs CPU emitter API split. The runbook below
  exercises sprite-CPU, sprite-GPU, and ribbon-CPU on every supported
  UE version.
- **T-08-01** — UE Python API drift across 5.4 → 5.7. Wave-0 symbol
  survey (`wave-0-symbol-survey/symbol-survey-niagara-{ue}.md`) is the
  pre-condition; this runbook is the live-render confirmation.

## Pre-conditions

- [ ] NYRA plugin builds clean for the target UE version
  (`Build/<Version>/Win64/UE5Editor-NyraEditor.dll` present and timestamp
  newer than the Plan 08-05 commits).
- [ ] `NyraEditor.Build.cs` has been batched by the orchestrator with
  `Niagara` + `NiagaraEditor` added to `PrivateDependencyModuleNames`
  (LOCKED-10). Without this, the C++ helper does not link.
- [ ] `nyrahost/mcp_server/__init__.py` has been batched by the
  orchestrator with the three PARITY-05 entries (LOCKED-10).
- [ ] Niagara plugin is enabled (Edit > Plugins > FX > Niagara).
- [ ] Wave-0 symbol survey for this UE version is committed under
  `wave-0-symbol-survey/symbol-survey-niagara-{ue}.md` and shows PASS
  for `unreal.NiagaraSystemFactoryNew`, `unreal.NiagaraSystem`, and
  `unreal.NyraNiagaraHelper`.
- [ ] NYRA chat panel docks visibly (`Window -> NYRA`) and the sidecar
  WS handshake completes (`nyra_ping` returns ok in chat).

## Per-version runbook

For each UE version in {5.4, 5.5, 5.6, 5.7}: open the project in that
editor, then run the seven steps below. Mark PASS / FAIL / SKIPPED per
step in the result table at the bottom.

### Step 1 — Create the system
Send to chat (or invoke via the MCP debug console):
```json
{
  "tool": "nyra_niagara_create_system",
  "params": {"asset_path": "/Game/VFX/NS_TestSparks"}
}
```
- **Expect:** `ok` envelope, `data.asset_path == "/Game/VFX/NS_TestSparks"`.
  Open Content Browser → `/Game/VFX/`; `NS_TestSparks` exists with the
  Niagara System icon.
- **Fail signal:** `not_supported_on_this_ue_version`, OR asset missing
  in Content Browser, OR error envelope.

### Step 2 — Add CPU sprite emitter (T-08-04 leg A)
```json
{
  "tool": "nyra_niagara_add_emitter",
  "params": {
    "system_path":   "/Game/VFX/NS_TestSparks",
    "template_path": "/Niagara/Templates/Sprite/SpriteBurst",
    "sim_target":    "cpu",
    "handle_name":   "SpriteBurstCPU"
  }
}
```
- **Expect:** `ok`, `data.handle_name == "SpriteBurstCPU"`,
  `data.sim_target == "cpu"`. Double-click NS_TestSparks → Niagara editor
  → an emitter named `SpriteBurstCPU` exists with sim-target `CPUSim`.

### Step 3 — Add GPU sprite emitter (T-08-04 leg B — the load-bearing one)
```json
{
  "tool": "nyra_niagara_add_emitter",
  "params": {
    "system_path":   "/Game/VFX/NS_TestSparks",
    "template_path": "/Niagara/Templates/Sprite/SpriteBurst",
    "sim_target":    "gpu",
    "handle_name":   "SpriteBurstGPU"
  }
}
```
- **Expect:** `ok`, emitter `SpriteBurstGPU` exists in the system with
  `GPUComputeSim` as the simulation target. The editor triggers a shader
  compile pass (status bar shows "Compiling Shaders").
- **Fail signal:** `ok` from the tool but the emitter ticks with errors
  in the editor's Niagara compile log. Document the exact error in the
  Notes column. **This is the parity-bar make-or-break leg.**

### Step 4 — Add ribbon emitter
```json
{
  "tool": "nyra_niagara_add_emitter",
  "params": {
    "system_path":   "/Game/VFX/NS_TestSparks",
    "template_path": "/Niagara/Templates/Ribbon/Ribbon",
    "sim_target":    "cpu",
    "handle_name":   "RibbonTrail"
  }
}
```
- **Expect:** Ribbon emitter present, draws as a continuous trail in the
  Niagara editor preview.

### Step 5 — Set scalar module parameter on the CPU emitter
```json
{
  "tool": "nyra_niagara_set_module_parameter",
  "params": {
    "system_path":    "/Game/VFX/NS_TestSparks",
    "emitter_handle": "SpriteBurstCPU",
    "parameter_name": "SpawnRate",
    "value_kind":     "scalar",
    "scalar_value":   50.0
  }
}
```
- **Expect:** `ok`. Open NS_TestSparks → SpriteBurstCPU → Spawn module →
  SpawnRate reads `50.0` (or whatever scalar slot the helper exposes).
  The BL-06 readback proves the value persisted; this step also visually
  confirms the editor reflects the override.

### Step 6 — Drop the system into a level and play
1. Drag `/Game/VFX/NS_TestSparks` into the active level.
2. Press Play (PIE).
- **Expect:** Both sprite emitters render visible particles, ribbon
  emitter draws a trail. No red error banners in the Niagara compile log.
- **Fail signal:** Any emitter is invisible, the ribbon does not draw,
  or PIE produces compile errors.

### Step 7 — Idempotency dry-run
Re-issue Step 1 with the identical asset path. Confirm:
```
data: {"asset_path": "/Game/VFX/NS_TestSparks", "deduped": true}
```
This is a process-local cache hit — no second asset is created. (If the
sidecar restarted between steps the cache is empty; in that case step 7
falls through to the post-condition isinstance-check, which still
returns `ok` without `deduped: true`. Both outcomes are PASS; document
which path was taken in the Notes column.)

## Result table

| UE version | Step 1 (create) | Step 2 (CPU sprite) | Step 3 (GPU sprite) | Step 4 (ribbon) | Step 5 (param + readback) | Step 6 (PIE render) | Step 7 (dedup) | Notes |
|------------|-----------------|---------------------|---------------------|-----------------|---------------------------|---------------------|-----------------|-------|
| 5.4        | TBD             | TBD                 | TBD                 | TBD             | TBD                       | TBD                 | TBD             |       |
| 5.5        | TBD             | TBD                 | TBD                 | TBD             | TBD                       | TBD                 | TBD             |       |
| 5.6        | TBD             | TBD                 | TBD                 | TBD             | TBD                       | TBD                 | TBD             |       |
| 5.7        | TBD             | TBD                 | TBD                 | TBD             | TBD                       | TBD                 | TBD             |       |

## T-08-04 divergence playbook

If `sim_target="gpu"` returns `ok` from the tool but the emitter fails
to compile inside the editor on a specific UE version (the canonical
T-08-04 failure shape):

1. Capture the exact Niagara compile error from the editor's Niagara
   message log and paste it into the Notes column with the UE build
   number (`Help -> About Unreal Editor`).
2. Add `"5.X"` to `KNOWN_NIAGARA_BAD_VERSIONS` in
   `nyrahost/tools/niagara_tools.py` ONLY if the failure is
   reproducible and the operator confirms it's not a project-side
   shader cache issue (`Saved/Shaders/` cleanup).
3. If the GPU path is broken on the version but the CPU path works,
   surface a `sim_target_supported: ["cpu"]` field in the tool's
   startup banner for that version (out of scope for this plan;
   tracked as a follow-up amendment to LOCKED-XX).
4. Phase 8 EXIT-GATE accepts CPU-only on a single shipped version as
   long as at least one of {5.4, 5.5, 5.6, 5.7} passes both legs.

## T-08-01 divergence playbook

If `unreal.NyraNiagaraHelper` is **not** reflected on a UE version
(Wave-0 survey FAIL on the helper line), the plan is in the
`not_supported_on_this_ue_version` graceful-degradation state. The
Python tools surface the err envelope; this VERIFICATION.md result
row marks all live-render steps as SKIPPED with a pointer to the
Wave-0 file. **This is not a failure of Plan 08-05** — per CONTEXT.md
LOCKED-09, EXIT-GATE PARITY-05 only requires UE 5.6 + one of
{5.4, 5.5, 5.7} to pass.

## Operator sign-off

- **Operator name:** _________________________
- **Date verified:** _________________________
- **Result:** PASS / PASS-WITH-NOTES / FAIL
- **`pending_manual_verification`:** flip to `false` only after at least
  UE 5.6 + one of {5.4, 5.5, 5.7} pass Steps 1–6 cleanly with the GPU
  leg (Step 3) confirmed on at least one version.
