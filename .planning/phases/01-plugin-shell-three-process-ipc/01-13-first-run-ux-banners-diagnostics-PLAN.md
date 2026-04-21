---
phase: 01-plugin-shell-three-process-ipc
plan: 13
type: execute
wave: 4
depends_on: [10, 12, 12b]
autonomous: true
requirements: [CHAT-01, PLUG-02, PLUG-03]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraBanner.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraBanner.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraDownloadModal.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraDownloadModal.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraDiagnosticsDrawer.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraDiagnosticsDrawer.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp
objective: >
  Wave 4: first-run UX polish — banner states (bootstrap/unstable/handshake-
  timeout), Gemma download modal with progress bar (consumes
  diagnostics/download-progress notifications from Plan 09), diagnostics
  drawer tailing Saved/NYRA/logs/nyrahost-YYYY-MM-DD.log directly (no
  diagnostics/tail method — RESEARCH Open Q 6 resolved: skip in Phase 1).
  Wire supervisor state changes into the panel so users ALWAYS see a clear
  state per RESEARCH §3.9 state machine.
must_haves:
  truths:
    - "When FNyraSupervisor is in Spawning/WaitingForHandshake/Connecting state, SNyraBanner shows 'Setting up NYRA (~30s)' with an indeterminate progress bar"
    - "When FNyraSupervisor fires OnUnstable, SNyraBanner shows red-accent 'NyraHost is unstable — see Saved/NYRA/logs/' with [Restart] and [Open log] buttons"
    - "When user clicks 'Download Gemma' (surfaced from the gemma_not_installed error bubble or from a future settings panel), SNyraDownloadModal opens with progress bar driven by diagnostics/download-progress notifications"
    - "Download modal supports Cancel (closes modal, sends diagnostics/download-cancel notification which is a no-op in Phase 1 Python side — documented as known limit)"
    - "Download modal correctly updates on status 'downloading' -> 'verifying' -> 'done' -> close; on 'error' shows the remediation"
    - "SNyraDiagnosticsDrawer is collapsed by default; clicking 'Diagnostics' expands and calls FFileHelper::LoadFileToStringArray on the latest nyrahost-YYYY-MM-DD.log, shows last 100 lines in a monospace SMultiLineEditableTextBox (read-only)"
    - "Banner is mounted above the message list in SNyraChatPanel; diagnostics drawer is below"
  artifacts:
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraBanner.h
      provides: "SNyraBanner widget with SetState(ENyraBannerKind, text, buttons)"
      exports: ["SNyraBanner", "ENyraBannerKind"]
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraDownloadModal.h
      provides: "Modal-style widget with progress bar + cancel; bound to diagnostics/download-progress"
      exports: ["SNyraDownloadModal"]
    - path: TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraDiagnosticsDrawer.h
      provides: "Collapsed-by-default expander showing log tail"
      exports: ["SNyraDiagnosticsDrawer"]
  key_links:
    - from: SNyraChatPanel::HandleNotification
      to: SNyraDownloadModal::OnDiagnosticsProgress
      via: "Env.Method == 'diagnostics/download-progress' dispatches to modal"
      pattern: "diagnostics/download-progress"
    - from: SNyraBanner
      to: FNyraSupervisor.OnStateChanged + OnUnstable
      via: "State machine drives banner visibility"
      pattern: "OnStateChanged"
    - from: SNyraDiagnosticsDrawer
      to: FFileHelper::LoadFileToStringArray
      via: "Read <ProjectDir>/Saved/NYRA/logs/nyrahost-YYYY-MM-DD.log directly"
      pattern: "FFileHelper::LoadFileToStringArray"
---

<objective>
Per RESEARCH §3.9 first-run UX state machine, panel is ALWAYS usable. Plan 12
handles the happy path; Plan 13 covers the degraded states:

- Bootstrap in progress (banner + spinner)
- NyraHost crashed (banner after 3-in-60s)
- Gemma not installed (error bubble + Download Gemma button triggers modal)
- Handshake timeout (banner)
- Diagnostics drawer (on demand log tail)

Per CONTEXT.md §specifics:
- Banner visuals via SBorder + themed colors
- "NYRA Chat" tab is always mounted — banners are inside the tab content

Per Research Open Q 6: diagnostics/tail is SKIPPED in Phase 1; drawer reads
log file directly (FFileHelper::LoadFileToStringArray).

Purpose: CHAT-01's "panel depth" success criterion — user always sees a clear
state, no blank screens, no unexplained failures.
Output: 3 widgets + updated SNyraChatPanel wiring.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md
@docs/JSONRPC.md
@TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraChatPanel.h
@TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp
@TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraSupervisor.h
@TestProject/Plugins/NYRA/Source/NyraEditor/Public/WS/FNyraJsonRpc.h
</context>

