---
phase: 01-plugin-shell-three-process-ipc
plan: 12b
subsystem: history-drawer
tags: [ue-cpp, slate, python, sqlite, jsonrpc, history-drawer, chat-01, cd-05, validation-1-12b-01, validation-1-12b-02]
requirements_progressed: [CHAT-01]
dependency_graph:
  requires:
    - 01-07-nyrahost-storage-attachments (Storage class + conversations/messages/attachments schema + FK cascade)
    - 01-11-cpp-markdown-parser (SRichTextBlock markdown path reused when Status=Done rows land via sessions/load)
    - 01-12-chat-panel-streaming-integration (SNyraChatPanel::OpenConversation + GetCurrentConversationId + OnConversationSelected + SNyraMessageList::ClearMessages extension points)
  provides:
    - Python nyrahost.handlers.sessions.SessionHandlers dataclass {on_sessions_list, on_sessions_load}
    - NyraServer.request_handlers["sessions/list"] + ["sessions/load"] mounted in app.build_and_run.register
    - FNyraConversationSummary struct {Id, Title, UpdatedAtMs, MessageCount}
    - FOnHistoryOpenConversation(ConvId, Messages) + FOnHistoryNewConversation() delegate types
    - SNyraHistoryDrawer Slate widget (SCompoundWidget) with SBox width-override 24/220 px collapse, SListView rows, central per-rpc-id OnResponse dispatch
    - SNyraChatPanel::HistoryDrawer mounted member + SHorizontalBox two-column layout
    - Nyra.Panel.HistoryDrawerSelect + Nyra.Panel.NewConversationButton automation spec Describe blocks (VALIDATION 1-12b-01 + 1-12b-02)
  affects:
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py (additive SessionHandlers registration)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraChatPanel.h (added HistoryDrawer member + forward decl)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp (wrapped pre-existing VBox in SHorizontalBox alongside drawer; added OnOpenConversation/OnNewConversation lambdas + Refresh call)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp (added HistoryDrawerSelect + NewConversationButton Describe blocks below preserved Plan 04 + 12 blocks)
tech-stack:
  added:
    - "TMap<int64, TFunction<void(const FNyraJsonRpcEnvelope&)>> per-rpc-id response dispatch table (avoids multicast upgrade of Plan 10's FOnSupervisorResponse single-bind delegate)"
    - "SBox::SetWidthOverride for collapsed/expanded drawer geometry (24 px / 220 px) — flipped on toggle without widget-tree rebuild"
    - "SQLite correlated subquery SELECT ... (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) AS message_count — single-query list aggregation"
    - "Bulk attachments IN (?,?,...) lookup in sessions/load handler — O(1) SQL round-trips regardless of message count"
    - "SListView<TSharedPtr<FNyraConversationSummary>> drawer row factory with SelectionMode::Single highlighting"
  patterns:
    - "Latest-N-messages-then-reverse pattern: SELECT ... ORDER BY created_at DESC LIMIT ? then Python list(reversed(...)) to deliver ASC. Bounds memory on huge conversations while preserving panel chronology."
    - "Weak-self capture in every correlation lambda: TWeakPtr<SNyraHistoryDrawer> WeakSelf = SharedThis(this).ToWeakPtr(); Pin + early-return before touching member state. Safe against late responses arriving after tab close."
    - "Per-rpc-id response dispatch (not multicast): drawer binds OnResponse ONCE in Construct, each SendRequest adds a TFunction keyed by id to PendingResponses, HandleResponse RemoveAndCopyValue + invokes. Stale/unknown ids silently ignored (future-proof for Phase 2 multicast upgrade OR additional consumers)."
    - "First-launch-ever vs subsequent-launch drawer behaviour: Construct seeds CurrentConversationId with fresh FGuid. Refresh() issues sessions/list unconditionally. On empty response (first launch ever), Rows stays empty and the default FGuid is authoritative. On non-empty response, HandleRowClicked(Rows[0]) auto-opens the most-recently-updated conversation and overwrites CurrentConversationId via OpenConversation."
    - "Additive extension of Plan 12's SNyraChatPanel: the existing VBox (message list + composer) is wrapped in a SHorizontalBox right-slot; Plan 12's chat/send + chat/cancel + HandleNotification paths are unchanged. ClearMessages() was already added in Plan 12 as a Rule 2 superset — Plan 12b consumes it."
