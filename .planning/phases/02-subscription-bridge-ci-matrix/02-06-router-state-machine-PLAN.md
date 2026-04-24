---
phase: 02-subscription-bridge-ci-matrix
plan: 06
slug: router-state-machine
type: execute
wave: 1
depends_on: [02, 03, 05]
autonomous: true
tdd: true
requirements: [SUBS-02, SUBS-03]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/router.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/chat.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/session_mode.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_router.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_session_mode.py
research_refs: [§2.1, §2.2, §2.3, §2.4, §2.5, §10.6]
context_refs: [D-03, D-04, D-05, D-23]
phase0_clearance_required: true
must_haves:
  truths:
    - "nyrahost.router.Router exposes a state enum matching RESEARCH §2.2 exactly: Disconnected, ClaudeReady, ClaudeStreaming, ClaudeRateLimited, AuthDrift, GemmaFallback, PrivacyMode"
    - "Router state transitions are driven from BackendEvent streams: Retry(error_category='rate_limit') with exhausted attempts → ClaudeRateLimited; Retry(error_category='authentication_failed') → AuthDrift; server_error / unknown attempts < 3 → silent retry in place; server_error / unknown attempts ≥ 3 → surface but DO NOT fallback (RESEARCH §10.6 false-positive mitigation)"
    - "Router.decide_backend(params.backend, current_state, mode) maps the chat/send backend param + state → concrete AgentBackend instance. Claude-requested + ClaudeReady → ClaudeBackend. Claude-requested + AuthDrift/ClaudeRateLimited with NO user-approved fallback → Error(-32008 or -32009). PrivacyMode overrides: always returns GemmaBackend (refuses Claude)"
    - "Router never silently flips to Gemma mid-stream per D-04 — user must explicitly approve via UI button (represented in tests as a 'user_approved_fallback' boolean flag)"
    - "handlers/session_mode.SessionModeHandler.on_set_mode handles session/set-mode request; mode='privacy' triggers router.enter_privacy_mode() + emits diagnostics/backend-state notification"
    - "app.py wires handshake-file path + plugin-binaries-dir into Router construction (DI surface expanded); server registers session/set-mode via ChatHandlers or a new handler"
    - "test_router.py covers: initial state, Disconnected→ClaudeReady on health_check pass, ClaudeReady→ClaudeStreaming on chat/send, ClaudeStreaming→ClaudeRateLimited on exhausted rate-limit, ClaudeStreaming→AuthDrift on auth_failed, server_error retry<3 stays, server_error retry≥3 surfaces error but no fallback, user_approved_fallback + ClaudeRateLimited → GemmaFallback, PrivacyMode entry refuses claude, PrivacyMode exit restores prior path"
    - "Full pytest green — Phase 1 tests + Plan 02-03/02-05 tests + new router tests"
  artifacts:
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/router.py
      provides: "Router state machine + transition policy + backend selection"
      exports: ["Router", "RouterState", "BackendDecision"]
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/session_mode.py
      provides: "session/set-mode request handler"
      exports: ["SessionModeHandler"]
  key_links:
    - from: Router.observe_event
      to: BackendEvent tagged union (from Plan 02-03)
      via: "Pattern-match on Retry / Error / Done payloads to drive transitions"
      pattern: "match event:.*Retry|Error|Done"
    - from: Router transition → diagnostics/backend-state notification
      to: docs/JSONRPC.md §4.8
      via: "server.send_notification('diagnostics/backend-state', params)"
      pattern: "diagnostics/backend-state"
---

<objective>
Layer the router state machine ON TOP of Plan 02-05's `ClaudeBackend` + Plan 02-03's `AgentBackend` abstraction. This plan:

- Owns the state enum + transition table (RESEARCH §2.1–2.3)
- Decides which concrete backend to spawn per `chat/send` based on current state + user mode
- Emits `diagnostics/backend-state` notifications on every transition (wire contract from Plan 02-02 §4.8)
- Handles `session/set-mode` for Privacy Mode toggle

Per CONTEXT.md:
- D-03: state enum + transitions locked per RESEARCH §2.2
- D-04: no silent fallback mid-stream — user must explicitly approve
- D-05: Privacy Mode refuses Claude; cannot silently bypass
- D-23: wire contract for `diagnostics/backend-state` and `session/set-mode` already documented in Plan 02-02

**This plan is phase0_clearance_required** — Privacy Mode toggle mechanics are planning-safe, but the Claude-path transitions execute-live only after Phase 0 ToS clearance.

**TDD** with state-machine tests the highest-leverage path — transition tests are cheap, prevent regressions, and make the rate-limit-false-positive mitigation (RESEARCH §10.6) literally an asserted invariant.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/02-subscription-bridge-ci-matrix/02-CONTEXT.md
@.planning/phases/02-subscription-bridge-ci-matrix/02-RESEARCH.md
@docs/JSONRPC.md
@docs/ERROR_CODES.md

