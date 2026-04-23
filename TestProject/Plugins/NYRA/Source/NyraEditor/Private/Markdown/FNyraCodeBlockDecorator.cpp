// =============================================================================
// FNyraCodeBlockDecorator.cpp  (Phase 1 Plan 11 -- cpp-markdown-parser)
// =============================================================================
//
// URichTextBlockDecorator implementation that materialises <nyra-code> tags
// emitted by FNyraMarkdownParser into an inline Slate widget (SBorder
// wrapping a two-slot SVerticalBox: header row + monospace body).
//
// Lifetime:
//   - UNyraCodeBlockDecorator::CreateDecorator returns a new
//     FNyraCodeBlockDecoratorImpl shared instance per RichTextBlock;
//   - Supports() gates the decorator to RunInfo.Name == "nyra-code";
//   - Create() captures the fenced-code body + lang from the parse result,
//     then builds a FSlateWidgetRun hosting MakeCodeBlockWidget(body, lang).
//
// Copy button contract (CONTEXT CD-06):
//   FPlatformApplicationMisc::ClipboardCopy(*BodyCopy) writes the RAW body
//   (no rich-text tags) to the system clipboard. Captured by value in the
//   OnClicked lambda so the widget survives the decorator's lifetime.
// =============================================================================

#include "Markdown/FNyraCodeBlockDecorator.h"
#include "Components/RichTextBlock.h"
#include "Framework/Text/ITextDecorator.h"
#include "Framework/Text/SlateTextRun.h"
#include "Framework/Text/SlateWidgetRun.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Styling/AppStyle.h"
#include "HAL/PlatformApplicationMisc.h"

#define LOCTEXT_NAMESPACE "NyraCodeBlock"

namespace
{
    /** Build the Slate widget rendered in place of a <nyra-code> tag run. */
    TSharedRef<SWidget> MakeCodeBlockWidget(const FString& InBody, const FString& InLang)
    {
        // Capture-by-value so the OnClicked lambda outlives the decorator call.
        const FString BodyCopy = InBody;

        const FText LangText = FText::FromString(InLang.IsEmpty() ? TEXT("code") : InLang);

        return SNew(SBorder)
            .BorderImage(FAppStyle::GetBrush("ToolPanel.GroupBorder"))
            .Padding(8.f)
            [
                SNew(SVerticalBox)

                // Header row: language label (left) + Copy button (right).
                + SVerticalBox::Slot()
                .AutoHeight()
                [
                    SNew(SHorizontalBox)
                    + SHorizontalBox::Slot()
                    .FillWidth(1.0f)
                    [
                        SNew(STextBlock)
                        .Text(LangText)
                        .ColorAndOpacity(FLinearColor(0.5f, 0.5f, 0.5f))
                    ]
                    + SHorizontalBox::Slot()
                    .AutoWidth()
                    [
                        SNew(SButton)
                        .Text(LOCTEXT("CopyLabel", "Copy"))
                        .OnClicked_Lambda([BodyCopy]() -> FReply
                        {
                            FPlatformApplicationMisc::ClipboardCopy(*BodyCopy);
                            return FReply::Handled();
                        })
                    ]
                ]

                // Body row: monospace + auto-wrap.
                + SVerticalBox::Slot()
                .AutoHeight()
                .Padding(0, 8, 0, 0)
                [
                    SNew(STextBlock)
                    .Text(FText::FromString(InBody))
                    .Font(FAppStyle::GetFontStyle(TEXT("MonospacedText")))
                    .AutoWrapText(true)
                ]
            ];
    }
}  // anonymous namespace

/**
 * Actual Slate ITextDecorator that the RichTextBlock parser hands parse
 * results to. Gates on RunInfo.Name == "nyra-code" and emits a
 * FSlateWidgetRun wrapping the code-block widget.
 */
class FNyraCodeBlockDecoratorImpl : public ITextDecorator
{
public:
    virtual bool Supports(const FTextRunParseResults& RunInfo, const FString& Text) const override
    {
        return RunInfo.Name == TEXT("nyra-code");
    }

    virtual TSharedRef<ISlateRun> Create(
        const TSharedRef<FTextLayout>& TextLayout,
        const FTextRunParseResults& RunParseResult,
        const FString& OriginalText,
        const TSharedRef<FString>& InOutModelText,
        const ISlateStyle* Style) override
    {
        // Extract raw fenced-code body (between the opening-tag '>' and
        // the closing </nyra-code>).
        const FString Body = OriginalText.Mid(
            RunParseResult.ContentRange.BeginIndex,
            RunParseResult.ContentRange.EndIndex - RunParseResult.ContentRange.BeginIndex);

        // Extract the lang="..." meta attribute, if present.
        FString Lang;
        if (const FTextRange* Found = RunParseResult.MetaData.Find(TEXT("lang")))
        {
            Lang = OriginalText.Mid(
                Found->BeginIndex,
                Found->EndIndex - Found->BeginIndex);
        }

        // Assemble FRunInfo for the widget run.
        FRunInfo RunInfo(RunParseResult.Name);
        RunInfo.MetaData.Add(TEXT("lang"), Lang);

        // Reserve one zero-width character in the model so the layout
        // engine has a cursor position corresponding to the widget run.
        InOutModelText->Append(TEXT("\x200B"));
        const FTextRange ModelRange(InOutModelText->Len() - 1, InOutModelText->Len());

        return FSlateWidgetRun::Create(
            TextLayout,
            RunInfo,
            InOutModelText,
            FSlateWidgetRun::FWidgetRunInfo(
                MakeCodeBlockWidget(Body, Lang),
                /*InBaselinePercent=*/16.f),
            ModelRange);
    }
};

UNyraCodeBlockDecorator::UNyraCodeBlockDecorator() = default;

TSharedPtr<ITextDecorator> UNyraCodeBlockDecorator::CreateDecorator(URichTextBlock* InOwner)
{
    return MakeShared<FNyraCodeBlockDecoratorImpl>();
}

#undef LOCTEXT_NAMESPACE