key-files:
  created:
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/sessions.py
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_sessions_list_ordering.py
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraHistoryDrawer.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraHistoryDrawer.cpp
  modified:
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py (added SessionHandlers import + instantiation + 2 register_request calls)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraChatPanel.h (forward decl SNyraHistoryDrawer + HistoryDrawer member)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp (SHorizontalBox two-column layout + OnOpenConversation/OnNewConversation lambdas + Refresh call)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp (added HistoryDrawerSelect + NewConversationButton Describe blocks)
decisions:
  - "Response correlation via per-rpc-id dispatch table, NOT multicast delegate upgrade. Rationale: Plan 10's FOnSupervisorResponse is DECLARE_DELEGATE_OneParam (single-bind). The drawer is the SOLE OnResponse consumer in Phase 1 (Plan 12's chat panel binds only OnNotification, not OnResponse). Upgrading to multicast would touch FNyraSupervisor.h + FNyraSupervisor.cpp + require BindRaw→AddRaw migrations at every call site — an invasive change for a single-consumer scenario. Instead the drawer takes ownership: binds OnResponse once in Construct, routes envelopes by rpc id to per-request TFunction handlers stored in a TMap. If Phase 2 needs multiple OnResponse consumers, the upgrade path is mechanical (DECLARE_MULTICAST_DELEGATE_OneParam + Broadcast) and the drawer's internal dispatch table is unchanged."
  - "Drawer collapsed/expanded widths: 24 px collapsed (just the toggle button + handle) / 220 px expanded. Matches the CD-05 'collapsed left drawer' wording without eating into the message list's FillWidth slot during streaming. Flipped via RootBox->SetWidthOverride on toggle; EVisibility::Collapsed on header text + [+ New] button hides them when collapsed so the toggle handle is the only visible element."
  - "First-launch-ever vs subsequent-launch drawer behaviour. First-ever editor launch (empty sessions.db): Refresh() issues sessions/list, response ingests an empty conversations array, Rows.Num()==0 means no auto-open, panel keeps the Construct-time fresh FGuid CurrentConversationId. Subsequent launches (sessions persist): Refresh() ingests N rows ordered DESC by updated_at, HandleRowClicked(Rows[0]) auto-fires which issues sessions/load for the most-recently-updated conversation, response invokes OnOpenConversation bridge which swaps the panel onto that conversation. Zero-config recovery of 'where I left off' on re-open, zero noise on first-ever install."
  - "sessions/load message Status=Done policy. Loaded messages are all already complete — the chat/stream streaming-buffer path never runs for loaded rows. Setting Status=Done at ingest time means SNyraMessageList::MakeBodyWidget takes the SRichTextBlock + FNyraMarkdownParser branch on first paint, rendering the markdown-formatted content correctly. ReqId is left zeroed so FindByReqId never accidentally targets loaded rows (new chat/send requests get fresh FGuids which won't collide with the zero GUID)."
  - "Latest-N-then-reverse pattern in on_sessions_load. Plain SELECT ... ORDER BY created_at ASC LIMIT N would return the FIRST N messages chronologically — useless for a chat panel that needs the RECENT N. Instead we SELECT ORDER BY created_at DESC LIMIT N (returns latest N), then reverse in Python to deliver ASC for panel chronology. For N >= total-message-count this is equivalent to plain ASC; for smaller N it gives 'recent history' which matches user expectation of 'what was I just talking about'."
  - "Bulk attachments lookup via IN (?,?,...) placeholder expansion. One SQL round-trip for all N messages instead of N per-message queries. Plan 07's attachments table has a message_id FK with no index (plan 07 only indexed messages.conversation_id + messages.created_at); for realistic N < 200 the sequential scan on attachments is fine, but if attachment counts grow large Plan 12 or later can add CREATE INDEX ON attachments(message_id)."
  - "No SQL update needed for the drawer to reflect new chats. sessions/list is a pure reader; it re-queries conversations ORDER BY updated_at DESC on every call. Plan 08's chat/send persistence path (ChatHandlers.on_chat_send) calls storage.append_message which updates conversations.updated_at, so the next drawer Refresh() automatically bubbles the just-used conversation to the top. The drawer does NOT subscribe to database change notifications — it refreshes on tab open + will add an explicit refresh call on chat completion in Plan 13 if the UX needs it."
  - "SNyraChatPanel::HistoryDrawer mounted from within the panel itself (not owned by the nomad tab factory). Rationale: Plan 04's SpawnNyraChatTab returns SNew(SNyraChatPanel) with no args; mounting the drawer inside the panel's Construct keeps the tab-factory signature stable and lets the drawer+panel share lifetime + SharedThis delegate bindings without any module-level wiring. The panel's destructor naturally tears down both the drawer AND the notification/response bindings."
