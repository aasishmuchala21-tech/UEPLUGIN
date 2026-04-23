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
#include "FNyraCodeBlockDecorator.generated.h"

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