<interfaces>
<!-- State enum + transitions (RESEARCH §2.2): -->
<!-- Disconnected → ClaudeReady: claude auth status exit 0 -->
<!-- ClaudeReady → ClaudeStreaming: chat/send with backend=claude -->
<!-- ClaudeStreaming → ClaudeReady: BackendEvent.Done observed -->
<!-- ClaudeStreaming → ClaudeRateLimited: N consecutive Retry(error_category='rate_limit') events with attempt==max_retries -->
<!-- ClaudeStreaming → AuthDrift: Retry(error_category='authentication_failed') observed -->
<!-- ClaudeStreaming → (stay) silent: Retry(error_category in {'server_error','unknown'}) and attempt < 3 -->
<!-- ClaudeStreaming → (stay + Error frame out): Retry same categories and attempt ≥ 3 -->
<!-- ClaudeRateLimited + user_approved_fallback → GemmaFallback -->
<!-- AuthDrift + user_approved_fallback → GemmaFallback -->
<!-- * → PrivacyMode: session/set-mode mode=privacy (orthogonal; stores prior state in pop-back variable) -->
<!-- PrivacyMode → prior_state: session/set-mode mode=normal -->

<!-- Router public surface: -->
<!--   class Router: -->
<!--     state: RouterState -->
<!--     mode: Literal['normal','privacy'] -->
<!--     prior_state_before_privacy: RouterState | None -->
<!--     def __init__(self, registry: dict[str, type[AgentBackend]], emit_notification: Callable[[str, dict], Awaitable[None]], ...): -->
<!--     async def health_probe() -> None            # runs claude auth status → may transition Disconnected → ClaudeReady or back -->
<!--     async def decide_backend(request_backend: str, user_approved_fallback: bool) -> AgentBackend | Error -->
<!--     async def observe_event(ev: BackendEvent) -> None   # in the middle of a turn -->
<!--     async def enter_privacy_mode() -> None -->
<!--     async def exit_privacy_mode() -> None -->
<!--   RouterState = Enum 'Disconnected','ClaudeReady','ClaudeStreaming','ClaudeRateLimited','AuthDrift','GemmaFallback','PrivacyMode' -->

<!-- Every transition emits diagnostics/backend-state (notifies UE panel); params shape per docs/JSONRPC.md §4.8. -->