<interfaces>
SProgressBar canonical usage:
```cpp
SNew(SProgressBar)
    .Percent_Lambda([&]() { return float(BytesDone) / float(BytesTotal); })
    .Style(&FAppStyle::Get().GetWidgetStyle<FProgressBarStyle>("ProgressBar.Regular"))
```

Log tail via FFileHelper:
```cpp
TArray<FString> Lines;
const FString LogPath = FPaths::Combine(
    FPaths::ProjectSavedDir(), TEXT("NYRA"), TEXT("logs"),
    FString::Printf(TEXT("nyrahost-%s.log"), *FDateTime::UtcNow().ToString(TEXT("%Y-%m-%d"))));
FFileHelper::LoadFileToStringArray(Lines, *LogPath);
// Take last 100 entries
const int32 Start = FMath::Max(0, Lines.Num() - 100);
for (int32 I = Start; I < Lines.Num(); ++I) { Out += Lines[I] + TEXT("\n"); }
```
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: SNyraBanner + SNyraDiagnosticsDrawer</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraBanner.h
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraBanner.cpp
    TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraDiagnosticsDrawer.h
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraDiagnosticsDrawer.cpp
  </files>
  <read_first>
    - .planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md §specifics (banner states table)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.9 banner states table, §3.10 P1.4 SmartScreen accepted note
    - docs/ERROR_CODES.md (for remediation text used in banners)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraSupervisor.h (state enum)
  </read_first>
  <action>
    **1. CREATE Public/Panel/SNyraBanner.h:**

    ```cpp
    #pragma once
    #include "CoreMinimal.h"
    #include "Widgets/SCompoundWidget.h"
    #include "Widgets/DeclarativeSyntaxSupport.h"

    enum class ENyraBannerKind : uint8
    {
        Hidden,
        Info,      // blue-accent: Setting up NYRA
        Warning,   // yellow-accent: Handshake timeout
        Error,     // red-accent: NyraHost unstable
    };

    DECLARE_DELEGATE(FOnBannerRestartClicked);
    DECLARE_DELEGATE(FOnBannerOpenLogClicked);

    class NYRAEDITOR_API SNyraBanner : public SCompoundWidget
    {
    public:
        SLATE_BEGIN_ARGS(SNyraBanner) {}
        SLATE_END_ARGS()

        void Construct(const FArguments& InArgs);

        /** Primary state setter. Buttons shown only if corresponding delegate is bound. */
        void SetState(ENyraBannerKind Kind, const FText& Message,
                      const FOnBannerRestartClicked& RestartHandler,
                      const FOnBannerOpenLogClicked& OpenLogHandler);

        void SetState(ENyraBannerKind Kind, const FText& Message);  // no buttons

        void Hide();

    private:
        FReply HandleRestart();
        FReply HandleOpenLog();

        ENyraBannerKind CurrentKind = ENyraBannerKind::Hidden;
        TSharedPtr<class SHorizontalBox> Row;
        FOnBannerRestartClicked RestartDelegate;
        FOnBannerOpenLogClicked OpenLogDelegate;
    };
    ```

    **2. CREATE Private/Panel/SNyraBanner.cpp:**

    ```cpp
    #include "Panel/SNyraBanner.h"
    #include "Widgets/SBoxPanel.h"
    #include "Widgets/Layout/SBorder.h"
    #include "Widgets/Layout/SBox.h"
    #include "Widgets/Text/STextBlock.h"
    #include "Widgets/Input/SButton.h"
    #include "Widgets/Notifications/SProgressBar.h"
    #include "Styling/AppStyle.h"
    #include "Styling/CoreStyle.h"

    #define LOCTEXT_NAMESPACE "NyraBanner"

    static FLinearColor ColorForKind(ENyraBannerKind K)
    {
        switch (K)
        {
        case ENyraBannerKind::Info:    return FLinearColor(0.25f, 0.40f, 0.75f, 0.95f);
        case ENyraBannerKind::Warning: return FLinearColor(0.75f, 0.55f, 0.15f, 0.95f);
        case ENyraBannerKind::Error:   return FLinearColor(0.80f, 0.25f, 0.25f, 0.95f);
        default:                       return FLinearColor::Transparent;
        }
    }

    void SNyraBanner::Construct(const FArguments& InArgs)
    {
        ChildSlot
        [
            SNew(SBorder)
            .Visibility(EVisibility::Collapsed)
            .BorderImage(FAppStyle::GetBrush("ToolPanel.GroupBorder"))
            .BorderBackgroundColor_Lambda([this]() { return ColorForKind(CurrentKind); })
            .Padding(FMargin(8))
            [
                SAssignNew(Row, SHorizontalBox)
            ]
        ];
    }

    void SNyraBanner::SetState(ENyraBannerKind Kind, const FText& Message)
    {
        SetState(Kind, Message, FOnBannerRestartClicked(), FOnBannerOpenLogClicked());
    }

    void SNyraBanner::SetState(ENyraBannerKind Kind, const FText& Message,
                                const FOnBannerRestartClicked& RestartHandler,
                                const FOnBannerOpenLogClicked& OpenLogHandler)
    {
        CurrentKind = Kind;
        RestartDelegate = RestartHandler;
        OpenLogDelegate = OpenLogHandler;
        if (ChildSlot.GetWidget().IsValid())
        {
            ChildSlot.GetWidget()->SetVisibility(Kind == ENyraBannerKind::Hidden ? EVisibility::Collapsed : EVisibility::Visible);
        }
        if (!Row.IsValid()) return;
        Row->ClearChildren();

        // Progress bar for Info state (indeterminate)
        if (Kind == ENyraBannerKind::Info)
        {
            Row->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 8, 0)
            [
                SNew(SBox).WidthOverride(80).HeightOverride(6)
                [
                    SNew(SProgressBar)  // indeterminate mode — no Percent binding
                ]
            ];
        }

        Row->AddSlot().FillWidth(1.0f).VAlign(VAlign_Center)
        [
            SNew(STextBlock).Text(Message).ColorAndOpacity(FLinearColor::White).AutoWrapText(true)
        ];

        if (RestartDelegate.IsBound())
        {
            Row->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(8, 0, 0, 0)
            [
                SNew(SButton).Text(LOCTEXT("Restart", "Restart"))
                    .OnClicked(this, &SNyraBanner::HandleRestart)
            ];
        }
        if (OpenLogDelegate.IsBound())
        {
            Row->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(8, 0, 0, 0)
            [
                SNew(SButton).Text(LOCTEXT("OpenLog", "Open log"))
                    .OnClicked(this, &SNyraBanner::HandleOpenLog)
            ];
        }
    }

    void SNyraBanner::Hide()
    {
        CurrentKind = ENyraBannerKind::Hidden;
        if (ChildSlot.GetWidget().IsValid())
        {
            ChildSlot.GetWidget()->SetVisibility(EVisibility::Collapsed);
        }
    }

    FReply SNyraBanner::HandleRestart()
    {
        RestartDelegate.ExecuteIfBound();
        return FReply::Handled();
    }

    FReply SNyraBanner::HandleOpenLog()
    {
        OpenLogDelegate.ExecuteIfBound();
        return FReply::Handled();
    }

    #undef LOCTEXT_NAMESPACE
    ```

    **3. CREATE Public/Panel/SNyraDiagnosticsDrawer.h:**

    ```cpp
    #pragma once
    #include "CoreMinimal.h"
    #include "Widgets/SCompoundWidget.h"
    #include "Widgets/DeclarativeSyntaxSupport.h"

    class NYRAEDITOR_API SNyraDiagnosticsDrawer : public SCompoundWidget
    {
    public:
        SLATE_BEGIN_ARGS(SNyraDiagnosticsDrawer) {}
        SLATE_END_ARGS()

        void Construct(const FArguments& InArgs);

        /** Refresh tail from disk (100 lines). */
        void RefreshFromDisk();

        /** Returns absolute log path (<ProjectDir>/Saved/NYRA/logs/nyrahost-<today>.log). */
        static FString LogFilePath();

    private:
        FReply HandleToggle();
        FReply HandleRefresh();

        TSharedPtr<class SMultiLineEditableTextBox> TailBox;
        TSharedPtr<class SBox> ContentContainer;
        bool bExpanded = false;
    };
    ```

    **4. CREATE Private/Panel/SNyraDiagnosticsDrawer.cpp:**

    ```cpp
    #include "Panel/SNyraDiagnosticsDrawer.h"
    #include "Widgets/SBoxPanel.h"
    #include "Widgets/Layout/SBorder.h"
    #include "Widgets/Layout/SBox.h"
    #include "Widgets/Layout/SExpandableArea.h"
    #include "Widgets/Input/SButton.h"
    #include "Widgets/Input/SMultiLineEditableTextBox.h"
    #include "Widgets/Text/STextBlock.h"
    #include "Misc/Paths.h"
    #include "Misc/FileHelper.h"
    #include "Misc/DateTime.h"
    #include "Styling/AppStyle.h"

    #define LOCTEXT_NAMESPACE "NyraDiagnosticsDrawer"

    FString SNyraDiagnosticsDrawer::LogFilePath()
    {
        const FString DateStr = FDateTime::UtcNow().ToString(TEXT("%Y-%m-%d"));
        return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("NYRA"), TEXT("logs"),
                                FString::Printf(TEXT("nyrahost-%s.log"), *DateStr));
    }

    void SNyraDiagnosticsDrawer::Construct(const FArguments& InArgs)
    {
        ChildSlot
        [
            SNew(SExpandableArea)
            .InitiallyCollapsed(true)
            .HeaderContent()
            [
                SNew(STextBlock).Text(LOCTEXT("DiagHeader", "Diagnostics"))
            ]
            .BodyContent()
            [
                SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight()
                [
                    SNew(SHorizontalBox)
                    + SHorizontalBox::Slot().AutoWidth()
                    [
                        SNew(SButton).Text(LOCTEXT("Refresh", "Refresh"))
                            .OnClicked(this, &SNyraDiagnosticsDrawer::HandleRefresh)
                    ]
                    + SHorizontalBox::Slot().FillWidth(1.0f).VAlign(VAlign_Center).Padding(8, 0)
                    [
                        SNew(STextBlock).Text_Lambda([]() { return FText::FromString(LogFilePath()); })
                            .ColorAndOpacity(FLinearColor(0.6f, 0.6f, 0.6f))
                    ]
                ]
                + SVerticalBox::Slot().FillHeight(1.0f).MaxHeight(300).Padding(0, 6, 0, 0)
                [
                    SAssignNew(TailBox, SMultiLineEditableTextBox)
                    .IsReadOnly(true)
                    .AutoWrapText(false)
                    .Font(FAppStyle::GetFontStyle(TEXT("MonospacedText")))
                ]
            ]
        ];
    }

    void SNyraDiagnosticsDrawer::RefreshFromDisk()
    {
        if (!TailBox.IsValid()) return;
        TArray<FString> Lines;
        if (!FFileHelper::LoadFileToStringArray(Lines, *LogFilePath()))
        {
            TailBox->SetText(FText::FromString(TEXT("(log file not yet written)")));
            return;
        }
        const int32 Start = FMath::Max(0, Lines.Num() - 100);
        FString Out;
        for (int32 I = Start; I < Lines.Num(); ++I)
        {
            Out += Lines[I] + TEXT("\n");
        }
        TailBox->SetText(FText::FromString(Out));
    }

    FReply SNyraDiagnosticsDrawer::HandleToggle()
    {
        bExpanded = !bExpanded;
        if (bExpanded) RefreshFromDisk();
        return FReply::Handled();
    }

    FReply SNyraDiagnosticsDrawer::HandleRefresh()
    {
        RefreshFromDisk();
        return FReply::Handled();
    }

    #undef LOCTEXT_NAMESPACE
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "class NYRAEDITOR_API SNyraBanner" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraBanner.h` equals 1
      - `grep -c "enum class ENyraBannerKind" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraBanner.h` equals 1
      - `grep -c "SetState" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraBanner.h` >= 2
      - `grep -c "SProgressBar" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraBanner.cpp` >= 1
      - `grep -c "FFileHelper::LoadFileToStringArray" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraDiagnosticsDrawer.cpp` equals 1
      - `grep -c 'TEXT("nyrahost-%s.log")' TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraDiagnosticsDrawer.cpp` equals 1
      - `grep -c "FMath::Max(0, Lines.Num() - 100)" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraDiagnosticsDrawer.cpp` equals 1
      - `grep -c "SExpandableArea" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraDiagnosticsDrawer.cpp` >= 1
    </automated>
  </verify>
  <acceptance_criteria>
    - SNyraBanner.h exports `enum class ENyraBannerKind {Hidden, Info, Warning, Error}` AND `SetState` overloads (with/without button delegates) AND `Hide()`
    - SNyraBanner.cpp uses `SProgressBar` (indeterminate mode) inside Info-kind banner
    - SNyraBanner.cpp color-codes banners via ColorForKind: Info=blue, Warning=yellow, Error=red
    - SNyraDiagnosticsDrawer.h exports `LogFilePath()` static returning `<ProjectSaved>/NYRA/logs/nyrahost-<YYYY-MM-DD>.log`
    - SNyraDiagnosticsDrawer.cpp uses `SExpandableArea` with `InitiallyCollapsed(true)`
    - SNyraDiagnosticsDrawer.cpp `RefreshFromDisk` calls `FFileHelper::LoadFileToStringArray` and shows last 100 lines in a monospace `SMultiLineEditableTextBox` (read-only)
    - SNyraDiagnosticsDrawer.cpp falls back gracefully when log file doesn't exist yet
  </acceptance_criteria>
  <done>Banner + diagnostics drawer widgets ready; Task 2 wires them into SNyraChatPanel.</done>
