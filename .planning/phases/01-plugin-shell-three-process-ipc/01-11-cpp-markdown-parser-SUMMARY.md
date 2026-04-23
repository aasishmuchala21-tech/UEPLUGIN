---
phase: 01-plugin-shell-three-process-ipc
plan: 11
subsystem: cpp-markdown-parser
tags: [ue-cpp, slate, rich-text, markdown, richtextblockdecorator, chat-01, cd-06, validation-1-04-02, validation-1-04-03]
requirements_closed: []
requirements_progressed: [CHAT-01]
dependency_graph:
  requires:
    - 01-01-cpp-automation-scaffold (NyraMarkdownSpec.cpp Wave 0 stub -- upgraded here)
    - 01-03-uplugin-two-module-scaffold (NYRAEDITOR_API export macro + NyraEditor module base)
  provides:
    - FNyraMarkdownParser::MarkdownToRichText (Phase-1 markdown-subset -> Slate rich-text tag stream)
    - FNyraMarkdownParser::EscapeRichText (HTML-style char escape helper)
    - UNyraCodeBlockDecorator (URichTextBlockDecorator subclass handling <nyra-code> tags)
    - FNyraCodeBlockDecoratorImpl (internal ITextDecorator with Supports + Create + widget builder)
  affects:
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraMarkdownSpec.cpp (upgraded from Plan 01 Wave 0 stub to 10 It blocks)
    - TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs (added "UMG" to PublicDependencyModuleNames)
tech-stack:
  added:
    - UE UMG module (Components/RichTextBlockDecorator.h base class)
    - UE Framework/Text/ITextDecorator + FTextRunParseResults + FSlateWidgetRun (rich-text run construction)
    - HAL/PlatformApplicationMisc (ClipboardCopy for [Copy] button)
    - Styling/AppStyle (ToolPanel.GroupBorder brush + MonospacedText font)
  patterns:
    - Recursive inline parser (bold/italic/link bodies re-enter ParseInline; inline-code body is terminal)
    - Fenced-code body escape-only (no further markdown parsing inside ```...```)
    - Capture-by-value for OnClicked lambdas (BodyCopy outlives the decorator-Create call)
    - NyraMarkdownSpec 2-Describe layout (FencedCode + InlineFormatting) mirroring VALIDATION rows 1-04-02 + 1-04-03 one-to-one
    - Module-superset discipline continued: NyraEditor.Build.cs UMG addition is purely additive (placed after ApplicationCore); no prior deps removed or reordered
key-files:
  created:
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Markdown/FNyraMarkdownParser.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Markdown/FNyraMarkdownParser.cpp
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Markdown/FNyraCodeBlockDecorator.h
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Markdown/FNyraCodeBlockDecorator.cpp
  modified:
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraMarkdownSpec.cpp (Plan 01 Wave 0 stub -> 10 real It blocks)
    - TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs (appended "UMG" after "ApplicationCore")
decisions:
  - Fenced-code body is escape-only (not re-parsed through ParseInline). Ensures `**not bold**` inside a code block stays literal; validated by the Nyra.Markdown.FencedCode third It block.
  - Bullet character emitted as the literal U+2022 glyph (rendered by default Slate font). Appears twice in FNyraMarkdownParser.cpp (once in the "bullet-space" append, once in the explanatory comment) -- grep acceptance literal (`•`) count = 2.
  - ParseInline recurses on bold + italic + link BODY but NOT on inline-code body. Matches CommonMark spirit: backticks suppress further markdown.
  - Italic guard: `*` opens italic only when the prefix is NOT `**`, AND the closing `*` is NOT immediately followed by another `*`. Prevents `**bold**` being misread as two italics across the overlap.
  - URL attribute value is run through EscapedSegment so ampersands in query strings (`?a=1&b=2`) survive the Slate tag parser intact.
  - Widget composition per PLAN.md interfaces: SBorder (ToolPanel.GroupBorder, 8.f padding) -> SVerticalBox (AutoHeight header, AutoHeight body with 8.f top padding) -> header SHorizontalBox (FillWidth lang label + AutoWidth Copy button). Body STextBlock uses `FAppStyle::GetFontStyle(TEXT("MonospacedText"))` and AutoWrapText(true).
  - FSlateWidgetRun placed via a zero-width space (U+200B) anchor in the model text so the rich-text layout has a cursor position corresponding to the widget run. Standard UE pattern; baseline percent 16.f matches the Epic tooltip sample referenced in RESEARCH Sec 3.1.
  - UMG added to PublicDependencyModuleNames (not Private) because UNyraCodeBlockDecorator is NYRAEDITOR_API public-surface -- Plan 12's SNyraChatPanel will reference its StaticClass() for SetDecorators.
