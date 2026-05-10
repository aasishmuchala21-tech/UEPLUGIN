// =============================================================================
// NyraMessageModel.h  (Phase 1 Plan 12 -- chat panel streaming integration)
// =============================================================================
//
// Slate-side message data model backing SNyraMessageList. NOT a UObject --
// the chat panel does not need reflection or GC for in-memory message rows.
// Each row is owned by a TSharedPtr<FNyraMessage> stored in the list view's
// ItemsSource array.
//
// Streaming strategy (RESEARCH Sec 3.1):
//   - During stream: StreamingBuffer is appended via AppendDelta; Slate
//     renders the buffer in a plain STextBlock.
//   - On done=true: FinalContent is set (usually == StreamingBuffer) and
//     Status flips to Done; Slate swaps the row to a SRichTextBlock with
//     FNyraMarkdownParser::MarkdownToRichText applied.
//   - On error frame: Status=Failed + ErrorRemediation is rendered verbatim
//     in red (D-11 error.data.remediation).
//   - On chat/cancel: Status=Cancelled; FinalContent captures the partial
//     StreamingBuffer so the user still sees what streamed before cancel.
//
// ReqId policy: the user message and its corresponding assistant message
// share the SAME ReqId so chat/stream notifications can be routed to the
// correct row via SNyraMessageList::FindByReqId. See SNyraChatPanel.cpp
// OnComposerSubmit for the pairing.
//
// Plan 12b (history-drawer) consumes this model read-only when loading a
// sessions/load snapshot into SNyraChatPanel::OpenConversation -- it does
// not introduce new fields.
// =============================================================================

#pragma once

#include "CoreMinimal.h"

/** Role of a chat message row. */
enum class ENyraMessageRole : uint8
{
    User,
    Assistant,
    System,
    Error,
};

/** Lifecycle status of a chat message row. Drives the render strategy in
 *  SNyraMessageList::GenerateRow (plain STextBlock for Streaming/Cancelled,
 *  SRichTextBlock for Done, red STextBlock for Failed). */
enum class ENyraMessageStatus : uint8
{
    Idle,
    Streaming,
    Done,
    Cancelled,
    Retried,  // original after supervisor respawn-replay (Plan 10 P1.7)
    Failed,   // error frame ended stream
};

/** Kind discriminator for FNyraAttachmentRef.
 *
 *  Phase 1 only had image/text/video drops via the FDesktopPlatform picker
 *  and the SNyraImageDropZone external-file path. Phase 8 extends:
 *
 *    - Plan 08-01 (PARITY-01) adds Document (PDF/DOCX/PPTX/XLSX/HTML/MD)
 *      so document attachments flow through the same chip row + JSONRPC
 *      attachment shape with extracted text + embedded-image re-ingestion.
 *    - Plan 08-04 (PARITY-04) adds Asset for drag-from-Content-Browser
 *      payloads. Asset attachments carry both AssetPath (/Game/...) and
 *      AssetClass (StaticMesh / Material / Blueprint / ...) so NyraHost
 *      can interpret them per-tool without round-tripping a path lookup.
 *
 *  LOCKED-10 co-ownership note: Document and Asset enum values are added
 *  by Plan 08-01 and Plan 08-04 respectively. Order is plan-number first
 *  (Document then Asset). New consumers must handle every value defensively.
 */
enum class ENyraAttachmentKind : uint8
{
    Image,
    Text,
    Video,
    Document,   // Plan 08-01 (PARITY-01) — co-owned with 08-04 per LOCKED-10
    Asset,      // Plan 08-04 (PARITY-04) — drag from UE Content Browser
};

/** Attachment reference (Phase 1 forwards paths; does NOT upload).
 *
 *  Plan 08-04 (PARITY-04) extension: when Kind == Asset, AssetPath and
 *  AssetClass carry the structured FAssetData fields captured at drop
 *  time (see SNyraImageDropZone::OnDrop -> SNyraComposer::HandleAssetDropped).
 *  AbsolutePath stays empty for Asset kind because /Game/... isn't a
 *  filesystem path -- the asset lives inside a UE .uasset and NyraHost
 *  resolves it via unreal.EditorAssetLibrary.load_asset(AssetPath) on
 *  the editor side.
 *
 *  JSON serialization note: this struct currently has no inline ToJson /
 *  FromJson methods. The existing chat/send pipeline (SNyraChatPanel::
 *  OnComposerSubmit) does NOT yet forward attachments over JSONRPC --
 *  that's Plan 08-01's scope. Plan 08-04 wires the new delegate +
 *  populates the new fields; the JSON emission path that consumes them
 *  lands with 08-01.
 */
struct NYRAEDITOR_API FNyraAttachmentRef
{
    /** Plan 08-01/08-04: kind discriminator. Default Image preserves the
     *  Phase 1 contract for existing 3-field initializers (composer +
     *  chip + tests rely on AbsolutePath/DisplayName/SizeBytes only). */
    ENyraAttachmentKind Kind = ENyraAttachmentKind::Image;

    FString AbsolutePath;
    FString DisplayName;
    int64 SizeBytes = 0;

    /** Plan 08-04: /Game/... object path for Asset kind. Empty otherwise. */
    FString AssetPath;
    /** Plan 08-04: short asset class name (StaticMesh / Material / ...).
     *  Empty when Kind != Asset. Sourced from FAssetData::AssetClassPath. */
    FString AssetClass;
};

/**
 * Slate-side message model -- NOT a UObject. Lives in the list view's
 * TArray<TSharedPtr<FNyraMessage>>.
 *
 * Field ownership:
 *   - MessageId       : unique id for the row (never collides with ReqId)
 *   - ConversationId  : links the row to SNyraChatPanel::CurrentConversationId
 *   - ReqId           : shared by the user request row AND its assistant reply
 *                       row so chat/stream notifications route via FindByReqId
 *   - Role            : User/Assistant/System/Error -- drives header label
 *   - Status          : Idle/Streaming/Done/Cancelled/Retried/Failed
 *   - StreamingBuffer : in-progress text appended by chat/stream deltas
 *   - FinalContent    : text captured at done:true (usually markdown source)
 *   - ErrorRemediation: error.data.remediation text rendered verbatim for Failed rows
 *   - Attachments     : paths the user dragged/picked for the prompt
 */
struct NYRAEDITOR_API FNyraMessage
{
    FGuid MessageId;
    FGuid ConversationId;
    FGuid ReqId;  // assigned when sent as user msg; reused on corresponding assistant reply
    ENyraMessageRole Role = ENyraMessageRole::User;
    ENyraMessageStatus Status = ENyraMessageStatus::Idle;
    FString StreamingBuffer;   // in-progress text during streaming (plain)
    FString FinalContent;      // text captured on Done (markdown source)
    FString ErrorRemediation;  // rendered verbatim for Failed rows
    TArray<FNyraAttachmentRef> Attachments;

    /** Append a chat/stream delta frame to the streaming buffer. */
    void AppendDelta(const FString& Delta)
    {
        StreamingBuffer.Append(Delta);
    }

    /** Finalize the message on chat/stream done:true. */
    void Finalize(const FString& Content)
    {
        FinalContent = Content;
        Status = ENyraMessageStatus::Done;
    }
};
