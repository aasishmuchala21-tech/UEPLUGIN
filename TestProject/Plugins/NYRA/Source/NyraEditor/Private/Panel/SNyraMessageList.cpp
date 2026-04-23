// =============================================================================
// SNyraMessageList.cpp  (Phase 1 Plan 12 -- chat panel streaming integration)
// =============================================================================
//
// Virtualized list of chat rows. Uses SListView<TSharedPtr<FNyraMessage>>
// with ListItemsSource bound to the Messages TArray. GenerateRow is the
// per-row factory applying the RESEARCH Sec 3.1 streaming strategy:
//
//   Status == Done      -> SRichTextBlock + FNyraMarkdownParser tag stream +
//                          FNyraCodeBlockDecoratorImpl for <nyra-code> tags
//   Status == Failed    -> STextBlock in red showing ErrorRemediation (D-11)
//   Status == Cancelled -> STextBlock showing the partial buffer (done frame
//                          also sets FinalContent to the partial buffer)
//   otherwise (Streaming) -> STextBlock showing StreamingBuffer as it grows
//
// Row header: role label (You / NYRA / System / Error) tinted by role +
// optional status badge ("streaming...", "cancelled", "retried").
//
// Extension point for Plan 12b: GenerateRow + MakeBodyWidget are protected
// virtuals so the history-drawer companion plan can override row layout
// (e.g. conversation-title separators) or inject additional decorators
// (heading / link / inline-code) without rewriting the row body.
// =============================================================================

#include "Panel/SNyraMessageList.h"
#include "Markdown/FNyraMarkdownParser.h"
#include "Markdown/FNyraCodeBlockDecorator.h"
#include "Framework/Text/ITextDecorator.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Text/SRichTextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Styling/AppStyle.h"

// FNyraCodeBlockDecoratorImpl is exported from Plan 11's public header
// (FNyraCodeBlockDecorator.h) so SRichTextBlock consumers like this file
// can construct it directly via MakeShared<FNyraCodeBlockDecoratorImpl>()
// without going through the URichTextBlockDecorator UCLASS wrapper.

#define LOCTEXT_NAMESPACE "NyraMessageList"

void SNyraMessageList::Construct(const FArguments& InArgs)
{
    OnCancelDelegate = InArgs._OnCancel;
    ListView = SNew(SListView<TSharedPtr<FNyraMessage>>)
        .ListItemsSource(&Messages)
        .OnGenerateRow(this, &SNyraMessageList::GenerateRow)
        .SelectionMode(ESelectionMode::None);
    ChildSlot
    [
        ListView.ToSharedRef()
    ];
}

void SNyraMessageList::AppendMessage(const TSharedPtr<FNyraMessage>& Msg)
{
    Messages.Add(Msg);
    if (ListView.IsValid())
    {
        ListView->RequestListRefresh();
        ListView->ScrollToBottom();
    }
}

void SNyraMessageList::UpdateMessageStreaming(const FGuid& ReqId, const FString& Delta)
{
    if (TSharedPtr<FNyraMessage> M = FindByReqId(ReqId))
    {
        M->AppendDelta(Delta);
        if (ListView.IsValid())
        {
            // Force the affected row to re-generate -- SListView only rebuilds
            // rows whose source data changed identity, not those whose fields
            // mutated in place, so RequestListRefresh is the cheapest path.
            ListView->RequestListRefresh();
        }
    }
}

void SNyraMessageList::FinalizeMessage(const FGuid& ReqId, const FString& FinalContent, bool bCancelled, const FString& Remediation)
{
    if (TSharedPtr<FNyraMessage> M = FindByReqId(ReqId))
    {
        if (bCancelled)
        {
            M->Status = ENyraMessageStatus::Cancelled;
            // Preserve the partial buffer as FinalContent so the user can still
            // see what streamed up to the cancel point. Per CD-07 cancellation
            // should NEVER discard the partial assistant output.
            M->FinalContent = M->StreamingBuffer;
        }
        else if (!Remediation.IsEmpty())
        {
            M->Status = ENyraMessageStatus::Failed;
            M->ErrorRemediation = Remediation;
            M->FinalContent = M->StreamingBuffer;
        }
        else
        {
            M->Finalize(FinalContent.IsEmpty() ? M->StreamingBuffer : FinalContent);
        }
        if (ListView.IsValid())
        {
            ListView->RequestListRefresh();
        }
    }
}

TSharedPtr<FNyraMessage> SNyraMessageList::FindByReqId(const FGuid& ReqId) const
{
    for (const TSharedPtr<FNyraMessage>& M : Messages)
    {
        if (M.IsValid() && M->ReqId == ReqId) return M;
    }
    return nullptr;
}

void SNyraMessageList::ClearMessages()
{
    Messages.Empty();
    if (ListView.IsValid())
    {
        ListView->RequestListRefresh();
    }
}

