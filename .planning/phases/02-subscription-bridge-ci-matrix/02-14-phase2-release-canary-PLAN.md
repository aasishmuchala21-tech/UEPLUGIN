---
phase: 02-subscription-bridge-ci-matrix
plan: 14
slug: phase2-release-canary
type: execute
wave: 3
depends_on: [01, 05, 06, 08, 09, 10, 11, 12]
autonomous: false
tdd: false
requirements: [PLUG-04, SUBS-01, SUBS-02, SUBS-03, CHAT-02, CHAT-03, CHAT-04, ACT-06, ACT-07]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Dev/FNyraDevTools.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Dev/FNyraDevTools.h
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_claude_live_turn.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/fixtures/stream-json-cli-v2.1.118.ndjson
  - .planning/phases/02-subscription-bridge-ci-matrix/02-VERIFICATION.md
research_refs: [§10.1, §11]
context_refs: [D-26, D-27]
phase0_clearance_required: true
must_haves:
  truths:
    - "FNyraDevTools gains a new static method RunSubscriptionBridgeCanary(N=10) — spawns N Claude turns with a canned prompt 'Reply with the single word OK only.' via chat/send backend=claude, measures turn-complete latency + tool-call count + error count"
    - "Nyra.Dev.SubscriptionBridgeCanary console command registered; clamp N=1..50 (shorter than Phase 1 bench since each Claude turn consumes real subscription quota)"
    - "Pass thresholds: p95 turn-complete < 8000ms (Claude is slower than Gemma; 8s is generous), 0 parse errors on stream-json NDJSON, 0 unexpected exceptions, at least one successful plan/preview + plan/decision round-trip if the prompt induces a tool call, diagnostics/backend-state notification observed on every turn"
    - "Canary produces a structured report at Saved/NYRA/canary-subscription-bridge-<ts>.log with per-turn metrics + pass/fail verdict + NYRA Phase 2 SC coverage table"
    - "test_claude_live_turn.py adds a -m live guarded pytest that exercises the Python-side claude_adapter end-to-end against a REAL claude CLI invocation when CLAUDE_CODE_OAUTH_TOKEN is set AND Phase 0 legal clearance has completed (env-guard pattern mirrors Phase 1's approach to Windows-only tests)"
    - "Wave 0-captured NDJSON fixture from the installed Claude CLI version at phase-execution time committed as stream-json-cli-v2.1.X.ndjson for schema-drift regression baseline (RESEARCH §10.1)"
    - ".planning/phases/02-subscription-bridge-ci-matrix/02-VERIFICATION.md — the phase-exit verification doc; follows Phase 1's VERIFICATION.md shape; lists PASS/FAIL per ROADMAP Phase 2 Success Criterion #1 through #6 + per-requirement REQ-ID satisfaction"
  artifacts:
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/Dev/FNyraDevTools.h
      provides: "Extended Nyra.Dev.* console commands (Phase 1 Nyra.Dev.RoundTripBench preserved verbatim; Phase 2 adds SubscriptionBridgeCanary)"
    - path: TestProject/Plugins/NYRA/Source/NyraHost/tests/test_claude_live_turn.py
      provides: "pytest -m live integration test for Claude CLI driver"
    - path: .planning/phases/02-subscription-bridge-ci-matrix/02-VERIFICATION.md
      provides: "Phase 2 exit verification — PASS/FAIL per SC + REQ"
  key_links:
    - from: Nyra.Dev.SubscriptionBridgeCanary (new console cmd)
      to: FNyraSupervisor.OnChatSendForwarded (Plan 02-08)
      via: "GameThread console Exec → synchronous bench pump using FTSTicker::Tick like Phase 1 Plan 14"
      pattern: "FNyraSupervisor.*chat/send"
    - from: 02-VERIFICATION.md pass table
      to: ROADMAP Phase 2 SC #1..#6 + REQ-IDs PLUG-04, SUBS-01/02/03, CHAT-02/03/04, ACT-06/07
      via: "One row per SC with verifier evidence (test file path, bench report path, CI run URL)"
      pattern: "SC#[1-6]|REQ-ID"
