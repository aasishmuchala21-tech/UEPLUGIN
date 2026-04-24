---
phase: 02-subscription-bridge-ci-matrix
plan: 09
slug: safe-mode-permission-gate
type: execute
wave: 2
depends_on: [02, 03, 05, 06]
autonomous: true
tdd: true
requirements: [CHAT-04]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/__init__.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/__main__.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/permission_gate.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/preview.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_permission_gate.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_preview_handler.py
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraPreviewCard.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraPreviewCard.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPreviewSpec.cpp
research_refs: [§1.6, §4.1, §4.2, §4.3, §4.4, §4.5, §4.6]
context_refs: [D-06, D-07, D-08, D-09, D-23, D-24]
phase0_clearance_required: true
must_haves:
  truths:
    - "nyrahost.mcp_server package exposes a stdio MCP server entry-point invokable as `python -m nyrahost.mcp_server --handshake-file <path>`; connects BACK to NyraHost's WebSocket via the handshake file (per RESEARCH §1.6)"
    - "nyra_permission_gate MCP tool registered with schema from RESEARCH §4.2 exactly (summary, steps[{tool,args,rationale,risk}], estimated_duration_seconds, affects_files; risk enum read-only|reversible|destructive|irreversible)"
    - "handlers/preview.py.PreviewHandler maintains a dict[preview_id, asyncio.Future[decision]]; on nyra_permission_gate tool call, emits plan/preview notification, awaits plan/decision request from UE (future resolves), returns decision to Claude as the tool result"
    - "Partial JSON buffering per D-08: input_json_delta fragments from stream parser are buffered until content_block_stop; only the COMPLETE JSON is emitted as plan/preview (prevents UE panel re-render loops)"
    - "plan/decision handler validates decision enum (approve|reject|edit), looks up preview_id, resolves the future; reject → returns -32011 plan_rejected to Claude via tool_result"
    - "Auto-approve-read-only-this-session flag persists in SessionState for current session only; read-only steps fast-path the preview card when flag is set"
    - "SNyraPreviewCard Slate widget renders: summary, expandable step list (tool, rationale, risk pill color-coded, args JSON collapsed), [Approve] [Reject] [Edit] buttons (v1: Edit raises 'not implemented' toast — UI polish is v1.1 per CONTEXT.md deferred list), auto-approve-read-only checkbox"
    - "SNyraChatPanel mounts SNyraPreviewCard in a new overlay slot between banner and message list; handler bindings forward user clicks as plan/decision requests"
    - "NyraPreviewSpec.cpp tests: renders-on-plan-preview, approve-click-sends-decision, reject-click-sends-decision-with-reject-reason, auto-approve-bypass for read-only"
    - "Python tests cover: schema validation (reject missing fields), partial-JSON buffering emits once at stop, plan/decision resolves future, plan_rejected error code flow"
  artifacts:
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/__init__.py
      provides: "Stdio MCP server package exposing NYRA tools; Phase 2 registers only nyra_permission_gate (console + log-tail land in Plans 02-10 + 02-11)"
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/preview.py
      provides: "preview_id tracking + plan/decision resolver"
      exports: ["PreviewHandler"]
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraPreviewCard.h
      provides: "Slate preview card widget"
      exports: ["SNyraPreviewCard"]
  key_links:
    - from: Claude CLI via --permission-prompt-tool
      to: nyra_permission_gate MCP tool (stdio)
      via: "MCP server registered via --mcp-config file (Plan 02-05 writer)"
      pattern: "nyra_permission_gate"
    - from: nyra_permission_gate tool call
      to: plan/preview notification (NH → UE)
      via: "PreviewHandler emits + awaits plan/decision response"
      pattern: "plan/preview"
    - from: SNyraPreviewCard [Approve]/[Reject]
      to: plan/decision request (UE → NH)
      via: "FNyraWsClient::SendRequest"
      pattern: "plan/decision"
---

