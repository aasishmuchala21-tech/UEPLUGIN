---
phase: 02-subscription-bridge-ci-matrix
plan: 08
slug: session-super-transaction
type: execute
wave: 2
depends_on: [02]
autonomous: true
tdd: true
requirements: [CHAT-03]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Transactions/FNyraSessionTransaction.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Transactions/FNyraSessionTransaction.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraSupervisor.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraSupervisor.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTransactionsSpec.cpp
research_refs: [§3.1, §3.2, §3.3, §3.4, §3.5, §3.6, §10.4]
context_refs: [D-10, D-11, D-24]
phase0_clearance_required: false
must_haves:
  truths:
    - "FNyraSessionTransaction class exposes Begin(FString SessionSummary), End(), Cancel(); internally manages int32 TransactionIndex (INDEX_NONE when inactive)"
    - "Begin() calls GEditor->BeginTransaction(FText::Format NYRA: {Summary}) only when GEditor && GEditor->Trans; stores returned index"
    - "End() calls GEditor->EndTransaction(); resets TransactionIndex = INDEX_NONE"
    - "Cancel() calls GEditor->CancelTransaction(TransactionIndex) when index != INDEX_NONE; idempotent (safe to call on already-cancelled)"
    - "FNyraSupervisor integration: Begin called on first chat/send of a session (one super-transaction per conversation turn that does any mutation); End on chat/stream done:true without cancelled; Cancel on chat/cancel OR on chat/stream error frame"
    - "NyraEditorModule::ShutdownModule calls SessionTransaction.Cancel() unconditionally (RESEARCH §10.4 hot-reload safety)"
    - "PIE-active gate: FNyraSupervisor refuses to forward chat/send while GEditor->PlayWorld != nullptr; emits error frame with -32014 pie_active"
    - "diagnostics/pie-state UE→NH notification emitted on FEditorDelegates::BeginPIE / EndPIE for router awareness (Plan 02-06 consumes it)"
    - "NyraTransactionsSpec.cpp has three Describe blocks (RESEARCH §11 Wave 0 plan): Nyra.Transactions.SessionScope (Begin/End/Cancel roundtrip on a RF_Transactional UObject), Nyra.Transactions.NestedCoalesce (inner FScopedTransaction under outer BeginTransaction — verify single UTransBuffer entry), Nyra.Transactions.CancelRollback (inner mutation + outer Cancel rolls back)"
  artifacts:
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/Transactions/FNyraSessionTransaction.h
      provides: "Super-transaction boundary RAII helper"
      exports: ["FNyraSessionTransaction"]
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Private/Transactions/FNyraSessionTransaction.cpp
      provides: "Begin/End/Cancel impl guarded on GEditor + Trans"
  key_links:
    - from: FNyraSupervisor chat/send forwarder
      to: FNyraSessionTransaction::Begin
      via: "GameThread dispatch before SendRequest"
      pattern: "SessionTransaction\\.Begin"
    - from: FNyraSupervisor chat/stream final frame handler
      to: FNyraSessionTransaction::End / Cancel
      via: "done:true + !cancelled → End; done:true + cancelled OR error → Cancel"
      pattern: "SessionTransaction\\.End|SessionTransaction\\.Cancel"
    - from: FNyraEditorModule::ShutdownModule
      to: FNyraSessionTransaction::Cancel
      via: "unconditional call before module unload"
      pattern: "SessionTransaction\\.Cancel"
---

<objective>
Ship the session super-transaction pattern: every NYRA session (from first
chat/send through final chat/stream done) is wrapped in one outermost
`BeginTransaction` / `EndTransaction` pair, and all inner `FScopedTransaction`
objects (opened by Phase 4+ tool handlers) coalesce into that one
UTransBuffer entry. Ctrl+Z rolls back the entire session as one atomic unit.

**Phase 2 ships the boundary framework only.** Phase 4+ fills in per-tool
`FScopedTransaction` usage as tools land. This plan proves the boundary
correctly opens, closes, and cancels.

Per CONTEXT.md:
- D-10: manual Begin/End over long-lived FScopedTransaction member (exception safety)
- D-11: all seven session-boundary rules enforced via tests
- D-24: module-superset on NyraEditorModule.cpp + FNyraSupervisor.cpp/.h

Per RESEARCH §3.1 (UTransBuffer nesting semantics verified) and §10.4 (hot-reload safety).