TSharedRef<SWidget> SNyraMessageList::MakeBodyWidget(const TSharedPtr<FNyraMessage>& InItem) const
{
    if (!InItem.IsValid())
    {
        return SNullWidget::NullWidget;
    }

    if (InItem->Status == ENyraMessageStatus::Done)
    {
        const FString Markup = FNyraMarkdownParser::MarkdownToRichText(InItem->FinalContent);
        TArray<TSharedRef<ITextDecorator>> Decorators;
        // Phase 1 registers only the nyra-code decorator from Plan 11.
        // Plan 12b may override MakeBodyWidget to add heading/link/inline
        // decorators without rewriting this method.
        Decorators.Add(MakeShared<FNyraCodeBlockDecoratorImpl>());
        return SNew(SRichTextBlock)
            .Text(FText::FromString(Markup))
            .AutoWrapText(true)
            .DecoratorStyleSet(&FAppStyle::Get())
            .Decorators(Decorators);
    }

    if (InItem->Status == ENyraMessageStatus::Failed && !InItem->ErrorRemediation.IsEmpty())
    {
        return SNew(STextBlock)
            .Text(FText::FromString(InItem->ErrorRemediation))
            .ColorAndOpacity(FLinearColor(1.0f, 0.4f, 0.4f))
            .AutoWrapText(true);
    }

    // Streaming / Cancelled / Idle: plain STextBlock on the buffer. Falls
    // back to FinalContent if FinalContent was set but StreamingBuffer is
    // empty (Plan 12b can push snapshotted Done rows whose buffer is empty).
    const FString Txt = InItem->StreamingBuffer.IsEmpty() && !InItem->FinalContent.IsEmpty()
        ? InItem->FinalContent : InItem->StreamingBuffer;
    return SNew(STextBlock)
        .Text(FText::FromString(Txt))
        .AutoWrapText(true);
}

TSharedRef<ITableRow> SNyraMessageList::GenerateRow(TSharedPtr<FNyraMessage> InItem, const TSharedRef<STableViewBase>& OwnerTable)
{
    if (!InItem.IsValid())
    {
        return SNew(STableRow<TSharedPtr<FNyraMessage>>, OwnerTable);
    }

    // Role label + tint
    FText RoleText = LOCTEXT("UserRole", "You");
    FLinearColor RoleColor(0.6f, 0.8f, 1.0f);
    if (InItem->Role == ENyraMessageRole::Assistant)
    {
        RoleText = LOCTEXT("AssistantRole", "NYRA");
        RoleColor = FLinearColor(0.8f, 1.0f, 0.8f);
    }
    else if (InItem->Role == ENyraMessageRole::System)
    {
        RoleText = LOCTEXT("SystemRole", "System");
        RoleColor = FLinearColor(0.7f, 0.7f, 0.7f);
    }
    else if (InItem->Role == ENyraMessageRole::Error)
    {
        RoleText = LOCTEXT("ErrorRole", "Error");
        RoleColor = FLinearColor(1.0f, 0.4f, 0.4f);
    }

    // Status badge suffix (only visible when non-Idle/Done)
    FText StatusBadge;
    if (InItem->Status == ENyraMessageStatus::Streaming)      StatusBadge = LOCTEXT("Streaming", "streaming...");
    else if (InItem->Status == ENyraMessageStatus::Cancelled) StatusBadge = LOCTEXT("Cancelled", "cancelled");
    else if (InItem->Status == ENyraMessageStatus::Retried)   StatusBadge = LOCTEXT("Retried", "retried");

    return SNew(STableRow<TSharedPtr<FNyraMessage>>, OwnerTable)
    .Padding(FMargin(8, 6))
    [
        SNew(SBorder)
        .BorderImage(FAppStyle::GetBrush("NoBorder"))
        [
            SNew(SVerticalBox)
            + SVerticalBox::Slot().AutoHeight()
            [
                SNew(SHorizontalBox)
                + SHorizontalBox::Slot().AutoWidth()
                [
                    SNew(STextBlock)
                    .Text(RoleText)
                    .ColorAndOpacity(RoleColor)
                    .Font(FAppStyle::GetFontStyle(TEXT("BoldFont")))
                ]
                + SHorizontalBox::Slot().AutoWidth().Padding(8, 0, 0, 0)
                [
                    SNew(STextBlock)
                    .Text(StatusBadge)
                    .ColorAndOpacity(FLinearColor(0.6f, 0.6f, 0.6f))
                ]
            ]
            + SVerticalBox::Slot().AutoHeight().Padding(0, 4, 0, 0)
            [
                MakeBodyWidget(InItem)
            ]
        ]
    ];
}

#undef LOCTEXT_NAMESPACE