---

<objective>
End-of-phase release canary + verification artifact. Proves every Phase 2 thread lands correctly:
- Four-version matrix green with signed artifacts (Plan 02-01 + 02-07 + 02-13)
- Claude subprocess driving end-to-end with at least one plan-preview round-trip (Plans 02-05 + 02-06 + 02-09)
- Router state machine surfaces correct diagnostics/backend-state on every turn (Plan 02-06 + 02-12)
- Super-transaction wraps the turn; Ctrl+Z rolls back (Plan 02-08)
- Console + log tools operational (Plans 02-10 + 02-11)
- Status pill reflects real backend state (Plan 02-12)

Per CONTEXT.md:
- D-26: EXECUTE-time precondition — Phase 0 legal clearance must be on file before real Claude turns run (CI may use a mocked claude binary for schema-drift fixture capture, but live canary gates on clearance)
- D-27: Phase 1 Plan 15 empirical bench gate (SC#3) pass verdict committed before this plan executes

This plan is **phase0_clearance_required: true** and **autonomous: false** because (a) the live canary consumes the founder's own Claude subscription quota and should be manually triggered with an explicit consent, (b) the VERIFICATION.md authoring needs the operator to paste CI run URLs.

**Not TDD** — this is verification infrastructure + a manual-operator gate. The tests it adds are themselves live-guarded.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/02-subscription-bridge-ci-matrix/02-CONTEXT.md
@.planning/phases/02-subscription-bridge-ci-matrix/02-RESEARCH.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-14-ring0-bench-harness-SUMMARY.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-VERIFICATION.md

<interfaces>
<!-- FNyraDevTools extension (module-superset on Phase 1 Plan 14 — D-24): -->
```cpp
// Phase 1 preserved: Nyra.Dev.RoundTripBench N
// Phase 2 adds:
//   Nyra.Dev.SubscriptionBridgeCanary N [prompt]
//   Default N=10, prompt="Reply with the single word OK only."
//   Output:
//     [PER TURN] turn 1: first_token=1234ms total=3456ms tool_calls=0 errors=0 backend_state=ready
//     ...
//     [SUMMARY] turns=10 p50_total=3100ms p95_total=5200ms errors=0 plan_previews=0 state_transitions=11
//     [VERDICT] PASS / FAIL (reason if FAIL)
//   Results file: Saved/NYRA/canary-subscription-bridge-<ISO-ts>.log (JSON lines + summary block)
```

<!-- 02-VERIFICATION.md shape (mirrors 01-VERIFICATION.md): -->
```markdown
---
phase: 2
slug: subscription-bridge-ci-matrix
status: draft | in-progress | pass | partial | fail
ci_matrix_run: "<github-actions-run-url>"
canary_run: "Saved/NYRA/canary-subscription-bridge-<ts>.log"
phase0_clearance: yes | no | pending
phase1_sc3_bench_commit: <sha or n/a if not yet in>
pending_manual_verification: true | false
---

# Phase 2 — Verification

## Success Criteria
| SC | Claim | Verifier | Evidence | Status |
|----|-------|---------|----------|--------|
| SC#1 | Claude Code CLI subscription driving verified end-to-end | Plan 02-05 + live canary | canary log path; test_claude_live_turn.py PASS | ⬜ pending / ✅ pass / ❌ fail |
| SC#2 | Graceful fallback + Privacy Mode | Plan 02-06 + NyraStatusPillSpec | Nyra.Panel.StatusPill.PrivacyMode It block PASS + manual Privacy Mode toggle roundtrip | ⬜ / ✅ / ❌ |
| SC#3 | Plan-first-by-default (CHAT-04) | Plan 02-09 permission gate | Nyra.Preview.ApproveFlow + RejectFlow It block PASS + live canary plan/preview observed | ⬜ / ✅ / ❌ |
| SC#4 | FScopedTransaction + Ctrl+Z rollback | Plan 02-08 NyraTransactionsSpec | Nyra.Transactions.* It blocks PASS + manual Ctrl+Z after canary | ⬜ / ✅ / ❌ |
| SC#5 | Four-version CI matrix green + compat shim populated | Plans 02-01 + 02-07 + 02-13 | github-actions-run-url with all four cells green, EV-signed; compat-matrix-first-run.md committed | ⬜ / ✅ / ❌ |
| SC#6 | EV code-signing + router multi-backend + console/log tools | Plans 02-13 + 02-06 + 02-10 + 02-11 | signtool verify output committed; test_backend_interface passed; Nyra.Console.* + Nyra.Logging.* PASS | ⬜ / ✅ / ❌ |

## Requirement coverage
| REQ | Plan(s) | Verified |
|-----|---------|----------|
| PLUG-04 | 02-01, 02-07, 02-13 | ✅ / ❌ |
| SUBS-01 | 02-05 | ✅ / ❌ |
| SUBS-02 | 02-06 | ✅ / ❌ |
| SUBS-03 | 02-03, 02-06 | ✅ / ❌ |
| CHAT-02 | 02-12 | ✅ / ❌ |
| CHAT-03 | 02-08 | ✅ / ❌ |
| CHAT-04 | 02-09 | ✅ / ❌ |
| ACT-06 | 02-10 | ✅ / ❌ |
| ACT-07 | 02-11 | ✅ / ❌ |

## Manual verification log
[Operator fills after live canary run:]
- <ts>: canary run N=10, all turns PASS, no Claude-side errors
- <ts>: Privacy Mode toggle — pill turned purple, subsequent chat/send refused Claude, GemmaBackend answered
- <ts>: Ctrl+Z after a canned-tool-call canary turn — full session rolled back, UTransBuffer visible entry disappeared

## Known Wave 0 gaps discovered empirically
- <gap 1 if any>
- <gap 2 if any>
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add Nyra.Dev.SubscriptionBridgeCanary + test_claude_live_turn.py</name>
  <files>TestProject/Plugins/NYRA/Source/NyraEditor/Public/Dev/FNyraDevTools.h, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Dev/FNyraDevTools.cpp, TestProject/Plugins/NYRA/Source/NyraHost/tests/test_claude_live_turn.py</files>
  <action>
    **Module-superset on Phase 1 Plan 14 (FNyraDevTools — D-24):** every Nyra.Dev.RoundTripBench line preserved verbatim. Phase 2 adds:

    1. New static method `FNyraDevTools::RunSubscriptionBridgeCanary(int32 N, const FString& Prompt)` mirroring the Phase 1 RunRoundTripBench structure but:
       - Uses backend=claude (not gemma-local)
       - Per-turn measures: first_token_ms, total_ms, tool_calls_count (if any plan_preview fired), errors_count (non-zero done frames), backend_state_observed (copies from diagnostics/backend-state notifications)
       - Captures the reason any turn failed (via chat/stream error frame .remediation string)
       - Writes results to Saved/NYRA/canary-subscription-bridge-<ISO-ts>.log as JSON lines + a final SUMMARY block
       - Pass verdict: all turns done=true with no error AND diagnostics/backend-state observed AND (if any turn induced a tool_use) plan/preview AND plan/decision round-trip observed
    2. New FAutoConsoleCommand registering Nyra.Dev.SubscriptionBridgeCanary with default N=10 + prompt. Clamp N to [1, 50] (lower cap than Phase 1 because each Claude turn consumes real quota).
    3. Phase 1's FNyraDevTools::RunRoundTripBench stays intact; the new canary is a parallel method.

    Add `tests/test_claude_live_turn.py`:
    - pytest marker `@pytest.mark.live` registered in pyproject.toml (ini option `markers = ['live: uses real Claude CLI via CLAUDE_CODE_OAUTH_TOKEN env']`)
    - Skip marker at file top: `pytestmark = pytest.mark.skipif(not os.getenv('CLAUDE_CODE_OAUTH_TOKEN'), reason='requires CLAUDE_CODE_OAUTH_TOKEN env')` — AND `pytest.mark.skipif(os.getenv('NYRA_PHASE0_CLEARANCE') != 'confirmed', reason='Phase 0 legal clearance precondition')`
    - Tests:
      - test_live_turn_emits_done — spawn ClaudeBackend with real claude CLI; send 'Reply with OK only'; assert Done event observed + emit log for schema
      - test_live_turn_captures_ndjson_fixture — during the turn, capture the raw stdout as NDJSON and write to tests/fixtures/stream-json-cli-v<VERSION>.ndjson; next CI run uses this for schema-drift regression detection (RESEARCH §10.1)

    Commit: feat(02-14): add Nyra.Dev.SubscriptionBridgeCanary + test_claude_live_turn guarded pytest
  </action>
  <verify>
    <automated>grep -q "Nyra.Dev.SubscriptionBridgeCanary" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Dev/FNyraDevTools.cpp && grep -q "Nyra.Dev.RoundTripBench" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Dev/FNyraDevTools.cpp && test -f TestProject/Plugins/NYRA/Source/NyraHost/tests/test_claude_live_turn.py</automated>
  </verify>
  <done>
    - FNyraDevTools preserves Phase 1 RunRoundTripBench + adds RunSubscriptionBridgeCanary
    - Console command Nyra.Dev.SubscriptionBridgeCanary registered with 1..50 clamp
    - test_claude_live_turn.py guarded by CLAUDE_CODE_OAUTH_TOKEN + NYRA_PHASE0_CLEARANCE env vars
    - NDJSON fixture capture pathway in place for Wave 0 schema-drift regression
    - Module-superset discipline preserved
  </done>
</task>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task 2: FOUNDER — Run the live canary + author 02-VERIFICATION.md</name>
  <what-built>
    Claude has landed the canary harness + guarded live test + the empty VERIFICATION.md template. The live canary cannot run on the macOS dev host (no Claude Code CLI Windows build in this env); it runs on the Windows self-hosted runner OR on the founder's Windows dev workstation with a real Claude Pro/Max subscription.
  </what-built>
  <how-to-verify>
    ### Preconditions (all must be true)
    1. Phase 0 written ToS clearance from Anthropic on file; `NYRA_PHASE0_CLEARANCE=confirmed` in the environment used for execution.
    2. Phase 1 Plan 15 ring0 empirical bench pass verdict committed (see ring0-bench-results.md frontmatter `pending_manual_verification: false`).
    3. EV cert acquired + GitHub Actions secrets populated (Plan 02-04 resume-signal `ev-cert-in-akv-and-secrets-populated` OR documented `ev-cert-stalled` deferral).
    4. All Plans 02-01 through 02-13 SUMMARYs on disk (look under `.planning/phases/02-subscription-bridge-ci-matrix/02-*-SUMMARY.md`).

    ### Procedure
    1. **CI matrix trigger:** Push the full Phase 2 branch to main (or open a release PR). Wait for plugin-matrix.yml to go green on all four UE cells with signed artifacts uploaded. Capture the GitHub Actions run URL.
    2. **Live canary (Windows):** Open the UE editor with the plugin, sign into Claude via `claude auth login` if not already authenticated, open the chat panel, open the console, run:
       ```
       Nyra.Dev.SubscriptionBridgeCanary 10 "Reply with the single word OK only."
       ```
       Wait for the SUMMARY block; expect VERDICT: PASS. Capture `Saved/NYRA/canary-subscription-bridge-<ts>.log`.
    3. **Manual sanity checks** (each must pass):
       - Observe the Claude pill turn Green during streaming (diagnostics/backend-state live)
       - Trigger a turn that induces a tool_use (prompt e.g. "Spawn a point light at origin in the current level") — verify SNyraPreviewCard appears with correct plan summary
       - Click Reject on the preview card; verify chat/stream returns `-32011 plan_rejected`
       - After a successful tool-use turn, press Ctrl+Z — verify the tool-side mutation is undone (if tool-use reaches a real Phase 4+ tool — in Phase 2, a smoke-test tool may be required; OR substitute by observing UTransBuffer's undo count increment by exactly 1 per NYRA session)
       - Toggle Privacy Mode from the Privacy pill; verify next chat/send routes to Gemma; toggle off; verify Claude accepted again
    4. **Live pytest:** On Windows, `CLAUDE_CODE_OAUTH_TOKEN=<token> NYRA_PHASE0_CLEARANCE=confirmed python -m pytest tests/test_claude_live_turn.py -v -m live` — expect PASS; verify `stream-json-cli-v2.1.X.ndjson` fixture file created under tests/fixtures/ with captured NDJSON lines.
    5. **Compile 02-VERIFICATION.md:** Using the template shape from the interfaces block, replace PENDING cells with evidence (CI run URL, canary log path, manual-check timestamps). Set frontmatter `status: pass` if every SC is ✅; `partial` if at least one is ❌ with a documented cut-line waiver; `fail` otherwise.
  </how-to-verify>
  <resume-signal>
    Reply with `phase-2-verified-pass` + the 02-VERIFICATION.md contents (or a path confirming commit of the populated doc). Attach the github-actions-run-url + canary log path.

    If any SC fails reply `phase-2-partial: SC#X failed; proposed waiver: ...` OR `phase-2-fail: SC#Y blocker; remediation plan needed`.
  </resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Live canary → Claude Pro/Max quota | Operator's own subscription; consumption is bounded by N=10..50 clamp |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-14-01 | Denial of Service | Canary with N=50 consumes 50 turns of operator's quota; if run carelessly, exhausts 5-hour window | mitigate | Default N=10 (small); cap N=50; canary console command shows a one-time ConsentModal on first run per session asking "This will use ~N turns of your Claude subscription. Continue? [Y/N]" |
| T-02-14-02 | Information Disclosure | NDJSON fixture captured from live canary may contain operator's identifying info | mitigate | Capture routine redacts `session_id`, `uuid`, and any obvious email/org strings before writing to fixture. Runbook in SIGNING_VERIFICATION-adjacent doc. |
</threat_model>

<verification>
- `grep -q "Nyra.Dev.SubscriptionBridgeCanary" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Dev/FNyraDevTools.cpp`
- `test -f TestProject/Plugins/NYRA/Source/NyraHost/tests/test_claude_live_turn.py`
- Checkpoint resolved with `phase-2-verified-pass` OR documented `phase-2-partial` / `phase-2-fail` with remediation
- 02-VERIFICATION.md committed with all SC + REQ rows populated
</verification>

<success_criteria>
- Live canary demonstrates Claude CLI driver end-to-end on a Windows host with real subscription
- All six ROADMAP Phase 2 Success Criteria evaluated PASS/FAIL with concrete evidence
- All nine REQ-IDs traceable to their owning plan + verification test
- Schema-drift regression fixture captured for Wave 0 of Phase 3
- Phase 2 is declared COMPLETE when 02-VERIFICATION.md frontmatter `status: pass`
</success_criteria>

<output>
After completion, create `.planning/phases/02-subscription-bridge-ci-matrix/02-14-SUMMARY.md`

Plan 02-14 is the LAST plan in Phase 2. Its SUMMARY.md closes the phase at source/docs layer; 02-VERIFICATION.md closes the phase at verification layer.
</output>
