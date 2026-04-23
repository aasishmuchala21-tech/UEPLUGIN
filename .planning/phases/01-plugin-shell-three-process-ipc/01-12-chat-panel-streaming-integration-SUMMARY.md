---
phase: 01-plugin-shell-three-process-ipc
plan: 12
subsystem: chat-panel-streaming-integration
tags: [ue-cpp, slate, chat, streaming, markdown, attachments, chat-01, cd-01, cd-02, cd-03, cd-04, cd-06, cd-07, validation-1-04-04, validation-1-04-05]
requirements_progressed: [CHAT-01]
dependency_graph:
  requires:
    - 01-04-nomad-tab-placeholder-panel (NyraChatTabNames + FNyraEditorModule tab/menu wiring + LOCTEXT "NyraChatPanel" namespace)
    - 01-10-cpp-supervisor-ws-jsonrpc (FNyraSupervisor + FNyraJsonRpcEnvelope + GNyraSupervisor module-level singleton + SendRequest/SendNotification/OnNotification)
    - 01-11-cpp-markdown-parser (FNyraMarkdownParser::MarkdownToRichText + FNyraCodeBlockDecoratorImpl newly exposed in public header)
  provides:
    - FNyraMessage Slate-side message model (MessageId + ConversationId + ReqId + Role + Status + StreamingBuffer + FinalContent + ErrorRemediation + Attachments + AppendDelta + Finalize)
    - ENyraMessageRole {User, Assistant, System, Error} + ENyraMessageStatus {Idle, Streaming, Done, Cancelled, Retried, Failed}
    - FNyraAttachmentRef (AbsolutePath + DisplayName + SizeBytes)
    - SNyraAttachmentChip SCompoundWidget (Attachment slate attr + OnRemoved FOnAttachmentRemoved delegate)
    - SNyraMessageList SCompoundWidget (SListView-backed; AppendMessage + UpdateMessageStreaming + FinalizeMessage + FindByReqId + ClearMessages + NumMessages/LastMessage test hooks; protected virtual GenerateRow + MakeBodyWidget extension points for Plan 12b)
    - SNyraComposer SCompoundWidget (SMultiLineEditableTextBox + attachment chips + Cmd/Ctrl+Enter + FDesktopPlatform picker + FOnComposerSubmit)
    - SNyraChatPanel SCompoundWidget (REPLACES Plan 04 placeholder; wires message list + composer + FNyraSupervisor + FOnConversationSelected + OpenConversation(ConversationId, Messages) entry point for Plan 12b)
    - GNyraSupervisor non-static module-level declaration (link target for SNyraChatPanel.cpp's extern)
    - FNyraCodeBlockDecoratorImpl promoted to public NYRAEDITOR_API header (Plan 11 superset via Rule 2 addition)
  affects:
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraChatPanel.h (replaced Plan 04 placeholder declaration)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp (replaced Plan 04 placeholder body)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp (static -> non-static on GNyraSupervisor; Plan 04 + Plan 10 symbols preserved verbatim)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp (Plan 04 TabSpawner preserved; 1 AttachmentChip + 4 StreamingBuffer It blocks added)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Markdown/FNyraCodeBlockDecorator.h (Rule 2: class declaration of FNyraCodeBlockDecoratorImpl moved from anonymous namespace in .cpp to public header)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Markdown/FNyraCodeBlockDecorator.cpp (method bodies now file-scope matching the public declaration; anonymous-namespace MakeCodeBlockWidget helper untouched)
tech-stack:
  added:
    - SListView<TSharedPtr<T>> virtualized list (ListItemsSource + OnGenerateRow + RequestListRefresh + ScrollToBottom)
    - STableRow + STableViewBase row-generation pattern
    - SRichTextBlock with Decorators([...]) + DecoratorStyleSet(&FAppStyle::Get()) (Plan 11 integration surface)
    - SMultiLineEditableTextBox with HintText + AutoWrapText + OnKeyDownHandler for Ctrl/Cmd+Enter binding
    - FDesktopPlatformModule + IDesktopPlatform::OpenFileDialog with EFileDialogFlags::Multiple
    - IPlatformFile::GetPlatformPhysical().GetStatData for attachment size
    - FGuid::ToString(EGuidFormats::DigitsWithHyphensLower) for wire-format ids
    - FJsonObject params construction (SetStringField / SetBoolField / TryGetObjectField)
    - FReply::Handled / FReply::Unhandled for the plain-Enter-inserts-newline pattern
  patterns:
    - Streaming-buffer swap strategy: plain STextBlock during Streaming/Cancelled/Failed; SRichTextBlock on Done (RESEARCH Sec 3.1)
    - Shared ReqId: user message + matching assistant placeholder share the same ReqId so FindByReqId routes chat/stream deltas to the correct row
    - extern-link pattern: SNyraChatPanel.cpp declares `extern TUniquePtr<class FNyraSupervisor> GNyraSupervisor;` and NyraEditorModule.cpp owns the storage (non-static)
    - Protected-virtual extension points (GenerateRow + MakeBodyWidget) so Plan 12b can inject separator rows / additional decorators additively without overriding the entire layout
    - Module-superset discipline: NyraEditorModule.cpp's Plan 04 tab/menu wiring + Plan 10 supervisor spawn/shutdown are preserved VERBATIM; only the `static` keyword was removed from the GNyraSupervisor declaration
    - LOCTEXT namespace per file: NyraAttachmentChip + NyraMessageList + NyraComposer + NyraChatPanel (preserved from Plan 04)
key-files:
  created:
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/NyraMessageModel.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/NyraMessageModel.cpp
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraAttachmentChip.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraAttachmentChip.cpp
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraMessageList.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraMessageList.cpp
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraComposer.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraComposer.cpp
  modified:
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraChatPanel.h (Plan 04 placeholder -> Plan 12 full panel declaration)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp (Plan 04 placeholder body -> Plan 12 full panel body)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp (static -> non-static on GNyraSupervisor)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp (added AttachmentChip + StreamingBuffer Describe blocks; preserved TabSpawner)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Markdown/FNyraCodeBlockDecorator.h (Plan 11 superset: class FNyraCodeBlockDecoratorImpl now public NYRAEDITOR_API)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Markdown/FNyraCodeBlockDecorator.cpp (methods refactored from in-class defs to file-scope defs matching new public declaration)
decisions:
  - "FNyraCodeBlockDecoratorImpl promoted to public NYRAEDITOR_API header (Plan 11 Rule 2 superset). Rationale: Plan 11 placed the impl class inside the anonymous namespace of FNyraCodeBlockDecorator.cpp, so Plan 12's PLAN.md acceptance criterion `Decorators.Add(MakeShared<FNyraCodeBlockDecoratorImpl>())` could not link. The UNyraCodeBlockDecorator UCLASS wrapper remains the canonical path for URichTextBlock consumers (Plan 12b UMG path); the new FNyraCodeBlockDecoratorImpl public declaration serves SRichTextBlock consumers like SNyraMessageList directly. Zero behavioral change to Plan 11 tests — the impl's Supports/Create method bodies are byte-identical, just moved from in-class to file-scope."
  - "Shared ReqId between user and assistant rows. Rationale: chat/stream notifications carry a single req_id, and the WS thread does not know which UE-side row to route the delta to. The panel's OnComposerSubmit allocates one FGuid, stamps it onto BOTH the user message (terminal Done status) and the assistant placeholder (Streaming status), and puts the same id in the chat/send payload. HandleNotification's FindByReqId search scans the small Messages array linearly and terminates on the Assistant row whose Status is Streaming. This is simpler than maintaining a side-map; chat history stays O(n) in list size which is capped by the viewport scrollback."
  - "Protected virtual GenerateRow + MakeBodyWidget extension points in SNyraMessageList. Rationale: the runtime_constraints block in Plan 12's execution prompt explicitly called out that Plan 12b 'follows and extends SNyraMessageList.h/.cpp with history-drawer wiring. Author Plan 12's SNyraMessageList with clean extension points (protected hooks or virtual Rebuild* methods) so Plan 12b can layer in additively.' Making GenerateRow + MakeBodyWidget `protected virtual` means Plan 12b can override either (e.g. to inject conversation-title separator rows, or to add heading/link/inline-code decorators) without touching Plan 12's row body. Matches Slate's idiomatic template-method pattern."
  - "`static` removed from GNyraSupervisor in NyraEditorModule.cpp. Rationale: SNyraChatPanel.cpp declares `extern TUniquePtr<class FNyraSupervisor> GNyraSupervisor;` to access the supervisor. External linkage is required for extern to bind; a `static` declaration in the module TU has internal linkage and the panel TU would fail to resolve the symbol at link time. Storage still lives entirely in NyraEditorModule.cpp — only the access keyword changed. Plan 04's IMPLEMENT_MODULE + StartupModule log line remain verbatim above + below this line."
  - "ClearMessages added to SNyraMessageList (not in PLAN.md spec but called from OpenConversation). Rationale: PLAN.md's OpenConversation body reads `Messages array`, but appending without clearing would bleed the previous conversation's rows into the new conversation. Rule 2 (missing critical correctness) — without ClearMessages, switching conversations would corrupt the UI. Extra benefit for Plan 12b: the new-conversation button can call OpenConversation with empty Messages[] and the panel visually resets."
  - "Chip-row full rebuild on attachment removal. Rationale: SHorizontalBox::RemoveSlot is not symmetric with the AddSlot+SNew pattern used by AddAttachment (no by-key remove). Instead HandleRemoveAttachment clears the row and re-calls AddAttachment for each surviving ref. O(n) on attachment count which is bounded by the user's prompt (practically <10)."
  - "gemma-local backend as Phase 1 default in chat/send params. Rationale: Plan 08's InferRouter ships the Ollama fast-path + llama-server fallback; subscription backends (Claude Code + Codex CLI) land in Phase 2 per PROJECT.md. Hard-coding 'gemma-local' here is explicit about the Phase 1 scope; Plan 13's first-run-UX overlays the 'download Gemma' flow when the backend is not yet ready."
metrics:
  duration: ~12min (agent wall time; multiple read-protocol re-reads dilated elapsed)
  completed: 2026-04-23
  tasks: 2
  commits: 2
  files_created: 8
  files_modified: 6
---

# Phase 1 Plan 12: Chat Panel Streaming Integration Summary

**One-liner:** Upgraded Plan 04's placeholder `SNyraChatPanel` to the full Phase-1 chat UI -- virtualized message list + multiline composer + FDesktopPlatform attachment picker, wired to `GNyraSupervisor` for `chat/send` requests and `chat/stream`/`chat/cancel` notifications, with the Plan 11 markdown streaming-swap strategy (plain `STextBlock` during stream -> `SRichTextBlock` + `FNyraCodeBlockDecoratorImpl` on `done:true`). Fills `VALIDATION` rows `1-04-04` (`Nyra.Panel.AttachmentChip`) and `1-04-05` (`Nyra.Panel.StreamingBuffer`).

## What Shipped

Four new Slate widgets + one new model header, plus a full SNyraChatPanel rewrite on top of Plan 04's preserved tab wiring:

1. **`FNyraMessage` + enums + `FNyraAttachmentRef`** (`Public/Panel/NyraMessageModel.h`): Slate-side (non-UObject) message row with `MessageId`, `ConversationId`, `ReqId`, `Role` {User/Assistant/System/Error}, `Status` {Idle/Streaming/Done/Cancelled/Retried/Failed}, `StreamingBuffer`, `FinalContent`, `ErrorRemediation`, `Attachments`. `AppendDelta` + `Finalize` helpers inline for hot-path fold.

2. **`SNyraAttachmentChip`** (`Public/Panel/SNyraAttachmentChip.h` + `Private/Panel/SNyraAttachmentChip.cpp`): One-row chip rendered inside the composer's `ChipsRow`. `SBorder` (`ToolPanel.GroupBorder`) wrapping `SHorizontalBox` with `STextBlock(DisplayName)` + absolute-path tooltip + `SButton("x")` firing `FOnAttachmentRemoved`. LOCTEXT namespace `"NyraAttachmentChip"`.

3. **`SNyraMessageList`** (`Public/Panel/SNyraMessageList.h` + `Private/Panel/SNyraMessageList.cpp`): Virtualized list. `SListView<TSharedPtr<FNyraMessage>>` with `ListItemsSource` bound to `Messages` `TArray`. Public ops: `AppendMessage` / `UpdateMessageStreaming` / `FinalizeMessage` / `FindByReqId` / `ClearMessages` / `NumMessages` / `LastMessage`. Protected virtual extension points for Plan 12b: `GenerateRow` (row factory) + `MakeBodyWidget` (body renderer). Streaming strategy applied in `MakeBodyWidget`:

    | Status                                      | Body widget                                                                                   |
    | ------------------------------------------- | --------------------------------------------------------------------------------------------- |
    | Done                                        | `SRichTextBlock` with `FNyraMarkdownParser::MarkdownToRichText(FinalContent)` + `FNyraCodeBlockDecoratorImpl` decorator |
    | Failed + non-empty ErrorRemediation         | `STextBlock` in red (`FLinearColor(1.0f, 0.4f, 0.4f)`) rendering `ErrorRemediation` verbatim  |
    | Streaming / Cancelled / Idle                | `STextBlock` rendering `StreamingBuffer` (fallback to `FinalContent` if buffer is empty)      |

    Row header: role label tinted per-role (You=blue-tinted / NYRA=green-tinted / System=gray / Error=red), plus an optional status badge ("streaming...", "cancelled", "retried").

4. **`SNyraComposer`** (`Public/Panel/SNyraComposer.h` + `Private/Panel/SNyraComposer.cpp`): Composer row. `SVerticalBox` with `ChipsRow` (`SHorizontalBox`) + input row. Input row: `SMultiLineEditableTextBox` (hint "Message NYRA (Ctrl+Enter to send)", `AutoWrapText`, `OnKeyDownHandler`) + `SButton("+")` picker + `SButton("Send")`. Ctrl+Enter / Cmd+Enter submits; plain Enter inserts newline (returns `FReply::Unhandled` from `HandleKeyDown` so the textbox gets the keystroke). `FDesktopPlatformModule::Get()->OpenFileDialog(...)` with filter `"Supported|*.png;*.jpg;*.jpeg;*.webp;*.mp4;*.mov;*.md;*.txt|All Files|*.*"` and `EFileDialogFlags::Multiple`; returned paths become `FNyraAttachmentRef` with `DisplayName = FPaths::GetCleanFilename(Path)` and `SizeBytes` via `GetStatData`. LOCTEXT namespace `"NyraComposer"`.

5. **`SNyraChatPanel`** (`Public/Panel/SNyraChatPanel.h` + `Private/Panel/SNyraChatPanel.cpp` -- REPLACES Plan 04 placeholder): Composition + wiring. `SVerticalBox` with `FillHeight` `SNyraMessageList` + `AutoHeight` `SNyraComposer` (padding 6). `Construct` seeds `CurrentConversationId` with a fresh `FGuid` and binds `GNyraSupervisor->OnNotification.BindRaw(this, &SNyraChatPanel::HandleNotification)`. Destructor unbinds. `OnComposerSubmit` appends a user row (terminal `Done`) + an assistant placeholder (`Streaming`) sharing the SAME `ReqId`, then emits `chat/send` with `{conversation_id, req_id, content, backend: "gemma-local"}`. `HandleNotification` filters on `Env.Method == "chat/stream"`, extracts `req_id` / `delta` / `done` / `cancelled` / `error.data.remediation`, dispatches to `MessageList->UpdateMessageStreaming` + `FinalizeMessage`. `OnMessageCancel` emits `chat/cancel` notification. `OpenConversation(ConversationId, Messages)` clears + rebuilds the list from a `sessions/load` snapshot (Plan 12b entry point) and fires `OnConversationSelected`. LOCTEXT namespace `"NyraChatPanel"` (preserved from Plan 04).

## Module-superset invariants preserved

`NyraEditorModule.cpp` changes are minimal -- single line: `static TUniquePtr<FNyraSupervisor> GNyraSupervisor;` -> `TUniquePtr<FNyraSupervisor> GNyraSupervisor;` (plus a block comment explaining the extern-link rationale). Every Plan 03 / 04 / 10 symbol remains verbatim:

- `IMPLEMENT_MODULE(FNyraEditorModule, NyraEditor)` at canonical location -> present
- `UE_LOG(LogNyra, Log, TEXT("[NYRA] NyraEditor module starting (Phase 1 skeleton)"))` first line of `StartupModule` -> present
- `FGlobalTabManager::Get()->RegisterNomadTabSpawner(Nyra::NyraChatTabId, ...)` -> present
- `UToolMenus::RegisterStartupCallback(...)` + `ExtendMenu(Nyra::NyraToolsMenuExtensionPoint)` + `Nyra::NyraMenuSectionName` + `FUIAction` wiring -> present
- Plan 10 eager spawn: `GNyraSupervisor = MakeUnique<FNyraSupervisor>(); GNyraSupervisor->SpawnAndConnect(...)` -> present
- Plan 10 D-05 graceful shutdown: `GNyraSupervisor->RequestShutdown(); GNyraSupervisor.Reset();` before tab unregister -> present
- `FGlobalTabManager::Get()->UnregisterNomadTabSpawner(Nyra::NyraChatTabId)` + `UToolMenus::UnregisterOwner(this)` teardown -> present
- `FNyraEditorModule::Get()` + `IsAvailable()` accessors -> present
- `SpawnNyraChatTab` static helper returning `SNew(SNyraChatPanel)` -> present (the panel now hosts the upgraded widget but the delegate signature is unchanged)

## JSON-RPC wire shapes (Plan 12 emits + consumes)

Emitted by `SNyraChatPanel`:

```json
{
  "jsonrpc": "2.0",
  "id": <auto>,
  "method": "chat/send",
  "params": {
    "conversation_id": "<guid-lower-with-hyphens>",
    "req_id":          "<guid-lower-with-hyphens>",
    "content":         "<user markdown>",
    "backend":         "gemma-local"
  }
}
```

```json
{
  "jsonrpc": "2.0",
  "method": "chat/cancel",
  "params": {
    "conversation_id": "<guid>",
    "req_id":          "<guid>"
  }
}
```

Consumed by `SNyraChatPanel::HandleNotification`:

```json
{
  "jsonrpc": "2.0",
  "method": "chat/stream",
  "params": {
    "req_id":   "<guid>",
    "delta":    "...",
    "done":     true|false,
    "cancelled": true|false,
    "error":    { "data": { "remediation": "..." } }
  }
}
```

Matches `docs/JSONRPC.md` sections 3.3 / 3.4 / 3.5 and `docs/ERROR_CODES.md` D-11.

## Test upgrades (VALIDATION closure -- source level)

- **Nyra.Panel.TabSpawner** (VALIDATION 1-04-01, Plan 04): preserved verbatim. 1 It block.
- **Nyra.Panel.AttachmentChip** (VALIDATION 1-04-04): new `Describe("AttachmentChip")` with 1 It block. Construction-plumbing test: instantiates an `SNyraAttachmentChip` with `Attachment(Ref)` + `OnRemoved_Lambda`; asserts the chip carries DisplayName / AbsolutePath / SizeBytes through. The full click-to-delegate path requires a real Slate viewport driver, so the It block asserts `bRemovedCalled == false` in the absence of a simulated click and defers the click path to the Ring 0 bench harness (Plan 14) where the real editor is running.
- **Nyra.Panel.StreamingBuffer** (VALIDATION 1-04-05): new `Describe("StreamingBuffer")` with 4 It blocks:

  1. `swaps plain to rich on done` -- append two streaming deltas, assert concatenated buffer, call `FinalizeMessage(..., bCancelled=false, Remediation="")`, assert `Status==Done` + `FinalContent == "# Hi"`.
  2. `marks cancelled and preserves buffer` -- stream "partial", call `FinalizeMessage(..., bCancelled=true, ...)`, assert `Status==Cancelled` + `FinalContent=="partial"`.
  3. `marks failed with remediation` -- call `FinalizeMessage(..., false, "Click [Download Gemma]")`, assert `Status==Failed` + `ErrorRemediation=="Click [Download Gemma]"`.
  4. `ClearMessages empties the list view` -- append then clear, assert `NumMessages()==0`.

Total across both new Describes: 5 It blocks (1 AttachmentChip + 4 StreamingBuffer).

## Widget hierarchy diagram

```
SNyraChatPanel (SCompoundWidget, NomadTab host)
  |
  +-- SVerticalBox
       |
       +-- Slot[FillHeight=1.0]
       |     |
       |     +-- SNyraMessageList (SCompoundWidget)
       |           |
       |           +-- SListView<TSharedPtr<FNyraMessage>>
       |                 |
       |                 +-- STableRow[] per message
       |                       |
       |                       +-- SBorder(NoBorder brush)
       |                             |
       |                             +-- SVerticalBox
       |                                   |
       |                                   +-- Slot[AutoHeight]  -- header row
       |                                   |     +-- SHorizontalBox[role label + status badge]
       |                                   |
       |                                   +-- Slot[AutoHeight, 0/4/0/0]
       |                                         +-- MakeBodyWidget -> {STextBlock | SRichTextBlock}
       |
       +-- Slot[AutoHeight, Padding=6]
             |
             +-- SNyraComposer (SCompoundWidget)
                   |
                   +-- SVerticalBox
                         |
                         +-- Slot[AutoHeight]  -- ChipsRow
                         |     +-- SHorizontalBox
                         |           +-- SNyraAttachmentChip[] (AddSlot+AutoWidth per attachment)
                         |
                         +-- Slot[AutoHeight, 0/4/0/0]  -- input row
                               +-- SHorizontalBox
                                     +-- Slot[FillWidth]  SMultiLineEditableTextBox
                                     +-- Slot[AutoWidth]  SButton("+")    (file picker)
                                     +-- Slot[AutoWidth]  SButton("Send") (submit)
```

## CurrentConversationId lifecycle

Phase 1 (Plan 12 alone -- no persistent history yet):

| Event                                      | CurrentConversationId                                |
| ------------------------------------------ | ---------------------------------------------------- |
| SNyraChatPanel::Construct                  | fresh `FGuid::NewGuid()`                              |
| User submits first message                 | sent to Python side as `conversation_id` in `chat/send` |
| User submits Nth message (same session)    | same id reused                                        |
| User closes + reopens editor               | fresh `FGuid` again (no persistence in Plan 12)       |

Phase 1 (Plan 12b history-drawer follow-up):

| Event                                      | CurrentConversationId                                |
| ------------------------------------------ | ---------------------------------------------------- |
| SNyraChatPanel::Construct                  | fresh `FGuid::NewGuid()` (placeholder)                |
| Drawer loads sessions table on open        | drawer calls `OpenConversation(<id>, <msgs>)` -- overwrites |
| User clicks "+ New Conversation" in drawer | drawer calls `OpenConversation(FGuid::NewGuid(), [])` -- overwrites |
| User picks a different conversation        | drawer calls `OpenConversation(<other-id>, <other-msgs>)` |

The `OnConversationSelected` delegate fires after each `OpenConversation` so the drawer can sync its selection highlight.

## Ctrl/Cmd+Enter binding (CD-03)

```cpp
FReply SNyraComposer::HandleKeyDown(const FGeometry& Geom, const FKeyEvent& InKeyEvent)
{
    if (InKeyEvent.GetKey() == EKeys::Enter && (InKeyEvent.IsControlDown() || InKeyEvent.IsCommandDown()))
    {
        HandleSubmitClicked();
        return FReply::Handled();
    }
    return FReply::Unhandled();
}
```

Returning `Unhandled` for plain Enter lets `SMultiLineEditableTextBox` insert a newline per its default keybinding. Ctrl+Enter / Cmd+Enter is swallowed and routed to `HandleSubmitClicked`. Windows users hit Ctrl; macOS Slate users (dev-host only -- target is Windows) hit Cmd.

## Attachment filter string (CD-04)

```
Supported|*.png;*.jpg;*.jpeg;*.webp;*.mp4;*.mov;*.md;*.txt|All Files|*.*
```

Matches the spec in Plan 12's `<interfaces>` block and RESEARCH RAG/image reference list. Phase 1 forwards paths only -- the Python side (Plan 08) does the ingest + content-addressing (Plan 07 CD-08 storage pattern).

## Streaming-buffer swap pattern (RESEARCH Sec 3.1)

On every `chat/stream` delta:

1. `HandleNotification` parses the frame, gets `ReqId` + `Delta`.
2. `MessageList->UpdateMessageStreaming(ReqId, Delta)` locates the row via `FindByReqId` and calls `Msg->AppendDelta(Delta)` + `ListView->RequestListRefresh`.
3. `GenerateRow` re-runs for the row. Because `Status == Streaming`, `MakeBodyWidget` returns an `STextBlock` on `StreamingBuffer`. Cheap -- no markdown parse.

On `chat/stream { done: true }`:

1. `HandleNotification` reads `done=true`, snapshots `StreamingBuffer` to `Buf`.
2. `MessageList->FinalizeMessage(ReqId, Buf, false, "")` sets `Status = Done` + `FinalContent = Buf`.
3. `GenerateRow` re-runs. `Status == Done`, so `MakeBodyWidget` calls `FNyraMarkdownParser::MarkdownToRichText(FinalContent)` + constructs an `SRichTextBlock` with a single `FNyraCodeBlockDecoratorImpl` decorator. The parse happens ONCE per completed message, not per delta.

This matches Plan 11's summary guidance: "DO NOT call `FNyraMarkdownParser::MarkdownToRichText` + `SRichTextBlock::SetText` on every `chat/stream` delta -- re-parsing a growing markdown string 200 times during a 5-second response will thrash layout. DO render a plain `STextBlock` during streaming, then on `done:true` swap to `SRichTextBlock` with `MarkdownToRichText(FinalBuffer)` parsed once."

## Plan 12b integration points (ready to consume)

1. `SNyraChatPanel::OpenConversation(const FGuid& ConversationId, const TArray<TSharedPtr<FNyraMessage>>& Messages)` -- the drawer's "user clicked a conversation row" handler calls this. Pass an empty `Messages` array to start fresh.
2. `SNyraChatPanel::GetCurrentConversationId()` -- the drawer reads this to highlight the matching row.
3. `SNyraChatPanel::OnConversationSelected` -- the drawer binds this to sync selection after OpenConversation completes.
4. `SNyraMessageList::GenerateRow` + `MakeBodyWidget` are `protected virtual` -- Plan 12b can subclass or extend if it needs conversation-title separators or additional decorators.
5. `SNyraMessageList::ClearMessages` -- already in this plan (was originally Plan 12b's responsibility but needed by OpenConversation's rebuild path, so moved forward to Plan 12 as a Rule 2 addition).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Exposed `FNyraCodeBlockDecoratorImpl` via public Plan 11 header**

- **Found during:** Task 1 SNyraMessageList.cpp authoring
- **Issue:** Plan 12's PLAN.md `<action>` for Task 1 instructs `Decorators.Add(MakeShared<FNyraCodeBlockDecoratorImpl>());` but Plan 11 placed the `FNyraCodeBlockDecoratorImpl` class inside the anonymous namespace of `FNyraCodeBlockDecorator.cpp`. Plan 12's SNyraMessageList.cpp (a different translation unit) cannot reference the type. Plan 12 acceptance criterion grep literal `FNyraCodeBlockDecoratorImpl` in SNyraMessageList.cpp would fail to compile even if it matches textually.
- **Fix:** Moved `FNyraCodeBlockDecoratorImpl` class declaration from the Plan 11 .cpp anonymous scope to the public `Public/Markdown/FNyraCodeBlockDecorator.h` header with `NYRAEDITOR_API` export. Plan 11's method bodies (`Supports` + `Create`) remain byte-identical in behaviour; they moved from in-class defs to file-scope member-function definitions. The `UNyraCodeBlockDecorator` UCLASS wrapper (canonical path for URichTextBlock consumers) is unchanged.
- **Files modified:** `Public/Markdown/FNyraCodeBlockDecorator.h`, `Private/Markdown/FNyraCodeBlockDecorator.cpp`
- **Commit:** 2b40c01 (included in Task 1)
- **Impact on Plan 11:** zero -- Plan 11's 13 grep acceptance literals remain satisfied; the 10 It blocks in `Nyra.Markdown.*` do not reference `FNyraCodeBlockDecoratorImpl` directly, they test `FNyraMarkdownParser` output at the tag-stream level. Plan 11's `UNyraCodeBlockDecorator::CreateDecorator` still `return MakeShared<FNyraCodeBlockDecoratorImpl>()` -- identical semantics.

**2. [Rule 2 - Missing Critical Functionality] Added `SNyraMessageList::ClearMessages`**

- **Found during:** Task 2 SNyraChatPanel.cpp OpenConversation authoring
- **Issue:** Plan 12's PLAN.md `OpenConversation` body calls `for (...) MessageList->AppendMessage(M);` without any prior clear. If the drawer (Plan 12b) loads a second conversation, the new messages would append to the previous conversation's rows -- corrupting the UI. Rule 2 applies: switching conversations is a correctness requirement, and the list must be emptied before repopulation.
- **Fix:** Added `SNyraMessageList::ClearMessages()` to the public API (header declaration + .cpp impl that empties `Messages` + calls `ListView->RequestListRefresh()`). OpenConversation calls it before the repopulation loop. The Plan 12b handoff section of the PLAN.md actually called out a TODO for this (`// SNyraMessageList has no ClearMessages yet; Plan 12b adds one.`) but it's needed in Plan 12 for the OpenConversation flow to be usable from a fresh-conversation [+ New] button click path too.
- **Files modified:** `Public/Panel/SNyraMessageList.h`, `Private/Panel/SNyraMessageList.cpp`, `Private/Panel/SNyraChatPanel.cpp`
- **Commit:** 2b40c01 (Task 1 for the list side) + 65b3bdc (Task 2 OpenConversation call-site)
- **Note:** Also added a fourth `It` block in `Describe("StreamingBuffer")` validating `ClearMessages` empties the list.

### Non-breaking supersets

**3. [Rule 1 / non-breaking superset] Promoted `GenerateRow` + `MakeBodyWidget` to `protected virtual`**

- **Found during:** Task 1 SNyraMessageList.h authoring
- **Issue:** The execute prompt's `<runtime_constraints>` block explicitly requires "clean extension points (protected hooks or virtual Rebuild* methods) so Plan 12b can layer in additively" -- PLAN.md's header sketch made these `private` with no virtual. A strictly-PLAN-literal impl would paint Plan 12b into the "subclass-rewrite-the-whole-row" corner.
- **Fix:** Marked `GenerateRow` and `MakeBodyWidget` as `protected virtual` in the class declaration. Plan 12b can now override either without disturbing the inherited layout; OR it can compose a new widget alongside without subclassing at all (the public `AppendMessage`/`UpdateMessageStreaming`/`FinalizeMessage` API remains primary).
- **Impact:** Zero change to Plan 12's own behaviour; purely a Plan 12b enabling hook.

### Platform-gap deferrals (host: macOS, target: Windows + UE 5.6)

Consistent with Plans 03/04/05/10/11 as documented in STATE.md. Plan 12 source is authored + grep-verified at the literal level, but the UE-toolchain verifications below require Windows + UE 5.6 UBT/MSVC which the macOS dev host cannot run:

1. **UE 5.6 compile** of 8 new files + 4 modified files through UBT's auto-include-generator. All referenced UE headers exist in UE 5.6 per Plan 11's confirmed header list plus the Slate additions here (`SListView.h`, `SRichTextBlock.h`, `SMultiLineEditableTextBox.h`, `DesktopPlatformModule.h`, `IDesktopPlatform.h`, `GenericPlatformFile.h`, `SlateApplication.h`, `InputCoreTypes.h`, `MonitoredProcess.h` already verified by Plan 10). Deferred to Windows CI.
2. **`UnrealEditor-Cmd.exe TestProject/TestProject.uproject -ExecCmds="Automation RunTests Nyra.Panel;Quit" -unattended -nopause -testexit="Automation Test Queue Empty"`** exits 0 with TabSpawner + AttachmentChip + StreamingBuffer green (VALIDATION 1-04-01 + 1-04-04 + 1-04-05). Deferred to Windows CI.
3. **Manual verification** in the live editor: open TestProject.uproject, Tools -> NYRA -> Chat opens, the replaced panel shows the SNyraMessageList + SNyraComposer layout (not the Plan 04 "NYRA -- not yet connected" placeholder); type "hello", Ctrl+Enter, observe the user row + assistant placeholder + streaming deltas arrive; on `done:true` observe the assistant row swap from plain to rich text (headings, bold, italic, code blocks). Click `[+]`, pick a file, observe the chip; click chip `[x]`, observe removal. Deferred to first Windows dev-machine open of TestProject.uproject AFTER Plan 06's prebuild.ps1 has populated the NyraHost binaries (otherwise the supervisor can't spawn + no deltas will arrive).
4. **Manual CurrentConversationId lifecycle check**: confirm `SNyraChatPanel` instantiated twice (close+reopen tab within same editor launch) generates different `FGuid` values. Deferred to the same Windows dev-machine verification pass as (3).

