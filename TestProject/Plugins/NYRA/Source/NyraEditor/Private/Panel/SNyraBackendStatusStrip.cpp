// =============================================================================
// SNyraBackendStatusStrip.cpp  (Phase 2 Plan 02-12 — status pill UI)
//
// Per RESEARCH §9.3 colour mapping:
//   Claude:  ready → Green | rate-limited → Yellow | auth-drift → Red | offline → Grey
//   Gemma:  ready → Green | downloading/loading → Blue | not-installed → Grey
//   Privacy: PrivacyMode → solid Purple pill (always visible, toggles mode on click)
//
// Clicking a pill fires its delegate so SNyraChatPanel opens the popover.
// Privacy pill always visible — its click toggles session/set-mode.
//
// Privacy-mode overlay (D-05): when Mode==PrivacyMode, a purple SBorder
// wraps all three pills with alpha 0.5 so the user immediately sees egress is blocked.
// =============================================================================

#include "Panel/SNyraBackendStatusStrip.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

#define LOCTEXT_NAMESPACE "NyraBackendStatusStrip"

// -----------------------------------------------------------------
// FNyraBackendState::ParseJson — mirrors docs/JSONRPC.md §4.8 shape
// -----------------------------------------------------------------

FNyraBackendState FNyraBackendState::ParseJson(const FString& Json)
{
    FNyraBackendState Out;

    TSharedRef<TJsonReader<TCHAR>> Reader = TJsonReaderFactory<TCHAR>::Create(Json);
    TSharedPtr<FJsonObject> Obj;
    if (!FJsonSerializer::Deserialize(Reader, Obj) || !Obj.IsValid())
    {
        return Out;  // default: all-grey / Normal
    }

    // claude block
    if (TSharedPtr<FJsonObject> C = Obj->GetObjectField(TEXT("claude")))
    {
        Out.Claude.bInstalled = C->GetBoolField(TEXT("installed"));
        Out.Claude.Version   = C->GetStringField(TEXT("version"));
        Out.Claude.Auth      = C->GetStringField(TEXT("auth"));
        Out.Claude.State     = C->GetStringField(TEXT("state"));

        double Ts = 0.0;
        if (C->TryGetNumberField(TEXT("rate_limit_resets_at"), Ts))
        {
            Out.Claude.RateLimitResetsAt = FDateTime::FromUnixTimestamp(static_cast<int64>(Ts));
        }
    }

    // gemma block
    if (TSharedPtr<FJsonObject> G = Obj->GetObjectField(TEXT("gemma")))
    {
        Out.Gemma.bModelPresent = G->GetBoolField(TEXT("model_present"));
        Out.Gemma.Runtime       = G->GetStringField(TEXT("runtime"));
        Out.Gemma.State         = G->GetStringField(TEXT("state"));
    }


    // mode
    FString ModeStr;
    if (Obj->TryGetStringField(TEXT("mode"), ModeStr))
    {
        Out.Mode = (ModeStr == TEXT("privacy-mode"))
            ? ENyraPrivacyMode::PrivacyMode
            : ENyraPrivacyMode::Normal;
    }

    double UpdatedAt = 0.0;
    if (Obj->TryGetNumberField(TEXT("updated_at"), UpdatedAt))
    {
        Out.UpdatedAt = FDateTime::FromUnixTimestamp(static_cast<int64>(UpdatedAt));
    }

    return Out;
}

// -----------------------------------------------------------------
// Helper: relative-time string for rate-limit resets
// -----------------------------------------------------------------

static FText RelativeTimeFromDateTime(const FDateTime& DateTime)
{
    if (!DateTime.IsValid()) return FText::GetEmpty();

    FTimespan Diff = DateTime - FDateTime::Now();
    if (Diff.GetTotalMinutes() < 1)
        return LOCTEXT("LessThanMin", "< 1 min");
    if (Diff.GetTotalHours() < 1)
        return FText::Format(LOCTEXT("MinutesFmt", "{0} min"),
            FText::AsNumber(static_cast<int32>(Diff.GetTotalMinutes())));

    return FText::Format(LOCTEXT("HoursMinFmt", "{0}h {1}m"),
        FText::AsNumber(static_cast<int32>(Diff.GetHours())),
        FText::AsNumber(static_cast<int32>(Diff.GetMinutes() % 60)));
}

