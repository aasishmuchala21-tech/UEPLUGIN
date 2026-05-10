---
phase: 8
plan: 08-08
requirement: PARITY-08
verification_type: operator-manual
pending_manual_verification: true
ue_versions: [5.4, 5.5, 5.6, 5.7]
threats_addressed: [T-08-01, A4-capitalisation-drift, A5-builder-reflection-risk]
created: 2026-05-10
status: pending
---

# Plan 08-08 (PARITY-08) — Operator Verification Runbook

> **HONEST: this is gloss-tier scope** (CONTEXT.md SC#8). Most game audio
> lives in Wwise/FMOD outside UE. PARITY-08 ships for marketing-comparison
> parity and is the smallest plan in Phase 8. The operator verification
> below is intentionally tiny — three tools, one round-trip per UE version.

**Why this is operator-manual:** the live audio-graph round-trip (oscillator
node connected to the audio output, asset preview produces audible audio)
requires a running UE editor with the MetaSounds plugin enabled. The
autonomous executor cannot spawn the four UE versions side-by-side from
this dev box — the survey + verification is genuinely operator-bound.

**Threats covered:**
- **T-08-01** UE Python API drift across 5.4 → 5.7: `_resolve_factory` /
  `_resolve_asset_class` / `_resolve_builder_subsystem` probe BOTH
  capitalisations; partial-degradation path returns
  `not_supported_on_this_ue_version` cleanly.
- **A4 capitalisation drift** (RESEARCH.md): explicit dual-spelling probe
  in code + unit tests; documented per-version in this VERIFICATION.md.
- **A5 builder subsystem reflection risk** (RESEARCH.md Q1
  RESOLVED-DEFERRED-TO-WAVE-0): if the builder subsystem isn't reflected
  on a shipped version, only `nyra_metasound_create` is usable on that
  version; the other two return `not_supported_on_this_ue_version`.

## Pre-conditions

- [ ] NYRA plugin builds clean for the target UE version (operator
  verifies with `Build/<Version>/Win64/UE5Editor-NyraEditor.dll`
  present and timestamp newer than this commit).
- [ ] **MetaSounds plugin is enabled** in
  `Edit -> Plugins -> Audio -> MetaSounds`.
- [ ] NYRA chat panel docks visibly (`Window -> NYRA`).
- [ ] Wave 0 symbol survey is complete for this UE version
  (`.planning/phases/08-competitive-parity-aura/wave-0-symbol-survey/symbol-survey-metasound-{version}.md`
  exists and Verdict section is filled in). The verdict tells the
  operator whether the full 3-tool surface or the
  `nyra_metasound_create`-only surface is expected on this version.
- [ ] A target Content folder exists for test assets, e.g.
  `/Game/Audio/PARITY-08/`. Operator deletes any prior
  `MS_TestTone` asset before re-running.

## Per-version runbook

For each UE version in {5.4, 5.5, 5.6, 5.7}: open the project in that
editor, then run the steps below. Mark PASS / FAIL / SKIPPED per version
in the result table.

1. **Probe capitalisation.** In the UE Output Log Python REPL:

   ```python
   import unreal
   print([s for s in dir(unreal) if "etaSound" in s or "etasound" in s][:30])
   ```

   - **Expect:** at least one symbol with `MetaSound` or `Metasound` prefix
     (factory class + source class).
   - **Fail signal:** empty list. Add this version to
     `KNOWN_METASOUND_BAD_VERSIONS` in `metasound_tools.py` and skip steps
     2-5 (mark them N/A in the result row).

2. **Create a test MetaSoundSource.** Send via NYRA chat:

   ```
   nyra_metasound_create("/Game/Audio/PARITY-08/MS_TestTone")
   ```

   - **Expect:** the JSON-RPC response has no `error` and `data.asset_path`
     equals `/Game/Audio/PARITY-08/MS_TestTone` (or the UE-canonicalised
     full path, e.g. `/Game/Audio/PARITY-08/MS_TestTone.MS_TestTone`).
   - **Fail signal:** error envelope OR Content Browser does not show the
     new asset.

3. **Idempotency.** Re-send the exact same `nyra_metasound_create` call.

   - **Expect:** response includes `data.deduped: true` (or `data.deduped: True`).
     No second asset is created in the Content Browser.
   - **Fail signal:** a second asset appears OR `deduped` is missing/false.

4. **Add an oscillator node.** (SKIP if Wave 0 verdict said builder
   subsystem is not reflected on this version.)

   ```
   nyra_metasound_add_node(
     asset_path="/Game/Audio/PARITY-08/MS_TestTone",
     node_class="Oscillator",
     node_name="Osc1",
   )
   ```

   - **Expect:** no `error`; `data.node_name == "Osc1"`. Opening the asset
     in the Metasound editor shows the new Osc1 node.
   - **Fail signal:** error envelope. Record the error string verbatim in
     the Notes column — that text drives the next iteration of the
     `add_node*` reflective dispatch in `metasound_tools.py`.

5. **Connect oscillator output to audio output.** (SKIP if step 4 was
   skipped.) Inspect the asset's existing default output node — its name
   is engine-version-dependent (commonly `Output` or `OnPlay`). Then:

   ```
   nyra_metasound_connect(
     asset_path="/Game/Audio/PARITY-08/MS_TestTone",
     from_node_id="Osc1",
     from_pin="Out",
     to_node_id="<observed output node>",
     to_pin="<observed input pin>",
   )
   ```

   - **Expect:** no `error`. Open the Metasound editor and visually
     confirm the Osc1.Out -> output edge is drawn.
   - **Fail signal:** error envelope OR no edge in the graph after the
     call returns ok. The latter is a BL-06 post-condition gap; record
     and escalate.

6. **(Optional) Audible round-trip.** Open the asset in the Metasound
   editor and click the play / preview button. Confirm an audible tone
   plays. This is the gloss-tier-but-honest "you can hear it" check —
   useful for the marketing screenshot, not load-bearing for PARITY-08
   acceptance (the API mutators succeeding is the parity claim).

## Result table

| UE version | Step 1 (probe) | Step 2 (create) | Step 3 (idempotent) | Step 4 (add_node) | Step 5 (connect) | Step 6 (audible) | Capitalisation winner | Wave 0 verdict | Notes |
|------------|----------------|-----------------|---------------------|-------------------|------------------|------------------|-----------------------|----------------|-------|
| 5.4        | TBD            | TBD             | TBD                 | TBD               | TBD              | TBD              | TBD                   | TBD            |       |
| 5.5        | TBD            | TBD             | TBD                 | TBD               | TBD              | TBD              | TBD                   | TBD            |       |
| 5.6        | TBD            | TBD             | TBD                 | TBD               | TBD              | TBD              | TBD                   | TBD            |       |
| 5.7        | TBD            | TBD             | TBD                 | TBD               | TBD              | TBD              | TBD                   | TBD            |       |

## A4 / A5 divergence playbook

If `_resolve_factory` returns the lower-case `MetasoundFactory` on any
version, OR `_resolve_builder_subsystem` returns None despite step 1
showing some `MetaSound` symbols:

1. Record the per-version capitalisation winner in the result-table
   column above.
2. If builder subsystem is missing on a version, add `"5.X"` to
   `KNOWN_METASOUND_BUILDER_BAD_VERSIONS` in `metasound_tools.py`
   (constant currently exists only as a documented future slot — add it
   when the first version requires it). The two graph-mutation tools
   continue to ship a clean `not_supported_on_this_ue_version` envelope;
   `nyra_metasound_create` continues to work.
3. If `add_node` / `connect` succeed on the call but the asset shows no
   visible change, the BL-06 post-condition is too weak — it currently
   re-loads the asset and confirms isinstance, but does NOT re-fetch
   the graph topology. Document the gap in this VERIFICATION.md and
   open an item in `deferred-items.md` to strengthen the post-condition.

## Honest gloss-tier acknowledgment

Per CONTEXT.md SC#8 + the plan's `## Honest acknowledgments` section:

> THIS PLAN IS GLOSS. PARITY-08 is the lowest-leverage plan in Phase 8.
> It's tier-2 and not on the LOCKED-09 mandatory list. It exists so the
> marketing-comparison table doesn't have a blank cell next to "Audio"
> — that's the entire claim.

Operator: do not over-invest in this verification. Steps 1-3 are the
load-bearing claim ("the create tool works, idempotency works"); steps
4-5 are nice-to-have for the full mutator triplet; step 6 is for
marketing screenshots. If LOCKED-09's "≥2 of {05, 06, 07, 08}" bar is
already satisfied by 05 + 06 + 07, this plan can ship with steps 4-5-6
deferred.

## Operator sign-off

- **Operator name:** _________________________
- **Date verified:** _________________________
- **Result:** PASS / PASS-WITH-NOTES / FAIL
- **`pending_manual_verification`:** flip to `false` only after at least
  UE 5.6 + one of {5.4, 5.5, 5.7} pass steps 1-3 cleanly. Steps 4-5-6 are
  not required to flip the gate per the gloss-tier acknowledgment.