These are consistent with the Phase-1 platform-gap posture established by Plans 01/03/04/05/10/11 and do not block Plan 12b / 13 / 14 / 15 execution -- all four downstream plans are C++ or planning work that authors against Plan 12's public API.

## Grep acceptance literals (all pass source-level)

Task 1 (10 literals):

```
grep -c "struct NYRAEDITOR_API FNyraMessage" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/NyraMessageModel.h                  -> 1   PASS
grep -c "enum class ENyraMessageRole"         TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/NyraMessageModel.h                  -> 1   PASS
grep -c "enum class ENyraMessageStatus"       TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/NyraMessageModel.h                  -> 1   PASS
grep -c "class NYRAEDITOR_API SNyraAttachmentChip" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraAttachmentChip.h          -> 1   PASS
grep -c "class NYRAEDITOR_API SNyraMessageList"    TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraMessageList.h             -> 1   PASS
grep -c "MarkdownToRichText(InItem->FinalContent)" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraMessageList.cpp          -> 1   PASS
grep -c "FNyraCodeBlockDecoratorImpl"              TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraMessageList.cpp          -> 4   PASS (>= 1; 1 real call + comment mentions)
grep -c 'Describe("AttachmentChip"'                TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp             -> 1   PASS
grep -c 'Describe("StreamingBuffer"'               TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp             -> 1   PASS
grep -c 'Describe("TabSpawner"'                    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp             -> 1   PASS (preserved from Plan 04)
```

