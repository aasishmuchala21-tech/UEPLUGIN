---
phase: 02-subscription-bridge-ci-matrix
plan: 02
slug: wire-protocol-extension
type: execute
wave: 0
depends_on: []
autonomous: true
tdd: false
requirements: [SUBS-01, SUBS-02, CHAT-02, CHAT-03, CHAT-04, ACT-06, ACT-07]
files_modified:
  - docs/JSONRPC.md
  - docs/ERROR_CODES.md
research_refs: [§1.6, §2.3, §4.3, §7.4, §8.5, §9.2, §12]
context_refs: [D-03, D-05, D-06, D-09, D-23, D-24]
phase0_clearance_required: false
must_haves:
  truths:
    - "docs/JSONRPC.md Phase 1 content preserved verbatim (§1 Envelopes, §2 Id policy, §3.1–3.7 Phase 1 method surface untouched)"
    - "New §4 'Phase 2 Additions' section appends nine new methods: chat/send backend=claude extension, session/set-mode, plan/preview, plan/decision, console/exec, log/tail, log/message-log-list, diagnostics/backend-state, diagnostics/pie-state, claude/auth-status"
    - "Every new method specifies direction (UE→NH or NH→UE), kind (request vs notification), exact params shape, exact result shape (for requests), and at least one worked JSON example"
    - "docs/ERROR_CODES.md Phase 1 codes -32001..-32006 preserved verbatim; appends -32007 claude_not_installed, -32008 claude_auth_drift, -32009 claude_rate_limited, -32010 privacy_mode_egress_blocked, -32011 plan_rejected, -32012 console_command_blocked, -32013 transaction_already_active, -32014 pie_active with remediation templates"
  artifacts:
    - path: docs/JSONRPC.md
      provides: "Wire protocol spec — Phase 1 + Phase 2 additive superset"
      contains: "### 4.1 chat/send params extension, ### 4.2 session/set-mode, ### 4.3 plan/preview, ### 4.4 plan/decision, ### 4.5 console/exec, ### 4.6 log/tail, ### 4.7 log/message-log-list, ### 4.8 diagnostics/backend-state, ### 4.9 diagnostics/pie-state, ### 4.10 claude/auth-status"
    - path: docs/ERROR_CODES.md
      provides: "Error code catalog — Phase 1 + Phase 2 additive superset"
      contains: "-32001.*-32002.*-32003.*-32004.*-32005.*-32006.*-32007.*-32008.*-32009.*-32010.*-32011.*-32012.*-32013.*-32014"
  key_links:
    - from: "Every Phase 2 Python plan that calls server.register_request(...)"
      to: "docs/JSONRPC.md §4.x"
      via: "Method name literal match"
      pattern: "console/exec|log/tail|plan/preview|plan/decision|session/set-mode"
    - from: "Every Phase 2 C++ plan that issues a JSON-RPC request or notification"
      to: "docs/JSONRPC.md §4.x"
      via: "FNyraWsClient::SendRequest / SendNotification method-name literal"
      pattern: "diagnostics/backend-state|diagnostics/pie-state|plan/decision"
---

<objective>
Phase 2's wire-protocol contract: nine new JSON-RPC methods + eight new error codes appended to the Phase 1 docs. **This plan is the source of truth every other Phase 2 plan cites by reference.** Plan 02-04 (Claude driver), Plan 02-05 (router), Plan 02-07 (super-transaction), Plan 02-08 (permission gate), Plan 02-09 (console exec), Plan 02-10 (log tail), and Plan 02-12 (status pill) all implement against these specs. Landing the docs in Wave 0 prevents every downstream plan from arguing over wire shapes.

Per CONTEXT.md:
- D-03: router state machine states map 1:1 to `diagnostics/backend-state.params.claude.state` enum
- D-05: Privacy Mode needs `session/set-mode` wire method
- D-06: `--permission-prompt-tool nyra_permission_gate` path B = `plan/preview` + `plan/decision`
- D-09: `plan/decision` carries approve/reject/edit verdict
- D-23: ADDITIVE only — every Phase 1 envelope / method / error code stays verbatim
- D-24: module-superset discipline — the edit preserves Phase 1 content line-for-line