**TDD** on the boundary mechanics (Begin/End/Cancel with a real UTransBuffer via the editor test harness). UE automation-spec tests run on the dev host.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/02-subscription-bridge-ci-matrix/02-CONTEXT.md
@.planning/phases/02-subscription-bridge-ci-matrix/02-RESEARCH.md
@docs/ERROR_CODES.md

<interfaces>
<!-- Existing FNyraSupervisor surface (from Phase 1 Plan 10): -->
<!--   FNyraSupervisor::SpawnAndConnect(), RequestShutdown(), SendRequest<T>(), CancelInflight(req_id) -->
<!--   Phase 1 state: Spawning, WaitingForHandshake, Connecting, Authenticating, Ready, Crashed, Unstable -->
<!-- Phase 2 adds session-transaction hooks on top. -->

<!-- FNyraSessionTransaction public surface: -->
```cpp
class NYRAEDITOR_API FNyraSessionTransaction
{
public:
    void Begin(const FString& SessionSummary);   // opens super-transaction if not already active
    void End();                                   // closes gracefully
    void Cancel();                                // rolls back; idempotent
    bool IsActive() const { return TransactionIndex != INDEX_NONE; }
private:
    int32 TransactionIndex = INDEX_NONE;
};
```

<!-- FNyraSupervisor Phase 2 additions (module-superset on .h + .cpp): -->
<!--   FNyraSessionTransaction SessionTransaction;   // member -->
<!--   bool bPIEActive = false;                      // tracked via FEditorDelegates::BeginPIE/EndPIE -->
<!--   void OnBeginPIE(bool bIsSimulating);          // new delegate handler -->
<!--   void OnEndPIE(bool bIsSimulating); -->
<!--   void OnChatSendForwarding(...) {              // new private helper; called from Panel -->
<!--       if (bPIEActive) { emit error -32014; return; } -->
<!--       if (!SessionTransaction.IsActive()) { SessionTransaction.Begin(TruncSummary); } -->
<!--       SendRequest(chat/send, params); -->
<!--   } -->
<!--   On incoming chat/stream notification with done=true: -->
<!--       if (cancelled || error) SessionTransaction.Cancel(); else SessionTransaction.End(); -->

<!-- NyraEditorModule.cpp (module-superset on Plans 03/04/10/13 content): -->
<!-- ShutdownModule preserves Plan 10's GNyraSupervisor->RequestShutdown() timing AND adds: -->
<!--   if (GNyraSupervisor) { GNyraSupervisor->SessionTransaction.Cancel(); } // hot-reload safety per §10.4 -->

