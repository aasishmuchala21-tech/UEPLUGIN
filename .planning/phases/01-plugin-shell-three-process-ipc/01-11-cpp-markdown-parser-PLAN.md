---
phase: 01-plugin-shell-three-process-ipc
plan: 11
type: execute
wave: 3
depends_on: [01, 03]
autonomous: true
requirements: [CHAT-01]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Markdown/FNyraMarkdownParser.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Markdown/FNyraMarkdownParser.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Markdown/FNyraCodeBlockDecorator.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Markdown/FNyraCodeBlockDecorator.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraMarkdownSpec.cpp
objective: >
  Implement a minimal C++ markdown subset parser that converts Markdown
  source into Slate rich-text tag stream consumable by SRichTextBlock +
  custom URichTextBlockDecorator. Scope per RESEARCH §3.1: headings
  (#, ##, ###), bold (**), italic (*), inline code (`), fenced code blocks
  (```lang), links [text](url), unordered lists (- / *). No tables, no
  images, no HTML. Plus a custom `<nyra-code lang="python">...</nyra-code>`
  tag for the Slate code-block decorator (with copy button). Fills VALIDATION
  rows 1-04-02 (Nyra.Markdown.FencedCode) and 1-04-03
  (Nyra.Markdown.InlineFormatting).
must_haves:
  truths:
    - "FNyraMarkdownParser::MarkdownToRichText('# Hello') contains a rich-text bold/large heading tag"
    - "FNyraMarkdownParser::MarkdownToRichText(3-backtick fenced code with lang=python and body) produces a <nyra-code lang=\"python\">...</nyra-code> tag with the raw body preserved (including newlines)"
    - "Inline code `x` produces <code>x</code>; bold **x** produces <bold>x</bold>; italic *x* produces <italic>x</italic>"
    - "Links [text](https://x) produce <link url=\"https://x\">text</link>"
    - "Unordered list lines starting with '- ' or '* ' produce \\u2022 prefix (bullet char) with surrounding newline"
    - "Code-block decorator subclass compiles and registers for the 'nyra-code' tag"
    - "Nyra.Markdown.FencedCode + Nyra.Markdown.InlineFormatting automation tests pass"
  artifacts:
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/Markdown/FNyraMarkdownParser.h
      provides: "Static parser MarkdownToRichText + enum of supported tokens"
      exports: ["FNyraMarkdownParser"]
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/Markdown/FNyraCodeBlockDecorator.h
      provides: "URichTextBlockDecorator subclass handling <nyra-code>"
      exports: ["UNyraCodeBlockDecorator"]
  key_links:
    - from: FNyraMarkdownParser::MarkdownToRichText
      to: SRichTextBlock (consumed in Plan 12 chat panel)
      via: "Produces RichText format tags that SRichTextBlock decorators parse"
      pattern: "<nyra-code"
---

<objective>
CHAT-01 quality requirement: "streaming tokens, markdown rendering, code
blocks". Plan 11 is the markdown half; Plan 12 wires it into SNyraChatPanel.

Per RESEARCH §3.1:
- Primary widget: SRichTextBlock + custom URichTextBlockDecorator stack
- Scope: headings, bold/italic, inline code, fenced code, links, unordered lists
- Custom tag: `<nyra-code lang="python">...</nyra-code>` for code-block widget
  (which has a copy button). Epic canonical sample:
  `github.com/Nauja/ue4-richtextblocktooltip-sample`.
- ~500 LOC hand-rolled parser is acceptable for Phase 1 (md4c is an
  alternative but CommonMark strictness is overkill).

Streaming strategy (Plan 12 wires): plain STextBlock during stream, swap to
SRichTextBlock + this parser on done. Parser therefore does NOT need incremental
mode — one-shot batch per message is fine.

Purpose: SRichTextBlock needs a markdown-to-rich-text translator; this is it.
Output: Parser + decorator + 2 automation test suites green.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md
@TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraMarkdownSpec.cpp
@TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs
</context>

<interfaces>
UE RichText tag format (what SRichTextBlock consumes with decorators):
- Inline formatting tags: `<bold>x</bold>`, `<italic>x</italic>`, `<code>x</code>`
- Link tag (custom): `<link url="https://x">text</link>`
- Custom code block: `<nyra-code lang="python">... raw body ...</nyra-code>`
- Headings map to style variants of plain text (no dedicated tag — decorators
  or SRichTextBlock style names handle this). For Phase 1 we map:
  - `# H1` → `<heading level="1">H1</heading>`
  - `## H2` → `<heading level="2">H2</heading>`
  - `### H3` → `<heading level="3">H3</heading>`

URichTextBlockDecorator skeleton (UE 5.6):
```cpp
#include "Components/RichTextBlockDecorator.h"

UCLASS()
class UNyraCodeBlockDecorator : public URichTextBlockDecorator
{
    GENERATED_BODY()
public:
    virtual TSharedPtr<ITextDecorator> CreateDecorator(URichTextBlock* InOwner) override;
};

class FNyraCodeBlockDecoratorImpl : public ITextDecorator
{
public:
    virtual bool Supports(const FTextRunParseResults& RunInfo, const FString& Text) const override
    {
        return RunInfo.Name == TEXT("nyra-code");
    }
    virtual TSharedRef<ISlateRun> Create(...) override { /* build widget */ }
};
```
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: FNyraMarkdownParser + NyraMarkdownSpec</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraEditor/Public/Markdown/FNyraMarkdownParser.h
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Markdown/FNyraMarkdownParser.cpp
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraMarkdownSpec.cpp
  </files>
  <read_first>
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.1 "Markdown parser choice" section
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraMarkdownSpec.cpp (Plan 01 placeholder)
    - TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs (Slate/SlateCore already in deps)
  </read_first>
  <behavior>
    - test_headings: `# H1\n## H2\n### H3\n` → contains `<heading level="1">H1</heading>`, same for level 2 and 3; body text after last heading preserved.
    - test_bold_italic_inline_code: `**b**`, `*i*`, `` `c` `` produce `<bold>b</bold>`, `<italic>i</italic>`, `<code>c</code>`.
    - test_link: `[NYRA](https://nyra.ai)` → `<link url="https://nyra.ai">NYRA</link>`.
    - test_unordered_list: lines `- a\n- b` produce bullet characters (`• a\n• b`).
    - test_fenced_code_block: 3-backtick ```` ```python\nprint("x")\n``` ```` → `<nyra-code lang="python">print("x")\n</nyra-code>` with body preserved.
    - test_fenced_code_no_lang: ```` ```\ncode\n``` ```` → `<nyra-code lang="">code\n</nyra-code>`.
    - test_inline_inside_fenced_is_not_parsed: body inside triple-backticks is not further parsed (no <bold> inside code).
    - test_escape_special_chars: `<` in source text is escaped to `&lt;` etc. to avoid collision with Slate tag parsing.
  </behavior>
  <action>
    **1. CREATE Public/Markdown/FNyraMarkdownParser.h:**

    ```cpp
    #pragma once
    #include "CoreMinimal.h"

    class NYRAEDITOR_API FNyraMarkdownParser
    {
    public:
        /** Convert a markdown source string to Slate RichText tag markup.
         *
         * Supported subset (Phase 1):
         *   Headings:    #, ##, ###    -> <heading level="1|2|3">...</heading>
         *   Bold:        **x**          -> <bold>x</bold>
         *   Italic:      *x*            -> <italic>x</italic>
         *   Inline code: `x`            -> <code>x</code>
         *   Link:        [t](url)       -> <link url="url">t</link>
         *   UL item:     - x, * x       -> "• x\n"
         *   Fenced code: ```lang\n...\n``` -> <nyra-code lang="lang">raw-body</nyra-code>
         *
         * Everything else is emitted as plain text with HTML-style char
         * escaping (< -> &lt;, > -> &gt;, & -> &amp;).
         */
        static FString MarkdownToRichText(const FString& Source);

        /** Escape < > & for embedding into RichText markup outside tags. */
        static FString EscapeRichText(const FString& Raw);
    };
    ```

    **2. CREATE Private/Markdown/FNyraMarkdownParser.cpp:**

    ```cpp
    #include "Markdown/FNyraMarkdownParser.h"

    namespace
    {
        bool StartsWith(const FString& S, int32 Idx, const TCHAR* Needle)
        {
            const int32 NLen = FCString::Strlen(Needle);
            if (Idx + NLen > S.Len()) return false;
            return FCString::Strncmp(*S + Idx, Needle, NLen) == 0;
        }

        void AppendEscaped(FString& Out, const TCHAR Ch)
        {
            switch (Ch)
            {
            case TCHAR('<'): Out.Append(TEXT("&lt;")); break;
            case TCHAR('>'): Out.Append(TEXT("&gt;")); break;
            case TCHAR('&'): Out.Append(TEXT("&amp;")); break;
            default: Out.AppendChar(Ch); break;
            }
        }

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

        /** Parse inline formatting inside a single line (already newline-stripped).
         *  Handles **bold**, *italic*, `inline code`, [link](url). */
        FString ParseInline(const FString& Line)
        {
            FString Out;
            const int32 Len = Line.Len();
            int32 I = 0;
            while (I < Len)
            {
                // Inline code `x`
                if (Line[I] == TCHAR('`'))
                {
                    const int32 CloseIdx = Line.Find(TEXT("`"), ESearchCase::CaseSensitive, ESearchDir::FromStart, I + 1);
                    if (CloseIdx != INDEX_NONE)
                    {
                        Out.Append(TEXT("<code>"));
                        Out.Append(EscapedSegment(Line, I + 1, CloseIdx));
                        Out.Append(TEXT("</code>"));
                        I = CloseIdx + 1;
                        continue;
                    }
                }
                // Bold **x**
                if (StartsWith(Line, I, TEXT("**")))
                {
                    const int32 CloseIdx = Line.Find(TEXT("**"), ESearchCase::CaseSensitive, ESearchDir::FromStart, I + 2);
                    if (CloseIdx != INDEX_NONE)
                    {
                        Out.Append(TEXT("<bold>"));
                        Out.Append(ParseInline(Line.Mid(I + 2, CloseIdx - (I + 2))));
                        Out.Append(TEXT("</bold>"));
                        I = CloseIdx + 2;
                        continue;
                    }
                }
                // Italic *x* (NOT when preceded/followed by another *)
                if (Line[I] == TCHAR('*') && !StartsWith(Line, I, TEXT("**")))
                {
                    const int32 CloseIdx = Line.Find(TEXT("*"), ESearchCase::CaseSensitive, ESearchDir::FromStart, I + 1);
                    if (CloseIdx != INDEX_NONE && (CloseIdx + 1 >= Len || Line[CloseIdx + 1] != TCHAR('*')))
                    {
                        Out.Append(TEXT("<italic>"));
                        Out.Append(ParseInline(Line.Mid(I + 1, CloseIdx - (I + 1))));
                        Out.Append(TEXT("</italic>"));
                        I = CloseIdx + 1;
                        continue;
                    }
                }
                // Link [text](url)
                if (Line[I] == TCHAR('['))
                {
                    const int32 CloseBracket = Line.Find(TEXT("]"), ESearchCase::CaseSensitive, ESearchDir::FromStart, I + 1);
                    if (CloseBracket != INDEX_NONE && CloseBracket + 1 < Len && Line[CloseBracket + 1] == TCHAR('('))
                    {
                        const int32 CloseParen = Line.Find(TEXT(")"), ESearchCase::CaseSensitive, ESearchDir::FromStart, CloseBracket + 2);
                        if (CloseParen != INDEX_NONE)
                        {
                            const FString Text = Line.Mid(I + 1, CloseBracket - (I + 1));
                            const FString Url = Line.Mid(CloseBracket + 2, CloseParen - (CloseBracket + 2));
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
                AppendEscaped(Out, Line[I]);
                ++I;
            }
            return Out;
        }
    }

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
            // Strip trailing \r if present (Windows newlines)
            if (Line.EndsWith(TEXT("\r"), ESearchCase::CaseSensitive))
            {
                Line.LeftChopInline(1, false);
            }

            // Fenced code block: ```lang (or just ``` )
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
                Out.Append(EscapeRichText(Lang));
                Out.Append(TEXT("\">"));
                Out.Append(EscapeRichText(Body));
                Out.Append(TEXT("</nyra-code>"));
                continue;
            }
            // Heading ### (order: longest prefix first)
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
            // Unordered list item
            else if (Line.StartsWith(TEXT("- ")) || Line.StartsWith(TEXT("* ")))
            {
                Out.Append(TEXT("• "));
                Out.Append(ParseInline(Line.Mid(2)));
                Out.Append(TEXT("\n"));
            }
            // Blank line
            else if (Line.IsEmpty())
            {
                Out.Append(TEXT("\n"));
            }
            // Regular paragraph line
            else
            {
                Out.Append(ParseInline(Line));
                Out.Append(TEXT("\n"));
            }
            ++I;
        }
        return Out;
    }
    ```

    **3. REPLACE NyraMarkdownSpec.cpp with real tests:**

    ```cpp
    #include "Misc/AutomationTest.h"
    #include "NyraTestFixtures.h"
    #include "Markdown/FNyraMarkdownParser.h"

    #if WITH_AUTOMATION_TESTS

    BEGIN_DEFINE_SPEC(FNyraMarkdownSpec,
                       "Nyra.Markdown",
                       EAutomationTestFlags::EditorContext |
                       EAutomationTestFlags::EngineFilter)
    END_DEFINE_SPEC(FNyraMarkdownSpec)

    void FNyraMarkdownSpec::Define()
    {
        Describe("FencedCode", [this]()
        {
            It("renders python fenced block with raw body preserved", [this]()
            {
                const FString Src = TEXT("```python\nprint(\"x\")\n```");
                const FString Out = FNyraMarkdownParser::MarkdownToRichText(Src);
                TestTrue(TEXT("open tag with lang"), Out.Contains(TEXT("<nyra-code lang=\"python\">")));
                TestTrue(TEXT("body preserved"), Out.Contains(TEXT("print(\"x\")")));
                TestTrue(TEXT("close tag"), Out.Contains(TEXT("</nyra-code>")));
            });
            It("renders unnamed fenced block with empty lang", [this]()
            {
                const FString Src = TEXT("```\ncode\n```");
                const FString Out = FNyraMarkdownParser::MarkdownToRichText(Src);
                TestTrue(TEXT("empty lang"), Out.Contains(TEXT("<nyra-code lang=\"\">")));
                TestTrue(TEXT("body"), Out.Contains(TEXT("code")));
            });
            It("does NOT apply inline formatting inside fenced body", [this]()
            {
                const FString Src = TEXT("```\n**not bold**\n```");
                const FString Out = FNyraMarkdownParser::MarkdownToRichText(Src);
                TestFalse(TEXT("no bold tag"), Out.Contains(TEXT("<bold>")));
                TestTrue(TEXT("asterisks preserved literally"), Out.Contains(TEXT("**not bold**")));
            });
        });

        Describe("InlineFormatting", [this]()
        {
            It("emits bold", [this]()
            {
                TestTrue(TEXT("bold"),
                    FNyraMarkdownParser::MarkdownToRichText(TEXT("**hi**")).Contains(TEXT("<bold>hi</bold>")));
            });
            It("emits italic", [this]()
            {
                TestTrue(TEXT("italic"),
                    FNyraMarkdownParser::MarkdownToRichText(TEXT("*hi*")).Contains(TEXT("<italic>hi</italic>")));
            });
            It("emits inline code", [this]()
            {
                TestTrue(TEXT("code"),
                    FNyraMarkdownParser::MarkdownToRichText(TEXT("`x`")).Contains(TEXT("<code>x</code>")));
            });
            It("emits link with url attr", [this]()
            {
                const FString Out = FNyraMarkdownParser::MarkdownToRichText(TEXT("[NYRA](https://nyra.ai)"));
                TestTrue(TEXT("link tag"), Out.Contains(TEXT("<link url=\"https://nyra.ai\">NYRA</link>")));
            });
            It("emits headings H1-H3", [this]()
            {
                const FString Out = FNyraMarkdownParser::MarkdownToRichText(TEXT("# a\n## b\n### c"));
                TestTrue(TEXT("H1"), Out.Contains(TEXT("<heading level=\"1\">a</heading>")));
                TestTrue(TEXT("H2"), Out.Contains(TEXT("<heading level=\"2\">b</heading>")));
                TestTrue(TEXT("H3"), Out.Contains(TEXT("<heading level=\"3\">c</heading>")));
            });
            It("emits unordered list bullets", [this]()
            {
                const FString Out = FNyraMarkdownParser::MarkdownToRichText(TEXT("- apple\n- banana"));
                TestTrue(TEXT("bullet 1"), Out.Contains(TEXT("• apple")));
                TestTrue(TEXT("bullet 2"), Out.Contains(TEXT("• banana")));
            });
            It("escapes < > & outside tags", [this]()
            {
                const FString Out = FNyraMarkdownParser::MarkdownToRichText(TEXT("1 < 2 & 3 > 0"));
                TestTrue(TEXT("lt"), Out.Contains(TEXT("&lt;")));
                TestTrue(TEXT("gt"), Out.Contains(TEXT("&gt;")));
                TestTrue(TEXT("amp"), Out.Contains(TEXT("&amp;")));
            });
        });
    }

    #endif
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "class NYRAEDITOR_API FNyraMarkdownParser" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Markdown/FNyraMarkdownParser.h` equals 1
      - `grep -c "static FString MarkdownToRichText" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Markdown/FNyraMarkdownParser.h` equals 1
      - `grep -c '<nyra-code lang=\\"' TestProject/Plugins/NYRA/Source/NyraEditor/Private/Markdown/FNyraMarkdownParser.cpp` >= 1
      - `grep -c '<heading level=\\"' TestProject/Plugins/NYRA/Source/NyraEditor/Private/Markdown/FNyraMarkdownParser.cpp` >= 3
      - `grep -c "\\\\u2022" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Markdown/FNyraMarkdownParser.cpp` >= 1
      - `grep -c 'Describe("FencedCode"' TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraMarkdownSpec.cpp` equals 1
      - `grep -c 'Describe("InlineFormatting"' TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraMarkdownSpec.cpp` equals 1
      - After build: `UnrealEditor-Cmd.exe TestProject/TestProject.uproject -ExecCmds="Automation RunTests Nyra.Markdown;Quit" -unattended -nopause -testexit="Automation Test Queue Empty"` exits 0 with all It blocks passing (>= 10 tests)
    </automated>
  </verify>
  <acceptance_criteria>
    - FNyraMarkdownParser.h exports class with static `MarkdownToRichText(const FString&)` returning `FString`
    - FNyraMarkdownParser.h exports static `EscapeRichText`
    - FNyraMarkdownParser.cpp handles (in order): fenced code, ### heading, ## heading, # heading, unordered list prefix, blank line, regular line
    - FNyraMarkdownParser.cpp inline parser handles (recursively): inline code, bold, italic, link
    - FNyraMarkdownParser.cpp escapes `<`, `>`, `&` to `&lt;`, `&gt;`, `&amp;` in plain text segments
    - FNyraMarkdownParser.cpp fenced body is NOT further parsed (raw text escaped only)
    - FNyraMarkdownParser.cpp emits `• ` (bullet char) for `- ` and `* ` list prefixes
    - NyraMarkdownSpec.cpp has `Describe("FencedCode", ...)` with 3 It blocks (python lang, empty lang, no-inline-inside)
    - NyraMarkdownSpec.cpp has `Describe("InlineFormatting", ...)` with 7 It blocks (bold, italic, inline code, link, H1/H2/H3, unordered list, escape)
    - `UnrealEditor-Cmd.exe TestProject/TestProject.uproject -ExecCmds="Automation RunTests Nyra.Markdown;Quit" -unattended -nopause -testexit="Automation Test Queue Empty"` exits 0
  </acceptance_criteria>
  <done>Parser + tests green; VALIDATION 1-04-02 (FencedCode) + 1-04-03 (InlineFormatting) satisfied.</done>
</task>

<task type="auto">
  <name>Task 2: UNyraCodeBlockDecorator for SRichTextBlock consumption</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraEditor/Public/Markdown/FNyraCodeBlockDecorator.h
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Markdown/FNyraCodeBlockDecorator.cpp
  </files>
  <read_first>
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.1 "Custom URichTextBlockDecorator subclasses" + "Copy" button requirement (CD-06)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Markdown/FNyraMarkdownParser.h (just created — produces <nyra-code> tags)
    - TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs (UMG deps — may need "UMG" added)
  </read_first>
  <action>
    **1. CHECK and UPDATE NyraEditor.Build.cs** — if `"UMG"` is not present
    in `PublicDependencyModuleNames.AddRange`, ADD it. The `URichTextBlockDecorator`
    base class lives in UMG module.

    Executor MUST add `"UMG"` after `"ApplicationCore"` in the dependency
    array if missing.

    **2. CREATE Public/Markdown/FNyraCodeBlockDecorator.h:**

    ```cpp
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
    ```

    **3. CREATE Private/Markdown/FNyraCodeBlockDecorator.cpp:**

    ```cpp
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

    /** Widget rendered in place of a <nyra-code> tag run. */
    static TSharedRef<SWidget> MakeCodeBlockWidget(const FString& InBody, const FString& InLang)
    {
        const FString BodyCopy = InBody;  // capture by value for OnClicked
        return SNew(SBorder)
            .BorderImage(FAppStyle::GetBrush("ToolPanel.GroupBorder"))
            .Padding(8.f)
            [
                SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight()
                [
                    SNew(SHorizontalBox)
                    + SHorizontalBox::Slot().FillWidth(1.0f)
                    [
                        SNew(STextBlock)
                        .Text(FText::FromString(InLang.IsEmpty() ? TEXT("code") : InLang))
                        .ColorAndOpacity(FLinearColor(0.5f, 0.5f, 0.5f))
                    ]
                    + SHorizontalBox::Slot().AutoWidth()
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
                + SVerticalBox::Slot().AutoHeight().Padding(0, 8, 0, 0)
                [
                    SNew(STextBlock)
                    .Text(FText::FromString(InBody))
                    .Font(FAppStyle::GetFontStyle(TEXT("MonospacedText")))
                    .AutoWrapText(true)
                ]
            ];
    }

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
            const FString Body = OriginalText.Mid(
                RunParseResult.ContentRange.BeginIndex,
                RunParseResult.ContentRange.EndIndex - RunParseResult.ContentRange.BeginIndex);
            FString Lang;
            if (const FTextRange* Found = RunParseResult.MetaData.Find(TEXT("lang")))
            {
                Lang = OriginalText.Mid(Found->BeginIndex, Found->EndIndex - Found->BeginIndex);
            }

            FRunInfo RunInfo(RunParseResult.Name);
            RunInfo.MetaData.Add(TEXT("lang"), Lang);

            InOutModelText->Append(TEXT("\x200B"));  // zero-width marker; Slate replaces with widget
            const FTextRange ModelRange(InOutModelText->Len() - 1, InOutModelText->Len());
            return FSlateWidgetRun::Create(
                TextLayout, RunInfo, InOutModelText, FSlateWidgetRun::FWidgetRunInfo(
                    MakeCodeBlockWidget(Body, Lang), 16.f), ModelRange);
        }
    };

    UNyraCodeBlockDecorator::UNyraCodeBlockDecorator() = default;

    TSharedPtr<ITextDecorator> UNyraCodeBlockDecorator::CreateDecorator(URichTextBlock* InOwner)
    {
        return MakeShared<FNyraCodeBlockDecoratorImpl>();
    }

    #undef LOCTEXT_NAMESPACE
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "UCLASS()" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Markdown/FNyraCodeBlockDecorator.h` equals 1
      - `grep -c "class NYRAEDITOR_API UNyraCodeBlockDecorator : public URichTextBlockDecorator" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Markdown/FNyraCodeBlockDecorator.h` equals 1
      - `grep -c "\"UMG\"" TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs` >= 1
      - `grep -c "FPlatformApplicationMisc::ClipboardCopy" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Markdown/FNyraCodeBlockDecorator.cpp` >= 1
      - `grep -c "RunInfo.Name == TEXT(\"nyra-code\")" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Markdown/FNyraCodeBlockDecorator.cpp` >= 1
      - TestProject compiles cleanly after this plan (no compilation errors).
    </automated>
  </verify>
  <acceptance_criteria>
    - FNyraCodeBlockDecorator.h contains `UCLASS()` + `class NYRAEDITOR_API UNyraCodeBlockDecorator : public URichTextBlockDecorator` + `GENERATED_BODY()`
    - FNyraCodeBlockDecorator.h declares `virtual TSharedPtr<ITextDecorator> CreateDecorator(URichTextBlock* InOwner) override`
    - FNyraCodeBlockDecorator.cpp `FNyraCodeBlockDecoratorImpl::Supports` returns true for `RunInfo.Name == TEXT("nyra-code")`
    - FNyraCodeBlockDecorator.cpp `MakeCodeBlockWidget` renders: header row (language label + Copy button), body (monospace STextBlock)
    - FNyraCodeBlockDecorator.cpp Copy button invokes `FPlatformApplicationMisc::ClipboardCopy(*BodyCopy)`
    - NyraEditor.Build.cs contains `"UMG"` in PublicDependencyModuleNames (added if missing)
  </acceptance_criteria>
  <done>Decorator compiles; Plan 12 panel can register it on its SRichTextBlock.</done>
</task>

</tasks>

<verification>
`UnrealEditor-Cmd.exe TestProject/TestProject.uproject -ExecCmds="Automation RunTests Nyra.Markdown;Quit" -unattended -nopause -testexit="Automation Test Queue Empty"` exits 0 with all Nyra.Markdown tests passing (FencedCode + InlineFormatting sub-suites).
</verification>

<success_criteria>
- FNyraMarkdownParser converts Phase 1 markdown subset to Slate RichText tags
- UNyraCodeBlockDecorator renders <nyra-code> with monospace body + Copy button
- Nyra.Markdown.FencedCode + Nyra.Markdown.InlineFormatting automation tests green
- UMG module added to NyraEditor.Build.cs deps
</success_criteria>

<output>
After completion, create `.planning/phases/01-plugin-shell-three-process-ipc/01-11-SUMMARY.md`
listing: supported markdown subset, rich-text tag vocabulary, decorator's
widget composition, how Plan 12 registers UNyraCodeBlockDecorator on
SRichTextBlock.
</output>