// -----------------------------------------------------------------
// Colour helpers
// -----------------------------------------------------------------

FLinearColor SNyraBackendStatusStrip::ClaudeColour() const
{
    const FString& S = CurrentState.Claude.State;
    if (S == TEXT("ready"))        return GreenColour();
    if (S == TEXT("rate-limited")) return YellowColour();
    if (S == TEXT("auth-drift"))   return RedColour();
    // Grey: offline / not-installed / empty
    return GreyColour();
}

FText SNyraBackendStatusStrip::ClaudeTooltip() const
{
    const FString& S = CurrentState.Claude.State;
    if (S == TEXT("ready"))
    {
        return FText::Format(LOCTEXT("ClaudeReady", "Claude {0} connected"),
            CurrentState.Claude.Auth.IsEmpty()
                ? TEXT("CLI")
                : FText::FromString(CurrentState.Claude.Auth));
    }
    if (S == TEXT("rate-limited"))
    {
        FText RelTime = RelativeTimeFromDateTime(
            CurrentState.Claude.RateLimitResetsAt.Get(FDateTime::MaxValue()));
        if (RelTime.IsEmpty())
            return LOCTEXT("RateLimited", "Rate-limited. Resume soon.");
        return FText::Format(LOCTEXT("RateLimitedUntil", "Rate-limited. Resume in {0}."),
            RelTime);
    }
    if (S == TEXT("auth-drift"))
    {
        return LOCTEXT("AuthDrift", "Signed out — run `claude auth login`");
    }
    if (!CurrentState.Claude.bInstalled)
    {
        return LOCTEXT("NotInstalled", "Claude CLI not installed. Run `claude auth login`");
    }
    return LOCTEXT("Offline", "Offline");
}

FLinearColor SNyraBackendStatusStrip::GemmaColour() const
{
    const FString& S = CurrentState.Gemma.State;
    if (S == TEXT("ready"))       return GreenColour();
    if (S == TEXT("downloading")
        || S == TEXT("loading")) return BlueColour();
    // Grey: not-installed / any other
    return GreyColour();
}

FText SNyraBackendStatusStrip::GemmaTooltip() const
{
    const FString& S = CurrentState.Gemma.State;
    if (S == TEXT("ready"))
    {
        return FText::Format(LOCTEXT("GemmaReady", "Gemma ({0}) ready"),
            CurrentState.Gemma.Runtime.IsEmpty()
                ? TEXT("llama-server")
                : FText::FromString(CurrentState.Gemma.Runtime));
    }
    if (S == TEXT("downloading"))
        return LOCTEXT("Downloading", "Downloading Gemma… (3.16 GB)");
    if (S == TEXT("loading"))
        return LOCTEXT("Loading", "Loading Gemma (~8 s)…");
    if (S == TEXT("not-installed"))
        return LOCTEXT("GemmaNotInstalled", "Gemma not installed. Click to download (3.16 GB).");
    return LOCTEXT("GemmaOffline", "Gemma offline");
}

FLinearColor SNyraBackendStatusStrip::PrivacyColour() const
{
    return IsPrivacyMode() ? PurpleColour() : GreyColour();
}

FText SNyraBackendStatusStrip::PrivacyTooltip() const
{
    return IsPrivacyMode()
        ? LOCTEXT("PrivacyActive", "Privacy Mode active — egress blocked. Click to exit.")
        : LOCTEXT("PrivacyInactive", "Privacy Mode — local Gemma only. Click to enable.");
}