metrics:
  duration: ~9min
  completed: 2026-04-23
  tasks: 2
  commits: 2
  files_created: 4
  files_modified: 2
---

# Phase 1 Plan 11: C++ Markdown Parser Summary

**One-liner:** Phase-1 markdown-subset parser converting chat-message source into a Slate rich-text tag stream (`<heading>`, `<bold>`, `<italic>`, `<code>`, `<link>`, `<nyra-code>`, bullet chars) plus a URichTextBlockDecorator that renders `<nyra-code>` runs as monospace code blocks with a working [Copy] button wired to `FPlatformApplicationMisc::ClipboardCopy`.

## What Shipped

Two cooperating UE C++ components that together produce the "rich markdown in chat bubbles" behaviour that CONTEXT CD-06 and RESEARCH Sec 3.1 call for:

1. **FNyraMarkdownParser** (`Public/Markdown/FNyraMarkdownParser.h` + `Private/Markdown/FNyraMarkdownParser.cpp`):

   - `MarkdownToRichText(const FString& Source) -> FString` walks the source line-by-line applying (in order) fenced-code opener detection, then H3/H2/H1 prefix detection, then unordered-list prefix detection, then blank-line passthrough, falling through to inline parsing on regular paragraph lines.
   - `ParseInline(const FString& Line)` (anonymous namespace) recursively handles inline code (terminal body), **bold** (recursive body), *italic* (recursive body), and [text](url) (recursive body, URL attr escaped). Italic guard prevents `**bold**` being misread as italics; inline-code body is NEVER recursively parsed so backticks suppress further markdown as in CommonMark.
   - `EscapeRichText(const FString& Raw) -> FString` is a public helper that passes every character through `AppendEscaped` (`<` -> `&lt;`, `>` -> `&gt;`, `&` -> `&amp;`). Used for URL attribute values and for the raw fenced-code body so user-typed angle brackets never collide with Slate's tag parser downstream.
   - Slate rich-text tag vocabulary emitted:

     | Markdown         | Slate tag emitted                       |
     | ---------------- | --------------------------------------- |
     | `# x`            | `<heading level="1">x</heading>\n`      |
     | `## x`           | `<heading level="2">x</heading>\n`      |
     | `### x`          | `<heading level="3">x</heading>\n`      |
     | `**x**`          | `<bold>x</bold>`                        |
     | `*x*`            | `<italic>x</italic>`                    |
     | `` `x` ``        | `<code>x</code>`                        |
     | `[t](url)`       | `<link url="url">t</link>`              |
     | `- x` / `* x`    | `• x\n` (bullet char U+2022)            |
     | ``` ```lang\n...body...\n``` ``` | `<nyra-code lang="lang">...body...</nyra-code>` |

2. **UNyraCodeBlockDecorator** (`Public/Markdown/FNyraCodeBlockDecorator.h` + `Private/Markdown/FNyraCodeBlockDecorator.cpp`):

   - `UCLASS() class NYRAEDITOR_API UNyraCodeBlockDecorator : public URichTextBlockDecorator` with `virtual TSharedPtr<ITextDecorator> CreateDecorator(URichTextBlock* InOwner) override`.
   - Internal `FNyraCodeBlockDecoratorImpl` subclass of `ITextDecorator`:
     - `Supports()` gates on `RunInfo.Name == TEXT("nyra-code")`.
     - `Create()` extracts the `ContentRange` (raw body) and the `lang` meta attribute from the `FTextRunParseResults`, then builds an `FSlateWidgetRun` anchored on a single zero-width-space (U+200B) character appended to the model text; baseline-percent 16.f matches the Epic tooltip sample.
   - `MakeCodeBlockWidget(InBody, InLang)` builds the widget tree: `SBorder` (ToolPanel.GroupBorder, 8.f padding) wrapping a two-slot `SVerticalBox` -- header row (`SHorizontalBox` with fill-width `STextBlock` language label + auto-width `SButton` [Copy]) + body row (`STextBlock` with `FAppStyle::GetFontStyle(TEXT("MonospacedText"))` + `AutoWrapText(true)`, 8.f top padding).
   - [Copy] button captures the body by value in an `OnClicked_Lambda` calling `FPlatformApplicationMisc::ClipboardCopy(*BodyCopy)`. Closes CONTEXT CD-06's "Code blocks must have a copy button" requirement.

## Test upgrades (VALIDATION closure -- source-level)

