// =============================================================================
// FNyraMarkdownParser.h  (Phase 1 Plan 11 -- cpp-markdown-parser)
// =============================================================================
//
// Minimal markdown-subset parser that converts chat-assistant markdown source
// into the Slate rich-text tag stream consumed by SRichTextBlock + custom
// URichTextBlockDecorator stack (Plan 12 wires this into SNyraChatPanel).
//
// Supported subset (per RESEARCH Sec 3.1 + CONTEXT CD-06):
//   Headings       #, ##, ###         -> <heading level="1|2|3">...</heading>
//   Bold           **x**              -> <bold>x</bold>
//   Italic         *x*                -> <italic>x</italic>
//   Inline code    `x`                -> <code>x</code>
//   Link           [t](url)           -> <link url="url">t</link>
//   UL item        - x / * x          -> "\x2022 x\n"   (bullet char)
//   Fenced code    ```lang\n...\n``` -> <nyra-code lang="lang">body</nyra-code>
//
// Everything else is emitted as plain text with HTML-style char escaping
// (<  ->  &lt;,  >  ->  &gt;,  &  ->  &amp;) so user-typed angle brackets
// never collide with the Slate tag parser downstream.
//
// Scope exclusions (Phase 1):
//   - No tables
//   - No images
//   - No raw HTML passthrough
//   - No nested lists / ordered lists
//   - No reference-style links
//   - No setext (underline) headings
// =============================================================================
#pragma once

#include "CoreMinimal.h"

/**
 * Static parser for the Phase-1 markdown subset.
 *
 * Output is a Slate rich-text tag string ready to feed
 * SRichTextBlock::SetText with the decorator stack defined by
 * UNyraCodeBlockDecorator (Plan 11 Task 2) plus any future
 * heading/link/inline decorators Plan 12 adds.
 *
 * All methods are stateless + pure; safe to call on the GameThread during
 * chat/stream done:true finalisation per RESEARCH Sec 3.1 streaming
 * strategy (plain STextBlock during stream, rich on done).
 */
class NYRAEDITOR_API FNyraMarkdownParser
{
public:
    /** Convert a markdown source string to Slate RichText tag markup. */
    static FString MarkdownToRichText(const FString& Source);

    /** Escape < > & for embedding into RichText markup outside tags. */
    static FString EscapeRichText(const FString& Raw);
};