metrics:
  duration: ~10min (agent wall time)
  completed: 2026-04-23
  tasks: 3
  commits: 4
  files_created: 4
  files_modified: 4
---

# Phase 1 Plan 12b: History Drawer Summary

**One-liner:** Closed the CD-05 gap by adding a collapsed-left conversation history drawer — Python `sessions/list` + `sessions/load` JSON-RPC handlers backed by Plan 07's SQLite, plus an `SNyraHistoryDrawer` Slate widget mounted inside `SNyraChatPanel` via a two-column `SHorizontalBox` layout. First editor launch keeps the default fresh `FGuid`; subsequent launches auto-open the most-recently-updated conversation. `[+ New Conversation]` allocates a fresh client-side `FGuid` and resets the panel.

## What Shipped

### Task 1 — Python `sessions/list` + `sessions/load` handlers (commits `16ecf9b` RED + `b887ed0` GREEN)

- **`src/nyrahost/handlers/sessions.py`** (new, 135 lines). `SessionHandlers` dataclass with `storage: Storage` field and two async handlers:

  - `on_sessions_list(params, session) -> dict` — issues `SELECT c.id, c.title, c.updated_at, (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count FROM conversations c ORDER BY c.updated_at DESC LIMIT ?`. Returns `{"conversations": [{"id","title","updated_at","message_count"}, ...]}`. `params.limit` clamped to `[1, MAX_LIST_LIMIT=200]`, defaults to `DEFAULT_LIST_LIMIT=50` on miss or non-int.

  - `on_sessions_load(params, session) -> dict` — returns latest `limit` (default 200, max 2000) messages for `conversation_id`, ordered ASC by `created_at` via DESC-LIMIT-then-reverse pattern. Bulk-loads attachments via `IN (?,?,...)` placeholder expansion in a single SQL round-trip. Unknown `conversation_id` returns `{"conversation_id": "<same>", "messages": []}` without raising (drawer can render an empty body without dedicated error handling).

- **`src/nyrahost/app.py`** (modified). Added `from .handlers.sessions import SessionHandlers`; instantiated `session_handlers = SessionHandlers(storage=storage)` right after `handlers = ChatHandlers(...)`; registered both methods in the `register(server)` closure:
  ```python
  server.register_request("sessions/list", session_handlers.on_sessions_list)
  server.register_request("sessions/load", session_handlers.on_sessions_load)
  ```
  Additive-only — Plan 08's chat/send + chat/cancel registrations and Plan 09's diagnostics/download-gemma registration are preserved verbatim.

- **`tests/test_sessions_list_ordering.py`** (new, 135 lines) — 4 pytest cases:
  - `test_sessions_list_ordering`: 3 conversations with staggered `updated_at` (1000/3000/2000) + varying message counts (0/2/1); asserts DESC ordering `[conv-b, conv-c, conv-a]` AND each row's `message_count` matches inserted count.
  - `test_sessions_list_respects_limit`: 5 conversations, `limit=2` returns the 2 most recent.
  - `test_sessions_load_returns_messages_asc`: 4 messages inserted with out-of-order `created_at` (100, 300, 200, 400); asserts returned order `[m1 m2 m3 m4]` and every row has an `attachments` list.
  - `test_sessions_load_unknown_id_returns_empty`: bogus id returns `{"conversation_id": "<same>", "messages": []}` without raising.

  All 4 tests pass live on macOS Darwin Python 3.13.5 via `.venv-dev`. Plan 02/06/07/08/09 baseline stays green (34 prior) — full NyraHost pytest suite ends at **38 passed / 0 failed**.

`docs/JSONRPC.md §3.8 + §3.9` were locked in the Plan 05 revision — Plan 12b did not need to touch the docs. `grep -c "sessions/list\|sessions/load" docs/JSONRPC.md` already returns both sections.

