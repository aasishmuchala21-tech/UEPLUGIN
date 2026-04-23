// =============================================================================
// FNyraMarkdownParser.cpp  (Phase 1 Plan 11 -- cpp-markdown-parser)
// =============================================================================
//
// Implementation of FNyraMarkdownParser::MarkdownToRichText + EscapeRichText.
//
// Block-level dispatch (in order of precedence per line):
//   1. Fenced code block opener:   line.StartsWith("```")   -> consume until
//                                   next "```" line; emit
//                                   <nyra-code lang="...">body</nyra-code>
//                                   with RAW body (no inline parsing inside)
//   2. H3:                         line.StartsWith("### ")
//   3. H2:                         line.StartsWith("## ")
//   4. H1:                         line.StartsWith("# ")
//   5. UL item:                    line.StartsWith("- ") || "* "
//   6. Blank line:                 -> "\n"
//   7. Regular paragraph line:     run ParseInline()
//
// Inline dispatch (recursive, inside a single line):
//   1. Inline code `x`     -> <code>ESCAPED(x)</code>   (body NOT recursively parsed)
//   2. Bold **x**          -> <bold>ParseInline(x)</bold>
//   3. Italic *x*          -> <italic>ParseInline(x)</italic>
//      (NOT triggered when prefix is "**")
//   4. Link [text](url)    -> <link url="ESCAPED(url)">ParseInline(text)</link>
//   5. Otherwise AppendEscaped(Ch)
//
// Character escape policy (RESEARCH Sec 3.1 + UE RichText grammar):
//   -  <  ->  &lt;
//   -  >  ->  &gt;
//   -  &  ->  &amp;
// Applied in: plain text segments, inline-code body, fenced-code body,
// link URL attribute value. Markdown-specific markers (*, _, `, [, ]) are
// NOT escaped because they are consumed by the parser structurally.
// =============================================================================

#include "Markdown/FNyraMarkdownParser.h"

namespace
{
    /** True when S has Needle as a substring starting at Idx. */
    bool StartsWith(const FString& S, int32 Idx, const TCHAR* Needle)
    {
        const int32 NLen = FCString::Strlen(Needle);
        if (Idx + NLen > S.Len())
        {
            return false;
        }
        return FCString::Strncmp(*S + Idx, Needle, NLen) == 0;
    }

    /** Append a single character with HTML-style escape for <, >, &. */
    void AppendEscaped(FString& Out, const TCHAR Ch)
    {
        switch (Ch)
        {
        case TCHAR('<'): Out.Append(TEXT("&lt;")); break;
        case TCHAR('>'): Out.Append(TEXT("&gt;")); break;
        case TCHAR('&'): Out.Append(TEXT("&amp;")); break;
        default:         Out.AppendChar(Ch); break;
        }
    }

    /** Return S[Start..End) with each character passed through AppendEscaped. */
    FString EscapedSegment(const FString& S, int32 Start, int32 End)
    {
        FString Out;
        Out.Reserve((End - Start) + 4);
        for (int32 I = Start; I < End; ++I)
        {
            AppendEscaped(Out, S[I]);
        }
        return Out;
    }

    /**
     * Parse inline formatting inside a single line (already newline-stripped).
     * Handles inline code, **bold**, *italic*, [text](url). Recursive for
     * bold/italic/link body; inline-code body is NOT recursively parsed
     * (the whole point of inline code is to suppress further markdown).
     */
    FString ParseInline(const FString& Line)
    {
        FString Out;
        const int32 Len = Line.Len();
        int32 I = 0;
        while (I < Len)
        {
            // Inline code `x`  (body NOT recursively parsed, only escaped).
            if (Line[I] == TCHAR('`'))
            {
                const int32 CloseIdx = Line.Find(
                    TEXT("`"),
                    ESearchCase::CaseSensitive,
                    ESearchDir::FromStart,
                    I + 1);
                if (CloseIdx != INDEX_NONE)
                {
                    Out.Append(TEXT("<code>"));
                    Out.Append(EscapedSegment(Line, I + 1, CloseIdx));
                    Out.Append(TEXT("</code>"));
                    I = CloseIdx + 1;
                    continue;
                }
            }

            // Bold **x**  (body recursively parsed).
            if (StartsWith(Line, I, TEXT("**")))
            {
                const int32 CloseIdx = Line.Find(
                    TEXT("**"),
                    ESearchCase::CaseSensitive,
                    ESearchDir::FromStart,
                    I + 2);
                if (CloseIdx != INDEX_NONE)
                {
                    Out.Append(TEXT("<bold>"));
                    Out.Append(ParseInline(Line.Mid(I + 2, CloseIdx - (I + 2))));
                    Out.Append(TEXT("</bold>"));
                    I = CloseIdx + 2;
                    continue;
                }
            }

            // Italic *x*  (single-star; NOT triggered when prefix is "**").
            // Also require the closing star NOT to be immediately followed by
            // another star (which would make the close actually a bold marker).
            if (Line[I] == TCHAR('*') && !StartsWith(Line, I, TEXT("**")))
            {
                const int32 CloseIdx = Line.Find(
                    TEXT("*"),
                    ESearchCase::CaseSensitive,
                    ESearchDir::FromStart,
                    I + 1);
                if (CloseIdx != INDEX_NONE
                    && (CloseIdx + 1 >= Len || Line[CloseIdx + 1] != TCHAR('*')))
                {
                    Out.Append(TEXT("<italic>"));
                    Out.Append(ParseInline(Line.Mid(I + 1, CloseIdx - (I + 1))));
                    Out.Append(TEXT("</italic>"));
                    I = CloseIdx + 1;
                    continue;
                }
            }

            // Link [text](url).
            if (Line[I] == TCHAR('['))
            {
                const int32 CloseBracket = Line.Find(
                    TEXT("]"),
                    ESearchCase::CaseSensitive,
                    ESearchDir::FromStart,
                    I + 1);
                if (CloseBracket != INDEX_NONE
                    && CloseBracket + 1 < Len
                    && Line[CloseBracket + 1] == TCHAR('('))
                {
                    const int32 CloseParen = Line.Find(
                        TEXT(")"),
                        ESearchCase::CaseSensitive,
                        ESearchDir::FromStart,
                        CloseBracket + 2);
                    if (CloseParen != INDEX_NONE)
                    {
                        const FString Text = Line.Mid(I + 1, CloseBracket - (I + 1));
                        const FString Url = Line.Mid(
                            CloseBracket + 2,
                            CloseParen - (CloseBracket + 2));
                        Out.Append(TEXT("<link url=\""));
                        Out.Append(EscapedSegment(Url, 0, Url.Len()));
                        Out.Append(TEXT("\">"));
                        Out.Append(ParseInline(Text));
                        Out.Append(TEXT("</link>"));
                        I = CloseParen + 1;
                        continue;
                    }
                }
            }

            // Plain character (with HTML-escape for <, >, &).
            AppendEscaped(Out, Line[I]);
            ++I;
        }
        return Out;
    }
}  // anonymous namespace

