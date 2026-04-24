---
phase: 2
slug: subscription-bridge-ci-matrix
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-23
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `02-RESEARCH.md` §11 "Validation Architecture" + user-provided
> suggested wave structure. Authoritative.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (C++)** | UE **Automation Spec** (inherited from Phase 1 Plan 01; `Nyra.*` namespace). |
| **Framework (Python)** | **pytest 8.x** + `pytest-asyncio` + `pytest-httpx` (inherited Phase 1) + **pytest-subprocess ≥1.5** (NEW in Plan 02-05 for claude CLI spawn mocking). |
| **Framework (CI)** | GitHub Actions with self-hosted Windows runner labeled `self-hosted,Windows,unreal` (NEW in Plan 02-01). |
| **C++ config file** | None — specs discovered via macros in `TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/`. |
| **Python config file** | `TestProject/Plugins/NYRA/Source/NyraHost/pyproject.toml` (extended additively by Plan 02-05 for pytest-subprocess). |
| **Quick run command (C++)** | `UnrealEditor-Cmd.exe TestProject.uproject -ExecCmds="Automation RunTests Nyra;Quit" -unattended -nopause -nullrhi` (UE 5.6 dev host). |
| **Quick run command (Python)** | `cd TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest -x` |
| **Full suite (C++)** | As above, no filter — runs on dev host + all four matrix cells on PR. |
| **Full suite (Python)** | `python -m pytest -v` — runs once per PR (version-agnostic pytest-host.yml). |
| **Live-guarded Python** | `CLAUDE_CODE_OAUTH_TOKEN=<t> NYRA_PHASE0_CLEARANCE=confirmed python -m pytest -m live` — Plan 02-14 only. Skipped in CI. |
| **Four-version matrix** | `.github/workflows/plugin-matrix.yml` targets 5.4/5.5/5.6/5.7 with `fail-fast: false`. EV-signing step added by Plan 02-13. |

---

## Sampling Rate

- **After every task commit:** `python -m pytest -x` (sub-second for most; claude_live_turn skips without env) + Automation quick filter matching the modified module
- **After every wave merge:** Full pytest suite + full `Nyra.*` Automation suite on UE 5.6 dev host
- **Per PR:** Four-version CI matrix runs to completion (all cells, even if one fails, per D-14 fail-fast:false). pytest-host.yml runs once.
- **Before phase-exit verification (Plan 02-14):**
  1. Four-version matrix GREEN with signed artifacts
  2. EV-signed binaries verified with `signtool verify /pa <dll>` (manual Plan 02-13 runbook)
  3. Live Claude turn (`pytest -m live`) PASS with `CLAUDE_CODE_OAUTH_TOKEN` env set on Windows host
  4. Nyra.Dev.SubscriptionBridgeCanary 10 PASS on Windows UE editor (Plan 02-14)
  5. Privacy Mode toggle round-trip manually verified (Plan 02-12)