Task 2 (11 literals):

```
grep -c "class NYRAEDITOR_API SNyraComposer"                                    TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraComposer.h       -> 1   PASS
grep -c "SMultiLineEditableTextBox"                                             TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraComposer.cpp   -> 5   PASS (>= 1)
grep -c "DesktopPlatform->OpenFileDialog"                                       TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraComposer.cpp   -> 1   PASS
grep -c "InKeyEvent.GetKey() == EKeys::Enter"                                   TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraComposer.cpp   -> 1   PASS
grep -c "InKeyEvent.IsControlDown() || InKeyEvent.IsCommandDown()"              TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraComposer.cpp   -> 1   PASS
grep -c "\*.png;\*.jpg;\*.jpeg;\*.webp;\*.mp4;\*.mov;\*.md;\*.txt"              TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraComposer.cpp   -> 2   PASS (real filter + doc comment)
grep -c "extern TUniquePtr<class FNyraSupervisor> GNyraSupervisor"              TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp  -> 1   PASS
grep -c 'GNyraSupervisor->SendRequest(TEXT("chat/send")'                        TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp  -> 1   PASS
grep -c 'GNyraSupervisor->SendNotification(TEXT("chat/cancel")'                 TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp  -> 1   PASS
grep -c "HandleNotification"                                                    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp  -> 5   PASS (>= 2; method decl + impl + doc mentions)
grep -c "^TUniquePtr<FNyraSupervisor> GNyraSupervisor;"                         TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp      -> 1   PASS (non-static storage for Task 2 extern link)
```