<!-- diagnostics/pie-state notification (docs/JSONRPC.md §4.9 from Plan 02-02): -->
<!--   Method: "diagnostics/pie-state"   direction UE→NH   notification -->
<!--   Params: {active: bool} -->
<!--   UE emits on BeginPIE (active=true) + EndPIE (active=false) -->
<!--   Router uses this in Plan 02-06 to refuse chat/send (redundant with UE-side gate but defense-in-depth) -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1 (RED+GREEN): FNyraSessionTransaction + NyraTransactionsSpec three Describe blocks</name>
  <files>TestProject/Plugins/NYRA/Source/NyraEditor/Public/Transactions/FNyraSessionTransaction.h, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Transactions/FNyraSessionTransaction.cpp, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraTransactionsSpec.cpp</files>
  <behavior>
    Three Describe blocks per RESEARCH §11 Wave 0:

    - Nyra.Transactions.SessionScope:
      - It("Begin followed by End leaves UTransBuffer with one visible transaction") — spawn a transient RF_Transactional UObject, Begin("test"), Target->Modify(), set a field, End(); UTransBuffer::UndoCount == 1 before; GEditor->UndoTransaction(); field reverted.
      - It("Cancel rolls back modifications") — Begin, Target->Modify, set field, Cancel(); field remains at original value; UTransBuffer shows no new transaction entry after.
      - It("End on inactive is no-op") — calling End() without Begin() doesn't crash + returns cleanly.
      - It("Cancel is idempotent") — Begin, Cancel, Cancel — second Cancel is no-op.

    - Nyra.Transactions.NestedCoalesce:
      - It("inner FScopedTransaction coalesces into outer BeginTransaction via refcount") — Begin outer ("session"); { FScopedTransaction Inner("inner"); Target->Modify; set field; } (inner ref count decrements but outer stays); End outer; UndoTransaction reverts field AND counts as ONE undo entry (not two).
      - It("two inner scopes in sequence still coalesce") — Begin outer; { FScopedTransaction A; Target1->Modify; mutate; } { FScopedTransaction B; Target2->Modify; mutate; } End; single UndoTransaction reverts both mutations.

    - Nyra.Transactions.CancelRollback:
      - It("outer Cancel after inner completed rolls back both") — Begin; { FScopedTransaction Inner; Target->Modify; set field; } Cancel; field is at original value.
      - It("outer Cancel is safe after WS disconnect simulated") — Begin; simulate WS drop (invoke Cancel directly without End); no crash, no leak, UTransBuffer consistent.
  </behavior>
  <action>
    RED: commit test(02-08): add failing NyraTransactionsSpec three Describe blocks

    Implementation notes for GREEN (RESEARCH §3.2 pattern):
      - FNyraSessionTransaction.h declares the class per interfaces block.
      - .cpp Begin: `if (!GEditor || !GEditor->Trans) return; const FText Desc = FText::Format(LOCTEXT("NyraSessionFmt", "NYRA: {0}"), FText::FromString(SessionSummary)); TransactionIndex = GEditor->BeginTransaction(Desc);`
      - .cpp End: `if (!GEditor || !GEditor->Trans || TransactionIndex == INDEX_NONE) return; GEditor->EndTransaction(); TransactionIndex = INDEX_NONE;`
      - .cpp Cancel: `if (!GEditor || !GEditor->Trans || TransactionIndex == INDEX_NONE) return; GEditor->CancelTransaction(TransactionIndex); TransactionIndex = INDEX_NONE;`
      - All three methods return early + gracefully when not in editor context (`-game` / commandlet).

    Tests use a transient `UTestNyraObject` UPROPERTY class declared in the spec (RF_Transactional set explicitly to verify the transaction pathway).

    Commit: feat(02-08): add FNyraSessionTransaction with Begin/End/Cancel
  </action>
  <verify>
    <automated>echo "C++ Automation Spec — manual verification on dev host: run 'Automation RunTests Nyra.Transactions' and expect 8+ It blocks pass"</automated>
  </verify>
  <done>
    - NyraTransactionsSpec has three Describe blocks with 8+ It blocks total
    - FNyraSessionTransaction + impl compile cleanly on UE 5.6 dev host
    - All Nyra.Transactions.* tests green in UE Automation runner
    - RED/GREEN commit pair landed
  </done>
</task>