- **Max feedback latency:** 60s quick (unit/spec) / 5min full pytest / 30-60min full CI matrix (depends on runner)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 0 | PLUG-04 | CI workflow | PR triggers plugin-matrix.yml; all four cells go green at least once (via feature-branch smoke) | ❌ W0 | ⬜ pending |
| 2-01-02 | 01 | 0 | PLUG-04 | C++ compile | `NYRACompat.h` compiles on UE 5.6 dev host (Automation Spec `Nyra.Compat.Macro`) | ❌ W0 | ⬜ pending |
| 2-02-01 | 02 | 0 | all | docs | `grep -q "session/set-mode" docs/JSONRPC.md && grep -q "diagnostics/backend-state" docs/JSONRPC.md` | ❌ W0 | ⬜ pending |
| 2-02-02 | 02 | 0 | all | docs | `grep -c "^\\| -320" docs/ERROR_CODES.md` ≥ 14 | ❌ W0 | ⬜ pending |
| 2-03-01 | 03 | 0 | SUBS-03 | pytest | `pytest tests/test_backend_interface.py::test_abc_rejects_direct_instantiation` | ❌ W0 | ⬜ pending |
| 2-03-02 | 03 | 0 | SUBS-03 | pytest | `pytest tests/test_backend_interface.py::test_registry_has_gemma_local` | ❌ W0 | ⬜ pending |
| 2-03-03 | 03 | 0 | SUBS-03 | pytest | `pytest tests/test_gemma_backend_adapter.py` (4 tests) | ❌ W0 | ⬜ pending |
| 2-04-01 | 04 | 0 | PLUG-04 | docs | `docs/EV_CERT_ACQUISITION.md` exists + grep-verifiable markers | ❌ W0 | ⬜ pending |
| 2-04-02 | 04 | 0 | PLUG-04 | manual | FOUNDER checkpoint: resume-signal `ev-cert-in-akv-and-secrets-populated` received | — | ⬜ pending |
| 2-05-01 | 05 | 1 | SUBS-01 | pytest | `pytest tests/test_claude_stream.py` (≥8 tests) | ❌ W0 | ⬜ pending |
| 2-05-02 | 05 | 1 | SUBS-01 | pytest | `pytest tests/test_claude_mcp_config.py` (≥6 tests) | ❌ W0 | ⬜ pending |
| 2-05-03 | 05 | 1 | SUBS-01 | pytest | `pytest tests/test_claude_backend.py` (≥10 tests) | ❌ W0 | ⬜ pending |
| 2-06-01 | 06 | 1 | SUBS-02, SUBS-03 | pytest | `pytest tests/test_router.py` (≥14 tests covering state machine) | ❌ W0 | ⬜ pending |
| 2-06-02 | 06 | 1 | SUBS-02 | pytest | `pytest tests/test_session_mode.py` (≥7 tests) | ❌ W0 | ⬜ pending |
| 2-07-01 | 07 | 1 | PLUG-04 | manual + C++ | compat-matrix-first-run.md committed; NyraCompatSpec It blocks match drift count | ❌ W0 | ⬜ pending |
| 2-08-01 | 08 | 2 | CHAT-03 | automation | `Nyra.Transactions.SessionScope` (4 Its) | ❌ W0 | ⬜ pending |
| 2-08-02 | 08 | 2 | CHAT-03 | automation | `Nyra.Transactions.NestedCoalesce` (2 Its) | ❌ W0 | ⬜ pending |
| 2-08-03 | 08 | 2 | CHAT-03 | automation | `Nyra.Transactions.CancelRollback` (2 Its) | ❌ W0 | ⬜ pending |
| 2-08-04 | 08 | 2 | CHAT-03 | integration | diagnostics/pie-state emitted on BeginPIE/EndPIE (manual UE editor check) | ❌ W0 | ⬜ pending |
| 2-09-01 | 09 | 2 | CHAT-04 | pytest | `pytest tests/test_permission_gate.py` (schema validation + MCP reg) | ❌ W0 | ⬜ pending |
| 2-09-02 | 09 | 2 | CHAT-04 | pytest | `pytest tests/test_preview_handler.py` (≥7 tests — partial JSON, auto-approve, reject) | ❌ W0 | ⬜ pending |
| 2-09-03 | 09 | 2 | CHAT-04 | automation | `Nyra.Preview.Render`, `Nyra.Preview.ApproveFlow`, `Nyra.Preview.RejectFlow`, `Nyra.Preview.AutoApproveReadOnly` | ❌ W0 | ⬜ pending |
| 2-10-01 | 10 | 2 | ACT-06 | pytest | `pytest tests/test_console_whitelist.py` (12+ classifier tests) | ❌ W0 | ⬜ pending |
| 2-10-02 | 10 | 2 | ACT-06 | pytest | `pytest tests/test_console_handler.py` (tier routing tests) | ❌ W0 | ⬜ pending |
| 2-10-03 | 10 | 2 | ACT-06 | automation | `Nyra.Console.ExecCaptureOutput`, `Nyra.Console.RefusesDuringPIE`, `Nyra.Console.OutputDeviceCapture` | ❌ W0 | ⬜ pending |
| 2-11-01 | 11 | 2 | ACT-07 | pytest | `pytest tests/test_log_tail.py` (≥7 tests — forwarding + cap + defaults) | ❌ W0 | ⬜ pending |
| 2-11-02 | 11 | 2 | ACT-07 | automation | `Nyra.Logging.RingBufferBounded`, `CategoryFilter`, `MinVerbosity`, `DefaultExclusions`, `RegexFilter`, `MessageLogListingRegistered`, `CrashFlushToFile` | ❌ W0 | ⬜ pending |
| 2-12-01 | 12 | 3 | CHAT-02 | automation | `Nyra.Panel.StatusPill.Ready`, `RateLimited`, `AuthDrift`, `PrivacyMode`, `ParseJson` | ❌ W0 | ⬜ pending |
| 2-12-02 | 12 | 3 | CHAT-02 | manual | Privacy Mode toggle turns pills purple; session/set-mode round-trip observed in NyraHost structlog | ❌ W0 | ⬜ pending |
| 2-13-01 | 13 | 3 | PLUG-04 | CI | plugin-matrix.yml signs all emitted binaries; `signtool verify /pa` passes on every cell | ❌ W0 | ⬜ pending |
| 2-13-02 | 13 | 3 | PLUG-04 | manual | FOUNDER runs docs/SIGNING_VERIFICATION.md runbook on one artifact bundle before RC1 | ❌ W0 | ⬜ pending |
| 2-14-01 | 14 | 3 | all | live canary | `Nyra.Dev.SubscriptionBridgeCanary 10` VERDICT=PASS on Windows host with real Claude subscription | ❌ W0 | ⬜ pending |
| 2-14-02 | 14 | 3 | all | live pytest | `pytest -m live` with CLAUDE_CODE_OAUTH_TOKEN + NYRA_PHASE0_CLEARANCE env PASS | ❌ W0 | ⬜ pending |
| 2-14-03 | 14 | 3 | all | manual | FOUNDER authors 02-VERIFICATION.md with `status: pass` frontmatter; all 6 SCs + 9 REQs ✅ | ❌ W0 | ⬜ pending |