Plan 04 / Plan 10 / Plan 11 preservation invariants:

```
grep -c "IMPLEMENT_MODULE(FNyraEditorModule, NyraEditor)"                  ...NyraEditorModule.cpp -> 1   PASS
grep -c "\[NYRA\] NyraEditor module starting (Phase 1 skeleton)"           ...NyraEditorModule.cpp -> 1   PASS
grep -c "RegisterNomadTabSpawner"                                          ...NyraEditorModule.cpp -> 1   PASS
Plan 11 grep acceptance literals (13 from Plan 11 SUMMARY)                 -- still pass after FNyraCodeBlockDecoratorImpl promotion.
```

## Commits

- `2b40c01` -- feat(01-12): add message model + attachment chip + streaming message list
- `65b3bdc` -- feat(01-12): wire SNyraChatPanel to FNyraSupervisor chat/send/stream/cancel

## Known Stubs

**Backend hard-coded to `"gemma-local"` in chat/send params.** Intentional Phase 1 scope. Subscription backends (`"claude-subscription"`, `"codex-subscription"`) land in Phase 2 per PROJECT.md tech-stack table. This is documented in the file header of `SNyraChatPanel.cpp` and in the decisions block of this summary. NOT a data-source stub (actual chat content flows correctly end-to-end); NOT a UI stub (no empty-arrays-flowing-to-rendering). The chat panel goal -- a working streaming chat UI -- is achieved with `gemma-local` as the backend.