Matches RESEARCH §12 one-for-one. This is a documentation-only plan;
no code ships. Compilation / wire conformance verified when the next
plans consume these specs.
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
<!-- Phase 1's JSONRPC.md current structure (do not rewrite): -->
<!--   §1 Envelopes (Request, Success response, Error response, Notification) -->
<!--   §2 Id policy (P1.7 monotonic FAtomicInt64) -->
<!--   §3 Method surface (Phase 1): §3.1 session/authenticate, §3.2 session/hello, §3.3 chat/send, §3.4 chat/stream, §3.5 chat/cancel, §3.6 shutdown, §3.7 diagnostics/download-progress -->

<!-- Phase 2 additions land as new §4 "Phase 2 Additions" section AFTER Phase 1 §3, preserving §1/§2/§3 verbatim. -->

<!-- New method catalog (from RESEARCH §12): -->
<!--   §4.1 chat/send.params.backend += "claude" (additive enum extension) -->
<!--   §4.2 session/set-mode   UE→NH req   {mode: "normal"|"privacy"} -->
<!--   §4.3 plan/preview       NH→UE notif {conversation_id, req_id, preview_id, summary, steps[{tool,args,rationale,risk}], estimated_duration_seconds, affects_files} -->
<!--   §4.4 plan/decision      UE→NH req   {preview_id, decision: "approve"|"reject"|"edit", edited_plan?, auto_approve_read_only_this_session: bool} → resp {acknowledged: bool} -->
<!--   §4.5 console/exec       NH→UE req   {command, rationale} → resp {stdout, tier: "A"|"B", exit_status: "ok"|"blocked"} -->
<!--   §4.6 log/tail           NH→UE req   {categories?, min_verbosity?, since_ts?, max_entries: int ≤200, regex?} → resp {entries[{ts,category,verbosity,message}], truncated, last_ts} -->
<!--   §4.7 log/message-log-list NH→UE req {listing_name, since_index?, max_entries ≤200} → resp {entries[{index, severity, message, token_refs}], total} -->
<!--   §4.8 diagnostics/backend-state NH→UE notif {claude:{installed,version,auth,state,rate_limit_resets_at?}, gemma:{model_present,runtime,state}, computer_use:{state}, mode, updated_at} -->
<!--   §4.9 diagnostics/pie-state     UE→NH notif {active: bool}   (so router can refuse chat/send while PIE running — RESEARCH Open Q #5) -->
<!--   §4.10 claude/auth-status       NH→UE notif {installed, auth, tier?, remediation_hint?} (fine-grained for first-run wizard) -->

<!-- Phase 1 ERROR_CODES.md current list: -32001 subprocess_failed, -32002 auth, -32003 rate_limit (placeholder), -32004 model_not_loaded, -32005 gemma_not_installed, -32006 infer_oom -->
<!-- Phase 2 appends -32007..-32014 per RESEARCH §12: -->
<!--   -32007 claude_not_installed — "Claude Code CLI not found. Install from code.claude.com." -->
<!--   -32008 claude_auth_drift — "Claude session expired. Run `claude auth login` in a terminal." -->
<!--   -32009 claude_rate_limited — "Claude rate-limited. Resume at {time}, or switch to local Gemma ([Switch])." -->
<!--     [PROMOTES Phase 1's -32003 placeholder — Phase 1 -32003 now retained as alias for generic rate-limit; Phase 2 usage directs Claude-specific rate-limit through -32009.] -->
<!--   -32010 privacy_mode_egress_blocked — "This action requires internet access. Exit Privacy Mode to continue." -->
<!--   -32011 plan_rejected — "Plan rejected by user." -->
<!--   -32012 console_command_blocked — "Console command '{cmd}' is not in the safe-mode whitelist." -->
<!--   -32013 transaction_already_active — "Another NYRA session is already running. End it before starting a new one." -->
<!--   -32014 pie_active — "NYRA cannot mutate while Play-In-Editor is running. Stop PIE and retry." -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Extend docs/JSONRPC.md with Phase 2 §4 additions</name>
  <files>docs/JSONRPC.md</files>
  <action>
    READ the current docs/JSONRPC.md in full first to confirm the Phase 1 structure (§1–§3) is intact. This edit is ADDITIVE-ONLY.

    Append a new top-level section §4 "Phase 2 Additions" AFTER Phase 1's §3. Do NOT edit §1, §2, or §3 beyond a single header-link update (if an index exists) to include §4.

    For each new method, include:
    - Method name + direction (UE→NH or NH→UE) + kind (request vs notification)
    - JSON worked example (both request frame and, if request, the response frame; for notifications, just the frame)
    - Params schema in prose + table of fields (name, type, required?, description)
    - Cross-references back to the RESEARCH section + CONTEXT.md D-XX that locks each decision
    - Error-code expectations (e.g., plan/decision replies -32011 plan_rejected if decision='reject')

    The nine new subsections are:
    - §4.1 chat/send.params.backend extension — document that `backend` now accepts `"claude"` (in addition to `"gemma-local"` from Phase 1 D-10). Phase 1 examples stay valid.
    - §4.2 session/set-mode — UE→NH request, {mode: "normal" | "privacy"} → {mode_applied: bool}. Privacy Mode semantics from CONTEXT.md D-05.
    - §4.3 plan/preview — NH→UE notification emitting structured plan. Schema fields locked from RESEARCH §4.3. Include the worked "golden-hour" example from RESEARCH.
    - §4.4 plan/decision — UE→NH request carrying approve/reject/edit + auto-approve-read-only toggle. Response echoes acknowledged:true. If decision=reject, NH surfaces -32011 plan_rejected back to Claude as the tool result.
    - §4.5 console/exec — NH→UE request; NyraHost sends this after classifying the agent's nyra_console_exec MCP call as Tier A or Tier B-approved. Response carries captured output + tier + exit_status. Tier C rejected without a wire call (NyraHost returns -32012 directly in the MCP tool result).
    - §4.6 log/tail — NH→UE request. Parameters locked per RESEARCH §8.5. max_entries hard-capped at 200; server returns truncated:true if more entries match.
    - §4.7 log/message-log-list — NH→UE request for Message Log tailed entries. Token refs are opaque string ids UE resolves into navigation actions later (Phase 4+).
    - §4.8 diagnostics/backend-state — NH→UE notification emitted on every router state transition. Schema locked per RESEARCH §9.2. `claude.state` enum: ready | rate-limited | auth-drift | offline. `gemma.state` enum: ready | downloading | loading | not-installed. `mode` enum: normal | privacy-mode.
    - §4.9 diagnostics/pie-state — UE→NH notification fired when PIE starts/stops. NyraHost router refuses chat/send while active:true (→ -32014 pie_active).
    - §4.10 claude/auth-status — NH→UE notification emitted on startup + every 5-minute TTL refresh + on each router transition into/out of AuthDrift.

    At the end of §4, add a short "Change Log" subsection noting: "Phase 2 (D-23): additions only. Phase 1 §1–§3 preserved verbatim."
  </action>
  <verify>
    <automated>python3 -c "import re; t=open('docs/JSONRPC.md').read(); phase1_markers=['session/authenticate','session/hello','chat/send','chat/stream','chat/cancel','shutdown','diagnostics/download-progress']; phase2_markers=['session/set-mode','plan/preview','plan/decision','console/exec','log/tail','log/message-log-list','diagnostics/backend-state','diagnostics/pie-state','claude/auth-status']; missing=[m for m in phase1_markers+phase2_markers if m not in t]; print('MISSING:', missing) if missing else print('OK')"</automated>
  </verify>
  <done>
    - Phase 1 §1/§2/§3 preserved verbatim (grep-verifiable)
    - New §4 section contains all 9 new methods with schemas + examples
    - Every method cross-references RESEARCH.md section + CONTEXT.md D-XX
  </done>
</task>

<task type="auto">
  <name>Task 2: Extend docs/ERROR_CODES.md with Phase 2 codes -32007..-32014</name>
  <files>docs/ERROR_CODES.md</files>
  <action>
    READ docs/ERROR_CODES.md to confirm Phase 1 codes -32001..-32006 are present. Preserve them VERBATIM.

    Append a new section "## Phase 2 Additions (D-23)" after the Phase 1 code table. Include eight rows in the same table format as Phase 1:

    | Code | Name | When emitted | Remediation template |
    |------|------|--------------|----------------------|
    | -32007 | claude_not_installed | NyraHost boot `which claude` / `where claude` fails | "Claude Code CLI not found. Install from code.claude.com." |
    | -32008 | claude_auth_drift | `claude auth status` exits 1 mid-session OR system/api_retry error=authentication_failed seen | "Claude session expired. Run `claude auth login` in a terminal." |
    | -32009 | claude_rate_limited | system/api_retry error=rate_limit exhausted attempts. Supersedes Phase 1's -32003 placeholder for Claude-specific cases; -32003 retained as generic. | "Claude rate-limited. Resume at {time}, or switch to local Gemma ([Switch])." |
    | -32010 | privacy_mode_egress_blocked | Router in Privacy Mode; agent/user attempts action requiring network egress | "This action requires internet access. Exit Privacy Mode to continue." |
    | -32011 | plan_rejected | User clicked Reject in plan/preview card | "Plan rejected by user." |
    | -32012 | console_command_blocked | Tier C console command OR unmapped command submitted via nyra_console_exec | "Console command '{cmd}' is not in the safe-mode whitelist." |
    | -32013 | transaction_already_active | Another NYRA session active (plugin hot-reload corner case) | "Another NYRA session is already running. End it before starting a new one." |
    | -32014 | pie_active | chat/send received while PIE active | "NYRA cannot mutate while Play-In-Editor is running. Stop PIE and retry." |

    Add a short paragraph note under the table clarifying the -32003 / -32009 relationship: Phase 1 -32003 remains a generic rate-limit code (Gemma/Ollama backend could still emit it); Phase 2 -32009 is Claude-specific and carries the rate_limit_resets_at timestamp. Both populate error.data.remediation.

    End the section with a "Usage by Phase 2 plan" matrix listing which plan issues each code:
    - 02-04 (Claude driver): -32007, -32008, -32009
    - 02-05 (Router): -32010
    - 02-08 (Permission gate): -32011
    - 02-09 (Console exec): -32012
    - 02-07 (Super-transaction): -32013, -32014
  </action>
  <verify>
    <automated>python3 -c "t=open('docs/ERROR_CODES.md').read(); phase1=['-32001','-32002','-32003','-32004','-32005','-32006']; phase2=['-32007','-32008','-32009','-32010','-32011','-32012','-32013','-32014']; missing=[c for c in phase1+phase2 if c not in t]; print('MISSING:', missing) if missing else print('OK')"</automated>
  </verify>
  <done>
    - Phase 1 codes -32001..-32006 preserved verbatim
    - Phase 2 codes -32007..-32014 appended with remediation templates
    - Usage matrix maps each new code to the plan that owns it
    - -32003/-32009 relationship documented
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

No new trust boundaries. This plan is documentation-only.

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-02-01 | Tampering | Phase 1 wire content rewritten by mistake | mitigate | Additive-only rule (D-23 / D-24); grep-based verify in Task 1/2 confirms all Phase 1 markers survive |
| T-02-02-02 | Information Disclosure | plan/preview `args` may leak PII / filesystem paths into logs | accept for spec layer | Structured logging redaction is Plan 02-05 router concern; spec just documents field shapes |
</threat_model>

<verification>
- `grep -q "session/authenticate" docs/JSONRPC.md && grep -q "session/set-mode" docs/JSONRPC.md` — both present (Phase 1 + Phase 2)
- `grep -c "^| -320" docs/ERROR_CODES.md` ≥ 14 (six Phase 1 + eight Phase 2)
- `grep -q "## Phase 2 Additions" docs/ERROR_CODES.md` — section header present
</verification>

<success_criteria>
- Both docs are pure supersets of their Phase 1 forms (zero Phase 1 lines deleted or renumbered)
- All nine Phase 2 methods documented with worked JSON examples + field schemas
- All eight Phase 2 error codes documented with remediation templates
- Usage matrix attributes each new code to its owning plan
- Downstream plans (02-04, 02-05, 02-07, 02-08, 02-09, 02-10, 02-12) can cite these docs for wire-conformance tests
</success_criteria>

<output>
After completion, create `.planning/phases/02-subscription-bridge-ci-matrix/02-02-SUMMARY.md`
</output>