*Status legend: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · 🔒 phase0-clearance-gated*

---

## Wave 0 Requirements

**CI + infrastructure** (Plans 02-01, 02-04):
- [ ] `.github/workflows/plugin-matrix.yml` authored with four-version strategy matrix + fail-fast:false
- [ ] `.github/workflows/pytest-host.yml` authored with single pytest-single job
- [ ] `.github/workflows/README-CI.md` runbook published
- [ ] Self-hosted Windows runner provisioned + registered with `self-hosted,Windows,unreal` labels (FOUNDER checkpoint)
- [ ] `TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h` — macro armed, empty namespace
- [ ] `NyraCompatSpec.cpp` smoke-test It block
- [ ] `docs/EV_CERT_ACQUISITION.md` end-to-end runbook
- [ ] `docs/EV_CERT_RENEWAL.md` companion runbook
- [ ] FOUNDER checkpoint resume-signal `ev-cert-in-akv-and-secrets-populated` (non-blocking until Plan 02-13 executes)

**Wire protocol** (Plan 02-02):
- [ ] `docs/JSONRPC.md` extended with nine new Phase 2 methods
- [ ] `docs/ERROR_CODES.md` extended with codes `-32007..-32014`

**Backend abstraction** (Plan 02-03):
- [ ] `nyrahost.backends.base.AgentBackend` ABC + `BackendEvent` tagged union + `HealthState` enum
- [ ] `nyrahost.backends.gemma.GemmaBackend` wraps Phase 1 InferRouter with zero behaviour change
- [ ] `nyrahost.backends.__init__.BACKEND_REGISTRY['gemma-local']` populated

**Wave-0 tests that must already be present** (from Plans 02-01 through 02-04):
- [ ] `test_backend_interface.py` — 5+ tests
- [ ] `test_gemma_backend_adapter.py` — 4+ tests
- [ ] Phase 1 pytest suite (34 tests from Plan 01-09 liquidation) — STILL green; no regressions

---

## Test Evidence Map (Wave 2+ creates these)

