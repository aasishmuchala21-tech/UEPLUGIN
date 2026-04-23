// =============================================================================
// NyraMarkdownSpec.cpp  (Phase 1 Plan 11 -- cpp-markdown-parser)
// =============================================================================
//
// Upgraded from Plan 01 Wave 0 stub (commit ca182ba) to the full It() block
// suite that closes VALIDATION rows 1-04-02 (Nyra.Markdown.FencedCode) and
// 1-04-03 (Nyra.Markdown.InlineFormatting).
//
// Test paths:
//   Nyra.Markdown.FencedCode.*        -- 3 It blocks
//   Nyra.Markdown.InlineFormatting.*  -- 7 It blocks
//
// Total: 10 It blocks (>= 10 per PLAN.md acceptance).
// =============================================================================

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
    // -----------------------------------------------------------------------
    // VALIDATION 1-04-02 -- Nyra.Markdown.FencedCode
    // -----------------------------------------------------------------------
    Describe("FencedCode", [this]()
    {
        It("renders python fenced block with raw body preserved", [this]()
        {
            const FString Src = TEXT("```python\nprint(\"x\")\n```");
            const FString Out = FNyraMarkdownParser::MarkdownToRichText(Src);
            TestTrue(TEXT("open tag with lang"),
                Out.Contains(TEXT("<nyra-code lang=\"python\">")));
            TestTrue(TEXT("body preserved"),
                Out.Contains(TEXT("print(\"x\")")));
            TestTrue(TEXT("close tag"),
                Out.Contains(TEXT("</nyra-code>")));
        });

        It("renders unnamed fenced block with empty lang", [this]()
        {
            const FString Src = TEXT("```\ncode\n```");
            const FString Out = FNyraMarkdownParser::MarkdownToRichText(Src);
            TestTrue(TEXT("empty lang"),
                Out.Contains(TEXT("<nyra-code lang=\"\">")));
            TestTrue(TEXT("body"),
                Out.Contains(TEXT("code")));
        });

        It("does NOT apply inline formatting inside fenced body", [this]()
        {
            const FString Src = TEXT("```\n**not bold**\n```");
            const FString Out = FNyraMarkdownParser::MarkdownToRichText(Src);
            TestFalse(TEXT("no bold tag"),
                Out.Contains(TEXT("<bold>")));
            TestTrue(TEXT("asterisks preserved literally"),
                Out.Contains(TEXT("**not bold**")));
        });
    });

    // -----------------------------------------------------------------------
    // VALIDATION 1-04-03 -- Nyra.Markdown.InlineFormatting
    // -----------------------------------------------------------------------
    Describe("InlineFormatting", [this]()
    {
        It("emits bold", [this]()
        {
            TestTrue(TEXT("bold"),
                FNyraMarkdownParser::MarkdownToRichText(TEXT("**hi**"))
                    .Contains(TEXT("<bold>hi</bold>")));
        });

        It("emits italic", [this]()
        {
            TestTrue(TEXT("italic"),
                FNyraMarkdownParser::MarkdownToRichText(TEXT("*hi*"))
                    .Contains(TEXT("<italic>hi</italic>")));
        });

        It("emits inline code", [this]()
        {
            TestTrue(TEXT("code"),
                FNyraMarkdownParser::MarkdownToRichText(TEXT("`x`"))
                    .Contains(TEXT("<code>x</code>")));
        });

        It("emits link with url attr", [this]()
        {
            const FString Out = FNyraMarkdownParser::MarkdownToRichText(
                TEXT("[NYRA](https://nyra.ai)"));
            TestTrue(TEXT("link tag"),
                Out.Contains(TEXT("<link url=\"https://nyra.ai\">NYRA</link>")));
        });

        It("emits headings H1-H3", [this]()
        {
            const FString Out = FNyraMarkdownParser::MarkdownToRichText(
                TEXT("# a\n## b\n### c"));
            TestTrue(TEXT("H1"),
                Out.Contains(TEXT("<heading level=\"1\">a</heading>")));
            TestTrue(TEXT("H2"),
                Out.Contains(TEXT("<heading level=\"2\">b</heading>")));
            TestTrue(TEXT("H3"),
                Out.Contains(TEXT("<heading level=\"3\">c</heading>")));
        });

        It("emits unordered list bullets", [this]()
        {
            const FString Out = FNyraMarkdownParser::MarkdownToRichText(
                TEXT("- apple\n- banana"));
            TestTrue(TEXT("bullet 1"), Out.Contains(TEXT("• apple")));
            TestTrue(TEXT("bullet 2"), Out.Contains(TEXT("• banana")));
        });

        It("escapes < > & outside tags", [this]()
        {
            const FString Out = FNyraMarkdownParser::MarkdownToRichText(
                TEXT("1 < 2 & 3 > 0"));
            TestTrue(TEXT("lt"), Out.Contains(TEXT("&lt;")));
            TestTrue(TEXT("gt"), Out.Contains(TEXT("&gt;")));
            TestTrue(TEXT("amp"), Out.Contains(TEXT("&amp;")));
        });
    });
}

#endif // WITH_AUTOMATION_TESTS