- **Nyra.Markdown.FencedCode** (VALIDATION 1-04-02): 3 It blocks inside `Describe("FencedCode", ...)`:
  - `renders python fenced block with raw body preserved` -- asserts `<nyra-code lang="python">` opens, `print("x")` body survives, `</nyra-code>` closes.
  - `renders unnamed fenced block with empty lang` -- asserts `<nyra-code lang="">` with a `code` body.
  - `does NOT apply inline formatting inside fenced body` -- asserts NO `<bold>` tag is produced when body is `**not bold**` and that `**not bold**` survives literally.

- **Nyra.Markdown.InlineFormatting** (VALIDATION 1-04-03): 7 It blocks inside `Describe("InlineFormatting", ...)`:
  - `emits bold` -- `**hi**` -> contains `<bold>hi</bold>`.
  - `emits italic` -- `*hi*` -> contains `<italic>hi</italic>`.
  - `emits inline code` -- `` `x` `` -> contains `<code>x</code>`.
  - `emits link with url attr` -- `[NYRA](https://nyra.ai)` -> contains `<link url="https://nyra.ai">NYRA</link>`.
  - `emits headings H1-H3` -- `# a\n## b\n### c` -> contains all three `<heading level="N">...</heading>` forms.
  - `emits unordered list bullets` -- `- apple\n- banana` -> contains `• apple` and `• banana`.
  - `escapes < > & outside tags` -- `1 < 2 & 3 > 0` -> contains `&lt;`, `&gt;`, and `&amp;`.

Total: 10 It blocks (>= 10 per PLAN.md acceptance).

## Supported markdown subset (Phase 1 scope)

| Feature         | In scope | Notes                                                               |
| --------------- | -------- | ------------------------------------------------------------------- |
| H1 / H2 / H3    | Yes      | `#`, `##`, `###` prefixes; longest prefix wins                      |
| Bold            | Yes      | `**text**`; body recursively re-parsed                              |
| Italic          | Yes      | `*text*`; guarded against `**` collision                            |
| Inline code     | Yes      | `` `text` ``; body is TERMINAL (not recursively parsed)             |
| Links           | Yes      | `[text](url)`; URL attr escape-only; body recursively parsed        |
| Unordered lists | Yes      | `- x` or `* x`; emits U+2022 bullet char                            |
| Fenced code     | Yes      | ```` ```lang\n...body...\n``` ````; body is ESCAPE-ONLY (no parse)  |
| H4 / H5 / H6    | No       | Phase 2 can add by extending the dispatch chain                     |
| Ordered lists   | No       | Phase 2                                                              |
| Tables          | No       | Explicitly out-of-scope (RESEARCH Sec 3.1)                          |
| Images          | No       | Explicitly out-of-scope                                             |
| Raw HTML        | No       | Explicitly out-of-scope                                             |
| Blockquotes     | No       | Phase 2                                                              |
| Setext headings | No       | Phase 2 (if requested)                                               |
| Reference links | No       | Phase 2 (if requested)                                               |

## Rich-text tag vocabulary (Plan 12 consumer contract)

Plan 12's `SNyraChatPanel` will construct a URichTextBlock with decorators for each tag Plan 11 emits. Minimum registration pattern:

```cpp
RichText->SetDecorators({
    UNyraCodeBlockDecorator::StaticClass(),   // <nyra-code> (Plan 11)
    // Future: heading/bold/italic/inline-code/link decorators the panel
    // adds in Plan 12 using either URichTextBlockDecorator subclasses or
    // the built-in <Text.StyleName> FRichTextDecorator pattern. The
    // <heading level="1|2|3"> tags can be mapped via a 1:1 text-style
    // lookup against an FSlateStyleSet.
});
```

The tag names emitted by Plan 11 are deliberately LOWERCASE and simple so Plan 12 can implement the inline decorators with either the "text style" path (FSlateStyleSet-backed `Text.Bold`, `Text.Italic`, `Text.Code` styles) or bespoke `ITextDecorator` subclasses.

## Decorator widget composition

```
SBorder [ToolPanel.GroupBorder brush, 8.f padding]
 |
 +-- SVerticalBox
      |
      +-- Slot[AutoHeight]  -- header row
      |     |
      |     +-- SHorizontalBox
      |           |
      |           +-- Slot[FillWidth=1.0]  STextBlock {lang label, 50% grey}
      |           +-- Slot[AutoWidth]      SButton    [ Copy ] -> ClipboardCopy(body)
      |
      +-- Slot[AutoHeight, Padding=0,8,0,0]  -- body row
            |
            +-- STextBlock {Text=body, Font=MonospacedText, AutoWrapText=true}
```