| File | Created by | Purpose |
|------|-----------|---------|
| `tests/test_claude_stream.py` | 02-05 | NDJSON parser tests |
| `tests/test_claude_mcp_config.py` | 02-05 | MCP config writer tests |
| `tests/test_claude_backend.py` | 02-05 | ClaudeBackend subprocess tests |
| `tests/test_router.py` | 02-06 | Router state machine tests |
| `tests/test_session_mode.py` | 02-06 | session/set-mode + privacy integration |
| `tests/test_permission_gate.py` | 02-09 | MCP tool schema validation |
| `tests/test_preview_handler.py` | 02-09 | Plan/preview + plan/decision |
| `tests/test_console_whitelist.py` | 02-10 | Classifier matrix |
| `tests/test_console_handler.py` | 02-10 | Tier routing |
| `tests/test_log_tail.py` | 02-11 | MCP tool wrappers |
| `tests/test_claude_live_turn.py` | 02-14 | Live guarded integration |
| `tests/fixtures/stream-json-*.ndjson` | 02-05 + 02-14 | Schema-drift regression baseline |
| `NyraCompatSpec.cpp` | 02-01 + 02-07 | Macro + per-drift It blocks |
| `NyraTransactionsSpec.cpp` | 02-08 | Three Describe blocks |
| `NyraPreviewSpec.cpp` | 02-09 | Plan preview UI tests |
| `NyraConsoleSpec.cpp` | 02-10 | GameThread Exec capture |
| `NyraLoggingSpec.cpp` | 02-11 | Sink + listener + crash flush |
| `NyraStatusPillSpec.cpp` | 02-12 | Pill color/tooltip tests |

---

## Live / Manual-Only Verifications

These cannot run on ephemeral CI or the macOS dev host; they are the operator's responsibility:

1. **Cert acquisition** (Plan 02-04) — founder task; 1-3 business days at minimum.
2. **Self-hosted runner provisioning** (Plan 02-01) — founder's Windows workstation must be Online in GitHub Actions.
3. **Compat matrix first-run drift capture** (Plan 02-07) — requires CI matrix to execute at least once; operator pastes compile errors back for shim population.
4. **Live Claude canary** (Plan 02-14) — requires real Claude subscription + Phase 0 legal clearance + Windows UE editor. Consumes ~10-50 turns of operator's quota per run. DO NOT run in CI.
5. **Phase 1 SC#3 empirical bench gate** (inherited from Phase 1 Plan 15) — still pending Windows bench measurement; Phase 2 execution of Plan 02-14 requires this to be committed as `pending_manual_verification: false`.
6. **EV cert signing verification** (Plan 02-13) — manual `signtool verify /pa` on first release-candidate bundle before any Fab-direction activity.
7. **Privacy Mode round-trip** (Plan 02-12) — manual toggle + assert no egress in network sniffer / pcap capture (bonus verification for enterprise/NDA user assurance).
8. **Ctrl+Z end-to-end** (Plan 02-08) — post-tool-call in the live editor; tricky to automate fully because tool side-effects land in Phase 4+.

---

## Known Risks to Validation Plan

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Claude Code CLI ships breaking stream-json schema change mid-phase | MEDIUM (RESEARCH §10.1) | Nightly canary re-captures NDJSON fixture; PR bumps pin and lands compat delta in same MR |
| UE 5.7 not GA at phase-execution time | LOW-MEDIUM | D-15 deferral; Plan 02-01 + 02-07 + 02-13 operator downgrade documented |
| Self-hosted runner offline mid-phase | LOW | Cloud Windows VM as v1.1 backup budgeted; manual local `RunUAT BuildPlugin` as fallback |
| DigiCert cert acquisition stalls beyond Wave 3 | LOW-MEDIUM | Plan 02-13 can ship unsigned with `ev-cert-stalled` escalation; phase-exit waives SC#6 EV-signing sub-criterion with explicit note |
| Live canary false-positive from anthropic 5xx window | LOW | RESEARCH §10.6 + Plan 02-06 test test_observe_retry_server_error_attempt_3_surfaces_error_but_stays ensures transient 5xx doesn't register as phase failure |

---

*Validation authored: 2026-04-23 following user-supplied wave structure + RESEARCH §11.*
*Phase-exit target: all ⬜ flipped to ✅ + 02-VERIFICATION.md `status: pass`.*
