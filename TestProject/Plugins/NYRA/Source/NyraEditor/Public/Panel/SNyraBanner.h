// =============================================================================
// SNyraBanner.h  (Phase 1 Plan 13 -- first-run UX banners + diagnostics)
// =============================================================================
//
// Top-banner widget mounted above SNyraMessageList in SNyraChatPanel. Wired
// to FNyraSupervisor state transitions (Plan 10) to satisfy RESEARCH §3.9's
// "panel is ALWAYS usable" invariant.
//
// Banner state mapping (RESEARCH §3.9 table):
//   ENyraSupervisorState::Spawning
//                       ::WaitingForHandshake
//                       ::Connecting
//                       ::Authenticating   -> ENyraBannerKind::Info
//                       ::Ready            -> ENyraBannerKind::Hidden
//                       ::Crashed          -> ENyraBannerKind::Warning
//   OnUnstable (3-in-60s trip)             -> ENyraBannerKind::Error
//
// Kind -> visual:
//   Hidden   -> EVisibility::Collapsed (zero layout footprint)
//   Info     -> blue-accent border + indeterminate SProgressBar + message
//   Warning  -> yellow-accent border + message
//   Error    -> red-accent border + message + [Restart] + [Open log] buttons
//
// The two SetState overloads distinguish banners with button delegates
// (Error kind) from banners with message only (Info/Warning).
// =============================================================================

#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/DeclarativeSyntaxSupport.h"

enum class ENyraBannerKind : uint8
{
    Hidden,
    Info,      // blue-accent: Setting up NYRA
    Warning,   // yellow-accent: Crashed / handshake timeout
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

    /** Primary state setter. Buttons shown only if the corresponding delegate is bound. */
    void SetState(ENyraBannerKind Kind, const FText& Message,
                  const FOnBannerRestartClicked& RestartHandler,
                  const FOnBannerOpenLogClicked& OpenLogHandler);

    /** Convenience: banner with no action buttons. */
    void SetState(ENyraBannerKind Kind, const FText& Message);

    void Hide();

    ENyraBannerKind GetCurrentKind() const { return CurrentKind; }

private:
    FReply HandleRestart();
    FReply HandleOpenLog();

    ENyraBannerKind CurrentKind = ENyraBannerKind::Hidden;
    TSharedPtr<class SBorder> RootBorder;
    TSharedPtr<class SHorizontalBox> Row;
    FOnBannerRestartClicked RestartDelegate;
    FOnBannerOpenLogClicked OpenLogDelegate;
};