<objective>
Ship the safe-mode / dry-run plan-first preview gate end-to-end. When Claude issues ANY destructive MCP tool call, the `--permission-prompt-tool nyra_permission_gate` flag (from Plan 02-05's driver) routes the plan through NyraHost's stdio MCP server to the UE Slate panel, where the user sees a structured preview card and clicks Approve / Reject / Edit.

This is the **trust-through-transparency** competitive differentiator (ROADMAP Phase 2 SC#3): NYRA ships plan-first-by-default on day one of actions, beating CoPilot's opt-in preview and Aura's execute-then-plan pattern.

Per CONTEXT.md:
- D-06: Path B is canonical (`--permission-prompt-tool`), not `--permission-mode plan`
- D-07: plan-first-by-default cannot be disabled in v1
- D-08: partial JSON buffering rule
- D-09: plan/preview + plan/decision wire contract
- D-23: wire extensions already documented in Plan 02-02
- D-24: module-superset on SNyraChatPanel.cpp + app.py

**phase0_clearance_required: true** — Permission-gate plumbing is planning-safe + tests pass with mocks; live execution happens after Phase 0 clearance.

**TDD** on the Python side (schema validation, future resolution, partial buffering). UE Slate widget side uses Automation Spec with mocked WS.
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
<!-- nyra_permission_gate schema (RESEARCH §4.2 — LOCKED): -->
```json
{
  "name": "nyra_permission_gate",
  "description": "Request user approval for a planned sequence of UE mutations. MUST be called before any destructive tool (spawn_actor, edit_blueprint, modify_material, delete_*).",
  "inputSchema": {
    "type": "object",
    "required": ["summary", "steps"],
    "properties": {
      "summary": {"type": "string"},
      "steps": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["tool", "args", "rationale"],
          "properties": {
            "tool": {"type": "string"},
            "args": {"type": "object"},
            "rationale": {"type": "string"},
            "risk": {"type": "string", "enum": ["read-only","reversible","destructive","irreversible"]}
          }
        }
      },
      "estimated_duration_seconds": {"type": "number"},
      "affects_files": {"type": "array", "items": {"type": "string"}}
    }
  }
}
```

<!-- PreviewHandler flow: -->
<!--   1. MCP tool handler receives nyra_permission_gate call; validates against schema -->
<!--   2. Generates preview_id = uuid.uuid4() -->
<!--   3. Creates asyncio.Future() for this preview_id -->
<!--   4. Emits plan/preview notification over WS (conversation_id + req_id + preview_id + schema-validated plan) -->
<!--   5. awaits future.result()  — resolved when plan/decision arrives -->
<!--   6. Returns decision to Claude as the MCP tool_result: -->
<!--      - approve  → returns {"approved": true, "auto_approve_read_only_this_session": bool} — Claude proceeds -->
<!--      - reject   → returns error { code: -32011, message: "plan rejected by user", remediation: ... } — Claude sees and adapts -->
<!--      - edit     → returns {"approved": true, "edited_plan": {...}} — Claude uses edited plan (v1: edited_plan equals original; UI-editable deferred) -->

<!-- Partial JSON buffering (D-08 + RESEARCH §4.4): -->
<!--   Plan 02-05's StreamParser emits tool-use partials as they arrive. -->
<!--   PreviewHandler keeps a per-tool-id buffer; only on content_block_stop does it parse the complete JSON + emit plan/preview. -->
<!--   Prevents UE panel from re-rendering mid-build. -->

<!-- Auto-approve read-only flag: -->
<!--   When user clicks Approve with the checkbox set, subsequent read-only steps in THIS session fast-path: -->
<!--     if step.risk == 'read-only' AND session.auto_approve_read_only: emit plan/preview BUT resolve future immediately with approve (card shown informationally, user can still Reject during the short display window — OR implement as 'silent skip' per UX preference; v1 = short display window for user awareness, ~1 second). -->

<!-- SNyraPreviewCard Slate composition: -->
<!--   SBorder -> SVerticalBox { -->
<!--     SHeader { summary STextBlock (large), risk-summary pill row } -->
<!--     SExpandableArea { step list — SListView<FPreviewStep> } -->
<!--     SHorizontalBox { -->
<!--       [Approve] SButton (emits plan/decision approve) -->
<!--       [Reject] SButton (emits plan/decision reject) -->
<!--       [Edit] SButton (v1: shows toast "Plan edit lands in v1.1") -->
<!--       SCheckBox "Auto-approve read-only this session" -->
<!--     } -->
<!--   } -->
<!-- Mounted in SNyraChatPanel via SOverlay between banner and message list (module-superset discipline on SNyraChatPanel). -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1 (RED+GREEN): Stdio MCP server bootstrap + nyra_permission_gate tool + PreviewHandler</name>
  <files>TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/__init__.py, TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/__main__.py, TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/permission_gate.py, TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/preview.py, TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py, TestProject/Plugins/NYRA/Source/NyraHost/tests/test_permission_gate.py, TestProject/Plugins/NYRA/Source/NyraHost/tests/test_preview_handler.py</files>
  <behavior>
    test_permission_gate.py:
    - test_schema_valid_minimal — minimal valid plan (summary + 1 step with tool/args/rationale) passes validation
    - test_schema_rejects_missing_summary — missing summary raises ValueError
    - test_schema_rejects_invalid_risk — risk='super-dangerous' raises
    - test_schema_accepts_all_four_risks — read-only / reversible / destructive / irreversible all accepted
    - test_mcp_server_registers_nyra_permission_gate — module-level MCP server object has the tool registered at module import

    test_preview_handler.py:
    - test_emit_plan_preview_with_uuid — on tool call, handler creates preview_id, emits plan/preview notification
    - test_await_decision_resolves_future — inbound plan/decision with approve resolves future with approve
    - test_reject_returns_plan_rejected_error_code — inbound plan/decision with reject triggers return of -32011 to Claude
    - test_unknown_preview_id_plan_decision_errors — inbound plan/decision with unknown id raises (logged + ignored, future never resolves — prevents stale id confusion)
    - test_partial_json_buffering — accumulated input_json_delta fragments emit plan/preview only on content_block_stop (NOT on each fragment)
    - test_auto_approve_read_only_flag_persists_in_session — SessionState.auto_approve_read_only defaults False; approving with checkbox sets True for the session
    - test_read_only_step_fastpath_when_flag_set — with flag True, read-only step auto-resolves; other risks still gate
  </behavior>
  <action>
    RED: commit test(02-09): add failing permission-gate + preview-handler tests

    GREEN:

    1. Create `nyrahost/mcp_server/` package:
       - `__init__.py` exposes `create_server()` factory returning a configured `mcp.Server` instance (uses the `mcp` PyPI package already pinned in Phase 1 D-15)
       - `__main__.py` parses --handshake-file, loads handshake, opens a stdio MCP server loop; on nyra_permission_gate call, forwards to the parent NyraHost via WebSocket (NOT a new connection — uses the handshake file to grab the token + port and connects as an internal client). Simpler v1: the MCP server process shares nyrahost's Python import path and calls into PreviewHandler via an IPC channel — design option. **For Phase 2, implement the simpler pattern: MCP stdio server forwards the tool call payload back to NyraHost via a dedicated internal WS connection using the handshake auth.**
       - `permission_gate.py` defines the JSON schema + the tool handler registered with the MCP server

    2. Create `nyrahost/handlers/preview.py` `PreviewHandler`:
       - Tracks `self._pending: dict[str, asyncio.Future[dict]]`
       - `async def begin_preview(plan: dict) -> dict` — generates preview_id, creates future, emits plan/preview notification via injected emit_notification callable, awaits future
       - `async def on_plan_decision(params)` — registered as server.register_request; validates decision enum, looks up preview_id, sets future result (or future exception for reject)
       - Auto-approve-read-only fast-path: before emitting plan/preview, inspect `plan.steps`; if all steps have risk='read-only' AND SessionState.auto_approve_read_only, resolve future immediately with approve (skip the notification — UI not pestered). If mixed-risk, always surface the card.

    3. Partial-JSON buffering: Plan 02-05's StreamParser currently emits each input_json_delta as a ToolUse event. **Update** Plan 02-05's emission so that for tool name == 'nyra_permission_gate' specifically, fragments accumulate and only emit on content_block_stop with `is_final=True`. Router (or PreviewHandler — simpler) reads only `is_final=True` events for this specific tool. Preserves the general-purpose partials for other tools (when Phase 3+ tools land).

    4. Wire app.py: instantiate PreviewHandler with emit_notification; server.register_request("plan/decision", preview_handler.on_plan_decision); SessionModeHandler unchanged. **Module-superset discipline on app.py (D-24)** — new lines inserted after router wiring, before server.serve_forever().

    Commit: feat(02-09): add MCP stdio server + nyra_permission_gate + plan/preview + plan/decision handlers
  </action>
  <verify>
    <automated>cd TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest tests/test_permission_gate.py tests/test_preview_handler.py -v 2>&1 | tail -5 | grep -E "passed|failed"</automated>
  </verify>
  <done>
    - nyrahost.mcp_server package invokable as `python -m nyrahost.mcp_server`
    - nyra_permission_gate tool schema validated; MCP server registers it
    - PreviewHandler tracks previews + resolves on plan/decision
    - Partial JSON buffering emits plan/preview only on content_block_stop
    - Auto-approve-read-only fast-path works when flag set
    - Full pytest suite green
  </done>
</task>

<task type="auto">
  <name>Task 2: SNyraPreviewCard Slate widget + mount in SNyraChatPanel + NyraPreviewSpec</name>
  <files>TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraPreviewCard.h, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraPreviewCard.cpp, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPreviewSpec.cpp</files>
  <action>
    Create SNyraPreviewCard widget per interfaces composition. Key specifics:
    - FPreviewStep model struct: Tool, Args (FString JSON — collapsed by default via SExpandableArea), Rationale, Risk enum
    - Risk pill color: read-only=grey, reversible=green, destructive=yellow, irreversible=red; use FSlateColor from NYRA theme (extend Phase 1 palette if needed)
    - OnApproveClicked delegate: fires with the SNyraPreviewCard's current plan + the checkbox's bIsAutoApproveReadOnly state
    - OnRejectClicked delegate: fires with no payload (reject is terminal)
    - OnEditClicked delegate: v1 pops a toast "Plan editing lands in v1.1" via SNotificationList; delegate still fires so tests can bind to it
    - SNyraPreviewCard.SetPlan(const FNyraPlanPreview& Plan) — populates summary + rebuilds step list; triggers SetVisibility(Visible)
    - SNyraPreviewCard.Clear() — SetVisibility(Collapsed) + empty state

    Mount in SNyraChatPanel:
    - **Module-superset on SNyraChatPanel.cpp/.h (D-24):** every Phase 1 (Plans 12/12b/13) line preserved verbatim
    - Add new SOverlay slot between the existing banner and message list
    - On chat/stream notification carrying a plan/preview params (dispatched via router-notification handler in Plan 02-05/06 — panel adds a new HandleNotification branch): parse params, call PreviewCard.SetPlan(...)
    - On OnApproveClicked: Supervisor.SendRequest("plan/decision", {preview_id, decision:"approve", auto_approve_read_only_this_session:bool})
    - On OnRejectClicked: Supervisor.SendRequest("plan/decision", {preview_id, decision:"reject"})
    - On successful response, Clear()

    NyraPreviewSpec.cpp:
    - Nyra.Preview.Render — SetPlan with a 2-step plan renders 2 list items + correct risk pill colors + summary text
    - Nyra.Preview.ApproveFlow — simulate click on Approve → captures a mocked plan/decision request with decision='approve' and the checkbox flag
    - Nyra.Preview.RejectFlow — click on Reject → captures decision='reject'
    - Nyra.Preview.AutoApproveReadOnly — checkbox toggles bAutoApproveReadOnly flag on OnApprove callback payload

    Commit: feat(02-09): add SNyraPreviewCard Slate widget + mount in chat panel + preview spec
  </action>
  <verify>
    <automated>test -f TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraPreviewCard.h &amp;&amp; test -f TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPreviewSpec.cpp &amp;&amp; grep -q "plan/decision" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp</automated>
  </verify>
  <done>
    - SNyraPreviewCard renders summary + step list + risk pills + Approve/Reject/Edit + auto-approve checkbox
    - Mounted in SNyraChatPanel via SOverlay between banner and message list
    - plan/preview notification handler + plan/decision send path wired
    - NyraPreviewSpec has 4 It blocks covering render + approve + reject + auto-approve
    - Module-superset on SNyraChatPanel preserved
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Claude CLI ↔ NYRA MCP stdio server | Untrusted tool-call payload from Claude — NyraHost validates against JSON schema before surfacing to UE |
| UE Slate panel ↔ NyraHost WS | plan/decision carries trusted user intent; must match a real preview_id |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-09-01 | Tampering | Attacker crafts fake plan/decision with approve to bypass user | mitigate | plan/decision requires first-frame auth token (Phase 1 D-07); preview_id is a UUID matched against in-memory pending dict — unknown ids are logged and ignored. |
| T-02-09-02 | Elevation of Privilege | Claude skips nyra_permission_gate and calls destructive tool directly | mitigate | `--permission-mode dontAsk` + allowedTools whitelist cap direct calls; NyraHost MCP server rejects any destructive tool invocation not preceded by a permission_gate approval (server-side enforcement). Open Q #2 — Wave 0 test suite validates empirically; if gaps found, add server-side enforcement layer. |
| T-02-09-03 | Information Disclosure | plan/preview args contain sensitive paths | accept | User sees args in plain text; this is the POINT of plan-first transparency. Structured logs redact nothing — user-visible content is already surface. |
</threat_model>

<verification>
- `cd TestProject/Plugins/NYRA/Source/NyraHost &amp;&amp; python -m pytest -v` — all passed
- `grep -q "nyra_permission_gate" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/permission_gate.py` — tool registered
- Automation run: `Automation RunTests Nyra.Preview` — 4+ It blocks pass
- Live execution gated on phase0_clearance_required
</verification>

<success_criteria>
- `--permission-prompt-tool nyra_permission_gate` wiring complete from Claude CLI → MCP stdio → NyraHost → UE panel → user → back to Claude
- Schema validation rejects malformed plans before UI surfaces them
- Partial JSON buffering prevents mid-build re-render
- Auto-approve-read-only fast-path preserves UX fluidity for knowledge queries
- Reject → -32011 error flows correctly back to Claude
- Plan-first-by-default cannot be silently disabled (no UI toggle removes the gate)
</success_criteria>

<output>
After completion, create `.planning/phases/02-subscription-bridge-ci-matrix/02-09-SUMMARY.md`
</output>