// -----------------------------------------------------------------
// SNyraBackendStatusStrip::Construct
// -----------------------------------------------------------------

void SNyraBackendStatusStrip::Construct(const FArguments& InArgs)
{
    OnClaudeClick = InArgs._OnClaudeClick;
    OnGemmaClick  = InArgs._OnGemmaClick;
    OnPrivacyClick = InArgs._OnPrivacyClick;

    // Lambdas capturing 'this' so colour + tooltip update on every paint pass.
    auto BuildClaudePill = [=]() -> TSharedRef<SWidget>
    {
        return SNew(SBorder)
            .BorderBackgroundColor_Lambda([this]() { return this->ClaudeColour(); })
            .Padding(FMargin(10, 3))
            .OnMouseButtonDown_Lambda([=](const FGeometry&, const FMouseEvent&) -> FReply
            {
                this->OnClaudeClick.ExecuteIfBound();
                return FReply::Handled();
            })
            [
                SNew(STextBlock)
                    .Text(LOCTEXT("Claude", "Claude"))
                    .ColorAndOpacity(FSlateColor(FLinearColor::White))
                    .Font(FAppStyle::GetFontStyle("SmallBoldFont"))
                    .ToolTipText_Lambda([this]() { return this->ClaudeTooltip(); })
            ];
    };

    auto BuildGemmaPill = [=]() -> TSharedRef<SWidget>
    {
        return SNew(SBorder)
            .BorderBackgroundColor_Lambda([this]() { return this->GemmaColour(); })
            .Padding(FMargin(10, 3))
            .OnMouseButtonDown_Lambda([=](const FGeometry&, const FMouseEvent&) -> FReply
            {
                this->OnGemmaClick.ExecuteIfBound();
                return FReply::Handled();
            })
            [
                SNew(STextBlock)
                    .Text(LOCTEXT("Gemma", "Gemma"))
                    .ColorAndOpacity(FSlateColor(FLinearColor::White))
                    .Font(FAppStyle::GetFontStyle("SmallBoldFont"))
                    .ToolTipText_Lambda([this]() { return this->GemmaTooltip(); })
            ];
    };

    auto BuildPrivacyPill = [=]() -> TSharedRef<SWidget>
    {
        return SNew(SBorder)
            .BorderBackgroundColor_Lambda([this]() { return this->PrivacyColour(); })
            .Padding(FMargin(10, 3))
            .OnMouseButtonDown_Lambda([=](const FGeometry&, const FMouseEvent&) -> FReply
            {
                this->OnPrivacyClick.ExecuteIfBound();
                return FReply::Handled();
            })
            [
                SNew(STextBlock)
                    .Text(LOCTEXT("Privacy", "Privacy"))
                    .ColorAndOpacity(FSlateColor(FLinearColor::White))
                    .Font(FAppStyle::GetFontStyle("SmallBoldFont"))
                    .ToolTipText_Lambda([this]() { return this->PrivacyTooltip(); })
            ];
    };

    // Privacy-mode overlay: wraps all three pills when PrivacyMode active
    auto Pills = SHorizontalBox::Slot()
        .AutoWidth()
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 4, 0)[ BuildClaudePill() ]
            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 4, 0)[ BuildGemmaPill() ]
            + SHorizontalBox::Slot().AutoWidth()[ BuildPrivacyPill() ]
        ];

    ChildSlot
    [
        SNew(SBorder)
            .BorderBackgroundColor_Lambda([this]() -> FLinearColor
            {
                return this->IsPrivacyMode()
                    ? FLinearColor(0.55f, 0.25f, 0.75f, 0.25f)
                    : FLinearColor::Transparent;
            })
            .Padding(FMargin(0, 4))
            [
                Pills
            ]
    ];
}

void SNyraBackendStatusStrip::SetState(const FNyraBackendState& NewState)
{
    CurrentState = NewState;
    Invalidate(EInvalidationReason::Paint);
}

#undef LOCTEXT_NAMESPACE
