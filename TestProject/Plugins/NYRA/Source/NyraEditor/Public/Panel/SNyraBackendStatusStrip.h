// =============================================================================
// SNyraBackendStatusStrip.h  (Phase 2 Plan 02-12 — status pill UI)
//
// Three-pill horizontal status strip:
//   [Claude] [Gemma] [Privacy]
//
// Pill colour maps router states per RESEARCH §9.3:
//   Green  = ready
//   Yellow = rate-limited
//   Red    = auth-drift / signed out
//   Grey   = offline / not-installed / not-configured
//   Blue   = downloading / loading
//   Purple = privacy-mode active (overlay on all pills)
//
// Mounted in SNyraChatPanel between the banner (Plan 13) and the message list
// (Plan 12). Subscribes to diagnostics/backend-state notifications and
// updates pill appearance in real time. Click opens a context-sensitive popover.
//
// Per CONTEXT.md:
//   D-03  — state enum maps 1:1 to pill colour
//   D-05  — Privacy Mode has distinctive purple overlay across all three pills
//   D-23  — diagnostics/backend-state notification already documented
//   D-24  — module-superset on SNyraChatPanel
// =============================================================================

#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Button/SButton.h"
#include "Widgets/SBorder.h"
#include "Widgets/SMenuAnchor.h"
#include "Widgets/Notifications/SNotificationList.h"

// -----------------------------------------------------------------
// FNyraBackendState — POD mirror of diagnostics/backend-state params
// -----------------------------------------------------------------

class FNyraBackendState
{
public:
    struct FClaudeState
    {
        bool bInstalled = false;
        FString Version;
        FString Auth;        // "pro" | "max" | "teams" | "enterprise" | ""
        FString State;       // "ready" | "rate-limited" | "auth-drift" | "offline"
        TOptional<FDateTime> RateLimitResetsAt;
    };
    struct FGemmaState
    {
        bool bModelPresent = false;
        FString Runtime;     // "ollama" | "llama-server"
        FString State;       // "ready" | "downloading" | "loading" | "not-installed"
    };


    FClaudeState Claude;
    FGemmaState Gemma;


    /** Normal = normal mode; PrivacyMode = egress-blocked overlay active. */
    enum class ENyraPrivacyMode : uint8
    {
        Normal = 0,
        PrivacyMode = 1,
    };
    ENyraPrivacyMode Mode = ENyraPrivacyMode::Normal;
    FDateTime UpdatedAt;

    /** Parse JSON shaped like docs/JSONRPC.md §4.8 diagnostics/backend-state params.
     *  Returns a default-constructed (all-grey) state on parse failure. */
    static FNyraBackendState ParseJson(const FString& Json);
};

// -----------------------------------------------------------------
// SNyraBackendStatusStrip
// -----------------------------------------------------------------

class NYRAEDITOR_API SNyraBackendStatusStrip : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SNyraBackendStatusStrip) {}
        /** Fired when user clicks the Claude pill. */
        SLATE_EVENT(FSimpleDelegate, OnClaudeClick)
        /** Fired when user clicks the Gemma pill. */
        SLATE_EVENT(FSimpleDelegate, OnGemmaClick)
        /** Fired when user clicks the Privacy pill. */
        SLATE_EVENT(FSimpleDelegate, OnPrivacyClick)
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);

    /** Update strip state from a parsed FNyraBackendState.
     *  Triggers Invalidate(EInvalidationReason::Paint) so colours + tooltips refresh. */
    void SetState(const FNyraBackendState& NewState);

private:
    // Pill colour constants (per RESEARCH §9.3)
    static constexpr FLinearColor GreenColour()  { return FLinearColor(0.2f, 0.7f, 0.3f); }
    static constexpr FLinearColor YellowColour() { return FLinearColor(0.85f, 0.7f, 0.15f); }
    static constexpr FLinearColor RedColour()     { return FLinearColor(0.8f, 0.15f, 0.15f); }
    static constexpr FLinearColor GreyColour()    { return FLinearColor(0.45f, 0.45f, 0.45f); }
    static constexpr FLinearColor PurpleColour() { return FLinearColor(0.55f, 0.25f, 0.75f); }
    static constexpr FLinearColor BlueColour()    { return FLinearColor(0.2f, 0.5f, 0.85f); }

    // Colour from Claude pill state string
    FLinearColor ClaudeColour() const;
    FText ClaudeTooltip() const;

    FLinearColor GemmaColour() const;
    FText GemmaTooltip() const;

    FLinearColor PrivacyColour() const;
    FText PrivacyTooltip() const;

    // Privacy-mode overlay — applied to the outer wrapper when in PrivacyMode
    bool IsPrivacyMode() const { return CurrentState.Mode == FNyraBackendState::ENyraPrivacyMode::PrivacyMode; }

    FNyraBackendState CurrentState;

    // Delegates from SNyraChatPanel
    FSimpleDelegate OnClaudeClick;
    FSimpleDelegate OnGemmaClick;
    FSimpleDelegate OnPrivacyClick;

    // Popover anchor (opened on pill click)
    TSharedPtr<SMenuAnchor> PopoverAnchor;
};