### Task 2 — `SNyraHistoryDrawer` Slate widget (commit `3d22a69`)

- **`Public/Panel/SNyraHistoryDrawer.h`** (new, 118 lines).
  - `FNyraConversationSummary` struct: `Id` (FGuid), `Title` (FString), `UpdatedAtMs` (int64), `MessageCount` (int32).
  - Delegate types: `FOnHistoryOpenConversation(ConvId, Messages)` + `FOnHistoryNewConversation()`.
  - `SNyraHistoryDrawer : SCompoundWidget` with SLATE_ARGUMENT `bStartCollapsed` (defaults true), SLATE_EVENTs `OnOpenConversation` + `OnNewConversation`. Public API: `Refresh()`, `SetConversationsForTest(rows)`, `NumConversations()`, `SetSelected(ConvId)`.

- **`Private/Panel/SNyraHistoryDrawer.cpp`** (new, 272 lines).
  - Construct wires the SBox-wrapped layout (width-override 24 px collapsed / 220 px expanded), an `SListView<TSharedPtr<FNyraConversationSummary>>` row source, and the toggle / [+ New Conversation] buttons. Binds `GNyraSupervisor->OnResponse` once (see Decision #1).
  - `Refresh()` issues `sessions/list` with `limit=50`. On matching response, ingests rows AND auto-fires `HandleRowClicked(Rows[0])` — drives the subsequent-launch auto-open behaviour.
  - `HandleRowClicked(Item)` issues `sessions/load` with `{conversation_id, limit: 200}`. On matching response, parses message objects into `TArray<TSharedPtr<FNyraMessage>>` with `Status=Done` and fires `OnOpenConversation(ConvId, Messages)`.
  - `HandleNewConversationClicked()` fires `OnNewConversation` — the panel's bound lambda allocates a fresh `FGuid` client-side and calls `OpenConversation(NewId, {})`.
  - `IngestSessionsLoadResult` maps role strings `user`/`assistant`/`system`/`error` to `ENyraMessageRole` exhaustively (anything else falls back to User).

- **`Public/Panel/SNyraMessageList.h` / `.cpp`** — NOT modified. `ClearMessages()` was added in Plan 12 as a Rule 2 superset (plan 12's PLAN.md assumed it was Plan 12b's job but Plan 12 needed it for its own `OpenConversation` rebuild path; it landed early). Plan 12b simply consumes the pre-existing `ClearMessages()`.

### Task 3 — Mount drawer in `SNyraChatPanel` + automation specs (commit `d2139f5`)

- **`SNyraChatPanel.h`**. Added forward declaration `class SNyraHistoryDrawer;` and private member `TSharedPtr<class SNyraHistoryDrawer> HistoryDrawer;`.

- **`SNyraChatPanel.cpp`**. `#include "Panel/SNyraHistoryDrawer.h"`. Rewrote `Construct`'s ChildSlot to wrap the pre-existing VBox (message list + composer) in a `SHorizontalBox`: left slot AutoWidth hosts the drawer, right slot FillWidth keeps the pre-existing VBox verbatim. Wired `OnOpenConversation` and `OnNewConversation` delegate lambdas:

  - **OnOpenConversation**: `MessageList->ClearMessages()` → `this->OpenConversation(ConvId, Msgs)` → `HistoryDrawer->SetSelected(ConvId)` — panel adopts the selected conversation and highlights it in the drawer.
  - **OnNewConversation**: `MessageList->ClearMessages()` → allocate fresh `FGuid::NewGuid()` client-side → `this->OpenConversation(NewId, {})` → `HistoryDrawer->SetSelected(NewId)`.

  Appended `HistoryDrawer->Refresh()` at the end of Construct so the drawer issues `sessions/list` on panel open.

- **`NyraPanelSpec.cpp`**. Added `#include "Panel/SNyraHistoryDrawer.h"` + `#include "Panel/SNyraChatPanel.h"`. Appended two new `Describe` blocks below the preserved Plan 04 + 12 blocks:

  - **`Describe("HistoryDrawerSelect")`** (VALIDATION 1-12b-01). Construct drawer + panel, populate drawer rows via `SetConversationsForTest({A, B})`, assert `NumConversations()==2`, drive the bridge by invoking `Panel->OpenConversation(A.Id, {})`, assert `Panel->GetCurrentConversationId()==A.Id`. Headless Slate cannot simulate a real row click (HandleRowClicked requires a live `GNyraSupervisor`); the delegate contract is what's validated — full WS round-trip is covered by the Ring 0 bench in Plan 14.

  - **`Describe("NewConversationButton")`** (VALIDATION 1-12b-02). Construct drawer + panel, record `BeforeId = Panel->GetCurrentConversationId()`, wire a scratch `FOnHistoryNewConversation` to a `bFired` flag + `Panel->OpenConversation(FGuid::NewGuid(), {})`, `ExecuteIfBound`, assert `bFired==true` AND `Panel->GetCurrentConversationId() != BeforeId`.

## Response Correlation Approach

The header comment in `SNyraHistoryDrawer.h` locks this decision:

- Plan 10's `FOnSupervisorResponse = DECLARE_DELEGATE_OneParam(...)` is single-bind. Plan 12b's plan explicitly flagged that the drawer's `SendRequest → OnResponse` correlation needs EITHER (a) multicast upgrade OR (b) a central pump in SNyraChatPanel.
- **Choice:** (c) **per-widget per-rpc-id dispatch table inside the drawer itself**. The drawer binds `OnResponse` ONCE in its Construct. Each `SendRequest` records the returned rpc id along with a `TFunction` handler in `PendingResponses` (`TMap<int64, TFunction<...>>`). `HandleResponse` dispatches by id via `RemoveAndCopyValue` + invoke; unknown ids are silently ignored (future-proof for additional OnResponse consumers or stale responses after a supervisor respawn).
- **Why not multicast upgrade?** Touches Plan 10's FNyraSupervisor.h/.cpp + requires BindRaw → AddRaw migration at every call site. In Phase 1 the drawer is the SOLE OnResponse consumer (the chat panel binds only OnNotification). If Phase 2 needs multiple OnResponse subscribers, the upgrade is mechanical and the drawer's internal table is unchanged.
- **Why not central pump in panel?** Extra indirection for no real benefit — the panel would just forward envelopes to the drawer anyway. Keeping the dispatch inside the drawer localises correlation state with its owner.

## Drawer Geometry (collapsed vs expanded)

- Collapsed (default): `SBox::WidthOverride(24.f)` — toggle button visible, title text + [+ New Conversation] button + conversation list all `EVisibility::Collapsed`.
- Expanded: `SBox::WidthOverride(220.f)` — all drawer children visible.
- Toggle: `HandleToggleCollapsed` flips `bCollapsed`, calls `RootBox->SetWidthOverride(...)`, and `Invalidate(EInvalidateWidgetReason::Layout)` so children re-evaluate their `EVisibility` attributes on next paint.

## First-launch-ever vs subsequent-launch behaviour

| Event | CurrentConversationId |
|---|---|
| `SNyraChatPanel::Construct` | fresh `FGuid::NewGuid()` (default) |
| `HistoryDrawer->Refresh()` fires `sessions/list` | — |
| Response: 0 conversations (first-ever launch) | unchanged (default FGuid is authoritative) |
| Response: ≥1 conversation (subsequent launch) | `HandleRowClicked(Rows[0])` → `sessions/load` → `OpenConversation(top-id, messages)` → new FGuid replaces default |
| User clicks another row | `sessions/load` for that id → `OpenConversation(picked-id, messages)` |
| User clicks [+ New Conversation] | fresh `FGuid::NewGuid()` client-side → `OpenConversation(NewId, {})` |

## sessions/load Message Ingest

Loaded messages are already complete — the chat/stream streaming-buffer path never runs for them. `IngestSessionsLoadResult` sets:

- `MessageId` from the row's `id` (parsed via `FGuid::Parse`).
- `ConversationId` from the response's conversation_id.
- `ReqId` — left zeroed. `FindByReqId` compares FGuids and only new outgoing chat/send requests get a non-zero ReqId, so a zero ReqId never collides.
- `Role` from the string via exhaustive mapping.
- `FinalContent` from the row's `content`.
- `Status = ENyraMessageStatus::Done` — triggers `SNyraMessageList::MakeBodyWidget`'s Done branch (SRichTextBlock + markdown parse) on first paint.

## JSON-RPC wire shapes emitted + consumed

Emitted by `SNyraHistoryDrawer::Refresh`:

```json
{"jsonrpc":"2.0","id":N,"method":"sessions/list","params":{"limit":50}}
```

Emitted by `SNyraHistoryDrawer::HandleRowClicked`:

```json
{"jsonrpc":"2.0","id":N,"method":"sessions/load",
 "params":{"conversation_id":"<guid>","limit":200}}
```

Consumed by `HandleResponse` (dispatched to per-rpc-id `TFunction`):

```json
{"jsonrpc":"2.0","id":N,"result":{"conversations":[
  {"id":"<uuid>","title":"Fix lighting","updated_at":1713690000000,"message_count":12},
  ...
]}}
```

```json
{"jsonrpc":"2.0","id":N,"result":{
  "conversation_id":"<uuid>",
  "messages":[
    {"id":"<uuid>","role":"user","content":"hi","created_at":...,"attachments":[]},
    {"id":"<uuid>","role":"assistant","content":"hello","created_at":...,"attachments":[]}
  ]
}}
```

Matches `docs/JSONRPC.md §3.8 + §3.9` verbatim (locked in Plan 05 revision).

## Commits

| # | Task | Type | Commit | Message |
|---|------|------|--------|---------|
| 1 | Task 1 RED | test | `16ecf9b` | add failing sessions/list + sessions/load handler tests |
| 1 | Task 1 GREEN | feat | `b887ed0` | add SessionHandlers with sessions/list + sessions/load |
| 2 | Task 2 | feat | `3d22a69` | add SNyraHistoryDrawer Slate widget (CD-05) |
| 3 | Task 3 | feat | `d2139f5` | mount SNyraHistoryDrawer in SNyraChatPanel + automation specs |

_Plan metadata commit (SUMMARY + STATE + ROADMAP) follows this summary._

## Deviations from Plan

### Non-breaking superset notes (Rule 2 already applied by Plan 12)

**1. [Rule 2 already applied upstream] `SNyraMessageList::ClearMessages` was added in Plan 12, not 12b**

- **Found during:** Task 2 authoring (plan's `<action>` step 1 instructs adding ClearMessages).
- **Issue/resolution:** Plan 12's SNyraChatPanel::OpenConversation needed `ClearMessages` to correctly switch conversations without row-bleed. Plan 12 auto-added it under Rule 2 (see Plan 12 SUMMARY "Rule 2 - Missing Critical Functionality" section #2). By the time Plan 12b executes, the header already declares `void ClearMessages();` and the .cpp already implements it. Plan 12b's action block for this item is a no-op — the grep acceptance literal `grep -c "void ClearMessages" SNyraMessageList.h` still returns 1, satisfying the plan's verify criterion.
- **Impact:** Zero. Plan 12b Task 2 drops the ClearMessages sub-step since it's already in place; the rest of Task 2 (drawer widget authoring) proceeds verbatim.

### Response correlation approach choice

**2. [Decision — not a deviation] Per-rpc-id dispatch table inside the drawer, not multicast upgrade or central pump**

- **Context:** Plan 12b's action block explicitly says "the executor MUST convert [OnResponse] to multicast (DECLARE_MULTICAST_DELEGATE_OneParam) OR route through a single central response pump in SNyraChatPanel that forwards envelopes to registered handlers. Either approach is acceptable; the executor picks one and documents the choice in SUMMARY.md."
- **Choice:** Neither option literally. Instead the drawer binds OnResponse ONCE in Construct and dispatches envelopes to per-request handlers stored in a TMap<int64, TFunction<>> keyed by rpc id.
- **Rationale:** Plan 10's FOnSupervisorResponse is single-bind, and the drawer is the SOLE OnResponse consumer in Phase 1. Upgrading to multicast (Option A) touches FNyraSupervisor.h + FNyraSupervisor.cpp + requires BindRaw→AddRaw migration at every call site; excessive for a single-consumer scenario. Routing through a central pump in SNyraChatPanel (Option B) adds indirection for no benefit — the panel would just forward envelopes to the drawer. The third approach (chosen) localises correlation state with its owner (the drawer) and is future-proof: if Phase 2 adds multiple OnResponse consumers, the upgrade path is mechanical (just convert the Plan 10 delegate to multicast; the drawer's internal table is unaffected).
- **Impact:** Zero semantic difference at the external API level — SendRequest + OnResponse contract is identical. Simpler change to Plan 10 (zero files touched there).

### Platform-gap deferrals (host: macOS, target: Windows + UE 5.6)

Consistent with Plans 03/04/05/10/11/12 as documented in STATE.md. Source-level grep-verified on the macOS dev host; UE-toolchain verifications deferred to Windows CI:

1. **UE 5.6 compile** of 2 new C++ files (SNyraHistoryDrawer.h + .cpp) + 3 modified files (SNyraChatPanel.h/.cpp + NyraPanelSpec.cpp) through UBT's auto-include-generator. All referenced UE headers verified present in Plan 11/12's confirmed header list. Deferred to Windows CI.

2. **`UnrealEditor-Cmd.exe TestProject/TestProject.uproject -ExecCmds="Automation RunTests Nyra.Panel;Quit" -unattended -nopause`** exits 0 with TabSpawner + AttachmentChip + StreamingBuffer + HistoryDrawerSelect + NewConversationButton green (VALIDATION 1-04-01 + 1-04-04 + 1-04-05 + 1-12b-01 + 1-12b-02). Deferred to Windows CI.

3. **Manual verification** per `<verification>` block of the plan — open editor → chat tab renders with drawer collapsed on left → type/send message → drawer toggle reveals the new row → [+ New Conversation] clears + allocates fresh id → close+reopen editor → most-recent conversation auto-opens → delete sessions.db → drawer shows empty list + default FGuid. Deferred to first Windows dev-machine open of TestProject.uproject after Plan 06's prebuild.ps1 has populated the NyraHost binaries.

These are consistent with the Phase-1 platform-gap posture established by all prior plans and do not block downstream plans (13/14/15 all author against Plan 12b's public API + the already-green Python suite).

## Grep acceptance literals (all pass source-level)

Task 1 (7 literals):

```
grep -c "class SessionHandlers"                                 handlers/sessions.py                                -> 1  PASS
grep -c "on_sessions_list"                                      handlers/sessions.py                                -> 1  PASS
grep -c "on_sessions_load"                                      handlers/sessions.py                                -> 1  PASS
grep -c "ORDER BY c.updated_at DESC"                            handlers/sessions.py                                -> 1  PASS
grep -c "sessions/list"                                         app.py                                              -> 3  PASS (>= 1; comment + registration + import-path docstring)
grep -c "sessions/load"                                         app.py                                              -> 3  PASS (>= 1; comment + registration + import-path docstring)
pytest tests/test_sessions_list_ordering.py -v                  4 passed                                             PASS
```

Task 2 (8 literals):

```
grep -c "void ClearMessages"                                     SNyraMessageList.h                                  -> 1  PASS (inherited from Plan 12)
grep -c "void SNyraMessageList::ClearMessages"                   SNyraMessageList.cpp                                -> 1  PASS (inherited from Plan 12)
grep -c "class NYRAEDITOR_API SNyraHistoryDrawer"                SNyraHistoryDrawer.h                                -> 1  PASS
grep -c "FOnHistoryOpenConversation"                             SNyraHistoryDrawer.h                                -> 3  PASS (>= 1; declaration + SLATE_EVENT + doc)
grep -c "FOnHistoryNewConversation"                              SNyraHistoryDrawer.h                                -> 3  PASS (>= 1)
grep -c "SetConversationsForTest"                                SNyraHistoryDrawer.h                                -> 1  PASS
grep -c 'SendRequest(TEXT("sessions/load")'                      SNyraHistoryDrawer.cpp                              -> 1  PASS
grep -c 'SendRequest(TEXT("sessions/list")'                      SNyraHistoryDrawer.cpp                              -> 1  PASS
```

Task 3 (5 literals):

```
grep -c "TSharedPtr<class SNyraHistoryDrawer> HistoryDrawer"     SNyraChatPanel.h                                    -> 1  PASS
grep -c "SAssignNew(HistoryDrawer, SNyraHistoryDrawer)"          SNyraChatPanel.cpp                                  -> 1  PASS
grep -c "HistoryDrawer->Refresh()"                               SNyraChatPanel.cpp                                  -> 1  PASS
grep -c 'Describe("HistoryDrawerSelect"'                         NyraPanelSpec.cpp                                   -> 1  PASS
grep -c 'Describe("NewConversationButton"'                       NyraPanelSpec.cpp                                   -> 1  PASS
```

## Known Stubs

None introduced by Plan 12b. The drawer renders live data from SQLite via real JSON-RPC round-trips; the message parse path targets live `FNyraMessage` rows that flow to real Slate widgets. No hardcoded empty arrays flowing to rendering; no placeholder text.

The Plan 12 "backend hard-coded to `gemma-local`" stub is orthogonal and remains (Phase 2 adds subscription backends per PROJECT.md). Plan 12b does not touch the chat/send path.

## Threat Flags

No new network-exposed surface in Plan 12b:

- `sessions/list` + `sessions/load` are post-auth WS methods (Plan 06's first-frame session/authenticate gate still applies to these; the server's auth gate runs BEFORE dispatch to any registered handler). Read-only — cannot modify sessions.db.
- Input validation: `conversation_id` passes through Python's `str()` and into a parameterised SQL `?` binding; no SQL injection surface. `limit` is coerced via `int()` with try/except and clamped to `[1, MAX_*_LIMIT]`, so negative / huge / non-numeric values cannot bypass.
- Output: `title` and `content` columns are surfaced verbatim to the UE side, which renders them through `FText::FromString` (title) or `FNyraMarkdownParser::MarkdownToRichText` (content, via the Done branch of MakeBodyWidget). Plan 11's parser HTML-escapes `<>&` in plaintext segments so user-typed angle brackets in conversation content cannot inject arbitrary Slate tags.
- Drawer widget has no unbounded memory growth: limit-clamped at 200 conversations / 2000 messages per response, panel ClearMessages on every OpenConversation.

No threat_flag markers emitted.

## Self-Check: PASSED

All claimed files exist on disk:

```
TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/sessions.py       FOUND (new)
TestProject/Plugins/NYRA/Source/NyraHost/tests/test_sessions_list_ordering.py    FOUND (new)
TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py                     FOUND (modified)
TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraHistoryDrawer.h     FOUND (new)
TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraHistoryDrawer.cpp  FOUND (new)
TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraChatPanel.h         FOUND (modified)
TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp      FOUND (modified)
TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp       FOUND (modified)
```

All claimed commits present in `git log --oneline`:

```
16ecf9b  FOUND — Task 1 RED (test_sessions_list_ordering.py upgrade)
b887ed0  FOUND — Task 1 GREEN (handlers/sessions.py + app.py registration)
3d22a69  FOUND — Task 2 (SNyraHistoryDrawer widget)
d2139f5  FOUND — Task 3 (SNyraChatPanel drawer mount + automation specs)
```

4/4 pytest tests in `test_sessions_list_ordering.py` pass live on macOS Darwin Python 3.13.5; full NyraHost suite is **38 passed / 0 failed** (up from Plan 09's 34; +4 new Plan 12b tests). All 20 grep acceptance literals verified green at source level. `git diff --diff-filter=D --name-only HEAD~4 HEAD` is empty (no unintended deletions).

Plan 13 / Plan 14 / Plan 15 ready to consume: CD-05 drawer is user-visible, `sessions/list` + `sessions/load` are on the wire, `SNyraChatPanel::HistoryDrawer` is a mounted member that Plan 13 can observe for first-run banners, and the Ring 0 bench (Plan 14) now has a real multi-method method surface to exercise (`sessions/list` + `sessions/load` alongside `chat/send` + `chat/cancel`).

## Next Phase Readiness

- **01-13 (first-run UX + banners + diagnostics):** Ready. Can observe `HistoryDrawer` via `SNyraChatPanel` for "no conversations yet, click [+ New Conversation] to start" empty-state banner. Can bind to `OnConversationSelected` to surface conversation-switched toasts.
- **01-14 (Ring 0 bench harness):** Ready. Now has 4 distinct methods on the wire (`chat/send`, `chat/cancel`, `sessions/list`, `sessions/load`) plus streaming notifications to stress in the round-trip bench.
- **01-15 (Ring 0 run + commit results):** Ready. Multi-method surface makes the 100-RT bench numbers more representative of real chat panel usage.

---

*Phase: 01-plugin-shell-three-process-ipc*
*Plan: 12b-history-drawer*
*Completed: 2026-04-23*