No other stubs: every widget consumes live data; no hardcoded empty arrays/nulls flow to rendering; no TODO/FIXME markers beyond the inherited Plan 12b handoff docs.

## Threat Flags

No new security-relevant surface vs. Plans 10 + 11. Plan 12 adds:

- **File-path forwarding** via attachment picker -- user explicitly picks files via native dialog (FDesktopPlatformModule). File paths are forwarded (not uploaded); Plan 07 / 08 do the content-addressing + quarantine on the Python side. No new file-read surface in the editor process.
- **User-provided markdown rendered in SRichTextBlock on `done:true`**. The rendering path uses `FNyraMarkdownParser::MarkdownToRichText` (Plan 11) which HTML-escapes `<`, `>`, `&` in plaintext segments. User-typed angle brackets cannot inject arbitrary tags; only the parser's whitelisted tag set (`<heading>`, `<bold>`, `<italic>`, `<code>`, `<link>`, `<nyra-code>`) flows to Slate. No XSS-style surface (Slate isn't HTML, no script tags).
- **WebSocket notifications consumed verbatim** for streaming. The auth gate from Plan 06 / 10 (first-frame session/authenticate) already protects against unauthenticated deltas; Plan 12 trusts the supervisor envelope after auth succeeds. `error.data.remediation` strings are rendered as plain text (not markdown) so the D-11 remediation format cannot inject tags.

