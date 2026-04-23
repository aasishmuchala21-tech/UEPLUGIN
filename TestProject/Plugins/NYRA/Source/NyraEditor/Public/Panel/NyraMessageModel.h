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

/** Attachment reference (Phase 1 forwards paths; does NOT upload). */
struct NYRAEDITOR_API FNyraAttachmentRef
{
    FString AbsolutePath;
    FString DisplayName;
    int64 SizeBytes = 0;
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
