// =============================================================================
// FNyraCodeBlockDecorator.h  (Phase 1 Plan 11 -- cpp-markdown-parser)
// =============================================================================
//
// URichTextBlockDecorator subclass that handles the <nyra-code> tag emitted
// by FNyraMarkdownParser (Plan 11 Task 1). Renders a monospace code block
// with a header row (language label + [Copy] button) inside an SBorder
// styled with the editor's ToolPanel.GroupBorder brush.
//
// Registered on Plan 12's SNyraChatPanel's URichTextBlock as follows:
//
//     RichText->SetDecorators({
//         UNyraCodeBlockDecorator::StaticClass(),
//         // ...plus any future heading/inline decorators...
//     });
//
// The [Copy] button invokes FPlatformApplicationMisc::ClipboardCopy on the
// raw fenced-code body, satisfying CONTEXT CD-06 ("Code blocks must have a
// copy button"). No syntax highlighting in Phase 1 -- the language label
// is informational only.
// =============================================================================
#pragma once

#include "CoreMinimal.h"
#include "Components/RichTextBlockDecorator.h"
#include "Framework/Text/ITextDecorator.h"
#include "FNyraCodeBlockDecorator.generated.h"

class FTextLayout;
struct FTextRunParseResults;
class ISlateStyle;
class ISlateRun;

/**
 * Decorator that handles <nyra-code lang="python">raw body</nyra-code>
 * tags emitted by FNyraMarkdownParser. Renders a monospace text box with
 * a [Copy] button in the top-right.
 */
UCLASS()
class NYRAEDITOR_API UNyraCodeBlockDecorator : public URichTextBlockDecorator
{
    GENERATED_BODY()
public:
    UNyraCodeBlockDecorator();

    virtual TSharedPtr<ITextDecorator> CreateDecorator(URichTextBlock* InOwner) override;
};

/**
 * ITextDecorator used by SRichTextBlock to materialise <nyra-code> tags
 * into inline Slate widgets. Exposed via the public header so Plan 12's
 * SNyraMessageList (using SRichTextBlock, not URichTextBlock) can add it
 * directly to the Decorators array without going through the UCLASS
 * wrapper:
 *
 *     TArray<TSharedRef<ITextDecorator>> Decorators;
 *     Decorators.Add(MakeShared<FNyraCodeBlockDecoratorImpl>());
 *     SRichTextBlock::Decorators(Decorators)
 *
 * The UNyraCodeBlockDecorator UCLASS wrapper remains the canonical path
 * for URichTextBlock consumers (Plan 12b history-drawer UMG path).
 */
class NYRAEDITOR_API FNyraCodeBlockDecoratorImpl : public ITextDecorator
{
public:
    virtual bool Supports(const FTextRunParseResults& RunInfo, const FString& Text) const override;

    virtual TSharedRef<ISlateRun> Create(
        const TSharedRef<FTextLayout>& TextLayout,
        const FTextRunParseResults& RunParseResult,
        const FString& OriginalText,
        const TSharedRef<FString>& InOutModelText,
        const ISlateStyle* Style) override;
};