FString FNyraMarkdownParser::EscapeRichText(const FString& Raw)
{
    FString Out;
    Out.Reserve(Raw.Len() + 8);
    for (int32 I = 0; I < Raw.Len(); ++I)
    {
        AppendEscaped(Out, Raw[I]);
    }
    return Out;
}

FString FNyraMarkdownParser::MarkdownToRichText(const FString& Source)
{
    FString Out;
    Out.Reserve(Source.Len() + 64);

    TArray<FString> Lines;
    Source.ParseIntoArray(Lines, TEXT("\n"), /*InCullEmpty=*/false);

    int32 I = 0;
    while (I < Lines.Num())
    {
        FString Line = Lines[I];

        // Strip trailing \r (Windows CRLF newlines arrive with \r attached).
        if (Line.EndsWith(TEXT("\r"), ESearchCase::CaseSensitive))
        {
            Line.LeftChopInline(1, false);
        }

        // 1. Fenced code block opener:  ```lang  (or just  ```  ).
        //    Body is accumulated verbatim until the next "```" line;
        //    NO inline parsing is applied inside (so asterisks + brackets
        //    in code survive literally).
        if (Line.StartsWith(TEXT("```")))
        {
            FString Lang = Line.Mid(3).TrimStartAndEnd();
            FString Body;
            ++I;
            while (I < Lines.Num())
            {
                FString InnerLine = Lines[I];
                if (InnerLine.EndsWith(TEXT("\r"), ESearchCase::CaseSensitive))
                {
                    InnerLine.LeftChopInline(1, false);
                }
                if (InnerLine.StartsWith(TEXT("```")))
                {
                    ++I;
                    break;
                }
                Body.Append(InnerLine);
                Body.Append(TEXT("\n"));
                ++I;
            }
            Out.Append(TEXT("<nyra-code lang=\""));
            Out.Append(FNyraMarkdownParser::EscapeRichText(Lang));
            Out.Append(TEXT("\">"));
            Out.Append(FNyraMarkdownParser::EscapeRichText(Body));
            Out.Append(TEXT("</nyra-code>"));
            continue;
        }

        // 2. Heading dispatch (longest prefix first so H3 wins over H2/H1).
        if (Line.StartsWith(TEXT("### ")))
        {
            Out.Append(TEXT("<heading level=\"3\">"));
            Out.Append(ParseInline(Line.Mid(4)));
            Out.Append(TEXT("</heading>\n"));
        }
        else if (Line.StartsWith(TEXT("## ")))
        {
            Out.Append(TEXT("<heading level=\"2\">"));
            Out.Append(ParseInline(Line.Mid(3)));
            Out.Append(TEXT("</heading>\n"));
        }
        else if (Line.StartsWith(TEXT("# ")))
        {
            Out.Append(TEXT("<heading level=\"1\">"));
            Out.Append(ParseInline(Line.Mid(2)));
            Out.Append(TEXT("</heading>\n"));
        }
        // 3. Unordered list item (either "- " or "* " prefix).
        else if (Line.StartsWith(TEXT("- ")) || Line.StartsWith(TEXT("* ")))
        {
            // "•" = U+2022 BULLET  (one glyph, rendered by the default Slate font)
            Out.Append(TEXT("• "));
            Out.Append(ParseInline(Line.Mid(2)));
            Out.Append(TEXT("\n"));
        }
        // 4. Blank line -- preserve the hard line break so paragraph
        //    separation survives the inline-merge pass downstream.
        else if (Line.IsEmpty())
        {
            Out.Append(TEXT("\n"));
        }
        // 5. Regular paragraph line.
        else
        {
            Out.Append(ParseInline(Line));
            Out.Append(TEXT("\n"));
        }
        ++I;
    }
    return Out;
}