<task type="auto">
  <name>Task 2: Wire FNyraSessionTransaction into FNyraSupervisor + PIE gate + diagnostics/pie-state</name>
  <files>TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraSupervisor.h, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraSupervisor.cpp, TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp</files>
  <action>
    **Module-superset discipline (D-24):** every Phase 1 line in FNyraSupervisor.h/.cpp and NyraEditorModule.cpp is preserved VERBATIM. Phase 2 additions append only.

    FNyraSupervisor.h additions:
      - `#include "Transactions/FNyraSessionTransaction.h"`
      - private member `FNyraSessionTransaction SessionTransaction;`
      - private member `bool bPIEActive = false;`
      - private member `FDelegateHandle BeginPIEHandle, EndPIEHandle;` for FEditorDelegates unregister
      - public `bool IsPIEActive() const { return bPIEActive; }`
      - declare `void OnChatSendForwarded(...)` helper that Panel calls instead of raw SendRequest for chat/send (PIE-aware)
      - declare `void HandleChatStreamFinal(const FNyraJsonRpcEnvelope& Env)` — the completion hook for chat/stream that decides End vs Cancel

    FNyraSupervisor.cpp additions:
      - In constructor (or SpawnAndConnect path after Ready state): register `FEditorDelegates::BeginPIE.AddRaw(this, &FNyraSupervisor::OnBeginPIE)` + EndPIE. On destroy / RequestShutdown: unregister the delegates using the stored handles.
      - `OnBeginPIE(bool bSimulating) { bPIEActive = true; SendNotification("diagnostics/pie-state", {active: true}); }` + `OnEndPIE` inverse.
      - `OnChatSendForwarded`: if (bPIEActive) emit local error -32014 (via a new OnError multicast or an immediate chat/stream error notif handle), return. Else if (!SessionTransaction.IsActive()) SessionTransaction.Begin(TruncateToSummary(UserMessage, 48 chars)); SendRequest(chat/send, params).
      - In the chat/stream notification handler (Phase 1 already wired via broadcast to panel): inspect `done`, `cancelled`, `error`; if done && (cancelled || error.IsSet()) → SessionTransaction.Cancel(); if done && !cancelled && !error → SessionTransaction.End().

    NyraEditorModule.cpp (module-superset on Plan 03/04/10/13 content):
      - ShutdownModule extension: AFTER existing Plan 10 `GNyraSupervisor->RequestShutdown()` and Plan 13 cleanup but BEFORE tab unregister (which is Plan 04's block), add: `if (GNyraSupervisor) { GNyraSupervisor->GetSessionTransaction().Cancel(); }`. Every other line preserved.
      - Add getter `FNyraSessionTransaction& GetSessionTransaction() { return SessionTransaction; }` to FNyraSupervisor.h public surface so the module shutdown path has access.

    Verify that Phase 1 Automation tests (Nyra.Jsonrpc.*, Nyra.Supervisor.RestartPolicy, Nyra.Panel.*) still pass with these additions — module-superset discipline means zero regressions.

    Commit: feat(02-08): wire session super-transaction into FNyraSupervisor + PIE gate + diagnostics/pie-state
  </action>
  <verify>
    <automated>grep -q "FNyraSessionTransaction SessionTransaction" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraSupervisor.h && grep -q "FEditorDelegates::BeginPIE" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraSupervisor.cpp && grep -q "diagnostics/pie-state" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Process/FNyraSupervisor.cpp && grep -q "SessionTransaction.Cancel" TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp</automated>
  </verify>
  <done>
    - FNyraSupervisor owns SessionTransaction + bPIEActive + PIE delegate registrations
    - diagnostics/pie-state notification wired to BeginPIE/EndPIE
    - Chat/send forwarder refuses during PIE (-32014)
    - chat/stream done handler decides End vs Cancel based on frame contents
    - NyraEditorModule::ShutdownModule unconditionally Cancels (hot-reload safety)
    - Phase 1 tests + Plan 02-08 Transactions tests all green
    - Module-superset discipline preserved on NyraEditorModule.cpp + FNyraSupervisor.cpp/.h
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| WS inbound chat/send → UE transaction system | Untrusted params drive mutation scope; PIE gate + pre-validation prevent accidents |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-08-01 | Tampering | Session runs through multiple plugin reloads; UTransBuffer leaks | mitigate | ShutdownModule unconditional Cancel (D-11 + RESEARCH §10.4); test SessionScope It block covers the "hot-reload mid-session" equivalent by calling Cancel without prior End. |
| T-02-08-02 | Denial of Service | Mutation during PIE corrupts runtime world | mitigate | PIE gate rejects chat/send with -32014 at UE-side supervisor BEFORE touching transaction system; diagnostics/pie-state propagates to NyraHost router for defense-in-depth. |
| T-02-08-03 | Repudiation | User cancels mid-stream, UE state partially modified | mitigate | Cancel uses CancelTransaction(Index) which reverts all Modify()'ed objects to pre-transaction state; verified by Nyra.Transactions.CancelRollback It block. |
</threat_model>

<verification>
- `grep -c "UBT" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Transactions/FNyraSessionTransaction.h || true` — no UBT-specific ifdefs (cross-UE-version clean)
- Automation run on dev host: `Automation RunTests Nyra.Transactions` → all It blocks pass
- Automation run on dev host: `Automation RunTests Nyra.Supervisor` → Phase 1 tests still green (regression check)
- Grep confirmations per verify command above
</verification>

<success_criteria>
- FNyraSessionTransaction cleanly wraps UTransBuffer's Begin/End/Cancel with graceful no-ops for non-editor contexts
- Inner FScopedTransaction objects coalesce into the outer per RESEARCH §3.1 verified via NestedCoalesce tests
- PIE gate blocks chat/send with -32014 at UE side; diagnostics/pie-state notifies NyraHost
- Hot-reload safety via unconditional ShutdownModule Cancel
- Module-superset discipline intact (Phase 1 tests still green)
- Phase 4+ tool handlers can now open inner FScopedTransaction under the outer without further wiring
</success_criteria>

<output>
After completion, create `.planning/phases/02-subscription-bridge-ci-matrix/02-08-SUMMARY.md`
</output>