<!-- Integration: handlers/chat.py.on_chat_send now delegates to Router: -->
<!--   backend = await router.decide_backend(params.backend, params.user_approved_fallback or False) -->
<!--   if isinstance(backend, Error): emit chat/stream done with error and return -->
<!--   async for ev in backend.send_stream(...): await router.observe_event(ev); await emit(ev) -->
<!-- chat.py's module-superset discipline (D-24) preserved; Router just replaces what was Plan 02-03's backend_cls = registry[...]. -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1 (RED+GREEN): Router state machine + transition table</name>
  <files>TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/router.py, TestProject/Plugins/NYRA/Source/NyraHost/tests/test_router.py</files>
  <behavior>
    - test_initial_state_is_disconnected
    - test_health_probe_exit_0_sets_claude_ready
    - test_health_probe_exit_1_sets_auth_drift
    - test_health_probe_binary_missing_stays_disconnected
    - test_decide_backend_claude_when_ready — returns ClaudeBackend instance
    - test_decide_backend_claude_when_ratelimited_refuses — returns Error(-32009)
    - test_decide_backend_claude_when_ratelimited_with_approved_fallback_returns_gemma — returns GemmaBackend, state = GemmaFallback
    - test_decide_backend_privacy_mode_refuses_claude — returns GemmaBackend regardless of request
    - test_observe_retry_rate_limit_exhausted_transitions_to_ratelimited — Retry(attempt=3, max_retries=3, rate_limit) triggers transition
    - test_observe_retry_rate_limit_not_exhausted_stays — Retry(attempt=1, max_retries=3, rate_limit) stays in ClaudeStreaming
    - test_observe_retry_auth_failed_transitions_to_authdrift — first auth_failed event transitions
    - test_observe_retry_server_error_attempt_1_stays_silent — Retry(attempt=1, 'server_error') stays + NO error frame out
    - test_observe_retry_server_error_attempt_3_surfaces_error_but_stays — attempt=3 emits error frame but state stays (RESEARCH §10.6)
    - test_observe_done_returns_to_claude_ready — from ClaudeStreaming to ClaudeReady
    - test_enter_privacy_mode_stores_prior_state — mode=privacy from ClaudeReady stores 'ClaudeReady' for pop-back
    - test_exit_privacy_mode_restores — mode=normal pops back to prior state
    - test_every_transition_emits_diagnostics_backend_state — emit_notification mock records method='diagnostics/backend-state' + params shape per docs/JSONRPC.md §4.8
  </behavior>
  <action>
    RED: commit test(02-06): add failing router state-machine tests

    GREEN: implement `nyrahost/router.py`:
      - RouterState IntEnum
      - Router class with methods from interfaces block
      - Transition table encoded as a dict[(state, event_type), Callable] OR an explicit match/case block in observe_event (Python 3.10+ match statements)
      - Every transition writes the `diagnostics/backend-state` notification via the injected `emit_notification(method, params)` callable
      - No imports of concrete backends — Router depends on AgentBackend ABC only. Registry is DI'd.

    Commit: feat(02-06): add router state machine + transition policy
  </action>
  <verify>
    <automated>cd TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest tests/test_router.py -v 2>&1 | tail -5 | grep -E "passed|failed"</automated>
  </verify>
  <done>
    - Router + 14+ transition tests green
    - Every transition path covered; rate-limit false-positive mitigation asserted
    - diagnostics/backend-state notification emitted on every transition
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2 (RED+GREEN): session/set-mode handler + privacy mode integration</name>
  <files>TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/session_mode.py, TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/chat.py, TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py, TestProject/Plugins/NYRA/Source/NyraHost/tests/test_session_mode.py</files>
  <behavior>
    - test_set_mode_privacy_transitions_router — on_set_mode({mode:'privacy'}) → router.enter_privacy_mode() called
    - test_set_mode_normal_exits_privacy — on_set_mode({mode:'normal'}) → router.exit_privacy_mode() called
    - test_set_mode_returns_mode_applied_true — response payload
    - test_set_mode_invalid_mode_raises — mode='lol' raises ValueError → JSON-RPC error surface
    - test_chat_send_in_privacy_mode_uses_gemma — chat/send params.backend='claude' while mode=privacy routes to GemmaBackend (Router.decide_backend)
    - test_chat_send_outside_privacy_mode_uses_claude — ends with ClaudeBackend in Ready state
    - test_chat_send_emits_diagnostics_backend_state — on stream start
  </behavior>
  <action>
    RED: commit test(02-06): add failing session/set-mode + privacy-mode integration tests

    GREEN:
    - Create `nyrahost/handlers/session_mode.py` with `SessionModeHandler(router)` dataclass + `async def on_set_mode(params)` returning `{mode_applied: bool}`. Invalid mode → ValueError(f"invalid mode {mode!r}; expected 'normal' or 'privacy'") which the `_dispatch` generic handler converts to JSON-RPC error.
    - Update `handlers/chat.py.ChatHandlers.on_chat_send`: replace the direct `BACKEND_REGISTRY[backend_name](...)` path from Plan 02-05 with `backend_or_err = await self._router.decide_backend(params.backend, getattr(params, 'user_approved_fallback', False))`. If Error → emit chat/stream done frame with that error and return. Else call backend.send with an on_event wrapper that both notifies UE AND calls router.observe_event. Module-superset discipline (D-24): every Phase 1 line preserved.
    - Update `app.py.build_and_run`: construct Router(BACKEND_REGISTRY, emit_notification_fn); construct ChatHandlers(storage, router, ...); construct SessionModeHandler(router); server.register_request('session/set-mode', session_mode.on_set_mode). Preserve all other lines verbatim.

    Commit: feat(02-06): add session/set-mode handler + wire Router into chat.py
  </action>
  <verify>
    <automated>cd TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest -v 2>&1 | tail -5 | grep -E "passed|failed"</automated>
  </verify>
  <done>
    - session/set-mode handler registered in app.py
    - chat.py dispatches through Router, not direct registry
    - Privacy Mode entry refuses Claude backend; chat/send with backend=claude uses GemmaBackend
    - Full pytest suite green
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| WS inbound → Router | `params.backend` and `params.user_approved_fallback` are user-influenced; must not enable bypass of Privacy Mode or auth-drift gates |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-06-01 | Elevation of Privilege | UE panel sends `user_approved_fallback=true` without user actually clicking | mitigate | Flag is ephemeral per chat/send (not persisted); UE CHAT-02 pill (Plan 02-12) only sets this after explicit click. Router test assertion: without the flag, ClaudeRateLimited refuses Claude AND does NOT fall back. |
| T-02-06-02 | Tampering | session/set-mode spoofed to re-enable Claude in Privacy Mode | mitigate | First-frame auth (Phase 1 D-07) blocks unauthenticated WS clients; only the authenticated UE panel can send the request. Mode transition emits structured log for audit trail (structlog JSON). |
| T-02-06-03 | Denial of Service | Repeated retry-storm on server_error keeps state in ClaudeStreaming forever | mitigate | `attempt < 3` rule caps silent retries at 3; past that, error surfaces but state stays (user may cancel). Bench test validates in Plan 02-14. |
</threat_model>

<verification>
- `cd TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest -v` — ALL passed
- `grep -c "diagnostics/backend-state" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/router.py` ≥ 1 (emit call present)
- `grep -q "session/set-mode" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py` — handler registered
</verification>

<success_criteria>
- Router enforces every transition from RESEARCH §2.2 — no silent mid-stream fallback, no Privacy-Mode bypass
- `diagnostics/backend-state` notification emitted on every transition
- `session/set-mode` handler registered, tested, and gated by auth
- RESEARCH §10.6 false-positive mitigation encoded as explicit test
- Plan 02-12 (status pill) can subscribe to `diagnostics/backend-state` and render
</success_criteria>

<output>
After completion, create `.planning/phases/02-subscription-bridge-ci-matrix/02-06-SUMMARY.md`
</output>