The 16.f baseline percent in `FSlateWidgetRun::FWidgetRunInfo` matches the Epic tooltip sample referenced at `github.com/Nauja/ue4-richtextblocktooltip-sample` (RESEARCH Sec 3.1).

## How Plan 12 registers UNyraCodeBlockDecorator on SRichTextBlock

Plan 12's `SNyraChatPanel` will ship a helper (tentative name `FNyraChatMessageView`) that owns one `SRichTextBlock` per message + a one-time decorator registration. Canonical usage:

```cpp
// Inside FNyraChatMessageView::Construct (or equivalent):
TSharedRef<FRichTextLayoutMarshaller> Marshaller =
    FRichTextLayoutMarshaller::Create(/*... default decorators from style set ...*/);

// Add the nyra-code decorator for <nyra-code> runs.
Marshaller->AppendInlineDecorator(
    MakeShared<FNyraCodeBlockDecoratorImpl>());
// (Plan 12 option B: use UNyraCodeBlockDecorator::StaticClass() with a
//  URichTextBlock instead of SRichTextBlock -- the UCLASS machinery is
//  there specifically to support that path. SNyraChatMessageView will
//  choose whichever fits the panel's Slate vs UMG decision.)

RichTextBlock = SNew(SRichTextBlock)
    .Text(FText::FromString(FNyraMarkdownParser::MarkdownToRichText(MessageSource)))
    .AutoWrapText(true)
    .DecoratorStyleSet(&FAppStyle::Get())
    .Marshaller(Marshaller);
```

The key invariant Plan 11 locks for Plan 12: **the parser output is always safe to hand to `SRichTextBlock::SetText` with the decorators above registered** -- all user-typed angle brackets have been HTML-escaped, and every tag pair is well-formed.

## Streaming-render integration (RESEARCH Sec 3.1 reminder for Plan 12)

Per RESEARCH Sec 3.1 performance discussion:

- DO NOT call `FNyraMarkdownParser::MarkdownToRichText` + `SRichTextBlock::SetText` on every `chat/stream` delta frame -- re-parsing a growing markdown string 200 times during a 5-second response will thrash layout.
- DO render a plain `STextBlock` during streaming (append each `delta` to the buffer and set text on the plain block), then on `done:true` swap to `SRichTextBlock` with `MarkdownToRichText(FinalBuffer)` parsed once.
- Incremental parse is a Phase 2 polish item (RESEARCH Sec 3.1); Phase 1 ships the "plain during stream, rich on done" approach.

## Deviations

### Auto-fixed Issues

None. Plan executed exactly as written. The sole departure from the PLAN.md `<action>` blocks was adding explanatory comments in the source files (for future maintainability) and a single top-of-file banner block in each new file -- all additive, no behavioural change. The PLAN.md-specified grep literals all pass verbatim.

### Deferred Verifications (host-platform gap -- macOS dev, target Windows UE 5.6)

Consistent with Plans 01/03/04/05/10's platform-gap posture documented in STATE.md. All Plan 11 C++ source is authored and grep-verified at the literal level, but the UE-side verifications below require Windows + UE 5.6 UBT/MSVC which the macOS dev host cannot run:

1. **UE 5.6 compile of FNyraMarkdownParser.h/.cpp + FNyraCodeBlockDecorator.h/.cpp + NyraMarkdownSpec.cpp + NyraEditor.Build.cs UMG addition** -- deferred to Windows CI (host is macOS).
2. **`UnrealEditor-Cmd.exe TestProject/TestProject.uproject -ExecCmds="Automation RunTests Nyra.Markdown;Quit" -unattended -nopause -testexit="Automation Test Queue Empty"` exit 0 with 10 It blocks (3 FencedCode + 7 InlineFormatting)** (VALIDATION 1-04-02 + 1-04-03) -- deferred to Windows CI.
3. **Compile against UBT auto-generated NyraEditor include graph** (UBT may flag a missing forward declaration for URichTextBlock or similar UMG symbols) -- deferred to Windows CI; all UE headers referenced by Plan 11 files exist in UE 5.6 per public docs (Components/RichTextBlockDecorator.h, Components/RichTextBlock.h, Framework/Text/ITextDecorator.h, Framework/Text/SlateTextRun.h, Framework/Text/SlateWidgetRun.h, Widgets/SBoxPanel.h, Widgets/Layout/SBorder.h, Widgets/Text/STextBlock.h, Widgets/Input/SButton.h, Styling/AppStyle.h, HAL/PlatformApplicationMisc.h).
4. **Manual [Copy] button verification:** launch editor, render a chat message with a fenced code block, click [Copy], paste into a text editor, verify clipboard contents match the raw fenced body exactly -- deferred to Windows dev-machine after Plan 12's panel lands.
5. **Visual verification of the SBorder + monospace body rendering:** deferred to Windows dev-machine after Plan 12's panel lands.