No threat_flag markers emitted.

## Self-Check: PASSED

All claimed files exist on disk:

```
TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/NyraMessageModel.h                    FOUND
TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/NyraMessageModel.cpp                 FOUND
TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraAttachmentChip.h                 FOUND
TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraAttachmentChip.cpp              FOUND
TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraMessageList.h                    FOUND
TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraMessageList.cpp                 FOUND
TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraComposer.h                       FOUND
TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraComposer.cpp                    FOUND
TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraChatPanel.h                      FOUND (modified -- Plan 04 placeholder replaced)
TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp                   FOUND (modified -- Plan 04 placeholder replaced)
TestProject/Plugins/NYRA/Source/NyraEditor/Private/NyraEditorModule.cpp                       FOUND (static -> non-static GNyraSupervisor)
TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp                    FOUND (modified -- AttachmentChip + StreamingBuffer added)
TestProject/Plugins/NYRA/Source/NyraEditor/Public/Markdown/FNyraCodeBlockDecorator.h          FOUND (modified -- FNyraCodeBlockDecoratorImpl promoted)
TestProject/Plugins/NYRA/Source/NyraEditor/Private/Markdown/FNyraCodeBlockDecorator.cpp       FOUND (modified -- in-class -> file-scope method defs)
```

All claimed commits present in `git log --oneline`:

```
2b40c01 FOUND -- Task 1 (message model + attachment chip + streaming message list)
65b3bdc FOUND -- Task 2 (composer + chat panel + supervisor wiring)
```

All 10 Task 1 + 11 Task 2 = 21 grep acceptance literals verified green at source level. Plan 04 tab wiring, Plan 10 supervisor wiring, Plan 11 markdown + decorator pipeline all preserved and integrated. `git diff --diff-filter=D --name-only HEAD~2 HEAD` is empty (no unintended deletions).

Plan 12b / Plan 13 / Plan 14 / Plan 15 ready to consume: `SNyraChatPanel::OpenConversation` + `GetCurrentConversationId` + `OnConversationSelected` + `SNyraMessageList::ClearMessages` + protected virtual `GenerateRow`/`MakeBodyWidget` extension points all in place.