</task>

<task type="auto">
  <name>Task 2: SNyraDownloadModal + wire banner/modal/drawer into SNyraChatPanel</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraDownloadModal.h
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraDownloadModal.cpp
    TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp
  </files>
  <read_first>
    - docs/JSONRPC.md §3.7 diagnostics/download-progress param shape
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraBanner.h (just created)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraDiagnosticsDrawer.h (just created)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp (Plan 12)
    - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Process/FNyraSupervisor.h (state enum)
  </read_first>
  <action>
    **1. CREATE Public/Panel/SNyraDownloadModal.h:**

    ```cpp
    #pragma once
    #include "CoreMinimal.h"
    #include "Widgets/SCompoundWidget.h"
    #include "Widgets/DeclarativeSyntaxSupport.h"
    #include "WS/FNyraJsonRpc.h"

    DECLARE_DELEGATE(FOnDownloadCancelled);

    class NYRAEDITOR_API SNyraDownloadModal : public SCompoundWidget
    {
    public:
        SLATE_BEGIN_ARGS(SNyraDownloadModal) {}
            SLATE_EVENT(FOnDownloadCancelled, OnCancelled)
        SLATE_END_ARGS()

        void Construct(const FArguments& InArgs);

        /** Feed a diagnostics/download-progress params object (from Env.Params). */
        void OnProgress(const TSharedPtr<FJsonObject>& Params);

        void Show();
        void Hide();
        bool IsShown() const { return bVisible; }

    private:
        FReply HandleCancel();

        TSharedPtr<class SProgressBar> ProgressBar;
        TSharedPtr<class STextBlock> StatusText;
        TSharedPtr<class STextBlock> BytesText;
        TSharedPtr<class SBox> RootContainer;
        int64 BytesDone = 0;
        int64 BytesTotal = 0;
        FString CurrentStatus;
        FOnDownloadCancelled OnCancelledDelegate;
        bool bVisible = false;
    };
    ```

    **2. CREATE Private/Panel/SNyraDownloadModal.cpp:**

    ```cpp
    #include "Panel/SNyraDownloadModal.h"
    #include "Widgets/SBoxPanel.h"
    #include "Widgets/Layout/SBorder.h"
    #include "Widgets/Layout/SBox.h"
    #include "Widgets/Text/STextBlock.h"
    #include "Widgets/Input/SButton.h"
    #include "Widgets/Notifications/SProgressBar.h"
    #include "Styling/AppStyle.h"
    #include "Dom/JsonObject.h"

    #define LOCTEXT_NAMESPACE "NyraDownloadModal"

    void SNyraDownloadModal::Construct(const FArguments& InArgs)
    {
        OnCancelledDelegate = InArgs._OnCancelled;
        ChildSlot
        [
            SAssignNew(RootContainer, SBox)
            .Visibility(EVisibility::Collapsed)
            [
                SNew(SBorder)
                .BorderImage(FAppStyle::GetBrush("ToolPanel.GroupBorder"))
                .Padding(FMargin(16))
                [
                    SNew(SVerticalBox)
                    + SVerticalBox::Slot().AutoHeight()
                    [
                        SNew(STextBlock).Text(LOCTEXT("Title", "Downloading Gemma 3 4B (3.16 GB)"))
                            .Font(FAppStyle::GetFontStyle(TEXT("BoldFont")))
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 8, 0, 0)
                    [
                        SAssignNew(StatusText, STextBlock).Text(LOCTEXT("Starting", "Starting…"))
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 6, 0, 0)
                    [
                        SAssignNew(ProgressBar, SProgressBar).Percent_Lambda([this]() -> TOptional<float>
                        {
                            if (BytesTotal <= 0) return TOptional<float>();
                            return float(BytesDone) / float(BytesTotal);
                        })
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 6, 0, 0)
                    [
                        SAssignNew(BytesText, STextBlock).Text(FText::GetEmpty())
                            .ColorAndOpacity(FLinearColor(0.6f, 0.6f, 0.6f))
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 12, 0, 0)
                    [
                        SNew(SButton).Text(LOCTEXT("Cancel", "Cancel"))
                            .OnClicked(this, &SNyraDownloadModal::HandleCancel)
                    ]
                ]
            ]
        ];
    }

    void SNyraDownloadModal::Show()
    {
        bVisible = true;
        if (RootContainer.IsValid()) RootContainer->SetVisibility(EVisibility::Visible);
    }

    void SNyraDownloadModal::Hide()
    {
        bVisible = false;
        if (RootContainer.IsValid()) RootContainer->SetVisibility(EVisibility::Collapsed);
    }

    void SNyraDownloadModal::OnProgress(const TSharedPtr<FJsonObject>& Params)
    {
        if (!Params.IsValid()) return;
        Show();
        FString Status;
        Params->TryGetStringField(TEXT("status"), Status);
        CurrentStatus = Status;

        double BytesDoneD = 0.0, BytesTotalD = 0.0;
        Params->TryGetNumberField(TEXT("bytes_done"), BytesDoneD);
        Params->TryGetNumberField(TEXT("bytes_total"), BytesTotalD);
        BytesDone = static_cast<int64>(BytesDoneD);
        BytesTotal = static_cast<int64>(BytesTotalD);

        if (Status == TEXT("downloading"))
        {
            const int32 Pct = BytesTotal > 0 ? int32(100.0 * BytesDone / BytesTotal) : 0;
            StatusText->SetText(FText::Format(LOCTEXT("Downloading", "Downloading… {0}%"), FText::AsNumber(Pct)));
        }
        else if (Status == TEXT("verifying"))
        {
            StatusText->SetText(LOCTEXT("Verifying", "Verifying SHA256…"));
        }
        else if (Status == TEXT("done"))
        {
            StatusText->SetText(LOCTEXT("Done", "Done!"));
            // Auto-hide after a short delay in a real app; Phase 1: user dismisses manually.
        }
        else if (Status == TEXT("error"))
        {
            FString Remediation;
            const TSharedPtr<FJsonObject>* Err;
            if (Params->TryGetObjectField(TEXT("error"), Err) && Err && Err->IsValid())
            {
                const TSharedPtr<FJsonObject>* Data;
                if ((*Err)->TryGetObjectField(TEXT("data"), Data) && Data && Data->IsValid())
                {
                    (*Data)->TryGetStringField(TEXT("remediation"), Remediation);
                }
            }
            StatusText->SetText(FText::FromString(TEXT("Error: ") + Remediation));
        }

        if (BytesTotal > 0)
        {
            BytesText->SetText(FText::FromString(FString::Printf(
                TEXT("%.1f MB / %.1f MB"),
                double(BytesDone) / (1024.0 * 1024.0),
                double(BytesTotal) / (1024.0 * 1024.0))));
        }
    }

    FReply SNyraDownloadModal::HandleCancel()
    {
        OnCancelledDelegate.ExecuteIfBound();
        Hide();
        return FReply::Handled();
    }

    #undef LOCTEXT_NAMESPACE
    ```

    **3. UPDATE Private/Panel/SNyraChatPanel.cpp** — add banner/modal/drawer
    members (in SNyraChatPanel.h declaration too). Modifications:

    In SNyraChatPanel.h, add private members:
    ```cpp
    TSharedPtr<class SNyraBanner> Banner;
    TSharedPtr<class SNyraDownloadModal> DownloadModal;
    TSharedPtr<class SNyraDiagnosticsDrawer> Diagnostics;
    ```

    Add includes at top of SNyraChatPanel.cpp:
    ```cpp
    #include "Panel/SNyraBanner.h"
    #include "Panel/SNyraDownloadModal.h"
    #include "Panel/SNyraDiagnosticsDrawer.h"
    #include "Process/FNyraSupervisor.h"
    #include "Misc/Paths.h"
    #include "HAL/PlatformProcess.h"
    ```

    Modify `SNyraChatPanel::Construct` to build a 4-row layout
    (Banner / MessageList / DownloadModal overlay / Composer / Diagnostics):

    ```cpp
    void SNyraChatPanel::Construct(const FArguments& InArgs)
    {
        CurrentConversationId = FGuid::NewGuid();

        ChildSlot
        [
            SNew(SVerticalBox)
            + SVerticalBox::Slot().AutoHeight()
            [
                SAssignNew(Banner, SNyraBanner)
            ]
            + SVerticalBox::Slot().FillHeight(1.0f)
            [
                SNew(SOverlay)
                + SOverlay::Slot()
                [
                    SAssignNew(MessageList, SNyraMessageList)
                    .OnCancel(FOnMessageCancel::CreateRaw(this, &SNyraChatPanel::OnMessageCancel))
                ]
                + SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
                [
                    SAssignNew(DownloadModal, SNyraDownloadModal)
                    .OnCancelled_Lambda([]()
                    {
                        // Phase 1: Python side has no cancel endpoint for the downloader;
                        // Plan 13 accepts this and the modal simply closes. The background
                        // task in NyraHost finishes or errors naturally.
                    })
                ]
            ]
            + SVerticalBox::Slot().AutoHeight().Padding(6)
            [
                SAssignNew(Composer, SNyraComposer)
                .OnSubmit(FOnComposerSubmit::CreateRaw(this, &SNyraChatPanel::OnComposerSubmit))
            ]
            + SVerticalBox::Slot().AutoHeight()
            [
                SAssignNew(Diagnostics, SNyraDiagnosticsDrawer)
            ]
        ];

        if (GNyraSupervisor.IsValid())
        {
            GNyraSupervisor->OnNotification.BindRaw(this, &SNyraChatPanel::HandleNotification);
            GNyraSupervisor->OnStateChanged.BindLambda([this](ENyraSupervisorState NewState)
            {
                if (!Banner.IsValid()) return;
                switch (NewState)
                {
                case ENyraSupervisorState::Spawning:
                case ENyraSupervisorState::WaitingForHandshake:
                case ENyraSupervisorState::Connecting:
                case ENyraSupervisorState::Authenticating:
                    Banner->SetState(ENyraBannerKind::Info,
                        FText::FromString(TEXT("Setting up NYRA (~30s)")));
                    break;
                case ENyraSupervisorState::Ready:
                    Banner->Hide();
                    break;
                case ENyraSupervisorState::Crashed:
                    Banner->SetState(ENyraBannerKind::Warning,
                        FText::FromString(TEXT("NyraHost crashed — restarting")));
                    break;
                default:
                    break;
                }
            });
            GNyraSupervisor->OnUnstable.BindLambda([this]()
            {
                if (!Banner.IsValid()) return;
                FOnBannerRestartClicked RestartCb = FOnBannerRestartClicked::CreateLambda([]()
                {
                    // Full restart: shut down + respawn via supervisor
                    if (GNyraSupervisor.IsValid())
                    {
                        GNyraSupervisor->RequestShutdown();
                        // Respawn: recreate the supervisor
                        const FString PluginDir = IPluginManager::Get().FindPlugin(TEXT("NYRA"))->GetBaseDir();
                        const FString ProjectDir = FPaths::ProjectDir();
                        const FString LogDir = FPaths::Combine(ProjectDir, TEXT("Saved"), TEXT("NYRA"), TEXT("logs"));
                        GNyraSupervisor = MakeUnique<FNyraSupervisor>();
                        GNyraSupervisor->SpawnAndConnect(ProjectDir, PluginDir, LogDir);
                    }
                });
                FOnBannerOpenLogClicked OpenLogCb = FOnBannerOpenLogClicked::CreateLambda([]()
                {
                    const FString LogPath = SNyraDiagnosticsDrawer::LogFilePath();
                    FPlatformProcess::ExploreFolder(*FPaths::GetPath(LogPath));
                });
                Banner->SetState(ENyraBannerKind::Error,
                    FText::FromString(TEXT("NyraHost is unstable — see Saved/NYRA/logs/")),
                    RestartCb, OpenLogCb);
            });
        }
    }
    ```

    Extend `HandleNotification` to route diagnostics/download-progress to the
    modal:

    ```cpp
    void SNyraChatPanel::HandleNotification(const FNyraJsonRpcEnvelope& Env)
    {
        if (!Env.Params.IsValid()) return;

        // Download progress
        if (Env.Method == TEXT("diagnostics/download-progress"))
        {
            if (DownloadModal.IsValid()) DownloadModal->OnProgress(Env.Params);
            return;
        }

        // Chat stream (existing Plan 12 body)
        if (Env.Method == TEXT("chat/stream"))
        {
            FString ReqIdStr;
            if (!Env.Params->TryGetStringField(TEXT("req_id"), ReqIdStr)) return;
            FGuid ReqId; FGuid::Parse(ReqIdStr, ReqId);
            FString Delta; Env.Params->TryGetStringField(TEXT("delta"), Delta);
            bool bDone = false; Env.Params->TryGetBoolField(TEXT("done"), bDone);
            bool bCancelled = false; Env.Params->TryGetBoolField(TEXT("cancelled"), bCancelled);
            FString Remediation;
            const TSharedPtr<FJsonObject>* ErrObj;
            if (Env.Params->TryGetObjectField(TEXT("error"), ErrObj) && ErrObj && ErrObj->IsValid())
            {
                const TSharedPtr<FJsonObject>* DataObj;
                if ((*ErrObj)->TryGetObjectField(TEXT("data"), DataObj) && DataObj && DataObj->IsValid())
                {
                    (*DataObj)->TryGetStringField(TEXT("remediation"), Remediation);
                }
            }
            if (!Delta.IsEmpty()) MessageList->UpdateMessageStreaming(ReqId, Delta);
            if (bDone)
            {
                if (TSharedPtr<FNyraMessage> M = MessageList->FindByReqId(ReqId))
                {
                    MessageList->FinalizeMessage(ReqId, M->StreamingBuffer, bCancelled, Remediation);
                }
            }
            return;
        }
    }
    ```

    Also update SNyraChatPanel.h to include the additional include required
    for `IPluginManager`:
    ```cpp
    // In SNyraChatPanel.cpp top
    #include "Interfaces/IPluginManager.h"
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "class NYRAEDITOR_API SNyraDownloadModal" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraDownloadModal.h` equals 1
      - `grep -c "OnProgress" TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraDownloadModal.h` >= 1
      - `grep -c "SProgressBar" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraDownloadModal.cpp` >= 1
      - `grep -c "diagnostics/download-progress" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp` >= 1
      - `grep -c "GNyraSupervisor->OnStateChanged.BindLambda" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp` equals 1
      - `grep -c "GNyraSupervisor->OnUnstable.BindLambda" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp` equals 1
      - `grep -c "FPlatformProcess::ExploreFolder" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp` >= 1
      - `grep -c "Setting up NYRA" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp` >= 1
      - `grep -c "NyraHost is unstable" TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp` >= 1
      - TestProject builds cleanly
    </automated>
  </verify>
  <acceptance_criteria>
    - SNyraDownloadModal.h exports SCompoundWidget with methods `OnProgress(TSharedPtr<FJsonObject>)`, `Show`, `Hide`, `IsShown`, delegate `OnCancelled`
    - SNyraDownloadModal.cpp `OnProgress` interprets status field values: `downloading`, `verifying`, `done`, `error`; updates StatusText accordingly
    - SNyraDownloadModal.cpp displays `SProgressBar` with Percent_Lambda reading BytesDone/BytesTotal
    - SNyraChatPanel.cpp Construct adds Banner on top, MessageList + DownloadModal overlay in middle, Composer + Diagnostics below
    - SNyraChatPanel.cpp binds `GNyraSupervisor->OnStateChanged` with banner state transitions matching the spec (Info for Spawning/WaitingForHandshake/Connecting/Authenticating, Hide for Ready, Warning for Crashed)
    - SNyraChatPanel.cpp binds `GNyraSupervisor->OnUnstable` with Error banner containing `[Restart]` + `[Open log]` buttons
    - SNyraChatPanel.cpp `[Open log]` button calls `FPlatformProcess::ExploreFolder` on the logs directory
    - SNyraChatPanel.cpp `HandleNotification` dispatches `diagnostics/download-progress` to DownloadModal BEFORE chat/stream handling
    - Project compiles; manual verification: opening Tools > NYRA > Chat during bootstrap shows Info banner; after Ready, banner disappears
  </acceptance_criteria>
  <done>Banner state machine, download modal, diagnostics drawer all wired into SNyraChatPanel; first-run UX complete.</done>
</task>

</tasks>

<verification>
Manual:
1. Delete `%LOCALAPPDATA%/NYRA/venv/` and `<ProjectDir>/Saved/NYRA/`. Open UE 5.6 test project, open NYRA Chat tab.
2. Observe: banner "Setting up NYRA (~30s)" → panel shows message "gemma_not_installed" on first chat send → clicking "Download Gemma" (to be surfaced in Phase 1 either via settings or via the error message) opens modal.
3. Kill NyraHost 3 times via Task Manager within 60s → banner shows "NyraHost is unstable" with Restart + Open log buttons.
4. Click Diagnostics → drawer expands → shows last 100 log lines.
</verification>

<success_criteria>
- SNyraBanner shows Info during bootstrap, Warning on crash, Error on Unstable
- SNyraDownloadModal consumes diagnostics/download-progress notifications
- SNyraDiagnosticsDrawer tails log directly (no diagnostics/tail WS method)
- First-run state machine per RESEARCH §3.9 fully implemented
</success_criteria>

<output>
After completion, create `.planning/phases/01-plugin-shell-three-process-ipc/01-13-SUMMARY.md`
listing: banner kind -> supervisor state mapping, download modal status flow,
log path convention, known limit (no download cancel on Python side in Phase 1).
</output>