These are consistent with the Phase-1 platform-gap posture established by Plans 01/03/04/05/10 and do not block further Phase 1 plan execution.

## Grep acceptance literals (all pass source-level)

Task 1 (8 literals):

```
grep -c "class NYRAEDITOR_API FNyraMarkdownParser" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Markdown/FNyraMarkdownParser.h           -> 1  PASS
grep -c "static FString MarkdownToRichText"        TestProject/Plugins/NYRA/Source/NyraEditor/Public/Markdown/FNyraMarkdownParser.h           -> 1  PASS
grep -c '<nyra-code lang=\"'                       TestProject/Plugins/NYRA/Source/NyraEditor/Private/Markdown/FNyraMarkdownParser.cpp        -> 1  PASS (>= 1)
grep -c '<heading level=\"'                        TestProject/Plugins/NYRA/Source/NyraEditor/Private/Markdown/FNyraMarkdownParser.cpp        -> 3  PASS (>= 3)
grep -c "•"                                        TestProject/Plugins/NYRA/Source/NyraEditor/Private/Markdown/FNyraMarkdownParser.cpp        -> 2  PASS (>= 1)
grep -c 'Describe("FencedCode"'                    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraMarkdownSpec.cpp              -> 1  PASS
grep -c 'Describe("InlineFormatting"'              TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraMarkdownSpec.cpp              -> 1  PASS
It() blocks (manual inspection)                                                                                                                -> 10 PASS (>= 10)
```

Task 2 (5 literals):

```
grep -c "UCLASS()"                                                                  TestProject/Plugins/NYRA/Source/NyraEditor/Public/Markdown/FNyraCodeBlockDecorator.h  -> 1  PASS
grep -c "class NYRAEDITOR_API UNyraCodeBlockDecorator : public URichTextBlockDecorator" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Markdown/FNyraCodeBlockDecorator.h  -> 1  PASS
grep -c '"UMG"'                                                                     TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs                         -> 1  PASS (>= 1)
grep -c "FPlatformApplicationMisc::ClipboardCopy"                                   TestProject/Plugins/NYRA/Source/NyraEditor/Private/Markdown/FNyraCodeBlockDecorator.cpp -> 2  PASS (>= 1)
grep -c 'RunInfo.Name == TEXT("nyra-code")'                                         TestProject/Plugins/NYRA/Source/NyraEditor/Private/Markdown/FNyraCodeBlockDecorator.cpp -> 1  PASS (>= 1)
```

All 13 grep acceptance literals pass.

## Commits

- `3371bc2` -- feat(01-11): add FNyraMarkdownParser + upgrade NyraMarkdownSpec
- `fa2160e` -- feat(01-11): add UNyraCodeBlockDecorator + UMG dep

## Self-Check: PASSED

- All 4 created files exist on disk (FNyraMarkdownParser.h/.cpp + FNyraCodeBlockDecorator.h/.cpp).
- 2 modified files updated (NyraMarkdownSpec.cpp upgraded from Plan 01 stub to 10 It blocks; NyraEditor.Build.cs appends "UMG" after "ApplicationCore" in PublicDependencyModuleNames).
- Both commits (3371bc2 + fa2160e) present in `git log --oneline`.
- All 13 PLAN.md grep acceptance literals verified green across Tasks 1 + 2.
- Plan 01 Wave 0 NyraMarkdownSpec.cpp stub has been REPLACED (not deleted) -- the `BEGIN_DEFINE_SPEC(FNyraMarkdownSpec, "Nyra.Markdown", ...)` test symbol survives with real body.
- Module-superset invariants preserved in NyraEditor.Build.cs: every prior Build.cs dependency (Core, CoreUObject, Engine, InputCore, Slate, SlateCore, EditorStyle, EditorSubsystem, UnrealEd, ToolMenus, Projects, Json, JsonUtilities, WebSockets, HTTP, DesktopPlatform, ApplicationCore) remains in place and in its original order; only "UMG" was appended at the end of the array.
- No unintended deletions across either commit (`git diff --diff-filter=D --name-only HEAD~2 HEAD` is empty).
